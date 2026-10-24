"""密码记录分段读取的有界元数据；不保存字段全文或任何片段。"""

from __future__ import annotations

from dataclasses import dataclass
import secrets
import threading
import time
from typing import Callable


FIELD_LIMITS = {
    "PLATFORM": (128, 512),
    "ACCOUNT": (512, 2048),
    "PASSWORD": (1024, 4096),
    "NOTES": (8192, 32768),
    "NOTE_TITLE": (256, 1024),
    "NOTE_CONTENT": (65536, 262144),
}
CHUNK_CHARACTERS = 8192
CHUNK_UTF8_BYTES = 32768


def field_is_long(field: str, value: str) -> bool:
    """输入上限只判断是否需要长字段路径，不拒绝读取已有值。"""
    characters, byte_limit = FIELD_LIMITS[field]
    return len(value) > characters or len(value.encode("utf-8")) > byte_limit


def field_preview(field: str, value: str) -> str:
    """只返回有界预览；调用方必须同时提供长字段标记。"""
    characters, byte_limit = FIELD_LIMITS[field]
    if not field_is_long(field, value):
        return value
    if field == "PASSWORD":
        return ""
    preview = value[:characters - 1]
    while len((preview + "…").encode("utf-8")) > byte_limit:
        preview = preview[:-1]
    return preview + "…"


class FieldReadRejected(ValueError):
    """只携带固定错误码，不包含字段文本。"""


@dataclass(slots=True)
class _Read:
    read_id: str
    binding: tuple[int, int, int, str, str, str]
    next_offset: int
    expires_at: float


class RecordFieldReads:
    """每个适配器最多一个正在读取的字段，按版本和用途严格顺序取段。"""

    def __init__(self, *, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        self._lock = threading.RLock()
        self._active: _Read | None = None

    def take(
        self,
        *,
        page_epoch: int,
        session_epoch: int,
        record_id: int,
        revision: str,
        field: str,
        authority_lease_id: str,
        read_id: str,
        offset: int,
        value: str,
        cancelled: threading.Event,
    ) -> dict[str, object]:
        # ponytail: 每片由调用方重读同一行，极长字段会重复解密；实测不足再优化，当前不缓存明文。
        binding = (
            page_epoch, session_epoch, record_id, revision, field, authority_lease_id,
        )
        with self._lock:
            if cancelled.is_set():
                if self._active is not None and self._active.binding == binding:
                    self._active = None
                raise FieldReadRejected("CANCELLED")
            if field not in FIELD_LIMITS or type(offset) is not int or offset < 0:
                raise FieldReadRejected("INVALID_ARGUMENT")
            if self._active is not None and self._active.expires_at <= self._clock():
                self._active = None
            if not read_id:
                if offset != 0:
                    raise FieldReadRejected("INVALID_ARGUMENT")
                if self._active is not None:
                    raise FieldReadRejected("REQUEST_BUSY")
                self._active = _Read(
                    secrets.token_urlsafe(24), binding, 0, self._clock() + 300.0,
                )
            current = self._active
            if current is None or (read_id and current.read_id != read_id):
                raise FieldReadRejected("SECRET_LEASE_EXPIRED")
            if current.binding != binding or current.next_offset != offset or offset > len(value):
                self._active = None
                raise FieldReadRejected("INVALID_ARGUMENT")
            chunk = value[offset:offset + CHUNK_CHARACTERS]
            while len(chunk.encode("utf-8")) > CHUNK_UTF8_BYTES:
                chunk = chunk[:-1]
            next_offset = offset + len(chunk)
            done = next_offset == len(value)
            result = {
                "readId": current.read_id,
                "text": chunk,
                "nextOffset": next_offset,
                "done": done,
            }
            if done:
                self._active = None
            else:
                current.next_offset = next_offset
            return result

    def release(self, read_id: str, *, page_epoch: int, session_epoch: int) -> bool:
        with self._lock:
            current = self._active
            if current is None:
                return True
            if current.read_id != read_id or current.binding[:2] != (page_epoch, session_epoch):
                return False
            self._active = None
            return True

    def revoke_lease(self, lease_id: str) -> None:
        with self._lock:
            if self._active is not None and self._active.binding[-1] == lease_id:
                self._active = None

    def clear(self) -> None:
        with self._lock:
            self._active = None


__all__ = [
    "FIELD_LIMITS", "FieldReadRejected", "RecordFieldReads", "field_is_long", "field_preview",
]
