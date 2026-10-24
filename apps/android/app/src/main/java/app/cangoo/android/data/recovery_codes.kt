package app.cangoo.android.data

import android.util.JsonReader
import android.util.JsonToken
import android.util.JsonWriter
import java.io.StringReader
import java.io.StringWriter

data class RecoveryCode(val value: String, val used: Boolean = false) {
    override fun toString() = "RecoveryCode(内容已隐藏)"
}

enum class RecoveryCodeProblem(val text: String) {
    INVALID("恢复码格式无效，请检查后重试。"),
    LIMIT("恢复码超出限制：最多128条，每条最多1024字符，整组最多8192字符。请调整后重试。"),
    DUPLICATE("恢复码存在完全重复行，请检查后重试。"),
}

class RecoveryCodeException(val problem: RecoveryCodeProblem, val line: Int = 0) : IllegalArgumentException(problem.text)

fun normalizeRecoveryCodes(raw: String): List<RecoveryCode> {
    checkRecoveryText(raw, 8192, 32768)
    val codes = mutableListOf<RecoveryCode>()
    val seen = mutableSetOf<String>()
    raw.replace("\r\n", "\n").split('\n').forEachIndexed { index, line ->
        val value = trimRecoveryCode(line)
        if (value.isNotEmpty()) {
            validateRecoveryCode(value, index + 1)
            if (!seen.add(value)) recoveryFailure(RecoveryCodeProblem.DUPLICATE, index + 1)
            codes.add(RecoveryCode(value))
            if (codes.size > 128) recoveryFailure(RecoveryCodeProblem.LIMIT, index + 1)
        }
    }
    return validateRecoveryCodes(codes)
}

fun validateRecoveryCodes(codes: List<RecoveryCode>): List<RecoveryCode> {
    if (codes.size > 128) recoveryFailure(RecoveryCodeProblem.LIMIT)
    val seen = mutableSetOf<String>()
    codes.forEachIndexed { index, code ->
        validateRecoveryCode(code.value, index + 1)
        if (!seen.add(code.value)) recoveryFailure(RecoveryCodeProblem.DUPLICATE, index + 1)
    }
    checkRecoveryText(codes.joinToString("\n") { it.value }, 8192, 32768)
    return codes.toList()
}

fun encodeRecoveryCodes(codes: List<RecoveryCode>): String {
    val validated = validateRecoveryCodes(codes)
    val output = StringWriter()
    try {
        JsonWriter(output).use { writer ->
            writer.beginArray()
            validated.forEach { code ->
                writer.beginObject().name("value").value(code.value).name("used").value(code.used).endObject()
            }
            writer.endArray()
        }
    } catch (_: Exception) {
        throw IllegalStateException("恢复码编码未能完成，请重试。")
    }
    return output.toString()
}

fun decodeRecoveryCodes(json: String): List<RecoveryCode> {
    val jsonLimit = 8192 * 12 + 128 * 32 + 2
    checkRecoveryText(json, jsonLimit, jsonLimit)
    checkRecoveryJsonTokens(json)
    try {
        return JsonReader(StringReader(json)).use { reader ->
            reader.isLenient = false
            reader.beginArray()
            val codes = mutableListOf<RecoveryCode>()
            while (reader.hasNext()) {
                if (codes.size == 128) recoveryFailure(RecoveryCodeProblem.LIMIT)
                reader.beginObject()
                var value: String? = null
                var used: Boolean? = null
                val fields = mutableSetOf<String>()
                while (reader.hasNext()) {
                    val field = reader.nextName()
                    if (!fields.add(field)) recoveryFailure(RecoveryCodeProblem.INVALID)
                    when (field) {
                        "value" -> {
                            if (reader.peek() != JsonToken.STRING) recoveryFailure(RecoveryCodeProblem.INVALID)
                            value = reader.nextString()
                        }
                        "used" -> {
                            if (reader.peek() != JsonToken.BOOLEAN) recoveryFailure(RecoveryCodeProblem.INVALID)
                            used = reader.nextBoolean()
                        }
                        else -> recoveryFailure(RecoveryCodeProblem.INVALID)
                    }
                }
                reader.endObject()
                codes.add(RecoveryCode(value ?: recoveryFailure(RecoveryCodeProblem.INVALID), used ?: recoveryFailure(RecoveryCodeProblem.INVALID)))
            }
            reader.endArray()
            if (reader.peek() != JsonToken.END_DOCUMENT) recoveryFailure(RecoveryCodeProblem.INVALID)
            validateRecoveryCodes(codes)
        }
    } catch (failure: RecoveryCodeException) {
        throw failure
    } catch (_: Exception) {
        // 平台解析异常可能携带输入片段，只返回固定原因。
        recoveryFailure(RecoveryCodeProblem.INVALID)
    }
}

// 原生读取器仍接受大写布尔和非法转义；只约束本格式字面量，结构由原生解析。
internal fun checkRecoveryJsonTokens(json: String) {
    var index = 0
    while (index < json.length) {
        when (json[index]) {
            '"' -> {
                index++
                var closed = false
                while (index < json.length) {
                    val character = json[index++]
                    if (character == '"') { closed = true; break }
                    if (character < ' ') recoveryFailure(RecoveryCodeProblem.INVALID)
                    if (character == '\\') {
                        if (index == json.length) recoveryFailure(RecoveryCodeProblem.INVALID)
                        val escaped = json[index++]
                        if (escaped == 'u') {
                            if (index + 4 > json.length || (index until index + 4).any {
                                json[it] !in '0'..'9' && json[it] !in 'a'..'f' && json[it] !in 'A'..'F'
                            }) recoveryFailure(RecoveryCodeProblem.INVALID)
                            index += 4
                        } else if (escaped !in "\"\\/bfnrt") recoveryFailure(RecoveryCodeProblem.INVALID)
                    }
                }
                if (!closed) recoveryFailure(RecoveryCodeProblem.INVALID)
            }
            't' -> {
                if (!json.startsWith("true", index)) recoveryFailure(RecoveryCodeProblem.INVALID)
                index += 4
            }
            'f' -> {
                if (!json.startsWith("false", index)) recoveryFailure(RecoveryCodeProblem.INVALID)
                index += 5
            }
            in "{}[]:, \t\r\n" -> index++
            else -> recoveryFailure(RecoveryCodeProblem.INVALID)
        }
    }
}

private fun validateRecoveryCode(value: String, line: Int) {
    if (value.isEmpty() || value != trimRecoveryCode(value) || value.any { it.code < 32 || it.code == 127 }) {
        recoveryFailure(RecoveryCodeProblem.INVALID, line)
    }
    checkRecoveryText(value, 1024, 4096, line)
}

private fun trimRecoveryCode(value: String): String = value.trim { it.isWhitespace() || it == '\u0085' }

private fun checkRecoveryText(value: String, maxCharacters: Int, maxBytes: Int, line: Int = 0) {
    if (value.codePointCount(0, value.length) > maxCharacters) recoveryFailure(RecoveryCodeProblem.LIMIT, line)
    val bytes = try { validatedUtf8(value, maxCharacters, Int.MAX_VALUE) }
    catch (_: VaultException) { recoveryFailure(RecoveryCodeProblem.INVALID, line) }
    try {
        if (bytes.size > maxBytes) recoveryFailure(RecoveryCodeProblem.LIMIT, line)
    } finally { bytes.fill(0) }
}

private fun recoveryFailure(problem: RecoveryCodeProblem, line: Int = 0): Nothing = throw RecoveryCodeException(problem, line)
