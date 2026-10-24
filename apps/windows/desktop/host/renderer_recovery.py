"""Opaque native renderer-recovery curtain.

The curtain is a QWidget-only security surface.  It never embeds WebEngine,
renders the previous frame, or accepts renderer-provided text.  The host owns
the retry and exit signals and decides whether recovery is authorized.
"""

from __future__ import annotations

from enum import Enum

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont, QPaintEvent, QPainter, QPalette
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .focus_visibility import (
    NativeFocusVisibilityController,
    install_managed_focus_fallback,
)
from .window_chrome import TITLEBAR_HEIGHT, WINDOW_CONTROL_WIDTH
from desktop.ui_font_scale import normalize_ui_font_scale, scaled_font_pixel_size


_CARD_LOGICAL_WIDTH = 640


class RendererRecoveryViewState(str, Enum):
    CLIPBOARD_EXIT_RETRYING = "clipboard_exit_retrying"
    CLIPBOARD_EXIT_BLOCKED = "clipboard_exit_blocked"
    STARTING = "starting"
    SECURING = "securing"
    TRANSITION = "transition"
    LOCKED = "locked"
    RECOVERY_AVAILABLE = "recovery_available"
    REBUILDING = "rebuilding"
    BLOCKED = "blocked"
    DATABASE_RECOVERY_FAILED = "database_recovery_failed"
    STARTUP_BLOCKED = "startup_blocked"
    RUNTIME_PATH_BLOCKED = "runtime_path_blocked"
    INSTALLATION_INCOMPLETE = "installation_incomplete"


class RendererRecoverySurfaceMode(str, Enum):
    """在局部内容遮挡和完整原生表面之间作固定选择。"""

    CONTENT_PROCESSING = "content_processing"
    FULL_NATIVE = "full_native"


_FIXED_COPY = {
    RendererRecoveryViewState.CLIPBOARD_EXIT_RETRYING: ("应用已锁定", "正在重试清空剪贴板，其他退出清理已完成。"),
    RendererRecoveryViewState.CLIPBOARD_EXIT_BLOCKED: ("剪贴板尚未清空", "应用已锁定，其他退出清理已完成。复制的内容可能仍在剪贴板中。可以重试清空，或确认仍然退出。"),
    RendererRecoveryViewState.STARTING: (
        "正在启动",
        "正在准备本地加密空间。",
    ),
    RendererRecoveryViewState.SECURING: (
        "界面已安全停止",
        "正在撤销访问权限并清理敏感状态。",
    ),
    RendererRecoveryViewState.TRANSITION: (
        "正在安全锁定",
        "正在清理敏感状态并准备重新连接。",
    ),
    RendererRecoveryViewState.LOCKED: (
        "应用已锁定",
        "访问权限和可达敏感状态已清理。请安全退出应用。",
    ),
    RendererRecoveryViewState.RECOVERY_AVAILABLE: (
        "界面进程已停止",
        "应用已锁定并完成敏感状态清理。可以安全重建界面。",
    ),
    RendererRecoveryViewState.REBUILDING: (
        "正在安全重建界面",
        "应用保持锁定；新界面完成首帧交接前不会显示。",
    ),
    RendererRecoveryViewState.BLOCKED: (
        "应用保持锁定",
        "安全清理或界面恢复未完整结束。为保护数据，请退出应用。",
    ),
    RendererRecoveryViewState.DATABASE_RECOVERY_FAILED: (
        "数据库恢复未完成",
        "为保护数据，应用已停止数据库操作并保留加密恢复快照。请退出应用。",
    ),
    RendererRecoveryViewState.STARTUP_BLOCKED: (
        "无法安全启动",
        "应用未能完成安全启动。请退出应用，检查启动环境后重新启动。",
    ),
    RendererRecoveryViewState.INSTALLATION_INCOMPLETE: (
        "安装或更新尚未完成",
        "请退出软件，重新运行安装包完成恢复，然后再启动。",
    ),
    RendererRecoveryViewState.RUNTIME_PATH_BLOCKED: (
        "无法准备本地数据目录",
        "本地数据目录不明确、不安全或无法准备。请退出应用，处理目录或权限问题后重新启动。",
    ),
}

_FIXED_COPY_EN = {
    RendererRecoveryViewState.CLIPBOARD_EXIT_RETRYING: ("The app is locked", "Retrying clipboard cleanup. Other exit cleanup has completed."),
    RendererRecoveryViewState.CLIPBOARD_EXIT_BLOCKED: ("Clipboard cleanup is incomplete", "The app is locked and other exit cleanup has completed. Copied content may remain in the clipboard. Retry clearing it, or confirm exit anyway."),
    RendererRecoveryViewState.STARTING: (
        "Starting",
        "Preparing the local encrypted workspace.",
    ),
    RendererRecoveryViewState.SECURING: (
        "The interface has stopped safely",
        "Revoking access and clearing sensitive state.",
    ),
    RendererRecoveryViewState.TRANSITION: (
        "Locking securely",
        "Clearing sensitive state and preparing reconnection.",
    ),
    RendererRecoveryViewState.LOCKED: (
        "The app is locked",
        "Access and reachable sensitive state were cleared. Exit the app safely.",
    ),
    RendererRecoveryViewState.RECOVERY_AVAILABLE: (
        "The interface process stopped",
        "The app is locked and sensitive state was cleared. The interface can be rebuilt safely.",
    ),
    RendererRecoveryViewState.REBUILDING: (
        "Rebuilding the interface safely",
        "The app remains locked until the first frame of the new interface is ready.",
    ),
    RendererRecoveryViewState.BLOCKED: (
        "The app remains locked",
        "Security cleanup or interface recovery did not complete. Exit the app to protect your data.",
    ),
    RendererRecoveryViewState.DATABASE_RECOVERY_FAILED: (
        "Database recovery did not complete",
        "Database activity has stopped and an encrypted recovery snapshot was preserved. Exit the app to protect your data.",
    ),
    RendererRecoveryViewState.STARTUP_BLOCKED: (
        "Unable to start safely",
        "The app could not complete a safe startup. Exit the app, check the startup environment, and try again.",
    ),
    RendererRecoveryViewState.INSTALLATION_INCOMPLETE: (
        "Installation or update is incomplete",
        "Exit the app and run the installer again to complete recovery before starting the app.",
    ),
    RendererRecoveryViewState.RUNTIME_PATH_BLOCKED: (
        "Unable to prepare local data folders",
        "The local data folders are unavailable or unsafe. Exit the app, resolve the folder or permission issue, and try again.",
    ),
}


class RendererRecoveryCurtain(QWidget):
    """使用固定非敏感文字的真正不透明原生遮挡面。"""

    retry_requested = Signal()
    clipboard_exit_confirmed = Signal()
    minimize_requested = Signal()
    maximize_requested = Signal()
    exit_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._state = RendererRecoveryViewState.SECURING
        self._surface_mode = RendererRecoverySurfaceMode.FULL_NATIVE
        self._language = "zh"
        self._effective_theme = "DARK"
        self._ui_font_scale = "100"
        self._maximized = False
        self.setObjectName("rendererRecoveryCurtain")
        self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)
        self.setAutoFillBackground(True)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        title_bar = QFrame(self)
        self._title_bar = title_bar
        title_bar.setObjectName("rendererRecoveryTitleBar")
        title_bar.setFixedHeight(TITLEBAR_HEIGHT)
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(18, 0, 0, 0)
        title_layout.setSpacing(0)
        product_name = QLabel("小仓", title_bar)
        self._product_name = product_name
        product_name.setObjectName("rendererRecoveryProductName")
        title_layout.addWidget(product_name)
        title_layout.addStretch(1)
        title_minimize = QToolButton(title_bar)
        self._title_minimize = title_minimize
        title_minimize.setObjectName("rendererRecoveryTitleMinimize")
        title_minimize.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        title_minimize.setText("−")
        title_minimize.setAccessibleName("最小化")
        title_minimize.setFixedSize(WINDOW_CONTROL_WIDTH, TITLEBAR_HEIGHT)
        title_minimize.clicked.connect(self.minimize_requested)
        title_layout.addWidget(title_minimize)

        title_maximize = QToolButton(title_bar)
        self._title_maximize = title_maximize
        title_maximize.setObjectName("rendererRecoveryTitleMaximize")
        title_maximize.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        title_maximize.setText("□")
        title_maximize.setAccessibleName("最大化")
        title_maximize.setFixedSize(WINDOW_CONTROL_WIDTH, TITLEBAR_HEIGHT)
        title_maximize.clicked.connect(self.maximize_requested)
        title_layout.addWidget(title_maximize)

        title_exit = QToolButton(title_bar)
        self._title_exit = title_exit
        title_exit.setObjectName("rendererRecoveryTitleExit")
        title_exit.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        title_exit.setText("×")
        title_exit.setAccessibleName("退出应用")
        title_exit.setFixedSize(WINDOW_CONTROL_WIDTH, TITLEBAR_HEIGHT)
        title_exit.clicked.connect(self.exit_requested)
        title_layout.addWidget(title_exit)
        root.addWidget(title_bar)

        divider = QFrame(self)
        self._divider = divider
        divider.setFixedHeight(1)
        root.addWidget(divider)

        body = QWidget(self)
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(48, 44, 48, 44)
        body_layout.setSpacing(0)
        body_layout.addItem(
            QSpacerItem(
                0,
                0,
                QSizePolicy.Policy.Minimum,
                QSizePolicy.Policy.Expanding,
            )
        )

        card = QFrame(body)
        self._card = card
        card.setObjectName("rendererRecoveryCard")
        card.setFixedWidth(_CARD_LOGICAL_WIDTH)
        card.setSizePolicy(
            QSizePolicy.Policy.Fixed,
            QSizePolicy.Policy.Preferred,
        )
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(36, 34, 36, 34)
        card_layout.setSpacing(14)

        shield = QLabel("●", card)
        self._shield = shield
        shield.setObjectName("rendererRecoveryShield")
        shield.setAlignment(Qt.AlignmentFlag.AlignCenter)
        shield.setFixedSize(46, 46)
        card_layout.addWidget(
            shield,
            0,
            Qt.AlignmentFlag.AlignHCenter,
        )

        self._title = QLabel(card)
        self._title.setObjectName("rendererRecoveryTitle")
        self._title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._title.setWordWrap(True)
        card_layout.addWidget(self._title)

        self._message = QLabel(card)
        self._message.setObjectName("rendererRecoveryMessage")
        self._message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._message.setWordWrap(True)
        card_layout.addWidget(self._message)
        card_layout.addSpacing(12)

        actions = QHBoxLayout()
        actions.setSpacing(12)
        self._retry = QPushButton("安全重建界面", card)
        self._retry.setObjectName("rendererRecoveryRetry")
        self._retry.setAccessibleName("安全重建界面")
        self._retry.setCursor(Qt.CursorShape.PointingHandCursor)
        self._retry.setMinimumHeight(40)
        self._retry.setProperty("pdmFocusRadius", 10)
        self._retry.clicked.connect(self.retry_requested)
        actions.addWidget(self._retry)

        exit_button = QPushButton("退出应用", card)
        self._exit = exit_button
        exit_button.setObjectName("rendererRecoveryExit")
        exit_button.setAccessibleName("退出应用")
        exit_button.setCursor(Qt.CursorShape.PointingHandCursor)
        exit_button.setMinimumHeight(40)
        exit_button.setProperty("pdmFocusRadius", 10)
        exit_button.clicked.connect(self._request_exit_action)
        actions.addWidget(exit_button)
        self._action_font_baseline = QFont(self._retry.font())
        QWidget.setTabOrder(self._retry, self._exit)
        card_layout.addLayout(actions)

        centered = QHBoxLayout()
        centered.addStretch(1)
        centered.addWidget(card)
        centered.addStretch(1)
        body_layout.addLayout(centered)
        body_layout.addItem(
            QSpacerItem(
                0,
                0,
                QSizePolicy.Policy.Minimum,
                QSizePolicy.Policy.Expanding,
            )
        )
        root.addWidget(body, 1)
        self._apply_theme()
        self._focus_visibility: NativeFocusVisibilityController | None
        try:
            self._focus_visibility = NativeFocusVisibilityController(
                self,
                self._focus_targets,
                effective_theme=self._effective_theme,
                safe_anchor=self,
                default_action=self._invoke_primary_action,
                focused_target_action=self._activate_focus_target,
                parent=self,
            )
        except Exception:
            self._focus_visibility = None
            for button in (self._retry, self._exit):
                install_managed_focus_fallback(button)
        self.set_state(RendererRecoveryViewState.SECURING)

    @property
    def state(self) -> RendererRecoveryViewState:
        return self._state

    @property
    def surface_mode(self) -> RendererRecoverySurfaceMode:
        return self._surface_mode

    @property
    def recovery_enabled(self) -> bool:
        return self._retry.isEnabled()

    @property
    def language(self) -> str:
        return self._language

    @property
    def effective_theme(self) -> str:
        return self._effective_theme

    @property
    def primary_action_name(self) -> str:
        if self._state in {
            RendererRecoveryViewState.STARTING,
            RendererRecoveryViewState.TRANSITION,
        }:
            return ""
        return (
            self._retry.objectName()
            if self._retry.isEnabled()
            else self._exit.objectName()
        )

    def focus_primary_action(
        self,
        reason: Qt.FocusReason = Qt.FocusReason.OtherFocusReason,
    ) -> None:
        if self._state in {
            RendererRecoveryViewState.STARTING,
            RendererRecoveryViewState.TRANSITION,
        }:
            if self._focus_visibility is not None:
                self._focus_visibility.reset()
            return
        if self._focus_visibility is not None:
            self._focus_visibility.reset()
            self._focus_visibility.focus_safe_anchor(reason)
            return
        target = self._retry if self._retry.isEnabled() else self._exit
        target.setFocus(reason)

    def set_language(self, language: str) -> None:
        """Select one fixed native copy table; renderer text is never used."""

        if language not in {"zh", "en"}:
            raise ValueError("recovery curtain language must be zh or en")
        self._language = language
        retry_text = "安全重建界面" if language == "zh" else "Rebuild safely"
        exit_text = "退出应用" if language == "zh" else "Exit app"
        self._retry.setText(retry_text)
        self._retry.setAccessibleName(retry_text)
        self._exit.setText(exit_text)
        self._exit.setAccessibleName(exit_text)
        self._title_exit.setAccessibleName(exit_text)
        self._product_name.setText(
            "小仓" if language == "zh" else "Cangoo"
        )
        self._title_minimize.setAccessibleName(
            "最小化" if language == "zh" else "Minimize"
        )
        self.set_maximized(self._maximized)
        self._apply_copy()

    def set_effective_theme(self, effective_theme: str) -> None:
        """Apply one bounded native LIGHT/DARK recovery presentation."""

        if effective_theme not in {"LIGHT", "DARK"}:
            raise ValueError(
                "recovery curtain effective theme must be LIGHT or DARK"
            )
        if effective_theme == self._effective_theme:
            return
        self._effective_theme = effective_theme
        self._apply_theme()
        if self._focus_visibility is not None:
            self._focus_visibility.set_effective_theme(effective_theme)

    def set_ui_font_scale(self, scale: str) -> None:
        normalized = normalize_ui_font_scale(scale)
        if normalized != scale:
            raise ValueError("invalid UI font scale")
        if scale == self._ui_font_scale:
            return
        self._ui_font_scale = scale
        self._apply_theme()

    def set_surface_mode(self, mode: RendererRecoverySurfaceMode) -> None:
        """应用一个明确布局模式，不从状态名称隐式推断。"""

        if not isinstance(mode, RendererRecoverySurfaceMode):
            raise TypeError("recovery curtain surface mode must be fixed")
        self.set_native_titlebar_control_state(None, None)
        self._surface_mode = mode
        full_native = mode is RendererRecoverySurfaceMode.FULL_NATIVE
        self._title_bar.setVisible(full_native)
        self._divider.setVisible(full_native)

    def set_native_titlebar_control_state(
        self,
        hovered: str | None,
        pressed: str | None,
    ) -> None:
        """只投影宿主持有的三个窗口按钮状态，不接管窗口操作。"""

        allowed = {None, "minimize", "maximize", "close"}
        if hovered not in allowed or pressed not in allowed:
            raise ValueError("native titlebar control state must be fixed")
        if self._surface_mode is not RendererRecoverySurfaceMode.FULL_NATIVE:
            hovered = None
            pressed = None
        controls = {
            "minimize": self._title_minimize,
            "maximize": self._title_maximize,
            "close": self._title_exit,
        }
        for name, control in controls.items():
            control.setProperty("pdmNativeHover", name == hovered)
            control.setProperty("pdmNativePressed", name == pressed)
            style = control.style()
            style.unpolish(control)
            style.polish(control)
            control.update()

    def hideEvent(self, event) -> None:  # noqa: N802
        self.set_native_titlebar_control_state(None, None)
        if self._focus_visibility is not None:
            self._focus_visibility.reset()
        super().hideEvent(event)

    def set_maximized(self, maximized: bool) -> None:
        """让完整原生标题栏的最大化/还原控件反映真实状态。"""

        self._maximized = bool(maximized)
        if maximized:
            self._title_maximize.setText("❐")
            self._title_maximize.setAccessibleName(
                "还原" if self._language == "zh" else "Restore"
            )
        else:
            self._title_maximize.setText("□")
            self._title_maximize.setAccessibleName(
                "最大化" if self._language == "zh" else "Maximize"
            )

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: N802
        """绘满根区域每个像素；控件属性本身不能代替实际绘制。"""

        painter = QPainter(self)
        painter.fillRect(
            self.rect(),
            self.palette().color(QPalette.ColorRole.Window),
        )
        painter.end()
        event.accept()

    def _apply_theme(self) -> None:
        light = self._effective_theme == "LIGHT"
        window = "#ece8f4" if light else "#10151f"
        titlebar = "#e8e3f0" if light else "#10151f"
        primary = "#2d2640" if light else "#f7f9fc"
        secondary = "#6b6480" if light else "#aeb9ca"
        weak = "#a8a0bc" if light else "#7e8999"
        divider = "#d9d2e6" if light else "#273142"
        card = "#ffffff" if light else "#171e2a"
        card_border = "#ded7e9" if light else "#303b4d"
        shield_background = "#ede7fe" if light else "#203c67"
        shield_foreground = "#7c3aed" if light else "#8ab8ff"
        accent = "#8b5cf6" if light else "#4d86e8"
        accent_hover = "#7c3aed" if light else "#6197f0"
        accent_pressed = "#6d28d9" if light else "#3e72ca"
        focus_accent = "#8b5cf6" if light else "#6366f1"
        disabled_background = "#e6e0f2" if light else "#313b4b"
        secondary_border = "#cfc6df" if light else "#465268"
        secondary_hover = "#f0ecf7" if light else "#222b39"
        secondary_hover_border = "#a89cbe" if light else "#607089"
        secondary_pressed = "#e6e0f2" if light else "#1b222e"

        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor(window))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(primary))
        self.setPalette(palette)
        self._title_bar.setStyleSheet(f"background:{titlebar};")
        self._product_name.setStyleSheet(
            f"color:{primary};font-size:"
            f"{scaled_font_pixel_size(13, self._ui_font_scale)}px;"
            "font-weight:600;"
        )
        self._divider.setStyleSheet(f"background:{divider};")
        title_control_style = (
            f"QToolButton{{color:{secondary};background:transparent;"
            "border:0;font-size:16px;border-radius:0;}"
            f"QToolButton:hover{{background:{secondary_hover};}}"
            f"QToolButton:pressed{{background:{secondary_pressed};}}"
            "QToolButton[pdmNativeHover=\"true\"]"
            f"{{background:{secondary_hover};}}"
            "QToolButton[pdmNativePressed=\"true\"]"
            f"{{background:{secondary_pressed};}}"
        )
        self._title_minimize.setStyleSheet(title_control_style)
        self._title_maximize.setStyleSheet(title_control_style)
        self._title_exit.setStyleSheet(
            f"QToolButton{{color:{secondary};background:transparent;"
            "border:0;font-size:22px;border-radius:0;}"
            "QToolButton:hover{background:#9f2d38;color:#ffffff;}"
            "QToolButton:pressed{background:#84232d;color:#ffffff;}"
            "QToolButton[pdmNativeHover=\"true\"]"
            "{background:#9f2d38;color:#ffffff;}"
            "QToolButton[pdmNativePressed=\"true\"]"
            "{background:#84232d;color:#ffffff;}"
        )
        self._shield.setStyleSheet(
            f"background:{shield_background};color:{shield_foreground};"
            "border-radius:23px;font-size:18px;"
        )
        self._title.setStyleSheet(
            f"color:{primary};font-size:"
            f"{scaled_font_pixel_size(22, self._ui_font_scale)}px;"
            "font-weight:700;"
        )
        self._message.setStyleSheet(
            f"color:{secondary};font-size:"
            f"{scaled_font_pixel_size(14, self._ui_font_scale)}px;"
        )
        self._retry.setStyleSheet(
            f"QPushButton{{background:{accent};color:#ffffff;border:0;"
            "border-radius:8px;padding:0 20px;font-weight:600;}"
            f"QPushButton:hover{{background:{accent_hover};}}"
            f"QPushButton:pressed{{background:{accent_pressed};}}"
            f"QPushButton:disabled{{background:{disabled_background};"
            f"color:{weak};}}"
            "QPushButton[pdmFocusFrameReady=\"false\"]:focus{"
            f"border:2px solid {focus_accent};}}"
        )
        self._exit.setStyleSheet(
            f"QPushButton{{background:transparent;color:{secondary};"
            f"border:1px solid {secondary_border};border-radius:8px;"
            "padding:0 20px;font-weight:600;}"
            f"QPushButton:hover{{background:{secondary_hover};"
            f"border-color:{secondary_hover_border};}}"
            f"QPushButton:pressed{{background:{secondary_pressed};}}"
            "QPushButton[pdmFocusFrameReady=\"false\"]:focus{"
            f"border:2px solid {focus_accent};}}"
        )
        self._apply_action_font_scale()
        self._apply_card_style(card, card_border)

    def _apply_action_font_scale(self) -> None:
        font = QFont(self._action_font_baseline)
        factor = int(self._ui_font_scale) / 100
        if font.pixelSize() > 0:
            font.setPixelSize(max(1, round(font.pixelSize() * factor)))
        elif font.pointSizeF() > 0:
            font.setPointSizeF(font.pointSizeF() * factor)
        self._retry.setFont(font)
        self._exit.setFont(font)

    def _apply_card_style(
        self,
        card: str | None = None,
        card_border: str | None = None,
    ) -> None:
        if self._state is RendererRecoveryViewState.STARTING:
            self._card.setStyleSheet(
                "QFrame#rendererRecoveryCard{background:transparent;"
                "border:0;}"
            )
            return
        light = self._effective_theme == "LIGHT"
        resolved_card = card or ("#ffffff" if light else "#171e2a")
        resolved_border = card_border or (
            "#ded7e9" if light else "#303b4d"
        )
        self._card.setStyleSheet(
            "QFrame#rendererRecoveryCard{"
            f"background:{resolved_card};border:1px solid "
            f"{resolved_border};border-radius:16px;}}"
        )

    def _request_exit_action(self) -> None:
        if self._state is RendererRecoveryViewState.CLIPBOARD_EXIT_BLOCKED:
            self.clipboard_exit_confirmed.emit()
        elif self._state is not RendererRecoveryViewState.CLIPBOARD_EXIT_RETRYING:
            self.exit_requested.emit()

    def _apply_copy(self) -> None:
        copy_table = _FIXED_COPY if self._language == "zh" else _FIXED_COPY_EN
        title, message = copy_table[self._state]
        self._title.setText(title)
        self._message.setText(message)
        clipboard = self._state in {
            RendererRecoveryViewState.CLIPBOARD_EXIT_RETRYING,
            RendererRecoveryViewState.CLIPBOARD_EXIT_BLOCKED,
        }
        zh = self._language == "zh"
        retry_text = ("重试清空" if zh else "Retry clearing") if clipboard else ("安全重建界面" if zh else "Rebuild safely")
        exit_text = ("仍然退出" if zh else "Exit anyway") if clipboard else ("退出应用" if zh else "Exit app")
        self._retry.setText(retry_text)
        self._retry.setAccessibleName(retry_text)
        self._exit.setText(exit_text)
        self._exit.setAccessibleName(exit_text)

    def _focus_targets(self) -> tuple[QPushButton, ...]:
        return tuple(
            button
            for button in (self._retry, self._exit)
            if not button.isHidden() and button.isEnabled()
        )

    def _activate_focus_target(self, target: QWidget) -> bool:
        if target is self._retry:
            self._retry.click()
            return True
        if target is self._exit:
            self._exit.click()
            return True
        return False

    def _invoke_primary_action(self) -> None:
        action_name = self.primary_action_name
        if (
            action_name == self._retry.objectName()
            and not self._retry.isHidden()
            and self._retry.isEnabled()
        ):
            self.retry_requested.emit()
            return
        if (
            action_name == self._exit.objectName()
            and not self._exit.isHidden()
            and self._exit.isEnabled()
        ):
            self._request_exit_action()

    def set_state(self, state: RendererRecoveryViewState) -> None:
        if not isinstance(state, RendererRecoveryViewState):
            raise TypeError("recovery curtain state must be a fixed enum")
        self._state = state
        self._apply_copy()
        starting = state is RendererRecoveryViewState.STARTING
        transition = state is RendererRecoveryViewState.TRANSITION
        exit_only = state in {
            RendererRecoveryViewState.DATABASE_RECOVERY_FAILED,
            RendererRecoveryViewState.STARTUP_BLOCKED,
            RendererRecoveryViewState.RUNTIME_PATH_BLOCKED,
            RendererRecoveryViewState.INSTALLATION_INCOMPLETE,
        }
        if transition:
            self._retry.clearFocus()
            self._exit.clearFocus()
            self._title_exit.clearFocus()
        self._title_exit.setVisible(True)
        self._card.setVisible(True)
        self._shield.setVisible(not starting)
        self._retry.setVisible(
            not starting and not transition and not exit_only
        )
        self._exit.setVisible(not starting and not transition)
        self._apply_card_style()
        self._retry.setEnabled(
            state in {RendererRecoveryViewState.RECOVERY_AVAILABLE, RendererRecoveryViewState.CLIPBOARD_EXIT_BLOCKED}
        )
        self._exit.setEnabled(state is not RendererRecoveryViewState.CLIPBOARD_EXIT_RETRYING)
        if self._focus_visibility is None:
            return
        if starting or transition:
            self._focus_visibility.reset()
            self._focus_visibility.focus_safe_anchor()
            return
        self._focus_visibility.refresh()


__all__ = [
    "RendererRecoveryCurtain",
    "RendererRecoverySurfaceMode",
    "RendererRecoveryViewState",
]
