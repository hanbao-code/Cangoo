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
import java.util.UUID

internal enum class DirectTransferRole { SENDER, RECEIVER }
internal enum class DirectTransferSettings { APPLICATION, BLUETOOTH }
internal enum class DirectTransferPhase {
    CONFIG, DISCOVERING, WAITING, CONNECTING, SAS, PREPARING, REVIEW, TRANSFERRING, VERIFYING, RECEIVED, SENT, FAILED,
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
    val sas: List<Int> = emptyList(),
    val sasConfirmed: Boolean = false,
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
        val serial = Mutex()
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
        state = state.copy(phase = if (owner.role == DirectTransferRole.SENDER) DirectTransferPhase.DISCOVERING else DirectTransferPhase.WAITING,
            peers = emptyList(), peersSelectable = owner.role == DirectTransferRole.SENDER, localAddresses = emptyList(),
            error = UiText.Empty, settings = null, manualError = UiText.Empty)
        work(owner) {
            if (owner.role == DirectTransferRole.SENDER) {
                val peers = owner.transport.discover { found ->
                    scope.launch { if (current(owner) && state.phase == DirectTransferPhase.DISCOVERING) state = state.copy(peers = found) }
                }
                if (current(owner) && state.phase == DirectTransferPhase.DISCOVERING) state = state.copy(peers = peers)
            } else {
                val connection = owner.transport.accept(owner.deviceId, deviceName(), AUTH_TIMEOUT) { addresses ->
                    scope.launch { if (current(owner) && state.phase == DirectTransferPhase.WAITING) state = state.copy(localAddresses = addresses) }
                }
                connected(owner, connection)
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
                owner.expectedPeerId = peer.id
                state = state.copy(manualSearching = false, phase = DirectTransferPhase.CONNECTING, peerName = peer.displayName)
                connected(owner, owner.transport.connect(peer, CONNECT_TIMEOUT))
            }
        }
    }

    fun selectPeer(peer: DirectTransferPeer) {
        val owner = active ?: return
        if (!interact() || !current(owner) || !state.peersSelectable || state.manualSearching ||
            state.phase != DirectTransferPhase.DISCOVERING || state.peers.none { it === peer }) return
        owner.expectedPeerId = peer.id.takeIf { owner.channel == DirectTransferChannel.LAN }
        state = state.copy(phase = DirectTransferPhase.CONNECTING, peerName = peer.displayName)
        work(owner) { connected(owner, owner.transport.connect(peer, CONNECT_TIMEOUT)) }
    }

    fun confirmSas() {
        val owner = active ?: return
        if (!interact() || !current(owner) || state.phase != DirectTransferPhase.SAS || state.sasConfirmed) return
        state = state.copy(sasConfirmed = true)
        work(owner) { owner.serial.withLock { result(owner, requireNotNull(owner.protocol).confirmSas()) } }
    }

    fun rejectSas() {
        if (!interact()) return
        active?.let { finish(it, DirectTransferPhase.FAILED, UiText(R.string.transfer_code_mismatch)) }
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
            owner.serial.withLock {
                result(owner, requireNotNull(owner.protocol).sendMessage(mapOf("type" to "offer", "scope" to owner.offerScope.name,
                    "byteCount" to owner.totalBytes, "passwordCount" to owner.passwordCount, "noteCount" to owner.noteCount, "sha256" to digest)))
            }
            if (current(owner)) state = state.copy(phase = DirectTransferPhase.REVIEW, offerPrepared = true,
                totalBytes = owner.totalBytes, passwordCount = owner.passwordCount, noteCount = owner.noteCount)
        }
    }

    fun acceptTransfer() {
        val owner = active ?: return
        if (!interact() || !current(owner) || owner.role != DirectTransferRole.RECEIVER || state.phase != DirectTransferPhase.REVIEW ||
            !state.offerPrepared || state.accepted) return
        state = state.copy(accepted = true)
        work(owner) { owner.serial.withLock { result(owner, requireNotNull(owner.protocol).sendMessage(mapOf("type" to "accept", "sha256" to owner.offerHash))) } }
    }

    fun startTransfer() {
        val owner = active ?: return
        if (!interact() || !current(owner) || owner.role != DirectTransferRole.SENDER || state.phase != DirectTransferPhase.REVIEW ||
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

    fun permissionDenied() {
        if (closed || !qualified()) return
        releaseOwner()
        state = state.copy(phase = DirectTransferPhase.FAILED, peersSelectable = false, error = UiText(R.string.transfer_error_permissions),
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
        owner.protocol = DirectTransferSession(owner.role.name, owner.deviceId, deviceName())
        state = state.copy(phase = DirectTransferPhase.CONNECTING, peers = emptyList(), peersSelectable = false)
        work(owner) {
            delay(AUTH_TIMEOUT)
            if (current(owner) && owner.protocol?.authenticated != true) finish(owner, DirectTransferPhase.FAILED, UiText(R.string.transfer_error_timeout))
        }
        owner.serial.withLock { result(owner, requireNotNull(owner.protocol).begin()) }
        val buffer = ByteArray(CHUNK_SIZE)
        try {
            while (current(owner)) {
                val count = withContext(Dispatchers.IO) { connection.input.read(buffer) }
                if (count < 0) throw EOFException()
                if (count == 0) continue
                val frame = buffer.copyOf(count)
                try { owner.serial.withLock { if (current(owner)) result(owner, requireNotNull(owner.protocol).receive(frame)) } }
                finally { frame.fill(0) }
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
                    "sas" -> state = state.copy(phase = DirectTransferPhase.SAS, sas = owner.protocol?.sas.orEmpty())
                    "authenticated" -> {
                        state = state.copy(phase = DirectTransferPhase.REVIEW, sas = emptyList())
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
                            totalBytes = owner.totalBytes, passwordCount = owner.passwordCount, noteCount = owner.noteCount)
                    }
                    "accept" -> state = state.copy(accepted = true)
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
            catch (error: Exception) {
                if (current(owner)) {
                    val message = when (error) {
                        is BackupProtocolException -> when (error.problem) {
                            BackupProblem.LIMIT -> R.string.transfer_error_limit
                            BackupProblem.AUTHENTICATION -> R.string.transfer_error_authentication
                            BackupProblem.IO -> R.string.transfer_error_io
                            else -> R.string.transfer_error_format
                        }
                        is BackupStoreException -> if (error.problem == BackupStoreProblem.LIMIT) R.string.transfer_error_limit
                            else R.string.transfer_error_session
                        is VaultException -> if (error.code == VaultError.SESSION_CLOSED) R.string.transfer_error_session else R.string.transfer_error_io
                        is DirectTransferException -> when (error.code) {
                            "AUTH" -> R.string.transfer_error_authentication
                            "LIMIT" -> R.string.transfer_error_limit
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
            }
        }
        owner.jobs.add(job)
        job.invokeOnCompletion { scope.launch { owner.jobs.remove(job) } }
    }

    private fun current(owner: Owner): Boolean = !closed && active === owner && !owner.revoked && qualified()

    private fun finish(owner: Owner, phase: DirectTransferPhase, error: UiText = UiText.Empty, settings: DirectTransferSettings? = null) {
        if (!current(owner)) return
        val completed = owner.localVerified || phase == DirectTransferPhase.RECEIVED
        state = state.copy(phase = if (completed) DirectTransferPhase.RECEIVED else phase,
            error = if (completed) UiText.Empty else error, peers = emptyList(), peersSelectable = false, sas = emptyList(),
            settings = if (completed) null else settings)
        releaseOwner()
        if (completed && !closed && qualified()) received()
    }

    private fun releaseOwner() {
        val owner = active ?: return
        active = null
        owner.revoked = true
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
        const val AUTH_TIMEOUT = 180_000L
        const val PROGRESS_TIMEOUT = 30_000L
        const val TRANSFER_TIMEOUT = 1_800_000L
    }
}
