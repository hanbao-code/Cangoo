"""Windows 会话锁屏、睡眠及恢复事件的原生接入。"""

from __future__ import annotations

from collections import Counter
import ctypes
import math
import sys
import time
from typing import Callable

from PySide6.QtCore import QObject, Qt, QTimer, Signal


WM_POWERBROADCAST = 0x0218
PBT_APMSUSPEND = 0x0004
PBT_APMRESUMESUSPEND = 0x0007
PBT_APMRESUMEAUTOMATIC = 0x0012
DEVICE_NOTIFY_WINDOW_HANDLE = 0x00000000
WM_WTSSESSION_CHANGE = 0x02B1
WTS_SESSION_LOCK = 0x0007
NOTIFY_FOR_THIS_SESSION = 0

_POWER_EVENT_NAMES = {
    PBT_APMSUSPEND: "suspend",
    PBT_APMRESUMESUSPEND: "resume_user",
    PBT_APMRESUMEAUTOMATIC: "resume_automatic",
}


class _LastInputInfo(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.c_uint),
        ("dwTime", ctypes.c_uint),
    ]


class NativeIdleMonitor(QObject):
    """Own the Windows-session idle deadline outside the renderer.

    A failed or implausible native sample never becomes fresh activity.  The
    last trusted deadline keeps advancing and therefore still fails closed at
    the configured threshold instead of granting an unbounded grace period.
    """

    timeout_reached = Signal()
    sample_state_changed = Signal(str)

    def __init__(
        self,
        parent: QObject | None = None,
        *,
        clock: Callable[[], float] = time.monotonic,
        idle_seconds_provider: Callable[[], float | None] | None = None,
        poll_interval_ms: int = 1000,
    ) -> None:
        super().__init__(parent)
        if not callable(clock):
            raise TypeError("clock must be callable")
        if idle_seconds_provider is not None and not callable(
            idle_seconds_provider
        ):
            raise TypeError("idle_seconds_provider must be callable")
        if (
            type(poll_interval_ms) is not int
            or not 50 <= poll_interval_ms <= 60_000
        ):
            raise ValueError("poll_interval_ms must be bounded")
        self._clock = clock
        self._idle_seconds_provider = (
            idle_seconds_provider or self._windows_idle_seconds
        )
        self._timer = QTimer(self)
        self._timer.setInterval(poll_interval_ms)
        self._timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._timer.timeout.connect(self.poll_now)
        self._session_active = False
        self._enabled = True
        self._minutes = 5
        self._deadline: float | None = None
        self._last_trusted_input: float | None = None
        self._sample_state = "DISARMED"
        self._timeout_count = 0

    @property
    def armed(self) -> bool:
        return self._session_active and self._enabled and self._timer.isActive()

    @property
    def timeout_count(self) -> int:
        return self._timeout_count

    @property
    def policy(self) -> tuple[bool, int]:
        return self._enabled, self._minutes

    def configure_policy(self, enabled: bool, minutes: int) -> None:
        if type(enabled) is not bool:
            raise TypeError("enabled must be a bool")
        if type(minutes) is not int or not 1 <= minutes <= 60:
            raise ValueError("minutes must be between 1 and 60")
        was_enabled = self._enabled
        minutes_changed = minutes != self._minutes
        self._enabled = enabled
        self._minutes = minutes
        if not self._session_active:
            return
        if not enabled:
            self._timer.stop()
            self._deadline = None
            self._last_trusted_input = None
            self._set_sample_state("DISARMED")
            return
        now = self._safe_clock()
        if not was_enabled or self._last_trusted_input is None:
            self._last_trusted_input = now
        if minutes_changed or not was_enabled or self._deadline is None:
            self._deadline = (
                self._last_trusted_input + self._minutes * 60.0
            )
        if not self._timer.isActive():
            self._timer.start()
        self.poll_now()

    def arm_session(self, enabled: bool, minutes: int) -> None:
        if type(enabled) is not bool:
            raise TypeError("enabled must be a bool")
        if type(minutes) is not int or not 1 <= minutes <= 60:
            raise ValueError("minutes must be between 1 and 60")
        self._timer.stop()
        self._session_active = True
        self._enabled = enabled
        self._minutes = minutes
        now = self._safe_clock()
        self._last_trusted_input = now
        self._deadline = now + minutes * 60.0 if enabled else None
        if enabled:
            self._timer.start()
            self.poll_now()
        else:
            self._set_sample_state("DISARMED")

    def disarm_session(self) -> None:
        self._timer.stop()
        self._session_active = False
        self._deadline = None
        self._last_trusted_input = None
        self._set_sample_state("DISARMED")

    def poll_now(self) -> None:
        if not self._session_active or not self._enabled:
            return
        now = self._safe_clock()
        idle_seconds: float | None
        try:
            raw_idle = self._idle_seconds_provider()
            idle_seconds = (
                float(raw_idle) if raw_idle is not None else None
            )
        except Exception:
            idle_seconds = None
        trusted = (
            idle_seconds is not None
            and math.isfinite(idle_seconds)
            and 0.0 <= idle_seconds <= (0x7FFFFFFF / 1000.0)
        )
        if trusted:
            observed_input = now - idle_seconds
            if observed_input <= now + 0.001:
                if (
                    self._last_trusted_input is None
                    or observed_input > self._last_trusted_input
                ):
                    self._last_trusted_input = observed_input
                    self._deadline = (
                        observed_input + self._minutes * 60.0
                    )
                self._set_sample_state("TRUSTED_SAMPLE")
            else:
                trusted = False
        if not trusted:
            self._set_sample_state("DEGRADED")

        deadline = self._deadline
        if deadline is not None and now >= deadline:
            self._timer.stop()
            # Mark this native session consumed before notifying the host.
            # The synchronous H06 path may re-project the persisted C47
            # policy while it settles accepted settings writes.  Leaving the
            # session active here would let that projection re-arm and emit
            # the same timeout recursively before session revocation lands.
            self._session_active = False
            self._deadline = None
            self._last_trusted_input = None
            self._set_sample_state("DEADLINE_REACHED")
            self._timeout_count += 1
            self.timeout_reached.emit()

    def snapshot(self) -> dict[str, object]:
        now = self._safe_clock()
        remaining = (
            None
            if self._deadline is None
            else max(0.0, self._deadline - now)
        )
        return {
            "session_active": self._session_active,
            "enabled": self._enabled,
            "minutes": self._minutes,
            "armed": self.armed,
            "sample_state": self._sample_state,
            "deadline_remaining_seconds": remaining,
            "timeout_count": self._timeout_count,
        }

    def _safe_clock(self) -> float:
        value = float(self._clock())
        if not math.isfinite(value):
            raise RuntimeError("monotonic clock is not finite")
        return value

    def _set_sample_state(self, state: str) -> None:
        if state == self._sample_state:
            return
        self._sample_state = state
        self.sample_state_changed.emit(state)

    @staticmethod
    def _windows_idle_seconds() -> float | None:
        if sys.platform != "win32":
            return None
        try:
            user32 = ctypes.WinDLL("user32", use_last_error=True)
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            get_last_input = user32.GetLastInputInfo
            get_last_input.argtypes = [ctypes.POINTER(_LastInputInfo)]
            get_last_input.restype = ctypes.c_bool
            get_tick_count = kernel32.GetTickCount64
            get_tick_count.argtypes = []
            get_tick_count.restype = ctypes.c_ulonglong
            info = _LastInputInfo(ctypes.sizeof(_LastInputInfo), 0)
            if not get_last_input(ctypes.byref(info)):
                return None
            now_tick = int(get_tick_count()) & 0xFFFFFFFF
            elapsed_ms = (now_tick - int(info.dwTime)) & 0xFFFFFFFF
            if elapsed_ms > 0x7FFFFFFF:
                return None
            return elapsed_ms / 1000.0
        except (AttributeError, OSError, TypeError, ValueError):
            return None


class SessionLockLifecycle(QObject):
    """只转发当前已注册窗口的锁屏消息，业务撤权由宿主扩展层负责。"""

    locked = Signal()
    availability_changed = Signal(bool)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.registration_supported = sys.platform == "win32"
        self.registration_active = False
        self.registration_error = 0
        self._registration_hwnd = 0
        self._available = False

    @property
    def registered_hwnd(self) -> int:
        return self._registration_hwnd

    def is_registered_for(self, hwnd: int) -> bool:
        return self._available and self.registration_active and hwnd == self._registration_hwnd

    def _set_available(self, available: bool) -> None:
        if available != self._available:
            self._available = available
            self.availability_changed.emit(available)

    def register_window(self, hwnd: int) -> bool:
        if not self.registration_supported:
            self.registration_error = 50
            self._set_available(False)
            return False
        if type(hwnd) is not int or not 0 < hwnd < 1 << (ctypes.sizeof(ctypes.c_void_p) * 8):
            self.registration_error = 87
            self._set_available(False)
            return False
        if self.is_registered_for(hwnd):
            return True
        self._set_available(False)
        if self.registration_active and not self.unregister_window():
            return False
        try:
            from ctypes import wintypes

            ctypes.set_last_error(0)
            library = ctypes.WinDLL("wtsapi32", use_last_error=True)
            register = library.WTSRegisterSessionNotification
            register.argtypes = [wintypes.HWND, wintypes.DWORD]
            register.restype = wintypes.BOOL
            succeeded = bool(register(wintypes.HWND(hwnd), wintypes.DWORD(NOTIFY_FOR_THIS_SESSION)))
        except (AttributeError, OSError):
            succeeded = False
        if not succeeded:
            self.registration_error = int(ctypes.get_last_error()) or 31
            return False
        self._registration_hwnd = hwnd
        self.registration_active = True
        self.registration_error = 0
        self._set_available(True)
        return True

    def unregister_window(self) -> bool:
        self._set_available(False)
        if not self.registration_active:
            return True
        try:
            from ctypes import wintypes

            ctypes.set_last_error(0)
            library = ctypes.WinDLL("wtsapi32", use_last_error=True)
            unregister = library.WTSUnRegisterSessionNotification
            unregister.argtypes = [wintypes.HWND]
            unregister.restype = wintypes.BOOL
            succeeded = bool(unregister(wintypes.HWND(self._registration_hwnd)))
        except (AttributeError, OSError):
            succeeded = False
        if not succeeded:
            self.registration_error = int(ctypes.get_last_error()) or 31
            return False
        self._registration_hwnd = 0
        self.registration_active = False
        self.registration_error = 0
        return True

    def handle_session_change(self, hwnd: int, event_code: int) -> bool:
        if event_code != WTS_SESSION_LOCK or not self.is_registered_for(hwnd):
            return False
        self.locked.emit()
        return True


class PowerLifecycle(QObject):
    """Track logical sleep cycles without pretending synthetic events are sleep."""

    suspending = Signal(int)
    resumed = Signal(str, int)
    broadcast_received = Signal(str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.suspend_count = 0
        self.resume_count = 0
        self.suspended = False
        self._resume_pair_pending_user = False
        self.last_event = ""
        self.broadcast_counts: Counter[str] = Counter()
        self.registration_supported = sys.platform == "win32"
        self.registration_attempted = False
        self.registration_active = False
        self.registration_error = 0
        self.registration_count = 0
        self.unregistration_count = 0
        self._registration_handle = 0
        self._registration_hwnd = 0
        self._registration_available = False

    def is_registered_for(self, hwnd: int) -> bool:
        return bool(
            self._registration_available
            and self.registration_active
            and hwnd == self._registration_hwnd
        )

    def register_window(self, hwnd: int) -> bool:
        """Opt an HWND into suspend/resume delivery, including Modern Standby."""

        if not self.registration_supported:
            self._registration_available = False
            self.registration_error = 50
            return False
        if type(hwnd) is not int or not 0 < hwnd < 1 << (ctypes.sizeof(ctypes.c_void_p) * 8):
            self._registration_available = False
            self.registration_error = 87
            return False
        if self.is_registered_for(hwnd):
            return True
        if self.registration_active and not self.unregister_window():
            return False

        self.registration_attempted = True
        try:
            from ctypes import wintypes

            user32 = ctypes.WinDLL("user32", use_last_error=True)
            register = user32.RegisterSuspendResumeNotification
            register.argtypes = [wintypes.HANDLE, wintypes.DWORD]
            register.restype = wintypes.HANDLE
            ctypes.set_last_error(0)
            handle = register(
                wintypes.HANDLE(hwnd),
                wintypes.DWORD(DEVICE_NOTIFY_WINDOW_HANDLE),
            )
        except (AttributeError, OSError):
            self.registration_error = int(ctypes.get_last_error()) or 31
            return False

        self._registration_handle = int(handle or 0)
        if not self._registration_handle:
            self.registration_error = int(ctypes.get_last_error()) or 31
            return False

        self._registration_hwnd = hwnd
        self.registration_error = 0
        self.registration_active = True
        self._registration_available = True
        self.registration_count += 1
        return True

    def unregister_window(self) -> bool:
        """Cancel the HWND subscription during the explicit exit path."""

        self._registration_available = False
        if not self.registration_active:
            return True
        try:
            from ctypes import wintypes

            user32 = ctypes.WinDLL("user32", use_last_error=True)
            unregister = user32.UnregisterSuspendResumeNotification
            unregister.argtypes = [wintypes.HANDLE]
            unregister.restype = wintypes.BOOL
            ctypes.set_last_error(0)
            succeeded = bool(
                unregister(wintypes.HANDLE(self._registration_handle))
            )
        except (AttributeError, OSError):
            succeeded = False

        if not succeeded:
            self.registration_error = int(ctypes.get_last_error()) or 31
            return False

        self._registration_handle = 0
        self._registration_hwnd = 0
        self.registration_error = 0
        self.registration_active = False
        self.unregistration_count += 1
        return True

    def handle_broadcast(self, event_code: int) -> bool:
        """Record one known ``WM_POWERBROADCAST`` event."""

        event_name = _POWER_EVENT_NAMES.get(int(event_code))
        if event_name is None:
            return False

        self.last_event = event_name
        self.broadcast_counts[event_name] += 1
        self.broadcast_received.emit(event_name)
        if event_code == PBT_APMSUSPEND:
            self.suspend_count += 1
            self.suspended = True
            self._resume_pair_pending_user = False
            self.suspending.emit(self.suspend_count)
            return True

        if self.suspended:
            self.suspended = False
            self.resume_count += 1
            self._resume_pair_pending_user = (
                event_code == PBT_APMRESUMEAUTOMATIC
            )
        elif event_code == PBT_APMRESUMEAUTOMATIC:
            # Windows 可能漏发挂起广播。每个孤立 automatic 都开启新周期，
            # 紧随其后的 user 恢复复用该周期，避免同次唤醒重复锁定。
            self.resume_count += 1
            self._resume_pair_pending_user = True
        elif self._resume_pair_pending_user:
            self._resume_pair_pending_user = False
        else:
            # 没有可配对 automatic 的孤立 user 恢复同样是新周期。
            self.resume_count += 1
        self.resumed.emit(event_name, self.resume_count)
        return True

    def snapshot(self) -> dict[str, object]:
        """Return public lifecycle counters suitable for verification reports."""

        return {
            "suspend_count": self.suspend_count,
            "resume_count": self.resume_count,
            "suspended": self.suspended,
            "last_event": self.last_event,
            "broadcast_counts": dict(sorted(self.broadcast_counts.items())),
            "registration": {
                "supported": self.registration_supported,
                "attempted": self.registration_attempted,
                "active": self.registration_active,
                "error": self.registration_error,
                "registration_count": self.registration_count,
                "unregistration_count": self.unregistration_count,
            },
        }
