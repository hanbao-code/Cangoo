package app.cangoo.android.data

import com.fasterxml.jackson.core.JsonFactory
import com.fasterxml.jackson.core.JsonParser
import com.fasterxml.jackson.core.JsonToken
import com.fasterxml.jackson.core.StreamReadConstraints
import com.fasterxml.jackson.core.StreamReadFeature
import com.fasterxml.jackson.core.json.UTF8StreamJsonParser
import com.google.gson.Strictness
import java.io.InputStream
import java.io.InputStreamReader
import java.io.OutputStream
import java.io.StringReader
import java.nio.charset.CodingErrorAction
import java.util.Base64

// 仅保存本次加密字节；读入结束后封存，认证两遍始终读取同一份内容。
internal class BackupPacketBytes(private val memory: BackupMemoryBudget = BackupMemoryBudget()) : OutputStream() {
    private val blocks = mutableListOf<ByteArray>()
    private var sealed = false
    var size = 0
        private set

    override fun write(value: Int) {
        bound(1)
        if (size % BLOCK == 0) addBlock()
        blocks.last()[size++ % BLOCK] = value.toByte()
    }

    override fun write(bytes: ByteArray, offset: Int, length: Int) {
        bound(length)
        var copied = 0
        while (copied < length) {
            if (size % BLOCK == 0) addBlock()
            val count = minOf(length - copied, BLOCK - size % BLOCK)
            bytes.copyInto(blocks.last(), size % BLOCK, offset + copied, offset + copied + count)
            copied += count
            size += count
        }
    }

    private fun bound(length: Int) {
        check(!sealed)
        require(length >= 0)
        if (size.toLong() + length > BackupProtocol.MAX_BYTES) packetFailure(BackupProblem.LIMIT)
    }

    private fun addBlock() {
        memory.reserve(BLOCK.toLong())
        blocks.add(ByteArray(BLOCK))
    }

    fun seal() { sealed = true }
    fun byteAt(index: Int): Int {
        if (index !in 0 until size) packetFailure()
        return blocks[index / BLOCK][index % BLOCK].toInt() and 255
    }

    fun input(start: Int = 0, guard: () -> Unit): InputStream {
        check(sealed)
        if (start !in 0..size) packetFailure()
        return object : InputStream() {
            private var position = start
            override fun read(): Int {
                guard()
                return (if (position < size) byteAt(position++) else -1).also { guard() }
            }
            override fun read(bytes: ByteArray, offset: Int, length: Int): Int {
                guard()
                if (length == 0) return 0
                if (position >= size) return -1
                val count = minOf(length, size - position, BLOCK - position % BLOCK)
                blocks[position / BLOCK].copyInto(bytes, offset, position % BLOCK, position % BLOCK + count)
                position += count
                guard()
                return count
            }
        }
    }

    fun erase() { blocks.forEach { it.fill(0) }; memory.release(blocks.size.toLong() * BLOCK); blocks.clear(); size = 0; sealed = true }
    private companion object { const val BLOCK = 8192 }
}

internal class BackupEnvelope(val salt: ByteArray, val encrypted: BackupPacketBytes) {
    companion object {
        const val TYPE = "password_manager_encrypted_backup"
        private val fields = setOf("type", "version", "kdf", "payload")
        private val kdfFields = setOf("name", "salt", "memory_cost", "time_cost", "parallelism", "hash_len")
        private val integers = Regex("-?(0|[1-9][0-9]*)")
        private val parserFactory = JsonFactory.builder()
            .disable(JsonFactory.Feature.CHARSET_DETECTION)
            .disable(StreamReadFeature.AUTO_CLOSE_SOURCE)
            .enable(StreamReadFeature.STRICT_DUPLICATE_DETECTION)
            .streamReadConstraints(StreamReadConstraints.builder().maxNameLength(11).maxStringLength(34)
                .maxNumberLength(11).maxNestingDepth(2).build()).build()

        fun read(input: InputStream, guard: () -> Unit, memory: BackupMemoryBudget = BackupMemoryBudget()): BackupEnvelope {
            val original = BackupPacketBytes(memory)
            val encrypted = BackupPacketBytes(memory)
            val buffer = ByteArray(8192)
            var salt: ByteArray? = null
            var completed = false
            try {
                while (true) {
                    guard()
                    val count = input.read(buffer, 0, minOf(buffer.size, BackupProtocol.MAX_BYTES - original.size + 1))
                    if (count < 0) break
                    if (count > 0) original.write(buffer, 0, count)
                }
                original.seal()
                validateUtf8(original, guard)
                var start = -1L
                var end = -1L
                parserFactory.createParser(original.input(guard = guard)).use { parser ->
                    if (parser !is UTF8StreamJsonParser || parser.nextToken() != JsonToken.START_OBJECT) packetFailure()
                    val found = mutableSetOf<String>()
                    var token = parser.nextToken()
                    while (token != JsonToken.END_OBJECT) {
                        guard()
                        if (token != JsonToken.FIELD_NAME) packetFailure()
                        val field = parser.currentName()
                        if (!found.add(field)) packetFailure()
                        parser.nextToken()
                        when (field) {
                            "type" -> if (parser.string() != TYPE) packetFailure()
                            "version" -> if (parser.integer() != 2) packetFailure()
                            "kdf" -> salt = readKdf(parser, guard)
                            "payload" -> {
                                if (parser.currentToken() != JsonToken.VALUE_STRING) packetFailure()
                                start = parser.currentTokenLocation().byteOffset
                                if (start < 0 || start >= original.size || original.byteAt(start.toInt()) != '"'.code) packetFailure()
                            }
                            else -> packetFailure()
                        }
                        token = parser.nextToken()
                        if (field == "payload") end = parser.currentTokenLocation().byteOffset
                    }
                    if (found != fields || parser.nextToken() != null) packetFailure()
                }
                guard()
                if (start < 0 || end <= start || end > original.size) packetFailure()
                val characters = JsonBase64(original.input(start.toInt(), guard), guard)
                Base64.getDecoder().wrap(characters).use { decoded ->
                    while (true) {
                        guard()
                        val count = decoded.read(buffer)
                        if (count < 0) break
                        if (count > 0) encrypted.write(buffer, 0, count)
                    }
                }
                val closing = start + characters.rawBytes - 1
                if (!characters.done || !characters.quotedEnd || characters.rawBytes < 2 || closing >= end ||
                    closing >= original.size || original.byteAt(closing.toInt()) != '"'.code || encrypted.size < 28) packetFailure()
                encrypted.seal()
                guard()
                completed = true
                return BackupEnvelope(salt ?: packetFailure(), encrypted)
            } finally {
                buffer.fill(0)
                original.erase()
                if (!completed) { salt?.fill(0); encrypted.erase() }
            }
        }

        private fun validateUtf8(original: BackupPacketBytes, guard: () -> Unit) {
            val characters = CharArray(8192)
            try {
                InputStreamReader(original.input(guard = guard), Charsets.UTF_8.newDecoder()
                    .onMalformedInput(CodingErrorAction.REPORT).onUnmappableCharacter(CodingErrorAction.REPORT)).use { reader ->
                    guard()
                    if (reader.read() == 0xfeff) packetFailure()
                    while (true) { guard(); if (reader.read(characters) < 0) break }
                }
            } finally { characters.fill('\u0000') }
        }

        private fun JsonParser.string(): String {
            if (currentToken() != JsonToken.VALUE_STRING) packetFailure()
            return text
        }

        private fun JsonParser.integer(): Int {
            if (currentToken() != JsonToken.VALUE_NUMBER_INT) packetFailure()
            val raw = text
            if (!integers.matches(raw)) packetFailure()
            return raw.toIntOrNull() ?: packetFailure()
        }

        private fun readKdf(parser: JsonParser, guard: () -> Unit): ByteArray {
            if (parser.currentToken() != JsonToken.START_OBJECT) packetFailure()
            val found = mutableSetOf<String>()
            var salt: String? = null
            while (parser.nextToken() != JsonToken.END_OBJECT) {
                guard()
                if (parser.currentToken() != JsonToken.FIELD_NAME) packetFailure()
                val field = parser.currentName()
                if (!found.add(field)) packetFailure()
                parser.nextToken()
                when (field) {
                    "name" -> if (parser.string() != "argon2id") packetFailure()
                    "salt" -> salt = parser.string()
                    "memory_cost" -> if (parser.integer() != VaultCrypto.MEMORY_KIB) packetFailure()
                    "time_cost" -> if (parser.integer() != VaultCrypto.ITERATIONS) packetFailure()
                    "parallelism" -> if (parser.integer() != VaultCrypto.PARALLELISM) packetFailure()
                    "hash_len" -> if (parser.integer() != VaultCrypto.KEY_BYTES) packetFailure()
                    else -> packetFailure()
                }
            }
            if (found != kdfFields || salt?.length != 24) packetFailure()
            return BackupProtocol.decodeBase64(salt ?: packetFailure()).also { if (it.size != 16) packetFailure() }
        }
    }

    // 已严格验证的字符串只作有界反转义；成功Base64原文和转义均为ASCII字节。
    private class JsonBase64(input: InputStream, private val guard: () -> Unit) : InputStream() {
        private val reader = InputStreamReader(input, Charsets.UTF_8.newDecoder()
            .onMalformedInput(CodingErrorAction.REPORT).onUnmappableCharacter(CodingErrorAction.REPORT)).buffered(8192)
        private var decoded = ""
        private var position = 0
        private var alphabet = 0L
        var rawBytes = 0L
            private set
        var quotedEnd = false
            private set
        var done = false
            private set
        init { if (take() != '"'.code) packetFailure() }
        private fun take(): Int = reader.read().also { if (it >= 0) rawBytes++ }
        private fun character(): Int {
            while (position >= decoded.length) {
                guard()
                if (quotedEnd) return -1
                val piece = StringBuilder(4102)
                while (piece.length < 4096) {
                    val value = take()
                    if (value < 0) packetFailure()
                    if (value == '"'.code) { quotedEnd = true; break }
                    piece.append(value.toChar())
                    if (value == '\\'.code) {
                        val escaped = take()
                        if (escaped < 0) packetFailure()
                        piece.append(escaped.toChar())
                        if (escaped == 'u'.code) repeat(4) {
                            val hex = take()
                            if (hex < 0) packetFailure()
                            piece.append(hex.toChar())
                        }
                    }
                }
                val parser = com.google.gson.stream.JsonReader(StringReader("\"$piece\"")).apply { setStrictness(Strictness.STRICT) }
                decoded = parser.nextString()
                if (parser.peek() != com.google.gson.stream.JsonToken.END_DOCUMENT) packetFailure()
                position = 0
            }
            return decoded[position++].code
        }
        private fun end(padding: Int) {
            val remainder = alphabet % 4
            if (padding > 2 || remainder == 1L || remainder == 2L && padding != 2 || remainder == 3L && padding < 1) packetFailure()
            done = true
        }
        override fun read(): Int {
            if (done) return -1
            var value = character()
            if (value < 0) { end(0); return -1 }
            if (value == '='.code) {
                var padding = 1
                while (true) {
                    value = character()
                    if (value < 0) break
                    if (value != '='.code || ++padding > 2) packetFailure()
                }
                end(padding)
                return -1
            }
            if (value !in 'A'.code..'Z'.code && value !in 'a'.code..'z'.code && value !in '0'.code..'9'.code &&
                value != '+'.code && value != '/'.code) packetFailure()
            alphabet++
            return value
        }
        override fun read(bytes: ByteArray, offset: Int, length: Int): Int {
            if (length == 0) return 0
            var count = 0
            while (count < length) {
                val value = read()
                if (value < 0) break
                bytes[offset + count++] = value.toByte()
            }
            return if (count == 0) -1 else count
        }
        override fun close() { decoded = ""; reader.close() }
    }
}

private fun packetFailure(problem: BackupProblem = BackupProblem.FORMAT): Nothing = throw BackupProtocolException(problem)
