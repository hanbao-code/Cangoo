"""产品运行时；装配业务桥接、原生窗口控制器及安全生命周期。"""

from __future__ import annotations

import json
import math
import threading
from functools import partial
from typing import Protocol

from PySide6.QtCore import QObject, QThread, Qt, QTimer, QUrl, Signal, Slot
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineScript
from PySide6.QtWidgets import QApplication

from desktop.bridge.command_ids import CommandId
from desktop.bridge.protocol import (
    C49_INTERNAL_FAILURE_REASON,
    SecurityBoundaryOutcome,
)
from desktop.bridge.web_bridge import PdmBridgeV1
from desktop.host.native_capabilities import NativeClipboard, NativeHotkey
from desktop.host.security_lifecycle import (
    SecurityBoundaryContext,
    SecurityBoundaryCoordinator,
    SecurityCleanupPhase,
)
from desktop.runtime_paths import RuntimePaths

from .adapter import ApplicationAdapter, SettingsCommitPublication
from .backup import BackupFileSelector
from .backup_window import BackupWindowController, BACKUP_COMMANDS
from .clipboard import ProductClipboardController
from .contract import load_bridge_contract
from .database_targets import DatabaseTargetSelector
from .editor_window import EditorWindowController
from .quickbar import NativeQuickbarController, QuickbarFocusPort
from .resources import ProductResourceCatalog
from .update_controller import UpdateController


_READ_PASSWORD_INPUT_SELECTION = r"""
JSON.stringify((() => {
  const active = document.activeElement;
  const allowed = new Set([
    'db-password',
    'check-input',
    'mf-password',
    'kf-current',
    'kf-new',
    'kf-confirm',
  ]);
  if (!(active instanceof HTMLInputElement) || !allowed.has(active.id)) {
    return {action: 'FALLBACK'};
  }
  if (
    !active.isConnected ||
    active.disabled ||
    active.dataset.pdmM4Disabled === 'true' ||
    active.getClientRects().length === 0 ||
    getComputedStyle(active).visibility !== 'visible' ||
    !['password', 'text'].includes(active.type)
  ) {
    return {action: 'NONE'};
  }
  const modal = active.closest('#active-modal');
  if (
    active.id === 'mf-password' &&
    !(
      modal?.dataset.pdmM4Create === 'true' ||
      (
        modal?.dataset.pdmM4Edit === 'true' &&
        active.dataset.pdmCopyAuthorized === 'edit'
      )
    )
  ) {
    return {action: 'NONE'};
  }
  if (
    ['kf-current', 'kf-new', 'kf-confirm'].includes(active.id) &&
    modal?.dataset.pdmM4ChangeKey !== 'true'
  ) {
    return {action: 'NONE'};
  }
  const start = active.selectionStart;
  const end = active.selectionEnd;
  if (
    !Number.isSafeInteger(start) ||
    !Number.isSafeInteger(end) ||
    start < 0 ||
    end <= start ||
    end > active.value.length
  ) {
    return {action: 'NONE'};
  }
  return {
    action: 'PASSWORD',
    fieldId: active.id,
    start,
    end,
    valueLength: active.value.length,
    text: active.value.slice(start, end),
  };
})())
"""

_NOTIFY_PASSWORD_INPUT_COPY_FAILED = (
    "window.pdmM4?.showNativeClipboardUnavailableToast?.();"
)

_PASSWORD_COPY_FIELDS = frozenset(
    {
        "db-password",
        "check-input",
        "mf-password",
        "kf-current",
        "kf-new",
        "kf-confirm",
    }
)


class _ProductHostPort(Protocol):
    security: SecurityBoundaryCoordinator

    def on_m4_handshake(self, page_epoch: int) -> None: ...

    def ensure_m4_power_protection(self) -> bool: ...

    def m4_power_rebind_pending(self) -> bool: ...

    def on_m4_session_opened(self, session_epoch: int) -> None: ...

    def on_m4_locked(self, reason: str) -> None: ...

    def on_m4_lock_failed(self) -> None: ...

    def on_m4_settings_projection(
        self,
        theme: str,
        effective_theme: str,
        language: str,
        ui_font_scale: str,
        sidebar_text: bool,
        close_behavior: str,
        auto_lock_enabled: bool,
        auto_lock_minutes: int,
        quickbar_enabled: bool,
        quickbar_idle_seconds: int,
        quickbar_hotkey: str,
        quickbar_registration: str,
    ) -> None: ...

    def on_m4_change_key_terminal(self, reason: str) -> None: ...

    def announce_m4_accessible_operation(
        self,
        operation: str,
        error_code: str,
    ) -> bool: ...

    def set_m4_external_change_key_settlement_token(
        self,
        token: int | None,
    ) -> None: ...

    def current_sensitive_dom(self): ...

    def current_native_clipboard(self) -> NativeClipboard: ...

    def current_native_hotkey(self) -> NativeHotkey: ...

    def m4_copy_focus_is_current(self, page: QWebEnginePage) -> bool: ...

    def create_m4_editor_view(self, entry_path: str = "/editor.html"): ...

class _CurrentSensitiveDomSink:
    """Delegate lease cleanup to the controller for the current page."""

    def __init__(self, host: _ProductHostPort) -> None:
        self._host = host

    def revoke_secret_leases(
        self,
        reason: str,
        *,
        lease_ids: tuple[str, ...],
        page_id: str | None = None,
        session_id: str | None = None,
        parent_lease_id: str | None = None,
    ) -> None:
        self._host.current_sensitive_dom().revoke_secret_leases(
            reason,
            lease_ids=lease_ids,
            page_id=page_id,
            session_id=session_id,
            parent_lease_id=parent_lease_id,
        )


class RendererBridgeSecurityPort:
    """Make RequestBoundary the sole renderer-failure authority."""

    def __init__(self, runtime: "ProductRuntime") -> None:
        self._runtime = runtime
        self._last_request: dict[str, object] = {}

    @property
    def last_request(self) -> dict[str, object]:
        return dict(self._last_request)

    def enter_boundary(
        self,
        reason: str,
        *,
        authority_serial: int,
        page_epoch: int,
        session_epoch: int,
        page_revoked: bool,
    ) -> SecurityBoundaryOutcome:
        # Record entry before consulting any runtime-owned object.  These
        # fixed phases let the isolated lifecycle verifier distinguish a
        # dispatch failure from an epoch-read or cleanup failure without
        # exposing exception text, paths, or renderer-controlled data.
        self._last_request = {
            "status": "ENTERED",
            "reason": reason,
            "authoritySerial": authority_serial,
            "pageEpoch": page_epoch,
            "sessionEpoch": session_epoch,
            "pageRevoked": page_revoked,
        }
        runtime = self._runtime
        try:
            expected_page_epoch = runtime.active_page_epoch
            expected_session_epoch = runtime.active_session_epoch
        except Exception:
            self._last_request["status"] = "EPOCH_READ_FAILED"
            raise
        self._last_request.update(
            {
                "status": "EPOCHS_READ",
                "expectedPageEpoch": expected_page_epoch,
                "expectedSessionEpoch": expected_session_epoch,
            }
        )
        if (
            reason != "renderer_failure"
            or page_revoked is not True
            or page_epoch != expected_page_epoch
            or session_epoch != expected_session_epoch
        ):
            self._last_request["status"] = "REJECTED"
            return SecurityBoundaryOutcome(
                authority_revoked=False,
                complete=False,
            )
        self._last_request["status"] = "ACCEPTED"
        complete = runtime.invalidate_renderer_page()
        self._last_request["complete"] = complete
        return SecurityBoundaryOutcome(
            authority_revoked=True,
            complete=complete,
        )


class _GuiCallPort(QObject):
    requested = Signal(object)
    WAIT_SECONDS = 10

    def __init__(self, parent: QObject) -> None:
        super().__init__(parent)
        self._pending_lock = threading.Lock()
        self._pending: list[tuple[object, threading.Event, list[object]]] = []
        self.requested.connect(self._run, Qt.ConnectionType.QueuedConnection)

    def call(self, action):
        if QThread.currentThread() == self.thread():
            return action()
        settled = threading.Event()
        result: list[object] = []
        payload = (action, settled, result)
        with self._pending_lock:
            self._pending.append(payload)
        self.requested.emit(payload)
        if not settled.wait(self.WAIT_SECONDS):
            with self._pending_lock:
                self._pending = [item for item in self._pending if item is not payload]
            raise RuntimeError("GUI hotkey operation timed out")
        value = result[0]
        if isinstance(value, BaseException):
            raise value
        return value

    @Slot(object)
    def _run(self, payload: object) -> None:
        with self._pending_lock:
            if not any(item is payload for item in self._pending):
                return
            self._pending = [item for item in self._pending if item is not payload]
        self._execute(payload)

    def drain_pending(self) -> None:
        """Execute queued native calls before GUI-thread settings settlement."""

        if QThread.currentThread() != self.thread():
            raise RuntimeError("GUI call drain requires the GUI thread")
        while True:
            with self._pending_lock:
                if not self._pending:
                    return
                payload = self._pending.pop(0)
            self._execute(payload)

    @staticmethod
    def _execute(payload: object) -> None:
        action, settled, result = payload
        try:
            result.append(action())
        except BaseException as exc:
            result.append(exc)
        finally:
            settled.set()


class ProductRuntime(QObject):
    """Own one Bridge/channel/adapter across every renderer generation."""

    WEBCHANNEL_OBJECT = "pdmBridgeV1"
    _change_key_progress_received = Signal(str, int, int, str, int, int)
    _strength_changed_received = Signal(int, int)

    def __init__(
        self,
        host: _ProductHostPort,
        isolation: RuntimePaths,
        selector: DatabaseTargetSelector,
        parent: QObject,
        *,
        quickbar_focus_port: QuickbarFocusPort | None = None,
        backup_selector: BackupFileSelector | None = None,
        startup_update_check: bool = False,
        update_client_factory=None,
    ) -> None:
        super().__init__(parent)
        self._host = host
        self.clipboard = ProductClipboardController(
            host.current_native_clipboard(),
            self,
        )
        application = QApplication.instance()
        if application is None:
            raise RuntimeError("M4 Bridge requires an active QApplication")
        self._style_hints = application.styleHints()
        self._system_effective_theme = self._effective_theme_from_qt(
            self._style_hints.colorScheme()
        )
        self._settings_theme: str | None = None
        self._settings_effective_theme: str | None = None
        self._settings_language: str | None = None
        self._settings_ui_font_scale: str | None = None
        self._settings_close_behavior: str | None = None
        self._settings_auto_lock_enabled: bool | None = None
        self._settings_auto_lock_minutes: int | None = None
        self._settings_quickbar_enabled: bool | None = None
        self._settings_quickbar_idle_seconds: int | None = None
        self._settings_quickbar_hotkey: str | None = None
        self._settings_quickbar_registration: str | None = None
        self._renderer_settings_revision = ""
        self._renderer_invalidation_status = "NEVER"
        self._change_key_connection_notice = ""
        self._change_key_success_toast_available = False
        self._password_input_copy_serial = 0
        self._password_input_copy_selection_serial = 0
        self._password_input_copy_page_serial = 0
        self._password_input_copy_pending_serial = 0
        self._closed = False
        self._close_complete: bool | None = None
        failure_retry_ms = min(
            86_400_000,
            max(1, int(application.doubleClickInterval()) + 50),
        )
        self._gui_calls = _GuiCallPort(self)
        self.adapter = ApplicationAdapter(
            isolation,
            selector,
            self.clipboard,
            hotkey=host.current_native_hotkey(),
            backup_selector=backup_selector,
            failure_retry_ms=failure_retry_ms,
            effective_theme_provider=(
                lambda: self.current_system_effective_theme
            ),
            hotkey_dispatch=self._gui_calls.call,
        )
        self._database_label = ""
        catalog = load_bridge_contract()
        self.bridge = PdmBridgeV1(
            catalog,
            self.adapter,
            self,
            secret_lifecycle_sink=_CurrentSensitiveDomSink(host),
            security_boundary_sink=host.security,
            session_state_sink=self,
            accessible_rejection_sink=self._on_accessible_submit_rejected,
            request_admission=self._admit_main_bridge_request,
        )
        version_resource = ProductResourceCatalog().payload_for_url(QUrl("pdm://app/assets/help/content.json"))
        if version_resource is None:
            raise RuntimeError("installed version resource is unavailable")
        self.updates = UpdateController(
            self.adapter.update_state_store(), self.adapter.submit_update_storage,
            json.loads(version_resource.content)["version"], self,
            client_factory=update_client_factory,
        )
        self._startup_update_check = startup_update_check
        self.adapter.bind_update_controller(self.updates)
        self.updates.changed.connect(self._on_update_state_changed)
        self.quickbar = NativeQuickbarController(
            catalog,
            self.adapter,
            self,
            focus_port=quickbar_focus_port,
        )
        self.editor = EditorWindowController(
            catalog,
            self.adapter,
            authority=lambda: (
                self.bridge.active_page_epoch,
                self.bridge.active_session_epoch,
            ),
            renderer_failed=self._on_editor_renderer_failed,
            copy_password=self._copy_editor_password,
            clone_generated_prefill=self._clone_editor_generated_prefill,
            view_factory=lambda: host.create_m4_editor_view("/editor.html"),
            note_view_factory=lambda: host.create_m4_editor_view(
                "/note-editor.html"
            ),
            parent=self,
        )
        self.editor.editorFinishedV1.connect(self._on_editor_finished)
        self.backup_window = BackupWindowController(
            catalog, self.adapter,
            authority=lambda: (self.active_page_epoch, self.active_session_epoch),
            view_factory=lambda: host.create_m4_editor_view("/index.html"),
            renderer_failed=self._on_editor_renderer_failed,
            parent=self,
        )
        self._change_key_progress_received.connect(
            self._on_change_key_progress,
            Qt.ConnectionType.QueuedConnection,
        )
        self.adapter.set_change_key_progress_sink(
            self._change_key_progress_received.emit
        )
        self._strength_changed_received.connect(
            self._on_strength_changed, Qt.ConnectionType.QueuedConnection)
        self.adapter.set_strength_changed_sink(self._strength_changed_received.emit)
        self.channel = QWebChannel(self)
        self.channel.registerObject(self.WEBCHANNEL_OBJECT, self.bridge)
        self.channel.registerObject("pdmBackupLauncherV1", self.backup_window.launcher)
        self.channel.registerObject(
            "pdmEditorLauncherV1",
            self.editor.launcher,
        )
        self.clipboard.state_changed.connect(
            self._on_clipboard_state_changed,
            Qt.ConnectionType.QueuedConnection,
        )
        self.renderer_security_port = RendererBridgeSecurityPort(self)
        self._attached_page: QWebEnginePage | None = None

        host.security.register(
            SecurityCleanupPhase.STOP_ACTIVITY,
            "m4.quickbar.stop",
            self._stop_quickbar_activity,
        )
        host.security.register(
            SecurityCleanupPhase.CONCEAL_RENDERER,
            "m4.editor.close",
            self._close_editor_for_security,
        )
        host.security.register(
            SecurityCleanupPhase.CLEAR_NATIVE_SECRETS,
            "m4.clipboard.reset_state",
            lambda _context: self.clipboard.reset_authority(),
        )
        host.security.register(
            SecurityCleanupPhase.CLEAR_NATIVE_SECRETS,
            "m4.password_input_copy.invalidate",
            lambda _context: self.note_password_input_copy_interaction(),
        )
        host.security.register(
            SecurityCleanupPhase.RELEASE_SESSION,
            "m4.adapter.invalidate_session",
            self._invalidate_adapter_session,
        )
        self.bridge.handshakeCompletedV1.connect(
            self._on_handshake_completed
        )
        self.bridge.openDatabaseCompletedV1.connect(
            self._on_open_completed
        )
        self.bridge.lockCompletedV1.connect(
            self._on_lock_completed
        )
        self.bridge.openQuickbarCompletedV1.connect(
            self._on_open_quickbar_completed,
            Qt.ConnectionType.QueuedConnection,
        )
        self.bridge.setThemeCompletedV1.connect(
            self._on_settings_completed,
            Qt.ConnectionType.QueuedConnection,
        )
        self.bridge.setLanguageCompletedV1.connect(
            self._on_settings_completed,
            Qt.ConnectionType.QueuedConnection,
        )
        self.bridge.setUiFontScaleCompletedV1.connect(
            self._on_settings_completed,
            Qt.ConnectionType.QueuedConnection,
        )
        self.bridge.setStartupAutofillCompletedV1.connect(
            self._on_session_setting_completed,
            Qt.ConnectionType.QueuedConnection,
        )
        self.bridge.setDefaultViewCompletedV1.connect(
            self._on_session_setting_completed,
            Qt.ConnectionType.QueuedConnection,
        )
        self.bridge.setSidebarTextCompletedV1.connect(
            self._on_settings_completed,
            Qt.ConnectionType.QueuedConnection,
        )
        self.bridge.setSortModeCompletedV1.connect(
            self._on_session_setting_completed,
            Qt.ConnectionType.QueuedConnection,
        )
        self.bridge.setClipboardPolicyCompletedV1.connect(
            self._on_session_setting_completed,
            Qt.ConnectionType.QueuedConnection,
        )
        self.bridge.setCloseBehaviorCompletedV1.connect(
            self._on_session_setting_completed,
            Qt.ConnectionType.QueuedConnection,
        )
        self.bridge.setQuickbarEnabledCompletedV1.connect(
            self._on_session_setting_completed,
            Qt.ConnectionType.QueuedConnection,
        )
        self.bridge.setQuickbarHotkeyCompletedV1.connect(
            self._on_session_setting_completed,
            Qt.ConnectionType.QueuedConnection,
        )
        self.bridge.setStaleThresholdCompletedV1.connect(
            self._on_session_setting_completed,
            Qt.ConnectionType.QueuedConnection,
        )
        self.bridge.setAutoLockPolicyCompletedV1.connect(
            self._on_session_setting_completed,
            Qt.ConnectionType.QueuedConnection,
        )
        self.bridge.setPasswordGeneratorDefaultsCompletedV1.connect(
            self._on_session_setting_completed,
            Qt.ConnectionType.QueuedConnection,
        )
        for signal, operation, page_scoped, announce_success in (
            (self.bridge.createRecordCompletedV1, "PASSWORD_ADDED", False, True),
            (self.bridge.updateRecordCompletedV1, "PASSWORD_UPDATED", False, True),
            (self.bridge.updateRecordFieldsCompletedV1, "PASSWORD_UPDATED", False, True),
            (self.bridge.deleteRecordCompletedV1, "PASSWORD_DELETED", False, True),
            (self.bridge.createNoteCompletedV1, "NOTE_ADDED", False, True),
            (self.bridge.updateNoteCompletedV1, "NOTE_SAVED", False, True),
            (self.bridge.updateNoteFieldsCompletedV1, "NOTE_SAVED", False, True),
            (self.bridge.deleteNoteCompletedV1, "NOTE_DELETED", False, True),
            (self.bridge.generatePasswordCompletedV1, "PASSWORD_GENERATED", True, True),
            (self.bridge.copyRecordAccountCompletedV1, "ACCOUNT_COPIED", False, True),
            (self.bridge.copyRecordPasswordCompletedV1, "PASSWORD_COPIED", False, True),
            (self.bridge.copyRecordTotpCompletedV1, "TOTP_COPIED", False, True),
            (self.bridge.clearClipboardCompletedV1, "CLIPBOARD_CLEARED", True, True),
            (self.bridge.copyGeneratedPasswordCompletedV1, "GENERATED_PASSWORD_COPIED", True, True),
            (self.bridge.chooseBackupDestinationCompletedV1, "BACKUP_EXPORTED", False, False),
            (self.bridge.exportEncryptedBackupCompletedV1, "BACKUP_EXPORTED", False, True),
            (self.bridge.chooseBackupSourceCompletedV1, "BACKUP_IMPORTED", False, False),
            (self.bridge.previewEncryptedBackupCompletedV1, "BACKUP_IMPORTED", False, False),
            (self.bridge.executeEncryptedBackupImportCompletedV1, "BACKUP_IMPORTED", False, True),
        ):
            signal.connect(
                partial(
                    self._on_accessible_operation_completed,
                    operation,
                    page_scoped=page_scoped,
                    announce_success=announce_success,
                ),
                Qt.ConnectionType.QueuedConnection,
            )
        initial_projection = self._settings_result_projection(
            self.adapter.current_settings_authority()
        )
        if initial_projection is None:
            raise RuntimeError("M4 native settings projection is invalid")
        initial_revision, initial_settings = initial_projection
        self._adopt_settings_projection(
            initial_settings,
            initial_revision,
        )
        self._style_hints.colorSchemeChanged.connect(
            self._on_system_color_scheme_changed,
            Qt.ConnectionType.QueuedConnection,
        )

    def _admit_main_bridge_request(
        self,
        command_id: CommandId,
        arguments: tuple[object, ...],
    ) -> str | None:
        if self._closed:
            return "STALE_PAGE"
        if self._host.m4_power_rebind_pending():
            return "REQUEST_BUSY"
        if command_id is CommandId.C04 and not self._host.ensure_m4_power_protection():
            return "INTERNAL_FAILURE"
        # 备份操作只从独立窗口的固定命令面进入，主页面保留开窗能力。
        if command_id in BACKUP_COMMANDS:
            return "REQUEST_BUSY"
        occupancy = self.adapter.editor_occupancy
        if occupancy is None:
            return None
        if command_id in {
            CommandId.C02,
            CommandId.C03,
            CommandId.C05,
            CommandId.C12,
            CommandId.C14,
            CommandId.C15,
            CommandId.C26,
            CommandId.C27,
            CommandId.C49,
            CommandId.C52,
            CommandId.C53,
            CommandId.C54,
            CommandId.C55,
            CommandId.C56,
            CommandId.C57,
            CommandId.C58,
            CommandId.C59,
            CommandId.C62,
            CommandId.C65,
        }:
            return "REQUEST_BUSY"
        kind, record_id, _session_epoch, _instance_id = occupancy
        record_argument = {
            CommandId.C16: 3,
            CommandId.C17: 3,
            CommandId.C28: 3,
            CommandId.C29: 3,
        }.get(command_id)
        if record_argument is None:
            return None
        expected_kind = (
            "PASSWORD"
            if command_id in {CommandId.C16, CommandId.C17}
            else "NOTE"
        )
        return (
            "REQUEST_BUSY"
            if kind == expected_kind
            and arguments[record_argument] == record_id
            else None
        )

    def _copy_editor_password(self, text: str) -> bool:
        if type(text) is not str or not text or "\x00" in text:
            return False
        try:
            return self.clipboard.copy(text, "PASSWORD") is not None
        except Exception:
            return False

    def _clone_editor_generated_prefill(
        self,
        lease_id: str,
        page_epoch: int,
    ) -> dict[str, object] | None:
        if (
            self._closed
            or page_epoch != self.bridge.active_page_epoch
            or self.bridge.active_session_epoch <= 0
            or not self.bridge.generated_lease_is_authorized(
                lease_id,
                page_epoch,
            )
        ):
            return None
        return self.adapter.clone_generated_secret_for_editor(
            page_epoch,
            lease_id,
        )

    def _on_editor_renderer_failed(self) -> None:
        if self._closed or self.bridge.active_session_epoch <= 0:
            return
        self.lock_session_from_native("RENDERER_FAILURE")

    def _close_editor_for_security(
        self,
        context: SecurityBoundaryContext,
    ) -> None:
        if not self.backup_window.close(force=True, reason=context.reason.value):
            raise RuntimeError("backup window security cleanup incomplete")
        if not self.editor.close_instance(
            "SECURITY_REVOKED",
            clear_reason=context.reason.value,
        ):
            raise RuntimeError("editor security cleanup incomplete")

    @Slot(int, int)
    def _on_strength_changed(self, page_epoch: int, session_epoch: int) -> None:
        if (self._closed or page_epoch != self.bridge.active_page_epoch
                or session_epoch != self.bridge.active_session_epoch):
            return
        revisions = self.adapter.publish_strength_change(page_epoch, session_epoch)
        if revisions is not None:
            self.bridge.dataRevisionChangedV1.emit(page_epoch, session_epoch, *revisions)

    def _on_editor_finished(
        self,
        _intent_id: str,
        _instance_id: str,
        outcome: str,
        _record_id: int,
        _revision: str,
    ) -> None:
        if outcome not in {"SAVED", "DELETED"} or self._closed:
            return
        mode = self.editor.mode
        page_epoch = self.bridge.active_page_epoch
        session_epoch = self.bridge.active_session_epoch
        revisions = self.adapter.current_data_revisions()
        if page_epoch <= 0 or session_epoch <= 0 or revisions is None:
            return
        self.bridge.dataRevisionChangedV1.emit(
            page_epoch,
            session_epoch,
            *revisions,
        )
        self._host.announce_m4_accessible_operation(
            (
                "NOTE_DELETED"
                if outcome == "DELETED"
                else {
                    "CREATE": "PASSWORD_ADDED",
                    "EDIT": "PASSWORD_UPDATED",
                    "NOTE_CREATE": "NOTE_ADDED",
                    "NOTE_EDIT": "NOTE_SAVED",
                }.get(mode, "PASSWORD_UPDATED")
            ),
            "OK",
        )

    @property
    def active_page_epoch(self) -> int:
        return self.bridge.active_page_epoch

    @property
    def active_session_epoch(self) -> int:
        return self.bridge.active_session_epoch

    @property
    def attached(self) -> bool:
        return self._attached_page is not None and not self._closed

    @property
    def current_system_effective_theme(self) -> str:
        """Return the cached Qt style-hints LIGHT/DARK authority."""

        return self._system_effective_theme

    @property
    def change_key_connection_notice(self) -> str:
        """返回仅在本进程内保留的有界 C49 重连说明原因。"""

        reason = self._change_key_connection_notice
        return (
            reason
            if reason in {
                "CHANGE_KEY_SUCCESS",
                "CHANGE_KEY_RESTORED",
            }
            else ""
        )

    def _remember_change_key_connection_notice(self, reason: str) -> None:
        if reason not in {
            "CHANGE_KEY_SUCCESS",
            "CHANGE_KEY_RESTORED",
        }:
            raise ValueError("unsupported C49 connection notice reason")
        self._change_key_connection_notice = reason
        self._change_key_success_toast_available = (
            reason == "CHANGE_KEY_SUCCESS"
        )

    def clear_change_key_connection_notice(self) -> None:
        """清除固定说明和尚未认领的成功提示标记。"""

        self._change_key_connection_notice = ""
        self._change_key_success_toast_available = False

    def _project_change_key_connection_notice(
        self,
        page_epoch: int,
    ) -> bool:
        """向当前已握手网页重投影进程内固定说明。"""

        reason = self.change_key_connection_notice
        if (
            self._closed
            or reason
            not in {
                "CHANGE_KEY_SUCCESS",
                "CHANGE_KEY_RESTORED",
            }
            or page_epoch <= 0
            or page_epoch != self.bridge.active_page_epoch
            or self.bridge.active_session_epoch != 0
            or self._attached_page is None
        ):
            return False
        self.bridge.sessionStateChangedV1.emit(
            page_epoch,
            0,
            "LOCKED",
            reason,
            "",
        )
        return True

    def take_change_key_success_toast(
        self,
        page_epoch: int,
    ) -> bool:
        """在通知网页前先认领至多一次的 C49 成功提示。"""

        if (
            not self._change_key_success_toast_available
            or self.change_key_connection_notice != "CHANGE_KEY_SUCCESS"
            or page_epoch <= 0
            or page_epoch != self.bridge.active_page_epoch
            or self.bridge.active_session_epoch != 0
            or self._attached_page is None
        ):
            return False
        self._change_key_success_toast_available = False
        return True

    def attach_page(self, page: QWebEnginePage) -> None:
        if self._closed:
            raise RuntimeError("cannot attach a closed M4 Bridge")
        if self._attached_page is not None:
            raise RuntimeError("M4 Bridge already has an attached page")
        page.setWebChannel(self.channel)
        self.note_password_input_copy_interaction()
        self._password_input_copy_page_serial += 1
        page.selectionChanged.connect(
            self._on_password_input_copy_selection_changed
        )
        self._attached_page = page

    def detach_page(self, page: QWebEnginePage) -> None:
        if self._attached_page is not page:
            return
        self.note_password_input_copy_interaction()
        self._password_input_copy_page_serial += 1
        try:
            page.selectionChanged.disconnect(
                self._on_password_input_copy_selection_changed
            )
        except (RuntimeError, TypeError):
            pass
        page.setWebChannel(None)
        self._attached_page = None

    def note_password_input_copy_interaction(self) -> None:
        self._password_input_copy_serial += 1
        self._password_input_copy_pending_serial = 0

    def _on_password_input_copy_selection_changed(self) -> None:
        self._password_input_copy_selection_serial += 1
        self.note_password_input_copy_interaction()

    def request_password_input_copy(self) -> None:
        page = self._attached_page
        page_epoch = self.bridge.active_page_epoch
        session_epoch = self.bridge.active_session_epoch
        if self._password_input_copy_pending_serial:
            return
        if (
            self._closed
            or page is None
            or page_epoch <= 0
            or not self._host.m4_copy_focus_is_current(page)
        ):
            return
        self.note_password_input_copy_interaction()
        copy_serial = self._password_input_copy_serial
        selection_serial = self._password_input_copy_selection_serial
        page_serial = self._password_input_copy_page_serial
        self._password_input_copy_pending_serial = copy_serial
        try:
            page.runJavaScript(
                _READ_PASSWORD_INPUT_SELECTION,
                QWebEngineScript.ScriptWorldId.ApplicationWorld,
                lambda result: self._complete_password_input_copy(
                    page,
                    page_epoch,
                    session_epoch,
                    page_serial,
                    selection_serial,
                    copy_serial,
                    result,
                ),
            )
        except Exception:
            if self._password_input_copy_pending_serial == copy_serial:
                self._password_input_copy_pending_serial = 0
            return

    def _complete_password_input_copy(
        self,
        page: QWebEnginePage,
        page_epoch: int,
        session_epoch: int,
        page_serial: int,
        selection_serial: int,
        copy_serial: int,
        result: object,
    ) -> None:
        if self._password_input_copy_pending_serial == copy_serial:
            self._password_input_copy_pending_serial = 0
        # 当前 PySide6 不保留脚本对象返回值，使用项目既有的 JSON 字符串回传。
        if isinstance(result, str):
            try:
                result = json.loads(result)
            except (ValueError, RecursionError):
                return
        if (
            self._closed
            or page is not self._attached_page
            or page_serial != self._password_input_copy_page_serial
            or selection_serial
            != self._password_input_copy_selection_serial
            or copy_serial != self._password_input_copy_serial
            or page_epoch != self.bridge.active_page_epoch
            or session_epoch != self.bridge.active_session_epoch
            or not self._host.m4_copy_focus_is_current(page)
            or not isinstance(result, dict)
        ):
            self._scrub_password_input_copy_result(result)
            return
        action = result.get("action")
        if action == "FALLBACK" and set(result) == {"action"}:
            try:
                page.triggerAction(QWebEnginePage.WebAction.Copy)
            except Exception:
                pass
            return
        if action != "PASSWORD" or set(result) != {
            "action",
            "fieldId",
            "start",
            "end",
            "valueLength",
            "text",
        }:
            self._scrub_password_input_copy_result(result)
            return
        field_id = result.get("fieldId")
        start = self._password_input_copy_integer(result.get("start"))
        end = self._password_input_copy_integer(result.get("end"))
        value_length = self._password_input_copy_integer(
            result.get("valueLength")
        )
        text = result.get("text")
        copy_failed = False
        valid = False
        try:
            utf16_length = (
                len(text.encode("utf-16-le", errors="surrogatepass")) // 2
                if type(text) is str
                else -1
            )
            valid = (
                field_id in _PASSWORD_COPY_FIELDS
                and (
                    field_id == "check-input"
                    or (field_id == "db-password" and session_epoch == 0)
                    or (
                        field_id
                        in {
                            "mf-password",
                            "kf-current",
                            "kf-new",
                            "kf-confirm",
                        }
                        and session_epoch > 0
                    )
                )
                and start is not None
                and end is not None
                and value_length is not None
                and 0 <= start < end <= value_length <= 2_147_483_647
                and type(text) is str
                and text != ""
                and "\x00" not in text
                and utf16_length == end - start
            )
            if valid:
                copy_failed = self.clipboard.copy(text, "PASSWORD") is None
        except Exception:
            copy_failed = valid
        finally:
            self._scrub_password_input_copy_result(result)
        if copy_failed:
            try:
                page.runJavaScript(_NOTIFY_PASSWORD_INPUT_COPY_FAILED)
            except Exception:
                pass

    @staticmethod
    def _scrub_password_input_copy_result(result: object) -> None:
        if isinstance(result, dict) and "text" in result:
            result["text"] = ""

    @staticmethod
    def _password_input_copy_integer(value: object) -> int | None:
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

    def invalidate_renderer_page(self) -> bool:
        """先撤销失效页面并安装原生遮挡，再收敛公开设置投影。

        设置收敛可能等待磁盘或工作线程，不能延迟页面/会话权威撤销与安全
        表面安装。投影失败仍阻断恢复；固定诊断状态不包含路径或异常文本。
        """

        page_epoch = self.bridge.active_page_epoch
        session_epoch = self.bridge.active_session_epoch
        c49_token = self.bridge.pending_change_key_token
        self._host.set_m4_external_change_key_settlement_token(c49_token)
        self._renderer_invalidation_status = "REVOKING_AUTHORITY"
        try:
            self.adapter.note_settings_session_invalidation(
                session_epoch
            )
            self._gui_calls.drain_pending()
            boundary_complete = self.bridge.invalidate_page(
                "renderer_failure"
            )
            self.adapter.clear_settings_session_invalidation(session_epoch)
        except Exception:
            self.adapter.clear_settings_session_invalidation(session_epoch)
            outcome = self._consume_external_change_key_settlement(
                c49_token,
                cleanup_complete=False,
            )
            self._apply_external_change_key_settlement(
                outcome,
                page_revoked=True,
            )
            self._renderer_invalidation_status = "BOUNDARY_FAILED"
            return False
        outcome = self._consume_external_change_key_settlement(
            c49_token,
            cleanup_complete=boundary_complete is True,
        )
        if not self._apply_external_change_key_settlement(
            outcome,
            page_revoked=True,
        ):
            self._renderer_invalidation_status = "C49_SETTLEMENT_BLOCKED"
            return False
        if boundary_complete is not True:
            self._renderer_invalidation_status = "BOUNDARY_INCOMPLETE"
            return False

        projection_complete = False
        self._renderer_invalidation_status = "SETTLING_SETTINGS_AFTER_BOUNDARY"
        try:
            if page_epoch > 0:
                self.adapter.settle_settings_projection_for_page(
                    page_epoch
                )
                projection = self._latest_settings_authority_projection()
                if projection is None:
                    raise RuntimeError(
                        "settled page settings authority is invalid"
                    )
                settings_revision, settings = projection
                self._adopt_settings_projection(
                    settings,
                    settings_revision,
                )
            projection_complete = True
        except Exception:
            self._renderer_invalidation_status = (
                "SETTINGS_FAILED_AFTER_BOUNDARY"
            )
        if not projection_complete:
            return False
        self._renderer_invalidation_status = "COMPLETE"
        return True

    @property
    def renderer_invalidation_status(self) -> str:
        return self._renderer_invalidation_status

    def settle_close_behavior_for_native_close(self) -> str:
        """Return final persisted close authority before native dispatch.

        The adapter first settles every setting accepted before close so the
        complete native snapshot, including D18 language, is deterministic.
        This path does not wait for renderer completion or S02.  A queued
        publication remains one-shot for the current page:
        successful TO_TRAY and D18 cancellation keep that renderer alive and
        its pending setting control still needs the eventual S02 settlement.
        C06/session invalidation drops the marker because its old page/session
        completion is no longer authorized.
        """

        if self._closed:
            raise RuntimeError("cannot settle settings on a closed runtime")
        session_epoch = self.bridge.active_session_epoch
        self.adapter.note_settings_session_invalidation(session_epoch)
        try:
            self._gui_calls.drain_pending()
            authority = self.adapter.settle_close_behavior_authority()
        finally:
            self.adapter.clear_settings_session_invalidation(session_epoch)
        if session_epoch > 0:
            self.adapter.activate_quickbar_hotkey_for_session()
            authority = self.adapter.current_settings_authority()
        projection = self._settings_result_projection(authority)
        if projection is None:
            raise RuntimeError("native close settings authority is invalid")
        settings_revision, projected_settings = projection
        projected_settings = self._settings_with_current_effective_theme(
            projected_settings
        )
        self._adopt_settings_projection(
            projected_settings,
            settings_revision,
        )
        return str(projected_settings["closeBehavior"])

    def lock_session_from_native(self, reason: str) -> bool:
        """先同步撤权和遮蔽，再清理会话；电源换绑也清理无会话公共页。"""

        boundary_reason = {
            "AUTO_LOCK": "auto_lock",
            "RENDERER_FAILURE": "renderer_failure",
            "SUSPEND_LOCK": "suspend_lock",
            "SESSION_INVALIDATED": "session_invalidated",
        }.get(reason)
        if boundary_reason is None:
            raise ValueError("unsupported native lock reason")
        if self._closed or (
            self.bridge.active_session_epoch <= 0
            and (reason != "SESSION_INVALIDATED" or self.bridge.active_page_epoch <= 0)
        ):
            return False
        c49_token = self.bridge.pending_change_key_token
        self._host.set_m4_external_change_key_settlement_token(c49_token)
        cleanup_complete = self.bridge.invalidate_session(boundary_reason)
        outcome = self._consume_external_change_key_settlement(
            c49_token,
            cleanup_complete=cleanup_complete,
        )
        if not self._apply_external_change_key_settlement(
            outcome,
            page_revoked=False,
        ):
            return False
        if cleanup_complete:
            if outcome in {"SUCCESS", "RESTORED"}:
                return True
            try:
                self._settle_settings_for_locked_presentation()
            except (RuntimeError, ValueError):
                # 设置投影不是安全结果权威，也不能重新打开已经撤销的
                # session。
                pass
            self._publish_public_lock(
                "RENDERER_FAILURE"
                if reason == "RENDERER_FAILURE"
                else reason
            )
        else:
            self._database_label = ""
            self._host.on_m4_lock_failed()
        return cleanup_complete

    def lock_public_page_for_suspend(self) -> bool:
        """挂起时清理当前无会话公共页面及其全部秘密。"""

        if (
            self._closed
            or self.bridge.active_page_epoch <= 0
            or self.bridge.active_session_epoch != 0
        ):
            return False
        cleanup_complete = self.bridge.invalidate_session("suspend_lock")
        if cleanup_complete:
            try:
                self._settle_settings_for_locked_presentation()
            except (RuntimeError, ValueError):
                pass
            self._publish_public_lock("SUSPEND_LOCK")
        else:
            self._database_label = ""
            self._host.on_m4_lock_failed()
        return cleanup_complete

    def _consume_external_change_key_settlement(
        self,
        token: int | None,
        *,
        cleanup_complete: bool,
    ) -> str | None:
        if token is None:
            self._host.set_m4_external_change_key_settlement_token(None)
            return None
        outcome = self.adapter.take_change_key_settlement(token)
        self._host.set_m4_external_change_key_settlement_token(None)
        if outcome == "RECOVERY_FAILED":
            return outcome
        if cleanup_complete is not True:
            return "INTERNAL_FAILURE"
        if outcome in {
            "SUCCESS",
            "RESTORED",
            "REVERSIBLE_ABORTED",
            "INTERNAL_FAILURE",
        }:
            return outcome
        return "INTERNAL_FAILURE"

    def _apply_external_change_key_settlement(
        self,
        outcome: str | None,
        *,
        page_revoked: bool,
    ) -> bool:
        if outcome is None:
            return True
        if outcome == "REVERSIBLE_ABORTED":
            if page_revoked:
                self._database_label = ""
            return True
        if outcome in {"SUCCESS", "RESTORED"}:
            try:
                self._settle_settings_for_locked_presentation()
            except (RuntimeError, ValueError):
                pass
            public_reason = (
                "CHANGE_KEY_SUCCESS"
                if outcome == "SUCCESS"
                else "CHANGE_KEY_RESTORED"
            )
            page_epoch = self.bridge.active_page_epoch
            database_label = self._database_label
            self._database_label = ""
            self._remember_change_key_connection_notice(public_reason)
            if (
                not page_revoked
                and page_epoch > 0
                and self._attached_page is not None
            ):
                self.bridge.sessionStateChangedV1.emit(
                    page_epoch,
                    0,
                    "LOCKED",
                    public_reason,
                    database_label,
                )
            self._host.on_m4_change_key_terminal(public_reason)
            return True
        self.clear_change_key_connection_notice()
        self._database_label = ""
        self._host.on_m4_change_key_terminal(
            (
                "CHANGE_KEY_RECOVERY_FAILED"
                if outcome == "RECOVERY_FAILED"
                else C49_INTERNAL_FAILURE_REASON
            )
        )
        return False

    @property
    def non_clipboard_close_complete(self) -> bool:
        return getattr(self, "_non_clipboard_close_complete", False) is True

    def close(self, reason: str = "exit") -> bool:
        if self._closed:
            return self._close_complete is True
        self._closed = True
        self.updates.close()
        self._non_clipboard_close_complete = False
        self.clear_change_key_connection_notice()
        complete = False
        other_complete = False
        session_epoch = self.bridge.active_session_epoch
        self.adapter.note_settings_session_invalidation(session_epoch)
        try:
            try:
                self._style_hints.colorSchemeChanged.disconnect(self._on_system_color_scheme_changed)
            except (RuntimeError, TypeError):
                pass
            self._gui_calls.drain_pending()
            complete = self.bridge.close_bridge(reason)
            native = self._host.security.last_result
            other_complete = bool(
                self.bridge.non_native_cleanup_complete
                and native is not None and native.authority_revoked
                and not (set(native.failed) - {"native.clipboard.force_clear"})
            )
        finally:
            page = self._attached_page
            cleanup = [
                lambda: self.adapter.clear_settings_session_invalidation(session_epoch),
                self.quickbar.close,
            ]
            if page is not None:
                cleanup.append(lambda: page.setWebChannel(None))
            for action in cleanup:
                try:
                    action()
                except Exception:
                    complete = other_complete = False
            self._attached_page = None
            self._close_complete = complete is True
            self._non_clipboard_close_complete = other_complete is True
        return self._close_complete

    def open_quickbar_from_native_hotkey(self) -> bool:
        """Consume H03 only while the current native session is authorized."""

        if not self._quickbar_intent_is_admitted(require_registration=True):
            return False
        return self._present_quickbar(require_registration=True)

    def _present_quickbar(self, *, require_registration: bool = False) -> bool:
        if not self._quickbar_intent_is_admitted(
            require_registration=require_registration,
        ):
            return False
        return self.quickbar.open_for_current_session(
            require_registration=require_registration,
        )

    def _quickbar_intent_is_admitted(
        self,
        *,
        require_registration: bool,
    ) -> bool:
        """Recheck native authority at presentation time.

        C44/C45 complete on the GUI thread, while their public S02 projection
        is deliberately queued. Both entry points therefore read current
        adapter authority; only H03 additionally checks RegisterHotKey.
        """

        if self._closed or self.bridge.active_session_epoch <= 0:
            return False
        latest = self._latest_settings_authority_projection()
        if latest is None:
            return False
        _settings_revision, settings = latest
        if settings.get("quickbarEnabled") is not True:
            return False
        if not require_registration:
            return True
        hotkey = self._host.current_native_hotkey()
        return (
            settings.get("quickbarRegistration") == "REGISTERED"
            and hotkey.registered
        )

    def _stop_quickbar_activity(self, context: object) -> None:
        reason = getattr(getattr(context, "reason", None), "value", "")
        self.quickbar.invalidate_session(
            reason if isinstance(reason, str) else "session_invalidated"
        )
        self.adapter.note_quickbar_hotkey_unregistered()

    def _invalidate_adapter_session(
        self,
        context: SecurityBoundaryContext,
    ) -> None:
        """Run potentially blocking adapter teardown behind native cover."""

        self.adapter.note_settings_session_invalidation(context.session_epoch)
        try:
            self._gui_calls.drain_pending()
            if context.session_epoch > 0:
                self.adapter.invalidate_session(context.session_epoch)
                return
            self.adapter.release_session()
        finally:
            self.adapter.clear_settings_session_invalidation(
                context.session_epoch
            )

    def _on_handshake_completed(
        self,
        _request_id: str,
        page_epoch: int,
        session_epoch: int,
        error_code: str,
        _error_argument_index: int,
        _retry_after_ms: int,
        result: object,
    ) -> None:
        settings_projection = self._settings_result_projection(result)
        if (
            error_code == "OK"
            and isinstance(result, dict)
            and page_epoch > 0
            and page_epoch == self.bridge.active_page_epoch
            and session_epoch == 0
            and result.get("pageEpoch") == page_epoch
            and result.get("sessionEpoch") == 0
            and result.get("state") == "LOCKED"
            and settings_projection is not None
        ):
            settings_revision, settings = settings_projection
            settings = self._settings_with_current_effective_theme(settings)
            self._adopt_settings_projection(settings, settings_revision)
            self._renderer_settings_revision = settings_revision
            self.clipboard.bind_page(page_epoch)
            self._host.on_m4_handshake(page_epoch)
            if self._startup_update_check:
                self.updates.start_for_startup()
            if self.change_key_connection_notice:
                # handshakeCompletedV1 的 JavaScript 处理器必须先把新网页
                # 建成 LOCKED 连接页；同一事件循环的零延迟续接只负责
                # 跨过当前信号分发顺序，回调仍复核当前 page epoch。
                QTimer.singleShot(
                    0,
                    lambda page_epoch=page_epoch:
                    self._project_change_key_connection_notice(page_epoch),
                )
            return
        if (
            page_epoch == self.bridge.active_page_epoch
            and session_epoch == 0
        ):
            self._host.on_m4_lock_failed()

    @Slot(object)
    def _on_update_state_changed(self, state) -> None:
        if not self._closed and self._attached_page is not None and self.bridge.active_page_epoch > 0:
            # 更新状态的原子读取也可能采纳另一实例提交的公开设置。
            # 只在这些设置确实变化时复用既有原生策略与网页投影。
            if self.adapter.current_settings_revision() != self._renderer_settings_revision:
                self.adapter._reconcile_quickbar_registration()
                self._reconcile_renderer_settings_from_authority()
            self.bridge.updateStateChangedV1.emit(self.bridge.active_page_epoch, state)

    def _on_open_quickbar_completed(
        self,
        _request_id: str,
        page_epoch: int,
        session_epoch: int,
        error_code: str,
        _error_argument_index: int,
        _retry_after_ms: int,
        result: object,
    ) -> None:
        if (
            error_code == "OK"
            and isinstance(result, dict)
            and not result
            and page_epoch == self.bridge.active_page_epoch
            and session_epoch == self.bridge.active_session_epoch
        ):
            self._present_quickbar()

    def _on_settings_completed(
        self,
        request_id: str,
        page_epoch: int,
        _session_epoch: int,
        error_code: str,
        _error_argument_index: int,
        _retry_after_ms: int,
        result: object,
    ) -> None:
        """Publish S02 only for one consumed native changed-commit marker."""

        if self._closed or error_code != "OK":
            return
        projection = self._settings_result_projection(result)
        if projection is None:
            return
        settings_revision, settings = projection
        publication = self.adapter.take_settings_commit_publication(
            request_id,
            settings_revision,
        )
        if (
            page_epoch <= 0
            or page_epoch != self.bridge.active_page_epoch
            or self._attached_page is None
        ):
            return
        latest = self._latest_settings_authority_projection()
        latest_revision = ""
        latest_settings: dict[str, object] | None = None
        if latest is not None:
            latest_revision, latest_settings = latest
            self._adopt_settings_projection(
                latest_settings,
                latest_revision,
            )
        if publication is None:
            return
        if not self._publication_matches_completion(
            publication,
            page_epoch,
            settings_revision,
            settings,
        ):
            return
        published_settings = self._settings_with_current_effective_theme(
            publication.settings
        )
        self.bridge.settingsChangedV1.emit(
            page_epoch,
            settings_revision,
            published_settings,
        )
        self._renderer_settings_revision = settings_revision
        if (
            latest_settings is not None
            and (
                latest_revision != settings_revision
                or latest_settings != published_settings
            )
        ):
            self.bridge.settingsChangedV1.emit(
                page_epoch,
                latest_revision,
                latest_settings,
            )
            self._renderer_settings_revision = latest_revision

    def _on_accessible_operation_completed(
        self,
        operation: str,
        _request_id: str,
        page_epoch: int,
        session_epoch: int,
        error_code: str,
        _error_argument_index: int,
        _retry_after_ms: int,
        _result: object,
        *,
        page_scoped: bool = False,
        announce_success: bool = True,
    ) -> None:
        """把一次当前产品操作结果投影到原生可访问宿主。"""

        if (
            self._closed
            or self._attached_page is None
            or page_epoch <= 0
            or page_epoch != self.bridge.active_page_epoch
            or (
                session_epoch != 0
                if page_scoped
                else (
                    session_epoch <= 0
                    or session_epoch != self.bridge.active_session_epoch
                )
            )
            or error_code in {
                "CANCELLED",
                "SESSION_REQUIRED",
                "STALE_PAGE",
                "STALE_SESSION",
            }
            or (error_code == "OK" and not announce_success)
        ):
            return
        self._host.announce_m4_accessible_operation(
            operation,
            error_code,
        )

    def _on_accessible_submit_rejected(
        self,
        command_id: CommandId,
        page_epoch: int,
        session_epoch: int,
        error_code: str,
    ) -> None:
        """只投影当前页面 C35 的固定租约过期拒绝。"""

        if (
            self._closed
            or self._attached_page is None
            or command_id is not CommandId.C35
            or page_epoch <= 0
            or page_epoch != self.bridge.active_page_epoch
            or session_epoch != 0
            or error_code != "SECRET_LEASE_EXPIRED"
        ):
            return
        self._host.announce_m4_accessible_operation(
            "GENERATED_PASSWORD_COPIED",
            error_code,
        )

    def _on_session_setting_completed(
        self,
        request_id: str,
        page_epoch: int,
        session_epoch: int,
        error_code: str,
        error_argument_index: int,
        retry_after_ms: int,
        result: object,
    ) -> None:
        """会话撤销后丢弃排队中的会话设置完成结果。"""

        if (
            session_epoch <= 0
            or session_epoch != self.bridge.active_session_epoch
        ):
            projection = self._settings_result_projection(result)
            if projection is not None:
                settings_revision, _settings = projection
                self.adapter.take_settings_commit_publication(
                    request_id,
                    settings_revision,
                )
            return
        self._on_settings_completed(
            request_id,
            page_epoch,
            session_epoch,
            error_code,
            error_argument_index,
            retry_after_ms,
            result,
        )

    def _on_system_color_scheme_changed(self, _scheme: object) -> None:
        """Refresh native AUTO authority and emit one current-page S05."""

        if self._closed:
            return
        candidate = self._effective_theme_from_qt(
            self._style_hints.colorScheme()
        )
        if candidate == self._system_effective_theme:
            return
        previous = self._system_effective_theme
        self._system_effective_theme = candidate
        try:
            refreshed = self.adapter.refresh_effective_theme_from_provider()
        except Exception:
            self._system_effective_theme = previous
            return
        if refreshed != candidate:
            self._system_effective_theme = previous
            return
        latest = self._latest_settings_authority_projection()
        if latest is None:
            return
        settings_revision, settings = latest
        if (
            settings.get("theme") != "AUTO"
            or settings.get("effectiveTheme") != candidate
        ):
            return
        self._adopt_settings_projection(settings, settings_revision)
        page_epoch = self.bridge.active_page_epoch
        if page_epoch <= 0 or self._attached_page is None:
            return
        self.bridge.systemThemeChangedV1.emit(page_epoch, candidate)

    @staticmethod
    def _effective_theme_from_qt(color_scheme: object) -> str:
        return (
            "DARK"
            if color_scheme == Qt.ColorScheme.Dark
            else "LIGHT"
        )

    @staticmethod
    def _settings_result_projection(
        result: object,
    ) -> tuple[str, dict[str, object]] | None:
        if not isinstance(result, dict):
            return None
        settings_revision = result.get("settingsRevision")
        settings = result.get("settings")
        if (
            type(settings_revision) is not str
            or not settings_revision
            or len(settings_revision) > 64
            or "\x00" in settings_revision
            or not isinstance(settings, dict)
        ):
            return None
        theme = settings.get("theme")
        effective_theme = settings.get("effectiveTheme")
        language = settings.get("language")
        ui_font_scale = settings.get("uiFontScale")
        sidebar_text = settings.get("sidebarText")
        clipboard_mode = settings.get("clipboardMode")
        clipboard_seconds = settings.get("clipboardSeconds")
        close_behavior = settings.get("closeBehavior")
        auto_lock_enabled = settings.get("autoLockEnabled")
        auto_lock_minutes = settings.get("autoLockMinutes")
        quickbar_enabled = settings.get("quickbarEnabled")
        quickbar_idle_seconds = settings.get("quickbarIdleSeconds")
        quickbar_hotkey = settings.get("quickbarHotkey")
        quickbar_registration = settings.get("quickbarRegistration")
        stale_days = settings.get("staleDays")
        if (
            theme not in {"LIGHT", "DARK", "AUTO"}
            or effective_theme not in {"LIGHT", "DARK"}
            or language not in {"ZH", "EN"}
            or ui_font_scale not in {"90", "100", "110", "125"}
            or type(sidebar_text) is not bool
            or clipboard_mode not in {"COUNTDOWN", "MANUAL"}
            or type(clipboard_seconds) is not int
            or not 5 <= clipboard_seconds <= 60
            or close_behavior not in {"TO_TRAY", "EXIT"}
            or type(auto_lock_enabled) is not bool
            or type(auto_lock_minutes) is not int
            or not 1 <= auto_lock_minutes <= 60
            or type(quickbar_enabled) is not bool
            or type(quickbar_idle_seconds) is not int
            or not 10 <= quickbar_idle_seconds <= 600
            or type(quickbar_hotkey) is not str
            or not 3 <= len(quickbar_hotkey) <= 64
            or quickbar_registration
            not in {"DISABLED", "REGISTERED", "UNAVAILABLE"}
            or type(stale_days) is not int
            or not 30 <= stale_days <= 365
            or (theme != "AUTO" and effective_theme != theme)
        ):
            return None
        return settings_revision, dict(settings)

    def _adopt_settings_projection(
        self,
        settings: dict[str, object],
        settings_revision: str,
    ) -> None:
        if (
            type(settings_revision) is not str
            or not settings_revision
            or len(settings_revision) > 64
            or "\x00" in settings_revision
        ):
            raise ValueError("settings revision is invalid")
        theme = str(settings["theme"])
        effective_theme = str(settings["effectiveTheme"])
        language = str(settings["language"])
        ui_font_scale = str(settings["uiFontScale"])
        sidebar_text = settings["sidebarText"]
        clipboard_mode = str(settings["clipboardMode"])
        clipboard_seconds = int(settings["clipboardSeconds"])
        close_behavior = str(settings["closeBehavior"])
        auto_lock_enabled = settings["autoLockEnabled"]
        auto_lock_minutes = settings["autoLockMinutes"]
        quickbar_enabled = settings["quickbarEnabled"]
        quickbar_idle_seconds = settings["quickbarIdleSeconds"]
        quickbar_hotkey = str(settings["quickbarHotkey"])
        quickbar_registration = str(settings["quickbarRegistration"])
        generator_options = dict(settings["generator"])
        self._settings_theme = theme
        self._settings_effective_theme = effective_theme
        self._settings_language = language
        self._settings_ui_font_scale = ui_font_scale
        self._settings_close_behavior = close_behavior
        self._settings_auto_lock_enabled = bool(auto_lock_enabled)
        self._settings_auto_lock_minutes = int(auto_lock_minutes)
        self._settings_quickbar_enabled = bool(quickbar_enabled)
        self._settings_quickbar_idle_seconds = int(quickbar_idle_seconds)
        self._settings_quickbar_hotkey = quickbar_hotkey
        self._settings_quickbar_registration = quickbar_registration
        self.clipboard.apply_policy_after_commit(
            clipboard_mode,
            clipboard_seconds,
        )
        self.quickbar.apply_settings(
            enabled=bool(quickbar_enabled),
            registration=quickbar_registration,
            idle_seconds=int(quickbar_idle_seconds),
            effective_theme=effective_theme,
            language=language,
            ui_font_scale=ui_font_scale,
        )
        self.editor.apply_settings(
            effective_theme,
            language,
            ui_font_scale,
            generator_options,
        )
        self.backup_window.apply_settings(effective_theme, language, ui_font_scale)
        self._host.on_m4_settings_projection(
            theme,
            effective_theme,
            language,
            ui_font_scale,
            bool(sidebar_text),
            close_behavior,
            bool(auto_lock_enabled),
            int(auto_lock_minutes),
            bool(quickbar_enabled),
            int(quickbar_idle_seconds),
            quickbar_hotkey,
            quickbar_registration,
        )

    def _settings_with_current_effective_theme(
        self,
        settings: dict[str, object],
    ) -> dict[str, object]:
        """Reconcile AUTO only after the commit proof was validated.

        A Qt color-scheme event can update the native cache while a
        C36/C37/C41/C43/C44/C45/C47
        file commit is in flight.  ``effectiveTheme`` is derived and excluded
        from ``settingsRevision``, so S02 must carry the current Qt authority
        rather than replaying the worker's older derived value.
        """

        projected = dict(settings)
        theme = projected.get("theme")
        projected["effectiveTheme"] = (
            self._system_effective_theme
            if theme == "AUTO"
            else theme
        )
        return projected

    def _latest_settings_authority_projection(
        self,
    ) -> tuple[str, dict[str, object]] | None:
        """Read and normalize one current native revision/snapshot pair."""

        projection = self._settings_result_projection(
            self.adapter.current_settings_authority()
        )
        if projection is None:
            return None
        settings_revision, settings = projection
        return (
            settings_revision,
            self._settings_with_current_effective_theme(settings),
        )

    def _settle_settings_for_locked_presentation(self) -> None:
        """Converge PAGE settings behind cover and project them before S01."""

        projection = self._settings_result_projection(
            self.adapter.settle_settings_authority()
        )
        if projection is None:
            raise RuntimeError("settled settings authority is invalid")
        settings_revision, settings = projection
        settings = self._settings_with_current_effective_theme(settings)
        self._adopt_settings_projection(settings, settings_revision)
        page_epoch = self.bridge.active_page_epoch
        if page_epoch > 0 and self._attached_page is not None:
            self.bridge.settingsChangedV1.emit(
                page_epoch,
                settings_revision,
                settings,
            )
            self._renderer_settings_revision = settings_revision

    def _reconcile_renderer_settings_from_authority(self) -> None:
        """Refresh a surviving page without reviving an old SESSION result."""

        if self._closed or self._attached_page is None:
            return
        page_epoch = self.bridge.active_page_epoch
        if page_epoch <= 0:
            return
        latest = self._latest_settings_authority_projection()
        if latest is None:
            return
        settings_revision, settings = latest
        self._adopt_settings_projection(settings, settings_revision)
        if settings_revision == self._renderer_settings_revision:
            return
        self.bridge.settingsChangedV1.emit(
            page_epoch,
            settings_revision,
            settings,
        )
        self._renderer_settings_revision = settings_revision

    @staticmethod
    def _publication_matches_completion(
        publication: SettingsCommitPublication,
        page_epoch: int,
        settings_revision: str,
        settings: dict[str, object],
    ) -> bool:
        return (
            isinstance(publication, SettingsCommitPublication)
            and publication.page_epoch == page_epoch
            and publication.settings_revision == settings_revision
            and publication.settings == settings
        )

    def _on_open_completed(
        self,
        _request_id: str,
        page_epoch: int,
        session_epoch: int,
        error_code: str,
        _error_argument_index: int,
        _retry_after_ms: int,
        result: object,
    ) -> None:
        if (
            not self._closed
            and error_code == "OK"
            and isinstance(result, dict)
            and page_epoch == self.bridge.active_page_epoch
            and session_epoch > 0
            and session_epoch == self.bridge.active_session_epoch
            and result.get("sessionEpoch") == session_epoch
            and result.get("state") == "UNLOCKED"
        ):
            if not self._host.ensure_m4_power_protection():
                return
            self.clear_change_key_connection_notice()
            database_label = result.get("databaseLabel", "")
            self._database_label = (
                database_label
                if isinstance(database_label, str)
                and "\x00" not in database_label
                and len(database_label) <= 256
                else ""
            )
            self.clipboard.bind_session(
                self.bridge.active_page_epoch,
                session_epoch,
            )
            self._host.on_m4_session_opened(session_epoch)
            if self.bridge.active_session_epoch != session_epoch:
                return
            self.quickbar.set_session_epoch(session_epoch)
            self._host.current_native_hotkey().bind_window_handle()
            self.adapter.activate_quickbar_hotkey_for_session()
            self._reconcile_renderer_settings_from_authority()

    def _on_lock_completed(
        self,
        _request_id: str,
        _page_epoch: int,
        session_epoch: int,
        error_code: str,
        _error_argument_index: int,
        _retry_after_ms: int,
        result: object,
    ) -> None:
        active_authority_is_locked = (
            self.bridge.active_session_epoch == 0
        )
        valid_locked_result = (
            error_code == "OK"
            and session_epoch == 0
            and isinstance(result, dict)
            and result.get("state") == "LOCKED"
            and result.get("sessionEpoch") == 0
        )
        if active_authority_is_locked and valid_locked_result:
            try:
                self._settle_settings_for_locked_presentation()
            except (RuntimeError, ValueError):
                pass
            self._publish_public_lock("MANUAL_LOCK")
            return
        if active_authority_is_locked:
            self._database_label = ""
            self._host.on_m4_lock_failed()

    def _publish_public_lock(self, reason: str) -> None:
        presentation_reason = {
            "MANUAL_LOCK": "MANUAL",
            "AUTO_LOCK": "AUTO",
            "RENDERER_FAILURE": "RENDERER_FAILURE",
            "SUSPEND_LOCK": "SUSPEND",
            "SESSION_INVALIDATED": "SESSION_INVALIDATED",
        }.get(reason)
        if presentation_reason is None:
            raise ValueError("unsupported public lock reason")
        page_epoch = self.bridge.active_page_epoch
        database_label = self._database_label
        self._database_label = ""
        if page_epoch > 0:
            self.clipboard.bind_page(page_epoch)
        if page_epoch > 0 and self._attached_page is not None:
            self.bridge.sessionStateChangedV1.emit(
                page_epoch,
                0,
                "LOCKED",
                reason,
                database_label,
            )
        self._host.on_m4_locked(presentation_reason)

    def session_state_changed(
        self,
        *,
        authority_serial: int,
        page_epoch: int,
        session_epoch: int,
        state: str,
        reason: str,
    ) -> None:
        """Project a bounded C49 terminal state after native cleanup."""

        del authority_serial
        try:
            self._settle_settings_for_locked_presentation()
        except (RuntimeError, ValueError):
            pass
        public_reasons = {
            "CHANGE_KEY_SUCCESS",
            "CHANGE_KEY_RESTORED",
            "CHANGE_KEY_RECOVERY_FAILED",
        }
        valid_public = (
            page_epoch > 0
            and page_epoch == self.bridge.active_page_epoch
            and session_epoch == 0
            and state == "LOCKED"
            and reason in public_reasons
        )
        database_label = self._database_label
        self._database_label = ""
        if valid_public:
            self.clipboard.bind_page(page_epoch)
            if reason in {
                "CHANGE_KEY_SUCCESS",
                "CHANGE_KEY_RESTORED",
            }:
                self._remember_change_key_connection_notice(reason)
            else:
                self.clear_change_key_connection_notice()
            self.bridge.sessionStateChangedV1.emit(
                page_epoch,
                0,
                "LOCKED",
                reason,
                database_label,
            )
            self._host.on_m4_change_key_terminal(reason)
            return

        # INTERNAL_FAILURE and malformed native metadata never become S01.
        # The opaque native curtain remains the only observable surface.
        self.clear_change_key_connection_notice()
        self._host.on_m4_change_key_terminal(C49_INTERNAL_FAILURE_REASON)

    def _on_clipboard_state_changed(
        self,
        page_epoch: int,
        session_epoch: int,
        content_kind: str,
        mode: str,
        remaining_seconds: int,
        owned: bool,
    ) -> None:
        if (
            page_epoch <= 0
            or page_epoch != self.bridge.active_page_epoch
            or session_epoch != self.bridge.active_session_epoch
            or (
                session_epoch == 0
                and content_kind not in {"PASSWORD", "NONE"}
            )
        ):
            return
        self.bridge.clipboardStateChangedV1.emit(
            page_epoch,
            session_epoch,
            content_kind,
            mode,
            remaining_seconds,
            owned,
        )

    def _on_change_key_progress(
        self,
        request_id: str,
        page_epoch: int,
        session_epoch: int,
        phase: str,
        completed: int,
        total: int,
    ) -> None:
        allowed_phases = {
            "QUEUED",
            "DERIVING_KEY",
            "READING",
            "VALIDATING",
            "ENCRYPTING",
            "WRITING",
            "COMMITTING",
            "RESTORING",
            "FINALIZING",
        }
        if (
            not isinstance(request_id, str)
            or not request_id
            or len(request_id) > 64
            or page_epoch <= 0
            or page_epoch != self.bridge.active_page_epoch
            or session_epoch <= 0
            or session_epoch != self.bridge.active_session_epoch
            or phase not in allowed_phases
            or type(completed) is not int
            or type(total) is not int
            or completed < 0
            or total < 0
            or completed > total
            or total > 1_000_000_000
        ):
            return
        self.bridge.requestProgressV1.emit(
            page_epoch,
            session_epoch,
            request_id,
            phase,
            completed,
            total,
        )


__all__ = [
    "ProductRuntime",
    "RendererBridgeSecurityPort",
]
