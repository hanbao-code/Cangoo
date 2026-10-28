"""Native-only capability ownership for the isolated WebEngine host."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path
import sys
import threading
from typing import Protocol

from PySide6.QtCore import QObject, QThread, Signal
from PySide6.QtWidgets import QFileDialog, QWidget

from .hotkey import WindowsGlobalHotkey
from .security_lifecycle import (
    SecurityBoundaryCoordinator,
    SecurityCleanupPhase,
)


class CleanupPhase(IntEnum):
    """Required synchronous order for a native leave-session boundary."""

    STOP_ACTIVITY = 10
    CLEAR_SENSITIVE_UI = 20
    CLEAR_CLIPBOARD = 30
    RELEASE_SESSION = 40


@dataclass(frozen=True)
class CleanupResult:
    attempted: tuple[str, ...]
    failed: tuple[str, ...]
    complete: bool


class NativeSecurityLifecycle:
    """Compatibility facade for native cleanup registration and results.

    The standalone form preserves the historical M2.3 fixture.  A production
    host supplies its one ``SecurityBoundaryCoordinator``; callbacks are then
    registered with that coordinator and :meth:`run` only exposes its completed
    result.  It never executes a second cleanup sequence.
    """

    _SECURITY_PHASES = {
        CleanupPhase.STOP_ACTIVITY: SecurityCleanupPhase.STOP_ACTIVITY,
        CleanupPhase.CLEAR_SENSITIVE_UI:
            SecurityCleanupPhase.CLEAR_NATIVE_SECRETS,
        CleanupPhase.CLEAR_CLIPBOARD:
            SecurityCleanupPhase.CLEAR_CLIPBOARD,
        CleanupPhase.RELEASE_SESSION:
            SecurityCleanupPhase.RELEASE_SESSION,
    }

    def __init__(
        self,
        coordinator: SecurityBoundaryCoordinator | None = None,
    ) -> None:
        self._steps: list[tuple[CleanupPhase, str, Callable[[], object]]] = []
        self._result: CleanupResult | None = None
        self._result_authority_serial = 0
        self._coordinator = coordinator

    @property
    def complete(self) -> bool:
        if self._coordinator is not None:
            return self._coordinator.last_result is not None
        return self._result is not None

    def register(
        self,
        phase: CleanupPhase,
        name: str,
        callback: Callable[[], object],
    ) -> None:
        if self.complete:
            raise RuntimeError("cleanup lifecycle is already complete")
        if not name or any(existing == name for _, existing, _ in self._steps):
            raise ValueError("cleanup step names must be non-empty and unique")
        normalized_phase = CleanupPhase(phase)
        if self._coordinator is not None:
            self._coordinator.register(
                self._SECURITY_PHASES[normalized_phase],
                name,
                lambda _context, callback=callback: callback(),
            )
        self._steps.append((normalized_phase, name, callback))

    def run(self) -> CleanupResult:
        if self._coordinator is not None:
            source = self._coordinator.last_result
            if source is None:
                raise RuntimeError(
                    "native cleanup must run through the security coordinator"
                )
            if (
                self._result is not None
                and self._result_authority_serial == source.authority_serial
            ):
                return self._result
            self._result = CleanupResult(
                attempted=source.attempted,
                failed=source.failed,
                complete=source.complete,
            )
            self._result_authority_serial = source.authority_serial
            return self._result
        if self._result is not None:
            return self._result
        attempted: list[str] = []
        failed: list[str] = []
        for _phase, name, callback in sorted(
            self._steps,
            key=lambda item: (item[0], item[1]),
        ):
            attempted.append(name)
            try:
                callback()
            except Exception:
                failed.append(name)
        self._result = CleanupResult(
            attempted=tuple(attempted),
            failed=tuple(failed),
            complete=True,
        )
        return self._result


class ClipboardBackend(Protocol):
    def copy(self, text: str, label: str = "") -> bool: ...

    def clear(self) -> object: ...

    def force_clear(self) -> object: ...

    def is_owned_by_us(self) -> bool | None: ...

    def set_mode(self, mode: str, countdown_sec: int = 30) -> object: ...


def _real_clipboard_backend() -> ClipboardBackend:
    from core.clipboard import ClipboardManager

    return ClipboardManager()


class NativeClipboard:
    """Lazy system clipboard adapter; construction has no system side effect."""

    def __init__(
        self,
        backend_factory: Callable[[], ClipboardBackend] = _real_clipboard_backend,
    ) -> None:
        self._backend_factory = backend_factory
        self._backend: ClipboardBackend | None = None
        self._lock = threading.RLock()
        self._owner_hwnd = 0

    def bind_window_handle(self, hwnd: int) -> None:
        """接收宿主已捕获的句柄，后端延迟创建和句柄重建使用同一份值。"""
        with self._lock:
            self._owner_hwnd = hwnd
            if self._backend is not None:
                bind = getattr(self._backend, "bind_window_handle", None)
                if bind is not None:
                    bind(hwnd)

    @property
    def initialized(self) -> bool:
        with self._lock:
            return self._backend is not None

    def _get_backend(self) -> ClipboardBackend:
        with self._lock:
            if self._backend is None:
                self._backend = self._backend_factory()
                bind = getattr(self._backend, "bind_window_handle", None)
                if bind is not None:
                    bind(self._owner_hwnd)
            return self._backend

    def copy(self, text: str, label: str = "") -> bool:
        return bool(self._get_backend().copy(text, label))

    def configure(self, mode: str, countdown_sec: int) -> None:
        self._get_backend().set_mode(mode, countdown_sec)

    def is_owned_by_us(self) -> bool | None:
        with self._lock:
            backend = self._backend
        return False if backend is None else backend.is_owned_by_us()

    def clear_owned(self) -> bool:
        with self._lock:
            backend = self._backend
        return bool(backend is None or backend.clear())

    def force_clear_if_initialized(self) -> bool:
        with self._lock:
            backend = self._backend
        return bool(backend is None or backend.force_clear())


OpenDialog = Callable[[QWidget, str, str, str], tuple[str, str]]
SaveDialog = Callable[[QWidget, str, str, str], tuple[str, str]]


class NativeFileDialogs:
    """Fixed native file-dialog tasks; no arbitrary web-supplied filters."""

    def __init__(
        self,
        parent: QWidget,
        *,
        open_dialog: OpenDialog = QFileDialog.getOpenFileName,
        save_dialog: SaveDialog = QFileDialog.getSaveFileName,
    ) -> None:
        self._parent = parent
        self._open_dialog = open_dialog
        self._save_dialog = save_dialog

    @staticmethod
    def _selected_path(value: str) -> Path | None:
        return Path(value) if value else None

    def choose_database(self) -> Path | None:
        value, _selected_filter = self._open_dialog(
            self._parent,
            "选择密码数据库",
            "",
            "Password database (*.db)",
        )
        return self._selected_path(value)

    def choose_backup_import(self) -> Path | None:
        value, _selected_filter = self._open_dialog(
            self._parent,
            "导入加密备份",
            "",
            "Encrypted backup (*.pdmbackup.json *.json)",
        )
        return self._selected_path(value)

    def choose_backup_export(self) -> Path | None:
        value, _selected_filter = self._save_dialog(
            self._parent,
            "导出加密备份",
            "",
            "Encrypted backup (*.pdmbackup.json)",
        )
        selected = self._selected_path(value)
        if selected is not None and not str(selected).lower().endswith(
            ".pdmbackup.json"
        ):
            selected = Path(f"{selected}.pdmbackup.json")
        return selected


class HotkeyBackend(Protocol):
    HOTKEY_ID: int

    @property
    def registered(self) -> bool: ...

    def register(self, hwnd: int, hotkey: str) -> bool: ...

    def unregister(self) -> None: ...


@dataclass(frozen=True)
class NativeHotkeyDiagnostic:
    stage: str
    gui_thread_match: bool
    hwnd_positive: bool
    hwnd_current: bool
    platform_error: int

    def __post_init__(self) -> None:
        if self.stage not in {
            "UNATTEMPTED",
            "GUI_THREAD_MISMATCH",
            "HWND_READ_FAILED",
            "HWND_NON_POSITIVE",
            "HWND_CACHE_CHANGED",
            "BACKEND_REJECTED",
            "REGISTERED",
            "ROLLBACK_REGISTERED",
            "ROLLBACK_REJECTED",
        }:
            raise ValueError("invalid native hotkey diagnostic stage")
        if not 0 <= self.platform_error <= 0xFFFFFFFF:
            raise ValueError("invalid native hotkey platform error")


class NativeHotkey:
    """Thread-safe native registration with rollback on replacement failure."""

    def __init__(
        self,
        window: QWidget,
        backend: HotkeyBackend | None = None,
    ) -> None:
        # Creating a native HWND while HostWindow is still assembling its
        # WebEngine surface can terminate Chromium startup.  Bind explicitly
        # after host construction, or lazily from a GUI-thread caller.
        self._window = window
        self._hwnd: int | None = None
        self._backend = backend or WindowsGlobalHotkey()
        self._lock = threading.RLock()
        self._hotkey: str | None = None
        self._diagnostic = NativeHotkeyDiagnostic(
            "UNATTEMPTED", False, False, False, 0
        )
        self._last_emitted_diagnostic: NativeHotkeyDiagnostic | None = None

    def bind_window_handle(self) -> bool:
        """Capture HWND once, and never reach QWidget from a worker thread."""

        with self._lock:
            return self._current_window_handle() is not None

    @property
    def diagnostic(self) -> NativeHotkeyDiagnostic:
        with self._lock:
            return self._diagnostic

    @property
    def registered(self) -> bool:
        with self._lock:
            return bool(self._backend.registered)

    @property
    def current_hotkey(self) -> str | None:
        with self._lock:
            return self._hotkey if self._backend.registered else None

    @property
    def hotkey_id(self) -> int:
        return int(self._backend.HOTKEY_ID)

    def register(self, hotkey: str) -> bool:
        with self._lock:
            hwnd = self._current_window_handle()
            if hwnd is None:
                return False
            registered = bool(self._backend.register(hwnd, hotkey))
            self._hotkey = hotkey if registered else None
            self._set_diagnostic(
                "REGISTERED" if registered else "BACKEND_REJECTED",
                True,
                True,
                True,
                0 if registered else self._backend_error_code(),
            )
            return registered

    def replace_preserving(self, hotkey: str) -> bool:
        """Replace the active registration, restoring the old one on error."""

        with self._lock:
            hwnd = self._current_window_handle()
            if hwnd is None:
                return False
            old_hotkey = (
                self._hotkey if self._backend.registered else None
            )
            if old_hotkey == hotkey:
                self._set_diagnostic("REGISTERED", True, True, True, 0)
                return True
            if self._backend.register(hwnd, hotkey):
                self._hotkey = hotkey
                self._set_diagnostic("REGISTERED", True, True, True, 0)
                return True
            platform_error = self._backend_error_code()
            self._hotkey = None
            if old_hotkey is not None and self._backend.register(hwnd, old_hotkey):
                self._hotkey = old_hotkey
                self._set_diagnostic(
                    "ROLLBACK_REGISTERED", True, True, True, platform_error
                )
            else:
                self._set_diagnostic(
                    "ROLLBACK_REJECTED" if old_hotkey is not None else "BACKEND_REJECTED",
                    True,
                    True,
                    True,
                    platform_error,
                )
            return False

    def unregister(self) -> None:
        with self._lock:
            if QThread.currentThread() != self._window.thread():
                raise RuntimeError(
                    "native hotkey unregister requires the GUI thread"
                )
            self._backend.unregister()
            self._hotkey = None

    def matches(self, message_id: int) -> bool:
        return self.registered and int(message_id) == self.hotkey_id

    def _current_window_handle(self) -> int | None:
        gui_thread_match = QThread.currentThread() == self._window.thread()
        if not gui_thread_match:
            self._set_diagnostic("GUI_THREAD_MISMATCH", False, False, False, 0)
            return None
        try:
            hwnd = int(self._window.winId())
        except Exception:
            self._set_diagnostic("HWND_READ_FAILED", True, False, False, 0)
            return None
        if hwnd <= 0:
            self._set_diagnostic("HWND_NON_POSITIVE", True, False, False, 0)
            return None
        if self._hwnd is not None and self._hwnd != hwnd:
            self._set_diagnostic("HWND_CACHE_CHANGED", True, True, False, 0)
            return None
        self._hwnd = hwnd
        return hwnd

    def _backend_error_code(self) -> int:
        value = getattr(self._backend, "last_error_code", 0)
        return int(value) & 0xFFFFFFFF if isinstance(value, int) else 0

    def _set_diagnostic(
        self,
        stage: str,
        gui_thread_match: bool,
        hwnd_positive: bool,
        hwnd_current: bool,
        platform_error: int,
    ) -> None:
        diagnostic = NativeHotkeyDiagnostic(
            stage,
            gui_thread_match,
            hwnd_positive,
            hwnd_current,
            platform_error,
        )
        self._diagnostic = diagnostic
        if diagnostic == self._last_emitted_diagnostic:
            return
        self._last_emitted_diagnostic = diagnostic
        print(
            "PDM_NATIVE_HOTKEY"
            f" stage={diagnostic.stage}"
            f" gui_thread_match={int(diagnostic.gui_thread_match)}"
            f" hwnd_positive={int(diagnostic.hwnd_positive)}"
            f" hwnd_current={int(diagnostic.hwnd_current)}"
            f" platform_error={diagnostic.platform_error}",
            file=sys.stderr,
            flush=True,
        )


class NativeCapabilities(QObject):
    """Single native owner for fixed capabilities and cleanup registration."""

    quickbar_requested = Signal()

    def __init__(
        self,
        window: QWidget,
        *,
        security: SecurityBoundaryCoordinator | None = None,
    ) -> None:
        super().__init__(window)
        self.clipboard = NativeClipboard()
        self.file_dialogs = NativeFileDialogs(window)
        self.hotkey = NativeHotkey(window)
        self.lifecycle = NativeSecurityLifecycle(security)
        self.lifecycle.register(
            CleanupPhase.STOP_ACTIVITY,
            "native.hotkey.unregister",
            lambda: self.hotkey.unregister(),
        )
        self.lifecycle.register(
            CleanupPhase.CLEAR_CLIPBOARD,
            "native.clipboard.force_clear",
            self._clear_clipboard_for_boundary,
        )

    def _clear_clipboard_for_boundary(self) -> None:
        if not self.clipboard.force_clear_if_initialized():
            raise RuntimeError("CLIPBOARD_CLEAR_FAILED")

    def handle_hotkey(self, message_id: int) -> bool:
        if not self.hotkey.matches(message_id):
            return False
        self.quickbar_requested.emit()
        return True

    def shutdown(self) -> CleanupResult:
        return self.lifecycle.run()
