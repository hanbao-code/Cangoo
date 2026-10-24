"""本次库会话内的设备直传；协议、通道和资料所有权由原生串行衔接。"""

from __future__ import annotations

from collections import deque
import hashlib
import secrets
import threading
import time

from PySide6.QtCore import QObject, Qt, QTimer, Signal, Slot

from core.direct_transfer import DirectTransferError, DirectTransferSession, MAX_CHUNK, MAX_INPUT, MAX_PAYLOAD
from desktop.host.network_interfaces import interface_status
from .direct_transfer_transport import DirectTransferTransport


class DirectTransferController(QObject):
    stateChanged = Signal(object)
    _snapshotFinished = Signal(int, str, object)

    def __init__(self, adapter, *, authority, lock_monitor_ready, busy, hold,
                 adopt_received, parent=None, transport_factory=None, clock=time.monotonic, lan_access=None):
        super().__init__(parent)
        self.adapter = adapter
        self._authority, self._lock_monitor_ready, self._busy = authority, lock_monitor_ready, busy
        self._hold, self._adopt_received = hold, adopt_received
        self._transport_factory = transport_factory
        self._clock = clock
        if lan_access is None:
            from desktop.host.lan_access import LanAccess
            lan_access = LanAccess(self)
        self._lan_access = lan_access
        self._lan_access.statusChanged.connect(self._network_changed)
        self._page = self._session = self._revision = self._run = 0
        self._transport = self._protocol = None
        self._payload = None
        self._job = ""
        self._cancel_job = ""
        self._completion_lock = threading.Lock()
        self._pending_completion = None
        self._cleanup_failed = False
        self._outbound = deque()
        self._writing = self._handed_over = self._holding = False
        self._auth_deadline = self._transfer_started = None
        self._last_progress = 0.0
        self._selected_peer = ""
        self._offer = None
        self._device_id = ""
        self._state = {}
        self._address_signature = None
        self._address_rows = []
        self._projection = {"effectiveTheme": "DARK", "language": "ZH", "uiFontScale": "100"}
        self._timeout = QTimer(self)
        self._timeout.setInterval(1000)
        self._timeout.timeout.connect(self.check_deadlines)
        self._pump_timer = QTimer(self)
        self._pump_timer.setSingleShot(True)
        self._pump_timer.timeout.connect(self._pump)
        self._snapshotFinished.connect(self._snapshot_finished, Qt.ConnectionType.QueuedConnection)

    @property
    def active(self):
        return self._transport is not None or bool(self._job)

    @property
    def epochs(self):
        return self._page, self._session

    def bind(self, page, session, *, role="SEND", transport="LAN"):
        try:
            self.close()
        except RuntimeError:
            return False
        if type(page) is not int or type(session) is not int or page <= 0 or session <= 0 or self._authority() != (page, session):
            return False
        self._page, self._session = page, session
        try:
            vault = self.adapter.transfer_vault_name(page, session)
        except Exception:
            self._page = self._session = 0
            return False
        self._state = {
            "flowId": secrets.token_hex(16), "phase": "IDLE", "role": role, "transport": transport,
            "scope": "ALL", "peers": [], "sas": "", "localConfirmed": False, "peerConfirmed": False,
            "receiverAccepted": False, "offerReady": False, "preparing": False,
            "peerDeviceName": "", "localVaultName": vault, "peerVaultName": "",
            "transferredBytes": 0, "totalBytes": 0, "errorCode": "NONE",
            "localAddresses": [], "manualAddress": "", "manualSearching": False,
        }
        self._publish()
        self._lan_access.refresh()
        return True

    def snapshot(self):
        return {**self._state, "peers": [dict(item) for item in self._state.get("peers", [])],
                "localAddresses": [dict(item) for item in self._state.get("localAddresses", [])],
                "revision": self._revision, "pageEpoch": self._page, "sessionEpoch": self._session,
                "networkAccess": self._lan_access.status, **self._projection}

    def _network_changed(self, _status):
        if self._state and self._current():
            self._publish()

    def apply_settings(self, effectiveTheme, language, uiFontScale):
        self._projection = {"effectiveTheme": effectiveTheme, "language": language, "uiFontScale": uiFontScale}
        if self._state:
            self._publish()

    def _publish(self):
        self._revision += 1
        self.stateChanged.emit(self.snapshot())

    def _current(self, run=None):
        return bool(self._page > 0 and self._session > 0 and self._authority() == self.epochs
                    and (run is None or run == self._run))

    @staticmethod
    def _ack(error="OK"):
        return {"accepted": error == "OK", "errorCode": error}

    def action(self, action, flow_id, *arguments):
        if not self._current():
            return self._ack("SESSION_REQUIRED")
        if type(flow_id) is not str or flow_id != self._state["flowId"]:
            return self._ack("STALE_FLOW")
        if action == "cancel":
            self.cancel()
            return self._ack()
        if action == "restart":
            if arguments:
                return self._ack("INVALID_ARGUMENT")
            if self.active or self._state["phase"] not in {"FAILED", "CANCELLED"}:
                return self._ack("REQUEST_BUSY")
            page, session = self.epochs
            role, kind = self._state["role"], self._state["transport"]
            return self._ack() if self.bind(page, session, role=role, transport=kind) else self._ack("SESSION_REQUIRED")
        if action in {"authorizeNetwork", "revokeNetwork"}:
            if arguments or self.active or self._busy() or self._state["phase"] not in {"IDLE", "FAILED", "CANCELLED"}:
                return self._ack("REQUEST_BUSY")
            operation = self._lan_access.request if action == "authorizeNetwork" else self._lan_access.revoke
            if not operation():
                return self._ack("REQUEST_BUSY")
            self._state.update(phase="IDLE", errorCode="NONE")
            self._publish()
            return self._ack()
        if not self._lock_monitor_ready():
            self._fail("LOCK_MONITOR_UNAVAILABLE")
            return self._ack("INTERNAL_FAILURE")
        try:
            if action == "begin":
                return self._begin(*arguments)
            if action == "connectAddress":
                if len(arguments) != 1:
                    return self._ack("INVALID_ARGUMENT")
                if self._state["phase"] not in {"IDLE", "DISCOVERING"}:
                    return self._ack("REQUEST_BUSY")
                if self._state["phase"] == "DISCOVERING" and (self._state["role"], self._state["transport"]) != ("SEND", "LAN"):
                    return self._ack("REQUEST_BUSY")
                if self._state["manualSearching"]:
                    return self._ack("REQUEST_BUSY")
                target = DirectTransferTransport.manual_lan_target(arguments[0])
                if target is None:
                    return self._ack("INVALID_ADDRESS")
                return self._begin("SEND", "LAN", target[0])
            if action == "choose":
                if self._state["phase"] != "DISCOVERING" or self._transport is None or self._state["manualAddress"]:
                    return self._ack("REQUEST_BUSY")
                peer_id, = arguments
                if type(peer_id) is not str or not any(item["peerId"] == peer_id for item in self._state["peers"]):
                    return self._ack("INVALID_ARGUMENT")
                self._choose_peer(peer_id)
                return self._ack()
            if action == "confirm":
                matches, = arguments
                if type(matches) is not bool:
                    return self._ack("INVALID_ARGUMENT")
                if self._state["phase"] != "VERIFYING" or self._state["localConfirmed"]:
                    return self._ack("REQUEST_BUSY")
                if not matches:
                    self.cancel()
                    return self._ack()
                self._state["localConfirmed"] = True
                self._consume(self._protocol.confirm_sas())
                self._publish()
                return self._ack()
            if action == "prepare":
                scope, = arguments
                if scope not in ("ALL", "PASSWORDS", "NOTES") or type(scope) is not str:
                    return self._ack("INVALID_ARGUMENT")
                if (self._state["role"] != "SEND" or self._state["phase"] != "REVIEW"
                        or self._state["offerReady"] or self._state["preparing"] or not self._state["peerVaultName"]):
                    return self._ack("REQUEST_BUSY")
                self._state.update(scope=scope, preparing=True)
                run = self._run
                self._job = self.adapter.export_transfer_snapshot(self._page, self._session, scope,
                    lambda completion: self._deliver_snapshot(run, "send", completion))
                self._publish()
                return self._ack()
            if action == "accept":
                if (self._state["role"] != "RECEIVE" or self._state["phase"] != "REVIEW"
                        or not self._state["offerReady"] or self._state["receiverAccepted"]):
                    return self._ack("REQUEST_BUSY")
                self._consume(self._protocol.send_message({"type": "accept", "sha256": self._offer["sha256"]}))
                self._state["receiverAccepted"] = True
                self._publish()
                return self._ack()
            if action == "send":
                if self._state["role"] != "SEND" or self._state["phase"] != "REVIEW" or not self._state["receiverAccepted"]:
                    return self._ack("REQUEST_BUSY")
                self._start_transfer()
                self._consume(self._protocol.send_message({"type": "start", "sha256": self._offer["sha256"]}))
                return self._ack()
        except DirectTransferError as error:
            self._protocol_error(error)
            return self._ack("INTERNAL_FAILURE")
        except Exception:
            self._fail("INTERNAL_FAILURE")
            return self._ack("INTERNAL_FAILURE")
        return self._ack("INVALID_ARGUMENT")

    def _begin(self, role, kind, manual_address=""):
        if role not in ("SEND", "RECEIVE") or kind not in ("LAN", "BLUETOOTH") or type(role) is not str or type(kind) is not str:
            return self._ack("INVALID_ARGUMENT")
        if self._cleanup_failed:
            return self._ack("INTERNAL_FAILURE")
        if kind == "LAN" and self._lan_access.status not in {"READY", "DEVELOPMENT"}:
            return self._ack("LAN_ACCESS_REQUIRED")
        replaceable = self._state["phase"] == "DISCOVERING" or (
            self._state["phase"] == "IDLE" and bool(self._state["manualAddress"]))
        if self.active and not replaceable or self._busy():
            return self._ack("REQUEST_BUSY")
        phase = self._state["phase"] if manual_address else "DISCOVERING" if role == "SEND" else "WAITING"
        peers = list(self._state["peers"]) if manual_address else []
        vault = self.adapter.transfer_vault_name(self._page, self._session)
        self._stop_activity()
        self._clear_material()
        if self._cleanup_failed:
            self._fail("UNAVAILABLE")
            return self._ack("INTERNAL_FAILURE")
        self._state.update(flowId=secrets.token_hex(16), role=role, transport=kind, scope="ALL",
            phase=phase, peers=peers, sas="", localConfirmed=False,
            peerConfirmed=False, receiverAccepted=False, offerReady=False, preparing=False,
            peerDeviceName="", localVaultName=vault, peerVaultName="", transferredBytes=0, totalBytes=0, errorCode="NONE",
            localAddresses=self._receiving_addresses() if role == "RECEIVE" and kind == "LAN" else [],
            manualAddress=manual_address, manualSearching=bool(manual_address))
        self._device_id = secrets.token_hex(16)
        self._selected_peer = ""
        if role == "RECEIVE":
            self._auth_deadline = self._clock() + 180
            self._timeout.start()
        from PySide6.QtCore import QSysInfo
        name = QSysInfo.machineHostName()
        self._device_name = name if name and len(name) <= 64 and len(name.encode("utf-8")) <= 256 and not any(ord(c) < 32 or 127 <= ord(c) <= 159 for c in name) else "Windows"
        factory = self._transport_factory
        if factory is None:
            factory = DirectTransferTransport
        transport = factory(self._device_id, self._device_name, self)
        self._transport = transport
        run = self._run
        transport.peersChanged.connect(lambda peers: self._peers(run, peers))
        transport.connected.connect(lambda peer: self._connected(run, peer))
        transport.dataReceived.connect(lambda data: self._receive(run, data))
        transport.drained.connect(lambda: self._drained(run))
        transport.failed.connect(lambda code: self._transport_failed(run, code))
        transport.discoveryFinished.connect(lambda: self._discovery_finished(run))
        self._publish()
        started = transport.start(role, kind, manual_address) if manual_address else transport.start(role, kind)
        if not started:
            self._fail("UNAVAILABLE")
        return self._ack()

    def _peers(self, run, peers):
        if self._current(run) and (self._state["phase"] == "DISCOVERING" or self._state["manualSearching"]):
            self._state["peers"] = peers
            if self._state["manualSearching"] and len(peers) == 1:
                self._state["manualSearching"] = False
                self._choose_peer(peers[0]["peerId"])
            else:
                self._publish()

    def _choose_peer(self, peer_id):
        self._selected_peer = peer_id
        self._state["phase"] = "CONNECTING"
        self._auth_deadline = self._clock() + 20
        self._timeout.start()
        self._publish()
        if not self._transport.choose_peer(peer_id):
            self._fail("CONNECT_FAILED")

    def _discovery_finished(self, run):
        if self._current(run) and self._state["phase"] in {"IDLE", "DISCOVERING"} and self._state["manualSearching"]:
            self._state.update(manualSearching=False, errorCode="ADDRESS_NOT_FOUND")
            self._publish()

    def _connected(self, run, _peer):
        if not self._current(run):
            return
        if self._protocol is not None:
            self._fail("INVALID_DATA")
            return
        try:
            self._protocol = DirectTransferSession("SENDER" if self._state["role"] == "SEND" else "RECEIVER",
                                                   self._device_id, self._device_name)
            self._auth_deadline = self._clock() + 180
            self._timeout.start()
            self._state["phase"] = "CONNECTING"
            self._state["localAddresses"] = []
            self._consume(self._protocol.begin())
            self._publish()
        except Exception:
            self._fail("INTERNAL_FAILURE")

    def _receive(self, run, data):
        if not self._current(run) or self._protocol is None:
            return
        try:
            self._consume(self._protocol.receive(data))
        except DirectTransferError as error:
            self._protocol_error(error)
        except Exception:
            self._fail("INTERNAL_FAILURE")

    def _consume(self, result):
        if len(self._outbound) + len(result.outbound) > 8 or any(len(frame) > MAX_INPUT for frame in result.outbound):
            raise DirectTransferError("LIMIT")
        self._outbound.extend(result.outbound)
        changed = False
        for event in result.events:
            fields = event.fields
            if event.type == "peer":
                if self._state["role"] == "SEND" and self._state["transport"] == "LAN" and fields["deviceId"] != self._selected_peer:
                    raise DirectTransferError("AUTH")
                self._state["peerDeviceName"] = fields["name"]
            elif event.type == "sas":
                self._state.update(phase="VERIFYING", sas=" ".join(str(value) for value in fields["numbers"]))
            elif event.type == "authenticated":
                self._auth_deadline = None
                self._state.update(phase="REVIEW", peerConfirmed=True, sas="")
                self._consume(self._protocol.send_message({"type": "metadata", "vaultName": self._state["localVaultName"]}))
            elif event.type == "metadata":
                self._state["peerVaultName"] = fields["vaultName"]
            elif event.type == "offer":
                self._offer = dict(fields)
                self._state.update(scope=fields["scope"], totalBytes=fields["byteCount"], offerReady=True)
            elif event.type == "accept":
                self._state["receiverAccepted"] = True
            elif event.type == "start":
                self._start_transfer()
            elif event.type == "progress":
                self._progress(fields["bytes"])
                continue
            elif event.type == "complete":
                self._state["phase"] = "VERIFYING_PAYLOAD"
                encoded = bytes(event.data)
                event.data.clear()
                event.data = None
                run = self._run
                self._job = self.adapter.install_received_snapshot(self._page, self._session, encoded,
                    self._offer["scope"], self._offer["passwordCount"], self._offer["noteCount"],
                    lambda completion: self._deliver_snapshot(run, "receive", completion))
            elif event.type == "received":
                self._state["phase"] = "SENT"
                self._stop_activity()
                self._clear_material()
            elif event.type == "cancelled":
                if self._handed_over:
                    self._stop_activity()
                    self._clear_material()
                else:
                    self._fail("CANCELLED")
                return
            changed = True
        if changed:
            self._publish()
        self._schedule_pump()

    def _start_transfer(self):
        if not self._current() or not self._lock_monitor_ready() or not self._hold(True, self._session):
            raise DirectTransferError("CLOSED")
        self._holding = True
        self._transfer_started = self._last_progress = self._clock()
        self._state["phase"] = "TRANSFERRING"
        self._publish()

    def _progress(self, amount):
        previous = self._state["transferredBytes"]
        self._state["transferredBytes"] = amount
        self._last_progress = self._clock()
        total = max(1, self._state["totalBytes"])
        if amount * 100 // total != previous * 100 // total:
            self._publish()

    def _schedule_pump(self):
        if self._transport is not None and not self._writing and not self._pump_timer.isActive():
            self._pump_timer.start(0)

    def _pump(self):
        if not self._current() or self._transport is None or self._writing:
            return
        try:
            if not self._outbound and self._payload is not None and self._protocol.phase == "TRANSFERRING":
                offset = self._protocol.sent_bytes
                if offset < len(self._payload):
                    self._outbound.extend(self._protocol.send_chunk(memoryview(self._payload)[offset:offset + MAX_CHUNK]).outbound)
                else:
                    self._outbound.extend(self._protocol.send_message({"type": "finish", "sha256": self._offer["sha256"]}).outbound)
                    self._payload = None
                    self._state["phase"] = "WAIT_RECEIPT"
                    self._publish()
            if self._outbound:
                self._writing = True
                if not self._transport.write(self._outbound.popleft()):
                    self._fail("DISCONNECTED")
        except DirectTransferError as error:
            self._protocol_error(error)
        except Exception:
            self._fail("INTERNAL_FAILURE")

    def _drained(self, run):
        if not self._current(run):
            return
        self._writing = False
        if self._handed_over and not self._outbound:
            self._stop_activity()
            self._clear_material()
            return
        if self._protocol is not None and self._state["role"] == "SEND" and self._transfer_started is not None:
            self._progress(self._protocol.sent_bytes)
        self._schedule_pump()

    def _deliver_snapshot(self, run, kind, completion):
        # 回调先归原生所有者，再排进网页线程；局部撤销不等待该队列清快照。
        with self._completion_lock:
            current = run == self._run and self._page > 0 and self._session > 0
            if current:
                self._pending_completion = completion
        if not current:
            self._discard_completion(completion)
            return
        try:
            self._snapshotFinished.emit(run, kind, completion)
        except RuntimeError:
            with self._completion_lock:
                if self._pending_completion is completion:
                    self._pending_completion = None
            self._discard_completion(completion)

    def _discard_completion(self, completion):
        try:
            self.adapter.discard(completion)
        finally:
            if isinstance(completion.result, dict):
                completion.result.clear()

    @Slot(int, str, object)
    def _snapshot_finished(self, run, kind, completion):
        with self._completion_lock:
            if self._pending_completion is completion:
                self._pending_completion = None
        if not self._current(run):
            if completion.result:
                self._discard_completion(completion)
            return
        self._job = ""
        self._state["preparing"] = False
        if completion.error_code != "OK":
            self._discard_completion(completion)
            code = "REQUEST_BUSY" if completion.error_code == "REQUEST_BUSY" else "LIMIT_EXCEEDED" if "LIMIT" in completion.error_code else "INVALID_DATA"
            self._fail(code)
            return
        try:
            result = completion.result
            if kind == "send":
                payload = result["rawPayload"]
                if type(payload) is not bytes or not 1 <= len(payload) <= MAX_PAYLOAD:
                    raise DirectTransferError("LIMIT")
                self._payload = payload
                self._offer = {"scope": self._state["scope"], "byteCount": len(payload),
                    "passwordCount": result["passwordCount"], "noteCount": result["noteCount"],
                    "sha256": hashlib.sha256(payload).hexdigest()}
                result.clear()
                self._consume(self._protocol.send_message({"type": "offer", **self._offer}))
                self._state.update(offerReady=True, totalBytes=len(payload))
            else:
                if not self._adopt_received(result, self._page, self._session,
                                            self._state["peerDeviceName"]):
                    self._discard_completion(completion)
                    self._fail("INTERNAL_FAILURE")
                    return
                self._handed_over = True
                self._state["phase"] = "RECEIVED"
                self._consume(self._protocol.send_received())
                self._release_hold()
            self._publish()
        except DirectTransferError as error:
            if not self._handed_over:
                self._discard_completion(completion)
            self._protocol_error(error)
        except Exception:
            if not self._handed_over:
                self._discard_completion(completion)
            self._fail("INTERNAL_FAILURE")

    def check_deadlines(self):
        if not self._current():
            self.close()
            return
        now = self._clock()
        expired = bool(self._auth_deadline is not None and now >= self._auth_deadline)
        expired = expired or bool(self._transfer_started is not None and now - self._transfer_started >= 1800)
        expired = expired or bool(self._state.get("phase") == "TRANSFERRING" and now - self._last_progress >= 30)
        if expired:
            self._transport_failed(self._run, "TIMEOUT")
        elif self._state.get("phase") == "WAITING" and self._state.get("transport") == "LAN":
            addresses = self._receiving_addresses()
            if self._state["localAddresses"] != addresses:
                self._state["localAddresses"] = addresses
                self._publish()

    def _receiving_addresses(self):
        candidates = DirectTransferTransport.lan_address_candidates()
        if candidates != self._address_signature:
            statuses = {index: interface_status(index) for index in {row[1] for row in candidates}}
            rows = []
            for address, index, name, kind in candidates:
                status = statuses[index]
                preferred = bool(status and status[1] and (kind == "WIFI" or kind == "ETHERNET" and status[0]))
                rows.append({"address": address, "interfaceIndex": index, "name": name,
                             "kind": kind if preferred else "OTHER", "preferred": preferred})
            self._address_signature = candidates
            self._address_rows = sorted(rows, key=lambda row: (not row["preferred"], row["kind"] != "WIFI",
                                                               row["interfaceIndex"], row["address"]))
        return self._address_rows

    def _transport_failed(self, run, code):
        if not self._current(run):
            return
        if self._handed_over:
            self._stop_activity()
            self._clear_material()
        else:
            self._fail(code if code in {"UNAVAILABLE", "CONNECT_FAILED", "DISCONNECTED", "TIMEOUT", "LIMIT_EXCEEDED", "INVALID_DATA"} else "INTERNAL_FAILURE")

    def _protocol_error(self, error):
        self._fail({"AUTH": "AUTH_FAILED", "LIMIT": "LIMIT_EXCEEDED", "CANCELLED": "CANCELLED"}.get(error.code, "INVALID_DATA"))

    def _fail(self, code):
        handed_over = self._handed_over or self._state.get("phase") == "RECEIVED"
        self._stop_activity()
        self._clear_material()
        if self._cleanup_failed:
            code = "UNAVAILABLE"
        self._state.update(phase="RECEIVED" if handed_over else "CANCELLED" if code == "CANCELLED" else "FAILED",
                           errorCode="NONE" if handed_over else code,
                           sas="", localConfirmed=False, peerConfirmed=False, preparing=False,
                           localAddresses=[], manualSearching=False)
        self._publish()

    def cancel(self):
        # 本地撤销不等待远端响应；已移交的接收快照由比较窗独立持有。
        self._fail("CANCELLED")

    def _release_hold(self):
        if self._holding:
            self._holding = False
            self._hold(False, self._session)

    def _stop_activity(self):
        with self._completion_lock:
            self._run += 1
        self._timeout.stop()
        self._pump_timer.stop()
        transport, self._transport = self._transport, None
        job, self._job = self._job, ""
        if job:
            self._cancel_job = job
        for cleanup in (
            self._lan_access.cancel_pending,
            lambda: transport.close() if transport is not None else None,
            lambda: transport.deleteLater() if transport is not None else None,
            self._release_hold,
        ):
            try:
                if cleanup() is False:
                    self._cleanup_failed = True
            except Exception:
                self._cleanup_failed = True
        self._writing = False

    def _clear_material(self):
        job, self._cancel_job = self._cancel_job, ""
        with self._completion_lock:
            pending, self._pending_completion = self._pending_completion, None
        protocol, self._protocol = self._protocol, None
        failed = False
        for cleanup in (
            lambda: self.adapter.cancel_transfer_snapshot(job) if job else None,
            lambda: self._discard_completion(pending) if pending is not None else None,
            lambda: protocol.close() if protocol is not None else None,
        ):
            try:
                cleanup()
            except Exception:
                failed = True
        self._payload = self._offer = None
        self._outbound.clear()
        self._handed_over = False
        self._auth_deadline = self._transfer_started = None
        self._last_progress = 0.0
        self._address_signature = None
        self._address_rows = []
        self._cleanup_failed = self._cleanup_failed or failed

    def stop_for_security(self):
        self._stop_activity()
        if self._cleanup_failed:
            raise RuntimeError("direct transfer cleanup incomplete")

    def clear_for_security(self):
        self._clear_material()
        self._page = self._session = 0
        self._state.clear()
        if self._cleanup_failed:
            raise RuntimeError("direct transfer cleanup incomplete")

    def close(self):
        self._stop_activity()
        self.clear_for_security()
