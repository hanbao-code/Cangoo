package app.cangoo.android.data

/** 一次操作的预留量与实时堆余量共同约束分配；不改变备份协议容量。 */
internal class BackupMemoryBudget(private val available: () -> Long = {
    Runtime.getRuntime().let { it.maxMemory() - (it.totalMemory() - it.freeMemory()) }
}) {
    private val capacity = (available() - WORKING_RESERVE).coerceAtLeast(0)
    private var reserved = 0L

    fun reserve(bytes: Long) {
        if (bytes < 0 || bytes > capacity - reserved) unavailable()
        checkAvailable(bytes)
        reserved += bytes
    }

    fun release(bytes: Long) { check(bytes in 0..reserved); reserved -= bytes }

    fun checkAvailable(bytes: Long) {
        if (bytes < 0 || bytes > available() - WORKING_RESERVE) unavailable()
    }

    inline fun <T> temporary(bytes: Long, work: () -> T): T {
        reserve(bytes)
        return try { work() } finally { release(bytes) }
    }

    companion object {
        // 8KiB流、JSON字段集合、GCM及单个数据库读取之外留16MiB给宿主的并发小分配；已有占用另由Runtime计入。
        const val WORKING_RESERVE = 16L * 1024 * 1024
        // Argon2固定19MiB块，加块对象/引用数组及实现工作区，向上取24MiB。
        const val KDF_BYTES = 24L * 1024 * 1024
        // UTF-16结果每字节最多2字节；StringBuilder增长时旧/新数组合计最多6倍，已读字符串占用同一总预算。
        fun textPeak(bytes: Long): Long = Math.multiplyExact(bytes, 6L)
        // 每条最多14个字符串头、记录/解析对象、列表引用及比较预览的索引/摘要节点，向上取2KiB；正文另计。
        const val RECORD_BYTES = 2048L
        // 恢复码的字符串头、记录、列表引用及查重节点，正文仍计入textPeak。
        const val RECOVERY_CODE_BYTES = 256L
        private fun unavailable(): Nothing = throw BackupProtocolException(BackupProblem.MEMORY)
    }
}
