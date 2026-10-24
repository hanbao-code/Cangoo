package app.cangoo.android.data

import android.system.ErrnoException
import android.system.Os
import android.system.OsConstants
import android.system.StructStat
import com.google.gson.Strictness
import com.google.gson.stream.JsonReader
import com.google.gson.stream.JsonToken
import com.google.gson.stream.JsonWriter
import kotlinx.coroutines.CancellationException
import java.io.File
import java.io.StringReader
import java.io.StringWriter
import java.util.UUID

internal data class VaultLayoutSelection(val dataGroup: String, val descriptorGroup: String)

internal data class VaultResolvedFiles(
    val root: File,
    val database: File,
    val manifest: File,
    val selection: VaultLayoutSelection,
) {
    override fun toString() = "VaultResolvedFiles(路径已隐藏)"
}

// 所有调用由 VaultStore 的唯一互斥串行化；选择只定位资产，不授予认证权限。
internal object VaultLayout {
    private const val ACTIVE = "active.json"
    private const val MARKER = "layout_version.json"
    private const val LEGACY = "legacy"
    private const val MAX_BYTES = 4096
    private val legacySelection = VaultLayoutSelection(LEGACY, LEGACY)
    private val legacyNames = setOf(
        "vault.db", "vault.db-journal", "vault.db-wal", "vault.db-shm",
        "manifest.json", "manifest.json.bak", "manifest.json.new",
        "recovery_before_v3", ".pending_recovery_before_v3",
        "recovery_before_v4", ".pending_recovery_before_v4",
        "last_backup.json", "last_backup.json.bak", "last_backup.json.new",
    )

    fun resolve(root: File, id: String): VaultResolvedFiles = checked {
        checkRoot(root, id)
        val marker = File(root, MARKER)
        val markerPresent = statOrMissing(marker) != null
        if (markerPresent) decode(readBytes(marker), id, selection = false)
        val active = File(root, ACTIVE)
        val selected = if (statOrMissing(active) != null) {
            requireNotNull(decode(readBytes(active), id, selection = true))
        } else {
            if (markerPresent || hasLayoutEvidence(root)) unavailable()
            legacySelection
        }
        resolved(root, selected)
    }

    // 调用方已认证旧布局；缺标记的有效选择只补标记，不能再次选择旧根。
    fun bootstrap(root: File, id: String, guard: () -> Unit) = checked {
        guard()
        val current = resolve(root, id)
        val active = File(root, ACTIVE)
        if (statOrMissing(active) == null) {
            check(current.selection == legacySelection)
            atomicWrite(root, active, encode(id, legacySelection), guard) { temporary ->
                if (statOrMissing(active) != null || statOrMissing(File(root, MARKER)) != null ||
                    hasLayoutEvidence(root, temporary.name)) unavailable()
                resolved(root, legacySelection)
            }
        } else {
            // 有效选择可能来自上次未完成同步；确认持久化后才补稳定标记。
            syncFile(active)
            syncDirectory(root)
            if (resolve(root, id).selection != current.selection) unavailable()
        }
        guard()
        val marker = File(root, MARKER)
        if (statOrMissing(marker) == null) {
            atomicWrite(root, marker, encode(id, null), guard) {
                if (resolve(root, id).selection != current.selection || statOrMissing(marker) != null) unavailable()
            }
        } else {
            decode(readBytes(marker), id, selection = false)
            syncFile(marker)
            syncDirectory(root)
        }
    }

    fun publish(
        root: File,
        id: String,
        expected: VaultLayoutSelection,
        next: VaultLayoutSelection,
        guard: () -> Unit,
    ) = checked {
        guard()
        if (resolve(root, id).selection != expected) unavailable()
        // 候选创建之前必须已完成 bootstrap；这里不能临时补标记掩盖错误顺序。
        decode(readBytes(File(root, MARKER)), id, selection = false)
        resolved(root, next)
        atomicWrite(root, File(root, ACTIVE), encode(id, next), guard) {
            if (resolve(root, id).selection != expected) unavailable()
            decode(readBytes(File(root, MARKER)), id, selection = false)
            resolved(root, next)
        }
        try {
            if (resolve(root, id).selection != next) unavailable()
        } catch (_: Exception) { throw VaultException(VaultError.COMMIT_UNCERTAIN) }
    }

    private fun resolved(root: File, selection: VaultLayoutSelection): VaultResolvedFiles {
        if (!validGroup(selection.dataGroup) || !validGroup(selection.descriptorGroup)) unavailable()
        val data = if (selection.dataGroup == LEGACY) root else checkedDirectory(File(root, "data_${selection.dataGroup}"))
        val descriptor = if (selection.descriptorGroup == LEGACY) root else {
            checkedDirectory(File(checkedDirectory(File(root, "descriptors")), selection.descriptorGroup))
        }
        val database = File(data, "vault.db")
        val manifest = File(descriptor, "manifest.json")
        checkedRegular(database)
        checkedManifest(manifest)
        return VaultResolvedFiles(root, database, manifest, selection)
    }

    private fun hasLayoutEvidence(root: File, ownedTemporary: String? = null): Boolean {
        val children = root.listFiles() ?: unavailable()
        return children.any { it.name != ownedTemporary && it.name !in legacyNames && !it.name.startsWith("vault.db-mj") }
    }

    private fun encode(id: String, selection: VaultLayoutSelection?): ByteArray {
        if (!validUuid(id)) unavailable()
        if (selection != null && (!validGroup(selection.dataGroup) || !validGroup(selection.descriptorGroup))) unavailable()
        val text = StringWriter()
        JsonWriter(text).use { writer ->
            writer.setStrictness(Strictness.STRICT)
            writer.beginObject().name("version").value(1L).name("vault_id").value(id)
            if (selection != null) {
                writer.name("data_group").value(selection.dataGroup)
                writer.name("descriptor_group").value(selection.descriptorGroup)
            }
            writer.endObject()
        }
        return text.toString().encodeToByteArray(throwOnInvalidSequence = true)
    }

    private fun decode(bytes: ByteArray, id: String, selection: Boolean): VaultLayoutSelection? = try {
        val text = bytes.decodeToString(throwOnInvalidSequence = true)
        require(!text.startsWith('\uFEFF'))
        JsonReader(StringReader(text)).use { reader ->
            reader.setStrictness(Strictness.STRICT)
            reader.setNestingLimit(2)
            val seen = mutableSetOf<String>()
            var vaultId: String? = null
            var data: String? = null
            var descriptor: String? = null
            require(reader.peek() == JsonToken.BEGIN_OBJECT)
            reader.beginObject()
            while (reader.hasNext()) {
                val name = reader.nextName()
                require(seen.add(name))
                when (name) {
                    "version" -> { require(reader.peek() == JsonToken.NUMBER); require(reader.nextString() == "1") }
                    "vault_id" -> vaultId = reader.strictString()
                    "data_group" -> { require(selection); data = reader.strictString() }
                    "descriptor_group" -> { require(selection); descriptor = reader.strictString() }
                    else -> throw IllegalArgumentException()
                }
            }
            reader.endObject()
            val fields = if (selection) setOf("version", "vault_id", "data_group", "descriptor_group") else setOf("version", "vault_id")
            require(seen == fields && reader.peek() == JsonToken.END_DOCUMENT)
            require(vaultId == id && validUuid(requireNotNull(vaultId)))
            if (selection) VaultLayoutSelection(requireNotNull(data), requireNotNull(descriptor)).also {
                require(validGroup(it.dataGroup) && validGroup(it.descriptorGroup))
            } else null
        }
    } catch (failure: VaultException) { throw failure }
    catch (_: Exception) { unavailable() }

    private fun JsonReader.strictString(): String {
        require(peek() == JsonToken.STRING)
        return nextString()
    }

    private fun readBytes(file: File): ByteArray {
        val before = checkedRegular(file)
        if (before.st_size !in 1L..MAX_BYTES.toLong()) unavailable()
        val descriptor = Os.open(file.absolutePath, OsConstants.O_RDONLY or OsConstants.O_NOFOLLOW or OsConstants.O_CLOEXEC, 0)
        try {
            if (!sameStamp(before, Os.fstat(descriptor))) unavailable()
            val bytes = ByteArray(MAX_BYTES + 1)
            var size = 0
            while (size < bytes.size) {
                val count = Os.read(descriptor, bytes, size, bytes.size - size)
                if (count == 0) break
                size += count
            }
            if (size.toLong() != before.st_size || !sameStamp(before, Os.fstat(descriptor)) ||
                !sameStamp(before, checkedRegular(file))) unavailable()
            return bytes.copyOf(size)
        } finally { Os.close(descriptor) }
    }

    private fun atomicWrite(root: File, base: File, bytes: ByteArray, guard: () -> Unit, beforeCommit: (File) -> Unit) {
        val rootStamp = checkRoot(root, root.name)
        val temporary = File(root, "${base.name.removeSuffix(".json")}_pending_${UUID.randomUUID()}.json")
        var temporaryStamp: StructStat? = null
        var commitStarted = false
        try {
            val descriptor = Os.open(temporary.absolutePath,
                OsConstants.O_WRONLY or OsConstants.O_CREAT or OsConstants.O_EXCL or OsConstants.O_NOFOLLOW or OsConstants.O_CLOEXEC, 0x180)
            try {
                temporaryStamp = Os.fstat(descriptor)
                var written = 0
                while (written < bytes.size) {
                    guard()
                    val count = Os.write(descriptor, bytes, written, bytes.size - written)
                    check(count > 0)
                    written += count
                }
                Os.fsync(descriptor)
            } finally { Os.close(descriptor) }
            if (!bytes.contentEquals(readBytes(temporary))) unavailable()
            decode(readBytes(temporary), root.name, selection = base.name == ACTIVE)
            beforeCommit(temporary)
            if (!sameIdentity(rootStamp, checkRoot(root, root.name))) unavailable()
            guard()
            // 从替换开始不再传播普通取消或反向回滚；失败只能据持久事实恢复。
            commitStarted = true
            Os.rename(temporary.absolutePath, base.absolutePath)
            syncDirectory(root)
            if (!sameIdentity(rootStamp, checkRoot(root, root.name)) || !bytes.contentEquals(readBytes(base))) unavailable()
        } catch (failure: Exception) {
            val reported = if (commitStarted) VaultException(VaultError.COMMIT_UNCERTAIN) else failure
            try {
                val present = statOrMissing(temporary)
                if (present != null && temporaryStamp?.let { sameIdentity(it, present) } == true &&
                    sameIdentity(rootStamp, checkRoot(root, root.name))) Os.remove(temporary.absolutePath)
            } catch (cleanup: Exception) { reported.addSuppressed(cleanup) }
            throw reported
        }
    }

    private fun syncFile(file: File) {
        val before = checkedRegular(file)
        val descriptor = Os.open(file.absolutePath, OsConstants.O_RDONLY or OsConstants.O_NOFOLLOW or OsConstants.O_CLOEXEC, 0)
        try {
            if (!sameStamp(before, Os.fstat(descriptor))) unavailable()
            Os.fsync(descriptor)
            if (!sameStamp(before, checkedRegular(file))) unavailable()
        } finally { Os.close(descriptor) }
    }

    private fun checkRoot(root: File, id: String): StructStat {
        if (!validUuid(id) || root.name != id) unavailable()
        return directoryStat(root)
    }

    private fun checkedDirectory(file: File): File = file.also { directoryStat(it) }

    private fun directoryStat(file: File): StructStat {
        val stat = statOrMissing(file) ?: unavailable()
        if (!OsConstants.S_ISDIR(stat.st_mode)) unavailable()
        return stat
    }

    private fun checkedRegular(file: File): StructStat {
        val stat = statOrMissing(file) ?: unavailable()
        if (!OsConstants.S_ISREG(stat.st_mode) || stat.st_size <= 0) unavailable()
        return stat
    }

    private fun checkedManifest(file: File) {
        val base = statOrMissing(file)
        val backup = statOrMissing(File(file.path + ".bak"))
        val pending = statOrMissing(File(file.path + ".new"))
        if (listOfNotNull(base, backup, pending).any { !OsConstants.S_ISREG(it.st_mode) }) unavailable()
        if (backup != null && backup.st_size <= 0) unavailable()
        if ((base?.st_size ?: 0) <= 0 && backup == null) unavailable()
        // 只允许定位所选组的合法 AtomicFile 恢复来源；恢复及认证仍由 Metadata 完成。
    }

    private fun statOrMissing(file: File): StructStat? {
        if (file.canonicalFile != file.absoluteFile) unavailable()
        return try {
            Os.lstat(file.absolutePath).also { if (OsConstants.S_ISLNK(it.st_mode)) unavailable() }
        } catch (failure: ErrnoException) {
            if (failure.errno == OsConstants.ENOENT) null else throw failure
        }
    }

    private fun validUuid(value: String) = runCatching { UUID.fromString(value).toString() == value }.getOrDefault(false)
    private fun validGroup(value: String) = value == LEGACY || validUuid(value)
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
