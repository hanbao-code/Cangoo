"""Bounded Win32 foreground and monitor helpers for the native QuickBar."""

from __future__ import annotations

import ctypes
from ctypes import wintypes
import sys


MONITOR_DEFAULTTONEAREST = 0x00000002


class _MonitorInfoExW(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("rcMonitor", wintypes.RECT),
        ("rcWork", wintypes.RECT),
        ("dwFlags", wintypes.DWORD),
        ("szDevice", wintypes.WCHAR * 32),
    ]


class NativeQuickbarFocus:
    """Expose only the foreground operations required by D10.

    Raw HWND values remain native-only and are never returned to the renderer.
    The class is deliberately injectable so the strict gate can prove focus
    decisions without stealing the real desktop foreground during automation.
    """

    def __init__(self) -> None:
        self._user32 = None
        if sys.platform != "win32":
            return
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        user32.GetForegroundWindow.argtypes = []
        user32.GetForegroundWindow.restype = wintypes.HWND
        user32.IsWindow.argtypes = [wintypes.HWND]
        user32.IsWindow.restype = wintypes.BOOL
        user32.SetForegroundWindow.argtypes = [wintypes.HWND]
        user32.SetForegroundWindow.restype = wintypes.BOOL
        user32.MonitorFromWindow.argtypes = [wintypes.HWND, wintypes.DWORD]
        user32.MonitorFromWindow.restype = wintypes.HANDLE
        user32.GetMonitorInfoW.argtypes = [
            wintypes.HANDLE,
            ctypes.POINTER(_MonitorInfoExW),
        ]
        user32.GetMonitorInfoW.restype = wintypes.BOOL
        self._user32 = user32

    def foreground_window(self) -> int:
        user32 = self._user32
        if user32 is None:
            return 0
        try:
            return int(user32.GetForegroundWindow() or 0)
        except Exception:
            return 0

    def is_window(self, hwnd: int) -> bool:
        user32 = self._user32
        if user32 is None or type(hwnd) is not int or hwnd <= 0:
            return False
        try:
            return bool(user32.IsWindow(wintypes.HWND(hwnd)))
        except Exception:
            return False

    def monitor_name_for_window(self, hwnd: int) -> str:
        user32 = self._user32
        if user32 is None or not self.is_window(hwnd):
            return ""
        try:
            monitor = user32.MonitorFromWindow(
                wintypes.HWND(hwnd),
                MONITOR_DEFAULTTONEAREST,
            )
            if not monitor:
                return ""
            info = _MonitorInfoExW()
            info.cbSize = ctypes.sizeof(info)
            if not user32.GetMonitorInfoW(monitor, ctypes.byref(info)):
                return ""
            return str(info.szDevice)
        except Exception:
            return ""

    def activate_window(self, hwnd: int) -> bool:
        user32 = self._user32
        if user32 is None or not self.is_window(hwnd):
            return False
        try:
            return bool(user32.SetForegroundWindow(wintypes.HWND(hwnd)))
        except Exception:
            return False


__all__ = ["NativeQuickbarFocus"]
