"""密码独立编辑窗口的最小原生边界。

本模块不拥有数据库或主会话；它只将一个已核对的主页面身份借给
一个无父普通顶层窗口，并在窗口结束时回收本实例的请求与秘密。
"""

from __future__ import annotations

from dataclasses import dataclass
import ctypes
import json
import math
import sys
from typing import Callable
from uuid import uuid4

from PySide6.QtCore import QEvent, QObject, QRect, QSize, Qt, QTimer, QUrl, Signal, Slot
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineScript
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtGui import QColor, QKeyEvent, QKeySequence, QShowEvent
from shiboken6 import isValid

from desktop.bridge.command_ids import CommandId
from desktop.bridge.contract_catalog import ContractCatalog, ValueRejected
from desktop.bridge.protocol import (
    AdapterCompletion,
    AdapterRequest,
    BridgeAdapter,
    CompletionCallback,
    CompletionEnvelope,
    SecurityBoundaryOutcome,
)
from desktop.bridge.request_boundary import RequestBoundary, Surface
from desktop.bridge.web_bridge_base import _BridgeLifetimeGuard
from desktop.host.sensitive_dom import SensitiveDomController
from desktop.host.window_placement import fit_window_rect, native_window_rect
from desktop.host.window_chrome import (
    HTCAPTION,
    HTCLOSE,
    HTMAXBUTTON,
    HTMINBUTTON,
    TITLEBAR_HEIGHT,
    WINDOW_CONTROL_COUNT,
    WINDOW_CONTROL_WIDTH,
    WM_NCCALCSIZE,
    WM_NCHITTEST,
    WM_NCMOUSELEAVE,
    WM_NCMOUSEMOVE,
    WM_NCLBUTTONDOWN,
    WM_NCLBUTTONUP,
    ProductTitleBar,
    apply_standard_window_frame,
    native_dpi_scale,
    native_resize_border,
    native_window_control_hit,
    native_window_control_hit_at_cursor,
    native_window_is_maximized,
    resize_hit_test,
    set_win11_border_color_none,
    set_win11_corner_preference,
    standard_window_frame_client_rect,
    track_non_client_mouse_leave,
)
from desktop.m4.editor_chrome import (
    EditorConfirmationDialog,
    EditorConfirmationKind,
)


_READ_EDITOR_PASSWORD_SELECTION = r"""
JSON.stringify((() => {
  const active = document.activeElement;
  if (!(active instanceof HTMLInputElement)) return {action: 'FALLBACK'};
  if (active.id !== 'editor-password') return {action: 'FALLBACK'};
  if (
    !active.isConnected || active.disabled ||
    active.getClientRects().length === 0 ||
    getComputedStyle(active).visibility !== 'visible' ||
    !['password', 'text'].includes(active.type)
  ) return {action: 'NONE'};
  const start = active.selectionStart;
  const end = active.selectionEnd;
  if (!Number.isSafeInteger(start) || !Number.isSafeInteger(end) ||
      start < 0 || end <= start || end > active.value.length) {
    return {action: 'NONE'};
  }
  return {
    action: 'PASSWORD', start, end, valueLength: active.value.length,
    text: active.value.slice(start, end),
  };
})())
"""


class _EditorPasswordCopyFilter(QObject):
    """仅把已授权的编辑密码选区交给原生剪贴板控制器。"""

    def __init__(
        self,
        controller: "EditorWindowController",
        view: QWebEngineView,
        instance_id: str,
        copy_password: Callable[[str], bool],
    ) -> None:
        super().__init__(view)
        self._controller = controller
        self._view = view
        self._instance_id = instance_id
        self._copy_password = copy_password
        self._serial = 0
        self._pending = 0

    def invalidate(self) -> None:
        self._serial += 1
        self._pending = 0

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:  # noqa: N802
        if watched is not self._view:
            return False
        event_type = event.type()
        if event_type in {
            QEvent.Type.FocusOut,
            QEvent.Type.WindowDeactivate,
            QEvent.Type.MouseButtonPress,
        }:
            self.invalidate()
            return False
        if (
            event_type == QEvent.Type.ShortcutOverride
            and isinstance(event, QKeyEvent)
            and event.matches(QKeySequence.StandardKey.Copy)
            and self._view.hasFocus()
        ):
            event.accept()
            return False
        if event_type != QEvent.Type.KeyPress or not isinstance(event, QKeyEvent):
            return False
        if not event.matches(QKeySequence.StandardKey.Copy):
            self.invalidate()
            return False
        if event.isAutoRepeat() or not self._view.hasFocus():
            return False
        self._request_copy()
        event.accept()
        return True

    def _request_copy(self) -> None:
        if self._pending or not self._controller._copy_is_current(
            self._instance_id, self._view
        ):
            return
        self._serial += 1
        serial = self._serial
        self._pending = serial
        try:
            self._view.page().runJavaScript(
                _READ_EDITOR_PASSWORD_SELECTION,
                QWebEngineScript.ScriptWorldId.ApplicationWorld,
                lambda result: self._complete_copy(serial, result),
            )
        except Exception:
            if self._pending == serial:
                self._pending = 0

    def _complete_copy(self, serial: int, result: object) -> None:
        if self._pending == serial:
            self._pending = 0
        if isinstance(result, str):
            try:
                result = json.loads(result)
            except (ValueError, RecursionError):
                return
        try:
            if (
                serial != self._serial
                or not self._view.hasFocus()
                or not self._controller._copy_is_current(
                    self._instance_id, self._view
                )
                or not isinstance(result, dict)
            ):
                return
            if result.get("action") == "FALLBACK" and set(result) == {"action"}:
                self._view.page().triggerAction(QWebEnginePage.WebAction.Copy)
                return
            if set(result) != {
                "action", "start", "end", "valueLength", "text"
            } or result.get("action") != "PASSWORD":
                return
            start = self._integer(result.get("start"))
            end = self._integer(result.get("end"))
            length = self._integer(result.get("valueLength"))
            text = result.get("text")
            if (
                start is None
                or end is None
                or length is None
                or not (0 <= start < end <= length <= 2_147_483_647)
                or type(text) is not str
                or not text
                or "\x00" in text
                or len(text.encode("utf-16-le", errors="surrogatepass")) // 2
                != end - start
            ):
                return
            if not self._copy_password(text):
                self._view.page().runJavaScript(
                    "window.pdmEditorRuntime?.showClipboardUnavailableV1?.();"
                )
        except Exception:
            return
        finally:
            if isinstance(result, dict):
                result["text"] = ""

    @staticmethod
    def _integer(value: object) -> int | None:
        if type(value) is int:
            return value
        if (
            type(value) is float
            and math.isfinite(value)
            and value.is_integer()
            and abs(value) <= 9_007_199_254_740_991
        ):
            return int(value)
        return None


class _PassiveEditorAdapter:
    """转发业务请求，但绝不拥有或释放主页面／主会话。"""

    def __init__(self, adapter: BridgeAdapter) -> None:
        self._adapter = adapter

    def submit(
        self, request: AdapterRequest, complete: CompletionCallback
    ) -> None:
        self._adapter.submit(request, complete)

    def cancel(self, request: AdapterRequest) -> str:
        return self._adapter.cancel(request)

    def invalidate_page(self, page_epoch: int) -> None:
        del page_epoch

    def invalidate_session(self, session_epoch: int) -> None:
        del session_epoch

    def revoke_secret_lease(self, secret_lease_id: str) -> None:
        self._adapter.revoke_secret_lease(secret_lease_id)

    def discard(self, completion: AdapterCompletion) -> None:
        self._adapter.discard(completion)

    def backup_read_remaining_ms(self, read_id: str, page_epoch: int, session_epoch: int) -> int:
        return self._adapter.backup_read_remaining_ms(read_id, page_epoch, session_epoch)

    def close(self) -> None:
        return


class _EditorSecurityBoundarySink:
    """Only report cleanup complete after the editor is synchronously hidden."""

    def __init__(self, conceal: Callable[[], bool]) -> None:
        self._conceal = conceal

    def enter_boundary(
        self,
        reason: str,
        *,
        authority_serial: int,
        page_epoch: int,
        session_epoch: int,
        page_revoked: bool,
    ) -> SecurityBoundaryOutcome:
        del reason, authority_serial, page_epoch, session_epoch
        complete = page_revoked is True and self._conceal()
        return SecurityBoundaryOutcome(
            authority_revoked=True,
            complete=complete,
        )


class EditorWindow(QMainWindow):
    """一个无父、标准边框的编辑页宿主。"""

    close_requested = Signal()

    def __init__(
        self,
        view_factory: Callable[[], QWidget] = QWebEngineView,
        *, effective_theme: str = "DARK",
    ) -> None:
        super().__init__(None)
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.WindowTitleHint
            | Qt.WindowType.WindowSystemMenuHint
            | Qt.WindowType.WindowMinimizeButtonHint
            | Qt.WindowType.WindowMaximizeButtonHint
            | Qt.WindowType.WindowCloseButtonHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)
        self.setWindowTitle("编辑密码")
        self.product_titlebar = ProductTitleBar(self)
        self.product_titlebar.set_window_titles("编辑密码", "Edit password")
        self.product_titlebar.minimize_requested.connect(
            lambda: self._perform_native_control(HTMINBUTTON)
        )
        self.product_titlebar.maximize_requested.connect(
            lambda: self._perform_native_control(HTMAXBUTTON)
        )
        self.product_titlebar.close_requested.connect(
            lambda: self._perform_native_control(HTCLOSE)
        )
        self.setMenuWidget(self.product_titlebar)
        self.setCentralWidget(view_factory())
        self.setMinimumSize(360, 420)
        self.resize(480, 640)
        self.set_theme(effective_theme)
        self.view.hide()
        self._native_control_hover: int | None = None
        self._native_control_pressed: int | None = None
        if (
            sys.platform == "win32"
            and QApplication.platformName().casefold() != "offscreen"
        ):
            hwnd = int(self.winId())
            if (
                not apply_standard_window_frame(hwnd)
                or not set_win11_border_color_none(hwnd)
            ):
                raise RuntimeError("editor standard frame initialization failed")

    @property
    def view(self) -> QWidget:
        view = self.centralWidget()
        assert view is not None
        return view

    def closeEvent(self, event) -> None:  # noqa: N802
        self.close_requested.emit()
        event.ignore()

    def set_theme(self, effective_theme: str) -> None:
        color = "#f7f5ff" if effective_theme == "LIGHT" else "#111018"
        self.setStyleSheet(f"QMainWindow {{ background: {color}; }}")
        if isinstance(self.view, QWebEngineView):
            # 网页首帧之前也使用主题底色，避免默认白底参与呈现。
            page = self.view.page()
            page.setBackgroundColor(QColor(color))
            script = QWebEngineScript()
            script.setName("pdm-editor-initial-theme")
            script.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentCreation)
            script.setWorldId(QWebEngineScript.ScriptWorldId.MainWorld)
            theme = "LIGHT" if effective_theme == "LIGHT" else "DARK"
            script.setSourceCode("window.pdmEditorInitialTheme=" + json.dumps(theme) + ";")
            scripts = page.scripts()
            for previous in scripts.find(script.name()):
                scripts.remove(previous)
            scripts.insert(script)
        self.product_titlebar.set_effective_theme(effective_theme)

    def apply_title_projection(
        self,
        mode: str,
        language: str,
        ui_font_scale: str,
    ) -> None:
        titles = {
            "CREATE": ("新增密码", "Add password"),
            "EDIT": ("编辑密码", "Edit password"),
            "NOTE_CREATE": ("新增记事", "Add note"),
            "NOTE_EDIT": ("编辑记事", "Edit note"),
        }
        zh_title, en_title = titles[mode]
        self.product_titlebar.set_window_titles(
            zh_title,
            en_title,
        )
        self.product_titlebar.set_language("en" if language == "EN" else "zh")
        self.product_titlebar.set_ui_font_scale(ui_font_scale)
        self.setWindowTitle(
            en_title if language == "EN" else zh_title
        )

    def configure_mode(self, mode: str) -> None:
        if mode in {"NOTE_CREATE", "NOTE_EDIT"}:
            self.setMinimumSize(420, 360)
            self.resize(640, 560)
        else:
            self.setMinimumSize(360, 420)
            self.resize(480, 640)

    def showEvent(self, event: QShowEvent) -> None:  # noqa: N802
        super().showEvent(event)
        if sys.platform == "win32":
            set_win11_corner_preference(int(self.winId()), self.isMaximized())
        self.product_titlebar.set_maximized(self.isMaximized())

    def changeEvent(self, event: QEvent) -> None:  # noqa: N802
        super().changeEvent(event)
        if event.type() == QEvent.Type.WindowStateChange:
            self._native_control_hover = None
            self._native_control_pressed = None
            self.product_titlebar.set_control_state(None, None)
            self.product_titlebar.set_maximized(self.isMaximized())
            if sys.platform == "win32":
                set_win11_corner_preference(int(self.winId()), self.isMaximized())
        elif (
            event.type() == QEvent.Type.ActivationChange
            and not self.isActiveWindow()
        ):
            self._native_control_hover = None
            self._native_control_pressed = None
            self._project_native_controls()

    def nativeEvent(self, event_type, message):  # noqa: N802
        if (
            sys.platform == "win32"
            and bytes(event_type)
            in {b"windows_generic_MSG", b"windows_dispatcher_MSG"}
        ):
            try:
                from ctypes.wintypes import MSG

                msg = MSG.from_address(int(message))
                if msg.message == WM_NCCALCSIZE and bool(msg.wParam) and int(msg.lParam):
                    from ctypes import wintypes

                    class NCCALCSIZE_PARAMS(ctypes.Structure):
                        _fields_ = [("rgrc", wintypes.RECT * 3), ("lppos", ctypes.c_void_p)]

                    params = NCCALCSIZE_PARAMS.from_address(int(msg.lParam))
                    source = params.rgrc[0]
                    border_x, border_y = native_resize_border(int(msg.hWnd))
                    source.left, source.top, source.right, source.bottom = (
                        standard_window_frame_client_rect(
                            (int(source.left), int(source.top), int(source.right), int(source.bottom)),
                            maximized=native_window_is_maximized(int(msg.hWnd)),
                            border_x=border_x,
                            border_y=border_y,
                        )
                    )
                    return True, 0
                if msg.message == WM_NCHITTEST:
                    outer = native_window_rect(int(msg.hWnd))
                    if outer is not None:
                        x = ctypes.c_short(msg.lParam & 0xFFFF).value
                        y = ctypes.c_short((msg.lParam >> 16) & 0xFFFF).value
                        left, top, right, bottom = outer
                        scale = native_dpi_scale(int(msg.hWnd))
                        if self.isMaximized():
                            border_x, border_y = native_resize_border(int(msg.hWnd))
                            left, top, right, bottom = standard_window_frame_client_rect(
                                outer, maximized=True, border_x=border_x, border_y=border_y
                            )
                        else:
                            border_x, border_y = native_resize_border(int(msg.hWnd))
                            hit = resize_hit_test(x, y, left, top, right, bottom, border_x, border_y)
                            if hit is not None:
                                return True, hit
                        control = native_window_control_hit(x, y, left, top, right, scale)
                        if control is not None:
                            return True, control
                        controls_width = round(WINDOW_CONTROL_WIDTH * WINDOW_CONTROL_COUNT * scale)
                        if top <= y < top + round(TITLEBAR_HEIGHT * scale) and left <= x < right - controls_width:
                            return True, HTCAPTION
                if msg.message == WM_NCMOUSEMOVE:
                    hit = native_window_control_hit_at_cursor(int(msg.hWnd))
                    self._native_control_hover = hit
                    self._project_native_controls()
                    track_non_client_mouse_leave(int(msg.hWnd))
                elif msg.message == WM_NCMOUSELEAVE:
                    self._native_control_hover = None
                    self._project_native_controls()
                elif msg.message == WM_NCLBUTTONDOWN and msg.wParam in {
                    HTMINBUTTON,
                    HTMAXBUTTON,
                    HTCLOSE,
                }:
                    self._native_control_pressed = int(msg.wParam)
                    self._project_native_controls()
                    return True, 0
                elif msg.message == WM_NCLBUTTONUP and (
                    self._native_control_pressed is not None
                    or msg.wParam in {HTMINBUTTON, HTMAXBUTTON, HTCLOSE}
                ):
                    pressed = self._native_control_pressed
                    self._native_control_pressed = None
                    self._project_native_controls()
                    if pressed == int(msg.wParam):
                        self._perform_native_control(pressed)
                    return True, 0
            except Exception:
                pass
        return super().nativeEvent(event_type, message)

    def _project_native_controls(self) -> None:
        names = {
            HTMINBUTTON: "minimize",
            HTMAXBUTTON: "maximize",
            HTCLOSE: "close",
        }
        self.product_titlebar.set_control_state(
            names.get(self._native_control_hover),
            names.get(self._native_control_pressed),
        )

    def _perform_native_control(self, hit: int) -> None:
        if hit == HTMINBUTTON:
            self.showMinimized()
        elif hit == HTMAXBUTTON:
            self.showNormal() if self.isMaximized() else self.showMaximized()
        elif hit == HTCLOSE:
            self.close()

    def reveal_view(self) -> None:
        self.view.setEnabled(True)
        self.view.show()


@dataclass(frozen=True, slots=True)
class _RequestContext:
    action_id: str
    command_id: CommandId
    resource_id: str = ""
    completion: str = ""


class EditorBridge(QObject):
    """编辑页唯一可见的固定命令面。"""

    initializeCompletedV1 = Signal(str, str, str, int, int, "QVariant")
    reauthorizeCompletedV1 = Signal(str, str, str, int, int, "QVariant")
    readFieldChunkCompletedV1 = Signal(str, str, str, int, int, "QVariant")
    releaseFieldReadCompletedV1 = Signal(str, str, str, int, int, "QVariant")
    generatePasswordCompletedV1 = Signal(str, str, str, int, int, "QVariant")
    releaseSecretLeaseCompletedV1 = Signal(str, str, str, int, int, "QVariant")
    savePasswordCompletedV1 = Signal(str, str, str, int, int, "QVariant")
    createPasswordCompletedV1 = Signal(str, str, str, int, int, "QVariant")
    confirmRecoveryChangeCompletedV1 = Signal(str, str, str, bool)
    readNoteFieldChunkCompletedV1 = Signal(str, str, str, int, int, "QVariant")
    releaseNoteFieldReadCompletedV1 = Signal(str, str, str, int, int, "QVariant")
    createNoteCompletedV1 = Signal(str, str, str, int, int, "QVariant")
    saveNoteCompletedV1 = Signal(str, str, str, int, int, "QVariant")
    deleteNoteCompletedV1 = Signal(str, str, str, int, int, "QVariant")
    reloadLatestCompletedV1 = Signal(str, str, str, int, int, "QVariant")
    projectionChangedV1 = Signal(str, str, str, str, "QVariant")
    generateAfterOpenV1 = Signal(str)

    def __init__(
        self,
        catalog: ContractCatalog,
        adapter: BridgeAdapter,
        *,
        page_epoch: int,
        session_epoch: int,
        record_id: int,
        revision: str,
        mode: str,
        instance_id: str,
        generate_after_open: bool,
        sensitive_dom: SensitiveDomController | None = None,
        security_boundary_sink: object | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._catalog = catalog
        self._page_epoch = page_epoch
        self._session_epoch = session_epoch
        self._record_id = record_id
        self._revision = revision
        self._mode = mode
        self._instance_id = instance_id
        self._generate_after_open = generate_after_open
        self._sensitive_dom = sensitive_dom
        self._accepting = True
        self._contexts: dict[str, _RequestContext] = {}
        self._read_ids: set[str] = set()
        self._note_read_ids: set[str] = set()
        self._edit_lease_id = ""
        self._edit_lease_ids: set[str] = set()
        self._generated_lease_ids: set[str] = set()
        self._projection: tuple[str, str, str, object] | None = None
        self._create_initial: dict[str, object] | None = (
            ({
                "mode": "CREATE",
                "recordId": 0,
                "revision": "",
                "platform": "",
                "account": "",
                "password": "",
                "notes": "",
                "hasTotp": False,
                "recoveryCount": 0,
                "favorite": False,
                "longFields": [],
                "editLeaseId": "",
                "generatedLeaseId": "",
                "expiresInMs": 0,
            } if mode == "CREATE" else {
                "mode": "NOTE_CREATE",
                "noteId": 0,
                "revision": "",
                "title": "",
                "content": "",
                "favorite": False,
                "longFields": [],
                "updatedDate": "",
            })
            if mode in {"CREATE", "NOTE_CREATE"} else None
        )
        self._lifetime_guard = _BridgeLifetimeGuard()
        self._boundary = RequestBoundary(
            catalog,
            _PassiveEditorAdapter(adapter),
            Surface.WEBCHANNEL,
            self._on_envelope,
            adapter_completion_receiver=(
                self._lifetime_guard.queue_adapter_completion
            ),
            secret_lifecycle_sink=sensitive_dom,
            security_boundary_sink=security_boundary_sink,
        )
        self._lifetime_guard.bind_boundary(self._boundary)
        self._boundary.bind_borrowed_web_authority(page_epoch, session_epoch)
        self.destroyed.connect(self._lifetime_guard.close_boundary)
        if parent is not None:
            self.destroyed.connect(
                lambda *_unused: parent._on_bridge_destroyed(instance_id)
            )

    @property
    def boundary(self) -> RequestBoundary:
        return self._boundary

    @property
    def read_ids(self) -> frozenset[str]:
        return frozenset((*self._read_ids, *self._note_read_ids))

    def apply_settings(
        self,
        effective_theme: str,
        language: str,
        ui_font_scale: str,
        generator_options: object,
    ) -> None:
        self._projection = (
            effective_theme,
            language,
            ui_font_scale,
            generator_options,
        )
        self.projectionChangedV1.emit(
            self._instance_id,
            effective_theme,
            language,
            ui_font_scale,
            generator_options,
        )

    def _submit(
        self,
        command_id: CommandId,
        action_id: object,
        arguments: tuple[object, ...],
        *,
        resource_id: str = "",
        completion: str = "",
    ) -> dict[str, object]:
        if not self._accepting:
            return {"accepted": False, "errorCode": "STALE_PAGE"}
        if (
            type(action_id) is not str
            or not 1 <= len(action_id) <= 128
            or "\x00" in action_id
        ):
            return {"accepted": False, "errorCode": "INVALID_ARGUMENT"}
        request_id = str(uuid4())
        ack = self._boundary.submit(command_id, (request_id, *arguments))
        if ack.accepted:
            self._contexts[request_id] = _RequestContext(
                action_id, command_id, resource_id, completion
            )
            if command_id in {
                CommandId.C14,
                CommandId.C26,
                CommandId.C30,
                CommandId.C62,
                CommandId.C65,
            }:
                self.parent().set_saving(True)  # type: ignore[union-attr]
        return ack.to_wire()

    @Slot("QVariant", result="QVariantMap")
    def initializeV1(self, actionId: object) -> dict[str, object]:
        if self._mode in {"CREATE", "NOTE_CREATE"}:
            if not self._valid_action_id(actionId) or self._create_initial is None:
                return {"accepted": False, "errorCode": "INVALID_ARGUMENT"}
            result = dict(self._create_initial)
            self._create_initial = None

            def complete() -> None:
                if not self._accepting:
                    for field in ("password", "title", "content"):
                        if field in result:
                            result[field] = ""
                    return
                self.initializeCompletedV1.emit(
                    actionId,
                    self._instance_id,
                    "OK",
                    0,
                    0,
                    result,
                )
                for field in ("password", "title", "content"):
                    if field in result:
                        result[field] = ""
                if self._projection is not None:
                    self.projectionChangedV1.emit(
                        self._instance_id,
                        *self._projection,
                    )

            QTimer.singleShot(0, complete)
            return {"accepted": True, "errorCode": "OK"}
        if self._mode == "NOTE_EDIT":
            return self._submit(
                CommandId.C25,
                actionId,
                (
                    self._page_epoch,
                    self._session_epoch,
                    self._record_id,
                    self._revision,
                ),
                completion="initialize",
            )
        return self._submit(
            CommandId.C12,
            actionId,
            (self._page_epoch, self._session_epoch, self._record_id, self._revision),
            completion="initialize",
        )

    def adopt_create_prefill(self, result: dict[str, object]) -> bool:
        if self._mode != "CREATE" or self._create_initial is None:
            return False
        if not self._boundary.adopt_generated_secret_result(result):
            return False
        lease_id = result.get("secretLeaseId")
        password = result.get("password")
        expires_in_ms = result.get("expiresInMs")
        if (
            type(lease_id) is not str
            or type(password) is not str
            or type(expires_in_ms) is not int
        ):
            return False
        self._generated_lease_ids.add(lease_id)
        self._create_initial.update(
            {
                "password": password,
                "generatedLeaseId": lease_id,
                "expiresInMs": expires_in_ms,
            }
        )
        return True

    @staticmethod
    def _valid_action_id(action_id: object) -> bool:
        return bool(
            type(action_id) is str
            and 1 <= len(action_id) <= 128
            and "\x00" not in action_id
        )

    @Slot("QVariant", result="QVariantMap")
    def reauthorizeV1(self, actionId: object) -> dict[str, object]:
        if self._mode != "EDIT":
            return {"accepted": False, "errorCode": "INVALID_ARGUMENT"}
        return self._submit(
            CommandId.C12,
            actionId,
            (self._page_epoch, self._session_epoch, self._record_id, self._revision),
            completion="reauthorize",
        )

    @Slot("QVariant", result="QVariantMap")
    def reloadLatestV1(self, actionId: object) -> dict[str, object]:
        if self._mode not in {"EDIT", "NOTE_EDIT"}:
            return {"accepted": False, "errorCode": "INVALID_ARGUMENT"}
        return self.parent().request_reload(  # type: ignore[union-attr]
            actionId,
            self._instance_id,
        )

    def reload_from_revision(
        self,
        action_id: str,
        revision: str,
    ) -> dict[str, object]:
        return self._submit(
            CommandId.C25 if self._mode == "NOTE_EDIT" else CommandId.C12,
            action_id,
            (self._page_epoch, self._session_epoch, self._record_id, revision),
            completion="reload",
        )

    def emit_reload_failure(self, action_id: str, error_code: str) -> None:
        self.reloadLatestCompletedV1.emit(
            action_id,
            self._instance_id,
            error_code,
            0,
            0,
            {},
        )

    def emit_note_delete_failure(
        self,
        action_id: str,
        error_code: str,
    ) -> None:
        self.deleteNoteCompletedV1.emit(
            action_id,
            self._instance_id,
            error_code,
            0,
            0,
            {},
        )

    @Slot("QVariant", "QVariant", "QVariant", "QVariant", result="QVariantMap")
    def readFieldChunkV1(
        self, actionId: object, field: object, readId: object, offset: object
    ) -> dict[str, object]:
        if self._mode != "EDIT":
            return {"accepted": False, "errorCode": "INVALID_ARGUMENT"}
        return self._submit(
            CommandId.C60,
            actionId,
            (
                self._page_epoch,
                self._session_epoch,
                self._record_id,
                self._revision,
                field,
                self._edit_lease_id,
                readId,
                offset,
            ),
        )

    @Slot("QVariant", "QVariant", result="QVariantMap")
    def releaseFieldReadV1(
        self, actionId: object, readId: object
    ) -> dict[str, object]:
        return self._submit(
            CommandId.C61,
            actionId,
            (self._page_epoch, self._session_epoch, readId),
            resource_id=readId if isinstance(readId, str) else "",
        )

    @Slot("QVariant", "QVariant", "QVariant", "QVariant", result="QVariantMap")
    def readNoteFieldChunkV1(
        self,
        actionId: object,
        field: object,
        readId: object,
        offset: object,
    ) -> dict[str, object]:
        if self._mode != "NOTE_EDIT":
            return {"accepted": False, "errorCode": "INVALID_ARGUMENT"}
        return self._submit(
            CommandId.C63,
            actionId,
            (
                self._page_epoch,
                self._session_epoch,
                self._record_id,
                self._revision,
                field,
                readId,
                offset,
            ),
        )

    @Slot("QVariant", "QVariant", result="QVariantMap")
    def releaseNoteFieldReadV1(
        self,
        actionId: object,
        readId: object,
    ) -> dict[str, object]:
        if self._mode != "NOTE_EDIT":
            return {"accepted": False, "errorCode": "INVALID_ARGUMENT"}
        return self._submit(
            CommandId.C64,
            actionId,
            (self._page_epoch, self._session_epoch, readId),
            resource_id=readId if isinstance(readId, str) else "",
        )

    @Slot(
        "QVariant", "QVariant", "QVariant", "QVariant", "QVariant", "QVariant", "QVariant",
        result="QVariantMap",
    )
    def generatePasswordV1(
        self,
        actionId: object,
        length: object,
        lower: object,
        upper: object,
        digits: object,
        symbols: object,
        avoidAmbiguous: object,
    ) -> dict[str, object]:
        return self._submit(
            CommandId.C33,
            actionId,
            (self._page_epoch, length, lower, upper, digits, symbols, avoidAmbiguous),
        )

    @Slot("QVariant", "QVariant", result="QVariantMap")
    def releaseSecretLeaseV1(
        self, actionId: object, leaseId: object
    ) -> dict[str, object]:
        if type(leaseId) is not str or leaseId not in {
            *self._edit_lease_ids,
            *self._generated_lease_ids,
        }:
            return {"accepted": False, "errorCode": "SECRET_LEASE_EXPIRED"}
        return self._submit(
            CommandId.C08,
            actionId,
            (self._page_epoch, leaseId),
            resource_id=leaseId,
        )

    @Slot("QVariant", "QVariant", "QVariant", "QVariant", "QVariant", "QVariant", "QVariant", "QVariant", "QVariant", "QVariant", "QVariant", "QVariant", "QVariant", "QVariant", result="QVariantMap")
    def savePasswordV1(
        self,
        actionId: object,
        platformAction: object,
        platform: object,
        accountAction: object,
        account: object,
        passwordAction: object,
        password: object,
        notesAction: object,
        notes: object,
        totpAction: object,
        totpSecret: object,
        favorite: object,
        recoveryAction: object = "KEEP",
        recoveryText: object = "",
    ) -> dict[str, object]:
        if self._mode != "EDIT":
            return {"accepted": False, "errorCode": "INVALID_ARGUMENT"}
        return self._submit(
            CommandId.C62,
            actionId,
            (
                self._page_epoch,
                self._session_epoch,
                self._record_id,
                self._revision,
                self._edit_lease_id,
                platformAction,
                platform,
                accountAction,
                account,
                passwordAction,
                password,
                notesAction,
                notes,
                totpAction,
                totpSecret,
                favorite,
                recoveryAction,
                recoveryText,
            ),
        )

    @Slot("QVariant", "QVariant", "QVariant", "QVariant", "QVariant", "QVariant", "QVariant", "QVariant", "QVariant", result="QVariantMap")
    def createPasswordV1(
        self,
        actionId: object,
        platform: object,
        account: object,
        password: object,
        notes: object,
        totpAction: object,
        totpSecret: object,
        favorite: object,
        recoveryText: object = "",
    ) -> dict[str, object]:
        if self._mode != "CREATE":
            return {"accepted": False, "errorCode": "INVALID_ARGUMENT"}
        return self._submit(
            CommandId.C14,
            actionId,
            (
                self._page_epoch,
                self._session_epoch,
                platform,
                account,
                password,
                notes,
                totpAction,
                totpSecret,
                favorite,
                recoveryText,
            ),
        )

    @Slot("QVariant", "QVariant", result="QVariantMap")
    def confirmRecoveryChangeV1(self, actionId: object, remove: object) -> dict[str, object]:
        """确认只绑定当前编辑实例，不携带码值或其他记录身份。"""
        if not self._accepting or self._mode != "EDIT":
            return {"accepted": False, "errorCode": "STALE_PAGE"}
        if type(actionId) is not str or not 1 <= len(actionId) <= 128 or type(remove) is not bool:
            return {"accepted": False, "errorCode": "INVALID_ARGUMENT"}
        return self.parent().request_recovery_change(actionId, remove)

    def emit_recovery_confirmation(self, action_id: str, code: str, confirmed: bool) -> None:
        if self._accepting:
            self.confirmRecoveryChangeCompletedV1.emit(action_id, self._instance_id, code, confirmed)

    @Slot(
        "QVariant", "QVariant", "QVariant", "QVariant",
        result="QVariantMap",
    )
    def createNoteV1(
        self,
        actionId: object,
        title: object,
        content: object,
        favorite: object,
    ) -> dict[str, object]:
        if self._mode != "NOTE_CREATE":
            return {"accepted": False, "errorCode": "INVALID_ARGUMENT"}
        return self._submit(
            CommandId.C26,
            actionId,
            (
                self._page_epoch,
                self._session_epoch,
                title,
                content,
                favorite,
            ),
        )

    @Slot(
        "QVariant", "QVariant", "QVariant", "QVariant", "QVariant", "QVariant",
        result="QVariantMap",
    )
    def saveNoteV1(
        self,
        actionId: object,
        titleAction: object,
        title: object,
        contentAction: object,
        content: object,
        favorite: object,
    ) -> dict[str, object]:
        if self._mode != "NOTE_EDIT":
            return {"accepted": False, "errorCode": "INVALID_ARGUMENT"}
        return self._submit(
            CommandId.C65,
            actionId,
            (
                self._page_epoch,
                self._session_epoch,
                self._record_id,
                self._revision,
                titleAction,
                title,
                contentAction,
                content,
                favorite,
            ),
        )

    @Slot("QVariant", "QVariant", result="QVariantMap")
    def requestDeleteNoteV1(
        self,
        actionId: object,
        entityLabel: object,
    ) -> dict[str, object]:
        if self._mode != "NOTE_EDIT":
            return {"accepted": False, "errorCode": "INVALID_ARGUMENT"}
        return self.parent().request_note_delete(  # type: ignore[union-attr]
            actionId,
            self._instance_id,
            entityLabel,
        )

    def prepare_note_delete(self, action_id: str) -> dict[str, object]:
        return self._submit(
            CommandId.C29,
            action_id,
            (
                self._page_epoch,
                self._session_epoch,
                self._record_id,
                self._revision,
            ),
            completion="delete_prepare",
        )

    @Slot("QVariant")
    def setDirtyV1(self, dirty: object) -> None:
        if type(dirty) is bool:
            self.parent().set_dirty(dirty)  # type: ignore[union-attr]

    @Slot()
    def requestCloseV1(self) -> None:
        self.parent().request_close()  # type: ignore[union-attr]

    @Slot()
    def presentReadyV1(self) -> None:
        self.parent().editor_ready(self._instance_id)  # type: ignore[union-attr]

    @Slot()
    def securityFailureV1(self) -> None:
        self.parent().editor_security_failure(self._instance_id)  # type: ignore[union-attr]

    def close_instance(self, clear_reason: str = "bridge_close") -> bool:
        """停止本实例；C61 先于边界关闭以释放已交付的长字段读取。"""

        if not self._accepting:
            return self._boundary.close("bridge_close")
        self._accepting = False
        for read_id in tuple(self._read_ids):
            self._submit_release(read_id)
        for read_id in tuple(self._note_read_ids):
            self._submit_note_release(read_id)
        self._contexts.clear()
        self._read_ids.clear()
        self._note_read_ids.clear()
        self._edit_lease_id = ""
        self._edit_lease_ids.clear()
        self._generated_lease_ids.clear()
        if self._create_initial is not None:
            for field in ("password", "title", "content"):
                if field in self._create_initial:
                    self._create_initial[field] = ""
            self._create_initial = None
        if self._sensitive_dom is not None:
            self._sensitive_dom.clear_all(clear_reason)
        return self._boundary.close("bridge_close")

    def _submit_release(self, read_id: str) -> None:
        request_id = str(uuid4())
        self._boundary.submit(
            CommandId.C61,
            (request_id, self._page_epoch, self._session_epoch, read_id),
        )

    def _submit_note_release(self, read_id: str) -> None:
        request_id = str(uuid4())
        self._boundary.submit(
            CommandId.C64,
            (request_id, self._page_epoch, self._session_epoch, read_id),
        )

    def _on_envelope(self, envelope: CompletionEnvelope) -> None:
        context = self._contexts.pop(envelope.request_id, None)
        if context is None or not self._boundary.authorize_envelope_delivery(envelope):
            return
        result = envelope.result or {}
        if envelope.command_id is CommandId.C12:
            result["mode"] = "EDIT"
            result["generatedLeaseId"] = ""
        elif envelope.command_id is CommandId.C25:
            result["mode"] = "NOTE_EDIT"
        if envelope.command_id is CommandId.C29:
            values = (
                context.action_id,
                self._instance_id,
                envelope.error_code,
                envelope.error_argument_index,
                envelope.retry_after_ms,
                result,
            )
            delivered = self._boundary.mark_envelope_delivered(envelope)
            if envelope.error_code != "OK" or not delivered:
                self.deleteNoteCompletedV1.emit(*values)
                self.parent().note_delete_completed(  # type: ignore[union-attr]
                    envelope.error_code
                )
                return
            ticket = result.get("deleteTicket")
            result.clear()
            ack = self._submit(
                CommandId.C30,
                context.action_id,
                (self._page_epoch, self._session_epoch, ticket),
                completion="delete_commit",
            )
            if ack.get("accepted") is not True:
                code = str(ack.get("errorCode") or "INTERNAL_FAILURE")
                self.deleteNoteCompletedV1.emit(
                    context.action_id,
                    self._instance_id,
                    code,
                    0,
                    0,
                    {},
                )
                self.parent().note_delete_completed(code)  # type: ignore[union-attr]
            return
        if envelope.error_code == "OK":
            if envelope.command_id is CommandId.C12:
                lease_id = result.get("editLeaseId")
                if isinstance(lease_id, str):
                    self._edit_lease_id = lease_id
                    self._edit_lease_ids.add(lease_id)
            elif envelope.command_id is CommandId.C60:
                read_id = result.get("readId")
                if isinstance(read_id, str):
                    self._read_ids.add(read_id)
            elif envelope.command_id is CommandId.C63:
                read_id = result.get("readId")
                if isinstance(read_id, str):
                    self._note_read_ids.add(read_id)
            elif envelope.command_id is CommandId.C33:
                lease_id = result.get("secretLeaseId")
                if isinstance(lease_id, str):
                    self._generated_lease_ids.add(lease_id)
            elif envelope.command_id is CommandId.C61:
                self._read_ids.discard(context.resource_id)
            elif envelope.command_id is CommandId.C64:
                self._note_read_ids.discard(context.resource_id)
            elif envelope.command_id is CommandId.C08:
                if context.resource_id == self._edit_lease_id:
                    self._edit_lease_id = ""
                self._edit_lease_ids.discard(context.resource_id)
                self._generated_lease_ids.discard(context.resource_id)
            elif envelope.command_id is CommandId.C65:
                item = result.get("item")
                revision = item.get("revision") if isinstance(item, dict) else None
                if isinstance(revision, str):
                    self._revision = revision
                    self.parent().set_revision(revision)  # type: ignore[union-attr]
            if (
                envelope.command_id in {CommandId.C12, CommandId.C25}
                and context.completion == "reload"
            ):
                revision = result.get("revision")
                if isinstance(revision, str):
                    self._revision = revision
                    self.parent().set_revision(revision)  # type: ignore[union-attr]
        if envelope.command_id is CommandId.C62:
            self._edit_lease_id = ""
        values = (
            context.action_id,
            self._instance_id,
            envelope.error_code,
            envelope.error_argument_index,
            envelope.retry_after_ms,
            result,
        )
        if context.command_id in {CommandId.C12, CommandId.C25}:
            {
                "reauthorize": self.reauthorizeCompletedV1,
                "reload": self.reloadLatestCompletedV1,
            }.get(context.completion, self.initializeCompletedV1).emit(*values)
        else:
            {
            CommandId.C60: self.readFieldChunkCompletedV1,
            CommandId.C61: self.releaseFieldReadCompletedV1,
            CommandId.C33: self.generatePasswordCompletedV1,
            CommandId.C08: self.releaseSecretLeaseCompletedV1,
            CommandId.C62: self.savePasswordCompletedV1,
            CommandId.C14: self.createPasswordCompletedV1,
            CommandId.C63: self.readNoteFieldChunkCompletedV1,
            CommandId.C64: self.releaseNoteFieldReadCompletedV1,
            CommandId.C26: self.createNoteCompletedV1,
            CommandId.C65: self.saveNoteCompletedV1,
            CommandId.C30: self.deleteNoteCompletedV1,
            }[context.command_id].emit(*values)
        delivered = self._boundary.mark_envelope_delivered(envelope)
        if (
            context.command_id in {CommandId.C12, CommandId.C25}
            and context.completion == "initialize"
            and envelope.error_code == "OK"
            and delivered
            and self._projection is not None
        ):
            self.projectionChangedV1.emit(
                self._instance_id,
                *self._projection,
            )
        if (
            context.command_id is CommandId.C12
            and envelope.error_code == "OK"
            and delivered
            and self._generate_after_open
        ):
            self._generate_after_open = False
            self.generateAfterOpenV1.emit(self._instance_id)
        if context.command_id in {CommandId.C14, CommandId.C62}:
            self.parent().save_completed(envelope.error_code)  # type: ignore[union-attr]
        elif context.command_id in {CommandId.C26, CommandId.C65}:
            self.parent().note_save_completed(envelope.error_code)  # type: ignore[union-attr]
        elif context.command_id is CommandId.C30:
            self.parent().note_delete_completed(envelope.error_code)  # type: ignore[union-attr]


class EditorWindowController(QObject):
    """主页面启动器与一个编辑实例的生命周期拥有者。"""

    editorFinishedV1 = Signal(str, str, str, int, str)
    _editorRevisionResolved = Signal(str, str, str, str)

    def __init__(
        self,
        catalog: ContractCatalog,
        adapter: BridgeAdapter,
        *,
        authority: Callable[[], tuple[int, int]],
        renderer_failed: Callable[[], None],
        copy_password: Callable[[str], bool],
        clone_generated_prefill: (
            Callable[[str, int], dict[str, object] | None] | None
        ) = None,
        view_factory: Callable[[], QWidget] = QWebEngineView,
        note_view_factory: Callable[[], QWidget] | None = None,
        confirm_discard: Callable[[QWidget], bool] | None = None,
        confirm_reload: Callable[[QWidget], bool] | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._catalog = catalog
        self._adapter = adapter
        self._authority = authority
        self._renderer_failed = renderer_failed
        self._copy_password = copy_password
        self._clone_generated_prefill = clone_generated_prefill
        self._view_factory = view_factory
        self._note_view_factory = note_view_factory or view_factory
        self._confirm_discard = confirm_discard
        self._confirm_reload = confirm_reload
        self._window: EditorWindow | None = None
        self._bridge: EditorBridge | None = None
        self._intent_id = ""
        self._instance_id = ""
        self._record_id = 0
        self._revision = ""
        self._mode = "EDIT"
        self._dirty = False
        self._saving = False
        self._projection = ("DARK", "ZH", "100", {})
        self._channel: QWebChannel | None = None
        self._sensitive_dom: SensitiveDomController | None = None
        self._copy_filter: _EditorPasswordCopyFilter | None = None
        self._last_geometry: dict[str, QRect] = {}
        self._close_check_serial = 0
        self._close_check_pending = False
        self._retiring_instance_id = ""
        self._reload_pending_action = ""
        self._delete_pending_action = ""
        self._delete_entity_label = ""
        self._confirmation: EditorConfirmationDialog | None = None
        self._confirmation_token = ""
        self._recovery_pending_action = ""
        self.launcher = EditorLauncherBridge(self, self)
        self._editorRevisionResolved.connect(
            self._complete_reload_revision,
            Qt.ConnectionType.QueuedConnection,
        )

    @property
    def instance_id(self) -> str:
        return self._instance_id

    @property
    def bridge(self) -> EditorBridge | None:
        return self._bridge

    @property
    def mode(self) -> str:
        return self._mode

    @Slot("QVariant", "QVariant", "QVariant", "QVariant", result="QVariantMap")
    def openPasswordEditorV1(
        self,
        intentId: object,
        recordId: object,
        revision: object,
        generateAfterOpen: object,
    ) -> dict[str, object]:
        try:
            self._catalog.validate_value("EntityId", recordId)
            self._catalog.validate_value("Revision", revision)
        except ValueRejected:
            return self._open_error("INVALID_ARGUMENT")
        if type(generateAfterOpen) is not bool:
            return self._open_error("INVALID_ARGUMENT")
        return self._open_editor_window(
            intentId,
            mode="EDIT",
            record_id=recordId,
            revision=revision,
            generate_after_open=generateAfterOpen,
            source_lease_id="",
        )

    @Slot("QVariant", "QVariant", result="QVariantMap")
    def openPasswordCreatorV1(
        self,
        intentId: object,
        sourceLeaseId: object,
    ) -> dict[str, object]:
        if type(sourceLeaseId) is not str:
            return self._open_error("INVALID_ARGUMENT")
        if sourceLeaseId:
            try:
                self._catalog.validate_value("OpaqueId", sourceLeaseId)
            except ValueRejected:
                return self._open_error("INVALID_ARGUMENT")
        return self._open_editor_window(
            intentId,
            mode="CREATE",
            record_id=0,
            revision="",
            generate_after_open=False,
            source_lease_id=sourceLeaseId,
        )

    @Slot("QVariant", result="QVariantMap")
    def openNoteCreatorV1(self, intentId: object) -> dict[str, object]:
        return self._open_editor_window(
            intentId,
            mode="NOTE_CREATE",
            record_id=0,
            revision="",
            generate_after_open=False,
            source_lease_id="",
        )

    @Slot("QVariant", "QVariant", "QVariant", result="QVariantMap")
    def openNoteEditorV1(
        self,
        intentId: object,
        noteId: object,
        revision: object,
    ) -> dict[str, object]:
        try:
            self._catalog.validate_value("EntityId", noteId)
            self._catalog.validate_value("Revision", revision)
        except ValueRejected:
            return self._open_error("INVALID_ARGUMENT")
        return self._open_editor_window(
            intentId,
            mode="NOTE_EDIT",
            record_id=noteId,
            revision=revision,
            generate_after_open=False,
            source_lease_id="",
        )

    @staticmethod
    def _open_error(error_code: str) -> dict[str, object]:
        return {
            "accepted": False,
            "errorCode": error_code,
            "status": "OPENING",
            "instanceId": "",
        }

    def _focus_existing(self) -> dict[str, object]:
        window = self._window
        assert window is not None
        if window.isMinimized():
            window.showNormal()
        else:
            window.show()
        window.raise_()
        window.activateWindow()
        return {
            "accepted": True,
            "errorCode": "OK",
            "status": "FOCUSED_EXISTING",
            "instanceId": self._instance_id,
        }

    def _open_editor_window(
        self,
        intent_id: object,
        *,
        mode: str,
        record_id: int,
        revision: str,
        generate_after_open: bool,
        source_lease_id: str,
    ) -> dict[str, object]:
        if self._window is not None:
            return self._focus_existing()
        if (
            type(intent_id) is not str
            or not 1 <= len(intent_id) <= 128
            or "\x00" in intent_id
            or mode not in {"CREATE", "EDIT", "NOTE_CREATE", "NOTE_EDIT"}
        ):
            return self._open_error("INVALID_ARGUMENT")
        page_epoch, session_epoch = self._authority()
        if page_epoch <= 0 or session_epoch <= 0:
            return self._open_error("STALE_SESSION")
        prefill: dict[str, object] | None = None
        if source_lease_id:
            clone = self._clone_generated_prefill
            if clone is None:
                return self._open_error("SECRET_LEASE_EXPIRED")
            try:
                prefill = clone(source_lease_id, page_epoch)
            except Exception:
                prefill = None
            if prefill is None:
                return self._open_error("SECRET_LEASE_EXPIRED")
        instance_id = str(uuid4())
        if not self._adapter.claim_editor(
            instance_id,
            {
                "EDIT": "PASSWORD",
                "CREATE": "PASSWORD_CREATE",
                "NOTE_EDIT": "NOTE",
                "NOTE_CREATE": "NOTE_CREATE",
            }[mode],
            record_id,
            session_epoch,
        ):
            if prefill is not None:
                self._adapter.revoke_secret_lease(
                    str(prefill.get("secretLeaseId", ""))
                )
                prefill["password"] = ""
            return self._open_error("REQUEST_BUSY")
        try:
            view_factory = (
                self._note_view_factory
                if mode in {"NOTE_CREATE", "NOTE_EDIT"}
                else self._view_factory
            )
            window = EditorWindow(view_factory, effective_theme=self._projection[0])
            window.configure_mode(mode)
            view = window.view
            sensitive_dom = None
            channel = None
            if isinstance(view, QWebEngineView):
                page = view.page()
                sensitive_dom = SensitiveDomController(page)
                channel = QWebChannel(window)
            bridge = EditorBridge(
                self._catalog,
                self._adapter,
                page_epoch=page_epoch,
                session_epoch=session_epoch,
                record_id=record_id,
                revision=revision,
                mode=mode,
                instance_id=instance_id,
                generate_after_open=generate_after_open,
                sensitive_dom=sensitive_dom,
                security_boundary_sink=_EditorSecurityBoundarySink(
                    lambda: self._conceal_for_boundary(window)
                ),
                parent=self,
            )
            if prefill is not None and not bridge.adopt_create_prefill(prefill):
                raise RuntimeError("generated prefill adoption failed")
            if channel is not None:
                channel.registerObject("pdmEditorV1", bridge)
                view.page().setWebChannel(channel)
                view.page().renderProcessTerminated.connect(
                    self._on_renderer_failed
                )
                view.loadFinished.connect(self._on_editor_load_finished)
                view.setUrl(
                    QUrl(
                        "pdm://app/note-editor.html"
                        if mode in {"NOTE_CREATE", "NOTE_EDIT"}
                        else "pdm://app/editor.html"
                    )
                )
        except Exception:
            if prefill is not None:
                self._adapter.revoke_secret_lease(
                    str(prefill.get("secretLeaseId", ""))
                )
                prefill["password"] = ""
            self._adapter.release_editor(instance_id)
            return self._open_error("INTERNAL_FAILURE")
        if prefill is not None:
            prefill["password"] = ""
        self._window = window
        self._bridge = bridge
        self._channel = channel
        self._sensitive_dom = sensitive_dom
        if isinstance(window.view, QWebEngineView):
            self._copy_filter = _EditorPasswordCopyFilter(
                self,
                window.view,
                instance_id,
                self._copy_password,
            )
            window.view.installEventFilter(self._copy_filter)
        self._intent_id = intent_id
        self._instance_id = instance_id
        self._record_id = record_id
        self._revision = revision
        self._mode = mode
        confirmation = EditorConfirmationDialog(window)
        confirmation.confirmed.connect(self._on_confirmation_confirmed)
        confirmation.cancelled.connect(self._on_confirmation_cancelled)
        self._confirmation = confirmation
        window.close_requested.connect(self.request_close)
        window.apply_title_projection(
            mode,
            self._projection[1],
            self._projection[2],
        )
        bridge.apply_settings(*self._projection)
        self._place_window(window)
        window.show()
        return {
            "accepted": True,
            "errorCode": "OK",
            "status": "OPENING",
            "instanceId": self._instance_id,
        }

    def set_dirty(self, dirty: bool) -> None:
        self._dirty = dirty

    def set_revision(self, revision: str) -> None:
        self._revision = revision

    def request_reload(
        self,
        action_id: object,
        instance_id: str,
    ) -> dict[str, object]:
        bridge, window = self._bridge, self._window
        if (
            bridge is None
            or window is None
            or instance_id != self._instance_id
            or type(action_id) is not str
            or not 1 <= len(action_id) <= 128
            or "\x00" in action_id
        ):
            return {"accepted": False, "errorCode": "INVALID_ARGUMENT"}
        if self._saving or self._reload_pending_action:
            return {"accepted": False, "errorCode": "REQUEST_BUSY"}
        if self._confirm_reload is not None:
            if not self._confirm_reload(window):
                bridge.emit_reload_failure(action_id, "CANCELLED")
                return {"accepted": True, "errorCode": "OK"}
            self._reload_pending_action = action_id
            self._begin_reload_resolution()
            return {"accepted": True, "errorCode": "OK"}
        self._reload_pending_action = action_id
        self._present_confirmation(EditorConfirmationKind.RELOAD)
        return {"accepted": True, "errorCode": "OK"}

    def _begin_reload_resolution(self) -> None:
        bridge = self._bridge
        action_id = self._reload_pending_action
        if bridge is None or not action_id:
            return
        resolver = getattr(self._adapter, "resolve_editor_revision", None)
        if not callable(resolver):
            self._reload_pending_action = ""
            bridge.emit_reload_failure(action_id, "INTERNAL_FAILURE")
            return
        try:
            resolver(
                self._instance_id,
                bridge._page_epoch,
                bridge._session_epoch,
                bridge._record_id,
                lambda code, revision: self._editorRevisionResolved.emit(
                    self._instance_id,
                    action_id,
                    code,
                    revision,
                ),
                kind="NOTE" if self._mode == "NOTE_EDIT" else "PASSWORD",
            )
        except Exception:
            self._reload_pending_action = ""
            bridge.emit_reload_failure(action_id, "INTERNAL_FAILURE")

    @Slot(str, str, str, str)
    def _complete_reload_revision(
        self,
        instance_id: str,
        action_id: str,
        error_code: str,
        revision: str,
    ) -> None:
        bridge = self._bridge
        if (
            bridge is None
            or instance_id != self._instance_id
            or action_id != self._reload_pending_action
        ):
            return
        self._reload_pending_action = ""
        if error_code != "OK":
            bridge.emit_reload_failure(action_id, error_code)
            return
        try:
            self._catalog.validate_value("Revision", revision)
        except ValueRejected:
            bridge.emit_reload_failure(action_id, "INTERNAL_FAILURE")
            return
        ack = bridge.reload_from_revision(action_id, revision)
        if ack.get("accepted") is not True:
            bridge.emit_reload_failure(
                action_id,
                str(ack.get("errorCode") or "INTERNAL_FAILURE"),
            )

    def set_saving(self, saving: bool) -> None:
        self._saving = saving

    def save_completed(self, error_code: str) -> None:
        self._saving = False
        if error_code == "OK" and not self.close_instance("SAVED"):
            self._renderer_failed()

    def note_save_completed(self, error_code: str) -> None:
        self._saving = False
        if error_code == "OK" and not self.close_instance("SAVED"):
            self._renderer_failed()

    def note_delete_completed(self, error_code: str) -> None:
        self._saving = False
        self._delete_pending_action = ""
        self._delete_entity_label = ""
        if error_code == "OK" and not self.close_instance("DELETED"):
            self._renderer_failed()

    def request_note_delete(
        self,
        action_id: object,
        instance_id: str,
        entity_label: object,
    ) -> dict[str, object]:
        if (
            self._mode != "NOTE_EDIT"
            or self._bridge is None
            or self._window is None
            or instance_id != self._instance_id
            or not EditorBridge._valid_action_id(action_id)
            or type(entity_label) is not str
            or not entity_label.strip()
            or "\x00" in entity_label
            or len(entity_label) > 8192
            or len(entity_label.encode("utf-8")) > 32768
        ):
            return {"accepted": False, "errorCode": "INVALID_ARGUMENT"}
        if self._saving or self._confirmation_token or self._delete_pending_action:
            return {"accepted": False, "errorCode": "REQUEST_BUSY"}
        self._delete_pending_action = str(action_id)
        self._delete_entity_label = entity_label
        self._present_confirmation(EditorConfirmationKind.DELETE_NOTE)
        return {"accepted": True, "errorCode": "OK"}

    def apply_settings(
        self,
        effective_theme: str,
        language: str,
        ui_font_scale: str,
        generator_options: object,
    ) -> None:
        self._projection = (
            effective_theme,
            language,
            ui_font_scale,
            generator_options,
        )
        if self._window is not None:
            self._window.set_theme(effective_theme)
            self._window.apply_title_projection(
                self._mode,
                language,
                ui_font_scale,
            )
        if self._confirmation is not None:
            self._confirmation.apply_projection(
                language,
                effective_theme,
                ui_font_scale,
            )
        if self._bridge is not None:
            self._bridge.apply_settings(*self._projection)

    def request_close(self) -> None:
        if self._saving or self._close_check_pending or self._confirmation_token:
            return
        window = self._window
        if window is None:
            return
        view = window.view
        if not isinstance(view, QWebEngineView):
            self._settle_close_check(self._dirty)
            return
        self._close_check_serial += 1
        serial = self._close_check_serial
        self._close_check_pending = True
        try:
            view.page().runJavaScript(
                (
                    "Boolean(window.pdmNoteEditorRuntime?.stateV1?.().dirty)"
                    if self._mode in {"NOTE_CREATE", "NOTE_EDIT"}
                    else "Boolean(window.pdmEditorRuntime?.stateV1?.().dirty)"
                ),
                QWebEngineScript.ScriptWorldId.MainWorld,
                lambda result: self._complete_close_check(serial, result),
            )
        except Exception:
            self._close_check_pending = False

    def _complete_close_check(self, serial: int, result: object) -> None:
        if (
            not self._close_check_pending
            or serial != self._close_check_serial
            or self._window is None
        ):
            return
        self._close_check_pending = False
        self._settle_close_check(
            result if type(result) is bool else True
        )

    def _settle_close_check(self, dirty: bool) -> None:
        window = self._window
        if window is None:
            return
        if dirty:
            if self._confirm_discard is not None:
                if not self._confirm_discard(window):
                    return
            else:
                self._present_confirmation(EditorConfirmationKind.DISCARD)
                return
        if not self.close_instance("DISCARDED"):
            self._renderer_failed()

    def request_recovery_change(self, action_id: str, remove: bool) -> dict[str, object]:
        """沿用当前实例的主题确认框，默认取消并拒绝重复请求。"""
        if self._window is None or self._bridge is None or self._mode != "EDIT":
            return {"accepted": False, "errorCode": "STALE_PAGE"}
        if self._saving or self._confirmation_token or self._recovery_pending_action:
            return {"accepted": False, "errorCode": "REQUEST_BUSY"}
        self._recovery_pending_action = action_id
        self._present_confirmation(
            EditorConfirmationKind.CLEAR_RECOVERY if remove else EditorConfirmationKind.REPLACE_RECOVERY,
        )
        return {"accepted": True, "errorCode": "OK"}

    def _finish_recovery_confirmation(self, code: str, confirmed: bool) -> None:
        action_id = self._recovery_pending_action
        self._recovery_pending_action = ""
        if self._bridge is not None and action_id:
            self._bridge.emit_recovery_confirmation(action_id, code, confirmed)

    def _present_confirmation(self, kind: EditorConfirmationKind) -> None:
        confirmation = self._confirmation
        if confirmation is None:
            if kind in {EditorConfirmationKind.REPLACE_RECOVERY, EditorConfirmationKind.CLEAR_RECOVERY}:
                self._finish_recovery_confirmation("INTERNAL_FAILURE", False)
            if kind is EditorConfirmationKind.RELOAD:
                action_id = self._reload_pending_action
                self._reload_pending_action = ""
                if self._bridge is not None and action_id:
                    self._bridge.emit_reload_failure(
                        action_id,
                        "INTERNAL_FAILURE",
                    )
            elif kind is EditorConfirmationKind.DELETE_NOTE:
                action_id = self._delete_pending_action
                self._delete_pending_action = ""
                self._delete_entity_label = ""
                if self._bridge is not None and action_id:
                    self._bridge.emit_note_delete_failure(
                        action_id,
                        "INTERNAL_FAILURE",
                    )
            return
        try:
            self._confirmation_token = confirmation.present(
                kind,
                language=self._projection[1],
                effective_theme=self._projection[0],
                ui_font_scale=self._projection[2],
                entity_label=(
                    self._delete_entity_label
                    if kind is EditorConfirmationKind.DELETE_NOTE
                    else ""
                ),
            )
        except Exception:
            self._confirmation_token = ""
            if kind in {EditorConfirmationKind.REPLACE_RECOVERY, EditorConfirmationKind.CLEAR_RECOVERY}:
                self._finish_recovery_confirmation("INTERNAL_FAILURE", False)
            if kind is EditorConfirmationKind.RELOAD:
                action_id = self._reload_pending_action
                self._reload_pending_action = ""
                if self._bridge is not None and action_id:
                    self._bridge.emit_reload_failure(
                        action_id,
                        "INTERNAL_FAILURE",
                    )
            elif kind is EditorConfirmationKind.DELETE_NOTE:
                action_id = self._delete_pending_action
                self._delete_pending_action = ""
                self._delete_entity_label = ""
                if self._bridge is not None and action_id:
                    self._bridge.emit_note_delete_failure(
                        action_id,
                        "INTERNAL_FAILURE",
                    )

    @Slot(str, str)
    def _on_confirmation_confirmed(self, token: str, kind: str) -> None:
        if token != self._confirmation_token:
            return
        self._confirmation_token = ""
        if kind in {EditorConfirmationKind.REPLACE_RECOVERY.value, EditorConfirmationKind.CLEAR_RECOVERY.value}:
            self._finish_recovery_confirmation("OK", True)
        elif kind == EditorConfirmationKind.DISCARD.value:
            if not self.close_instance("DISCARDED"):
                self._renderer_failed()
        elif kind == EditorConfirmationKind.RELOAD.value:
            self._begin_reload_resolution()
        elif kind == EditorConfirmationKind.DELETE_NOTE.value:
            bridge = self._bridge
            action_id = self._delete_pending_action
            if bridge is None or not action_id:
                return
            self._saving = True
            ack = bridge.prepare_note_delete(action_id)
            if ack.get("accepted") is not True:
                code = str(ack.get("errorCode") or "INTERNAL_FAILURE")
                self.note_delete_completed(code)
                bridge.emit_note_delete_failure(action_id, code)

    @Slot(str, str)
    def _on_confirmation_cancelled(self, token: str, kind: str) -> None:
        if token != self._confirmation_token:
            return
        self._confirmation_token = ""
        if kind in {EditorConfirmationKind.REPLACE_RECOVERY.value, EditorConfirmationKind.CLEAR_RECOVERY.value}:
            self._finish_recovery_confirmation("CANCELLED", False)
        elif kind == EditorConfirmationKind.RELOAD.value:
            action_id = self._reload_pending_action
            self._reload_pending_action = ""
            if self._bridge is not None and action_id:
                self._bridge.emit_reload_failure(action_id, "CANCELLED")
        elif kind == EditorConfirmationKind.DELETE_NOTE.value:
            action_id = self._delete_pending_action
            self._delete_pending_action = ""
            self._delete_entity_label = ""
            if self._bridge is not None and action_id:
                self._bridge.emit_note_delete_failure(
                    action_id,
                    "CANCELLED",
                )

    def _revoke_confirmation(self) -> None:
        self._confirmation_token = ""
        self._recovery_pending_action = ""
        confirmation = self._confirmation
        if confirmation is not None:
            confirmation.revoke_silently()

    def editor_ready(self, instance_id: str) -> None:
        window = self._window
        if window is None or instance_id != self._instance_id:
            return
        QTimer.singleShot(0, window.reveal_view)

    def editor_security_failure(self, instance_id: str) -> None:
        if instance_id == self._instance_id and self._window is not None:
            self._on_renderer_failed()

    def close_instance(
        self,
        outcome: str = "SECURITY_REVOKED",
        *,
        clear_reason: str = "bridge_close",
    ) -> bool:
        bridge, window = self._bridge, self._window
        if bridge is None or window is None:
            return True
        intent_id = self._intent_id
        instance_id = self._instance_id
        record_id = self._record_id
        revision = self._revision
        self._close_check_serial += 1
        self._close_check_pending = False
        self._reload_pending_action = ""
        self._delete_pending_action = ""
        self._delete_entity_label = ""
        self._revoke_confirmation()
        self._retiring_instance_id = instance_id
        complete = True
        try:
            self._conceal_window(window)
        except Exception:
            complete = False
        try:
            try:
                bridge_complete = bridge.close_instance(clear_reason) is True
                complete = bridge_complete and complete
            except Exception:
                complete = False
                try:
                    bridge.boundary.close("bridge_close")
                except Exception:
                    pass
            try:
                if not window.isMaximized():
                    self._last_geometry[self._mode] = QRect(window.geometry())
            except Exception:
                complete = False
        finally:
            try:
                complete = (
                    self._adapter.release_editor(instance_id) is True
                    and complete
                )
            except Exception:
                complete = False
            try:
                self._detach_web_surface(window, bridge)
            except Exception:
                complete = False
            self._bridge = None
            self._window = None
            self._confirmation = None
            self._intent_id = self._instance_id = self._revision = ""
            self._record_id = 0
            self._dirty = self._saving = False
            try:
                bridge.setParent(None)
                bridge.deleteLater()
            except Exception:
                pass
            try:
                window.hide()
                window.deleteLater()
            except Exception:
                pass
            self.editorFinishedV1.emit(
                intent_id,
                instance_id,
                outcome if complete else "SECURITY_REVOKED",
                record_id,
                revision,
            )
            self._retiring_instance_id = ""
        return complete

    @staticmethod
    def _conceal_for_boundary(window: EditorWindow) -> bool:
        EditorWindowController._conceal_window(window)
        return True

    @staticmethod
    def _conceal_window(window: EditorWindow) -> None:
        view = window.view
        view.setEnabled(False)
        view.hide()
        window.setEnabled(False)
        window.hide()
        try:
            QApplication.sync()
        except Exception:
            pass

    def _place_window(self, window: EditorWindow) -> None:
        active = QApplication.activeWindow()
        screen = active.screen() if active is not None else QApplication.primaryScreen()
        if screen is None:
            return
        available = screen.availableGeometry()
        geometry = QRect(self._last_geometry.get(self._mode, QRect()))
        if not geometry.isValid():
            size = window.size()
            geometry = QRect(
                available.center().x() - size.width() // 2,
                available.center().y() - size.height() // 2,
                size.width(),
                size.height(),
            )
        window.setGeometry(
            fit_window_rect(geometry, available, window.minimumSize())
        )

    def _copy_is_current(
        self, instance_id: str, view: QWebEngineView
    ) -> bool:
        return (
            self._bridge is not None
            and self._window is not None
            and self._instance_id == instance_id
            and self._window.view is view
            and view.hasFocus()
        )

    def _detach_web_surface(
        self, window: EditorWindow, bridge: EditorBridge
    ) -> None:
        sensitive_dom, channel = self._sensitive_dom, self._channel
        if sensitive_dom is not None:
            sensitive_dom.detach()
        view = window.view
        copy_filter = self._copy_filter
        if copy_filter is not None:
            copy_filter.invalidate()
            if isinstance(view, QWebEngineView):
                view.removeEventFilter(copy_filter)
        self._copy_filter = None
        if isinstance(view, QWebEngineView):
            page = view.page()
            try:
                page.setWebChannel(None)
            except RuntimeError:
                pass
            try:
                page.renderProcessTerminated.disconnect(self._on_renderer_failed)
            except (RuntimeError, TypeError):
                pass
            try:
                view.loadFinished.disconnect(self._on_editor_load_finished)
            except (RuntimeError, TypeError):
                pass
        if channel is not None:
            channel.deregisterObject(bridge)
        self._channel = None
        self._sensitive_dom = None

    def _on_renderer_failed(self, *_unused: object) -> None:
        window = self._window
        if window is None:
            return
        self._conceal_window(window)
        self._revoke_confirmation()
        self.close_instance(
            "SECURITY_REVOKED", clear_reason="renderer_failure"
        )
        self._renderer_failed()

    def _on_editor_load_finished(self, ok: bool) -> None:
        if not ok:
            self._on_renderer_failed()

    def _on_bridge_destroyed(self, instance_id: str) -> None:
        window = self._window
        if (
            window is None
            or self._bridge is None
            or not isValid(window)
            or instance_id != self._instance_id
            or instance_id == self._retiring_instance_id
        ):
            return
        intent_id = self._intent_id
        record_id = self._record_id
        revision = self._revision
        self._conceal_window(window)
        if self._sensitive_dom is not None:
            self._sensitive_dom.clear_all("bridge_destroyed")
        try:
            self._adapter.release_editor(instance_id)
        except Exception:
            pass
        try:
            self._detach_web_surface(window, self._bridge)
        except Exception:
            pass
        self._bridge = None
        self._window = None
        self._confirmation = None
        self._intent_id = self._instance_id = self._revision = ""
        self._record_id = 0
        self._dirty = self._saving = False
        self._reload_pending_action = ""
        self._delete_pending_action = ""
        self._delete_entity_label = ""
        try:
            window.hide()
            window.deleteLater()
        finally:
            try:
                self.editorFinishedV1.emit(
                    intent_id,
                    instance_id,
                    "SECURITY_REVOKED",
                    record_id,
                    revision,
                )
                self._renderer_failed()
            except RuntimeError:
                return

class EditorLauncherBridge(QObject):
    """Main-page façade; renderer deletion never owns the controller."""

    editorFinishedV1 = Signal(str, str, str, int, str)

    def __init__(
        self,
        controller: EditorWindowController,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._controller = controller
        controller.editorFinishedV1.connect(self.editorFinishedV1.emit)

    @Slot("QVariant", "QVariant", "QVariant", "QVariant", result="QVariantMap")
    def openPasswordEditorV1(
        self,
        intentId: object,
        recordId: object,
        revision: object,
        generateAfterOpen: object,
    ) -> dict[str, object]:
        return self._controller.openPasswordEditorV1(
            intentId,
            recordId,
            revision,
            generateAfterOpen,
        )

    @Slot("QVariant", "QVariant", result="QVariantMap")
    def openPasswordCreatorV1(
        self,
        intentId: object,
        sourceLeaseId: object,
    ) -> dict[str, object]:
        return self._controller.openPasswordCreatorV1(
            intentId,
            sourceLeaseId,
        )

    @Slot("QVariant", result="QVariantMap")
    def openNoteCreatorV1(self, intentId: object) -> dict[str, object]:
        return self._controller.openNoteCreatorV1(intentId)

    @Slot("QVariant", "QVariant", "QVariant", result="QVariantMap")
    def openNoteEditorV1(
        self,
        intentId: object,
        noteId: object,
        revision: object,
    ) -> dict[str, object]:
        return self._controller.openNoteEditorV1(
            intentId,
            noteId,
            revision,
        )


__all__ = [
    "EditorBridge",
    "EditorLauncherBridge",
    "EditorWindow",
    "EditorWindowController",
]
