"""Native system-tray surface for the isolated WebEngine candidate host."""

from __future__ import annotations

import ctypes
from ctypes import wintypes
from enum import Enum
import sys
import threading

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QIcon, QRegion
from PySide6.QtWidgets import QMenu, QSystemTrayIcon, QWidget

from .resources import application_icon


class TraySessionState(str, Enum):
    """以悬停文字区分会话状态，不暴露库资料。"""

    DISCONNECTED = "disconnected"
    CONNECTED = "connected"
    LOCKED = "locked"


_TOOLTIPS = {
    "zh": {
        TraySessionState.DISCONNECTED: "小仓 — 未连接",
        TraySessionState.CONNECTED: "小仓 — 已连接",
        TraySessionState.LOCKED: "小仓 — 未连接",
    },
    "en": {
        TraySessionState.DISCONNECTED: "Cangoo — Disconnected",
        TraySessionState.CONNECTED: "Cangoo — Connected",
        TraySessionState.LOCKED: "Cangoo — Disconnected",
    },
}

_MENU_TEXT = {
    "zh": {
        "show": "显示主窗口",
        "exit": "退出",
    },
    "en": {
        "show": "Show Main Window",
        "exit": "Exit",
    },
}


class _NotifyIconIdentifier(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("hWnd", wintypes.HWND),
        ("uID", wintypes.UINT),
        ("guidItem", ctypes.c_byte * 16),
    ]


def _native_tray_registered() -> bool:
    """只读确认当前界面线程唯一的 Qt 托盘图标已向 Windows 登记。"""
    if sys.platform != "win32":
        return False
    try:
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        shell32 = ctypes.WinDLL("shell32", use_last_error=True)
        callback_type = ctypes.WINFUNCTYPE(
            wintypes.BOOL, wintypes.HWND, wintypes.LPARAM
        )
        user32.EnumThreadWindows.argtypes = [
            wintypes.DWORD, callback_type, wintypes.LPARAM
        ]
        user32.EnumThreadWindows.restype = wintypes.BOOL
        user32.GetClassNameW.argtypes = [
            wintypes.HWND, wintypes.LPWSTR, ctypes.c_int
        ]
        user32.GetClassNameW.restype = ctypes.c_int
        shell32.Shell_NotifyIconGetRect.argtypes = [
            ctypes.POINTER(_NotifyIconIdentifier), ctypes.POINTER(wintypes.RECT)
        ]
        shell32.Shell_NotifyIconGetRect.restype = ctypes.c_long
        handles: list[int] = []

        @callback_type
        def collect(hwnd: int, _data: int) -> bool:
            name = ctypes.create_unicode_buffer(256)
            if user32.GetClassNameW(hwnd, name, len(name)):
                if name.value.startswith("Qt") and name.value.endswith(
                    "TrayIconMessageWindowClass"
                ):
                    handles.append(hwnd)
            return True

        if not user32.EnumThreadWindows(threading.get_native_id(), collect, 0):
            return False
        # 当前产品每个界面线程只有一个托盘。歧义时不能借其他图标证明可恢复。
        if len(handles) != 1:
            return False
        identifier = _NotifyIconIdentifier()
        identifier.cbSize = ctypes.sizeof(identifier)
        identifier.hWnd = handles[0]
        # Qt 6.9.3 的 qwindowssystemtrayicon.cpp 使用上述窗口类和图标 ID 0。
        # 升级 Qt 时须复核；公开 geometry() 会过滤隐藏区图标，不能作为登记依据。
        identifier.uID = 0
        rect = wintypes.RECT()
        result = shell32.Shell_NotifyIconGetRect(
            ctypes.byref(identifier), ctypes.byref(rect)
        )
        # S_OK=0；Windows 10 隐藏区的 S_FALSE=1 也表示图标存在。
        return result in (0, 1)
    except (OSError, AttributeError, ctypes.ArgumentError):
        return False


class TrayController(QObject):
    """Own the tray icon and emit only fixed native lifecycle intents."""

    restore_requested = Signal()
    exit_requested = Signal()

    def __init__(self, window: QWidget, *, language: str = "zh") -> None:
        super().__init__(window)
        self._language = self._normalize_language(language)
        self._state = TraySessionState.DISCONNECTED
        self.icon_asset = application_icon()
        image = self.icon_asset.pixmap(256, 256)
        if image.isNull() or QRegion(image.mask()).isEmpty():
            self.icon_asset = QIcon()
        self.icon = QSystemTrayIcon(self.icon_asset, window)
        self.menu = QMenu(window)
        self.show_action = self.menu.addAction("")
        self.show_action.triggered.connect(self.restore_requested.emit)
        self.menu.addSeparator()
        self.exit_action = self.menu.addAction("")
        self.exit_action.triggered.connect(self.exit_requested.emit)
        self.icon.setContextMenu(self.menu)
        self.icon.activated.connect(self._on_activated)
        self._sync_text()

    @property
    def available(self) -> bool:
        return bool(QSystemTrayIcon.isSystemTrayAvailable())

    @property
    def visible(self) -> bool:
        return bool(self.icon.isVisible())

    @property
    def state(self) -> TraySessionState:
        return self._state

    @property
    def language(self) -> str:
        return self._language

    def show(self) -> bool:
        return self.ensure_recoverable_entry()

    def ensure_recoverable_entry(self) -> bool:
        """Expose one verified native restore entry before hiding the window."""

        if not self.available or self.icon_asset.isNull():
            return False
        if not self.visible:
            self.icon.show()
        return self.visible and _native_tray_registered()

    def hide(self) -> None:
        self.icon.hide()

    def set_state(self, state: TraySessionState | str) -> None:
        self._state = TraySessionState(state)
        self._sync_tooltip()

    def set_language(self, language: str) -> None:
        normalized = self._normalize_language(language)
        if normalized == self._language:
            return
        self._language = normalized
        self._sync_text()

    @staticmethod
    def _normalize_language(language: str) -> str:
        if type(language) is not str:
            raise ValueError("tray language must be zh or en")
        normalized = language.strip().lower()
        if normalized not in _TOOLTIPS:
            raise ValueError("tray language must be zh or en")
        return normalized

    def _sync_text(self) -> None:
        menu_text = _MENU_TEXT[self._language]
        self.show_action.setText(menu_text["show"])
        self.exit_action.setText(menu_text["exit"])
        self._sync_tooltip()

    def _sync_tooltip(self) -> None:
        self.icon.setToolTip(_TOOLTIPS[self._language][self._state])

    def _on_activated(
        self,
        reason: QSystemTrayIcon.ActivationReason,
    ) -> None:
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.restore_requested.emit()
