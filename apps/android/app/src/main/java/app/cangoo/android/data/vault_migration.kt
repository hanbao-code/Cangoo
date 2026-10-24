package app.cangoo.android.data

import android.database.sqlite.SQLiteDatabaseLockedException
import android.database.sqlite.SQLiteException
import android.database.sqlite.SQLiteReadOnlyDatabaseException
import android.system.ErrnoException
import android.system.Os
import android.system.OsConstants
import android.system.StructStat
import kotlinx.coroutines.CancellationException
import net.zetetic.database.DatabaseErrorHandler
import net.zetetic.database.sqlcipher.SQLiteDatabase
import net.zetetic.database.sqlcipher.SQLiteConnection
import net.zetetic.database.sqlcipher.SQLiteDatabaseHook
import java.io.File
import java.io.FileInputStream
import java.io.FileOutputStream
import java.nio.file.Files
import java.security.MessageDigest

/** 本库原生回滚恢复及旧结构升级保护；调用方必须持有唯一存储互斥并已关闭数据库。 */
internal object VaultMigration {
    const val RECOVERY_DIRECTORY = "recovery_before_v3"
    private const val PENDING_DIRECTORY = ".pending_recovery_before_v3"
    const val RECOVERY_V4_DIRECTORY = "recovery_before_v4"
    private const val PENDING_V4_DIRECTORY = ".pending_recovery_before_v4"
    val recoveryNames = setOf(RECOVERY_DIRECTORY, PENDING_DIRECTORY, RECOVERY_V4_DIRECTORY, PENDING_V4_DIRECTORY)
    // 保留损坏文件，由打开失败向上拒绝；不使用默认删除处理。
    private val preserveCorruptFile = DatabaseErrorHandler { _, _ -> }
    internal class RecoverySnapshot(val directory: File, val directoryStat: StructStat, val databaseStat: StructStat,
                                   val manifestStat: StructStat, val databaseHash: ByteArray, val manifestHash: ByteArray)

    fun prepare(directory: File, id: String, master: String?, key: ByteArray, guard: () -> Unit): Boolean =
        prepare(VaultLayout.resolve(directory, id), id, master, key, guard)

    fun prepare(files: VaultResolvedFiles, id: String, master: String?, key: ByteArray, guard: () -> Unit): Boolean {
        guard()
        val directory = files.database.parentFile!!
        val database = checkedFile(directory, files.database.name)
        val manifest = checkedFile(files.manifest.parentFile!!, files.manifest.name)
        authenticateDescriptor(Metadata.read(manifest, id), master, key, files.selection, guard)
        val version = sourceVersion(database, key, guard)
        if (version == 4) return false
        if (version !in 1..3) throw VaultException(VaultError.DATA_UNAVAILABLE)
        var createdPending = false
        var verifiedPending = false
        val pending = checkedDirectory(directory, if (version == 3) PENDING_V4_DIRECTORY else PENDING_DIRECTORY)
        try {
            checkLogs(database)
            val databaseHash = hash(database, guard)
            val manifestHash = hash(manifest, guard)
            val recovery = checkedDirectory(directory, if (version == 3) RECOVERY_V4_DIRECTORY else RECOVERY_DIRECTORY)
            if (recovery.exists()) {
                verify(recovery, id, master, key, files.selection, version, databaseHash, manifestHash, guard)
                checkLogs(database)
                if (!databaseHash.contentEquals(hash(database, guard)) || !manifestHash.contentEquals(hash(manifest, guard))) {
                    throw VaultException(VaultError.MIGRATION_PROTECTION_FAILED)
                }
                syncDirectory(directory)
                guard()
                return true
            }
            if (!pending.exists()) {
                if (!pending.mkdir()) throw VaultException(VaultError.MIGRATION_PROTECTION_FAILED)
                createdPending = true
                copy(database, File(pending, VaultStore.DATABASE_FILE), guard)
                copy(manifest, File(pending, VaultStore.MANIFEST_FILE), guard)
            }
            verify(pending, id, master, key, files.selection, version, databaseHash, manifestHash, guard)
            verifiedPending = true
            checkLogs(database)
            if (!databaseHash.contentEquals(hash(database, guard)) || !manifestHash.contentEquals(hash(manifest, guard))) {
                throw VaultException(VaultError.MIGRATION_PROTECTION_FAILED)
            }
            guard()
            if (recovery.exists() || !pending.renameTo(recovery)) throw VaultException(VaultError.MIGRATION_PROTECTION_FAILED)
            syncDirectory(directory)
            guard()
            return true
        } catch (failure: CancellationException) {
            throw failure
        } catch (failure: VaultException) {
            if (failure.code == VaultError.SESSION_CLOSED) throw failure
            throw VaultException(VaultError.MIGRATION_PROTECTION_FAILED)
        } catch (_: Exception) {
            throw VaultException(VaultError.MIGRATION_PROTECTION_FAILED)
        } finally {
            // 只清理由本次创建且尚未核实完整的临时副本；已核实资产始终保留。
            if (createdPending && !verifiedPending) removeIncomplete(pending, directory)
        }
    }

    /** 只证明原配套；当前库资格、回执签证和删除由调用方控制。 */
    internal fun proveRecovery(files: VaultResolvedFiles, id: String, master: String?, key: ByteArray,
                               guard: () -> Unit): List<RecoverySnapshot> {
        guard()
        if (key.size != VaultCrypto.KEY_BYTES) throw VaultException(VaultError.MIGRATION_PROTECTION_FAILED)
        val parent = files.database.parentFile!!
        val directories = recoveryDirectories(parent)
        val snapshots = directories.map { directory ->
            guard()
            val database = checkedFile(directory, VaultStore.DATABASE_FILE)
            val manifest = checkedFile(directory, VaultStore.MANIFEST_FILE)
            val directoryStat = Os.lstat(directory.absolutePath)
            val databaseStat = Os.lstat(database.absolutePath)
            val manifestStat = Os.lstat(manifest.absolutePath)
            if (!OsConstants.S_ISDIR(directoryStat.st_mode) || !OsConstants.S_ISREG(databaseStat.st_mode) ||
                !OsConstants.S_ISREG(manifestStat.st_mode) ||
                directory.listFiles()?.map { it.name }?.toSet() != setOf(VaultStore.DATABASE_FILE, VaultStore.MANIFEST_FILE)) {
                throw VaultException(VaultError.MIGRATION_PROTECTION_FAILED)
            }
            val databaseHash = hash(database, guard)
            val manifestHash = hash(manifest, guard)
            val metadata = Metadata.read(manifest, id)
            authenticateDescriptor(metadata, master, key, files.selection, guard)
            checkLogs(database)
            if (readVersion(database, key, verifyContent = true) !in recoveryVersions(directory.name)) {
                throw VaultException(VaultError.MIGRATION_PROTECTION_FAILED)
            }
            RecoverySnapshot(directory, directoryStat, databaseStat, manifestStat, databaseHash, manifestHash)
        }
        snapshots.forEach { verifySnapshot(it, guard) }
        if (recoveryDirectories(parent) != directories) throw VaultException(VaultError.MIGRATION_PROTECTION_FAILED)
        guard()
        return snapshots
    }

    internal fun recoveryVersions(name: String): IntRange = when (name) {
        RECOVERY_DIRECTORY, PENDING_DIRECTORY -> 1..2
        RECOVERY_V4_DIRECTORY, PENDING_V4_DIRECTORY -> 3..3
        else -> throw VaultException(VaultError.MIGRATION_PROTECTION_FAILED)
    }

    internal fun authenticateDescriptor(metadata: Metadata, master: String?, key: ByteArray,
                                        expected: VaultLayoutSelection, guard: () -> Unit) {
        guard()
        if (key.size != VaultCrypto.KEY_BYTES) throw VaultException(VaultError.DATA_UNAVAILABLE)
        if (metadata.version == 2) VaultDescriptorAuth.verify(key, metadata, expected)
        else if (master == null) throw VaultException(VaultError.MIGRATION_PROTECTION_FAILED)
        // 旧描述没有认证码；现代描述在有主密码时仍同时证明其封装。
        if (master != null) {
            val authenticated = metadata.unlock(master, if (metadata.version == 2) expected else null)
            try {
                if (!MessageDigest.isEqual(authenticated, key)) throw VaultException(VaultError.DATA_UNAVAILABLE)
            } finally { authenticated.fill(0) }
        }
        guard()
    }

    private fun recoveryDirectories(parent: File): List<File> = recoveryNames
        .map { checkedDirectory(parent, it) }.filter { directory ->
            try { Os.lstat(directory.absolutePath); true }
            catch (failure: ErrnoException) { if (failure.errno == OsConstants.ENOENT) false else throw failure }
        }

    private fun verifySnapshot(snapshot: RecoverySnapshot, guard: () -> Unit) {
        guard()
        val directory = checkedDirectory(snapshot.directory.parentFile!!, snapshot.directory.name)
        val database = checkedFile(directory, VaultStore.DATABASE_FILE)
        val manifest = checkedFile(directory, VaultStore.MANIFEST_FILE)
        if (directory.listFiles()?.map { it.name }?.toSet() != setOf(VaultStore.DATABASE_FILE, VaultStore.MANIFEST_FILE) ||
            !snapshot.databaseHash.contentEquals(hash(database, guard)) || !snapshot.manifestHash.contentEquals(hash(manifest, guard)) ||
            !sameStamp(snapshot.directoryStat, Os.lstat(directory.absolutePath)) ||
            !sameStamp(snapshot.databaseStat, Os.lstat(database.absolutePath)) || !sameStamp(snapshot.manifestStat, Os.lstat(manifest.absolutePath))) {
            throw VaultException(VaultError.MIGRATION_PROTECTION_FAILED)
        }
        guard()
    }

    internal fun sourceVersion(file: File, key: ByteArray, guard: () -> Unit): Int {
        checkLogs(file, allowRollback = true, reason = VaultError.RECOVERY_FAILED)
        guard()
        val version = try {
            // 普通新版只识别结构；恢复后与升级副本仍执行完整一致性核验。
            try { readVersion(file, key) }
            catch (failure: SQLiteReadOnlyDatabaseException) {
                // 固定SQLCipher的JNI保留扩展码；776只表示热回滚日志不能在只读连接恢复。
                if (failure.message?.contains("(code 776)") != true || checkedFile(file.parentFile!!, file.name + "-journal").length() == 0L) {
                    throw VaultException(VaultError.RECOVERY_FAILED)
                }
                recoverRollback(file, key, guard)
                guard()
                readVersion(file, key, verifyContent = true)
            }
        } catch (failure: CancellationException) { throw failure }
        catch (failure: VaultException) { throw failure }
        catch (_: SQLiteDatabaseLockedException) { throw VaultException(VaultError.RECOVERY_FAILED) }
        catch (_: Exception) { throw VaultException(VaultError.DATA_UNAVAILABLE) }
        checkLogs(file, reason = VaultError.RECOVERY_FAILED)
        if (version !in 1..4) throw VaultException(VaultError.DATA_UNAVAILABLE)
        guard()
        return version
    }

    private fun recoverRollback(file: File, key: ByteArray, guard: () -> Unit) {
        checkedFile(file.parentFile!!, file.name)
        checkLogs(file, allowRollback = true, reason = VaultError.RECOVERY_FAILED)
        guard()
        var aborted: VaultError? = null
        val hook = object : SQLiteDatabaseHook {
            override fun preKey(connection: SQLiteConnection) { }
            override fun postKey(connection: SQLiteConnection) {
                try {
                    guard()
                    // 4.19.1随后会配置默认delete；必须在此确认原模式相同，避免实际切换或WAL合并。
                    if (!connection.executeForString("PRAGMA journal_mode", null, null).equals("delete", ignoreCase = true) ||
                        connection.executeForLong("PRAGMA user_version", null, null) !in 1L..4L) throw VaultException(VaultError.RECOVERY_FAILED)
                    guard()
                } catch (failure: VaultException) {
                    // Java打开路径仅捕获运行时异常；转换业务异常，确保未完成连接被释放。
                    aborted = failure.code
                    throw SQLiteException(failure.code.text)
                }
            }
        }
        try {
            val database = SQLiteDatabase.openDatabase(file.absolutePath, key, null,
                SQLiteDatabase.OPEN_READWRITE or SQLiteDatabase.NO_LOCALIZED_COLLATORS, preserveCorruptFile, hook)
            try {
                if (database.isReadOnly) throw VaultException(VaultError.RECOVERY_FAILED)
                guard()
                // 原生打开也核对sqlite3_db_readonly；空事务进一步确认实际写锁，不修改任何业务值。
                database.beginTransaction()
                try { guard() } finally { database.endTransaction() }
                guard()
            } finally { database.close() }
        } catch (failure: CancellationException) { throw failure }
        catch (failure: VaultException) { throw failure }
        catch (_: Exception) { throw VaultException(aborted ?: VaultError.RECOVERY_FAILED) }
    }

    fun readVersion(file: File, key: ByteArray, verifyContent: Boolean = false): Int {
        checkedFile(file.parentFile!!, file.name)
        VaultDatabase.initializeNative()
        val database = SQLiteDatabase.openDatabase(file.absolutePath, key, null,
            SQLiteDatabase.OPEN_READONLY or SQLiteDatabase.NO_LOCALIZED_COLLATORS, preserveCorruptFile, null)
        try {
            if (!database.isReadOnly) throw VaultException(VaultError.DATA_UNAVAILABLE)
            database.query("SELECT count(*) FROM sqlite_master").use { if (!it.moveToFirst()) throw VaultException(VaultError.DATA_UNAVAILABLE) }
            val version = database.version
            database.query("PRAGMA journal_mode").use {
                if (!it.moveToFirst() || !it.getString(0).equals("delete", ignoreCase = true)) throw VaultException(VaultError.RECOVERY_FAILED)
            }
            if (verifyContent) {
                database.query("PRAGMA cipher_status").use {
                    if (!it.moveToFirst() || it.getInt(0) != 1) throw VaultException(VaultError.DATA_UNAVAILABLE)
                }
                database.query("PRAGMA cipher_integrity_check").use {
                    if (it.moveToFirst()) throw VaultException(VaultError.DATA_UNAVAILABLE)
                }
                database.query("PRAGMA integrity_check").use {
                    if (!it.moveToFirst() || it.getString(0) != "ok" || it.moveToNext()) throw VaultException(VaultError.DATA_UNAVAILABLE)
                }
                database.query("PRAGMA foreign_key_check").use {
                    if (it.moveToFirst()) throw VaultException(VaultError.DATA_UNAVAILABLE)
                }
                database.query("SELECT count(*) FROM passwords").use { if (!it.moveToFirst()) throw VaultException(VaultError.DATA_UNAVAILABLE) }
                if (version in 2..4) database.query("SELECT count(*) FROM notes").use { if (!it.moveToFirst()) throw VaultException(VaultError.DATA_UNAVAILABLE) }
            }
            return version
        } finally { database.close() }
    }

    private fun verify(directory: File, id: String, master: String?, key: ByteArray, selection: VaultLayoutSelection, version: Int,
                       databaseHash: ByteArray, manifestHash: ByteArray, guard: () -> Unit) {
        val database = checkedFile(directory, VaultStore.DATABASE_FILE)
        val manifest = checkedFile(directory, VaultStore.MANIFEST_FILE)
        if (directory.listFiles()?.map { it.name }?.toSet() != setOf(VaultStore.DATABASE_FILE, VaultStore.MANIFEST_FILE)) {
            throw VaultException(VaultError.MIGRATION_PROTECTION_FAILED)
        }
        if (manifest.length() !in 1L..16384L || !databaseHash.contentEquals(hash(database, guard)) || !manifestHash.contentEquals(hash(manifest, guard))) {
            throw VaultException(VaultError.MIGRATION_PROTECTION_FAILED)
        }
        FileInputStream(database).use { it.fd.sync() }
        FileInputStream(manifest).use { it.fd.sync() }
        syncDirectory(directory)
        authenticateDescriptor(Metadata.read(manifest, id), master, key, selection, guard)
        if (readVersion(database, key, verifyContent = true) != version) {
            throw VaultException(VaultError.MIGRATION_PROTECTION_FAILED)
        }
        // 只读验证不能改变旧结构或任何原始字节。
        if (!databaseHash.contentEquals(hash(database, guard)) || !manifestHash.contentEquals(hash(manifest, guard))) throw VaultException(VaultError.MIGRATION_PROTECTION_FAILED)
        guard()
    }

    private fun copy(source: File, destination: File, guard: () -> Unit) {
        if (destination.exists() || Files.isSymbolicLink(destination.toPath()) || !destination.createNewFile()) throw VaultException(VaultError.MIGRATION_PROTECTION_FAILED)
        FileInputStream(source).use { input ->
            FileOutputStream(destination).use { output ->
                val buffer = ByteArray(65536)
                var copied = 0L
                while (true) {
                    guard()
                    val count = input.read(buffer)
                    if (count < 0) break
                    output.write(buffer, 0, count)
                    copied += count
                }
                if (copied != source.length()) throw VaultException(VaultError.MIGRATION_PROTECTION_FAILED)
                output.fd.sync()
            }
        }
    }

    private fun hash(file: File, guard: () -> Unit): ByteArray {
        val before = Os.lstat(checkedFile(file.parentFile!!, file.name).absolutePath)
        val digest = MessageDigest.getInstance("SHA-256")
        val descriptor = Os.open(file.absolutePath, OsConstants.O_RDONLY or OsConstants.O_NOFOLLOW or OsConstants.O_CLOEXEC, 0)
        val buffer = ByteArray(65536)
        try {
            if (!OsConstants.S_ISREG(before.st_mode) || !sameStamp(before, Os.fstat(descriptor))) throw VaultException(VaultError.MIGRATION_PROTECTION_FAILED)
            var size = 0L
            while (true) {
                guard()
                val count = Os.read(descriptor, buffer, 0, buffer.size)
                if (count == 0) break
                digest.update(buffer, 0, count)
                size = Math.addExact(size, count.toLong())
            }
            if (size != before.st_size || !sameStamp(before, Os.fstat(descriptor)) ||
                !sameStamp(before, Os.lstat(checkedFile(file.parentFile!!, file.name).absolutePath))) throw VaultException(VaultError.MIGRATION_PROTECTION_FAILED)
            return digest.digest()
        } finally { buffer.fill(0); Os.close(descriptor) }
    }

    private fun sameStamp(first: StructStat, second: StructStat): Boolean = first.st_dev == second.st_dev && first.st_ino == second.st_ino &&
        first.st_mode == second.st_mode && first.st_size == second.st_size &&
        first.st_mtim.tv_sec == second.st_mtim.tv_sec && first.st_mtim.tv_nsec == second.st_mtim.tv_nsec &&
        first.st_ctim.tv_sec == second.st_ctim.tv_sec && first.st_ctim.tv_nsec == second.st_ctim.tv_nsec

    internal fun checkLogs(database: File, allowRollback: Boolean = false, reason: VaultError = VaultError.MIGRATION_PROTECTION_FAILED) {
        listOf("-journal", "-wal", "-shm").forEach { suffix ->
            val file = File(database.path + suffix)
            if (Files.isSymbolicLink(file.toPath()) || file.canonicalFile != file.absoluteFile ||
                file.exists() && (!file.isFile || (suffix != "-journal" || !allowRollback) && file.length() != 0L)) throw VaultException(reason)
        }
        if (database.parentFile!!.listFiles()?.any { it.name.startsWith(database.name + "-mj") } != false) throw VaultException(reason)
    }

    private fun checkedDirectory(parent: File, name: String): File {
        val file = File(parent, name)
        if (!parent.isDirectory || parent.canonicalFile != parent.absoluteFile || Files.isSymbolicLink(file.toPath()) || file.canonicalFile != file.absoluteFile ||
            file.exists() && !file.isDirectory) throw VaultException(VaultError.MIGRATION_PROTECTION_FAILED)
        return file
    }

    private fun checkedFile(parent: File, name: String): File {
        val file = File(parent, name)
        if (!parent.isDirectory || parent.canonicalFile != parent.absoluteFile || Files.isSymbolicLink(file.toPath()) || file.canonicalFile != file.absoluteFile ||
            !file.isFile || file.length() == 0L) throw VaultException(VaultError.DATA_UNAVAILABLE)
        return file
    }

    private fun removeIncomplete(directory: File, parent: File) {
        if (!directory.exists() || directory.parentFile != parent || directory.canonicalFile != directory.absoluteFile || Files.isSymbolicLink(directory.toPath())) return
        val files = directory.listFiles() ?: return
        if (files.any { it.name !in setOf(VaultStore.DATABASE_FILE, VaultStore.MANIFEST_FILE) || !it.isFile || it.canonicalFile != it.absoluteFile || Files.isSymbolicLink(it.toPath()) }) return
        files.forEach { it.delete() }
        directory.delete()
    }
}
