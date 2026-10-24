package app.cangoo.android.ui

import android.content.Intent
import android.net.Uri
import android.os.Handler
import android.os.Looper
import androidx.activity.ComponentActivity
import androidx.activity.result.ActivityResultLauncher
import androidx.activity.result.contract.ActivityResultContracts
import androidx.annotation.MainThread
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import java.util.UUID

internal enum class BackupDocumentKind { IMPORT, EXPORT }

// 仅是内存中的非秘密关联，不代表库会话、文件可信性或业务操作权限。
internal data class BackupDocumentIntent(
    val kind: BackupDocumentKind,
    val vaultId: String,
    val requestId: String,
    val uri: Uri? = null,
) {
    override fun toString() = "BackupDocumentIntent(关联已隐藏)"
}

internal enum class BackupDocumentOutcome { SELECTED, CANCELED, LAUNCH_FAILED }

@MainThread
internal class BackupDocumentPicker(
    private val activity: ComponentActivity,
    private val onResult: (BackupDocumentIntent, BackupDocumentOutcome) -> Unit,
) {
    private val registry = activity.activityResultRegistry
    private val queue = Handler(Looper.getMainLooper())
    private val openDocument = ActivityResultContracts.OpenDocument()
    private val createDocument = ActivityResultContracts.CreateDocument("application/json")
    private val resultContract = ActivityResultContracts.StartActivityForResult()
    private val registrations = mutableMapOf<String, Registration>()
    private val usedKeys = mutableSetOf<String>()
    private var closed = activity.lifecycle.currentState == Lifecycle.State.DESTROYED
    private val lifecycleObserver = LifecycleEventObserver { _, event ->
        if (event == Lifecycle.Event.ON_DESTROY) close()
    }

    init {
        if (!closed) activity.lifecycle.addObserver(lifecycleObserver)
    }

    // 只由用户点击调用。重复请求或重建后已重新登记的请求不会再次启动选择器。
    fun launch(intent: BackupDocumentIntent): Boolean {
        if (intent.uri != null) return false
        if (closed) {
            onResult(intent, BackupDocumentOutcome.LAUNCH_FAILED)
            return false
        }
        val key = key(intent)
        if (!usedKeys.add(key)) return false
        val registration = Registration(key, intent)
        if (!register(registration) || registration.completed || closed) return false
        return try {
            registration.launcher!!.launch(chooserIntent(intent.kind))
            true
        } catch (_: Exception) {
            finish(registration, null, BackupDocumentOutcome.LAUNCH_FAILED)
            false
        }
    }

    // 只接回保留模型中的原进行中意图；登记本身可能同步交付系统暂存结果。
    fun reattach(intent: BackupDocumentIntent) {
        if (closed || intent.uri != null) return
        val key = key(intent)
        if (usedKeys.add(key)) register(Registration(key, intent))
    }

    fun close() {
        if (closed) return
        closed = true
        activity.lifecycle.removeObserver(lifecycleObserver)
        registrations.values.toList().forEach(::release)
        usedKeys.clear()
    }

    private fun register(registration: Registration): Boolean {
        registrations[registration.key] = registration
        return try {
            // 不带LifecycleOwner的重载允许已STARTED时动态登记；销毁由本组件精确解除。
            registration.launcher = registry.register(registration.key, resultContract) { result ->
                val original = registration.original
                val uri = when (original.kind) {
                    BackupDocumentKind.IMPORT -> openDocument.parseResult(result.resultCode, result.data)
                    BackupDocumentKind.EXPORT -> createDocument.parseResult(result.resultCode, result.data)
                }
                finish(registration, uri, if (uri == null) BackupDocumentOutcome.CANCELED else BackupDocumentOutcome.SELECTED)
            }
            if (closed) release(registration)
            true
        } catch (_: Exception) {
            finish(registration, null, BackupDocumentOutcome.LAUNCH_FAILED)
            false
        }
    }

    private fun finish(registration: Registration, uri: Uri?, outcome: BackupDocumentOutcome) {
        if (registration.completed || closed) return
        registration.completed = true
        // Registry先调用结果闭包再移除进行中键；排到本轮回调之后解除，属于事件顺序而非计时补偿。
        queue.post { release(registration) }
        onResult(registration.original.copy(uri = uri), outcome)
    }

    private fun release(registration: Registration) {
        registration.launcher?.unregister()
        registration.launcher = null
        if (registrations[registration.key] === registration) registrations.remove(registration.key)
    }

    private fun chooserIntent(kind: BackupDocumentKind): Intent = when (kind) {
        BackupDocumentKind.IMPORT -> openDocument.createIntent(activity, arrayOf("*/*"))
        BackupDocumentKind.EXPORT -> createDocument.createIntent(activity, "cangoo.pdmbackup.json")
    }.apply {
        addCategory(Intent.CATEGORY_OPENABLE)
        // 只是系统选择器提示；可信提供方、真实文件能力与读写验证仍由数据层判断。
        putExtra(Intent.EXTRA_LOCAL_ONLY, true)
        addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
        if (kind == BackupDocumentKind.EXPORT) addFlags(Intent.FLAG_GRANT_WRITE_URI_PERMISSION)
    }

    private fun key(intent: BackupDocumentIntent): String =
        "cangoo-backup:$processNamespace:${intent.requestId}"

    private class Registration(val key: String, val original: BackupDocumentIntent) {
        var launcher: ActivityResultLauncher<Intent>? = null
        var completed = false
    }

    private companion object {
        // 同进程配置重建保持键；本组件不另存/恢复此值，新进程也不恢复旧请求关联。
        // 系统仍会自行保存Registry运输状态；那些键和暂存结果不是业务意图或库授权。
        val processNamespace = UUID.randomUUID().toString()
    }
}
