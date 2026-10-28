package app.cangoo.android.ui

import android.content.Context
import android.os.Build
import android.os.SystemClock
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import app.cangoo.android.R
import app.cangoo.android.data.BackupScope
import app.cangoo.android.data.BackupTransferSnapshot
import app.cangoo.android.data.BackupProblem
import app.cangoo.android.data.BackupProtocolException
import app.cangoo.android.data.BackupStoreException
import app.cangoo.android.data.BackupStoreProblem
import app.cangoo.android.data.DirectTransferException
import app.cangoo.android.data.DirectTransferResult
import app.cangoo.android.data.DirectTransferSession
import app.cangoo.android.data.VaultError
import app.cangoo.android.data.VaultException
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.NonCancellable
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.withContext
import java.io.EOFException
import java.io.IOException
import java.security.MessageDigest
import java.security.SecureRandom
import java.util.UUID

internal enum class DirectTransferRole { SENDER, RECEIVER }
internal enum class DirectTransferSettings { APPLICATION, BLUETOOTH }
internal enum class DirectTransferPhase {
    CONFIG, DISCOVERING, WAITING, PAIRING_CODE, CONNECTING, WAIT_APPROVAL, PREPARING, REVIEW, TRANSFERRING, VERIFYING, RECEIVED, SENT, FAILED,
}

internal data class DirectTransferUiState(
    val localVaultName: String,
    val role: DirectTransferRole = DirectTransferRole.SENDER,
    val channel: DirectTransferChannel = DirectTransferChannel.LAN,
    val scope: BackupScope = BackupScope.ALL,
    val phase: DirectTransferPhase = DirectTransferPhase.CONFIG,
    val peers: List<DirectTransferPeer> = emptyList(),
    val peersSelectable: Boolean = false,
    val peerName: String? = null,
    val peerVaultName: String? = null,
    val pairingCode: String = "",
    val accepted: Boolean = false,
    val offerPrepared: Boolean = false,
    val totalBytes: Long? = null,
    val completedBytes: Long = 0,
    val passwordCount: Int? = null,
    val noteCount: Int? = null,
    val error: UiText = UiText.Empty,
    val settings: DirectTransferSettings? = null,
    val localAddresses: List<String> = emptyList(),
    val manualAddress: String = "",
    val manualAddressExpanded: Boolean = false,
    val manualSearching: Boolean = false,
    val manualError: UiText = UiText.Empty,
) {
    override fun toString() = "DirectTransferUiState(内容已隐藏)"
}

// 通道和协议只属于当前库的一次任务；界面只消费非秘密阶段和已认证元信息。
internal class DirectTransferController(
    private val context: Context,
    private val scope: CoroutineScope,
    localVaultName: String,
    private val qualified: () -> Boolean,
    private val interact: () -> Boolean,
    private val transferHold: (Boolean) -> Boolean,
    private val exportSnapshot: suspend (BackupScope, () -> Boolean) -> BackupTransferSnapshot,
    private val receiveSnapshot: suspend (ByteArray, BackupScope, Int, Int, () -> Boolean) -> Unit,
    private val received: () -> Unit,
) {
    var state by mutableStateOf(DirectTransferUiState(localVaultName))
        private set
    private var closed = false
    private var active: Owner? = null
    val hasActiveTask: Boolean get() = active != null

    private class Owner(val role: DirectTransferRole, val channel: DirectTransferChannel, val deviceId: String,
                        val transport: DirectTransferTransport) {
        @Volatile var revoked = false
        var connection: DirectTransferConnection? = null
        var protocol: DirectTransferSession? = null
        var serial = Mutex()
        var pairingCode = ""
        var selectedPeer: DirectTransferPeer? = null
        var pairingDeadline = 0L
        var authDeadline = 0L
        var authenticatedOnce = false
        val candidates = mutableSetOf<Candidate>()
        val jobs = mutableSetOf<Job>()
        var snapshot: BackupTransferSnapshot? = null
        var hold = false
        var expectedPeerId: String? = null
        var offerHash: String? = null
        var offerScope = BackupScope.ALL
        var passwordCount = 0
        var noteCount = 0
        var totalBytes = 0L
        var lastProgress = SystemClock.elapsedRealtime()
        var startedAt: Long? = null
        var waitingForValidation = false
        var localVerified = false
        var displayedPercent = -1
    }

    private class Candidate(val connection: DirectTransferConnection, val protocol: DirectTransferSession) {
        val serial = Mutex()
        var helloReceived = false
        var job: Job? = null
        var timeout: Job? = null
    }

    fun configure(role: DirectTransferRole? = null, channel: DirectTransferChannel? = null, scope: BackupScope? = null) {
        if (!interact() || closed || state.manualSearching) return
        if (state.phase == DirectTransferPhase.CONFIG) state = state.copy(role = role ?: state.role, channel = channel ?: state.channel)
        else if (role == null && channel == null && scope != null && state.phase == DirectTransferPhase.REVIEW &&
            state.role == DirectTransferRole.SENDER && !state.offerPrepared) state = state.copy(scope = scope)
    }

    fun start() {
        if (!interact() || closed || state.manualSearching || state.phase !in setOf(DirectTransferPhase.CONFIG, DirectTransferPhase.DISCOVERING)) return
        releaseOwner()
        val owner = Owner(state.role, state.channel, UUID.randomUUID().toString().replace("-", ""), DirectTransferTransport(context, state.channel))
        active = owner
        if (owner.role == DirectTransferRole.RECEIVER) {
            owner.pairingCode = SecureRandom().nextInt(100_000_000).toString().padStart(8, '0')
            owner.pairingDeadline = SystemClock.elapsedRealtime() + PAIRING_TIMEOUT
            work(owner) {
                delay(PAIRING_TIMEOUT)
                if (current(owner) && owner.protocol == null) finish(owner, DirectTransferPhase.FAILED, UiText(R.string.transfer_error_timeout))
            }
        }
        state = state.copy(pairingCode = owner.pairingCode, phase = if (owner.role == DirectTransferRole.SENDER) DirectTransferPhase.DISCOVERING else DirectTransferPhase.WAITING,
            peers = emptyList(), peersSelectable = owner.role == DirectTransferRole.SENDER, localAddresses = emptyList(),
            error = UiText.Empty, settings = null, manualError = UiText.Empty)
        work(owner) {
            if (owner.role == DirectTransferRole.SENDER) {
                val peers = owner.transport.discover { found ->
                    scope.launch { if (current(owner) && state.phase == DirectTransferPhase.DISCOVERING) state = state.copy(peers = found) }
                }
                if (current(owner) && state.phase == DirectTransferPhase.DISCOVERING) state = state.copy(peers = peers)
            } else {
                owner.transport.listen(owner.deviceId, deviceName(), onListening = { addresses ->
                    scope.launch { if (current(owner) && state.phase == DirectTransferPhase.WAITING) state = state.copy(localAddresses = addresses) }
                }, onCandidate = { connection ->
                    scope.launch { acceptCandidate(owner, connection) }
                })
            }
        }
    }

    private fun manualEditable() = !closed && !state.manualSearching && state.channel == DirectTransferChannel.LAN &&
        state.role == DirectTransferRole.SENDER && state.phase in setOf(DirectTransferPhase.CONFIG, DirectTransferPhase.DISCOVERING)

    fun toggleManualAddress() {
        if (manualEditable() && interact()) state = state.copy(manualAddressExpanded = !state.manualAddressExpanded)
    }

    fun updateManualAddress(value: String) {
        if (manualEditable() && interact()) state = state.copy(manualAddress = value.take(64), manualError = UiText.Empty)
    }

    fun findManualAddress() {
        if (!manualEditable() || !interact()) return
        val address = DirectTransferDiscovery.parseAddress(state.manualAddress)
        if (address == null) { state = state.copy(manualError = UiText(R.string.transfer_manual_invalid)); return }
        val local = try { DirectTransferDiscovery.localAddresses() } catch (_: Exception) {
            state = state.copy(manualError = UiText(R.string.transfer_error_connection)); return
        }
        if (!DirectTransferDiscovery.isLocalPeer(address, local)) {
            state = state.copy(manualError = UiText(R.string.transfer_manual_not_local)); return
        }
        releaseOwner()
        val owner = Owner(DirectTransferRole.SENDER, DirectTransferChannel.LAN, UUID.randomUUID().toString().replace("-", ""),
            DirectTransferTransport(context, DirectTransferChannel.LAN))
        active = owner
        state = state.copy(manualSearching = true, peersSelectable = false, manualError = UiText.Empty, error = UiText.Empty, settings = null)
        work(owner) {
            val peer = owner.transport.discoverAddress(address)
            if (!current(owner)) return@work
            if (peer == null) {
                releaseOwner()
                state = state.copy(manualSearching = false, manualError = UiText(R.string.transfer_manual_not_found))
            } else {
                state = state.copy(manualSearching = false)
                choosePeer(owner, peer)
            }
        }
    }

    fun selectPeer(peer: DirectTransferPeer) {
        val owner = active ?: return
        if (!interact() || !current(owner) || !state.peersSelectable || state.manualSearching ||
            state.phase != DirectTransferPhase.DISCOVERING || state.peers.none { it === peer }) return
        choosePeer(owner, peer)
    }

    private fun choosePeer(owner: Owner, peer: DirectTransferPeer) {
        if (peer.legacy) { finish(owner, DirectTransferPhase.FAILED, UiText(R.string.transfer_upgrade_required)); return }
        owner.selectedPeer = peer
        owner.expectedPeerId = peer.id.takeIf { owner.channel == DirectTransferChannel.LAN }
        state = state.copy(phase = DirectTransferPhase.PAIRING_CODE, peerName = peer.displayName, peersSelectable = false,
            peers = emptyList(), pairingCode = "", error = UiText.Empty)
    }

    fun updatePairingCode(value: String) {
        if (!interact() || closed || state.phase != DirectTransferPhase.PAIRING_CODE) return
        val digits = value.replace(" ", "")
        if (digits.length <= 8 && digits.all { it in '0'..'9' }) state = state.copy(pairingCode = digits, error = UiText.Empty)
    }

    fun copyPairingCode(publish: (String, () -> Boolean) -> Unit) {
        if (!interact()) return
        recheckDeadline()
        val owner = active ?: return
        fun allowed() = current(owner) && owner.role == DirectTransferRole.RECEIVER &&
            state.phase == DirectTransferPhase.WAITING && owner.protocol == null &&
            SystemClock.elapsedRealtime() < owner.pairingDeadline &&
            owner.pairingCode.length == 8 && owner.pairingCode.all { it in '0'..'9' }
        if (allowed()) publish(owner.pairingCode, ::allowed)
    }

    fun connectWithCode() {
        val owner = active ?: return
        if (!interact() || !current(owner) || state.phase != DirectTransferPhase.PAIRING_CODE ||
            state.pairingCode.length != 8 || state.pairingCode.any { it !in '0'..'9' }) return
        owner.pairingCode = state.pairingCode
        state = state.copy(phase = DirectTransferPhase.CONNECTING, pairingCode = "", error = UiText.Empty)
        work(owner) { connected(owner, owner.transport.connect(requireNotNull(owner.selectedPeer), CONNECT_TIMEOUT)) }
    }

    fun approvePeer() {
        val owner = active ?: return
        if (!interact() || !current(owner) || owner.role != DirectTransferRole.RECEIVER || state.phase != DirectTransferPhase.WAIT_APPROVAL) return
        work(owner) { owner.serial.withLock {
            if (current(owner) && owner.protocol?.approved == false) result(owner, requireNotNull(owner.protocol).approvePeer())
        } }
    }

    fun rejectPeer() {
        if (!interact()) return
        active?.let { finish(it, DirectTransferPhase.FAILED, UiText(R.string.transfer_error_cancelled)) }
    }

    fun prepareOffer() {
        val owner = active ?: return
        if (!interact() || !current(owner) || owner.role != DirectTransferRole.SENDER || state.phase != DirectTransferPhase.REVIEW ||
            state.peerVaultName == null || state.offerPrepared) return
        owner.offerScope = state.scope
        state = state.copy(phase = DirectTransferPhase.PREPARING)
        work(owner) {
            // 即使取消已到达，也先接回数据层返回对象的清理责任。
            val snapshot = withContext(NonCancellable) { exportSnapshot(owner.offerScope) { current(owner) } }
            if (!current(owner)) { snapshot.bytes.fill(0); return@work }
            owner.snapshot = snapshot
            val digest = withContext(Dispatchers.Default) { MessageDigest.getInstance("SHA-256").digest(snapshot.bytes).joinToString("") { "%02x".format(it) } }
            if (!current(owner)) return@work
            owner.offerHash = digest
            owner.passwordCount = snapshot.passwordCount
            owner.noteCount = snapshot.noteCount
            owner.totalBytes = snapshot.bytes.size.toLong()
            state = state.copy(phase = DirectTransferPhase.REVIEW, offerPrepared = true,
                totalBytes = owner.totalBytes, passwordCount = owner.passwordCount, noteCount = owner.noteCount)
            owner.serial.withLock {
                result(owner, requireNotNull(owner.protocol).sendMessage(mapOf("type" to "offer", "scope" to owner.offerScope.name,
                    "byteCount" to owner.totalBytes, "passwordCount" to owner.passwordCount, "noteCount" to owner.noteCount, "sha256" to digest)))
            }
        }
    }

    private fun startTransfer(owner: Owner) {
        if (!current(owner) || owner.role != DirectTransferRole.SENDER || state.phase != DirectTransferPhase.REVIEW ||
            !state.offerPrepared || !state.accepted) return
        if (!beginHold(owner)) return
        work(owner) {
            val snapshot = requireNotNull(owner.snapshot)
            owner.serial.withLock { result(owner, requireNotNull(owner.protocol).sendMessage(mapOf("type" to "start", "sha256" to owner.offerHash))) }
            var offset = 0
            while (current(owner) && offset < snapshot.bytes.size) {
                val end = minOf(offset + CHUNK_SIZE, snapshot.bytes.size)
                val chunk = snapshot.bytes.copyOfRange(offset, end)
                try { owner.serial.withLock { result(owner, requireNotNull(owner.protocol).sendChunk(chunk)) } }
                finally { chunk.fill(0) }
                offset = end
                progress(owner, offset.toLong())
            }
            if (!current(owner)) return@work
            owner.serial.withLock { result(owner, requireNotNull(owner.protocol).sendMessage(mapOf("type" to "finish", "sha256" to owner.offerHash))) }
            owner.waitingForValidation = true
            snapshot.bytes.fill(0)
            owner.snapshot = null
            if (current(owner)) state = state.copy(phase = DirectTransferPhase.VERIFYING)
        }
    }

    fun recheckDeadline() {
        val owner = active ?: return
        if (current(owner) && owner.role == DirectTransferRole.RECEIVER && owner.protocol == null &&
            SystemClock.elapsedRealtime() >= owner.pairingDeadline) finish(owner, DirectTransferPhase.FAILED, UiText(R.string.transfer_error_timeout))
    }

    fun permissionDenied() {
        if (closed || !qualified()) return
        releaseOwner()
        state = state.copy(phase = DirectTransferPhase.FAILED, pairingCode = "", peersSelectable = false, error = UiText(R.string.transfer_error_permissions),
            settings = DirectTransferSettings.APPLICATION)
    }

    fun settingsUnavailable() {
        if (closed || !qualified() || state.phase != DirectTransferPhase.FAILED) return
        state = state.copy(error = UiText(R.string.system_settings_failed))
    }

    fun reset() {
        if (!interact() || closed) return
        releaseOwner()
        state = DirectTransferUiState(state.localVaultName, state.role, state.channel, state.scope,
            manualAddress = state.manualAddress, manualAddressExpanded = state.manualAddressExpanded)
    }

    fun close() {
        if (closed) return
        closed = true
        releaseOwner()
        state = DirectTransferUiState(state.localVaultName)
    }

    private suspend fun connected(owner: Owner, connection: DirectTransferConnection) {
        if (!current(owner)) { connection.close(); return }
        owner.connection = connection
        owner.authDeadline = SystemClock.elapsedRealtime() + AUTH_TIMEOUT
        owner.protocol = DirectTransferSession(owner.role.name, owner.deviceId, deviceName(), owner.pairingCode)
        owner.pairingCode = ""
        state = state.copy(phase = DirectTransferPhase.CONNECTING, peers = emptyList(), peersSelectable = false)
        val timeout = scope.launch {
            delay(AUTH_TIMEOUT)
            if (current(owner) && !owner.authenticatedOnce) finish(owner, DirectTransferPhase.FAILED, UiText(R.string.transfer_error_timeout))
        }
        owner.jobs += timeout
        owner.serial.withLock { result(owner, requireNotNull(owner.protocol).begin()) }
        readFrames(owner, connection) { frame -> owner.serial.withLock {
            if (current(owner)) result(owner, requireNotNull(owner.protocol).receive(frame))
        } }
    }

    private fun acceptCandidate(owner: Owner, connection: DirectTransferConnection) {
        recheckDeadline()
        if (!current(owner) || owner.protocol != null || SystemClock.elapsedRealtime() >= owner.pairingDeadline) { connection.close(); return }
        val candidate = Candidate(connection, DirectTransferSession(owner.role.name, owner.deviceId, deviceName(), owner.pairingCode))
        owner.candidates += candidate
        candidate.timeout = scope.launch {
            delay((HELLO_TIMEOUT - (System.nanoTime() - connection.openedAtNanos) / 1_000_000L).coerceAtLeast(0))
            if (!candidate.helloReceived) closeCandidate(owner, candidate)
            else {
                delay((AUTH_TIMEOUT - (System.nanoTime() - connection.openedAtNanos) / 1_000_000L).coerceAtLeast(0))
                if (owner.protocol !== candidate.protocol) closeCandidate(owner, candidate)
            }
        }
        candidate.job = scope.launch {
            try {
                candidate.serial.withLock { candidateResult(owner, candidate, candidate.protocol.begin()) }
                readFrames(owner, connection) { frame -> candidate.serial.withLock {
                    if (current(owner) && candidate in owner.candidates) {
                        val value = candidate.protocol.receive(frame)
                        if (owner.protocol === candidate.protocol) result(owner, value) else candidateResult(owner, candidate, value)
                    }
                } }
            } catch (error: Exception) {
                if (error is CancellationException) throw error
                if (current(owner) && owner.protocol === candidate.protocol) handleFailure(owner, error)
            } finally {
                if (owner.protocol !== candidate.protocol) closeCandidate(owner, candidate)
            }
        }
        val job = requireNotNull(candidate.job)
        owner.jobs += job
        job.invokeOnCompletion { scope.launch { owner.jobs.remove(job) } }
    }

    private suspend fun candidateResult(owner: Owner, candidate: Candidate, value: DirectTransferResult) {
        try {
            if (value.events.any { it.type == "peer" }) {
                if (System.nanoTime() - candidate.connection.openedAtNanos >= HELLO_TIMEOUT * 1_000_000L) { closeCandidate(owner, candidate); return }
                candidate.helloReceived = true
            }
            for (frame in value.outbound) {
                if (!current(owner) || candidate !in owner.candidates) return
                withContext(Dispatchers.IO) { candidate.connection.output.write(frame); candidate.connection.output.flush() }
            }
            for (event in value.events) when (event.type) {
                "authenticated" -> {
                    if (!current(owner) || owner.protocol != null || SystemClock.elapsedRealtime() >= owner.pairingDeadline ||
                        System.nanoTime() - candidate.connection.openedAtNanos >= AUTH_TIMEOUT * 1_000_000L) { closeCandidate(owner, candidate); return }
                    owner.protocol = candidate.protocol
                    owner.authenticatedOnce = true
                    owner.connection = candidate.connection
                    owner.serial = candidate.serial
                    owner.pairingCode = ""
                    candidate.timeout?.cancel()
                    owner.transport.stopListening()
                    owner.candidates.filter { it !== candidate }.toList().forEach { closeCandidate(owner, it) }
                    state = state.copy(phase = DirectTransferPhase.WAIT_APPROVAL, pairingCode = "", peerName = candidate.protocol.peerName,
                        peers = emptyList(), peersSelectable = false, localAddresses = emptyList())
                }
                "cancelled" -> closeCandidate(owner, candidate)
            }
        } finally { value.outbound.forEach { it.fill(0) } }
    }

    private fun closeCandidate(owner: Owner, candidate: Candidate) {
        if (!owner.candidates.remove(candidate)) return
        candidate.connection.close()
        candidate.protocol.close()
        candidate.timeout?.cancel()
        candidate.job?.cancel()
    }

    private suspend fun readFrames(owner: Owner, connection: DirectTransferConnection, consume: suspend (ByteArray) -> Unit) {
        val buffer = ByteArray(CHUNK_SIZE)
        try {
            while (current(owner)) {
                val count = withContext(Dispatchers.IO) { connection.input.read(buffer) }
                if (count < 0) throw EOFException()
                if (count == 0) continue
                val frame = buffer.copyOf(count)
                try { consume(frame) } finally { frame.fill(0) }
            }
        } finally { buffer.fill(0) }
    }

    private suspend fun result(owner: Owner, value: DirectTransferResult) {
        try {
            for (frame in value.outbound) {
                if (!current(owner)) return
                withContext(Dispatchers.IO) {
                    val output = requireNotNull(owner.connection).output
                    var offset = 0
                    while (offset < frame.size && current(owner)) {
                        val length = minOf(CHUNK_SIZE, frame.size - offset)
                        output.write(frame, offset, length)
                        offset += length
                    }
                    output.flush()
                }
            }
            for (event in value.events) {
                if (!current(owner)) { event.data?.fill(0); continue }
                when (event.type) {
                    "peer" -> {
                        if (owner.expectedPeerId != null && owner.expectedPeerId != owner.protocol?.peerId) {
                            finish(owner, DirectTransferPhase.FAILED, UiText(R.string.transfer_error_authentication)); return
                        }
                        state = state.copy(peerName = owner.protocol?.peerName)
                    }
                    "authenticated" -> {
                        if (SystemClock.elapsedRealtime() >= owner.authDeadline) {
                            finish(owner, DirectTransferPhase.FAILED, UiText(R.string.transfer_error_timeout)); return
                        }
                        owner.authenticatedOnce = true
                        state = state.copy(phase = DirectTransferPhase.WAIT_APPROVAL, pairingCode = "")
                    }
                    "approved" -> {
                        state = state.copy(phase = DirectTransferPhase.REVIEW)
                        result(owner, requireNotNull(owner.protocol).sendMessage(mapOf("type" to "metadata", "vaultName" to state.localVaultName)))
                    }
                    "metadata" -> state = state.copy(peerVaultName = event.fields["vaultName"] as String)
                    "offer" -> {
                        owner.offerScope = BackupScope.valueOf(event.fields["scope"] as String)
                        owner.offerHash = event.fields["sha256"] as String
                        owner.totalBytes = (event.fields["byteCount"] as Number).toLong()
                        owner.passwordCount = (event.fields["passwordCount"] as Number).toInt()
                        owner.noteCount = (event.fields["noteCount"] as Number).toInt()
                        state = state.copy(phase = DirectTransferPhase.REVIEW, offerPrepared = true, scope = owner.offerScope,
                            totalBytes = owner.totalBytes, passwordCount = owner.passwordCount, noteCount = owner.noteCount, accepted = true)
                        result(owner, requireNotNull(owner.protocol).sendMessage(mapOf("type" to "accept", "sha256" to owner.offerHash)))
                    }
                    "accept" -> {
                        state = state.copy(accepted = true)
                        startTransfer(owner)
                    }
                    "start" -> if (!beginHold(owner)) return
                    "progress" -> progress(owner, (event.fields["bytes"] as Number).toLong())
                    "complete" -> {
                        owner.waitingForValidation = true
                        state = state.copy(phase = DirectTransferPhase.VERIFYING, completedBytes = owner.totalBytes)
                        val encoded = requireNotNull(event.data)
                        // 数据层消费此唯一缓冲，所有完成/取消路径由它擦除，控制器不并发清零。
                        withContext(NonCancellable) {
                            receiveSnapshot(encoded, owner.offerScope, owner.passwordCount, owner.noteCount) { current(owner) }
                        }
                        if (!current(owner)) return
                        owner.localVerified = true
                        state = state.copy(phase = DirectTransferPhase.RECEIVED)
                        if (owner.hold) { owner.hold = false; transferHold(false) }
                        if (!current(owner)) return
                        received()
                        if (!current(owner)) return
                        try { result(owner, requireNotNull(owner.protocol).sendReceived()) }
                        finally { if (current(owner)) finish(owner, DirectTransferPhase.RECEIVED) }
                    }
                    "received" -> finish(owner, DirectTransferPhase.SENT)
                    "cancelled" -> finish(owner, DirectTransferPhase.FAILED, UiText(R.string.transfer_error_cancelled))
                }
            }
        } finally { value.outbound.forEach { it.fill(0) } }
    }

    private fun beginHold(owner: Owner): Boolean {
        if (!current(owner) || owner.hold) return false
        if (!transferHold(true)) { finish(owner, DirectTransferPhase.FAILED, UiText(R.string.transfer_error_session)); return false }
        owner.hold = true
        owner.startedAt = SystemClock.elapsedRealtime()
        owner.lastProgress = owner.startedAt!!
        state = state.copy(phase = DirectTransferPhase.TRANSFERRING, completedBytes = 0)
        work(owner) {
            while (current(owner)) {
                delay(1000)
                val now = SystemClock.elapsedRealtime()
                if (now - requireNotNull(owner.startedAt) >= TRANSFER_TIMEOUT ||
                    !owner.waitingForValidation && now - owner.lastProgress >= PROGRESS_TIMEOUT) {
                    finish(owner, DirectTransferPhase.FAILED, UiText(R.string.transfer_error_timeout)); return@work
                }
            }
        }
        return true
    }

    private fun progress(owner: Owner, bytes: Long) {
        if (!current(owner)) return
        owner.lastProgress = SystemClock.elapsedRealtime()
        val percent = (bytes * 100 / owner.totalBytes.coerceAtLeast(1)).toInt()
        if (percent != owner.displayedPercent) {
            owner.displayedPercent = percent
            state = state.copy(completedBytes = bytes)
        }
    }

    private fun work(owner: Owner, operation: suspend () -> Unit) {
        val job = scope.launch {
            try { if (current(owner)) operation() }
            catch (cancelled: CancellationException) { throw cancelled }
            catch (error: Exception) { if (current(owner)) handleFailure(owner, error) }
        }
        owner.jobs.add(job)
        job.invokeOnCompletion { scope.launch { owner.jobs.remove(job) } }
    }

    private fun handleFailure(owner: Owner, error: Exception) {
        if (owner.role == DirectTransferRole.SENDER && !owner.authenticatedOnce &&
            (error is DirectTransferException && error.code == "AUTH" || error is IOException && error !is DirectTransferTransportException)) {
            retryPairing(owner)
            return
        }
        val message = when (error) {
            is BackupProtocolException -> when (error.problem) {
                BackupProblem.LIMIT -> R.string.transfer_error_limit
                BackupProblem.MEMORY -> R.string.backup_error_memory
                BackupProblem.AUTHENTICATION -> R.string.transfer_error_authentication
                BackupProblem.IO -> R.string.transfer_error_io
                else -> R.string.transfer_error_format
            }
            is BackupStoreException -> if (error.problem == BackupStoreProblem.LIMIT) R.string.transfer_error_limit
                else R.string.transfer_error_session
            is VaultException -> if (error.code == VaultError.SESSION_CLOSED) R.string.transfer_error_session else R.string.transfer_error_io
            is DirectTransferException -> when (error.code) {
                "AUTH" -> R.string.transfer_error_authentication
                "UPGRADE_REQUIRED" -> R.string.transfer_upgrade_required
                "LIMIT" -> R.string.transfer_error_limit
                "MEMORY" -> R.string.backup_error_memory
                else -> R.string.transfer_error_format
            }
            is DirectTransferTransportException -> when (error.problem) {
                DirectTransferTransportProblem.TIMEOUT -> R.string.transfer_error_timeout
                DirectTransferTransportProblem.PERMISSION -> R.string.transfer_error_permissions
                DirectTransferTransportProblem.ADDRESS_NOT_LOCAL -> R.string.transfer_manual_not_local
                DirectTransferTransportProblem.BLUETOOTH_UNAVAILABLE, DirectTransferTransportProblem.BLUETOOTH_DISABLED,
                DirectTransferTransportProblem.NOT_PAIRED -> R.string.transfer_error_bluetooth
                else -> R.string.transfer_error_connection
            }
            is IOException -> if (owner.waitingForValidation && owner.role == DirectTransferRole.SENDER) R.string.transfer_error_receipt
                else R.string.transfer_error_connection
            else -> R.string.transfer_error_io
        }
        val settings = when (message) {
            R.string.transfer_error_permissions -> DirectTransferSettings.APPLICATION
            R.string.transfer_error_bluetooth -> DirectTransferSettings.BLUETOOTH
            else -> null
        }
        if (state.manualSearching) {
            releaseOwner()
            state = state.copy(manualSearching = false, manualError = UiText(message))
        } else finish(owner, DirectTransferPhase.FAILED, UiText(message), settings)
    }

    private fun retryPairing(owner: Owner) {
        val peer = owner.selectedPeer ?: return
        releaseOwner()
        val retry = Owner(owner.role, owner.channel, UUID.randomUUID().toString().replace("-", ""), DirectTransferTransport(context, owner.channel))
        retry.selectedPeer = peer
        retry.expectedPeerId = owner.expectedPeerId
        active = retry
        state = state.copy(phase = DirectTransferPhase.PAIRING_CODE, pairingCode = "", error = UiText(R.string.transfer_pairing_retry))
    }

    private fun current(owner: Owner): Boolean = !closed && active === owner && !owner.revoked && qualified()

    private fun finish(owner: Owner, phase: DirectTransferPhase, error: UiText = UiText.Empty, settings: DirectTransferSettings? = null) {
        if (!current(owner)) return
        val completed = owner.localVerified || phase == DirectTransferPhase.RECEIVED
        state = state.copy(phase = if (completed) DirectTransferPhase.RECEIVED else phase,
            error = if (completed) UiText.Empty else error, peers = emptyList(), peersSelectable = false, pairingCode = "",
            settings = if (completed) null else settings)
        releaseOwner()
        if (completed && !closed && qualified()) received()
    }

    private fun releaseOwner() {
        val owner = active ?: return
        active = null
        owner.revoked = true
        owner.pairingCode = ""
        owner.candidates.toList().forEach { closeCandidate(owner, it) }
        owner.connection?.close()
        owner.transport.close()
        owner.protocol?.close()
        owner.snapshot?.bytes?.fill(0)
        owner.snapshot = null
        owner.jobs.toList().forEach { it.cancel() }
        if (owner.hold) { owner.hold = false; transferHold(false) }
    }

    private fun deviceName(): String {
        val value = Build.MODEL.orEmpty().filter { it.code !in 0..31 && it.code !in 127..159 && !it.isSurrogate() }.take(64)
        return value.ifEmpty { "Cangoo Android" }
    }

    private companion object {
        const val CHUNK_SIZE = 65_536
        const val CONNECT_TIMEOUT = 20_000L
        const val AUTH_TIMEOUT = 10_000L
        const val HELLO_TIMEOUT = 3_000L
        const val PAIRING_TIMEOUT = 600_000L
        const val PROGRESS_TIMEOUT = 30_000L
        const val TRANSFER_TIMEOUT = 1_800_000L
    }
}
