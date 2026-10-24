package app.cangoo.android.data

import android.content.Context
import android.content.Intent
import android.content.pm.ApplicationInfo
import android.content.pm.PackageManager
import android.database.Cursor
import android.net.Uri
import android.os.ParcelFileDescriptor
import android.os.Process
import android.provider.DocumentsContract
import android.system.Os
import android.system.OsConstants
import java.io.File
import java.io.FileDescriptor
import java.io.InputStream
import java.nio.file.Files
import java.security.MessageDigest
import kotlinx.coroutines.CancellationException

internal enum class BackupDocumentProblem(val text: String) {
    LOCAL_LOCATION("请选择本机存储或下载目录；所选位置目前无法可靠核验。"),
    ACCESS("文件权限已失效，请重新选择本机文件。"),
    LIMIT("备份文件超过64MiB限制，请选择较小的文件。"),
    SOURCE("备份校验未通过，请重新生成备份。"),
    NAME("所选文件名称无法可靠读取，请重新选择本机文件。"),
    CHANGED("文件已变化或读回不一致，请重新选择位置或重新生成备份。"),
    IO("文件读写未完成，请重试或重新选择位置。"),
    CANCELLED("操作已取消或已无法继续，请重新开始。"),
}

internal enum class BackupChangeCheck(val code: String) {
    CLAIM_EMPTY("B01"), PRIVATE_READ("B02"), BEFORE_WRITE("B03"), COPY_READ("B04"), COPY_PROOF("B05"),
    WRITTEN_IDENTITY("B06"), WRITTEN_SIZE("B07"), READ_STABLE("B08"), REOPEN_STABLE("B09"), FINAL_RECEIPT("B10"),
    REOPEN_READ_STABLE("B11"), REOPEN_PROOF("B12"),
}
internal enum class BackupChangeDifference(val code: String) {
    BYTES("B"), IDENTITY("I"), SIZE("S"), MODIFIED("M"), CHANGED_TIME("C"), DIGEST("H"),
}
internal enum class BackupLocalProvider(val code: String) { DOWNLOADS("D"), STORAGE("L") }
internal data class BackupChangeDiagnostic(val check: BackupChangeCheck, val provider: BackupLocalProvider?,
                                          val differences: Set<BackupChangeDifference>) {
    val code: String get() = listOfNotNull(check.code, provider?.code,
        differences.sortedBy { it.ordinal }.joinToString("") { it.code }).joinToString("-")
}
internal class BackupDocumentException(val problem: BackupDocumentProblem, val diagnostic: BackupChangeDiagnostic? = null) : IllegalStateException(problem.text) {
    fun displayMessage(debug: Boolean): String = problem.text +
        if (debug && problem == BackupDocumentProblem.CHANGED && diagnostic != null) "（检查编号：${diagnostic.code}）" else ""
}

internal data class BackupDocumentInfo(
    val documentId: String,
    val mimeType: String,
    val flags: Int,
    val size: Long?,
    val verifiedSystemProvider: Boolean,
    val grantedModes: Int,
    val displayName: String? = null,
) { override fun toString() = "BackupDocumentInfo(内容已隐藏)" }

internal data class BackupDocumentReceipt(
    val uri: Uri,
    val bytes: Long,
    val sha256: String,
    val device: Long,
    val inode: Long,
) { override fun toString() = "BackupDocumentReceipt(非秘密回执)" }

internal data class BackupDocumentRead<T>(val value: T, val receipt: BackupDocumentReceipt) {
    override fun toString() = "BackupDocumentRead(内容已隐藏)"
}

internal class CreatedBackupDocument internal constructor(
    val uri: Uri,
    val requestId: String,
    val ownershipToken: String,
    internal val emptyStamp: BackupDocuments.Stamp,
    val displayName: String,
) {
    internal val device: Long get() = emptyStamp.device
    internal val inode: Long get() = emptyStamp.inode
    // 已核实私有加密包的预期摘要；只在原空态仍一致、开始本次写入前记录。
    internal var preparedPacket: BackupDocumentReceipt? = null
    @Volatile internal var published: Boolean = false
    override fun toString() = "CreatedBackupDocument(非秘密引用)"
}

internal enum class BackupDocumentCleanup(val text: String) {
    PUBLISHED("已核实完整导出文件，文件已保留，请在所选位置核对。"),
    DELETED("已删除本次未完成文件。"),
    RESIDUAL("未能确认删除本次文件，可能仍有残留，请在本机文件管理器核对。"),
    OWNERSHIP_LOST("无法核实本次文件归属，已停止清理，请在文件管理器核对。"),
}

// 只隔离提供方查询、打开和删除；描述符读写仍使用系统原生能力。
internal interface BackupDocumentTransport {
    fun inspect(uri: Uri, requiredModes: Int, qualified: () -> Boolean): BackupDocumentInfo
    fun open(uri: Uri, mode: String, qualified: () -> Boolean): ParcelFileDescriptor
    fun delete(uri: Uri, qualified: () -> Boolean): Boolean
}

internal class AndroidBackupDocumentTransport(private val context: Context) : BackupDocumentTransport {
    override fun inspect(uri: Uri, requiredModes: Int, qualified: () -> Boolean): BackupDocumentInfo {
        documentGuard(qualified)
        val authority = uri.authority ?: documentFailure(BackupDocumentProblem.LOCAL_LOCATION)
        val expectedPackage = localPackages[authority] ?: documentFailure(BackupDocumentProblem.LOCAL_LOCATION)
        val provider = try { context.packageManager.resolveContentProvider(authority, 0) }
            catch (_: Exception) { documentFailure(BackupDocumentProblem.LOCAL_LOCATION) }
            ?: documentFailure(BackupDocumentProblem.LOCAL_LOCATION)
        val app = provider.applicationInfo
        if (provider.packageName != expectedPackage || !provider.enabled || !app.enabled || !provider.exported ||
            !provider.grantUriPermissions || provider.readPermission != "android.permission.MANAGE_DOCUMENTS" ||
            provider.writePermission != "android.permission.MANAGE_DOCUMENTS" ||
            app.flags and (ApplicationInfo.FLAG_SYSTEM or ApplicationInfo.FLAG_UPDATED_SYSTEM_APP) == 0) {
            documentFailure(BackupDocumentProblem.LOCAL_LOCATION)
        }
        var modes = 0
        listOf(Intent.FLAG_GRANT_READ_URI_PERMISSION, Intent.FLAG_GRANT_WRITE_URI_PERMISSION).forEach { flag ->
            if (requiredModes and flag != 0) {
                documentGuard(qualified)
                if (context.checkUriPermission(uri, Process.myPid(), Process.myUid(), flag) == PackageManager.PERMISSION_GRANTED) modes = modes or flag
            }
        }
        if (modes and requiredModes != requiredModes) documentFailure(BackupDocumentProblem.ACCESS)
        documentGuard(qualified)
        val columns = arrayOf(DocumentsContract.Document.COLUMN_DOCUMENT_ID, DocumentsContract.Document.COLUMN_MIME_TYPE,
            DocumentsContract.Document.COLUMN_FLAGS, DocumentsContract.Document.COLUMN_SIZE, DocumentsContract.Document.COLUMN_DISPLAY_NAME)
        val result = try { context.contentResolver.query(uri, columns, null, null, null)?.use { cursor ->
            documentGuard(qualified)
            if (cursor.count != 1 || !cursor.moveToFirst()) documentFailure(BackupDocumentProblem.LOCAL_LOCATION)
            val sizeIndex = cursor.getColumnIndexOrThrow(DocumentsContract.Document.COLUMN_SIZE)
            val flagsIndex = cursor.getColumnIndexOrThrow(DocumentsContract.Document.COLUMN_FLAGS)
            val nameIndex = cursor.getColumnIndex(DocumentsContract.Document.COLUMN_DISPLAY_NAME)
            if (cursor.isNull(flagsIndex)) documentFailure(BackupDocumentProblem.LOCAL_LOCATION)
            BackupDocumentInfo(cursor.getString(cursor.getColumnIndexOrThrow(DocumentsContract.Document.COLUMN_DOCUMENT_ID))
                ?: documentFailure(BackupDocumentProblem.LOCAL_LOCATION),
                cursor.getString(cursor.getColumnIndexOrThrow(DocumentsContract.Document.COLUMN_MIME_TYPE))
                    ?: documentFailure(BackupDocumentProblem.LOCAL_LOCATION), cursor.getInt(flagsIndex),
                if (cursor.isNull(sizeIndex)) null else cursor.getLong(sizeIndex), true, modes,
                if (nameIndex < 0 || cursor.isNull(nameIndex) || cursor.getType(nameIndex) != Cursor.FIELD_TYPE_STRING) null else cursor.getString(nameIndex))
        } } catch (error: BackupDocumentException) { throw error }
        catch (_: Exception) { documentFailure(BackupDocumentProblem.LOCAL_LOCATION) }
            ?: documentFailure(BackupDocumentProblem.LOCAL_LOCATION)
        documentGuard(qualified)
        return result
    }

    override fun open(uri: Uri, mode: String, qualified: () -> Boolean): ParcelFileDescriptor {
        documentGuard(qualified)
        val descriptor = context.contentResolver.openFileDescriptor(uri, mode) ?: documentFailure(BackupDocumentProblem.IO)
        try { documentGuard(qualified); return descriptor }
        catch (error: Exception) {
            try { descriptor.close() } catch (_: Exception) { /* 撤权后仍尝试释放描述符。 */ }
            throw error
        }
    }

    override fun delete(uri: Uri, qualified: () -> Boolean): Boolean {
        documentGuard(qualified)
        return DocumentsContract.deleteDocument(context.contentResolver, uri)
    }
}

internal class BackupDocuments(
    private val context: Context,
    private val privateDirectory: File,
    private val transport: BackupDocumentTransport = AndroidBackupDocumentTransport(context),
) {
    // 名称仅供显示；须由认证后的明确继续操作调用，不从URI猜名称或据名称授予权限。
    fun documentName(uri: Uri, qualified: () -> Boolean): String = documentChecked {
        val name = inspect(uri, READ, qualified).displayName
        if (name.isNullOrEmpty()) documentFailure(BackupDocumentProblem.NAME)
        try { validatedUtf8(name, Int.MAX_VALUE, Int.MAX_VALUE).fill(0) }
        catch (_: VaultException) { documentFailure(BackupDocumentProblem.NAME) }
        documentGuard(qualified)
        name
    }

    // 仅认领父层已登记创建请求的空文件；不读取正文或授予库权限。
    fun claimCreated(uri: Uri, requestId: String, ownershipToken: String, qualified: () -> Boolean): CreatedBackupDocument = documentChecked {
        if (requestId.isBlank() || ownershipToken.isBlank()) documentFailure(BackupDocumentProblem.CANCELLED)
        val name = inspect(uri, READ_WRITE, qualified).displayName.orEmpty()
        val identity = transport.open(uri, "rw", qualified).use { descriptor ->
            stamp(descriptor.fileDescriptor, qualified, writable = true).also {
                if (it.size != 0L) documentChanged(BackupChangeCheck.CLAIM_EMPTY, uri, setOf(BackupChangeDifference.SIZE))
            }
        }
        documentGuard(qualified)
        val displayName = try { validatedUtf8(name, Int.MAX_VALUE, Int.MAX_VALUE).fill(0); name }
            catch (_: VaultException) { "" }
        CreatedBackupDocument(uri, requestId, ownershipToken, identity, displayName)
    }

    // 消费回调只在父层数据所有者解析，最终回执前不得把值发布到界面。
    fun <T> readImport(uri: Uri, qualified: () -> Boolean, consume: (InputStream) -> T): BackupDocumentRead<T> = documentChecked {
        inspect(uri, READ, qualified)
        var initial: Stamp? = null
        val result = transport.open(uri, "r", qualified).use { descriptor ->
            val before = stamp(descriptor.fileDescriptor, qualified)
            initial = before
            seekStart(descriptor.fileDescriptor, qualified)
            val input = GuardedInput(descriptor.fileDescriptor, qualified)
            val value = consume(input)
            input.drain()
            if (input.bytes != before.size) documentChanged(BackupChangeCheck.READ_STABLE, uri, setOf(BackupChangeDifference.BYTES))
            val after = stamp(descriptor.fileDescriptor, qualified)
            if (after != before) documentChanged(BackupChangeCheck.READ_STABLE, uri, stampDifferences(before, after))
            if (descriptor.canDetectErrors()) { documentGuard(qualified); descriptor.checkError() }
            BackupDocumentRead(value, input.receipt(uri, before))
        }
        inspect(uri, READ, qualified)
        transport.open(uri, "r", qualified).use { descriptor ->
            val current = stamp(descriptor.fileDescriptor, qualified)
            if (current != initial) {
                val differences = stampDifferences(requireNotNull(initial), current)
                if (BackupChangeDifference.IDENTITY in differences || BackupChangeDifference.SIZE in differences)
                    documentChanged(BackupChangeCheck.REOPEN_STABLE, uri, differences)
                // 时间分歧不能视作无害；在当前句柄内补齐完整内容证明，不再开启句柄追逐时间。
                seekStart(descriptor.fileDescriptor, qualified)
                val input = GuardedInput(descriptor.fileDescriptor, qualified)
                input.drain()
                if (input.bytes != current.size) documentChanged(BackupChangeCheck.REOPEN_READ_STABLE, uri, setOf(BackupChangeDifference.BYTES))
                val after = stamp(descriptor.fileDescriptor, qualified)
                if (after != current) documentChanged(BackupChangeCheck.REOPEN_READ_STABLE, uri, stampDifferences(current, after))
                if (descriptor.canDetectErrors()) { documentGuard(qualified); descriptor.checkError() }
                val proof = input.receipt(uri, current)
                val contentDifferences = receiptDifferences(result.receipt, proof)
                if (contentDifferences.isNotEmpty()) documentChanged(BackupChangeCheck.REOPEN_PROOF, uri, contentDifferences)
                inspect(uri, READ, qualified)
            }
        }
        documentGuard(qualified)
        result
    }

    fun exportNew(source: File, created: CreatedBackupDocument, qualified: () -> Boolean,
                  stillOwned: (CreatedBackupDocument) -> Boolean): BackupDocumentReceipt = documentChecked {
        val active = { qualified() && stillOwned(created) }
        if (created.requestId.isBlank() || created.ownershipToken.isBlank()) documentFailure(BackupDocumentProblem.CANCELLED)
        val expected = privateFingerprint(source, active, created.uri)
        inspect(created.uri, READ_WRITE, active)
        transport.open(created.uri, "rw", active).use { destination ->
            val beforeWrite = stamp(destination.fileDescriptor, active, writable = true)
            if (beforeWrite.size != 0L) documentChanged(BackupChangeCheck.BEFORE_WRITE, created.uri, setOf(BackupChangeDifference.SIZE))
            if (beforeWrite != created.emptyStamp) documentChanged(BackupChangeCheck.BEFORE_WRITE, created.uri, stampDifferences(created.emptyStamp, beforeWrite))
            documentGuard(active)
            created.preparedPacket = expected.copy(uri = created.uri, device = created.device, inode = created.inode)
            Os.ftruncate(destination.fileDescriptor, 0)
            seekStart(destination.fileDescriptor, active)
            val copied = withPrivateSource(source, active) { descriptor, before ->
                val input = GuardedInput(descriptor.fileDescriptor, active)
                val buffer = ByteArray(8192)
                try {
                    while (true) {
                        val count = input.read(buffer)
                        if (count < 0) break
                        var offset = 0
                        while (offset < count) {
                            documentGuard(active)
                            val written = Os.write(destination.fileDescriptor, buffer, offset, count - offset)
                            if (written <= 0) documentFailure(BackupDocumentProblem.IO)
                            offset += written
                        }
                    }
                    if (input.bytes != before.size) documentChanged(BackupChangeCheck.COPY_READ, created.uri, setOf(BackupChangeDifference.BYTES))
                    val after = stamp(descriptor.fileDescriptor, active)
                    if (after != before) documentChanged(BackupChangeCheck.COPY_READ, created.uri, stampDifferences(before, after))
                    input.receipt(created.uri, before)
                } finally { buffer.fill(0) }
            }
            if (copied.bytes != expected.bytes || copied.sha256 != expected.sha256) documentChanged(BackupChangeCheck.COPY_PROOF, created.uri,
                receiptDifferences(expected, copied, identity = false))
            documentGuard(active)
            Os.fsync(destination.fileDescriptor)
            val written = stamp(destination.fileDescriptor, active)
            sameCreated(written, created)
            if (written.size != expected.bytes) documentChanged(BackupChangeCheck.WRITTEN_SIZE, created.uri, setOf(BackupChangeDifference.SIZE))
        }
        val readback = readImport(created.uri, active) { Unit }.receipt
        if (readback.device != created.device || readback.inode != created.inode ||
            readback.bytes != expected.bytes || readback.sha256 != expected.sha256) documentChanged(BackupChangeCheck.FINAL_RECEIPT, created.uri,
                receiptDifferences(expected.copy(device = created.device, inode = created.inode), readback))
        documentGuard(active)
        created.published = true
        readback
    }

    // 没有导入源删除入口；只按父层仍确认的本次新文件引用清理，不扫目录或猜路径。
    fun cleanupCreated(created: CreatedBackupDocument, stillOwned: (CreatedBackupDocument) -> Boolean): BackupDocumentCleanup {
        if (created.published) return BackupDocumentCleanup.PUBLISHED
        val owned = { created.requestId.isNotBlank() && created.ownershipToken.isNotBlank() && stillOwned(created) }
        return try {
            documentGuard(owned)
            val info = inspect(created.uri, READ_WRITE, owned)
            if (info.flags and DocumentsContract.Document.FLAG_SUPPORTS_DELETE == 0) return BackupDocumentCleanup.RESIDUAL
            val current = transport.open(created.uri, "r", owned).use { descriptor ->
                stamp(descriptor.fileDescriptor, owned)
            }
            if (current.device != created.device || current.inode != created.inode) return BackupDocumentCleanup.OWNERSHIP_LOST
            if (current != created.emptyStamp) {
                val expected = created.preparedPacket ?: return BackupDocumentCleanup.RESIDUAL
                val actual = readImport(created.uri, owned) { Unit }.receipt
                if (actual.device != created.device || actual.inode != created.inode ||
                    actual.bytes != expected.bytes || actual.sha256 != expected.sha256) return BackupDocumentCleanup.RESIDUAL
            }
            documentGuard(owned)
            if (transport.delete(created.uri, owned)) BackupDocumentCleanup.DELETED else BackupDocumentCleanup.RESIDUAL
        } catch (error: BackupDocumentException) {
            if (error.problem == BackupDocumentProblem.CANCELLED) BackupDocumentCleanup.OWNERSHIP_LOST
            else BackupDocumentCleanup.RESIDUAL
        } catch (_: Exception) { BackupDocumentCleanup.RESIDUAL }
    }

    private fun inspect(uri: Uri, modes: Int, qualified: () -> Boolean): BackupDocumentInfo {
        documentGuard(qualified)
        if (uri.scheme != "content" || uri.authority !in localPackages || uri.query != null || uri.fragment != null ||
            uri.pathSegments.size != 2 || uri.pathSegments[0] != "document" || uri.pathSegments[1].isEmpty()) {
            documentFailure(BackupDocumentProblem.LOCAL_LOCATION)
        }
        val info = transport.inspect(uri, modes, qualified)
        if (!info.verifiedSystemProvider || info.documentId != DocumentsContract.getDocumentId(uri) ||
            info.mimeType.isEmpty() || info.mimeType == DocumentsContract.Document.MIME_TYPE_DIR ||
            info.flags and (DocumentsContract.Document.FLAG_VIRTUAL_DOCUMENT or DocumentsContract.Document.FLAG_PARTIAL) != 0) {
            documentFailure(BackupDocumentProblem.LOCAL_LOCATION)
        }
        if (info.grantedModes and modes != modes) documentFailure(BackupDocumentProblem.ACCESS)
        if (modes and WRITE != 0 && info.flags and DocumentsContract.Document.FLAG_SUPPORTS_WRITE == 0) documentFailure(BackupDocumentProblem.LOCAL_LOCATION)
        if (info.size != null && info.size > BackupProtocol.MAX_BYTES) documentFailure(BackupDocumentProblem.LIMIT)
        documentGuard(qualified)
        return info
    }

    private fun privateFingerprint(source: File, qualified: () -> Boolean, destination: Uri): BackupDocumentReceipt =
        withPrivateSource(source, qualified) { descriptor, before ->
            val input = GuardedInput(descriptor.fileDescriptor, qualified)
            input.drain()
            if (input.bytes != before.size) documentChanged(BackupChangeCheck.PRIVATE_READ, destination, setOf(BackupChangeDifference.BYTES))
            val after = stamp(descriptor.fileDescriptor, qualified)
            if (after != before) documentChanged(BackupChangeCheck.PRIVATE_READ, destination, stampDifferences(before, after))
            input.receipt(Uri.EMPTY, before)
        }

    private fun <T> withPrivateSource(source: File, qualified: () -> Boolean, read: (ParcelFileDescriptor, Stamp) -> T): T {
        documentGuard(qualified)
        val root = privateDirectory.absoluteFile
        val anchors = listOf(context.cacheDir.canonicalFile, context.noBackupFilesDir.canonicalFile)
        if (!root.isDirectory || root.canonicalFile != root || Files.isSymbolicLink(root.toPath()) ||
            anchors.none { root.toPath().startsWith(it.toPath()) } || source.parentFile?.absoluteFile != root ||
            Files.isSymbolicLink(source.toPath()) || source.canonicalFile != source.absoluteFile || !source.isFile || source.length() == 0L) {
            documentFailure(BackupDocumentProblem.SOURCE)
        }
        if (source.length() > BackupProtocol.MAX_BYTES) documentFailure(BackupDocumentProblem.LIMIT)
        documentGuard(qualified)
        return ParcelFileDescriptor.open(source, ParcelFileDescriptor.MODE_READ_ONLY).use { descriptor ->
            val before = stamp(descriptor.fileDescriptor, qualified)
            seekStart(descriptor.fileDescriptor, qualified)
            read(descriptor, before)
        }
    }

    internal data class Stamp(val device: Long, val inode: Long, val size: Long, val modifiedSeconds: Long, val modifiedNanos: Long,
                              val changedSeconds: Long, val changedNanos: Long)

    private fun stamp(descriptor: FileDescriptor, qualified: () -> Boolean, writable: Boolean = false): Stamp {
        documentGuard(qualified)
        val value = Os.fstat(descriptor)
        if (!OsConstants.S_ISREG(value.st_mode) || value.st_ino <= 0 || value.st_size < 0) documentFailure(BackupDocumentProblem.LOCAL_LOCATION)
        if (value.st_size > BackupProtocol.MAX_BYTES) documentFailure(BackupDocumentProblem.LIMIT)
        documentGuard(qualified)
        Os.lseek(descriptor, 0, OsConstants.SEEK_CUR)
        documentGuard(qualified)
        if (Os.read(descriptor, byteArrayOf(), 0, 0) != 0) documentFailure(BackupDocumentProblem.IO)
        if (writable) {
            documentGuard(qualified)
            if (Os.write(descriptor, byteArrayOf(), 0, 0) != 0) documentFailure(BackupDocumentProblem.IO)
        }
        documentGuard(qualified)
        return Stamp(value.st_dev, value.st_ino, value.st_size, value.st_mtim.tv_sec, value.st_mtim.tv_nsec,
            value.st_ctim.tv_sec, value.st_ctim.tv_nsec)
    }

    private fun sameCreated(stamp: Stamp, created: CreatedBackupDocument) {
        if (stamp.device != created.device || stamp.inode != created.inode)
            documentChanged(BackupChangeCheck.WRITTEN_IDENTITY, created.uri, setOf(BackupChangeDifference.IDENTITY))
    }

    private fun stampDifferences(before: Stamp, after: Stamp): Set<BackupChangeDifference> = buildSet {
        if (before.device != after.device || before.inode != after.inode) add(BackupChangeDifference.IDENTITY)
        if (before.size != after.size) add(BackupChangeDifference.SIZE)
        if (before.modifiedSeconds != after.modifiedSeconds || before.modifiedNanos != after.modifiedNanos) add(BackupChangeDifference.MODIFIED)
        if (before.changedSeconds != after.changedSeconds || before.changedNanos != after.changedNanos) add(BackupChangeDifference.CHANGED_TIME)
    }

    private fun receiptDifferences(before: BackupDocumentReceipt, after: BackupDocumentReceipt, identity: Boolean = true): Set<BackupChangeDifference> = buildSet {
        if (identity && (before.device != after.device || before.inode != after.inode)) add(BackupChangeDifference.IDENTITY)
        if (before.bytes != after.bytes) add(BackupChangeDifference.BYTES)
        if (before.sha256 != after.sha256) add(BackupChangeDifference.DIGEST)
    }

    private fun seekStart(descriptor: FileDescriptor, qualified: () -> Boolean) {
        documentGuard(qualified)
        if (Os.lseek(descriptor, 0, OsConstants.SEEK_SET) != 0L) documentFailure(BackupDocumentProblem.IO)
        documentGuard(qualified)
    }

    private class GuardedInput(private val descriptor: FileDescriptor, private val qualified: () -> Boolean) : InputStream() {
        private val digest = MessageDigest.getInstance("SHA-256")
        var bytes: Long = 0
            private set
        override fun read(): Int {
            val single = ByteArray(1)
            return if (read(single, 0, 1) < 0) -1 else single[0].toInt() and 255
        }
        override fun read(buffer: ByteArray, offset: Int, length: Int): Int {
            if (length == 0) return 0
            documentGuard(qualified)
            val count = Os.read(descriptor, buffer, offset, minOf(length.toLong(), BackupProtocol.MAX_BYTES - bytes + 1).toInt())
            documentGuard(qualified)
            if (count == 0) return -1
            bytes += count
            if (bytes > BackupProtocol.MAX_BYTES) documentFailure(BackupDocumentProblem.LIMIT)
            digest.update(buffer, offset, count)
            return count
        }
        override fun close() { /* 描述符属于传输层，消费回调不能提前关闭。 */ }
        fun drain() {
            val buffer = ByteArray(8192)
            try { while (read(buffer) >= 0) { /* 读到真实末尾并累计完整摘要。 */ } }
            finally { buffer.fill(0) }
        }
        fun receipt(uri: Uri, stamp: Stamp): BackupDocumentReceipt =
            BackupDocumentReceipt(uri, bytes, digest.digest().joinToString("") { (it.toInt() and 255).toString(16).padStart(2, '0') }, stamp.device, stamp.inode)
    }
}

private val localPackages = mapOf("com.android.externalstorage.documents" to "com.android.externalstorage",
    "com.android.providers.downloads.documents" to "com.android.providers.downloads")
private const val READ = Intent.FLAG_GRANT_READ_URI_PERMISSION
private const val WRITE = Intent.FLAG_GRANT_WRITE_URI_PERMISSION
private const val READ_WRITE = READ or WRITE

private fun documentGuard(qualified: () -> Boolean) {
    val current = try { qualified() } catch (_: Exception) { false }
    if (!current) documentFailure(BackupDocumentProblem.CANCELLED)
}

private inline fun <T> documentChecked(action: () -> T): T = try { action() }
catch (error: BackupDocumentException) { throw error }
catch (error: BackupProtocolException) { throw error }
catch (_: CancellationException) { documentFailure(BackupDocumentProblem.CANCELLED) }
catch (_: Exception) { documentFailure(BackupDocumentProblem.IO) }

private fun documentFailure(problem: BackupDocumentProblem): Nothing = throw BackupDocumentException(problem)

private fun documentChanged(check: BackupChangeCheck, uri: Uri, differences: Set<BackupChangeDifference>): Nothing {
    val provider = when (uri.authority) {
        "com.android.providers.downloads.documents" -> BackupLocalProvider.DOWNLOADS
        "com.android.externalstorage.documents" -> BackupLocalProvider.STORAGE
        else -> null
    }
    throw BackupDocumentException(BackupDocumentProblem.CHANGED, BackupChangeDiagnostic(check, provider, differences))
}
