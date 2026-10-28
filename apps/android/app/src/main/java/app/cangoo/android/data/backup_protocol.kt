package app.cangoo.android.data

import com.fasterxml.jackson.core.JsonProcessingException
import com.google.gson.Strictness
import com.google.gson.stream.JsonReader
import com.google.gson.stream.JsonToken
import com.google.gson.stream.JsonWriter
import com.google.gson.stream.MalformedJsonException
import java.io.ByteArrayOutputStream
import java.io.EOFException
import java.io.InputStream
import java.io.InputStreamReader
import java.io.IOException
import java.io.OutputStream
import java.io.OutputStreamWriter
import java.io.PushbackReader
import java.nio.ByteBuffer
import java.nio.CharBuffer
import java.nio.charset.CharacterCodingException
import java.nio.charset.CodingErrorAction
import java.security.MessageDigest
import java.time.Instant
import java.time.LocalDate
import java.time.LocalDateTime
import java.time.ZoneId
import java.time.ZoneOffset
import java.time.format.DateTimeFormatter
import java.util.Base64
import java.util.TimeZone
import kotlinx.coroutines.CancellationException
import org.bouncycastle.crypto.InvalidCipherTextException
import org.bouncycastle.crypto.engines.AESEngine
import org.bouncycastle.crypto.modes.GCMBlockCipher
import org.bouncycastle.crypto.params.AEADParameters
import org.bouncycastle.crypto.params.KeyParameter

internal enum class BackupScope { ALL, PASSWORDS, NOTES }

internal data class BackupPassword(
    val platform: String,
    val account: String,
    val password: String,
    val notes: String,
    val totpSecret: String,
    val strength: String?,
    val passwordChangedAt: String?,
    val updatedAt: String,
    val favorite: Boolean,
    val recoveryCodes: List<RecoveryCode> = emptyList(),
) { override fun toString() = "BackupPassword(内容已隐藏)" }

internal data class BackupNote(
    val title: String,
    val content: String,
    val createdAt: String,
    val updatedAt: String,
    val sortOrder: Int,
    val favorite: Boolean,
) { override fun toString() = "BackupNote(内容已隐藏)" }

internal data class BackupPayload(
    val exportTime: String,
    val scope: BackupScope,
    val passwords: List<BackupPassword>,
    val notes: List<BackupNote>,
    val version: Int = 2,
) { override fun toString() = "BackupPayload(内容已隐藏)" }

internal enum class BackupProblem(val text: String) {
    FORMAT("备份格式、字段或编码无效，请检查文件。"),
    LIMIT("备份大小、记录数量或字段长度超出限制。"),
    MEMORY("当前可用内存不足，请关闭其他任务或选择更小的资料范围后重试。"),
    PASSWORD("备份密码须非空且不超出1024个字符，请检查后重试。"),
    AUTHENTICATION("未能认证备份，请检查密码或文件。"),
    IO("未能读取或写入备份，请重试。"),
}

internal class BackupProtocolException(val problem: BackupProblem) : IllegalArgumentException(problem.text)

internal class BackupContentProof(val bytes: Long, internal val sha256: ByteArray) {
    init { require(bytes in 1..BackupProtocol.MAX_BYTES.toLong() && sha256.size == 32) }
    fun erase() { sha256.fill(0) }
    override fun toString() = "BackupContentProof(内容已隐藏)"
}

internal object BackupProtocol {
    const val MAX_BYTES = 64 * 1024 * 1024
    const val MAX_RECORDS = 100_000
    private const val PAYLOAD_TYPE = "password_manager_backup_payload"
    private val payloadFields = setOf("type", "version", "export_time", "scope", "passwords", "notes")
    private val passwordFields = setOf("platform", "account", "password", "notes", "totp_secret", "strength", "password_changed_at", "updated_at", "is_favorite")
    private val noteFields = setOf("title", "content", "created_at", "updated_at", "sort_order", "is_favorite")
    private val integerPattern = Regex("-?(0|[1-9][0-9]*)")
    private val base64Pattern = Regex("[A-Za-z0-9+/]*={0,2}")
    private val totpPattern = Regex("[A-Za-z2-7= \\-]*")
    private val datePattern = Regex("[0-9]{4}-[0-9]{2}-[0-9]{2}")
    private val timePattern = Regex("([0-9]{2})(?::([0-9]{2}))?(?::([0-9]{2}))?(?:([.:])([0-9]{3}|[0-9]{6}))?")
    private val offsetPattern = Regex("([0-9]{2}):([0-9]{2})(?::([0-9]{2})(?:[.:]([0-9]{6}))?)?")
    private val exportClock = DateTimeFormatter.ofPattern("uuuu-MM-dd'T'HH:mm:ss.SSS").withZone(ZoneOffset.UTC)

    fun exportTime(epochMillis: Long): String = checked {
        (exportClock.format(Instant.ofEpochMilli(epochMillis)) + "+00:00").also(::timestamp)
    }

    // 只替换安卓自有UTC的结尾Z；已导入且合法的日期原串保持。
    fun exportTimestamp(value: String): String = checked {
        (if (value.endsWith('Z')) value.dropLast(1) + "+00:00" else value).also(::timestamp)
    }

    // 只生成排序值，不改持久日期；非法历史值与Windows一致回退到纪元零。
    fun timestampOrder(value: String): Long {
        if (value.length > 64) return 0L
        return try {
            val parts = dateTimeParts(if (value.endsWith('Z')) value.dropLast(1) + "+00:00" else value)
            val microsecond = parts.local.nano.toLong() / 1000
            val wallMicros = parts.local.toEpochSecond(ZoneOffset.UTC) * 1_000_000 + microsecond
            val offset = parts.offsetMicros
            if (offset != null) {
                // CPython3.10在整数偏移秒为零时忽略偏移微秒；沿Windows实际排序结果保留兼容。
                wallMicros - (if (offset / 1_000_000 == 0L) 0L else offset)
            } else {
                try { parts.local.atZone(ZoneId.systemDefault()).toEpochSecond() * 1_000_000 + microsecond }
                catch (_: Exception) { wallMicros - TimeZone.getDefault().rawOffset.toLong() * 1000 }
            }
        } catch (_: Exception) { 0L }
    }

    fun displayDate(value: String): LocalDate {
        val normalized = if (value.endsWith('Z')) value.dropLast(1) + "+00:00" else value
        dateTimeParts(normalized)
        val micros = timestampOrder(normalized)
        return Instant.ofEpochSecond(micros / 1_000_000, micros % 1_000_000 * 1000)
            .atZone(ZoneId.systemDefault()).toLocalDate()
    }

    // 调用者持有并关闭流；输出仍开放，以便父层同步、读回和最终发布。
    fun encrypt(payload: BackupPayload, password: String, output: OutputStream,
                memory: BackupMemoryBudget = BackupMemoryBudget(), guard: () -> Unit = {}) = checked {
        guard()
        validatePassword(password)
        validate(payload, exporting = true)
        val exported = payload.copy(version = 2)
        var plaintextBytes = 0L
        val expected = MessageDigest.getInstance("SHA-256")
        try {
            writePayload(exported, object : OutputStream() {
                override fun write(value: Int) { count(1); expected.update(value.toByte()) }
                override fun write(bytes: ByteArray, offset: Int, length: Int) { count(length); expected.update(bytes, offset, length) }
                private fun count(length: Int) {
                    guard()
                    plaintextBytes += length
                    if (plaintextBytes > MAX_BYTES) fail(BackupProblem.LIMIT)
                }
            })
            guard()
            val salt = VaultCrypto.randomBytes(VaultCrypto.SALT_BYTES)
            val nonce = VaultCrypto.randomBytes(VaultCrypto.NONCE_BYTES)
            var key: ByteArray? = null
            var proof: BackupContentProof? = null
            var completed = false
            try {
                val header = ByteArrayOutputStream().also { writeEnvelope(Base64.getEncoder().encodeToString(salt), "", it) }.toByteArray()
                val encodedSize = ((plaintextBytes + 28 + 2) / 3) * 4
                if (header.size + encodedSize > MAX_BYTES) fail(BackupProblem.LIMIT)
                val expectedContent = BackupContentProof(plaintextBytes, expected.digest())
                proof = expectedContent
                val derived = memory.temporary(BackupMemoryBudget.KDF_BYTES) { VaultCrypto.deriveKey(password, salt) }
                key = derived
                guard()
                output.write(header, 0, header.size - 2)
                val encoded = Base64.getEncoder().wrap(object : OutputStream() {
                    override fun write(value: Int) { guard(); output.write(value) }
                    override fun write(bytes: ByteArray, offset: Int, length: Int) { guard(); output.write(bytes, offset, length) }
                    override fun flush() { guard(); output.flush() }
                    override fun close() { flush() }
                })
                val cipher = GcmOutput(encoded, derived, nonce, guard)
                try {
                    encoded.write(nonce)
                    writePayload(exported, cipher)
                    // 标签成功生成后才完成Base64填充与JSON结尾；失败不自动补成完整包。
                    cipher.finish()
                    encoded.close()
                    output.write(byteArrayOf('"'.code.toByte(), '}'.code.toByte()))
                    output.flush()
                    guard()
                    completed = true
                    expectedContent
                } finally { cipher.erase() }
            } finally {
                if (!completed) proof?.erase()
                key?.fill(0)
                nonce.fill(0)
                salt.fill(0)
            }
        } finally { expected.reset() }
    }

    fun decrypt(input: InputStream, password: String, memory: BackupMemoryBudget = BackupMemoryBudget(),
                guard: () -> Unit = {}): BackupPayload = checked {
        openDecryption(input, password, guard, memory).use { decryption ->
            // 首遍只认证同一封存密文；在标签通过前不构造记录。
            val discard = ByteArray(8192)
            try {
                decryption.input().use { verified ->
                    while (verified.read(discard) >= 0) discard.fill(0)
                    verified.finish()
                }
            } finally { discard.fill(0) }
            decryption.input().use { plaintext ->
                val result = readPayload(plaintext, decryption.plaintextBytes, memory)
                plaintext.finish()
                guard()
                result
            }
        }
    }

    // 自有导出包只核本次预检的完整字节证明；不向导入或界面交付明文记录。
    fun verify(input: InputStream, password: String, expected: BackupContentProof,
               memory: BackupMemoryBudget = BackupMemoryBudget(), guard: () -> Unit = {}) = checked {
        val digest = MessageDigest.getInstance("SHA-256")
        val buffer = ByteArray(8192)
        var actual: ByteArray? = null
        try {
            var bytes = 0L
            openDecryption(input, password, guard, memory).use { decryption ->
                decryption.input().use { plaintext ->
                    while (true) {
                        guard()
                        val count = plaintext.read(buffer)
                        if (count < 0) break
                        digest.update(buffer, 0, count)
                        bytes += count
                        buffer.fill(0)
                    }
                    plaintext.finish()
                }
            }
            guard()
            val checksum = digest.digest()
            actual = checksum
            if (bytes != expected.bytes || !MessageDigest.isEqual(checksum, expected.sha256)) {
                throw BackupStoreException(BackupStoreProblem.VERIFICATION)
            }
            guard()
        } finally { buffer.fill(0); actual?.fill(0); digest.reset() }
    }

    private fun openDecryption(input: InputStream, password: String, guard: () -> Unit, memory: BackupMemoryBudget): Decryption {
        guard()
        validatePassword(password)
        val envelope = BackupEnvelope.read(input, guard, memory)
        val nonce = ByteArray(VaultCrypto.NONCE_BYTES)
        var key: ByteArray? = null
        var completed = false
        try {
            repeat(nonce.size) { nonce[it] = envelope.encrypted.byteAt(it).toByte() }
            guard()
            val derived = memory.temporary(BackupMemoryBudget.KDF_BYTES) { VaultCrypto.deriveKey(password, envelope.salt) }
            key = derived
            guard()
            return Decryption(envelope, derived, nonce, guard).also { completed = true }
        } finally {
            if (!completed) { key?.fill(0); nonce.fill(0); envelope.salt.fill(0); envelope.encrypted.erase() }
        }
    }

    private class Decryption(private val envelope: BackupEnvelope, private val key: ByteArray,
                             private val nonce: ByteArray, private val guard: () -> Unit) : AutoCloseable {
        val plaintextBytes get() = envelope.encrypted.size - VaultCrypto.NONCE_BYTES - 16
        fun input() = GcmInput(envelope.encrypted.input(nonce.size, guard), key, nonce, guard)
        override fun close() { key.fill(0); nonce.fill(0); envelope.salt.fill(0); envelope.encrypted.erase() }
    }

    // 纯结构入口供公开检查复用；产品导入须先通过decrypt认证。
    fun readPayload(input: InputStream, memory: BackupMemoryBudget = BackupMemoryBudget()): BackupPayload = checked {
        val packet = BackupPacketBytes(memory)
        val buffer = ByteArray(8192)
        try {
            while (true) {
                val count = input.read(buffer)
                if (count < 0) break
                if (count > 0) packet.write(buffer, 0, count)
            }
            packet.seal()
            readPayload(packet.input(guard = {}), packet.size, memory)
        } finally { buffer.fill(0); packet.erase() }
    }

    internal fun readPayload(input: InputStream, byteCount: Int, memory: BackupMemoryBudget = BackupMemoryBudget()): BackupPayload = checked {
        if (byteCount !in 1..MAX_BYTES) fail(if (byteCount == 0) BackupProblem.FORMAT else BackupProblem.LIMIT)
        memory.reserve(BackupMemoryBudget.textPeak(byteCount.toLong()))
        val reader = reader(input, byteCount)
        var version: Int? = null
        var exportTime: String? = null
        var scope: BackupScope? = null
        var passwords: List<ParsedPassword>? = null
        var notes: List<BackupNote>? = null
        var remaining = MAX_RECORDS
        val fields = reader.fields { field ->
            when (field) {
                "type" -> if (reader.string() != PAYLOAD_TYPE) fail()
                "version" -> version = reader.integer().also { if (it !in 1..2) fail() }
                "export_time" -> exportTime = reader.string()
                "scope" -> {
                    val value = reader.string()
                    scope = BackupScope.entries.firstOrNull { it.name == value } ?: fail()
                }
                "passwords" -> passwords = reader.items(remaining) { memory.reserve(BackupMemoryBudget.RECORD_BYTES); readPassword(reader, memory) }.also { remaining -= it.size }
                "notes" -> notes = reader.items(remaining) { memory.reserve(BackupMemoryBudget.RECORD_BYTES); readNote(reader) }.also { remaining -= it.size }
                else -> fail()
            }
        }
        if (fields != payloadFields || reader.peek() != JsonToken.END_DOCUMENT) fail()
        val actualVersion = version ?: fail()
        val records = passwords ?: fail()
        if (records.any { it.codesPresent != (actualVersion == 2) }) fail()
        BackupPayload(exportTime ?: fail(), scope ?: fail(), records.map { it.value }, notes ?: fail(), actualVersion)
            .also { validate(it, exporting = false) }
    }

    private data class ParsedPassword(val value: BackupPassword, val codesPresent: Boolean) {
        override fun toString() = "ParsedPassword(内容已隐藏)"
    }

    private fun readPassword(reader: JsonReader, memory: BackupMemoryBudget): ParsedPassword {
        var platform: String? = null
        var account: String? = null
        var password: String? = null
        var notes: String? = null
        var totp: String? = null
        var strength: String? = null
        var changed: String? = null
        var updated: String? = null
        var favorite: Boolean? = null
        var codes: List<RecoveryCode>? = null
        val fields = reader.fields { field ->
            when (field) {
                "platform" -> platform = reader.string()
                "account" -> account = reader.string()
                "password" -> password = reader.string()
                "notes" -> notes = reader.string()
                "totp_secret" -> totp = reader.string()
                "strength" -> strength = reader.nullableString()
                "password_changed_at" -> changed = reader.nullableString()
                "updated_at" -> updated = reader.string()
                "is_favorite" -> favorite = reader.boolean()
                "recovery_codes" -> codes = reader.items(128) { memory.reserve(BackupMemoryBudget.RECOVERY_CODE_BYTES); readRecoveryCode(reader) }
                else -> fail()
            }
        }
        if (fields - "recovery_codes" != passwordFields) fail()
        return ParsedPassword(BackupPassword(platform ?: fail(), account ?: fail(), password ?: fail(), notes ?: fail(),
            totp ?: fail(), strength, changed, updated ?: fail(), favorite ?: fail(), codes.orEmpty()), codes != null)
    }

    private fun readRecoveryCode(reader: JsonReader): RecoveryCode {
        var value: String? = null
        var used: Boolean? = null
        val fields = reader.fields { field ->
            when (field) {
                "value" -> value = reader.string()
                "used" -> used = reader.boolean()
                else -> fail()
            }
        }
        if (fields != setOf("value", "used")) fail()
        return RecoveryCode(value ?: fail(), used ?: fail())
    }

    private fun readNote(reader: JsonReader): BackupNote {
        var title: String? = null
        var content: String? = null
        var created: String? = null
        var updated: String? = null
        var order: Int? = null
        var favorite: Boolean? = null
        val fields = reader.fields { field ->
            when (field) {
                "title" -> title = reader.string()
                "content" -> content = reader.string()
                "created_at" -> created = reader.string()
                "updated_at" -> updated = reader.string()
                "sort_order" -> order = reader.integer()
                "is_favorite" -> favorite = reader.boolean()
                else -> fail()
            }
        }
        if (fields != noteFields) fail()
        return BackupNote(title ?: fail(), content ?: fail(), created ?: fail(), updated ?: fail(), order ?: fail(), favorite ?: fail())
    }

    private fun validate(payload: BackupPayload, exporting: Boolean) {
        if (payload.version !in 1..2) fail()
        if (payload.passwords.size.toLong() + payload.notes.size > MAX_RECORDS) fail(BackupProblem.LIMIT)
        if (payload.scope == BackupScope.PASSWORDS && payload.notes.isNotEmpty() ||
            payload.scope == BackupScope.NOTES && payload.passwords.isNotEmpty()) fail()
        fun date(value: String) { if (exporting) exportTimestamp(value) else timestamp(value) }
        date(payload.exportTime)
        val names = mutableSetOf<String>()
        payload.passwords.forEach { item ->
            text(item.platform, required = true)
            if (!names.add(item.platform)) fail()
            listOf(item.account, item.password, item.notes).forEach { text(it) }
            text(item.totpSecret, maxCharacters = 256, maxBytes = 512)
            if (!totpPattern.matches(item.totpSecret)) fail()
            if (item.strength != null && item.strength !in setOf("weak", "fair", "strong")) fail()
            item.passwordChangedAt?.let(::date)
            date(item.updatedAt)
            if (payload.version == 1 && item.recoveryCodes.isNotEmpty()) fail()
            try { validateRecoveryCodes(item.recoveryCodes) }
            catch (error: RecoveryCodeException) {
                fail(if (error.problem == RecoveryCodeProblem.LIMIT) BackupProblem.LIMIT else BackupProblem.FORMAT)
            }
        }
        payload.notes.forEach { item ->
            text(item.title, required = true)
            text(item.content)
            date(item.createdAt)
            date(item.updatedAt)
        }
    }

    internal fun encodePayload(payload: BackupPayload, guard: () -> Unit, memory: BackupMemoryBudget = BackupMemoryBudget()): ByteArray = checked {
        guard()
        validate(payload, exporting = true)
        val output = BackupPacketBytes(memory)
        try {
            writePayload(payload, object : OutputStream() {
                override fun write(value: Int) { guard(); output.write(value) }
                override fun write(bytes: ByteArray, offset: Int, length: Int) { guard(); output.write(bytes, offset, length) }
            })
            guard()
            output.seal()
            memory.reserve(output.size.toLong())
            val result = ByteArray(output.size)
            try {
                output.input(guard = guard).use { input ->
                    var position = 0
                    while (position < result.size) { val count = input.read(result, position, result.size - position); check(count > 0); position += count }
                }
                guard(); result
            } catch (failure: Exception) { result.fill(0); throw failure }
        } finally { output.erase() }
    }

    private fun writePayload(payload: BackupPayload, output: OutputStream) {
        val writer = writer(output)
        writer.beginObject().name("type").value(PAYLOAD_TYPE).name("version").value(payload.version)
            .name("export_time").value(exportTimestamp(payload.exportTime)).name("scope").value(payload.scope.name)
            .name("passwords").beginArray()
        payload.passwords.forEach { item ->
            writer.beginObject().name("platform").value(item.platform).name("account").value(item.account)
                .name("password").value(item.password).name("notes").value(item.notes).name("totp_secret").value(item.totpSecret)
                .name("strength").value(item.strength).name("password_changed_at").value(item.passwordChangedAt?.let(::exportTimestamp))
                .name("updated_at").value(exportTimestamp(item.updatedAt)).name("is_favorite").value(item.favorite)
            if (payload.version == 2) {
                writer.name("recovery_codes").beginArray()
                item.recoveryCodes.forEach { code ->
                    writer.beginObject().name("value").value(code.value).name("used").value(code.used).endObject()
                }
                writer.endArray()
            }
            writer.endObject()
        }
        writer.endArray().name("notes").beginArray()
        payload.notes.forEach { item ->
            writer.beginObject().name("title").value(item.title).name("content").value(item.content)
                .name("created_at").value(exportTimestamp(item.createdAt)).name("updated_at").value(exportTimestamp(item.updatedAt))
                .name("sort_order").value(item.sortOrder).name("is_favorite").value(item.favorite).endObject()
        }
        writer.endArray().endObject()
        writer.flush()
    }

    private fun writeEnvelope(salt: String, payload: String, output: OutputStream) {
        val writer = writer(output)
        writer.beginObject().name("type").value(BackupEnvelope.TYPE).name("version").value(2).name("kdf").beginObject()
            .name("name").value("argon2id").name("salt").value(salt).name("memory_cost").value(VaultCrypto.MEMORY_KIB)
            .name("time_cost").value(VaultCrypto.ITERATIONS).name("parallelism").value(VaultCrypto.PARALLELISM)
            .name("hash_len").value(VaultCrypto.KEY_BYTES).endObject().name("payload").value(payload).endObject()
        writer.flush()
    }

    private fun reader(input: InputStream, byteCount: Int): JsonReader {
        val decoded = PushbackReader(InputStreamReader(LimitedInput(input, byteCount),
            Charsets.UTF_8.newDecoder().onMalformedInput(CodingErrorAction.REPORT).onUnmappableCharacter(CodingErrorAction.REPORT)), 1)
        val first = decoded.read()
        // Gson即使在严格模式也跳过开头BOM；Windows的UTF-8字符串JSON入口拒绝它。
        if (first == 0xfeff) fail()
        if (first >= 0) decoded.unread(first)
        return JsonReader(decoded).apply { setStrictness(Strictness.STRICT); setNestingLimit(8) }
    }

    private fun writer(output: OutputStream): JsonWriter = JsonWriter(OutputStreamWriter(output, Charsets.UTF_8))
        .apply { setStrictness(Strictness.STRICT); setHtmlSafe(false); setSerializeNulls(true) }

    private inline fun JsonReader.fields(readField: (String) -> Unit): Set<String> {
        if (peek() != JsonToken.BEGIN_OBJECT) fail()
        beginObject()
        val fields = mutableSetOf<String>()
        while (hasNext()) {
            val field = nextName()
            if (!fields.add(field)) fail()
            readField(field)
        }
        endObject()
        return fields
    }

    private inline fun <T> JsonReader.items(limit: Int, readItem: () -> T): List<T> {
        if (peek() != JsonToken.BEGIN_ARRAY) fail()
        beginArray()
        val values = mutableListOf<T>()
        while (hasNext()) {
            if (values.size >= limit) fail(BackupProblem.LIMIT)
            values.add(readItem())
        }
        endArray()
        return values
    }

    private fun JsonReader.string(): String {
        if (peek() != JsonToken.STRING) fail()
        return nextString()
    }

    private fun JsonReader.nullableString(): String? = if (peek() == JsonToken.NULL) { nextNull(); null } else string()

    private fun JsonReader.boolean(): Boolean {
        if (peek() != JsonToken.BOOLEAN) fail()
        return nextBoolean()
    }

    private fun JsonReader.integer(): Int {
        if (peek() != JsonToken.NUMBER) fail()
        val raw = nextString()
        if (!integerPattern.matches(raw)) fail()
        return raw.toIntOrNull() ?: fail()
    }

    private fun validatePassword(value: String) {
        try {
            if (value.isEmpty()) fail(BackupProblem.PASSWORD)
            validatedUtf8(value, 1024, 4096).fill(0)
        } catch (_: VaultException) { fail(BackupProblem.PASSWORD) }
    }

    private fun text(value: String, required: Boolean = false, maxCharacters: Int = MAX_BYTES, maxBytes: Int = MAX_BYTES) {
        if ('\u0000' in value || required && (value.isEmpty() || value.all { it.isWhitespace() || it == '\u0085' })) fail()
        if (value.codePointCount(0, value.length) > maxCharacters) fail(BackupProblem.LIMIT)
        if (value.all { it.code < 128 }) {
            if (value.length > maxBytes) fail(BackupProblem.LIMIT)
            return
        }
        val bytes = ByteBuffer.allocate(minOf(8192, maxOf(4, value.length * 3)))
        val encoder = Charsets.UTF_8.newEncoder().onMalformedInput(CodingErrorAction.REPORT).onUnmappableCharacter(CodingErrorAction.REPORT)
        val chars = CharBuffer.wrap(value)
        var total = 0L
        try {
            while (true) {
                val result = encoder.encode(chars, bytes, true)
                total += bytes.position()
                if (total > maxBytes) fail(BackupProblem.LIMIT)
                if (result.isError) result.throwException()
                if (result.isUnderflow) break
                bytes.clear()
            }
        } finally { bytes.array().fill(0) }
    }

    private data class DateTimeParts(val local: LocalDateTime, val offsetMicros: Long?) {
        override fun toString() = "DateTimeParts(日期已隐藏)"
    }

    private fun timestamp(value: String) { dateTimeParts(value) }

    private fun dateTimeParts(value: String): DateTimeParts {
        text(value, required = true, maxCharacters = 64, maxBytes = 64)
        if (value.length < 10 || !datePattern.matches(value.substring(0, 10))) fail()
        val year = value.substring(0, 4).toInt()
        if (year == 0) fail()
        val date = LocalDate.of(year, value.substring(5, 7).toInt(), value.substring(8, 10).toInt())
        if (value.length == 10) return DateTimeParts(date.atStartOfDay(), null)
        val start = 10 + Character.charCount(value.codePointAt(10))
        val time = value.substring(start)
        val offsetIndex = time.indexOfAny(charArrayOf('+', '-'))
        val plainTime = if (offsetIndex < 0) time else time.substring(0, offsetIndex)
        val parsed = timePattern.matchEntire(plainTime) ?: fail()
        // CPython3.10的C实现也接受秒后冒号分隔的小数，较早组件仍须按分秒解析。
        if (parsed.groupValues[4] == ":" && parsed.groupValues[3].isEmpty()) fail()
        val hour = parsed.groupValues[1].toInt()
        val minute = parsed.groupValues[2].ifEmpty { "0" }.toInt()
        val second = parsed.groupValues[3].ifEmpty { "0" }.toInt()
        val microsecond = parsed.groupValues[5].padEnd(6, '0').toInt()
        if (hour > 23 || minute > 59 || second > 59) fail()
        var offsetMicros: Long? = null
        if (offsetIndex >= 0) {
            val offset = offsetPattern.matchEntire(time.substring(offsetIndex + 1)) ?: fail()
            val micros = (((offset.groupValues[1].toLong() * 60 + offset.groupValues[2].toLong()) * 60 +
                offset.groupValues[3].ifEmpty { "0" }.toLong()) * 1_000_000 + offset.groupValues[4].ifEmpty { "0" }.toLong())
            // Python3.10接受时区分秒进位；只要求最终绝对偏移小于24小时。
            if (micros >= 86_400_000_000L) fail()
            offsetMicros = if (time[offsetIndex] == '-') -micros else micros
        }
        return DateTimeParts(date.atTime(hour, minute, second, microsecond * 1000), offsetMicros)
    }

    internal fun decodeBase64(value: String): ByteArray {
        if (!base64Pattern.matches(value)) fail()
        val end = value.indexOf('=').let { if (it < 0) value.length else it }
        val padding = value.length - end
        val remainder = end % 4
        if (remainder == 1 || remainder == 2 && padding != 2 || remainder == 3 && padding < 1) fail()
        // Windows的Python3.10允许额外的尾部填充和非零填充位；先按它的规则检查，再交标准解码器。
        val source = object : InputStream() {
            var index = 0
            override fun read(): Int = if (index < end) value[index++].code else -1
        }
        val decoded = ByteArray(end / 4 * 3 + if (remainder == 0) 0 else remainder - 1)
        Base64.getDecoder().wrap(source).use { stream ->
            var offset = 0
            while (offset < decoded.size) {
                val count = stream.read(decoded, offset, decoded.size - offset)
                if (count <= 0) fail()
                offset += count
            }
            if (stream.read() != -1) fail()
        }
        return decoded
    }

    private class LimitedInput(private val source: InputStream, private val maximum: Int) : InputStream() {
        private var count = 0
        override fun read(): Int = source.read().also { if (it >= 0 && ++count > maximum) fail(BackupProblem.LIMIT) }
        override fun read(bytes: ByteArray, offset: Int, length: Int): Int {
            if (length == 0) return 0
            return source.read(bytes, offset, minOf(length, maximum - count + 1)).also {
                if (it > 0) { count += it; if (count > maximum) fail(BackupProblem.LIMIT) }
            }
        }
    }

    private fun gcm(encrypting: Boolean, key: ByteArray, nonce: ByteArray) =
        GCMBlockCipher.newInstance(AESEngine.newInstance()).apply { init(encrypting, AEADParameters(KeyParameter(key), 128, nonce)) }

    private class GcmOutput(private val output: OutputStream, key: ByteArray, nonce: ByteArray,
                            private val guard: () -> Unit) : OutputStream() {
        private val cipher = gcm(true, key, nonce)
        private val buffer = ByteArray(8192 + 32)
        override fun write(value: Int) { write(byteArrayOf(value.toByte())) }
        override fun write(bytes: ByteArray, offset: Int, length: Int) {
            var processed = 0
            while (processed < length) {
                guard()
                val count = minOf(8192, length - processed)
                val produced = cipher.processBytes(bytes, offset + processed, count, buffer, 0)
                output.write(buffer, 0, produced)
                buffer.fill(0)
                processed += count
            }
        }
        override fun flush() { guard(); output.flush() }
        fun finish() { guard(); val count = cipher.doFinal(buffer, 0); output.write(buffer, 0, count); guard() }
        fun erase() { buffer.fill(0); cipher.reset() }
    }

    private class GcmInput(private val input: InputStream, key: ByteArray, nonce: ByteArray,
                           private val guard: () -> Unit) : InputStream() {
        private val cipher = gcm(false, key, nonce)
        private val encrypted = ByteArray(8192)
        private val plaintext = ByteArray(8192 + 32)
        private var position = 0
        private var available = 0
        private var authenticated = false
        private var bytes = 0L
        private fun fill(): Boolean {
            while (position >= available) {
                guard()
                plaintext.fill(0)
                position = 0
                if (authenticated) return false
                val count = input.read(encrypted)
                available = if (count < 0) {
                    val finalCount = try { cipher.doFinal(plaintext, 0) }
                    catch (_: InvalidCipherTextException) { fail(BackupProblem.AUTHENTICATION) }
                    authenticated = true
                    finalCount
                } else {
                    val produced = cipher.processBytes(encrypted, 0, count, plaintext, 0)
                    encrypted.fill(0)
                    produced
                }
                bytes += available
                if (bytes > MAX_BYTES) fail(BackupProblem.LIMIT)
            }
            return true
        }
        override fun read(): Int = if (fill()) (plaintext[position++].toInt() and 255) else -1
        override fun read(buffer: ByteArray, offset: Int, length: Int): Int {
            if (length == 0) return 0
            if (!fill()) return -1
            val count = minOf(length, available - position)
            plaintext.copyInto(buffer, offset, position, position + count)
            plaintext.fill(0, position, position + count)
            position += count
            return count
        }
        fun finish() {
            while (fill()) { plaintext.fill(0); position = available }
            if (!authenticated) fail(BackupProblem.AUTHENTICATION)
            guard()
        }
        override fun close() { encrypted.fill(0); plaintext.fill(0); cipher.reset(); input.close() }
    }

    private inline fun <T> checked(action: () -> T): T = try { action() }
    catch (error: BackupProtocolException) { throw error }
    catch (error: CancellationException) { throw error }
    catch (error: VaultException) { throw error }
    catch (error: BackupStoreException) { throw error }
    catch (_: JsonProcessingException) { fail() }
    catch (_: MalformedJsonException) { fail() }
    catch (_: EOFException) { fail() }
    catch (_: CharacterCodingException) { fail() }
    catch (_: IOException) { fail(BackupProblem.IO) }
    catch (_: Exception) { fail() }

    private fun fail(problem: BackupProblem = BackupProblem.FORMAT): Nothing = throw BackupProtocolException(problem)
}
