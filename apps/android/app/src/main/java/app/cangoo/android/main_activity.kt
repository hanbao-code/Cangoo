package app.cangoo.android

import android.app.KeyguardManager
import android.app.ActivityManager
import android.Manifest
import android.content.pm.PackageManager
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.content.res.Configuration
import android.os.Build
import android.os.Bundle
import android.os.PowerManager
import android.provider.Settings
import android.util.TypedValue
import android.view.MotionEvent
import android.view.WindowManager
import android.view.textclassifier.TextClassificationManager
import android.view.textclassifier.TextClassifier
import androidx.activity.ComponentActivity
import androidx.activity.SystemBarStyle
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.result.contract.ActivityResultContracts
import androidx.core.content.ContextCompat
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.ViewModel
import androidx.lifecycle.lifecycleScope
import app.cangoo.android.ui.LegalContent
import app.cangoo.android.ui.TermsAcceptanceStore
import app.cangoo.android.ui.TermsPage
import app.cangoo.android.ui.UiPreferences
import app.cangoo.android.ui.UiPreferencesStore
import app.cangoo.android.ui.UiLanguage
import app.cangoo.android.ui.SystemAccessGuideStore
import app.cangoo.android.ui.CangooApp
import app.cangoo.android.ui.VaultModel
import app.cangoo.android.ui.BackupDocumentPicker
import app.cangoo.android.ui.DirectTransferController
import app.cangoo.android.ui.DirectTransferChannel
import app.cangoo.android.ui.DirectTransferSettings
import app.cangoo.android.ui.DirectTransferPhase
import app.cangoo.android.ui.SystemSettingsDestination
import app.cangoo.android.ui.BiometricPromptHost
import app.cangoo.android.ui.bThemeColors
import app.cangoo.android.ui.isDark
import app.cangoo.android.ui.openSystemSettings
import app.cangoo.android.ui.openContact
import app.cangoo.android.ui.openReleasePage
import androidx.compose.ui.graphics.toArgb
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.NonCancellable
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

class MainActivity : ComponentActivity() {
    private lateinit var model: VaultModel
    private lateinit var documentPicker: BackupDocumentPicker
    private lateinit var biometricPromptHost: BiometricPromptHost
    private var contentVisible by mutableStateOf(false)
    @Volatile private var topResumed = false
    @Volatile private var resumed = false
    private var clipboardHost = 0L
    private var biometricHost = 0L
    private var biometricRequest: Long? = null
    private var blockedTouch = false
    private var appliedSystemAppearance: Pair<Boolean, Int>? = null
    private var productReady by mutableStateOf(false)
    private var termsContent by mutableStateOf<LegalContent?>(null)
    private var termsPreferences by mutableStateOf(UiPreferences())
    private var termsBusy by mutableStateOf(true)
    private var termsError by mutableStateOf<Int?>(null)
    private var termsDecided by mutableStateOf(false)
    private var termsAccepted = false
    private var lockObservedBeforeEntry = false
    private var transferPermissionTarget: DirectTransferController? = null
    private val transferPermission = registerForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
        val target = transferPermissionTarget
        transferPermissionTarget = null
        if (target != null) existingModel()?.directTransferPermission(target, granted)
    }
    private class MissingVaultModel : RuntimeException()
    private val existingOnlyFactory = object : ViewModelProvider.Factory {
        override fun <T : ViewModel> create(modelClass: Class<T>): T = throw MissingVaultModel()
    }
    private val screenEvents = object : BroadcastReceiver() {
        override fun onReceive(context: Context, intent: Intent) {
            if (intent.action == Intent.ACTION_SCREEN_OFF) {
                contentVisible = false
                lockObservedBeforeEntry = !productReady
                existingModel()?.onScreenOff()
                cancelBiometricRequest()
                if (::model.isInitialized) model.observeClipboardHost(clipboardHost)
            } else if (intent.action == Intent.ACTION_USER_PRESENT) {
                revealAllowedContent()
            }
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        window.addFlags(WindowManager.LayoutParams.FLAG_SECURE)
        super.onCreate(savedInstanceState)
        if (Build.VERSION.SDK_INT >= 33) setRecentsScreenshotEnabled(false)
        val filter = IntentFilter(Intent.ACTION_SCREEN_OFF).apply { addAction(Intent.ACTION_USER_PRESENT) }
        if (Build.VERSION.SDK_INT >= 33) registerReceiver(screenEvents, filter, Context.RECEIVER_NOT_EXPORTED)
        else registerReceiver(screenEvents, filter)
        readTermsGate()
        setContent {
            if (productReady) CangooApp(model, contentVisible, onLeave = ::leaveApplication, onSystemAppearance = ::applySystemAppearance,
                onOpenSystemSettings = { destination -> openSystemSettings(this, destination, model.uiPreferences.language) },
                onOpenContact = { if (contentVisible && resumed && topResumed && !deviceRequiresLock()) openContact(this) else false },
                onOpenRelease = {
                    if (contentVisible && resumed && topResumed && !deviceRequiresLock())
                        model.updates.currentReleaseForOpen()?.let { openReleasePage(this, it) } ?: false
                    else false
                },
                onStartTransfer = ::startDirectTransfer,
                onTransferSettings = ::openTransferSettings,
                onChooseBackupFile = { kind, input -> model.prepareDocumentSelection(kind, input)?.let(documentPicker::launch) })
            else TermsPage(termsPreferences, termsContent, contentVisible && termsDecided, termsBusy, termsError,
                ::changeTermsLanguage, ::readTermsGate, ::acceptTerms, ::leaveApplication,
                onSystemAppearance = ::applySystemAppearance)
        }
    }

    private fun readTermsGate() {
        if (productReady || isFinishing || isDestroyed) return
        termsBusy = true
        termsError = null
        termsContent = null
        termsDecided = false
        termsAccepted = false
        // 小型公开偏好先读，只为首帧提供既有主题；不改写不可读文件。
        try { termsPreferences = UiPreferencesStore(this).read() }
        catch (_: Exception) { termsError = R.string.terms_preferences_read_failed }
        val systemDark = resources.configuration.uiMode and Configuration.UI_MODE_NIGHT_MASK == Configuration.UI_MODE_NIGHT_YES
        applySystemAppearance(termsPreferences.isDark(systemDark), bThemeColors(termsPreferences, systemDark).paper.toArgb())
        lifecycleScope.launch {
            try {
                withContext(Dispatchers.IO) { SystemAccessGuideStore(this@MainActivity).prepareBeforeTerms(this@MainActivity) }
            } catch (_: Exception) {
                termsError = R.string.terms_startup_failed
                termsBusy = false
                termsDecided = true
                return@launch
            }
            val content = try { withContext(Dispatchers.IO) { LegalContent.read(this@MainActivity) } }
            catch (_: Exception) {
                termsError = R.string.terms_resource_failed
                termsBusy = false
                termsDecided = true
                return@launch
            }
            val accepted = try { withContext(Dispatchers.IO) { TermsAcceptanceStore(this@MainActivity).accepted(content.termsVersion) } }
            catch (_: Exception) { termsError = R.string.terms_record_failed; false }
            if (isFinishing || isDestroyed) return@launch
            termsContent = content
            termsBusy = false
            termsAccepted = accepted
            termsDecided = !accepted
            if (accepted) revealAllowedContent()
        }
    }

    private fun changeTermsLanguage(language: UiLanguage) {
        if (termsBusy || productReady || !contentVisible || termsPreferences.language == language) return
        termsBusy = true
        lifecycleScope.launch {
            try {
                val saved = withContext(NonCancellable + Dispatchers.IO) {
                    UiPreferencesStore(this@MainActivity).update { it.copy(language = language) }
                }
                if (!isFinishing && !isDestroyed) { termsPreferences = saved; termsError = null }
            } catch (_: Exception) { termsError = R.string.terms_preferences_failed }
            finally { termsBusy = false }
        }
    }

    private fun acceptTerms() {
        val content = termsContent ?: return
        if (termsBusy || productReady || !contentVisible || !resumed || !topResumed || deviceRequiresLock()) return
        termsBusy = true
        lifecycleScope.launch {
            try {
                try {
                    withContext(NonCancellable + Dispatchers.IO) { TermsAcceptanceStore(this@MainActivity).accept(content.termsVersion) }
                } catch (_: Exception) { /* 阅读记录失败不限制本次运行；下次启动可重新告知。 */ }
                if (!isFinishing && !isDestroyed) {
                    termsAccepted = true
                    termsDecided = false
                    revealAllowedContent()
                }
            } catch (_: Exception) { termsError = R.string.terms_startup_failed }
            finally { termsBusy = false }
        }
    }

    private fun leaveApplication() {
        existingModel()?.onExplicitExit()
        finishAndRemoveTask()
    }

    private fun startDirectTransfer() {
        if (!contentVisible || !resumed || !topResumed || deviceRequiresLock()) return
        val target = existingModel()?.directTransfer ?: return
        if (target.state.channel == DirectTransferChannel.BLUETOOTH && Build.VERSION.SDK_INT >= 31 &&
            ContextCompat.checkSelfPermission(this, Manifest.permission.BLUETOOTH_CONNECT) != PackageManager.PERMISSION_GRANTED) {
            if (transferPermissionTarget != null) return
            transferPermissionTarget = target
            transferPermission.launch(Manifest.permission.BLUETOOTH_CONNECT)
        } else model.directTransferPermission(target, true)
    }

    private fun openTransferSettings(destination: DirectTransferSettings) {
        if (!contentVisible || !resumed || !topResumed || deviceRequiresLock()) return
        val target = existingModel()?.directTransfer ?: return
        if (target.state.phase != DirectTransferPhase.FAILED || target.state.settings != destination) return
        val opened = when (destination) {
            DirectTransferSettings.APPLICATION -> openSystemSettings(this, SystemSettingsDestination.APPLICATION, model.uiPreferences.language)
            DirectTransferSettings.BLUETOOTH -> try {
                startActivity(Intent(Settings.ACTION_BLUETOOTH_SETTINGS))
                true
            } catch (_: android.content.ActivityNotFoundException) { false }
            catch (_: SecurityException) { false }
        }
        if (!opened) target.settingsUnavailable()
    }

    // 轮转保留的模型仍接收撤权事件；查找不创建模型，也不开放业务呈现。
    internal fun existingModel(): VaultModel? = if (::model.isInitialized) model else try {
        ViewModelProvider(this, existingOnlyFactory)[VaultModel::class.java]
    } catch (_: MissingVaultModel) { null }

    private fun enterProduct() {
        if (productReady || !termsAccepted || !resumed || !topResumed || deviceRequiresLock() || isFinishing || isDestroyed) return
        model = ViewModelProvider(this)[VaultModel::class.java]
        if (lockObservedBeforeEntry) { model.onScreenOff(); lockObservedBeforeEntry = false }
        clipboardHost = model.bindClipboardHost { resumed && topResumed && hasWindowFocus() && !deviceRequiresLock() }
        biometricPromptHost = BiometricPromptHost(this) { model.uiPreferences.language }
        biometricHost = model.bindBiometricHost(
            authenticate = { request, cipher, purpose, qualified ->
                withContext(Dispatchers.Main.immediate) {
                    biometricRequest = request
                    try { biometricPromptHost.authenticate(request, cipher, purpose, qualified) }
                    finally { if (biometricRequest == request) biometricRequest = null }
                }
            },
            cancel = biometricPromptHost::cancel,
            capability = biometricPromptHost::capability,
            strings = biometricPromptHost::strings,
            eligible = { resumed && topResumed && !deviceRequiresLock() },
        )
        documentPicker = BackupDocumentPicker(this, model::onDocumentResult)
        model.pendingDocumentIntents.forEach(documentPicker::reattach)
        val systemDark = resources.configuration.uiMode and Configuration.UI_MODE_NIGHT_MASK == Configuration.UI_MODE_NIGHT_YES
        applySystemAppearance(model.uiPreferences.isDark(systemDark), bThemeColors(model.uiPreferences, systemDark).paper.toArgb())
        getSystemService(TextClassificationManager::class.java)?.setTextClassifier(TextClassifier.NO_OP)
        productReady = true
        model.updates.start()
        revealAllowedContent()
    }

    private fun applySystemAppearance(dark: Boolean, paper: Int) {
        val appearance = dark to paper
        if (appliedSystemAppearance == appearance) return
        if (Build.VERSION.SDK_INT >= 33) {
            // 系统安全占位按任务描述取底色，身份仅来自应用资源。
            val primaryColor = TypedValue()
            theme.resolveAttribute(android.R.attr.colorPrimary, primaryColor, true)
            setTaskDescription(ActivityManager.TaskDescription.Builder()
                .setLabel(applicationInfo.loadLabel(packageManager).toString())
                .setIcon(applicationInfo.icon)
                .setPrimaryColor(primaryColor.data)
                .setBackgroundColor(paper)
                .setStatusBarColor(paper)
                .setNavigationBarColor(paper)
                .build())
        }
        enableEdgeToEdge(
            statusBarStyle = if (dark) SystemBarStyle.dark(android.graphics.Color.TRANSPARENT)
                else SystemBarStyle.light(android.graphics.Color.TRANSPARENT, android.graphics.Color.TRANSPARENT),
            navigationBarStyle = if (dark) SystemBarStyle.dark(paper) else SystemBarStyle.light(paper, paper),
        )
        appliedSystemAppearance = appearance
    }

    override fun onTopResumedActivityChanged(isTopResumedActivity: Boolean) {
        // 实时任务卡片可能继续绘制已恢复的活动；失去前台资格后连锁定页也不呈现。
        topResumed = isTopResumedActivity
        if (isTopResumedActivity) revealAllowedContent() else hideContent()
        if (::model.isInitialized) model.observeClipboardHost(clipboardHost)
        super.onTopResumedActivityChanged(isTopResumedActivity)
    }

    override fun onPause() {
        // 暂停也禁止呈现；是否锁定由独立的会话规则决定。
        topResumed = false
        resumed = false
        hideContent()
        if (::model.isInitialized) model.observeClipboardHost(clipboardHost)
        super.onPause()
    }

    override fun onResume() {
        super.onResume()
        resumed = true
        revealAllowedContent()
        if (::model.isInitialized) model.observeClipboardHost(clipboardHost)
    }

    override fun onWindowFocusChanged(hasFocus: Boolean) {
        super.onWindowFocusChanged(hasFocus)
        if (::model.isInitialized) model.observeClipboardHost(clipboardHost)
    }

    override fun onUserInteraction() {
        if (::model.isInitialized) model.observeUserInteraction()
        super.onUserInteraction()
    }

    override fun dispatchTouchEvent(event: MotionEvent): Boolean {
        if (event.actionMasked == MotionEvent.ACTION_DOWN) {
            blockedTouch = ::model.isInitialized && !model.observeUserInteraction()
        }
        if (blockedTouch) {
            if (event.actionMasked == MotionEvent.ACTION_UP || event.actionMasked == MotionEvent.ACTION_CANCEL) {
                blockedTouch = false
            }
            return true
        }
        return super.dispatchTouchEvent(event)
    }

    private fun revealAllowedContent() {
        if (!resumed || !topResumed || isFinishing || isDestroyed) return
        if (deviceRequiresLock()) {
            contentVisible = false
            lockObservedBeforeEntry = !productReady
            existingModel()?.onScreenOff()
            cancelBiometricRequest()
            return
        }
        if (!productReady && termsAccepted) {
            enterProduct()
            return
        }
        if (::model.isInitialized) model.onForeground()
        contentVisible = true
        if (::model.isInitialized) model.observeClipboardHost(clipboardHost)
    }

    private fun hideContent() {
        contentVisible = false
        val existing = existingModel()
        if (deviceRequiresLock()) {
            lockObservedBeforeEntry = !productReady
            existing?.onScreenOff()
        } else {
            existing?.onBackground()
        }
        cancelBiometricRequest()
    }

    private fun cancelBiometricRequest() {
        if (::biometricPromptHost.isInitialized) biometricRequest?.let(biometricPromptHost::cancel)
    }

    private fun deviceRequiresLock(): Boolean =
        getSystemService(PowerManager::class.java)?.isInteractive != true ||
            getSystemService(KeyguardManager::class.java)?.isKeyguardLocked != false

    override fun onDestroy() {
        if (::model.isInitialized) {
            model.unbindClipboardHost(clipboardHost)
            model.unbindBiometricHost(biometricHost)
            if (isFinishing) model.onExplicitExit()
        }
        if (::documentPicker.isInitialized) documentPicker.close()
        if (::biometricPromptHost.isInitialized) biometricPromptHost.close()
        unregisterReceiver(screenEvents)
        super.onDestroy()
    }
}
