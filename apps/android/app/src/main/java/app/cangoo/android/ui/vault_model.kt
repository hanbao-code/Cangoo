package app.cangoo.android.ui

import android.app.Application
import android.content.ClipData
import android.content.ClipboardManager
import android.hardware.biometrics.BiometricManager
import android.os.SystemClock
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.mutableLongStateOf
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import app.cangoo.android.data.PasswordDraft
import app.cangoo.android.data.PasswordRecord
import app.cangoo.android.data.PasswordSummary
import app.cangoo.android.data.NoteDraft
import app.cangoo.android.data.NoteRecord
import app.cangoo.android.data.NoteSummary
import app.cangoo.android.data.PasswordChecks
import app.cangoo.android.data.VaultException
import app.cangoo.android.data.VaultError
import app.cangoo.android.data.VaultInfo
import app.cangoo.android.data.VaultStore
import app.cangoo.android.data.toSummary
import app.cangoo.android.data.decodeRecoveryCodes
import app.cangoo.android.data.normalizeRecoveryCodes
import app.cangoo.android.data.RecoveryCodeException
import app.cangoo.android.data.RecoveryCode
import app.cangoo.android.data.BackupDocumentCleanup
import app.cangoo.android.data.BackupDocumentException
import app.cangoo.android.data.BackupProtocolException
import app.cangoo.android.data.BackupStoreException
import app.cangoo.android.data.BackupStoreProblem
import app.cangoo.android.data.CreatedBackupDocument
import app.cangoo.android.data.BackupImportKind
import app.cangoo.android.data.BackupImportPreview
import app.cangoo.android.data.BackupComparisonField
import app.cangoo.android.data.BackupImportQuery
import app.cangoo.android.data.BackupImportBatchAction
import app.cangoo.android.data.BackupImportDecisions
import app.cangoo.android.data.BackupPreviewTextField
import app.cangoo.android.data.PasswordImportChoice
import app.cangoo.android.data.PasswordImportAction
import app.cangoo.android.data.NoteImportChoice
import app.cangoo.android.data.NoteImportAction
import app.cangoo.android.data.BackupPrivateCleanup
import app.cangoo.android.data.BackupScope
import app.cangoo.android.data.LocalBackupRecordState
import app.cangoo.android.data.LocalBackupRecordWrite
import app.cangoo.android.data.DeletionPreview
import app.cangoo.android.data.VaultDeletionResult
import app.cangoo.android.data.DeletionStatus
import app.cangoo.android.data.VaultBiometricPurpose
import app.cangoo.android.data.VaultBiometricAuthentication
import app.cangoo.android.data.VaultBiometricAuthenticator
import app.cangoo.android.data.VaultBiometricCancelled
import app.cangoo.android.data.VaultChangeStage
import app.cangoo.android.data.VaultRotationResult
import app.cangoo.android.data.VaultRotationFailure
import app.cangoo.android.data.VaultCleanupStatus
import app.cangoo.android.R
import javax.crypto.Cipher
import java.util.UUID
import java.util.concurrent.atomic.AtomicReference
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.CoroutineStart
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.NonCancellable
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock

enum class Page { VAULTS, VAULT_MANAGEMENT, CREATE, RENAME, LOCKED, HOME, PASSWORDS, SEARCH, TOOLS, SETTINGS, APPEARANCE, GENERATOR, STRENGTH, CHECKS, ADD, EDIT, DETAIL, NOTE_ADD, NOTE_EDIT, NOTE_DETAIL, SECURITY, BACKUP, VAULT_DELETE, HELP, MASTER, BIOMETRIC, SYSTEM_ACCESS, TRANSFER }
enum class BrowseKind { ALL, PASSWORD, NOTE }
enum class BrowseFilter { ALL, FAVORITE, WEAK, REPEATED }
enum class BrowseSort { RECENT, NAME }
internal enum class UiPreferenceErrorSource { GENERAL, GENERATOR, CLIPBOARD, DISPLAY }

internal data class DraftGeneratorPanel(val token: Long, val permission: Long, val input: Long, val page: Page,
    val id: String?, val revision: Long?, val options: GeneratorOptions, val error: UiText = UiText.Empty)

data class VaultUiState(
    val page: Page = Page.VAULTS,
    val vaults: List<VaultInfo> = emptyList(),
    val vault: VaultInfo? = null,
    val unlocked: Boolean = false,
    val passwords: List<PasswordSummary> = emptyList(),
    val notes: List<NoteSummary> = emptyList(),
    val record: PasswordRecord? = null,
    val note: NoteRecord? = null,
    val draft: PasswordDraft = PasswordDraft("", "", "", ""),
    val noteDraft: NoteDraft = NoteDraft(""),
    val secretDraft: RecordSecretDraft = RecordSecretDraft(),
    val secretView: RecordSecretView = RecordSecretView(),
    val checks: PasswordChecks = PasswordChecks(),
    val checksAvailable: Boolean = true,
    val recentKeys: List<Pair<String, Boolean>> = emptyList(),
    val localBackupRecordLabel: UiText? = null,
    val query: String = "",
    val effectiveQuery: String = "",
    val searchOpening: Long = 0L,
    val browseRun: Long = 0L,
    val searchNotes: List<NoteSummary> = emptyList(),
    val searchPasswords: List<PasswordSummary> = emptyList(),
    val searchPending: Boolean = false,
    val browseKind: BrowseKind = BrowseKind.ALL,
    val browseFilter: BrowseFilter = BrowseFilter.ALL,
    val browseSort: BrowseSort = BrowseSort.RECENT,
    val orderKeys: List<Pair<String, Boolean>> = emptyList(),
    val orderPending: Boolean = false,
    val orderAvailable: Boolean = false,
    val generatorOptions: GeneratorOptions = GeneratorOptions(),
    val generated: String = "",
    val generatedExpanded: Boolean = false,
    val generatedExpiresAt: Long? = null,
    val strengthInput: String = "",
    val strengthResult: PasswordStrengthResult? = null,
    val strengthPending: Boolean = false,
    val vaultName: String = "",
    val master: String = "",
    val newMaster: String = "",
    val confirmation: String = "",
    val securityStage: UiText = UiText.Empty,
    val passwordShown: Boolean = false,
    val showVaults: Boolean = false,
    val showAdd: Boolean = false,
    val deleteConfirm: Boolean = false,
    val discard: Boolean = false,
    val busy: Boolean = false,
    val error: UiText = UiText.Empty,
    val notice: UiText = UiText.Empty,
) {
    override fun toString() = "VaultUiState(内容已隐藏)"
}

class VaultModel private constructor(application: Application, private val clipboardTransport: ClipboardPublishTransport) : AndroidViewModel(application) {
    constructor(application: Application) : this(application, AndroidClipboardPublishTransport(application.getSystemService(ClipboardManager::class.java)))
    internal companion object {
        fun withClipboard(application: Application, transport: ClipboardPublishTransport) = VaultModel(application, transport)
        // 同进程快速退出重开时，新模型也等待已成功会话的定位提交。
        private var lastVaultWrite: Job? = null
    }
    private val systemGuideStore = SystemAccessGuideStore(application)
    internal var systemGuideVisible by mutableStateOf(systemGuideStore.shouldOffer(application))
        private set
    private val store = VaultStore(application)
    private val settingsStore = SecuritySettingsStore(application)
    private val uiPreferencesStore = UiPreferencesStore(application)
    internal val updates = UpdateCheckController(application, viewModelScope)
    private val lastVaultStore = LastVaultStore(application)
    private var generatedExpiryJob: Job? = null
    private val uiPreferencesMutex = Mutex()
    private var uiPreferenceWrites = 0
    private var generatorWriteRun = 0L
    private var draftGeneratorRun = 0L
    private var activeDraftGenerator by mutableStateOf<DraftGeneratorPanel?>(null)
    internal val draftGenerator: DraftGeneratorPanel? get() = activeDraftGenerator?.takeIf {
        it.permission == generation && editorMatches(it.input, it.page, it.id, it.revision)
    }
    private val idleDeadline = IdleDeadline(SystemClock.elapsedRealtime())
    private var idleJob: Job? = null
    @Volatile private var foreground = false
    @Volatile private var contentVisible = false
    internal var backupState by mutableStateOf(BackupUiState())
        private set
    internal var directTransfer by mutableStateOf<DirectTransferController?>(null)
        private set
    private var transferHoldOwner: Pair<Long, String>? = null
    private var pendingTransferPreview: BackupImportPreview? = null
    private var pendingTransferStart: DirectTransferController? = null
    private var transferSourceName = ""
    internal var documentIntent by mutableStateOf<BackupDocumentIntent?>(null)
        private set
    private class ExportTarget(val request: BackupDocumentIntent, val scope: BackupScope, val permission: Long) {
        val token = UUID.randomUUID().toString()
        val mutex = Mutex()
        var uri: android.net.Uri? = null
        var received = false
        var autoStart = true
        @Volatile var abandoned = false
        @Volatile var owns = true
        var created: CreatedBackupDocument? = null
        var cleanup: BackupDocumentCleanup? = null
    }
    private val exportTargets = mutableMapOf<String, ExportTarget>()
    private val exportFileOwners = mutableMapOf<Pair<Long, Long>, ExportTarget>()
    private var backupOwnerClosed = false
    internal val pendingDocumentIntents: List<BackupDocumentIntent> get() =
        exportTargets.values.filter { !it.received }.map { it.request } +
            listOfNotNull(documentIntent?.takeIf { it.kind == BackupDocumentKind.IMPORT && it.uri == null })
    internal val exportSelectionPending: Boolean get() = currentExport()?.let { it.autoStart && !it.abandoned } == true
    private fun currentExport(): ExportTarget? = documentIntent?.let { exportTargets[it.requestId] }

    private suspend fun cleanupExport(target: ExportTarget): BackupDocumentCleanup? = withContext(NonCancellable) {
        target.mutex.withLock {
            target.cleanup ?: target.created?.let { created ->
                withContext(Dispatchers.IO) { store.cleanupBackupDestination(created) { it === created && target.owns } }
                    .also { target.cleanup = it }
            }
        }.also {
            if (target.received) {
                exportTargets.remove(target.request.requestId, target)
                target.created?.let { created -> exportFileOwners.remove(created.device to created.inode, target) }
            }
        }
    }

    private fun abandonExport(target: ExportTarget) {
        val report = !target.abandoned
        target.abandoned = true
        target.autoStart = false
        val permission = generation
        val input = inputGeneration
        val page = state.page
        val vaultId = state.vault?.id
        viewModelScope.launch(NonCancellable, start = CoroutineStart.UNDISPATCHED) {
            val result = cleanupExport(target)
            if (report && !backupOwnerClosed && permission == generation && input == inputGeneration &&
                page == state.page && vaultId == state.vault?.id && result != null && result != BackupDocumentCleanup.PUBLISHED &&
                (documentIntent == null || documentIntent?.requestId == target.request.requestId)) {
                state = state.copy(notice = result.uiText())
            }
        }
    }

    private fun startReadyExport() {
        val target = currentExport() ?: return
        if (target.permission != generation) target.autoStart = false
        if (!target.autoStart || target.abandoned || target.created == null || target.cleanup != null ||
            !foreground || !contentVisible || !state.unlocked || state.page != Page.BACKUP || state.busy ||
            state.vault?.id != target.request.vaultId) return
        target.autoStart = false
        exportBackup(inputGeneration)
    }

    private var backupReturn = Page.SETTINGS
    private var backupJob: Job? = null
    @Volatile private var backupRun = 0L
    private var backupDetailRun = 0L
    private var backupReviewRun = 0L
    internal var deletionState by mutableStateOf(VaultDeletionUiState())
        private set
    private var deletionReturn = Page.VAULTS
    private var totpJob: Job? = null
    private var secretRun = 0L
    private val recoveryJobs = mutableMapOf<Int, Job>()
    @Volatile private var generation = 0L
    private var inputGeneration by mutableLongStateOf(0L)
    val editGeneration: Long get() = inputGeneration
    private var createReturn = Page.VAULTS
    private var securityReturn = Page.VAULTS
    private var preferenceReturn = Page.SETTINGS
    private var systemAccessReturn = Page.SECURITY
    private var systemAccessJob: Job? = null
    internal var systemAccessSnapshot by mutableStateOf<SystemAccessSnapshot?>(null)
        private set
    private var recordReturn = Page.PASSWORDS
    internal val editingFromChecks: Boolean get() = state.page == Page.EDIT && recordReturn == Page.CHECKS
    private var searchReturn = Page.HOME
    private var searchOriginKind = BrowseKind.ALL
    private var searchOriginFilter = BrowseFilter.ALL
    private var searchOriginSort = BrowseSort.RECENT
    private var checksReturn = Page.HOME
    private var unlockReturn = Page.HOME
    private var queryJob: Job? = null
    private var queryRun = 0L
    private var orderJob: Job? = null
    private var orderRun = 0L
    private var strengthOwner: PasswordStrengthOwner? = null
    private var recordStrengthJob: Job? = null
    private var recordStrengthWakePending = false
    private var recordStrengthReply: Pair<Long, CompletableDeferred<PasswordStrengthOutcome>>? = null
    @Volatile private var recordStrengthRun = 0L
    var checksPaused by mutableStateOf(false)
        private set
    var checksRunning by mutableStateOf(false)
        private set
    private var failedStrength by mutableStateOf<Map<String, Long>>(emptyMap())
    val failedCheckIds: Set<String> get() = state.checks.pendingEpochs.filter { (id, epoch) -> failedStrength[id] == epoch }.keys
    val failedCheckCount: Int get() = failedCheckIds.size

    private var strengthRun = 0L
    private var strengthPermission = 0L
    private var strengthInputGeneration = 0L
    private var strengthVaultId: String? = null
    private val recentByVault = mutableMapOf<String, List<Pair<String, Boolean>>>()
    var securitySettings by mutableStateOf(SecuritySettings())
        private set
    var securitySettingsSaving by mutableStateOf(false)
        private set
    private var securitySettingsFailure by mutableStateOf<UiText?>(null)
    val securitySettingsError: String get() = securitySettingsFailure?.resolve(localizedResources(getApplication(), uiPreferences.language)).orEmpty()
    var uiPreferences by mutableStateOf(UiPreferences())
        private set
    var uiPreferencesSaving by mutableStateOf(false)
        private set
    private var uiPreferencesFailure by mutableStateOf<UiText?>(null)
    val uiPreferencesError: String get() = uiPreferencesFailure?.resolve(localizedResources(getApplication(), uiPreferences.language)).orEmpty()
    internal var uiPreferencesErrorSource by mutableStateOf(UiPreferenceErrorSource.GENERAL)
        private set
    var state by mutableStateOf(VaultUiState())
        private set
    internal var clipboardDuty by mutableStateOf<ClipboardDuty?>(null)
        private set
    internal var clipboardField by mutableStateOf(ClipboardField.TEXT)
        private set
    internal var clipboardFeedback by mutableStateOf<ClipboardFeedbackMessage?>(null)
        private set
    private var clipboardFeedbackId = 0L
    private var clipboardHost = 0L
    private var clipboardHostQuery: (() -> Boolean)? = null
    private var biometricHost = 0L
    private var biometricAuthenticate: (suspend (Long, Cipher, VaultBiometricPurpose, () -> Boolean) -> VaultBiometricAuthentication)? = null
    private var biometricCancel: ((Long) -> Unit)? = null
    private var biometricCapabilityQuery: (() -> Int)? = null
    private var biometricTextQuery: (() -> BiometricText)? = null
    internal var biometricText by mutableStateOf(BiometricText())
        private set
    private var biometricEligible: (() -> Boolean)? = null
    private var vaultSecurityJob: Job? = null
    private var vaultSecurityRun = 0L
    @Volatile private var vaultSecurityCancelled = false
    internal var biometricCapability by mutableIntStateOf(BiometricManager.BIOMETRIC_ERROR_HW_UNAVAILABLE)
        private set
    private var clipboardHostEligible = false
    private var copyIntent = 0L
    private var copyReadJob: Job? = null
    private val clipboardController = ClipboardController(viewModelScope, clipboardTransport::clearPrimaryClip,
        onChanged = { clipboardDuty = it }, restoreEligible = ::clipboardHostQualified,
        onClearAttempt = { result ->
            val failed = result == ClipboardClearResult.FAILED
            showClipboardFeedback(UiText(if (failed) app.cangoo.android.R.string.clear_failed else app.cangoo.android.R.string.clear_attempted), retryClear = failed)
        })

    private fun showClipboardFeedback(text: UiText, retryClear: Boolean = false) {
        if (foreground && contentVisible && clipboardHostQualified() &&
            (state.unlocked || state.page in listOf(Page.CREATE, Page.RENAME, Page.SECURITY))) {
            clipboardFeedback = ClipboardFeedbackMessage(++clipboardFeedbackId, text, SystemClock.elapsedRealtime(), retryClear)
        }
    }

    internal fun dismissClipboardFeedback(id: Long) {
        if (clipboardFeedback?.id == id) clipboardFeedback = null
    }

    internal fun bindClipboardHost(qualified: () -> Boolean): Long {
        clipboardHostQuery = qualified
        clipboardHostEligible = false
        return ++clipboardHost
    }

    internal fun unbindClipboardHost(host: Long) {
        if (host != clipboardHost) return
        clipboardHostQuery = null
        clipboardHostEligible = false
        clipboardHost++
    }

    internal fun observeClipboardHost(host: Long) {
        if (host != clipboardHost) return
        val eligible = clipboardHostQualified()
        if (eligible && !clipboardHostEligible) clipboardController.onForegroundRestore(true)
        clipboardHostEligible = eligible
    }

    private fun clipboardHostQualified(): Boolean = try { clipboardHostQuery?.invoke() == true } catch (_: Exception) { false }

    internal fun frameworkClipboard(page: Page, vaultId: String?, input: Long): ClipboardPublisher {
        val permission = generation
        return clipboardPublisher(ClipboardField.TEXT) {
            permission == generation && input == inputGeneration && state.page == page && state.vault?.id == vaultId &&
                foreground && contentVisible && !state.busy && !expireIfNeeded() && clipboardHostQualified()
        }
    }

    private fun clipboardPublisher(field: ClipboardField, qualified: () -> Boolean) = ClipboardPublisher(
        clipboardTransport, qualified, onFailure = { if (qualified()) showClipboardFeedback(UiText(app.cangoo.android.R.string.copy_failed)) },
        onPrepared = {
            // 框架只在实际准备发布时撤旧读取；创建适配或重组不是复制请求。
            if (field == ClipboardField.TEXT) beginCopyIntent()
            clipboardField = field
            clipboardController.prepare(it, uiPreferences.clipboardSeconds)
        },
        onConfirmed = { clipboardController.confirm(it); showClipboardFeedback(UiText(app.cangoo.android.R.string.copied)) },
    )

    internal fun clearClipboard() {
        if (foreground && contentVisible && clipboardHostQualified() && onUserInteraction()) {
            beginCopyIntent()
            clipboardController.manualClear()
        }
    }

    private fun beginCopyIntent(): Long {
        copyReadJob?.cancel()
        copyReadJob = null
        return ++copyIntent
    }

    internal val exitConfirmation = ExitConfirmation()

    internal fun onExplicitExit() { updates.close(); clearDirectTransfer(); if (backupState.source == BackupSource.TRANSFER) clearBackup(); exitConfirmation.cancel(); stopRecordStrength(); stopStrength(); cancelVaultSecurityInternal(); beginCopyIntent(); clipboardController.close(); clipboardFeedback = null }

    internal fun bindBiometricHost(
        authenticate: suspend (Long, Cipher, VaultBiometricPurpose, () -> Boolean) -> VaultBiometricAuthentication,
        cancel: (Long) -> Unit, capability: () -> Int, eligible: () -> Boolean, strings: () -> BiometricText,
    ): Long {
        cancelVaultSecurityInternal()
        biometricAuthenticate = authenticate
        biometricCancel = cancel
        biometricCapabilityQuery = capability
        biometricTextQuery = strings
        biometricEligible = eligible
        refreshBiometricPresentation()
        return ++biometricHost
    }

    internal fun unbindBiometricHost(host: Long) {
        if (host != biometricHost) return
        cancelVaultSecurityInternal()
        biometricAuthenticate = null; biometricCancel = null
        biometricCapabilityQuery = null; biometricTextQuery = null; biometricText = BiometricText(); biometricEligible = null
        biometricCapability = BiometricManager.BIOMETRIC_ERROR_HW_UNAVAILABLE
        biometricHost++
    }

    private fun refreshBiometricPresentation() {
        biometricCapability = runCatching { biometricCapabilityQuery?.invoke() }.getOrNull() ?: BiometricManager.BIOMETRIC_ERROR_HW_UNAVAILABLE
        biometricText = runCatching { biometricTextQuery?.invoke() }.getOrNull() ?: BiometricText()
    }

    private fun cancelVaultSecurityInternal() {
        vaultSecurityCancelled = true
        biometricCancel?.invoke(vaultSecurityRun)
    }

    internal fun cancelVaultSecurity() {
        if (!onUserInteraction() || vaultSecurityJob == null) return
        cancelVaultSecurityInternal()
    }

    init {
        try { uiPreferences = uiPreferencesStore.read() }
        catch (_: Exception) { uiPreferencesFailure = UiText(app.cangoo.android.R.string.preferences_read_failed) }
        try { securitySettings = settingsStore.read() }
        catch (_: Exception) {
            securitySettings = SecuritySettings(lockOnLeave = true)
            securitySettingsFailure = UiText(app.cangoo.android.R.string.security_read_failed)
        }
        loadVaults(restoreLast = true)
    }

    fun onForeground() {
        foreground = true
        expireGeneratedIfNeeded()
        refreshBiometricPresentation()
        // 恢复呈现前同步清理到期状态，不能先更新时间或显示旧页面。
        if (!expireIfNeeded()) { directTransfer?.recheckDeadline(); scheduleIdleLock(); startReadyExport() }
        refreshSystemAccess()
    }

    fun onBackground() {
        exitConfirmation.cancel()
        systemAccessJob?.cancel()
        if (!foreground) return
        foreground = false
        contentVisible = false
        clipboardFeedback = null
        cancelVaultSecurityInternal()
        stopRecordSecrets()
        state = state.copy(passwordShown = false, secretDraft = state.secretDraft.copy(totpShown = false, recoveryShown = false))
        stopRecordStrength()
        stopStrength()
        stopBackupWork()
        clearBackupDetail()
        if (!transferProtected()) { if (securitySettings.lockOnLeave) lock() else expireIfNeeded() }
    }

    fun onScreenOff() {
        foreground = false
        contentVisible = false
        lock()
    }

    // 呈现资格仍由宿主提供；Compose 只同步成功组合后的许可与销毁事件。
    fun observeContentVisible(visible: Boolean) {
        val allowed = visible && foreground
        if (!allowed) exitConfirmation.cancel()
        if (contentVisible == allowed) { if (allowed) { startTotp(); startReadyTransfer() }; return }
        contentVisible = allowed
        if (!allowed) clipboardFeedback = null
        if (contentVisible) { startTotp(); wakeRecordStrength(); startReadyExport(); startReadyTransfer(); showReceivedTransfer() } else {
            if (backupState.reading) stopBackupWork()
            clearBackupDetail()
            stopRecordStrength()
            stopRecordSecrets()
            stopStrength()
        }
    }

    fun onUserInteraction(): Boolean {
        exitConfirmation.cancel()
        return observeUserInteraction()
    }

    // 宿主原始输入也包含返回手势，不能在导航处理前取消该手势的确认资格。
    internal fun observeUserInteraction(): Boolean {
        if (!foreground) return false
        expireGeneratedIfNeeded()
        if (!transferProtected() && !idleDeadline.interact(SystemClock.elapsedRealtime(), securitySettings.idleMinutes)) {
            lock()
            return false
        }
        scheduleIdleLock()
        viewModelScope.launch { wakeRecordStrength() }
        return true
    }

    fun openSecuritySettings() {
        if (!onUserInteraction() || state.busy || state.page !in listOf(Page.VAULTS, Page.LOCKED, Page.SETTINGS)) return
        securityReturn = state.page
        state = state.copy(page = Page.SECURITY, master = "", passwordShown = false, error = UiText.Empty, notice = UiText.Empty)
    }

    internal fun openSystemAccess() {
        if (!onUserInteraction() || state.busy || state.page !in listOf(Page.SETTINGS, Page.SECURITY)) return
        systemAccessReturn = state.page
        inputGeneration++
        systemAccessSnapshot = null
        state = state.copy(page = Page.SYSTEM_ACCESS, error = UiText.Empty, notice = UiText.Empty)
        refreshSystemAccess()
    }

    internal fun refreshSystemAccess() {
        if (!foreground || (systemGuideVisible && state.busy) || (!systemGuideVisible && state.page != Page.SYSTEM_ACCESS)) return
        systemAccessJob?.cancel()
        systemAccessSnapshot = null
        val permission = generation
        val input = inputGeneration
        val guide = systemGuideVisible
        val capability = biometricCapability
        val biometricName = biometricText.settingName
        systemAccessJob = viewModelScope.launch {
            val result = withContext(Dispatchers.IO) { readSystemAccess(getApplication(), capability, biometricName) }
            if (permission == generation && input == inputGeneration && foreground && guide == systemGuideVisible &&
                (guide || state.page == Page.SYSTEM_ACCESS)) systemAccessSnapshot = result
        }
    }

    internal fun prepareSystemSettings(): Boolean =
        (systemGuideVisible || state.page == Page.SYSTEM_ACCESS) && contentVisible && onUserInteraction()

    internal fun finishSystemGuide() {
        if (!systemGuideVisible || !foreground || !contentVisible) return
        onUserInteraction()
        systemGuideVisible = false
        systemAccessJob?.cancel()
        viewModelScope.launch(NonCancellable) {
            try { withContext(Dispatchers.IO) { systemGuideStore.complete() } }
            catch (_: Exception) {
                if (state.page == Page.VAULTS) state = state.copy(notice = UiText(R.string.guide_write_failed))
            }
        }
    }

    fun openAppearance() = edit {
        if (page in listOf(Page.SETTINGS, Page.SECURITY)) {
            preferenceReturn = page
            inputGeneration++
            copy(page = Page.APPEARANCE, error = UiText.Empty, notice = UiText.Empty)
        } else this
    }

    internal fun openHelp(input: Long) {
        if (input != inputGeneration || state.page !in listOf(Page.SETTINGS, Page.SECURITY) || state.busy || !onUserInteraction()) return
        preferenceReturn = state.page
        inputGeneration++
        state = state.copy(page = Page.HELP, error = UiText.Empty, notice = UiText.Empty)
    }

    internal fun openBackup() {
        if (!onUserInteraction() || state.busy || !state.unlocked || state.page !in listOf(Page.SETTINGS, Page.TOOLS)) return
        stopRecordStrength()
        backupReturn = state.page
        clearBackup()
        inputGeneration++
        state = state.copy(page = Page.BACKUP, error = UiText.Empty, notice = UiText.Empty)
    }

    internal fun openDirectTransfer() {
        if (!onUserInteraction() || state.busy || !state.unlocked || state.page !in setOf(Page.SETTINGS, Page.SECURITY, Page.TOOLS)) return
        stopRecordStrength()
        clearBackup()
        clearDirectTransfer()
        inputGeneration++
        state = state.copy(page = Page.TRANSFER, error = UiText.Empty, notice = UiText.Empty)
        createDirectTransfer()
    }

    private fun createDirectTransfer() {
        val vault = state.vault ?: return
        val permission = generation
        var receivedPreviewId: String? = null
        fun sessionCurrent() = permission == generation && state.vault?.id == vault.id && state.unlocked
        fun current() = sessionCurrent() && state.page == Page.TRANSFER
        directTransfer = DirectTransferController(getApplication(), viewModelScope, vault.name,
            qualified = { current() || sessionCurrent() && state.page == Page.BACKUP && backupState.source == BackupSource.TRANSFER &&
                receivedPreviewId != null && backupState.preview?.id == receivedPreviewId },
            interact = { current() && contentVisible && onUserInteraction() },
            transferHold = { held -> setTransferHold(permission, vault.id, held) },
            exportSnapshot = { selected, qualified -> store.exportTransferSnapshot(vault.id, selected, qualified) },
            receiveSnapshot = { encoded, selected, passwords, notes, qualified ->
                val preview = store.previewReceivedSnapshot(vault.id, encoded, selected, passwords, notes, qualified)
                if (current() && qualified()) {
                    receivedPreviewId = preview.id
                    pendingTransferPreview = preview
                    transferSourceName = directTransfer?.state?.peerName.orEmpty()
                } else store.discardImport(preview.id)
            }, received = ::showReceivedTransfer)
    }

    internal fun closeDirectTransfer() {
        if (state.page != Page.TRANSFER || !onUserInteraction()) return
        directTransfer?.close()
        clearDirectTransfer()
        clearBackup()
        inputGeneration++
        state = state.copy(page = Page.SETTINGS, error = UiText.Empty, notice = UiText.Empty)
        wakeRecordStrength()
    }

    internal fun directTransferPermission(controller: DirectTransferController, granted: Boolean) {
        if (directTransfer !== controller || state.page != Page.TRANSFER || !state.unlocked) return
        if (!granted) controller.permissionDenied()
        else { pendingTransferStart = controller; startReadyTransfer() }
    }

    private fun startReadyTransfer() {
        val controller = pendingTransferStart ?: return
        if (!foreground || !contentVisible || directTransfer !== controller || state.page != Page.TRANSFER || !state.unlocked) return
        pendingTransferStart = null
        controller.start()
    }

    private fun clearDirectTransfer() {
        val controller = directTransfer
        directTransfer = null
        transferHoldOwner = null
        pendingTransferStart = null
        pendingTransferPreview?.let { store.discardImport(it.id) }
        pendingTransferPreview = null
        transferSourceName = ""
        controller?.close()
    }

    private fun showReceivedTransfer() {
        val preview = pendingTransferPreview
        if (preview == null) {
            directTransfer?.takeIf { it.state.phase == DirectTransferPhase.RECEIVED && !it.hasActiveTask }?.let {
                it.close(); directTransfer = null
            }
            return
        }
        if (!foreground || !contentVisible || !state.unlocked || state.page != Page.TRANSFER ||
            directTransfer?.state?.phase != DirectTransferPhase.RECEIVED || expireIfNeeded()) return
        val source = transferSourceName
        pendingTransferPreview = null
        inputGeneration++
        backupReturn = Page.SETTINGS
        val kind = if (preview.passwordCount > 0) BackupImportKind.PASSWORD else BackupImportKind.NOTE
        backupState = BackupUiState(step = BackupStep.PREVIEW, source = BackupSource.TRANSFER, documentName = source,
            preview = preview, previewKind = kind, planSummary = preview.initialSummary)
        state = state.copy(page = Page.BACKUP, error = UiText.Empty, notice = UiText.Empty)
        backupPage(kind, 0, inputGeneration)
        directTransfer?.takeIf { !it.hasActiveTask }?.let { it.close(); directTransfer = null }
    }

    private fun transferProtected(): Boolean = transferHoldOwner?.let { (permission, vaultId) ->
        permission == generation && state.unlocked && state.vault?.id == vaultId
    } == true

    private fun setTransferHold(permission: Long, vaultId: String, held: Boolean): Boolean {
        fun current() = permission == generation && state.unlocked && state.vault?.id == vaultId
        if (held) {
            if (!current() || expireIfNeeded()) return false
            transferHoldOwner = permission to vaultId
            idleJob?.cancel()
            idleDeadline.clear()
        } else if (transferHoldOwner == (permission to vaultId)) {
            transferHoldOwner = null
            if (!current()) return false
            if (!foreground && securitySettings.lockOnLeave) { lock(); return false }
            idleDeadline.interact(SystemClock.elapsedRealtime(), securitySettings.idleMinutes)
            scheduleIdleLock()
        }
        return current()
    }

    internal fun beginBackup(kind: BackupDocumentKind, input: Long) {
        if (!backupMatches(input) || state.busy || !onUserInteraction()) return
        clearBackup()
        inputGeneration++
        backupState = BackupUiState(step = if (kind == BackupDocumentKind.EXPORT) BackupStep.EXPORT else BackupStep.IMPORT)
        state = state.copy(error = UiText.Empty, notice = UiText.Empty)
    }

    private fun validExportPassword(): Boolean {
        val password = backupState.password
        val message = when {
            password.isEmpty() -> UiText(R.string.backup_password_required)
            backupState.confirmation.isEmpty() -> UiText(R.string.backup_confirmation_required)
            password != backupState.confirmation -> UiText(R.string.backup_password_mismatch)
            else -> try { app.cangoo.android.data.validatedUtf8(password, 1024, 4096).fill(0); UiText.Empty }
                catch (_: VaultException) { UiText(R.string.backup_password_invalid) }
        }
        if (message.isNotEmpty()) state = state.copy(error = message, notice = UiText.Empty)
        return message.isEmpty()
    }

    internal fun prepareDocumentSelection(kind: BackupDocumentKind, input: Long): BackupDocumentIntent? {
        if (!backupMatches(input) || state.busy || !onUserInteraction() ||
            backupState.step != if (kind == BackupDocumentKind.EXPORT) BackupStep.EXPORT else BackupStep.IMPORT) return null
        if (kind == BackupDocumentKind.EXPORT && (exportSelectionPending || !validExportPassword())) return null
        val vaultId = state.vault?.id ?: return null
        val configuration = backupState
        clearBackup(keepStep = true)
        if (kind == BackupDocumentKind.EXPORT) backupState = configuration.copy(documentName = "")
        inputGeneration++
        val next = BackupDocumentIntent(kind, vaultId, UUID.randomUUID().toString())
        documentIntent = next
        if (kind == BackupDocumentKind.EXPORT) exportTargets[next.requestId] = ExportTarget(next, configuration.scope, generation)
        state = state.copy(error = UiText.Empty, notice = UiText.Empty)
        return next
    }

    internal fun onDocumentResult(result: BackupDocumentIntent, outcome: BackupDocumentOutcome) {
        if (result.kind == BackupDocumentKind.EXPORT) {
            val target = exportTargets[result.requestId]?.takeIf { it.request.vaultId == result.vaultId } ?: return
            if (target.received) return
            target.received = true
            val expected = documentIntent?.requestId == result.requestId
            if (outcome != BackupDocumentOutcome.SELECTED || result.uri == null) {
                exportTargets.remove(result.requestId)
                if (expected) {
                    documentIntent = null
                    state = state.copy(notice = if (outcome == BackupDocumentOutcome.CANCELED) UiText(R.string.file_cancelled) else UiText.Empty,
                        error = if (outcome == BackupDocumentOutcome.LAUNCH_FAILED) UiText(R.string.file_picker_failed) else UiText.Empty)
                }
                return
            }
            target.uri = result.uri
            if (exportTargets.values.any { it !== target && it.uri == result.uri }) target.owns = false
            if (expected) documentIntent = result
            else target.abandoned = true
            // 元数据认领不读库；先拿证明再处理放弃，避免取消与结果交付之间丢清理责任。
            viewModelScope.launch(NonCancellable, start = CoroutineStart.UNDISPATCHED) {
                try {
                    target.mutex.withLock {
                        target.created = withContext(Dispatchers.IO) {
                            store.claimBackupDestination(result.uri, result.requestId, target.token) { target.owns }
                        }
                        val created = target.created!!
                        val key = created.device to created.inode
                        val owner = exportFileOwners[key]
                        if (owner != null && owner !== target) {
                            target.owns = false
                            error("该文件已有本次进程的在途归属")
                        }
                        exportFileOwners[key] = target
                        check(created.displayName.isNotEmpty())
                    }
                    if (target.abandoned || backupOwnerClosed) abandonExport(target)
                    else if (documentIntent?.requestId == result.requestId) {
                        backupState = backupState.copy(documentName = target.created!!.displayName)
                        if (target.permission != generation) target.autoStart = false
                        if (state.unlocked && state.page == Page.BACKUP) {
                            state = state.copy(notice = if (target.autoStart) UiText.Empty else UiText(R.string.backup_password_again), error = UiText.Empty)
                        }
                        startReadyExport()
                    }
                } catch (_: Exception) {
                    target.abandoned = true
                    val cleanup = cleanupExport(target)
                    if (!backupOwnerClosed && documentIntent?.requestId == result.requestId) {
                        documentIntent = null
                        val message = when (cleanup) {
                            BackupDocumentCleanup.DELETED -> UiText(R.string.backup_target_cleaned)
                            BackupDocumentCleanup.PUBLISHED -> UiText(R.string.backup_saved)
                            null -> UiText(R.string.backup_location_unverified)
                            else -> cleanup.uiText()
                        }
                        state = if (state.unlocked && state.page == Page.BACKUP) state.copy(error = message)
                            else state.copy(notice = message)
                    }
                }
            }
            return
        }
        val expected = documentIntent
        if (expected == null || expected.requestId != result.requestId || expected.kind != result.kind || expected.vaultId != result.vaultId) return
        // 导入仍只接关联；认证且用户明确继续后才读取文件。
        if (outcome == BackupDocumentOutcome.SELECTED && result.uri != null) {
            documentIntent = expected.copy(uri = result.uri)
            backupState = backupState.copy(documentName = "")
            state = state.copy(notice = if (state.unlocked) UiText(R.string.file_ready)
                else UiText(R.string.file_ready_locked), error = UiText.Empty)
        } else {
            documentIntent = null
            backupState = backupState.copy(documentName = "")
            state = state.copy(notice = if (outcome == BackupDocumentOutcome.CANCELED) UiText(R.string.file_cancelled) else UiText.Empty,
                error = if (outcome == BackupDocumentOutcome.LAUNCH_FAILED) UiText(R.string.file_picker_failed) else UiText.Empty)
        }
    }

    internal fun changeBackup(input: Long, change: BackupUiState.() -> BackupUiState) {
        if (!backupMatches(input) || state.busy || !onUserInteraction()) return
        if (exportSelectionPending) return
        backupState = backupState.change().let { changed -> currentExport()?.let { changed.copy(scope = it.scope) } ?: changed }
        state = state.copy(error = UiText.Empty, notice = UiText.Empty)
    }

    private fun backupMatches(input: Long): Boolean = input == inputGeneration && state.page == Page.BACKUP && state.unlocked

    internal fun confirmBackupDocument(input: Long) {
        val intent = documentIntent?.takeIf { it.uri != null && it.vaultId == state.vault?.id } ?: return
        backupWork(input) { qualified ->
            val name = store.backupDocumentName(intent.vaultId, intent.uri!!, qualified)
            val apply: () -> Unit = { backupState = backupState.copy(documentName = name) }
            apply
        }
    }

    private fun stopBackupWork() {
        backupRun++
        val running = backupJob?.isActive == true
        backupJob?.cancel()
        backupJob = null
        if (running) state = state.copy(busy = false)
        backupState = backupState.copy(reading = false)
    }

    private fun clearBackupDetail() {
        if (backupState.detail != null && backupState.reading) stopBackupWork()
        backupState = backupState.copy(detail = null, candidates = emptyList(), candidateSourceIndex = null,
            comparison = null, comparisonTargetId = null, choosingTarget = false, fieldRequest = null, fieldPair = null, expandedField = null,
            batchReview = null, commitReview = null,
            candidateOffset = 0, text = "", textRequest = null, textOffset = 0, textRequestedOffset = 0, textNextOffset = 0, textComplete = true, readError = UiText.Empty)
    }

    internal fun openBackupDetail(index: Int, input: Long, expectedKind: BackupImportKind) {
        if (!backupMatches(input) || state.busy || backupState.step != BackupStep.PREVIEW ||
            expectedKind != backupState.previewKind ||
            backupState.rows.none { it.sourceIndex == index } || !onUserInteraction()) return
        clearBackupDetail()
        backupState = backupState.copy(detail = BackupDetail(backupState.previewKind, index, ++backupDetailRun))
    }

    internal fun closeBackupDetail(token: Long) {
        if (backupState.detail?.token != token || !onUserInteraction()) return
        clearBackupDetail()
        backupPage(backupState.previewKind, backupState.currentGroup.offset, inputGeneration)
    }

    internal fun closeBackupText(token: Long) {
        if (backupState.detail?.token != token || !onUserInteraction()) return
        if (backupState.reading) stopBackupWork()
        backupState = backupState.copy(text = "", textRequest = null, textOffset = 0, textRequestedOffset = 0, textNextOffset = 0,
            textComplete = true, readError = UiText.Empty)
    }

    internal fun backupComparison(targetId: String?, input: Long, token: Long) {
        val preview = backupState.preview ?: return
        val vaultId = state.vault?.id ?: return
        val detail = backupState.detail?.takeIf { it.token == token } ?: return
        if (!backupMatches(input) || state.busy || !onUserInteraction()) return
        backupState = backupState.copy(comparison = null, comparisonTargetId = targetId, fieldRequest = null, fieldPair = null, expandedField = null,
            text = "", textRequest = null)
        backupWork(input, reading = true, refreshPlan = backupState.planSummary == null) { qualified ->
            val row = backupState.rows.first { it.sourceIndex == detail.sourceIndex }
            val group = backupState.groupStates[detail.kind] ?: BackupGroupUiState()
            val chosen = targetId ?: group.comparisonTargets[detail.sourceIndex] ?:
                if (detail.kind == BackupImportKind.NOTE) backupState.decisions.notes[detail.sourceIndex]?.targetId else null
            val candidateOffset = if (backupState.candidateSourceIndex == detail.sourceIndex) backupState.candidateOffset else 0
            val candidates = if (detail.kind == BackupImportKind.NOTE) store.readImportCandidates(vaultId, preview.id, detail.sourceIndex, candidateOffset, qualified = qualified) else emptyList()
            val comparison = if (detail.kind == BackupImportKind.NOTE && row.candidateCount > 1 && chosen == null && !row.alreadyExists) null
                else store.readImportComparison(vaultId, preview.id, detail.kind, detail.sourceIndex, chosen, qualified)
            val targets = comparison?.targetId?.let { group.comparisonTargets + (detail.sourceIndex to it) } ?: group.comparisonTargets
            val apply: () -> Unit = { backupState = backupState.copy(comparison = comparison, comparisonTargetId = comparison?.targetId,
                choosingTarget = comparison == null && detail.kind == BackupImportKind.NOTE,
                candidates = candidates, candidateSourceIndex = if (detail.kind == BackupImportKind.NOTE) detail.sourceIndex else null,
                candidateOffset = candidateOffset, groupStates = backupState.groupStates + (detail.kind to group.copy(comparisonTargets = targets))) }
            apply
        }
    }

    internal fun backupField(field: BackupComparisonField, offset: Int, input: Long, token: Long) {
        val preview = backupState.preview ?: return
        val vaultId = state.vault?.id ?: return
        val detail = backupState.detail?.takeIf { it.token == token } ?: return
        val comparison = backupState.comparison ?: return
        if (!backupMatches(input) || state.busy || !onUserInteraction() || comparison.fields.none { it.field == field }) return
        val targetId = comparison.targetId
        // 一次只保留一个字段的成对值；重读失败也不能留下旧半边。
        backupState = backupState.copy(fieldPair = null, fieldRequest = BackupFieldRequest(field, offset, targetId), readError = UiText.Empty)
        backupWork(input, reading = true) { qualified ->
            val pair = store.readImportFieldPair(vaultId, preview.id, detail.kind, detail.sourceIndex, targetId, field, offset, qualified = qualified)
            val apply: () -> Unit = { backupState = backupState.copy(fieldPair = pair) }
            apply
        }
    }

    internal fun hideBackupField(token: Long) {
        if (backupState.detail?.token != token || !onUserInteraction()) return
        if (backupState.reading) stopBackupWork()
        backupState = backupState.copy(fieldRequest = null, fieldPair = null, expandedField = null, readError = UiText.Empty)
    }

    internal fun openBackupLongText(field: BackupComparisonField, input: Long, token: Long) {
        if (field != BackupComparisonField.NOTES || !backupMatches(input) || state.busy || !onUserInteraction() ||
            backupState.detail?.token != token || backupState.comparison?.fields?.none { it.field == field } != false) return
        backupState = backupState.copy(expandedField = field)
        backupField(field, 0, input, token)
    }

    internal fun closeBackupLongText(token: Long) {
        if (backupState.expandedField == null) return
        hideBackupField(token)
    }

    internal fun closeBackupCandidates(token: Long) {
        if (backupState.detail?.token != token || !onUserInteraction() || backupState.comparison == null) return
        if (backupState.reading) stopBackupWork()
        backupState = backupState.copy(choosingTarget = false, fieldPair = null, fieldRequest = null, expandedField = null, readError = UiText.Empty)
    }

    private fun clearBackup(keepStep: Boolean = false, keepDocument: Boolean = false) {
        if (backupState.source == BackupSource.TRANSFER) clearDirectTransfer()
        stopBackupWork()
        store.discardImport()
        val target = currentExport()
        if (!keepDocument && target != null) abandonExport(target)
        if (keepDocument && target != null) target.autoStart = false
        backupState = BackupUiState(step = if (keepStep) backupState.step else BackupStep.HOME,
            scope = if (keepDocument) target?.scope ?: BackupScope.ALL else BackupScope.ALL)
        if (!keepDocument) documentIntent = null
    }

    internal fun openVaultDeletion(id: String, input: Long, origin: Page) {
        if (input != inputGeneration || state.page != origin || origin !in listOf(Page.VAULTS, Page.LOCKED, Page.VAULT_MANAGEMENT) ||
            state.busy || !onUserInteraction()) return
        val target = state.vaults.firstOrNull { it.id == id } ?: return
        clearBackup()
        deletionReturn = origin
        inputGeneration++
        deletionState = VaultDeletionUiState(target = target)
        state = state.copy(page = Page.VAULT_DELETE, master = "", passwordShown = false, error = UiText.Empty, notice = UiText.Empty)
    }

    internal fun updateDeletionMaster(value: String, input: Long) {
        if (input != inputGeneration || state.page != Page.VAULT_DELETE || state.busy || !onUserInteraction()) return
        deletionState = deletionState.copy(master = value, preview = null)
        state = state.copy(error = UiText.Empty, notice = UiText.Empty)
    }

    internal fun authenticateDeletion(input: Long) {
        if (input != inputGeneration || state.page != Page.VAULT_DELETE || state.busy || !onUserInteraction()) return
        val target = deletionState.target ?: return
        val master = deletionState.master
        val permission = generation
        var obtained: DeletionPreview? = null
        perform(onCommitted = { deletionState = deletionState.copy(preview = obtained) }) {
            obtained = store.prepareVaultDeletion(target.id, master) { foreground && permission == generation && input == inputGeneration && state.page == Page.VAULT_DELETE }
            state.copy(error = UiText.Empty, notice = UiText.Empty)
        }
    }

    internal fun confirmDeletion(input: Long) {
        if (input != inputGeneration || state.page != Page.VAULT_DELETE || state.busy || !onUserInteraction()) return
        val preview = deletionState.preview ?: return
        if (preview.id != deletionState.target?.id) return
        val master = deletionState.master
        val permission = generation
        var completion: VaultDeletionResult? = null
        perform(onCommitted = {
            completion?.let { completed ->
                deletionState = if (completed.outcome.status == DeletionStatus.NOT_REMOVED) deletionState.copy(master = "", preview = null) else VaultDeletionUiState()
                val removedSelected = completed.outcome.status in listOf(DeletionStatus.REMOVED, DeletionStatus.REMOVED_RESIDUAL) && state.vault?.id == preview.id
                if (completed.currentSessionClosed || completed.outcome.status == DeletionStatus.UNCERTAIN || removedSelected) {
                    lock(if (completed.outcome.status == DeletionStatus.NOT_REMOVED) state.vault else null)
                    state = state.copy(notice = completed.outcome.uiText())
                }
            }
        }) {
            val result = store.confirmVaultDeletion(preview, master) { foreground && permission == generation && input == inputGeneration && state.page == Page.VAULT_DELETE }
            completion = result
            val vaults = try { store.listVaults() }
            catch (canceled: CancellationException) { throw canceled }
            catch (_: Exception) {
                if (result.outcome.status in listOf(DeletionStatus.REMOVED, DeletionStatus.REMOVED_RESIDUAL)) state.vaults.filter { it.id != preview.id }
                else emptyList()
            }
            state.copy(page = if (result.outcome.status == DeletionStatus.NOT_REMOVED) Page.VAULT_DELETE else deletionReturn,
                vaults = vaults, notice = result.outcome.uiText())
        }
    }

    private fun backupError(error: Exception): UiText = when (error) {
        is BackupDocumentException -> error.uiText()
        is VaultException -> error.code.uiText()
        is BackupStoreException -> error.problem.uiText()
        is BackupProtocolException -> error.problem.uiText()
        is BackupWorkFailure -> error.display
        else -> UiText(R.string.backup_failed)
    }

    private class BackupWorkFailure(val display: UiText, val sessionClosed: Boolean = false) : Exception()

    private fun backupWork(input: Long, reading: Boolean = false, refreshPlan: Boolean = false,
                           operation: suspend (() -> Boolean) -> (() -> Unit)) {
        if (!backupMatches(input) || state.busy || !onUserInteraction()) return
        stopRecordStrength()
        val vaultId = state.vault?.id ?: return
        val permission = generation
        val run = ++backupRun
        val previewId = backupState.preview?.id
        val detail = backupState.detail
        fun qualified() = foreground && contentVisible && permission == generation && run == backupRun &&
            input == inputGeneration && state.page == Page.BACKUP && state.unlocked && state.vault?.id == vaultId &&
            (!reading || backupState.preview?.id == previewId && backupState.detail == detail)
        backupState = if (reading && detail == null) backupState.copy(reading = true, listReadError = UiText.Empty)
            else backupState.copy(reading = reading, readError = UiText.Empty)
        state = state.copy(busy = true, error = UiText.Empty, notice = UiText.Empty)
        backupJob = viewModelScope.launch {
            try {
                val apply = operation(::qualified)
                if (qualified() && !expireIfNeeded()) {
                    apply()
                    if (refreshPlan) {
                        val preview = backupState.preview
                        val decisions = backupState.decisions
                        if (preview != null) {
                            val summary = store.summarizeImportDecisions(vaultId, preview.id, decisions, ::qualified)
                            if (qualified() && !expireIfNeeded() && backupState.preview?.id == preview.id && backupState.decisions == decisions)
                                backupState = backupState.copy(planSummary = summary)
                        }
                    }
                }
            } catch (canceled: CancellationException) { throw canceled }
            catch (error: Exception) {
                if (run == backupRun && permission == generation && state.page == Page.BACKUP) {
                    if (refreshPlan || error is BackupDocumentException ||
                        error is BackupStoreException && error.problem == BackupStoreProblem.STALE ||
                        error is VaultException && error.code in setOf(VaultError.DATA_UNAVAILABLE, VaultError.STORAGE_FAILED))
                        backupState = backupState.copy(planSummary = null)
                    val message = backupError(error)
                    if (error is VaultException && error.code == VaultError.SESSION_CLOSED || error is BackupWorkFailure && error.sessionClosed) lock()
                    if (reading && state.unlocked) backupState = if (detail == null) backupState.copy(listReadError = message)
                        else backupState.copy(readError = message)
                    else state = state.copy(error = message)
                }
            } finally {
                if (run == backupRun) {
                    backupJob = null
                    state = state.copy(busy = false)
                    backupState = backupState.copy(reading = false)
                }
            }
        }
    }

    internal fun exportBackup(input: Long) {
        val intent = documentIntent?.takeIf { it.kind == BackupDocumentKind.EXPORT && it.uri != null && it.vaultId == state.vault?.id } ?: return
        val target = currentExport()?.takeIf { !it.abandoned && it.owns && it.created != null && it.cleanup == null } ?: return
        if (!backupMatches(input) || backupState.step != BackupStep.EXPORT || backupState.documentName.isEmpty() || !validExportPassword()) return
        val password = backupState.password
        val permission = generation
        val scope = target.scope
        target.autoStart = false
        backupWork(input) { qualified ->
            val privateCleanup = AtomicReference<BackupPrivateCleanup?>()
            val recordWrite = AtomicReference<LocalBackupRecordWrite?>()
            try {
                val result = target.mutex.withLock {
                    val destination = requireNotNull(target.created)
                    store.exportBackup(intent.vaultId, scope, password, destination,
                        qualified = { qualified() && !target.abandoned && target.owns },
                        stillOwned = { it === target.created && target.owns },
                        onPrivateCleanup = { privateCleanup.set(it) }, onLocalRecordWrite = { recordWrite.set(it) })
                }
                val apply: () -> Unit = {
                    backupState = BackupUiState()
                    state = state.copy(localBackupRecordLabel = localBackupRecordLabel(result.localRecord),
                        notice = UiText(R.string.exported_items, listOf(UiText(R.plurals.password_count, listOf(result.passwordCount), result.passwordCount), UiText(R.plurals.note_count, listOf(result.noteCount), result.noteCount))) + localRecordNotice(result.localRecordWrite) +
                        if (privateCleanup.get() == BackupPrivateCleanup.RESIDUAL) BackupPrivateCleanup.RESIDUAL.uiText() else UiText.Empty)
                }
                apply
            } catch (error: Exception) {
                target.abandoned = true
                // 写入流程已退出非重入互斥，再取得同一目标的唯一清理结果。
                val cleanup = cleanupExport(target)
                if (documentIntent?.requestId == intent.requestId) {
                    documentIntent = null
                    backupState = backupState.copy(documentName = "")
                }
                val detail = (cleanup?.uiText() ?: UiText(R.string.backup_maybe_empty)) + localRecordNotice(recordWrite.get()) +
                    if (privateCleanup.get() == BackupPrivateCleanup.RESIDUAL) BackupPrivateCleanup.RESIDUAL.uiText() else UiText.Empty
                val message = if (cleanup == BackupDocumentCleanup.PUBLISHED) UiText(R.string.backup_saved) + localRecordNotice(recordWrite.get()) +
                    if (privateCleanup.get() == BackupPrivateCleanup.RESIDUAL) BackupPrivateCleanup.RESIDUAL.uiText() else UiText.Empty
                    else UiText(R.string.export_interrupted, listOf(detail))
                if (error is CancellationException) {
                    if (!backupOwnerClosed && permission == generation && input == inputGeneration && state.page == Page.BACKUP &&
                        state.vault?.id == intent.vaultId && (documentIntent == null || documentIntent?.requestId == intent.requestId)) {
                        state = state.copy(notice = message)
                    }
                    throw error
                }
                throw BackupWorkFailure(if (cleanup == BackupDocumentCleanup.PUBLISHED) message else backupError(error) + detail,
                    error is VaultException && error.code == VaultError.SESSION_CLOSED)
            } finally {
                if (target.created?.published == true) {
                    cleanupExport(target)
                    if (documentIntent?.requestId == intent.requestId) documentIntent = null
                }
            }
        }
    }

    internal fun previewBackup(input: Long) {
        val intent = documentIntent?.takeIf { it.kind == BackupDocumentKind.IMPORT && it.uri != null && it.vaultId == state.vault?.id } ?: return
        if (!backupMatches(input) || backupState.step != BackupStep.IMPORT || backupState.documentName.isEmpty()) return
        val password = backupState.password
        backupWork(input) { qualified ->
            val preview = store.previewImport(intent.vaultId, intent.uri!!, password, qualified)
            val kind = if (preview.passwordCount > 0) BackupImportKind.PASSWORD else BackupImportKind.NOTE
            val page = store.queryImportRows(intent.vaultId, preview.id, kind, BackupImportQuery(), BackupImportDecisions(), emptyMap(), emptySet(), 0, qualified = qualified)
            val apply: () -> Unit = {
                backupState = BackupUiState(step = BackupStep.PREVIEW, documentName = backupState.documentName,
                    preview = preview, previewKind = kind, rows = page.rows, pageInfo = page, planSummary = preview.initialSummary)
            }
            apply
        }
    }

    internal fun backupPage(kind: BackupImportKind, offset: Int, input: Long, query: BackupImportQuery? = null) {
        val preview = backupState.preview ?: return
        val vaultId = state.vault?.id ?: return
        if (backupState.detail != null) return
        val group = backupState.groupStates[kind] ?: BackupGroupUiState()
        val requested = query ?: group.query
        backupWork(input, reading = true, refreshPlan = backupState.planSummary == null) { qualified ->
            val page = store.queryImportRows(vaultId, preview.id, kind, requested, backupState.decisions, group.comparisonTargets,
                group.selected, offset, qualified = qualified)
            val apply: () -> Unit = { backupState = backupState.copy(previewKind = kind, offset = page.offset, rows = page.rows, pageInfo = page,
                groupStates = backupState.groupStates + (kind to group.copy(query = requested, offset = page.offset)),
                batchReview = null, commitReview = null, candidateSourceIndex = null, candidates = emptyList(), text = "", textRequest = null, textNextOffset = 0) }
            apply
        }
    }

    internal fun selectBackupKind(kind: BackupImportKind, input: Long) {
        backupPage(kind, backupState.groupStates[kind]?.offset ?: 0, input)
    }

    internal fun filterBackup(expectedKind: BackupImportKind, query: BackupImportQuery, input: Long) {
        if (expectedKind == backupState.previewKind) backupPage(expectedKind, 0, input, query)
    }

    internal fun selectBackupRow(expectedKind: BackupImportKind, index: Int, selected: Boolean, input: Long) {
        if (!backupMatches(input) || expectedKind != backupState.previewKind || state.busy || backupState.detail != null || !onUserInteraction()) return
        if (backupState.rows.none { it.sourceIndex == index && it.decisionRequired }) return
        val group = backupState.currentGroup
        backupState = backupState.copy(groupStates = backupState.groupStates + (backupState.previewKind to group.copy(
            selected = if (selected) group.selected + index else group.selected - index)), batchReview = null, commitReview = null)
    }

    internal fun selectBackupPage(expectedKind: BackupImportKind, expectedIndices: Set<Int>, input: Long) {
        if (!backupMatches(input) || expectedKind != backupState.previewKind || state.busy || backupState.detail != null || !onUserInteraction()) return
        val group = backupState.currentGroup
        val selected = backupState.rows.filter { it.decisionRequired }.mapTo(linkedSetOf()) { it.sourceIndex }
        if (expectedIndices != selected) return
        backupState = backupState.copy(groupStates = backupState.groupStates + (backupState.previewKind to group.copy(selected = group.selected + selected)),
            batchReview = null, commitReview = null)
    }

    internal fun selectBackupFiltered(expectedKind: BackupImportKind, input: Long) {
        val preview = backupState.preview ?: return
        val vaultId = state.vault?.id ?: return
        if (expectedKind != backupState.previewKind || backupState.detail != null) return
        val group = backupState.currentGroup
        val decisions = backupState.decisions
        backupWork(input, reading = true) { qualified ->
            val selected = store.selectImportRows(vaultId, preview.id, expectedKind, group.query, decisions, group.comparisonTargets, qualified)
            val apply: () -> Unit = {
                backupState = backupState.copy(groupStates = backupState.groupStates + (expectedKind to group.copy(selected = group.selected + selected)),
                    batchReview = null, commitReview = null)
            }
            apply
        }
    }

    internal fun refreshBackupPlan(input: Long) {
        if (backupState.preview == null) return
        backupWork(input, reading = true, refreshPlan = true) { { } }
    }

    internal fun clearBackupSelection(expectedKind: BackupImportKind, input: Long) {
        if (!backupMatches(input) || expectedKind != backupState.previewKind || state.busy || backupState.detail != null || !onUserInteraction()) return
        backupState = backupState.copy(groupStates = backupState.groupStates + (backupState.previewKind to backupState.currentGroup.copy(selected = emptySet())),
            pageInfo = backupState.pageInfo?.copy(selectedOutsideFilterCount = 0), batchReview = null, commitReview = null)
    }

    internal fun reviewBackupBatch(expectedKind: BackupImportKind, action: BackupImportBatchAction, input: Long) {
        val preview = backupState.preview ?: return
        val vaultId = state.vault?.id ?: return
        val kind = backupState.previewKind
        val group = backupState.currentGroup
        if (expectedKind != kind || backupState.detail != null || group.selected.isEmpty()) return
        val original = backupState.decisions
        backupWork(input, reading = true) { qualified ->
            val proposal = store.proposeImportBatch(vaultId, preview.id, kind, group.selected, action, original, group.query, group.comparisonTargets, qualified)
            val apply: () -> Unit = { backupState = backupState.copy(batchReview = BackupBatchReview(++backupReviewRun, proposal, original, group.selected), commitReview = null) }
            apply
        }
    }

    internal fun applyBackupBatch(token: Long, acknowledgeRecoveryRemoval: Boolean, input: Long) {
        val review = backupState.batchReview?.takeIf { it.token == token } ?: return
        val proposal = review.proposal
        if (!backupMatches(input) || state.busy || !onUserInteraction() || proposal.previewId != backupState.preview?.id ||
            proposal.kind != backupState.previewKind || review.original != backupState.decisions || review.selected != backupState.currentGroup.selected ||
            proposal.legacyRecoveryRemovalIndices.isNotEmpty() && !acknowledgeRecoveryRemoval) return
        val passwords = proposal.decisions.passwords.mapValues { (index, choice) ->
            if (index in proposal.legacyRecoveryRemovalIndices) choice.copy(acknowledgeRecoveryRemoval = true) else choice
        }
        val decisions = proposal.decisions.copy(passwords = passwords)
        val group = backupState.currentGroup
        val targets = if (proposal.kind == BackupImportKind.NOTE) group.comparisonTargets + proposal.appliedSourceIndices.mapNotNull { index ->
            decisions.notes[index]?.targetId?.let { index to it }
        } else group.comparisonTargets
        backupState = backupState.copy(decisions = decisions, requiredPasswordChoices = decisions.passwords.keys, requiredNoteChoices = decisions.notes.keys,
            groupStates = backupState.groupStates + (proposal.kind to group.copy(comparisonTargets = targets)),
            planSummary = null, batchReview = null, commitReview = null)
        backupPage(proposal.kind, group.offset, input)
    }

    internal fun dismissBackupReview(input: Long) {
        if (!backupMatches(input) || !onUserInteraction()) return
        backupState = backupState.copy(batchReview = null, commitReview = null)
    }

    internal fun reviewBackupCommit(input: Long) {
        if (backupState.detail != null) return
        if (backupMatches(input) && backupState.reading) stopBackupWork()
        val preview = backupState.preview ?: return
        val vaultId = state.vault?.id ?: return
        val decisions = backupState.decisions
        backupWork(input, reading = true) { qualified ->
            val summary = store.summarizeImportDecisions(vaultId, preview.id, decisions, qualified)
            val apply: () -> Unit = {
                backupState = backupState.copy(planSummary = summary)
                if (summary.pending > 0) state = state.copy(error = UiText(R.string.backup_pending_actions,
                    listOf(preview.passwordCount + preview.noteCount, summary.pending)))
                else backupState = backupState.copy(commitReview = BackupCommitReview(++backupReviewRun, summary, decisions), batchReview = null)
            }
            apply
        }
    }

    internal fun confirmBackupCommit(token: Long, input: Long) {
        val review = backupState.commitReview?.takeIf { it.token == token } ?: return
        if (!backupMatches(input) || state.busy || !onUserInteraction() || review.summary.previewId != backupState.preview?.id || review.decisions != backupState.decisions) return
        backupState = backupState.copy(commitReview = null)
        commitBackup(input)
    }

    internal fun chooseBackupPassword(index: Int, choice: PasswordImportChoice, input: Long, token: Long) {
        if (!backupMatches(input) || state.busy || !onUserInteraction() || backupState.previewKind != BackupImportKind.PASSWORD) return
        if (backupState.detail?.let { it.sourceIndex == index && it.token == token } != true) return
        val row = backupState.rows.firstOrNull { it.sourceIndex == index } ?: return
        if (!row.decisionRequired || row.legacyRecoveryWillClear && choice.action == PasswordImportAction.OVERWRITE && !choice.acknowledgeRecoveryRemoval) return
        backupState = backupState.copy(decisions = backupState.decisions.copy(passwords = backupState.decisions.passwords + (index to choice)),
            requiredPasswordChoices = if (row.decisionRequired) backupState.requiredPasswordChoices + index else backupState.requiredPasswordChoices,
            planSummary = null, batchReview = null, commitReview = null)
        refreshBackupPlan(input)
    }

    internal fun chooseBackupNote(index: Int, choice: NoteImportChoice, input: Long, token: Long) {
        if (!backupMatches(input) || state.busy || !onUserInteraction() || backupState.previewKind != BackupImportKind.NOTE) return
        if (backupState.detail?.let { it.sourceIndex == index && it.token == token } != true) return
        val row = backupState.rows.firstOrNull { it.sourceIndex == index } ?: return
        if (!row.decisionRequired) return
        val compared = backupState.comparison?.takeIf { it.sourceIndex == index && it.targetId == choice.targetId && !it.targetReserved }
        if (choice.action == NoteImportAction.OVERWRITE && (compared == null && (backupState.candidateSourceIndex != index ||
            backupState.candidates.none { it.id == choice.targetId && !it.reserved }) || backupState.decisions.notes.any { (source, decision) ->
                source != index && decision.action == NoteImportAction.OVERWRITE && decision.targetId == choice.targetId
            })) return
        backupState = backupState.copy(decisions = backupState.decisions.copy(notes = backupState.decisions.notes + (index to choice)),
            requiredNoteChoices = if (row.decisionRequired) backupState.requiredNoteChoices + index else backupState.requiredNoteChoices,
            groupStates = if (choice.targetId != null) backupState.groupStates + (BackupImportKind.NOTE to backupState.currentGroup.copy(
                comparisonTargets = backupState.currentGroup.comparisonTargets + (index to choice.targetId))) else backupState.groupStates,
            planSummary = null, batchReview = null, commitReview = null)
        refreshBackupPlan(input)
    }

    internal fun backupCandidates(index: Int, offset: Int, input: Long, token: Long) {
        val preview = backupState.preview ?: return
        val vaultId = state.vault?.id ?: return
        if (backupState.detail?.let { it.kind == BackupImportKind.NOTE && it.sourceIndex == index && it.token == token } != true) return
        backupWork(input, reading = true) { qualified ->
            backupState = backupState.copy(fieldPair = null, fieldRequest = null, expandedField = null, choosingTarget = true)
            val candidates = store.readImportCandidates(vaultId, preview.id, index, offset, qualified = qualified)
            val apply: () -> Unit = { backupState = backupState.copy(candidateSourceIndex = index, candidates = candidates, candidateOffset = offset,
                text = "", textRequest = null, textNextOffset = 0) }
            apply
        }
    }

    internal fun backupText(kind: BackupImportKind, index: Int, targetId: String?, field: BackupPreviewTextField, offset: Int, input: Long, token: Long) {
        val preview = backupState.preview ?: return
        val vaultId = state.vault?.id ?: return
        if (kind != backupState.previewKind || backupState.detail?.let { it.kind == kind && it.sourceIndex == index && it.token == token } != true) return
        backupWork(input, reading = true) { qualified ->
            val request = BackupTextRequest(kind, index, targetId, field)
            backupState = if (backupState.textRequest == request) backupState.copy(textRequestedOffset = offset)
                else backupState.copy(text = "", textRequest = request, textOffset = 0, textRequestedOffset = offset,
                    textNextOffset = 0, textComplete = true)
            val chunk = store.readImportText(vaultId, preview.id, kind, index, targetId, field, offset, qualified = qualified)
            val apply: () -> Unit = { backupState = backupState.copy(text = chunk.text,
                textRequest = BackupTextRequest(kind, index, targetId, field), textOffset = offset,
                textNextOffset = chunk.nextOffset, textComplete = chunk.complete) }
            apply
        }
    }

    internal fun commitBackup(input: Long) {
        if (backupState.detail != null) return
        if (backupMatches(input) && backupState.reading) stopBackupWork()
        val preview = backupState.preview ?: return
        val vaultId = state.vault?.id ?: return
        val decisions = backupState.decisions
        backupWork(input) { qualified ->
            val permission = generation
            val run = backupRun
            val result = try { store.commitImport(vaultId, preview.id, decisions, qualified) }
            catch (failure: Exception) {
                val interrupted = failure is CancellationException ||
                    failure is BackupStoreException && failure.problem == app.cangoo.android.data.BackupStoreProblem.CANCELLED
                // 已进入提交但未取得结果；撤销原预览，重新认证后读取实际资料，不能声称已回滚。
                if (interrupted && (backupRun == run || backupRun == run + 1) && permission == generation &&
                    input == inputGeneration && state.unlocked && state.page == Page.BACKUP && state.vault?.id == vaultId &&
                    backupState.preview?.id == preview.id) {
                    lock()
                    state = state.copy(notice = UiText(R.string.restore_unverified))
                }
                throw failure
            }
            if (qualified()) {
                documentIntent = null
                if (backupState.source == BackupSource.TRANSFER) clearDirectTransfer()
                backupState = BackupUiState(step = BackupStep.RESULT, result = result)
                state = state.copy(notice = UiText(R.string.restore_reading))
            }
            try {
                val passwords = store.listPasswords()
                val notes = store.listNotes()
                val checks = store.passwordChecks()
                val apply: () -> Unit = {
                documentIntent = null
                if (backupState.source == BackupSource.TRANSFER) clearDirectTransfer()
                backupState = BackupUiState(step = BackupStep.RESULT, result = result)
                state = state.copy(passwords = passwords, notes = notes, checks = checks, record = null, note = null,
                    notice = UiText.Empty)
                refreshOrder()
                }
                apply
            } catch (canceled: CancellationException) {
                if (state.vault?.id == vaultId && backupState.result == result) {
                    lock()
                    state = state.copy(notice = UiText(R.string.restore_reunlock))
                }
                throw canceled
            }
            catch (_: Exception) {
                // 数据已提交；摘要后续失败不能改报未恢复，也不继续展示旧资料。
                val apply: () -> Unit = {
                    documentIntent = null
                    lock()
                    state = state.copy(notice = UiText(R.string.restore_counts_reunlock, listOf(result.imported, result.overwritten, result.skipped)))
                }
                apply
            }
        }
    }

    internal fun backupConfiguration(input: Long) {
        if (backupMatches(input) && backupState.reading) stopBackupWork()
        if (!backupMatches(input) || state.busy || !onUserInteraction()) return
        if (backupState.source == BackupSource.TRANSFER) {
            clearBackup()
            inputGeneration++
            state = state.copy(page = Page.TRANSFER, error = UiText.Empty, notice = UiText.Empty)
            createDirectTransfer()
            return
        }
        val kind = documentIntent?.kind
        val name = backupState.documentName
        clearBackup(keepDocument = true)
        inputGeneration++
        backupState = BackupUiState(step = if (kind == BackupDocumentKind.EXPORT) BackupStep.EXPORT else BackupStep.IMPORT, documentName = name)
        state = state.copy(error = UiText.Empty, notice = UiText.Empty)
    }

    internal fun cancelBackupWork(input: Long) {
        if (!backupMatches(input) || !onUserInteraction()) return
        val target = currentExport()
        stopBackupWork()
        if (target != null) {
            abandonExport(target)
            documentIntent = null
            backupState = backupState.copy(documentName = "")
            state = state.copy(notice = if (target.created?.published == true) UiText(R.string.backup_saved) else UiText(R.string.backup_cancelling))
        } else state = state.copy(notice = UiText(R.string.operation_interrupted))
    }

    fun updateUiPreferences(value: UiPreferences, previous: UiPreferences, expectedPage: Page, expectedGeneration: Long, onSuccess: () -> Unit = {}) {
        if (uiPreferencesSaving || previous != uiPreferences || expectedPage !in listOf(Page.SETTINGS, Page.SECURITY, Page.APPEARANCE, Page.HELP) ||
            expectedPage != state.page || expectedGeneration != inputGeneration || !onUserInteraction()) return
        if (expectedPage == Page.HELP && value != previous.copy(language = value.language)) return
        val source = when {
            value.generatorAutoClear != previous.generatorAutoClear || value.generatorSeconds != previous.generatorSeconds -> UiPreferenceErrorSource.GENERATOR
            value.clipboardSeconds != previous.clipboardSeconds -> UiPreferenceErrorSource.CLIPBOARD
            else -> UiPreferenceErrorSource.DISPLAY
        }
        persistUiPreferences({ latest -> latest.copy(
            language = if (value.language != previous.language) value.language else latest.language,
            palette = if (value.palette != previous.palette) value.palette else latest.palette,
            theme = if (value.theme != previous.theme) value.theme else latest.theme,
            fontScale = if (value.fontScale != previous.fontScale) value.fontScale else latest.fontScale,
            clipboardSeconds = if (value.clipboardSeconds != previous.clipboardSeconds) value.clipboardSeconds else latest.clipboardSeconds,
            generatorAutoClear = if (value.generatorAutoClear != previous.generatorAutoClear) value.generatorAutoClear else latest.generatorAutoClear,
            generatorSeconds = if (value.generatorSeconds != previous.generatorSeconds) value.generatorSeconds else latest.generatorSeconds,
        ) }, recoverUnreadable = expectedPage != Page.HELP, onSuccess = {
            uiPreferencesFailure = null
            uiPreferencesErrorSource = UiPreferenceErrorSource.GENERAL
            if (expectedPage == state.page && expectedGeneration == inputGeneration) onSuccess()
        }) { unknown ->
            uiPreferencesFailure = UiText(if (unknown) app.cangoo.android.R.string.preferences_write_unknown else app.cangoo.android.R.string.preferences_write_failed)
            uiPreferencesErrorSource = source
        }
    }

    private fun persistUiPreferences(change: (UiPreferences) -> UiPreferences, recoverUnreadable: Boolean = false, onSuccess: () -> Unit = {}, onFailure: (Boolean) -> Unit) {
        uiPreferenceWrites++
        uiPreferencesSaving = true
        viewModelScope.launch(start = CoroutineStart.UNDISPATCHED) {
            try {
                uiPreferencesMutex.withLock {
                    try {
                        val fallback = uiPreferences.takeIf { recoverUnreadable }
                        uiPreferences = withContext(NonCancellable + Dispatchers.IO) { uiPreferencesStore.update(fallback, change) }
                        onSuccess()
                    } catch (canceled: CancellationException) { throw canceled }
                    catch (error: Exception) {
                        val unknown = error is UiPreferencesWriteException && error.outcomeUnverified
                        val persisted = if (unknown) withContext(Dispatchers.IO) { runCatching { uiPreferencesStore.read() }.getOrNull() } else null
                        if (persisted != null) uiPreferences = persisted
                        if (persisted != null && change(persisted) == persisted) onSuccess() else onFailure(unknown)
                    }
                }
            } finally { uiPreferenceWrites--; uiPreferencesSaving = uiPreferenceWrites > 0 }
        }
    }

    private fun rememberGeneratorOptions(options: GeneratorOptions) {
        val run = ++generatorWriteRun
        if (options == uiPreferences.generatorOptions && !uiPreferencesSaving) return
        val permission = generation
        val input = inputGeneration
        val page = state.page
        persistUiPreferences({ it.copy(generatorOptions = options) }) { unknown ->
            if (run == generatorWriteRun && permission == generation && input == inputGeneration && page == state.page && state.unlocked) {
                state = state.copy(notice = if (unknown) UiText(R.string.generator_preferences_unknown) else UiText(R.string.generator_preferences_failed))
            }
        }
    }

    fun updateSecuritySettings(value: SecuritySettings) {
        if (securitySettingsSaving || !onUserInteraction()) return
        securitySettingsSaving = true
        viewModelScope.launch {
            try {
                withContext(Dispatchers.IO) { settingsStore.write(value) }
                // 设备设置独立于库会话；只在成功落盘后生效，锁定后不回填旧页面。
                securitySettings = value
                securitySettingsFailure = null
                if (!transferProtected()) { if (!foreground && value.lockOnLeave) lock() else if (!expireIfNeeded()) scheduleIdleLock() }
            } catch (error: CancellationException) {
                throw error
            } catch (_: Exception) {
                securitySettingsFailure = UiText(app.cangoo.android.R.string.security_write_failed)
            } finally {
                securitySettingsSaving = false
            }
        }
    }

    private fun expireIfNeeded(): Boolean {
        if (transferProtected()) return false
        if (!idleDeadline.consumeExpired(SystemClock.elapsedRealtime(), securitySettings.idleMinutes)) return false
        lock()
        return true
    }

    private fun scheduleIdleLock() {
        idleJob?.cancel()
        if (transferProtected()) return
        val remaining = idleDeadline.remaining(SystemClock.elapsedRealtime(), securitySettings.idleMinutes) ?: return
        idleJob = viewModelScope.launch {
            delay(remaining)
            expireIfNeeded()
        }
    }

    fun refreshVaults() { exitConfirmation.cancel(); loadVaults(restoreLast = false) }
    private fun loadVaults(restoreLast: Boolean) = perform {
        val deletionCleanupPending = store.recoverVaultDeletions()
        val vaults = store.listVaults()
        var notice = UiText.Empty
        val lastId = if (restoreLast) try {
            lastVaultWrite?.join()
            withContext(Dispatchers.IO) { lastVaultStore.read() }
        }
            catch (canceled: CancellationException) { throw canceled }
            catch (_: Exception) { notice = UiText(R.string.last_vault_read_failed); null }
            else null
        val selected = vaults.firstOrNull { it.id == lastId }
        if (deletionCleanupPending) notice += UiText(R.string.deletion_cleanup_pending)
        VaultUiState(vaults = vaults, vault = selected, page = if (selected == null) Page.VAULTS else Page.LOCKED, notice = notice)
    }

    private fun rememberSuccessfulVault(id: String) {
        val previous = lastVaultWrite
        lastVaultWrite = viewModelScope.launch(start = CoroutineStart.UNDISPATCHED) {
            // 成功会话的非秘密定位按成功次序落盘，正常退出不取消已开始的提交。
            withContext(NonCancellable) {
                previous?.join()
                try { withContext(Dispatchers.IO) { lastVaultStore.write(id) } }
                catch (_: Exception) {
                    if (state.unlocked && state.vault?.id == id) state = state.copy(
                        notice = if (state.notice.isEmpty()) UiText(R.string.last_vault_write_failed)
                            else UiText(R.string.notice_append, listOf(state.notice, UiText(R.string.last_vault_write_failed))))
                }
            }
        }
    }

    fun updateVaultName(value: String, expectedGeneration: Long = editGeneration, expectedPage: Page = Page.CREATE) {
        if (expectedPage in listOf(Page.CREATE, Page.RENAME)) editField(expectedPage, expectedGeneration) { copy(vaultName = value) }
    }
    fun updateMaster(value: String, expectedPage: Page = state.page, expectedGeneration: Long = editGeneration) {
        if (expectedPage in listOf(Page.CREATE, Page.LOCKED, Page.RENAME, Page.MASTER, Page.BIOMETRIC)) {
            editField(expectedPage, expectedGeneration) { copy(master = value) }
        }
    }
    fun updateConfirmation(value: String, expectedGeneration: Long = editGeneration) =
        editField(Page.CREATE, expectedGeneration) { copy(confirmation = value) }
    fun updateDraft(value: PasswordDraft, expectedGeneration: Long = editGeneration, expectedPage: Page = Page.ADD) =
        changeDraft(expectedGeneration, expectedPage) { value }
    fun changeDraft(expectedGeneration: Long, expectedPage: Page, change: PasswordDraft.() -> PasswordDraft) {
        if (expectedPage in listOf(Page.ADD, Page.EDIT)) editField(expectedPage, expectedGeneration) { copy(draft = draft.change()) }
    }
    fun updateNoteDraft(value: NoteDraft, expectedGeneration: Long = editGeneration, expectedPage: Page = Page.NOTE_ADD) =
        changeNoteDraft(expectedGeneration, expectedPage) { value }
    fun changeNoteDraft(expectedGeneration: Long, expectedPage: Page, change: NoteDraft.() -> NoteDraft) {
        if (expectedPage in listOf(Page.NOTE_ADD, Page.NOTE_EDIT)) editField(expectedPage, expectedGeneration) { copy(noteDraft = noteDraft.change()) }
    }
    fun togglePassword(expectedGeneration: Long = editGeneration, expectedPage: Page = state.page, expectedId: String? = state.record?.id) {
        if (expectedGeneration == inputGeneration && expectedPage == state.page && expectedId == state.record?.id &&
            (expectedPage != Page.DETAIL || !state.secretView.stale) && onUserInteraction() && !state.busy) {
            state = state.copy(passwordShown = !state.passwordShown,
                error = if (expectedPage == Page.STRENGTH) state.error else UiText.Empty, notice = UiText.Empty)
        }
    }
    fun showVaults() = edit { copy(showVaults = true) }
    fun dismissVaults() = edit { copy(showVaults = false) }
    fun manageVaults() = edit { copy(page = if (unlocked) Page.VAULT_MANAGEMENT else Page.VAULTS, master = "") }
    fun keepDraft() = edit { copy(discard = false) }
    fun showAdd() = edit { if (unlocked) copy(showAdd = true) else this }
    fun dismissAdd() = edit { copy(showAdd = false) }
    fun dismissDelete() = edit { copy(deleteConfirm = false) }

    fun startCreate() {
        if (!onUserInteraction() || state.busy) return
        if (state.page == Page.SEARCH) stopQuery()
        inputGeneration++
        createReturn = state.page
        state = state.copy(page = Page.CREATE, showVaults = false, vaultName = "", master = "", confirmation = "", error = UiText.Empty, notice = UiText.Empty)
    }

    fun create() {
        if (!onUserInteraction() || state.busy || state.page != Page.CREATE) return
        if (state.master != state.confirmation) {
            state = state.copy(error = if (state.master.isNotEmpty() && state.confirmation.isEmpty())
                UiText(R.string.master_confirmation_required) else UiText(R.string.master_mismatch))
            return
        }
        val submitted = state
        perform(establishesSession = true) {
            val vault = store.createVault(submitted.vaultName, submitted.master)
            VaultUiState(page = Page.PASSWORDS, vaults = (submitted.vaults + vault).sortedWith(compareBy<VaultInfo> { it.name }.thenBy { it.id }), vault = vault, unlocked = true, notice = UiText(R.string.vault_created))
        }
    }

    fun startRename() = edit {
        if (!unlocked || vault == null || page != Page.VAULT_MANAGEMENT) this
        else { inputGeneration++; copy(page = Page.RENAME, vaultName = vault.name, master = "", passwordShown = false) }
    }

    fun rename() {
        if (!onUserInteraction() || state.busy || !state.unlocked || state.page != Page.RENAME) return
        val previous = state
        perform {
            val renamed = store.renameVault(previous.vaultName, if (previous.vault?.hasMasterPassword == true) previous.master else "")
            previous.copy(page = Page.VAULT_MANAGEMENT, vault = renamed,
                vaults = previous.vaults.map { if (it.id == renamed.id) renamed else it }.sortedWith(compareBy<VaultInfo> { it.name }.thenBy { it.id }),
                vaultName = "", master = "", notice = UiText(R.string.vault_renamed))
        }
    }

    internal fun openMasterChange() {
        if (!onUserInteraction() || state.busy || !state.unlocked || state.page != Page.SETTINGS) return
        stopRecordStrength()
        inputGeneration++
        state = state.copy(page = Page.MASTER, master = "", newMaster = "", confirmation = "", securityStage = UiText.Empty, error = UiText.Empty, notice = UiText.Empty)
    }

    internal fun openBiometricSettings() {
        if (!onUserInteraction() || state.busy || !state.unlocked || state.page != Page.SETTINGS) return
        stopRecordStrength()
        inputGeneration++
        state = state.copy(page = Page.BIOMETRIC, master = "", securityStage = UiText.Empty, error = UiText.Empty, notice = UiText.Empty)
    }

    internal fun updateNewMaster(value: String, input: Long) = editField(Page.MASTER, input) { copy(newMaster = value) }
    internal fun updateNewMasterConfirmation(value: String, input: Long) = editField(Page.MASTER, input) { copy(confirmation = value) }

    private fun biometricAuthenticator(run: Long, host: Long, qualified: () -> Boolean): VaultBiometricAuthenticator = { cipher, purpose ->
        withContext(Dispatchers.Main.immediate) {
            refreshBiometricPresentation()
            if (host != biometricHost || !qualified()) VaultBiometricAuthentication.Cancelled
            else biometricAuthenticate?.invoke(run, cipher, purpose, qualified)
                ?: VaultBiometricAuthentication.Failure(BiometricManager.BIOMETRIC_ERROR_HW_UNAVAILABLE)
        }
    }

    internal fun submitVaultSecurity() {
        if (!onUserInteraction() || state.busy || !state.unlocked || state.page !in listOf(Page.MASTER, Page.BIOMETRIC)) return
        val submitted = state
        val vault = submitted.vault ?: return
        val changeMaster = submitted.page == Page.MASTER
        if (changeMaster && submitted.newMaster != submitted.confirmation) {
            state = state.copy(error = if (submitted.newMaster.isNotEmpty() && submitted.confirmation.isEmpty())
                UiText(R.string.new_master_confirmation) else UiText(R.string.new_master_mismatch))
            return
        }
        val enable = !vault.biometricEnabled
        if (!changeMaster && enable && !vault.hasMasterPassword) {
            state = state.copy(error = UiText(R.string.biometric_requires_master))
            return
        }
        if (!changeMaster && enable && submitted.master.isEmpty()) {
            state = state.copy(error = UiText(R.string.current_master_required))
            return
        }
        val permission = generation
        val input = inputGeneration
        val host = biometricHost
        val run = ++vaultSecurityRun
        vaultSecurityCancelled = false
        fun restorePermission() = permission == generation && state.vault?.id == vault.id && state.unlocked &&
            idleDeadline.remaining(SystemClock.elapsedRealtime(), securitySettings.idleMinutes) != 0L
        fun qualified() = restorePermission() && run == vaultSecurityRun && !vaultSecurityCancelled && input == inputGeneration &&
            state.page == submitted.page && foreground && contentVisible && host == biometricHost &&
            runCatching { biometricEligible?.invoke() == true }.getOrDefault(false)
        val authenticate = biometricAuthenticator(run, host, ::qualified)
        fun stage(value: VaultChangeStage) {
            viewModelScope.launch(Dispatchers.Main.immediate) {
                if (run == vaultSecurityRun && permission == generation && state.busy && state.page == submitted.page) {
                    state = state.copy(securityStage = when (value) {
                        VaultChangeStage.AUTHENTICATING -> if (changeMaster || enable) UiText(R.string.stage_verify_master) else UiText(R.string.stage_disable_biometric)
                        VaultChangeStage.PREPARING -> UiText(R.string.stage_prepare_data)
                        VaultChangeStage.REENCRYPTING -> UiText(R.string.stage_reencrypt)
                        VaultChangeStage.VERIFYING -> UiText(R.string.stage_verify_data)
                        VaultChangeStage.BIOMETRIC -> UiText(R.string.stage_authenticate)
                        VaultChangeStage.PUBLISHING -> UiText(R.string.stage_commit)
                        VaultChangeStage.CLEANING -> UiText(R.string.stage_cleanup)
                        VaultChangeStage.RESTORING -> UiText(R.string.stage_restore)
                    })
                }
            }
        }
        beginCopyIntent()
        state = state.copy(busy = true, error = UiText.Empty, notice = UiText.Empty, securityStage = UiText(R.string.stage_prepare))
        vaultSecurityJob = viewModelScope.launch {
            try {
                val result = if (changeMaster) store.changeMasterPassword(vault.id, submitted.master, submitted.newMaster,
                    authenticator = authenticate, restorePermission = ::restorePermission, onStage = ::stage, qualified = ::qualified)
                else store.setBiometricEnabled(vault.id, if (enable) submitted.master else null, enable,
                    authenticate, restorePermission = ::restorePermission, onStage = ::stage, qualified = ::qualified)
                if (permission != generation || state.vault?.id != vault.id || expireIfNeeded()) return@launch
                when (result) {
                    VaultRotationResult.Rotated, is VaultRotationResult.Residual -> {
                        val cleanupNotice = if (result is VaultRotationResult.Residual)
                            cleanupText(VaultCleanupStatus(false, result.paths, result.categories)) else UiText.Empty
                        val notice = if (changeMaster) {
                            if (result is VaultRotationResult.Residual) UiText(R.string.new_master_effective) + cleanupNotice + UiText(R.string.unlock_again)
                            else UiText(R.string.master_changed)
                        } else {
                            (if (enable) UiText(R.string.biometric_enabled) else UiText(R.string.biometric_disabled)) + cleanupNotice
                        }
                        val listed = try { store.listVaults() }
                        catch (cancelled: CancellationException) { throw cancelled }
                        catch (_: Exception) {
                            if (permission != generation || state.vault?.id != vault.id || expireIfNeeded()) return@launch
                            val published = vault.copy(
                                hasMasterPassword = if (changeMaster) submitted.newMaster.isNotEmpty() else vault.hasMasterPassword,
                                biometricEnabled = if (changeMaster) vault.biometricEnabled && submitted.newMaster.isNotEmpty() else enable,
                            )
                            lock(published)
                            state = state.copy(notice = notice + UiText(R.string.vault_list_read_failed))
                            return@launch
                        }
                        val updated = listed.firstOrNull { it.id == vault.id }
                        if (permission != generation || state.vault?.id != vault.id || expireIfNeeded()) return@launch
                        if (changeMaster || store.currentSessionId() != vault.id || updated == null || !updated.available) {
                            lock(updated ?: vault)
                            state = state.copy(notice = notice)
                        } else {
                            inputGeneration++
                            state = state.copy(page = Page.SETTINGS, vault = updated, vaults = listed, master = "", newMaster = "",
                                confirmation = "", busy = false, securityStage = UiText.Empty, notice = notice)
                        }
                    }
                    is VaultRotationResult.Unknown -> {
                        lock(null)
                        state = state.copy(error = UiText(R.string.security_change_unknown))
                    }
                    is VaultRotationResult.NoCommit -> {
                        val active = store.currentSessionId()
                        if (permission != generation || state.vault?.id != vault.id) return@launch
                        if (active != vault.id) lock(vault)
                        if (result.reason == VaultRotationFailure.AUTHENTICATION) inputGeneration++
                        val message = when (result.reason) {
                            VaultRotationFailure.AUTHENTICATION -> UiText(R.string.current_master_rejected)
                            VaultRotationFailure.INVALID_INPUT -> UiText(R.string.master_invalid)
                            VaultRotationFailure.CANCELLED -> UiText(R.string.operation_cancelled_kept)
                            VaultRotationFailure.BIOMETRIC_UNAVAILABLE -> if (changeMaster)
                                UiText(R.string.rebuild_retry) else UiText(R.string.biometric_enable_failed)
                            VaultRotationFailure.RECOVERY_ASSETS -> UiText(R.string.recovery_unverified)
                            VaultRotationFailure.SESSION_CLOSED -> UiText(R.string.vault_locked_again)
                            VaultRotationFailure.STORAGE -> UiText(R.string.security_change_failed)
                        }
                        state = state.copy(busy = if (active == vault.id) false else state.busy,
                            master = if (result.reason == VaultRotationFailure.AUTHENTICATION) "" else state.master,
                            securityStage = UiText.Empty, error = if (result.reason == VaultRotationFailure.CANCELLED) UiText.Empty else message,
                            notice = (if (result.reason == VaultRotationFailure.CANCELLED) message else UiText.Empty) +
                                if (result.residual.isNotEmpty()) UiText(R.string.encrypted_temp_residual) else UiText.Empty)
                    }
                }
            } catch (cancelled: CancellationException) {
                if (run == vaultSecurityRun && permission == generation) {
                    state = state.copy(busy = false, securityStage = UiText.Empty, notice = UiText(R.string.operation_cancelled))
                }
                throw cancelled
            } catch (_: Exception) {
                if (run == vaultSecurityRun && permission == generation && state.vault?.id == vault.id) {
                    val active = store.currentSessionId()
                    if (active != vault.id) lock(vault)
                    state = state.copy(error = UiText(R.string.operation_check_vault),
                        busy = if (active == vault.id) false else state.busy, securityStage = UiText.Empty)
                }
            } finally {
                if (run == vaultSecurityRun) {
                    vaultSecurityJob = null
                    state = state.copy(busy = false, securityStage = UiText.Empty)
                    wakeRecordStrength()
                }
            }
        }
    }

    internal fun unlockWithBiometric() {
        if (!onUserInteraction() || state.busy || state.page != Page.LOCKED || state.vault?.biometricEnabled != true) return
        val vault = state.vault ?: return
        val permission = generation
        val input = inputGeneration
        val host = biometricHost
        val run = ++vaultSecurityRun
        vaultSecurityCancelled = false
        fun qualified() = permission == generation && run == vaultSecurityRun && !vaultSecurityCancelled && input == inputGeneration &&
            state.page == Page.LOCKED && state.vault?.id == vault.id && foreground && contentVisible && host == biometricHost &&
            runCatching { biometricEligible?.invoke() == true }.getOrDefault(false)
        state = state.copy(busy = true, error = UiText.Empty, notice = UiText.Empty)
        vaultSecurityJob = viewModelScope.launch {
            try {
                val opened = store.unlockBiometric(vault.id, biometricAuthenticator(run, host, ::qualified), ::qualified)
                val passwords = store.listPasswords()
                val notes = store.listNotes()
                val checks = store.passwordChecks()
                val cleanupNotice = pendingCleanupNotice(opened.id)
                if (!qualified() || expireIfNeeded()) {
                    if (permission == generation && state.vault?.id == vault.id) {
                        store.revoke()
                        withContext(NonCancellable) { store.lock() }
                    }
                    return@launch
                }
                generation++; inputGeneration++
                state = continueDocumentAfterUnlock(VaultUiState(page = unlockReturn, vaults = state.vaults.map { if (it.id == opened.id) opened else it },
                    vault = opened, unlocked = true, passwords = passwords, notes = notes, checks = checks,
                    recentKeys = recentByVault[opened.id].orEmpty(), notice = cleanupNotice))
                rememberSuccessfulVault(opened.id)
                checksPaused = false; failedStrength = emptyMap()
                wakeRecordStrength()
                refreshOrder()
            } catch (_: VaultBiometricCancelled) {
                if (permission == generation && state.vault?.id == vault.id) state = state.copy(busy = false, notice = UiText(R.string.master_unlock_required))
            } catch (cancelled: CancellationException) { throw cancelled }
            catch (_: Exception) {
                if (permission == generation && state.vault?.id == vault.id) {
                    store.revoke()
                    withContext(NonCancellable) { store.lock() }
                    state = state.copy(busy = false, error = UiText(R.string.biometric_unlock_failed))
                }
            } finally {
                if (run == vaultSecurityRun) {
                    vaultSecurityJob = null
                    state = state.copy(busy = false)
                }
            }
        }
    }

    fun selectVault(vault: VaultInfo) {
        if (!onUserInteraction() || state.busy) return
        if (state.vault?.id == vault.id && state.unlocked) {
            if (state.page == Page.VAULT_MANAGEMENT) selectRoot(Page.SETTINGS) else dismissVaults()
            return
        }
        lock(vault)
        unlockReturn = Page.PASSWORDS
    }

    fun unlock() {
        if (!onUserInteraction() || state.busy || state.page != Page.LOCKED) return
        val vault = state.vault ?: return
        val password = state.master
        perform(clearMasterOnFailure = true, establishesSession = true) {
            val opened = store.unlock(vault.id, password)
            val records = store.listPasswords()
            VaultUiState(page = unlockReturn, vaults = state.vaults.map { if (it.id == opened.id) opened else it }, vault = opened, unlocked = true, passwords = records, notes = store.listNotes(), checks = store.passwordChecks(), recentKeys = recentByVault[opened.id].orEmpty(), notice = pendingCleanupNotice(opened.id))
        }
    }

    private suspend fun pendingCleanupNotice(vaultId: String): UiText = try {
        cleanupText(store.pendingCleanupStatus(vaultId))
    } catch (cancelled: CancellationException) { throw cancelled }
    catch (_: Exception) { cleanupText(VaultCleanupStatus(false, emptyList())) }

    private fun continueDocumentAfterUnlock(opened: VaultUiState): VaultUiState {
        val pending = documentIntent?.takeIf { it.vaultId == opened.vault?.id } ?: return opened
        val target = exportTargets[pending.requestId]
        backupState = BackupUiState(step = if (pending.kind == BackupDocumentKind.EXPORT) BackupStep.EXPORT else BackupStep.IMPORT,
            scope = target?.scope ?: BackupScope.ALL, documentName = target?.created?.displayName.orEmpty())
        return opened.copy(page = Page.BACKUP, notice = if (pending.kind == BackupDocumentKind.EXPORT) UiText(R.string.backup_password_again) else opened.notice)
    }

    fun startAdd() {
        if (!onUserInteraction() || state.busy || !state.unlocked) return
        if (state.page == Page.SEARCH) stopQuery()
        inputGeneration++
        stopRecordSecrets()
        recordReturn = state.page
        state = state.copy(page = Page.ADD, showAdd = false, draft = PasswordDraft(""), secretDraft = RecordSecretDraft(), secretView = RecordSecretView(), record = null, note = null, passwordShown = false, error = UiText.Empty, notice = UiText.Empty)
    }

    fun save(input: Long = editGeneration, page: Page = state.page, id: String? = state.record?.id, revision: Long? = state.record?.revision) {
        if (!editorMatches(input, page, id, revision) || state.secretView.stale || !onUserInteraction() || state.busy || state.secretDraft.confirmation != null || state.secretDraft.reloadLatest) return
        val submitted = state
        val fromChecks = submitted.page == Page.EDIT && recordReturn == Page.CHECKS
        val secret = submitted.secretDraft
        if (!submitted.secretView.hasTotp && secret.totpIntent == RecordSecretIntent.REPLACE && secret.totpInput.isEmpty()) {
            state = state.copy(error = UiText(R.string.totp_setup_required))
            return
        }
        val totp = when {
            secret.totpIntent == RecordSecretIntent.REMOVE -> ""
            secret.totpIntent == RecordSecretIntent.REPLACE || !submitted.secretView.hasTotp -> secret.totpInput.ifEmpty { null }
            else -> null
        }
        val codes: List<RecoveryCode>? = try {
            when {
                secret.recoveryIntent == RecordSecretIntent.REMOVE -> emptyList()
                secret.recoveryIntent == RecordSecretIntent.REPLACE || submitted.secretView.recoveryUsed.isEmpty() ->
                    if (secret.recoveryInput.isEmpty()) null else normalizeRecoveryCodes(secret.recoveryInput).ifEmpty { null }
                else -> null
            }
        } catch (failure: RecoveryCodeException) {
            state = state.copy(error = failure.problem.uiText())
            return
        }
        perform {
            val original = submitted.record
            val record = if (submitted.page == Page.EDIT && original != null) {
                store.updatePassword(original.id, original.revision, submitted.draft, totp, codes)
            } else store.addPassword(submitted.draft, totp, codes)
            refreshChecksAfterWrite(submitted.copy(page = if (fromChecks) Page.CHECKS else Page.DETAIL, record = if (fromChecks) null else record, note = null,
                passwords = (submitted.passwords.filter { it.id != record.id } + record.toSummary()).sortedWith(compareByDescending<PasswordSummary> { it.updatedAt }.thenBy { it.id }),
                draft = PasswordDraft(""), secretDraft = RecordSecretDraft(), passwordShown = false, notice = UiText(R.string.password_saved)))
        }
    }

    fun openRecord(id: String) {
        if (!onUserInteraction() || state.busy || !state.unlocked) return
        if (state.page !in listOf(Page.DETAIL, Page.NOTE_DETAIL)) recordReturn = state.page
        stopQuery()
        stopRecordSecrets()
        perform(opened = id to false) {
            val record = store.readPassword(id)
            state.copy(page = Page.DETAIL, record = record, note = null, passwordShown = false, notice = UiText.Empty)
        }
    }

    fun startEdit() = edit {
        if (!unlocked || page != Page.DETAIL || record == null || secretView.stale) this
        else {
            inputGeneration++
            stopRecordSecrets()
            passwordEditor(record)
        }
    }

    private fun VaultUiState.passwordEditor(record: PasswordRecord): VaultUiState =
        copy(page = Page.EDIT, record = record, note = null,
            draft = PasswordDraft(record.title, record.account, record.password, record.notes, record.favorite),
            secretDraft = RecordSecretDraft(), secretView = metadata(record), passwordShown = false, error = UiText.Empty, notice = UiText.Empty)

    fun editCheckedRecord(vaultId: String, id: String, input: Long) {
        if (input != inputGeneration || state.page != Page.CHECKS || state.vault?.id != vaultId || !state.unlocked ||
            !state.checksAvailable || (id !in state.checks.warningIds && id !in failedCheckIds) || state.passwords.none { it.id == id } ||
            state.busy || !foreground || !contentVisible || !onUserInteraction()) return
        recordReturn = Page.CHECKS
        stopRecordSecrets()
        val run = secretRun
        perform {
            val record = store.readPassword(id)
            // 途中离开后即使回到前台，本次读取也不能自动开启编辑。
            if (run != secretRun || !foreground || !contentVisible) state.copy(record = null, note = null,
                draft = PasswordDraft(""), secretDraft = RecordSecretDraft(), secretView = RecordSecretView(), passwordShown = false,
                notice = UiText(R.string.edit_interrupted))
            else state.passwordEditor(record)
        }
    }

    private fun editorMatches(input: Long, page: Page, id: String?, revision: Long?): Boolean =
        input == inputGeneration && state.page == page && page in listOf(Page.ADD, Page.EDIT) && state.unlocked &&
            state.record?.id == id && state.record?.revision == revision

    internal fun openDraftGenerator(input: Long, page: Page, id: String?, revision: Long?) {
        if (!editorMatches(input, page, id, revision) || state.secretView.stale || state.busy || uiPreferencesSaving ||
            state.discard || state.deleteConfirm || state.secretDraft.confirmation != null || state.secretDraft.reloadLatest ||
            !contentVisible || !onUserInteraction()) return
        activeDraftGenerator = DraftGeneratorPanel(++draftGeneratorRun, generation, input, page, id, revision, uiPreferences.generatorOptions)
    }

    internal fun updateDraftGenerator(token: Long, options: GeneratorOptions) {
        val panel = draftGenerator?.takeIf { it.token == token } ?: return
        if (!contentVisible || !onUserInteraction() || state.busy || uiPreferencesSaving) return
        activeDraftGenerator = panel.copy(options = options, error = UiText.Empty)
    }

    internal fun dismissDraftGenerator(token: Long) {
        if (draftGenerator?.token == token && !uiPreferencesSaving && onUserInteraction()) activeDraftGenerator = null
    }

    internal fun saveDraftGenerator(panelToken: Long) {
        val panel = draftGenerator?.takeIf { it.token == panelToken } ?: return
        if (state.secretView.stale || state.busy || uiPreferencesSaving || !contentVisible || !onUserInteraction()) return
        val options = try { validatedGeneratorOptions(panel.options) }
        catch (error: IllegalArgumentException) { activeDraftGenerator = panel.copy(error = if (error is GeneratorValidationException) error.reason else UiText(R.string.operation_retry)); return }
        val run = ++generatorWriteRun
        persistUiPreferences({ it.copy(generatorOptions = options) }, onSuccess = {
            if (run == generatorWriteRun && state.generatorOptions != uiPreferences.generatorOptions) {
                clearGenerated()
                state = state.copy(generatorOptions = uiPreferences.generatorOptions)
            }
            if (draftGenerator?.token == panelToken) {
                activeDraftGenerator = null
                state = state.copy(notice = UiText(R.string.generator_parameters_saved))
            }
        }) { unknown ->
            if (draftGenerator?.token == panelToken) activeDraftGenerator = panel.copy(
                error = if (unknown) UiText(R.string.generator_parameters_unknown) else UiText(R.string.generator_parameters_failed))
        }
    }

    internal fun generateDraftPassword(input: Long, page: Page, id: String?, revision: Long?) {
        if (!editorMatches(input, page, id, revision) || draftGenerator != null || state.secretView.stale || state.busy || uiPreferencesSaving ||
            state.discard || state.deleteConfirm || state.secretDraft.confirmation != null || state.secretDraft.reloadLatest ||
            !contentVisible || !onUserInteraction()) return
        val password = generatePassword(uiPreferences.generatorOptions)
        state = state.copy(draft = state.draft.copy(password = password), passwordShown = true, error = UiText.Empty, notice = UiText(R.string.generated_save_to_apply))
    }

    fun changeSecretInput(field: RecordSecretField, value: String, input: Long, page: Page, id: String?, revision: Long?) {
        if (!editorMatches(input, page, id, revision)) return
        edit {
            val editable = if (field == RecordSecretField.TOTP) secretDraft.totpIntent == RecordSecretIntent.REPLACE
                else secretView.recoveryUsed.isEmpty() || secretDraft.recoveryIntent == RecordSecretIntent.REPLACE
            if (!editable) this else copy(secretDraft = if (field == RecordSecretField.TOTP) secretDraft.copy(totpInput = value)
                else secretDraft.copy(recoveryInput = value))
        }
    }

    fun enableNewTotp(enabled: Boolean, input: Long, page: Page, id: String?, revision: Long?) {
        if (!editorMatches(input, page, id, revision) || state.secretView.hasTotp) return
        edit { copy(secretDraft = secretDraft.copy(totpIntent = if (enabled) RecordSecretIntent.REPLACE else RecordSecretIntent.KEEP, totpInput = "", totpShown = false)) }
    }

    fun requestSecretChange(change: RecordSecretChange, input: Long, page: Page, id: String?, revision: Long?) {
        if (!editorMatches(input, page, id, revision) || change.intent == RecordSecretIntent.KEEP) return
        edit {
            val exists = if (change.field == RecordSecretField.TOTP) secretView.hasTotp else secretView.recoveryUsed.isNotEmpty()
            if (!exists) this else copy(secretDraft = secretDraft.copy(confirmation = change))
        }
    }

    fun confirmSecretChange(change: RecordSecretChange, input: Long, page: Page, id: String?, revision: Long?) {
        if (!editorMatches(input, page, id, revision) || state.secretDraft.confirmation != change) return
        edit {
            copy(secretDraft = if (change.field == RecordSecretField.TOTP) secretDraft.copy(totpIntent = change.intent, totpInput = "", totpShown = false, confirmation = null)
                else secretDraft.copy(recoveryIntent = change.intent, recoveryInput = "", recoveryShown = false, confirmation = null))
        }
    }

    fun cancelSecretChange(input: Long, page: Page, id: String?, revision: Long?) {
        if (editorMatches(input, page, id, revision)) edit { copy(secretDraft = secretDraft.copy(confirmation = null, reloadLatest = false)) }
    }

    fun requestLatestRecord(input: Long, id: String, revision: Long) {
        if (editorMatches(input, Page.EDIT, id, revision) && state.secretView.stale) edit { copy(secretDraft = secretDraft.copy(reloadLatest = true)) }
    }

    fun loadLatestRecord(input: Long, id: String, revision: Long) {
        if (!editorMatches(input, Page.EDIT, id, revision) || !state.secretDraft.reloadLatest || !onUserInteraction() || state.busy) return
        state = state.copy(secretDraft = state.secretDraft.copy(reloadLatest = false))
        val previous = state
        perform {
            val record = store.readPassword(id)
            previous.copy(record = record, draft = PasswordDraft(record.title, record.account, record.password, record.notes, record.favorite),
                secretDraft = RecordSecretDraft(), secretView = metadata(record))
        }
    }

    fun keepSecret(field: RecordSecretField, input: Long, page: Page, id: String?, revision: Long?) {
        if (!editorMatches(input, page, id, revision)) return
        edit {
            copy(secretDraft = if (field == RecordSecretField.TOTP) secretDraft.copy(totpIntent = RecordSecretIntent.KEEP, totpInput = "", totpShown = false)
                else secretDraft.copy(recoveryIntent = RecordSecretIntent.KEEP, recoveryInput = "", recoveryShown = false))
        }
    }

    fun toggleSecretInput(field: RecordSecretField, input: Long, page: Page, id: String?, revision: Long?) {
        if (!editorMatches(input, page, id, revision)) return
        edit { copy(secretDraft = if (field == RecordSecretField.TOTP) secretDraft.copy(totpShown = !secretDraft.totpShown)
            else secretDraft.copy(recoveryShown = !secretDraft.recoveryShown)) }
    }

    private fun metadata(record: PasswordRecord?): RecordSecretView = if (record == null) RecordSecretView()
        else RecordSecretView(hasTotp = record.totpSecret.isNotEmpty(), recoveryUsed = decodeRecoveryCodes(record.recoveryCodesJson).map { it.used })

    private fun detailMatches(vaultId: String, id: String, revision: Long, input: Long, permission: Long, run: Long): Boolean =
        permission == generation && input == inputGeneration && run == secretRun && foreground && contentVisible && state.unlocked &&
            state.page == Page.DETAIL && !state.secretView.stale && state.vault?.id == vaultId && state.record?.let { it.id == id && it.revision == revision } == true

    private fun invalidateRecordVersion() {
        stopRecordSecrets()
        inputGeneration++
        state = state.copy(passwordShown = false, secretView = state.secretView.copy(stale = true),
            secretDraft = state.secretDraft.copy(totpShown = false, recoveryShown = false, confirmation = null, reloadLatest = false))
    }

    private fun pauseRecordReads() {
        secretRun++
        totpJob?.cancel()
        totpJob = null
        recoveryJobs.values.forEach { it.cancel() }
        recoveryJobs.clear()
        state = state.copy(secretView = state.secretView.copy(recoveryPending = emptySet()))
    }

    private fun stopRecordSecrets(clearRecovery: Boolean = true) {
        pauseRecordReads()
        state = state.copy(secretView = state.secretView.copy(totpCode = "", totpRemaining = 0, totpValidUntilEpochSeconds = 0, totpError = UiText.Empty,
            recoveryValues = if (clearRecovery) emptyMap() else state.secretView.recoveryValues,
            recoveryPending = emptySet(), recoveryErrors = emptyMap()))
    }

    private fun startTotp() {
        if (!foreground || !contentVisible || !state.unlocked || state.page != Page.DETAIL || state.secretView.stale ||
            state.secretView.totpError.isNotEmpty() || !state.secretView.hasTotp || totpJob?.isActive == true) return
        val vaultId = state.vault?.id ?: return
        val record = state.record ?: return
        val input = inputGeneration
        val permission = generation
        val run = secretRun
        // 这是30秒口令的每秒功能计时，不刷新空闲期限，也不判断宿主可见性。
        totpJob = viewModelScope.launch {
            while (detailMatches(vaultId, record.id, record.revision, input, permission, run) && !expireIfNeeded()) {
                if (state.busy) {
                    // 同一详情写入期间只推进现码期限，不向正在变更的旧版本再次取码。
                    val now = System.currentTimeMillis() / 1000
                    val remaining = state.secretView.totpValidUntilEpochSeconds - now
                    val seconds = if (now >= 0 && remaining in 1L..30L) remaining.toInt() else 0
                    state = state.copy(secretView = state.secretView.copy(totpRemaining = seconds, totpCode = if (seconds > 0) state.secretView.totpCode else ""))
                    delay(1000)
                    continue
                }
                try {
                    if (System.currentTimeMillis() < 0) throw IllegalArgumentException()
                    val code = store.readTotpCode(vaultId, record.id, record.revision)
                    if (!detailMatches(vaultId, record.id, record.revision, input, permission, run) || expireIfNeeded()) return@launch
                    val seconds = code?.let { (it.validUntilEpochSeconds - System.currentTimeMillis() / 1000).coerceIn(0, 30).toInt() } ?: 0
                    state = state.copy(secretView = state.secretView.copy(totpCode = if (seconds > 0) code?.code.orEmpty() else "", totpRemaining = seconds,
                        totpValidUntilEpochSeconds = code?.validUntilEpochSeconds ?: 0, totpError = UiText.Empty))
                } catch (canceled: CancellationException) { throw canceled }
                catch (failure: Exception) {
                    if (!detailMatches(vaultId, record.id, record.revision, input, permission, run) || expireIfNeeded()) return@launch
                    if (failure is VaultException && failure.code == VaultError.SESSION_CLOSED) { lock(); return@launch }
                    if (failure is VaultException && failure.code == VaultError.REVISION_CONFLICT) {
                        invalidateRecordVersion()
                        state = state.copy(error = UiText(R.string.record_changed_read))
                        return@launch
                    }
                    val message = UiText(R.string.totp_unavailable)
                    state = state.copy(secretView = state.secretView.copy(totpCode = "", totpRemaining = 0, totpValidUntilEpochSeconds = 0, totpError = message))
                    return@launch
                }
                delay(1000)
            }
        }
    }

    fun toggleRecoveryCode(vaultId: String, id: String, revision: Long, index: Int, input: Long) {
        val permission = generation
        val run = secretRun
        if (!detailMatches(vaultId, id, revision, input, permission, run) || index !in state.secretView.recoveryUsed.indices ||
            state.busy || index in state.secretView.recoveryPending || !onUserInteraction()) return
        if (index in state.secretView.recoveryValues) {
            state = state.copy(secretView = state.secretView.copy(recoveryValues = state.secretView.recoveryValues - index, recoveryErrors = state.secretView.recoveryErrors - index))
            return
        }
        state = state.copy(secretView = state.secretView.copy(recoveryPending = state.secretView.recoveryPending + index, recoveryErrors = state.secretView.recoveryErrors - index))
        recoveryJobs[index] = viewModelScope.launch {
            try {
                val value = store.readRecoveryCode(vaultId, id, revision, index)
                if (detailMatches(vaultId, id, revision, input, permission, run) && !expireIfNeeded()) {
                    state = state.copy(secretView = state.secretView.copy(recoveryValues = state.secretView.recoveryValues + (index to value), recoveryPending = state.secretView.recoveryPending - index))
                }
            } catch (canceled: CancellationException) { throw canceled }
            catch (failure: Exception) {
                if (detailMatches(vaultId, id, revision, input, permission, run) && !expireIfNeeded()) {
                    if (failure is VaultException && failure.code == VaultError.SESSION_CLOSED) { lock(); return@launch }
                    if (failure is VaultException && failure.code == VaultError.REVISION_CONFLICT) {
                        invalidateRecordVersion()
                        state = state.copy(error = UiText(R.string.record_changed_read))
                        return@launch
                    }
                    val message = UiText(R.string.recovery_code_unavailable)
                    state = state.copy(secretView = state.secretView.copy(recoveryPending = state.secretView.recoveryPending - index, recoveryErrors = state.secretView.recoveryErrors + (index to message)))
                }
            } finally { if (run == secretRun) recoveryJobs.remove(index) }
        }
    }

    fun setRecoveryUsed(vaultId: String, id: String, revision: Long, index: Int, used: Boolean, input: Long) {
        if (!detailMatches(vaultId, id, revision, input, generation, secretRun) || index !in state.secretView.recoveryUsed.indices ||
            state.secretView.recoveryUsed[index] == used || !onUserInteraction() || state.busy) return
        val previous = state
        val original = previous.record ?: return
        perform(preserveRecordPresentation = true) {
            val changed = store.setRecoveryCodeUsed(vaultId, id, revision, index, used)
            val before = decodeRecoveryCodes(original.recoveryCodesJson)
            val after = decodeRecoveryCodes(changed.recoveryCodesJson)
            if (changed.id != id || before.size != after.size || before.indices.any { before[it].value != after[it].value }) {
                throw VaultException(VaultError.REVISION_CONFLICT)
            }
            previous.copy(record = changed, passwords = previous.passwords.map { if (it.id == changed.id) changed.toSummary() else it }, notice = if (used) UiText(R.string.marked_used) else UiText(R.string.unmarked_used))
        }
    }

    fun reloadSecretRecord(vaultId: String, id: String, revision: Long, input: Long) {
        if (input == inputGeneration && foreground && contentVisible && state.unlocked && state.page == Page.DETAIL &&
            state.vault?.id == vaultId && state.record?.let { it.id == id && it.revision == revision } == true) openRecord(id)
    }

    fun startSecretEdit(vaultId: String, id: String, revision: Long, input: Long) {
        if (detailMatches(vaultId, id, revision, input, generation, secretRun)) startEdit()
    }

    fun startNote() {
        if (!onUserInteraction() || state.busy || !state.unlocked) return
        if (state.page == Page.SEARCH) stopQuery()
        inputGeneration++
        stopRecordSecrets()
        recordReturn = state.page
        state = state.copy(page = Page.NOTE_ADD, showAdd = false, noteDraft = NoteDraft(""), secretDraft = RecordSecretDraft(), secretView = RecordSecretView(), record = null, note = null, passwordShown = false, error = UiText.Empty, notice = UiText.Empty)
    }

    fun openNote(id: String) {
        if (!onUserInteraction() || state.busy || !state.unlocked) return
        if (state.page !in listOf(Page.DETAIL, Page.NOTE_DETAIL)) recordReturn = state.page
        stopQuery()
        stopRecordSecrets()
        perform(opened = id to true) {
            val note = store.readNote(id)
            state.copy(page = Page.NOTE_DETAIL, note = note, record = null, passwordShown = false, notice = UiText.Empty)
        }
    }

    val noteTextChanged: Boolean get() = state.page == Page.NOTE_EDIT && state.note?.let {
        state.noteDraft.title != it.title || state.noteDraft.content != it.content
    } == true

    fun startNoteEdit(vaultId: String? = state.vault?.id, id: String? = state.note?.id,
                      revision: Long? = state.note?.revision, input: Long = editGeneration) {
        if (input != inputGeneration || state.vault?.id != vaultId || state.note?.id != id ||
            state.note?.revision != revision || !foreground || !contentVisible) return
        edit {
            if (!unlocked || page != Page.NOTE_DETAIL || note == null) this
            else { inputGeneration++; copy(page = Page.NOTE_EDIT, noteDraft = NoteDraft(note.title, note.content, note.favorite)) }
        }
    }

    fun saveNote() {
        if (!onUserInteraction() || state.busy || state.page !in listOf(Page.NOTE_ADD, Page.NOTE_EDIT) || !state.unlocked) return
        val submitted = state
        perform {
            val original = submitted.note
            val note = if (submitted.page == Page.NOTE_EDIT && original != null) {
                store.updateNote(original.id, original.revision, submitted.noteDraft)
            } else store.addNote(submitted.noteDraft)
            submitted.copy(page = Page.NOTE_DETAIL, note = note,
                notes = (submitted.notes.filter { it.id != note.id } + note.toSummary()).sortedWith(compareByDescending<NoteSummary> { it.updatedAt }.thenBy { it.id }),
                noteDraft = NoteDraft(""), notice = UiText(R.string.note_saved))
        }
    }

    fun toggleFavorite(id: String, isNote: Boolean, revision: Long, expectedGeneration: Long) {
        val matches = if (isNote) state.page in listOf(Page.NOTE_DETAIL, Page.NOTE_EDIT) && state.note?.let { it.id == id && it.revision == revision } == true
            else state.page == Page.DETAIL && state.record?.let { it.id == id && it.revision == revision } == true
        if (expectedGeneration != inputGeneration || !matches || (!isNote && state.secretView.stale) || !onUserInteraction() || state.busy || !state.unlocked) return
        val previous = state
        when (previous.page) {
            Page.DETAIL -> previous.record?.let { record -> perform {
                val changed = store.setPasswordFavorite(record.id, record.revision, !record.favorite)
                previous.copy(record = changed, passwords = previous.passwords.map { if (it.id == changed.id) changed.toSummary() else it })
            } }
            Page.NOTE_DETAIL, Page.NOTE_EDIT -> previous.note?.let { note -> perform {
                val changed = store.setNoteFavorite(note.id, note.revision, !note.favorite)
                previous.copy(note = changed, notes = previous.notes.map { if (it.id == changed.id) changed.toSummary() else it },
                    noteDraft = if (previous.page == Page.NOTE_EDIT) previous.noteDraft.copy(favorite = changed.favorite) else previous.noteDraft)
            } }
            else -> Unit
        }
    }

    fun requestDelete() = edit {
        if (unlocked && page in listOf(Page.EDIT, Page.NOTE_DETAIL, Page.NOTE_EDIT)) copy(deleteConfirm = true) else this
    }

    fun requestNoteDelete(vaultId: String?, id: String, revision: Long, input: Long) {
        if (input != inputGeneration || state.vault?.id != vaultId || state.note?.id != id ||
            state.note?.revision != revision || !foreground || !contentVisible) return
        requestDelete()
    }

    fun deleteRecord() {
        if (!onUserInteraction() || state.busy || !state.unlocked || !state.deleteConfirm) return
        val previous = state
        perform {
            when (previous.page) {
                Page.EDIT -> previous.record?.let { store.deletePassword(it.id, it.revision) }
                Page.NOTE_DETAIL, Page.NOTE_EDIT -> previous.note?.let { store.deleteNote(it.id, it.revision) }
                else -> return@perform previous.copy(deleteConfirm = false)
            }
            val next = previous.copy(page = recordReturn, passwords = previous.passwords.filter { it.id != previous.record?.id }, notes = previous.notes.filter { it.id != previous.note?.id }, record = null, note = null,
                draft = PasswordDraft(""), noteDraft = NoteDraft(""), deleteConfirm = false, passwordShown = false, notice = UiText(R.string.item_deleted))
            if (previous.page == Page.EDIT) refreshChecksAfterWrite(next) else next
        }
    }

    fun selectRoot(page: Page) {
        if (page !in listOf(Page.HOME, Page.PASSWORDS, Page.TOOLS, Page.SETTINGS) || !onUserInteraction() || state.busy || !state.unlocked) return
        if (page != state.page) inputGeneration++
        stopRecordSecrets()
        state = state.copy(page = page, record = null, note = null, secretDraft = RecordSecretDraft(), secretView = RecordSecretView(), passwordShown = false, error = UiText.Empty, notice = UiText.Empty)
        if (page == Page.PASSWORDS) {
            state = state.copy(browseKind = BrowseKind.ALL, browseFilter = BrowseFilter.ALL, browseRun = state.browseRun + 1)
            refreshOrder()
        }
        if (page == Page.SETTINGS) refreshLocalBackupRecord()
        wakeRecordStrength()
    }

    private fun refreshLocalBackupRecord() {
        val vault = state.vault ?: return
        if (state.page != Page.SETTINGS || !state.unlocked || state.busy) return
        state = state.copy(localBackupRecordLabel = null)
        val previous = state
        perform { previous.copy(localBackupRecordLabel = localBackupRecordLabel(store.localBackupRecord(vault.id))) }
    }

    private fun localBackupRecordLabel(value: LocalBackupRecordState): UiText = when (value) {
        LocalBackupRecordState.Missing -> UiText(R.string.backup_history_empty)
        LocalBackupRecordState.Unavailable -> UiText(R.string.backup_history_unavailable)
        is LocalBackupRecordState.Available -> {
            val record = value.record
            val time = UiDate(record.completedAt.toEpochMilli())
            val scope = when (record.scope) { BackupScope.ALL -> UiText(R.string.scope_all); BackupScope.PASSWORDS -> UiText(R.string.scope_passwords); BackupScope.NOTES -> UiText(R.string.scope_notes) }
            UiText(R.string.backup_history, listOf(time, scope))
        }
    }

    private fun localRecordNotice(value: LocalBackupRecordWrite?): UiText = when (value) {
        LocalBackupRecordWrite.NOT_SAVED -> UiText(R.string.backup_history_write_failed)
        LocalBackupRecordWrite.UNVERIFIED -> UiText(R.string.backup_history_unknown)
        else -> UiText.Empty
    }

    fun showFavorites() {
        selectRoot(Page.PASSWORDS)
        if (state.page == Page.PASSWORDS && state.unlocked) state = state.copy(browseFilter = BrowseFilter.FAVORITE)
    }

    fun changeBrowse(kind: BrowseKind = state.browseKind, filter: BrowseFilter = state.browseFilter, sort: BrowseSort = state.browseSort,
                     expectedGeneration: Long, expectedPage: Page) {
        if (expectedGeneration != inputGeneration || expectedPage != state.page || expectedPage !in listOf(Page.PASSWORDS, Page.SEARCH) ||
            !onUserInteraction() || state.busy || !state.unlocked) return
        val orderChanged = sort != state.browseSort
        val effectiveFilter = if (kind != state.browseKind) BrowseFilter.ALL else filter
        state = state.copy(browseKind = kind, browseFilter = effectiveFilter, browseSort = sort, browseRun = state.browseRun + 1)
        if (orderChanged || !state.orderAvailable) refreshOrder()
    }

    fun clearBrowse(expectedGeneration: Long, expectedPage: Page) {
        if (expectedGeneration != inputGeneration || expectedPage != state.page || expectedPage !in listOf(Page.PASSWORDS, Page.SEARCH)) return
        changeBrowse(BrowseKind.ALL, BrowseFilter.ALL, expectedGeneration = expectedGeneration, expectedPage = expectedPage)
        if (state.page == Page.SEARCH) updateQuery("", expectedGeneration)
    }

    private fun refreshOrder() {
        if (!state.unlocked) return
        val permission = generation
        val run = ++orderRun
        val sort = state.browseSort
        orderJob?.cancel()
        state = state.copy(orderPending = true)
        orderJob = viewModelScope.launch {
            try {
                val keys = store.recordOrder(byName = sort == BrowseSort.NAME)
                if (permission == generation && run == orderRun && state.unlocked && sort == state.browseSort && !expireIfNeeded()) {
                    state = state.copy(orderKeys = keys, orderPending = false, orderAvailable = true)
                }
            } catch (canceled: CancellationException) { throw canceled }
            catch (_: Exception) {
                if (permission == generation && run == orderRun) state = state.copy(orderPending = false, orderAvailable = false, notice = UiText(R.string.order_failed))
            }
        }
    }

    fun showChecks() {
        if (!onUserInteraction() || state.busy || !state.unlocked) return
        if (state.page != Page.CHECKS) checksReturn = state.page
        if (state.page == Page.CHECKS) state = state.copy(checksAvailable = false)
        val previous = state
        perform { previous.copy(page = Page.CHECKS, checks = store.passwordChecks(), checksAvailable = true, error = UiText.Empty, notice = UiText.Empty) }
    }

    fun startSearch() {
        if (!onUserInteraction() || state.busy || !state.unlocked) return
        inputGeneration++
        searchReturn = state.page
        searchOriginKind = state.browseKind
        searchOriginFilter = state.browseFilter
        searchOriginSort = state.browseSort
        state = state.copy(page = Page.SEARCH, query = "", effectiveQuery = "", searchNotes = state.notes, searchPasswords = state.passwords,
            searchOpening = state.searchOpening + 1, browseRun = state.browseRun + 1, browseKind = BrowseKind.ALL, browseFilter = BrowseFilter.ALL, error = UiText.Empty, notice = UiText.Empty)
    }

    fun updateQuery(value: String, expectedGeneration: Long) {
        if (expectedGeneration != inputGeneration || state.page != Page.SEARCH || !onUserInteraction() || state.busy) return
        queryRun++
        queryJob?.cancel()
        if (value.codePointCount(0, value.length) > 128) {
            state = state.copy(query = value, searchPending = false, error = UiText(R.string.search_limit))
            return
        }
        state = state.copy(query = value, error = UiText.Empty)
        query(value, expectedGeneration)
    }

    private fun query(value: String, expectedInputGeneration: Long, resetPosition: Boolean = true) {
        val run = ++queryRun
        val permission = generation
        queryJob?.cancel()
        state = state.copy(searchPending = true)
        queryJob = viewModelScope.launch {
            try {
                val passwords = store.searchPasswords(value)
                val notes = store.searchNotes(value)
                if (generation == permission && inputGeneration == expectedInputGeneration && run == queryRun && state.page == Page.SEARCH && !expireIfNeeded()) {
                    state = state.copy(effectiveQuery = value.trim(), searchPasswords = passwords, searchNotes = notes, searchPending = false,
                        browseRun = state.browseRun + if (resetPosition) 1 else 0)
                }
            } catch (error: CancellationException) { throw error }
            catch (_: Exception) {
                if (generation == permission && inputGeneration == expectedInputGeneration && run == queryRun && state.page == Page.SEARCH) state = state.copy(searchPending = false, error = UiText(R.string.search_failed))
            }
        }
    }

    private fun stopQuery() {
        queryRun++
        queryJob?.cancel()
        if (state.searchPending) state = state.copy(searchPending = false)
    }

    private fun restoreSearch() {
        if (state.query.codePointCount(0, state.query.length) > 128) {
            state = state.copy(error = UiText(R.string.search_limit))
        } else query(state.query, inputGeneration, resetPosition = false)
    }

    private fun recordStrengthEligible(): Boolean = state.unlocked && foreground && contentVisible && !checksPaused &&
        state.page !in listOf(Page.STRENGTH, Page.BACKUP, Page.MASTER, Page.BIOMETRIC)

    fun cancelChecks() {
        if (!onUserInteraction() || !state.unlocked) return
        checksPaused = true
        stopRecordStrength()
    }

    fun continueChecks() {
        if (!onUserInteraction() || !state.unlocked) return
        checksPaused = false
        wakeRecordStrength()
    }

    fun retryChecks() {
        if (!onUserInteraction() || !state.unlocked) return
        failedStrength = emptyMap()
        checksPaused = false
        wakeRecordStrength()
    }

    private fun stopRecordStrength() {
        recordStrengthRun++
        recordStrengthWakePending = false
        val pending = recordStrengthReply
        recordStrengthReply = null
        pending?.second?.cancel()
        recordStrengthJob?.cancel(); recordStrengthJob = null
        checksRunning = false
        if (pending != null) strengthOwner?.cancel() else strengthOwner?.releaseIdle()
    }

    private fun wakeRecordStrength() {
        failedStrength = failedStrength.filter { (id, epoch) -> state.checks.pendingEpochs[id] == epoch }
        if (state.busy || !recordStrengthEligible()) return
        if (recordStrengthJob != null) { recordStrengthWakePending = true; return }
        if (state.checks.pendingEpochs.none { (id, epoch) ->
            failedStrength[id] != epoch && !(state.page == Page.EDIT && state.record?.id == id) }) return
        recordStrengthWakePending = false
        val run = ++recordStrengthRun
        val permission = generation
        val vault = state.vault?.id ?: return
        fun qualified() = run == recordStrengthRun && permission == generation && state.vault?.id == vault && recordStrengthEligible()
        recordStrengthJob = viewModelScope.launch {
            try {
                val ids = state.checks.pendingEpochs.keys.toList()
                checksRunning = true
                for (id in ids) {
                    if (!qualified()) return@launch
                    if (state.page == Page.EDIT && state.record?.id == id) continue
                    val snapshot = try { store.strengthSnapshot(id) }
                    catch (cancelled: CancellationException) { throw cancelled }
                    catch (_: Exception) {
                        state.checks.pendingEpochs[id]?.let { failedStrength = failedStrength + (id to it) }
                        continue
                    } ?: continue
                    try {
                        if (!qualified()) return@launch
                        if (failedStrength[id] == snapshot.epoch) continue
                        val request = ++strengthRun
                        val reply = CompletableDeferred<PasswordStrengthOutcome>()
                        recordStrengthReply = request to reply
                        val owner = strengthOwner ?: PasswordStrengthOwner(getApplication<Application>(), ::acceptStrengthOutcome).also { strengthOwner = it }
                        owner.submit(request, snapshot.password, snapshot.title, snapshot.account, retain = true)
                        val outcome = reply.await()
                        recordStrengthReply = null
                        if (!qualified()) return@launch
                        when (outcome) {
                            is PasswordStrengthOutcome.Success -> {
                                val level = if (outcome.result.score < 3) "weak" else if (outcome.result.score == 3) "fair" else "strong"
                                if (store.commitStrength(snapshot, level) { qualified() && !(state.page == Page.EDIT && state.record?.id == id) }) {
                                    failedStrength = failedStrength - id
                                }
                            }
                            is PasswordStrengthOutcome.Failure -> failedStrength = failedStrength + (id to snapshot.epoch)
                        }
                    } catch (cancelled: CancellationException) { throw cancelled }
                    catch (_: Exception) { if (qualified()) failedStrength = failedStrength + (id to snapshot.epoch) }
                    finally { snapshot.clear() }
                    if (qualified()) {
                        val checks = store.passwordChecks()
                        if (qualified() && checks.revision >= state.checks.revision) state = state.copy(checks = checks, checksAvailable = true)
                    }
                }
            } catch (cancelled: CancellationException) { throw cancelled }
            catch (_: Exception) { if (qualified()) state = state.copy(checksAvailable = false) }
            finally {
                if (run == recordStrengthRun) {
                    recordStrengthReply = null; recordStrengthJob = null; checksRunning = false
                    strengthOwner?.releaseIdle()
                    if (recordStrengthWakePending) wakeRecordStrength()
                }
            }
        }
    }

    fun startGenerator() {
        if (!onUserInteraction() || state.busy || uiPreferencesSaving || !state.unlocked) return
        inputGeneration++
        if (state.generatorOptions != uiPreferences.generatorOptions) clearGenerated()
        state = state.copy(page = Page.GENERATOR, generatorOptions = uiPreferences.generatorOptions, error = UiText.Empty, notice = UiText.Empty)
    }

    fun startStrength() {
        if (!onUserInteraction() || state.busy || !state.unlocked || state.page != Page.TOOLS) return
        inputGeneration++
        stopRecordStrength()
        state = state.copy(page = Page.STRENGTH, strengthInput = "", strengthResult = null, strengthPending = false, passwordShown = false, error = UiText.Empty, notice = UiText.Empty)
    }

    fun updateStrengthInput(value: String, expectedGeneration: Long) {
        if (expectedGeneration != inputGeneration || state.page != Page.STRENGTH || !onUserInteraction() || state.busy || !state.unlocked) return
        stopStrength()
        state = state.copy(strengthInput = value, strengthResult = null, error = UiText.Empty, notice = UiText.Empty)
        if (value.isEmpty()) return
        if (value.codePointCount(0, value.length) > 1024) {
            state = state.copy(error = UiText(R.string.strength_input_limit))
            return
        }
        val run = ++strengthRun
        strengthPermission = generation
        strengthInputGeneration = expectedGeneration
        strengthVaultId = state.vault?.id
        state = state.copy(strengthPending = true)
        val owner = strengthOwner ?: PasswordStrengthOwner(getApplication<Application>(), ::acceptStrengthOutcome).also { strengthOwner = it }
        owner.submit(run, value)
    }

    private fun acceptStrengthOutcome(run: Long, outcome: PasswordStrengthOutcome) {
        recordStrengthReply?.takeIf { it.first == run }?.let { it.second.complete(outcome); return }

        if (run != strengthRun || strengthPermission != generation || strengthInputGeneration != inputGeneration ||
            state.vault?.id != strengthVaultId || !state.unlocked || state.page != Page.STRENGTH) return
        state = state.copy(strengthPending = false)
        if (!foreground || !contentVisible || expireIfNeeded()) return
        state = when (outcome) {
            is PasswordStrengthOutcome.Success -> state.copy(strengthResult = outcome.result, strengthPending = false, error = UiText.Empty)
            is PasswordStrengthOutcome.Failure -> state.copy(strengthResult = null, strengthPending = false, error = when (outcome.error) {
                PasswordStrengthError.INVALID_INPUT -> UiText(R.string.strength_input_invalid)
                PasswordStrengthError.UNSUPPORTED -> UiText(R.string.strength_unsupported)
                PasswordStrengthError.UNAVAILABLE -> UiText(R.string.strength_unavailable)
            })
        }
    }

    fun cancelStrength(expectedGeneration: Long) {
        if (expectedGeneration != inputGeneration || state.page != Page.STRENGTH || !onUserInteraction()) return
        stopStrength()
        state = state.copy(strengthResult = null)
    }

    private fun stopStrength() {
        strengthRun++
        strengthOwner?.cancel()
        if (state.strengthPending) state = state.copy(strengthPending = false)
    }
    fun updateGeneratorOptions(options: GeneratorOptions, expectedGeneration: Long) = editField(Page.GENERATOR, expectedGeneration) {
        generatedExpiryJob?.cancel()
        copy(generatorOptions = options, generated = "", generatedExpanded = false, generatedExpiresAt = null)
    }
    fun expandGenerated(expanded: Boolean, expectedGeneration: Long) = editField(Page.GENERATOR, expectedGeneration) { copy(generatedExpanded = expanded && generated.isNotEmpty()) }
    private fun clearGenerated() {
        generatedExpiryJob?.cancel()
        generatedExpiryJob = null
        state = state.copy(generated = "", generatedExpanded = false, generatedExpiresAt = null)
    }
    private fun expireGeneratedIfNeeded() {
        if (state.generatedExpiresAt?.let { SystemClock.elapsedRealtime() >= it } == true) clearGenerated()
    }
    fun generate() {
        if (!onUserInteraction() || state.busy || state.page != Page.GENERATOR || !state.unlocked) return
        clearGenerated()
        val options = try { validatedGeneratorOptions(state.generatorOptions) }
        catch (error: IllegalArgumentException) { state = state.copy(error = if (error is GeneratorValidationException) error.reason else UiText(R.string.operation_retry), notice = UiText.Empty); return }
        state = state.copy(generated = generatePassword(options), generatorOptions = options, generatedExpanded = false,
            generatedExpiresAt = if (uiPreferences.generatorAutoClear) SystemClock.elapsedRealtime() + uiPreferences.generatorSeconds * 1000L else null,
            error = UiText.Empty, notice = UiText.Empty)
        rememberGeneratorOptions(options)
        state.generatedExpiresAt?.let { deadline ->
            generatedExpiryJob = viewModelScope.launch {
                delay((deadline - SystemClock.elapsedRealtime()).coerceAtLeast(0L))
                expireGeneratedIfNeeded()
            }
        }
    }
    internal fun copyTransferPairingCode() {
        val controller = directTransfer ?: return
        val permission = generation
        fun qualified() = permission == generation && directTransfer === controller && state.page == Page.TRANSFER &&
            state.unlocked && !state.busy && foreground && contentVisible && !expireIfNeeded() && clipboardHostQualified()
        if (!qualified()) return
        controller.copyPairingCode { code, current ->
            viewModelScope.launch(start = CoroutineStart.UNDISPATCHED) {
                clipboardPublisher(ClipboardField.TEXT) { qualified() && current() }
                    .publish(ClipData.newPlainText("小仓", code))
            }
        }
    }

    internal fun copyGenerated(input: Long) {
        val permission = generation
        val vaultId = state.vault?.id
        fun qualified() = permission == generation && input == inputGeneration && state.page == Page.GENERATOR &&
            state.vault?.id == vaultId && state.unlocked && !state.busy && foreground && contentVisible &&
            !expireIfNeeded() && clipboardHostQualified()
        if (!qualified() || !onUserInteraction() || state.generated.isEmpty()) return
        val intent = beginCopyIntent()
        viewModelScope.launch(start = CoroutineStart.UNDISPATCHED) {
            clipboardPublisher(ClipboardField.GENERATED) { intent == copyIntent && qualified() }
                .publish(ClipData.newPlainText("小仓", state.generated))
        }
    }

    internal fun copyRecordField(vaultId: String, id: String, revision: Long, input: Long, field: ClipboardField, index: Int = -1): Job? {
        val permission = generation
        val run = secretRun
        fun qualified() = detailMatches(vaultId, id, revision, input, permission, run) && !state.busy &&
            !expireIfNeeded() && clipboardHostQualified()
        if (!qualified() || !onUserInteraction() || field !in setOf(ClipboardField.ACCOUNT, ClipboardField.PASSWORD, ClipboardField.TOTP, ClipboardField.RECOVERY)) return null
        if (field == ClipboardField.RECOVERY && index !in state.secretView.recoveryUsed.indices) return null
        val intent = beginCopyIntent()
        val job = viewModelScope.launch(start = CoroutineStart.UNDISPATCHED) {
            var validUntil = Long.MAX_VALUE
            try {
                val value = when (field) {
                    ClipboardField.ACCOUNT, ClipboardField.PASSWORD -> {
                        val record = store.readPassword(id)
                        if (record.revision != revision) throw VaultException(VaultError.REVISION_CONFLICT)
                        if (field == ClipboardField.ACCOUNT) record.account else record.password
                    }
                    ClipboardField.TOTP -> {
                        val code = store.readTotpCode(vaultId, id, revision) ?: return@launch
                        validUntil = code.validUntilEpochSeconds
                        code.code
                    }
                    ClipboardField.RECOVERY -> store.readRecoveryCode(vaultId, id, revision, index)
                    else -> return@launch
                }
                fun publishAllowed() = intent == copyIntent && qualified() && (field != ClipboardField.TOTP ||
                    System.currentTimeMillis() >= 0 && System.currentTimeMillis() / 1000 < validUntil)
                if (intent != copyIntent || !qualified()) return@launch
                if (value.isEmpty() || !publishAllowed()) {
                    state = state.copy(error = UiText(R.string.content_copy_failed))
                    return@launch
                }
                clipboardPublisher(field, ::publishAllowed).publish(ClipData.newPlainText("小仓", value))
            } catch (canceled: CancellationException) { throw canceled }
            catch (failure: Exception) {
                if (intent != copyIntent || !qualified()) return@launch
                if (failure is VaultException && failure.code == VaultError.SESSION_CLOSED) { lock(); return@launch }
                if (failure is VaultException && failure.code == VaultError.REVISION_CONFLICT) invalidateRecordVersion()
                state = state.copy(error = if (failure is VaultException && failure.code == VaultError.REVISION_CONFLICT)
                    UiText(R.string.record_changed_copy) else UiText(R.string.content_copy_failed))
            } finally { if (intent == copyIntent) copyReadJob = null }
        }
        copyReadJob = job.takeIf { it.isActive }
        return job
    }
    fun useGenerated(value: String, expectedGeneration: Long) {
        if (expectedGeneration != inputGeneration || state.page != Page.GENERATOR || !onUserInteraction() || value.isEmpty() || value != state.generated) return
        startAdd()
        if (state.page == Page.ADD) state = state.copy(draft = PasswordDraft("", password = value))
    }

    // 只有根库列表允许结束活动；常用首页先撤权并回根库列表。
    fun back(exitConfirmationMillis: Long = 2000L): Boolean {
        if (!observeUserInteraction()) return false
        if (backupState.batchReview != null || backupState.commitReview != null) {
            backupState = backupState.copy(batchReview = null, commitReview = null)
            return false
        }
        backupState.detail?.let {
            if (backupState.expandedField != null) closeBackupLongText(it.token)
            else if (backupState.fieldRequest != null) hideBackupField(it.token)
            else if (backupState.choosingTarget && backupState.comparison != null) closeBackupCandidates(it.token)
            else if (backupState.textRequest != null) closeBackupText(it.token) else closeBackupDetail(it.token)
            return false
        }
        draftGenerator?.let { dismissDraftGenerator(it.token); return false }
        if (state.discard) { keepDraft(); return false }
        if (state.deleteConfirm) { dismissDelete(); return false }
        if (state.showAdd) { dismissAdd(); return false }
        if (state.showVaults) { dismissVaults(); return false }
        if (state.secretDraft.confirmation != null) {
            state = state.copy(secretDraft = state.secretDraft.copy(confirmation = null))
            return false
        }
        if (state.secretDraft.reloadLatest) {
            state = state.copy(secretDraft = state.secretDraft.copy(reloadLatest = false))
            return false
        }
        if (state.busy) {
            if (state.page in listOf(Page.MASTER, Page.BIOMETRIC)) cancelVaultSecurityInternal()
            return false
        }
        when (state.page) {
            Page.CREATE, Page.RENAME, Page.ADD, Page.EDIT, Page.NOTE_ADD, Page.NOTE_EDIT -> {
                val changed = if (state.page == Page.CREATE) {
                    state.vaultName.isNotEmpty() || state.master.isNotEmpty() || state.confirmation.isNotEmpty()
                } else if (state.page == Page.RENAME) {
                    state.vaultName.trim() != state.vault?.name
                } else if (state.page == Page.NOTE_ADD || state.page == Page.NOTE_EDIT) {
                    val original = state.note?.let { NoteDraft(it.title, it.content, it.favorite) } ?: NoteDraft("")
                    state.noteDraft != original
                } else {
                    val original = state.record?.let { PasswordDraft(it.title, it.account, it.password, it.notes, it.favorite) } ?: PasswordDraft("")
                    state.draft != original || state.secretDraft.hasChanges
                }
                if (changed) state = state.copy(discard = true) else discardDraft()
            }
            Page.DETAIL, Page.NOTE_DETAIL -> {
                stopRecordSecrets()
                inputGeneration++
                state = state.copy(page = recordReturn, record = null, note = null, noteDraft = NoteDraft(""), secretView = RecordSecretView(), passwordShown = false, error = UiText.Empty, notice = UiText.Empty)
                if (recordReturn == Page.SEARCH) restoreSearch()
            }
            Page.SECURITY -> state = state.copy(page = securityReturn, error = UiText.Empty, notice = UiText.Empty)
            Page.SYSTEM_ACCESS -> {
                systemAccessJob?.cancel()
                inputGeneration++
                state = state.copy(page = systemAccessReturn, error = UiText.Empty, notice = UiText.Empty)
            }
            Page.APPEARANCE, Page.HELP -> {
                inputGeneration++
                state = state.copy(page = preferenceReturn, error = UiText.Empty, notice = UiText.Empty)
            }
            Page.MASTER, Page.BIOMETRIC -> {
                inputGeneration++
                state = state.copy(page = Page.SETTINGS, master = "", newMaster = "", confirmation = "", error = UiText.Empty, notice = UiText.Empty)
            }
            Page.BACKUP -> {
                if (backupState.source == BackupSource.TRANSFER && backupState.step == BackupStep.PREVIEW) backupConfiguration(inputGeneration)
                else {
                    clearBackup()
                    state = state.copy(page = backupReturn, error = UiText.Empty, notice = UiText.Empty)
                }
            }
            Page.TRANSFER -> closeDirectTransfer()
            Page.VAULT_DELETE -> {
                deletionState = VaultDeletionUiState()
                state = state.copy(page = deletionReturn, error = UiText.Empty, notice = UiText.Empty)
            }
            Page.VAULT_MANAGEMENT -> state = state.copy(page = if (state.unlocked) Page.SETTINGS else Page.VAULTS, error = UiText.Empty, notice = UiText.Empty)
            Page.SEARCH -> {
                stopQuery()
                state = state.copy(page = searchReturn, browseKind = searchOriginKind, browseFilter = searchOriginFilter, browseSort = searchOriginSort, error = UiText.Empty, notice = UiText.Empty)
                refreshOrder()
            }
            Page.CHECKS -> state = state.copy(page = checksReturn, error = UiText.Empty, notice = UiText.Empty)
            Page.GENERATOR -> state = state.copy(page = Page.TOOLS, error = UiText.Empty, notice = UiText.Empty)
            Page.STRENGTH -> {
                stopStrength()
                state = state.copy(page = Page.TOOLS, strengthInput = "", strengthResult = null, passwordShown = false, error = UiText.Empty, notice = UiText.Empty)
            }
            Page.PASSWORDS, Page.TOOLS, Page.SETTINGS -> selectRoot(Page.HOME)
            Page.HOME, Page.LOCKED -> lock(null)
            Page.VAULTS -> {
                if (!exitConfirmation.request(SystemClock.elapsedRealtime(), exitConfirmationMillis)) return false
                lock(null)
                return true
            }
        }
        if (state.page == Page.SETTINGS) refreshLocalBackupRecord()
        wakeRecordStrength()
        return false
    }

    fun discardDraft() {
        if (!onUserInteraction()) return
        val fromChecks = editingFromChecks
        if (fromChecks) stopRecordSecrets()
        state = state.copy(
            page = when (state.page) {
                Page.CREATE -> createReturn
                Page.RENAME -> Page.VAULT_MANAGEMENT
                Page.EDIT -> if (fromChecks) Page.CHECKS else Page.DETAIL
                Page.NOTE_EDIT -> recordReturn
                else -> recordReturn
            },
            draft = PasswordDraft(""), noteDraft = NoteDraft(""), vaultName = "", master = "", confirmation = "",
            record = if (fromChecks) null else state.record, note = if (fromChecks || state.page == Page.NOTE_EDIT) null else state.note,
            secretDraft = RecordSecretDraft(), secretView = metadata(if (state.page == Page.EDIT && !fromChecks) state.record else null),
            passwordShown = false, discard = false, error = UiText.Empty, notice = UiText.Empty,
        )
        inputGeneration++
        startTotp()
        if (state.page == Page.SEARCH) restoreSearch()
        wakeRecordStrength()
    }

    fun lock(target: VaultInfo? = state.vault) {
        exitConfirmation.cancel()
        clearDirectTransfer()
        systemAccessJob?.cancel()
        systemAccessSnapshot = null
        systemAccessReturn = Page.SECURITY
        activeDraftGenerator = null
        stopRecordStrength()
        checksPaused = false; failedStrength = emptyMap()
        generatedExpiryJob?.cancel()
        cancelVaultSecurityInternal()
        vaultSecurityRun++
        vaultSecurityJob = null
        beginCopyIntent()
        clipboardFeedback = null
        clipboardController.requestSecurityClear()
        deletionState = VaultDeletionUiState()
        clearBackup(keepDocument = target != null && documentIntent?.vaultId == target.id)
        stopRecordSecrets()
        queryRun++
        queryJob?.cancel()
        orderRun++
        orderJob?.cancel()
        stopStrength()
        idleJob?.cancel()
        idleDeadline.clear()
        val token = ++generation
        inputGeneration++
        store.revoke()
        unlockReturn = Page.HOME
        createReturn = Page.VAULTS
        securityReturn = Page.VAULTS
        recordReturn = Page.PASSWORDS
        searchReturn = Page.HOME
        checksReturn = Page.HOME
        state = VaultUiState(vaults = state.vaults, vault = target, page = if (target == null) Page.VAULTS else Page.LOCKED, busy = true)
        viewModelScope.launch(start = CoroutineStart.UNDISPATCHED) {
            try {
                store.lock()
                val vaults = store.listVaults()
                if (token == generation) state = state.copy(vaults = vaults,
                    vault = state.vault?.let { selected -> vaults.firstOrNull { it.id == selected.id } ?: selected }, busy = false)
            } catch (error: CancellationException) {
                throw error
            } catch (_: Exception) {
                if (token == generation) state = state.copy(busy = false, error = UiText(R.string.locked_list_failed))
            }
        }
    }

    private fun edit(change: VaultUiState.() -> VaultUiState) {
        if (onUserInteraction() && !state.busy) state = state.change().copy(error = UiText.Empty, notice = UiText.Empty)
    }


    private suspend fun refreshChecksAfterWrite(committed: VaultUiState): VaultUiState = try {
        committed.copy(checks = store.passwordChecks(), checksAvailable = true)
    } catch (error: CancellationException) { throw error }
    catch (_: VaultException) {
        // 已提交的资料不能因后续检查查询失败被报告为未保存。
        committed.copy(checksAvailable = false, notice = committed.notice + UiText(R.string.checks_update_failed))
    }

    private fun editField(expectedPage: Page, expectedGeneration: Long, change: VaultUiState.() -> VaultUiState) {
        // 旧输入回调在锁定完成后也可能迟到；拒绝时不得刷新空闲时钟。
        if (expectedGeneration != inputGeneration || expectedPage != state.page ||
            (expectedPage in listOf(Page.ADD, Page.EDIT, Page.NOTE_ADD, Page.NOTE_EDIT, Page.RENAME, Page.GENERATOR, Page.STRENGTH, Page.MASTER, Page.BIOMETRIC) && !state.unlocked)) return
        edit(change)
    }

    private fun perform(clearMasterOnFailure: Boolean = false, opened: Pair<String, Boolean>? = null, establishesSession: Boolean = false,
                        preserveRecordPresentation: Boolean = false, onCommitted: () -> Unit = {}, operation: suspend () -> VaultUiState) {
        if (state.busy) return
        val token = generation
        val input = inputGeneration
        val expectedPage = state.page
        val expectedId = state.record?.id
        val expectedRevision = state.record?.revision
        val expectedNoteId = state.note?.id
        val expectedNoteRevision = state.note?.revision
        val missingInput = when (expectedPage) {
            Page.CREATE, Page.RENAME -> if (state.vaultName.trim().isBlank()) UiText(R.string.vault_name_required) else null
            Page.ADD, Page.EDIT -> if (state.draft.title != state.record?.title && state.draft.title.isBlank()) UiText(R.string.name_required) else null
            Page.NOTE_ADD, Page.NOTE_EDIT -> if (state.noteDraft.title != state.note?.title && state.noteDraft.title.isBlank()) UiText(R.string.title_required) else null
            else -> null
        }
        val missingMaster = when (expectedPage) {
            Page.LOCKED, Page.RENAME, Page.MASTER, Page.BIOMETRIC -> state.vault?.hasMasterPassword == true && state.master.isEmpty()
            Page.VAULT_DELETE -> deletionState.target?.hasMasterPassword == true && deletionState.master.isEmpty()
            else -> false
        }
        fun currentRequest() = token == generation && input == inputGeneration && state.page == expectedPage &&
            state.record?.id == expectedId && state.record?.revision == expectedRevision &&
            state.note?.id == expectedNoteId && state.note?.revision == expectedNoteRevision
        // 详情写入与旧版本读取不能互相竞争；等待提交时保持当前展开，成功后换版本资格。
        if (state.page == Page.DETAIL) pauseRecordReads()
        state = state.copy(busy = true, error = UiText.Empty, notice = UiText.Empty)
        // 写入等待期间仅推进现码的截止时间，不向正在变更的旧版本取码。
        startTotp()
        viewModelScope.launch {
            if (!currentRequest()) return@launch
            try {
                var result = operation()
                if (!currentRequest() || expireIfNeeded()) return@launch
                expireGeneratedIfNeeded()
                // 资料异步提交的旧快照不能复活等待期间已清空的工具结果。
                if (result.unlocked && !establishesSession) result = result.copy(generated = state.generated,
                    generatedExpanded = state.generatedExpanded, generatedExpiresAt = state.generatedExpiresAt)
                if (establishesSession && state.vault?.id != result.vault?.id) {
                    clearBackup()
                    clipboardFeedback = null
                    clipboardController.requestSecurityClear()
                }
                if (establishesSession && expectedPage == Page.LOCKED) result = continueDocumentAfterUnlock(result)
                val changedRecord = state.record?.id != result.record?.id || state.record?.revision != result.record?.revision ||
                    state.note?.id != result.note?.id || state.note?.revision != result.note?.revision ||
                    state.page != result.page || state.secretView.stale && result.record != null
                val keepPresentation = preserveRecordPresentation && result.page == Page.DETAIL && state.page == Page.DETAIL && state.record?.id == result.record?.id && foreground && contentVisible
                val shown = keepPresentation && state.passwordShown
                val revealed = if (keepPresentation) state.secretView.recoveryValues else emptyMap()
                val details = if (changedRecord) metadata(result.record).copy(recoveryValues = revealed) else state.secretView
                if (changedRecord) { stopRecordSecrets(clearRecovery = !keepPresentation); inputGeneration++ }
                if (establishesSession) { generation++; inputGeneration++ }
                if (!establishesSession && result.unlocked && result.checks.revision < state.checks.revision) {
                    result = result.copy(checks = state.checks, checksAvailable = state.checksAvailable)
                }
                state = result.copy(busy = false, passwordShown = shown, secretView = details,
                    secretDraft = if (result.page in listOf(Page.ADD, Page.EDIT)) result.secretDraft else RecordSecretDraft(), error = UiText.Empty)
                if (establishesSession) {
                    checksPaused = false; failedStrength = emptyMap()
                    state.vault?.id?.let(::rememberSuccessfulVault)
                }
                onCommitted()
                wakeRecordStrength()
                startTotp()
                if (state.unlocked) refreshOrder()
                if (opened != null) state.vault?.id?.let { id ->
                    val recent = (listOf(opened) + recentByVault[id].orEmpty().filter { it != opened }).take(3)
                    recentByVault[id] = recent
                    state = state.copy(recentKeys = recent)
                }
                if (state.page == Page.SEARCH) restoreSearch()
            } catch (error: CancellationException) {
                if (expectedPage == Page.VAULT_DELETE && currentRequest()) {
                    val selectedId = state.vault?.id
                    val wasUnlocked = state.unlocked
                    val (activeId, vaults) = withContext(NonCancellable) {
                        val active = store.currentSessionId()
                        val listed = try { store.listVaults() } catch (_: Exception) { emptyList() }
                        active to listed
                    }
                    if (currentRequest()) {
                        deletionState = deletionState.copy(master = "", preview = null)
                        state = state.copy(busy = false, vaults = vaults)
                        if (wasUnlocked && activeId != selectedId || selectedId != null && vaults.none { it.id == selectedId }) lock(null)
                        state = state.copy(error = UiText(R.string.deletion_interrupted))
                    }
                }
                throw error
            } catch (error: Exception) {
                if (!currentRequest() || expireIfNeeded()) return@launch
                if (error is VaultException && error.code == VaultError.COMMIT_UNCERTAIN) {
                    lock(null)
                    state = state.copy(vaults = emptyList(), error = error.code.uiText())
                    return@launch
                }
                if (error is VaultException && error.code == VaultError.SESSION_CLOSED) {
                    lock()
                    state = state.copy(error = error.code.uiText())
                    return@launch
                }
                if (error is VaultException && error.code == VaultError.REVISION_CONFLICT && state.record != null) invalidateRecordVersion()
                if (token == generation && clearMasterOnFailure) {
                    store.revoke()
                    try { store.lock() } catch (_: VaultException) { /* 已撤权，仍保留原始失败原因。 */ }
                }
                if (clearMasterOnFailure || state.page == Page.RENAME) inputGeneration++
                if (state.page == Page.VAULT_DELETE) deletionState = deletionState.copy(master = "", preview = null)
                if (token == generation) state = state.copy(
                    busy = false,
                    master = if (clearMasterOnFailure || state.page == Page.RENAME) "" else state.master,
                    error = when {
                        error is VaultException && error.code == VaultError.INVALID_INPUT && missingInput != null -> missingInput
                        error is VaultException && error.code == VaultError.AUTHENTICATION_FAILED && missingMaster -> UiText(R.string.vault_master_required)
                        error is VaultException -> error.code.uiText()
                        else -> UiText(R.string.operation_retry_preserved)
                    },
                )
                startTotp()
            }
        }
    }

    override fun onCleared() {
        updates.close()
        clearDirectTransfer()
        exitConfirmation.cancel()
        systemAccessJob?.cancel()
        stopRecordStrength()
        generatedExpiryJob?.cancel()
        cancelVaultSecurityInternal()
        vaultSecurityRun++
        biometricAuthenticate = null; biometricCancel = null
        biometricCapabilityQuery = null; biometricTextQuery = null; biometricText = BiometricText(); biometricEligible = null
        beginCopyIntent()
        clipboardHostQuery = null
        clipboardHost++
        clipboardController.close()
        strengthRun++
        strengthOwner?.close()
        strengthOwner = null
        deletionState = VaultDeletionUiState()
        backupOwnerClosed = true
        clearBackup()
        exportTargets.values.toList().forEach(::abandonExport)
        stopRecordSecrets()
        generation++
        inputGeneration++
        state = VaultUiState()
        queryJob?.cancel()
        recentByVault.clear()
        idleJob?.cancel()
        store.revoke()
        viewModelScope.launch(NonCancellable, start = CoroutineStart.UNDISPATCHED) {
            try { store.lock() } catch (_: VaultException) { /* 会话已撤权，宿主销毁后不再展示错误。 */ }
        }
        super.onCleared()
    }
}
