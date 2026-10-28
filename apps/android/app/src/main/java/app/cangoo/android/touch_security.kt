package app.cangoo.android

import android.view.MotionEvent

/** 一次遮挡使整条手势失效，移开覆盖层后的抬起不能重新成为确认。 */
internal class ObscuredTouchGuard {
    private var blocked = false

    fun rejects(flags: Int, starts: Boolean, ends: Boolean): Boolean {
        if (starts) blocked = false
        blocked = blocked || flags and (MotionEvent.FLAG_WINDOW_IS_OBSCURED or MotionEvent.FLAG_WINDOW_IS_PARTIALLY_OBSCURED) != 0
        return blocked.also { if (ends) blocked = false }
    }
}

/** 原生窗口先拒绝遮挡；Compose可能省略同坐标MOVE，不能在指针转换后才判定。 */
internal class ProtectedTouchDispatcher {
    private val obscuredTouch = ObscuredTouchGuard()
    private var blocked = false

    fun dispatch(event: MotionEvent, allowed: () -> Boolean, forward: (MotionEvent) -> Boolean): Boolean {
        val starts = event.actionMasked == MotionEvent.ACTION_DOWN
        val ends = event.actionMasked == MotionEvent.ACTION_UP || event.actionMasked == MotionEvent.ACTION_CANCEL
        val obscured = obscuredTouch.rejects(event.flags, starts, ends)
        if (starts) blocked = false
        if (obscured && !blocked && !starts) {
            val cancel = MotionEvent.obtain(event).apply { action = MotionEvent.ACTION_CANCEL }
            try { forward(cancel) } finally { cancel.recycle() }
        }
        blocked = blocked || obscured || starts && !allowed()
        if (blocked) {
            if (ends) blocked = false
            return true
        }
        return forward(event)
    }
}
