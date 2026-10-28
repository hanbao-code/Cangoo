package app.cangoo.android.data

import com.google.gson.Strictness
import com.google.gson.stream.JsonReader
import com.google.gson.stream.JsonToken
import java.io.StringReader
import java.math.BigInteger
import java.nio.ByteBuffer
import java.nio.charset.CodingErrorAction
import java.security.MessageDigest
import java.security.SecureRandom
import java.util.Base64
import org.bouncycastle.crypto.AsymmetricCipherKeyPair
import org.bouncycastle.crypto.agreement.srp.SRP6Client
import org.bouncycastle.crypto.agreement.srp.SRP6Server
import org.bouncycastle.crypto.agreement.srp.SRP6StandardGroups
import org.bouncycastle.crypto.agreement.srp.SRP6VerifierGenerator
import org.bouncycastle.util.BigIntegers
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
    pairingCode: String,
    private val memory: BackupMemoryBudget = BackupMemoryBudget(),
) {
    var phase = "CONNECTING"
        private set
    var approved = false
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
    private var password: ByteArray? = pairingCode.toByteArray(Charsets.US_ASCII)
    private var srpServer: SRP6Server? = null
    private var srpSalt: ByteArray? = null
    private var srpB: BigInteger? = null
    private var expectedProof: ByteArray? = null
    private var secret: ByteArray? = null
    private val transcript = mutableListOf<ByteArray>()
    private var binding: ByteArray? = null
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
        ensure(Regex("[0-9]{8}").matches(pairingCode))
        name(deviceName, 64, 256)
        hpkePair = newPair()
    }

    fun begin(): DirectTransferResult = run {
        ensure(!begun, "SEQUENCE")
        begun = true
        if (sender) {
            session = hex(ByteArray(16).also(RANDOM::nextBytes))
            handshake = "WELCOME"
            val hello = identity("hello")
            transcript += canonical(hello)
            outbound += clearFrame(hello)
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

    fun approvePeer(): DirectTransferResult = run {
        ensure(!sender && authenticated, "SEQUENCE")
        if (approved) return@run
        control(mapOf("type" to "approved"), outgoing = true, this)
        outbound += protectedControl(mapOf("type" to "approved"))
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
                val version = number(message, "version")
                val extra = if (version == 1L) emptyArray() else if (sender) arrayOf("suite", "salt", "B") else arrayOf("suite")
                fields(message, "type", "version", "session", "device", "name", "hpke", *extra)
                val incomingSession = string(message, "session")
                ensure(HEX_ID.matches(incomingSession))
                if (sender) ensure(session == incomingSession, "SEQUENCE") else session = incomingSession
                val incomingId = string(message, "device")
                ensure(HEX_ID.matches(incomingId) && incomingId != deviceId)
                val incomingName = string(message, "name").also { name(it, 64, 256) }
                val key = unbase64(string(message, "hpke"))
                shared(requireNotNull(hpkePair), key).fill(0)
                ensure(version == 2L, "UPGRADE_REQUIRED")
                ensure(string(message, "suite") == SRP_SUITE, "UPGRADE_REQUIRED")
                peerId = incomingId
                peerName = incomingName
                peerHpke = key
                result.events += DirectTransferEvent("peer", mapOf("deviceId" to peerId, "name" to peerName))
                transcript += canonical(message)
                phase = "PAIRING"
                if (sender) {
                    val saltText = string(message, "salt")
                    ensure(saltText.length in 2..22)
                    val salt = unbase64(saltText, saltText.length * 6 / 8)
                    val b = srpPublic(string(message, "B"))
                    val client = SRP6Client().also { it.init(SRP_GROUP, SHA256Digest(), RANDOM) }
                    val a = client.generateClientCredentials(salt, SRP_IDENTITY, requireNotNull(password))
                    password?.fill(0); password = null
                    val shared = auth { client.calculateSecret(b) }
                    secret = sha256(unsigned(shared))
                    val proof = srpProof(a, b, salt, requireNotNull(secret))
                    expectedProof = sha256(unsigned(a) + proof + requireNotNull(secret))
                    val response = mapOf("type" to "srp_client", "session" to session,
                        "A" to srpWire(a), "proof" to b64(proof))
                    transcript += canonical(response)
                    setBinding()
                    result.outbound += clearFrame(response)
                    handshake = "SRP_SERVER"
                } else {
                    val salt = ByteArray(16).also(RANDOM::nextBytes)
                    srpSalt = salt
                    val generator = SRP6VerifierGenerator().also { it.init(SRP_GROUP, SHA256Digest(), RANDOM) }
                    val verifier = generator.generateVerifier(salt, SRP_IDENTITY, requireNotNull(password))
                    password?.fill(0); password = null
                    val server = SRP6Server().also { it.init(SRP_GROUP, verifier, SHA256Digest(), RANDOM) }
                    srpServer = server
                    srpB = server.generateServerCredentials()
                    val response = identity("welcome") + mapOf("salt" to b64(salt), "B" to srpWire(requireNotNull(srpB)))
                    transcript += canonical(response)
                    result.outbound += clearFrame(response)
                    handshake = "SRP_CLIENT"
                }
            }
            "SRP_CLIENT" -> {
                ensure(type == "srp_client", "SEQUENCE")
                fields(message, "type", "session", "A", "proof")
                sameSession(message)
                val a = srpPublic(string(message, "A"))
                val shared = auth { requireNotNull(srpServer).calculateSecret(a) }
                srpServer = null
                secret = sha256(unsigned(shared))
                val proof = srpProof(a, requireNotNull(srpB), requireNotNull(srpSalt), requireNotNull(secret))
                ensure(MessageDigest.isEqual(proof, unbase64(string(message, "proof"))), "AUTH")
                val serverProof = sha256(unsigned(a) + proof + requireNotNull(secret))
                srpSalt?.fill(0); srpSalt = null; srpB = null
                transcript += canonical(message)
                setBinding()
                result.outbound += clearFrame(mapOf("type" to "srp_server", "session" to session,
                    "proof" to b64(serverProof), "mac" to b64(bindingMac("RECEIVER"))))
                handshake = "BIND"
            }
            "SRP_SERVER" -> {
                ensure(type == "srp_server", "SEQUENCE")
                fields(message, "type", "session", "proof", "mac")
                sameSession(message)
                ensure(MessageDigest.isEqual(expectedProof, unbase64(string(message, "proof"))), "AUTH")
                ensure(MessageDigest.isEqual(bindingMac("RECEIVER"), unbase64(string(message, "mac"))), "AUTH")
                expectedProof?.fill(0); expectedProof = null
                result.outbound += clearFrame(mapOf("type" to "bind", "session" to session, "mac" to b64(bindingMac("SENDER"))))
                startProtected(result)
            }
            "BIND" -> {
                ensure(type == "bind", "SEQUENCE")
                fields(message, "type", "session", "mac")
                sameSession(message)
                ensure(MessageDigest.isEqual(bindingMac("SENDER"), unbase64(string(message, "mac"))), "AUTH")
                startProtected(result)
            }
            else -> fail("SEQUENCE")
        }
    }

    private fun setBinding() {
        val hash = MessageDigest.getInstance("SHA-256")
        transcript.forEach { hash.update(ByteBuffer.allocate(4).putInt(it.size).array()); hash.update(it) }
        binding = hash.digest()
        transcript.clear()
    }

    private fun bindingMac(role: String): ByteArray {
        val key = hkdf(requireNotNull(secret), "CANGOO_DIRECT_BIND_V2|$role", 32, requireNotNull(binding))
        try {
            val hmac = HMac(SHA256Digest())
            hmac.init(KeyParameter(key))
            val bytes = requireNotNull(binding)
            hmac.update(bytes, 0, bytes.size)
            return ByteArray(32).also { hmac.doFinal(it, 0) }
        } finally { key.fill(0) }
    }

    private fun startProtected(result: Pending) {
        ensure(sending == null, "SEQUENCE")
        sending = auth { hpke().setupAuthS(X25519PublicKeyParameters(requireNotNull(peerHpke)), hpkeInfo(true), requireNotNull(hpkePair)) }
        secret?.fill(0); secret = null
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
            phase = "WAIT_APPROVAL"
            result.events += DirectTransferEvent("authenticated")
            return
        }
        ensure(authenticated, "SEQUENCE")
        if (type == "approved") {
            fields(message, "type")
            ensure(outgoing != sender && phase == "WAIT_APPROVAL", "SEQUENCE")
            approved = true
            phase = "READY"
            result.events += DirectTransferEvent("approved")
            return
        }
        ensure(approved, "SEQUENCE")
        when (type) {
            "metadata" -> {
                fields(message, "type", "vaultName")
                ensure(phase == "READY" && !(if (outgoing) localMetadata else remoteMetadata), "SEQUENCE")
                name(string(message, "vaultName"), 256, 1024)
                if (outgoing) localMetadata = true else remoteMetadata = true
            }
            "offer" -> {
                fields(message, "type", "scope", "byteCount", "passwordCount", "noteCount", "sha256")
                ensure(outgoing == sender && phase == "READY" && localMetadata && remoteMetadata && offer == null, "SEQUENCE")
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
                if (!sender) {
                    val proposal = requireNotNull(offer)
                    val bytes = number(proposal, "byteCount")
                    val records = number(proposal, "passwordCount") + number(proposal, "noteCount")
                    memory.checkAvailable(bytes + BackupMemoryBudget.textPeak(bytes) + records * BackupMemoryBudget.RECORD_BYTES)
                    memory.reserve(bytes)
                    buffer = ByteArray(bytes.toInt())
                }
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

    private fun identity(type: String): Map<String, Any?> = mapOf("type" to type, "version" to 2L,
        "session" to session, "device" to deviceId, "name" to deviceName,
        "hpke" to b64(publicKey(requireNotNull(hpkePair))), "suite" to SRP_SUITE)

    private fun sameSession(message: Map<String, Any?>) { ensure(string(message, "session") == session, "SEQUENCE") }

    private fun hpkeInfo(outgoing: Boolean): ByteArray {
        val origin = if (outgoing) deviceId else peerId
        val target = if (outgoing) peerId else deviceId
        val direction = if (outgoing == sender) "SENDER_TO_RECEIVER" else "RECEIVER_TO_SENDER"
        return "CANGOO_DIRECT_HPKE_V2|$session|$origin|$target|$direction|${hex(requireNotNull(binding))}".toByteArray(Charsets.US_ASCII)
    }

    private fun aad(seq: Long, enc: ByteArray, outgoing: Boolean): ByteArray {
        val prefix = "CANGOO_DIRECT_FRAME_V2|".toByteArray(Charsets.US_ASCII)
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
        hpkePair = null; peerHpke = null
        password?.fill(0); password = null
        srpServer = null; srpB = null
        srpSalt?.fill(0); srpSalt = null
        expectedProof?.fill(0); expectedProof = null
        transcript.clear(); binding = null
        sending = null; receiving = null; receivingEnc = null
        buffer?.fill(0); buffer = null
        frameBuffer.fill(0); frameUsed = 0; frameSize = 0
        digest?.reset(); digest = null
        offer = null; authenticated = false; approved = false
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
            throw DirectTransferException(if (error is BackupProtocolException && error.problem == BackupProblem.MEMORY) "MEMORY"
                else (error as? DirectTransferException)?.code ?: "INVALID")
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
        private const val SRP_SUITE = "srp6a-3072-sha256"
        private val SRP_IDENTITY = "CANGOO_DIRECT_PAIR_V2".toByteArray(Charsets.US_ASCII)
        private val SRP_GROUP = SRP6StandardGroups.rfc5054_3072

        private fun unsigned(value: BigInteger) = BigIntegers.asUnsignedByteArray(value)
        private fun padded(value: BigInteger) = BigIntegers.asUnsignedByteArray(384, value)
        private fun srpWire(value: BigInteger) = b64(padded(value))
        private fun srpPublic(text: String): BigInteger = BigInteger(1, unbase64(text, 384)).also {
            ensure(it.signum() > 0 && it < SRP_GROUP.n, "AUTH")
        }
        private fun srpProof(a: BigInteger, b: BigInteger, salt: ByteArray, key: ByteArray): ByteArray {
            // 沿pysrp 1.0.22的证明编码；BC默认M1/M2与此格式不同。
            val nHash = sha256(unsigned(SRP_GROUP.n))
            val gHash = sha256(padded(SRP_GROUP.g))
            val groupHash = ByteArray(32) { (nHash[it].toInt() xor gHash[it].toInt()).toByte() }
            return sha256(groupHash + sha256(SRP_IDENTITY) + salt + unsigned(a) + unsigned(b) + key)
        }

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
        private fun unbase64(value: String, size: Int = 32): ByteArray {
            ensure(value.length == (size * 8 + 5) / 6)
            val bytes = try { Base64.getDecoder().decode(value) } catch (_: IllegalArgumentException) { fail("INVALID") }
            ensure(bytes.size == size && b64(bytes) == value)
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
        private fun hkdf(secret: ByteArray, info: String, count: Int, salt: ByteArray? = null): ByteArray {
            val generator = HKDFBytesGenerator(SHA256Digest())
            generator.init(HKDFParameters(secret, salt, info.toByteArray(Charsets.UTF_8)))
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
