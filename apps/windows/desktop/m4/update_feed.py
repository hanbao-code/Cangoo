"""公开发行资料的严格筛选及有界匿名查询。"""

from __future__ import annotations

from datetime import datetime
import json
import re
import time

from PySide6.QtCore import QObject, QTimer, Qt, QUrl, Signal
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest


RELEASES_API = "https://api.github.com/repos/hanbao-code/Cangoo/releases"
RELEASES_WEB = "https://github.com/hanbao-code/Cangoo/releases/tag/"
API_VERSION = b"2026-03-10"
USER_AGENT = b"Cangoo-Version-Check"
PAGE_SIZE = 100
MAX_PAGES = 10
MAX_RESPONSE_BYTES = 4 * 1024 * 1024
MAX_NOTES_LENGTH = 4096
TOTAL_TIMEOUT_MS = 20_000
IDLE_TIMEOUT_MS = 5_000
READ_CHUNK_BYTES = 64 * 1024

_VERSION = re.compile(r"(0|[1-9][0-9]{0,9})\.(0|[1-9][0-9]{0,9})\.(0|[1-9][0-9]{0,9})")
_PUBLISHED_AT = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}"
    r"(?:\.[0-9]{1,9})?(?:Z|[+-](?:[01][0-9]|2[0-3]):[0-5][0-9])"
)
_LINK_PARAMETER = re.compile(
    rb'<[^<>]*>|;\s*([A-Za-z][A-Za-z0-9_-]*)\s*=\s*("(?:[^"\\]|\\.)*"|[^;,\s]+)'
    rb'|"(?:[^"\\]|\\.)*"'
)


def parse_version(value: str) -> tuple[int, int, int] | None:
    if not isinstance(value, str) or not _VERSION.fullmatch(value):
        return None
    parts = tuple(int(part) for part in value.split("."))
    return parts if all(part <= 2_147_483_647 for part in parts) else None


def _tag_version(tag: str) -> str | None:
    if tag == "v1.0.0":
        return "1.0.0"
    if isinstance(tag, str) and tag.startswith("windows-v"):
        version = tag[len("windows-v"):]
        if parse_version(version) is not None:
            return version
    return None


def release_url(tag: str) -> str:
    if _tag_version(tag) is None:
        raise ValueError("invalid release tag")
    return RELEASES_WEB + tag


def validate_release_result(value: dict) -> dict:
    """缓存与网络共用同一公开结果边界；不接受附带网址或额外字段。"""
    if not isinstance(value, dict) or set(value) != {"version", "tag", "publishedAt", "notes"}:
        raise ValueError("invalid release result")
    if parse_version(value["version"]) is None or _tag_version(value["tag"]) != value["version"]:
        raise ValueError("invalid release version")
    published = value["publishedAt"]
    if not isinstance(published, str) or not _PUBLISHED_AT.fullmatch(published):
        raise ValueError("invalid publication date")
    try:
        # Python 3.10 的日期校验不支持任意小数秒精度。
        datetime.fromisoformat(re.sub(r"\.[0-9]+", "", published).replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError("invalid publication date") from error
    notes = value["notes"]
    if (not isinstance(notes, str) or len(notes) > MAX_NOTES_LENGTH or "\x00" in notes
            or any(0xD800 <= ord(char) <= 0xDFFF for char in notes)):
        raise ValueError("invalid release notes")
    return dict(value)


def _json_object(pairs: list[tuple[str, object]]) -> dict:
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("duplicate JSON field")
        value[key] = item
    return value


def _invalid_constant(_value: str):
    raise ValueError("invalid JSON number")


def parse_release_page(data: bytes) -> list[dict]:
    """保留未筛选条目数，保证跨平台条目不会提前结束分页。"""
    if not isinstance(data, bytes) or len(data) > MAX_RESPONSE_BYTES:
        raise ValueError("invalid release response")
    try:
        values = json.loads(data.decode("utf-8"), object_pairs_hook=_json_object,
                            parse_constant=_invalid_constant)
    except (UnicodeError, ValueError, RecursionError) as error:
        raise ValueError("invalid release response") from error
    if not isinstance(values, list) or len(values) > PAGE_SIZE:
        raise ValueError("invalid release page")
    for value in values:
        if (not isinstance(value, dict) or not isinstance(value.get("tag_name"), str)
                or type(value.get("draft")) is not bool
                or type(value.get("prerelease")) is not bool):
            raise ValueError("invalid release entry")
    return values


def _release_result(value: dict) -> dict | None:
    if value["draft"] or value["prerelease"]:
        return None
    version = _tag_version(value["tag_name"])
    if version is None:
        return None
    assets = value.get("assets")
    if not isinstance(assets, list):
        raise ValueError("missing release assets")
    uploaded = {
        asset.get("name") for asset in assets
        if isinstance(asset, dict) and isinstance(asset.get("name"), str)
        and asset.get("state") == "uploaded" and type(asset.get("size")) is int
        and asset["size"] > 0
    }
    packages = {f"cangoo-{version}-windows-x64-setup.exe",
                f"cangoo-{version}-windows-x64-portable.zip"}
    if "sha256sums.txt" not in uploaded or not packages.intersection(uploaded):
        raise ValueError("missing release assets")
    notes = value.get("body")
    if notes is None:
        notes = ""
    if not isinstance(notes, str):
        raise ValueError("invalid release notes")
    return validate_release_result({"version": version, "tag": value["tag_name"],
                                    "publishedAt": value.get("published_at"),
                                    "notes": notes[:MAX_NOTES_LENGTH]})


def _release_key(value: dict) -> tuple:
    return parse_version(value["version"]), value["tag"] != "v1.0.0"


def select_latest_release(releases: list[dict]) -> dict | None:
    latest = None
    for value in releases:
        result = _release_result(value)
        if result is not None and (latest is None or _release_key(result) > _release_key(latest)):
            latest = result
    return latest


def _has_next_link(header: bytes) -> bool:
    # 跳过目标网址和其他引号字段，只将关系标记用于是否继续分页。
    for parameter in _LINK_PARAMETER.finditer(header):
        if parameter[1] is None or parameter[1].lower() != b"rel":
            continue
        relations = parameter[2]
        if relations.startswith(b'"'):
            relations = re.sub(rb"\\(.)", rb"\1", relations[1:-1])
        if b"next" in relations.lower().split():
            return True
    return False


class UpdateFeedClient(QObject):
    """每个实例仅执行一次；控制器决定何时启动及是否保留结果。"""

    finished = Signal(object, str)

    def __init__(self, parent: QObject | None = None, *, network_manager=None):
        super().__init__(parent)
        self._manager = network_manager if network_manager is not None else QNetworkAccessManager(self)
        self._reply = None
        self._started = False
        self._done = False
        self._page = 0
        self._received = 0
        self._buffer = bytearray()
        self._latest = None
        self._deadline = 0.0
        self._idle_deadline = 0.0
        self._total_timer = QTimer(self)
        self._total_timer.setSingleShot(True)
        self._total_timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._total_timer.timeout.connect(lambda: self._finish("TIMEOUT"))
        self._idle_timer = QTimer(self)
        self._idle_timer.setSingleShot(True)
        self._idle_timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._idle_timer.timeout.connect(lambda: self._finish("TIMEOUT"))
        self._manager.authenticationRequired.connect(
            lambda reply, _auth: self._finish_if_current(reply, "NETWORK"))
        self._manager.proxyAuthenticationRequired.connect(
            lambda _proxy, _auth: self._finish_if_current(self._reply, "NETWORK")
            if self._reply is not None else None)

    def start(self) -> None:
        if self._started or self._done:
            return
        self._started = True
        self._deadline = time.monotonic() + TOTAL_TIMEOUT_MS / 1000
        self._total_timer.start(TOTAL_TIMEOUT_MS)
        self._request_page()

    def cancel(self) -> None:
        self._finish("CANCELLED")

    def _request_page(self) -> None:
        self._page += 1
        request = QNetworkRequest(QUrl(f"{RELEASES_API}?per_page={PAGE_SIZE}&page={self._page}"))
        request.setRawHeader(b"Accept", b"application/vnd.github+json")
        request.setRawHeader(b"Accept-Encoding", b"identity")
        request.setRawHeader(b"User-Agent", USER_AGENT)
        request.setRawHeader(b"X-GitHub-Api-Version", API_VERSION)
        for attribute in (QNetworkRequest.Attribute.CookieLoadControlAttribute,
                          QNetworkRequest.Attribute.CookieSaveControlAttribute,
                          QNetworkRequest.Attribute.AuthenticationReuseAttribute):
            request.setAttribute(attribute, QNetworkRequest.LoadControl.Manual)
        request.setAttribute(QNetworkRequest.Attribute.UseCredentialsAttribute, False)
        request.setAttribute(QNetworkRequest.Attribute.RedirectPolicyAttribute,
                             QNetworkRequest.RedirectPolicy.ManualRedirectPolicy)
        request.setAttribute(QNetworkRequest.Attribute.CacheLoadControlAttribute,
                             QNetworkRequest.CacheLoadControl.AlwaysNetwork)
        request.setAttribute(QNetworkRequest.Attribute.CacheSaveControlAttribute, False)
        request.setTransferTimeout(IDLE_TIMEOUT_MS)
        self._idle_deadline = time.monotonic() + IDLE_TIMEOUT_MS / 1000
        self._idle_timer.start(IDLE_TIMEOUT_MS)
        try:
            reply = self._manager.get(request)
        except (RuntimeError, OSError):
            self._finish("NETWORK")
            return
        self._reply = reply
        reply.setReadBufferSize(READ_CHUNK_BYTES)
        reply.metaDataChanged.connect(lambda: self._response_ok(reply))
        reply.readyRead.connect(lambda: self._read(reply))
        reply.sslErrors.connect(lambda _errors: self._finish_if_current(reply, "NETWORK"))
        reply.finished.connect(lambda: self._completed(reply))

    def _finish_if_current(self, reply, error: str) -> None:
        if reply is self._reply:
            self._finish(error)

    def _within_deadline(self) -> bool:
        if self._done:
            return False
        now = time.monotonic()
        if now >= self._deadline or now >= self._idle_deadline:
            self._finish("TIMEOUT")
            return False
        return True

    def _response_ok(self, reply) -> bool:
        if reply is not self._reply or not self._within_deadline():
            return False
        status = reply.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute)
        if status is None:
            return False
        if status != 200:
            limited = status == 429 or (status == 403 and (
                bytes(reply.rawHeader("X-RateLimit-Remaining")) == b"0"
                or bool(reply.rawHeader("Retry-After"))))
            self._finish("RATE_LIMITED" if limited else "NETWORK")
            return False
        if bytes(reply.rawHeader("Content-Encoding")).strip().lower() not in (b"", b"identity"):
            self._finish("INVALID_RESPONSE")
            return False
        return True

    def _read(self, reply) -> None:
        if not self._response_ok(reply):
            return
        while reply.bytesAvailable() > 0:
            remaining = MAX_RESPONSE_BYTES - self._received
            chunk = bytes(reply.read(min(READ_CHUNK_BYTES, remaining + 1)))
            if not chunk:
                break
            self._received += len(chunk)
            if self._received > MAX_RESPONSE_BYTES:
                self._finish("INCOMPLETE")
                return
            self._buffer.extend(chunk)
            self._idle_deadline = time.monotonic() + IDLE_TIMEOUT_MS / 1000
            self._idle_timer.start(IDLE_TIMEOUT_MS)
            if not self._within_deadline():
                return

    def _completed(self, reply) -> None:
        if reply is not self._reply or not self._within_deadline():
            return
        error = reply.error()
        if error == QNetworkReply.NetworkError.TimeoutError:
            self._finish("TIMEOUT")
            return
        if error != QNetworkReply.NetworkError.NoError:
            if not self._response_ok(reply) and self._done:
                return
            self._finish("NETWORK")
            return
        if not self._response_ok(reply):
            if not self._done:
                self._finish("INVALID_RESPONSE")
            return
        self._read(reply)
        if self._done:
            return
        try:
            releases = parse_release_page(bytes(self._buffer))
            latest = select_latest_release(releases)
        except ValueError:
            self._finish("INVALID_RESPONSE")
            return
        if latest is not None and (self._latest is None or _release_key(latest) > _release_key(self._latest)):
            self._latest = latest
        has_next = len(releases) >= PAGE_SIZE or _has_next_link(bytes(reply.rawHeader("Link")))
        self._reply = None
        reply.deleteLater()
        self._buffer.clear()
        if not self._within_deadline():
            return
        if not has_next:
            self._finish("NONE", self._latest)
        elif self._page >= MAX_PAGES:
            self._finish("INCOMPLETE")
        else:
            self._request_page()

    def _finish(self, error: str, result=None) -> None:
        if self._done:
            return
        self._done = True
        self._total_timer.stop()
        self._idle_timer.stop()
        reply, self._reply = self._reply, None
        if reply is not None:
            if not reply.isFinished():
                reply.abort()
            reply.deleteLater()
        self._buffer.clear()
        self._latest = None
        self.finished.emit(result, error)
