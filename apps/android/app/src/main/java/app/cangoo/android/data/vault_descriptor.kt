package app.cangoo.android.data

import com.google.gson.Strictness
import com.google.gson.stream.JsonReader
import com.google.gson.stream.JsonToken
import org.json.JSONObject
import java.io.ByteArrayOutputStream
import java.io.DataOutputStream
import java.io.StringReader
import java.security.MessageDigest
import javax.crypto.Mac
import javax.crypto.spec.SecretKeySpec

internal class VaultBiometricEnvelope(val version: Int, val alias: String, val nonce: ByteArray, val wrappedKey: ByteArray) {
    override fun toString() = "VaultBiometricEnvelope(内容已隐藏)"
}

/** 描述与生物封装各用固定域；二进制编码不依赖结构化文本的字段顺序。 */
internal object VaultDescriptorAuth {
    fun encoding(domain: String, version: Int = 1, write: DataOutputStream.() -> Unit): ByteArray = ByteArrayOutputStream().use { bytes ->
        DataOutputStream(bytes).use { output -> output.field(domain); output.writeInt(version); output.write() }
        bytes.toByteArray()
    }

    fun DataOutputStream.field(value: String) {
        val bytes = value.encodeToByteArray(throwOnInvalidSequence = true)
        try { field(bytes) } finally { bytes.fill(0) }
    }

    fun DataOutputStream.field(value: ByteArray) { writeInt(value.size); write(value) }

    fun mac(key: ByteArray, bytes: ByteArray): ByteArray {
        require(key.size == VaultCrypto.KEY_BYTES)
        return try { Mac.getInstance("HmacSHA256").run { init(SecretKeySpec(key, "HmacSHA256")); doFinal(bytes) } }
        finally { bytes.fill(0) }
    }

    fun descriptor(key: ByteArray, metadata: Metadata): ByteArray = mac(key, encoding("cangoo-android-descriptor-mac") {
        field(metadata.id)
        val selected = requireNotNull(metadata.selection)
        field(selected.dataGroup); field(selected.descriptorGroup)
        writeInt(metadata.version); field(metadata.name); writeBoolean(metadata.hasMasterPassword)
        field("argon2id")
        listOf(19, VaultCrypto.MEMORY_KIB, VaultCrypto.ITERATIONS, VaultCrypto.PARALLELISM, VaultCrypto.KEY_BYTES).forEach(::writeInt)
        field(metadata.salt); field(metadata.nonce); field(metadata.wrappedKey)
        writeBoolean(metadata.biometric != null)
        metadata.biometric?.let { bio -> writeInt(bio.version); field(bio.alias); field(bio.nonce); field(bio.wrappedKey) }
    })

    fun verify(key: ByteArray, metadata: Metadata, selection: VaultLayoutSelection) {
        if (metadata.version == 1) {
            if (selection != VaultLayoutSelection("legacy", "legacy")) unavailable()
            return
        }
        if (metadata.selection != selection) unavailable()
        val expected = descriptor(key, metadata)
        try { if (!MessageDigest.isEqual(expected, metadata.descriptorMac)) unavailable() }
        finally { expected.fill(0) }
    }

    fun biometricAad(id: String, dataGroup: String, alias: String): ByteArray = encoding("cangoo-android-biometric-wrap") {
        require(validUuid(id) && validGroup(dataGroup) && validAlias(alias))
        field(id); field(dataGroup); field(alias)
    }

    fun validUuid(value: String) = runCatching { java.util.UUID.fromString(value).toString() == value }.getOrDefault(false)
    fun validGroup(value: String) = value == "legacy" || validUuid(value)
    fun validAlias(value: String) = value.length in 1..128 && value.all { it in 'a'..'z' || it in '0'..'9' || it == '_' || it == '-' }

    // JSONObject 会吞掉重复字段；先用现有严格流解析器保留拒绝边界。
    fun readJson(text: String): JSONObject {
        require(!text.startsWith('\uFEFF'))
        JsonReader(StringReader(text)).use { reader ->
            reader.setStrictness(Strictness.STRICT)
            reader.setNestingLimit(4)
            fun readObject(depth: Int): JSONObject {
                require(depth <= 3 && reader.peek() == JsonToken.BEGIN_OBJECT)
                val result = JSONObject()
                reader.beginObject()
                while (reader.hasNext()) {
                    val name = reader.nextName()
                    require(!result.has(name))
                    val value: Any = when (reader.peek()) {
                        JsonToken.STRING -> reader.nextString()
                        JsonToken.NUMBER -> reader.nextString().let { number ->
                            require(number.matches(Regex("0|[1-9][0-9]*"))); number.toInt()
                        }
                        JsonToken.BOOLEAN -> reader.nextBoolean()
                        JsonToken.NULL -> { reader.nextNull(); JSONObject.NULL }
                        JsonToken.BEGIN_OBJECT -> readObject(depth + 1)
                        else -> throw IllegalArgumentException()
                    }
                    result.put(name, value)
                }
                reader.endObject()
                return result
            }
            return readObject(1).also { require(reader.peek() == JsonToken.END_DOCUMENT) }
        }
    }

    private fun unavailable(): Nothing = throw VaultException(VaultError.DATA_UNAVAILABLE)
}
