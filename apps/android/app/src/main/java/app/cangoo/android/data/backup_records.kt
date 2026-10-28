package app.cangoo.android.data

import com.google.gson.stream.JsonWriter
import java.io.OutputStream
import java.io.OutputStreamWriter
import java.security.DigestOutputStream
import java.security.MessageDigest
import java.util.UUID

/** 备份记录映射与内容复核；会话、取消和事务始终由VaultStore持有。 */
internal object BackupRecords {
    fun export(database: VaultDatabase, scope: BackupScope, guard: () -> Unit, encryptedEnvelope: Boolean = true,
               memory: BackupMemoryBudget = BackupMemoryBudget()): BackupPayload {
        val passwords = mutableListOf<BackupPassword>()
        val notes = mutableListOf<BackupNote>()
        guard()
        val passwordCount = if (scope != BackupScope.NOTES) database.passwords().backupCount() else 0
        guard()
        val count = passwordCount + (if (scope != BackupScope.PASSWORDS) database.notes().backupCount() else 0)
        guard()
        if (count > BackupProtocol.MAX_RECORDS) failLimit()
        var lowerBytes = 128L
        fun budget(bytes: Long) {
            lowerBytes = Math.addExact(lowerBytes, bytes)
            // 原UTF-8与必要结构是JSON下界；文件算封装开销，直传只算业务字节。
            if ((if (encryptedEnvelope) ((lowerBytes + 28 + 2) / 3) * 4 else lowerBytes) > BackupProtocol.MAX_BYTES) failLimit()
        }
        if (scope != BackupScope.NOTES) eachId(database, BackupImportKind.PASSWORD, guard) { id ->
            val textBytes = database.passwords().backupTextBytes(id)
            budget(textBytes + 146)
            val allocation = textBytes + database.passwords().backupRecoveryBytes(id)
            memory.reserve(2 * allocation + BackupMemoryBudget.RECORD_BYTES + 128 * BackupMemoryBudget.RECOVERY_CODE_BYTES)
            val item = memory.temporary(4 * allocation) {
                guard()
                val record = database.passwords().read(id) ?: throw VaultException(VaultError.DATA_UNAVAILABLE)
                guard()
                val codes = checkedRecoveryCodes(record.recoveryCodesJson)
                codes.forEach { budget(utf8Bytes(it.value, guard) + 24) }
                BackupPassword(record.title, record.account, record.password, record.notes, record.totpSecret,
                    record.strength, record.passwordChangedAt?.let(BackupProtocol::exportTimestamp),
                    BackupProtocol.exportTimestamp(record.updatedAt), record.favorite, codes)
            }
            memory.release((128 - item.recoveryCodes.size) * BackupMemoryBudget.RECOVERY_CODE_BYTES)
            passwords.add(item)
        }
        if (scope != BackupScope.PASSWORDS) eachId(database, BackupImportKind.NOTE, guard) { id ->
            val bytes = database.notes().backupTextBytes(id)
            budget(bytes + 89)
            memory.reserve(2 * bytes + BackupMemoryBudget.RECORD_BYTES)
            notes.add(memory.temporary(4 * bytes) {
                guard()
                val record = database.notes().read(id) ?: throw VaultException(VaultError.DATA_UNAVAILABLE)
                guard()
                BackupNote(record.title, record.content, BackupProtocol.exportTimestamp(record.createdAt),
                    BackupProtocol.exportTimestamp(record.updatedAt), record.sortOrder, record.favorite)
            })
        }
        guard()
        return BackupPayload(BackupProtocol.exportTime(System.currentTimeMillis()), scope, passwords, notes)
    }

    fun snapshot(database: VaultDatabase, payload: BackupPayload, guard: () -> Unit): BackupTargetSnapshot {
        val memory = BackupMemoryBudget()
        memory.reserve((payload.passwords.size.toLong() + payload.notes.size) * BackupMemoryBudget.RECORD_BYTES)
        val names = payload.passwords.mapTo(mutableSetOf()) { it.platform }
        val passwordContents = payload.passwords.mapIndexed { index, source ->
            guard()
            source.platform to (index to passwordContent(source.platform, source.account, source.password, source.notes,
                source.totpSecret, source.recoveryCodes, source.favorite, guard))
        }.toMap()
        val noteContents = payload.notes.map { noteContent(it.title, it.content, it.favorite, guard) }
        val wantedNotes = noteContents.toSet()
        val identicalPasswords = mutableSetOf<Int>()
        val matchingNotes = mutableMapOf<String, String>()
        val noteKeys = payload.notes.map { guard(); memory.temporary(BackupMemoryBudget.textPeak(utf8Bytes(it.title, guard))) { similarNoteTitleKey(it.title) } }
        val groups = noteKeys.toSet().associateWith { mutableListOf<BackupNoteTarget>() }
        val passwords = mutableMapOf<String, BackupPasswordTarget>()
        if (names.isNotEmpty()) eachId(database, BackupImportKind.PASSWORD, guard) { id ->
            val title = title(database, BackupImportKind.PASSWORD, id, guard)
            if (title in names) {
                memory.reserve(BackupMemoryBudget.RECORD_BYTES)
                guard()
                memory.temporary(BackupMemoryBudget.textPeak(database.passwords().backupTextBytes(id) + database.passwords().backupRecoveryBytes(id)) +
                    128 * BackupMemoryBudget.RECOVERY_CODE_BYTES) {
                    val record = database.passwords().read(id) ?: throw VaultException(VaultError.DATA_UNAVAILABLE)
                    guard()
                    passwords[title] = BackupPasswordTarget(record.toSummary(), fingerprint(record, guard))
                    val (index, expected) = passwordContents.getValue(title)
                    if (passwordContent(record.title, record.account, record.password, record.notes, record.totpSecret,
                            checkedRecoveryCodes(record.recoveryCodesJson), record.favorite, guard) == expected) identicalPasswords.add(index)
                }
            }
        }
        if (groups.isNotEmpty()) eachId(database, BackupImportKind.NOTE, guard) { id ->
            val title = title(database, BackupImportKind.NOTE, id, guard)
            val key = memory.temporary(BackupMemoryBudget.textPeak(utf8Bytes(title, guard))) { similarNoteTitleKey(title) }
            groups[key]?.let { values ->
                memory.reserve(BackupMemoryBudget.RECORD_BYTES)
                guard()
                memory.temporary(BackupMemoryBudget.textPeak(database.notes().backupTextBytes(id))) {
                    val record = database.notes().read(id) ?: throw VaultException(VaultError.DATA_UNAVAILABLE)
                    guard()
                    values.add(BackupNoteTarget(record.toSummary(), fingerprint(record, guard)))
                    val content = noteContent(record.title, record.content, record.favorite, guard)
                    if (content in wantedNotes) matchingNotes[content] = minOf(matchingNotes[content] ?: record.id, record.id)
                }
            }
        }
        val identicalNotes = noteContents.mapIndexedNotNull { index, content -> matchingNotes[content]?.let { index to it } }.toMap()
        return BackupTargetSnapshot(passwords, groups, noteKeys, noteKeys.groupingBy { it }.eachCount(), identicalPasswords, identicalNotes)
    }

    fun validateDecisions(payload: BackupPayload, targets: BackupTargetSnapshot, decisions: BackupImportDecisions,
                          complete: Boolean, allowUnacknowledgedRecoveryRemoval: Boolean = false, guard: () -> Unit) {
        val requiredPasswords = payload.passwords.indices.filterTo(mutableSetOf()) { it !in targets.identicalPasswords && payload.passwords[it].platform in targets.passwords }
        val requiredNotes = payload.notes.indices.filterTo(mutableSetOf()) { requiredNote(targets, it) }
        if (!requiredPasswords.containsAll(decisions.passwords.keys) || !requiredNotes.containsAll(decisions.notes.keys) ||
            complete && (decisions.passwords.keys != requiredPasswords || decisions.notes.keys != requiredNotes)) failDecisions()
        decisions.passwords.forEach { (index, choice) ->
            guard()
            if (choice.action == PasswordImportAction.OVERWRITE && payload.version == 1 && clearsRecoveryCodes(payload, targets, index) &&
                !choice.acknowledgeRecoveryRemoval && !allowUnacknowledgedRecoveryRemoval) failDecisions()
        }
        val used = mutableSetOf<String>()
        decisions.notes.forEach { (index, choice) ->
            guard()
            if (choice.action == NoteImportAction.OVERWRITE) {
                if (choice.targetId == null || choice.targetId in targets.reservedNoteIds ||
                    targets.noteTargetsById[choice.targetId]?.first != targets.noteKeys[index] || !used.add(choice.targetId)) failDecisions()
            } else if (choice.targetId != null) failDecisions()
        }
        guard()
    }

    fun validateSelected(payload: BackupPayload, targets: BackupTargetSnapshot, kind: BackupImportKind, selected: Set<Int>, guard: () -> Unit) {
        selected.forEach { index ->
            guard()
            val required = when (kind) {
                BackupImportKind.PASSWORD -> index in payload.passwords.indices && index !in targets.identicalPasswords && payload.passwords[index].platform in targets.passwords
                BackupImportKind.NOTE -> index in payload.notes.indices && requiredNote(targets, index)
            }
            if (!required) throw BackupStoreException(BackupStoreProblem.INPUT)
        }
    }

    fun planSummary(previewId: String, payload: BackupPayload, targets: BackupTargetSnapshot, decisions: BackupImportDecisions,
                    allowUnacknowledgedRecoveryRemoval: Boolean = false, guard: () -> Unit): BackupImportPlanSummary {
        validateDecisions(payload, targets, decisions, false, allowUnacknowledgedRecoveryRemoval, guard)
        var imported = 0; var overwritten = 0; var skipped = 0; var pending = 0; var recoveryRemovals = 0
        payload.passwords.forEachIndexed { index, source ->
            guard()
            when {
                index in targets.identicalPasswords -> skipped++
                source.platform !in targets.passwords -> imported++
                decisions.passwords[index] == null -> pending++
                decisions.passwords.getValue(index).action == PasswordImportAction.SKIP -> skipped++
                else -> { overwritten++; if (clearsRecoveryCodes(payload, targets, index)) recoveryRemovals++ }
            }
        }
        payload.notes.indices.forEach { index ->
            guard()
            when {
                index in targets.identicalNotes -> skipped++
                !requiredNote(targets, index) -> imported++
                decisions.notes[index] == null -> pending++
                decisions.notes.getValue(index).action == NoteImportAction.KEEP_BOTH -> imported++
                decisions.notes.getValue(index).action == NoteImportAction.SKIP -> skipped++
                else -> overwritten++
            }
        }
        guard()
        return BackupImportPlanSummary(previewId, imported, overwritten, skipped, pending, recoveryRemovals)
    }

    fun batchProposal(previewId: String, payload: BackupPayload, targets: BackupTargetSnapshot, kind: BackupImportKind,
                      selected: Set<Int>, action: BackupImportBatchAction, decisions: BackupImportDecisions,
                      outsideFilter: Int, guard: () -> Unit): BackupImportBatchProposal {
        validateDecisions(payload, targets, decisions, false, guard = guard)
        validateSelected(payload, targets, kind, selected, guard)
        if (selected.isEmpty() || kind == BackupImportKind.PASSWORD && action == BackupImportBatchAction.KEEP_BOTH)
            throw BackupStoreException(BackupStoreProblem.INPUT)
        val passwords = decisions.passwords.toMutableMap()
        val notes = decisions.notes.toMutableMap()
        val applied = linkedSetOf<Int>()
        val deferred = linkedMapOf<Int, BackupImportBatchDeferredReason>()
        val legacy = linkedSetOf<Int>()
        val removals = linkedSetOf<Int>()
        if (kind == BackupImportKind.PASSWORD) selected.sorted().forEach { index ->
            guard()
            passwords[index] = PasswordImportChoice(if (action == BackupImportBatchAction.SKIP) PasswordImportAction.SKIP else PasswordImportAction.OVERWRITE)
            if (action == BackupImportBatchAction.OVERWRITE && clearsRecoveryCodes(payload, targets, index)) {
                removals.add(index)
                if (payload.version == 1) legacy.add(index)
            }
            applied.add(index)
        } else {
            if (action != BackupImportBatchAction.OVERWRITE) selected.sorted().forEach { index ->
                guard()
                notes[index] = NoteImportChoice(if (action == BackupImportBatchAction.SKIP) NoteImportAction.SKIP else NoteImportAction.KEEP_BOTH)
                applied.add(index)
            } else {
                val occupied = notes.filterKeys { it !in selected }.values.filter { it.action == NoteImportAction.OVERWRITE }.mapNotNullTo(mutableSetOf()) { it.targetId }
                // 同组共用候选集且目标不跨组；共同唯一目标全部延期，延期项保原决定。
                val available = selected.map { targets.noteKeys[it] }.toSet().associateWith { key ->
                    targets.notes.getValue(key).mapNotNullTo(mutableSetOf()) { target ->
                        guard(); target.summary.id.takeIf { it !in occupied && it !in targets.reservedNoteIds }
                    }
                }
                val proposed = linkedMapOf<Int, String>()
                selected.sorted().forEach { index ->
                    guard()
                    val key = targets.noteKeys[index]
                    if (targets.notes.getValue(key).size > 1) {
                        deferred[index] = BackupImportBatchDeferredReason.AMBIGUOUS_TARGET
                        return@forEach
                    }
                    val candidates = available.getValue(key)
                    val target = candidates.singleOrNull()
                    if (target != null) proposed[index] = target
                    else deferred[index] = if (candidates.isEmpty()) BackupImportBatchDeferredReason.NO_AVAILABLE_TARGET else BackupImportBatchDeferredReason.AMBIGUOUS_TARGET
                }
                val uses = proposed.values.groupingBy { it }.eachCount()
                proposed.forEach { (index, target) ->
                    guard()
                    if (uses.getValue(target) != 1) deferred[index] = BackupImportBatchDeferredReason.SHARED_TARGET
                    else { notes[index] = NoteImportChoice(NoteImportAction.OVERWRITE, target); applied.add(index) }
                }
            }
        }
        val draft = BackupImportDecisions(passwords.toMap(), notes.toMap())
        val summary = planSummary(previewId, payload, targets, draft, true, guard)
        guard()
        return BackupImportBatchProposal(previewId, kind, draft, applied, deferred, legacy, removals, outsideFilter, summary)
    }

    private fun clearsRecoveryCodes(payload: BackupPayload, targets: BackupTargetSnapshot, index: Int): Boolean =
        payload.passwords[index].recoveryCodes.isEmpty() && targets.passwords.getValue(payload.passwords[index].platform).summary.recoveryCodeCount > 0

    fun apply(database: VaultDatabase, payload: BackupPayload, targets: BackupTargetSnapshot,
              decisions: BackupImportDecisions, guard: () -> Unit): BackupImportResult {
        validateDecisions(payload, targets, decisions, true, guard = guard)
        var imported = 0
        var overwritten = 0
        var skipped = 0
        payload.passwords.forEachIndexed { index, source ->
            guard()
            if (index in targets.identicalPasswords) { skipped++; return@forEachIndexed }
            val target = targets.passwords[source.platform]
            if (target != null && decisions.passwords.getValue(index).action == PasswordImportAction.SKIP) { skipped++; return@forEachIndexed }
            val previous = target?.let { database.passwords().read(it.summary.id) ?: throw BackupStoreException(BackupStoreProblem.STALE) }
            val codes = if (previous != null && checkedRecoveryCodes(previous.recoveryCodesJson) == source.recoveryCodes) previous.recoveryCodesJson else encodeRecoveryCodes(source.recoveryCodes)
            var record = PasswordRecord(previous?.id ?: UUID.randomUUID().toString(), source.platform, source.account, source.password,
                source.notes, source.updatedAt, source.favorite, previous?.revision ?: 1, previous?.createdAt, source.passwordChangedAt,
                source.totpSecret, codes, source.strength)
            guard()
            if (previous == null) { database.passwords().insert(record); imported++ }
            else {
                if (fingerprint(previous, guard) != fingerprint(record, guard)) record = record.copy(revision = Math.addExact(previous.revision, 1L))
                if (record != previous && database.passwords().update(record) != 1) throw BackupStoreException(BackupStoreProblem.STALE)
                overwritten++
            }
            guard()
        }
        guard()
        val nextOrder = (database.notes().lastSortOrder()?.toLong() ?: -1L) + 1
        guard()
        val ordered = payload.notes.indices.sortedWith(compareBy<Int> { payload.notes[it].sortOrder }.thenBy { it })
        ordered.forEachIndexed { offset, index ->
            guard()
            if (index in targets.identicalNotes) { skipped++; return@forEachIndexed }
            val source = payload.notes[index]
            val choice = decisions.notes[index] ?: NoteImportChoice(NoteImportAction.KEEP_BOTH)
            if (choice.action == NoteImportAction.SKIP) { skipped++; return@forEachIndexed }
            val previous = choice.targetId?.let { database.notes().read(it) ?: throw BackupStoreException(BackupStoreProblem.STALE) }
            val order = previous?.sortOrder ?: (nextOrder + offset).also { if (it > Int.MAX_VALUE) failLimit() }.toInt()
            var record = NoteRecord(previous?.id ?: UUID.randomUUID().toString(), source.title, source.content, source.createdAt,
                source.updatedAt, source.favorite, previous?.revision ?: 1, order)
            guard()
            if (previous == null) { database.notes().insert(record); imported++ }
            else {
                if (fingerprint(previous, guard) != fingerprint(record, guard)) record = record.copy(revision = Math.addExact(previous.revision, 1L))
                if (record != previous && database.notes().update(record) != 1) throw BackupStoreException(BackupStoreProblem.STALE)
                overwritten++
            }
            guard()
        }
        guard()
        return BackupImportResult(imported, overwritten, skipped)
    }

    fun requiredNote(targets: BackupTargetSnapshot, index: Int): Boolean =
        index !in targets.identicalNotes && (targets.notes.getValue(targets.noteKeys[index]).isNotEmpty() || targets.noteSourceCounts.getValue(targets.noteKeys[index]) > 1)

    fun comparison(source: BackupPassword, current: PasswordRecord?, guard: () -> Unit): List<BackupComparisonFieldSummary> =
        passwordFields(source, current).map { guard(); it.summary() }.also { guard() }

    fun comparison(source: BackupNote, current: NoteRecord?, guard: () -> Unit): List<BackupComparisonFieldSummary> =
        noteFields(source, current).map { guard(); it.summary() }.also { guard() }

    fun isBusinessField(kind: BackupImportKind, field: BackupComparisonField): Boolean = field in when (kind) {
        BackupImportKind.PASSWORD -> setOf(BackupComparisonField.TITLE, BackupComparisonField.ACCOUNT, BackupComparisonField.PASSWORD,
            BackupComparisonField.NOTES, BackupComparisonField.TOTP_SECRET, BackupComparisonField.RECOVERY_CODES, BackupComparisonField.FAVORITE)
        BackupImportKind.NOTE -> setOf(BackupComparisonField.TITLE, BackupComparisonField.NOTES, BackupComparisonField.FAVORITE)
    }

    fun businessChanges(source: BackupPassword, current: PasswordRecord, guard: () -> Unit): Set<BackupComparisonField> =
        passwordFields(source, current).filter { guard(); isBusinessField(BackupImportKind.PASSWORD, it.field) && it.changed() }.mapTo(linkedSetOf()) { it.field }

    fun businessChanges(source: BackupNote, current: NoteRecord, guard: () -> Unit): Set<BackupComparisonField> =
        noteFields(source, current).filter { guard(); isBusinessField(BackupImportKind.NOTE, it.field) && it.changed() }.mapTo(linkedSetOf()) { it.field }

    fun fieldPair(source: BackupPassword, current: PasswordRecord?, field: BackupComparisonField,
                  offset: Int, limit: Int, guard: () -> Unit): Pair<BackupImportFieldValue, BackupImportFieldValue?> =
        fieldPair(passwordFields(source, current), field, offset, limit, guard)

    fun fieldPair(source: BackupNote, current: NoteRecord?, field: BackupComparisonField,
                  offset: Int, limit: Int, guard: () -> Unit): Pair<BackupImportFieldValue, BackupImportFieldValue?> =
        fieldPair(noteFields(source, current), field, offset, limit, guard)

    private class ComparedValue(val text: String? = null, val codes: List<RecoveryCode>? = null, val missing: Boolean = false) {
        fun size(): Int = codes?.size ?: text?.codePointCount(0, text.length) ?: 0
        fun summary(secret: Boolean): BackupComparisonValueSummary {
            val count = if (secret) null else size()
            val preview = if (secret) null else text?.substring(0, text.offsetByCodePoints(0, minOf(requireNotNull(count), 4096)))
            return BackupComparisonValueSummary(preview, count, codes?.isNotEmpty() ?: !text.isNullOrEmpty(), missing, codes?.size)
        }
        fun chunk(offset: Int, limit: Int): BackupImportFieldValue {
            val total = size()
            val start = minOf(offset, total)
            val end = minOf(total.toLong(), start.toLong() + if (codes == null) limit else minOf(limit, 20)).toInt()
            val chunkText = text?.substring(text.offsetByCodePoints(0, start), text.offsetByCodePoints(0, end))
            val records = codes?.subList(start, end)?.mapIndexed { index, code -> BackupImportRecoveryCode(start + index, code.value, code.used) }.orEmpty()
            return BackupImportFieldValue(chunkText, records, total, end, end == total, missing)
        }
        override fun toString() = "ComparedValue(内容已隐藏)"
    }

    private class ComparedField(val field: BackupComparisonField, val source: ComparedValue, val current: ComparedValue?,
                                val policy: BackupComparisonWritePolicy = BackupComparisonWritePolicy.SOURCE) {
        fun summary(): BackupComparisonFieldSummary {
            val secret = field in setOf(BackupComparisonField.PASSWORD, BackupComparisonField.TOTP_SECRET, BackupComparisonField.RECOVERY_CODES)
            return BackupComparisonFieldSummary(field, source.summary(secret), current?.summary(secret), changed(), policy)
        }
        fun changed(): Boolean = when {
                source.missing -> false
                current == null -> true
                field in setOf(BackupComparisonField.CREATED_AT, BackupComparisonField.UPDATED_AT, BackupComparisonField.PASSWORD_CHANGED_AT) &&
                    source.text != null && current.text != null -> BackupProtocol.timestampOrder(source.text) != BackupProtocol.timestampOrder(current.text)
                else -> source.text != current.text || source.codes != current.codes
        }
        override fun toString() = "ComparedField(内容已隐藏)"
    }

    private fun passwordFields(source: BackupPassword, current: PasswordRecord?): List<ComparedField> {
        fun text(field: BackupComparisonField, sourceText: String?, currentText: String?) =
            ComparedField(field, ComparedValue(sourceText), current?.let { ComparedValue(currentText) })
        return listOf(
            text(BackupComparisonField.TITLE, source.platform, current?.title),
            text(BackupComparisonField.ACCOUNT, source.account, current?.account),
            text(BackupComparisonField.PASSWORD, source.password, current?.password),
            text(BackupComparisonField.NOTES, source.notes, current?.notes),
            text(BackupComparisonField.TOTP_SECRET, source.totpSecret, current?.totpSecret),
            ComparedField(BackupComparisonField.RECOVERY_CODES, ComparedValue(codes = source.recoveryCodes),
                current?.let { ComparedValue(codes = checkedRecoveryCodes(it.recoveryCodesJson)) }),
            text(BackupComparisonField.FAVORITE, source.favorite.toString(), current?.favorite?.toString()),
            text(BackupComparisonField.STRENGTH, source.strength, current?.strength),
            text(BackupComparisonField.PASSWORD_CHANGED_AT, source.passwordChangedAt, current?.passwordChangedAt),
            // 密码交换负载没有创建时间；覆盖保留目标，新增仍为未知。
            ComparedField(BackupComparisonField.CREATED_AT, ComparedValue(missing = true), current?.let { ComparedValue(it.createdAt) },
                BackupComparisonWritePolicy.KEEP_CURRENT),
            text(BackupComparisonField.UPDATED_AT, source.updatedAt, current?.updatedAt),
        )
    }

    private fun noteFields(source: BackupNote, current: NoteRecord?): List<ComparedField> {
        fun text(field: BackupComparisonField, sourceText: String, currentText: String?) =
            ComparedField(field, ComparedValue(sourceText), current?.let { ComparedValue(currentText) })
        return listOf(
            text(BackupComparisonField.TITLE, source.title, current?.title),
            text(BackupComparisonField.NOTES, source.content, current?.content),
            text(BackupComparisonField.FAVORITE, source.favorite.toString(), current?.favorite?.toString()),
            text(BackupComparisonField.CREATED_AT, source.createdAt, current?.createdAt),
            text(BackupComparisonField.UPDATED_AT, source.updatedAt, current?.updatedAt),
            // 记事覆盖保留本地位置，新增按来源相对顺序追加，均不是照抄来源数值。
            ComparedField(BackupComparisonField.SORT_ORDER, ComparedValue(source.sortOrder.toString()), current?.let { ComparedValue(it.sortOrder.toString()) },
                if (current == null) BackupComparisonWritePolicy.APPEND_ORDER else BackupComparisonWritePolicy.KEEP_CURRENT),
        )
    }

    private fun fieldPair(values: List<ComparedField>, field: BackupComparisonField, offset: Int, limit: Int,
                          guard: () -> Unit): Pair<BackupImportFieldValue, BackupImportFieldValue?> {
        if (offset < 0 || limit !in 1..4096) throw BackupStoreException(BackupStoreProblem.INPUT)
        val selected = values.firstOrNull { it.field == field } ?: throw BackupStoreException(BackupStoreProblem.INPUT)
        guard()
        if (offset > maxOf(selected.source.size(), selected.current?.size() ?: 0)) throw BackupStoreException(BackupStoreProblem.INPUT)
        val source = selected.source.chunk(offset, limit)
        guard()
        val current = selected.current?.chunk(offset, limit)
        guard()
        return source to current
    }

    // 业务相同只用于本次分类；原完整安全指纹仍独立校验ID、版本及时间。
    private fun passwordContent(title: String, account: String, password: String, notes: String, totp: String,
                                codes: List<RecoveryCode>, favorite: Boolean, guard: () -> Unit): String = digest(guard) { writer ->
        writer.beginArray().value(title).value(account).value(password).value(notes).value(totp).value(favorite).beginArray()
        codes.forEach { code -> guard(); writer.beginArray().value(code.value).value(code.used).endArray() }
        writer.endArray().endArray()
    }

    private fun noteContent(title: String, content: String, favorite: Boolean, guard: () -> Unit): String = digest(guard) {
        it.beginArray().value(title).value(content).value(favorite).endArray()
    }

    fun fingerprint(record: PasswordRecord, guard: () -> Unit): String = digest(guard) { writer ->
        writer.beginArray().value(record.id).value(record.revision).value(record.title).value(record.account).value(record.password)
            .value(record.notes).value(record.totpSecret).value(record.createdAt).value(record.passwordChangedAt).value(record.updatedAt).value(record.favorite)
        writer.beginArray()
        checkedRecoveryCodes(record.recoveryCodesJson).forEach { code -> writer.beginArray().value(code.value).value(code.used).endArray() }
        writer.endArray().endArray()
    }

    fun fingerprint(record: NoteRecord, guard: () -> Unit): String = digest(guard) { writer ->
        writer.beginArray().value(record.id).value(record.revision).value(record.title).value(record.content).value(record.createdAt)
            .value(record.updatedAt).value(record.sortOrder).value(record.favorite).endArray()
    }

    private fun digest(guard: () -> Unit, write: (JsonWriter) -> Unit): String {
        val digest = MessageDigest.getInstance("SHA-256")
        val sink = object : OutputStream() {
            override fun write(value: Int) { guard() }
            override fun write(buffer: ByteArray, offset: Int, length: Int) { guard() }
        }
        JsonWriter(OutputStreamWriter(DigestOutputStream(sink, digest), Charsets.UTF_8)).use { writer ->
            writer.setSerializeNulls(true)
            write(writer)
        }
        guard()
        return digest.digest().joinToString("") { (it.toInt() and 255).toString(16).padStart(2, '0') }
    }

    private fun eachId(database: VaultDatabase, kind: BackupImportKind, guard: () -> Unit, read: (String) -> Unit) {
        var offset = 0
        while (true) {
            guard()
            val rows = if (kind == BackupImportKind.PASSWORD) database.passwords().backupIds(128, offset) else database.notes().backupIds(128, offset)
            val count = rows.use {
                var count = 0
                while (true) {
                    guard()
                    if (!it.moveToNext()) break
                    guard(); read(it.getString(0)); count++
                }
                count
            }
            if (count < 128) return
            offset = Math.addExact(offset, count)
        }
    }

    private fun title(database: VaultDatabase, kind: BackupImportKind, id: String, guard: () -> Unit): String {
        guard()
        val table = if (kind == BackupImportKind.PASSWORD) "passwords" else "notes"
        val bytes = database.openHelper.readableDatabase.compileStatement("SELECT length(CAST(title AS BLOB)) FROM $table WHERE id = ?")
            .use { statement -> statement.bindString(1, id); statement.simpleQueryForLong() }
        BackupMemoryBudget().checkAvailable(BackupMemoryBudget.textPeak(bytes))
        return database.openHelper.readableDatabase
            .compileStatement(if (kind == BackupImportKind.PASSWORD) "SELECT title FROM passwords WHERE id = ?" else "SELECT title FROM notes WHERE id = ?")
            .use { statement -> statement.bindString(1, id); (statement.simpleQueryForString() ?: throw VaultException(VaultError.DATA_UNAVAILABLE)).also { guard() } }
    }

    private fun utf8Bytes(value: String, guard: () -> Unit): Long {
        var bytes = 0L
        var index = 0
        while (index < value.length) {
            if (index % 4096 == 0) guard()
            val point = value.codePointAt(index)
            bytes += when { point < 0x80 -> 1; point < 0x800 -> 2; point < 0x10000 -> 3; else -> 4 }
            index += Character.charCount(point)
        }
        return bytes
    }

    private fun failLimit(): Nothing = throw BackupStoreException(BackupStoreProblem.LIMIT)
    private fun failDecisions(): Nothing = throw BackupStoreException(BackupStoreProblem.DECISIONS)
}
