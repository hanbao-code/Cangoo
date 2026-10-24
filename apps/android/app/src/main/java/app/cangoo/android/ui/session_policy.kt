package app.cangoo.android.ui

data class SecuritySettings(val idleMinutes: Int = 5, val lockOnLeave: Boolean = false) {
    init { require(idleMinutes in setOf(0, 1, 5, 15)) }
}

internal class IdleDeadline(initialInteraction: Long) {
    private var lastInteraction: Long? = initialInteraction

    fun remaining(now: Long, minutes: Int): Long? {
        require(minutes in setOf(0, 1, 5, 15))
        val last = lastInteraction ?: return null
        return if (minutes == 0) null else (minutes * 60_000L - (now - last)).coerceAtLeast(0L)
    }

    fun consumeExpired(now: Long, minutes: Int): Boolean {
        if (remaining(now, minutes) != 0L) return false
        clear()
        return true
    }

    fun interact(now: Long, minutes: Int): Boolean {
        // 先结算旧期限，迟到输入不能把已过期会话续期。
        if (consumeExpired(now, minutes)) return false
        lastInteraction = now
        return true
    }

    fun clear() { lastInteraction = null }
}
