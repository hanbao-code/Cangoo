package app.cangoo.android.ui

import android.content.ClipData
import android.content.ClipDescription
import android.content.ClipboardManager
import android.os.PersistableBundle
import android.os.SystemClock
import androidx.compose.ui.platform.Clipboard
import androidx.compose.ui.platform.ClipEntry
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.currentCoroutineContext
import kotlinx.coroutines.ensureActive
import java.util.UUID

internal const val CLIPBOARD_COPY_MARKER = "app.cangoo.android.copy_marker"
internal const val CLIPBOARD_PUBLICATION_UNCONFIRMED = "未能确认复制，请重试。"

internal enum class ClipboardPublicationStatus { PREPARED, CONFIRMED }

internal data class ClipboardPublication(
    val marker: String,
    val preparedAtElapsedRealtime: Long,
    val status: ClipboardPublicationStatus,
)

// 仅隔离两次系统调用，公开替身无需取得或操作系统剪贴板。
internal interface ClipboardPublishTransport {
    fun setPrimaryClip(clip: ClipData)
    fun getPrimaryClipDescription(): ClipDescription?
    fun clearPrimaryClip()
}

internal class AndroidClipboardPublishTransport(private val clipboard: ClipboardManager) : ClipboardPublishTransport {
    override fun setPrimaryClip(clip: ClipData) = clipboard.setPrimaryClip(clip)
    override fun getPrimaryClipDescription(): ClipDescription? = clipboard.primaryClipDescription
    override fun clearPrimaryClip() = clipboard.clearPrimaryClip()
}

internal enum class ClipboardField(val label: String) {
    TEXT("文字"), GENERATED("密码"), ACCOUNT("账号"), PASSWORD("密码"), TOTP("动态口令"), RECOVERY("恢复码"),
}

internal class ClipboardPublisher(
    private val transport: ClipboardPublishTransport,
    private val qualified: () -> Boolean,
    private val onFailure: (String) -> Unit,
    private val onPrepared: (ClipboardPublication) -> Unit = {},
    private val onConfirmed: (ClipboardPublication) -> Unit = {},
) {
    // 业务按钮也须在独立子协程中调用，或显式捕获取消，不能裸放在点击回调内。
    fun publish(clip: ClipData?): ClipboardPublication {
        try {
            // 空项表示框架清空请求；本原语只发布复制，不裁决清理政策。
            if (clip == null || clip.itemCount == 0 || !qualified()) abort()
            val marker = UUID.randomUUID().toString()
            val extras = clip.description.extras?.let { PersistableBundle(it) } ?: PersistableBundle()
            extras.putString(CLIPBOARD_COPY_MARKER, marker)
            // 与系统常量同值的官方兼容键，覆盖安装下限29。
            extras.putBoolean("android.content.extra.IS_SENSITIVE", true)
            // 只附加描述，保留所有完整项目、格式和已有附加资料，不缓存正文。
            clip.description.extras = extras
            val prepared = ClipboardPublication(marker, SystemClock.elapsedRealtime(), ClipboardPublicationStatus.PREPARED)
            // 父层在写入前记录待核验责任；后续失败没有撤销责任的回调。
            onPrepared(prepared)
            if (!qualified()) abort()
            transport.setPrimaryClip(clip)
            if (!qualified()) abort()
            val actualMarker = transport.getPrimaryClipDescription()?.extras?.getString(CLIPBOARD_COPY_MARKER)
            if (!qualified() || actualMarker != marker) abort()
            val confirmed = prepared.copy(status = ClipboardPublicationStatus.CONFIRMED)
            onConfirmed(confirmed)
            return confirmed
        } catch (canceled: CancellationException) {
            throw canceled
        } catch (_: Exception) {
            abort()
        }
    }

    private fun abort(): Nothing {
        try {
            onFailure(CLIPBOARD_PUBLICATION_UNCONFIRMED)
        } catch (_: Exception) {
            // 提示失败也不能让剪切继续，或把原始异常交给界面作用域。
        }
        throw CancellationException(CLIPBOARD_PUBLICATION_UNCONFIRMED)
    }
}

// 框架复制和剪切在发布返回后才更新文字；失败只取消当前操作子协程。
internal class PublishingClipboard(
    delegate: Clipboard,
    private val publisher: ClipboardPublisher,
) : Clipboard by delegate {
    override suspend fun setClipEntry(clipEntry: ClipEntry?) {
        currentCoroutineContext().ensureActive()
        publisher.publish(clipEntry?.clipData)
    }
}

// 键盘与输入法快捷操作也可能绕过掩码菜单；失败不得继续剪切正文。
internal class GuardedClipboard(private val delegate: Clipboard, private val allowed: () -> Boolean) : Clipboard by delegate {
    override suspend fun setClipEntry(clipEntry: ClipEntry?) {
        currentCoroutineContext().ensureActive()
        if (!allowed()) throw CancellationException(CLIPBOARD_PUBLICATION_UNCONFIRMED)
        delegate.setClipEntry(clipEntry)
    }
}
