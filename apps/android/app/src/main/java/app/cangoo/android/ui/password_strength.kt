package app.cangoo.android.ui

import app.cangoo.android.R
import android.app.Application
import androidx.annotation.MainThread
import java.nio.CharBuffer
import java.nio.charset.CodingErrorAction
import java.nio.charset.StandardCharsets

data class PasswordStrengthResult(val score: Int, internal val runtimeVersion: String = "") {
    init { require(score in 0..4) { "分析结果暂时不可用，请修改输入后重试。" } }
    val labelResource: Int get() = if (score < 3) R.string.strength_weak else if (score == 3) R.string.strength_fair else R.string.strength_strong
    val adviceResource: Int get() = if (score < 3) R.string.strength_advice_weak else R.string.strength_advice_other
}

internal enum class PasswordStrengthError { INVALID_INPUT, UNSUPPORTED, UNAVAILABLE }
internal sealed interface PasswordStrengthOutcome {
    data class Success(val result: PasswordStrengthResult) : PasswordStrengthOutcome
    data class Failure(val error: PasswordStrengthError) : PasswordStrengthOutcome
}

private const val InvalidStrengthInput = "请输入1–1024个字符的密码，不能含空字符或无效统一码。"

internal fun encodePasswordStrengthInput(value: String): ByteArray {
    require(value.isNotEmpty() && value.length <= 2048 && value.codePointCount(0, value.length) <= 1024 && '\u0000' !in value) {
        InvalidStrengthInput
    }
    val encoded = try {
        StandardCharsets.UTF_16LE.newEncoder().onMalformedInput(CodingErrorAction.REPORT)
            .onUnmappableCharacter(CodingErrorAction.REPORT).encode(CharBuffer.wrap(value))
    } catch (_: Exception) { throw IllegalArgumentException(InvalidStrengthInput) }
    return ByteArray(encoded.remaining()).also { result ->
        encoded.get(result)
        if (encoded.hasArray()) encoded.array().fill(0)
    }
}

internal fun decodePasswordStrengthResult(value: String): PasswordStrengthResult {
    require(value.length == 1 && value[0] in '0'..'4') { "分析结果暂时不可用，请修改输入后重试。" }
    return PasswordStrengthResult(value[0] - '0')
}

internal fun interface PasswordStrengthSessionFactory {
    fun create(onCreated: (PasswordStrengthSession) -> Unit, onFailure: (PasswordStrengthError) -> Unit)
}
internal interface PasswordStrengthSession {
    fun analyze(input: ByteArray, platform: String, account: String, onOutcome: (PasswordStrengthOutcome) -> Unit)
    fun close(onClosed: () -> Unit)
}

@MainThread
internal class PasswordStrengthOwner internal constructor(
    private val factory: PasswordStrengthSessionFactory,
    private var onOutcome: ((Long, PasswordStrengthOutcome) -> Unit)?,
) : AutoCloseable {
    constructor(application: Application, onOutcome: (Long, PasswordStrengthOutcome) -> Unit) :
        this(AndroidStrengthSessionFactory(application), onOutcome)

    private class Request(val id: Long, var input: ByteArray?, var platform: String = "", var account: String = "", val retain: Boolean = false) {
        var valid = true
        var closing = false
        var session: PasswordStrengthSession? = null
        fun discardInput() { input?.fill(0); input = null; platform = ""; account = "" }
    }
    private var current: Request? = null
    private var pending: Request? = null
    private var idle: PasswordStrengthSession? = null
    private var permanentlyClosed = false

    fun submit(requestId: Long, input: String, platform: String = "", account: String = "", retain: Boolean = false) {
        if (permanentlyClosed) return
        pending?.discardInput(); pending = null
        current?.let { it.valid = false; it.discardInput(); finish(it, null) }
        val bytes = try { encodePasswordStrengthInput(input) }
        catch (_: IllegalArgumentException) {
            releaseIdle()
            onOutcome?.invoke(requestId, PasswordStrengthOutcome.Failure(PasswordStrengthError.INVALID_INPUT))
            return
        }
        if (current?.session != null && current?.closing == false) {
            bytes.fill(0)
            onOutcome?.invoke(requestId, PasswordStrengthOutcome.Failure(PasswordStrengthError.UNAVAILABLE))
            return
        }
        // 超长上下文沿Windows规则整体忽略，不截断参与评分。
        fun context(value: String) = if (value.codePointCount(0, value.length) > 32) "" else value
        pending = Request(requestId, bytes, context(platform), context(account), retain)
        startNext()
    }

    fun cancel() {
        pending?.discardInput(); pending = null
        current?.let { it.valid = false; it.discardInput(); finish(it, null) }
        releaseIdle()
    }

    fun releaseIdle() {
        val session = idle ?: return
        idle = null
        val request = Request(0, null).also { it.valid = false; it.session = session }
        check(current == null)
        current = request
        finish(request, null)
    }

    override fun close() {
        permanentlyClosed = true
        onOutcome = null
        cancel()
    }

    private fun startNext() {
        if (permanentlyClosed || current != null) return
        val request = pending ?: return
        pending = null
        current = request
        fun ready(session: PasswordStrengthSession) {
            if (current !== request) { session.close {}; return }
            request.session = session
            if (!request.valid || permanentlyClosed) { finish(request, null); return }
            val bytes = request.input ?: run { finish(request, null); return }
            request.input = null
            try { session.analyze(bytes, request.platform, request.account) { outcome -> finish(request, outcome) } }
            catch (_: Exception) { finish(request, PasswordStrengthOutcome.Failure(PasswordStrengthError.UNAVAILABLE)) }
            finally { request.platform = ""; request.account = "" }
        }
        val warm = idle
        idle = null
        try {
            if (warm != null) ready(warm)
            else factory.create(::ready) { error ->
                if (current === request) {
                    request.discardInput(); current = null
                    if (request.valid && !permanentlyClosed) onOutcome?.invoke(request.id, PasswordStrengthOutcome.Failure(error))
                    startNext()
                }
            }
        } catch (_: Exception) {
            if (request.session != null) finish(request, PasswordStrengthOutcome.Failure(PasswordStrengthError.UNAVAILABLE))
            else {
                request.discardInput(); current = null
                if (request.valid && !permanentlyClosed) onOutcome?.invoke(request.id, PasswordStrengthOutcome.Failure(PasswordStrengthError.UNAVAILABLE))
                startNext()
            }
        }
    }

    private fun finish(request: Request, outcome: PasswordStrengthOutcome?) {
        if (current !== request || request.closing) return
        val session = request.session ?: return // 未决绑定保留迟到关闭责任。
        if (request.valid && request.retain && outcome is PasswordStrengthOutcome.Success && !permanentlyClosed) {
            request.discardInput(); request.session = null; current = null; idle = session
            onOutcome?.invoke(request.id, outcome)
            startNext()
            return
        }
        request.closing = true
        try { session.close {
            if (current === request) {
                request.discardInput(); request.session = null; current = null
                if (request.valid && !permanentlyClosed && outcome != null) onOutcome?.invoke(request.id, outcome)
                startNext()
            }
        } } catch (_: Exception) {
            request.closing = false
            val qualified = request.valid
            request.valid = false; request.discardInput()
            val waiting = pending
            waiting?.discardInput(); pending = null
            if (!permanentlyClosed && (waiting != null || qualified)) onOutcome?.invoke(waiting?.id ?: request.id,
                PasswordStrengthOutcome.Failure(PasswordStrengthError.UNAVAILABLE))
        }
    }
}
