"""设备直传独立窗口；网页只提交本次流程的固定意图。"""

from __future__ import annotations

from PySide6.QtCore import QEvent, QObject, QRect, QTimer, QUrl, Signal, Slot
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWidgets import QApplication
from shiboken6 import isValid

from desktop.host.scene_refresh import SceneRefresh, request_surface_frame, scene_target
from desktop.host.window_placement import fit_window_rect
from desktop.bridge.export_selection_bridge import ExportSelectionBridgeSurface
from desktop.bridge.command_ids import CommandId
from .editor_window import EditorWindow, _PassiveEditorAdapter, _EditorSecurityBoundarySink


class DirectTransferLauncherBridge(QObject):
    def __init__(self, owner):
        super().__init__(owner)
        self._owner = owner

    @Slot(result="QVariantMap")
    def openV1(self):
        return self._owner.open()


class DirectTransferWindowBridge(ExportSelectionBridgeSurface):
    stateChangedV1 = Signal("QVariantMap")

    def __init__(self, owner):
        self._owner = owner
        super().__init__(owner.catalog, _PassiveEditorAdapter(owner.core.adapter), owner,
                         security_boundary_sink=_EditorSecurityBoundarySink(owner.conceal))
        self._boundary.bind_borrowed_web_authority(*owner.core.epochs)

    def _submit_explicit(self, command_id, arguments):
        core = self._owner.core
        if self._owner.bridge is not self or not core._current():
            return {"accepted": False, "errorCode": "STALE_PAGE"}
        if command_id not in {CommandId.C07, CommandId.C90} and (
                core._state["role"] != "SEND" or core._state["phase"] != "REVIEW"
                or core._state["offerReady"] or core._state["preparing"]):
            return {"accepted": False, "errorCode": "REQUEST_BUSY"}
        return super()._submit_explicit(command_id, arguments)

    def _invoke(self, action, flow_id, *arguments):
        if self._owner.bridge is not self:
            return {"accepted": False, "errorCode": "STALE_FLOW"}
        return self._owner.core.action(action, flow_id, *arguments)

    @Slot(result="QVariantMap")
    def initializeV1(self):
        return self._owner.core.snapshot() if self._owner.bridge is self and self._owner.core._current() else {}

    @Slot()
    def presentReadyV1(self):
        if self._owner.bridge is self and self._owner.core._current() and self._owner.window is not None:
            self._owner.window.reveal_view()
            self._owner._schedule_refresh()

    @Slot()
    def requestCloseV1(self):
        if self._owner.bridge is self:
            self._owner.close()

    @Slot("QVariant", "QVariant", "QVariant", result="QVariantMap")
    def beginV1(self, flow_id, role, transport):
        return self._invoke("begin", flow_id, role, transport)

    @Slot("QVariant", "QVariant", result="QVariantMap")
    def choosePeerV1(self, flow_id, peer_id):
        return self._invoke("choose", flow_id, peer_id)

    @Slot("QVariant", "QVariant", result="QVariantMap")
    def connectAddressV1(self, flow_id, address):
        return self._invoke("connectAddress", flow_id, address)

    @Slot("QVariant", "QVariant", result="QVariantMap")
    def submitPairingCodeV1(self, flow_id, code):
        return self._invoke("pairingCode", flow_id, code)

    @Slot("QVariant", result="QVariantMap")
    def copyPairingCodeV1(self, flow_id):
        return self._invoke("copyPairingCode", flow_id)

    @Slot("QVariant", result="QVariantMap")
    def approvePeerV1(self, flow_id):
        return self._invoke("approve", flow_id)

    @Slot("QVariant", "QVariant", result="QVariantMap")
    def sendV1(self, flow_id, scope):
        return self._invoke("send", flow_id, scope)

    @Slot("QVariant", result="QVariantMap")
    def cancelV1(self, flow_id):
        return self._invoke("cancel", flow_id)

    @Slot("QVariant", result="QVariantMap")
    def authorizeNetworkV1(self, flow_id):
        return self._invoke("authorizeNetwork", flow_id)

    @Slot("QVariant", result="QVariantMap")
    def revokeNetworkV1(self, flow_id):
        return self._invoke("revokeNetwork", flow_id)

    @Slot("QVariant", result="QVariantMap")
    def restartV1(self, flow_id):
        return self._invoke("restart", flow_id)


class DirectTransferWindowController(QObject):
    def __init__(self, core, *, catalog, authority, busy, view_factory, renderer_failed, parent=None):
        super().__init__(parent)
        self.core = core
        self.catalog = catalog
        self._authority, self._busy = authority, busy
        self._view_factory, self._renderer_failed = view_factory, renderer_failed
        self.window = self.bridge = self._channel = self._handle = None
        self._geometry = QRect()
        self._appearance = None
        self._refresh_pending = None
        self._refresh_timer = QTimer(self)
        self._refresh_timer.setSingleShot(True)
        self._refresh_timer.timeout.connect(self._refresh)
        self._scene = SceneRefresh(self, self._scene_target)
        self.launcher = DirectTransferLauncherBridge(self)
        core.stateChanged.connect(self._state_changed)

    def open(self):
        if self.window is not None:
            if not self.core._current():
                self.close()
                return self.core._ack("SESSION_REQUIRED")
            self.window.showNormal() if self.window.isMinimized() else self.window.show()
            self.window.raise_()
            self.window.activateWindow()
            return self.core._ack()
        if self._busy():
            return self.core._ack("REQUEST_BUSY")
        if not self.core.bind(*self._authority()):
            return self.core._ack("SESSION_REQUIRED")
        try:
            self.window = EditorWindow(self._view_factory, effective_theme=self.core.snapshot()["effectiveTheme"])
            window = self.window
            window.setMinimumSize(600, 520)
            window.resize(900, 720)
            window.installEventFilter(self)
            window.close_requested.connect(self.close)
            self.bridge = DirectTransferWindowBridge(self)
            self.bridge.destroyed.connect(lambda: self._bridge_destroyed(window))
            self._channel = QWebChannel(window)
            self._channel.registerObject("pdmDirectTransferV1", self.bridge)
            page = window.view.page()
            page.setWebChannel(self._channel)
            page.renderProcessTerminated.connect(self._renderer_failure)
            window.view.loadFinished.connect(self._loaded)
            self._state_changed(self.core.snapshot())
            screen = QApplication.primaryScreen()
            if screen is not None:
                available = screen.availableGeometry()
                rect = QRect(self._geometry) if self._geometry.isValid() else QRect(available.center().x() - 450, available.center().y() - 360, 900, 720)
                window.setGeometry(fit_window_rect(rect, available, window.minimumSize()))
            window.view.setUrl(QUrl("pdm://app/transfer.html"))
            window.show()
            return self.core._ack()
        except Exception:
            self.close()
            return self.core._ack("INTERNAL_FAILURE")

    def _state_changed(self, state):
        window = self.window
        if window is None or self.bridge is None:
            return
        appearance = (state["effectiveTheme"], state["language"], state["uiFontScale"])
        if appearance != self._appearance:
            self._appearance = appearance
            window.set_theme(state["effectiveTheme"])
            titlebar = window.product_titlebar
            titlebar.set_window_titles("设备传输", "Device transfer")
            titlebar.set_language("en" if state["language"] == "EN" else "zh")
            titlebar.set_ui_font_scale(state["uiFontScale"])
            window.setWindowTitle("Device transfer" if state["language"] == "EN" else "设备传输")
        self.bridge.stateChangedV1.emit(state)

    def return_to_start(self, page_epoch, session_epoch):
        if min(page_epoch, session_epoch) <= 0 or self._authority() != (page_epoch, session_epoch):
            return
        epochs = self._authority()
        if self.window is None:
            self.open()
        elif self.core.bind(*epochs):
            self.window.show()
            self.window.reveal_view()
            self.window.raise_()
            self.window.activateWindow()
            self._schedule_refresh()

    def _scene_target(self):
        window = self.window
        if (window is None or self.bridge is None or not isValid(window) or not self.core._current()
                or not window.isVisible() or window.isMinimized() or not window.view.isEnabled()):
            return None
        return scene_target(window.view, window.windowHandle(), (*self.core.epochs, id(self.bridge)))

    def _schedule_refresh(self):
        window = self.window
        if window is None:
            return
        handle = window.windowHandle()
        if handle is not self._handle:
            if self._handle is not None and isValid(self._handle):
                self._handle.removeEventFilter(self)
            self._handle = handle
            if handle is not None:
                handle.installEventFilter(self)
        if not window.isVisible() or window.isMinimized():
            self._cancel_refresh()
            return
        self._refresh_pending = (window, self.bridge, handle)
        if not self._refresh_timer.isActive():
            self._refresh_timer.start(0)

    def _refresh(self):
        pending, self._refresh_pending = self._refresh_pending, None
        if pending != (self.window, self.bridge, self._handle) or self._scene_target() is None:
            return
        request_surface_frame(self.window.view.page(), self.window.view, self.window.windowHandle)
        self._scene.schedule()

    def _cancel_refresh(self):
        self._refresh_pending = None
        self._refresh_timer.stop()
        self._scene.cancel()

    def eventFilter(self, watched, event):  # noqa: N802
        if watched is self.window:
            if event.type() == QEvent.Type.Hide or event.type() == QEvent.Type.WindowStateChange and self.window.isMinimized():
                self._cancel_refresh()
            elif event.type() in {QEvent.Type.Show, QEvent.Type.Resize, QEvent.Type.WindowStateChange, QEvent.Type.WinIdChange}:
                self._schedule_refresh()
        elif watched is self._handle and event.type() == QEvent.Type.Expose:
            self._schedule_refresh()
        return False

    def conceal(self):
        self._cancel_refresh()
        if self.window is not None:
            self.window.view.setEnabled(False)
            self.window.view.hide()
            self.window.hide()
            QApplication.sync()
        return True

    def close(self):
        complete = self._close()
        if not complete:
            self._renderer_failed()
        return complete

    def close_for_security(self):
        if not self._close():
            raise RuntimeError("direct transfer window cleanup incomplete")

    def _close(self):
        complete = True
        for cleanup in (self.conceal, self.core.close, self._dispose_window):
            try:
                if cleanup() is False:
                    complete = False
            except Exception:
                complete = False
        return complete

    def handoff_received(self):
        self.conceal()
        self._dispose_window()

    def _dispose_window(self):
        window, bridge, channel = self.window, self.bridge, self._channel
        self.window = self.bridge = self._channel = None
        self._appearance = None
        if bridge is not None and not bridge.close_bridge("bridge_close"):
            self._renderer_failed()
        if self._handle is not None and isValid(self._handle):
            self._handle.removeEventFilter(self)
        self._handle = None
        if window is not None:
            if not window.isMaximized():
                self._geometry = QRect(window.geometry())
            window.removeEventFilter(self)
            page = window.view.page()
            page.setWebChannel(None)
            for signal, callback in ((page.renderProcessTerminated, self._renderer_failure), (window.view.loadFinished, self._loaded)):
                try:
                    signal.disconnect(callback)
                except (RuntimeError, TypeError):
                    pass
            if channel is not None and bridge is not None:
                channel.deregisterObject(bridge)
            if bridge is not None:
                bridge.deleteLater()
            window.deleteLater()

    def _loaded(self, ok):
        if not ok:
            self._renderer_failure()

    def _renderer_failure(self, *_args):
        self.conceal()
        self._renderer_failed()
        self._close()

    def _bridge_destroyed(self, window):
        if self.window is window:
            self._renderer_failure()
