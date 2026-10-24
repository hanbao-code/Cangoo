package app.cangoo.android.ui

import android.content.Context
import android.util.AtomicFile
import android.util.JsonReader
import android.util.JsonToken
import android.util.JsonWriter
import app.cangoo.android.BuildConfig
import app.cangoo.android.data.PublicRelease
import app.cangoo.android.data.publicVersionCompare
import app.cangoo.android.data.releasePageUrl
import java.io.File
import java.io.FileOutputStream
import java.io.IOException
import java.io.StringReader
import java.io.StringWriter
import java.time.Instant
import java.util.UUID

internal data class UpdateCheckPreferences(
    val enabled: Boolean = true,
    val intervalDays: Int = 1,
    val lastAttemptMillis: Long? = null,
    val attemptId: String? = null,
    val checkedAtMillis: Long? = null,
    val checkedArchitecture: String? = null,
    val release: PublicRelease? = null,
    val ignoredVersions: Map<String, Long> = emptyMap(),
) {
    init {
        require(intervalDays > 0)
        require(lastAttemptMillis == null || lastAttemptMillis >= 0)
        require(checkedAtMillis == null || checkedAtMillis >= 0)
        require(checkedAtMillis == null || lastAttemptMillis != null)
        require((checkedAtMillis == null) == (checkedArchitecture == null))
        require(checkedArchitecture == null || checkedArchitecture in setOf("arm64", "x64", "arm32", "x86"))
        require((lastAttemptMillis == null) == (attemptId == null))
        if (attemptId != null) require(UUID.fromString(attemptId).toString() == attemptId)
        require(release == null || checkedAtMillis != null)
        release?.let {
            releasePageUrl(it)
            Instant.parse(it.publishedAt)
            require(it.notes.codePointCount(0, it.notes.length) <= 4000)
        }
        ignoredVersions.forEach { (version, until) -> require(publicVersionCompare(version, version) == 0 && until >= 0) }
    }

    fun suppresses(version: String, now: Long): Boolean = ignoredVersions[version]?.let { it == 0L || now < it } == true
}

internal class UpdateCheckWriteException(val outcomeUnverified: Boolean) : IOException("版本检查设置未能保存。")

internal class UpdateCheckStore private constructor(private val file: AtomicFile) {
    constructor(context: Context) : this(AtomicFile(File(context.noBackupFilesDir, "update_check.json")))
    internal constructor(file: File) : this(AtomicFile(file))
    private companion object {
        val fileLock = Any()
        const val MAX_BYTES = 256 * 1024
        const val DAY_MILLIS = 86_400_000L
    }

    fun read(): UpdateCheckPreferences = synchronized(fileLock) {
        try {
            if (!file.baseFile.exists() && !File(file.baseFile.path + ".bak").exists()) return@synchronized UpdateCheckPreferences()
            val bytes = file.openRead().use { input ->
                val buffer = ByteArray(MAX_BYTES + 1)
                var size = 0
                while (size < buffer.size) {
                    val count = input.read(buffer, size, buffer.size - size)
                    if (count < 0) break
                    size += count
                }
                require(size <= MAX_BYTES)
                buffer.copyOf(size)
            }
            decode(bytes.decodeToString(throwOnInvalidSequence = true))
        } catch (_: Exception) { throw IOException("版本检查设置不可读。") }
    }

    fun update(change: (UpdateCheckPreferences) -> UpdateCheckPreferences): UpdateCheckPreferences = synchronized(fileLock) {
        val current = read()
        val next = change(current)
        if (next != current) {
            try { write(next) }
            catch (error: UpdateCheckWriteException) {
                if (!error.outcomeUnverified || runCatching { read() }.getOrNull() != next) throw error
            }
        }
        next
    }

    fun claimAttempt(now: Long, manual: Boolean): UpdateCheckPreferences? = synchronized(fileLock) {
        require(now >= 0)
        val current = read()
        val previous = current.lastAttemptMillis
        if (!manual && (!current.enabled || previous != null &&
                (now < previous || now - previous < current.intervalDays * DAY_MILLIS))) return@synchronized null
        // 回拨不抹掉较晚的尝试事实；独立标识区分同毫秒或不同实例的请求。
        update { it.copy(lastAttemptMillis = maxOf(previous ?: now, now), attemptId = UUID.randomUUID().toString()) }
    }

    fun completeAttempt(attemptId: String, checkedAt: Long, release: PublicRelease?, architecture: String = BuildConfig.FLAVOR,
                        qualified: () -> Boolean): UpdateCheckPreferences? = synchronized(fileLock) {
        val current = read()
        if (current.attemptId != attemptId || !qualified()) return@synchronized null
        update { latest ->
            check(latest.attemptId == attemptId && qualified())
            latest.copy(checkedAtMillis = checkedAt, checkedArchitecture = architecture, release = release)
        }
    }

    private fun write(value: UpdateCheckPreferences) {
        val text = StringWriter()
        JsonWriter(text).use { writer ->
            writer.beginObject()
            writer.name("version").value(1L)
            writer.name("enabled").value(value.enabled)
            writer.name("interval_days").value(value.intervalDays.toLong())
            writer.name("last_attempt_ms").value(value.lastAttemptMillis)
            writer.name("attempt_id").value(value.attemptId)
            writer.name("checked_at_ms").value(value.checkedAtMillis)
            writer.name("checked_architecture").value(value.checkedArchitecture)
            writer.name("release")
            if (value.release == null) writer.nullValue() else {
                writer.beginObject()
                writer.name("version").value(value.release.version)
                writer.name("tag").value(value.release.tag)
                writer.name("published_at").value(value.release.publishedAt)
                writer.name("notes").value(value.release.notes)
                writer.endObject()
            }
            writer.name("ignored_versions").beginObject()
            value.ignoredVersions.forEach { (version, until) -> writer.name(version).value(until) }
            writer.endObject().endObject()
        }
        val bytes = text.toString().toByteArray(Charsets.UTF_8)
        if (bytes.size > MAX_BYTES) throw UpdateCheckWriteException(false)
        var output: FileOutputStream? = null
        var commitStarted = false
        try {
            output = file.startWrite()
            output.write(bytes)
            output.fd.sync()
            commitStarted = true
            file.finishWrite(output)
            output = null
            check(file.baseFile.isFile && read() == value)
        } catch (_: Exception) {
            if (commitStarted) {
                try { output?.close() } catch (_: Exception) { }
                throw UpdateCheckWriteException(true)
            }
            try { if (output != null) file.failWrite(output) }
            catch (_: Exception) { throw UpdateCheckWriteException(true) }
            throw UpdateCheckWriteException(false)
        }
    }

    private fun decode(text: String): UpdateCheckPreferences = JsonReader(StringReader(text)).use { reader ->
        reader.isLenient = false
        val names = mutableSetOf<String>()
        var enabled: Boolean? = null
        var days: Int? = null
        var lastAttempt: Long? = null
        var attempt: String? = null
        var checkedAt: Long? = null
        var checkedArchitecture: String? = null
        var release: PublicRelease? = null
        val ignored = linkedMapOf<String, Long>()
        reader.beginObject()
        while (reader.hasNext()) {
            val name = reader.nextName()
            require(names.add(name))
            when (name) {
                "version" -> require(reader.integer() == 1L)
                "enabled" -> { require(reader.peek() == JsonToken.BOOLEAN); enabled = reader.nextBoolean() }
                "interval_days" -> { val value = reader.integer(); require(value in 1..Int.MAX_VALUE.toLong()); days = value.toInt() }
                "last_attempt_ms" -> lastAttempt = reader.nullableLong()
                "attempt_id" -> attempt = reader.nullableString()
                "checked_at_ms" -> checkedAt = reader.nullableLong()
                "checked_architecture" -> checkedArchitecture = reader.nullableString()
                "release" -> {
                    if (reader.peek() == JsonToken.NULL) reader.nextNull() else {
                        val fields = mutableMapOf<String, String>()
                        reader.beginObject()
                        while (reader.hasNext()) {
                            val key = reader.nextName()
                            require(key in setOf("version", "tag", "published_at", "notes") && key !in fields)
                            require(reader.peek() == JsonToken.STRING)
                            fields[key] = reader.nextString()
                        }
                        reader.endObject()
                        require(fields.size == 4)
                        release = PublicRelease(fields.getValue("version"), fields.getValue("tag"), fields.getValue("published_at"), fields.getValue("notes"))
                    }
                }
                "ignored_versions" -> {
                    reader.beginObject()
                    while (reader.hasNext()) {
                        val key = reader.nextName()
                        require(key !in ignored)
                        ignored[key] = reader.integer()
                    }
                    reader.endObject()
                }
                else -> error("未知检查设置字段。")
            }
        }
        reader.endObject()
        require(reader.peek() == JsonToken.END_DOCUMENT)
        require(names == setOf("version", "enabled", "interval_days", "last_attempt_ms", "attempt_id", "checked_at_ms", "checked_architecture", "release", "ignored_versions"))
        UpdateCheckPreferences(requireNotNull(enabled), requireNotNull(days), lastAttempt, attempt, checkedAt, checkedArchitecture, release, ignored.toMap())
    }

    private fun JsonReader.integer(): Long {
        require(peek() == JsonToken.NUMBER)
        val literal = nextString()
        require(literal.matches(Regex("0|[1-9][0-9]*")))
        return requireNotNull(literal.toLongOrNull())
    }
    private fun JsonReader.nullableLong(): Long? = if (peek() == JsonToken.NULL) { nextNull(); null } else integer()
    private fun JsonReader.nullableString(): String? = if (peek() == JsonToken.NULL) { nextNull(); null } else {
        require(peek() == JsonToken.STRING)
        nextString()
    }
}
