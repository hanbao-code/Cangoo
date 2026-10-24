package app.cangoo.android.ui

import android.os.SystemClock
import kotlinx.coroutines.CoroutineDispatcher
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

internal enum class ClipboardClearResult { REQUESTED_UNVERIFIED, FAILED }

internal data class ClipboardDuty(
    val marker: String,
    val deadlineElapsedRealtime: Long,
    val confirmationDeadlineElapsedRealtime: Long,
    val phase: ClipboardPublicationStatus,
    val firstUsed: Boolean = false,
    val restoreUsed: Boolean = false,
    val lastResult: ClipboardClearResult? = null,
)

// 所有入口由主线程串行调用；控制器不持宿主、系统描述或复制正文。
internal class ClipboardController(
    scope: CoroutineScope,
    private val clear: () -> Unit,
    dispatcher: CoroutineDispatcher = Dispatchers.Main,
    private val now: () -> Long = SystemClock::elapsedRealtime,
    private val onChanged: (ClipboardDuty?) -> Unit = {},
    private val restoreEligible: () -> Boolean = { true },
    private val onClearAttempt: (ClipboardClearResult) -> Unit = {},
) {
    private val jobs = SupervisorJob(scope.coroutineContext[Job])
    private val work = CoroutineScope(scope.coroutineContext + jobs + dispatcher)
    private var automaticJob: Job? = null
    private var scheduleToken = 0L
    private var publicationToken = 0L
    private var closed = false
    var state: ClipboardDuty? = null
        private set

    fun prepare(publication: ClipboardPublication, seconds: Int) {
        check(!closed)
        require(publication.status == ClipboardPublicationStatus.PREPARED && publication.marker.isNotEmpty())
        require(seconds in setOf(5, 30, 60))
        val deadline = publication.preparedAtElapsedRealtime + seconds * 1000L
        val earlier = state?.deadlineElapsedRealtime?.coerceAtMost(deadline) ?: deadline
        publicationToken++
        invalidateAutomatic()
        state = ClipboardDuty(publication.marker, earlier, deadline, publication.status)
        enqueueAutomatic((earlier - now()).coerceAtLeast(0L), restore = false)
        onChanged(state)
    }

    fun confirm(publication: ClipboardPublication) {
        val duty = state ?: return
        if (closed || publication.status != ClipboardPublicationStatus.CONFIRMED ||
            publication.marker != duty.marker || duty.phase != ClipboardPublicationStatus.PREPARED) return
        publicationToken++
        invalidateAutomatic()
        state = duty.copy(deadlineElapsedRealtime = duty.confirmationDeadlineElapsedRealtime, phase = publication.status)
        if (!duty.firstUsed) enqueueAutomatic((state!!.deadlineElapsedRealtime - now()).coerceAtLeast(0L), restore = false)
        onChanged(state)
    }

    fun requestSecurityClear() {
        if (closed || state?.firstUsed != false) return
        invalidateAutomatic()
        enqueueAutomatic(0L, restore = false)
    }

    fun onForegroundRestore(eligible: Boolean) {
        val duty = state ?: return
        if (closed || !eligible) return
        if (!duty.firstUsed) {
            if (now() >= duty.deadlineElapsedRealtime) requestSecurityClear()
        } else if (!duty.restoreUsed) {
            invalidateAutomatic()
            enqueueAutomatic(0L, restore = true)
        }
    }

    fun manualClear() {
        val duty = state ?: return
        if (closed) return
        invalidateAutomatic()
        val publication = publicationToken
        // 独立保留每次明确操作；新发布或确认仍使旧操作失效。
        work.launch {
            if (!closed && publication == publicationToken && state?.marker == duty.marker &&
                state?.deadlineElapsedRealtime == duty.deadlineElapsedRealtime) attempt(restore = false)
        }
    }

    fun close() {
        if (closed) return
        closed = true
        publicationToken++
        invalidateAutomatic()
        if (state?.firstUsed == false) attempt(restore = false)
        work.cancel()
    }

    private fun invalidateAutomatic() {
        scheduleToken++
        automaticJob?.cancel()
        automaticJob = null
    }

    private fun enqueueAutomatic(wait: Long, restore: Boolean) {
        val duty = state ?: return
        val token = scheduleToken
        // 普通主队列先结束同步发布栈，零等待也不能在准备回调内清理。
        automaticJob = work.launch {
            delay(wait)
            val current = state
            if (closed || token != scheduleToken || current?.marker != duty.marker ||
                current.deadlineElapsedRealtime != duty.deadlineElapsedRealtime) return@launch
            if (restore) {
                if (!current.firstUsed || current.restoreUsed) return@launch
                if (!restoreEligible()) return@launch
            } else if (current.firstUsed) return@launch
            attempt(restore)
        }
    }

    private fun attempt(restore: Boolean) {
        val duty = state ?: return
        invalidateAutomatic()
        state = duty.copy(firstUsed = true, restoreUsed = duty.restoreUsed || restore)
        val result = try {
            clear()
            ClipboardClearResult.REQUESTED_UNVERIFIED
        } catch (_: Exception) {
            ClipboardClearResult.FAILED
        }
        state = state!!.copy(lastResult = result)
        onChanged(state)
        onClearAttempt(result)
    }
}
