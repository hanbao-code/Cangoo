package app.cangoo.android.data

import com.google.gson.Strictness
import com.google.gson.stream.JsonReader
import com.google.gson.stream.JsonToken
import java.io.StringReader
import java.nio.ByteBuffer
import java.nio.charset.CodingErrorAction
import java.security.MessageDigest
import java.security.SecureRandom
import java.util.Base64
import org.bouncycastle.crypto.AsymmetricCipherKeyPair
import org.bouncycastle.crypto.digests.SHA256Digest
import org.bouncycastle.crypto.generators.HKDFBytesGenerator
import org.bouncycastle.crypto.hpke.HPKE
import org.bouncycastle.crypto.hpke.HPKEContext
import org.bouncycastle.crypto.hpke.HPKEContextWithEncapsulation
import org.bouncycastle.crypto.macs.HMac
import org.bouncycastle.crypto.params.HKDFParameters
import org.bouncycastle.crypto.params.KeyParameter
import org.bouncycastle.crypto.params.X25519PrivateKeyParameters
import org.bouncycastle.crypto.params.X25519PublicKeyParameters

internal class DirectTransferException(val code: String) : IllegalArgumentException(code)

internal data class DirectTransferEvent(
    val type: String,
    val fields: Map<String, Any?> = emptyMap(),
    val data: ByteArray? = null,
) { override fun toString() = "DirectTransferEvent($type)" }

internal data class DirectTransferResult(
    val outbound: List<ByteArray> = emptyList(),
    val events: List<DirectTransferEvent> = emptyList(),
) { override fun toString() = "DirectTransferResult(内容已隐藏)" }

// 仅处理有界消息和认证；库会话、超时和串行所有权由平台控制器维护。
internal class DirectTransferSession(
    val role: String,
    private val deviceId: String,
    private val deviceName: String,
) {
    var phase = "CONNECTING"
        private set
    var sas: List<Int>? = null
        private set
    var peerId: String? = null
        private set
    var peerName: String? = null
        private set
    var authenticated = false
        private set
    var sentBytes = 0L
        private set
    var receivedBytes = 0L
        private set

    private val sender = role == "SENDER"
    private var begun = false
    private var handshake = if (sender) "NEW" else "HELLO"
    private var session: String? = null
    private var hpkePair: AsymmetricCipherKeyPair? = null
    private var peerHpke: ByteArray? = null
    private var sasPair: AsymmetricCipherKeyPair? = null
    private var peerSas: ByteArray? = null
    private var secret: ByteArray? = null
    private var startBytes: ByteArray? = null
    private var commitment: ByteArray? = null
    private var locallyConfirmed = false
    private var peerConfirmed = false
    private var sending: HPKEContextWithEncapsulation? = null
    private var receiving: HPKEContext? = null
    private var receivingEnc: ByteArray? = null
    private var sendSequence = 0L
    private var receiveSequence = 0L
    private var localMetadata = false
    private var remoteMetadata = false
    private var offer: Map<String, Any?>? = null
    private var buffer: ByteArray? = null
    private var digest: MessageDigest? = null
    private val frameBuffer = ByteArray(MAX_FRAME + 4)
    private var frameUsed = 0
    private var frameSize = 0

    init {
        ensure(role == "SENDER" || role == "RECEIVER")
        ensure(HEX_ID.matches(deviceId))
        name(deviceName, 64, 256)
        hpkePair = newPair()
    }

    fun begin(): DirectTransferResult = run {
        ensure(!begun, "SEQUENCE")
        begun = true
        if (sender) {
            session = hex(ByteArray(16).also(RANDOM::nextBytes))
            handshake = "WELCOME"
            outbound += clearFrame(identity("hello"))
        }
    }

    fun receive(data: ByteArray): DirectTransferResult = run {
        ensure(begun, "SEQUENCE")
        ensure(data.size <= MAX_FRAME + 4, "LIMIT")
        var offset = 0
        while (offset < data.size) {
            val target = if (frameUsed < 4) 4 else frameSize + 4
            val count = minOf(target - frameUsed, data.size - offset)
            data.copyInto(frameBuffer, frameUsed, offset, offset + count)
            frameUsed += count
            offset += count
            if (frameUsed == 4 && frameSize == 0) {
                val length = ByteBuffer.wrap(frameBuffer, 0, 4).int.toLong() and 0xffffffffL
                ensure(length in 1..MAX_FRAME.toLong(), "LIMIT")
                frameSize = length.toInt()
            }
            if (frameSize != 0 && frameUsed == frameSize + 4) {
                val frame = frameBuffer.copyOfRange(4, frameUsed)
                frameBuffer.fill(0, 0, frameUsed)
                frameUsed = 0
                frameSize = 0
                try { receiveFrame(frame, this) } finally { frame.fill(0) }
                if (phase == "CLOSED") break
            }
        }
    }

    fun confirmSas(): DirectTransferResult = run {
        if (locallyConfirmed) return@run
        ensure(handshake == "MAC" && sas != null, "SEQUENCE")
        locallyConfirmed = true
        val id = "hpke:$deviceId"
        outbound += clearFrame(mapOf("type" to "mac", "session" to session,
            "keys" to b64(mac(deviceId, requireNotNull(peerId), "KEY_IDS", id)),
            "mac" to mapOf(id to b64(mac(deviceId, requireNotNull(peerId), id, b64(publicKey(requireNotNull(hpkePair))))))))
        startProtected(this)
    }

    fun sendMessage(message: Map<String, Any?>): DirectTransferResult = run {
        val frozen = parseJson(canonical(message))
        val type = string(frozen, "type")
        ensure(type in setOf("metadata", "offer", "accept", "start", "finish"))
        control(frozen, outgoing = true, this)
        outbound += protectedControl(frozen)
    }

    fun sendChunk(data: ByteArray): DirectTransferResult = run {
        ensure(sender && authenticated && phase == "TRANSFERRING", "SEQUENCE")
        ensure(data.size in 1..CHUNK_SIZE, "LIMIT")
        ensure(sentBytes + data.size <= number(requireNotNull(offer), "byteCount"), "LIMIT")
        val plaintext = ByteBuffer.allocate(9 + data.size).put(2).putLong(sentBytes).put(data).array()
        try { outbound += protect(plaintext) } finally { plaintext.fill(0) }
        requireNotNull(digest).update(data)
        sentBytes += data.size
    }

    fun sendReceived(): DirectTransferResult = run {
        ensure(!sender && phase == "VERIFYING", "SEQUENCE")
        outbound += protectedControl(mapOf("type" to "received", "sha256" to string(requireNotNull(offer), "sha256")))
        phase = "COMPLETE"
    }

    fun cancel(): DirectTransferResult = run {
        if (session != null) {
            outbound += if (sending != null) protectedControl(mapOf("type" to "cancel", "code" to "CANCELLED"))
            else clearFrame(mapOf("type" to "cancel", "session" to session, "code" to "CANCELLED"))
        }
        close()
    }

    fun close() {
        erase()
        if (phase != "FAILED") phase = "CLOSED"
    }

    private fun receiveFrame(frame: ByteArray, result: Pending) {
        when (frame[0].toInt()) {
            1 -> {
                ensure(sending == null, "SEQUENCE")
                ensure(frame.size - 1 <= JSON_LIMIT, "LIMIT")
                handshake(parseJson(frame.copyOfRange(1, frame.size)), result)
            }
            2 -> {
                ensure(sending != null, "SEQUENCE")
                ensure(frame.size >= 58)
                val seq = ByteBuffer.wrap(frame, 1, 8).long
                ensure(seq >= 0 && seq == receiveSequence, "SEQUENCE")
                val enc = frame.copyOfRange(9, 41)
                if (receiving == null) {
                    receivingEnc = enc.copyOf()
                    receiving = auth {
                        hpke().setupAuthR(enc, requireNotNull(hpkePair), hpkeInfo(outgoing = false),
                            X25519PublicKeyParameters(requireNotNull(peerHpke)))
                    }
                } else ensure(MessageDigest.isEqual(enc, receivingEnc), "AUTH")
                val ciphertext = frame.copyOfRange(41, frame.size)
                val plaintext = auth { requireNotNull(receiving).open(aad(seq, enc, outgoing = false), ciphertext) }
                receiveSequence++
                try {
                    ensure(plaintext.isNotEmpty())
                    when (plaintext[0].toInt()) {
                        1 -> {
                            ensure(plaintext.size - 1 <= JSON_LIMIT, "LIMIT")
                            val bytes = plaintext.copyOfRange(1, plaintext.size)
                            try { control(parseJson(bytes), outgoing = false, result) } finally { bytes.fill(0) }
                        }
                        2 -> receiveChunk(plaintext, result)
                        else -> fail("INVALID")
                    }
                } finally { plaintext.fill(0) }
            }
            else -> fail("INVALID")
        }
    }

    private fun handshake(message: Map<String, Any?>, result: Pending) {
        val type = string(message, "type")
        if (type == "cancel") {
            fields(message, "type", "session", "code")
            ensure(session != null && string(message, "session") == session, "SEQUENCE")
            ensure(string(message, "code") == "CANCELLED")
            close()
            result.events += DirectTransferEvent("cancelled")
            return
        }
        when (handshake) {
            "HELLO", "WELCOME" -> {
                ensure(type == if (sender) "welcome" else "hello", "SEQUENCE")
                fields(message, "type", "version", "session", "device", "name", "hpke")
                ensure(number(message, "version") == 1L)
                val incomingSession = string(message, "session")
                ensure(HEX_ID.matches(incomingSession))
                if (sender) ensure(session == incomingSession, "SEQUENCE") else session = incomingSession
                val incomingId = string(message, "device")
                ensure(HEX_ID.matches(incomingId) && incomingId != deviceId)
                val incomingName = string(message, "name").also { name(it, 64, 256) }
                val key = unbase64(string(message, "hpke"))
                // 握手早期即排除低阶点；不保留用于检查的共享值。
                shared(requireNotNull(hpkePair), key).fill(0)
                peerId = incomingId
                peerName = incomingName
                peerHpke = key
                result.events += DirectTransferEvent("peer", mapOf("deviceId" to peerId, "name" to peerName))
                if (sender) {
                    val start = startMessage()
                    startBytes = canonical(start)
                    result.outbound += clearFrame(start)
                    handshake = "ACCEPT"
                } else {
                    result.outbound += clearFrame(identity("welcome"))
                    handshake = "START"
                }
            }
            "START" -> {
                ensure(type == "start", "SEQUENCE")
                ensure(message == startMessage())
                startBytes = canonical(message)
                sasPair = newPair()
                val committed = sha256(b64(publicKey(requireNotNull(sasPair))).toByteArray(Charsets.UTF_8) + requireNotNull(startBytes))
                result.outbound += clearFrame(mapOf("type" to "accept", "session" to session, "commitment" to b64(committed)))
                handshake = "KEY"
            }
            "ACCEPT" -> {
                ensure(type == "accept", "SEQUENCE")
                fields(message, "type", "session", "commitment")
                sameSession(message)
                commitment = unbase64(string(message, "commitment"))
                sasPair = newPair()
                result.outbound += clearFrame(mapOf("type" to "key", "session" to session, "key" to b64(publicKey(requireNotNull(sasPair)))))
                handshake = "KEY"
            }
            "KEY" -> {
                ensure(type == "key", "SEQUENCE")
                fields(message, "type", "session", "key")
                sameSession(message)
                val key = unbase64(string(message, "key"))
                if (sender) {
                    val actual = sha256(b64(key).toByteArray(Charsets.UTF_8) + requireNotNull(startBytes))
                    ensure(MessageDigest.isEqual(actual, commitment), "AUTH")
                }
                secret = shared(requireNotNull(sasPair), key)
                peerSas = key
                if (!sender) result.outbound += clearFrame(mapOf("type" to "key", "session" to session,
                    "key" to b64(publicKey(requireNotNull(sasPair)))))
                val ours = b64(publicKey(requireNotNull(sasPair)))
                val theirs = b64(key)
                val info = if (sender) "CANGOO_DIRECT_SAS_V1|$deviceId|$ours|$peerId|$theirs|$session"
                    else "CANGOO_DIRECT_SAS_V1|$peerId|$theirs|$deviceId|$ours|$session"
                val bits = hkdf(requireNotNull(secret), info, 5)
                val b = bits.map { it.toInt() and 255 }
                sas = listOf(((b[0] shl 5) or (b[1] shr 3)) + 1000,
                    (((b[1] and 7) shl 10) or (b[2] shl 2) or (b[3] shr 6)) + 1000,
                    (((b[3] and 63) shl 7) or (b[4] shr 1)) + 1000)
                bits.fill(0)
                handshake = "MAC"
                phase = "SAS"
                result.events += DirectTransferEvent("sas", mapOf("numbers" to sas))
            }
            "MAC" -> {
                ensure(type == "mac" && !peerConfirmed, "SEQUENCE")
                fields(message, "type", "session", "keys", "mac")
                sameSession(message)
                val id = "hpke:$peerId"
                val provided = message["mac"] as? Map<*, *> ?: fail("INVALID")
                ensure(provided.keys == setOf(id))
                val keyMac = unbase64(provided[id] as? String ?: fail("INVALID"))
                val idsMac = unbase64(string(message, "keys"))
                ensure(MessageDigest.isEqual(keyMac, mac(requireNotNull(peerId), deviceId, id, b64(requireNotNull(peerHpke)))), "AUTH")
                ensure(MessageDigest.isEqual(idsMac, mac(requireNotNull(peerId), deviceId, "KEY_IDS", id)), "AUTH")
                peerConfirmed = true
                startProtected(result)
            }
            else -> fail("SEQUENCE")
        }
    }

    private fun startProtected(result: Pending) {
        if (!locallyConfirmed || !peerConfirmed) return
        sending = auth { hpke().setupAuthS(X25519PublicKeyParameters(requireNotNull(peerHpke)), hpkeInfo(true), requireNotNull(hpkePair)) }
        secret?.fill(0)
        secret = null
        sasPair = null
        peerSas = null
        commitment = null
        startBytes = null
        phase = "WAIT_READY"
        handshake = "DONE"
        result.outbound += protectedControl(mapOf("type" to "ready"))
    }

    private fun control(message: Map<String, Any?>, outgoing: Boolean, result: Pending) {
        val type = string(message, "type")
        if (type == "cancel") {
            fields(message, "type", "code")
            ensure(string(message, "code") == "CANCELLED")
            close()
            result.events += DirectTransferEvent("cancelled")
            return
        }
        if (type == "ready") {
            fields(message, "type")
            ensure(!outgoing && phase == "WAIT_READY", "SEQUENCE")
            authenticated = true
            phase = "AUTHENTICATED"
            result.events += DirectTransferEvent("authenticated")
            return
        }
        ensure(authenticated, "SEQUENCE")
        when (type) {
            "metadata" -> {
                fields(message, "type", "vaultName")
                ensure(phase == "AUTHENTICATED" && !(if (outgoing) localMetadata else remoteMetadata), "SEQUENCE")
                name(string(message, "vaultName"), 256, 1024)
                if (outgoing) localMetadata = true else remoteMetadata = true
            }
            "offer" -> {
                fields(message, "type", "scope", "byteCount", "passwordCount", "noteCount", "sha256")
                ensure(outgoing == sender && phase == "AUTHENTICATED" && localMetadata && remoteMetadata && offer == null, "SEQUENCE")
                ensure(number(message, "byteCount") in 1..MAX_BYTES.toLong(), "LIMIT")
                val passwords = number(message, "passwordCount")
                val notes = number(message, "noteCount")
                ensure(passwords in 0..100_000L && notes in 0..100_000L && passwords + notes <= 100_000L, "LIMIT")
                val scope = string(message, "scope")
                ensure(scope in setOf("ALL", "PASSWORDS", "NOTES"))
                ensure((scope != "PASSWORDS" || notes == 0L) && (scope != "NOTES" || passwords == 0L))
                ensure(HEX_HASH.matches(string(message, "sha256")))
                offer = message.toMap()
                phase = "OFFERED"
            }
            "accept" -> {
                checkTransferControl(message)
                ensure(outgoing != sender && phase == "OFFERED", "SEQUENCE")
                if (!sender) buffer = ByteArray(number(requireNotNull(offer), "byteCount").toInt())
                digest = MessageDigest.getInstance("SHA-256")
                phase = "ACCEPTED"
            }
            "start" -> {
                checkTransferControl(message)
                ensure(outgoing == sender && phase == "ACCEPTED", "SEQUENCE")
                phase = "TRANSFERRING"
            }
            "finish" -> {
                checkTransferControl(message)
                ensure(outgoing == sender && phase == "TRANSFERRING", "SEQUENCE")
                val size = if (sender) sentBytes else receivedBytes
                ensure(size == number(requireNotNull(offer), "byteCount"), "LIMIT")
                ensure(hex(requireNotNull(digest).digest()) == string(requireNotNull(offer), "sha256"), "AUTH")
                digest = null
                phase = if (sender) "WAIT_RECEIPT" else "VERIFYING"
                if (!sender) {
                    val complete = requireNotNull(buffer)
                    buffer = null
                    result.events += DirectTransferEvent("complete", mapOf("byteCount" to size,
                        "sha256" to string(requireNotNull(offer), "sha256")), complete)
                }
                return
            }
            "received" -> {
                checkTransferControl(message)
                ensure(!outgoing && sender && phase == "WAIT_RECEIPT", "SEQUENCE")
                phase = "COMPLETE"
            }
            else -> fail("INVALID")
        }
        if (!outgoing) result.events += DirectTransferEvent(type, message.filterKeys { it != "type" })
    }

    private fun checkTransferControl(message: Map<String, Any?>) {
        fields(message, "type", "sha256")
        ensure(offer != null, "SEQUENCE")
        ensure(string(message, "sha256") == string(requireNotNull(offer), "sha256"), "AUTH")
    }

    private fun receiveChunk(plaintext: ByteArray, result: Pending) {
        ensure(!sender && authenticated && phase == "TRANSFERRING", "SEQUENCE")
        ensure(plaintext.size in 10..CHUNK_SIZE + 9, "LIMIT")
        val offset = ByteBuffer.wrap(plaintext, 1, 8).long
        ensure(offset == receivedBytes, "SEQUENCE")
        val count = plaintext.size - 9
        val target = requireNotNull(buffer)
        ensure(receivedBytes + count <= target.size.toLong(), "LIMIT")
        plaintext.copyInto(target, receivedBytes.toInt(), 9)
        requireNotNull(digest).update(plaintext, 9, count)
        receivedBytes += count
        result.events += DirectTransferEvent("progress", mapOf("bytes" to receivedBytes))
    }

    private fun identity(type: String): Map<String, Any?> = mapOf("type" to type, "version" to 1L,
        "session" to session, "device" to deviceId, "name" to deviceName, "hpke" to b64(publicKey(requireNotNull(hpkePair))))

    private fun startMessage(): Map<String, Any?> = mapOf("type" to "start", "version" to 1L,
        "session" to session, "from" to if (sender) deviceId else peerId, "to" to if (sender) peerId else deviceId,
        "method" to "m.sas.v1", "keyAgreement" to "curve25519-hkdf-sha256", "hash" to "sha256",
        "mac" to "hkdf-hmac-sha256.v2", "sas" to "decimal")

    private fun sameSession(message: Map<String, Any?>) { ensure(string(message, "session") == session, "SEQUENCE") }

    private fun mac(origin: String, target: String, suffix: String, value: String): ByteArray {
        val key = hkdf(requireNotNull(secret), "CANGOO_DIRECT_MAC_V1|$origin|$target|$session|$suffix", 32)
        try {
            val hmac = HMac(SHA256Digest())
            hmac.init(KeyParameter(key))
            val bytes = value.toByteArray(Charsets.UTF_8)
            hmac.update(bytes, 0, bytes.size)
            return ByteArray(32).also { hmac.doFinal(it, 0) }
        } finally { key.fill(0) }
    }

    private fun hpkeInfo(outgoing: Boolean): ByteArray {
        val origin = if (outgoing) deviceId else peerId
        val target = if (outgoing) peerId else deviceId
        val direction = if (outgoing == sender) "SENDER_TO_RECEIVER" else "RECEIVER_TO_SENDER"
        return "CANGOO_DIRECT_HPKE_V1|$session|$origin|$target|$direction".toByteArray(Charsets.US_ASCII)
    }

    private fun aad(seq: Long, enc: ByteArray, outgoing: Boolean): ByteArray {
        val prefix = "CANGOO_DIRECT_FRAME_V1|".toByteArray(Charsets.US_ASCII)
        val sessionBytes = requireNotNull(session).chunked(2).map { it.toInt(16).toByte() }.toByteArray()
        return ByteBuffer.allocate(prefix.size + 16 + 1 + 8 + 32).put(prefix).put(sessionBytes)
            .put(if (outgoing == sender) 1.toByte() else 2.toByte()).putLong(seq).put(enc).array()
    }

    private fun protectedControl(message: Map<String, Any?>): ByteArray {
        val json = canonical(message)
        ensure(json.size <= JSON_LIMIT, "LIMIT")
        val plaintext = byteArrayOf(1) + json
        return try { protect(plaintext) } finally { plaintext.fill(0); json.fill(0) }
    }

    private fun protect(plaintext: ByteArray): ByteArray {
        val context = requireNotNull(sending)
        val enc = context.encapsulation
        val ciphertext = auth { context.seal(aad(sendSequence, enc, true), plaintext) }
        val body = ByteBuffer.allocate(41 + ciphertext.size).put(2).putLong(sendSequence).put(enc).put(ciphertext).array()
        sendSequence++
        return frame(body)
    }

    private fun erase() {
        secret?.fill(0); secret = null
        hpkePair = null; sasPair = null; peerHpke = null; peerSas = null
        sending = null; receiving = null; receivingEnc = null
        startBytes = null; commitment = null; sas = null
        buffer?.fill(0); buffer = null
        frameBuffer.fill(0); frameUsed = 0; frameSize = 0
        digest?.reset(); digest = null
        offer = null; authenticated = false
    }

    private class Pending {
        val outbound = mutableListOf<ByteArray>()
        val events = mutableListOf<DirectTransferEvent>()
    }

    private inline fun run(block: Pending.() -> Unit): DirectTransferResult {
        if (phase == "CLOSED" || phase == "FAILED") fail("CLOSED")
        val result = Pending()
        try {
            result.block()
            return DirectTransferResult(result.outbound.toList(), result.events.toList())
        } catch (error: Exception) {
            result.events.forEach { it.data?.fill(0) }
            result.outbound.forEach { it.fill(0) }
            erase()
            phase = "FAILED"
            throw DirectTransferException((error as? DirectTransferException)?.code ?: "INVALID")
        }
    }

    companion object {
        const val MAX_BYTES = 67_108_864
        const val CHUNK_SIZE = 65_536
        const val MAX_FRAME = 65_602
        private const val JSON_LIMIT = 16_384
        private val HEX_ID = Regex("[0-9a-f]{32}")
        private val HEX_HASH = Regex("[0-9a-f]{64}")
        private val INTEGER = Regex("-?(0|[1-9][0-9]*)")
        private val RANDOM = SecureRandom()

        private fun fail(code: String): Nothing = throw DirectTransferException(code)
        private fun ensure(condition: Boolean, code: String = "INVALID") { if (!condition) fail(code) }
        private fun string(message: Map<String, Any?>, key: String): String = message[key] as? String ?: fail("INVALID")
        private fun number(message: Map<String, Any?>, key: String): Long = when (val value = message[key]) {
            is Long -> value
            is Int -> value.toLong()
            else -> fail("INVALID")
        }
        private fun fields(message: Map<String, Any?>, vararg expected: String) { ensure(message.keys == expected.toSet()) }
        private fun b64(bytes: ByteArray): String = Base64.getEncoder().withoutPadding().encodeToString(bytes)
        private fun unbase64(value: String): ByteArray {
            ensure(value.length == 43)
            val bytes = try { Base64.getDecoder().decode(value) } catch (_: IllegalArgumentException) { fail("INVALID") }
            ensure(bytes.size == 32 && b64(bytes) == value)
            return bytes
        }
        private fun hex(bytes: ByteArray) = bytes.joinToString("") { "%02x".format(it.toInt() and 255) }
        private fun sha256(bytes: ByteArray) = MessageDigest.getInstance("SHA-256").digest(bytes)
        private fun newPair(): AsymmetricCipherKeyPair {
            val key = X25519PrivateKeyParameters(RANDOM)
            return AsymmetricCipherKeyPair(key.generatePublicKey(), key)
        }
        private fun hpke() = HPKE(HPKE.mode_auth, HPKE.kem_X25519_SHA256, HPKE.kdf_HKDF_SHA256, HPKE.aead_AES_GCM256)
        private fun publicKey(pair: AsymmetricCipherKeyPair) = (pair.public as X25519PublicKeyParameters).encoded
        private fun shared(pair: AsymmetricCipherKeyPair, peer: ByteArray): ByteArray = auth {
            ByteArray(32).also { (pair.private as X25519PrivateKeyParameters).generateSecret(X25519PublicKeyParameters(peer), it, 0) }
        }
        private inline fun <T> auth(block: () -> T): T = try { block() } catch (_: Exception) { fail("AUTH") }
        private fun hkdf(secret: ByteArray, info: String, count: Int): ByteArray {
            val generator = HKDFBytesGenerator(SHA256Digest())
            generator.init(HKDFParameters(secret, null, info.toByteArray(Charsets.UTF_8)))
            return ByteArray(count).also { generator.generateBytes(it, 0, count) }
        }
        private fun frame(body: ByteArray): ByteArray {
            ensure(body.size in 1..MAX_FRAME, "LIMIT")
            return ByteBuffer.allocate(body.size + 4).putInt(body.size).put(body).array()
        }
        private fun clearFrame(message: Map<String, Any?>): ByteArray {
            val bytes = canonical(message)
            ensure(bytes.size <= JSON_LIMIT, "LIMIT")
            return frame(byteArrayOf(1) + bytes)
        }
        private fun unicode(value: String) {
            var index = 0
            while (index < value.length) {
                val char = value[index++]
                if (char.isHighSurrogate()) ensure(index < value.length && value[index++].isLowSurrogate())
                else ensure(!char.isLowSurrogate())
            }
        }
        private fun name(value: String, maxPoints: Int, maxBytes: Int) {
            unicode(value)
            ensure(value.codePointCount(0, value.length) in 1..maxPoints && value.toByteArray(Charsets.UTF_8).size <= maxBytes)
            ensure(value.none { it.code <= 31 || it.code in 127..159 })
        }
        private fun parseJson(bytes: ByteArray): Map<String, Any?> {
            ensure(bytes.size in 1..JSON_LIMIT, "LIMIT")
            val text = Charsets.UTF_8.newDecoder().onMalformedInput(CodingErrorAction.REPORT)
                .onUnmappableCharacter(CodingErrorAction.REPORT).decode(ByteBuffer.wrap(bytes)).toString()
            JsonReader(StringReader(text)).use { reader ->
                reader.strictness = Strictness.STRICT
                val value = readObject(reader, 0)
                ensure(reader.peek() == JsonToken.END_DOCUMENT)
                return value
            }
        }
        private fun readObject(reader: JsonReader, depth: Int): Map<String, Any?> {
            ensure(depth <= 1 && reader.peek() == JsonToken.BEGIN_OBJECT)
            val value = linkedMapOf<String, Any?>()
            reader.beginObject()
            while (reader.hasNext()) {
                val key = reader.nextName().also(::unicode)
                ensure(!value.containsKey(key))
                value[key] = when (reader.peek()) {
                    JsonToken.STRING -> reader.nextString().also(::unicode)
                    JsonToken.NUMBER -> reader.nextString().let { ensure(INTEGER.matches(it)); it.toLongOrNull() ?: fail("INVALID") }
                    JsonToken.BEGIN_OBJECT -> readObject(reader, depth + 1)
                    else -> fail("INVALID")
                }
            }
            reader.endObject()
            return value
        }
        private fun canonical(message: Map<String, Any?>): ByteArray = buildString { appendObject(message, 0) }.toByteArray(Charsets.UTF_8)
        private fun StringBuilder.appendObject(value: Map<*, *>, depth: Int) {
            ensure(depth <= 1 && value.keys.all { it is String })
            append('{')
            // 协议字段和唯一MAC键均为ASCII；拒绝其他键，保持两端排序完全一致。
            val keys = value.keys.map { it as String }.also { ensure(it.all { key -> key.all { char -> char.code in 32..126 } }) }.sorted()
            keys.forEachIndexed { index, key ->
                if (index != 0) append(',')
                appendQuoted(key); append(':')
                when (val item = value[key]) {
                    is String -> appendQuoted(item)
                    is Int -> append(item)
                    is Long -> append(item)
                    is Map<*, *> -> appendObject(item, depth + 1)
                    else -> fail("INVALID")
                }
            }
            append('}')
        }
        private fun StringBuilder.appendQuoted(value: String) {
            unicode(value)
            append('"')
            value.forEach { char ->
                when (char) {
                    '"' -> append("\\\"")
                    '\\' -> append("\\\\")
                    '\b' -> append("\\b")
                    '\t' -> append("\\t")
                    '\n' -> append("\\n")
                    '\u000c' -> append("\\f")
                    '\r' -> append("\\r")
                    else -> if (char.code < 32) append("\\u%04x".format(char.code)) else append(char)
                }
            }
            append('"')
        }
    }
}
