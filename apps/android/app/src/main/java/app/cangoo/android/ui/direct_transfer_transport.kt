package app.cangoo.android.ui

import android.Manifest
import android.annotation.SuppressLint
import android.bluetooth.BluetoothAdapter
import android.bluetooth.BluetoothDevice
import android.bluetooth.BluetoothManager
import android.content.Context
import android.content.pm.PackageManager
import android.net.wifi.WifiManager
import android.os.Build
import com.google.gson.Strictness
import com.google.gson.stream.JsonReader
import com.google.gson.stream.JsonToken
import com.google.gson.stream.JsonWriter
import java.io.Closeable
import java.io.FilterInputStream
import java.io.FilterOutputStream
import java.io.IOException
import java.io.InputStream
import java.io.OutputStream
import java.io.StringReader
import java.io.StringWriter
import java.net.DatagramPacket
import java.net.DatagramSocket
import java.net.Inet4Address
import java.net.InetAddress
import java.net.InetSocketAddress
import java.net.NetworkInterface
import java.net.ServerSocket
import java.net.Socket
import java.net.SocketTimeoutException
import java.nio.ByteBuffer
import java.nio.charset.CodingErrorAction
import java.security.SecureRandom
import java.util.Timer
import java.util.TimerTask
import java.util.UUID
import java.util.concurrent.CancellationException
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlin.coroutines.EmptyCoroutineContext
import kotlin.coroutines.resumeWithException

internal enum class DirectTransferChannel { LAN, BLUETOOTH }
internal enum class DirectTransferTransportProblem { CONNECTION, TIMEOUT, PERMISSION, BLUETOOTH_UNAVAILABLE, BLUETOOTH_DISABLED, NOT_PAIRED, ADDRESS_NOT_LOCAL }
internal class DirectTransferTransportException(val problem: DirectTransferTransportProblem) : IOException("设备通道失败：$problem")

internal class DirectTransferPeer internal constructor(
    val id: String,
    val displayName: String,
    val channel: DirectTransferChannel,
    internal val address: InetSocketAddress? = null,
    internal val bluetoothDevice: BluetoothDevice? = null,
    val legacy: Boolean = false,
) {
    val key: String get() = "$channel/$id"
}

internal class DirectTransferConnection internal constructor(
    val input: InputStream,
    val output: OutputStream,
    private val closeOwner: () -> Unit,
    val source: String = "",
    val openedAtNanos: Long = System.nanoTime(),
) : Closeable {
    override fun close() = closeOwner()
}

internal data class DirectTransferLanAddress(val address: Inet4Address, val prefixLength: Int, val broadcast: Inet4Address?)

// 每个面板任务独占通道；候选不是认证身份，协议和库授权由上层所有者核定。
internal class DirectTransferTransport(context: Context, private val channel: DirectTransferChannel) : Closeable {
    private val context = context.applicationContext
    private val lock = Any()
    private val resources = mutableListOf<Closeable>()
    private val peers = linkedMapOf<String, DirectTransferPeer>()
    private var closed = false
    private var expired = false
    private var connected = false
    private var operation = 0L
    private var activeOperation: Long? = null
    private var discoveryStopped = false
    private var discoverySocket: DatagramSocket? = null
    private var discoveryFinished: CompletableDeferred<Unit>? = null
    private val listeners = mutableListOf<Closeable>()
    private var listeningStopped = false
    private val admission = DirectTransferAdmission()

    // 发现和就绪回调在 IO 线程执行，调用方切回主线程后仍须核本次任务资格。
    suspend fun discover(onPeers: (List<DirectTransferPeer>) -> Unit = {}): List<DirectTransferPeer> =
        runOperation(null, connectionResult = false, discovery = true) {
            synchronized(lock) { peers.clear() }
            when (channel) {
                DirectTransferChannel.LAN -> discoverLan(onPeers)
                DirectTransferChannel.BLUETOOTH -> discoverBluetooth(onPeers)
            }
        }

    suspend fun discoverAddress(address: Inet4Address): DirectTransferPeer? =
        runOperation(null, connectionResult = false, discovery = true) {
            check(channel == DirectTransferChannel.LAN)
            discoverLan({}, address).firstOrNull()
        }

    suspend fun connect(peer: DirectTransferPeer, timeoutMillis: Long): DirectTransferConnection {
        try { stopDiscovery() } catch (error: CancellationException) { close(); throw error }
        return runOperation(timeoutMillis, connectionResult = true) {
            check(peer.channel == channel && !peer.legacy)
            when (channel) {
                DirectTransferChannel.LAN -> {
                    if (!DirectTransferDiscovery.isLocalPeer(requireNotNull(peer.address).address as Inet4Address,
                            DirectTransferDiscovery.localAddresses()))
                        throw DirectTransferTransportException(DirectTransferTransportProblem.ADDRESS_NOT_LOCAL)
                    val socket = own(Socket())
                    socket.connect(requireNotNull(peer.address), timeoutMillis.coerceAtMost(Int.MAX_VALUE.toLong()).toInt())
                    socket.tcpNoDelay = true
                    connection(socket.getInputStream(), socket.getOutputStream(), socket)
                }
                DirectTransferChannel.BLUETOOTH -> connectBluetooth(peer)
            }
        }
    }

    suspend fun listen(
        deviceId: String,
        displayName: String,
        onListening: (List<String>) -> Unit = {},
        onCandidate: (DirectTransferConnection) -> Unit,
    ): Unit = runOperation(null, connectionResult = false) {
        require(DirectTransferDiscovery.validId(deviceId) && DirectTransferDiscovery.validName(displayName))
        when (channel) {
            DirectTransferChannel.LAN -> acceptLan(deviceId, displayName, onListening, onCandidate)
            DirectTransferChannel.BLUETOOTH -> acceptBluetooth({ onListening(emptyList()) }, onCandidate)
        }
    }

    fun stopListening() {
        val closing = synchronized(lock) { listeningStopped = true; listeners.toList().also { resources.removeAll(it.toSet()); listeners.clear() } }
        closing.asReversed().forEach { runCatching { it.close() } }
    }

    override fun close() {
        val closing = synchronized(lock) {
            closed = true
            peers.clear()
            resources.toList().also { resources.clear() }
        }
        closing.asReversed().forEach { runCatching { it.close() } }
    }

    private suspend fun stopDiscovery() {
        val (socket, finished) = synchronized(lock) {
            val pending = discoveryFinished?.takeUnless { it.isCompleted } ?: return
            discoveryStopped = true
            discoverySocket to pending
        }
        socket?.close()
        finished.await()
        checkActive()
    }

    @OptIn(kotlinx.coroutines.ExperimentalCoroutinesApi::class)
    private suspend fun <T> runOperation(timeoutMillis: Long?, connectionResult: Boolean, discovery: Boolean = false, action: () -> T): T {
        require(timeoutMillis == null || timeoutMillis > 0)
        return suspendCancellableCoroutine { continuation ->
            var discoveryDone: CompletableDeferred<Unit>? = null
            val current = try {
                synchronized(lock) {
                    checkActive()
                    check(activeOperation == null && !connected)
                    if (discovery) {
                        discoveryStopped = false
                        discoveryDone = CompletableDeferred()
                        discoveryFinished = discoveryDone
                    }
                    (++operation).also { activeOperation = it }
                }
            } catch (error: Exception) {
                continuation.resumeWithException(error)
                return@suspendCancellableCoroutine
            }
            continuation.invokeOnCancellation { close() }
            Dispatchers.IO.dispatch(EmptyCoroutineContext) {
                val timer = timeoutMillis?.let { Timer("cangoo_transfer_deadline", true) }
                try {
                    if (timer != null) timer.schedule(object : TimerTask() {
                        override fun run() {
                            val timedOut = synchronized(lock) {
                                if (activeOperation != current || closed) false
                                else { expired = true; true }
                            }
                            if (timedOut) close()
                        }
                    }, requireNotNull(timeoutMillis))
                    checkActive()
                    val result = action()
                    synchronized(lock) {
                        checkActive()
                        connected = connectionResult
                        activeOperation = null
                    }
                    continuation.resume(result) { close() }
                } catch (error: Exception) {
                    val failure = when {
                        synchronized(lock) { expired } || error is SocketTimeoutException -> DirectTransferTransportException(DirectTransferTransportProblem.TIMEOUT)
                        synchronized(lock) { closed } -> CancellationException("设备连接已关闭")
                        error is DirectTransferTransportException || error is CancellationException -> error
                        error is SecurityException -> DirectTransferTransportException(DirectTransferTransportProblem.PERMISSION)
                        error is IOException -> DirectTransferTransportException(DirectTransferTransportProblem.CONNECTION)
                        else -> error
                    }
                    close()
                    continuation.resumeWithException(failure)
                } finally { timer?.cancel(); discoveryDone?.complete(Unit) }
            }
        }
    }

    private fun <T : Closeable> own(value: T): T {
        try {
            synchronized(lock) { checkActive(); resources += value }
            return value
        } catch (error: Exception) { runCatching { value.close() }; throw error }
    }

    private fun release(value: Closeable) {
        if (synchronized(lock) { resources.remove(value) }) value.close()
    }

    private fun checkActive() = synchronized(lock) {
        if (expired) throw SocketTimeoutException("设备连接等待超时")
        if (closed) throw CancellationException("设备连接已关闭")
    }

    private fun connection(input: InputStream, output: OutputStream, resource: Closeable, source: String = ""): DirectTransferConnection = DirectTransferConnection(
        object : FilterInputStream(input) {
            override fun read(): Int { checkActive(); return `in`.read().also { checkActive() } }
            override fun read(bytes: ByteArray, offset: Int, length: Int): Int {
                if (offset < 0 || length < 0 || offset > bytes.size - length) throw IndexOutOfBoundsException()
                checkActive()
                return `in`.read(bytes, offset, minOf(length, IO_CHUNK_BYTES)).also { checkActive() }
            }
            override fun close() = releaseConnection(resource, source)
        },
        object : FilterOutputStream(output) {
            override fun write(value: Int) { checkActive(); out.write(value); checkActive() }
            override fun write(bytes: ByteArray, offset: Int, length: Int) {
                if (offset < 0 || length < 0 || offset > bytes.size - length) throw IndexOutOfBoundsException()
                var position = offset
                while (position < offset + length) {
                    checkActive()
                    val count = minOf(IO_CHUNK_BYTES, offset + length - position)
                    out.write(bytes, position, count)
                    position += count
                }
                checkActive()
            }
            override fun flush() { checkActive(); out.flush(); checkActive() }
            override fun close() = releaseConnection(resource, source)
        },
        { releaseConnection(resource, source) }, source,
    )

    private fun releaseConnection(resource: Closeable, source: String) {
        val owned = synchronized(lock) {
            if (!resources.remove(resource)) false
            else { if (source.isNotEmpty()) admission.finish(source, System.nanoTime()); true }
        }
        if (owned) runCatching { resource.close() }
    }

    private fun <T : Closeable> listener(resource: T): T = own(resource).also { synchronized(lock) { listeners += it } }


    private fun publish(key: String, peer: DirectTransferPeer, onPeers: (List<DirectTransferPeer>) -> Unit) {
        val snapshot = synchronized(lock) {
            checkActive()
            if (discoveryStopped || key !in peers && peers.size >= MAX_PEERS) null
            else {
                val previous = peers[key]
                val preferred = DirectTransferDiscovery.preferredPeer(previous, peer)
                if (preferred === previous) null else { peers[key] = preferred; peers.values.toList() }
            }
        }
        if (snapshot != null) onPeers(snapshot)
    }

    private fun discoverLan(onPeers: (List<DirectTransferPeer>) -> Unit, manualAddress: Inet4Address? = null): List<DirectTransferPeer> {
        val socket = own(DatagramSocket(null))
        try {
            synchronized(lock) { discoverySocket = socket }
            if (synchronized(lock) { discoveryStopped }) return synchronized(lock) { peers.values.toList() }
            socket.broadcast = true
            socket.bind(InetSocketAddress(InetAddress.getByAddress(ByteArray(4)), 0))
            val local = DirectTransferDiscovery.localAddresses()
            if (manualAddress != null && !DirectTransferDiscovery.isLocalPeer(manualAddress, local))
                throw DirectTransferTransportException(DirectTransferTransportProblem.ADDRESS_NOT_LOCAL)
            val request = DirectTransferDiscovery.newId()
            val query = DirectTransferDiscovery.query(request)
            val broadcasts = if (manualAddress != null) listOf(manualAddress) else
                (listOf(InetAddress.getByAddress(byteArrayOf(-1, -1, -1, -1))) + local.mapNotNull { it.broadcast }).distinct()
            val directed = if (manualAddress == null) DirectTransferDiscovery.directedTargets(local) else emptyList()
            var directedIndex = 0
            val sentAddresses = mutableSetOf<InetAddress>()
            val began = System.nanoTime()
            val broadcastTiming = DirectTransferDiscoveryTiming(began, repeated = manualAddress == null)
            var nextDirected = began
            val finish = began + DISCOVERY_MILLIS * 1_000_000
            val buffer = ByteArray(DirectTransferDiscovery.MAX_PACKET_BYTES + 1)
            var sent = false
            var failure: IOException? = null
            fun send(address: InetAddress, directedOnce: Boolean = true) {
                checkActive()
                if (synchronized(lock) { discoveryStopped }) return
                if (directedOnce && !sentAddresses.add(address)) return
                try { socket.send(DatagramPacket(query, query.size, address, DISCOVERY_PORT)); sent = true }
                catch (error: IOException) { checkActive(); failure = error }
            }
            while (System.nanoTime() - finish < 0 && !synchronized(lock) { discoveryStopped }) {
                checkActive()
                val now = System.nanoTime()
                if (broadcastTiming.due(now)) broadcasts.forEach { send(it, directedOnce = false) }
                if (directedIndex < directed.size && now - nextDirected >= 0) {
                    val end = minOf(directedIndex + 16, directed.size)
                    while (directedIndex < end) send(directed[directedIndex++])
                    nextDirected = now + 200_000_000L
                }
                if (!sent) throw failure ?: IOException("无法发送设备发现请求")
                val next = minOf(broadcastTiming.next, if (directedIndex < directed.size) nextDirected else finish, finish)
                socket.soTimeout = ((next - System.nanoTime()) / 1_000_000L).coerceIn(1, 2000).toInt()
                val packet = DatagramPacket(buffer, buffer.size)
                try { socket.receive(packet) } catch (_: SocketTimeoutException) { continue }
                val source = packet.address as? Inet4Address ?: continue
                if (!DirectTransferDiscovery.acceptsSource(source, packet.port, manualAddress, local)) continue
                val offer = DirectTransferDiscovery.offer(buffer, packet.length, request) ?: continue
                val address = InetSocketAddress(source, offer.port)
                val peer = DirectTransferPeer(offer.id, offer.name, channel, address = address, legacy = offer.legacy)
                publish(peer.key, peer, onPeers)
                if (manualAddress != null) return synchronized(lock) { peers.values.toList() }
            }
            return synchronized(lock) { peers.values.toList() }
        } catch (error: IOException) {
            if (!synchronized(lock) { discoveryStopped }) throw error
            return synchronized(lock) { peers.values.toList() }
        } finally {
            synchronized(lock) { if (discoverySocket === socket) discoverySocket = null }
            release(socket)
        }
    }

    private fun acceptLan(deviceId: String, displayName: String, onListening: (List<String>) -> Unit,
                          onCandidate: (DirectTransferConnection) -> Unit) {
        val server = listener(ServerSocket())
        val discovery = listener(DatagramSocket(null))
        var multicast: Closeable? = null
        try {
            server.bind(InetSocketAddress(InetAddress.getByAddress(ByteArray(4)), 0), 4)
            server.soTimeout = 100
            discovery.bind(InetSocketAddress(InetAddress.getByAddress(ByteArray(4)), DISCOVERY_PORT))
            discovery.soTimeout = 100
            // Wi-Fi 可能过滤发现广播；候选认证成功后才关闭发现监听。
            context.getSystemService(WifiManager::class.java)?.createMulticastLock("cangoo_transfer_discovery")?.let {
                it.setReferenceCounted(false)
                it.acquire()
                multicast = listener(Closeable { it.release() })
            }
            onListening(DirectTransferDiscovery.localAddresses().filter { it.broadcast != null }
                .mapNotNull { it.address.hostAddress }.distinct())
            val buffer = ByteArray(DirectTransferDiscovery.MAX_PACKET_BYTES + 1)
            while (!synchronized(lock) { listeningStopped }) {
                checkActive()
                val packet = DatagramPacket(buffer, buffer.size)
                try {
                    discovery.receive(packet)
                    val source = packet.address as? Inet4Address
                    val request = DirectTransferDiscovery.request(buffer, packet.length)
                    if (source != null && !source.isAnyLocalAddress && !source.isMulticastAddress && !source.isLoopbackAddress &&
                        packet.port in 1..65535 && request != null) {
                        val offer = DirectTransferDiscovery.response(request, deviceId, displayName, server.localPort)
                        try { discovery.send(DatagramPacket(offer, offer.size, source, packet.port)) }
                        catch (error: IOException) {
                            // 单次回复不可达不结束等待；关闭仍收束，接收和监听错误不在此捕获。
                            checkActive()
                            if (discovery.isClosed || server.isClosed) throw error
                        }
                    }
                } catch (_: SocketTimeoutException) { }
                val socket = try { server.accept() } catch (_: SocketTimeoutException) { continue }
                own(socket)
                val source = socket.inetAddress.hostAddress.orEmpty()
                if (!synchronized(lock) { admission.begin(source, System.nanoTime()) }) { releaseConnection(socket, ""); continue }
                try {
                    socket.tcpNoDelay = true
                    onCandidate(connection(socket.getInputStream(), socket.getOutputStream(), socket, source))
                } catch (_: IOException) { releaseConnection(socket, source) }
            }
        } catch (error: IOException) {
            if (!synchronized(lock) { listeningStopped }) throw error
        } finally {
            try { release(discovery) }
            finally { try { release(server) } finally { multicast?.let(::release) } }
        }
    }

    @SuppressLint("MissingPermission")
    private fun bluetoothAdapter(): BluetoothAdapter {
        if (Build.VERSION.SDK_INT >= 31 && context.checkSelfPermission(Manifest.permission.BLUETOOTH_CONNECT) != PackageManager.PERMISSION_GRANTED)
            throw SecurityException("尚未允许蓝牙连接权限")
        return (context.getSystemService(BluetoothManager::class.java)?.adapter
            ?: throw DirectTransferTransportException(DirectTransferTransportProblem.BLUETOOTH_UNAVAILABLE))
            .also { if (!it.isEnabled) throw DirectTransferTransportException(DirectTransferTransportProblem.BLUETOOTH_DISABLED) }
    }

    @SuppressLint("MissingPermission")
    private fun discoverBluetooth(onPeers: (List<DirectTransferPeer>) -> Unit): List<DirectTransferPeer> {
        bluetoothAdapter().bondedDevices.sortedBy { it.address }.take(MAX_PEERS).forEach { device ->
            checkActive()
            if (synchronized(lock) { discoveryStopped }) return synchronized(lock) { peers.values.toList() }
            val name = device.name?.takeIf(DirectTransferDiscovery::validName)?.takeIf { it.isNotBlank() } ?: device.address
            val peer = DirectTransferPeer(device.address, name, channel, bluetoothDevice = device)
            publish(peer.key, peer, onPeers)
        }
        return synchronized(lock) { peers.values.toList() }
    }

    @SuppressLint("MissingPermission")
    private fun connectBluetooth(peer: DirectTransferPeer): DirectTransferConnection {
        bluetoothAdapter()
        val device = requireNotNull(peer.bluetoothDevice)
        if (device.bondState != BluetoothDevice.BOND_BONDED) throw DirectTransferTransportException(DirectTransferTransportProblem.NOT_PAIRED)
        val socket = own(device.createRfcommSocketToServiceRecord(BLUETOOTH_UUID))
        socket.connect()
        return connection(socket.inputStream, socket.outputStream, socket)
    }

    @SuppressLint("MissingPermission")
    private fun acceptBluetooth(onListening: () -> Unit, onCandidate: (DirectTransferConnection) -> Unit) {
        val server = listener(bluetoothAdapter().listenUsingRfcommWithServiceRecord("Cangoo Transfer", BLUETOOTH_UUID))
        try {
            onListening()
            while (!synchronized(lock) { listeningStopped }) {
                val socket = own(server.accept())
                val source = socket.remoteDevice.address
                if (socket.remoteDevice.bondState != BluetoothDevice.BOND_BONDED ||
                    !synchronized(lock) { admission.begin(source, System.nanoTime()) }) { releaseConnection(socket, ""); continue }
                try { onCandidate(connection(socket.inputStream, socket.outputStream, socket, source)) }
                catch (_: IOException) { releaseConnection(socket, source) }
            }
        } catch (error: IOException) {
            if (!synchronized(lock) { listeningStopped }) throw error
        } finally { release(server) }
    }

    companion object {
        internal const val DISCOVERY_PORT = 45962
        private const val DISCOVERY_MILLIS = 12_000L
        private const val MAX_PEERS = 64
        private const val IO_CHUNK_BYTES = 64 * 1024
        private val BLUETOOTH_UUID = UUID.fromString("86acb2b0-92d5-4e2f-9635-72f7dc195a2a")
    }
}

internal object DirectTransferDiscovery {
    const val MAX_PACKET_BYTES = 1024
    private val idPattern = Regex("[0-9a-f]{32}")
    private val portPattern = Regex("[1-9][0-9]{0,4}")
    private val addressPartPattern = Regex("0|[1-9][0-9]{0,2}")
    internal data class Offer(val id: String, val name: String, val port: Int, val legacy: Boolean = false)

    fun preferredPeer(current: DirectTransferPeer?, offered: DirectTransferPeer): DirectTransferPeer =
        if (current == null || current.legacy && !offered.legacy) offered else current

    fun localAddresses(): List<DirectTransferLanAddress> = NetworkInterface.getNetworkInterfaces()?.toList().orEmpty()
        .filter { it.isUp && !it.isLoopback }.flatMap { network ->
            network.interfaceAddresses.mapNotNull { local ->
                (local.address as? Inet4Address)?.let { DirectTransferLanAddress(it, local.networkPrefixLength.toInt(), local.broadcast as? Inet4Address) }
            }
        }

    fun parseAddress(value: String): Inet4Address? {
        val parts = value.trim().split('.')
        if (parts.size != 4 || parts.any { !addressPartPattern.matches(it) || it.toInt() > 255 }) return null
        return InetAddress.getByAddress(parts.map { it.toInt().toByte() }.toByteArray()) as Inet4Address
    }

    private fun number(address: Inet4Address): Long = ByteBuffer.wrap(address.address).int.toLong() and 0xffffffffL

    private fun range(local: DirectTransferLanAddress): LongRange {
        val mask = (0xffffffffL shl (32 - local.prefixLength)) and 0xffffffffL
        val network = number(local.address) and mask
        return network..(network or (mask xor 0xffffffffL))
    }

    fun isLocalPeer(address: Inet4Address, local: List<DirectTransferLanAddress>): Boolean {
        if (address.isAnyLocalAddress || address.isLoopbackAddress || address.isMulticastAddress || local.any { it.address == address }) return false
        val value = number(address)
        val ranges = local.filter { it.broadcast != null && it.prefixLength in 1..30 }.map(::range)
        if (ranges.any { value == it.first || value == it.last }) return false
        return ranges.any { value in it }
    }

    fun directedTargets(local: List<DirectTransferLanAddress>): List<Inet4Address> {
        val result = linkedSetOf<Inet4Address>()
        for (network in local.filter { it.broadcast != null && it.prefixLength in 24..30 }) {
            val range = range(network)
            for (value in (range.first + 1) until range.last) {
                val address = InetAddress.getByAddress(ByteBuffer.allocate(4).putInt(value.toInt()).array()) as Inet4Address
                if (isLocalPeer(address, local)) result += address
                if (result.size == 254) return result.toList()
            }
        }
        return result.toList()
    }

    fun acceptsSource(source: Inet4Address, port: Int, expected: Inet4Address?, local: List<DirectTransferLanAddress>): Boolean =
        port == DirectTransferTransport.DISCOVERY_PORT && (expected == null || source == expected) && isLocalPeer(source, local)

    fun newId(): String = ByteArray(16).also { SecureRandom().nextBytes(it) }.joinToString("") { "%02x".format(it) }
    fun validId(value: String) = idPattern.matches(value)
    fun validName(value: String): Boolean = value.codePointCount(0, value.length) in 1..64 &&
        value.toByteArray(Charsets.UTF_8).size <= 256 && value.codePoints().allMatch { !Character.isISOControl(it) && it !in 0xd800..0xdfff }

    fun query(request: String): ByteArray {
        require(validId(request))
        return write("discover", request)
    }

    fun response(request: String, id: String, name: String, port: Int): ByteArray {
        require(validId(request) && validId(id) && validName(name) && port in 1..65535)
        return write("offer", request, Offer(id, name, port))
    }

    fun request(bytes: ByteArray, length: Int): String? = parse(bytes, length, setOf("v", "kind", "request"))?.let {
        it["request"]?.takeIf { request -> it["v"] == "1" && it["kind"] == "discover" && validId(request) }
    }

    fun offer(bytes: ByteArray, length: Int, request: String): Offer? {
        val fields = parse(bytes, length, setOf("v", "kind", "request", "id", "name", "port")) ?: return null
        if (fields["v"] !in setOf("1", "2") || fields["kind"] != "offer" || fields["request"] != request || !validId(request)) return null
        val id = fields.getValue("id")
        val name = fields.getValue("name")
        val port = fields.getValue("port").takeIf(portPattern::matches)?.toIntOrNull() ?: return null
        return if (validId(id) && validName(name) && port in 1..65535) Offer(id, name, port, fields["v"] == "1") else null
    }

    private fun write(kind: String, request: String, offer: Offer? = null): ByteArray {
        val text = StringWriter()
        JsonWriter(text).use { writer ->
            writer.beginObject().name("v").value(if (offer == null) 1 else 2).name("kind").value(kind).name("request").value(request)
            if (offer != null) writer.name("id").value(offer.id).name("name").value(offer.name).name("port").value(offer.port)
            writer.endObject()
        }
        return text.toString().toByteArray(Charsets.UTF_8).also { check(it.size <= MAX_PACKET_BYTES) }
    }

    private fun parse(bytes: ByteArray, length: Int, keys: Set<String>): Map<String, String>? {
        if (length !in 1..MAX_PACKET_BYTES || length > bytes.size) return null
        return try {
            val decoder = Charsets.UTF_8.newDecoder().onMalformedInput(CodingErrorAction.REPORT).onUnmappableCharacter(CodingErrorAction.REPORT)
            val text = decoder.decode(ByteBuffer.wrap(bytes, 0, length)).toString()
            JsonReader(StringReader(text)).use { reader ->
                reader.setStrictness(Strictness.STRICT)
                reader.setNestingLimit(2)
                val fields = mutableMapOf<String, String>()
                reader.beginObject()
                while (reader.hasNext()) {
                    val key = reader.nextName()
                    if (key !in keys || key in fields) return null
                    if (reader.peek() != if (key == "v" || key == "port") JsonToken.NUMBER else JsonToken.STRING) return null
                    fields[key] = reader.nextString()
                }
                reader.endObject()
                if (reader.peek() != JsonToken.END_DOCUMENT || fields.keys != keys) null else fields
            }
        } catch (_: Exception) { null }
    }
}

// 接入预算使用单调时间；失败只冷却来源，不消耗接收页的一次配对资格。
internal class DirectTransferAdmission {
    private data class Source(var touched: Long, var active: Boolean = false, var blockedUntil: Long = 0)
    private val sources = linkedMapOf<String, Source>()
    private var tokens = 4.0
    private var updated: Long? = null

    fun begin(source: String, now: Long): Boolean {
        sources.entries.removeAll { !it.value.active && now - it.value.touched >= 60_000_000_000L }
        val previous = updated
        if (previous != null) tokens = (tokens + (now - previous).coerceAtLeast(0) / 1_000_000_000.0).coerceAtMost(4.0)
        updated = now
        val entry = sources[source]
        if (entry?.active == true || entry != null && now < entry.blockedUntil || sources.values.count { it.active } >= 4 || tokens < 1) return false
        if (entry == null && sources.size >= 64) return false
        val accepted = entry ?: Source(now).also { sources[source] = it }
        accepted.touched = now
        accepted.active = true
        tokens -= 1
        return true
    }

    fun finish(source: String, now: Long) {
        sources[source]?.let { it.active = false; it.touched = now; it.blockedUntil = now + 2_000_000_000L }
    }
}

internal class DirectTransferDiscoveryTiming(startNanos: Long, private val repeated: Boolean) {
    var next = startNanos
        private set

    fun due(now: Long): Boolean {
        if (now < next) return false
        next = if (repeated) now + 2_000_000_000L else Long.MAX_VALUE
        return true
    }
}
