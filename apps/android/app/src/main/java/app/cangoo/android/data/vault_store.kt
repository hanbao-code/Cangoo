package app.cangoo.android.data

import app.cangoo.android.BuildConfig
import android.content.Context
import android.net.Uri
import android.system.Os
import android.system.OsConstants
import android.util.AtomicFile
import android.util.Base64
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.NonCancellable
import kotlinx.coroutines.currentCoroutineContext
import kotlinx.coroutines.ensureActive
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.io.ByteArrayOutputStream
import java.io.DataOutputStream
import java.io.File
import java.io.FileOutputStream
import java.io.FilterInputStream
import java.io.FilterOutputStream
import java.io.InputStream
import java.nio.file.Files
import java.security.MessageDigest
import java.text.Collator
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.TimeZone
import java.util.UUID
import java.util.concurrent.Callable
import java.util.concurrent.atomic.AtomicLong
import java.util.concurrent.atomic.AtomicReference
import java.time.Instant
import javax.crypto.AEADBadTagException

internal class BackupTransferSnapshot(val bytes: ByteArray, val passwordCount: Int, val noteCount: Int) {
    override fun toString() = "BackupTransferSnapshot(内容已隐藏)"
}

class VaultStore private constructor(context: Context, documentFactory: (Context, File) -> BackupDocuments) {
    constructor(context: Context) : this(context, { app, directory -> BackupDocuments(app, directory) })
    internal constructor(context: Context, transport: BackupDocumentTransport) :
        this(context, { app, directory -> BackupDocuments(app, directory, transport) })
    private val context = context.applicationContext
    private val root = File(this.context.noBackupFilesDir.canonicalFile, "vaults")
    private val backupDirectory = File(this.context.noBackupFilesDir.canonicalFile, "backup_work")
    private val backupDocuments = documentFactory(this.context, backupDirectory)
    // ponytail: 单进程只打开一个库；需要并行后台业务时再细分锁。
    private val mutex = Mutex()
    private val generation = AtomicLong()
    private var session: Session? = null
    private class PendingImport(val id: String, val vaultId: String, val generation: Long, val epoch: Long,
                                val source: Uri?, val receipt: BackupDocumentReceipt?, val payload: BackupPayload, val targets: BackupTargetSnapshot)
    private class ImportSlot(val epoch: Long, val preview: PendingImport? = null, val activeId: String? = null)
    private val importSlot = AtomicReference(ImportSlot(0))

    private class Session(val id: String, val generation: Long, val database: VaultDatabase, val key: ByteArray,
                          val cleanup: VaultCleanupStatus = VaultCleanupStatus(true, emptyList())) {
        val strengthEpochs = mutableMapOf<String, Long>()
        var nextStrengthEpoch = 0L
        var dataRevision = 0L
        fun invalidateStrength(id: String) { strengthEpochs[id] = ++nextStrengthEpoch }
    }

    fun revoke() {
        generation.incrementAndGet()
        discardImport()
    }

    internal suspend fun currentSessionId(): String? = withContext(Dispatchers.IO) {
        mutex.withLock { session?.takeIf { it.generation == generation.get() }?.id }
    }

    internal suspend fun pendingCleanupStatus(vaultId: String): VaultCleanupStatus = withSession { current ->
        checkVault(current, vaultId)
        current.cleanup
    }

    internal fun discardImport(previewId: String? = null) {
        while (true) {
            val current = importSlot.get()
            if (previewId != null && current.activeId != previewId) return
            if (importSlot.compareAndSet(current, ImportSlot(current.epoch + 1))) return
        }
    }

    internal fun cleanupBackupDestination(created: CreatedBackupDocument, stillOwned: (CreatedBackupDocument) -> Boolean): BackupDocumentCleanup =
        backupDocuments.cleanupCreated(created, stillOwned)

    internal suspend fun localBackupRecord(vaultId: String): LocalBackupRecordState = withSession { current ->
        checkVault(current, vaultId)
        try { LocalBackupRecordFile(vaultDirectory(vaultId), vaultId).read() }
        catch (_: Exception) { LocalBackupRecordState.Unavailable }
    }

    // 系统回调只交关联；父层在正常目标认证且用户明确继续后才能调用这段IO。
    internal suspend fun backupDocumentName(vaultId: String, uri: Uri, qualified: () -> Boolean): String {
        val request = currentCoroutineContext()
        return withSession { current ->
            checkVault(current, vaultId)
            val guard = { request.ensureActive(); checkGeneration(current.generation); backupQualified(qualified) }
            guard()
            val name = try { backupDocuments.documentName(uri) { backupAllowed(guard) } }
                catch (failure: Exception) { guard(); throw failure }
            guard()
            name
        }
    }

    // 创建请求的有限文件证明独立于库会话；调用方必须持有原登记请求。
    internal fun claimBackupDestination(uri: Uri, requestId: String, ownershipToken: String,
                                        qualified: () -> Boolean): CreatedBackupDocument =
        backupDocuments.claimCreated(uri, requestId, ownershipToken, qualified)

    internal suspend fun exportBackup(vaultId: String, scope: BackupScope, password: String,
                                      destination: CreatedBackupDocument, qualified: () -> Boolean,
                                      stillOwned: (CreatedBackupDocument) -> Boolean,
                                      onPrivateCleanup: (BackupPrivateCleanup) -> Unit = {},
                                      onLocalRecordWrite: (LocalBackupRecordWrite) -> Unit = {}): BackupExportResult {
        val request = currentCoroutineContext()
        return withSession { current ->
            checkVault(current, vaultId)
            val guard = { request.ensureActive(); checkGeneration(current.generation); backupQualified(qualified) }
            guard()
            try {
                if (password.isEmpty()) throw BackupProtocolException(BackupProblem.PASSWORD)
                validatedUtf8(password, 1024, 4096).fill(0)
            } catch (_: VaultException) { throw BackupProtocolException(BackupProblem.PASSWORD) }
            val file = File(backupDirectory, "pending_${UUID.randomUUID()}.pdmbackup.json")
            var privateIdentity: Pair<Long, Long>? = null
            var contentProof: BackupContentProof? = null
            try {
                if ((!backupDirectory.isDirectory && !backupDirectory.mkdir()) || backupDirectory.canonicalFile != backupDirectory.absoluteFile ||
                    Files.isSymbolicLink(backupDirectory.toPath()) || !file.createNewFile()) throw VaultException(VaultError.STORAGE_FAILED)
                val created = Os.lstat(file.absolutePath)
                if (!OsConstants.S_ISREG(created.st_mode)) throw VaultException(VaultError.DATA_UNAVAILABLE)
                privateIdentity = created.st_dev to created.st_ino
                val payload = current.database.runInTransaction(Callable { guard(); BackupRecords.export(current.database, scope, guard) })
                FileOutputStream(file).use { output ->
                    contentProof = BackupProtocol.encrypt(payload, password, object : FilterOutputStream(output) {
                        private var bytes = 0L
                        override fun write(value: Int) { guard(); out.write(value); bytes++; limit() }
                        override fun write(buffer: ByteArray, offset: Int, length: Int) { guard(); out.write(buffer, offset, length); bytes += length; limit() }
                        override fun flush() { guard(); out.flush(); guard() }
                        private fun limit() { if (bytes > BackupProtocol.MAX_BYTES) throw BackupStoreException(BackupStoreProblem.LIMIT); guard() }
                    }, guard = guard)
                    guard()
                    output.fd.sync()
                }
                guard()
                file.inputStream().use { input -> BackupProtocol.verify(guardedInput(input, guard), password, contentProof!!, guard = guard) }
                guard()
                val receipt = backupDocuments.exportNew(file, destination, { backupAllowed(guard) }, stillOwned)
                // 已发生的完整导出事实在原库同步收尾；不再读库或恢复会话。
                val completed = LocalBackupRecord(current.id, Instant.ofEpochMilli(System.currentTimeMillis()), scope)
                var localRecord: LocalBackupRecordState = LocalBackupRecordState.Unavailable
                val localWrite = try {
                    val recordFile = LocalBackupRecordFile(vaultDirectory(current.id), current.id)
                    recordFile.write(completed).also { outcome ->
                        localRecord = when (outcome) {
                            LocalBackupRecordWrite.SAVED -> LocalBackupRecordState.Available(completed)
                            LocalBackupRecordWrite.NOT_SAVED -> recordFile.read()
                            LocalBackupRecordWrite.UNVERIFIED -> LocalBackupRecordState.Unavailable
                        }
                    }
                } catch (_: Exception) { LocalBackupRecordWrite.NOT_SAVED }
                runCatching { onLocalRecordWrite(localWrite) }
                guard()
                BackupExportResult(payload.passwords.size, payload.notes.size, receipt, localWrite, localRecord)
            } catch (failure: Exception) {
                guard()
                throw failure
            } finally {
                contentProof?.erase()
                // 新系统文档由文件意图finally消费cleanup结果；此处只精确清理私有加密临时包。
                val cleanup = cleanupPrivateBackup(file, privateIdentity)
                // 只交付本次局部原子holder；接收方异常不能改写已核实的完整文档发布事实。
                runCatching { onPrivateCleanup(cleanup) }
            }
        }
    }

    private fun cleanupPrivateBackup(file: File, identity: Pair<Long, Long>?): BackupPrivateCleanup = try {
        val path = file.toPath()
        if (file.parentFile != backupDirectory || backupDirectory.canonicalFile != backupDirectory.absoluteFile ||
            Files.isSymbolicLink(backupDirectory.toPath()) || file.canonicalFile != file.absoluteFile || Files.isSymbolicLink(path)) BackupPrivateCleanup.RESIDUAL
        else if (!Files.exists(path, java.nio.file.LinkOption.NOFOLLOW_LINKS)) BackupPrivateCleanup.REMOVED
        else if (identity == null) BackupPrivateCleanup.RESIDUAL
        else {
            val current = Os.lstat(file.absolutePath)
            if (!OsConstants.S_ISREG(current.st_mode) || current.st_dev != identity.first || current.st_ino != identity.second) BackupPrivateCleanup.RESIDUAL
            else if (file.delete() && !Files.exists(path, java.nio.file.LinkOption.NOFOLLOW_LINKS)) BackupPrivateCleanup.REMOVED
            else BackupPrivateCleanup.RESIDUAL
        }
    } catch (_: Exception) { BackupPrivateCleanup.RESIDUAL }

    internal suspend fun exportTransferSnapshot(vaultId: String, scope: BackupScope,
                                                qualified: () -> Boolean): BackupTransferSnapshot {
        val request = currentCoroutineContext()
        var encoded: ByteArray? = null
        try {
            return withSession { current ->
                checkVault(current, vaultId)
                val guard = { request.ensureActive(); checkGeneration(current.generation); backupQualified(qualified) }
                guard()
                val payload = current.database.runInTransaction(Callable {
                    BackupRecords.export(current.database, scope, guard, encryptedEnvelope = false)
                })
                val bytes = BackupProtocol.encodePayload(payload, guard)
                encoded = bytes
                guard()
                BackupTransferSnapshot(bytes, payload.passwords.size, payload.notes.size)
            }
        } catch (failure: Exception) { encoded?.fill(0); throw failure }
    }

    // 原生认证后转移encoded唯一所有权；调用方不能并发改写，所有退出均由此擦除。
    internal suspend fun previewReceivedSnapshot(vaultId: String, encoded: ByteArray, expectedScope: BackupScope,
                                                  expectedPasswordCount: Int, expectedNoteCount: Int,
                                                  qualified: () -> Boolean): BackupImportPreview {
        try {
            if (encoded.size > BackupProtocol.MAX_BYTES) throw BackupProtocolException(BackupProblem.LIMIT)
            return previewPayload(vaultId, null, qualified) { guard ->
                if (expectedPasswordCount < 0 || expectedNoteCount < 0 ||
                    expectedPasswordCount.toLong() + expectedNoteCount > BackupProtocol.MAX_RECORDS)
                    throw BackupProtocolException(BackupProblem.FORMAT)
                val payload = encoded.inputStream().use { BackupProtocol.readPayload(guardedInput(it, guard), encoded.size) }
                guard()
                if (payload.scope != expectedScope || payload.passwords.size != expectedPasswordCount || payload.notes.size != expectedNoteCount)
                    throw BackupProtocolException(BackupProblem.FORMAT)
                payload to null
            }
        } finally { encoded.fill(0) }
    }

    internal suspend fun previewImport(vaultId: String, source: Uri, password: String, qualified: () -> Boolean): BackupImportPreview =
        previewPayload(vaultId, source, qualified) { guard ->
            val read = backupDocuments.readImport(source, { backupAllowed(guard) }) { BackupProtocol.decrypt(it, password, guard = guard) }
            read.value to read.receipt
        }

    private suspend fun previewPayload(vaultId: String, source: Uri?, qualified: () -> Boolean,
                                        readPayload: (() -> Unit) -> Pair<BackupPayload, BackupDocumentReceipt?>): BackupImportPreview {
        val request = currentCoroutineContext()
        val id = UUID.randomUUID().toString()
        val owner = importSlot.updateAndGet { ImportSlot(it.epoch + 1, activeId = id) }
        var installed = false
        try {
            val result = withSession { current ->
                checkVault(current, vaultId)
                val guard = { request.ensureActive(); checkGeneration(current.generation); checkImportEpoch(owner.epoch); backupQualified(qualified) }
                guard()
                val (payload, receipt) = try { readPayload(guard) }
                    catch (failure: Exception) { guard(); throw failure }
                guard()
                val targets = current.database.runInTransaction(Callable { guard(); BackupRecords.snapshot(current.database, payload, guard) })
                val pending = PendingImport(id, vaultId, current.generation, owner.epoch, source, receipt, payload, targets)
                guard()
                if (!importSlot.compareAndSet(owner, ImportSlot(owner.epoch, pending, id))) throw BackupStoreException(BackupStoreProblem.CANCELLED)
                guard()
                previewInfo(pending, guard)
            }
            request.ensureActive()
            installed = true
            return result
        } finally { if (!installed) discardImport(id) }
    }

    internal suspend fun readImportRows(vaultId: String, previewId: String, kind: BackupImportKind, offset: Int,
                                       limit: Int = 20, qualified: () -> Boolean): List<BackupImportRow> {
        val request = currentCoroutineContext()
        return withSession { current ->
            val pending = pendingImport(current, vaultId, previewId)
            val epoch = pending.epoch
            val guard = { request.ensureActive(); checkGeneration(current.generation); checkImportEpoch(epoch); backupQualified(qualified) }
            pageInput(offset, limit)
            val size = if (kind == BackupImportKind.PASSWORD) pending.payload.passwords.size else pending.payload.notes.size
            (offset until minOf(size.toLong(), offset.toLong() + limit).toInt()).map { index ->
                guard()
                importRow(pending, kind, index)
            }.also { guard() }
        }
    }

    private fun importRow(pending: PendingImport, kind: BackupImportKind, index: Int): BackupImportRow = if (kind == BackupImportKind.PASSWORD) {
        val source = pending.payload.passwords[index]
        val target = pending.targets.passwords[source.platform]
        BackupImportRow(index, textPreview(source.platform), truncated(source.platform), textPreview(source.account), truncated(source.account),
            textPreview(source.notes.substringBefore('\n').substringBefore('\r')), source.favorite, source.totpSecret.isNotEmpty(), source.recoveryCodes.size,
            if (target == null) 0 else 1, target != null && index !in pending.targets.identicalPasswords,
            pending.payload.version == 1 && target?.summary?.recoveryCodeCount?.let { it > 0 } == true,
            source.password.isNotEmpty(), target?.summary?.id, target?.summary?.revision, index in pending.targets.identicalPasswords)
    } else {
        val source = pending.payload.notes[index]
        BackupImportRow(index, textPreview(source.title), truncated(source.title), "", false,
            textPreview(source.content.substringBefore('\n').substringBefore('\r')), source.favorite, false, 0,
            pending.targets.notes.getValue(pending.targets.noteKeys[index]).size, BackupRecords.requiredNote(pending.targets, index), false,
            alreadyExists = index in pending.targets.identicalNotes)
    }

    internal suspend fun queryImportRows(vaultId: String, previewId: String, kind: BackupImportKind, query: BackupImportQuery,
                                         decisions: BackupImportDecisions, comparisonTargets: Map<Int, String>, selected: Set<Int>,
                                         offset: Int, limit: Int = 20, qualified: () -> Boolean): BackupImportPage {
        val choices = decisions.copy(passwords = decisions.passwords.toMap(), notes = decisions.notes.toMap())
        val targets = comparisonTargets.toMap()
        val selection = selected.toSet()
        return withImportPreview(vaultId, previewId, qualified) { current, pending, guard ->
            pageInput(offset, limit)
            val result = importQuery(current, pending, kind, query, choices, targets, selection, guard)
            val actualOffset = if (result.indices.isEmpty()) 0 else if (offset >= result.indices.size) (result.indices.size - 1) / limit * limit else offset
            val indices = result.indices.drop(actualOffset).take(limit)
            val masks = if (query.changedField == null) businessMasks(current, pending, kind, indices, result.targets, guard) else result.masks
            val rows = indices.map { index ->
                guard()
                val row = importRow(pending, kind, index)
                val target = result.targets[index]
                row.copy(comparisonTargetId = target, businessChangedFields = when {
                    target != null -> BackupComparisonField.entries.filterTo(linkedSetOf()) { (masks.getValue(index) and (1 shl it.ordinal)) != 0 }
                    row.candidateCount == 0 -> emptySet()
                    else -> null
                }, hasDifferences = row.candidateCount > 0 && !row.alreadyExists)
            }
            val matched = result.indices.toSet()
            BackupImportPage(previewId, kind, rows, actualOffset, result.indices.size,
                (actualOffset + rows.size).takeIf { it < result.indices.size }, result.awaitingTargetCount,
                selection.count { it !in matched })
        }
    }

    internal suspend fun selectImportRows(vaultId: String, previewId: String, kind: BackupImportKind, query: BackupImportQuery,
                                         decisions: BackupImportDecisions, comparisonTargets: Map<Int, String>,
                                         qualified: () -> Boolean): Set<Int> {
        val choices = decisions.copy(passwords = decisions.passwords.toMap(), notes = decisions.notes.toMap())
        val targets = comparisonTargets.toMap()
        return withImportPreview(vaultId, previewId, qualified) { current, pending, guard ->
            val result = importQuery(current, pending, kind, query, choices, targets, emptySet(), guard)
            result.indices.filterTo(linkedSetOf()) { index ->
                guard()
                if (kind == BackupImportKind.PASSWORD) index !in pending.targets.identicalPasswords &&
                    pending.payload.passwords[index].platform in pending.targets.passwords
                else BackupRecords.requiredNote(pending.targets, index)
            }.also { guard() }
        }
    }

    internal suspend fun proposeImportBatch(vaultId: String, previewId: String, kind: BackupImportKind, selected: Set<Int>,
                                            action: BackupImportBatchAction, decisions: BackupImportDecisions, query: BackupImportQuery,
                                            comparisonTargets: Map<Int, String>, qualified: () -> Boolean): BackupImportBatchProposal {
        val choices = decisions.copy(passwords = decisions.passwords.toMap(), notes = decisions.notes.toMap())
        val targets = comparisonTargets.toMap()
        val selection = selected.toSet()
        return withImportPreview(vaultId, previewId, qualified) { current, pending, guard ->
            checkedImportSnapshot(current, pending, guard)
            val result = importQuery(current, pending, kind, query, choices, targets, selection, guard)
            val matched = result.indices.toSet()
            BackupRecords.batchProposal(previewId, pending.payload, pending.targets, kind, selection, action, choices,
                selection.count { it !in matched }, guard)
        }
    }

    internal suspend fun summarizeImportDecisions(vaultId: String, previewId: String, decisions: BackupImportDecisions,
                                                  qualified: () -> Boolean): BackupImportPlanSummary {
        val choices = decisions.copy(passwords = decisions.passwords.toMap(), notes = decisions.notes.toMap())
        return withImportPreview(vaultId, previewId, qualified) { current, pending, guard ->
            val actual = checkedImportSnapshot(current, pending, guard)
            BackupRecords.planSummary(previewId, pending.payload, actual, choices, guard = guard)
        }
    }

    private class ImportQueryResult(val indices: List<Int>, val targets: Map<Int, String?>, val masks: Map<Int, Int>, val awaitingTargetCount: Int)

    private fun importQuery(current: Session, pending: PendingImport, kind: BackupImportKind, query: BackupImportQuery,
                            decisions: BackupImportDecisions, targets: Map<Int, String>, selected: Set<Int>, guard: () -> Unit): ImportQueryResult {
        if (query.changedField != null && !BackupRecords.isBusinessField(kind, query.changedField)) throw BackupStoreException(BackupStoreProblem.INPUT)
        BackupRecords.validateDecisions(pending.payload, pending.targets, decisions, false, guard = guard)
        BackupRecords.validateSelected(pending.payload, pending.targets, kind, selected, guard)
        targets.forEach { (index, target) -> guard(); comparisonTarget(pending, kind, index, target, true) }
        val size = if (kind == BackupImportKind.PASSWORD) pending.payload.passwords.size else pending.payload.notes.size
        val indices = (0 until size).filter { index ->
            guard()
            val identical = if (kind == BackupImportKind.PASSWORD) index in pending.targets.identicalPasswords else index in pending.targets.identicalNotes
            val exists = if (kind == BackupImportKind.PASSWORD) pending.payload.passwords[index].platform in pending.targets.passwords
                else pending.targets.notes.getValue(pending.targets.noteKeys[index]).isNotEmpty()
            val required = if (kind == BackupImportKind.PASSWORD) exists && !identical else BackupRecords.requiredNote(pending.targets, index)
            val decided = if (kind == BackupImportKind.PASSWORD) index in decisions.passwords else index in decisions.notes
            val skipped = if (kind == BackupImportKind.PASSWORD) decisions.passwords[index]?.action == PasswordImportAction.SKIP
                else decisions.notes[index]?.action == NoteImportAction.SKIP
            when (query.state) {
                BackupImportFilter.ALL -> true
                BackupImportFilter.PENDING -> required && !decided
                BackupImportFilter.DIFFERENT -> exists && !identical
                BackupImportFilter.SKIPPED -> identical || skipped
            }
        }
        val resolved = indices.associateWith { index ->
            guard()
            val requested = targets[index] ?: if (kind == BackupImportKind.NOTE) decisions.notes[index]?.targetId else null
            comparisonTarget(pending, kind, index, requested, true)
        }
        val awaiting = if (kind == BackupImportKind.PASSWORD) 0 else indices.count {
            resolved[it] == null && pending.targets.notes.getValue(pending.targets.noteKeys[it]).isNotEmpty()
        }
        val masks = if (query.changedField == null) emptyMap() else businessMasks(current, pending, kind, indices, resolved, guard)
        val matches = if (query.changedField == null) indices else indices.filter { ((masks[it] ?: 0) and (1 shl query.changedField.ordinal)) != 0 }
        return ImportQueryResult(matches, resolved, masks, awaiting)
    }

    private fun businessMasks(current: Session, pending: PendingImport, kind: BackupImportKind, indices: List<Int>,
                              targets: Map<Int, String?>, guard: () -> Unit): Map<Int, Int> {
        val result = mutableMapOf<Int, Int>()
        // 同一目标正文仅在当前组读取期间持有，结果只保字段位标记。
        indices.filter { targets[it] != null }.groupBy { requireNotNull(targets[it]) }.forEach { (id, sources) ->
            guard()
            val first = sources.first()
            val password = if (kind == BackupImportKind.PASSWORD) comparisonPassword(current, pending, first, id, guard) else null
            val note = if (kind == BackupImportKind.NOTE) comparisonNote(current, pending, first, id, guard) else null
            sources.forEach { index ->
                guard()
                val fields = if (password != null) BackupRecords.businessChanges(pending.payload.passwords[index], password, guard)
                    else BackupRecords.businessChanges(pending.payload.notes[index], requireNotNull(note), guard)
                result[index] = fields.fold(0) { mask, field -> mask or (1 shl field.ordinal) }
            }
        }
        guard()
        return result
    }

    private fun checkedImportSnapshot(current: Session, pending: PendingImport, guard: () -> Unit): BackupTargetSnapshot {
        requireSource(pending, guard)
        return current.database.runInTransaction(Callable {
            val actual = BackupRecords.snapshot(current.database, pending.payload, guard)
            if (!pending.targets.sameContent(actual)) throw BackupStoreException(BackupStoreProblem.STALE)
            actual.also { guard() }
        })
    }

    internal suspend fun readImportCandidates(vaultId: String, previewId: String, noteSourceIndex: Int, offset: Int,
                                             limit: Int = 20, qualified: () -> Boolean): List<BackupImportCandidate> {
        val request = currentCoroutineContext()
        return withSession { current ->
            val pending = pendingImport(current, vaultId, previewId)
            val epoch = pending.epoch
            val guard = { request.ensureActive(); checkGeneration(current.generation); checkImportEpoch(epoch); backupQualified(qualified) }
            pageInput(offset, limit)
            if (noteSourceIndex !in pending.payload.notes.indices) throw BackupStoreException(BackupStoreProblem.INPUT)
            val candidates = pending.targets.notes.getValue(pending.targets.noteKeys[noteSourceIndex])
            (offset until minOf(candidates.size.toLong(), offset.toLong() + limit).toInt()).map { index ->
                guard()
                val item = candidates[index]
                val record = noteRecord(current, item.summary.id)
                if (BackupRecords.fingerprint(record, guard) != item.fingerprint) throw BackupStoreException(BackupStoreProblem.STALE)
                BackupImportCandidate(record.id, record.revision, item.summary.title, item.summary.titleTruncated, item.summary.preview,
                    record.title == pending.payload.notes[noteSourceIndex].title, record.id in pending.targets.reservedNoteIds)
            }.also { guard() }
        }
    }

    internal suspend fun readImportText(vaultId: String, previewId: String, kind: BackupImportKind, sourceIndex: Int,
                                       targetId: String?, field: BackupPreviewTextField, offset: Int,
                                       limit: Int = 4096, qualified: () -> Boolean): BackupImportText {
        val request = currentCoroutineContext()
        return withSession { current ->
            val pending = pendingImport(current, vaultId, previewId)
            val epoch = pending.epoch
            val guard = { request.ensureActive(); checkGeneration(current.generation); checkImportEpoch(epoch); backupQualified(qualified) }
            if (offset < 0 || limit !in 1..4096) throw BackupStoreException(BackupStoreProblem.INPUT)
            guard()
            val value = if (kind == BackupImportKind.PASSWORD) {
                val source = pending.payload.passwords.getOrNull(sourceIndex) ?: throw BackupStoreException(BackupStoreProblem.INPUT)
                val target = targetId?.let { id ->
                    val expected = pending.targets.passwords[source.platform] ?: throw BackupStoreException(BackupStoreProblem.INPUT)
                    if (id != expected.summary.id) throw BackupStoreException(BackupStoreProblem.INPUT)
                    passwordRecord(current, id).also { if (BackupRecords.fingerprint(it, guard) != expected.fingerprint) throw BackupStoreException(BackupStoreProblem.STALE) }
                }
                when (field) { BackupPreviewTextField.TITLE -> target?.title ?: source.platform; BackupPreviewTextField.ACCOUNT -> target?.account ?: source.account
                    BackupPreviewTextField.NOTES -> target?.notes ?: source.notes; else -> throw BackupStoreException(BackupStoreProblem.INPUT) }
            } else {
                val source = pending.payload.notes.getOrNull(sourceIndex) ?: throw BackupStoreException(BackupStoreProblem.INPUT)
                val target = targetId?.let { id ->
                    val expected = pending.targets.notes.getValue(pending.targets.noteKeys[sourceIndex]).firstOrNull { it.summary.id == id } ?: throw BackupStoreException(BackupStoreProblem.INPUT)
                    noteRecord(current, id).also { if (BackupRecords.fingerprint(it, guard) != expected.fingerprint) throw BackupStoreException(BackupStoreProblem.STALE) }
                }
                when (field) { BackupPreviewTextField.TITLE -> target?.title ?: source.title; BackupPreviewTextField.CONTENT -> target?.content ?: source.content
                    else -> throw BackupStoreException(BackupStoreProblem.INPUT) }
            }
            val total = value.codePointCount(0, value.length)
            if (offset > total) throw BackupStoreException(BackupStoreProblem.INPUT)
            val end = minOf(total.toLong(), offset.toLong() + limit).toInt()
            val chunk = value.substring(value.offsetByCodePoints(0, offset), value.offsetByCodePoints(0, end))
            guard()
            BackupImportText(chunk, end, end == total)
        }
    }

    internal suspend fun readImportComparison(vaultId: String, previewId: String, kind: BackupImportKind, sourceIndex: Int,
                                               targetId: String? = null, qualified: () -> Boolean): BackupImportComparison =
        withImportComparison(vaultId, previewId, kind, sourceIndex, targetId, qualified) { pending, password, note, guard ->
            val fields = when (kind) {
                BackupImportKind.PASSWORD -> BackupRecords.comparison(pending.payload.passwords[sourceIndex], password, guard)
                BackupImportKind.NOTE -> BackupRecords.comparison(pending.payload.notes[sourceIndex], note, guard)
            }
            val metadata = setOf(BackupComparisonField.STRENGTH, BackupComparisonField.PASSWORD_CHANGED_AT,
                BackupComparisonField.CREATED_AT, BackupComparisonField.UPDATED_AT, BackupComparisonField.SORT_ORDER)
            BackupImportComparison(previewId, kind, sourceIndex, password?.id ?: note?.id, password?.revision ?: note?.revision,
                fields, fields.filter { it.changed && it.field !in metadata }.mapTo(linkedSetOf()) { it.field },
                fields.filter { it.changed && it.field in metadata }.mapTo(linkedSetOf()) { it.field },
                if (kind == BackupImportKind.PASSWORD) sourceIndex in pending.targets.identicalPasswords else sourceIndex in pending.targets.identicalNotes,
                pending.payload.version == 1 && password?.let { checkedRecoveryCodes(it.recoveryCodesJson).isNotEmpty() } == true,
                targetReserved = note?.id?.let(pending.targets.reservedNoteIds::contains) == true)
        }

    internal suspend fun readImportFieldPair(vaultId: String, previewId: String, kind: BackupImportKind, sourceIndex: Int,
                                              targetId: String? = null, field: BackupComparisonField, offset: Int,
                                              limit: Int = 4096, qualified: () -> Boolean): BackupImportFieldPair =
        withImportComparison(vaultId, previewId, kind, sourceIndex, targetId, qualified) { pending, password, note, guard ->
            val (source, current) = when (kind) {
                BackupImportKind.PASSWORD -> BackupRecords.fieldPair(pending.payload.passwords[sourceIndex], password, field, offset, limit, guard)
                BackupImportKind.NOTE -> BackupRecords.fieldPair(pending.payload.notes[sourceIndex], note, field, offset, limit, guard)
            }
            BackupImportFieldPair(previewId, kind, sourceIndex, password?.id ?: note?.id, field, offset, source, current)
        }

    private suspend fun <T> withImportComparison(vaultId: String, previewId: String, kind: BackupImportKind, sourceIndex: Int,
                                                targetId: String?, qualified: () -> Boolean,
                                                read: (PendingImport, PasswordRecord?, NoteRecord?, () -> Unit) -> T): T =
        withImportPreview(vaultId, previewId, qualified) { current, pending, guard ->
            val target = comparisonTarget(pending, kind, sourceIndex, targetId, false)
            val password = if (kind == BackupImportKind.PASSWORD && target != null) comparisonPassword(current, pending, sourceIndex, target, guard) else null
            val note = if (kind == BackupImportKind.NOTE && target != null) comparisonNote(current, pending, sourceIndex, target, guard) else null
            if (kind == BackupImportKind.PASSWORD && target == null &&
                current.database.passwords().idForTitle(pending.payload.passwords[sourceIndex].platform) != null) throw BackupStoreException(BackupStoreProblem.STALE)
            guard()
            read(pending, password, note, guard)
        }

    private fun comparisonTarget(pending: PendingImport, kind: BackupImportKind, index: Int, requested: String?, allowUnresolved: Boolean): String? =
        when (kind) {
            BackupImportKind.PASSWORD -> {
                val source = pending.payload.passwords.getOrNull(index) ?: throw BackupStoreException(BackupStoreProblem.INPUT)
                val expected = pending.targets.passwords[source.platform]?.summary?.id
                if (requested != null && requested != expected) throw BackupStoreException(BackupStoreProblem.INPUT)
                expected
            }
            BackupImportKind.NOTE -> {
                pending.payload.notes.getOrNull(index) ?: throw BackupStoreException(BackupStoreProblem.INPUT)
                val key = pending.targets.noteKeys[index]
                val candidates = pending.targets.notes.getValue(key)
                val identical = pending.targets.identicalNotes[index]
                if (requested != null && (pending.targets.noteTargetsById[requested]?.first != key || identical != null && requested != identical))
                    throw BackupStoreException(BackupStoreProblem.INPUT)
                requested ?: identical ?: when (candidates.size) {
                    0 -> null
                    1 -> candidates.single().summary.id
                    else -> if (allowUnresolved) null else throw BackupStoreException(BackupStoreProblem.INPUT)
                }
            }
        }

    private fun comparisonPassword(current: Session, pending: PendingImport, index: Int, id: String, guard: () -> Unit): PasswordRecord {
        val expected = pending.targets.passwords[pending.payload.passwords[index].platform] ?: throw BackupStoreException(BackupStoreProblem.INPUT)
        if (expected.summary.id != id) throw BackupStoreException(BackupStoreProblem.INPUT)
        requireId(id)
        val record = current.database.passwords().read(id) ?: throw BackupStoreException(BackupStoreProblem.STALE)
        checkPasswordData(record)
        if (BackupRecords.fingerprint(record, guard) != expected.fingerprint) throw BackupStoreException(BackupStoreProblem.STALE)
        return record
    }

    private fun comparisonNote(current: Session, pending: PendingImport, index: Int, id: String, guard: () -> Unit): NoteRecord {
        val expected = pending.targets.noteTargetsById[id] ?: throw BackupStoreException(BackupStoreProblem.INPUT)
        if (expected.first != pending.targets.noteKeys[index]) throw BackupStoreException(BackupStoreProblem.INPUT)
        requireId(id)
        val record = current.database.notes().read(id) ?: throw BackupStoreException(BackupStoreProblem.STALE)
        if (BackupRecords.fingerprint(record, guard) != expected.second.fingerprint) throw BackupStoreException(BackupStoreProblem.STALE)
        return record
    }

    private suspend fun <T> withImportPreview(vaultId: String, previewId: String, qualified: () -> Boolean,
                                             read: (Session, PendingImport, () -> Unit) -> T): T {
        val request = currentCoroutineContext()
        return withSession { current ->
            val pending = pendingImport(current, vaultId, previewId)
            val guard = { request.ensureActive(); checkGeneration(current.generation); checkImportEpoch(pending.epoch); backupQualified(qualified) }
            guard()
            read(current, pending, guard).also { guard() }
        }
    }

    internal suspend fun commitImport(vaultId: String, previewId: String, decisions: BackupImportDecisions,
                                     qualified: () -> Boolean): BackupImportResult {
        val request = currentCoroutineContext()
        val choices = decisions.copy(passwords = decisions.passwords.toMap(), notes = decisions.notes.toMap())
        return withSession { current ->
            val state = importSlot.get()
            val pending = pendingImport(current, vaultId, previewId)
            val guard = { request.ensureActive(); checkGeneration(current.generation); checkImportEpoch(state.epoch); backupQualified(qualified) }
            guard()
            if (!importSlot.compareAndSet(state, ImportSlot(state.epoch, activeId = previewId))) throw BackupStoreException(BackupStoreProblem.STALE)
            val changedIds = mutableListOf<String>()
            try {
                requireSource(pending, guard)
                write(current) {
                    guard()
                    val actual = BackupRecords.snapshot(current.database, pending.payload, guard)
                    if (!pending.targets.sameContent(actual)) throw BackupStoreException(BackupStoreProblem.STALE)
                    val result = BackupRecords.apply(current.database, pending.payload, actual, choices, guard)
                    pending.payload.passwords.forEachIndexed { index, source ->
                        if (index !in actual.identicalPasswords && choices.passwords[index]?.action != PasswordImportAction.SKIP) {
                            current.database.passwords().idForTitle(source.platform)?.let(changedIds::add)
                        }
                    }
                    requireSource(pending, guard)
                    guard()
                    result
                }.also { changedIds.forEach(current::invalidateStrength); guard() }
            } catch (failure: Exception) {
                request.ensureActive()
                checkGeneration(current.generation)
                backupQualified(qualified)
                throw failure
            }
            finally { discardImport(previewId) }
        }
    }

    private fun previewInfo(pending: PendingImport, guard: () -> Unit): BackupImportPreview = BackupImportPreview(pending.id,
        pending.payload.passwords.size, pending.payload.notes.size,
        pending.payload.passwords.indices.count { it !in pending.targets.identicalPasswords && pending.payload.passwords[it].platform in pending.targets.passwords },
        pending.payload.notes.indices.count { BackupRecords.requiredNote(pending.targets, it) },
        BackupRecords.planSummary(pending.id, pending.payload, pending.targets, BackupImportDecisions(), guard = guard))

    private fun pendingImport(current: Session, vaultId: String, id: String): PendingImport {
        checkVault(current, vaultId)
        val pending = importSlot.get().preview ?: throw BackupStoreException(BackupStoreProblem.STALE)
        if (pending.id != id || pending.vaultId != current.id || pending.generation != current.generation) throw BackupStoreException(BackupStoreProblem.STALE)
        return pending
    }

    private fun checkImportEpoch(epoch: Long) {
        if (importSlot.get().epoch != epoch) throw BackupStoreException(BackupStoreProblem.CANCELLED)
    }

    private fun requireSource(pending: PendingImport, guard: () -> Unit) {
        guard()
        val source = pending.source ?: return
        val receipt = try { backupDocuments.readImport(source, { backupAllowed(guard) }) { Unit }.receipt }
            catch (failure: Exception) { guard(); throw failure }
        if (receipt != pending.receipt) throw BackupStoreException(BackupStoreProblem.STALE)
        guard()
    }

    private fun pageInput(offset: Int, limit: Int) {
        if (offset < 0 || limit !in 1..100) throw BackupStoreException(BackupStoreProblem.INPUT)
    }

    private fun truncated(value: String): Boolean = value.codePointCount(0, value.length) > 128
    private fun backupQualified(qualified: () -> Boolean) {
        if (!runCatching(qualified).getOrDefault(false)) throw BackupStoreException(BackupStoreProblem.CANCELLED)
    }
    private fun backupAllowed(guard: () -> Unit): Boolean = try { guard(); true } catch (_: Exception) { false }
    private fun guardedInput(input: InputStream, guard: () -> Unit): InputStream = object : FilterInputStream(input) {
        override fun read(): Int { guard(); return super.read().also { guard() } }
        override fun read(buffer: ByteArray, offset: Int, length: Int): Int { guard(); return super.read(buffer, offset, length).also { guard() } }
    }

    suspend fun lock(): Unit = safely {
        revoke()
        withContext(NonCancellable + Dispatchers.IO) { mutex.withLock { closeSession() } }
    }

    suspend fun listVaults(): List<VaultInfo> = safely {
        withContext(Dispatchers.IO) { mutex.withLock { listVaultsLocked() } }
    }

    internal suspend fun recoverVaultDeletions(): Boolean = safely {
        withContext(Dispatchers.IO) {
            val request = currentCoroutineContext()
            mutex.withLock {
                VaultDeletion.recover(root) { request.ensureActive() }
            }
        }
    }

    internal suspend fun prepareVaultDeletion(vaultId: String, rawMaster: String, qualified: () -> Boolean): DeletionPreview {
        val request = currentCoroutineContext()
        val ticket = generation.get()
        return safely {
            withContext(Dispatchers.IO) {
                mutex.withLock {
                    val guard = { request.ensureActive(); checkGeneration(ticket); deletionQualified(qualified) }
                    guard()
                    VaultDeletion.preview(root, vaultId, rawMaster, guard).also { guard() }
                }
            }
        }
    }

    internal suspend fun confirmVaultDeletion(preview: DeletionPreview, rawMaster: String,
                                              qualified: () -> Boolean): VaultDeletionResult {
        val request = currentCoroutineContext()
        val ticket = generation.get()
        return safely {
            // 受控收尾仍检查原请求；取消不能进入rename，发布后的Outcome则由helper准确返回。
            withContext(NonCancellable + Dispatchers.IO) {
                mutex.withLock {
                    val guard = { request.ensureActive(); checkGeneration(ticket); deletionQualified(qualified) }
                    var closed = false
                    try {
                        guard()
                        val outcome = VaultDeletion.confirm(root, preview, rawMaster, {
                            guard()
                            if (session?.id == preview.id) {
                                closed = true
                                discardImport()
                                closeSession()
                            }
                        }, guard)
                        // 不再用末尾撤权/取消异常覆盖已经确定的目录发布事实。
                        VaultDeletionResult(outcome, closed)
                    } catch (failure: Exception) {
                        // helper只在发布前抛普通异常；当前连接已关闭时明确交付安全终态。
                        if (closed) VaultDeletionResult(DeletionOutcome(DeletionStatus.NOT_REMOVED), true) else throw failure
                    }
                }
            }
        }
    }

    private fun deletionQualified(qualified: () -> Boolean) {
        if (!runCatching(qualified).getOrDefault(false)) throw CancellationException("删除操作已取消或资格已失效。")
    }

    internal suspend fun changeMasterPassword(vaultId: String, oldMaster: String, newMaster: String,
                                              authenticator: VaultBiometricAuthenticator? = null,
                                              restorePermission: () -> Boolean = { true },
                                              onStage: (VaultChangeStage) -> Unit = {},
                                              qualified: () -> Boolean): VaultRotationResult {
        val request = currentCoroutineContext()
        return securityChange(vaultId, oldMaster, newMaster, null, authenticator, restorePermission, onStage, qualified, request)
    }

    internal suspend fun setBiometricEnabled(vaultId: String, master: String?, enabled: Boolean,
                                            authenticator: VaultBiometricAuthenticator, restorePermission: () -> Boolean,
                                            onStage: (VaultChangeStage) -> Unit = {},
                                            qualified: () -> Boolean): VaultRotationResult {
        val request = currentCoroutineContext()
        if (enabled && master.isNullOrEmpty()) return VaultRotationResult.NoCommit(VaultRotationFailure.INVALID_INPUT)
        return securityChange(vaultId, if (enabled) master else null, if (enabled) master else null, enabled,
            authenticator, restorePermission, onStage, qualified, request)
    }

    private suspend fun securityChange(vaultId: String, oldMaster: String?, newMaster: String?, bindingEnabled: Boolean?,
                                       authenticator: VaultBiometricAuthenticator?, restorePermission: () -> Boolean,
                                       onStage: (VaultChangeStage) -> Unit, qualified: () -> Boolean,
                                       request: kotlin.coroutines.CoroutineContext): VaultRotationResult {
        val ticket = generation.get()
        return withContext(NonCancellable) {
            withContext(Dispatchers.IO) {
                mutex.withLock {
                    var authenticated: ByteArray? = null
                    var closed = false
                    var transferred = false
                    var files: VaultResolvedFiles? = null
                    var metadata: Metadata? = null
                    var proof: VaultRotation.SourceProof? = null
                    var completed: VaultRotationResult? = null
                    val guard = {
                        request.ensureActive(); checkGeneration(ticket)
                        if (!runCatching(qualified).getOrDefault(false)) throw CancellationException("本次安全设置操作已取消。")
                    }
                    val restoreGuard = {
                        checkGeneration(ticket)
                        if (!runCatching(restorePermission).getOrDefault(false)) throw VaultException(VaultError.SESSION_CLOSED)
                    }
                    fun restore(): Boolean {
                        if (!closed || session != null || authenticated == null || files == null || metadata == null || proof == null) return false
                        return try {
                            restoreGuard()
                            onStage(VaultChangeStage.RESTORING)
                            VaultRotation.verifySource(requireNotNull(files), requireNotNull(metadata), requireNotNull(authenticated), requireNotNull(proof), restoreGuard)
                            val database = VaultDatabase.open(context, requireNotNull(files).database, requireNotNull(authenticated))
                            try { restoreGuard() }
                            catch (failure: Exception) { database.close(); throw failure }
                            session = Session(vaultId, ticket, database, requireNotNull(authenticated))
                            transferred = true
                            true
                        } catch (_: Exception) { false }
                    }
                    try {
                        guard(); onStage(VaultChangeStage.AUTHENTICATING)
                        val current = session ?: throw VaultException(VaultError.SESSION_CLOSED)
                        checkVault(current, vaultId)
                        if (current.generation != ticket) throw VaultException(VaultError.SESSION_CLOSED)
                        oldMaster?.let { validatedUtf8(it, 1024).fill(0) }
                        newMaster?.let { validatedUtf8(it, 1024).fill(0) }
                        files = VaultLayout.resolve(vaultDirectory(vaultId), vaultId)
                        metadata = Metadata.read(requireNotNull(files).manifest, vaultId)
                        authenticated = oldMaster?.let { requireNotNull(metadata).unlock(it, requireNotNull(files).selection) } ?: current.key.copyOf()
                        VaultDescriptorAuth.verify(requireNotNull(authenticated), requireNotNull(metadata), requireNotNull(files).selection)
                        if (!MessageDigest.isEqual(authenticated, current.key)) throw VaultException(VaultError.DATA_UNAVAILABLE)
                        if (bindingEnabled != null && bindingEnabled == (requireNotNull(metadata).biometric != null)) return@withLock VaultRotationResult.Rotated
                        if (bindingEnabled == null && requireNotNull(metadata).biometric != null && newMaster?.isNotEmpty() == true && authenticator == null) {
                            return@withLock VaultRotationResult.NoCommit(VaultRotationFailure.BIOMETRIC_UNAVAILABLE)
                        }
                        guard(); closed = true; closeSession()
                        proof = VaultRotation.sourceProof(requireNotNull(files), guard)
                        val port = authenticator?.let { native ->
                            val cancellable: VaultBiometricAuthenticator = { cipher, purpose -> withContext(request) { native(cipher, purpose) } }
                            cancellable
                        }
                        val result = VaultRotation.change(requireNotNull(files), vaultId, requireNotNull(metadata), oldMaster, newMaster,
                            requireNotNull(authenticated), port, bindingEnabled, onStage, guard)
                        completed = result
                        if (result is VaultRotationResult.NoCommit) restore()
                        else if (bindingEnabled != null && (result == VaultRotationResult.Rotated || result is VaultRotationResult.Residual)) {
                            // 数据秘密不变，已发布的新描述须重新认证；保持原权限而不制造一次新解锁。
                            restoreGuard()
                            val selected = VaultLayout.resolve(vaultDirectory(vaultId), vaultId)
                            val saved = Metadata.read(selected.manifest, vaultId)
                            VaultDescriptorAuth.verify(requireNotNull(authenticated), saved, selected.selection)
                            val database = VaultDatabase.open(context, selected.database, requireNotNull(authenticated))
                            try { restoreGuard() } catch (failure: Exception) { database.close(); throw failure }
                            session = Session(vaultId, ticket, database, requireNotNull(authenticated),
                                VaultCleanupStatus(result == VaultRotationResult.Rotated, if (result is VaultRotationResult.Residual) result.paths else emptyList(),
                                    if (result is VaultRotationResult.Residual) result.categories else emptySet()))
                            transferred = true
                        }
                        result
                    } catch (failure: Exception) {
                        val published = completed
                        if (published != null && published !is VaultRotationResult.NoCommit) return@withLock published
                        restore()
                        VaultRotationResult.NoCommit(VaultRotation.reason(failure))
                    } finally {
                        if (!transferred) authenticated?.fill(0)
                        if (closed && !transferred) generation.compareAndSet(ticket, ticket + 1)
                    }
                }
            }
        }
    }

    internal suspend fun unlockBiometric(vaultId: String, authenticator: VaultBiometricAuthenticator,
                                          qualified: () -> Boolean): VaultInfo {
        val request = currentCoroutineContext()
        val ticket = generation.incrementAndGet()
        discardImport()
        return safely {
            try {
            withContext(NonCancellable) {
                withContext(Dispatchers.IO) {
                    mutex.withLock {
                        closeSession()
                        val guard = { request.ensureActive(); checkGeneration(ticket)
                            if (!runCatching(qualified).getOrDefault(false)) throw CancellationException("快捷解锁已取消。") }
                        guard()
                        val files = VaultLayout.resolve(vaultDirectory(vaultId), vaultId)
                        val metadata = Metadata.read(files.manifest, vaultId)
                        val envelope = metadata.biometric ?: throw VaultBiometricFailure()
                        if (!metadata.hasMasterPassword) throw VaultBiometricFailure()
                        val proof = VaultRotation.sourceProof(files, guard)
                        val key = VaultBiometric.decrypt(vaultId, files.selection.dataGroup, envelope, VaultBiometricPurpose.UNLOCK,
                            { cipher, purpose -> withContext(request) { authenticator(cipher, purpose) } }, guard)
                        var database: VaultDatabase? = null
                        var transferred = false
                        try {
                            VaultDescriptorAuth.verify(key, metadata, files.selection)
                            VaultRotation.verifySource(files, metadata, key, proof, guard)
                            val protectedUpgrade = VaultMigration.prepare(files, vaultId, null, key, guard)
                            database = VaultDatabase.open(context, files.database, key,
                                migrationGuard = if (protectedUpgrade) guard else null)
                            database.close()
                            database = null
                            val cleanup = VaultRotation.finishRecovery(files, vaultId, key, null, guard)
                            database = VaultDatabase.open(context, files.database, key)
                            val current = VaultLayout.resolve(files.root, vaultId)
                            if (current.selection != files.selection || !metadata.sameContent(Metadata.read(current.manifest, vaultId))) throw VaultException(VaultError.DATA_UNAVAILABLE)
                            guard()
                            session = Session(vaultId, ticket, database, key, cleanup)
                            transferred = true
                            metadata.info()
                        } finally { if (!transferred) { try { database?.close() } finally { key.fill(0) } } }
                    }
                }
            }
            } catch (failure: CancellationException) {
                closeCancelledSession(vaultId, ticket)
                throw failure
            }
        }
    }

    suspend fun renameVault(newName: String, currentMaster: String): VaultInfo {
        val requestContext = currentCoroutineContext()
        return withSession { current ->
            val name = newName.trim()
            if (name.isBlank()) throw VaultException(VaultError.INVALID_INPUT)
            validatedUtf8(name, 256).fill(0)
            val files = VaultLayout.resolve(vaultDirectory(current.id), current.id)
            val file = files.manifest
            val metadata = Metadata.read(file, current.id)
            if (name == metadata.name) return@withSession metadata.info()
            if (listVaultsLocked().any { it.id != current.id && it.name == name }) {
                throw VaultException(VaultError.DUPLICATE_NAME)
            }
            val unlockedKey = metadata.unlock(currentMaster, files.selection)
            try {
                if (!MessageDigest.isEqual(unlockedKey, current.key)) throw VaultException(VaultError.DATA_UNAVAILABLE)
                val renamed = Metadata.create(current.id, name, currentMaster, current.key, metadata.selection, metadata.biometric)
                val verifiedKey = renamed.unlock(currentMaster, files.selection)
                try {
                    if (!MessageDigest.isEqual(verifiedKey, current.key)) throw VaultException(VaultError.STORAGE_FAILED)
                } finally { verifiedKey.fill(0) }
                requestContext.ensureActive()
                checkGeneration(current.generation)
                renamed.write(file) {
                    requestContext.ensureActive()
                    checkGeneration(current.generation)
                }
                renamed.info()
            } finally { unlockedKey.fill(0) }
        }
    }

    suspend fun createVault(name: String, masterPassword: String): VaultInfo {
        val ticket = generation.get()
        val id = UUID.randomUUID().toString()
        return safely {
            try {
                withContext(Dispatchers.IO) {
                    mutex.withLock {
                        checkGeneration(ticket)
                        val displayName = name.trim()
                        if (displayName.isBlank()) throw VaultException(VaultError.INVALID_INPUT)
                        validatedUtf8(displayName, 256).fill(0)
                        validatedUtf8(masterPassword, 1024).fill(0)
                        if (listVaultsLocked().any { it.name == displayName }) {
                            throw VaultException(VaultError.DUPLICATE_NAME)
                        }
                        if (!root.isDirectory && !root.mkdirs()) throw VaultException(VaultError.STORAGE_FAILED)
                        val pending = childDirectory(".pending_$id")
                        if (!pending.mkdir()) throw VaultException(VaultError.STORAGE_FAILED)
                        val key = VaultCrypto.randomBytes(VaultCrypto.KEY_BYTES)
                        var database: VaultDatabase? = null
                        var transferred = false
                        try {
                            val metadata = Metadata.create(id, displayName, masterPassword, key)
                            database = VaultDatabase.open(context, File(pending, DATABASE_FILE), key, create = true)
                            database.close()
                            database = null
                            metadata.write(File(pending, MANIFEST_FILE))
                            syncDirectory(pending)
                            currentCoroutineContext().ensureActive()
                            checkGeneration(ticket)
                            val destination = vaultDirectory(id)
                            if (destination.exists() || !pending.renameTo(destination)) {
                                throw VaultException(VaultError.STORAGE_FAILED)
                            }
                            syncDirectory(root)
                            // 发布后即为完整库；此后失败或撤权保留文件，下一次可重新解锁。
                            database = VaultDatabase.open(context, File(destination, DATABASE_FILE), key)
                            currentCoroutineContext().ensureActive()
                            if (!generation.compareAndSet(ticket, ticket + 1)) throw VaultException(VaultError.SESSION_CLOSED)
                            closeSession()
                            session = Session(id, ticket + 1, database, key)
                            transferred = true
                            metadata.info()
                        } finally {
                            if (!transferred) {
                                try { database?.close() } finally { key.fill(0) }
                            }
                            removePending(pending)
                        }
                    }
                }
            } catch (failure: CancellationException) {
                closeCancelledSession(id, ticket + 1)
                throw failure
            }
        }
    }

    suspend fun unlock(vaultId: String, masterPassword: String): VaultInfo {
        val ticket = generation.incrementAndGet()
        discardImport()
        return safely {
            try {
                withContext(Dispatchers.IO) {
                    mutex.withLock {
                        checkGeneration(ticket)
                        closeSession()
                        validatedUtf8(masterPassword, 1024).fill(0)
                        val directory = vaultDirectory(vaultId)
                        val files = VaultLayout.resolve(directory, vaultId)
                        val metadata = Metadata.read(files.manifest, vaultId)
                        val key = metadata.unlock(masterPassword, files.selection)
                        var database: VaultDatabase? = null
                        var transferred = false
                        try {
                            val request = currentCoroutineContext()
                            val guard = { request.ensureActive(); checkGeneration(ticket) }
                            val protectedUpgrade = VaultMigration.prepare(files, vaultId, masterPassword, key, guard)
                            database = VaultDatabase.open(context, files.database, key,
                                migrationGuard = if (protectedUpgrade) guard else null)
                            // 升级连接先关闭，再核验完整当前库及认证恢复配套；清理失败保可用库。
                            database.close()
                            database = null
                            val cleanup = VaultRotation.finishRecovery(files, vaultId, key, masterPassword, guard)
                            database = VaultDatabase.open(context, files.database, key)
                            val currentFiles = VaultLayout.resolve(directory, vaultId)
                            val currentMetadata = Metadata.read(currentFiles.manifest, vaultId)
                            if (currentFiles.selection != files.selection || !metadata.sameContent(currentMetadata)) {
                                throw VaultException(VaultError.DATA_UNAVAILABLE)
                            }
                            currentCoroutineContext().ensureActive()
                            checkGeneration(ticket)
                            session = Session(vaultId, ticket, database, key, cleanup)
                            transferred = true
                            metadata.info()
                        } finally {
                            if (!transferred) {
                                try { database?.close() } finally { key.fill(0) }
                            }
                        }
                    }
                }
            } catch (failure: CancellationException) {
                // 取消可能发生在切库操作进入互斥区之前，此时旧会话也已被撤权。
                withContext(NonCancellable + Dispatchers.IO) {
                    mutex.withLock {
                        if (session?.generation?.let { it <= ticket } == true) {
                            generation.compareAndSet(ticket, ticket + 1)
                            closeSession()
                        }
                    }
                }
                throw failure
            }
        }
    }

    suspend fun listPasswords(): List<PasswordSummary> = withSession { current ->
        passwordSummaries(current)
    }

    suspend fun searchPasswords(query: String): List<PasswordSummary> {
        val request = currentCoroutineContext()
        return withSession { current ->
            validatedUtf8(query, 128).fill(0)
            val term = query.trim().lowercase(Locale.ROOT)
            if (term.isEmpty()) return@withSession passwordSummaries(current)
            val matches = mutableSetOf<String>()
            current.database.passwords().searchValues().use { rows ->
                while (rows.moveToNext()) {
                    request.ensureActive()
                    checkGeneration(current.generation)
                    if (rows.getString(1).lowercase(Locale.ROOT).contains(term) || rows.getString(2).lowercase(Locale.ROOT).contains(term)) matches.add(rows.getString(0))
                }
            }
            passwordSummaries(current, matches)
        }
    }

    suspend fun readPassword(id: String): PasswordRecord = withSession { current ->
        passwordRecord(current, id)
    }

    suspend fun recordOrder(byName: Boolean = false): List<Pair<String, Boolean>> {
        val request = currentCoroutineContext()
        return withSession { current ->
            val values = mutableListOf<OrderValue>()
            fun readRows(rows: android.database.Cursor, isNote: Boolean) = rows.use {
                while (it.moveToNext()) {
                    request.ensureActive()
                    checkGeneration(current.generation)
                    values.add(OrderValue(it.getString(0), isNote, it.getString(1), if (byName) 0L else BackupProtocol.timestampOrder(it.getString(2))))
                }
            }
            readRows(current.database.passwords().orderValues(), false)
            readRows(current.database.notes().orderValues(), true)
            val collator = Collator.getInstance(Locale.SIMPLIFIED_CHINESE)
            values.sortedWith { a, b ->
                request.ensureActive()
                val primary = if (byName) collator.compare(a.title, b.title) else b.time.compareTo(a.time)
                if (primary != 0) primary else a.id.compareTo(b.id).let { if (it != 0) it else a.isNote.compareTo(b.isNote) }
            }.map { it.id to it.isNote }
        }
    }

    private data class OrderValue(val id: String, val isNote: Boolean, val title: String, val time: Long)

    suspend fun addPassword(draft: PasswordDraft, totpSecret: String? = null, recoveryCodes: List<RecoveryCode>? = null): PasswordRecord {
        val replacement = replacementCodes(recoveryCodes)
        return withSession { current ->
            validateDraft(draft)
            val now = utcNow()
            val record = PasswordRecord(
                UUID.randomUUID().toString(), draft.title, draft.account, draft.password, draft.notes,
                now, favorite = draft.favorite, createdAt = now, passwordChangedAt = now,
                totpSecret = replacementTotp(totpSecret) ?: "", recoveryCodesJson = replacement ?: "[]",
            )
            write(current) {
                checkPasswordData(record)
                if (current.database.passwords().nameExists(draft.title)) throw VaultException(VaultError.DUPLICATE_NAME)
                current.database.passwords().insert(record)
                record
            }
        }
    }

    suspend fun updatePassword(id: String, expectedRevision: Long, draft: PasswordDraft, totpSecret: String? = null, recoveryCodes: List<RecoveryCode>? = null): PasswordRecord {
        val replacement = replacementCodes(recoveryCodes)
        return withSession { current ->
            var strengthChanged = false
            write(current) {
                val previous = passwordRecord(current, id)
                checkRevision(previous.revision, expectedRevision)
                validateDraft(draft, previous)
                val dao = current.database.passwords()
                if (dao.nameExists(draft.title, id)) throw VaultException(VaultError.DUPLICATE_NAME)
                val newTotp = if (totpSecret == null || totpSecret == previous.totpSecret) previous.totpSecret else replacementTotp(totpSecret)!!
                val newCodes = replacement?.let {
                    if (checkedRecoveryCodes(it) == checkedRecoveryCodes(previous.recoveryCodesJson)) previous.recoveryCodesJson else it
                } ?: previous.recoveryCodesJson
                val contentChanged = previous.title != draft.title || previous.account != draft.account ||
                    previous.password != draft.password || previous.notes != draft.notes || previous.totpSecret != newTotp || previous.recoveryCodesJson != newCodes
                val updatedAt = if (contentChanged) utcNow() else previous.updatedAt
                strengthChanged = previous.password != draft.password || previous.title != draft.title || previous.account != draft.account
                val record = previous.copy(
                    title = draft.title, account = draft.account, password = draft.password, notes = draft.notes,
                    favorite = draft.favorite, updatedAt = updatedAt,
                    passwordChangedAt = if (previous.password != draft.password) updatedAt else previous.passwordChangedAt,
                    totpSecret = newTotp, recoveryCodesJson = newCodes,
                    strength = if (strengthChanged) null else previous.strength,
                    strengthScheme = if (strengthChanged) null else previous.strengthScheme,
                )
                if (record == previous) previous else record.copy(revision = Math.addExact(previous.revision, 1L)).also {
                    if (dao.update(it) != 1) throw VaultException(VaultError.REVISION_CONFLICT)
                }
            }.also { if (strengthChanged) current.invalidateStrength(id) }
        }
    }

    suspend fun readTotpCode(vaultId: String, id: String, expectedRevision: Long): TotpCodeResult? = withSession { current ->
        checkVault(current, vaultId)
        val record = passwordRecord(current, id)
        checkRevision(record.revision, expectedRevision)
        if (record.totpSecret.isEmpty()) null else {
            val now = System.currentTimeMillis() / 1000
            TotpCodeResult(generateStoredTotp(record.totpSecret, now), now + totpRemainingSeconds(now))
        }
    }

    suspend fun readRecoveryCode(vaultId: String, id: String, expectedRevision: Long, index: Int): String = withSession { current ->
        checkVault(current, vaultId)
        val record = passwordRecord(current, id)
        checkRevision(record.revision, expectedRevision)
        val codes = checkedRecoveryCodes(record.recoveryCodesJson)
        if (index !in codes.indices) throw VaultException(VaultError.INVALID_INPUT)
        codes[index].value
    }

    suspend fun setRecoveryCodeUsed(vaultId: String, id: String, expectedRevision: Long, index: Int, used: Boolean): PasswordRecord = withSession { current ->
        checkVault(current, vaultId)
        write(current) {
            val record = passwordRecord(current, id)
            checkRevision(record.revision, expectedRevision)
            val codes = checkedRecoveryCodes(record.recoveryCodesJson).toMutableList()
            if (index !in codes.indices) throw VaultException(VaultError.INVALID_INPUT)
            if (codes[index].used == used) record else {
                codes[index] = codes[index].copy(used = used)
                record.copy(recoveryCodesJson = encodeRecoveryCodes(codes), updatedAt = utcNow(), revision = Math.addExact(record.revision, 1L)).also {
                    if (current.database.passwords().update(it) != 1) throw VaultException(VaultError.REVISION_CONFLICT)
                }
            }
        }
    }

    suspend fun deletePassword(id: String, expectedRevision: Long): Unit = withSession { current ->
        write(current) {
            val record = passwordRecord(current, id)
            checkRevision(record.revision, expectedRevision)
            if (current.database.passwords().delete(id, expectedRevision) != 1) throw VaultException(VaultError.REVISION_CONFLICT)
        }
    }

    suspend fun setPasswordFavorite(id: String, expectedRevision: Long, favorite: Boolean): PasswordRecord = withSession { current ->
        write(current) {
            val record = passwordRecord(current, id)
            checkRevision(record.revision, expectedRevision)
            if (record.favorite == favorite) record else record.copy(favorite = favorite, revision = Math.addExact(record.revision, 1L)).also {
                if (current.database.passwords().update(it) != 1) throw VaultException(VaultError.REVISION_CONFLICT)
            }
        }
    }

    suspend fun listNotes(): List<NoteSummary> = withSession { current ->
        current.database.notes().list().map { it.copy(preview = it.preview.substringBefore('\r')) }
    }

    suspend fun searchNotes(query: String): List<NoteSummary> {
        val request = currentCoroutineContext()
        return withSession { current ->
            validatedUtf8(query, 128).fill(0)
            val term = query.trim().lowercase(Locale.ROOT)
            current.database.notes().list().filter { summary ->
                request.ensureActive()
                checkGeneration(current.generation)
                term.isEmpty() || noteRecord(current, summary.id).let { note ->
                    note.title.lowercase(Locale.ROOT).contains(term) || note.content.lowercase(Locale.ROOT).contains(term)
                }
            }.map { it.copy(preview = it.preview.substringBefore('\r')) }
        }
    }

    suspend fun passwordChecks(): PasswordChecks = withSession { current ->
        val dao = current.database.passwords()
        PasswordChecks(dao.checkedCount(), dao.weakIds(BuildConfig.STRENGTH_SCHEME).toSet(), dao.repeatedIds().toSet(),
            dao.pendingStrengthIds(BuildConfig.STRENGTH_SCHEME).associateWith { current.strengthEpochs[it] ?: 0L }, current.dataRevision)
    }

    internal suspend fun strengthSnapshot(id: String): PasswordStrengthSnapshot? = withSession { current ->
        requireId(id)
        current.database.passwords().read(id)?.takeIf { it.password.isNotEmpty() &&
            (it.strengthScheme != BuildConfig.STRENGTH_SCHEME || it.strength !in setOf("weak", "fair", "strong")) }?.let {
            PasswordStrengthSnapshot(current.id, current.generation, id, current.strengthEpochs[id] ?: 0L, it.title, it.account, it.password)
        }
    }

    internal suspend fun commitStrength(snapshot: PasswordStrengthSnapshot, level: String, qualified: () -> Boolean): Boolean = withSession { current ->
        require(level in setOf("weak", "fair", "strong"))
        if (current.id != snapshot.vaultId || current.generation != snapshot.session || !qualified()) return@withSession false
        write(current) {
            val row = current.database.passwords().read(snapshot.id)
            if (row == null || row.password != snapshot.password || row.title != snapshot.title || row.account != snapshot.account ||
                (current.strengthEpochs[snapshot.id] ?: 0L) != snapshot.epoch || !qualified()) false
            else {
                val changed = current.database.passwords().writeStrength(snapshot.id, level, BuildConfig.STRENGTH_SCHEME) == 1
                if (!qualified()) throw CancellationException("评分资格已撤销")
                changed
            }
        }
    }

    suspend fun readNote(id: String): NoteRecord = withSession { current -> noteRecord(current, id) }

    suspend fun addNote(draft: NoteDraft): NoteRecord = withSession { current ->
        validateDraft(draft)
        val now = utcNow()
        write(current) {
            val last = current.database.notes().lastSortOrder() ?: -1
            if (last == Int.MAX_VALUE) throw VaultException(VaultError.STORAGE_FAILED)
            val record = NoteRecord(UUID.randomUUID().toString(), draft.title, draft.content, now, now, draft.favorite, sortOrder = last + 1)
            current.database.notes().insert(record)
            record
        }
    }

    suspend fun updateNote(id: String, expectedRevision: Long, draft: NoteDraft): NoteRecord = withSession { current ->
        write(current) {
            val previous = noteRecord(current, id)
            checkRevision(previous.revision, expectedRevision)
            validateDraft(draft, previous)
            val record = previous.copy(
                title = draft.title, content = draft.content, favorite = draft.favorite,
                updatedAt = if (previous.title != draft.title || previous.content != draft.content) utcNow() else previous.updatedAt,
            )
            if (record == previous) previous else record.copy(revision = Math.addExact(previous.revision, 1L)).also {
                if (current.database.notes().update(it) != 1) throw VaultException(VaultError.REVISION_CONFLICT)
            }
        }
    }

    suspend fun deleteNote(id: String, expectedRevision: Long): Unit = withSession { current ->
        write(current) {
            val record = noteRecord(current, id)
            checkRevision(record.revision, expectedRevision)
            if (current.database.notes().delete(id, expectedRevision) != 1) throw VaultException(VaultError.REVISION_CONFLICT)
        }
    }

    suspend fun setNoteFavorite(id: String, expectedRevision: Long, favorite: Boolean): NoteRecord = withSession { current ->
        write(current) {
            val record = noteRecord(current, id)
            checkRevision(record.revision, expectedRevision)
            if (record.favorite == favorite) record else record.copy(favorite = favorite, revision = Math.addExact(record.revision, 1L)).also {
                if (current.database.notes().update(it) != 1) throw VaultException(VaultError.REVISION_CONFLICT)
            }
        }
    }

    private fun passwordRecord(current: Session, id: String): PasswordRecord {
        requireId(id)
        return (current.database.passwords().read(id) ?: throw VaultException(VaultError.RECORD_MISSING)).also(::checkPasswordData)
    }

    private fun passwordSummaries(current: Session, matches: Set<String>? = null): List<PasswordSummary> {
        val dao = current.database.passwords()
        return dao.list().filter { matches == null || it.id in matches }.map { summary ->
            checkGeneration(current.generation)
            val json = dao.recoveryJson(summary.id) ?: throw VaultException(VaultError.DATA_UNAVAILABLE)
            summary.copy(recoveryCodeCount = checkedRecoveryCodes(json).size)
        }
    }

    private fun checkPasswordData(record: PasswordRecord) {
        if (record.strength != null && record.strength !in setOf("weak", "fair", "strong")) throw VaultException(VaultError.DATA_UNAVAILABLE)
        checkedRecoveryCodes(record.recoveryCodesJson)
    }

    private fun checkVault(current: Session, id: String) {
        requireId(id)
        if (current.id != id) throw VaultException(VaultError.SESSION_CLOSED)
    }

    private fun replacementTotp(value: String?): String? = when (value) {
        null -> null
        "" -> ""
        else -> try { normalizeTotpSecret(value) } catch (_: IllegalArgumentException) { throw VaultException(VaultError.INVALID_TOTP) }
    }

    private fun replacementCodes(value: List<RecoveryCode>?): String? = value?.let {
        try { encodeRecoveryCodes(validateRecoveryCodes(it).map { code -> code.copy(used = false) }) }
        catch (_: RecoveryCodeException) { throw VaultException(VaultError.INVALID_RECOVERY_CODES) }
    }

    private fun noteRecord(current: Session, id: String): NoteRecord {
        requireId(id)
        return current.database.notes().read(id) ?: throw VaultException(VaultError.RECORD_MISSING)
    }

    private fun checkRevision(actual: Long, expected: Long) {
        if (expected < 1) throw VaultException(VaultError.INVALID_INPUT)
        if (actual != expected) throw VaultException(VaultError.REVISION_CONFLICT)
    }

    private fun <T> write(current: Session, action: () -> T): T = current.database.runInTransaction(Callable {
        checkGeneration(current.generation)
        val result = action()
        // 撤权后的写入回滚；事务结束后的旧结果仍由会话边界拒绝。
        checkGeneration(current.generation)
        result
    }).also { current.dataRevision++ }

    private fun utcNow(): String = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss.SSS'Z'", Locale.ROOT)
        .apply { timeZone = TimeZone.getTimeZone("UTC") }.format(Date())

    private suspend fun <T> withSession(action: (Session) -> T): T {
        val ticket = generation.get()
        return safely {
            withContext(Dispatchers.IO) {
                mutex.withLock {
                    val current = session
                    if (current == null || current.generation != ticket) throw VaultException(VaultError.SESSION_CLOSED)
                    checkGeneration(ticket)
                    val result = action(current)
                    checkGeneration(ticket)
                    result
                }
            }
        }
    }

    private fun checkGeneration(ticket: Long) {
        if (generation.get() != ticket) throw VaultException(VaultError.SESSION_CLOSED)
    }

    private fun closeSession() {
        discardImport()
        val current = session ?: return
        session = null
        try { current.database.close() } finally { current.key.fill(0) }
    }

    private suspend fun closeCancelledSession(id: String, ticket: Long) {
        withContext(NonCancellable + Dispatchers.IO) {
            mutex.withLock {
                val current = session
                if (current != null && current.id == id && current.generation == ticket) {
                    generation.compareAndSet(current.generation, current.generation + 1)
                    closeSession()
                }
            }
        }
    }

    private fun listVaultsLocked(): List<VaultInfo> {
        if (!root.exists()) return emptyList()
        val directories = root.listFiles() ?: throw VaultException(VaultError.STORAGE_FAILED)
        return directories.filter { validId(it.name) }.map { directory ->
            try {
                val safeDirectory = vaultDirectory(directory.name)
                val files = VaultLayout.resolve(safeDirectory, directory.name)
                Metadata.read(files.manifest, directory.name).info()
            } catch (_: Exception) {
                VaultInfo(directory.name, "无法读取的密码库", hasMasterPassword = true, available = false)
            }
        }.sortedWith(compareBy<VaultInfo> { it.name }.thenBy { it.id })
    }

    private fun childDirectory(name: String): File {
        val file = File(root, name)
        if (file.canonicalFile != file.absoluteFile || root.canonicalFile != root.absoluteFile) {
            throw VaultException(VaultError.DATA_UNAVAILABLE)
        }
        return file
    }

    private fun vaultDirectory(id: String): File {
        requireId(id)
        return childDirectory(id)
    }

    private fun removePending(directory: File) {
        if (!directory.exists() || directory.canonicalFile != directory.absoluteFile || directory.parentFile != root) return
        // 仅清理由本次调用创建的未发布目录；不递归跟随链接，也不触碰已发布库。
        directory.listFiles()?.forEach { file ->
            if (file.isFile && file.canonicalFile == file.absoluteFile) file.delete()
        }
        directory.delete()
    }

    private suspend fun <T> safely(action: suspend () -> T): T = try {
        action()
    } catch (failure: CancellationException) {
        throw failure
    } catch (failure: VaultException) {
        throw failure
    } catch (_: VaultBiometricFailure) {
        throw VaultException(VaultError.BIOMETRIC_UNAVAILABLE)
    } catch (failure: BackupStoreException) {
        throw failure
    } catch (failure: BackupProtocolException) {
        throw failure
    } catch (failure: BackupDocumentException) {
        throw failure
    } catch (_: Exception) {
        // 第三方异常可能包含SQL及参数；只向界面返回固定原因。
        throw VaultException(VaultError.STORAGE_FAILED)
    }

    companion object {
        internal const val MANIFEST_FILE = "manifest.json"
        internal const val DATABASE_FILE = "vault.db"
        private fun validId(value: String): Boolean = runCatching { UUID.fromString(value).toString() == value }.getOrDefault(false)
        private fun requireId(value: String) {
            if (!validId(value)) throw VaultException(VaultError.DATA_UNAVAILABLE)
        }
    }
}

internal fun generateStoredTotp(secret: String, epochSeconds: Long): String = try {
    // Windows读取历史值会移除全部填充符；不改变原值，也不移除其他无效字符。
    generateTotp(secret.replace("=", ""), epochSeconds)
} catch (_: IllegalArgumentException) { throw VaultException(VaultError.INVALID_TOTP) }

internal fun syncDirectory(directory: File) {
    if (!directory.isDirectory || directory.canonicalFile != directory.absoluteFile) {
        throw VaultException(VaultError.DATA_UNAVAILABLE)
    }
    val descriptor = Os.open(directory.absolutePath, OsConstants.O_RDONLY, 0)
    try { Os.fsync(descriptor) } finally { Os.close(descriptor) }
}

internal class Metadata(
    val id: String,
    val name: String,
    val hasMasterPassword: Boolean,
    val salt: ByteArray,
    val nonce: ByteArray,
    var wrappedKey: ByteArray,
    val version: Int = 1,
    val selection: VaultLayoutSelection? = null,
    val biometric: VaultBiometricEnvelope? = null,
    var descriptorMac: ByteArray = byteArrayOf(),
) {
    fun info() = VaultInfo(id, name, hasMasterPassword, biometricEnabled = biometric != null)

    fun rebind(next: VaultLayoutSelection, key: ByteArray, bio: VaultBiometricEnvelope?): Metadata {
        require(version == 2)
        return Metadata(id, name, hasMasterPassword, salt.copyOf(), nonce.copyOf(), wrappedKey.copyOf(), 2, next, bio).also {
            it.descriptorMac = VaultDescriptorAuth.descriptor(key, it)
        }
    }

    fun sameContent(other: Metadata): Boolean = id == other.id && name == other.name && version == other.version &&
        hasMasterPassword == other.hasMasterPassword && selection == other.selection && salt.contentEquals(other.salt) &&
        nonce.contentEquals(other.nonce) && wrappedKey.contentEquals(other.wrappedKey) && descriptorMac.contentEquals(other.descriptorMac) &&
        ((biometric == null && other.biometric == null) || (biometric != null && other.biometric != null &&
            biometric.version == other.biometric.version && biometric.alias == other.biometric.alias &&
            biometric.nonce.contentEquals(other.biometric.nonce) && biometric.wrappedKey.contentEquals(other.biometric.wrappedKey)))

    private fun aad(): ByteArray = ByteArrayOutputStream().use { bytes ->
        DataOutputStream(bytes).use { out ->
            listOf("cangoo-android-vault", id, name, "argon2id").forEach { value ->
                val encoded = value.toByteArray(Charsets.UTF_8)
                out.writeInt(encoded.size)
                out.write(encoded)
            }
            out.writeInt(version)
            out.writeBoolean(hasMasterPassword)
            listOf(19, VaultCrypto.MEMORY_KIB, VaultCrypto.ITERATIONS, VaultCrypto.PARALLELISM, VaultCrypto.KEY_BYTES)
                .forEach(out::writeInt)
            out.write(salt)
        }
        bytes.toByteArray()
    }

    fun unlock(password: String, selected: VaultLayoutSelection? = null): ByteArray {
        val masterKey = VaultCrypto.deriveKey(password, salt)
        return try {
            VaultCrypto.unwrap(masterKey, nonce, wrappedKey, aad()).also { key ->
                try {
                    if (key.size != VaultCrypto.KEY_BYTES || password.isNotEmpty() != hasMasterPassword) {
                        throw VaultException(VaultError.DATA_UNAVAILABLE)
                    }
                    if (version == 2 || selected != null) VaultDescriptorAuth.verify(key, this, requireNotNull(selected))
                } catch (failure: Exception) {
                    key.fill(0)
                    throw failure
                }
            }
        } catch (_: AEADBadTagException) {
            throw VaultException(VaultError.AUTHENTICATION_FAILED)
        } finally {
            masterKey.fill(0)
        }
    }

    fun write(file: File, beforeCommit: () -> Unit = {}) {
        checkFiles(file)
        val json = JSONObject().put("version", version).put("id", id).put("name", name)
            .put("has_master_password", hasMasterPassword)
            .put("kdf", JSONObject().put("name", "argon2id").put("version", 19)
                .put("memory_kib", VaultCrypto.MEMORY_KIB).put("iterations", VaultCrypto.ITERATIONS)
                .put("parallelism", VaultCrypto.PARALLELISM).put("key_bytes", VaultCrypto.KEY_BYTES))
            .put("salt", encode(salt)).put("nonce", encode(nonce)).put("wrapped_key", encode(wrappedKey))
        if (version == 2) {
            val selected = requireNotNull(selection)
            json.put("data_group", selected.dataGroup).put("descriptor_group", selected.descriptorGroup)
                .put("biometric", biometric?.let { bio -> JSONObject().put("version", bio.version).put("alias", bio.alias)
                    .put("nonce", encode(bio.nonce)).put("wrapped_key", encode(bio.wrappedKey)) } ?: JSONObject.NULL)
                .put("descriptor_mac", encode(descriptorMac))
        }
        val atomic = AtomicFile(file)
        val output = atomic.startWrite()
        var commitStarted = false
        try {
            output.write(json.toString().toByteArray(Charsets.UTF_8))
            // 系统finishWrite只记录部分I/O失败；先显式同步，再核实实际提交结果。
            output.fd.sync()
            checkFiles(file)
            beforeCommit()
            commitStarted = true
            atomic.finishWrite(output)
            val saved = read(file, id)
            check(sameContent(saved))
            syncDirectory(file.parentFile!!)
        } catch (failure: Exception) {
            // 已进入原子提交边界，不能再以failWrite冒充回滚到原名。
            if (commitStarted) throw VaultException(VaultError.COMMIT_UNCERTAIN)
            atomic.failWrite(output)
            throw failure
        }
    }

    companion object {
        fun create(id: String, name: String, password: String, key: ByteArray,
                   selection: VaultLayoutSelection? = null, biometric: VaultBiometricEnvelope? = null): Metadata {
            require(VaultDescriptorAuth.validUuid(id) && (selection == null ||
                VaultDescriptorAuth.validGroup(selection.dataGroup) && VaultDescriptorAuth.validUuid(selection.descriptorGroup)))
            require(biometric == null || selection != null && password.isNotEmpty())
            val metadata = Metadata(id, name, password.isNotEmpty(), VaultCrypto.randomBytes(16), VaultCrypto.randomBytes(12), byteArrayOf(),
                if (selection == null) 1 else 2, selection, biometric)
            val masterKey = VaultCrypto.deriveKey(password, metadata.salt)
            try {
                metadata.wrappedKey = VaultCrypto.wrap(masterKey, metadata.nonce, key, metadata.aad())
                if (selection != null) metadata.descriptorMac = VaultDescriptorAuth.descriptor(key, metadata)
                return metadata
            } finally {
                masterKey.fill(0)
            }
        }

        fun read(file: File, id: String): Metadata = try {
            checkFiles(file)
            val bytes = ByteArray(16385)
            val count = AtomicFile(file).openRead().use { input ->
                checkFiles(file)
                require(file.isFile && !File(file.path + ".bak").exists() && !File(file.path + ".new").exists())
                var size = 0
                while (size < bytes.size) {
                    val read = input.read(bytes, size, bytes.size - size)
                    if (read < 0) break
                    size += read
                }
                size
            }
            val json = try {
                require(count in 1..16384)
                VaultDescriptorAuth.readJson(bytes.decodeToString(0, count, throwOnInvalidSequence = true))
            } finally { bytes.fill(0) }
            val version = json.get("version") as Int
            require(version in 1..2 && VaultDescriptorAuth.validUuid(id) && json.get("id") == id)
            val fields = setOf("version", "id", "name", "has_master_password", "kdf", "salt", "nonce", "wrapped_key")
            require(json.keys().asSequence().toSet() == if (version == 1) fields else fields + setOf("data_group", "descriptor_group", "biometric", "descriptor_mac"))
            val name = json.get("name") as String
            require(name.isNotBlank() && name == name.trim())
            validatedUtf8(name, 256).fill(0)
            val kdf = json.getJSONObject("kdf")
            require(kdf.keys().asSequence().toSet() == setOf("name", "version", "memory_kib", "iterations", "parallelism", "key_bytes"))
            require(kdf.get("name") == "argon2id" && kdf.get("version") == 19 && kdf.get("memory_kib") == VaultCrypto.MEMORY_KIB)
            require(kdf.get("iterations") == VaultCrypto.ITERATIONS && kdf.get("parallelism") == VaultCrypto.PARALLELISM && kdf.get("key_bytes") == 32)
            val selected = if (version == 2) VaultLayoutSelection(json.get("data_group") as String, json.get("descriptor_group") as String).also {
                require(VaultDescriptorAuth.validGroup(it.dataGroup) && VaultDescriptorAuth.validUuid(it.descriptorGroup))
            } else null
            val biometric = if (version == 2 && !json.isNull("biometric")) json.getJSONObject("biometric").let { bio ->
                require(bio.keys().asSequence().toSet() == setOf("version", "alias", "nonce", "wrapped_key"))
                require(bio.get("version") == 1 && VaultDescriptorAuth.validAlias(bio.get("alias") as String) && json.get("has_master_password") == true)
                VaultBiometricEnvelope(1, bio.get("alias") as String, decode(bio.get("nonce") as String, 12), decode(bio.get("wrapped_key") as String, 48))
            } else null
            Metadata(id, name, json.get("has_master_password") as Boolean,
                decode(json.get("salt") as String, 16), decode(json.get("nonce") as String, 12), decode(json.get("wrapped_key") as String, 48),
                version, selected, biometric, if (version == 2) decode(json.get("descriptor_mac") as String, 32) else byteArrayOf())
        } catch (_: Exception) {
            throw VaultException(VaultError.DATA_UNAVAILABLE)
        }

        private fun checkFiles(file: File) {
            val directory = file.parentFile ?: throw IllegalArgumentException()
            require(directory.isDirectory && directory.canonicalFile == directory.absoluteFile)
            listOf(file, File(file.path + ".bak"), File(file.path + ".new")).forEach { path ->
                require(!Files.isSymbolicLink(path.toPath()) && path.canonicalFile == path.absoluteFile)
                require(!path.exists() || path.isFile)
            }
        }

        private fun encode(bytes: ByteArray) = Base64.encodeToString(bytes, Base64.NO_WRAP)
        private fun decode(text: String, size: Int): ByteArray {
            val bytes = Base64.decode(text, Base64.NO_WRAP)
            require(bytes.size == size && encode(bytes) == text)
            return bytes
        }
    }
}
