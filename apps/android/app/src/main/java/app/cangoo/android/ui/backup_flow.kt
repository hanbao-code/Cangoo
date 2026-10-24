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
import app.cangoo.android.data.BackupPreviewTextField

internal enum class BackupStep { HOME, EXPORT, IMPORT, PREVIEW, RESULT }
internal enum class BackupSource { FILE, TRANSFER }
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
