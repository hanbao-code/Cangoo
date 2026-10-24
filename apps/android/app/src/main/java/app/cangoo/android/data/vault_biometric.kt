package app.cangoo.android.data

import android.os.Build
import android.security.keystore.KeyInfo
import android.security.keystore.KeyProperties
import android.security.keystore.KeyProtection
import kotlinx.coroutines.CancellationException
import java.security.KeyStore
import javax.crypto.Cipher
import javax.crypto.SecretKey
import javax.crypto.SecretKeyFactory
import javax.crypto.spec.GCMParameterSpec
import javax.crypto.spec.SecretKeySpec

internal enum class VaultBiometricPurpose { ENABLE, REBUILD, UNLOCK }
internal sealed interface VaultBiometricAuthentication {
    data class Authenticated(val cipher: Cipher) : VaultBiometricAuthentication
    data object Cancelled : VaultBiometricAuthentication
    data class Failure(val code: Int) : VaultBiometricAuthentication
}
internal typealias VaultBiometricAuthenticator = suspend (Cipher, VaultBiometricPurpose) -> VaultBiometricAuthentication
internal enum class VaultChangeStage { AUTHENTICATING, PREPARING, REENCRYPTING, VERIFYING, BIOMETRIC, PUBLISHING, CLEANING, RESTORING }
internal class VaultBiometricCancelled : CancellationException("强认证已取消。")
internal class VaultBiometricFailure : Exception("强认证或设备绑定未能完成。")

/** 宿主只认证同一对象；密钥导入、附加数据和实际解封都由数据层完成。 */
internal object VaultBiometric {
    fun plannedAlias(id: String, operation: String): String {
        require(VaultDescriptorAuth.validUuid(id) && VaultDescriptorAuth.validUuid(operation))
        return "cangoo_vault_${id}_$operation"
    }

    private fun store() = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }
    fun exists(alias: String): Boolean = store().containsAlias(alias)

    fun create(id: String, dataGroup: String, alias: String, databaseKey: ByteArray, onImported: () -> Unit): VaultBiometricEnvelope {
        require(databaseKey.size == 32 && VaultDescriptorAuth.validAlias(alias))
        val store = store()
        if (store.containsAlias(alias)) throw VaultBiometricFailure()
        val raw = VaultCrypto.randomBytes(32)
        val nonce = VaultCrypto.randomBytes(12)
        val aad = VaultDescriptorAuth.biometricAad(id, dataGroup, alias)
        var rawSpec: SecretKeySpec? = null
        try {
            val wrapped = VaultCrypto.wrap(raw, nonce, databaseKey, aad)
            val protection = KeyProtection.Builder(KeyProperties.PURPOSE_DECRYPT)
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM).setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                .setUserAuthenticationRequired(true).setInvalidatedByBiometricEnrollment(true).apply {
                    if (Build.VERSION.SDK_INT >= 30) setUserAuthenticationParameters(0, KeyProperties.AUTH_BIOMETRIC_STRONG)
                    else setUserAuthenticationValidityDurationSeconds(-1)
                }.build()
            rawSpec = SecretKeySpec(raw, "AES")
            if (store.containsAlias(alias)) throw VaultBiometricFailure()
            store.setEntry(alias, KeyStore.SecretKeyEntry(rawSpec), protection)
            raw.fill(0); rawSpec = null
            onImported()
            val key = store.getKey(alias, null) as SecretKey
            verifyKey(key)
            return VaultBiometricEnvelope(1, alias, nonce, wrapped)
        } catch (failure: CancellationException) { throw failure }
        catch (failure: VaultException) { throw failure }
        catch (_: java.security.GeneralSecurityException) { throw VaultBiometricFailure() }
        finally { raw.fill(0); rawSpec = null; aad.fill(0) }
    }

    suspend fun decrypt(id: String, dataGroup: String, envelope: VaultBiometricEnvelope, purpose: VaultBiometricPurpose,
                        authenticate: VaultBiometricAuthenticator, guard: () -> Unit): ByteArray {
        try {
        guard()
        val key = store().getKey(envelope.alias, null) as? SecretKey ?: throw VaultBiometricFailure()
        verifyKey(key)
        val cipher = Cipher.getInstance("AES/GCM/NoPadding").apply { init(Cipher.DECRYPT_MODE, key, GCMParameterSpec(128, envelope.nonce)) }
        when (val outcome = authenticate(cipher, purpose)) {
            VaultBiometricAuthentication.Cancelled -> throw VaultBiometricCancelled()
            is VaultBiometricAuthentication.Failure -> throw VaultBiometricFailure()
            is VaultBiometricAuthentication.Authenticated -> if (outcome.cipher !== cipher) throw VaultBiometricFailure()
        }
        guard()
        val aad = VaultDescriptorAuth.biometricAad(id, dataGroup, envelope.alias)
        val unwrapped = try { cipher.updateAAD(aad); cipher.doFinal(envelope.wrappedKey) } finally { aad.fill(0) }
        try { require(unwrapped.size == 32); guard(); return unwrapped }
        catch (failure: Exception) { unwrapped.fill(0); throw failure }
        } catch (failure: CancellationException) { throw failure }
        catch (failure: VaultException) { throw failure }
        catch (_: java.security.GeneralSecurityException) { throw VaultBiometricFailure() }
    }

    fun remove(id: String, alias: String) {
        require(VaultDescriptorAuth.validUuid(id) && VaultDescriptorAuth.validAlias(alias) && alias.startsWith("cangoo_vault_${id}_") &&
            VaultDescriptorAuth.validUuid(alias.removePrefix("cangoo_vault_${id}_")))
        val store = store()
        if (store.containsAlias(alias)) store.deleteEntry(alias)
        if (store.containsAlias(alias)) throw VaultBiometricFailure()
    }

    private fun verifyKey(key: SecretKey) {
        if (key.encoded != null) throw VaultBiometricFailure()
        val info = SecretKeyFactory.getInstance("AES", "AndroidKeyStore").getKeySpec(key, KeyInfo::class.java) as KeyInfo
        if (info.origin != KeyProperties.ORIGIN_IMPORTED || info.purposes != KeyProperties.PURPOSE_DECRYPT ||
            !info.isUserAuthenticationRequired || !info.isInvalidatedByBiometricEnrollment || info.userAuthenticationValidityDurationSeconds > 0 ||
            !info.blockModes.contentEquals(arrayOf(KeyProperties.BLOCK_MODE_GCM)) ||
            !info.encryptionPaddings.contentEquals(arrayOf(KeyProperties.ENCRYPTION_PADDING_NONE)) ||
            Build.VERSION.SDK_INT >= 30 && info.userAuthenticationType != KeyProperties.AUTH_BIOMETRIC_STRONG) throw VaultBiometricFailure()
    }
}
