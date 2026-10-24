"""Win32 global-hotkey adapter owned by the native WebEngine host."""

from __future__ import annotations

import ctypes
from ctypes import wintypes
from collections.abc import Callable


MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000
WM_HOTKEY = 0x0312


def _virtual_key(main: str) -> int | None:
    if not main:
        return None
    key = main.lower()
    if len(key) == 1 and key.isalnum():
        return ord(key.upper())
    if key.startswith("f") and key[1:].isdigit() and 1 <= int(key[1:]) <= 12:
        return 0x70 + int(key[1:]) - 1
    return {
        "space": 0x20,
        "tab": 0x09,
        "enter": 0x0D,
        "backspace": 0x08,
        "`": 0xC0,
        "-": 0xBD,
        "=": 0xBB,
        "[": 0xDB,
        "]": 0xDD,
        "\\": 0xDC,
        ";": 0xBA,
        "'": 0xDE,
        ",": 0xBC,
        ".": 0xBE,
        "/": 0xBF,
    }.get(key)


class WindowsGlobalHotkey:
    """Replace one process-local RegisterHotKey registration."""

    HOTKEY_ID = 0x504D

    def __init__(
        self,
        user32: object | None = None,
        get_last_error: Callable[[], int] | None = None,
    ) -> None:
        self._hwnd: int | None = None
        self._registered = False
        self._last_error_code = 0
        self._user32 = user32 or self._load_user32()
        self._get_last_error = get_last_error or getattr(
            ctypes,
            "get_last_error",
            lambda: 0,
        )
        if self._user32 is not None:
            self._configure_user32(self._user32)

    @property
    def registered(self) -> bool:
        return self._registered

    @property
    def last_error_code(self) -> int:
        """Return the last failed ``RegisterHotKey`` platform error code."""

        return self._last_error_code

    @staticmethod
    def _load_user32() -> object | None:
        if not hasattr(ctypes, "WinDLL"):
            return None
        return ctypes.WinDLL("user32", use_last_error=True)

    @staticmethod
    def _configure_user32(user32: object) -> None:
        register = user32.RegisterHotKey
        register.argtypes = [
            wintypes.HWND,
            wintypes.INT,
            wintypes.UINT,
            wintypes.UINT,
        ]
        register.restype = wintypes.BOOL
        unregister = user32.UnregisterHotKey
        unregister.argtypes = [wintypes.HWND, wintypes.INT]
        unregister.restype = wintypes.BOOL

    def unregister(self) -> None:
        if self._registered and self._user32 is not None:
            self._user32.UnregisterHotKey(
                wintypes.HWND(self._hwnd),
                wintypes.INT(self.HOTKEY_ID),
            )
        self._registered = False
        self._hwnd = None

    def register(self, hwnd: int, hotkey: str) -> bool:
        self.unregister()
        self._last_error_code = 0
        if self._user32 is None:
            return False
        # Keep the zero-capability M3 host import path independent of core.
        # The stable parser is loaded only when a real registration is
        # explicitly requested by the native capability owner.
        from core.hotkey_parser import parse_hotkey

        parsed = parse_hotkey(hotkey)
        virtual_key = _virtual_key(parsed.main) if parsed else None
        if (
            not parsed
            or not virtual_key
            or not (
                parsed.ctrl or parsed.alt or parsed.shift or parsed.win
            )
        ):
            return False
        modifiers = MOD_NOREPEAT
        if parsed.ctrl:
            modifiers |= MOD_CONTROL
        if parsed.alt:
            modifiers |= MOD_ALT
        if parsed.shift:
            modifiers |= MOD_SHIFT
        if parsed.win:
            modifiers |= MOD_WIN
        set_last_error = getattr(ctypes, "set_last_error", None)
        if callable(set_last_error):
            set_last_error(0)
        if not bool(
            self._user32.RegisterHotKey(
                wintypes.HWND(hwnd),
                wintypes.INT(self.HOTKEY_ID),
                wintypes.UINT(modifiers),
                wintypes.UINT(virtual_key),
            )
        ):
            self._last_error_code = int(self._get_last_error()) & 0xFFFFFFFF
            return False
        self._hwnd = int(hwnd)
        self._registered = True
        return True
