"""独立备份窗口；借用主会话，只开放已有备份命令。"""

from __future__ import annotations

from PySide6.QtCore import QEvent, QObject, QRect, Qt, QUrl, Signal, Slot
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineCore import QWebEngineScript
from PySide6.QtWidgets import QApplication
from shiboken6 import isValid

from desktop.bridge.backup_bridge import BackupBridgeSurface
from desktop.bridge.command_ids import CommandId
from desktop.host.sensitive_dom import SensitiveDomController
from desktop.host.scene_refresh import SceneRefresh, request_surface_frame, scene_target
from desktop.host.window_placement import fit_window_rect
from .editor_window import EditorWindow, _PassiveEditorAdapter, _EditorSecurityBoundarySink

BACKUP_COMMANDS = frozenset({*(CommandId(f"C{number}") for number in range(50, 60)),
                             *(CommandId(f"C{number}") for number in range(87, 91)), CommandId.C81})
BACKUP_IMPORT_COMMANDS = BACKUP_COMMANDS - {CommandId.C50, CommandId.C51, *(CommandId(f"C{number}") for number in range(87, 91))}


class BackupLauncherBridge(QObject):
    """仅向主页面开放固定入口；控制器后续的Qt连接不改变此对象的元接口。"""

    operationCompletedV1 = Signal(int, int, str, "QVariantMap")

    def __init__(self, controller):
        super().__init__(controller)
        self._controller = controller
        controller.operationCompletedV1.connect(self.operationCompletedV1.emit)

    @Slot("QVariant", result="QVariantMap")
    def openV1(self, mode):
        return self._controller.openV1(mode)


class BackupWindowBridge(BackupBridgeSurface):
    projectionChangedV1 = Signal("QVariantMap")
    closeDeferredV1 = Signal()

    def __init__(self, controller, page_epoch, session_epoch, sensitive_dom):
        super().__init__(
            controller.catalog, _PassiveEditorAdapter(controller.adapter), controller,
            secret_lifecycle_sink=sensitive_dom,
            security_boundary_sink=_EditorSecurityBoundarySink(controller.conceal),
        )
        self._controller = controller
        self._active_operations = set()
        self._boundary.bind_borrowed_web_authority(page_epoch, session_epoch)

    def _submit_explicit(self, command_id, arguments):
        if self._controller.adapter.editor_occupancy is not None and command_id in BACKUP_IMPORT_COMMANDS:
            return {"accepted": False, "errorCode": "REQUEST_BUSY"}
        ack = super()._submit_explicit(command_id, arguments)
        if ack.get("accepted") and command_id in {CommandId.C51, CommandId.C53, CommandId.C58}:
            self._active_operations.add(arguments[0])
        return ack

    @Slot(result="QVariantMap")
    def initializeV1(self):
        if self._controller.bridge is not self:
            return {}
        received = self._controller._received_preview
        if self._controller.source_kind == "TRANSFER" and received is None:
            return {}
        self._controller._received_preview = None
        return {
            "pageEpoch": self.active_page_epoch,
            "sessionEpoch": self.active_session_epoch,
            "mode": self._controller.mode,
            "sourceKind": self._controller.source_kind,
            "displayName": self._controller.display_name,
            "receivedPreview": received,
            **self._controller.projection,
        }

    @Slot()
    def presentReadyV1(self):
        if self._controller.bridge is self and self._controller.window is not None:
            self._controller.window.reveal_view()
            self._controller._queue_surface_refresh(self._controller.window)

    @Slot()
    def requestCloseV1(self):
        if self._controller.bridge is self:
            self._controller.close()

    def _emit_completion(self, command_id, envelope):
        self._active_operations.discard(envelope.request_id)
        super()._emit_completion(command_id, envelope)
        if self._controller.bridge is self and envelope.error_code == "OK":
            if command_id in {CommandId.C51, CommandId.C58}:
                if command_id is CommandId.C58:
                    self._controller._received_import_completed = True
                self._controller.operationCompletedV1.emit(
                    envelope.page_epoch, envelope.session_epoch,
                    "IMPORT" if command_id is CommandId.C58 else "EXPORT",
                    dict(envelope.result),
                )


class BackupWindowController(QObject):
    """唯一窗口实例，原生关闭与安全边界统一收回备份能力。"""

    operationCompletedV1 = Signal(int, int, str, "QVariantMap")
    receivedPreviewClosed = Signal(int, int)
    _surface_refresh_queued = Signal(int, object, object)

    def __init__(self, catalog, adapter, *, authority, view_factory,
                 renderer_failed, parent=None):
        super().__init__(parent)
        self.catalog, self.adapter = catalog, adapter
        self._authority, self._view_factory = authority, view_factory
        self._renderer_failed = renderer_failed
        self.window = None
        self.bridge = None
        self._channel = None
        self._sensitive_dom = None
        self._geometry = QRect()
        self._surface_refresh_serial = 0
        self._surface_refresh_pending = None
        self._surface_refresh_handle = None
        self._scene_refresh = SceneRefresh(self, self._scene_refresh_target)
        self._surface_refresh_queued.connect(self._consume_surface_refresh, Qt.ConnectionType.QueuedConnection)
        self.mode = "export"
        self.source_kind = "FILE"
        self.display_name = ""
        self._received_preview = None
        self._received_import_completed = False
        self._transfer_busy = lambda: False
        self.projection = {"effectiveTheme": "DARK", "language": "ZH", "uiFontScale": "100"}
        self.launcher = BackupLauncherBridge(self)

    @Slot("QVariant", result="QVariantMap")
    def openV1(self, mode):
        return self._open(mode)

    def bind_transfer_guard(self, callback):
        self._transfer_busy = callback

    def open_received_preview(self, result, page_epoch, session_epoch, display_name):
        if self.window is not None or self._authority() != (page_epoch, session_epoch) or page_epoch <= 0 or session_epoch <= 0:
            return False
        if type(result) is not dict or type(result.get("previewTicket")) is not str or not result["previewTicket"]:
            return False
        self.source_kind = "TRANSFER"
        self.display_name = display_name
        self._received_preview = dict(result)
        self._received_import_completed = False
        return self._open("import", received=True)["accepted"]

    def _open(self, mode, *, received=False):
        if mode not in ("import", "export") or type(mode) is not str:
            return {"accepted": False, "errorCode": "INVALID_ARGUMENT"}
        if self.window is not None:
            if self.window.isMinimized():
                self.window.showNormal()
            self.window.raise_()
            self.window.activateWindow()
            return {"accepted": True, "errorCode": "OK"}
        if not received:
            if self._transfer_busy():
                return {"accepted": False, "errorCode": "REQUEST_BUSY"}
            self.source_kind, self.display_name, self._received_preview = "FILE", "", None
            self._received_import_completed = False
        page_epoch, session_epoch = self._authority()
        if page_epoch <= 0 or session_epoch <= 0:
            return {"accepted": False, "errorCode": "SESSION_REQUIRED"}
        self.mode = mode
        try:
            window = EditorWindow(self._view_factory, effective_theme=self.projection["effectiveTheme"])
            self.window = window
            window.installEventFilter(self)
            window.setMinimumSize(540, 480)
            window.resize(960, 760)
            window.close_requested.connect(self.close)
            view = window.view
            page = view.page()
            initial = QWebEngineScript()
            initial.setName("pdm-backup-window")
            initial.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentCreation)
            initial.setWorldId(QWebEngineScript.ScriptWorldId.MainWorld)
            initial.setSourceCode("window.pdmBackupWindow = true;")
            page.scripts().insert(initial)
            self._sensitive_dom = SensitiveDomController(page)
            self.bridge = BackupWindowBridge(self, page_epoch, session_epoch, self._sensitive_dom)
            self.bridge.destroyed.connect(lambda: self._bridge_destroyed(window, page_epoch))
            self._channel = QWebChannel(window)
            self._channel.registerObject("pdmBackupV1", self.bridge)
            page.setWebChannel(self._channel)
            page.renderProcessTerminated.connect(self._renderer_failure)
            view.loadFinished.connect(self._loaded)
            self.adapter.set_backup_window_parent(window)
            self.apply_settings(**self.projection)
            screen = QApplication.primaryScreen()
            if screen is not None:
                available = screen.availableGeometry()
                rect = QRect(self._geometry)
                if not rect.isValid():
                    rect = QRect(available.center().x() - 480, available.center().y() - 380, 960, 760)
                window.setGeometry(fit_window_rect(rect, available, window.minimumSize()))
            view.setUrl(QUrl("pdm://app/index.html"))
            window.show()
            self._sync_surface_refresh_handle(window)
            return {"accepted": True, "errorCode": "OK"}
        except Exception:
            self.close(force=True)
            return {"accepted": False, "errorCode": "INTERNAL_FAILURE"}

    def apply_settings(self, effectiveTheme, language, uiFontScale):
        self.projection = {"effectiveTheme": effectiveTheme, "language": language, "uiFontScale": uiFontScale}
        if self.window is None:
            return
        self.window.set_theme(effectiveTheme)
        titlebar = self.window.product_titlebar
        chinese, english = ("比较接收的资料", "Compare received data") if self.source_kind == "TRANSFER" else ("导入 / 导出", "Import / Export")
        titlebar.set_window_titles(chinese, english)
        titlebar.set_language("en" if language == "EN" else "zh")
        titlebar.set_ui_font_scale(uiFontScale)
        self.window.setWindowTitle(english if language == "EN" else chinese)
        if self.bridge is not None:
            self.bridge.projectionChangedV1.emit(dict(self.projection))

    def conceal(self):
        self._cancel_surface_refresh()
        if self.window is not None:
            self.window.view.setEnabled(False)
            self.window.view.hide()
            self.window.hide()
            QApplication.sync()
        return True

    def close(self, *, force=False, reason="bridge_close"):
        window, bridge = self.window, self.bridge
        if window is None:
            return True
        # 普通关闭沿现有备份语义等待在途操作，不能把已开始提交谎报为取消。
        if bridge is not None and bridge._active_operations and not force:
            bridge.closeDeferredV1.emit()
            return False
        return_to_transfer = bool(self.source_kind == "TRANSFER" and not force and not self._received_import_completed
            and bridge is not None and self._authority() == (bridge.active_page_epoch, bridge.active_session_epoch))
        return_epochs = self._authority() if return_to_transfer else (0, 0)
        complete = self.conceal()
        self._detach_surface_refresh(window)
        if not window.isMaximized():
            self._geometry = QRect(window.geometry())
        if bridge is not None:
            page_epoch = bridge.active_page_epoch
            complete = bridge.close_bridge("bridge_close") and complete
            self.adapter.close_backup_window(page_epoch)
        self.adapter.set_backup_window_parent(None)
        page = window.view.page()
        page.setWebChannel(None)
        for signal, callback in ((page.renderProcessTerminated, self._renderer_failure),
                                 (window.view.loadFinished, self._loaded)):
            try:
                signal.disconnect(callback)
            except (RuntimeError, TypeError):
                pass
        if self._sensitive_dom is not None:
            self._sensitive_dom.clear_all(reason)
            self._sensitive_dom.detach()
        if self._channel is not None and bridge is not None:
            self._channel.deregisterObject(bridge)
        self.window = self.bridge = self._channel = self._sensitive_dom = None
        self.source_kind, self.display_name, self._received_preview = "FILE", "", None
        self._received_import_completed = False
        if bridge is not None:
            bridge.deleteLater()
        window.deleteLater()
        if return_to_transfer and complete:
            self.receivedPreviewClosed.emit(*return_epochs)
        return complete

    def _cancel_surface_refresh(self):
        self._surface_refresh_serial += 1
        self._surface_refresh_pending = None
        self._scene_refresh.cancel()

    def _sync_surface_refresh_handle(self, window):
        if window is not self.window or not isValid(window):
            return None
        handle = window.windowHandle()
        if handle is not None and not isValid(handle):
            handle = None
        if handle is not self._surface_refresh_handle:
            self._cancel_surface_refresh()
            previous = self._surface_refresh_handle
            if previous is not None and isValid(previous):
                previous.removeEventFilter(self)
            self._surface_refresh_handle = handle
            if handle is not None:
                handle.installEventFilter(self)
        return handle

    def _detach_surface_refresh(self, window):
        self._cancel_surface_refresh()
        handle = self._surface_refresh_handle
        self._surface_refresh_handle = None
        if handle is not None and isValid(handle):
            handle.removeEventFilter(self)
        if isValid(window):
            window.removeEventFilter(self)

    def _scene_refresh_target(self):
        window, bridge = self.window, self.bridge
        if window is None or bridge is None or not isValid(window) or not isValid(bridge):
            return None
        try:
            page_epoch, session_epoch = self._authority()
            if (
                type(page_epoch) is not int or type(session_epoch) is not int
                or page_epoch <= 0 or session_epoch <= 0
                or (bridge.active_page_epoch, bridge.active_session_epoch) != (page_epoch, session_epoch)
                or not window.isVisible() or window.isMinimized() or not window.isEnabled()
            ):
                return None
            view = window.view
            if not isValid(view) or not view.isEnabled() or not isValid(view.page()):
                return None
            return scene_target(view, window.windowHandle(), (page_epoch, session_epoch, id(bridge)))
        except (RuntimeError, TypeError):
            return None

    def _queue_surface_refresh(self, window, source_handle=None):
        handle = self._sync_surface_refresh_handle(window)
        if handle is None or source_handle is not None and source_handle is not handle:
            return
        if not window.isVisible() or window.isMinimized():
            self._cancel_surface_refresh()
            return
        pending = self._surface_refresh_pending
        if pending is not None and pending[0] is window and pending[1] is handle:
            return
        self._surface_refresh_pending = (window, handle)
        self._surface_refresh_queued.emit(self._surface_refresh_serial, window, handle)

    @Slot(int, object, object)
    def _consume_surface_refresh(self, serial, window, handle):
        pending = self._surface_refresh_pending
        if (
            serial != self._surface_refresh_serial or window is not self.window
            or pending is None or pending[0] is not window or pending[1] is not handle
            or handle is not self._surface_refresh_handle
        ):
            return
        self._surface_refresh_pending = None
        target = self._scene_refresh_target()
        if target is None or target[-1] is not handle:
            self._scene_refresh.cancel()
            return
        request_surface_frame(window.view.page(), window.view, window.windowHandle)
        self._scene_refresh.schedule()

    def eventFilter(self, watched, event):  # noqa: N802
        if not isValid(watched):
            return False
        window = self.window
        if watched is window:
            if event.type() == QEvent.Type.Hide or (
                event.type() == QEvent.Type.WindowStateChange and window.isMinimized()
            ):
                self._cancel_surface_refresh()
            elif event.type() in {QEvent.Type.Show, QEvent.Type.WinIdChange, QEvent.Type.Resize, QEvent.Type.WindowStateChange}:
                self._queue_surface_refresh(window)
        elif watched is self._surface_refresh_handle and event.type() == QEvent.Type.Expose:
            self._queue_surface_refresh(window, watched)
        return False

    def _loaded(self, ok):
        if not ok:
            self._renderer_failure()

    def _renderer_failure(self, *_args):
        self.conceal()
        self._renderer_failed()
        self.close(force=True, reason="renderer_failure")

    def _bridge_destroyed(self, window, page_epoch):
        if self.window is not window:
            return
        self.bridge = None
        self.adapter.close_backup_window(page_epoch)
        self._renderer_failure()
