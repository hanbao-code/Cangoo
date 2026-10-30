"""产品剪贴板状态及复制任务的原生所有者。"""

from __future__ import annotations

from dataclasses import dataclass, field
import math
import threading
import time
from typing import Callable

from PySide6.QtCore import QObject, QThread, Qt, QTimer, Signal, Slot

from desktop.host.native_capabilities import NativeClipboard


@dataclass
class _PendingCopy:
    text: str
    content_kind: str
    publication_token: int
    cancelled: threading.Event | None
    deadline: float
    settled: threading.Event = field(default_factory=threading.Event)
    result: dict[str, object] | None = None


class ProductClipboardController(QObject):
    """Keep clipboard content, timer and renderer-visible state native-owned."""

    state_changed = Signal(int, int, str, str, int, bool)
    _timer_requested = Signal(bool)
    _copy_requested = Signal(object)
    COPY_WAIT_SECONDS = 10.0

    def __init__(
        self,
        clipboard: NativeClipboard,
        parent: QObject,
        *,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        super().__init__(parent)
        self._clipboard = clipboard
        self._clock = clock
        self._lock = threading.RLock()
        self._page_epoch = 0
        self._session_epoch = 0
        self._authority_serial = 1
        self._pending_copies: dict[int, _PendingCopy] = {}
        self._next_copy_id = 0
        self._mode = "COUNTDOWN"
        self._seconds = 30
        self._content_kind = "NONE"
        self._owned = False
        self._deadline = 0.0
        self._last_remaining = 0
        self._timer = QTimer(self)
        self._timer.setInterval(250)
        self._timer.timeout.connect(self._on_tick)
        self._timer_requested.connect(self._set_timer_active)
        self._copy_requested.connect(self._run_pending_copy, Qt.ConnectionType.QueuedConnection)

    def configure(self, mode: str, seconds: int) -> None:
        normalized_mode = mode if mode in {"COUNTDOWN", "MANUAL"} else "COUNTDOWN"
        normalized_seconds = min(60, max(5, int(seconds)))
        with self._lock:
            self._mode = normalized_mode
            self._seconds = normalized_seconds

    def apply_policy_after_commit(self, mode: str, seconds: int) -> bool:
        """Adopt one committed policy and restart only owned countdowns."""

        if mode not in {"COUNTDOWN", "MANUAL"}:
            raise ValueError("unsupported M4 clipboard mode")
        if type(seconds) is not int or not 5 <= seconds <= 60:
            raise ValueError("invalid M4 clipboard timeout")
        with self._lock:
            if mode == self._mode and seconds == self._seconds:
                return False
            still_owned = False
            if self._owned:
                try:
                    still_owned = self._clipboard.is_owned_by_us()
                except Exception:
                    still_owned = None
            self._mode = mode
            self._seconds = seconds
            if self._owned and still_owned is False:
                self._reset_state_locked()
            elif self._owned and mode == "COUNTDOWN":
                self._deadline = self._clock() + seconds
                self._last_remaining = seconds
            elif self._owned:
                self._deadline = 0.0
                self._last_remaining = 0
            snapshot = self._snapshot_locked()
            timer_active = self._owned and mode == "COUNTDOWN"
        self._timer_requested.emit(timer_active)
        self._emit_snapshot(snapshot)
        return True

    def bind_page(self, page_epoch: int) -> None:
        with self._lock:
            self._revoke_publications_locked()
            self._page_epoch = page_epoch
            self._session_epoch = 0
            self._reset_state_locked()
        self._timer_requested.emit(False)

    def bind_session(self, page_epoch: int, session_epoch: int) -> None:
        with self._lock:
            preserve_owned = self._page_epoch == page_epoch and self._owned
        if preserve_owned:
            try:
                preserve_owned = self._clipboard.is_owned_by_us() is not False
            except Exception:
                preserve_owned = True
        with self._lock:
            self._revoke_publications_locked()
            self._page_epoch = page_epoch
            self._session_epoch = session_epoch
            if not preserve_owned:
                self._reset_state_locked()
            elif self._mode == "COUNTDOWN":
                self._last_remaining = max(
                    0,
                    min(
                        60,
                        int(math.ceil(self._deadline - self._clock())),
                    ),
                )
            snapshot = self._snapshot_locked()
        if preserve_owned and snapshot[4] <= 0 and snapshot[3] == "COUNTDOWN":
            if self.clear_owned() is None:
                self._emit_snapshot(snapshot)
            return
        self._timer_requested.emit(preserve_owned)
        self._emit_snapshot(snapshot)

    def reset_authority(self) -> None:
        """Forget UI/timer state; the security coordinator force-clears next."""

        with self._lock:
            self._revoke_publications_locked()
            self._reset_state_locked()
            self._page_epoch = 0
            self._session_epoch = 0
        self._timer_requested.emit(False)

    def publication_token(
        self,
        *,
        page_epoch: int | None = None,
        session_epoch: int | None = None,
    ) -> int:
        """提交操作时捕获授权；撤权前的后台任务不能借用后来的会话。"""
        with self._lock:
            if (
                self._page_epoch <= 0
                or (page_epoch is not None and page_epoch != self._page_epoch)
                or (session_epoch is not None and session_epoch != self._session_epoch)
            ):
                return 0
            return self._authority_serial

    def copy(
        self,
        text: str,
        content_kind: str,
        *,
        publication_token: int | None = None,
        cancelled: threading.Event | None = None,
    ) -> dict[str, object] | None:
        """Write a bounded record field and return content-free state."""

        if not text:
            with self._lock:
                return self._public_result(self._snapshot_locked())
        if content_kind not in {"ACCOUNT", "PASSWORD", "TOTP", "RECOVERY_CODE"}:
            raise ValueError("unsupported M4 clipboard content kind")
        if QThread.currentThread() == self.thread():
            return self._copy_on_gui(text, content_kind, publication_token, cancelled)
        with self._lock:
            # 正式后台执行器只有一个；只容纳一次待发布复制，避免秘密排队累积。
            if (publication_token is None or self._pending_copies
                    or not self._publication_is_current_locked(publication_token, cancelled)):
                return None
            self._next_copy_id += 1
            request_id = self._next_copy_id
            request = _PendingCopy(text, content_kind, self._authority_serial, cancelled,
                                   time.monotonic() + self.COPY_WAIT_SECONDS)
            self._pending_copies[request_id] = request
        text = ""
        try:
            # Qt 排队事件只持有 ID；正文撤销后，迟到事件无法重放秘密。
            self._copy_requested.emit(request_id)
            while not request.settled.is_set():
                remaining = request.deadline - time.monotonic()
                if remaining <= 0 or (cancelled is not None and cancelled.is_set()):
                    break
                request.settled.wait(min(0.05, remaining))
            with self._lock:
                return request.result
        except Exception:
            return None
        finally:
            with self._lock:
                self._finish_pending_copy_locked(request_id)

    @Slot(object)
    def _run_pending_copy(self, request_id: int) -> None:
        with self._lock:
            request = self._pending_copies.get(request_id)
            if request is None:
                return
            try:
                if time.monotonic() < request.deadline:
                    request.result = self._copy_on_gui(
                        request.text, request.content_kind,
                        request.publication_token, request.cancelled,
                    )
            finally:
                self._finish_pending_copy_locked(request_id)

    def _finish_pending_copy_locked(self, request_id: int) -> None:
        request = self._pending_copies.pop(request_id, None)
        if request is not None:
            request.text = ""
            request.settled.set()

    def _revoke_publications_locked(self) -> None:
        self._authority_serial += 1
        for request_id in tuple(self._pending_copies):
            self._finish_pending_copy_locked(request_id)

    def _publication_is_current_locked(self, token: int | None, cancelled: threading.Event | None) -> bool:
        return (self._page_epoch > 0
                and (token is None or token == self._authority_serial)
                and (cancelled is None or not cancelled.is_set()))

    def _copy_on_gui(
        self, text: str, content_kind: str, publication_token: int | None,
        cancelled: threading.Event | None,
    ) -> dict[str, object] | None:
        with self._lock:
            if not self._publication_is_current_locked(publication_token, cancelled):
                return None
            mode = self._mode
            seconds = self._seconds
            try:
                # Windows 发布只在 GUI 线程执行，不让窗口消息等待持锁工作线程。
                self._clipboard.configure("manual", seconds)
                if not self._clipboard.copy(text, content_kind.lower()):
                    return None
            except Exception:
                return None
            self._content_kind = content_kind
            self._owned = True
            self._deadline = (
                self._clock() + seconds if mode == "COUNTDOWN" else 0.0
            )
            self._last_remaining = seconds if mode == "COUNTDOWN" else 0
            snapshot = self._snapshot_locked()
        self._timer_requested.emit(mode == "COUNTDOWN")
        self._emit_snapshot(snapshot)
        return self._public_result(snapshot)

    def clear_owned(self) -> dict[str, object] | None:
        with self._lock:
            if not self._owned:
                return self._public_result(self._snapshot_locked())
        try:
            cleared = self._clipboard.clear_owned()
        except Exception:
            cleared = False
        if not cleared:
            return None
        with self._lock:
            page_epoch = self._page_epoch
            session_epoch = self._session_epoch
            mode = self._mode
            self._reset_state_locked()
            snapshot = (
                page_epoch,
                session_epoch,
                "NONE",
                mode,
                0,
                False,
            )
        self._timer_requested.emit(False)
        self._emit_snapshot(snapshot)
        return self._public_result(snapshot)

    def snapshot(self) -> dict[str, object]:
        with self._lock:
            owned = self._owned
        if owned and self._clipboard.is_owned_by_us() is False:
            with self._lock:
                self._reset_state_locked()
                snapshot = self._snapshot_locked()
            self._timer_requested.emit(False)
            self._emit_snapshot(snapshot)
            return self._public_result(snapshot)
        with self._lock:
            return self._public_result(self._snapshot_locked())

    @Slot(bool)
    def _set_timer_active(self, active: bool) -> None:
        if active:
            if not self._timer.isActive():
                self._timer.start()
        else:
            self._timer.stop()

    @Slot()
    def _on_tick(self) -> None:
        with self._lock:
            if not self._owned:
                self._timer.stop()
                return
            mode = self._mode
            deadline = self._deadline
            previous = self._last_remaining
        if self._clipboard.is_owned_by_us() is False:
            with self._lock:
                self._reset_state_locked()
                snapshot = self._snapshot_locked()
            self._timer.stop()
            self._emit_snapshot(snapshot)
            return
        if mode == "MANUAL":
            return
        remaining = max(
            0,
            min(60, int(math.ceil(deadline - self._clock()))),
        )
        if remaining <= 0:
            result = self.clear_owned()
            if result is None:
                with self._lock:
                    self._last_remaining = 0
                    snapshot = self._snapshot_locked()
                self._emit_snapshot(snapshot)
            return
        if remaining != previous:
            with self._lock:
                self._last_remaining = remaining
                snapshot = self._snapshot_locked()
            self._emit_snapshot(snapshot)

    def _reset_state_locked(self) -> None:
        self._content_kind = "NONE"
        self._owned = False
        self._deadline = 0.0
        self._last_remaining = 0

    def _snapshot_locked(self) -> tuple[int, int, str, str, int, bool]:
        return (
            self._page_epoch,
            self._session_epoch,
            self._content_kind,
            self._mode,
            self._last_remaining if self._owned else 0,
            self._owned,
        )

    def _emit_snapshot(
        self,
        snapshot: tuple[int, int, str, str, int, bool],
    ) -> None:
        self.state_changed.emit(*snapshot)

    @staticmethod
    def _public_result(
        snapshot: tuple[int, int, str, str, int, bool],
    ) -> dict[str, object]:
        return {
            "contentKind": snapshot[2],
            "mode": snapshot[3],
            "remainingSeconds": snapshot[4],
            "owned": snapshot[5],
        }


__all__ = ["ProductClipboardController"]
