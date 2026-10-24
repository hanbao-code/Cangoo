package app.cangoo.android.data

import org.bouncycastle.util.encoders.Base32
import java.nio.ByteBuffer
import java.security.GeneralSecurityException
import java.util.Locale
import javax.crypto.Mac
import javax.crypto.spec.SecretKeySpec

data class TotpCodeResult(val code: String, val validUntilEpochSeconds: Long) {
    override fun toString() = "TotpCodeResult(内容已隐藏)"
}

fun normalizeTotpSecret(secret: String): String {
    val key = decodeTotpSecret(secret)
    return try { Base32.toBase32String(key).trimEnd('=') } finally { key.fill(0) }
}

fun generateTotp(secret: String, epochSeconds: Long): String = generateTotp(secret, epochSeconds, 6)

// RFC 6238公开向量使用8位；产品入口固定返回6位，不持有计时或会话状态。
internal fun generateTotp(secret: String, epochSeconds: Long, digits: Int): String {
    require(epochSeconds >= 0) { "动态口令时间无效，请检查设备时间。" }
    require(digits == 6 || digits == 8) { "动态口令生成参数无效。" }
    val key = decodeTotpSecret(secret)
    try {
        val counter = ByteBuffer.allocate(8).putLong(epochSeconds / 30).array()
        val digest = Mac.getInstance("HmacSHA1").run {
            init(SecretKeySpec(key, "HmacSHA1"))
            doFinal(counter)
        }
        try {
            val offset = digest.last().toInt() and 0x0f
            val binary = ByteBuffer.wrap(digest, offset, 4).int and Int.MAX_VALUE
            val modulus = if (digits == 6) 1_000_000 else 100_000_000
            return (binary % modulus).toString().padStart(digits, '0')
        } finally { digest.fill(0) }
    } catch (_: GeneralSecurityException) {
        throw IllegalStateException("动态口令未能生成，请重试。")
    } finally { key.fill(0) }
}

fun totpRemainingSeconds(epochSeconds: Long): Int {
    require(epochSeconds >= 0) { "动态口令时间无效，请检查设备时间。" }
    return (30 - epochSeconds % 30).toInt()
}

private fun decodeTotpSecret(secret: String): ByteArray {
    try { validatedUtf8(secret, 256, 512).fill(0) }
    catch (_: VaultException) { invalidTotpSecret() }
    val compact = secret.filterNot { it.isWhitespace() || it == '\u0085' }.trimEnd('=')
    if (compact.isEmpty() || compact.any { it !in 'A'..'Z' && it !in 'a'..'z' && it !in '2'..'7' }) invalidTotpSecret()
    val normalized = compact.uppercase(Locale.ROOT)
    val remainder = normalized.length % 8
    if (remainder == 1 || remainder == 3 || remainder == 6) invalidTotpSecret()
    return try {
        Base32.decode(normalized + "=".repeat((8 - remainder) % 8)).also {
            if (it.isEmpty()) invalidTotpSecret()
        }
    } catch (_: Exception) { invalidTotpSecret() }
}

private fun invalidTotpSecret(): Nothing = throw IllegalArgumentException("动态口令密钥格式无效，请检查后重试。")
