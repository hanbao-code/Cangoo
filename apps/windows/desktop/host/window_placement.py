"""Screen-safe placement helpers for the isolated native candidate host."""

from __future__ import annotations

import ctypes
import sys

from PySide6.QtCore import QRect, QSize


WINDOW_WORK_AREA_MARGIN = 8
SW_SHOWNORMAL = 1
SW_SHOWMINIMIZED = 2
SW_SHOWMAXIMIZED = 3
SW_RESTORE = 9
WPF_RESTORETOMAXIMIZED = 0x0002


class _WindowPlacement(ctypes.Structure):
    """Win32 ``WINDOWPLACEMENT`` layout through ``rcNormalPosition``."""

    if sys.platform == "win32":
        from ctypes import wintypes

        _fields_ = (
            ("length", wintypes.UINT),
            ("flags", wintypes.UINT),
            ("showCmd", wintypes.UINT),
            ("ptMinPosition", wintypes.POINT),
            ("ptMaxPosition", wintypes.POINT),
            ("rcNormalPosition", wintypes.RECT),
        )
    else:
        _fields_: tuple[()] = ()


def native_window_rect(
    hwnd: int,
    *,
    user32=None,
) -> tuple[int, int, int, int] | None:
    """Read one top-level HWND rectangle in native physical coordinates."""

    if type(hwnd) is not int or hwnd <= 0:
        return None
    if user32 is None:
        if sys.platform != "win32":
            return None
        try:
            user32 = ctypes.windll.user32
            from ctypes import wintypes

            user32.GetWindowRect.argtypes = (
                wintypes.HWND,
                ctypes.POINTER(wintypes.RECT),
            )
            user32.GetWindowRect.restype = wintypes.BOOL
        except Exception:
            return None
    from ctypes import wintypes

    rect = wintypes.RECT()
    try:
        if not user32.GetWindowRect(
            wintypes.HWND(hwnd),
            ctypes.byref(rect),
        ):
            return None
        return (rect.left, rect.top, rect.right, rect.bottom)
    except Exception:
        return None


def read_native_window_placement(hwnd: int) -> dict[str, object] | None:
    """Return public Win32 placement fields for lifecycle verification."""

    if sys.platform != "win32" or int(hwnd) <= 0:
        return None
    placement = _WindowPlacement()
    placement.length = ctypes.sizeof(placement)
    if not ctypes.windll.user32.GetWindowPlacement(
        int(hwnd),
        ctypes.byref(placement),
    ):
        return None
    rect = placement.rcNormalPosition
    return {
        "flags": int(placement.flags),
        "show_cmd": int(placement.showCmd),
        "normal_rect": [
            int(rect.left),
            int(rect.top),
            int(rect.right),
            int(rect.bottom),
        ],
    }


def minimize_native_window(
    hwnd: int,
    *,
    restore_to_maximized: bool,
    normal_rect: tuple[int, int, int, int] | None = None,
) -> bool:
    """Minimize through WINDOWPLACEMENT so taskbar restore is one-step."""

    if sys.platform != "win32" or int(hwnd) <= 0:
        return False
    if restore_to_maximized and normal_rect is None:
        return False

    placement = _WindowPlacement()
    placement.length = ctypes.sizeof(placement)
    if not ctypes.windll.user32.GetWindowPlacement(
        int(hwnd),
        ctypes.byref(placement),
    ):
        return False
    if normal_rect is not None:
        (
            placement.rcNormalPosition.left,
            placement.rcNormalPosition.top,
            placement.rcNormalPosition.right,
            placement.rcNormalPosition.bottom,
        ) = normal_rect
    placement.flags = (
        WPF_RESTORETOMAXIMIZED if restore_to_maximized else 0
    )
    placement.showCmd = SW_SHOWMINIMIZED
    return bool(
        ctypes.windll.user32.SetWindowPlacement(
            int(hwnd),
            ctypes.byref(placement),
        )
    )


def restore_native_window(hwnd: int) -> bool:
    """Simulate the native taskbar restore action in automated guards."""

    if sys.platform != "win32" or int(hwnd) <= 0:
        return False
    return bool(ctypes.windll.user32.ShowWindow(int(hwnd), SW_RESTORE))


def show_native_normal_window(
    hwnd: int,
    *,
    normal_rect: tuple[int, int, int, int] | None = None,
) -> bool:
    """Leave native maximized placement in one direct normal-window step."""

    if sys.platform != "win32" or int(hwnd) <= 0:
        return False
    placement = _WindowPlacement()
    placement.length = ctypes.sizeof(placement)
    if not ctypes.windll.user32.GetWindowPlacement(
        int(hwnd),
        ctypes.byref(placement),
    ):
        return False
    if normal_rect is not None:
        (
            placement.rcNormalPosition.left,
            placement.rcNormalPosition.top,
            placement.rcNormalPosition.right,
            placement.rcNormalPosition.bottom,
        ) = normal_rect
    placement.flags = 0
    placement.showCmd = SW_SHOWNORMAL
    return bool(
        ctypes.windll.user32.SetWindowPlacement(
            int(hwnd),
            ctypes.byref(placement),
        )
    )


def show_native_maximized_window(
    hwnd: int,
    *,
    normal_rect: tuple[int, int, int, int] | None = None,
) -> bool:
    """Show a hidden window directly in its native maximized placement."""

    if sys.platform != "win32" or int(hwnd) <= 0:
        return False
    placement = _WindowPlacement()
    placement.length = ctypes.sizeof(placement)
    if not ctypes.windll.user32.GetWindowPlacement(
        int(hwnd),
        ctypes.byref(placement),
    ):
        return False
    if normal_rect is not None:
        (
            placement.rcNormalPosition.left,
            placement.rcNormalPosition.top,
            placement.rcNormalPosition.right,
            placement.rcNormalPosition.bottom,
        ) = normal_rect
    placement.flags = 0
    placement.showCmd = SW_SHOWMAXIMIZED
    if not ctypes.windll.user32.SetWindowPlacement(
        int(hwnd),
        ctypes.byref(placement),
    ):
        return False
    # A hidden Qt HWND can keep the placement while remaining invisible.
    # Show it directly as maximized; no normal window is exposed in between.
    ctypes.windll.user32.ShowWindow(int(hwnd), SW_SHOWMAXIMIZED)
    visible = bool(ctypes.windll.user32.IsWindowVisible(int(hwnd)))
    verified = _WindowPlacement()
    verified.length = ctypes.sizeof(verified)
    return bool(
        visible
        and ctypes.windll.user32.GetWindowPlacement(
            int(hwnd),
            ctypes.byref(verified),
        )
        and int(verified.showCmd) == SW_SHOWMAXIMIZED
    )


def fit_window_rect(
    rect: QRect,
    available: QRect,
    minimum_size: QSize,
    *,
    margin: int = WINDOW_WORK_AREA_MARGIN,
) -> QRect:
    """Return a normal-window rectangle contained by the screen work area."""

    source = QRect(rect)
    work_area = QRect(available).adjusted(margin, margin, -margin, -margin)
    if not source.isValid() or not work_area.isValid():
        return source

    width = min(
        max(source.width(), min(minimum_size.width(), work_area.width())),
        work_area.width(),
    )
    height = min(
        max(source.height(), min(minimum_size.height(), work_area.height())),
        work_area.height(),
    )
    maximum_x = work_area.right() - width + 1
    maximum_y = work_area.bottom() - height + 1
    x = min(max(source.x(), work_area.left()), maximum_x)
    y = min(max(source.y(), work_area.top()), maximum_y)
    return QRect(x, y, width, height)


def rect_fits_work_area(
    rect: QRect,
    available: QRect,
    *,
    margin: int = WINDOW_WORK_AREA_MARGIN,
) -> bool:
    """Return whether a rectangle is fully inside the usable screen bounds."""

    work_area = QRect(available).adjusted(margin, margin, -margin, -margin)
    return work_area.isValid() and work_area.contains(QRect(rect))
