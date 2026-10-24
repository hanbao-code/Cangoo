package app.cangoo.android.ui

import android.app.Application
import android.app.Service
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.content.ServiceConnection
import android.os.Bundle
import android.os.Handler
import android.os.IBinder
import android.os.Looper
import android.os.Message
import android.os.Messenger
import android.os.Process
import com.chaquo.python.Python
import com.chaquo.python.android.AndroidPlatform
import java.nio.ByteBuffer
import java.nio.charset.CodingErrorAction
import java.nio.charset.StandardCharsets
import java.util.concurrent.Executors

private const val Analyze = 1
private const val Result = 2
private const val Failed = 3
private const val Close = 4

/** 仅绑定于本应用的评分进程；数据库和密钥不进入此服务。 */
class PasswordStrengthService : Service() {
    private val worker = Executors.newSingleThreadExecutor()
    private val main = Handler(Looper.getMainLooper())
    private var busy = false
    private var runtime = ""
    private var client: IBinder? = null
    private val clientDeath = IBinder.DeathRecipient { terminate() }
    private val endpoint = Messenger(Handler(Looper.getMainLooper()) { message ->
        if (message.sendingUid == Process.myUid()) when (message.what) {
            Analyze -> analyze(message)
            Close -> terminate()
        }
        true
    })

    override fun onBind(intent: Intent): IBinder = endpoint.binder
    override fun onUnbind(intent: Intent): Boolean { terminate(); return false }
    override fun onDestroy() { super.onDestroy(); terminate() }

    private fun terminate() {
        worker.shutdownNow()
        // 完整算法不能靠线程中断取消，只终止这个私有评分进程。
        Process.killProcess(Process.myPid())
    }

    private fun send(target: Messenger, what: Int, request: Long, score: String? = null) {
        try { target.send(Message.obtain(null, what).apply { data = Bundle().apply {
            putLong("request", request)
            if (score != null) { putString("score", score); putString("runtime", runtime) }
        } }) } catch (_: Exception) { terminate() }
    }

    private fun analyze(message: Message) {
        val target = message.replyTo ?: return
        var input: ByteArray? = null
        var request = 0L
        try {
            val data = message.data
            require(data.keySet() == setOf("request", "input", "platform", "account"))
            require(data.get("request") is Long)
            request = data.getLong("request")
            require(request > 0 && !busy)
            input = data.getByteArray("input") ?: error("输入缺失")
            val platform = data.getString("platform") ?: error("上下文缺失")
            val account = data.getString("account") ?: error("上下文缺失")
            require(input.size in 0..4096 && input.size % 2 == 0)
            val password = StandardCharsets.UTF_16LE.newDecoder().onMalformedInput(CodingErrorAction.REPORT)
                .onUnmappableCharacter(CodingErrorAction.REPORT).decode(ByteBuffer.wrap(input)).toString()
            if (password.isNotEmpty()) encodePasswordStrengthInput(password).fill(0)
            for (value in listOf(platform, account)) {
                require(value.codePointCount(0, value.length) <= 32 && '\u0000' !in value)
                StandardCharsets.UTF_8.newEncoder().onMalformedInput(CodingErrorAction.REPORT).encode(java.nio.CharBuffer.wrap(value))
            }
            if (client == null) {
                target.binder.linkToDeath(clientDeath, 0)
                client = target.binder
            }
            require(client == target.binder)
            busy = true
            val ownRequest = request
            worker.execute {
                val result = try {
                    if (!Python.isStarted()) Python.start(AndroidPlatform(applicationContext))
                    val bridge = Python.getInstance().getModule("strength_bridge")
                    if (runtime.isEmpty()) runtime = bridge.callAttr("runtime").toString()
                    bridge.callAttr("evaluate", password, platform, account)
                        .toString().also { decodePasswordStrengthResult(it) }
                } catch (_: Throwable) { null }
                main.post {
                    busy = false
                    send(target, if (result == null) Failed else Result, ownRequest, result)
                }
            }
        } catch (_: Exception) { send(target, Failed, request) }
        finally { input?.fill(0) }
    }
}

internal class AndroidStrengthSessionFactory(private val application: Application) : PasswordStrengthSessionFactory {
    override fun create(onCreated: (PasswordStrengthSession) -> Unit, onFailure: (PasswordStrengthError) -> Unit) {
        var bound = false
        var settled = false
        var session: AndroidStrengthSession? = null
        lateinit var connection: ServiceConnection
        fun release() { if (bound) { bound = false; application.unbindService(connection) } }
        fun failed() {
            val existing = session
            if (existing != null) existing.died()
            else if (!settled) { settled = true; release(); onFailure(PasswordStrengthError.UNAVAILABLE) }
        }
        connection = object : ServiceConnection {
            override fun onServiceConnected(name: ComponentName, binder: IBinder) {
                if (settled) return
                try {
                    val created = AndroidStrengthSession(application, binder, ::release)
                    session = created
                    settled = true
                    onCreated(created)
                } catch (_: Exception) { failed() }
            }
            override fun onServiceDisconnected(name: ComponentName) = failed()
            override fun onBindingDied(name: ComponentName) = failed()
            override fun onNullBinding(name: ComponentName) = failed()
        }
        try {
            bound = application.bindService(Intent(application, PasswordStrengthService::class.java), connection, Context.BIND_AUTO_CREATE)
            if (!bound) failed()
        } catch (_: Exception) { failed() }
    }
}

private class AndroidStrengthSession(
    private val application: Application,
    private val binder: IBinder,
    private val release: () -> Unit,
) : PasswordStrengthSession {
    private var request = 0L
    private var outcome: ((PasswordStrengthOutcome) -> Unit)? = null
    private var closed: (() -> Unit)? = null
    private var dead = false
    private var stopping = false
    private val remote = Messenger(binder)
    private val receiver = Messenger(Handler(Looper.getMainLooper()) { message ->
        if (!dead && !stopping && message.sendingUid == Process.myUid() && message.data.get("request") is Long &&
            message.data.getLong("request") == request) {
            val result = try {
                require(message.what == Result && message.data.keySet() == setOf("request", "score", "runtime"))
                val runtime = requireNotNull(message.data.getString("runtime"))
                require(runtime.length in 1..64 && runtime.all { it in '0'..'9' || it == '.' || it == '/' })
                PasswordStrengthOutcome.Success(decodePasswordStrengthResult(requireNotNull(message.data.getString("score"))).copy(runtimeVersion = runtime))
            } catch (_: Exception) { PasswordStrengthOutcome.Failure(PasswordStrengthError.UNAVAILABLE) }
            val callback = outcome; outcome = null
            callback?.invoke(result)
        }
        true
    })
    private val death = IBinder.DeathRecipient { application.mainExecutor.execute(::died) }
    init { binder.linkToDeath(death, 0) }

    override fun analyze(input: ByteArray, platform: String, account: String, onOutcome: (PasswordStrengthOutcome) -> Unit) {
        check(!stopping && !dead && outcome == null)
        outcome = onOutcome
        request++
        try { remote.send(Message.obtain(null, Analyze).apply {
            replyTo = receiver
            data = Bundle().apply {
                putLong("request", request); putByteArray("input", input)
                putString("platform", platform); putString("account", account)
            }
        }) } catch (_: Exception) {
            val callback = outcome; outcome = null
            callback?.invoke(PasswordStrengthOutcome.Failure(PasswordStrengthError.UNAVAILABLE))
        } finally { input.fill(0) }
    }

    override fun close(onClosed: () -> Unit) {
        outcome = null
        if (dead) { onClosed(); return }
        check(closed == null)
        closed = onClosed
        stopping = true
        // 发送关闭后仍持绑定和死亡监听，只有真实Binder死亡才放行下一个进程。
        try { remote.send(Message.obtain(null, Close)) }
        catch (_: Exception) { if (!binder.isBinderAlive) died() else { closed = null; stopping = false; throw IllegalStateException("评分进程尚未关闭") } }
    }

    fun died() {
        if (dead) return
        dead = true
        binder.unlinkToDeath(death, 0)
        release()
        val completion = closed; closed = null
        val callback = outcome; outcome = null
        if (completion != null) completion() else callback?.invoke(PasswordStrengthOutcome.Failure(PasswordStrengthError.UNAVAILABLE))
    }
}
