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
                 adopt_received, parent=None, transport_factory=None, clock=time.monotonic, lan_access=None,
                 clipboard=None):
        super().__init__(parent)
        self.adapter = adapter
        self._authority, self._lock_monitor_ready, self._busy = authority, lock_monitor_ready, busy
        self._hold, self._adopt_received = hold, adopt_received
        self._transport_factory = transport_factory
        self._clock = clock
        self._clipboard = clipboard
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
        self._selected_target = None
        self._pairing_code = ""
        self._candidates = {}
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
            "scope": "ALL", "peers": [], "pairingCode": "",
            "receiverAccepted": False, "offerReady": False, "preparing": False,
            "peerDeviceName": "", "localVaultName": vault, "peerVaultName": "",
            "transferredBytes": 0, "totalBytes": 0, "errorCode": "NONE",
            "passwordCount": 0, "noteCount": 0,
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
        if action == "copyPairingCode":
            if arguments:
                return self._ack("COPY_FAILED")
            if (self._clipboard is None or not self._lock_monitor_ready()
                    or self._state["role"] != "RECEIVE" or self._state["phase"] != "WAITING"
                    or self._transport is None or self._protocol is not None
                    or self._auth_deadline is None or self._clock() >= self._auth_deadline
                    or len(self._pairing_code) != 8 or not all("0" <= digit <= "9" for digit in self._pairing_code)):
                return self._ack("COPY_FAILED")
            try:
                token = self._clipboard.publication_token(page_epoch=self._page, session_epoch=self._session)
                if token and self._clipboard.copy(self._pairing_code, "PASSWORD", publication_token=token) is not None:
                    return self._ack()
            except Exception:
                pass
            return self._ack("COPY_FAILED")
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
            if action == "pairingCode":
                code, = arguments
                if type(code) is not str or len(code) != 8 or not all("0" <= digit <= "9" for digit in code):
                    return self._ack("INVALID_PAIRING_CODE")
                if self._state["role"] != "SEND" or self._state["phase"] != "PAIRING_CODE":
                    return self._ack("REQUEST_BUSY")
                self._pairing_code = code
                self._state.update(phase="CONNECTING", errorCode="NONE")
                self._auth_deadline = self._clock() + 20
                self._timeout.start()
                self._publish()
                if self._transport is None:
                    transport = self._new_transport()
                    started = transport.connect_target(self._selected_peer, self._selected_target, self._state["transport"], self._state["manualAddress"])
                else:
                    started = self._transport.choose_peer(self._selected_peer)
                if not started:
                    self._retry_sender("CONNECT_FAILED")
                return self._ack()
            if action == "approve":
                if arguments:
                    return self._ack("INVALID_ARGUMENT")
                if self._state["role"] != "RECEIVE" or self._state["phase"] != "WAIT_APPROVAL":
                    return self._ack("REQUEST_BUSY")
                self._consume(self._protocol.approve_peer())
                return self._ack()
            if action == "send":
                scope, = arguments
                if scope not in ("ALL", "PASSWORDS", "NOTES", "CUSTOM") or type(scope) is not str:
                    return self._ack("INVALID_ARGUMENT")
                if (self._state["role"] != "SEND" or self._state["phase"] != "REVIEW"
                        or self._state["offerReady"] or self._state["preparing"] or not self._state["peerVaultName"]):
                    return self._ack("REQUEST_BUSY")
                self._state.update(scope=scope, preparing=True, errorCode="NONE")
                run = self._run
                self._job = self.adapter.export_transfer_snapshot(self._page, self._session, scope,
                    lambda completion: self._deliver_snapshot(run, "send", completion))
                self._publish()
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
            phase=phase, peers=peers, pairingCode="", receiverAccepted=False, offerReady=False, preparing=False,
            peerDeviceName="", localVaultName=vault, peerVaultName="", transferredBytes=0, totalBytes=0, errorCode="NONE",
            localAddresses=self._receiving_addresses() if role == "RECEIVE" and kind == "LAN" else [],
            manualAddress=manual_address, manualSearching=bool(manual_address))
        self._device_id = secrets.token_hex(16)
        self._selected_peer = ""
        self._selected_target = None
        if role == "RECEIVE":
            self._pairing_code = f"{secrets.randbelow(100_000_000):08d}"
            self._state["pairingCode"] = self._pairing_code
            self._auth_deadline = self._clock() + 600
            self._timeout.start()
        from PySide6.QtCore import QSysInfo
        name = QSysInfo.machineHostName()
        self._device_name = name if name and len(name) <= 64 and len(name.encode("utf-8")) <= 256 and not any(ord(c) < 32 or 127 <= ord(c) <= 159 for c in name) else "Windows"
        transport = self._new_transport()
        self._publish()
        started = transport.start(role, kind, manual_address) if manual_address else transport.start(role, kind)
        if not started:
            self._fail("UNAVAILABLE")
        return self._ack()

    def _new_transport(self):
        factory = self._transport_factory or DirectTransferTransport
        transport = factory(self._device_id, self._device_name, self)
        self._transport = transport
        run = self._run
        transport.peersChanged.connect(lambda peers: self._peers(run, peers))
        transport.connected.connect(lambda peer: self._connected(run, peer))
        transport.dataReceived.connect(lambda data: self._receive(run, data))
        transport.drained.connect(lambda: self._drained(run))
        transport.failed.connect(lambda code: self._transport_failed(run, code))
        transport.discoveryFinished.connect(lambda: self._discovery_finished(run))
        transport.candidateConnected.connect(lambda candidate: self._candidate_connected(run, candidate))
        transport.candidateData.connect(lambda candidate, data: self._candidate_receive(run, candidate, data))
        transport.candidateFailed.connect(lambda candidate, _code: self._candidate_gone(run, candidate))
        transport.candidateDrained.connect(lambda candidate: self._candidate_drain(run, candidate))
        return transport

    def _peers(self, run, peers):
        if self._current(run) and (self._state["phase"] == "DISCOVERING" or self._state["manualSearching"]):
            self._state["peers"] = peers
            if self._state["manualSearching"] and len(peers) == 1:
                self._state["manualSearching"] = False
                self._choose_peer(peers[0]["peerId"])
            else:
                self._publish()

    def _choose_peer(self, peer_id):
        peer = next(item for item in self._state["peers"] if item["peerId"] == peer_id)
        if peer.get("legacy"):
            self._state.update(errorCode="UPGRADE_REQUIRED", manualSearching=False)
            self._publish()
            return
        self._selected_peer = peer_id
        self._selected_target = self._transport.peer_target(peer_id)
        self._state.update(phase="PAIRING_CODE", peerDeviceName=peer["name"], errorCode="NONE", manualSearching=False)
        self._publish()

    def _discovery_finished(self, run):
        if self._current(run) and self._state["phase"] in {"IDLE", "DISCOVERING"} and self._state["manualSearching"]:
            self._state.update(manualSearching=False, errorCode="ADDRESS_NOT_FOUND")
            self._publish()

    def _connected(self, run, _peer):
        if not self._current(run):
            return
        if self._protocol is not None or self._state["role"] != "SEND":
            self._fail("INVALID_DATA")
            return
        try:
            self._protocol = DirectTransferSession("SENDER", self._device_id, self._device_name, self._pairing_code)
            self._pairing_code = ""
            self._auth_deadline = self._clock() + 10
            self._timeout.start()
            self._consume(self._protocol.begin())
        except Exception:
            self._fail("INTERNAL_FAILURE")

    def _candidate_connected(self, run, candidate):
        if not self._current(run) or self._protocol is not None or self._state["phase"] != "WAITING":
            return
        if self._auth_deadline is None or self._clock() >= self._auth_deadline:
            self._fail("TIMEOUT")
            return
        try:
            protocol = DirectTransferSession("RECEIVER", self._device_id, self._device_name, self._pairing_code)
            self._candidates[candidate] = [protocol, deque(), ""]
            result = protocol.begin()
            self._candidate_result(run, candidate, result)
        except Exception:
            self._candidate_gone(run, candidate)
            if self._transport is not None:
                self._transport.reject_candidate(candidate)

    def _candidate_receive(self, run, candidate, data):
        if not self._current(run) or candidate not in self._candidates:
            return
        try:
            self._candidate_result(run, candidate, self._candidates[candidate][0].receive(data))
        except Exception:
            self._candidate_gone(run, candidate)
            if self._transport is not None:
                self._transport.reject_candidate(candidate)

    def _candidate_result(self, run, candidate, result):
        if not self._transport.candidate_alive(candidate):
            return
        protocol, queue, _name = self._candidates[candidate]
        if any(event.type == "cancelled" for event in result.events):
            self._candidate_gone(run, candidate)
            self._transport.reject_candidate(candidate)
            return
        for event in result.events:
            if event.type == "peer":
                self._transport.mark_candidate_hello(candidate)
                self._candidates[candidate][2] = event.fields["name"]
        if protocol.authenticated:
            if self._auth_deadline is None or self._clock() >= self._auth_deadline:
                self._fail("TIMEOUT")
                return
            self._protocol = protocol
            del self._candidates[candidate]
            for other in list(self._candidates):
                self._candidate_gone(run, other)
            self._pairing_code = ""
            self._state.update(pairingCode="", peerDeviceName=_name or next((event.fields["name"] for event in result.events if event.type == "peer"), ""))
            self._auth_deadline = None
            self._writing = self._transport.candidate_writing(candidate)
            self._outbound.extend(queue)
            if not self._transport.promote_candidate(candidate):
                self._fail("UNAVAILABLE")
                return
            self._consume(result)
            return
        if len(queue) + len(result.outbound) > 8:
            raise DirectTransferError("LIMIT")
        queue.extend(result.outbound)
        self._candidate_drain(run, candidate)

    def _candidate_drain(self, run, candidate):
        if not self._current(run) or candidate not in self._candidates:
            return
        queue = self._candidates[candidate][1]
        if queue and not self._transport.candidate_writing(candidate):
            if not self._transport.write_candidate(candidate, queue.popleft()):
                self._candidate_gone(run, candidate)
                self._transport.reject_candidate(candidate)

    def _candidate_gone(self, run, candidate):
        if not self._current(run):
            return
        entry = self._candidates.pop(candidate, None)
        if entry is not None:
            entry[0].close()
            entry[1].clear()

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
            elif event.type == "authenticated":
                self._auth_deadline = None
                self._pairing_code = ""
                self._state.update(phase="WAIT_APPROVAL", pairingCode="", localAddresses=[])
            elif event.type == "approved":
                self._state["phase"] = "REVIEW"
                self._consume(self._protocol.send_message({"type": "metadata", "vaultName": self._state["localVaultName"]}))
            elif event.type == "metadata":
                self._state["peerVaultName"] = fields["vaultName"]
            elif event.type == "offer":
                self._offer = dict(fields)
                self._state.update(scope=fields["scope"], totalBytes=fields["byteCount"], offerReady=True,
                                   passwordCount=fields["passwordCount"], noteCount=fields["noteCount"])
                self._consume(self._protocol.send_message({"type": "accept", "sha256": self._offer["sha256"]}))
                self._state["receiverAccepted"] = True
            elif event.type == "accept":
                self._state["receiverAccepted"] = True
                self._start_transfer()
                self._consume(self._protocol.send_message({"type": "start", "sha256": self._offer["sha256"]}))
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
                if self._state["role"] == "RECEIVE" and self._state["phase"] == "VERIFYING_PAYLOAD":
                    self._close_channel()
                elif self._handed_over:
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
            if kind == "send" and completion.error_code == "REVISION_CONFLICT":
                self._state.update(errorCode="REVISION_CONFLICT", preparing=False)
                self._publish()
                return
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
                self._offer = {"scope": result.get("scope", self._state["scope"]), "byteCount": len(payload),
                    "passwordCount": result["passwordCount"], "noteCount": result["noteCount"],
                    "sha256": hashlib.sha256(payload).hexdigest()}
                result.clear()
                self._consume(self._protocol.send_message({"type": "offer", **self._offer}))
                self._state.update(offerReady=True, totalBytes=len(payload),
                                   passwordCount=self._offer["passwordCount"], noteCount=self._offer["noteCount"])
            else:
                if not self._adopt_received(result, self._page, self._session,
                                            self._state["peerDeviceName"]):
                    self._discard_completion(completion)
                    self._fail("INTERNAL_FAILURE")
                    return
                self._handed_over = True
                self._state["phase"] = "RECEIVED"
                if self._transport is None:
                    self._stop_activity()
                    self._clear_material()
                else:
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
        if code == "DISCONNECTED" and self._state.get("role") == "RECEIVE" and self._state.get("phase") == "VERIFYING_PAYLOAD":
            self._close_channel()
        elif self._handed_over:
            self._stop_activity()
            self._clear_material()
        elif self._state.get("role") == "SEND" and self._state.get("phase") == "CONNECTING":
            self._retry_sender(code if code in {"CONNECT_FAILED", "DISCONNECTED", "TIMEOUT"} else "INTERNAL_FAILURE")
        else:
            self._fail(code if code in {"UNAVAILABLE", "CONNECT_FAILED", "DISCONNECTED", "TIMEOUT", "LIMIT_EXCEEDED", "INVALID_DATA"} else "INTERNAL_FAILURE")

    def _close_channel(self):
        # 完整来源已归本地校验；关闭通道不改变原会话、任务代次或取消资格。
        transport, self._transport = self._transport, None
        protocol, self._protocol = self._protocol, None
        self._pump_timer.stop()
        self._outbound.clear()
        self._writing = False
        for cleanup in (
            lambda: transport.close() if transport is not None else None,
            lambda: transport.deleteLater() if transport is not None else None,
            lambda: protocol.close() if protocol is not None else None,
        ):
            try:
                if cleanup() is False:
                    self._cleanup_failed = True
            except Exception:
                self._cleanup_failed = True
        if self._cleanup_failed:
            self._fail("UNAVAILABLE")

    def _protocol_error(self, error):
        code = {"AUTH": "AUTH_FAILED", "LIMIT": "LIMIT_EXCEEDED", "CANCELLED": "CANCELLED",
                "UPGRADE_REQUIRED": "UPGRADE_REQUIRED"}.get(error.code, "INVALID_DATA")
        if self._state.get("role") == "SEND" and self._state.get("phase") == "CONNECTING" and code != "UPGRADE_REQUIRED":
            self._retry_sender(code)
        else:
            self._fail(code)

    def _retry_sender(self, code):
        selected_peer, selected_target = self._selected_peer, self._selected_target
        self._stop_activity()
        self._clear_material()
        self._selected_peer, self._selected_target = selected_peer, selected_target
        if self._cleanup_failed:
            self._state.update(phase="FAILED", pairingCode="", errorCode="UNAVAILABLE", preparing=False, manualSearching=False)
        else:
            self._state.update(phase="PAIRING_CODE", pairingCode="", errorCode=code,
                               preparing=False, manualSearching=False)
        self._publish()

    def _fail(self, code):
        handed_over = self._handed_over or self._state.get("phase") == "RECEIVED"
        self._stop_activity()
        self._clear_material()
        if self._cleanup_failed:
            code = "UNAVAILABLE"
        self._state.update(phase="RECEIVED" if handed_over else "CANCELLED" if code == "CANCELLED" else "FAILED",
                           errorCode="NONE" if handed_over else code,
                           pairingCode="", preparing=False,
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
        candidates, self._candidates = self._candidates, {}
        self._pairing_code = ""
        self._selected_peer, self._selected_target = "", None
        if self._state:
            self._state["pairingCode"] = ""
        failed = False
        for candidate_protocol, queue, _name in candidates.values():
            try:
                candidate_protocol.close()
                queue.clear()
            except Exception:
                failed = True
        for cleanup in (
            lambda: self.adapter.close_export_selection(self._page, self._session) if self._page > 0 and self._session > 0 else None,
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
