package app.cangoo.android.data

import android.system.ErrnoException
import android.system.Os
import android.system.OsConstants
import android.system.StructStat
import java.io.DataOutputStream
import java.io.File
import java.io.OutputStream
import java.nio.file.Files
import java.security.DigestOutputStream
import java.security.MessageDigest
import java.util.UUID
import kotlinx.coroutines.CancellationException
import net.zetetic.database.DatabaseErrorHandler
import net.zetetic.database.sqlcipher.SQLiteDatabase

internal data class DeletionPreview internal constructor(
    val id: String,
    val name: String,
    val passwordCount: Long,
    val noteCount: Long,
    val snapshot: String,
    internal val rootDevice: Long,
    internal val rootInode: Long,
    internal val directoryDevice: Long,
    internal val directoryInode: Long,
    internal val bindings: VaultBindingClaims,
) { override fun toString() = "DeletionPreview(内容已隐藏)" }

internal enum class DeletionStatus(val text: String) {
    NOT_REMOVED("密码库已变化或尚未移除，请重新认证并确认后重试。"),
    REMOVED("密码库已删除。"),
    REMOVED_RESIDUAL("密码库已从列表移除，但仍有加密文件残留，尚未完成物理清理。"),
    UNCERTAIN("密码库移除结果暂时无法核实，请重新读取库列表并保留现存文件。"),
}

internal data class DeletionOutcome(val status: DeletionStatus, internal val residualDirectory: File? = null,
                                   internal val bindingCleanup: VaultCleanupStatus =
                                       VaultCleanupStatus(status != DeletionStatus.UNCERTAIN, emptyList())) {
    val text: String get() = status.text + vaultCleanupNotice(bindingCleanup)
    override fun toString() = "DeletionOutcome(${status.name})"
}

/** 只在Store的唯一存储互斥内调用；快照不授予权限，主密码每次按原值重新认证。 */
internal object VaultDeletion {
    private val preserveCorruptFile = DatabaseErrorHandler { _, _ -> }

    fun preview(root: File, id: String, rawMaster: String, guard: () -> Unit): DeletionPreview = checked {
        guard()
        if (runCatching { UUID.fromString(id).toString() == id }.getOrDefault(false).not()) unavailable()
        val rootStat = directoryStat(root)
        val directory = File(root, id)
        val directoryBefore = directoryStat(directory)
        val files = VaultLayout.resolve(directory, id)
        val manifest = files.manifest
        val metadata = Metadata.read(manifest, id)
        val key = metadata.unlock(rawMaster, files.selection)
        try {
            guard()
            // 只复用已认证的原生回滚恢复；不走Room打开或结构升级。
            val databaseFile = files.database
            val version = VaultMigration.sourceVersion(databaseFile, key, guard)
            val bindings = VaultRotation.deletionBindings(files, id, key, guard)
            val before = fingerprint(directory, guard)
            val counts = SQLiteDatabase.openDatabase(databaseFile.absolutePath, key, null,
                SQLiteDatabase.OPEN_READONLY or SQLiteDatabase.NO_LOCALIZED_COLLATORS, preserveCorruptFile, null).use { database ->
                if (!database.isReadOnly || database.version != version) unavailable()
                guard()
                val sql = if (version == 1) "SELECT (SELECT count(*) FROM passwords), 0"
                    else "SELECT (SELECT count(*) FROM passwords), (SELECT count(*) FROM notes)"
                database.query(sql).use { rows ->
                    guard()
                    if (!rows.moveToFirst() || rows.isNull(0) || rows.isNull(1)) unavailable()
                    val result = rows.getLong(0) to rows.getLong(1)
                    if (result.first < 0 || result.second < 0 || rows.moveToNext()) unavailable()
                    result
                }
            }
            val verifiedMetadata = Metadata.read(manifest, id)
            val verifiedKey = verifiedMetadata.unlock(rawMaster, files.selection)
            try { if (!metadata.sameContent(verifiedMetadata) || !MessageDigest.isEqual(key, verifiedKey) ||
                    VaultLayout.resolve(directory, id).selection != files.selection) unavailable() }
            finally { verifiedKey.fill(0) }
            if (before != fingerprint(directory, guard) || !sameIdentity(rootStat, directoryStat(root)) ||
                !sameIdentity(directoryBefore, directoryStat(directory))) unavailable()
            guard()
            DeletionPreview(id, metadata.name, counts.first, counts.second, before,
                rootStat.st_dev, rootStat.st_ino, directoryBefore.st_dev, directoryBefore.st_ino, bindings)
        } finally { key.fill(0) }
    }

    fun confirm(root: File, preview: DeletionPreview, rawMaster: String, beforePublish: () -> Unit,
                guard: () -> Unit): DeletionOutcome = checked {
        val current = this.preview(root, preview.id, rawMaster, guard)
        if (current != preview) return@checked DeletionOutcome(DeletionStatus.NOT_REMOVED)
        val source = File(root, preview.id)
        val operation = UUID.randomUUID().toString()
        val removed = File(root, ".removed_${preview.id}_$operation")
        if (Files.exists(removed.toPath(), java.nio.file.LinkOption.NOFOLLOW_LINKS)) unavailable()
        guard()
        beforePublish()
        guard()
        // 关闭当前目标连接后的最后核对仍属于发布前；此处失败尚未移动库目录。
        val assets = mutableListOf<DeletionAsset>()
        if (!matchesRoot(root, preview) || !matchesDirectory(source, preview) || fingerprint(source, guard, assets) != preview.snapshot) {
            return@checked DeletionOutcome(DeletionStatus.NOT_REMOVED)
        }
        val receipt = DeletionReceipt(preview.id, operation, preview.rootDevice, preview.rootInode,
            preview.directoryDevice, preview.directoryInode, preview.bindings, assets)
        try { VaultDeletionReceipts.write(root, receipt) }
        catch (failure: CancellationException) { throw failure }
        catch (_: Exception) { guard(); return@checked DeletionOutcome(DeletionStatus.NOT_REMOVED) }
        if (!matchesRoot(root, preview) || !matchesDirectory(source, preview) || fingerprint(source, guard) != preview.snapshot) {
            return@checked DeletionOutcome(DeletionStatus.NOT_REMOVED)
        }
        guard()
        val published = try {
            // 同一父目录整目录发布；绝不用逐文件删除代替这一步。
            Os.rename(source.absolutePath, removed.absolutePath)
            publicationState(root, source, removed, preview)
        } catch (_: Exception) {
            publicationState(root, source, removed, preview)
        }
        // 从此以后不抛普通取消冒充未删除；撤权/中断只停止清理并准确返回残留。
        if (published.status != DeletionStatus.REMOVED_RESIDUAL) return@checked published
        var bindingCleanup = VaultCleanupStatus(false, emptyList())
        try {
            guard()
            bindingCleanup = finishRemoval(root, receipt, guard)
            if (Files.exists(removed.toPath(), java.nio.file.LinkOption.NOFOLLOW_LINKS)) {
                DeletionOutcome(DeletionStatus.REMOVED_RESIDUAL, removed, bindingCleanup)
            } else {
                syncDirectory(root)
                if (!matchesRoot(root, preview) || Files.exists(source.toPath(), java.nio.file.LinkOption.NOFOLLOW_LINKS)) {
                    DeletionOutcome(DeletionStatus.UNCERTAIN)
                } else DeletionOutcome(DeletionStatus.REMOVED, bindingCleanup = bindingCleanup)
            }
        } catch (_: Exception) {
            if (runCatching { matchesRoot(root, preview) && !Files.exists(source.toPath(), java.nio.file.LinkOption.NOFOLLOW_LINKS) &&
                    matchesDirectory(removed, preview) }.getOrDefault(false)) DeletionOutcome(DeletionStatus.REMOVED_RESIDUAL, removed)
            else DeletionOutcome(DeletionStatus.UNCERTAIN)
        }.let { if (it.bindingCleanup.complete && !bindingCleanup.complete) it.copy(bindingCleanup = bindingCleanup) else it }
    }

    private fun removeBindings(id: String, bindings: VaultBindingClaims, guard: () -> Unit): VaultCleanupStatus {
        val remaining = mutableListOf<String>()
        val categories = mutableSetOf<VaultCleanupCategory>()
        if (!bindings.complete) categories += VaultCleanupCategory.UNVERIFIED
        for (alias in bindings.aliases) {
            try { guard(); VaultBiometric.remove(id, alias) }
            catch (_: Exception) { remaining += "keystore:$alias"; categories += VaultCleanupCategory.DEVICE_BINDING }
        }
        return VaultCleanupStatus(categories.isEmpty(), remaining, categories)
    }

    private fun publicationState(root: File, source: File, removed: File, preview: DeletionPreview): DeletionOutcome = try {
        if (!matchesRoot(root, preview)) DeletionOutcome(DeletionStatus.UNCERTAIN)
        else if (matchesDirectory(source, preview) && !Files.exists(removed.toPath(), java.nio.file.LinkOption.NOFOLLOW_LINKS)) {
            DeletionOutcome(DeletionStatus.NOT_REMOVED)
        } else if (!Files.exists(source.toPath(), java.nio.file.LinkOption.NOFOLLOW_LINKS) && matchesDirectory(removed, preview)) {
            syncDirectory(root)
            if (!matchesRoot(root, preview) || Files.exists(source.toPath(), java.nio.file.LinkOption.NOFOLLOW_LINKS) ||
                !matchesDirectory(removed, preview)) DeletionOutcome(DeletionStatus.UNCERTAIN)
            else DeletionOutcome(DeletionStatus.REMOVED_RESIDUAL, removed)
        } else DeletionOutcome(DeletionStatus.UNCERTAIN)
    } catch (_: Exception) { DeletionOutcome(DeletionStatus.UNCERTAIN) }

    /** 名称只用于找到责任文件；认证、精确身份和完整剩余清单才允许续清。 */
    fun recover(root: File, guard: () -> Unit = {}): Boolean {
        if (!Files.exists(root.toPath(), java.nio.file.LinkOption.NOFOLLOW_LINKS)) return false
        return try {
            directoryStat(root)
            val candidates = root.listFiles() ?: unavailable()
            val names = candidates.filter { it.name.startsWith(".deletion_") }
                .map { it.name.removeSuffix(".bak").removeSuffix(".new") }.distinct()
            for (name in names) {
                guard()
                try {
                    val receipt = VaultDeletionReceipts.read(root, File(root, name))
                    checkReceiptRoot(root, receipt)
                    val source = File(root, receipt.id)
                    val removed = File(root, receipt.removedName)
                    if (exists(source)) {
                        val stamp = directoryStat(source)
                        if (!exists(removed) && stamp.st_dev == receipt.directoryDevice && stamp.st_ino == receipt.directoryInode)
                            VaultDeletionReceipts.remove(root, receipt)
                    } else finishRemoval(root, receipt, guard)
                } catch (failure: CancellationException) { throw failure }
                catch (_: Exception) { /* 无法认证的责任保留，不阻断其他库。 */ }
            }
            root.listFiles()?.any { it.name.startsWith(".removed_") || it.name.startsWith(".deletion_") } ?: true
        } catch (failure: CancellationException) { throw failure }
        catch (_: Exception) { true }
    }

    private fun finishRemoval(root: File, expected: DeletionReceipt, guard: () -> Unit): VaultCleanupStatus {
        val receipt = VaultDeletionReceipts.read(root, File(root, expected.receiptName))
        if (receipt != expected) unavailable()
        val removed = File(root, receipt.removedName)
        fun stillOwned() {
            guard(); checkReceiptRoot(root, receipt)
            if (exists(File(root, receipt.id))) unavailable()
            if (exists(removed)) directoryStat(removed).let {
                if (it.st_dev != receipt.directoryDevice || it.st_ino != receipt.directoryInode) unavailable()
            }
        }
        stillOwned()
        if (exists(removed)) {
            val remaining = mutableListOf<DeletionAsset>()
            fingerprint(removed, guard, remaining)
            val approved = receipt.assets.associateBy { it.path }
            if (remaining.any { approved[it.path] != it }) unavailable()
        }
        // 重启可能发生在rename之后、父目录同步之前；续清前先确认移除事实持久化。
        syncDirectory(root)
        stillOwned()
        val bindingCleanup = removeBindings(receipt.id, receipt.bindings, guard)
        // 每个文件仍须匹配；只接受已认证清单的已删子集，目录最后删除。
        val ordered = receipt.assets.filter { it.size >= 0 } +
            receipt.assets.filter { it.size == -1L }.sortedByDescending { it.path.count { c -> c == '/' } * 2 + if (it.path.isEmpty()) 0 else 1 }
        for (entry in ordered) {
            stillOwned()
            val file = if (entry.path.isEmpty()) removed else File(removed, entry.path)
            checkedPath(file, removed)
            if (!exists(file)) { syncExistingParent(root, file); continue }
            if (entry.size == -1L) {
                val stamp = directoryStat(file)
                if (stamp.st_dev != entry.device || stamp.st_ino != entry.inode || file.listFiles()?.isEmpty() != true) unavailable()
            } else {
                val actual = mutableListOf<DeletionAsset>()
                fingerprint(file, guard, actual)
                if (actual.singleOrNull()?.copy(path = entry.path) != entry) unavailable()
            }
            stillOwned()
            Os.remove(file.absolutePath); syncDirectory(file.parentFile!!)
        }
        stillOwned()
        if (exists(removed)) unavailable()
        syncDirectory(root)
        if (bindingCleanup.complete) VaultDeletionReceipts.remove(root, receipt)
        return bindingCleanup
    }

    private fun checkReceiptRoot(root: File, receipt: DeletionReceipt) {
        directoryStat(root).let { if (it.st_dev != receipt.rootDevice || it.st_ino != receipt.rootInode) unavailable() }
    }

    private fun syncExistingParent(root: File, file: File) {
        var parent = file.parentFile ?: unavailable()
        while (!exists(parent)) {
            if (parent == root || !parent.toPath().startsWith(root.toPath())) unavailable()
            parent = parent.parentFile ?: unavailable()
        }
        directoryStat(parent); syncDirectory(parent)
    }

    private fun exists(file: File) = Files.exists(file.toPath(), java.nio.file.LinkOption.NOFOLLOW_LINKS)

    private fun fingerprint(directory: File, guard: () -> Unit, assets: MutableList<DeletionAsset>? = null): String {
        val digest = MessageDigest.getInstance("SHA-256")
        val output = DataOutputStream(DigestOutputStream(object : OutputStream() { override fun write(value: Int) { } }, digest))
        fun visit(file: File) {
            guard()
            checkedPath(file, directory)
            val before = Os.lstat(file.absolutePath)
            val relative = directory.toPath().relativize(file.toPath()).toString().replace(File.separatorChar, '/')
            if (OsConstants.S_ISDIR(before.st_mode)) {
                assets?.add(DeletionAsset(relative, before.st_dev, before.st_ino, -1, ""))
                // 整目录重命名只改变父目录位置，快照不把自身目录时间当内容。
                output.writeByte(0)
                output.writeUTF(directory.toPath().relativize(file.toPath()).toString())
                output.writeLong(before.st_dev)
                output.writeLong(before.st_ino)
                val children = file.listFiles()?.sortedBy { it.name } ?: unavailable()
                children.forEach(::visit)
                guard()
                val after = Os.lstat(file.absolutePath)
                if (!sameStamp(before, after) || file.listFiles()?.map { it.name }?.sorted() != children.map { it.name }) unavailable()
            } else {
                if (!OsConstants.S_ISREG(before.st_mode)) unavailable()
                output.writeByte(1)
                output.writeUTF(directory.toPath().relativize(file.toPath()).toString())
                output.writeLong(before.st_dev)
                output.writeLong(before.st_ino)
                output.writeLong(before.st_size)
                output.writeLong(before.st_mtim.tv_sec)
                output.writeLong(before.st_mtim.tv_nsec)
                output.writeLong(before.st_ctim.tv_sec)
                output.writeLong(before.st_ctim.tv_nsec)
                val descriptor = Os.open(file.absolutePath, OsConstants.O_RDONLY or OsConstants.O_NOFOLLOW or OsConstants.O_CLOEXEC, 0)
                val buffer = ByteArray(65536)
                val fileDigest = if (assets != null) MessageDigest.getInstance("SHA-256") else null
                try {
                    if (!sameStamp(before, Os.fstat(descriptor))) unavailable()
                    var size = 0L
                    while (true) {
                        guard()
                        val count = Os.read(descriptor, buffer, 0, buffer.size)
                        if (count == 0) break
                        digest.update(buffer, 0, count)
                        fileDigest?.update(buffer, 0, count)
                        size = Math.addExact(size, count.toLong())
                    }
                    if (size != before.st_size || !sameStamp(before, Os.fstat(descriptor))) unavailable()
                } finally {
                    buffer.fill(0)
                    Os.close(descriptor)
                }
                guard()
                if (!sameStamp(before, Os.lstat(file.absolutePath))) unavailable()
                assets?.add(DeletionAsset(relative, before.st_dev, before.st_ino, before.st_size,
                    fileDigest!!.digest().joinToString("") { "%02x".format(it) }))
            }
        }
        visit(directory)
        output.close()
        guard()
        return digest.digest().joinToString("") { (it.toInt() and 255).toString(16).padStart(2, '0') }
    }

    private fun checkedPath(file: File, directory: File) {
        if (file.canonicalFile != file.absoluteFile || Files.isSymbolicLink(file.toPath()) ||
            !file.toPath().startsWith(directory.toPath())) unavailable()
    }

    private fun directoryStat(directory: File): StructStat {
        if (directory.canonicalFile != directory.absoluteFile || Files.isSymbolicLink(directory.toPath())) unavailable()
        val stat = Os.lstat(directory.absolutePath)
        if (!OsConstants.S_ISDIR(stat.st_mode) || stat.st_ino <= 0) unavailable()
        return stat
    }

    private fun matchesRoot(root: File, preview: DeletionPreview): Boolean = directoryStat(root).let {
        it.st_dev == preview.rootDevice && it.st_ino == preview.rootInode
    }

    private fun matchesDirectory(directory: File, preview: DeletionPreview): Boolean = try {
        directoryStat(directory).let { it.st_dev == preview.directoryDevice && it.st_ino == preview.directoryInode }
    } catch (failure: ErrnoException) {
        if (failure.errno == OsConstants.ENOENT) false else throw failure
    }

    private fun sameIdentity(first: StructStat, second: StructStat) = first.st_dev == second.st_dev && first.st_ino == second.st_ino
    private fun sameStamp(first: StructStat, second: StructStat) = sameIdentity(first, second) && first.st_mode == second.st_mode &&
        first.st_size == second.st_size && first.st_mtim.tv_sec == second.st_mtim.tv_sec && first.st_mtim.tv_nsec == second.st_mtim.tv_nsec &&
        first.st_ctim.tv_sec == second.st_ctim.tv_sec && first.st_ctim.tv_nsec == second.st_ctim.tv_nsec

    private inline fun <T> checked(action: () -> T): T = try { action() }
    catch (failure: CancellationException) { throw failure }
    catch (failure: VaultException) { throw failure }
    catch (_: Exception) { throw VaultException(VaultError.STORAGE_FAILED) }

    private fun unavailable(): Nothing = throw VaultException(VaultError.DATA_UNAVAILABLE)
}
