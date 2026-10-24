package app.cangoo.android.data

import org.bouncycastle.crypto.generators.Argon2BytesGenerator
import org.bouncycastle.crypto.params.Argon2Parameters
import java.security.SecureRandom
import javax.crypto.Cipher
import javax.crypto.spec.GCMParameterSpec
import javax.crypto.spec.SecretKeySpec

internal object VaultCrypto {
    const val MEMORY_KIB = 19456
    const val ITERATIONS = 2
    const val PARALLELISM = 1
    const val KEY_BYTES = 32
    const val SALT_BYTES = 16
    const val NONCE_BYTES = 12
    private val random = SecureRandom()

    fun randomBytes(size: Int) = ByteArray(size).also(random::nextBytes)

    fun deriveKey(password: String, salt: ByteArray): ByteArray {
        require(salt.size == SALT_BYTES)
        val encoded = validatedUtf8(password, 1024)
        val parameters = Argon2Parameters.Builder(Argon2Parameters.ARGON2_id)
            .withVersion(Argon2Parameters.ARGON2_VERSION_13)
            .withMemoryAsKB(MEMORY_KIB)
            .withIterations(ITERATIONS)
            .withParallelism(PARALLELISM)
            .withSalt(salt)
            .build()
        val result = ByteArray(KEY_BYTES)
        try {
            Argon2BytesGenerator().apply { init(parameters) }.generateBytes(encoded, result)
            return result
        } catch (failure: Exception) {
            result.fill(0)
            throw failure
        } finally {
            encoded.fill(0)
            parameters.clear()
        }
    }

    fun wrap(key: ByteArray, nonce: ByteArray, plaintext: ByteArray, aad: ByteArray): ByteArray =
        crypt(Cipher.ENCRYPT_MODE, key, nonce, plaintext, aad)

    fun unwrap(key: ByteArray, nonce: ByteArray, ciphertext: ByteArray, aad: ByteArray): ByteArray =
        crypt(Cipher.DECRYPT_MODE, key, nonce, ciphertext, aad)

    private fun crypt(mode: Int, key: ByteArray, nonce: ByteArray, input: ByteArray, aad: ByteArray): ByteArray {
        require(key.size == KEY_BYTES && nonce.size == NONCE_BYTES)
        return Cipher.getInstance("AES/GCM/NoPadding").run {
            init(mode, SecretKeySpec(key, "AES"), GCMParameterSpec(128, nonce))
            updateAAD(aad)
            doFinal(input)
        }
    }
}
