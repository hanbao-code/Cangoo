"""Independent native QWidget QuickBar for the isolated M4 candidate.

The widget only receives bounded public summaries. Account/password copy and
password generation stay behind the typed native port and never return secret
text to this object. The top-level window is intentionally outside the main
window tree: global invocation cannot restore or foreground the full product.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
import time
from typing import Protocol
import uuid

from PySide6.QtCore import QEvent, QObject, QPoint, Qt, QTimer, Signal, Slot
from PySide6.QtGui import (
    QAccessible,
    QAccessibleAnnouncementEvent,
    QColor,
    QCursor,
    QFont,
    QPainter,
)
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from core.platform import platform_color, platform_icon
from desktop.bridge.command_ids import CommandId
from desktop.bridge.contract_catalog import ContractCatalog
from desktop.bridge.native_quickbar import NativeQuickbarPort
from desktop.bridge.protocol import (
    AdapterCompletion,
    AdapterRequest,
    BridgeAdapter,
    CompletionCallback,
    CompletionEnvelope,
)
from desktop.host.focus_visibility import (
    NativeFocusVisibilityController,
    install_managed_focus_fallback,
)
from desktop.host.quickbar_focus import NativeQuickbarFocus
from desktop.ui_font_scale import UI_FONT_SCALES, scaled_font_pixel_size


_GENERATOR = re.compile(r"^gen\s*(\d*)$", re.IGNORECASE)
_QUERY_MAX_CHARS = 128
_QUERY_MAX_UTF8_BYTES = 512
_GENERATOR_MIN_LENGTH = 4
_GENERATOR_MAX_LENGTH = 1024

_TEXT = {
    "ZH": {
        "window": "快捷搜索",
        "search": "搜索条目或输入命令",
        "placeholder": "搜索条目名称或输入命令 (gen 20)...",
        "empty": "输入条目名称搜索，或输入 gen 20 生成密码",
        "not_found": "未找到匹配记录",
        "loading": "正在搜索…",
        "generate": "生成 {length} 位随机密码 — 按 Enter 复制",
        "generate_hint": "包含大小写字母、数字和特殊字符",
        "generate_copied": "已复制",
        "generate_range": "生成长度仅支持 4–1024 位",
        "query_chars": "搜索内容最多 128 个字符，请删减后重试",
        "query_bytes": "搜索内容最多 512 个 UTF-8 字节，请删减后重试",
        "more_results": "共 {total} 条，继续输入以缩小范围",
        "account_empty": "账号为空，未复制",
        "password_empty": "密码为空，未复制",
        "clipboard_unavailable": "剪贴板暂时不可用，请重试",
        "copy_busy": "另一个操作正在进行，请稍后重试",
        "copy_cancelled": "复制已取消",
        "account": "账号",
        "password": "密码",
        "copy_account": "复制账号",
        "copy_password": "复制密码",
        "copied": "已复制",
        "account_copied": "账号已复制",
        "password_copied": "密码已复制",
        "generated_password_copied": "密码已生成并复制",
        "footer": "Enter 复制密码  ·  Ctrl+Enter 复制账号",
        "autohide": "{seconds} 秒后自动隐藏",
        "clear": "清空搜索",
        "move": "拖动 Quick Bar",
        "failed": "操作未完成，请重试",
    },
    "EN": {
        "window": "Quick search",
        "search": "Search entries or enter a command",
        "placeholder": "Search entry name or type command (gen 20)...",
        "empty": "Search an entry, or type gen 20 to generate a password",
        "not_found": "No matching records",
        "loading": "Searching…",
        "generate": "Generate {length}-char random password — press Enter to copy",
        "generate_hint": "Includes upper/lower case, digits, and symbols",
        "generate_copied": "Copied",
        "generate_range": "Password length must be 4–1024 characters",
        "query_chars": "Search is limited to 128 characters. Remove some text and try again.",
        "query_bytes": "Search is limited to 512 UTF-8 bytes. Remove some text and try again.",
        "more_results": "{total} results — keep typing to narrow the search",
        "account_empty": "The account is empty and was not copied",
        "password_empty": "The password is empty and was not copied",
        "clipboard_unavailable": "The clipboard is unavailable. Try again",
        "copy_busy": "Another action is in progress. Try again shortly",
        "copy_cancelled": "Copy cancelled",
        "account": "Account",
        "password": "Password",
        "copy_account": "Copy account",
        "copy_password": "Copy password",
        "copied": "Copied",
        "account_copied": "Account copied",
        "password_copied": "Password copied",
        "generated_password_copied": "Password generated and copied",
        "footer": "Enter: password  ·  Ctrl+Enter: account",
        "autohide": "Auto-hide in {seconds}s",
        "clear": "Clear search",
        "move": "Drag Quick Bar",
        "failed": "The action could not be completed. Try again.",
    },
}

_COPY_FEEDBACK_KEYS = {
    "CLIPBOARD_UNAVAILABLE": "clipboard_unavailable",
    "REQUEST_BUSY": "copy_busy",
    "CANCELLED": "copy_cancelled",
}


def _parse_generator_command(query: str) -> tuple[int | None, bool]:
    """Return a generator length and whether ``query`` is command-shaped."""

    matched = _GENERATOR.fullmatch(query.strip())
    if matched is None:
        return None, False
    try:
        length = int(matched.group(1) or 20)
    except ValueError:
        return None, False
    return length, True


def _query_limit_error(query: str) -> str | None:
    if len(query) > _QUERY_MAX_CHARS:
        return "query_chars"
    if len(query.encode("utf-8")) > _QUERY_MAX_UTF8_BYTES:
        return "query_bytes"
    return None


class QuickbarFocusPort(Protocol):
    def foreground_window(self) -> int: ...

    def is_window(self, hwnd: int) -> bool: ...

    def monitor_name_for_window(self, hwnd: int) -> str: ...

    def activate_window(self, hwnd: int) -> bool: ...


@dataclass(frozen=True, slots=True)
class QuickbarSummary:
    record_id: int
    revision: str
    platform: str
    account_display: str
    favorite: bool
    has_totp: bool


class _PassiveQuickbarAdapter:
    """Delegate requests, while leaving lifecycle authority with Web Bridge."""

    def __init__(self, adapter: BridgeAdapter) -> None:
        self._adapter = adapter

    def submit(
        self,
        request: AdapterRequest,
        complete: CompletionCallback,
    ) -> None:
        self._adapter.submit(request, complete)

    def cancel(self, request: AdapterRequest) -> str:
        return self._adapter.cancel(request)

    def invalidate_page(self, page_epoch: int) -> None:
        del page_epoch

    def invalidate_session(self, session_epoch: int) -> None:
        del session_epoch

    def revoke_secret_lease(self, secret_lease_id: str) -> None:
        del secret_lease_id

    def discard(self, completion: AdapterCompletion) -> None:
        self._adapter.discard(completion)

    def close(self) -> None:
        return


class _PlatformBadge(QWidget):
    def __init__(
        self,
        platform: str,
        ui_font_scale: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._platform = platform
        self._ui_font_scale = ui_font_scale
        self.setFixedSize(32, 32)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def paintEvent(self, event) -> None:  # noqa: N802
        del event
        color = QColor(platform_color(self._platform))
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor(color.red(), color.green(), color.blue(), 34))
        painter.setPen(QColor(color.red(), color.green(), color.blue(), 70))
        painter.drawRoundedRect(self.rect().adjusted(0, 0, -1, -1), 6, 6)
        painter.setPen(color)
        font = painter.font()
        font.setPixelSize(scaled_font_pixel_size(14, self._ui_font_scale))
        font.setWeight(QFont.Weight.DemiBold)
        painter.setFont(font)
        painter.drawText(
            self.rect(),
            Qt.AlignmentFlag.AlignCenter,
            platform_icon(self._platform),
        )

    def set_ui_font_scale(self, scale: str) -> None:
        scaled_font_pixel_size(14, scale)
        self._ui_font_scale = scale
        self.update()


class _ResultRow(QFrame):
    action_requested = Signal(str, int, str, object)

    def __init__(
        self,
        summary: QuickbarSummary,
        index: int,
        language: str,
        ui_font_scale: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.summary = summary
        self.index = index
        self._language = language
        self._ui_font_scale = ui_font_scale
        self.setObjectName("m4QuickbarResult")
        self.setProperty("highlighted", False)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setFixedHeight(54)
        layout = QHBoxLayout(self)
        self._layout = layout
        layout.setContentsMargins(12, 8, 10, 8)
        layout.setSpacing(12)
        self._badge = _PlatformBadge(summary.platform, ui_font_scale, self)
        layout.addWidget(self._badge)

        info = QVBoxLayout()
        info.setContentsMargins(0, 0, 0, 0)
        info.setSpacing(1)
        name = QLabel(summary.platform, self)
        name.setObjectName("m4QuickbarName")
        name.setTextFormat(Qt.TextFormat.PlainText)
        self.account_label = QLabel(summary.account_display, self)
        self.account_label.setObjectName("m4QuickbarAccount")
        self.account_label.setTextFormat(Qt.TextFormat.PlainText)
        self._feedback_token = 0
        self._feedback_key: str | None = None
        info.addWidget(name)
        info.addWidget(self.account_label)
        layout.addLayout(info, 1)

        text = _TEXT[language]
        self.account_button = self._make_button(text["account"], "account")
        self.password_button = self._make_button(
            text["password"],
            "password",
        )
        layout.addWidget(self.account_button)
        layout.addWidget(self.password_button)

    def _make_button(self, label: str, action: str) -> QPushButton:
        button = QPushButton(label, self)
        button.setObjectName("m4QuickbarCopy")
        button.setProperty("copied", False)
        button.setProperty("pdmFocusVisualManaged", True)
        button.setProperty("pdmFocusFrameReady", False)
        button.setProperty("pdmFocusRadius", 4)
        button.setAccessibleName(_TEXT[self._language][f"copy_{action}"])
        button.setFixedHeight(28)
        button.clicked.connect(
            lambda _checked=False, value=action, source=button: (
                self.action_requested.emit(
                    value,
                    self.summary.record_id,
                    self.summary.revision,
                    source,
                )
            )
        )
        return button

    def set_highlighted(self, highlighted: bool) -> None:
        self.setProperty("highlighted", highlighted)
        self.style().unpolish(self)
        self.style().polish(self)

    def flash_copied(self, button: QPushButton) -> None:
        button.setText("✓")
        button.setAccessibleName(_TEXT[self._language]["copied"])
        button.setProperty("copied", True)
        button.style().unpolish(button)
        button.style().polish(button)

        def restore() -> None:
            try:
                button.setProperty("copied", False)
                self.set_language(self._language)
                button.style().unpolish(button)
                button.style().polish(button)
            except RuntimeError:
                pass

        QTimer.singleShot(1200, restore)

    def flash_message(self, key: str) -> None:
        self._feedback_token += 1
        token = self._feedback_token
        self._feedback_key = key
        self.account_label.setText(_TEXT[self._language][key])
        QTimer.singleShot(2000, lambda: self._restore_message(token))

    def _restore_message(self, token: int) -> None:
        try:
            if token == self._feedback_token:
                self._feedback_key = None
                self.account_label.setText(self.summary.account_display)
        except RuntimeError:
            pass

    def set_language(self, language: str) -> None:
        self._language = language
        text = _TEXT[language]
        for action, button in (
            ("account", self.account_button),
            ("password", self.password_button),
        ):
            if bool(button.property("copied")):
                button.setAccessibleName(text["copied"])
            else:
                button.setText(text[action])
                button.setAccessibleName(text[f"copy_{action}"])
        if self._feedback_key is not None:
            self.account_label.setText(text[self._feedback_key])

    def set_ui_font_scale(self, scale: str) -> None:
        scaled_font_pixel_size(14, scale)
        self._ui_font_scale = scale
        vertical_margin = 7 if scale == "125" else 8
        self._layout.setContentsMargins(12, vertical_margin, 10, vertical_margin)
        self._badge.set_ui_font_scale(scale)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self.action_requested.emit(
                "password",
                self.summary.record_id,
                self.summary.revision,
                self.password_button,
            )
        super().mouseReleaseEvent(event)


class NativeQuickbarWidget(QWidget):
    query_changed = Signal(str)
    projection_refresh_requested = Signal(str)
    row_action_requested = Signal(str, int, str, object)
    generate_requested = Signal(int)
    closed = Signal(str)

    def __init__(
        self,
        focus_port: QuickbarFocusPort | None = None,
    ) -> None:
        flags = (
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        super().__init__(None, flags)
        self._focus_port = focus_port or NativeQuickbarFocus()
        self._language = "ZH"
        self._theme = "DARK"
        self._ui_font_scale = "100"
        self._idle_seconds = 30
        self._rows: list[_ResultRow] = []
        self._summaries: list[QuickbarSummary] = []
        self._index = 0
        self._command_length: int | None = None
        self._command_button: QPushButton | None = None
        self._generate_hint: QLabel | None = None
        self._generate_feedback_token = 0
        self._return_hwnd = 0
        self._screen_name = ""
        self._drag_active = False
        self._drag_offset = QPoint()
        self._user_positioned = False
        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.setInterval(30_000)
        self._hide_timer.timeout.connect(
            lambda: self.close_bar("timeout", restore_if_owned=True)
        )
        self._countdown_timer = QTimer(self)
        self._countdown_timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._countdown_timer.setInterval(1000)
        self._countdown_timer.timeout.connect(self._refresh_autohide_label)
        self._last_autohide_seconds: int | None = None
        self.setObjectName("m4NativeQuickbarWindow")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)
        self.hide()

        outer = QVBoxLayout(self)
        outer.setContentsMargins(8, 8, 8, 8)
        outer.setSpacing(0)
        self.card = QFrame(self)
        self.card.setObjectName("m4NativeQuickbarCard")
        self.card.setFixedWidth(480)
        self.card.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(0)

        self.drag_area = QFrame(self.card)
        self.drag_area.setObjectName("m4QuickbarDragArea")
        self.drag_area.setFixedHeight(16)
        self.drag_area.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.drag_area.setCursor(Qt.CursorShape.SizeAllCursor)
        drag_layout = QHBoxLayout(self.drag_area)
        drag_layout.setContentsMargins(0, 6, 0, 4)
        drag_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.drag_grip = QFrame(self.drag_area)
        self.drag_grip.setObjectName("m4QuickbarDragGrip")
        self.drag_grip.setFixedSize(32, 3)
        self.drag_grip.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.drag_grip.setCursor(Qt.CursorShape.SizeAllCursor)
        drag_layout.addWidget(self.drag_grip)
        card_layout.addWidget(self.drag_area)

        input_frame = QFrame(self.card)
        input_frame.setObjectName("m4QuickbarInputWrap")
        input_layout = QHBoxLayout(input_frame)
        input_layout.setContentsMargins(16, 14, 16, 14)
        input_layout.setSpacing(0)
        self.search_halo = QFrame(input_frame)
        self.search_halo.setObjectName("m4QuickbarSearchHalo")
        self.search_halo.setProperty("focused", False)
        self.search_halo.setFixedHeight(46)
        halo_layout = QHBoxLayout(self.search_halo)
        halo_layout.setContentsMargins(3, 3, 3, 3)
        halo_layout.setSpacing(0)
        self.search_box = QFrame(self.search_halo)
        self.search_box.setObjectName("m4QuickbarSearchBox")
        self.search_box.setFixedHeight(40)
        search_layout = QHBoxLayout(self.search_box)
        search_layout.setContentsMargins(12, 0, 6, 0)
        search_layout.setSpacing(8)
        self.search_icon = QLabel("⌕", self.search_box)
        self.search_icon.setObjectName("m4QuickbarSearchIcon")
        self.search_icon.setFixedWidth(18)
        self.search_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        search_layout.addWidget(self.search_icon)
        self.input = QLineEdit(self.search_box)
        self.input.setObjectName("m4QuickbarInput")
        self.input.setClearButtonEnabled(False)
        self.input.setMaxLength(256)
        search_layout.addWidget(self.input, 1)
        self.clear_slot = QWidget(self.search_box)
        self.clear_slot.setObjectName("m4QuickbarClearSlot")
        self.clear_slot.setFixedSize(28, 28)
        clear_layout = QHBoxLayout(self.clear_slot)
        clear_layout.setContentsMargins(0, 0, 0, 0)
        clear_layout.setSpacing(0)
        self.clear_button = QPushButton("×", self.clear_slot)
        self.clear_button.setObjectName("m4QuickbarClear")
        self.clear_button.setProperty("pdmFocusVisualManaged", True)
        self.clear_button.setProperty("pdmFocusFrameReady", False)
        self.clear_button.setProperty("pdmFocusRadius", 5)
        self.clear_button.setFixedSize(28, 28)
        self.clear_button.hide()
        self.clear_button.clicked.connect(self._clear_search)
        clear_layout.addWidget(self.clear_button)
        search_layout.addWidget(self.clear_slot)
        self.input.textChanged.connect(self._on_input_text_changed)
        halo_layout.addWidget(self.search_box)
        input_layout.addWidget(self.search_halo, 1)
        card_layout.addWidget(input_frame)

        self.result_host = QWidget(self.card)
        self.result_layout = QVBoxLayout(self.result_host)
        self.result_layout.setContentsMargins(6, 6, 6, 6)
        self.result_layout.setSpacing(0)
        self.scroll = QScrollArea(self.card)
        self.scroll.setObjectName("m4QuickbarResults")
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.scroll.setWidget(self.result_host)
        self.scroll.setMaximumHeight(360)
        card_layout.addWidget(self.scroll)

        footer = QFrame(self.card)
        footer.setObjectName("m4QuickbarFooter")
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(16, 8, 16, 8)
        footer_layout.setSpacing(12)
        self.shortcut_label = QLabel(footer)
        self.shortcut_label.setObjectName("m4QuickbarFooterText")
        self.autohide_label = QLabel(footer)
        self.autohide_label.setObjectName("m4QuickbarFooterText")
        self.autohide_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        footer_layout.addWidget(self.shortcut_label)
        footer_layout.addWidget(self.autohide_label, 1)
        card_layout.addWidget(footer)
        outer.addWidget(self.card)

        self._watch_activity(self)
        self._focus_visibility: NativeFocusVisibilityController | None
        try:
            self._focus_visibility = NativeFocusVisibilityController(
                self,
                lambda: self._focus_targets(),
                effective_theme=self._theme,
                safe_anchor=self,
                parent=self,
            )
        except Exception:
            self._focus_visibility = None
        self.apply_projection("DARK", "ZH", 30, "100")

    @property
    def idle_seconds(self) -> int:
        return self._idle_seconds

    @property
    def return_hwnd(self) -> int:
        return self._return_hwnd

    def announce_accessible_result(self, key: str) -> bool:
        if not self.isVisible() or key not in _TEXT[self._language]:
            return False
        try:
            event = QAccessibleAnnouncementEvent(
                self,
                _TEXT[self._language][key],
            )
            event.setPoliteness(
                QAccessible.AnnouncementPoliteness.Assertive
            )
            QAccessible.updateAccessibility(event)
        except (RuntimeError, TypeError):
            return False
        return True

    def apply_projection(
        self,
        theme: str,
        language: str,
        idle_seconds: int,
        ui_font_scale: str,
    ) -> None:
        if (
            theme not in {"LIGHT", "DARK"}
            or language not in _TEXT
            or type(idle_seconds) is not int
            or not 10 <= idle_seconds <= 600
            or ui_font_scale not in UI_FONT_SCALES
        ):
            raise ValueError("invalid QuickBar projection")
        remaining_ms = self._hide_timer.remainingTime()
        language_changed = self._language != language
        self._theme = theme
        self._language = language
        self._idle_seconds = idle_seconds
        self._ui_font_scale = ui_font_scale
        if remaining_ms < 0:
            self._hide_timer.setInterval(idle_seconds * 1000)
        text = _TEXT[language]
        self.setWindowTitle(text["window"])
        self.setAccessibleName(text["window"])
        self.input.setPlaceholderText(text["placeholder"])
        self.input.setAccessibleName(text["search"])
        self.clear_button.setToolTip(text["clear"])
        self.clear_button.setAccessibleName(text["clear"])
        self.drag_area.setToolTip(text["move"])
        self.drag_area.setAccessibleName(text["move"])
        self.drag_grip.setToolTip(text["move"])
        self.shortcut_label.setText(text["footer"])
        for row in self._rows:
            row.set_language(language)
            row.set_ui_font_scale(ui_font_scale)
        displayed_seconds = (
            idle_seconds
            if remaining_ms < 0
            else max(1, (remaining_ms + 999) // 1000)
        )
        self._set_autohide_label(displayed_seconds, force=True)
        dark = theme == "DARK"
        background = "#0f0f18" if dark else "#ffffff"
        deepest = "#090910" if dark else "#f7f5fb"
        text_color = "#f1eff7" if dark else "#24202d"
        secondary = "#a7a2b3" if dark else "#686170"
        weak = "#777184" if dark else "#8b8493"
        border = "#302b40" if dark else "#ded8e8"
        scrollbar = border if dark else "#8b819f"
        scrollbar_hover = border if dark else "#6b6480"
        hover = "#282337" if dark else "#eee9f5"
        accent = "#6366f1" if dark else "#8b5cf6"
        accent_soft = (
            "rgba(99,102,241,0.18)"
            if dark
            else "rgba(139,92,246,0.14)"
        )
        input_padding = 7 if ui_font_scale == "125" else 9
        self.setStyleSheet(
            f"""
            QWidget#m4NativeQuickbarWindow {{ background: transparent; }}
            QFrame#m4NativeQuickbarCard {{
                background: {background}; border: 1px solid {border};
                border-radius: 12px;
            }}
            QFrame#m4QuickbarDragArea {{
                background: transparent; border: 0;
            }}
            QFrame#m4QuickbarDragGrip {{
                background: {border}; border: 0; border-radius: 1px;
            }}
            QFrame#m4QuickbarInputWrap {{
                border: 0; border-bottom: 1px solid {border};
                background: transparent;
            }}
            QFrame#m4QuickbarSearchHalo {{
                background: transparent; border: 0; border-radius: 8px;
            }}
            QFrame#m4QuickbarSearchHalo[focused="true"] {{
                background: {accent_soft};
            }}
            QFrame#m4QuickbarSearchBox {{
                background: {deepest}; border: 1px solid {border};
                border-radius: 5px;
            }}
            QFrame#m4QuickbarSearchHalo[focused="true"]
            QFrame#m4QuickbarSearchBox {{
                border: 1px solid {accent};
            }}
            QLabel#m4QuickbarSearchIcon {{ color: {weak}; font-size: {scaled_font_pixel_size(20, ui_font_scale)}px; }}
            QLineEdit#m4QuickbarInput {{
                color: {text_color}; background: transparent;
                border: 0; padding: {input_padding}px 0; font-size: {scaled_font_pixel_size(14, ui_font_scale)}px;
                selection-background-color: {accent};
            }}
            QPushButton#m4QuickbarClear {{
                color: {secondary}; background: transparent; border: 0;
                border-radius: 5px; font-size: {scaled_font_pixel_size(20, ui_font_scale)}px;
            }}
            QPushButton#m4QuickbarClear:hover {{
                color: {text_color}; background: {hover};
            }}
            QScrollArea#m4QuickbarResults,
            QScrollArea#m4QuickbarResults > QWidget > QWidget {{
                background: {background}; border: 0;
            }}
            QFrame#m4QuickbarResult {{
                background: transparent; border: 0; border-radius: 5px;
            }}
            QFrame#m4QuickbarResult[highlighted="true"] {{ background: {hover}; }}
            QLabel#m4QuickbarName {{ color: {text_color}; font-size: {scaled_font_pixel_size(13, ui_font_scale)}px; font-weight: 600; }}
            QLabel#m4QuickbarAccount {{ color: {secondary}; font-size: {scaled_font_pixel_size(11, ui_font_scale)}px; }}
            QPushButton#m4QuickbarCopy {{
                color: {secondary}; background: transparent;
                border: 1px solid transparent; border-radius: 4px;
                padding: 4px 7px; font-size: {scaled_font_pixel_size(11, ui_font_scale)}px;
            }}
            QPushButton#m4QuickbarCopy:hover {{
                background: {hover}; color: {text_color}; border-color: {border};
            }}
            QPushButton#m4QuickbarCopy[copied="true"] {{
                color: #22c55e; background: rgba(34,197,94,0.18);
                border: 1px solid rgba(34,197,94,0.40);
            }}
            QPushButton#m4QuickbarCommand {{
                text-align: left; color: {accent}; background: {accent_soft};
                border: 1px solid transparent; border-radius: 5px;
                padding: 12px 14px; font-size: {scaled_font_pixel_size(13, ui_font_scale)}px; font-weight: 600;
            }}
            QPushButton[pdmFocusVisualManaged="true"][pdmFocusFrameReady="false"]:focus {{
                border: 2px solid {accent};
            }}
            QLabel#m4QuickbarHint {{ color: {weak}; padding: 12px; font-size: {scaled_font_pixel_size(12, ui_font_scale)}px; }}
            QFrame#m4QuickbarFooter {{
                border: 0; border-top: 1px solid {border}; background: transparent;
            }}
            QLabel#m4QuickbarFooterText {{ color: {weak}; font-size: {scaled_font_pixel_size(10, ui_font_scale)}px; }}
            QScrollBar:vertical {{ background: transparent; width: 6px; margin: 2px; }}
            QScrollBar::handle:vertical {{ background: {scrollbar}; border-radius: 3px; min-height: 24px; }}
            QScrollBar::handle:vertical:hover {{ background: {scrollbar_hover}; }}
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {{ height: 0; }}
            """
        )
        if self._focus_visibility is not None:
            self._focus_visibility.set_effective_theme(theme)
        else:
            self._refresh_focus_targets()
        if self.isVisible() and language_changed:
            self.projection_refresh_requested.emit(self.input.text())

    def open_bar(self) -> None:
        if self._focus_visibility is not None:
            self._focus_visibility.reset()
        self._remember_foreground()
        self._screen_name = self._focus_port.monitor_name_for_window(
            self._return_hwnd
        )
        self._drag_active = False
        self._user_positioned = False
        self.input.clear()
        self._position_on_target_screen()
        self.show()
        self.raise_()
        self.activateWindow()
        self._focus_port.activate_window(self.window_handle())
        QTimer.singleShot(
            0,
            lambda: self.focus_bar(capture_return_target=False),
        )
        self.reset_timer()

    def focus_bar(self, *, capture_return_target: bool = True) -> None:
        if not self.isVisible():
            return
        # The initial OPENING path already captured the pre-QuickBar window.
        # Capturing again on its queued focus pass can race Windows activation
        # and replace that target with another top-level window from this app.
        # A later duplicate hotkey still captures the then-current external
        # window before bringing an already-visible QuickBar back to the front.
        if capture_return_target:
            self._remember_foreground()
        self.raise_()
        self.activateWindow()
        self._focus_port.activate_window(self.window_handle())
        self.input.setFocus(Qt.FocusReason.ShortcutFocusReason)
        self.reset_timer()

    def close_bar(
        self,
        reason: str = "manual",
        *,
        restore_if_owned: bool = True,
    ) -> None:
        if self._focus_visibility is not None:
            self._focus_visibility.reset()
        was_visible = self.isVisible()
        target = self._return_hwnd
        owned = False
        quickbar_hwnd = 0
        if was_visible:
            quickbar_hwnd = self.window_handle()
            current = self._focus_port.foreground_window()
            owned = current == quickbar_hwnd
        restore_target = (
            was_visible
            and restore_if_owned
            and owned
            and target != quickbar_hwnd
            and self._focus_port.is_window(target)
        )
        restored_before_hide = False
        if restore_target:
            # Hand foreground ownership back while QuickBar still owns it.
            # Hiding first lets Windows briefly activate another window from
            # this process (usually the main WebView) before a queued restore,
            # which can visibly flash focus on an unrelated renderer control.
            restored_before_hide = self._focus_port.activate_window(target)
        self._hide_timer.stop()
        self._countdown_timer.stop()
        self._drag_active = False
        self.hide()
        self._set_autohide_label(self._idle_seconds, force=True)
        self.clear_public_state(clear_query=True)
        if restore_target and not restored_before_hide:
            QTimer.singleShot(
                0,
                lambda hwnd=target: self._focus_port.activate_window(hwnd),
            )
        if was_visible:
            self.closed.emit(reason)

    def clear_public_state(self, *, clear_query: bool) -> None:
        self._clear_rows()
        self._command_length = None
        self._command_button = None
        self._index = 0
        if clear_query:
            self.input.blockSignals(True)
            self.input.clear()
            self.input.blockSignals(False)
            self.clear_button.hide()

    def _on_input_text_changed(self, value: str) -> None:
        self.clear_button.setVisible(bool(value))
        self._refresh_focus_targets()
        self.query_changed.emit(value)

    def _clear_search(self) -> None:
        if self.input.text():
            self.input.clear()
            # 立即撤销旧命令和结果动作；随后由防抖后的空查询替换此加载态，
            # 避免快速连按 Enter 重放已经清空的旧动作。
            self.show_loading()
        self.input.setFocus(Qt.FocusReason.OtherFocusReason)

    def reset_timer(self) -> None:
        if self.isVisible():
            self._hide_timer.start(self._idle_seconds * 1000)
            self._refresh_autohide_label(force=True)
            self._countdown_timer.start()

    def _refresh_autohide_label(self, *, force: bool = False) -> None:
        remaining_ms = self._hide_timer.remainingTime()
        seconds = (
            self._idle_seconds
            if remaining_ms < 0
            else max(1, (remaining_ms + 999) // 1000)
        )
        self._set_autohide_label(seconds, force=force)

    def _set_autohide_label(self, seconds: int, *, force: bool = False) -> None:
        if not force and self._last_autohide_seconds == seconds:
            return
        self._last_autohide_seconds = seconds
        self.autohide_label.setText(
            _TEXT[self._language]["autohide"].format(seconds=seconds)
        )

    def show_loading(self) -> None:
        self._command_length = None
        self._command_button = None
        self._show_hint(_TEXT[self._language]["loading"])

    def show_error(self) -> None:
        self._command_length = None
        self._command_button = None
        self._show_hint(_TEXT[self._language]["failed"])

    def show_query_error(self, error_key: str) -> None:
        self._command_length = None
        self._command_button = None
        self._show_hint(_TEXT[self._language][error_key])

    def show_search_results(
        self,
        summaries: list[QuickbarSummary],
        *,
        had_query: bool,
        total: int | None = None,
    ) -> None:
        total = len(summaries) if total is None else total
        self._clear_rows()
        self._command_length = None
        self._command_button = None
        self._summaries = list(summaries)
        self._index = 0
        if not summaries:
            key = "not_found" if had_query else "empty"
            self._show_hint(_TEXT[self._language][key], already_cleared=True)
            return
        for index, summary in enumerate(summaries):
            row = _ResultRow(
                summary,
                index,
                self._language,
                self._ui_font_scale,
                self.result_host,
            )
            row.action_requested.connect(self.row_action_requested)
            row.set_highlighted(index == 0)
            self._watch_activity(row)
            self._rows.append(row)
            self.result_layout.addWidget(row)
        if total > len(summaries):
            hint = QLabel(
                _TEXT[self._language]["more_results"].format(total=total),
                self.result_host,
            )
            hint.setObjectName("m4QuickbarHint")
            hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
            hint.setWordWrap(True)
            self._watch_activity(hint)
            self.result_layout.addWidget(hint)
        self._set_result_height(
            len(self._rows) * 54 + (64 if total > len(summaries) else 12)
        )
        self._refresh_focus_targets()

    def show_generate_command(self, length: int) -> None:
        self._clear_rows()
        self._command_length = length
        text = _TEXT[self._language]
        button = QPushButton(
            text["generate"].format(length=length),
            self.result_host,
        )
        button.setObjectName("m4QuickbarCommand")
        button.setProperty("pdmFocusVisualManaged", True)
        button.setProperty("pdmFocusFrameReady", False)
        button.setProperty("pdmFocusRadius", 5)
        button.clicked.connect(lambda: self.generate_requested.emit(length))
        self._command_button = button
        self._watch_activity(button)
        self.result_layout.addWidget(button)
        hint = QLabel(text["generate_hint"], self.result_host)
        hint.setObjectName("m4QuickbarHint")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setWordWrap(True)
        self._generate_hint = hint
        self.result_layout.addWidget(hint)
        self._set_result_height(104)
        self._refresh_focus_targets()

    def set_generate_pending(self, pending: bool) -> None:
        if self._command_button is not None:
            self._command_button.setEnabled(not pending)

    def show_generate_feedback(self) -> None:
        if self._generate_hint is None:
            return
        self._generate_feedback_token += 1
        token = self._generate_feedback_token
        self._generate_hint.setText(_TEXT[self._language]["generate_copied"])
        QTimer.singleShot(
            2_000,
            lambda: self._restore_generate_hint(token),
        )

    def show_generate_error(self) -> None:
        if self._generate_hint is not None:
            self._generate_hint.setText(_TEXT[self._language]["failed"])

    def show_generate_range_error(self) -> None:
        self._command_length = None
        self._command_button = None
        self._show_hint(_TEXT[self._language]["generate_range"])

    def _restore_generate_hint(self, token: int) -> None:
        if (
            token == self._generate_feedback_token
            and self._generate_hint is not None
        ):
            self._generate_hint.setText(_TEXT[self._language]["generate_hint"])

    def event(self, event: QEvent) -> bool:
        if event.type() == QEvent.Type.WindowDeactivate and self.isVisible():
            self._drag_active = False
            QTimer.singleShot(0, self._remember_foreground)
        return super().event(event)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        event_type = event.type()
        if (
            watched in {self.search_box, self.search_icon, self.clear_slot}
            and event_type == QEvent.Type.MouseButtonPress
            and event.button() == Qt.MouseButton.LeftButton
        ):
            self.input.setFocus(Qt.FocusReason.MouseFocusReason)
            self.reset_timer()
        if watched is self.input and event_type in {
            QEvent.Type.FocusIn,
            QEvent.Type.FocusOut,
        }:
            self.search_halo.setProperty(
                "focused",
                event_type == QEvent.Type.FocusIn,
            )
            self.search_halo.style().unpolish(self.search_halo)
            self.search_halo.style().polish(self.search_halo)
            self.search_halo.update()
        if watched is self.drag_area or watched is self.drag_grip:
            if (
                event_type == QEvent.Type.MouseButtonPress
                and event.button() == Qt.MouseButton.LeftButton
            ):
                self._drag_active = True
                self._drag_offset = (
                    event.globalPosition().toPoint()
                    - self.frameGeometry().topLeft()
                )
                self._user_positioned = True
                self.reset_timer()
                event.accept()
                return True
            if event_type == QEvent.Type.MouseMove and self._drag_active:
                if event.buttons() & Qt.MouseButton.LeftButton:
                    self._move_constrained(
                        event.globalPosition().toPoint() - self._drag_offset
                    )
                    self.reset_timer()
                    event.accept()
                    return True
                self._drag_active = False
            if (
                event_type == QEvent.Type.MouseButtonRelease
                and event.button() == Qt.MouseButton.LeftButton
            ):
                if self._drag_active:
                    self._move_constrained(
                        event.globalPosition().toPoint() - self._drag_offset
                    )
                self._drag_active = False
                self.reset_timer()
                event.accept()
                return True
        if event_type == QEvent.Type.KeyPress:
            if NativeFocusVisibilityController._is_composing_key(event):
                self.reset_timer()
                return super().eventFilter(watched, event)
            key = event.key()
            if key == Qt.Key.Key_Escape:
                self.close_bar("manual", restore_if_owned=True)
                return True
            self.reset_timer()
            if (
                watched is self.clear_button
                and key in {Qt.Key.Key_Return, Qt.Key.Key_Enter}
            ):
                self._clear_search()
                return True
            if watched is self.input:
                if key in {Qt.Key.Key_Up, Qt.Key.Key_Down}:
                    self._move(-1 if key == Qt.Key.Key_Up else 1)
                    return True
                if key in {Qt.Key.Key_Return, Qt.Key.Key_Enter}:
                    if self._command_length is not None:
                        self.generate_requested.emit(self._command_length)
                    else:
                        self._activate(
                            bool(
                                event.modifiers()
                                & Qt.KeyboardModifier.ControlModifier
                            )
                        )
                    return True
        if event_type in {
            QEvent.Type.MouseButtonPress,
            QEvent.Type.MouseMove,
            QEvent.Type.Wheel,
        }:
            self.reset_timer()
        return super().eventFilter(watched, event)

    def focusNextPrevChild(self, next: bool) -> bool:  # noqa: A002, N802
        if self._focus_visibility is None:
            return super().focusNextPrevChild(next)
        return self._focus_visibility.focus_next(backwards=not next)

    def closeEvent(self, event) -> None:  # noqa: N802
        event.ignore()
        self.close_bar("manual", restore_if_owned=True)

    def _focus_targets(self) -> list[QWidget]:
        targets: list[QWidget] = [self.input, self.clear_button]
        for row in self._rows:
            targets.extend([row.account_button, row.password_button])
        if self._command_button is not None:
            targets.append(self._command_button)
        return [
            target
            for target in targets
            if target.isVisible()
            and target.isEnabled()
            and target.focusPolicy() != Qt.FocusPolicy.NoFocus
        ]

    def _refresh_focus_targets(self) -> None:
        controller = getattr(self, "_focus_visibility", None)
        if controller is not None:
            controller.refresh()
            return
        for target in self._focus_targets():
            if isinstance(target, QLineEdit) or bool(
                target.property("pdmFocusFallbackInstalled")
            ):
                continue
            try:
                install_managed_focus_fallback(
                    target,
                    radius=int(target.property("pdmFocusRadius") or 0),
                )
            except (RuntimeError, TypeError, ValueError):
                continue
            target.setProperty("pdmFocusFallbackInstalled", True)

    def _watch_activity(self, widget: QWidget) -> None:
        widget.installEventFilter(self)
        widget.setMouseTracking(True)
        for child in widget.findChildren(QWidget):
            child.installEventFilter(self)
            child.setMouseTracking(True)

    def _activate(self, account: bool) -> None:
        if not self._summaries or not 0 <= self._index < len(self._rows):
            return
        summary = self._summaries[self._index]
        row = self._rows[self._index]
        source = row.account_button if account else row.password_button
        self.row_action_requested.emit(
            "account" if account else "password",
            summary.record_id,
            summary.revision,
            source,
        )

    def _move(self, delta: int) -> None:
        if not self._summaries:
            return
        self._index = max(
            0,
            min(len(self._summaries) - 1, self._index + delta),
        )
        for index, row in enumerate(self._rows):
            row.set_highlighted(index == self._index)
        self.scroll.ensureWidgetVisible(self._rows[self._index], 0, 8)
        self.reset_timer()

    def _show_hint(self, value: str, *, already_cleared: bool = False) -> None:
        if not already_cleared:
            self._clear_rows()
        hint = QLabel(value, self.result_host)
        hint.setObjectName("m4QuickbarHint")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setWordWrap(True)
        self._watch_activity(hint)
        self.result_layout.addWidget(hint)
        self._set_result_height(64)

    def _set_result_height(self, height: int) -> None:
        self.scroll.setFixedHeight(min(360, max(64, height)))
        self.card.adjustSize()
        self.adjustSize()
        if self.isVisible():
            if self._user_positioned:
                self._move_constrained(self.pos())
            else:
                self._position_on_target_screen()

    def _clear_rows(self) -> None:
        self._generate_feedback_token += 1
        self._generate_hint = None
        while self.result_layout.count():
            item = self.result_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.hide()
                widget.setParent(None)
                widget.deleteLater()
        self._rows = []
        self._summaries = []
        self._command_button = None
        self._refresh_focus_targets()

    def _remember_foreground(self) -> None:
        candidate = self._focus_port.foreground_window()
        if (
            candidate > 0
            and candidate != self.window_handle()
            and self._focus_port.is_window(candidate)
        ):
            self._return_hwnd = candidate

    def _position_on_target_screen(self) -> None:
        application = QApplication.instance()
        if application is None:
            return
        screens = application.screens()
        screen = None
        wanted = self._normalized_screen_name(self._screen_name)
        if wanted:
            for candidate in screens:
                if self._normalized_screen_name(candidate.name()) == wanted:
                    screen = candidate
                    break
        if screen is None:
            screen = application.screenAt(QCursor.pos())
        if screen is None:
            screen = application.primaryScreen()
        if screen is None:
            return
        available = screen.availableGeometry()
        self.card.setFixedWidth(max(320, min(480, available.width() - 32)))
        self.card.adjustSize()
        self.adjustSize()
        size = self.sizeHint()
        x = available.x() + max(0, (available.width() - size.width()) // 2)
        y = available.y() + min(
            120,
            max(16, available.height() - size.height()),
        )
        self._move_within_available(QPoint(x, y), available)

    def _move_constrained(self, top_left: QPoint) -> None:
        application = QApplication.instance()
        if application is None:
            return
        center = top_left + QPoint(self.width() // 2, self.height() // 2)
        screen = application.screenAt(center)
        if screen is None:
            screen = application.screenAt(QCursor.pos())
        if screen is None:
            wanted = self._normalized_screen_name(self._screen_name)
            screen = next(
                (
                    candidate
                    for candidate in application.screens()
                    if self._normalized_screen_name(candidate.name()) == wanted
                ),
                None,
            )
        if screen is None:
            screen = application.primaryScreen()
        if screen is None:
            return
        self._screen_name = screen.name()
        self._move_within_available(top_left, screen.availableGeometry())

    def _move_within_available(self, top_left: QPoint, available) -> None:
        maximum_x = max(available.x(), available.right() - self.width() + 1)
        maximum_y = max(available.y(), available.bottom() - self.height() + 1)
        self.move(
            max(available.x(), min(top_left.x(), maximum_x)),
            max(available.y(), min(top_left.y(), maximum_y)),
        )

    def window_handle(self) -> int:
        try:
            return int(self.winId())
        except (RuntimeError, TypeError, ValueError):
            return 0

    @staticmethod
    def _normalized_screen_name(value: str) -> str:
        return str(value or "").replace("\\\\.\\", "").casefold()


class NativeQuickbarController(QObject):
    """Bind one independent native widget to N01-N04."""

    adapter_completion_ready = Signal(object)

    def __init__(
        self,
        catalog: ContractCatalog,
        adapter: BridgeAdapter,
        parent: QObject | None = None,
        *,
        focus_port: QuickbarFocusPort | None = None,
    ) -> None:
        super().__init__(parent)
        self.widget = NativeQuickbarWidget(focus_port)
        self.destroyed.connect(self.widget.deleteLater)
        self._session_epoch = 0
        self._enabled = False
        self._registration = "DISABLED"
        self._search_in_flight = False
        self._generate_in_flight = False
        self._display_epoch = 0
        self._queued_query: str | None = None
        self._last_intent_at = 0.0
        self._contexts: dict[str, tuple[str, object, int]] = {}
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(90)
        self._search_timer.timeout.connect(self._submit_queued_search)
        self._port = NativeQuickbarPort(
            catalog,
            _PassiveQuickbarAdapter(adapter),
            self._on_envelope,
            adapter_completion_receiver=self.adapter_completion_ready.emit,
        )
        self.adapter_completion_ready.connect(
            self._forward_adapter_completion,
            Qt.ConnectionType.QueuedConnection,
        )
        self.widget.query_changed.connect(self._on_query_changed)
        self.widget.projection_refresh_requested.connect(
            self._on_projection_refresh_requested
        )
        self.widget.row_action_requested.connect(self._copy)
        self.widget.generate_requested.connect(self._generate)
        self.widget.closed.connect(self._on_widget_closed)

    @property
    def visible(self) -> bool:
        return self.widget.isVisible()

    def apply_settings(
        self,
        *,
        enabled: bool,
        registration: str,
        idle_seconds: int,
        effective_theme: str,
        language: str,
        ui_font_scale: str,
    ) -> None:
        was_visible = self.widget.isVisible()
        idle_changed = self.widget.idle_seconds != idle_seconds
        self._enabled = enabled
        self._registration = registration
        self.widget.apply_projection(
            effective_theme,
            language,
            idle_seconds,
            ui_font_scale,
        )
        if not enabled:
            self.widget.close_bar("policy", restore_if_owned=False)
        elif was_visible and idle_changed:
            self.widget.reset_timer()

    def set_session_epoch(self, session_epoch: int) -> None:
        if type(session_epoch) is not int or session_epoch <= 0:
            raise ValueError("QuickBar requires a positive session epoch")
        if self._session_epoch:
            self.invalidate_session("session_invalidated")
        self._port.set_session_epoch(session_epoch)
        self._session_epoch = session_epoch

    def open_for_current_session(
        self,
        *,
        require_registration: bool,
    ) -> bool:
        if (
            self._session_epoch <= 0
            or not self._enabled
            or (
                require_registration
                and self._registration != "REGISTERED"
            )
        ):
            return False
        now = time.monotonic()
        duplicate = now - self._last_intent_at < 0.15
        self._last_intent_at = now
        if self.widget.isVisible():
            if duplicate:
                self.widget.focus_bar()
            else:
                self.widget.close_bar("manual", restore_if_owned=True)
            return True
        self._display_epoch += 1
        self.widget.open_bar()
        self._on_query_changed("")
        return True

    def invalidate_session(self, reason: str = "session_invalidated") -> None:
        self._search_timer.stop()
        self._queued_query = None
        self._search_in_flight = False
        self._generate_in_flight = False
        self._last_intent_at = 0.0
        self._contexts.clear()
        self.widget.close_bar("security", restore_if_owned=False)
        if self._session_epoch > 0:
            self._port.invalidate_session(
                reason
                if reason in {
                    "auto_lock",
                    "change_key_failed",
                    "change_key_restored",
                    "change_key_success",
                    "manual_lock",
                    "session_invalidated",
                    "suspend_lock",
                    "switch_database",
                }
                else "session_invalidated"
            )
        self._session_epoch = 0

    def close(self) -> None:
        self.invalidate_session("session_invalidated")
        self._port.close("bridge_close")

    @Slot(object)
    def _forward_adapter_completion(self, completion: object) -> None:
        self._port.receive_adapter_completion(completion)

    def _on_query_changed(self, query: str) -> None:
        self._queue_query(query, reset_activity=True)

    def _on_projection_refresh_requested(self, query: str) -> None:
        self._queue_query(query, reset_activity=False)

    def _queue_query(self, query: str, *, reset_activity: bool) -> None:
        if not self.widget.isVisible() or self._session_epoch <= 0:
            return
        if reset_activity:
            self.widget.reset_timer()
        length, command_shaped = _parse_generator_command(query)
        if command_shaped:
            self._queued_query = None
            self._search_timer.stop()
            if length is None or not (
                _GENERATOR_MIN_LENGTH
                <= length
                <= _GENERATOR_MAX_LENGTH
            ):
                self.widget.show_generate_range_error()
            else:
                self.widget.show_generate_command(length)
            return
        error_key = _query_limit_error(query)
        if error_key is not None:
            self._queued_query = None
            self._search_timer.stop()
            self.widget.show_query_error(error_key)
            return
        self._queued_query = query
        if self._search_in_flight:
            self.widget.show_loading()
            return
        self._search_timer.start()

    def _submit_queued_search(self) -> None:
        query = self._queued_query
        if (
            query is None
            or self._search_in_flight
            or self._session_epoch <= 0
            or not self.widget.isVisible()
        ):
            return
        self._queued_query = None
        request_id = str(uuid.uuid4())
        ack = self._port.quickbarSearchV1(
            request_id,
            self._session_epoch,
            query,
            20,
        )
        if ack.get("accepted") is not True:
            self.widget.show_error()
            return
        self._search_in_flight = True
        self._contexts[request_id] = ("search", query, self._display_epoch)
        self.widget.show_loading()

    def _copy(
        self,
        action: str,
        record_id: int,
        revision: str,
        source: object,
    ) -> None:
        if self._session_epoch <= 0 or action not in {"account", "password"}:
            return
        request_id = str(uuid.uuid4())
        method = (
            self._port.quickbarCopyAccountV1
            if action == "account"
            else self._port.quickbarCopyPasswordV1
        )
        ack = method(
            request_id,
            self._session_epoch,
            record_id,
            revision,
        )
        if ack.get("accepted") is not True:
            row = self._result_row(source)
            error_code = ack.get("errorCode")
            if row is not None and error_code == "EMPTY_FIELD":
                key = f"{action}_empty"
                row.flash_message(key)
            elif row is not None and error_code in _COPY_FEEDBACK_KEYS:
                key = _COPY_FEEDBACK_KEYS[error_code]
                row.flash_message(key)
            else:
                key = "failed"
                self.widget.show_error()
            self.widget.announce_accessible_result(key)
            return
        self._contexts[request_id] = (
            "copy",
            (source, action, self.widget.input.text()),
            self._display_epoch,
        )
        self.widget.reset_timer()

    def _generate(self, length: int) -> None:
        if (
            self._session_epoch <= 0
            or self._generate_in_flight
        ):
            return
        if type(length) is not int or not (
            _GENERATOR_MIN_LENGTH <= length <= _GENERATOR_MAX_LENGTH
        ):
            self.widget.show_generate_range_error()
            return
        request_id = str(uuid.uuid4())
        ack = self._port.quickbarGenerateAndCopyV1(
            request_id,
            self._session_epoch,
            length,
        )
        if ack.get("accepted") is not True:
            self.widget.show_generate_error()
            self.widget.announce_accessible_result("failed")
            return
        self._generate_in_flight = True
        self._contexts[request_id] = (
            "generate",
            (length, self.widget.input.text()),
            self._display_epoch,
        )
        self.widget.set_generate_pending(True)
        self.widget.reset_timer()

    def _on_envelope(self, envelope: CompletionEnvelope) -> None:
        context = self._contexts.pop(envelope.request_id, None)
        if context is None:
            self._port.mark_envelope_delivered(envelope)
            return
        action, payload, display_epoch = context
        if action == "search":
            self._search_in_flight = False
        elif action == "generate":
            self._generate_in_flight = False
        if (
            envelope.session_epoch != self._session_epoch
            or self._session_epoch <= 0
        ):
            self._port.mark_envelope_delivered(envelope)
            return
        display_is_current = display_epoch == self._display_epoch
        refresh_after_copy = False
        search_still_current = bool(
            action == "search"
            and display_is_current
            and self.widget.isVisible()
            and self.widget.input.text() == payload
            and self._queued_query is None
        )
        if action == "generate":
            _length, input_value = payload
            if (
                display_is_current
                and self.widget.isVisible()
                and self.widget.input.text() == input_value
            ):
                self.widget.set_generate_pending(False)
                if envelope.error_code == "OK" and isinstance(
                    envelope.result,
                    dict,
                ):
                    self.widget.show_generate_feedback()
                    self.widget.announce_accessible_result(
                        "generated_password_copied"
                    )
                    self.widget.input.setFocus(
                        Qt.FocusReason.OtherFocusReason
                    )
                    self.widget.reset_timer()
                else:
                    self.widget.show_generate_error()
                    self.widget.announce_accessible_result("failed")
        elif action == "copy":
            source, field, input_value = payload
            copy_is_current = bool(
                display_is_current
                and self.widget.isVisible()
                and self.widget.input.text() == input_value
            )
            row = self._result_row(source) if copy_is_current else None
            if row not in self.widget._rows:
                row = None
            if copy_is_current and row is not None:
                if envelope.error_code == "OK" and isinstance(
                    envelope.result,
                    dict,
                ):
                    row.flash_copied(source)
                    key = f"{field}_copied"
                elif envelope.error_code == "EMPTY_FIELD":
                    key = f"{field}_empty"
                    row.flash_message(key)
                elif envelope.error_code in _COPY_FEEDBACK_KEYS:
                    key = _COPY_FEEDBACK_KEYS[envelope.error_code]
                    row.flash_message(key)
                elif envelope.error_code in {
                    "NOT_FOUND",
                    "REVISION_CONFLICT",
                }:
                    key = "failed"
                    refresh_after_copy = True
                else:
                    key = "failed"
                    self.widget.show_error()
                self.widget.announce_accessible_result(key)
                self.widget.reset_timer()
        elif envelope.error_code != "OK" or not isinstance(envelope.result, dict):
            if display_is_current and self.widget.isVisible() and (
                action != "search" or search_still_current
            ):
                self.widget.show_error()
        elif action == "search":
            parsed = self._parse_summaries(envelope.result)
            if parsed is None:
                if search_still_current:
                    self.widget.show_error()
            elif search_still_current:
                summaries, total = parsed
                self.widget.show_search_results(
                    summaries,
                    had_query=bool(str(payload).strip()),
                    total=total,
                )
        self._port.mark_envelope_delivered(envelope)
        if refresh_after_copy:
            self._queue_query(self.widget.input.text(), reset_activity=False)
            self._search_timer.stop()
            self._submit_queued_search()
        if action == "search" and self._queued_query is not None:
            self._search_timer.start()

    @staticmethod
    def _result_row(source: object) -> _ResultRow | None:
        if not isinstance(source, QPushButton):
            return None
        try:
            candidate = source.parentWidget()
        except RuntimeError:
            return None
        return candidate if isinstance(candidate, _ResultRow) else None

    @staticmethod
    def _parse_summaries(
        result: dict[str, object],
    ) -> tuple[list[QuickbarSummary], int] | None:
        items = result.get("items")
        total = result.get("total")
        if not isinstance(items, list) or type(total) is not int or total < len(items):
            return None
        summaries: list[QuickbarSummary] = []
        for item in items:
            if not isinstance(item, dict):
                return None
            record_id = item.get("recordId")
            revision = item.get("revision")
            platform = item.get("platform")
            account = item.get("accountDisplay")
            favorite = item.get("favorite")
            has_totp = item.get("hasTotp")
            if (
                type(record_id) is not int
                or record_id <= 0
                or type(revision) is not str
                or type(platform) is not str
                or type(account) is not str
                or type(favorite) is not bool
                or type(has_totp) is not bool
            ):
                return None
            summaries.append(
                QuickbarSummary(
                    record_id,
                    revision,
                    platform,
                    account,
                    favorite,
                    has_totp,
                )
            )
        return summaries, total

    def _on_widget_closed(self, _reason: str) -> None:
        self._queued_query = None
        self._search_timer.stop()


__all__ = [
    "NativeQuickbarController",
    "NativeQuickbarWidget",
    "QuickbarFocusPort",
    "QuickbarSummary",
]
