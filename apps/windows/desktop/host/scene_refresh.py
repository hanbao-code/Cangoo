"""复用窗口恢复时的立即更新与单次场景重画。"""

from __future__ import annotations

from typing import Callable

from PySide6.QtCore import QObject, Qt, QTimer
from PySide6.QtQuickWidgets import QQuickWidget
from shiboken6 import isValid


def scene_target(view, handle, token):
    """只读取当前可呈现对象；窗口和会话资格由调用方检查。"""

    try:
        if not isValid(view) or not view.isVisible():
            return None
        quick_widget = view.focusProxy()
        if (
            not isinstance(quick_widget, QQuickWidget)
            or not isValid(quick_widget)
            or not quick_widget.isVisible()
        ):
            return None
        scene = quick_widget.quickWindow()
        if (
            scene is None or not isValid(scene)
            or handle is None or not isValid(handle) or not handle.isExposed()
        ):
            return None
        return token, view, quick_widget, scene, handle
    except (RuntimeError, TypeError):
        return None


def request_surface_frame(page, view, handle_callback) -> None:
    """沿既有顺序请求网页、控件、原生句柄和场景更新。"""

    page.setVisible(True)
    view.update()
    handle = handle_callback()
    if handle is not None:
        handle.requestUpdate()
    try:
        quick_widget = view.focusProxy()
        if not isinstance(quick_widget, QQuickWidget) or not isValid(quick_widget):
            return
        scene = quick_widget.quickWindow()
        if scene is not None and isValid(scene):
            scene.update()
    except (RuntimeError, TypeError):
        pass


class SceneRefresh:
    """合并窗口变更，约200毫秒后仅重画同一合法场景一次。"""

    # shortcut: 沿用主窗的有界恢复，Qt 根因未定；若仍有可见黑帧，须重新定位。
    def __init__(self, parent: QObject | None, target_callback: Callable[[], tuple | None]):
        self._target = target_callback
        self.ticket = None
        self.timer = QTimer(parent)
        self.timer.setSingleShot(True)
        self.timer.setTimerType(Qt.TimerType.PreciseTimer)
        self.timer.timeout.connect(self.consume)

    def cancel(self) -> None:
        self.ticket = None
        self.timer.stop()

    def schedule(self) -> None:
        self.cancel()
        target = self._target()
        if target is not None:
            self.ticket = target
            self.timer.start(200)

    def consume(self) -> None:
        ticket = self.ticket
        self.ticket = None
        if ticket is None:
            return
        current = self._target()
        if (
            current is None
            or current[0] != ticket[0]
            or any(now is not before for now, before in zip(current[1:], ticket[1:]))
        ):
            return
        try:
            current[3].update()
        except (RuntimeError, TypeError):
            pass
