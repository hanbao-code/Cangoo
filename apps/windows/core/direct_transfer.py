"""本地直传的有界帧、SAS认证和单次接收；不持有库权限或系统通道。"""
from __future__ import annotations

import base64
from dataclasses import dataclass, field
from functools import wraps
import hashlib
import hmac
import json
import re
import secrets
from typing import Any

from Crypto.Hash import SHA256
from Crypto.Protocol import DH, HPKE
from Crypto.Protocol.KDF import HKDF
from Crypto.PublicKey import ECC


MAX_PAYLOAD = 64 * 1024 * 1024
MAX_CHUNK = 64 * 1024
MAX_FRAME = 65_602
MAX_INPUT = MAX_FRAME + 4
MAX_JSON = 16_384
MAX_RECORDS = 100_000
_ID = re.compile(r"[0-9a-f]{32}\Z")
_DIGEST = re.compile(r"[0-9a-f]{64}\Z")


class DirectTransferError(ValueError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


@dataclass
class DirectTransferEvent:
    type: str
    fields: dict[str, Any] = field(default_factory=dict, repr=False)
    data: bytearray | None = field(default=None, repr=False)


@dataclass
class DirectTransferResult:
    outbound: list[bytes] = field(default_factory=list, repr=False)
    events: list[DirectTransferEvent] = field(default_factory=list, repr=False)


def _check(condition: bool, code: str = "INVALID") -> None:
    if not condition:
        raise DirectTransferError(code)


def _fields(value: dict, *names: str) -> None:
    _check(type(value) is dict and set(value) == set(names))


def _integer(value: Any, low: int, high: int, range_code: str = "INVALID") -> None:
    _check(type(value) is int)
    _check(low <= value <= high, range_code)


def _name(value: Any, characters: int, byte_limit: int) -> None:
    _check(type(value) is str and 1 <= len(value) <= characters)
    _check(not any(ord(c) < 32 or 127 <= ord(c) <= 159 or 0xD800 <= ord(c) <= 0xDFFF for c in value))
    _check(len(value.encode("utf-8")) <= byte_limit)


def _b64(value: bytes) -> str:
    return base64.b64encode(value).decode("ascii").rstrip("=")


def _unb64(value: Any, length: int = 32) -> bytes:
    _check(type(value) is str and len(value) == (length * 8 + 5) // 6)
    try:
        result = base64.b64decode(value + "=" * (-len(value) % 4), validate=True)
    except (ValueError, TypeError):
        raise DirectTransferError("INVALID") from None
    _check(len(result) == length and _b64(result) == value)
    return result


def _canonical(value: dict) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _parse(data: bytes) -> dict:
    _check(0 < len(data) <= MAX_JSON, "LIMIT")

    def pairs(items: list[tuple[str, Any]]) -> dict:
        result = {}
        for key, value in items:
            _check(key not in result)
            result[key] = value
        return result

    def forbidden(_value: str) -> None:
        raise DirectTransferError("INVALID")

    def integer(value: str) -> int:
        _check(len(value) <= 20)
        return int(value)

    try:
        result = json.loads(data.decode("utf-8", "strict"), object_pairs_hook=pairs,
                            parse_int=integer, parse_float=forbidden, parse_constant=forbidden)
        _check(type(result) is dict)
        # 规范化也拒绝由JSON转义引入的孤立代理码点。
        _canonical(result)
        return result
    except (ValueError, UnicodeError, RecursionError) as failure:
        if isinstance(failure, DirectTransferError):
            raise
        raise DirectTransferError("INVALID") from None


def _frame(body: bytes) -> bytes:
    _check(0 < len(body) <= MAX_FRAME, "LIMIT")
    return len(body).to_bytes(4, "big") + body


def _handshake(value: dict) -> bytes:
    data = _canonical(value)
    _check(len(data) <= MAX_JSON, "LIMIT")
    return _frame(b"\x01" + data)


def _operation(method):
    @wraps(method)
    def guarded(self, *args, **kwargs):
        if self.phase in ("CLOSED", "FAILED"):
            raise DirectTransferError("CLOSED")
        try:
            return method(self, *args, **kwargs)
        except DirectTransferError:
            self.close()
            self.phase = "FAILED"
            raise
        except MemoryError:
            self.close()
            self.phase = "FAILED"
            raise DirectTransferError("LIMIT") from None
        except (ValueError, TypeError, OverflowError, UnicodeError, RecursionError):
            self.close()
            self.phase = "FAILED"
            raise DirectTransferError("INVALID") from None
    return guarded


class DirectTransferSession:
    """同一实例由一个串行控制器调用；事件中的完整缓冲交调用方独占。"""

    def __init__(self, role: str, device_id: str, device_name: str):
        _check(role in ("SENDER", "RECEIVER") and type(role) is str)
        _check(type(device_id) is str and _ID.fullmatch(device_id) is not None)
        _name(device_name, 64, 256)
        self.role = role
        self.device_id = device_id
        self.device_name = device_name
        self.phase = "CONNECTING"
        self.sas: list[int] | None = None
        self.peer_id: str | None = None
        self.peer_name: str | None = None
        self.sent_bytes = 0
        self.received_bytes = 0
        self._session: str | None = None
        self._step = "NEW"
        self._wire = bytearray()
        self._length: int | None = None
        self._hpke = ECC.generate(curve="Curve25519")
        self._peer_hpke = None
        self._peer_hpke_text: str | None = None
        self._sas_key = None
        self._peer_sas_text: str | None = None
        self._start: bytes | None = None
        self._commitment: bytes | None = None
        self._shared: bytes | None = None
        self._confirmed = False
        self._peer_confirmed = False
        self._ready_received = False
        self._tx = None
        self._rx = None
        self._rx_enc: bytes | None = None
        self._tx_seq = 0
        self._rx_seq = 0
        self._metadata_sent = False
        self._metadata_received = False
        self._offer: dict | None = None
        self._payload: bytearray | None = None
        self._digest = hashlib.sha256()

    @property
    def authenticated(self) -> bool:
        return self._ready_received and self.phase not in ("CLOSED", "FAILED")

    @property
    def session_id(self) -> str | None:
        return self._session

    def close(self) -> None:
        self._wire.clear()
        self._length = None
        self._payload = None
        self._hpke = self._peer_hpke = self._sas_key = self._shared = None
        self._tx = self._rx = self._rx_enc = None
        self._start = self._commitment = self._peer_sas_text = self._peer_hpke_text = None
        self.sas = None
        self._offer = None
        self._digest = None
        self._confirmed = self._peer_confirmed = self._ready_received = False
        if self.phase != "FAILED":
            self.phase = "CLOSED"

    @_operation
    def begin(self) -> DirectTransferResult:
        _check(self._step == "NEW", "SEQUENCE")
        if self.role == "RECEIVER":
            self._step = "HELLO"
            return DirectTransferResult()
        self._session = secrets.token_hex(16)
        self._step = "WELCOME"
        return DirectTransferResult([_handshake(self._identity("hello"))])

    def _identity(self, kind: str) -> dict:
        return {"type": kind, "version": 1, "session": self._session, "device": self.device_id,
                "name": self.device_name, "hpke": _b64(self._hpke.public_key().export_key(format="raw"))}

    def _start_message(self) -> dict:
        sender, receiver = self._participants()
        return {"type": "start", "version": 1, "session": self._session, "from": sender, "to": receiver,
                "method": "m.sas.v1", "keyAgreement": "curve25519-hkdf-sha256", "hash": "sha256",
                "mac": "hkdf-hmac-sha256.v2", "sas": "decimal"}

    def _participants(self) -> tuple[str, str]:
        return (self.device_id, self.peer_id) if self.role == "SENDER" else (self.peer_id, self.device_id)

    def _take_identity(self, value: dict, kind: str) -> None:
        _fields(value, "type", "version", "session", "device", "name", "hpke")
        _check(value["type"] == kind)
        _integer(value["version"], 1, 1)
        _check(type(value["session"]) is str and _ID.fullmatch(value["session"]) is not None)
        if self._session is not None:
            _check(value["session"] == self._session, "SEQUENCE")
        _check(type(value["device"]) is str and _ID.fullmatch(value["device"]) is not None)
        _check(value["device"] != self.device_id)
        _name(value["name"], 64, 256)
        public = _unb64(value["hpke"])
        try:
            self._peer_hpke = DH.import_x25519_public_key(public)
            shared = DH.key_agreement(eph_priv=self._hpke, eph_pub=self._peer_hpke, kdf=lambda raw: raw)
            _check(any(shared), "AUTH")
        except ValueError:
            raise DirectTransferError("AUTH") from None
        self._peer_hpke_text = value["hpke"]
        self._session = value["session"]
        self.peer_id, self.peer_name = value["device"], value["name"]

    @_operation
    def receive(self, data: bytes | bytearray) -> DirectTransferResult:
        _check(self._step != "NEW", "SEQUENCE")
        _check(isinstance(data, (bytes, bytearray, memoryview)))
        _check(len(data) <= MAX_INPUT, "LIMIT")
        result = DirectTransferResult()
        position = 0
        try:
            while position < len(data):
                target = 4 if self._length is None else self._length + 4
                amount = min(target - len(self._wire), len(data) - position)
                self._wire.extend(data[position:position + amount])
                position += amount
                if self._length is None and len(self._wire) == 4:
                    self._length = int.from_bytes(self._wire, "big")
                    _check(0 < self._length <= MAX_FRAME, "LIMIT")
                if self._length is not None and len(self._wire) == self._length + 4:
                    body = bytes(self._wire[4:])
                    self._wire.clear()
                    self._length = None
                    if body[0] == 1:
                        self._receive_handshake(_parse(body[1:]), result)
                    elif body[0] == 2:
                        self._receive_sealed(body, result)
                    else:
                        raise DirectTransferError("INVALID")
                    if self.phase == "CLOSED":
                        break
            return result
        except Exception:
            for event in result.events:
                if event.data is not None:
                    event.data.clear()
                    event.data = None
            raise

    def _receive_handshake(self, value: dict, result: DirectTransferResult) -> None:
        _check(self._tx is None and not self.authenticated, "SEQUENCE")
        if value.get("type") == "cancel":
            _fields(value, "type", "session", "code")
            _check(self._session is not None and value["session"] == self._session and value["code"] == "CANCELLED")
            self.close()
            result.events.append(DirectTransferEvent("cancelled"))
            return
        if self._step == "HELLO":
            self._take_identity(value, "hello")
            self._step = "START"
            result.outbound.append(_handshake(self._identity("welcome")))
            result.events.append(DirectTransferEvent("peer", {"deviceId": self.peer_id, "name": self.peer_name}))
            return
        _check(value.get("session") == self._session, "SEQUENCE")
        if self._step == "WELCOME":
            self._take_identity(value, "welcome")
            start = self._start_message()
            self._start = _canonical(start)
            self._step = "ACCEPT"
            result.outbound.append(_handshake(start))
            result.events.append(DirectTransferEvent("peer", {"deviceId": self.peer_id, "name": self.peer_name}))
        elif self._step == "START":
            _check(value == self._start_message() and type(value.get("version")) is int)
            self._start = _canonical(value)
            self._sas_key = ECC.generate(curve="Curve25519")
            public = _b64(self._sas_key.public_key().export_key(format="raw"))
            commitment = hashlib.sha256(public.encode("ascii") + self._start).digest()
            self._step = "SENDER_KEY"
            result.outbound.append(_handshake({"type": "accept", "session": self._session, "commitment": _b64(commitment)}))
        elif self._step == "ACCEPT":
            _fields(value, "type", "session", "commitment")
            _check(value["type"] == "accept", "SEQUENCE")
            self._commitment = _unb64(value["commitment"])
            self._sas_key = ECC.generate(curve="Curve25519")
            self._step = "RECEIVER_KEY"
            result.outbound.append(self._key_frame())
        elif self._step in ("SENDER_KEY", "RECEIVER_KEY"):
            _fields(value, "type", "session", "key")
            _check(value["type"] == "key", "SEQUENCE")
            public = _unb64(value["key"])
            try:
                peer_key = DH.import_x25519_public_key(public)
            except ValueError:
                raise DirectTransferError("AUTH") from None
            if self.role == "SENDER":
                expected = hashlib.sha256(value["key"].encode("ascii") + self._start).digest()
                _check(hmac.compare_digest(expected, self._commitment), "AUTH")
            self._peer_sas_text = value["key"]
            try:
                self._shared = bytes(DH.key_agreement(eph_priv=self._sas_key, eph_pub=peer_key, kdf=lambda raw: raw))
            except ValueError:
                raise DirectTransferError("AUTH") from None
            _check(len(self._shared) == 32 and any(self._shared), "AUTH")
            if self.role == "RECEIVER":
                result.outbound.append(self._key_frame())
            self._set_sas()
            self._step = "MAC"
            self.phase = "SAS"
            result.events.append(DirectTransferEvent("sas", {"numbers": list(self.sas)}))
        elif self._step == "MAC":
            _fields(value, "type", "session", "keys", "mac")
            _check(value["type"] == "mac" and not self._peer_confirmed, "SEQUENCE")
            key_id = "hpke:" + self.peer_id
            _fields(value["mac"], key_id)
            expected = self._mac(self.peer_id, self.device_id, key_id, self._peer_hpke_text)
            expected_ids = self._mac(self.peer_id, self.device_id, "KEY_IDS", key_id)
            _check(hmac.compare_digest(_unb64(value["mac"][key_id]), expected)
                   and hmac.compare_digest(_unb64(value["keys"]), expected_ids), "AUTH")
            self._peer_confirmed = True
            self._activate(result)
        else:
            raise DirectTransferError("SEQUENCE")

    def _key_frame(self) -> bytes:
        return _handshake({"type": "key", "session": self._session,
                           "key": _b64(self._sas_key.public_key().export_key(format="raw"))})

    def _set_sas(self) -> None:
        sender, receiver = self._participants()
        public = _b64(self._sas_key.public_key().export_key(format="raw"))
        keys = (public, self._peer_sas_text) if self.role == "SENDER" else (self._peer_sas_text, public)
        info = "|".join(("CANGOO_DIRECT_SAS_V1", sender, keys[0], receiver, keys[1], self._session))
        b = HKDF(self._shared, 5, b"", SHA256, context=info.encode("ascii"))
        self.sas = [(b[0] << 5 | b[1] >> 3) + 1000,
                    ((b[1] & 7) << 10 | b[2] << 2 | b[3] >> 6) + 1000,
                    ((b[3] & 63) << 7 | b[4] >> 1) + 1000]

    def _mac(self, origin: str, target: str, key_id: str, value: str) -> bytes:
        info = "|".join(("CANGOO_DIRECT_MAC_V1", origin, target, self._session, key_id))
        key = HKDF(self._shared, 32, b"", SHA256, context=info.encode("ascii"))
        return hmac.new(key, value.encode("ascii"), hashlib.sha256).digest()

    @_operation
    def confirm_sas(self) -> DirectTransferResult:
        if self._confirmed:
            return DirectTransferResult()
        _check(self.phase == "SAS" and self.sas is not None, "SEQUENCE")
        self._confirmed = True
        key_id = "hpke:" + self.device_id
        public = _b64(self._hpke.public_key().export_key(format="raw"))
        message = {"type": "mac", "session": self._session,
                   "keys": _b64(self._mac(self.device_id, self.peer_id, "KEY_IDS", key_id)),
                   "mac": {key_id: _b64(self._mac(self.device_id, self.peer_id, key_id, public))}}
        result = DirectTransferResult([_handshake(message)])
        self._activate(result)
        return result

    def _direction(self, outgoing: bool) -> tuple[str, str, str, int]:
        sender, receiver = self._participants()
        forward = (self.role == "SENDER") == outgoing
        return (sender, receiver, "SENDER_TO_RECEIVER", 1) if forward else (receiver, sender, "RECEIVER_TO_SENDER", 2)

    def _info(self, outgoing: bool) -> bytes:
        origin, target, direction, _ = self._direction(outgoing)
        return "|".join(("CANGOO_DIRECT_HPKE_V1", self._session, origin, target, direction)).encode("ascii")

    def _aad(self, outgoing: bool, seq: int, enc: bytes) -> bytes:
        direction = self._direction(outgoing)[3]
        return (b"CANGOO_DIRECT_FRAME_V1|" + bytes.fromhex(self._session) + bytes([direction])
                + seq.to_bytes(8, "big") + enc)

    def _activate(self, result: DirectTransferResult) -> None:
        if not (self._confirmed and self._peer_confirmed) or self._tx is not None:
            return
        self._tx = HPKE.new(receiver_key=self._peer_hpke, sender_key=self._hpke,
                            aead_id=HPKE.AEAD.AES256_GCM, info=self._info(True))
        self._step = "READY"
        self.phase = "WAIT_READY"
        result.outbound.append(self._seal_control({"type": "ready"}))
        self._shared = self._sas_key = self._start = self._commitment = None

    def _seal(self, plaintext: bytes) -> bytes:
        _check(self._tx is not None and self._tx_seq < 2 ** 64, "SEQUENCE")
        enc = self._tx.enc
        seq = self._tx_seq
        ciphertext = self._tx.seal(plaintext, self._aad(True, seq, enc))
        self._tx_seq += 1
        return _frame(b"\x02" + seq.to_bytes(8, "big") + enc + ciphertext)

    def _seal_control(self, value: dict) -> bytes:
        plaintext = _canonical(value)
        _check(len(plaintext) <= MAX_JSON, "LIMIT")
        return self._seal(b"\x01" + plaintext)

    def _receive_sealed(self, body: bytes, result: DirectTransferResult) -> None:
        _check(self._tx is not None and len(body) >= 58, "SEQUENCE")
        seq, enc = int.from_bytes(body[1:9], "big"), body[9:41]
        _check(seq == self._rx_seq, "SEQUENCE")
        try:
            if self._rx is None:
                self._rx = HPKE.new(receiver_key=self._hpke, sender_key=self._peer_hpke,
                                    aead_id=HPKE.AEAD.AES256_GCM, enc=enc, info=self._info(False))
                self._rx_enc = enc
            _check(hmac.compare_digest(enc, self._rx_enc), "AUTH")
            plaintext = self._rx.unseal(body[41:], self._aad(False, seq, enc))
        except ValueError:
            raise DirectTransferError("AUTH") from None
        self._rx_seq += 1
        _check(len(plaintext) >= 2)
        if plaintext[0] == 1:
            value = _parse(plaintext[1:])
            if value.get("type") == "cancel":
                self._control(value, outgoing=False, result=result)
            elif not self._ready_received:
                _fields(value, "type")
                _check(value["type"] == "ready" and self.phase == "WAIT_READY", "SEQUENCE")
                self._ready_received = True
                self.phase = "AUTHENTICATED"
                result.events.append(DirectTransferEvent("authenticated"))
            else:
                self._control(value, outgoing=False, result=result)
        elif plaintext[0] == 2:
            _check(self.authenticated and self.role == "RECEIVER" and self.phase == "TRANSFERRING", "SEQUENCE")
            _check(9 < len(plaintext) <= 9 + MAX_CHUNK, "LIMIT")
            offset, chunk = int.from_bytes(plaintext[1:9], "big"), plaintext[9:]
            _check(offset == self.received_bytes, "SEQUENCE")
            end = offset + len(chunk)
            _check(end <= self._offer["byteCount"], "LIMIT")
            self._payload[offset:end] = chunk
            self._digest.update(chunk)
            self.received_bytes = end
            result.events.append(DirectTransferEvent("progress", {"bytes": end}))
        else:
            raise DirectTransferError("INVALID")

    @_operation
    def send_message(self, message: dict) -> DirectTransferResult:
        _check(self.authenticated, "SEQUENCE")
        _check(type(message) is dict and message.get("type") in ("metadata", "offer", "accept", "start", "finish"))
        result = DirectTransferResult()
        self._control(message, outgoing=True, result=result)
        return result

    def _control(self, value: dict, *, outgoing: bool, result: DirectTransferResult) -> None:
        _check(type(value) is dict)
        kind = value.get("type")
        origin = self.role if outgoing else ("RECEIVER" if self.role == "SENDER" else "SENDER")
        if kind == "cancel":
            _fields(value, "type", "code")
            _check(value["code"] == "CANCELLED")
            if outgoing:
                result.outbound.append(self._seal_control(value))
            else:
                result.events.append(DirectTransferEvent("cancelled"))
            self.close()
            return
        if kind == "metadata":
            _fields(value, "type", "vaultName")
            _name(value["vaultName"], 256, 1024)
            _check(self.phase == "AUTHENTICATED", "SEQUENCE")
            _check(not (self._metadata_sent if outgoing else self._metadata_received), "SEQUENCE")
            if outgoing:
                self._metadata_sent = True
            else:
                self._metadata_received = True
        elif kind == "offer":
            _fields(value, "type", "scope", "byteCount", "passwordCount", "noteCount", "sha256")
            _check(origin == "SENDER" and self.phase == "AUTHENTICATED"
                   and self._metadata_sent and self._metadata_received, "SEQUENCE")
            _check(value["scope"] in ("ALL", "PASSWORDS", "NOTES"))
            _integer(value["byteCount"], 1, MAX_PAYLOAD, "LIMIT")
            _integer(value["passwordCount"], 0, MAX_RECORDS, "LIMIT")
            _integer(value["noteCount"], 0, MAX_RECORDS, "LIMIT")
            _check(value["passwordCount"] + value["noteCount"] <= MAX_RECORDS, "LIMIT")
            _check(value["scope"] != "PASSWORDS" or value["noteCount"] == 0)
            _check(value["scope"] != "NOTES" or value["passwordCount"] == 0)
            self._check_digest(value["sha256"])
            self._offer = dict(value)
            self.phase = "OFFERED"
        elif kind in ("accept", "start", "finish", "received"):
            _fields(value, "type", "sha256")
            self._check_digest(value["sha256"])
            _check(self._offer is not None and hmac.compare_digest(value["sha256"], self._offer["sha256"]), "AUTH")
            expected = {"accept": ("RECEIVER", "OFFERED"), "start": ("SENDER", "ACCEPTED"),
                        "finish": ("SENDER", "TRANSFERRING"), "received": ("RECEIVER", "VERIFYING" if outgoing else "WAIT_RECEIPT")}
            expected_role, expected_phase = expected[kind]
            _check(origin == expected_role and self.phase == expected_phase, "SEQUENCE")
            if kind == "accept":
                if self.role == "RECEIVER":
                    self._payload = bytearray(self._offer["byteCount"])
                self.phase = "ACCEPTED"
            elif kind == "start":
                self.phase = "TRANSFERRING"
            elif kind == "finish":
                count = self.sent_bytes if outgoing else self.received_bytes
                _check(count == self._offer["byteCount"], "LIMIT")
                _check(hmac.compare_digest(self._digest.hexdigest(), value["sha256"]), "AUTH")
                self.phase = "WAIT_RECEIPT" if outgoing else "VERIFYING"
                if not outgoing:
                    payload, self._payload = self._payload, None
                    result.events.append(DirectTransferEvent("complete", {"byteCount": count, "sha256": value["sha256"]}, payload))
            else:
                self.phase = "COMPLETE"
        else:
            raise DirectTransferError("INVALID")
        if outgoing:
            result.outbound.append(self._seal_control(value))
        elif kind != "finish":
            result.events.append(DirectTransferEvent(kind, {key: item for key, item in value.items() if key != "type"}))

    @staticmethod
    def _check_digest(value: Any) -> None:
        _check(type(value) is str and _DIGEST.fullmatch(value) is not None)

    @_operation
    def send_chunk(self, data: bytes | bytearray) -> DirectTransferResult:
        _check(self.authenticated and self.role == "SENDER" and self.phase == "TRANSFERRING", "SEQUENCE")
        _check(isinstance(data, (bytes, bytearray, memoryview)))
        _check(1 <= len(data) <= MAX_CHUNK and self.sent_bytes + len(data) <= self._offer["byteCount"], "LIMIT")
        frame = self._seal(b"\x02" + self.sent_bytes.to_bytes(8, "big") + bytes(data))
        self._digest.update(data)
        self.sent_bytes += len(data)
        return DirectTransferResult([frame])

    @_operation
    def send_received(self) -> DirectTransferResult:
        _check(self.authenticated and self._offer is not None, "SEQUENCE")
        result = DirectTransferResult()
        self._control({"type": "received", "sha256": self._offer["sha256"]}, outgoing=True, result=result)
        return result

    @_operation
    def cancel(self) -> DirectTransferResult:
        result = DirectTransferResult()
        if self._tx is not None:
            result.outbound.append(self._seal_control({"type": "cancel", "code": "CANCELLED"}))
        elif self._session is not None:
            result.outbound.append(_handshake({"type": "cancel", "session": self._session, "code": "CANCELLED"}))
        self.close()
        return result
