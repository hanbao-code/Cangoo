package app.cangoo.android.data

internal enum class BackupImportKind { PASSWORD, NOTE }
internal data class BackupSelection(val passwords: Map<String, Long> = emptyMap(), val notes: Map<String, Long> = emptyMap()) {
    val empty: Boolean get() = passwords.isEmpty() && notes.isEmpty()
    val scope: BackupScope get() = when { notes.isEmpty() -> BackupScope.PASSWORDS; passwords.isEmpty() -> BackupScope.NOTES; else -> BackupScope.ALL }
    override fun toString() = "BackupSelection(记录身份已隐藏)"
}
internal enum class PasswordImportAction { OVERWRITE, SKIP }
internal enum class NoteImportAction { KEEP_BOTH, OVERWRITE, SKIP }
internal enum class BackupPreviewTextField { TITLE, ACCOUNT, NOTES, CONTENT }
internal enum class BackupComparisonField {
    TITLE, ACCOUNT, PASSWORD, NOTES, TOTP_SECRET, RECOVERY_CODES, FAVORITE, STRENGTH,
    PASSWORD_CHANGED_AT, CREATED_AT, UPDATED_AT, SORT_ORDER,
}
internal enum class BackupComparisonWritePolicy { SOURCE, KEEP_CURRENT, APPEND_ORDER }
internal enum class BackupImportFilter { ALL, PENDING, DIFFERENT, SKIPPED }
internal data class BackupImportQuery(val state: BackupImportFilter = BackupImportFilter.ALL, val changedField: BackupComparisonField? = null)
internal enum class BackupImportBatchAction { OVERWRITE, SKIP, KEEP_BOTH }
internal enum class BackupImportBatchDeferredReason { AMBIGUOUS_TARGET, NO_AVAILABLE_TARGET, SHARED_TARGET }

internal data class BackupImportPage(
    val previewId: String, val kind: BackupImportKind, val rows: List<BackupImportRow>, val offset: Int,
    val matchedCount: Int, val nextOffset: Int?, val awaitingTargetCount: Int, val selectedOutsideFilterCount: Int,
) { override fun toString() = "BackupImportPage(内容已隐藏)" }

internal data class BackupImportPlanSummary(
    val previewId: String, val imported: Int, val overwritten: Int, val skipped: Int,
    val pending: Int, val recoveryRemovalCount: Int,
)

internal data class BackupImportBatchProposal(
    val previewId: String, val kind: BackupImportKind, val decisions: BackupImportDecisions,
    val appliedSourceIndices: Set<Int>, val deferred: Map<Int, BackupImportBatchDeferredReason>,
    val legacyRecoveryRemovalIndices: Set<Int>, val recoveryRemovalIndices: Set<Int>,
    val selectedOutsideFilterCount: Int, val summary: BackupImportPlanSummary,
) { override fun toString() = "BackupImportBatchProposal(决定草稿)" }

internal data class BackupComparisonValueSummary(
    val preview: String?, val codePoints: Int?, val hasValue: Boolean,
    val missing: Boolean = false, val count: Int? = null,
) { override fun toString() = "BackupComparisonValueSummary(内容已隐藏)" }

internal data class BackupComparisonFieldSummary(
    val field: BackupComparisonField, val source: BackupComparisonValueSummary,
    val current: BackupComparisonValueSummary?, val changed: Boolean,
    val writePolicy: BackupComparisonWritePolicy,
) { override fun toString() = "BackupComparisonFieldSummary(内容已隐藏)" }

internal data class BackupImportComparison(
    val previewId: String, val kind: BackupImportKind, val sourceIndex: Int,
    val targetId: String?, val targetRevision: Long?, val fields: List<BackupComparisonFieldSummary>,
    val businessChangedFields: Set<BackupComparisonField>, val metadataChangedFields: Set<BackupComparisonField>,
    val alreadyExists: Boolean, val legacyRecoveryWillClear: Boolean,
    val targetReserved: Boolean = false,
) { override fun toString() = "BackupImportComparison(内容已隐藏)" }

internal data class BackupImportRecoveryCode(val index: Int, val value: String, val used: Boolean) {
    override fun toString() = "BackupImportRecoveryCode(内容已隐藏)"
}

internal data class BackupImportFieldValue(
    val text: String?, val recoveryCodes: List<BackupImportRecoveryCode>,
    val total: Int, val nextOffset: Int, val complete: Boolean, val missing: Boolean = false,
) { override fun toString() = "BackupImportFieldValue(内容已隐藏)" }

internal data class BackupImportFieldPair(
    val previewId: String, val kind: BackupImportKind, val sourceIndex: Int, val targetId: String?,
    val field: BackupComparisonField, val offset: Int,
    val source: BackupImportFieldValue, val current: BackupImportFieldValue?,
) { override fun toString() = "BackupImportFieldPair(内容已隐藏)" }

internal data class PasswordImportChoice(val action: PasswordImportAction, val acknowledgeRecoveryRemoval: Boolean = false)
internal data class NoteImportChoice(val action: NoteImportAction, val targetId: String? = null)
internal data class BackupImportDecisions(
    val passwords: Map<Int, PasswordImportChoice> = emptyMap(),
    val notes: Map<Int, NoteImportChoice> = emptyMap(),
)

internal data class BackupImportPreview(
    val id: String, val passwordCount: Int, val noteCount: Int,
    val passwordConflictCount: Int, val noteConflictCount: Int,
    val initialSummary: BackupImportPlanSummary,
)

internal data class BackupImportRow(
    val sourceIndex: Int, val title: String, val titleTruncated: Boolean,
    val account: String, val accountTruncated: Boolean, val preview: String,
    val favorite: Boolean, val hasTotp: Boolean, val recoveryCodeCount: Int,
    val candidateCount: Int, val decisionRequired: Boolean, val legacyRecoveryWillClear: Boolean,
    val hasPassword: Boolean = false, val passwordTargetId: String? = null, val passwordTargetRevision: Long? = null,
    val alreadyExists: Boolean = false,
    val comparisonTargetId: String? = null, val businessChangedFields: Set<BackupComparisonField>? = null,
    val hasDifferences: Boolean = false,
) { override fun toString() = "BackupImportRow(内容已隐藏)" }

internal data class BackupImportCandidate(
    val id: String, val revision: Long, val title: String, val titleTruncated: Boolean,
    val preview: String, val exactTitle: Boolean,
    val reserved: Boolean = false,
) { override fun toString() = "BackupImportCandidate(内容已隐藏)" }

internal data class BackupImportText(val text: String, val nextOffset: Int, val complete: Boolean) {
    override fun toString() = "BackupImportText(内容已隐藏)"
}

internal data class BackupImportResult(val imported: Int, val overwritten: Int, val skipped: Int)
internal data class BackupExportResult(val passwordCount: Int, val noteCount: Int, val receipt: BackupDocumentReceipt,
                                     val localRecordWrite: LocalBackupRecordWrite, val localRecord: LocalBackupRecordState)
internal enum class BackupPrivateCleanup(val text: String) {
    REMOVED("私有加密临时包已清理。"),
    RESIDUAL("私有加密临时包清理未完成，仍可能留有密文残留。"),
}
internal data class VaultDeletionResult(val outcome: DeletionOutcome, val currentSessionClosed: Boolean)

internal enum class BackupStoreProblem(val text: String) {
    STALE("备份预览已失效或来源、目标已变化，请重新选择文件并预览。"),
    DECISIONS("冲突决定尚未完整、目标重复占用或未确认旧恢复码清空，请检查后重试。"),
    CANCELLED("备份操作已取消，请重新开始。"),
    LIMIT("备份大小、记录数量或记事排序位置超出可接收范围。"),
    INPUT("备份预览读取参数无效，请重新打开。"),
    VERIFICATION("备份校验未通过，本次导出未完成，请重试。"),
    EXPORT_EMPTY("请至少选择一条密码或记事。"),
    EXPORT_CHANGED("所选资料已修改或删除，请重新选择并核对。"),
}

internal class BackupStoreException(val problem: BackupStoreProblem) : IllegalStateException(problem.text)

internal class BackupPasswordTarget(val summary: PasswordSummary, val fingerprint: String) {
    override fun toString() = "BackupPasswordTarget(内容已隐藏)"
}
internal class BackupNoteTarget(val summary: NoteSummary, val fingerprint: String) {
    override fun toString() = "BackupNoteTarget(内容已隐藏)"
}
internal class BackupTargetSnapshot(
    val passwords: Map<String, BackupPasswordTarget>, val notes: Map<String, List<BackupNoteTarget>>,
    val noteKeys: List<String>, val noteSourceCounts: Map<String, Int>,
    val identicalPasswords: Set<Int>, val identicalNotes: Map<Int, String>,
) {
    val reservedNoteIds: Set<String> = identicalNotes.values.toSet()
    val noteTargetsById: Map<String, Pair<String, BackupNoteTarget>> = notes.flatMap { (key, values) ->
        values.map { it.summary.id to (key to it) }
    }.toMap()
    fun sameContent(other: BackupTargetSnapshot): Boolean = passwords.keys == other.passwords.keys &&
        passwords.all { (key, value) -> value.fingerprint == other.passwords[key]?.fingerprint } &&
        notes.keys == other.notes.keys && notes.all { (key, values) ->
            values.map { it.fingerprint } == other.notes[key]?.map { it.fingerprint }
        }
    override fun toString() = "BackupTargetSnapshot(内容摘要已隐藏)"
}
