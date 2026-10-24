"""一次直传的局域网与经典蓝牙通道；所有操作与消费者均在同一 Qt 线程。"""

from __future__ import annotations

from collections import deque
import ipaddress
import secrets
import time

from PySide6.QtCore import QObject, QTimer, Qt, QUuid, Signal
from PySide6.QtNetwork import QAbstractSocket, QHostAddress, QNetworkDatagram, QNetworkInterface, QTcpServer, QTcpSocket, QUdpSocket
from PySide6.QtBluetooth import (
    QBluetoothAddress, QBluetoothLocalDevice,
    QBluetoothServer, QBluetoothServiceInfo, QBluetoothSocket, QBluetoothUuid,
)

from desktop.host.bluetooth_devices import paired_bluetooth_devices
from core.direct_transfer import (
    DirectTransferError, MAX_CHUNK, MAX_INPUT, _ID, _canonical, _fields, _integer, _name, _parse,
)


DISCOVERY_PORT = 45962
DISCOVERY_BYTES = 1024
MAX_PEERS = 64
DISCOVERY_MS = 12_000
BROADCAST_MS = 2_000
PROBE_BATCH = 16
PROBE_INTERVAL_MS = 50
MAX_PROBE_TARGETS = 254
BUFFER_LIMIT = 2 * MAX_INPUT
SERVICE_UUID = "86acb2b0-92d5-4e2f-9635-72f7dc195a2a"
SERVICE_NAME = "Cangoo Transfer"


class DirectTransferTransport(QObject):
    peersChanged = Signal(object)
    connected = Signal(str)
    dataReceived = Signal(bytes)
    drained = Signal()
    failed = Signal(str)
    discoveryFinished = Signal()

    def __init__(self, device_id: str, device_name: str, parent=None):
        super().__init__(parent)
        if type(device_id) is not str or not _ID.fullmatch(device_id):
            raise ValueError("invalid device identity")
        _name(device_name, 64, 256)
        self._device_id, self._device_name = device_id, device_name
        self._started = self._closed = self._connected = self._scanning = False
        self._cleanup_succeeded = True
        self._role = self._kind = self._selected = self._request = ""
        self._scan_deadline = 0.0
        self._manual_address = ""
        self._manual_path = None
        self._probe_targets = deque()
        self._discovery_sent = False
        self._socket = self._server = self._udp = self._local = self._service = None
        self._peers = {}
        self._endpoints = {}
        self._out_frame = None
        self._out_offset = self._out_acked = 0
        self._reading = self._writing = False
        self._scan_timer = self._timer(self._finish_discovery)
        self._broadcast_timer = self._timer(self._broadcast, repeating=True)
        self._probe_timer = self._timer(self._pump_probes)
        self._read_timer = self._timer(self._pump_read)
        self._udp_timer = self._timer(self._pump_udp)
        self._write_timer = self._timer(self._pump_write)

    def _timer(self, callback, *, repeating=False):
        timer = QTimer(self)
        timer.setSingleShot(not repeating)
        timer.setTimerType(Qt.TimerType.PreciseTimer)
        timer.timeout.connect(callback)
        return timer

    @property
    def listening(self) -> bool:
        if self._closed or self._role != "RECEIVE" or self._server is None:
            return False
        if not self._server.isListening():
            return False
        if self._kind == "LAN":
            return self._udp is not None and self._udp.state() == QAbstractSocket.SocketState.BoundState
        return self._service is not None and self._service.isRegistered()

    def start(self, role: str, kind: str, manual_address: str = "") -> bool:
        if self._started or self._closed:
            return False
        self._started = True
        if type(role) is not str or type(kind) is not str or role not in {"SEND", "RECEIVE"} or kind not in {"LAN", "BLUETOOTH"}:
            self._fail("INVALID_DATA")
            return False
        self._role, self._kind = role, kind
        if manual_address:
            target = self.manual_lan_target(manual_address) if role == "SEND" and kind == "LAN" else None
            if target is None:
                self._fail("INVALID_ADDRESS")
                return False
            self._manual_address, self._manual_path = target
        elif type(manual_address) is not str:
            self._fail("INVALID_ADDRESS")
            return False
        try:
            if kind == "LAN":
                self._start_lan()
            else:
                self._start_bluetooth()
        except (OSError, RuntimeError, ValueError, TypeError):
            self._fail("UNAVAILABLE")
        return not self._closed

    def _begin_discovery(self):
        self._scanning = True
        self._scan_deadline = time.monotonic() + DISCOVERY_MS / 1000
        self._scan_timer.start(DISCOVERY_MS)

    def _start_lan(self):
        if self._role == "RECEIVE":
            server = self._server = QTcpServer(self)
            server.setMaxPendingConnections(1)
            server.setListenBacklogSize(1)
            server.newConnection.connect(lambda: self._accept(server))
            server.acceptError.connect(lambda _error: self._fail("UNAVAILABLE") if server is self._server else None)
            if not server.listen(QHostAddress.SpecialAddress.AnyIPv4, 0):
                self._fail("UNAVAILABLE")
                return
        if self._closed:
            return
        udp = self._udp = QUdpSocket(self)
        udp.readyRead.connect(lambda: self._pump_udp() if udp is self._udp else None)
        udp.errorOccurred.connect(lambda error: self._udp_error(udp, error))
        port = DISCOVERY_PORT if self._role == "RECEIVE" else 0
        if not udp.bind(QHostAddress.SpecialAddress.AnyIPv4, port, QAbstractSocket.BindFlag.DontShareAddress):
            self._fail("UNAVAILABLE")
            return
        if self._closed:
            return
        if self._role == "SEND":
            self._request = secrets.token_hex(16)
            self._begin_discovery()
            if not self._manual_address:
                self._probe_targets = deque(self._lan_probe_targets(self._lan_paths()))
                if self._probe_targets:
                    self._probe_timer.start(0)
            self._broadcast_timer.start(BROADCAST_MS)
            self._broadcast()
        elif not self.listening:
            self._fail("UNAVAILABLE")

    @staticmethod
    def _lan_paths():
        paths = []
        for interface in QNetworkInterface.allInterfaces():
            flags = interface.flags()
            if (not flags & QNetworkInterface.InterfaceFlag.IsUp
                    or not flags & QNetworkInterface.InterfaceFlag.IsRunning
                    or not flags & QNetworkInterface.InterfaceFlag.CanBroadcast
                    or flags & (QNetworkInterface.InterfaceFlag.IsLoopBack | QNetworkInterface.InterfaceFlag.IsPointToPoint)):
                continue
            index = interface.index()
            if index <= 0:
                continue
            for entry in interface.addressEntries():
                local, broadcast = entry.ip(), entry.broadcast()
                if (local.protocol() == QAbstractSocket.NetworkLayerProtocol.IPv4Protocol
                        and not local.isNull() and not local.isLoopback() and not local.isMulticast()
                        and local.toIPv4Address() not in (0, 0xffffffff)
                        and broadcast.protocol() == QAbstractSocket.NetworkLayerProtocol.IPv4Protocol
                        and not broadcast.isNull() and 1 <= entry.prefixLength() <= 30):
                    path = local.toString(), broadcast.toString(), index, entry.prefixLength()
                    if path not in paths:
                        paths.append(path)
        return paths

    @classmethod
    def lan_address_candidates(cls):
        interfaces = {interface.index(): interface for interface in QNetworkInterface.allInterfaces()}
        entries = {}
        for address, _broadcast, index, _prefix in cls._lan_paths():
            interface = interfaces.get(index)
            name = (interface.humanReadableName() or interface.name()) if interface is not None else ""
            name = "".join(character for character in name if character.isprintable()).strip()[:128]
            kind = "OTHER"
            if interface is not None:
                if interface.type() == QNetworkInterface.InterfaceType.Wifi:
                    kind = "WIFI"
                elif interface.type() == QNetworkInterface.InterfaceType.Ethernet:
                    kind = "ETHERNET"
            entries[index, address] = (address, index, name or str(index), kind)
        return tuple(entries[key] for key in sorted(entries))[:64]

    @staticmethod
    def _local_ipv4_addresses():
        return {entry.ip().toString() for interface in QNetworkInterface.allInterfaces()
                for entry in interface.addressEntries()
                if entry.ip().protocol() == QAbstractSocket.NetworkLayerProtocol.IPv4Protocol}

    @classmethod
    def manual_lan_target(cls, value):
        if type(value) is not str or len(value) > 64:
            return None
        try:
            address = ipaddress.IPv4Address(value.strip())
        except ipaddress.AddressValueError:
            return None
        paths = cls._lan_paths()
        if (address.is_unspecified or address.is_loopback or address.is_multicast
                or str(address) in cls._local_ipv4_addresses()):
            return None
        candidates = []
        for path in paths:
            network = ipaddress.IPv4Network((path[0], path[3]), strict=False)
            if address in network:
                if address in (network.network_address, network.broadcast_address):
                    return None
                candidates.append(path)
        return (str(address), max(candidates, key=lambda path: path[3])) if candidates else None

    @classmethod
    def _lan_probe_targets(cls, paths):
        # 多网卡轮流分配同一次查找的限额，避免首个网段耗尽全部补查机会。
        candidates = [(path, iter(ipaddress.IPv4Network((path[0], path[3]), strict=False).hosts()))
                      for path in paths if 24 <= path[3] <= 30]
        seen = cls._local_ipv4_addresses() | {path[0] for path in paths}
        for path in paths:
            network = ipaddress.IPv4Network((path[0], path[3]), strict=False)
            seen.update((str(network.network_address), str(network.broadcast_address)))
        targets = []
        while candidates and len(targets) < MAX_PROBE_TARGETS:
            remaining = []
            for path, addresses in candidates:
                for address in addresses:
                    target = str(address)
                    if target not in seen and not address.is_loopback and not address.is_multicast:
                        seen.add(target)
                        targets.append((target, path))
                        remaining.append((path, addresses))
                        break
                if len(targets) == MAX_PROBE_TARGETS:
                    break
            candidates = remaining
        return targets

    def _send_discovery(self, target, path):
        payload = _canonical({"v": 1, "kind": "discover", "request": self._request})
        datagram = QNetworkDatagram(payload, QHostAddress(target), DISCOVERY_PORT)
        datagram.setSender(QHostAddress(path[0]))
        datagram.setInterfaceIndex(path[2])
        sent = self._send_datagram(datagram)
        self._discovery_sent |= sent
        return sent

    def _pump_probes(self):
        if self._closed or not self._scanning or self._udp is None:
            return
        if time.monotonic() >= self._scan_deadline:
            self._finish_discovery()
            return
        paths = self._lan_paths()
        for _index in range(PROBE_BATCH):
            if not self._probe_targets or self._closed or self._udp is None:
                break
            target, path = self._probe_targets.popleft()
            if path in paths:
                self._send_discovery(target, path)
        if self._probe_targets and not self._closed:
            self._probe_timer.start(PROBE_INTERVAL_MS)
        elif not self._discovery_sent:
            self._fail("UNAVAILABLE")

    @staticmethod
    def _local_source(datagram, paths, *, exact=False):
        index = datagram.interfaceIndex()
        destination = datagram.destinationAddress().toString()
        candidates = [path for path in paths if not index or path[2] == index]
        matching = [path for path in candidates if path[0] == destination]
        if len(matching) == 1:
            return matching[0]
        if exact or not index or not candidates:
            return None
        # 广播的目的地址不是本机单播地址；回复沿入站网卡选择相应子网的源地址。
        matching = [path for path in candidates if datagram.senderAddress().isInSubnet(QHostAddress(path[0]), path[3])]
        return max(matching, key=lambda path: path[3]) if matching else candidates[0]

    def _udp_error(self, udp, error):
        if self._closed or udp is not self._udp:
            return
        packet_errors = {
            QAbstractSocket.SocketError.SocketAccessError, QAbstractSocket.SocketError.HostNotFoundError,
            QAbstractSocket.SocketError.DatagramTooLargeError, QAbstractSocket.SocketError.NetworkError,
            QAbstractSocket.SocketError.SocketAddressNotAvailableError, QAbstractSocket.SocketError.TemporaryError,
        }
        if udp.state() == QAbstractSocket.SocketState.BoundState and error in packet_errors:
            return
        self._fail("UNAVAILABLE")

    def _send_datagram(self, datagram):
        udp = self._udp
        if self._closed or udp is None:
            return False
        try:
            return udp.writeDatagram(datagram) == len(datagram.data()) and not self._closed
        except (OSError, RuntimeError):
            return False

    def _broadcast(self):
        if self._closed or not self._scanning or self._udp is None:
            return
        if time.monotonic() >= self._scan_deadline:
            self._finish_discovery()
            return
        try:
            paths = self._lan_paths()
            if self._manual_address:
                if self._manual_path not in paths:
                    self._fail("UNAVAILABLE")
                    return
                self._send_discovery(self._manual_address, self._manual_path)
                return
            succeeded = False
            for path in paths:
                for address in dict.fromkeys((path[1], "255.255.255.255")):
                    if self._closed or self._udp is None:
                        return
                    succeeded |= self._send_discovery(address, path)
            if not succeeded and not self._probe_targets and not self._discovery_sent:
                self._fail("UNAVAILABLE")
        except (OSError, RuntimeError, ValueError, TypeError):
            self._fail("UNAVAILABLE")

    def _pump_udp(self):
        udp = self._udp
        if self._closed or udp is None:
            return
        if self._role == "SEND" and (not self._scanning or time.monotonic() >= self._scan_deadline):
            self._finish_discovery()
            return
        try:
            paths = self._lan_paths()
            for _index in range(64):
                if self._closed or udp is not self._udp or not udp.hasPendingDatagrams():
                    return
                datagram = udp.receiveDatagram(DISCOVERY_BYTES + 1)
                data = bytes(datagram.data())
                address, port = datagram.senderAddress(), datagram.senderPort()
                if (not 0 < len(data) <= DISCOVERY_BYTES or address.protocol() != QAbstractSocket.NetworkLayerProtocol.IPv4Protocol
                        or address.isNull() or address.isLoopback() or address.isMulticast()
                        or address.toIPv4Address() in (0, 0xffffffff) or not 1 <= port <= 65535):
                    continue
                source = self._local_source(datagram, paths, exact=self._role == "SEND")
                if source is None:
                    continue
                if self._manual_address and (address.toString() != self._manual_address
                        or port != DISCOVERY_PORT or source != self._manual_path):
                    continue
                try:
                    value = _parse(data)
                    _integer(value.get("v"), 1, 1)
                    request = value.get("request")
                    if type(request) is not str or not _ID.fullmatch(request):
                        continue
                    if self._role == "RECEIVE":
                        _fields(value, "v", "kind", "request")
                        if value["kind"] != "discover" or not self.listening:
                            continue
                        offer = _canonical({"v": 1, "kind": "offer", "request": request,
                                            "id": self._device_id, "name": self._device_name,
                                            "port": self._server.serverPort()})
                        reply = datagram.makeReply(offer)
                        reply.setSender(QHostAddress(source[0]))
                        reply.setInterfaceIndex(source[2])
                        self._send_datagram(reply)
                    else:
                        _fields(value, "v", "kind", "request", "id", "name", "port")
                        if value["kind"] != "offer" or request != self._request:
                            continue
                        _integer(value["port"], 1, 65535)
                        _name(value["name"], 64, 256)
                        peer_id = value["id"]
                        if type(peer_id) is str and _ID.fullmatch(peer_id) and peer_id != self._device_id:
                            self._add_peer(peer_id, value["name"], (address.toString(), value["port"], source[0], source[2]))
                except (DirectTransferError, ValueError, TypeError):
                    continue
            if udp is self._udp and udp.hasPendingDatagrams() and not self._udp_timer.isActive():
                self._udp_timer.start(0)
        except (OSError, RuntimeError):
            self._fail("UNAVAILABLE")

    def _add_peer(self, peer_id, name, endpoint):
        if peer_id in self._peers or endpoint in self._endpoints or len(self._peers) >= MAX_PEERS:
            return
        self._peers[peer_id] = (name, endpoint)
        self._endpoints[endpoint] = peer_id
        self.peersChanged.emit([{"peerId": key, "name": value[0]} for key, value in self._peers.items()])

    def _paired(self, address) -> bool:
        return self._local is not None and self._local.isValid() and self._local.pairingStatus(address) in {
            QBluetoothLocalDevice.Pairing.Paired, QBluetoothLocalDevice.Pairing.AuthorizedPaired,
        }

    def _start_bluetooth(self):
        local = self._local = QBluetoothLocalDevice(self)
        if not local.isValid() or local.hostMode() == QBluetoothLocalDevice.HostMode.HostPoweredOff:
            self._fail("UNAVAILABLE")
            return
        local.hostModeStateChanged.connect(lambda mode: self._fail("UNAVAILABLE")
                                          if local is self._local and mode == QBluetoothLocalDevice.HostMode.HostPoweredOff else None)
        if self._role == "RECEIVE":
            server = self._server = QBluetoothServer(QBluetoothServiceInfo.Protocol.RfcommProtocol, self)
            server.setMaxPendingConnections(1)
            server.newConnection.connect(lambda: self._accept(server))
            server.errorOccurred.connect(lambda _error: self._fail("UNAVAILABLE") if server is self._server else None)
            service = server.listen(QBluetoothUuid(QUuid(SERVICE_UUID)), SERVICE_NAME)
            if self._closed or server is not self._server:
                if service.isRegistered():
                    service.unregisterService()
                return
            self._service = service
            if not self.listening:
                self._fail("UNAVAILABLE")
            return
        self._begin_discovery()
        for address, name in paired_bluetooth_devices(local.address().toString(), MAX_PEERS):
            self._bluetooth_peer(QBluetoothAddress(address), name)
            if self._closed:
                return
        self._finish_discovery()

    def _bluetooth_peer(self, address, name):
        if self._closed or not self._scanning:
            return
        if time.monotonic() >= self._scan_deadline:
            self._finish_discovery()
            return
        try:
            if address.isNull() or not self._paired(address):
                return
            endpoint = address.toString()
            try:
                _name(name, 64, 256)
            except (DirectTransferError, UnicodeError):
                name = endpoint
            if endpoint in self._endpoints or len(self._peers) >= MAX_PEERS:
                return
            peer_id = secrets.token_hex(16)
            while peer_id in self._peers or peer_id == self._device_id:
                peer_id = secrets.token_hex(16)
            self._add_peer(peer_id, name, endpoint)
        except DirectTransferError:
            return
        except (OSError, RuntimeError, ValueError, TypeError):
            self._fail("UNAVAILABLE")

    def _stop_discovery(self):
        self._scanning = False
        self._scan_timer.stop()
        self._broadcast_timer.stop()
        self._probe_timer.stop()
        self._probe_targets.clear()
        self._udp_timer.stop()
        udp, self._udp = self._udp, None
        return self._dispose(udp, "close")

    def _finish_discovery(self):
        if self._closed or not self._scanning:
            return
        if not self._stop_discovery():
            self._fail("UNAVAILABLE")
            return
        self.discoveryFinished.emit()

    def choose_peer(self, peer_id: str) -> bool:
        if self._closed or self._role != "SEND" or self._socket is not None or type(peer_id) is not str or peer_id not in self._peers:
            return False
        endpoint = self._peers[peer_id][1]
        try:
            if self._kind == "BLUETOOTH" and not self._paired(QBluetoothAddress(endpoint)):
                self._fail("CONNECT_FAILED")
                return False
            if not self._stop_discovery():
                self._fail("UNAVAILABLE")
                return False
            self._selected = peer_id
            if self._kind == "LAN":
                if self._manual_address and self.manual_lan_target(self._manual_address) != (self._manual_address, self._manual_path):
                    self._fail("CONNECT_FAILED")
                    return False
                if not any(path[0] == endpoint[2] and path[2] == endpoint[3] for path in self._lan_paths()):
                    self._fail("CONNECT_FAILED")
                    return False
                socket = QTcpSocket(self)
                self._bind_socket(socket)
                if not socket.bind(QHostAddress(endpoint[2]), 0):
                    self._fail("CONNECT_FAILED")
                    return False
                if not self._closed:
                    socket.connectToHost(QHostAddress(endpoint[0]), endpoint[1])
            else:
                socket = QBluetoothSocket(QBluetoothServiceInfo.Protocol.RfcommProtocol, self)
                self._bind_socket(socket)
                socket.connectToService(QBluetoothAddress(endpoint), QBluetoothUuid(QUuid(SERVICE_UUID)))
        except (OSError, RuntimeError, ValueError, TypeError):
            self._fail("CONNECT_FAILED")
        return not self._closed

    def _stop_listener(self):
        service, self._service = self._service, None
        server, self._server = self._server, None
        succeeded = True
        if service is not None:
            try:
                if service.isRegistered():
                    succeeded = service.unregisterService() is True
            except (OSError, RuntimeError):
                succeeded = False
        return self._dispose(server, "close") and succeeded

    def _accept(self, server):
        if self._closed or server is not self._server:
            return
        try:
            socket = server.nextPendingConnection()
            if socket is None:
                return
            if self._socket is not None or (self._kind == "BLUETOOTH" and not self._paired(socket.peerAddress())):
                if not self._dispose(socket, "abort"):
                    self._fail("UNAVAILABLE")
                return
            self._bind_socket(socket)
            discovery_closed = self._stop_discovery()
            if not self._stop_listener() or not discovery_closed:
                self._fail("UNAVAILABLE")
                return
            self._socket_connected(socket)
        except (OSError, RuntimeError, ValueError, TypeError):
            self._fail("CONNECT_FAILED")

    def _bind_socket(self, socket):
        self._socket = socket
        socket.setParent(self)
        if self._kind == "LAN":
            socket.setReadBufferSize(BUFFER_LIMIT)
        socket.connected.connect(lambda: self._socket_connected(socket))
        socket.readyRead.connect(lambda: self._read_ready(socket), Qt.ConnectionType.DirectConnection)
        socket.bytesWritten.connect(lambda count: self._bytes_written(socket, count), Qt.ConnectionType.DirectConnection)
        socket.disconnected.connect(lambda: self._socket_failed(socket))
        # Qt 蓝牙服务查找的错误回调尚会访问内部对象，必须等其返回再 abort。
        socket.errorOccurred.connect(lambda _error: self._socket_failed(socket), Qt.ConnectionType.QueuedConnection)

    def _socket_failed(self, socket):
        if self._closed or socket is not self._socket:
            return
        if self._connected:
            self._read_timer.stop()
            self._pump_read()
        self._fail("DISCONNECTED" if self._connected else "CONNECT_FAILED")

    def _socket_connected(self, socket):
        if self._closed or socket is not self._socket or self._connected:
            return
        self._connected = True
        self.connected.emit(self._selected)
        self._read_ready(socket)

    def _read_ready(self, socket):
        if self._closed or socket is not self._socket or not self._connected:
            return
        try:
            if socket.bytesAvailable() > BUFFER_LIMIT:
                self._fail("LIMIT_EXCEEDED")
            elif not self._reading and not self._read_timer.isActive():
                self._pump_read()
        except (OSError, RuntimeError):
            self._fail("DISCONNECTED")

    def _pump_read(self):
        socket = self._socket
        if self._closed or socket is None or not self._connected or self._reading:
            return
        self._reading = True
        try:
            for _index in range(4):
                available = socket.bytesAvailable()
                if available < 0:
                    self._fail("DISCONNECTED")
                    return
                if available > BUFFER_LIMIT:
                    self._fail("LIMIT_EXCEEDED")
                    return
                if not available:
                    return
                data = bytes(socket.read(min(MAX_CHUNK, available)))
                if not data:
                    self._fail("DISCONNECTED")
                    return
                # 消费者必须在本线程捕获协议异常并关闭通道；Qt 槽异常不由 emit 重新抛出。
                self.dataReceived.emit(data)
                if self._closed or socket is not self._socket:
                    return
            if socket.bytesAvailable() and not self._read_timer.isActive():
                self._read_timer.start(0)
        except (OSError, RuntimeError):
            self._fail("DISCONNECTED")
        finally:
            self._reading = False

    def write(self, frame: bytes) -> bool:
        if self._closed or not self._connected or self._socket is None or self._out_frame is not None:
            return False
        if type(frame) is not bytes or len(frame) < 5 or int.from_bytes(frame[:4], "big") != len(frame) - 4:
            self._fail("INVALID_DATA")
            return False
        if len(frame) > MAX_INPUT:
            self._fail("LIMIT_EXCEEDED")
            return False
        self._out_frame, self._out_offset, self._out_acked = frame, 0, 0
        self._pump_write()
        return not self._closed

    def _bytes_written(self, socket, count):
        if self._closed or socket is not self._socket or self._out_frame is None:
            return
        if type(count) is not int or count < 0:
            self._fail("INVALID_DATA")
            return
        self._out_acked += count
        if not self._writing:
            self._pump_write()

    def _pump_write(self):
        socket = self._socket
        if self._closed or socket is None or self._out_frame is None or self._writing:
            return
        self._writing = True
        retry_delay = 0
        try:
            if self._out_acked == self._out_offset and self._out_offset < len(self._out_frame):
                size = socket.write(self._out_frame[self._out_offset:])
                if size < 0 or size > len(self._out_frame) - self._out_offset:
                    self._fail("DISCONNECTED")
                    return
                if self._closed or socket is not self._socket:
                    return
                self._out_offset += size
                retry_delay = 10 if size == 0 else 0
            if self._out_acked > self._out_offset:
                self._fail("INVALID_DATA")
                return
            if self._out_acked == self._out_offset == len(self._out_frame) and socket.bytesToWrite() == 0:
                self._out_frame = None
                self.drained.emit()
            if self._out_frame is not None and self._out_acked == self._out_offset and not self._write_timer.isActive():
                self._write_timer.start(retry_delay)
        except (OSError, RuntimeError, ValueError, TypeError):
            self._fail("DISCONNECTED")
        finally:
            self._writing = False

    @staticmethod
    def _dispose(resource, stop=None):
        if resource is None:
            return True
        succeeded = True
        for method in ((stop, "deleteLater") if stop else ("deleteLater",)):
            try:
                getattr(resource, method)()
            except (OSError, RuntimeError):
                succeeded = False
        return succeeded

    def _shutdown(self):
        if self._closed:
            return self._cleanup_succeeded
        self._closed, self._connected = True, False
        socket, self._socket = self._socket, None
        local, self._local = self._local, None
        self._read_timer.stop()
        self._write_timer.stop()
        succeeded = self._stop_discovery()
        succeeded = self._stop_listener() and succeeded
        succeeded = self._dispose(socket, "abort") and succeeded
        succeeded = self._dispose(local) and succeeded
        self._out_frame = None
        self._out_offset = self._out_acked = 0
        self._peers.clear()
        self._endpoints.clear()
        self._selected = self._request = ""
        self._cleanup_succeeded = self._cleanup_succeeded and succeeded
        return self._cleanup_succeeded

    def close(self) -> bool:
        was_closed = self._closed
        succeeded = self._shutdown()
        if not succeeded and not was_closed:
            self.failed.emit("UNAVAILABLE")
        return succeeded

    def _fail(self, code):
        if self._closed:
            return
        self._shutdown()
        self.failed.emit(code)
