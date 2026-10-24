package app.cangoo.android.ui

import android.hardware.biometrics.BiometricManager
import app.cangoo.android.R
import android.hardware.biometrics.BiometricPrompt
import android.os.Build
import android.os.CancellationSignal
import android.os.Looper
import androidx.activity.ComponentActivity
import app.cangoo.android.data.VaultBiometricAuthentication
import app.cangoo.android.data.VaultBiometricPurpose
import kotlinx.coroutines.CancellableContinuation
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlinx.coroutines.withContext
import kotlin.coroutines.resume
import javax.crypto.Cipher

internal data class BiometricText(
    val buttonLabel: String? = null,
    val promptMessage: String? = null,
    val settingName: String? = null,
)

// 只持当前系统操作；数据库秘密、持久提交及会话授权均由数据/模型所有者负责。
internal class BiometricPromptHost(private val activity: ComponentActivity, private val language: () -> UiLanguage = { UiLanguage.CHINESE }) {
    private var closed = false
    private var active: Request? = null

    suspend fun authenticate(
        requestId: Long,
        cipher: Cipher,
        purpose: VaultBiometricPurpose,
        qualified: () -> Boolean,
    ): VaultBiometricAuthentication = withContext<VaultBiometricAuthentication>(Dispatchers.Main.immediate) {
        if (closed || !allowed(qualified)) return@withContext VaultBiometricAuthentication.Cancelled
        active?.let { finish(it, VaultBiometricAuthentication.Cancelled, cancelSignal = true) }
        suspendCancellableCoroutine<VaultBiometricAuthentication> { continuation ->
            val request = Request(requestId, cipher, qualified, continuation)
            active = request
            continuation.invokeOnCancellation {
                onMain { if (active === request) finish(request, VaultBiometricAuthentication.Cancelled, cancelSignal = true) }
            }
            if (!current(request)) {
                finish(request, VaultBiometricAuthentication.Cancelled, cancelSignal = true)
                return@suspendCancellableCoroutine
            }
            try {
                val texts = localizedResources(activity, language())
                val prompt = BiometricPrompt.Builder(activity)
                    .setTitle(when (purpose) {
                        VaultBiometricPurpose.ENABLE -> texts.getString(R.string.enable_quick_unlock)
                        VaultBiometricPurpose.REBUILD -> texts.getString(R.string.verify_new_biometric)
                        VaultBiometricPurpose.UNLOCK -> texts.getString(R.string.unlock_current_vault)
                    })
                    .setSubtitle(strings().promptMessage ?: texts.getString(R.string.biometric_prompt_fallback))
                    .setNegativeButton(if (purpose == VaultBiometricPurpose.UNLOCK) texts.getString(R.string.use_master) else texts.getString(R.string.cancel), activity.mainExecutor) { _, _ ->
                        if (active === request) finish(request, VaultBiometricAuthentication.Cancelled, cancelSignal = true)
                    }.apply {
                        if (Build.VERSION.SDK_INT >= 30) setAllowedAuthenticators(BiometricManager.Authenticators.BIOMETRIC_STRONG)
                        else setDeviceCredentialAllowed(false)
                    }.build()
                prompt.authenticate(BiometricPrompt.CryptoObject(cipher), request.signal, activity.mainExecutor,
                    object : BiometricPrompt.AuthenticationCallback() {
                        override fun onAuthenticationFailed() {
                            if (active === request && !current(request)) finish(request, VaultBiometricAuthentication.Cancelled, cancelSignal = true)
                        }

                        override fun onAuthenticationError(errorCode: Int, errString: CharSequence) {
                            if (active !== request) return
                            val outcome = if (!current(request) || errorCode in setOf(
                                    BiometricPrompt.BIOMETRIC_ERROR_CANCELED,
                                    BiometricPrompt.BIOMETRIC_ERROR_USER_CANCELED,
                                )) VaultBiometricAuthentication.Cancelled else VaultBiometricAuthentication.Failure(errorCode)
                            finish(request, outcome, cancelSignal = false)
                        }

                        override fun onAuthenticationSucceeded(result: BiometricPrompt.AuthenticationResult) {
                            if (active !== request) return
                            if (!current(request)) {
                                finish(request, VaultBiometricAuthentication.Cancelled, cancelSignal = true)
                                return
                            }
                            val original = request.cipher
                            val outcome = if (original != null && result.cryptoObject?.cipher === original)
                                VaultBiometricAuthentication.Authenticated(original)
                            else VaultBiometricAuthentication.Failure(BiometricPrompt.BIOMETRIC_ERROR_UNABLE_TO_PROCESS)
                            // AAD 与 doFinal 留给数据所有者；此处仅交回同一个已认证操作。
                            finish(request, outcome, cancelSignal = false)
                        }
                    })
            } catch (_: Exception) {
                if (active === request) finish(request,
                    if (current(request)) VaultBiometricAuthentication.Failure(BiometricPrompt.BIOMETRIC_ERROR_HW_UNAVAILABLE)
                    else VaultBiometricAuthentication.Cancelled, cancelSignal = true)
            }
        }
    }

    fun cancel(requestId: Long) = onMain {
        active?.takeIf { it.id == requestId }?.let { finish(it, VaultBiometricAuthentication.Cancelled, cancelSignal = true) }
    }

    fun close() = onMain {
        if (!closed) {
            closed = true
            active?.let { finish(it, VaultBiometricAuthentication.Cancelled, cancelSignal = true) }
        }
    }

    fun strings(): BiometricText {
        if (Build.VERSION.SDK_INT < 31) return BiometricText()
        val strings = runCatching { activity.getSystemService(BiometricManager::class.java)
            .getStrings(BiometricManager.Authenticators.BIOMETRIC_STRONG) }.getOrNull() ?: return BiometricText()
        return BiometricText(
            runCatching { strings.buttonLabel?.toString()?.takeIf { it.isNotBlank() } }.getOrNull(),
            runCatching { strings.promptMessage?.toString()?.takeIf { it.isNotBlank() } }.getOrNull(),
            runCatching { strings.settingName?.toString()?.takeIf { it.isNotBlank() } }.getOrNull(),
        )
    }

    fun capability(): Int = try {
        val manager = activity.getSystemService(BiometricManager::class.java)
        if (Build.VERSION.SDK_INT >= 30) manager.canAuthenticate(BiometricManager.Authenticators.BIOMETRIC_STRONG)
        else manager.canAuthenticate()
    } catch (_: Exception) { BiometricManager.BIOMETRIC_ERROR_HW_UNAVAILABLE }

    private fun current(request: Request) = !closed && active === request && request.continuation?.isActive == true &&
        request.qualified?.let(::allowed) == true

    private fun allowed(qualified: () -> Boolean) = try { qualified() } catch (_: Exception) { false }

    private fun finish(request: Request, outcome: VaultBiometricAuthentication, cancelSignal: Boolean) {
        if (active !== request) return
        active = null
        val continuation = request.continuation
        request.continuation = null
        request.cipher = null
        request.qualified = null
        if (cancelSignal) runCatching { request.signal.cancel() }
        // 主动取消立即结算等待，不依赖系统稍后的终止回调或外层协程是否可取消。
        if (continuation?.isActive == true) continuation.resume(outcome)
    }

    private fun onMain(action: () -> Unit) {
        if (Looper.myLooper() == Looper.getMainLooper()) action() else activity.mainExecutor.execute { action() }
    }

    private class Request(
        val id: Long,
        var cipher: Cipher?,
        var qualified: (() -> Boolean)?,
        var continuation: CancellableContinuation<VaultBiometricAuthentication>?,
        val signal: CancellationSignal = CancellationSignal(),
    )
}
