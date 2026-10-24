"""Native frameless-window chrome helpers for the WebEngine host."""

from __future__ import annotations

from ctypes import byref, c_int, sizeof
import ctypes
import sys
from typing import Callable

from PySide6.QtCore import (
    QEvent,
    QObject,
    QPoint,
    QPointF,
    QRect,
    QRectF,
    Qt,
    Signal,
)
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontDatabase,
    QKeyEvent,
    QKeySequence,
    QPainter,
    QPainterPath,
    QPen,
)
from PySide6.QtWidgets import QApplication, QHBoxLayout, QToolButton, QWidget

from .resources import application_icon, frontend_root
from desktop.ui_font_scale import normalize_ui_font_scale, scaled_font_pixel_size


WM_NCHITTEST = 0x0084
WM_NCCALCSIZE = 0x0083
WM_NCMOUSEMOVE = 0x00A0
WM_NCLBUTTONDOWN = 0x00A1
WM_NCLBUTTONUP = 0x00A2
WM_NCLBUTTONDBLCLK = 0x00A3
WM_NCRBUTTONDOWN = 0x00A4
WM_NCMBUTTONDOWN = 0x00A7
WM_NCXBUTTONDOWN = 0x00AB
WM_NCPOINTERDOWN = 0x0242
WM_NCMOUSELEAVE = 0x02A2

HTCLIENT = 1
HTCAPTION = 2
HTMINBUTTON = 8
HTMAXBUTTON = 9
HTLEFT = 10
HTRIGHT = 11
HTTOP = 12
HTTOPLEFT = 13
HTTOPRIGHT = 14
HTBOTTOM = 15
HTBOTTOMLEFT = 16
HTBOTTOMRIGHT = 17
HTCLOSE = 20

GWL_STYLE = -16
WS_CAPTION = 0x00C00000
WS_THICKFRAME = 0x00040000
WS_SYSMENU = 0x00080000
WS_MINIMIZEBOX = 0x00020000
WS_MAXIMIZEBOX = 0x00010000
WS_POPUP = 0x80000000
STANDARD_WINDOW_FRAME_STYLE = (
    WS_CAPTION
    | WS_THICKFRAME
    | WS_SYSMENU
    | WS_MINIMIZEBOX
    | WS_MAXIMIZEBOX
)

SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOZORDER = 0x0004
SWP_NOACTIVATE = 0x0010
SWP_FRAMECHANGED = 0x0020
STANDARD_WINDOW_FRAME_CHANGED_FLAGS = (
    SWP_FRAMECHANGED
    | SWP_NOMOVE
    | SWP_NOSIZE
    | SWP_NOZORDER
    | SWP_NOACTIVATE
)

DWMWA_BORDER_COLOR = 34
DWMWA_CAPTION_COLOR = 35
DWMWA_TEXT_COLOR = 36
DWMWA_COLOR_NONE = 0xFFFFFFFE

TITLEBAR_HEIGHT = 32
PRODUCT_SIDEBAR_WIDTH = 72
WINDOW_CONTROL_WIDTH = 36
WINDOW_CONTROL_COUNT = 3

TME_LEAVE = 0x00000002
TME_NONCLIENT = 0x00000010


class _TitleBarControl(QToolButton):
    """绘制标题栏按钮；物理输入继续由原生非客户区唯一持有。"""

    def __init__(self, name: str, parent: QWidget) -> None:
        super().__init__(parent)
        self.name = name
        self.hovered = False
        self.pressed = False
        self.maximized = False
        self.theme = "DARK"
        self.setObjectName(f"productTitleBar{name.title()}")
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)
        self.setFixedSize(WINDOW_CONTROL_WIDTH, 28)

    def paintEvent(self, _event) -> None:  # noqa: N802
        dark = self.theme == "DARK"
        text = QColor("#8b8da3" if dark else "#6b6480")
        if self.hovered or self.pressed:
            if self.name == "close":
                background, text = QColor("#e81123"), QColor("white")
            else:
                background = (
                    QColor(255, 255, 255, 20)
                    if dark
                    else QColor(80, 60, 140, 20)
                )
                text = QColor("#e2e4f0" if dark else "#2d2640")
        else:
            background = QColor(Qt.GlobalColor.transparent)
        painter = QPainter(self)
        painter.fillRect(
            self.rect(),
            QColor("#0a0b14" if dark else "#e8e3f0"),
        )
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(background)
        painter.drawRoundedRect(self.rect(), 4, 4)
        painter.setPen(QPen(text, 1.25))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        if self.name == "minimize":
            painter.drawLine(14, 15, 22, 15)
        elif self.name == "close":
            painter.drawLine(14, 10, 22, 18)
            painter.drawLine(22, 10, 14, 18)
        elif self.maximized:
            path = QPainterPath(QPointF(15.25, 9.25))
            path.lineTo(22.75, 9.25)
            path.lineTo(22.75, 16.75)
            path.lineTo(20.75, 16.75)
            path.moveTo(13.25, 11.25)
            path.lineTo(20.75, 11.25)
            path.lineTo(20.75, 18.75)
            path.lineTo(13.25, 18.75)
            path.closeSubpath()
            painter.drawPath(path)
        else:
            painter.drawRoundedRect(QRectF(13.25, 9.25, 9.5, 9.5), .25, .25)
        painter.end()


class ProductTitleBar(QWidget):
    """置于主窗口布局内、由原生非客户区接收输入的产品标题栏。"""

    minimize_requested = Signal()
    maximize_requested = Signal()
    close_requested = Signal()

    _controls = ("minimize", "maximize", "close")
    _labels = {
        "zh": {
            "title": "小仓",
            "minimize": "最小化",
            "maximize": "最大化",
            "restore": "还原",
            "close": "关闭",
        },
        "en": {
            "title": "Cangoo",
            "minimize": "Minimize",
            "maximize": "Maximize",
            "restore": "Restore",
            "close": "Close",
        },
    }

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._language = "zh"
        self._theme = "DARK"
        self._ui_font_scale = "100"
        self._maximized = False
        self._window_titles: dict[str, str] | None = None
        font_id = QFontDatabase.addApplicationFont(
            str(frontend_root() / "assets" / "fonts" / "Manrope-Variable.ttf")
        )
        families = QFontDatabase.applicationFontFamilies(font_id)
        self._font_family = families[0] if families else "Manrope"
        self._brand_icon = application_icon()
        self.setObjectName("productTitleBar")
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)
        self.setFixedHeight(TITLEBAR_HEIGHT)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 0, 0, 0)
        layout.setSpacing(0)
        layout.addStretch(1)
        self._buttons = {
            name: _TitleBarControl(name, self) for name in self._controls
        }
        for name in self._controls:
            layout.addWidget(self._buttons[name], 0, Qt.AlignmentFlag.AlignVCenter)
        self._buttons["minimize"].clicked.connect(self.minimize_requested)
        self._buttons["maximize"].clicked.connect(self.maximize_requested)
        self._buttons["close"].clicked.connect(self.close_requested)
        self._apply_labels()

    def set_control_state(self, hovered: str | None, pressed: str | None) -> None:
        self._validate_control(hovered)
        self._validate_control(pressed)
        for name, button in self._buttons.items():
            button.hovered = name == hovered
            button.pressed = name == pressed
            button.update()

    def set_maximized(self, maximized: bool) -> None:
        if type(maximized) is not bool:
            raise ValueError("maximized must be bool")
        self._maximized = maximized
        button = self._buttons["maximize"]
        button.maximized = maximized
        button.setProperty("pdmWindowState", "maximized" if maximized else "normal")
        button.update()
        self._apply_labels()

    def set_language(self, language: str) -> None:
        if language not in self._labels:
            raise ValueError("language must be 'zh' or 'en'")
        self._language = language
        self._apply_labels()
        self.update()

    def set_window_titles(self, zh_title: str, en_title: str) -> None:
        """设置当前窗口固定的中英文产品标题。"""

        self._window_titles = {
            "zh": self._validate_title(zh_title),
            "en": self._validate_title(en_title),
        }
        self._apply_labels()
        self.update()

    def reset_window_titles(self) -> None:
        """恢复主窗口默认的本地化标题。"""

        self._window_titles = None
        self._apply_labels()
        self.update()

    def set_effective_theme(self, theme: str) -> None:
        if theme not in {"LIGHT", "DARK"}:
            raise ValueError("theme must be 'LIGHT' or 'DARK'")
        self._theme = theme
        for button in self._buttons.values():
            button.theme = theme
            button.update()
        self.update()

    def set_ui_font_scale(self, scale: str) -> None:
        normalized = normalize_ui_font_scale(scale)
        if normalized != scale:
            raise ValueError("invalid UI font scale")
        self._ui_font_scale = scale
        self.update()

    def paintEvent(self, _event) -> None:  # noqa: N802
        dark = self._theme == "DARK"
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#0a0b14" if dark else "#e8e3f0"))
        border = (
            QColor(255, 255, 255, 10)
            if dark
            else QColor(80, 60, 140, 20)
        )
        painter.fillRect(0, self.height() - 1, self.width(), 1, border)
        self._brand_icon.paint(painter, QRect(14, 6, 20, 20))
        font = QFont(self._font_family)
        font.setPixelSize(scaled_font_pixel_size(12, self._ui_font_scale))
        font.setWeight(QFont.Weight.DemiBold)
        painter.setFont(font)
        painter.setPen(QColor("#8b8da3" if dark else "#6b6480"))
        painter.drawText(
            42,
            0,
            max(0, self.width() - 144),
            self.height(),
            Qt.AlignmentFlag.AlignVCenter,
            self._title(),
        )
        painter.end()

    def _apply_labels(self) -> None:
        labels = self._labels[self._language]
        self.setAccessibleName(self._title())
        for name, button in self._buttons.items():
            key = (
                "restore"
                if name == "maximize" and self._maximized
                else name
            )
            label = labels[key]
            button.setAccessibleName(label)
            button.setToolTip(label)

    def _validate_control(self, name: str | None) -> None:
        if name is not None and name not in self._controls:
            raise ValueError("control must be minimize, maximize, close, or None")

    @staticmethod
    def _validate_title(value: str) -> str:
        if (
            type(value) is not str
            or not value.strip()
            or len(value) > 64
            or "\x00" in value
        ):
            raise ValueError("window title must be a non-empty string up to 64 characters")
        return value

    def _title(self) -> str:
        if self._window_titles is not None:
            return self._window_titles[self._language]
        return self._labels[self._language]["title"]


def standard_window_frame_style_is_valid(style: int) -> bool:
    """Return whether a Qt top-level exposes every required Win32 ability."""

    if type(style) is not int:
        return False
    return (style & STANDARD_WINDOW_FRAME_STYLE) == (
        STANDARD_WINDOW_FRAME_STYLE
    )


def apply_standard_window_frame(hwnd: int, user32=None) -> bool:
    """Verify one hidden Qt HWND and make its calculated client frame current."""

    if type(hwnd) is not int or hwnd <= 0:
        return False
    if user32 is None:
        if sys.platform != "win32":
            return False
        try:
            user32 = ctypes.windll.user32
            from ctypes import wintypes

            user32.GetWindowLongPtrW.argtypes = (
                wintypes.HWND,
                ctypes.c_int,
            )
            user32.GetWindowLongPtrW.restype = ctypes.c_ssize_t
            user32.SetWindowPos.argtypes = (
                wintypes.HWND,
                wintypes.HWND,
                ctypes.c_int,
                ctypes.c_int,
                ctypes.c_int,
                ctypes.c_int,
                wintypes.UINT,
            )
            user32.SetWindowPos.restype = wintypes.BOOL
        except Exception:
            return False
    try:
        from ctypes import wintypes

        get_style = user32.GetWindowLongPtrW
        set_window_pos = user32.SetWindowPos
        window_handle = wintypes.HWND(hwnd)
        insert_after = wintypes.HWND()
        style = int(get_style(window_handle, ctypes.c_int(GWL_STYLE)))
        if not standard_window_frame_style_is_valid(style):
            return False
        return bool(
            set_window_pos(
                window_handle,
                insert_after,
                ctypes.c_int(0),
                ctypes.c_int(0),
                ctypes.c_int(0),
                ctypes.c_int(0),
                STANDARD_WINDOW_FRAME_CHANGED_FLAGS,
            )
        )
    except Exception:
        return False


def set_win11_border_color_none(
    hwnd: int,
    *,
    dwmapi=None,
    windows_build: int | None = None,
) -> bool:
    """Hide the Win11 DWM border once for the standard-frame candidate."""

    if type(hwnd) is not int or hwnd <= 0:
        return False
    if windows_build is None:
        if sys.platform != "win32":
            return False
        try:
            windows_build = int(sys.getwindowsversion().build)
        except Exception:
            return False
    if type(windows_build) is not int:
        return False
    if windows_build < 22000:
        return True
    if dwmapi is None:
        if sys.platform != "win32":
            return False
        try:
            dwmapi = ctypes.windll.dwmapi
            from ctypes import wintypes

            dwmapi.DwmSetWindowAttribute.argtypes = (
                wintypes.HWND,
                wintypes.DWORD,
                ctypes.c_void_p,
                wintypes.DWORD,
            )
            dwmapi.DwmSetWindowAttribute.restype = ctypes.c_long
        except Exception:
            return False
    try:
        from ctypes import wintypes

        color = wintypes.DWORD(DWMWA_COLOR_NONE)
        result = dwmapi.DwmSetWindowAttribute(
            wintypes.HWND(hwnd),
            wintypes.DWORD(DWMWA_BORDER_COLOR),
            ctypes.byref(color),
            wintypes.DWORD(ctypes.sizeof(color)),
        )
        return int(result) == 0
    except Exception:
        return False


def set_win11_caption_colors(
    hwnd: int,
    background: str,
    foreground: str,
    *,
    dwmapi=None,
    windows_build: int | None = None,
) -> bool:
    """在支持的 Windows 11 窗口上设置原生标题背景与文字颜色。"""

    caption = QColor(background)
    text = QColor(foreground)
    if type(hwnd) is not int or hwnd <= 0 or not caption.isValid() or not text.isValid():
        return False
    if windows_build is None:
        if sys.platform != "win32":
            return False
        try:
            windows_build = int(sys.getwindowsversion().build)
        except Exception:
            return False
    if type(windows_build) is not int or windows_build < 22000:
        return False
    try:
        from ctypes import wintypes

        if dwmapi is None:
            dwmapi = ctypes.windll.dwmapi
            dwmapi.DwmSetWindowAttribute.argtypes = (
                wintypes.HWND, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD,
            )
            dwmapi.DwmSetWindowAttribute.restype = ctypes.c_long

        def apply(attribute: int, color: QColor) -> bool:
            value = wintypes.DWORD(color.red() | color.green() << 8 | color.blue() << 16)
            return int(dwmapi.DwmSetWindowAttribute(
                wintypes.HWND(hwnd), wintypes.DWORD(attribute),
                byref(value), wintypes.DWORD(sizeof(value)),
            )) == 0

        if not apply(DWMWA_CAPTION_COLOR, caption):
            return False
        if apply(DWMWA_TEXT_COLOR, text):
            return True
        default = wintypes.DWORD(0xFFFFFFFF)
        dwmapi.DwmSetWindowAttribute(
            wintypes.HWND(hwnd), wintypes.DWORD(DWMWA_CAPTION_COLOR),
            byref(default), wintypes.DWORD(sizeof(default)),
        )
    except Exception:
        pass
    return False


def standard_window_frame_client_rect(
    rect: tuple[int, int, int, int],
    *,
    maximized: bool,
    border_x: int,
    border_y: int,
) -> tuple[int, int, int, int]:
    """Return the WM_NCCALCSIZE client rectangle for the standard-frame mode."""

    if (
        type(rect) is not tuple
        or len(rect) != 4
        or any(type(value) is not int for value in rect)
    ):
        raise TypeError("standard frame rect must be four integers")
    if type(maximized) is not bool:
        raise TypeError("standard frame maximized flag must be bool")
    if type(border_x) is not int or type(border_y) is not int:
        raise TypeError("standard frame borders must be integers")
    left, top, right, bottom = rect
    if not maximized:
        return rect
    horizontal = min(max(0, border_x), max(0, (right - left - 1) // 2))
    vertical = min(max(0, border_y), max(0, (bottom - top - 1) // 2))
    return (
        left + horizontal,
        top + vertical,
        right - horizontal,
        bottom - vertical,
    )


def native_window_is_maximized(hwnd: int) -> bool:
    """Read the current Win32 zoom state for an NCCALCSIZE transition."""

    if sys.platform != "win32" or type(hwnd) is not int or hwnd <= 0:
        return False
    try:
        from ctypes import wintypes

        is_zoomed = ctypes.windll.user32.IsZoomed
        is_zoomed.argtypes = (wintypes.HWND,)
        is_zoomed.restype = wintypes.BOOL
        return bool(is_zoomed(wintypes.HWND(hwnd)))
    except Exception:
        return False


def resize_hit_test(
    x: int,
    y: int,
    left: int,
    top: int,
    right: int,
    bottom: int,
    border_x: int,
    border_y: int,
) -> int | None:
    """Return the native resize hit for a screen point on a window border."""

    on_left = left <= x < left + border_x
    on_right = right - border_x <= x < right
    on_top = top <= y < top + border_y
    on_bottom = bottom - border_y <= y < bottom

    if on_top and on_left:
        return HTTOPLEFT
    if on_top and on_right:
        return HTTOPRIGHT
    if on_bottom and on_left:
        return HTBOTTOMLEFT
    if on_bottom and on_right:
        return HTBOTTOMRIGHT
    if on_left:
        return HTLEFT
    if on_right:
        return HTRIGHT
    if on_top:
        return HTTOP
    if on_bottom:
        return HTBOTTOM
    return None


def native_resize_border(hwnd: int) -> tuple[int, int]:
    """Return the DPI-aware Windows resize border in physical pixels."""

    if sys.platform != "win32":
        return 8, 8
    try:
        from ctypes import wintypes

        user32 = ctypes.windll.user32
        get_dpi = getattr(user32, "GetDpiForWindow", None)
        if get_dpi is not None:
            get_dpi.argtypes = (wintypes.HWND,)
            get_dpi.restype = wintypes.UINT
            dpi = int(get_dpi(wintypes.HWND(hwnd)))
        else:
            dpi = 96
        get_metric = getattr(user32, "GetSystemMetricsForDpi", None)
        if get_metric is not None:
            get_metric.argtypes = (ctypes.c_int, wintypes.UINT)
            get_metric.restype = ctypes.c_int
            padded = int(get_metric(92, dpi))  # SM_CXPADDEDBORDER
            return (
                max(6, int(get_metric(32, dpi)) + padded),  # SM_CXSIZEFRAME
                max(6, int(get_metric(33, dpi)) + padded),  # SM_CYSIZEFRAME
            )
        scaled = max(6, round(8 * dpi / 96))
        return scaled, scaled
    except Exception:
        return 8, 8


def native_dpi_scale(hwnd: int) -> float:
    """Return the physical-pixel scale used by Win32 hit-test coordinates."""

    if sys.platform != "win32":
        return 1.0
    try:
        from ctypes import wintypes

        user32 = ctypes.windll.user32
        get_dpi = getattr(user32, "GetDpiForWindow", None)
        if get_dpi is None:
            return 1.0
        get_dpi.argtypes = (wintypes.HWND,)
        get_dpi.restype = wintypes.UINT
        dpi = int(get_dpi(wintypes.HWND(hwnd)))
        return max(1.0, dpi / 96.0)
    except Exception:
        return 1.0


def set_win11_corner_preference(hwnd: int, maximized: bool = False) -> bool:
    """Use round corners normally and square corners while maximized."""

    if sys.platform != "win32":
        return False
    try:
        from ctypes import wintypes

        dwmapi = ctypes.windll.dwmapi
        dwmapi.DwmSetWindowAttribute.argtypes = (
            wintypes.HWND,
            wintypes.DWORD,
            ctypes.c_void_p,
            wintypes.DWORD,
        )
        dwmapi.DwmSetWindowAttribute.restype = ctypes.c_long
        preference = c_int(1 if maximized else 2)  # DONOTROUND / ROUND
        result = dwmapi.DwmSetWindowAttribute(
            wintypes.HWND(hwnd),
            wintypes.DWORD(33),  # DWMWA_WINDOW_CORNER_PREFERENCE
            byref(preference),
            wintypes.DWORD(sizeof(preference)),
        )
        return result == 0
    except Exception:
        return False


def window_control_at(point: QPoint, window_width: int) -> str | None:
    """Map a logical client point to one of the three visible DOM controls."""

    controls_left = window_width - WINDOW_CONTROL_WIDTH * WINDOW_CONTROL_COUNT
    if not (
        0 <= point.y() < TITLEBAR_HEIGHT
        and controls_left <= point.x() < window_width
    ):
        return None
    index = (point.x() - controls_left) // WINDOW_CONTROL_WIDTH
    return ("minimize", "maximize", "close")[index]


def is_caption_point(point: QPoint, window_width: int) -> bool:
    """Return whether a logical point belongs to the non-control titlebar."""

    return (
        0 <= point.y() < TITLEBAR_HEIGHT
        and 0 <= point.x() < window_width - WINDOW_CONTROL_WIDTH * WINDOW_CONTROL_COUNT
    )


def native_window_control_hit(
    x: int,
    y: int,
    left: int,
    top: int,
    right: int,
    scale: float,
) -> int | None:
    """Map physical screen coordinates to the DOM-painted control regions."""

    titlebar_bottom = top + round(TITLEBAR_HEIGHT * scale)
    controls_width = round(
        WINDOW_CONTROL_WIDTH * WINDOW_CONTROL_COUNT * scale
    )
    if not (
        top <= y < titlebar_bottom
        and right - controls_width <= x < right
    ):
        return None
    relative_x = x - (right - controls_width)
    control_width = WINDOW_CONTROL_WIDTH * scale
    index = min(WINDOW_CONTROL_COUNT - 1, int(relative_x / control_width))
    return (HTMINBUTTON, HTMAXBUTTON, HTCLOSE)[index]


def native_window_control_hit_at_cursor(
    hwnd: int,
    *,
    client_rect: tuple[int, int, int, int] | None = None,
) -> int | None:
    """Resolve a control hit from the current physical cursor position."""

    if sys.platform != "win32" or int(hwnd) <= 0:
        return None
    try:
        from ctypes import wintypes

        point = wintypes.POINT()
        rect = wintypes.RECT()
        user32 = ctypes.windll.user32
        user32.GetWindowRect.argtypes = (
            wintypes.HWND,
            ctypes.POINTER(wintypes.RECT),
        )
        user32.GetWindowRect.restype = wintypes.BOOL
        if not user32.GetCursorPos(ctypes.byref(point)):
            return None
        if not user32.GetWindowRect(
            wintypes.HWND(hwnd),
            ctypes.byref(rect),
        ):
            return None
        bounds = client_rect or (
            int(rect.left),
            int(rect.top),
            int(rect.right),
            int(rect.bottom),
        )
        return native_window_control_hit(
            int(point.x),
            int(point.y),
            bounds[0],
            bounds[1],
            bounds[2],
            native_dpi_scale(int(hwnd)),
        )
    except Exception:
        return None


def track_non_client_mouse_leave(hwnd: int) -> bool:
    """Request one WM_NCMOUSELEAVE notification for the current HWND."""

    if sys.platform != "win32":
        return False
    try:
        from ctypes import wintypes

        class TRACKMOUSEEVENT(ctypes.Structure):
            _fields_ = [
                ("cbSize", wintypes.DWORD),
                ("dwFlags", wintypes.DWORD),
                ("hwndTrack", wintypes.HWND),
                ("dwHoverTime", wintypes.DWORD),
            ]

        request = TRACKMOUSEEVENT()
        request.cbSize = ctypes.sizeof(request)
        request.dwFlags = TME_LEAVE | TME_NONCLIENT
        request.hwndTrack = hwnd
        request.dwHoverTime = 0
        return bool(ctypes.windll.user32.TrackMouseEvent(ctypes.byref(request)))
    except Exception:
        return False


class WebChromeInputFilter(QObject):
    """Route DOM-painted window chrome to the native host without a Bridge."""

    def __init__(
        self,
        window,
        view,
        reset_focus_visibility: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(window)
        self._window = window
        self._view = view
        self._reset_focus_visibility = reset_focus_visibility
        self._copy_interaction: Callable[[], None] | None = None
        self._copy_shortcut: Callable[[], None] | None = None
        self._pressed_control: str | None = None
        self._caption_press_global: QPoint | None = None

    def reset(self) -> None:
        self._pressed_control = None
        self._caption_press_global = None

    def bind_view(self, view) -> None:
        """Atomically retarget chrome input after renderer-view recovery."""

        if view is None:
            raise TypeError("chrome input view is required")
        self.reset()
        self._view = view

    def set_copy_shortcut_handlers(
        self,
        interaction: Callable[[], None] | None,
        shortcut: Callable[[], None] | None,
    ) -> None:
        if interaction is not None and not callable(interaction):
            raise TypeError("copy interaction handler must be callable")
        if shortcut is not None and not callable(shortcut):
            raise TypeError("copy shortcut handler must be callable")
        self._copy_interaction = interaction
        self._copy_shortcut = shortcut

    def _belongs_to_view(self, watched: QObject) -> bool:
        current: QObject | None = watched
        while current is not None:
            if current is self._view:
                return True
            current = current.parent()
        return False

    def _request_focus_visibility_reset(self) -> None:
        callback = self._reset_focus_visibility
        if callback is None:
            return
        try:
            callback()
        except Exception:
            # 焦点可见性是局部呈现状态；清理失败不能吞掉原生输入。
            pass

    @staticmethod
    def _safe_call(callback: Callable[[], None] | None) -> None:
        if callback is None:
            return
        try:
            callback()
        except Exception:
            pass

    def _copy_event_belongs_to_view(self, watched: QObject) -> bool:
        if self._belongs_to_view(watched):
            return True
        focused = QApplication.focusWidget()
        return watched is self._window and (
            focused is not None and self._belongs_to_view(focused)
        )

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:  # noqa: N802
        if event.type() == QEvent.Type.WindowDeactivate:
            self._safe_call(self._copy_interaction)
            self.reset()
            return False
        if (
            event.type() == QEvent.Type.MouseButtonRelease
            and not self._belongs_to_view(watched)
            and (
                self._pressed_control is not None
                or self._caption_press_global is not None
            )
        ):
            self.reset()
            return False
        event_type = event.type()
        if (
            event_type == QEvent.Type.ShortcutOverride
            and self._copy_shortcut is not None
            and isinstance(event, QKeyEvent)
            and event.matches(QKeySequence.StandardKey.Copy)
            and self._copy_event_belongs_to_view(watched)
        ):
            event.accept()
            return False
        if not self._belongs_to_view(watched):
            return False

        if event_type in {QEvent.Type.FocusIn, QEvent.Type.FocusOut}:
            self._safe_call(self._copy_interaction)
            return False
        if event_type == QEvent.Type.KeyPress:
            if (
                isinstance(event, QKeyEvent)
                and self._copy_shortcut is not None
                and event.matches(QKeySequence.StandardKey.Copy)
            ):
                if not event.isAutoRepeat():
                    self._safe_call(self._copy_shortcut)
                event.accept()
                return True
            self._safe_call(self._copy_interaction)
            return False
        if event_type in {
            QEvent.Type.MouseButtonPress,
            QEvent.Type.TabletPress,
            QEvent.Type.TouchBegin,
        }:
            self._safe_call(self._copy_interaction)
            self._request_focus_visibility_reset()
        mouse_types = {
            QEvent.Type.MouseButtonPress,
            QEvent.Type.MouseButtonRelease,
            QEvent.Type.MouseButtonDblClick,
            QEvent.Type.MouseMove,
        }
        if event_type not in mouse_types or not hasattr(event, "globalPosition"):
            return False

        global_point = event.globalPosition().toPoint()
        local_point = self._window.mapFromGlobal(global_point)
        control = window_control_at(local_point, self._window.width())
        in_caption = is_caption_point(local_point, self._window.width())

        if event_type == QEvent.Type.MouseButtonPress:
            if event.button() != Qt.MouseButton.LeftButton:
                return False
            if control is not None:
                self._pressed_control = control
                self._caption_press_global = None
                event.accept()
                return True
            if self._window.isMaximized() and in_caption:
                self._caption_press_global = global_point
                self._pressed_control = None
                event.accept()
                return True
            return False

        if event_type == QEvent.Type.MouseMove:
            if self._pressed_control is not None:
                event.accept()
                return True
            if self._caption_press_global is not None:
                delta = global_point - self._caption_press_global
                threshold = QApplication.styleHints().startDragDistance()
                if abs(delta.x()) + abs(delta.y()) >= threshold:
                    self._caption_press_global = None
                    self._window._restore_maximized_for_caption_drag(global_point)
                event.accept()
                return True
            return False

        if event_type == QEvent.Type.MouseButtonDblClick:
            if event.button() != Qt.MouseButton.LeftButton:
                return False
            if control is not None:
                self.reset()
                event.accept()
                return True
            if self._window.isMaximized() and in_caption:
                self.reset()
                self._window._toggle_maximize()
                event.accept()
                return True
            return False

        if event_type == QEvent.Type.MouseButtonRelease:
            if event.button() != Qt.MouseButton.LeftButton:
                return False
            pressed_control = self._pressed_control
            had_caption_press = self._caption_press_global is not None
            self.reset()
            if pressed_control is not None:
                if control == pressed_control:
                    self._window._perform_window_control(pressed_control)
                event.accept()
                return True
            if had_caption_press:
                event.accept()
                return True
        return False
