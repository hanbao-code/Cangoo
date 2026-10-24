"""固定原生启动失败面；不得接收异常文本、路径或 renderer 内容。"""

from __future__ import annotations

import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QApplication, QMainWindow

from .diagnostics import STARTUP_REFUSAL_EXIT_CODE, StartupBlockReason
from .resources import application_icon
from .renderer_recovery import (
    RendererRecoveryCurtain,
    RendererRecoverySurfaceMode,
    RendererRecoveryViewState,
)


def _state_for_reason(
    reason: StartupBlockReason,
) -> RendererRecoveryViewState:
    if not isinstance(reason, StartupBlockReason):
        raise TypeError("startup block reason must be a fixed enum")
    if reason is StartupBlockReason.INSTALLATION_INCOMPLETE:
        return RendererRecoveryViewState.INSTALLATION_INCOMPLETE
    if reason is StartupBlockReason.RUNTIME_PATHS:
        return RendererRecoveryViewState.RUNTIME_PATH_BLOCKED
    return RendererRecoveryViewState.STARTUP_BLOCKED


class StartupBlockedSurface(QMainWindow):
    """使用标准系统标题栏承载既有不透明原生安全幕布。"""

    def __init__(self, reason: StartupBlockReason) -> None:
        super().__init__()
        self._reason = reason
        self.setWindowTitle("小仓")
        self.setWindowIcon(application_icon())
        self.setMinimumSize(960, 640)
        self.resize(1200, 800)
        self.curtain = RendererRecoveryCurtain(self)
        self.curtain.set_surface_mode(
            RendererRecoverySurfaceMode.CONTENT_PROCESSING
        )
        self.setCentralWidget(self.curtain)
        self.curtain.exit_requested.connect(self.close)
        self.set_reason(reason)

    @property
    def reason(self) -> StartupBlockReason:
        return self._reason

    def set_reason(self, reason: StartupBlockReason) -> None:
        state = _state_for_reason(reason)
        self._reason = reason
        self.curtain.set_state(state)

    def focus_exit_action(self) -> None:
        self.curtain.focus_primary_action(
            Qt.FocusReason.ActiveWindowFocusReason
        )

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        super().closeEvent(event)
        application = QApplication.instance()
        if application is not None:
            application.quit()


def show_startup_blocked(reason: StartupBlockReason) -> int:
    """显示一个固定原生失败面，并在用户退出后返回固定拒绝码。"""

    _state_for_reason(reason)
    existing = QApplication.instance()
    if existing is not None and not isinstance(existing, QApplication):
        raise RuntimeError("startup surface requires QApplication")
    application = existing or QApplication(sys.argv[:1])
    application.setApplicationName("Cangoo")
    application.setQuitOnLastWindowClosed(False)
    surface = StartupBlockedSurface(reason)
    surface.show()
    surface.focus_exit_action()
    application.exec()
    return STARTUP_REFUSAL_EXIT_CODE


__all__ = [
    "STARTUP_REFUSAL_EXIT_CODE",
    "StartupBlockedSurface",
    "StartupBlockReason",
    "show_startup_blocked",
]
