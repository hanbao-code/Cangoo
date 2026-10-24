"""接收已验证运行路径的 M4 产品宿主。"""

from __future__ import annotations

from enum import Enum
from typing import Callable

from PySide6.QtCore import QEvent, Qt, QTimer, Signal
from PySide6.QtGui import (
    QAccessible,
    QAccessibleAnnouncementEvent,
    QHideEvent,
    QShowEvent,
)
from PySide6.QtWebEngineCore import QWebEnginePage
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QApplication

from desktop.host.native_capabilities import (
    HotkeyBackend,
    NativeClipboard,
    NativeHotkey,
)
from desktop.host.power import NativeIdleMonitor
from desktop.host.processing_curtain import (
    ProcessingCurtainCoordinator,
    ProcessingCurtainProcess,
    ProcessingCurtainToken,
)
from desktop.host.renderer_lifecycle import (
    RendererDecision,
    RendererLifecycleState,
)
from desktop.host.renderer_recovery import (
    RendererRecoverySurfaceMode,
    RendererRecoveryViewState,
)
from desktop.host.security_lifecycle import (
    SecurityBoundaryContext,
    SecurityBoundaryReason,
    SecurityCleanupPhase,
)
from desktop.host.tray import TrayController, TraySessionState
from desktop.host.web_profile import AppPage, configure_page_settings
from desktop.host.window import HostWindow

from .database_targets import (
    DatabaseTargetSelector,
    NativeDatabaseTargetSelector,
)
from .backup import BackupFileSelector, NativeBackupFileSelector
from desktop.runtime_paths import RuntimePaths
from .quickbar import QuickbarFocusPort
from .resources import M4ResourceCatalog
from .runtime import M4BridgeRuntime


_M4_RENDERER_PRESENTATION_ARM = """
(() => {
  const generation = __PDM_GENERATION__;
  const presentationToken = __PDM_PRESENTATION_TOKEN__;
  const isCurrent = () => {
    const current = window.__pdmNativePresentation;
    return Boolean(
      current
      && current.generation === generation
      && current.presentationToken === presentationToken
    );
  };
  const readSample = () => {
    if (
      !isCurrent()
      || document.visibilityState !== 'visible'
      || !window.pdmM4
      || typeof window.pdmM4.lockedConnectionPresentationSample
        !== 'function'
    ) return '';
    try {
      return __PDM_LOCKED_CONNECTION_SAMPLE__;
    } catch (_error) {
      return '';
    }
  };
  const scheduleNext = () => {
    if (!isCurrent()) return;
    window.requestAnimationFrame(() => {
      if (!isCurrent()) return;
      const sample = readSample();
      if (!isCurrent()) return;
      const current = window.__pdmNativePresentation;
      if (typeof sample === 'string' && sample !== '') {
        if (current.previousSample === sample) {
          if (!isCurrent()) return;
          current.ready = true;
          return;
        }
        current.previousSample = sample;
      } else {
        current.previousSample = '';
      }
      if (!isCurrent()) return;
      scheduleNext();
    });
  };
  window.__pdmNativePresentation = {
    generation,
    presentationToken,
    ready: false,
    previousSample: '',
  };
  scheduleNext();
  return `${generation}:${presentationToken}`;
})()
"""

_M4_RENDERER_PRESENTATION_PROBE = """
(() => {
  const current = window.__pdmNativePresentation;
  return Boolean(
    current
    && current.generation === __PDM_GENERATION__
    && current.presentationToken === __PDM_PRESENTATION_TOKEN__
    && current.ready === true
    && document.visibilityState === 'visible'
    && window.pdmM4
    && typeof window.pdmM4.isLockedConnectionReady === 'function'
    && __PDM_LOCKED_CONNECTION_READY__
  );
})()
"""

_M4_LOCK_REASONS = frozenset(
    {
        "MANUAL",
        "AUTO",
        "SUSPEND",
        "RENDERER_FAILURE",
        "C49_SUCCESS",
        "C49_RESTORED",
    }
)
_M4_C49_FAILURE_REASONS = frozenset(
    {"CHANGE_KEY_RECOVERY_FAILED", "C49_INTERNAL_FAILURE"}
)
_PROCESSING_SECURITY_REASONS = frozenset(
    {
        SecurityBoundaryReason.MANUAL_LOCK,
        SecurityBoundaryReason.AUTO_LOCK,
        SecurityBoundaryReason.RENDERER_FAILURE,
        SecurityBoundaryReason.SUSPEND_LOCK,
        SecurityBoundaryReason.CHANGE_KEY_SUCCESS,
        SecurityBoundaryReason.CHANGE_KEY_RESTORED,
    }
)
_PROCESSING_FAILURE_STATES = frozenset(
    {
        RendererRecoveryViewState.RECOVERY_AVAILABLE,
        RendererRecoveryViewState.BLOCKED,
        RendererRecoveryViewState.DATABASE_RECOVERY_FAILED,
    }
)
_INITIAL_SURFACE_PROBE_TIMEOUT_MS = 2_000

_M4_CURTAIN_SURFACE_MODES = {
    RendererRecoveryViewState.CLIPBOARD_EXIT_RETRYING: RendererRecoverySurfaceMode.FULL_NATIVE,
    RendererRecoveryViewState.CLIPBOARD_EXIT_BLOCKED: RendererRecoverySurfaceMode.FULL_NATIVE,
    RendererRecoveryViewState.STARTING:
        RendererRecoverySurfaceMode.CONTENT_PROCESSING,
    RendererRecoveryViewState.TRANSITION:
        RendererRecoverySurfaceMode.CONTENT_PROCESSING,
    RendererRecoveryViewState.SECURING:
        RendererRecoverySurfaceMode.FULL_NATIVE,
    RendererRecoveryViewState.LOCKED:
        RendererRecoverySurfaceMode.FULL_NATIVE,
    RendererRecoveryViewState.RECOVERY_AVAILABLE:
        RendererRecoverySurfaceMode.FULL_NATIVE,
    RendererRecoveryViewState.REBUILDING:
        RendererRecoverySurfaceMode.FULL_NATIVE,
    RendererRecoveryViewState.BLOCKED:
        RendererRecoverySurfaceMode.FULL_NATIVE,
    RendererRecoveryViewState.DATABASE_RECOVERY_FAILED:
        RendererRecoverySurfaceMode.FULL_NATIVE,
    RendererRecoveryViewState.STARTUP_BLOCKED:
        RendererRecoverySurfaceMode.FULL_NATIVE,
    RendererRecoveryViewState.RUNTIME_PATH_BLOCKED:
        RendererRecoverySurfaceMode.FULL_NATIVE,
    RendererRecoveryViewState.INSTALLATION_INCOMPLETE:
        RendererRecoverySurfaceMode.FULL_NATIVE,
}

_ACCESSIBLE_OPERATION_TEXT = {
    "PASSWORD_ADDED": ("已新增密码记录", "Password record added"),
    "PASSWORD_UPDATED": ("已更新密码记录", "Password record updated"),
    "PASSWORD_DELETED": ("密码记录已删除", "Password record deleted"),
    "NOTE_ADDED": ("已新增记事", "Note added"),
    "NOTE_SAVED": ("记事已保存", "Note saved"),
    "NOTE_DELETED": ("记事已删除", "Note deleted"),
    "PASSWORD_GENERATED": ("密码已生成", "Password generated"),
    "ACCOUNT_COPIED": ("账号已复制", "Account copied"),
    "PASSWORD_COPIED": ("密码已复制", "Password copied"),
    "TOTP_COPIED": ("验证码已复制", "Verification code copied"),
    "CLIPBOARD_CLEARED": ("剪贴板已清空", "Clipboard cleared"),
    "GENERATED_PASSWORD_COPIED": (
        "生成的密码已复制",
        "Generated password copied",
    ),
    "BACKUP_EXPORTED": (
        "加密备份已导出",
        "Encrypted backup exported",
    ),
    "BACKUP_IMPORTED": (
        "备份导入处理完成",
        "Backup import processing completed",
    ),
    "KEY_CHANGED": (
        "密码修改成功，请重新连接数据库",
        "Password changed. Reconnect to the database",
    ),
}
_ACCESSIBLE_ERROR_TEXT = {
    "NOT_FOUND": (
        "当前记录已不存在，请按页面提示处理",
        "The record no longer exists. Follow the page instructions",
    ),
    "REQUEST_BUSY": (
        "已有操作正在进行，请稍候",
        "Another operation is in progress",
    ),
    "CLIPBOARD_UNAVAILABLE": (
        "剪贴板暂时不可用，请重试",
        "The clipboard is unavailable. Try again",
    ),
    "TOTP_UNAVAILABLE": (
        "验证码暂时不可用，未复制",
        "The verification code is unavailable and was not copied",
    ),
    "DATABASE_IO_FAILED": (
        "数据库访问失败，操作未完成，请重试",
        "Database access failed. The operation did not complete. Try again",
    ),
    "PLATFORM_CONFLICT": (
        "记录名称已存在，请使用不同名称",
        "The record name already exists. Use a different name",
    ),
    "PASSWORD_STRENGTH_FAILED": (
        "密码强度检测失败，记录未保存",
        "Password strength check failed. The record was not saved",
    ),
    "INVALID_ARGUMENT": (
        "输入或请求状态无效，请检查后重试",
        "The input or request state is invalid. Check it and retry",
    ),
    "REQUEST_TOO_LARGE": (
        "当前请求过大，请缩小范围后重试",
        "The request is too large. Narrow it and retry",
    ),
    "REVISION_CONFLICT": (
        "记录已发生变化，操作未完成，请按页面提示处理",
        "The record changed. The operation did not complete. Follow the page instructions",
    ),
    "INTERNAL_FAILURE": (
        "操作未完成，请重试",
        "The operation did not complete. Try again",
    ),
}
_ACCESSIBLE_GENERIC_FAILURE = (
    "操作未完成，请重试",
    "The operation did not complete. Try again",
)
_ACCESSIBLE_OPERATION_ERROR_TEXT = {
    ("ACCOUNT_COPIED", "EMPTY_FIELD"): (
        "账号为空，未复制",
        "The account is empty and was not copied",
    ),
    ("PASSWORD_COPIED", "EMPTY_FIELD"): (
        "密码为空，未复制",
        "The password is empty and was not copied",
    ),
    ("GENERATED_PASSWORD_COPIED", "SECRET_LEASE_EXPIRED"): (
        "生成的密码已过期，请重新生成",
        "The generated password expired. Generate a new one",
    ),
    ("BACKUP_IMPORTED", "BACKUP_AUTH_FAILED"): (
        "备份密码不正确，请重新输入并预览",
        "The backup password is incorrect. Enter it again and preview",
    ),
    ("BACKUP_IMPORTED", "BACKUP_INVALID"): (
        "备份无效或已损坏，请重新选择",
        "The backup is invalid or damaged. Select it again",
    ),
    ("BACKUP_IMPORTED", "BACKUP_LIMIT_EXCEEDED"): (
        "备份过大，无法处理",
        "The backup is too large to process",
    ),
    ("BACKUP_IMPORTED", "SELECTION_EXPIRED"): (
        "备份选择已过期，请重新选择",
        "The backup selection expired. Select it again",
    ),
    ("BACKUP_IMPORTED", "BACKUP_CONFLICTS_UNRESOLVED"): (
        "仍有未处理的冲突，请先完成选择",
        "Some conflicts are unresolved. Complete the choices first",
    ),
    ("BACKUP_EXPORTED", "BACKUP_TARGET_IS_DATABASE"): (
        "不能用备份覆盖当前数据库，请选择其他保存位置",
        "A backup cannot overwrite the current database. Choose another destination",
    ),
    ("BACKUP_EXPORTED", "SELECTION_EXPIRED"): (
        "备份保存位置授权已过期，请重新选择",
        "The backup destination expired. Select it again",
    ),
}


class _M4SuspendLockState(str, Enum):
    """One suspend transaction; COMPLETE must never be replayed."""

    NONE = "none"
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"
    FAILED = "failed"


class M4HostWindow(HostWindow):
    """M4 产品宿主；构造时必须显式注入已验证的运行路径。"""

    # 宿主在后台准备好首个安全表面后才允许顶层窗口出现。
    defers_initial_show = True
    initial_surface_ready = Signal()

    def __init__(
        self,
        isolation: RuntimePaths,
        *,
        target_selector: DatabaseTargetSelector | None = None,
        native_clipboard: NativeClipboard | None = None,
        hotkey_backend: HotkeyBackend | None = None,
        tray_controller_factory: (
            Callable[[HostWindow], TrayController] | None
        ) = None,
        tray_failure_confirmation: Callable[[str], bool] | None = None,
        idle_monitor_factory: (
            Callable[[HostWindow], NativeIdleMonitor] | None
        ) = None,
        quickbar_focus_port: QuickbarFocusPort | None = None,
        backup_selector: BackupFileSelector | None = None,
        standard_window_frame: bool = False,
        startup_update_check: bool = False,
        update_client_factory=None,
    ) -> None:
        if not isinstance(isolation, RuntimePaths):
            raise TypeError("M4HostWindow requires validated runtime paths")
        self._m4_isolation = isolation
        self._m4_target_selector = target_selector
        self._m4_hotkey_backend = hotkey_backend
        self._m4_quickbar_focus_port = quickbar_focus_port
        self._m4_backup_selector = backup_selector
        self._m4_startup_update_check = startup_update_check
        self._m4_update_client_factory = update_client_factory
        self._m4_runtime: M4BridgeRuntime | None = None
        self._m4_direct_transfer = None
        self._m4_transfer_core = None
        self._m4_transfer_hold_epoch = 0
        self._m4_auto_lock_enabled = True
        self._m4_auto_lock_minutes = 5
        self._m4_suspend_lock_state = _M4SuspendLockState.NONE
        self._m4_power_suspended = False
        self._m4_last_security_resume_count = -1
        self._m4_suspended_canvas_probe_generation = 0
        self._m4_suspended_initial_probe_generation = 0
        self._m4_suspended_initial_processing_token: (
            ProcessingCurtainToken | None
        ) = None
        self._m4_database_recovery_failed = False
        self._initial_surface_ready_emitted = False
        self._initial_static_probe_generation = 0
        self._initial_static_probe_token = 0
        self._initial_static_probe_attempts = 0
        self._locked_presentation_ready_token: (
            ProcessingCurtainToken | None
        ) = None
        self._processing_curtain = ProcessingCurtainCoordinator()
        self._processing_curtain_token: ProcessingCurtainToken | None = None
        self._processing_curtain_presentation_token: (
            ProcessingCurtainToken | None
        ) = None
        self._processing_curtain_presentation_generation = 0
        self._processing_curtain_presentation_serial = 0
        self._processing_curtain_wakeup_token: (
            ProcessingCurtainToken | None
        ) = None
        self._processing_curtain_wakeup_generation = 0
        self._processing_curtain_wakeup_serial = 0
        # M4 与宿主清理束共享一个稳定的剪贴板权威，确保原生复制与每条
        # H06 清理路径操作同一个对象。
        self._m4_native_clipboard = native_clipboard or NativeClipboard()
        super().__init__(
            M4ResourceCatalog(),
            enable_tray=True,
            close_to_tray=True,
            tray_controller_factory=tray_controller_factory,
            tray_failure_confirmation=tray_failure_confirmation,
            show_tray_on_init=False,
            standard_window_frame=standard_window_frame,
        )
        self.native.quickbar_requested.connect(
            self._on_m4_native_quickbar_requested
        )
        if self.tray is not None:
            try:
                self.tray.show()
            except Exception:
                # A later TO_TRAY close retries the recoverable-entry check;
                # construction must not publish exception text or exit.
                pass
        self.native.clipboard = self._m4_native_clipboard
        monitor = (
            idle_monitor_factory(self)
            if idle_monitor_factory is not None
            else NativeIdleMonitor(self)
        )
        if not isinstance(monitor, NativeIdleMonitor):
            raise TypeError("idle_monitor_factory returned an invalid monitor")
        self._m4_idle_monitor = monitor
        self._m4_idle_monitor.timeout_reached.connect(
            self._on_m4_idle_timeout
        )
        self.security.register(
            SecurityCleanupPhase.STOP_ACTIVITY,
            "m4.idle_monitor.stop",
            lambda _context: self._m4_idle_monitor.disarm_session(),
        )
        self._m4_idle_monitor.configure_policy(
            self._m4_auto_lock_enabled,
            self._m4_auto_lock_minutes,
        )
        self._processing_curtain_token = self._processing_curtain.begin(
            ProcessingCurtainProcess.STARTUP,
            self._renderer_page_generation,
            presentable=self._window_is_presentable_for_processing(),
        )
        self.view.setEnabled(False)
        self.view.hide()
        self._show_renderer_curtain(
            RendererRecoveryViewState.STARTING
        )

    @property
    def bridge_attached(self) -> bool:
        runtime = self._m4_runtime
        return runtime is not None and runtime.attached

    @property
    def m4_runtime(self) -> M4BridgeRuntime:
        runtime = self._m4_runtime
        if runtime is None:
            raise RuntimeError("M4 runtime has not been initialized")
        return runtime

    @property
    def m4_idle_monitor(self) -> NativeIdleMonitor:
        return self._m4_idle_monitor

    def _prepare_candidate_page(self, page: QWebEnginePage) -> None:
        runtime = self._m4_runtime
        if runtime is None:
            if self._m4_hotkey_backend is not None:
                self.native.hotkey = NativeHotkey(
                    self,
                    self._m4_hotkey_backend,
                )
            selector = self._m4_target_selector
            if selector is None:
                selector = NativeDatabaseTargetSelector(
                    self,
                    self._m4_isolation,
                )
            self._m4_target_selector = selector
            backup_selector = self._m4_backup_selector
            if backup_selector is None:
                backup_selector = NativeBackupFileSelector(
                    self,
                    self._m4_isolation.database_chooser_directory,
                )
            self._m4_backup_selector = backup_selector
            runtime = M4BridgeRuntime(
                self,
                self._m4_isolation,
                selector,
                self,
                quickbar_focus_port=self._m4_quickbar_focus_port,
                backup_selector=backup_selector,
                startup_update_check=self._m4_startup_update_check,
                update_client_factory=self._m4_update_client_factory,
            )
            self._m4_runtime = runtime
            from .direct_transfer import DirectTransferController
            from .direct_transfer_window import DirectTransferWindowController
            from desktop.host.lan_access import LanAccess

            authority = lambda: (runtime.active_page_epoch, runtime.active_session_epoch)
            busy = lambda: runtime.backup_window.window is not None or runtime.adapter.editor_occupancy is not None
            core = DirectTransferController(runtime.adapter, authority=authority,
                lock_monitor_ready=self._transfer_lock_monitor_ready, busy=busy,
                hold=self._set_transfer_hold, adopt_received=self._adopt_transfer_preview, parent=self,
                lan_access=LanAccess(self))
            self._m4_transfer_core = core
            transfer = DirectTransferWindowController(core, authority=authority, busy=busy,
                view_factory=lambda: self.create_m4_editor_view("/transfer.html"),
                renderer_failed=runtime._on_editor_renderer_failed, parent=self)
            self._m4_direct_transfer = transfer
            runtime.channel.registerObject("pdmTransferLauncherV1", transfer.launcher)
            runtime.backup_window.bind_transfer_guard(lambda: transfer.window is not None)
            runtime.backup_window.receivedPreviewClosed.connect(transfer.return_to_start)
            runtime.backup_window.operationCompletedV1.connect(self._transfer_import_completed)
            self.security.register(SecurityCleanupPhase.STOP_ACTIVITY, "m4.direct_transfer.stop",
                                   lambda _context: core.stop_for_security())
            self.security.register(SecurityCleanupPhase.CONCEAL_RENDERER, "m4.direct_transfer.conceal",
                                   lambda _context: transfer.conceal())
            self.security.register(SecurityCleanupPhase.CLEAR_NATIVE_SECRETS, "m4.direct_transfer.clear",
                                   lambda _context: transfer.close_for_security())
            self.renderer_lifecycle.bind_security_boundary(
                runtime.renderer_security_port
            )
        runtime.attach_page(page)
        self.chrome_input.set_copy_shortcut_handlers(
            runtime.note_password_input_copy_interaction,
            runtime.request_password_input_copy,
        )

    def _retire_candidate_page(self, page: QWebEnginePage) -> None:
        runtime = self._m4_runtime
        if runtime is not None:
            runtime.detach_page(page)

    def _renderer_security_epochs(self) -> tuple[int, int]:
        runtime = self._m4_runtime
        if runtime is None:
            return 0, 0
        return (
            runtime.active_page_epoch,
            runtime.active_session_epoch,
        )

    def m4_copy_focus_is_current(self, page: QWebEnginePage) -> bool:
        focused = QApplication.focusWidget()
        return bool(
            page is self.web.page
            and self.view.page() is page
            and self.view.isEnabled()
            and focused is not None
            and self.chrome_input._belongs_to_view(focused)
        )

    def _renderer_presentation_arm_source(
        self,
        generation: int,
        presentation_token: int,
    ) -> str:
        token = self._processing_curtain_token
        if (
            not isinstance(token, ProcessingCurtainToken)
            or token.process not in {
                ProcessingCurtainProcess.STARTUP,
                ProcessingCurtainProcess.SECURITY_LOCK,
            }
        ):
            return HostWindow._renderer_presentation_arm_source(
                self,
                generation,
                presentation_token,
            )
        return (
            _M4_RENDERER_PRESENTATION_ARM.replace(
                "__PDM_GENERATION__",
                str(generation),
            ).replace(
                "__PDM_PRESENTATION_TOKEN__",
                str(presentation_token),
            ).replace(
                "__PDM_LOCKED_CONNECTION_SAMPLE__",
                self._locked_connection_presentation_sample_expression(),
            )
        )

    def _renderer_presentation_probe_source(
        self,
        generation: int,
        presentation_token: int,
    ) -> str:
        return (
            _M4_RENDERER_PRESENTATION_PROBE.replace(
                "__PDM_GENERATION__",
                str(generation),
            ).replace(
                "__PDM_PRESENTATION_TOKEN__",
                str(presentation_token),
            ).replace(
                "__PDM_LOCKED_CONNECTION_READY__",
                M4HostWindow._locked_connection_ready_expression(self),
            )
        )

    def _locked_connection_presentation_sample_expression(self) -> str:
        runtime = self._m4_runtime
        reason = (
            runtime.change_key_connection_notice
            if runtime is not None
            else ""
        )
        if reason in {
            "CHANGE_KEY_SUCCESS",
            "CHANGE_KEY_RESTORED",
        }:
            return (
                "window.pdmM4.lockedConnectionPresentationSample("
                f"'{reason}')"
            )
        return "window.pdmM4.lockedConnectionPresentationSample()"

    def _locked_connection_ready_expression(self) -> str:
        runtime = self._m4_runtime
        reason = (
            runtime.change_key_connection_notice
            if runtime is not None
            else ""
        )
        if reason in {
            "CHANGE_KEY_SUCCESS",
            "CHANGE_KEY_RESTORED",
        }:
            return f"window.pdmM4.isLockedConnectionReady('{reason}')"
        return "window.pdmM4.isLockedConnectionReady()"

    def _renderer_curtain_surface_mode(
        self,
        state: RendererRecoveryViewState,
    ) -> RendererRecoverySurfaceMode:
        """正常启动和锁定保留原标题栏，启动另遮住尚未交付的侧栏。"""

        if not isinstance(state, RendererRecoveryViewState):
            raise TypeError("renderer curtain state must be fixed")
        try:
            return _M4_CURTAIN_SURFACE_MODES[state]
        except KeyError:
            raise RuntimeError(
                f"renderer curtain state is not classified: {state!r}"
            ) from None

    def _renderer_curtain_is_installed_for_presentation(self) -> bool:
        token = self._processing_curtain_token
        expected_state = None
        if isinstance(token, ProcessingCurtainToken):
            expected_state = {
                ProcessingCurtainProcess.STARTUP: (
                    RendererRecoveryViewState.STARTING
                ),
                ProcessingCurtainProcess.SECURITY_LOCK: (
                    RendererRecoveryViewState.TRANSITION
                ),
                ProcessingCurtainProcess.RENDERER_REBUILD: (
                    RendererRecoveryViewState.REBUILDING
                ),
            }.get(token.process)
        return bool(
            isinstance(token, ProcessingCurtainToken)
            and not self.renderer_curtain.isHidden()
            and self.renderer_curtain.state is expected_state
        )

    def _window_is_presentable_for_processing(self) -> bool:
        return bool(
            self.isVisible()
            and not self.isMinimized()
            and not self._m4_power_suspended
            and not self._tray_hide_settling
        )

    def _sync_transient_toast_presentation(self) -> bool:
        if getattr(self, "_exit_cleanup_started", False):
            return False
        try:
            presentable = bool(
                self._window_is_presentable_for_processing()
                and self.renderer_lifecycle.state
                is RendererLifecycleState.ACTIVE
                and self.view.isVisible()
                and not self.renderer_curtain.isVisible()
            )
        except (AttributeError, RuntimeError):
            return False
        page = getattr(getattr(self, "web", None), "page", None)
        if page is None:
            return False
        source = (
            "Boolean(window.pdmM4 "
            "&& window.pdmM4.setHostWindowPresentable "
            "&& window.pdmM4.setHostWindowPresentable("
            f"{'true' if presentable else 'false'}))"
        )
        try:
            page.runJavaScript(source)
        except RuntimeError:
            return False
        return presentable

    def _renderer_presentation_must_wait(self, generation: int) -> bool:
        token = self._processing_curtain_token
        return bool(
            generation == self._renderer_page_generation
            and isinstance(token, ProcessingCurtainToken)
            and not self._window_is_presentable_for_processing()
        )

    def _canvas_probe_must_wait(self, generation: int) -> bool:
        """睡眠期间保留真实加载结果，但不启动新的两秒画布检查。"""

        if not self._m4_power_suspended:
            return False
        if generation == self._renderer_page_generation:
            self._m4_suspended_canvas_probe_generation = generation
            self._m4_suspended_initial_probe_generation = 0
            self._m4_suspended_initial_processing_token = None
        return True

    def _clear_suspended_technical_probes(self) -> None:
        self._m4_suspended_canvas_probe_generation = 0
        self._m4_suspended_initial_probe_generation = 0
        self._m4_suspended_initial_processing_token = None

    def _suspend_technical_probes(self) -> None:
        """只作废睡眠前的网页检查身份，不重建处理过程。"""

        M4HostWindow._clear_suspended_technical_probes(self)
        generation = getattr(self, "_renderer_page_generation", 0)
        if type(generation) is not int or generation <= 0:
            return
        if self._canvas_probe_is_current(
            generation,
            self._canvas_probe_token,
        ):
            self._m4_suspended_canvas_probe_generation = generation
            self._clear_canvas_probe()
            return
        processing_token = self._processing_curtain_token
        if (
            isinstance(processing_token, ProcessingCurtainToken)
            and self._initial_surface_probe_is_current(
                generation,
                self._initial_static_probe_token,
                processing_token,
            )
        ):
            self._m4_suspended_initial_probe_generation = generation
            self._m4_suspended_initial_processing_token = processing_token
            self._clear_initial_surface_probe()

    def _resume_suspended_technical_probes(self) -> None:
        """恢复后至多重启一个仍属于当前页面的技术检查。"""

        if self._m4_power_suspended:
            return
        canvas_generation = getattr(
            self,
            "_m4_suspended_canvas_probe_generation",
            0,
        )
        initial_generation = getattr(
            self,
            "_m4_suspended_initial_probe_generation",
            0,
        )
        initial_processing_token = getattr(
            self,
            "_m4_suspended_initial_processing_token",
            None,
        )
        M4HostWindow._clear_suspended_technical_probes(self)
        generation = getattr(self, "_renderer_page_generation", 0)
        if type(generation) is not int or generation <= 0:
            return
        if (
            canvas_generation == generation
            and self.load_ok
            and self.renderer_lifecycle.state
            in {
                RendererLifecycleState.STARTING,
                RendererLifecycleState.RECOVERING,
            }
        ):
            self._start_canvas_probe(generation)
            return
        if (
            initial_generation == generation
            and initial_processing_token is self._processing_curtain_token
            and isinstance(initial_processing_token, ProcessingCurtainToken)
            and initial_processing_token.process
            is ProcessingCurtainProcess.STARTUP
            and not self._initial_surface_ready_emitted
            and self.ready
            and self.renderer_lifecycle.state is RendererLifecycleState.ACTIVE
        ):
            self._start_initial_surface_probe(
                generation,
                initial_processing_token,
            )

    def _prepare_renderer_page_for_presentation(self, generation: int) -> bool:
        """准备用户可见交接，并把协调器切入可呈现阶段。"""

        return M4HostWindow._prepare_renderer_page_for_processing(
            self,
            generation,
            enter_visible_stage=True,
        )

    def _prepare_renderer_page_for_initial_surface(
        self,
        generation: int,
    ) -> bool:
        """仅为隐藏首表面静态预检激活页面，不创建可见呈现阶段。"""

        return M4HostWindow._prepare_renderer_page_for_processing(
            self,
            generation,
            enter_visible_stage=False,
        )

    def _prepare_renderer_page_for_processing(
        self,
        generation: int,
        *,
        enter_visible_stage: bool,
    ) -> bool:
        if (
            generation != self._renderer_page_generation
            or not self._renderer_curtain_is_installed_for_presentation()
        ):
            return False
        token = self._processing_curtain_token
        if enter_visible_stage:
            if not self._window_is_presentable_for_processing():
                return False
        elif (
            not isinstance(token, ProcessingCurtainToken)
            or token.process is not ProcessingCurtainProcess.STARTUP
            or self._initial_surface_ready_emitted
            or self._window_is_presentable_for_processing()
        ):
            return False
        page = self.web.page
        try:
            if enter_visible_stage and (
                not isinstance(token, ProcessingCurtainToken)
                or not self._processing_curtain.set_presentable(token, True)
            ):
                return False
            page.setVisible(True)
            lifecycle_state = page.lifecycleState()
            if lifecycle_state is QWebEnginePage.LifecycleState.Discarded:
                return False
            if lifecycle_state is not QWebEnginePage.LifecycleState.Active:
                page.setLifecycleState(QWebEnginePage.LifecycleState.Active)
            if page.lifecycleState() is not QWebEnginePage.LifecycleState.Active:
                return False
            if not page.isVisible():
                return False
            self.view.setEnabled(False)
            self.view.show()
            self.renderer_curtain.raise_()
            return True
        except (RuntimeError, TypeError):
            return False

    def _begin_renderer_presentation(self, generation: int) -> None:
        """启动首帧先在隐藏窗口完成静态锁定页检查。"""

        token = self._processing_curtain_token
        if (
            isinstance(token, ProcessingCurtainToken)
            and token.process is ProcessingCurtainProcess.STARTUP
            and not self._initial_surface_ready_emitted
            and not self._window_is_presentable_for_processing()
        ):
            self._start_initial_surface_probe(generation, token)
            return
        super()._begin_renderer_presentation(generation)

    def _initial_surface_probe_is_current(
        self,
        generation: int,
        token: int,
        processing_token: ProcessingCurtainToken,
    ) -> bool:
        return bool(
            not self._initial_surface_ready_emitted
            and generation == self._initial_static_probe_generation
            and generation == self._renderer_page_generation
            and token == self._initial_static_probe_token
            and processing_token is self._processing_curtain_token
            and processing_token.process is ProcessingCurtainProcess.STARTUP
            and self.renderer_lifecycle.state
            is RendererLifecycleState.ACTIVE
            and self._renderer_curtain_is_installed_for_presentation()
        )

    def _clear_initial_surface_probe(self) -> None:
        """作废首表面预检的迟到网页回调和截止回调。"""

        self._initial_static_probe_generation = 0
        self._initial_static_probe_attempts = 0

    def _start_initial_surface_probe(
        self,
        generation: int,
        processing_token: ProcessingCurtainToken,
    ) -> None:
        if (
            generation != self._renderer_page_generation
            or processing_token is not self._processing_curtain_token
            or processing_token.process is not ProcessingCurtainProcess.STARTUP
            or self._initial_surface_ready_emitted
        ):
            return
        if self._m4_power_suspended:
            self._m4_suspended_canvas_probe_generation = 0
            self._m4_suspended_initial_probe_generation = generation
            self._m4_suspended_initial_processing_token = processing_token
            return
        if self._initial_static_probe_generation == generation:
            return
        self._initial_static_probe_token += 1
        token = self._initial_static_probe_token
        self._initial_static_probe_generation = generation
        self._initial_static_probe_attempts = 0
        QTimer.singleShot(
            0,
            lambda generation=generation, token=token,
            processing_token=processing_token:
            self._probe_initial_surface(
                generation,
                token,
                processing_token,
            ),
        )
        QTimer.singleShot(
            _INITIAL_SURFACE_PROBE_TIMEOUT_MS,
            lambda generation=generation, token=token,
            processing_token=processing_token:
            self._on_initial_surface_probe_timeout(
                generation,
                token,
                processing_token,
            ),
        )

    def _probe_initial_surface(
        self,
        generation: int,
        token: int,
        processing_token: ProcessingCurtainToken,
    ) -> None:
        if not self._initial_surface_probe_is_current(
            generation,
            token,
            processing_token,
        ):
            return
        if not self._prepare_renderer_page_for_initial_surface(generation):
            self._fail_initial_surface(
                generation,
                token,
                processing_token,
            )
            return
        self._initial_static_probe_attempts += 1
        self.web.page.runJavaScript(
            "Boolean(window.pdmM4 && window.pdmM4.isLockedConnectionReady "
            "&& window.pdmM4.isLockedConnectionReady())",
            lambda ready, generation=generation, token=token,
            processing_token=processing_token:
            self._on_initial_surface_probe(
                generation,
                token,
                processing_token,
                ready,
            ),
        )

    def _on_initial_surface_probe(
        self,
        generation: int,
        token: int,
        processing_token: ProcessingCurtainToken,
        ready: object,
    ) -> None:
        if not self._initial_surface_probe_is_current(
            generation,
            token,
            processing_token,
        ):
            return
        if ready is True:
            self._clear_initial_surface_probe()
            self._emit_initial_surface_ready()
            return
        if self._initial_static_probe_attempts < 200:
            QTimer.singleShot(
                10,
                lambda generation=generation, token=token,
                processing_token=processing_token:
                self._probe_initial_surface(
                    generation,
                    token,
                    processing_token,
                ),
            )
            return
        self._fail_initial_surface(generation, token, processing_token)

    def _on_initial_surface_probe_timeout(
        self,
        generation: int,
        token: int,
        processing_token: ProcessingCurtainToken,
    ) -> None:
        """网页不回调时，首表面预检固定两秒后失败闭合。"""

        self._fail_initial_surface(generation, token, processing_token)

    def _fail_initial_surface(
        self,
        generation: int,
        token: int,
        processing_token: ProcessingCurtainToken,
    ) -> None:
        if not self._initial_surface_probe_is_current(
            generation,
            token,
            processing_token,
        ):
            return
        self._clear_initial_surface_probe()
        self.ready = False
        self.load_ok = False
        self.view.setEnabled(False)
        self.view.hide()
        try:
            self.renderer_lifecycle.mark_recovery_failed(generation)
        except (RuntimeError, ValueError):
            pass
        self._show_renderer_curtain(RendererRecoveryViewState.BLOCKED)
        self.canvas_failed.emit()
        self._emit_initial_surface_ready()

    def _emit_initial_surface_ready(self) -> None:
        """无论成功或失败，首个表面只能驱动应用显示一次。"""

        if self._initial_surface_ready_emitted:
            return
        self._initial_surface_ready_emitted = True
        self.initial_surface_ready.emit()

    def _security_lock_transition_is_current(self) -> bool:
        token = self._processing_curtain_token
        return bool(
            isinstance(token, ProcessingCurtainToken)
            and token.process is ProcessingCurtainProcess.SECURITY_LOCK
            and self.renderer_curtain.state
            is RendererRecoveryViewState.TRANSITION
            and self._renderer_curtain_is_installed_for_presentation()
        )

    def _processing_presentation_is_active(
        self,
        token: ProcessingCurtainToken,
    ) -> bool:
        return bool(
            token is self._processing_curtain_presentation_token
            and self._processing_curtain_presentation_generation
            == self._renderer_page_generation
            and self._processing_curtain_presentation_serial > 0
            and self._processing_curtain_presentation_serial
            == self._renderer_presentation_token
        )

    def _pause_processing_presentation(self) -> None:
        token = self._processing_curtain_token
        if (
            not isinstance(token, ProcessingCurtainToken)
            or not self._renderer_curtain_is_installed_for_presentation()
        ):
            return
        self._processing_curtain.set_presentable(token, False)
        # 不可呈现只作废本轮技术身份、相邻样本与唤醒；同一安全过程、
        # 最低时长抽样和起点继续保留，恢复后必须取得新的完整呈现身份。
        self._renderer_presentation_generation = 0
        self._renderer_presentation_token = 0
        self._clear_processing_curtain_presentation()
        self.view.setEnabled(False)

    def _resume_processing_presentation_if_possible(self) -> None:
        # 不可呈现期间只完成安全撤权、连接页数据构造和最低停留计时。
        # 先返回，绝不准备网页或创建可见阶段的两秒截止。
        if not self._window_is_presentable_for_processing():
            return
        token = self._processing_curtain_token
        if (
            not isinstance(token, ProcessingCurtainToken)
            or not self._renderer_curtain_is_installed_for_presentation()
            or self._processing_presentation_is_active(token)
        ):
            return
        generation = self._renderer_page_generation
        if token.process is ProcessingCurtainProcess.SECURITY_LOCK:
            if self._locked_presentation_ready_token is token:
                self._begin_renderer_presentation(generation)
            return
        if (
            self.renderer_lifecycle.state is RendererLifecycleState.ACTIVE
            and self.ready
        ):
            self._begin_renderer_presentation(generation)

    def _clear_processing_curtain_wakeup(self) -> None:
        self._processing_curtain_wakeup_token = None
        self._processing_curtain_wakeup_generation = 0
        self._processing_curtain_wakeup_serial = 0

    def _clear_processing_curtain_presentation(self) -> None:
        HostWindow._clear_renderer_presentation_frame_gate(self)
        self._processing_curtain_presentation_token = None
        self._processing_curtain_presentation_generation = 0
        self._processing_curtain_presentation_serial = 0
        self._clear_processing_curtain_wakeup()

    def _terminate_processing_curtain(self) -> None:
        token = self._processing_curtain_token
        if isinstance(token, ProcessingCurtainToken):
            self._processing_curtain.fail(token)
        self._processing_curtain_token = None
        self._locked_presentation_ready_token = None
        self._clear_processing_curtain_presentation()

    def _processing_curtain_presentation_is_current(
        self,
        generation: int,
        presentation_token: int,
        token: ProcessingCurtainToken,
    ) -> bool:
        return bool(
            token is self._processing_curtain_token
            and token is self._processing_curtain_presentation_token
            and generation == self._processing_curtain_presentation_generation
            and generation == self._renderer_page_generation
            and presentation_token
            == self._processing_curtain_presentation_serial
            and presentation_token == self._renderer_presentation_token
            and self.renderer_lifecycle.state
            is RendererLifecycleState.ACTIVE
            and self._renderer_curtain_is_installed_for_presentation()
            and self._window_is_presentable_for_processing()
        )

    def _renderer_presentation_started(
        self,
        generation: int,
        presentation_token: int,
    ) -> None:
        token = self._processing_curtain_token
        self._clear_processing_curtain_presentation()
        if not isinstance(token, ProcessingCurtainToken):
            self._show_renderer_curtain(RendererRecoveryViewState.BLOCKED)
            return
        self._processing_curtain_presentation_token = token
        self._processing_curtain_presentation_generation = generation
        self._processing_curtain_presentation_serial = presentation_token

    def _on_renderer_presentation_started(
        self,
        generation: int,
        presentation_token: int,
    ) -> None:
        self._renderer_presentation_started(generation, presentation_token)

    def _on_renderer_presentation_frames_ready(
        self,
        generation: int,
        presentation_token: int,
    ) -> None:
        if (
            generation != self._renderer_page_generation
            or presentation_token != self._renderer_presentation_token
        ):
            return
        token = self._processing_curtain_presentation_token
        if not isinstance(token, ProcessingCurtainToken):
            self._fail_renderer_presentation(generation)
            return
        if not self._processing_curtain_presentation_is_current(
            generation,
            presentation_token,
            token,
        ):
            return
        if token.process is ProcessingCurtainProcess.SECURITY_LOCK:
            if self._locked_presentation_ready_token is not token:
                return
            # 严格双样本已经证明当前锁定连接页健康；最低时长只决定何时揭幕，
            # 不应继续把本页误记为加载失败。
            self.ready = True
            self.load_ok = True
        decision = self._processing_curtain.mark_ready(token)
        self._apply_processing_curtain_decision(
            generation,
            presentation_token,
            token,
            decision.reveal_now,
            decision.remaining_ms,
        )

    def _on_processing_curtain_wakeup(
        self,
        generation: int,
        presentation_token: int,
        token: ProcessingCurtainToken,
    ) -> None:
        if not self._processing_curtain_presentation_is_current(
            generation,
            presentation_token,
            token,
        ):
            return
        if (
            token is not self._processing_curtain_wakeup_token
            or generation != self._processing_curtain_wakeup_generation
            or presentation_token != self._processing_curtain_wakeup_serial
        ):
            return
        self._clear_processing_curtain_wakeup()
        decision = self._processing_curtain.reconcile(token)
        self._apply_processing_curtain_decision(
            generation,
            presentation_token,
            token,
            decision.reveal_now,
            decision.remaining_ms,
        )

    def _apply_processing_curtain_decision(
        self,
        generation: int,
        presentation_token: int,
        token: ProcessingCurtainToken,
        reveal_now: bool,
        remaining_ms: int | None,
    ) -> None:
        if not self._processing_curtain_presentation_is_current(
            generation,
            presentation_token,
            token,
        ):
            return
        if reveal_now:
            self._clear_processing_curtain_wakeup()
            self._request_renderer_presentation_frame(
                generation,
                presentation_token,
            )
            return
        if type(remaining_ms) is not int or remaining_ms <= 0:
            self._fail_renderer_presentation(generation)
            return
        if (
            token is self._processing_curtain_wakeup_token
            and generation == self._processing_curtain_wakeup_generation
            and presentation_token == self._processing_curtain_wakeup_serial
        ):
            return
        self._processing_curtain_wakeup_token = token
        self._processing_curtain_wakeup_generation = generation
        self._processing_curtain_wakeup_serial = presentation_token
        QTimer.singleShot(
            remaining_ms,
            lambda generation=generation,
            presentation_token=presentation_token,
            token=token: self._on_processing_curtain_wakeup(
                generation,
                presentation_token,
                token,
            ),
        )

    def _on_renderer_curtain_hidden(self, generation: int) -> None:
        HostWindow._on_renderer_curtain_hidden(self, generation)
        self.confirm_renderer_curtain_sidebar_width()
        self._locked_presentation_ready_token = None
        M4HostWindow._sync_transient_toast_presentation(self)
        if M4HostWindow._show_claimed_change_key_success_toast_if_presentable(
            self,
            generation,
        ):
            return
        self._consume_locked_notice_if_presentable()

    def _show_claimed_change_key_success_toast_if_presentable(
        self,
        generation: int,
    ) -> bool:
        runtime = self._m4_runtime
        page_epoch = runtime.active_page_epoch if runtime is not None else 0
        if (
            runtime is None
            or generation != self._renderer_page_generation
            or self.renderer_lifecycle.state
            is not RendererLifecycleState.ACTIVE
            or page_epoch <= 0
            or not self.isVisible()
            or self.isMinimized()
            or not self.view.isVisible()
            or self.renderer_curtain.isVisible()
        ):
            return False
        if not runtime.take_change_key_success_toast(page_epoch):
            return False
        self.web.page.runJavaScript(
            "Boolean(window.pdmM4 "
            "&& window.pdmM4.showClaimedChangeKeySuccessToast "
            "&& window.pdmM4.showClaimedChangeKeySuccessToast())",
        )
        self.announce_m4_accessible_operation("KEY_CHANGED", "OK")
        return True

    def _consume_locked_notice_if_presentable(self) -> bool:
        if (
            not self.isVisible()
            or self.isMinimized()
            or not self.view.isVisible()
            or self.renderer_curtain.isVisible()
        ):
            return False
        self.web.page.runJavaScript(
            "Boolean(window.pdmM4 && window.pdmM4.consumeLockedNotice "
            "&& window.pdmM4.consumeLockedNotice())"
        )
        return True

    def showEvent(self, event: QShowEvent) -> None:  # noqa: N802
        super().showEvent(event)
        if getattr(self, "_exit_cleanup_started", False):
            return
        QTimer.singleShot(
            0,
            lambda: M4HostWindow._sync_transient_toast_presentation(self),
        )
        QTimer.singleShot(0, self._resume_processing_presentation_if_possible)
        QTimer.singleShot(
            0,
            lambda generation=self._renderer_page_generation:
            self._show_claimed_change_key_success_toast_if_presentable(
                generation
            ),
        )
        QTimer.singleShot(0, self._consume_locked_notice_if_presentable)

    def hideEvent(self, event: QHideEvent) -> None:  # noqa: N802
        super().hideEvent(event)
        if getattr(self, "_exit_cleanup_started", False):
            return
        M4HostWindow._sync_transient_toast_presentation(self)
        # 此时 Qt 的隐藏状态已经生效；只作废本轮可见检查，恢复显示
        # 后再由 show/restore 入口建立新身份。
        self._pause_processing_presentation()

    def changeEvent(self, event: QEvent) -> None:  # noqa: N802
        window_state_change = event.type() == QEvent.Type.WindowStateChange
        old_window_state = event.oldState() if window_state_change else None
        super().changeEvent(event)
        if getattr(self, "_exit_cleanup_started", False):
            return
        entering_minimized = window_state_change and self.isMinimized()
        restoring_from_minimized = bool(
            window_state_change
            and old_window_state is not None
            and old_window_state & Qt.WindowState.WindowMinimized
            and not entering_minimized
        )
        if entering_minimized:
            # 原生最小化状态生效后只作废本轮技术检查，不排后台绘制。
            M4HostWindow._sync_transient_toast_presentation(self)
            self._pause_processing_presentation()
        if restoring_from_minimized:
            QTimer.singleShot(
                0,
                lambda: M4HostWindow._sync_transient_toast_presentation(self),
            )
            QTimer.singleShot(
                0,
                self._resume_processing_presentation_if_possible,
            )
            QTimer.singleShot(
                0,
                lambda generation=self._renderer_page_generation:
                self._show_claimed_change_key_success_toast_if_presentable(
                    generation
                ),
            )
            QTimer.singleShot(0, self._consume_locked_notice_if_presentable)

    def _schedule_taskbar_restore_surface_refresh(self) -> None:
        if self.standard_window_frame:
            super()._schedule_taskbar_restore_surface_refresh()
            if self._renderer_curtain_is_installed_for_presentation():
                self._resume_processing_presentation_if_possible()
            return
        if self._renderer_curtain_is_installed_for_presentation():
            QTimer.singleShot(
                0,
                self._resume_processing_presentation_if_possible,
            )
            return
        super()._schedule_taskbar_restore_surface_refresh()

    def _non_clipboard_exit_boundary_complete(self) -> bool:
        return self.m4_runtime.non_clipboard_close_complete

    def _enter_exit_security_boundary(self) -> bool:
        return self.m4_runtime.close("exit")

    def enter_native_security_boundary(
        self,
        reason: SecurityBoundaryReason,
        *,
        page_revoked: bool,
    ):
        del reason, page_revoked
        raise RuntimeError(
            "M4 security boundaries must revoke typed-Bridge authority"
        )

    def current_sensitive_dom(self):
        return self._sensitive_dom

    def current_native_clipboard(self):
        return self._m4_native_clipboard

    def current_native_hotkey(self) -> NativeHotkey:
        return self.native.hotkey

    def create_m4_editor_view(
        self,
        entry_path: str = "/editor.html",
    ) -> QWebEngineView:
        view = QWebEngineView()
        page = AppPage(
            self.web.profile,
            view,
            diagnostics=self.diagnostics,
            page_generation=self._renderer_page_generation,
            entry_path=entry_path,
        )
        configure_page_settings(page.settings())
        view.setPage(page)
        view.setAcceptDrops(False)
        view.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        return view

    def _on_m4_native_quickbar_requested(self) -> None:
        runtime = self._m4_runtime
        if runtime is not None:
            runtime.open_quickbar_from_native_hotkey()

    def on_m4_handshake(self, page_epoch: int) -> None:
        self.security.page_authorized(page_epoch)
        if (
            self.tray is not None
            and self.tray.state is not TraySessionState.LOCKED
        ):
            self.set_tray_state(TraySessionState.DISCONNECTED)

    def on_m4_session_opened(self, session_epoch: int) -> None:
        suspend_lock_required = self._m4_suspend_lock_state in {
            _M4SuspendLockState.IN_PROGRESS,
            _M4SuspendLockState.COMPLETE,
            _M4SuspendLockState.FAILED,
        }
        self.security.session_authorized(session_epoch)
        if suspend_lock_required:
            self._m4_idle_monitor.disarm_session()
            self.set_tray_state(TraySessionState.LOCKED)
            self._lock_m4_session_opened_during_suspend(session_epoch)
            return
        self._m4_suspend_lock_state = _M4SuspendLockState.NONE
        self.set_tray_state(TraySessionState.CONNECTED)
        self._m4_idle_monitor.arm_session(
            self._m4_auto_lock_enabled,
            self._m4_auto_lock_minutes,
        )

    def on_m4_locked(self, reason: str) -> None:
        if reason not in _M4_LOCK_REASONS:
            raise ValueError("unsupported M4 locked presentation reason")
        processing_token = self._processing_curtain_token
        if not self._security_lock_transition_is_current():
            if (
                self.renderer_curtain.state
                is RendererRecoveryViewState.TRANSITION
                and not self.renderer_curtain.isHidden()
                and (
                    not isinstance(
                        processing_token,
                        ProcessingCurtainToken,
                    )
                    or processing_token.process
                    is not ProcessingCurtainProcess.SECURITY_LOCK
                )
            ):
                self._show_renderer_curtain(
                    RendererRecoveryViewState.BLOCKED
                )
            return
        self._m4_idle_monitor.disarm_session()
        self.set_tray_state(TraySessionState.LOCKED)
        self._locked_presentation_ready_token = processing_token
        self._resume_processing_presentation_if_possible()

    def on_m4_lock_failed(self) -> None:
        """清理不完整时只保留失败幕布，不发布可连接终态。"""

        try:
            self.renderer_lifecycle.mark_recovery_failed(
                self._renderer_page_generation
            )
        except Exception:
            pass
        self._m4_idle_monitor.disarm_session()
        self.set_tray_state(TraySessionState.LOCKED)
        if self._m4_suspend_lock_state is _M4SuspendLockState.IN_PROGRESS:
            self._m4_suspend_lock_state = _M4SuspendLockState.FAILED
        self.ready = False
        self.load_ok = False
        self.view.setEnabled(False)
        self.view.hide()
        self._show_renderer_curtain(RendererRecoveryViewState.BLOCKED)

    def _install_renderer_conceal_surface(
        self,
        context: SecurityBoundaryContext,
    ) -> None:
        if (
            context.reason not in _PROCESSING_SECURITY_REASONS
            or (
                context.reason is SecurityBoundaryReason.RENDERER_FAILURE
                and context.page_revoked
            )
        ):
            super()._install_renderer_conceal_surface(context)
            return
        self._processing_curtain_token = self._processing_curtain.begin(
            ProcessingCurtainProcess.SECURITY_LOCK,
            context.authority_serial,
            presentable=self._window_is_presentable_for_processing(),
        )
        self._locked_presentation_ready_token = None
        self._clear_processing_curtain_presentation()
        self._show_renderer_curtain(RendererRecoveryViewState.TRANSITION)
        if self._renderer_curtain_is_installed_for_presentation():
            self._complete_tray_hide_presentation_with_native_curtain()

    def _conceal_renderer(self, context: SecurityBoundaryContext) -> None:
        """正常锁定以局部实心幕布遮住业务区，网页继续作为稳定底图。"""

        if (
            context.reason not in _PROCESSING_SECURITY_REASONS
            or (
                context.reason is SecurityBoundaryReason.RENDERER_FAILURE
                and context.page_revoked
            )
        ):
            super()._conceal_renderer(context)
            return
        self.ready = False
        self.load_ok = False
        HostWindow._clear_renderer_presentation_frame_gate(self)
        self._renderer_presentation_generation = 0
        self._renderer_presentation_token = 0
        try:
            self._install_renderer_conceal_surface(context)
        except Exception:
            # 局部幕布安装异常时立即回退为完整原生失败遮挡，绝不保留旧业务页。
            HostWindow._install_renderer_conceal_surface(self, context)
            self.view.hide()
            raise
        finally:
            self.view.setEnabled(False)
            app = QApplication.instance()
            if app is not None:
                app.sync()
            try:
                self.set_tray_state(TraySessionState.LOCKED)
            except Exception:
                pass

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
    ) -> None:
        """Synchronize the bounded native cover with public settings."""

        if theme not in {"LIGHT", "DARK", "AUTO"}:
            raise ValueError("M4 theme projection must be bounded")
        if effective_theme not in {"LIGHT", "DARK"}:
            raise ValueError("M4 effective theme projection must be bounded")
        if language not in {"ZH", "EN"}:
            raise ValueError("M4 language projection must be bounded")
        if ui_font_scale not in {"90", "100", "110", "125"}:
            raise ValueError("M4 UI font scale projection must be bounded")
        if type(sidebar_text) is not bool:
            raise ValueError("M4 sidebar text projection must be bool")
        if close_behavior not in {"TO_TRAY", "EXIT"}:
            raise ValueError("M4 close behavior projection must be bounded")
        if type(auto_lock_enabled) is not bool:
            raise ValueError("M4 auto-lock enabled projection must be bool")
        if (
            type(auto_lock_minutes) is not int
            or not 1 <= auto_lock_minutes <= 60
        ):
            raise ValueError("M4 auto-lock minutes projection is invalid")
        if type(quickbar_enabled) is not bool:
            raise ValueError("M4 QuickBar enabled projection must be bool")
        if (
            type(quickbar_idle_seconds) is not int
            or not 10 <= quickbar_idle_seconds <= 600
        ):
            raise ValueError("M4 QuickBar idle projection is invalid")
        if (
            type(quickbar_hotkey) is not str
            or not 3 <= len(quickbar_hotkey) <= 64
        ):
            raise ValueError("M4 QuickBar hotkey projection is invalid")
        if quickbar_registration not in {
            "DISABLED",
            "REGISTERED",
            "UNAVAILABLE",
        }:
            raise ValueError("M4 QuickBar registration projection is invalid")
        if theme != "AUTO" and effective_theme != theme:
            raise ValueError(
                "explicit M4 theme must match its effective projection"
            )
        self._m4_auto_lock_enabled = auto_lock_enabled
        self._m4_auto_lock_minutes = auto_lock_minutes
        self.set_renderer_curtain_sidebar_width(72 if sidebar_text else 48)
        self.set_close_to_tray(close_behavior == "TO_TRAY")
        self.set_native_language(language.lower())
        self.set_native_effective_theme(effective_theme)
        if self.product_titlebar is not None:
            self.product_titlebar.set_ui_font_scale(ui_font_scale)
        self.renderer_curtain.set_effective_theme(effective_theme)
        self.renderer_curtain.set_language(language.lower())
        self.renderer_curtain.set_ui_font_scale(ui_font_scale)
        selector = getattr(self, "_m4_target_selector", None)
        if isinstance(selector, NativeDatabaseTargetSelector):
            selector.set_language(language)
        backup_selector = getattr(self, "_m4_backup_selector", None)
        if isinstance(backup_selector, NativeBackupFileSelector):
            backup_selector.set_language(language)
        monitor = getattr(self, "_m4_idle_monitor", None)
        if monitor is not None:
            monitor.configure_policy(
                auto_lock_enabled,
                auto_lock_minutes,
            )
        transfer = getattr(self, "_m4_transfer_core", None)
        if transfer is not None:
            transfer.apply_settings(effective_theme, language, ui_font_scale)

    def _transfer_lock_monitor_ready(self) -> bool:
        monitor = getattr(self, "session_lock", None)
        return bool(monitor is not None and monitor.is_registered_for(int(self.internalWinId())))

    def _set_transfer_hold(self, active: bool, session_epoch: int) -> bool:
        runtime = self._m4_runtime
        if active:
            if (runtime is None or session_epoch <= 0 or runtime.active_session_epoch != session_epoch
                    or self._m4_power_suspended or not self._transfer_lock_monitor_ready()):
                return False
            self._m4_transfer_hold_epoch = session_epoch
            self._m4_idle_monitor.disarm_session()
            return True
        if self._m4_transfer_hold_epoch != session_epoch:
            return False
        self._m4_transfer_hold_epoch = 0
        if runtime is not None and session_epoch > 0 and runtime.active_session_epoch == session_epoch and not self._m4_power_suspended:
            self._m4_idle_monitor.arm_session(self._m4_auto_lock_enabled, self._m4_auto_lock_minutes)
        return True

    def _adopt_transfer_preview(self, result, page_epoch, session_epoch, display_name):
        runtime = self._m4_runtime
        if runtime is None or (runtime.active_page_epoch, runtime.active_session_epoch) != (page_epoch, session_epoch):
            return False
        if not runtime.backup_window.open_received_preview(result, page_epoch, session_epoch, display_name):
            return False
        self._m4_direct_transfer.handoff_received()
        return True

    def _transfer_import_completed(self, _page, _session, operation, _result):
        runtime = self._m4_runtime
        if runtime is not None and operation == "IMPORT" and runtime.backup_window.source_kind == "TRANSFER":
            self._m4_direct_transfer.close()

    def _revoke_direct_transfer(self):
        core, transfer = getattr(self, "_m4_transfer_core", None), getattr(self, "_m4_direct_transfer", None)
        runtime = getattr(self, "_m4_runtime", None)
        failed = False
        for cleanup in (
            lambda: core.stop_for_security() if core is not None else None,
            lambda: transfer.conceal() if transfer is not None else None,
            lambda: runtime.backup_window.close(force=True, reason="transfer_system_lock")
                if runtime is not None and runtime.backup_window.source_kind == "TRANSFER" else None,
            lambda: transfer.close() if transfer is not None else None,
        ):
            try:
                if cleanup() is False:
                    failed = True
            except Exception:
                failed = True
        if failed and runtime is not None:
            runtime._on_editor_renderer_failed()

    def _on_session_locked(self) -> None:
        HostWindow._on_session_locked(self)
        self._revoke_direct_transfer()

    def _on_session_lock_availability_changed(self, available: bool) -> None:
        HostWindow._on_session_lock_availability_changed(self, available)
        if not available:
            self._revoke_direct_transfer()

    def announce_m4_accessible_operation(
        self,
        operation: str,
        error_code: str,
    ) -> bool:
        """经 Windows 原生路径发送一次有界产品操作结果。"""

        if operation not in _ACCESSIBLE_OPERATION_TEXT:
            return False
        try:
            presentable = bool(
                self._window_is_presentable_for_processing()
                and self.renderer_lifecycle.state
                is RendererLifecycleState.ACTIVE
                and self.view.isVisible()
                and not self.renderer_curtain.isVisible()
            )
        except (AttributeError, RuntimeError):
            return False
        if not presentable:
            return False
        language_index = 1 if self._native_language == "en" else 0
        if error_code == "OK":
            text = _ACCESSIBLE_OPERATION_TEXT[operation][language_index]
        else:
            text = _ACCESSIBLE_OPERATION_ERROR_TEXT.get(
                (operation, error_code),
                _ACCESSIBLE_ERROR_TEXT.get(
                    error_code,
                    _ACCESSIBLE_GENERIC_FAILURE,
                ),
            )[language_index]
        try:
            event = QAccessibleAnnouncementEvent(self, text)
            event.setPoliteness(QAccessible.AnnouncementPoliteness.Assertive)
            QAccessible.updateAccessibility(event)
        except (RuntimeError, TypeError):
            return False
        return True

    def _on_m4_idle_timeout(self) -> None:
        runtime = self._m4_runtime
        if runtime is None or runtime.active_session_epoch <= 0:
            return
        if getattr(self, "_m4_transfer_hold_epoch", 0) == runtime.active_session_epoch:
            return
        runtime.lock_session_from_native("AUTO_LOCK")

    def _on_power_suspending(self, count: int) -> None:
        """先记录窗口状态，再同步完成或确认既有锁定。"""

        self._m4_power_suspended = True
        M4HostWindow._sync_transient_toast_presentation(self)
        M4HostWindow._suspend_technical_probes(self)
        self._pause_processing_presentation()
        HostWindow._on_power_suspending(self, count)
        runtime = self._m4_runtime
        if runtime is None:
            return
        if runtime.active_session_epoch <= 0:
            if runtime.active_page_epoch <= 0:
                self._m4_suspend_lock_state = _M4SuspendLockState.COMPLETE
                return
            self._m4_suspend_lock_state = _M4SuspendLockState.IN_PROGRESS
            complete = runtime.lock_public_page_for_suspend()
            self._m4_suspend_lock_state = (
                _M4SuspendLockState.COMPLETE
                if complete
                else _M4SuspendLockState.FAILED
            )
            return
        self._m4_suspend_lock_state = _M4SuspendLockState.IN_PROGRESS
        complete = runtime.lock_session_from_native("SUSPEND_LOCK")
        self._m4_suspend_lock_state = (
            _M4SuspendLockState.COMPLETE
            if complete
            else _M4SuspendLockState.FAILED
        )

    def _lock_m4_session_opened_during_suspend(
        self,
        session_epoch: int,
    ) -> None:
        """理论上不可达的迟到成功只允许撤销并进入失败幕布。"""

        runtime = self._m4_runtime
        if runtime is None:
            self._m4_suspend_lock_state = _M4SuspendLockState.FAILED
            self.on_m4_lock_failed()
            return
        if runtime.active_session_epoch == 0:
            self._m4_suspend_lock_state = _M4SuspendLockState.FAILED
            self.on_m4_lock_failed()
            return
        if runtime.active_session_epoch != session_epoch:
            self._m4_suspend_lock_state = _M4SuspendLockState.FAILED
            self.on_m4_lock_failed()
            return
        self._m4_suspend_lock_state = _M4SuspendLockState.IN_PROGRESS
        runtime.lock_session_from_native("SUSPEND_LOCK")
        self._m4_suspend_lock_state = _M4SuspendLockState.FAILED
        self.on_m4_lock_failed()

    def _on_power_resumed(self, event_name: str, count: int) -> None:
        """中断态幂等补锁；成功态绝不再次触发锁定。"""

        runtime = self._m4_runtime
        first_security_resume = count != self._m4_last_security_resume_count
        if first_security_resume:
            self._m4_last_security_resume_count = count
        if (
            first_security_resume
            and runtime is not None
            and runtime.active_session_epoch > 0
        ):
            self._m4_suspend_lock_state = _M4SuspendLockState.IN_PROGRESS
            complete = runtime.lock_session_from_native("SUSPEND_LOCK")
            self._m4_suspend_lock_state = (
                _M4SuspendLockState.COMPLETE
                if complete
                else _M4SuspendLockState.FAILED
            )
        failed = self._m4_suspend_lock_state is _M4SuspendLockState.FAILED
        if not failed:
            self._m4_suspend_lock_state = _M4SuspendLockState.NONE
        self._m4_power_suspended = False
        HostWindow._on_power_resumed(self, event_name, count)
        M4HostWindow._sync_transient_toast_presentation(self)
        if failed:
            M4HostWindow._clear_suspended_technical_probes(self)
        else:
            M4HostWindow._resume_suspended_technical_probes(self)
            QTimer.singleShot(
                0,
                self._resume_processing_presentation_if_possible,
            )

    def hide_to_tray(self) -> bool:
        """托盘结算前暂停；隐藏失败时继续同一处理中过程。"""
        if getattr(self, "_exit_cleanup_started", False):
            return False

        self._pause_processing_presentation()
        hidden = False
        try:
            hidden = super().hide_to_tray()
            return hidden
        finally:
            M4HostWindow._sync_transient_toast_presentation(self)
            if not hidden and self._window_is_presentable_for_processing():
                self._resume_processing_presentation_if_possible()

    def restore_from_tray(self) -> None:
        if getattr(self, "_exit_cleanup_started", False):
            return None
        if not self._initial_surface_ready_emitted:
            return
        super().restore_from_tray()
        QTimer.singleShot(
            0,
            lambda: M4HostWindow._sync_transient_toast_presentation(self),
        )
        QTimer.singleShot(0, self._resume_processing_presentation_if_possible)
        QTimer.singleShot(
            0,
            lambda generation=self._renderer_page_generation:
            self._show_claimed_change_key_success_toast_if_presentable(
                generation
            ),
        )
        QTimer.singleShot(0, self._consume_locked_notice_if_presentable)

    def _settle_close_behavior_before_close(self) -> bool:
        """Wait for accepted C43 writes before native close dispatch."""

        close_behavior = (
            self.m4_runtime.settle_close_behavior_for_native_close()
        )
        if close_behavior not in {"TO_TRAY", "EXIT"}:
            raise RuntimeError("invalid native close behavior authority")
        self.set_close_to_tray(close_behavior == "TO_TRAY")
        return True

    def on_m4_change_key_terminal(self, reason: str) -> None:
        """把 C49 精确结算投影到原连接页或失败幕布。"""

        self.set_tray_state(TraySessionState.LOCKED)
        if reason not in {
            "CHANGE_KEY_SUCCESS",
            "CHANGE_KEY_RESTORED",
        } | _M4_C49_FAILURE_REASONS:
            raise ValueError("unsupported C49 terminal reason")
        if reason in _M4_C49_FAILURE_REASONS:
            if reason == "CHANGE_KEY_RECOVERY_FAILED":
                self._m4_database_recovery_failed = True
            self.view.setEnabled(False)
            self.view.hide()
            try:
                self.renderer_lifecycle.mark_recovery_failed(
                    self._renderer_page_generation
                )
            except Exception:
                pass
            self._show_renderer_curtain(
                (
                    RendererRecoveryViewState.DATABASE_RECOVERY_FAILED
                    if reason == "CHANGE_KEY_RECOVERY_FAILED"
                    else RendererRecoveryViewState.BLOCKED
                )
            )
            return
        if reason == "CHANGE_KEY_SUCCESS":
            self.on_m4_locked("C49_SUCCESS")
            return
        if reason == "CHANGE_KEY_RESTORED":
            self.on_m4_locked("C49_RESTORED")
            return

    def set_m4_external_change_key_settlement_token(
        self,
        token: int | None,
    ) -> None:
        """校验由长生命周期运行时消费的精确结算通知。"""

        if token is not None and (type(token) is not int or token <= 0):
            raise ValueError("invalid external C49 settlement token")

    def _show_renderer_curtain(
        self,
        state: RendererRecoveryViewState,
    ) -> None:
        startup_failure = bool(
            not self._initial_surface_ready_emitted
            and isinstance(
                self._processing_curtain_token,
                ProcessingCurtainToken,
            )
            and self._processing_curtain_token.process
            is ProcessingCurtainProcess.STARTUP
            and state in _PROCESSING_FAILURE_STATES
        )
        if (
            self._m4_database_recovery_failed
            and state
            is not RendererRecoveryViewState.DATABASE_RECOVERY_FAILED
        ):
            state = RendererRecoveryViewState.DATABASE_RECOVERY_FAILED
        if state in _PROCESSING_FAILURE_STATES:
            self._terminate_processing_curtain()
        else:
            self._clear_processing_curtain_presentation()
        self._locked_presentation_ready_token = None
        super()._show_renderer_curtain(state)
        M4HostWindow._sync_transient_toast_presentation(self)
        if startup_failure:
            # 失败幕布已经完整安装，入口现在可以安全地显示一次窗口。
            self._emit_initial_surface_ready()

    def _fail_renderer_presentation(self, generation: int) -> None:
        if generation == self._renderer_page_generation:
            self._terminate_processing_curtain()
        super()._fail_renderer_presentation(generation)

    def _begin_renderer_recovery(self) -> None:
        transition = self.renderer_lifecycle.begin_recovery()
        if transition.decision is not RendererDecision.RECOVERY_PAGE_REQUIRED:
            return
        self._processing_curtain_token = self._processing_curtain.begin(
            ProcessingCurtainProcess.RENDERER_REBUILD,
            transition.page_generation,
            presentable=self._window_is_presentable_for_processing(),
        )
        self._clear_processing_curtain_presentation()
        self._show_renderer_curtain(RendererRecoveryViewState.REBUILDING)
        self._rebuild_renderer_page(transition.page_generation)

    def _prepare_for_true_exit(self) -> None:
        """只在 H06 已授权后撤下产品呈现面。"""

        super()._prepare_for_true_exit()
        self._terminate_processing_curtain()
        self._m4_suspend_lock_state = _M4SuspendLockState.NONE
        self.hide()


__all__ = ["M4HostWindow"]
