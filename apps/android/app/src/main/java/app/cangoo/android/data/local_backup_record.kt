package app.cangoo.android.data

import android.util.AtomicFile
import com.google.gson.Strictness
import com.google.gson.stream.JsonReader
import com.google.gson.stream.JsonToken
import com.google.gson.stream.JsonWriter
import java.io.File
import java.io.FileOutputStream
import java.io.OutputStreamWriter
import java.io.StringReader
import java.nio.file.Files
import java.time.Instant
import java.util.UUID

internal enum class LocalBackupScope { ALL, PASSWORDS, NOTES, CUSTOM }
internal data class LocalBackupRecord(val vaultId: String, val completedAt: Instant, val scope: LocalBackupScope)
internal sealed interface LocalBackupRecordState {
    data object Missing : LocalBackupRecordState
    data class Available(val record: LocalBackupRecord) : LocalBackupRecordState
    data object Unavailable : LocalBackupRecordState
}
internal enum class LocalBackupRecordWrite { SAVED, NOT_SAVED, UNVERIFIED }

// 只由现有 Store 的唯一存储互斥串行调用；非秘密本机提示不代表库权限或导出文件存续。
internal class LocalBackupRecordFile(private val directory: File, private val vaultId: String) {
    private val base = File(directory, "last_backup.json")
    private val backup = File(base.path + ".bak")
    private val temporary = File(base.path + ".new")
    private val atomic = AtomicFile(base)
    private val fields = setOf("version", "vault_id", "completed_at_utc", "scope")

    fun read(): LocalBackupRecordState = try {
        checkPaths()
        if (!base.exists() && !backup.exists()) {
            if (temporary.exists()) LocalBackupRecordState.Unavailable else LocalBackupRecordState.Missing
        }
        else {
            val bytes = atomic.openRead().use { input ->
                // openRead 恢复合法 .bak；恢复未完成时不能把不确定的 base 当最新值。
                checkPaths()
                require(base.isFile && !backup.exists() && !temporary.exists())
                val buffer = ByteArray(1025)
                var size = 0
                while (size < buffer.size) {
                    val count = input.read(buffer, size, buffer.size - size)
                    if (count < 0) break
                    size += count
                }
                require(size in 1..1024)
                buffer.copyOf(size)
            }
            LocalBackupRecordState.Available(decode(bytes))
        }
    } catch (_: Exception) { LocalBackupRecordState.Unavailable }

    fun write(record: LocalBackupRecord): LocalBackupRecordWrite {
        var output: FileOutputStream? = null
        var commitStarted = false
        var writeAttempted = false
        var previous: LocalBackupRecordState? = null
        try {
            require(validUuid(record.vaultId) && record.vaultId == vaultId)
            val timestamp = checkedTime(record.completedAt)
            checkPaths()
            previous = read()
            writeAttempted = true
            output = atomic.startWrite()
            // JsonWriter 只 flush，流由 AtomicFile 提交/回滚关闭。
            val writer = JsonWriter(OutputStreamWriter(output, Charsets.UTF_8)).apply { setStrictness(Strictness.STRICT) }
            writer.beginObject()
            writer.name("version").value(1L)
            writer.name("vault_id").value(record.vaultId)
            writer.name("completed_at_utc").value(timestamp)
            writer.name("scope").value(record.scope.name)
            writer.endObject()
            writer.flush()
            output.fd.sync()
            checkPaths()
            commitStarted = true
            atomic.finishWrite(output)
            output = null
            check(read() == LocalBackupRecordState.Available(record))
            syncDirectory(directory)
            return LocalBackupRecordWrite.SAVED
        } catch (_: Exception) {
            if (commitStarted) {
                try { output?.close() } catch (_: Exception) { /* 后续读取核实际值，不反向回滚。 */ }
                return LocalBackupRecordWrite.UNVERIFIED
            }
            try { if (output != null) atomic.failWrite(output) }
            catch (_: Exception) { return LocalBackupRecordWrite.UNVERIFIED }
            if (!writeAttempted) return LocalBackupRecordWrite.NOT_SAVED
            // 回滚完成也须核旧值；已有非法记录不能仅凭同为 Unavailable 宣称保旧已验证。
            return if (previous != LocalBackupRecordState.Unavailable && previous == read())
                LocalBackupRecordWrite.NOT_SAVED else LocalBackupRecordWrite.UNVERIFIED
        }
    }

    private fun checkPaths() {
        require(validUuid(vaultId))
        require(directory.isDirectory && !Files.isSymbolicLink(directory.toPath()) && directory.canonicalFile == directory.absoluteFile)
        listOf(base, backup, temporary).forEach { file ->
            require(!Files.isSymbolicLink(file.toPath()) && file.canonicalFile == file.absoluteFile)
            require(!file.exists() || file.isFile)
        }
    }

    private fun decode(bytes: ByteArray): LocalBackupRecord {
        val text = bytes.decodeToString(throwOnInvalidSequence = true)
        require(!text.startsWith('\uFEFF'))
        return JsonReader(StringReader(text)).use { reader ->
            reader.setStrictness(Strictness.STRICT)
            reader.setNestingLimit(2)
            val seen = mutableSetOf<String>()
            var id: String? = null
            var completedAt: Instant? = null
            var scope: LocalBackupScope? = null
            require(reader.peek() == JsonToken.BEGIN_OBJECT)
            reader.beginObject()
            while (reader.hasNext()) {
                val name = reader.nextName()
                require(seen.add(name))
                when (name) {
                    "version" -> { require(reader.peek() == JsonToken.NUMBER); require(reader.nextString() == "1") }
                    "vault_id" -> id = reader.strictString()
                    "completed_at_utc" -> {
                        val value = reader.strictString()
                        completedAt = Instant.parse(value).also { require(checkedTime(it) == value) }
                    }
                    "scope" -> {
                        val value = reader.strictString()
                        scope = requireNotNull(LocalBackupScope.entries.firstOrNull { it.name == value })
                    }
                    else -> throw IllegalArgumentException()
                }
            }
            reader.endObject()
            require(seen == fields && reader.peek() == JsonToken.END_DOCUMENT)
            require(id == vaultId && validUuid(requireNotNull(id)))
            LocalBackupRecord(requireNotNull(id), requireNotNull(completedAt), requireNotNull(scope))
        }
    }

    private fun JsonReader.strictString(): String {
        require(peek() == JsonToken.STRING)
        return nextString()
    }

    private fun checkedTime(value: Instant): String {
        // 采用原生 ISO-UTC 表达；限定可完整往返的毫秒值，拒绝精度损失及 epochMillis 溢出。
        require(Instant.ofEpochMilli(value.toEpochMilli()) == value)
        return value.toString()
    }

    private fun validUuid(value: String): Boolean = runCatching { UUID.fromString(value).toString() == value }.getOrDefault(false)
}
