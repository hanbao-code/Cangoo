package app.cangoo.android.ui

import app.cangoo.android.data.BackupImportCandidate
import app.cangoo.android.data.BackupComparisonField
import app.cangoo.android.data.BackupImportComparison
import app.cangoo.android.data.BackupImportFieldPair
import app.cangoo.android.data.BackupImportQuery
import app.cangoo.android.data.BackupImportPage
import app.cangoo.android.data.BackupImportBatchProposal
import app.cangoo.android.data.BackupImportPlanSummary
import app.cangoo.android.data.BackupImportDecisions
import app.cangoo.android.data.BackupImportKind
import app.cangoo.android.data.BackupImportPreview
import app.cangoo.android.data.BackupImportResult
import app.cangoo.android.data.BackupImportRow
import app.cangoo.android.data.BackupScope
import app.cangoo.android.data.BackupSelection
import app.cangoo.android.data.BackupPreviewTextField

internal enum class BackupStep { HOME, EXPORT, IMPORT, PREVIEW, RESULT }
internal enum class BackupSource { FILE, TRANSFER }
internal data class ExportSelectionRow(val kind: BackupImportKind, val id: String, val revision: Long,
                                      val title: String, val subtitle: String, val updatedAt: String) {
    override fun toString() = "ExportSelectionRow(内容已隐藏)"
}
internal data class ExportSelectionUiState(val token: Long, val permission: Long, val input: Long, val vaultId: String,
    val origin: Page, val selected: BackupSelection, val query: String = "", val kind: BrowseKind = BrowseKind.ALL,
    val rows: List<ExportSelectionRow> = emptyList(), val loading: Boolean = true, val error: UiText = UiText.Empty) {
    val visibleRows: List<ExportSelectionRow> get() = when (kind) {
        BrowseKind.ALL -> rows
        BrowseKind.PASSWORD -> rows.filter { it.kind == BackupImportKind.PASSWORD }
        BrowseKind.NOTE -> rows.filter { it.kind == BackupImportKind.NOTE }
    }
    fun isSelected(row: ExportSelectionRow): Boolean = row.id in if (row.kind == BackupImportKind.PASSWORD) selected.passwords else selected.notes
    val allVisibleSelected: Boolean get() = visibleRows.let { it.isNotEmpty() && it.all(::isSelected) }
    fun toggledVisibleSelection(): BackupSelection {
        val current = visibleRows
        if (current.isEmpty()) return selected
        val passwords = current.filter { it.kind == BackupImportKind.PASSWORD }.associate { it.id to it.revision }
        val notes = current.filter { it.kind == BackupImportKind.NOTE }.associate { it.id to it.revision }
        return if (current.all(::isSelected)) BackupSelection(selected.passwords - passwords.keys, selected.notes - notes.keys)
            else BackupSelection(selected.passwords + passwords, selected.notes + notes)
    }
    override fun toString() = "ExportSelectionUiState(内容已隐藏)"
}
internal data class BackupTextRequest(val kind: BackupImportKind, val sourceIndex: Int, val targetId: String?, val field: BackupPreviewTextField)
internal data class BackupDetail(val kind: BackupImportKind, val sourceIndex: Int, val token: Long)
internal data class BackupFieldRequest(val field: BackupComparisonField, val offset: Int, val targetId: String?)
internal data class BackupGroupUiState(
    val query: BackupImportQuery = BackupImportQuery(), val offset: Int = 0,
    val selected: Set<Int> = emptySet(), val comparisonTargets: Map<Int, String> = emptyMap(),
)
internal data class BackupBatchReview(val token: Long, val proposal: BackupImportBatchProposal,
                                    val original: BackupImportDecisions, val selected: Set<Int>) {
    override fun toString() = "BackupBatchReview(内容已隐藏)"
}
internal data class BackupCommitReview(val token: Long, val summary: BackupImportPlanSummary, val decisions: BackupImportDecisions)

// 只保当前进程的界面草稿与有界预览；完整认证负载属于存储层。
internal data class BackupUiState(
    val step: BackupStep = BackupStep.HOME,
    val scope: BackupScope = BackupScope.ALL,
    val custom: Boolean = false,
    val selection: BackupSelection = BackupSelection(),
    val documentName: String = "",
    val source: BackupSource = BackupSource.FILE,
    val password: String = "",
    val confirmation: String = "",
    val preview: BackupImportPreview? = null,
    val previewKind: BackupImportKind = BackupImportKind.PASSWORD,
    val rows: List<BackupImportRow> = emptyList(),
    val offset: Int = 0,
    val groupStates: Map<BackupImportKind, BackupGroupUiState> = emptyMap(),
    val pageInfo: BackupImportPage? = null,
    val planSummary: BackupImportPlanSummary? = null,
    val batchReview: BackupBatchReview? = null,
    val commitReview: BackupCommitReview? = null,
    val decisions: BackupImportDecisions = BackupImportDecisions(),
    val requiredPasswordChoices: Set<Int> = emptySet(),
    val requiredNoteChoices: Set<Int> = emptySet(),
    val detail: BackupDetail? = null,
    val comparison: BackupImportComparison? = null,
    val comparisonTargetId: String? = null,
    val choosingTarget: Boolean = false,
    val fieldRequest: BackupFieldRequest? = null,
    val fieldPair: BackupImportFieldPair? = null,
    val expandedField: BackupComparisonField? = null,
    val reading: Boolean = false,
    val readError: UiText = UiText.Empty,
    val listReadError: UiText = UiText.Empty,
    val candidateSourceIndex: Int? = null,
    val candidates: List<BackupImportCandidate> = emptyList(),
    val candidateOffset: Int = 0,
    val text: String = "",
    val textRequest: BackupTextRequest? = null,
    val textNextOffset: Int = 0,
    val textOffset: Int = 0,
    val textRequestedOffset: Int = 0,
    val textComplete: Boolean = true,
    val result: BackupImportResult? = null,
) {
    val currentGroup: BackupGroupUiState get() = groupStates[previewKind] ?: BackupGroupUiState()
    override fun toString() = "BackupUiState(内容已隐藏)"
}
