package app.cangoo.android.data

import android.system.ErrnoException
import android.system.Os
import android.system.OsConstants
import android.system.StructStat
import java.io.DataOutputStream
import java.io.File
import java.io.OutputStream
import java.nio.file.FileVisitResult
import java.nio.file.Files
import java.nio.file.Path
import java.nio.file.SimpleFileVisitor
import java.nio.file.attribute.BasicFileAttributes
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
        val removed = File(root, ".removed_${preview.id}_${UUID.randomUUID()}")
        if (Files.exists(removed.toPath(), java.nio.file.LinkOption.NOFOLLOW_LINKS)) unavailable()
        guard()
        beforePublish()
        guard()
        // 关闭当前目标连接后的最后核对仍属于发布前；此处失败尚未移动库目录。
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
        val bindingCleanup = removeBindings(preview, guard)
        try {
            guard()
            if (fingerprint(removed, guard) != preview.snapshot) return@checked DeletionOutcome(DeletionStatus.REMOVED_RESIDUAL, removed, bindingCleanup)
            removeOwned(root, removed, preview, guard)
            if (Files.exists(removed.toPath(), java.nio.file.LinkOption.NOFOLLOW_LINKS)) {
                DeletionOutcome(DeletionStatus.REMOVED_RESIDUAL, removed)
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

    private fun removeBindings(preview: DeletionPreview, guard: () -> Unit): VaultCleanupStatus {
        val remaining = mutableListOf<String>()
        val categories = mutableSetOf<VaultCleanupCategory>()
        if (!preview.bindings.complete) categories += VaultCleanupCategory.UNVERIFIED
        for (alias in preview.bindings.aliases) {
            try { guard(); VaultBiometric.remove(preview.id, alias) }
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

    private fun removeOwned(root: File, removed: File, preview: DeletionPreview, guard: () -> Unit) {
        fun stillOwned() {
            guard()
            if (!matchesRoot(root, preview) || !matchesDirectory(removed, preview) ||
                Files.exists(File(root, preview.id).toPath(), java.nio.file.LinkOption.NOFOLLOW_LINKS)) unavailable()
        }
        stillOwned()
        Files.walkFileTree(removed.toPath(), object : SimpleFileVisitor<Path>() {
            override fun preVisitDirectory(path: Path, attrs: BasicFileAttributes): FileVisitResult {
                stillOwned()
                checkedPath(path.toFile(), removed)
                if (!attrs.isDirectory || attrs.isSymbolicLink) unavailable()
                return FileVisitResult.CONTINUE
            }
            override fun visitFile(path: Path, attrs: BasicFileAttributes): FileVisitResult {
                stillOwned()
                checkedPath(path.toFile(), removed)
                if (!attrs.isRegularFile || attrs.isSymbolicLink) unavailable()
                Files.delete(path)
                return FileVisitResult.CONTINUE
            }
            override fun postVisitDirectory(path: Path, failure: java.io.IOException?): FileVisitResult {
                if (failure != null) throw failure
                stillOwned()
                checkedPath(path.toFile(), removed)
                Files.delete(path)
                return FileVisitResult.CONTINUE
            }
        })
    }

    private fun fingerprint(directory: File, guard: () -> Unit): String {
        val digest = MessageDigest.getInstance("SHA-256")
        val output = DataOutputStream(DigestOutputStream(object : OutputStream() { override fun write(value: Int) { } }, digest))
        fun visit(file: File) {
            guard()
            checkedPath(file, directory)
            val before = Os.lstat(file.absolutePath)
            if (OsConstants.S_ISDIR(before.st_mode)) {
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
                try {
                    if (!sameStamp(before, Os.fstat(descriptor))) unavailable()
                    var size = 0L
                    while (true) {
                        guard()
                        val count = Os.read(descriptor, buffer, 0, buffer.size)
                        if (count == 0) break
                        digest.update(buffer, 0, count)
                        size = Math.addExact(size, count.toLong())
                    }
                    if (size != before.st_size || !sameStamp(before, Os.fstat(descriptor))) unavailable()
                } finally {
                    buffer.fill(0)
                    Os.close(descriptor)
                }
                guard()
                if (!sameStamp(before, Os.lstat(file.absolutePath))) unavailable()
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
