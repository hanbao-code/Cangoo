"""仅由独立编辑窗口持有的小型原生确认表面。"""

from __future__ import annotations

from enum import Enum

from PySide6.QtCore import QTimer, QSize, Qt, Signal
from PySide6.QtGui import QColor, QCloseEvent, QFont, QKeyEvent, QPainter
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from desktop.host.focus_visibility import (
    NativeFocusVisibilityController,
    install_managed_focus_fallback,
)
from desktop.ui_font_scale import normalize_ui_font_scale, scaled_font_pixel_size


class EditorConfirmationKind(str, Enum):
    """编辑窗口的固定破坏性或替换性选择。"""

    DISCARD = "DISCARD"
    RELOAD = "RELOAD"
    DELETE_NOTE = "DELETE_NOTE"
    REPLACE_RECOVERY = "REPLACE_RECOVERY"
    CLEAR_RECOVERY = "CLEAR_RECOVERY"


_COPY = {
    "ZH": {
        "DISCARD": ("放弃修改？", "关闭后未保存的修改将被丢弃。", "放弃修改", "继续编辑"),
        "RELOAD": ("加载最新内容？", "当前草稿将被最新内容替换。", "加载最新内容", "继续编辑"),
        "DELETE_NOTE": ("删除记事？", "确定删除“{entity}”？删除后无法恢复。", "删除", "取消"),
        "REPLACE_RECOVERY": ("替换整组恢复码？", "保存后将替换全部现有恢复码，并重置本地使用标记。", "替换并保存", "继续编辑"),
        "CLEAR_RECOVERY": ("移除整组恢复码？", "保存后将移除此账号保存的全部恢复码及使用标记。", "移除并保存", "继续编辑"),
    },
    "EN": {
        "DISCARD": ("Discard changes?", "Unsaved changes will be lost.", "Discard", "Keep editing"),
        "RELOAD": ("Load latest version?", "Your current draft will be replaced.", "Load latest", "Keep editing"),
        "DELETE_NOTE": ("Delete note?", "Delete “{entity}”? This cannot be undone.", "Delete", "Cancel"),
        "REPLACE_RECOVERY": ("Replace recovery codes?", "Saving will replace all stored recovery codes and reset local usage marks.", "Replace and save", "Keep editing"),
        "CLEAR_RECOVERY": ("Remove recovery codes?", "Saving will remove all recovery codes and usage marks stored for this account.", "Remove and save", "Keep editing"),
    },
}


class _ConfirmationSymbol(QWidget):
    """确认卡片内部的固定警告或信息图标。"""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setObjectName("pdmEditorConfirmationIcon")
        self.setFixedSize(20, 20)
        self._kind = EditorConfirmationKind.DISCARD
        self._theme = "DARK"

    def set_projection(
        self,
        kind: EditorConfirmationKind,
        theme: str,
        language: str,
    ) -> None:
        self._kind = kind
        self._theme = theme
        self.setProperty("pdmConfirmationIconKind", kind.value)
        self.setProperty("pdmConfirmationIconTheme", theme)
        destructive = kind in {
            EditorConfirmationKind.DISCARD,
            EditorConfirmationKind.DELETE_NOTE,
            EditorConfirmationKind.REPLACE_RECOVERY,
            EditorConfirmationKind.CLEAR_RECOVERY,
        }
        self.setAccessibleName(
            "警告" if language == "ZH" and destructive
            else "信息" if language == "ZH" else "Warning" if destructive else "Information"
        )
        self.update()

    def sizeHint(self) -> QSize:  # noqa: N802
        return QSize(20, 20)

    def paintEvent(self, _event) -> None:  # noqa: N802
        dark = self._theme == "DARK"
        if self._kind in {
            EditorConfirmationKind.DISCARD,
            EditorConfirmationKind.DELETE_NOTE,
            EditorConfirmationKind.REPLACE_RECOVERY,
            EditorConfirmationKind.CLEAR_RECOVERY,
        }:
            color = "#fbbf24" if dark else "#b45309"
        else:
            color = "#818cf8" if dark else "#7c3aed"
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(color))
        painter.drawEllipse(self.rect().adjusted(1, 1, -1, -1))
        font = QFont(self.font())
        font.setPixelSize(13)
        font.setWeight(QFont.Weight.Bold)
        painter.setFont(font)
        painter.setPen(QColor("#ffffff"))
        painter.drawText(
            self.rect(),
            Qt.AlignmentFlag.AlignCenter,
            "!" if self._kind in {
                EditorConfirmationKind.DISCARD,
                EditorConfirmationKind.DELETE_NOTE,
            EditorConfirmationKind.REPLACE_RECOVERY,
            EditorConfirmationKind.CLEAR_RECOVERY,
            } else "i",
        )
        painter.end()


class EditorConfirmationDialog(QDialog):
    """带可作废回调 token（令牌）的非阻塞编辑确认框。"""

    confirmed = Signal(str, str)
    cancelled = Signal(str, str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("pdmEditorConfirmation")
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.FramelessWindowHint
        )
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.setModal(True)
        self.setSizeGripEnabled(False)
        self.setMinimumWidth(360)
        self.setMaximumWidth(460)
        self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        self._serial = 0
        self._active_token = ""
        self._active_kind: EditorConfirmationKind | None = None
        self._entity_label = ""
        self._focus_visibility: NativeFocusVisibilityController | None = None
        self._fallback_installed = False

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 18)
        root.setSpacing(10)
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(8)
        self.symbol = _ConfirmationSymbol(self)
        self.title_label = QLabel(self)
        self.title_label.setObjectName("pdmEditorConfirmationTitle")
        self.close_button = QToolButton(self)
        self.close_button.setObjectName("pdmEditorConfirmationClose")
        self.close_button.setText("×")
        self.close_button.setFixedSize(28, 28)
        self.close_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        header.addWidget(self.symbol)
        header.addWidget(self.title_label, 1)
        header.addWidget(self.close_button)
        self.message_label = QLabel(self)
        self.message_label.setTextFormat(Qt.TextFormat.PlainText)
        self.message_label.setObjectName("pdmEditorConfirmationMessage")
        self.message_label.setWordWrap(True)
        root.addLayout(header)
        root.addWidget(self.message_label)
        actions = QHBoxLayout()
        actions.setContentsMargins(0, 8, 0, 0)
        actions.addStretch(1)
        self.cancel_button = QPushButton(self)
        self.cancel_button.setObjectName("pdmEditorConfirmationCancel")
        self.confirm_button = QPushButton(self)
        self.confirm_button.setObjectName("pdmEditorConfirmationConfirm")
        actions.addWidget(self.cancel_button)
        actions.addWidget(self.confirm_button)
        root.addLayout(actions)
        self.cancel_button.clicked.connect(self.reject)
        self.confirm_button.clicked.connect(self.accept)
        self.close_button.clicked.connect(self.reject)

    @property
    def active_token(self) -> str:
        return self._active_token

    def present(
        self,
        kind: EditorConfirmationKind,
        *,
        language: str,
        effective_theme: str,
        ui_font_scale: str,
        entity_label: str = "",
    ) -> str:
        """打开一个窗口模态确认框，不创建嵌套 Qt 事件循环。"""

        if not isinstance(kind, EditorConfirmationKind):
            raise ValueError("invalid editor confirmation kind")
        self._validate_projection(language, effective_theme, ui_font_scale)
        self.revoke_silently()
        self._serial += 1
        token = str(self._serial)
        self._active_token = token
        self._active_kind = kind
        self._entity_label = self._validate_entity_label(kind, entity_label)
        self.apply_projection(language, effective_theme, ui_font_scale)
        self.cancel_button.setAutoDefault(True)
        self.cancel_button.setDefault(True)
        self.confirm_button.setAutoDefault(False)
        self.confirm_button.setDefault(False)
        self.open()
        QTimer.singleShot(0, self._focus_cancel_safely)
        return token

    def apply_projection(
        self,
        language: str,
        effective_theme: str,
        ui_font_scale: str,
    ) -> None:
        """原地投影当前设置，不重开或改变已发出的确认动作。"""

        self._validate_projection(language, effective_theme, ui_font_scale)
        kind = self._active_kind
        if not self._active_token or kind is None:
            return
        title, message, confirm, cancel = _COPY[language][kind.value]
        message = message.replace("{entity}", self._entity_label)
        self.setWindowTitle(title)
        self.setAccessibleName(title)
        self.title_label.setText(title)
        self.message_label.setText(message)
        self.confirm_button.setText(confirm)
        self.cancel_button.setText(cancel)
        self.confirm_button.setAccessibleName(confirm)
        self.cancel_button.setAccessibleName(cancel)
        self.close_button.setAccessibleName("关闭" if language == "ZH" else "Close")
        self.close_button.setToolTip("关闭" if language == "ZH" else "Close")
        self.symbol.set_projection(kind, effective_theme, language)
        self._apply_projection(effective_theme, ui_font_scale)

    def revoke_silently(self) -> None:
        """安全清理隐藏前，使尚未完成的选择失效且不回调。"""

        self._active_token = ""
        self._active_kind = None
        self._entity_label = ""
        self.hide()

    def accept(self) -> None:  # noqa: N802
        self._finish(True)

    def reject(self) -> None:  # noqa: N802
        self._finish(False)

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        event.ignore()
        self.reject()

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802
        if (
            event.key() == Qt.Key.Key_F4
            and event.modifiers() & Qt.KeyboardModifier.AltModifier
        ):
            event.accept()
            self.reject()
            return
        super().keyPressEvent(event)

    def _finish(self, confirmed: bool) -> None:
        token, kind = self._active_token, self._active_kind
        if not token or kind is None:
            return
        self._active_token = ""
        self._active_kind = None
        self._entity_label = ""
        self.hide()
        if confirmed:
            self.confirmed.emit(token, kind.value)
        else:
            self.cancelled.emit(token, kind.value)

    def _apply_projection(self, theme: str, scale: str) -> None:
        dark = theme == "DARK"
        foreground = "#e2e4f0" if dark else "#2d2640"
        muted = "#a5a7ba" if dark else "#6b6480"
        surface = "#151625" if dark else "#f7f3fb"
        border = "#33354d" if dark else "#d8d0e6"
        accent = (
            "#ef4444" if dark else "#dc2626"
        ) if self._active_kind is EditorConfirmationKind.DELETE_NOTE else (
            "#6366f1" if dark else "#8b5cf6"
        )
        self.setStyleSheet(
            "QDialog#pdmEditorConfirmation{"
            f"background:{surface};color:{foreground};"
            f"border:1px solid {border};border-radius:10px;}}"
            f"QLabel#pdmEditorConfirmationTitle{{color:{foreground};font-weight:600;}}"
            f"QLabel#pdmEditorConfirmationMessage{{color:{muted};}}"
            f"QToolButton#pdmEditorConfirmationClose{{background:transparent;color:{muted};border:0;border-radius:6px;font-size:20px;}}"
            f"QToolButton#pdmEditorConfirmationClose:hover{{background:{border};color:{foreground};}}"
            "QPushButton{min-height:32px;padding:0 14px;border-radius:6px;}"
            f"QPushButton#pdmEditorConfirmationCancel{{background:transparent;color:{foreground};border:1px solid {border};}}"
            f"QPushButton#pdmEditorConfirmationConfirm{{background:{accent};color:white;border:1px solid {accent};}}"
        )
        title_font = QFont(self.font())
        title_font.setPixelSize(scaled_font_pixel_size(15, scale))
        title_font.setWeight(QFont.Weight.DemiBold)
        self.title_label.setFont(title_font)
        body_font = QFont(self.font())
        body_font.setPixelSize(scaled_font_pixel_size(12, scale))
        self.message_label.setFont(body_font)
        for button in (self.cancel_button, self.confirm_button):
            button.setFont(body_font)
        if self._focus_visibility is None:
            try:
                self._focus_visibility = NativeFocusVisibilityController(
                    self,
                    lambda: (self.cancel_button, self.confirm_button),
                    effective_theme=theme,
                    safe_anchor=self,
                    default_action=self.reject,
                    parent=self,
                )
            except Exception:
                self._focus_visibility = None
                if not self._fallback_installed:
                    for button in (self.cancel_button, self.confirm_button):
                        install_managed_focus_fallback(button, radius=6)
                    self._fallback_installed = True
        elif self._focus_visibility.ready:
            self._focus_visibility.set_effective_theme(theme)

    def _focus_cancel_safely(self) -> None:
        if not self._active_token or not self.isVisible():
            return
        if self._focus_visibility is not None and self._focus_visibility.ready:
            self._focus_visibility.focus_safe_anchor(
                Qt.FocusReason.OtherFocusReason
            )
        self.cancel_button.setFocus(Qt.FocusReason.OtherFocusReason)

    @staticmethod
    def _validate_projection(
        language: str,
        effective_theme: str,
        ui_font_scale: str,
    ) -> None:
        if language not in _COPY:
            raise ValueError("language must be ZH or EN")
        if effective_theme not in {"LIGHT", "DARK"}:
            raise ValueError("effective theme must be LIGHT or DARK")
        if normalize_ui_font_scale(ui_font_scale) != ui_font_scale:
            raise ValueError("invalid UI font scale")

    @staticmethod
    def _validate_entity_label(
        kind: EditorConfirmationKind,
        value: str,
    ) -> str:
        if kind is not EditorConfirmationKind.DELETE_NOTE:
            if value:
                raise ValueError("entity label is only valid for note deletion")
            return ""
        if (
            type(value) is not str
            or not value.strip()
            or "\x00" in value
            or len(value) > 8192
            or len(value.encode("utf-8")) > 32768
        ):
            raise ValueError("invalid note deletion label")
        return value


__all__ = ["EditorConfirmationDialog", "EditorConfirmationKind"]
