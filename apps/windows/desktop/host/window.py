"""承载共享网页画布和原生系统能力的基础窗口。"""

from __future__ import annotations

import ctypes
from dataclasses import dataclass
import secrets
import sys
from typing import Callable

from PySide6.QtCore import (
    QEvent,
    QEventLoop,
    QPoint,
    QRect,
    QSize,
    Qt,
    QTimer,
    QUrl,
    Signal,
)
from PySide6.QtGui import (
    QCloseEvent,
    QCursor,
    QKeySequence,
    QMoveEvent,
    QResizeEvent,
    QShortcut,
    QShowEvent,
)
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineScript
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtQuickWidgets import QQuickWidget
from PySide6.QtWidgets import QApplication, QMainWindow, QMessageBox
from shiboken6 import isValid

from .diagnostics import (
    FixedDiagnosticRecorder,
    RendererTerminationStatus,
)
from .focus_visibility import (
    NativeFocusVisibilityController,
    install_managed_focus_fallback,
)
from .hotkey import WM_HOTKEY
from .native_capabilities import CleanupResult, NativeCapabilities
from .power import PowerLifecycle, SessionLockLifecycle, WM_POWERBROADCAST, WM_WTSSESSION_CHANGE
from .renderer_lifecycle import (
    RendererDecision,
    RendererLifecycleController,
    RendererLifecycleState,
)
from .renderer_recovery import (
    RendererRecoveryCurtain,
    RendererRecoverySurfaceMode,
    RendererRecoveryViewState,
)
from .resources import ENTRY_URL, ResourceCatalog, application_icon
from .scene_refresh import SceneRefresh, request_surface_frame, scene_target
from .security_lifecycle import (
    SecurityBoundaryContext,
    SecurityBoundaryCoordinator,
    SecurityBoundaryReason,
    SecurityBoundaryResult,
    SecurityCleanupPhase,
)
from .sensitive_dom import SensitiveDomController
from .tray import TrayController, TraySessionState
from .web_profile import AppWebProfile
from .window_placement import (
    fit_window_rect,
    minimize_native_window,
    native_window_rect,
    show_native_maximized_window,
    show_native_normal_window,
)
from .window_chrome import (
    HTCAPTION,
    HTCLIENT,
    HTCLOSE,
    HTMAXBUTTON,
    HTMINBUTTON,
    PRODUCT_SIDEBAR_WIDTH,
    TITLEBAR_HEIGHT,
    WINDOW_CONTROL_COUNT,
    WINDOW_CONTROL_WIDTH,
    WM_NCCALCSIZE,
    WM_NCHITTEST,
    WM_NCMOUSELEAVE,
    WM_NCMOUSEMOVE,
    WM_NCPOINTERDOWN,
    WM_NCLBUTTONDOWN,
    WM_NCLBUTTONDBLCLK,
    WM_NCLBUTTONUP,
    WM_NCMBUTTONDOWN,
    WM_NCRBUTTONDOWN,
    WM_NCXBUTTONDOWN,
    WebChromeInputFilter,
    ProductTitleBar,
    apply_standard_window_frame,
    native_dpi_scale,
    native_resize_border,
    native_window_is_maximized,
    native_window_control_hit,
    native_window_control_hit_at_cursor,
    resize_hit_test,
    set_win11_corner_preference,
    set_win11_border_color_none,
    standard_window_frame_client_rect,
    track_non_client_mouse_leave,
)

_CAPTURE_TRAY_FOCUS = """
(() => {
  const api = window.pdmFocusVisibility;
  if (api && typeof api.stashNative === 'function') {
    return api.stashNative('tray');
  }
  const active = document.activeElement;
  const id = active && typeof active.id === 'string' ? active.id : '';
  const key = active && typeof active.dataset?.pdmNativeFocusKey === 'string'
    ? active.dataset.pdmNativeFocusKey
    : '';
  const safeId = /^[A-Za-z][A-Za-z0-9:_.-]{0,127}$/.test(id) ? id : '';
  const safeKey = /^(?:recent|vault-list|vault-split|note|vault-filter|note-filter|vault-view):[A-Za-z0-9_-]{1,96}$/.test(key)
    ? key
    : '';
  window.__pdmNativeFocusDescriptor = safeId
    ? `id:${safeId}`
    : safeKey
      ? `key:${safeKey}`
      : '';
  return true;
})()
"""

_RESTORE_TRAY_FOCUS = """
(() => {
  const api = window.pdmFocusVisibility;
  if (api && typeof api.restoreNative === 'function') {
    return api.restoreNative('tray');
  }
  const descriptor = typeof window.__pdmNativeFocusDescriptor === 'string'
    ? window.__pdmNativeFocusDescriptor
    : '';
  window.__pdmNativeFocusDescriptor = '';
  let target = null;
  if (descriptor.startsWith('id:')) {
    const id = descriptor.slice(3);
    if (/^[A-Za-z][A-Za-z0-9:_.-]{0,127}$/.test(id)) {
      target = document.getElementById(id);
    }
  } else if (descriptor.startsWith('key:')) {
    const key = descriptor.slice(4);
    if (/^(?:recent|vault-list|vault-split|note|vault-filter|note-filter|vault-view):[A-Za-z0-9_-]{1,96}$/.test(key)) {
      target = Array.from(
        document.querySelectorAll('[data-pdm-native-focus-key]'),
      ).find((element) => element.dataset.pdmNativeFocusKey === key) || null;
    }
  }
  if (target && typeof target.focus === 'function') {
    target.focus({preventScroll: true});
    return target.id || target.dataset.pdmNativeFocusKey || '';
  }
  return '';
})()
"""

_CAPTURE_POWER_FOCUS = """
(() => {
  const api = window.pdmFocusVisibility;
  if (api && typeof api.stashNative === 'function') {
    return api.stashNative('power');
  }
  const active = document.activeElement;
  const id = active && typeof active.id === 'string' ? active.id : '';
  window.__pdmPowerFocusId = id.length <= 128 ? id : '';
  return window.__pdmPowerFocusId;
})()
"""

_RESTORE_POWER_FOCUS = """
(() => {
  const api = window.pdmFocusVisibility;
  if (api && typeof api.restoreNative === 'function') {
    return api.restoreNative('power');
  }
  const id = typeof window.__pdmPowerFocusId === 'string'
    ? window.__pdmPowerFocusId
    : '';
  const target = id ? document.getElementById(id) : null;
  if (target && typeof target.focus === 'function') {
    target.focus({preventScroll: true});
    return target.id;
  }
  return '';
})()
"""

_RESET_WEB_FOCUS_VISIBILITY = """
(() => {
  const api = window.pdmFocusVisibility;
  if (!api || typeof api.reset !== 'function') return false;
  api.reset();
  return true;
})()
"""

_CLEAR_WEB_FOCUS_VISIBILITY = """
(() => {
  const api = window.pdmFocusVisibility;
  if (!api || typeof api.clear !== 'function') return false;
  api.clear();
  return true;
})()
"""

_PROBE_RESUME_HEALTH = """
Boolean(
  window.pdmProduct
  && window.pdmProduct.ready
  && document.querySelector('#canvas-frame')
)
"""

_ARM_RENDERER_PRESENTATION = """
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
  window.__pdmNativePresentation = {
    generation,
    presentationToken,
    ready: false,
  };
  window.requestAnimationFrame(() => {
    if (!isCurrent()) return;
    window.requestAnimationFrame(() => {
      if (!isCurrent()) return;
      const current = window.__pdmNativePresentation;
      if (!isCurrent()) return;
      current.ready = true;
    });
  });
  return `${generation}:${presentationToken}`;
})()
"""

_PROBE_RENDERER_PRESENTATION = """
(() => {
  const current = window.__pdmNativePresentation;
  return Boolean(
    current
    && current.generation === __PDM_GENERATION__
    && current.presentationToken === __PDM_PRESENTATION_TOKEN__
    && current.ready === true
  );
})()
"""

_RENDERER_PRESENTATION_TIMEOUT_MS = 2_000
_STARTUP_FRAME_TIMEOUT_MS = 5_000
_CANVAS_PROBE_TIMEOUT_MS = 2_000


@dataclass(slots=True)
class _RendererPresentationFrameGate:
    generation: int
    presentation_token: int
    view: QWebEngineView
    quick_widget: QQuickWidget
    quick_window: object
    callback: Callable[[], None]
    stamp_bits: str = ""
    stamp_removed: bool = False
    geometry: tuple = ()
    frame_connected: bool = False


def _presentation_stamp_source(gate: _RendererPresentationFrameGate, *, remove: bool) -> str:
    """帧标记只存在于原生幕布后；不包含用户数据，也不提供新的业务权限。"""

    element_id = f"pdm-native-frame-stamp-{gate.presentation_token}"
    if remove:
        return f"(() => {{ document.getElementById('{element_id}')?.remove(); return true; }})()"
    return f"""
(() => {{
  const current = window.__pdmNativePresentation;
  if (!current || current.generation !== {gate.generation}
      || current.presentationToken !== {gate.presentation_token}) return false;
  document.querySelectorAll('[data-pdm-native-frame-stamp]').forEach(node => node.remove());
  const stamp = document.createElement('canvas');
  stamp.id = '{element_id}';
  stamp.dataset.pdmNativeFrameStamp = 'true';
  stamp.setAttribute('aria-hidden', 'true');
  stamp.inert = true;
  stamp.width = stamp.height = 32;
  Object.assign(stamp.style, {{position:'fixed', left:'50%', top:'50%',
    width:'32px', height:'32px', transform:'translate(-50%, -50%)',
    margin:'0', padding:'0', border:'0', opacity:'1', filter:'none',
    zIndex:'2147483647', pointerEvents:'none'}});
  const context = stamp.getContext('2d');
  if (!context) return false;
  Array.from('{gate.stamp_bits}').forEach((bit, index) => {{
    context.fillStyle = bit === '1' ? '#fff' : '#000';
    context.fillRect(index % 8 * 4, Math.floor(index / 8) * 4, 4, 4);
  }});
  document.documentElement.appendChild(stamp);
  return true;
}})()
"""


def _image_has_presentation_stamp(image, bits: str, scale: float) -> bool:
    """只比较本次标记的64个中心像素，不保留或解释其余画面。"""

    for index, bit in enumerate(bits):
        x = round(image.width() / 2 + (index % 8 - 3.5) * 4 * scale)
        y = round(image.height() / 2 + (index // 8 - 3.5) * 4 * scale)
        if not (0 <= x < image.width() and 0 <= y < image.height()):
            return False
        color = image.pixelColor(x, y)
        channels = (color.red(), color.green(), color.blue())
        if bit == "1" and min(channels) < 224:
            return False
        if bit == "0" and max(channels) > 31:
            return False
    return True

_INSTALL_NATIVE_QT_TITLEBAR_LAYOUT = """
document.documentElement.classList.add('pdm-native-qt-titlebar');
"""

_ARM_TRAY_HIDE_PRESENTATION = """
(() => {
  const generation = __PDM_GENERATION__;
  document.documentElement.classList.add('pdm-native-window-chrome');
  document.querySelectorAll('.titlebar-ctrl.pdm-native-hover').forEach(
    (element) => element.classList.remove('pdm-native-hover')
  );
  window.__pdmNativeTrayHidePresentationReady = 0;
  window.requestAnimationFrame(() => {
    window.requestAnimationFrame(() => {
      const controls = Array.from(
        document.querySelectorAll('.titlebar-ctrl')
      );
      const close = document.querySelector('.titlebar-ctrl.close');
      const closeStyle = close ? getComputedStyle(close) : null;
      const transitionDurations = closeStyle
        ? closeStyle.transitionDuration.split(',').map((value) => value.trim())
        : [];
      const neutral = Boolean(
        close
        && controls.length === 3
        && controls.every(
          (element) => !element.classList.contains('pdm-native-hover')
        )
        && closeStyle.backgroundColor !== 'rgb(232, 17, 35)'
        && transitionDurations.length > 0
        && transitionDurations.every((value) => value === '0s')
      );
      window.__pdmNativeTrayHidePresentationReady = neutral
        ? generation
        : -generation;
    });
  });
  return generation;
})()
"""

_TRAY_FAILURE_TEXT = {
    "zh": {
        "title": "无法最小化到托盘",
        "message": (
            "系统托盘暂时不可用，窗口将保持打开。"
            "是否改为安全退出？"
        ),
        "exit": "退出",
        "cancel": "取消",
    },
    "en": {
        "title": "Unable to minimize to tray",
        "message": (
            "The system tray is currently unavailable, so the window will "
            "remain open. Exit securely instead?"
        ),
        "exit": "Exit",
        "cancel": "Cancel",
    },
}

_SYNC_MAXIMIZE_CONTROL = """
(() => {
  // The native host owns non-client hit testing.  Disable Chromium's
  // independently cached :hover authority before the first visible frame so
  // a tray round-trip cannot replay the close button's old hover paint.
  document.documentElement.classList.add('pdm-native-window-chrome');
  const maximized = __PDM_MAXIMIZED__;
  if (typeof setWindowMaximizeControlState === 'function') {
    return setWindowMaximizeControlState(maximized);
  }
  const button = document.querySelector(
    '[data-pdm-window-control="maximize"]'
  );
  if (!button) return false;
  const key = maximized
    ? 'titlebar.button.restore'
    : 'titlebar.button.maximize';
  const fallback = maximized ? '还原' : '最大化';
  const label = typeof t === 'function' ? t(key) : fallback;
  button.setAttribute(
    'data-pdm-window-state',
    maximized ? 'maximized' : 'normal'
  );
  button.setAttribute('data-i18n-title', key);
  button.title = label;
  button.setAttribute('aria-label', label);
  return true;
})()
"""

_RENDERER_TERMINATION_STATUS = {
    QWebEnginePage.RenderProcessTerminationStatus.NormalTerminationStatus: (
        RendererTerminationStatus.NORMAL
    ),
    QWebEnginePage.RenderProcessTerminationStatus.AbnormalTerminationStatus: (
        RendererTerminationStatus.ABNORMAL
    ),
    QWebEnginePage.RenderProcessTerminationStatus.CrashedTerminationStatus: (
        RendererTerminationStatus.CRASHED
    ),
    QWebEnginePage.RenderProcessTerminationStatus.KilledTerminationStatus: (
        RendererTerminationStatus.KILLED
    ),
}

_BASE_CURTAIN_SURFACE_MODES = {
    RendererRecoveryViewState.CLIPBOARD_EXIT_RETRYING: RendererRecoverySurfaceMode.FULL_NATIVE,
    RendererRecoveryViewState.CLIPBOARD_EXIT_BLOCKED: RendererRecoverySurfaceMode.FULL_NATIVE,
    RendererRecoveryViewState.STARTING:
        RendererRecoverySurfaceMode.FULL_NATIVE,
    RendererRecoveryViewState.SECURING:
        RendererRecoverySurfaceMode.FULL_NATIVE,
    RendererRecoveryViewState.TRANSITION:
        RendererRecoverySurfaceMode.FULL_NATIVE,
    RendererRecoveryViewState.LOCKED:
        RendererRecoverySurfaceMode.FULL_NATIVE,
    RendererRecoveryViewState.RECOVERY_AVAILABLE:
        RendererRecoverySurfaceMode.FULL_NATIVE,
    RendererRecoveryViewState.REBUILDING:
        RendererRecoverySurfaceMode.FULL_NATIVE,
    RendererRecoveryViewState.BLOCKED:
        RendererRecoverySurfaceMode.FULL_NATIVE,
    RendererRecoveryViewState.POWER_PROTECTION_UNAVAILABLE:
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


class HostWindow(QMainWindow):
    """M2 candidate host.

    M2.3 adds native tray/focus lifecycle and owns lazy native capability
    adapters. The base host still has no QWebChannel object, real user state,
    or page-to-capability wiring. Later candidate gates extend it only through
    explicit page and security hooks.
    """

    canvas_ready = Signal()
    canvas_failed = Signal()
    hidden_to_tray = Signal()
    restored_from_tray = Signal()
    power_suspending = Signal(int)
    power_resumed = Signal(str, int)
    session_locked = Signal()
    session_lock_availability_changed = Signal(bool)
    resume_health_checked = Signal(bool)
    restored_from_taskbar = Signal(int)
    standard_surface_refresh_queued = Signal(int, object, int)
    exit_requested = Signal()

    def __init__(
        self,
        catalog: ResourceCatalog | None = None,
        *,
        enable_tray: bool = True,
        close_to_tray: bool = True,
        tray_controller_factory: (
            Callable[["HostWindow"], TrayController] | None
        ) = None,
        tray_failure_confirmation: Callable[[str], bool] | None = None,
        show_tray_on_init: bool = True,
        standard_window_frame: bool = False,
    ) -> None:
        super().__init__()
        self._renderer_curtain_sidebar_width = PRODUCT_SIDEBAR_WIDTH
        self._requested_renderer_curtain_sidebar_width = PRODUCT_SIDEBAR_WIDTH
        if type(standard_window_frame) is not bool:
            raise TypeError("standard_window_frame must be bool")
        self._standard_window_frame = standard_window_frame
        if self._standard_window_frame:
            if sys.platform != "win32":
                raise RuntimeError(
                    "standard window frame candidate requires Windows"
                )
            self.setWindowFlags(
                Qt.WindowType.Window
                | Qt.WindowType.WindowTitleHint
                | Qt.WindowType.WindowSystemMenuHint
                | Qt.WindowType.WindowMinimizeButtonHint
                | Qt.WindowType.WindowMaximizeButtonHint
                | Qt.WindowType.WindowCloseButtonHint
            )
        else:
            self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setWindowTitle("小仓")
        self.setWindowIcon(application_icon())
        self.resize(1200, 800)
        self.setMinimumSize(960, 640)

        self.product_titlebar: ProductTitleBar | None = None
        if self._standard_window_frame:
            self.product_titlebar = ProductTitleBar(self)
            self.product_titlebar.minimize_requested.connect(
                lambda: self._perform_window_control("minimize")
            )
            self.product_titlebar.maximize_requested.connect(
                lambda: self._perform_window_control("maximize")
            )
            self.product_titlebar.close_requested.connect(
                lambda: self._perform_window_control("close")
            )
            self.setMenuWidget(self.product_titlebar)

        self._catalog = catalog or ResourceCatalog()
        self.diagnostics = FixedDiagnosticRecorder()
        self.security = SecurityBoundaryCoordinator()
        self.renderer_lifecycle = RendererLifecycleController(
            self.security,
            diagnostics=self.diagnostics,
        )
        initial_transition = self.renderer_lifecycle.start_initial_page()
        if initial_transition.decision is not RendererDecision.INITIAL_PAGE_REQUIRED:
            raise RuntimeError("renderer lifecycle did not start")
        self.web = AppWebProfile(
            self,
            self._catalog,
            diagnostics=self.diagnostics,
            page_generation=initial_transition.page_generation,
        )
        self.view = QWebEngineView(self)
        self.view.setPage(self.web.page)
        self.view.setAcceptDrops(False)
        self.view.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        self.setCentralWidget(self.view)
        self.renderer_curtain = RendererRecoveryCurtain(self)
        self.renderer_curtain.hide()
        self.renderer_curtain.retry_requested.connect(self._on_renderer_retry)
        self.renderer_curtain.clipboard_exit_confirmed.connect(self._confirm_clipboard_exit)
        self.renderer_curtain.minimize_requested.connect(
            lambda: self._perform_window_control("minimize")
        )
        self.renderer_curtain.maximize_requested.connect(
            lambda: self._perform_window_control("maximize")
        )
        self.renderer_curtain.exit_requested.connect(self.request_exit)
        self._sensitive_dom = SensitiveDomController(self.web.page)
        self._renderer_page_generation = initial_transition.page_generation
        self._canvas_probe_generation = 0
        self._canvas_probe_serial = 0
        self._canvas_probe_token = 0
        self._renderer_presentation_generation = 0
        self._renderer_presentation_serial = 0
        self._renderer_presentation_token = 0
        self._renderer_presentation_frame_gate: (
            _RendererPresentationFrameGate | None
        ) = None
        self._renderer_presentation_probe_attempts = 0
        self._renderer_presentation_confirmed_generation = 0
        self._renderer_signal_page = None
        self._renderer_signal_handler = None
        self._bind_renderer_page(self.web.page, self._renderer_page_generation)
        self.chrome_input = WebChromeInputFilter(
            self,
            self.view,
            reset_focus_visibility=self._reset_web_focus_visibility,
        )
        app = QApplication.instance()
        self._chrome_filter_installed = app is not None
        if app is not None:
            app.installEventFilter(self.chrome_input)
        self._corner_preference_applied = False
        self._native_control_pressed: int | None = None
        self._native_control_hover: int | None = None
        self._tray_hide_settling = False
        self._exit_after_tray_hide_settle = False
        self._tray_hide_presentation_generation = 0
        self._tray_hide_presentation_confirmed_generation = 0
        self._tray_hide_presentation_acceptor: Callable[[], None] | None = None
        self._tray_focus_restore_serial = 0
        self._tray_focus_restore_token = 0
        self._native_hover_restore_pending = False
        self.native = NativeCapabilities(self, security=self.security)
        self.security.register(
            SecurityCleanupPhase.CONCEAL_RENDERER,
            "host.renderer.conceal",
            self._conceal_renderer,
        )
        self.security.register(
            SecurityCleanupPhase.CLEAR_NATIVE_SECRETS,
            "host.sensitive_dom.clear",
            lambda context: self._sensitive_dom.clear_all(
                context.reason.value
            ),
        )
        self.power = PowerLifecycle(self)
        self.power.suspending.connect(self._on_power_suspending)
        self.power.resumed.connect(self._on_power_resumed)
        self.session_lock = SessionLockLifecycle(self)
        self.session_lock.locked.connect(self._on_session_locked)
        self.session_lock.availability_changed.connect(self._on_session_lock_availability_changed)
        self._power_was_visible = False
        self._power_was_active = False
        self._power_focus_restore_serial = 0
        self._power_focus_restore_token = 0
        self._resume_health_ok = False
        self._taskbar_restore_count = 0
        self._renderer_surface_refresh_count = 0
        self._renderer_restore_generation = 0
        self._standard_surface_refresh_generation = 0
        self._standard_surface_refresh_serial = 0
        self._standard_surface_refresh_bound_handle = None
        self._standard_surface_refresh_pending_handle = None
        self._standard_surface_hover_refresh_pending = False
        self.standard_surface_refresh_queued.connect(
            self._consume_standard_surface_refresh_queued,
            Qt.ConnectionType.QueuedConnection,
        )
        self._standard_scene_refresh = SceneRefresh(
            self, lambda: HostWindow._standard_scene_refresh_target(self),
        )
        self._native_normal_rect: tuple[int, int, int, int] | None = None
        self._minimized_restore_maximized = False
        self._dpi_geometry_fit_count = 0
        self._dpi_maximized_settlement_count = 0
        self._dpi_maximized_settlement_signature: (
            tuple[str, int, int, int, int, int] | None
        ) = None
        self._dpi_surface_refresh_count = 0
        self._dpi_fit_generation = 0
        self._last_dpi_fit_before = QRect()
        self._last_dpi_fit_after = QRect()
        self._window_screen_change_bound_handle = None
        self._geometry_screen = None
        self._last_cleanup_result: CleanupResult | None = None
        self._close_to_tray = bool(close_to_tray)
        self._allow_exit = False
        self._exit_cleanup_started = False
        self._exit_cleanup_complete = False
        self._exit_clipboard_state = ""
        self._exit_clipboard_resolved = False
        self._exit_clipboard_attempts = 0
        self._exit_clipboard_timer = QTimer(self)
        self._exit_clipboard_timer.setSingleShot(True)
        self._exit_clipboard_timer.timeout.connect(self._retry_exit_clipboard)
        self._exit_teardown_attempted: list[str] = []
        self._exit_teardown_failures: list[str] = []
        self._native_language = "zh"
        self._tray_failure_confirmation = tray_failure_confirmation
        self._tray_failure_dialog: QMessageBox | None = None
        self._tray_hidden = False
        self._tray_restore_maximized = False
        self._tray_restore_geometry = QRect()
        self._maximized_from_tray = False
        tray_factory = tray_controller_factory or TrayController
        try:
            self.tray = tray_factory(self) if enable_tray else None
        except Exception:
            self.tray = None
        if self.tray is not None:
            try:
                self.tray.restore_requested.connect(self.restore_from_tray)
                self.tray.exit_requested.connect(self.request_exit)
                if show_tray_on_init:
                    self.tray.show()
            except Exception:
                try:
                    self.tray.hide()
                except Exception:
                    pass
                self.tray = None

        self.ready = False
        self.load_ok = False
        self.load_progress = 0
        self.load_finished_count = 0
        self._probe_attempts = 0
        self._prepare_native_qt_titlebar_page(self.web.page)
        self._prepare_candidate_page(self.web.page)
        if self.standard_window_frame:
            hwnd = int(self.winId())
            if not apply_standard_window_frame(hwnd):
                raise RuntimeError(
                    "standard window frame candidate could not initialize"
                )
            if not set_win11_border_color_none(hwnd):
                raise RuntimeError(
                    "standard window frame candidate could not set DWM border"
                )
            self._sync_standard_surface_refresh_filter()
        self.view.setUrl(QUrl(ENTRY_URL))
        HostWindow._sync_clipboard_window_handle(self)

    def _prepare_candidate_page(self, _page: QWebEnginePage) -> None:
        """Extension hook run before a candidate page receives its URL."""

    def _prepare_native_qt_titlebar_page(self, page: QWebEnginePage) -> None:
        """Install the candidate layout before any guarded surface appears."""

        if getattr(self, "product_titlebar", None) is None:
            return
        script = QWebEngineScript()
        script.setName("pdm-native-qt-titlebar-layout")
        script.setInjectionPoint(
            QWebEngineScript.InjectionPoint.DocumentReady
        )
        script.setWorldId(QWebEngineScript.ScriptWorldId.ApplicationWorld)
        script.setRunsOnSubFrames(False)
        script.setSourceCode(_INSTALL_NATIVE_QT_TITLEBAR_LAYOUT)
        page.scripts().insert(script)

    def _retire_candidate_page(self, _page: QWebEnginePage) -> None:
        """Extension hook run before an obsolete page is destroyed."""

    def _run_current_focus_visibility_script(self, source: str) -> None:
        """向当前页面发送一次固定焦点清理；失效时直接放弃。"""

        if getattr(self, "_exit_cleanup_started", False):
            return
        web = getattr(self, "web", None)
        page = getattr(web, "page", None)
        if page is None:
            return
        try:
            page.runJavaScript(source)
        except Exception:
            pass

    def _reset_web_focus_visibility(self) -> None:
        """清除当前页面的可见键盘模式，但保留原生暂存槽。"""

        self._run_current_focus_visibility_script(
            _RESET_WEB_FOCUS_VISIBILITY
        )

    def _clear_web_focus_visibility(self) -> None:
        """清空当前页面的模式、作用域与原生暂存描述。"""

        self._run_current_focus_visibility_script(
            _CLEAR_WEB_FOCUS_VISIBILITY
        )

    def _reset_renderer_curtain_focus_visibility(self) -> None:
        """归零幕布的局部原生焦点可见模式。"""

        controller = getattr(
            getattr(self, "renderer_curtain", None),
            "_focus_visibility",
            None,
        )
        if controller is None:
            return
        try:
            controller.reset()
        except Exception:
            pass

    def _renderer_security_epochs(self) -> tuple[int, int]:
        """Return the active authority identity for renderer diagnostics."""

        return 0, 0

    def _renderer_presentation_arm_source(
        self,
        generation: int,
        presentation_token: int,
    ) -> str:
        """Return the full-identity two-frame presentation arm script."""

        return (
            _ARM_RENDERER_PRESENTATION.replace(
                "__PDM_GENERATION__",
                str(generation),
            ).replace(
                "__PDM_PRESENTATION_TOKEN__",
                str(presentation_token),
            )
        )

    def _renderer_presentation_probe_source(
        self,
        generation: int,
        presentation_token: int,
    ) -> str:
        """Return the candidate-specific final-frame readiness probe."""

        return (
            _PROBE_RENDERER_PRESENTATION.replace(
                "__PDM_GENERATION__",
                str(generation),
            ).replace(
                "__PDM_PRESENTATION_TOKEN__",
                str(presentation_token),
            )
        )

    def _renderer_curtain_is_installed_for_presentation(self) -> bool:
        """Return whether the current native curtain may guard a handoff."""

        return self.renderer_curtain.isVisible()

    def _prepare_renderer_page_for_presentation(self, generation: int) -> bool:
        """Prepare the current page without changing base-host visibility."""

        return generation == self._renderer_page_generation

    def _renderer_presentation_must_wait(self, _generation: int) -> bool:
        """Return whether a valid guarded handoff must wait for visibility."""

        return False

    def _on_renderer_presentation_started(
        self,
        _generation: int,
        _presentation_token: int,
    ) -> None:
        """单次呈现取得令牌后的扩展点。"""

    def _on_renderer_presentation_frames_ready(
        self,
        generation: int,
        presentation_token: int,
    ) -> None:
        """现有两帧通过后立即执行既有交接。"""

        if presentation_token != self._renderer_presentation_token:
            return
        self._complete_renderer_presentation(generation)

    def _clear_renderer_presentation_frame_gate(self) -> None:
        gate = getattr(self, "_renderer_presentation_frame_gate", None)
        self._renderer_presentation_frame_gate = None
        if gate is not None and gate.stamp_bits and isValid(gate.view):
            try:
                gate.view.page().runJavaScript(_presentation_stamp_source(gate, remove=True))
            except RuntimeError:
                pass
        if gate is None or not gate.frame_connected or not isValid(gate.quick_window):
            return
        gate.frame_connected = False
        try:
            gate.quick_window.afterFrameEnd.disconnect(gate.callback)
        except (RuntimeError, TypeError):
            pass

    def _renderer_presentation_frame_gate_is_current(
        self,
        gate: _RendererPresentationFrameGate,
    ) -> bool:
        if (
            self._renderer_presentation_frame_gate is not gate
            or gate.generation != self._renderer_presentation_generation
            or gate.generation != self._renderer_page_generation
            or gate.presentation_token != self._renderer_presentation_token
            or self.renderer_lifecycle.state
            is not RendererLifecycleState.ACTIVE
            or not self._renderer_curtain_is_installed_for_presentation()
            or self._renderer_presentation_must_wait(gate.generation)
            or self.view is not gate.view
            or not isValid(gate.view)
            or not isValid(gate.quick_widget)
            or not isValid(gate.quick_window)
        ):
            return False
        try:
            return (
                gate.view.focusProxy() is gate.quick_widget
                and gate.quick_widget.quickWindow() is gate.quick_window
            )
        except RuntimeError:
            return False

    def _request_renderer_presentation_frame(
        self,
        generation: int,
        presentation_token: int,
    ) -> None:
        if (
            generation != self._renderer_presentation_generation
            or generation != self._renderer_page_generation
            or presentation_token != self._renderer_presentation_token
            or self.renderer_lifecycle.state
            is not RendererLifecycleState.ACTIVE
            or not self._renderer_curtain_is_installed_for_presentation()
        ):
            return
        existing_gate = self._renderer_presentation_frame_gate
        if isinstance(existing_gate, _RendererPresentationFrameGate):
            if self._renderer_presentation_frame_gate_is_current(existing_gate):
                return
        HostWindow._clear_renderer_presentation_frame_gate(self)
        view = self.view
        try:
            quick_widget = view.focusProxy()
            if not isinstance(quick_widget, QQuickWidget) or not isValid(
                quick_widget
            ):
                raise RuntimeError("WebEngine Quick widget is unavailable")
            quick_window = quick_widget.quickWindow()
            if quick_window is None or not isValid(quick_window):
                raise RuntimeError("WebEngine Quick window is unavailable")
        except RuntimeError:
            self._fail_renderer_presentation(generation)
            return

        gate: _RendererPresentationFrameGate

        def frame_submitted() -> None:
            self._on_renderer_presentation_frame_submitted(gate)

        gate = _RendererPresentationFrameGate(
            generation=generation,
            presentation_token=presentation_token,
            view=view,
            quick_widget=quick_widget,
            quick_window=quick_window,
            callback=frame_submitted,
            stamp_bits="10100101" + format(secrets.randbits(56), "056b"),
            geometry=(view.width(), view.height(), view.zoomFactor(), view.devicePixelRatioF()),
        )
        self._renderer_presentation_frame_gate = gate
        self.web.page.runJavaScript(
            _presentation_stamp_source(gate, remove=False),
            lambda ready: self._on_renderer_presentation_stamp_changed(gate, False, ready),
        )
        # 首次绘制可能晚于网页就绪；启动单独留出成像预算，仍凭标记交付撤幕。
        QTimer.singleShot(
            _STARTUP_FRAME_TIMEOUT_MS
            if self.renderer_curtain.state is RendererRecoveryViewState.STARTING
            else _RENDERER_PRESENTATION_TIMEOUT_MS,
            lambda: self._on_renderer_presentation_frame_timeout(gate),
        )

    def _on_renderer_presentation_stamp_changed(self, gate, removed: bool, ready: object) -> None:
        if not self._renderer_presentation_frame_gate_is_current(gate):
            return
        if ready is not True:
            self._fail_renderer_presentation(gate.generation)
            return
        gate.stamp_removed = removed
        try:
            gate.quick_window.afterFrameEnd.connect(
                gate.callback,
                Qt.ConnectionType.QueuedConnection,
            )
            gate.frame_connected = True
            gate.quick_window.update()
        except (RuntimeError, TypeError):
            HostWindow._clear_renderer_presentation_frame_gate(self)
            self._fail_renderer_presentation(gate.generation)

    def _on_renderer_presentation_frame_timeout(self, gate) -> None:
        if self._renderer_presentation_frame_gate is gate:
            self._fail_renderer_presentation(gate.generation)

    def _on_renderer_presentation_frame_submitted(
        self,
        gate: _RendererPresentationFrameGate,
    ) -> None:
        if self._renderer_presentation_frame_gate is not gate:
            return
        if not self._renderer_presentation_frame_gate_is_current(gate):
            HostWindow._clear_renderer_presentation_frame_gate(self)
            return
        if not gate.frame_connected:
            return
        view = gate.view
        if gate.geometry != (view.width(), view.height(), view.zoomFactor(), view.devicePixelRatioF()):
            HostWindow._clear_renderer_presentation_frame_gate(self)
            self._begin_renderer_presentation(gate.generation)
            return
        # 回读本身会绘制一帧，先断开信号，避免把回读触发的帧当成下一次交付。
        gate.quick_window.afterFrameEnd.disconnect(gate.callback)
        gate.frame_connected = False
        image = None
        try:
            image = gate.quick_widget.grabFramebuffer()
            if image.isNull():
                self._fail_renderer_presentation(gate.generation)
                return
            scale = image.width() / view.width() * view.zoomFactor()
            marked = _image_has_presentation_stamp(image, gate.stamp_bits, scale)
        except RuntimeError:
            self._fail_renderer_presentation(gate.generation)
            return
        finally:
            if image is not None:
                # 旧纹理可能仍含已撤权内容；临时CPU图像不保存，并在回调内清空。
                image.fill(0)
                del image
        if gate.stamp_removed and not marked:
            HostWindow._clear_renderer_presentation_frame_gate(self)
            self._complete_renderer_presentation(gate.generation)
        elif not gate.stamp_removed and marked:
            self.web.page.runJavaScript(
                _presentation_stamp_source(gate, remove=True),
                lambda ready: self._on_renderer_presentation_stamp_changed(gate, True, ready),
            )
        else:
            # 仍是旧图时等实际的新帧通知，不靠计时轮询或重复强制重画。
            gate.quick_window.afterFrameEnd.connect(gate.callback, Qt.ConnectionType.QueuedConnection)
            gate.frame_connected = True

    def _on_renderer_curtain_hidden(self, generation: int) -> None:
        """原生幕布实际隐藏后的扩展点。"""

        if (
            generation == self._renderer_page_generation
            and getattr(self, "standard_window_frame", False)
        ):
            self._consume_standard_surface_refresh()

    def _current_qwindow_handle(self):
        handle = self.windowHandle()
        if handle is None or not isValid(handle):
            return None
        return handle

    def _sync_standard_surface_refresh_filter(self):
        current = self._current_qwindow_handle()
        bound = self._standard_surface_refresh_bound_handle
        if bound is not current:
            HostWindow._cancel_standard_scene_refresh(self)
            if bound is not None and isValid(bound):
                bound.removeEventFilter(self)
            self._standard_surface_refresh_bound_handle = None
            if current is not None:
                current.installEventFilter(self)
                self._standard_surface_refresh_bound_handle = current
        pending = self._standard_surface_refresh_pending_handle
        if pending is not current:
            self._clear_standard_surface_refresh()
        return current

    def _sync_window_screen_change_binding(self):
        current = self._current_qwindow_handle()
        bound = self._window_screen_change_bound_handle
        if bound is not current:
            if bound is not None and isValid(bound):
                bound.screenChanged.disconnect(self._on_window_screen_changed)
            self._window_screen_change_bound_handle = None
            if current is not None:
                current.screenChanged.connect(self._on_window_screen_changed)
                self._window_screen_change_bound_handle = current
        return current

    def _register_standard_surface_refresh(
        self,
        *,
        reproject_hover: bool = False,
    ) -> None:
        """登记当前页面刷新，交给 Qt 事件队列及真实露出条件消费。"""

        if not self.standard_window_frame:
            return
        handle = self._sync_standard_surface_refresh_filter()
        if handle is None:
            self._clear_standard_surface_refresh()
            return
        preserve_hover = (
            self._standard_surface_refresh_pending_handle is handle
            and self._standard_surface_refresh_generation == self._renderer_page_generation
            and self._standard_surface_hover_refresh_pending
        )
        self._standard_surface_refresh_generation = self._renderer_page_generation
        self._standard_surface_refresh_pending_handle = handle
        self._standard_surface_hover_refresh_pending = bool(
            reproject_hover or preserve_hover
        )
        self._standard_surface_refresh_serial += 1
        self._queue_standard_surface_refresh(handle)

    def _queue_standard_surface_refresh(self, source_handle=None) -> None:
        handle = self._standard_surface_refresh_pending_handle
        generation = self._standard_surface_refresh_generation
        if (
            type(generation) is not int
            or generation <= 0
            or handle is None
            or source_handle is not None and source_handle is not handle
        ):
            return
        self.standard_surface_refresh_queued.emit(
            self._standard_surface_refresh_serial,
            handle,
            generation,
        )

    def _consume_standard_surface_refresh_queued(
        self,
        serial: int,
        source_handle,
        generation: int,
    ) -> None:
        if (
            serial != self._standard_surface_refresh_serial
            or generation != self._standard_surface_refresh_generation
            or source_handle is not self._standard_surface_refresh_pending_handle
        ):
            return
        self._consume_standard_surface_refresh(source_handle=source_handle)

    def _clear_standard_surface_refresh(self) -> None:
        self._standard_surface_refresh_serial += 1
        self._standard_surface_refresh_generation = 0
        self._standard_surface_refresh_pending_handle = None
        self._standard_surface_hover_refresh_pending = False

    def _consume_standard_surface_refresh(self, source_handle=None) -> bool:
        generation = getattr(self, "_standard_surface_refresh_generation", 0)
        if type(generation) is not int or generation <= 0:
            return False
        if generation != self._renderer_page_generation:
            self._clear_standard_surface_refresh()
            return False
        handle = self._sync_standard_surface_refresh_filter()
        pending = self._standard_surface_refresh_pending_handle
        if handle is None or pending is None or not isValid(pending):
            self._clear_standard_surface_refresh()
            return False
        if pending is not handle:
            self._clear_standard_surface_refresh()
            return False
        if source_handle is not None and source_handle is not handle:
            return False
        if (
            not handle.isExposed()
            or not self.isVisible()
            or self.isMinimized()
            or self.renderer_lifecycle.state
            is not RendererLifecycleState.ACTIVE
            or self.renderer_curtain.isVisible()
        ):
            return False
        if self._standard_surface_hover_refresh_pending:
            actual_hit = self._native_control_hit_at_cursor(
                int(handle.winId())
            )
            self._native_hover_restore_pending = False
            self._set_native_control_hover(actual_hit, force=True)
        self._clear_standard_surface_refresh()
        self._request_web_surface_frame_now()
        HostWindow._schedule_standard_scene_refresh(self)
        return True

    def _standard_scene_refresh_target(self):
        """只返回当前可呈现的标准窗口场景，不创建窗口或改变可见性。"""

        if (
            not self.standard_window_frame
            or not self.ready
            or not self.isVisible()
            or self.isMinimized()
            or self.renderer_lifecycle.state is not RendererLifecycleState.ACTIVE
            or self.renderer_curtain.isVisible()
            or self._allow_exit
            or self._exit_cleanup_started
        ):
            return None
        try:
            return scene_target(
                self.view,
                HostWindow._current_qwindow_handle(self),
                self._renderer_page_generation,
            )
        except (RuntimeError, TypeError):
            return None

    def _cancel_standard_scene_refresh(self) -> None:
        refresh = getattr(self, "_standard_scene_refresh", None)
        if refresh is not None:
            refresh.cancel()

    def _schedule_standard_scene_refresh(self) -> None:
        """合并窗口变更，约200毫秒后仅重绘一帧，不循环补偿。"""

        refresh = getattr(self, "_standard_scene_refresh", None)
        if refresh is not None:
            refresh.schedule()

    def _consume_standard_scene_refresh(self) -> None:
        self._standard_scene_refresh.consume()

    @property
    def bridge_attached(self) -> bool:
        """Whether this explicit candidate mode attached a typed Bridge."""

        return False

    def _bind_renderer_page(
        self,
        page: QWebEnginePage,
        generation: int,
    ) -> None:
        termination_handler = (
            lambda status, exit_code, generation=generation:
            self._on_renderer_terminated(
                generation,
                status,
                exit_code,
            )
        )
        progress_handler = (
            lambda progress, generation=generation:
            self._on_load_progress(generation, progress)
        )
        finished_handler = (
            lambda ok, generation=generation:
            self._on_load_finished(generation, ok)
        )
        page.renderProcessTerminated.connect(termination_handler)
        page.loadProgress.connect(progress_handler)
        page.loadFinished.connect(finished_handler)
        self._renderer_signal_page = page
        self._renderer_signal_handler = termination_handler
        self._renderer_progress_handler = progress_handler
        self._renderer_finished_handler = finished_handler

    def _unbind_renderer_page(self) -> None:
        HostWindow._cancel_standard_scene_refresh(self)
        self._clear_standard_surface_refresh()
        page = self._renderer_signal_page
        if page is None:
            return
        for signal, handler in (
            (page.renderProcessTerminated, self._renderer_signal_handler),
            (page.loadProgress, self._renderer_progress_handler),
            (page.loadFinished, self._renderer_finished_handler),
        ):
            try:
                signal.disconnect(handler)
            except (RuntimeError, TypeError):
                pass
        self._renderer_signal_page = None
        self._renderer_signal_handler = None
        self._renderer_progress_handler = None
        self._renderer_finished_handler = None

    def _on_load_progress(self, generation: int, progress: int) -> None:
        if generation == self._renderer_page_generation:
            self.load_progress = int(progress)

    def _on_load_finished(self, generation: int, ok: bool) -> None:
        if generation != self._renderer_page_generation:
            return
        if self.renderer_lifecycle.state not in {
            RendererLifecycleState.STARTING,
            RendererLifecycleState.RECOVERING,
        }:
            return
        self.load_finished_count += 1
        self.load_ok = bool(ok and self.web.page.url() == QUrl(ENTRY_URL))
        if not self.load_ok:
            self.ready = False
            self._clear_canvas_probe()
            self.renderer_lifecycle.mark_recovery_failed(generation)
            self._show_renderer_curtain(RendererRecoveryViewState.BLOCKED)
            self.canvas_failed.emit()
            return
        self._start_canvas_probe(generation)

    def _clear_canvas_probe(self) -> None:
        """作废当前页面的基础画布检查及其迟到回调。"""

        self._canvas_probe_generation = 0
        self._canvas_probe_token = 0

    def _canvas_probe_is_current(
        self,
        generation: int,
        token: int,
    ) -> bool:
        return bool(
            generation == self._canvas_probe_generation
            and generation == self._renderer_page_generation
            and token == self._canvas_probe_token
            and token > 0
            and self.renderer_lifecycle.state
            in {
                RendererLifecycleState.STARTING,
                RendererLifecycleState.RECOVERING,
            }
        )

    def _canvas_probe_must_wait(self, generation: int) -> bool:
        """子类可在页面无法稳定执行脚本时延后创建新的画布检查。"""

        del generation
        return False

    def _start_canvas_probe(self, generation: int) -> None:
        """开始一轮有界基础画布检查，网页吞掉回调也必须失败闭合。"""

        if generation != self._renderer_page_generation:
            return
        if self.renderer_lifecycle.state not in {
            RendererLifecycleState.STARTING,
            RendererLifecycleState.RECOVERING,
        }:
            return
        if self._canvas_probe_must_wait(generation):
            return
        self._canvas_probe_serial += 1
        token = self._canvas_probe_serial
        self._canvas_probe_generation = generation
        self._canvas_probe_token = token
        self._probe_attempts = 0
        self._probe_canvas(generation, token)
        QTimer.singleShot(
            _CANVAS_PROBE_TIMEOUT_MS,
            lambda generation=generation, token=token:
            self._on_canvas_probe_timeout(generation, token),
        )

    def _probe_canvas(self, generation: int, token: int) -> None:
        if not self._canvas_probe_is_current(generation, token):
            return
        self._probe_attempts += 1
        layout_ready = ""
        if getattr(self, "product_titlebar", None) is not None:
            layout_ready = (
                " && document.documentElement.classList.contains("
                "'pdm-native-qt-titlebar')"
                " && document.querySelector('.window-titlebar')"
                " && getComputedStyle(document.querySelector("
                "'.window-titlebar')).display === 'none'"
            )
        self.web.page.runJavaScript(
            "Boolean(window.pdmProduct && window.pdmProduct.ready "
            "&& document.querySelector('#canvas-frame')"
            f"{layout_ready})",
            lambda ready, generation=generation, token=token:
            self._on_canvas_probe(
                generation,
                token,
                ready,
            ),
        )

    def _on_canvas_probe(
        self,
        generation: int,
        token: int,
        ready: object,
    ) -> None:
        if not self._canvas_probe_is_current(generation, token):
            return
        self.ready = bool(ready)
        if self.ready:
            self._clear_canvas_probe()
            transition = self.renderer_lifecycle.mark_page_ready(generation)
            if transition.state is not RendererLifecycleState.ACTIVE:
                self.ready = False
                self._show_renderer_curtain(
                    RendererRecoveryViewState.BLOCKED
                )
                self.canvas_failed.emit()
                return
            self._sync_maximize_control()
            if self._renderer_curtain_is_installed_for_presentation():
                self._begin_renderer_presentation(generation)
            else:
                self.view.setEnabled(True)
                self.view.show()
                self.canvas_ready.emit()
        elif self._probe_attempts < 400:
            QTimer.singleShot(
                25,
                lambda generation=generation, token=token:
                self._probe_canvas(generation, token),
            )
        else:
            self._fail_canvas_probe(generation, token)

    def _on_canvas_probe_timeout(self, generation: int, token: int) -> None:
        """网页无回调时固定两秒后进入既有失败幕布。"""

        if not self._canvas_probe_is_current(generation, token):
            return
        self._fail_canvas_probe(generation, token)

    def _fail_canvas_probe(self, generation: int, token: int) -> None:
        if not self._canvas_probe_is_current(generation, token):
            return
        self._clear_canvas_probe()
        self.ready = False
        self.renderer_lifecycle.mark_recovery_failed(generation)
        self._show_renderer_curtain(RendererRecoveryViewState.BLOCKED)
        self.canvas_failed.emit()

    def _begin_renderer_presentation(self, generation: int) -> None:
        if (
            generation != self._renderer_page_generation
            or self.renderer_lifecycle.state
            is not RendererLifecycleState.ACTIVE
            or not self._renderer_curtain_is_installed_for_presentation()
        ):
            self._fail_renderer_presentation(generation)
            return
        if self._renderer_presentation_must_wait(generation):
            return
        if not self._prepare_renderer_page_for_presentation(generation):
            self._fail_renderer_presentation(generation)
            return
        self._renderer_presentation_generation = generation
        self._renderer_presentation_serial += 1
        presentation_token = self._renderer_presentation_serial
        self._renderer_presentation_token = presentation_token
        self._renderer_presentation_probe_attempts = 0
        self._on_renderer_presentation_started(
            generation,
            presentation_token,
        )
        self.view.setEnabled(False)
        self.view.show()
        self.renderer_curtain.raise_()
        self.renderer_curtain.focus_primary_action(
            Qt.FocusReason.ActiveWindowFocusReason
        )
        source = self._renderer_presentation_arm_source(
            generation,
            presentation_token,
        )
        self.web.page.runJavaScript(
            source,
            lambda armed, generation=generation,
            presentation_token=presentation_token:
            self._on_renderer_presentation_armed(
                generation,
                presentation_token,
                armed,
            ),
        )
        QTimer.singleShot(
            _RENDERER_PRESENTATION_TIMEOUT_MS,
            lambda generation=generation,
            presentation_token=presentation_token:
            self._on_renderer_presentation_timeout(
                generation,
                presentation_token,
            ),
        )

    def _on_renderer_presentation_armed(
        self,
        generation: int,
        presentation_token: int,
        armed: object,
    ) -> None:
        if (
            generation != self._renderer_presentation_generation
            or generation != self._renderer_page_generation
            or presentation_token != self._renderer_presentation_token
        ):
            return
        if armed != f"{generation}:{presentation_token}":
            self._fail_renderer_presentation(generation)
            return
        self._probe_renderer_presentation(generation, presentation_token)

    def _probe_renderer_presentation(
        self,
        generation: int,
        presentation_token: int,
    ) -> None:
        if (
            generation != self._renderer_presentation_generation
            or generation != self._renderer_page_generation
            or presentation_token != self._renderer_presentation_token
            or self.renderer_lifecycle.state
            is not RendererLifecycleState.ACTIVE
        ):
            return
        self._renderer_presentation_probe_attempts += 1
        source = self._renderer_presentation_probe_source(
            generation,
            presentation_token,
        )
        self.web.page.runJavaScript(
            source,
            lambda ready, generation=generation,
            presentation_token=presentation_token:
            self._on_renderer_presentation_probe(
                generation,
                presentation_token,
                ready,
            ),
        )

    def _on_renderer_presentation_probe(
        self,
        generation: int,
        presentation_token: int,
        ready: object,
    ) -> None:
        if (
            generation != self._renderer_presentation_generation
            or generation != self._renderer_page_generation
            or presentation_token != self._renderer_presentation_token
        ):
            return
        if ready is True:
            self._on_renderer_presentation_frames_ready(
                generation,
                presentation_token,
            )
            return
        if self._renderer_presentation_probe_attempts < 200:
            QTimer.singleShot(
                10,
                lambda generation=generation,
                presentation_token=presentation_token:
                self._probe_renderer_presentation(
                    generation,
                    presentation_token,
                ),
            )
            return
        self._fail_renderer_presentation(generation)

    def _on_renderer_presentation_timeout(
        self,
        generation: int,
        presentation_token: int,
    ) -> None:
        """Fail closed even when a WebEngine callback never arrives."""

        if (
            generation != self._renderer_presentation_generation
            or generation != self._renderer_page_generation
            or presentation_token != self._renderer_presentation_token
        ):
            return
        if self._renderer_presentation_frame_gate is not None:
            return
        self._fail_renderer_presentation(generation)

    def _complete_renderer_presentation(
        self,
        generation: int,
    ) -> None:
        if (
            generation != self._renderer_presentation_generation
            or generation != self._renderer_page_generation
            or self.renderer_lifecycle.state
            is not RendererLifecycleState.ACTIVE
            or not self._renderer_curtain_is_installed_for_presentation()
        ):
            return
        self._renderer_presentation_confirmed_generation = generation
        HostWindow._clear_renderer_presentation_frame_gate(self)
        self._renderer_presentation_generation = 0
        self._renderer_presentation_token = 0
        # 在同一次事件处理中完成交接，不能同步提交撤幕后仍禁用的中间态。
        self.view.setEnabled(True)
        self._reset_native_control_state(force=True)
        self.renderer_curtain.hide()
        self.view.setFocus(Qt.FocusReason.ActiveWindowFocusReason)
        self._on_renderer_curtain_hidden(generation)
        self.canvas_ready.emit()

    def _fail_renderer_presentation(self, generation: int) -> None:
        if generation != self._renderer_page_generation:
            return
        HostWindow._clear_renderer_presentation_frame_gate(self)
        self._renderer_presentation_generation = 0
        self._renderer_presentation_token = 0
        self.ready = False
        self.view.setEnabled(False)
        self.view.hide()
        self.renderer_lifecycle.mark_recovery_failed(generation)
        self._show_renderer_curtain(RendererRecoveryViewState.BLOCKED)
        self.canvas_failed.emit()

    def _renderer_curtain_surface_mode(
        self,
        state: RendererRecoveryViewState,
    ) -> RendererRecoverySurfaceMode:
        """显式归类基础宿主的全部状态，未知状态直接失败。"""

        if not isinstance(state, RendererRecoveryViewState):
            raise TypeError("renderer curtain state must be fixed")
        try:
            return _BASE_CURTAIN_SURFACE_MODES[state]
        except KeyError:
            raise RuntimeError(
                f"renderer curtain state is not classified: {state!r}"
            ) from None

    def _renderer_curtain_geometry(
        self,
        state: RendererRecoveryViewState,
    ) -> QRect:
        """根据当前窗口尺寸返回逻辑像素矩形。"""

        mode = self._renderer_curtain_surface_mode(state)
        if mode is RendererRecoverySurfaceMode.CONTENT_PROCESSING:
            # 启动先遮住尚未交付的网页侧栏；锁定保留已经可见的外框。
            left = (
                0 if state is RendererRecoveryViewState.STARTING
                else self._renderer_curtain_sidebar_width
            )
            return QRect(
                left,
                TITLEBAR_HEIGHT,
                max(0, self.width() - left),
                max(0, self.height() - TITLEBAR_HEIGHT),
            )
        if mode is RendererRecoverySurfaceMode.FULL_NATIVE:
            return self.rect()
        raise RuntimeError(f"unsupported renderer curtain mode: {mode!r}")

    def set_renderer_curtain_sidebar_width(self, width: int) -> None:
        if width not in {48, PRODUCT_SIDEBAR_WIDTH}:
            raise ValueError("renderer curtain sidebar width is invalid")
        self._requested_renderer_curtain_sidebar_width = width
        # 原生投影早于 QWebChannel 同值首帧：缩窄可立即采用，扩宽必须等待
        # 既有 renderer 呈现帧证明，避免夹缝锁定时暴露旧窄栏的 x=48..71。
        self._renderer_curtain_sidebar_width = min(
            self._renderer_curtain_sidebar_width,
            width,
        )
        self._sync_renderer_curtain_geometry()

    def confirm_renderer_curtain_sidebar_width(self) -> None:
        self._renderer_curtain_sidebar_width = (
            self._requested_renderer_curtain_sidebar_width
        )
        self._sync_renderer_curtain_geometry()

    def _sync_renderer_curtain_geometry(self) -> None:
        """每次尺寸变化后都从当前逻辑尺寸重新计算遮挡区域。"""

        if not hasattr(self, "renderer_curtain"):
            return
        self.renderer_curtain.setGeometry(
            self._renderer_curtain_geometry(self.renderer_curtain.state)
        )

    def _full_native_curtain_is_installed(self) -> bool:
        """完整故障表面由自身显式安装状态授权，与父窗口可见性无关。"""

        return bool(
            hasattr(self, "renderer_curtain")
            and not self.renderer_curtain.isHidden()
            and self.renderer_curtain.surface_mode
            is RendererRecoverySurfaceMode.FULL_NATIVE
        )

    def _show_renderer_curtain(
        self,
        state: RendererRecoveryViewState,
    ) -> None:
        HostWindow._cancel_standard_scene_refresh(self)
        self._clear_web_focus_visibility()
        self._reset_renderer_curtain_focus_visibility()
        mode = self._renderer_curtain_surface_mode(state)
        self.renderer_curtain.set_surface_mode(mode)
        self.renderer_curtain.set_state(state)
        self._sync_renderer_curtain_geometry()
        self.renderer_curtain.set_maximized(
            self.isMaximized() or self._minimized_restore_maximized
        )
        self.renderer_curtain.show()
        self.renderer_curtain.raise_()
        if hasattr(self, "_native_control_hover"):
            self._reset_native_control_state(force=True)
        self.renderer_curtain.focus_primary_action(
            Qt.FocusReason.ActiveWindowFocusReason
        )

    def _install_renderer_conceal_surface(
        self,
        _context: SecurityBoundaryContext,
    ) -> None:
        """Install the native surface that precedes renderer concealment."""

        self._show_renderer_curtain(RendererRecoveryViewState.SECURING)

    def _conceal_renderer(self, context: SecurityBoundaryContext) -> None:
        self.ready = False
        self.load_ok = False
        HostWindow._clear_renderer_presentation_frame_gate(self)
        self._renderer_presentation_generation = 0
        self._renderer_presentation_token = 0
        try:
            self._install_renderer_conceal_surface(context)
        except Exception:
            # 扩展表面安装失败必须让安全步骤保持不完整，但基础固定幕布仍须
            # 先挡住 renderer，不能因扩展异常而暴露旧画面。
            HostWindow._install_renderer_conceal_surface(self, context)
            raise
        finally:
            try:
                self.view.setEnabled(False)
            finally:
                try:
                    app = QApplication.instance()
                    if app is not None:
                        app.sync()
                finally:
                    try:
                        self.view.hide()
                    finally:
                        try:
                            self.set_tray_state(TraySessionState.LOCKED)
                        except Exception:
                            pass

    def _on_renderer_terminated(
        self,
        generation: int,
        status,
        exit_code: int,
    ) -> None:
        normalized = _RENDERER_TERMINATION_STATUS.get(
            status,
            RendererTerminationStatus.ABNORMAL,
        )
        page_epoch, session_epoch = self._renderer_security_epochs()
        transition = self.renderer_lifecycle.handle_termination(
            generation,
            normalized,
            int(exit_code),
            page_epoch=page_epoch,
            session_epoch=session_epoch,
        )
        termination_accepted = (
            transition.recovery_allowed
            or transition.decision
            in {
                RendererDecision.SECURITY_BOUNDARY_BLOCKED,
                RendererDecision.CRASH_STORM_BLOCKED,
            }
        )
        if termination_accepted:
            # 当前页面已经终止；先作废它登记的两帧检查和超时，再发布
            # 恢复/阻断界面。迟到回调只能观察到过期编号并直接退出。
            self._clear_canvas_probe()
            HostWindow._clear_renderer_presentation_frame_gate(self)
            self._renderer_presentation_generation = 0
            self._renderer_presentation_token = 0
        if transition.recovery_allowed:
            self._show_renderer_curtain(
                RendererRecoveryViewState.RECOVERY_AVAILABLE
            )
        elif transition.decision in {
            RendererDecision.SECURITY_BOUNDARY_BLOCKED,
            RendererDecision.CRASH_STORM_BLOCKED,
        }:
            self._show_renderer_curtain(RendererRecoveryViewState.BLOCKED)

    def _begin_renderer_recovery(self) -> None:
        transition = self.renderer_lifecycle.begin_recovery()
        if transition.decision is not RendererDecision.RECOVERY_PAGE_REQUIRED:
            return
        self._show_renderer_curtain(RendererRecoveryViewState.REBUILDING)
        self._rebuild_renderer_page(transition.page_generation)

    def _rebuild_renderer_page(self, generation: int) -> None:
        self._clear_web_focus_visibility()
        old_web = self.web
        old_page = old_web.page
        old_view = self.view
        self._clear_canvas_probe()
        HostWindow._clear_renderer_presentation_frame_gate(self)
        self._unbind_renderer_page()
        self._retire_candidate_page(old_page)
        self._sensitive_dom.detach()
        old_view.setEnabled(False)
        old_view.hide()
        old_page.setVisible(False)
        old_page.triggerAction(QWebEnginePage.WebAction.Stop)

        new_web = AppWebProfile(
            self,
            self._catalog,
            diagnostics=self.diagnostics,
            page_generation=generation,
        )
        new_view = QWebEngineView(self)
        new_view.setPage(new_web.page)
        new_view.setAcceptDrops(False)
        new_view.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        new_view.setEnabled(False)
        new_view.hide()

        detached = self.takeCentralWidget()
        if detached is not old_view:
            if detached is not None:
                detached.setEnabled(False)
                detached.hide()
                detached.deleteLater()
            new_view.deleteLater()
            new_web.page.deleteLater()
            new_web.profile.deleteLater()
            old_view.deleteLater()
            old_page.deleteLater()
            old_web.profile.deleteLater()
            self._renderer_page_generation = generation
            self.renderer_lifecycle.mark_recovery_failed(generation)
            self._show_renderer_curtain(RendererRecoveryViewState.BLOCKED)
            self.canvas_failed.emit()
            return

        self.web = new_web
        self.view = new_view
        self._renderer_page_generation = generation
        self.setCentralWidget(new_view)
        new_view.setEnabled(False)
        new_view.hide()
        self.chrome_input.bind_view(new_view)
        self._sensitive_dom = SensitiveDomController(self.web.page)
        self._prepare_native_qt_titlebar_page(self.web.page)
        self._prepare_candidate_page(self.web.page)
        self._bind_renderer_page(self.web.page, generation)
        self.ready = False
        self.load_ok = False
        self.load_progress = 0
        self._probe_attempts = 0
        new_view.setUrl(QUrl(ENTRY_URL))
        self._sync_renderer_curtain_geometry()
        self.renderer_curtain.raise_()
        self.renderer_curtain.focus_primary_action(
            Qt.FocusReason.ActiveWindowFocusReason
        )

        old_view.deleteLater()
        old_page.deleteLater()
        old_web.profile.deleteLater()

    def _perform_window_control(self, control: str) -> None:
        if control == "minimize":
            restore_to_maximized = self.isMaximized()
            self._minimized_restore_maximized = restore_to_maximized
            if not restore_to_maximized:
                self._remember_native_normal_rect()
            if self.standard_window_frame:
                self.showMinimized()
                return
            if minimize_native_window(
                int(self.winId()),
                restore_to_maximized=restore_to_maximized,
                normal_rect=(
                    self._native_normal_rect
                    if restore_to_maximized
                    else None
                ),
            ):
                return
            self.showMinimized()
        elif control == "maximize":
            self._toggle_maximize()
        elif control == "close":
            self.close()

    def _perform_native_window_control(self, hit: int) -> None:
        control = {
            HTMINBUTTON: "minimize",
            HTMAXBUTTON: "maximize",
            HTCLOSE: "close",
        }.get(hit)
        if control is not None:
            self._perform_window_control(control)

    @staticmethod
    def _native_control_name(hit: int | None) -> str | None:
        return {
            HTMINBUTTON: "minimize",
            HTMAXBUTTON: "maximize",
            HTCLOSE: "close",
        }.get(hit)

    def _project_native_control_state(self) -> None:
        """把唯一原生状态投影到当前可见的标题栏实现。"""

        full_native = self._full_native_curtain_is_installed()
        hovered = self._native_control_name(self._native_control_hover)
        pressed = self._native_control_name(self._native_control_pressed)
        self.renderer_curtain.set_native_titlebar_control_state(
            hovered if full_native else None,
            pressed if full_native else None,
        )
        if getattr(self, "product_titlebar", None) is not None:
            self.product_titlebar.set_control_state(
                hovered if not full_native else None,
                pressed if not full_native else None,
            )
            return
        hover_index = {
            HTMINBUTTON: 0,
            HTMAXBUTTON: 1,
            HTCLOSE: 2,
        }.get(self._native_control_hover, -1)
        pressed_index = {
            HTMINBUTTON: 0,
            HTMAXBUTTON: 1,
            HTCLOSE: 2,
        }.get(self._native_control_pressed, -1)
        if full_native:
            hover_index = -1
            pressed_index = -1
        self.web.page.runJavaScript(
            "document.querySelectorAll('.titlebar-ctrl').forEach("
            "(element, itemIndex) => {"
            f"element.classList.toggle('pdm-native-hover', "
            f"itemIndex === {hover_index} || "
            f"itemIndex === {pressed_index});"
            f"element.classList.toggle('pdm-native-pressed', "
            f"itemIndex === {pressed_index});"
            "});"
        )

    def _set_native_control_hover(
        self,
        hit: int | None,
        *,
        force: bool = False,
    ) -> None:
        if self._tray_hide_settling or self._native_hover_restore_pending:
            hit = None
        if hit not in {HTMINBUTTON, HTMAXBUTTON, HTCLOSE}:
            hit = None
        if hit == self._native_control_hover and not force:
            return
        self._native_control_hover = hit
        self._project_native_control_state()

    def _set_native_control_pressed(
        self,
        hit: int | None,
        *,
        force: bool = False,
    ) -> None:
        if self._tray_hide_settling or self._native_hover_restore_pending:
            hit = None
        if hit not in {HTMINBUTTON, HTMAXBUTTON, HTCLOSE}:
            hit = None
        if hit == self._native_control_pressed and not force:
            return
        self._native_control_pressed = hit
        self._project_native_control_state()

    def _reset_native_control_state(self, *, force: bool = False) -> None:
        changed = (
            self._native_control_hover is not None
            or self._native_control_pressed is not None
        )
        self._native_control_hover = None
        self._native_control_pressed = None
        if changed or force:
            self._project_native_control_state()

    def _handle_native_control_move(self, hit: int | None) -> None:
        self._set_native_control_hover(hit)

    def _handle_native_control_leave(self) -> None:
        self._set_native_control_hover(None)

    def _handle_native_control_press(self, hit: int | None) -> None:
        self._set_native_control_pressed(hit)

    def _handle_native_control_release(self, hit: int | None) -> None:
        pressed = self._native_control_pressed
        self._set_native_control_pressed(None)
        if pressed is not None and pressed == hit:
            self._perform_native_window_control(pressed)

    def _handle_native_control_deactivated(self) -> None:
        self._reset_native_control_state(force=True)

    def _native_control_hit_at_cursor(self, hwnd: int) -> int | None:
        """Resolve hover from the current physical cursor, never message history."""

        if self.standard_window_frame and self.isMaximized():
            outer = native_window_rect(int(hwnd))
            if outer is not None:
                border_x, border_y = native_resize_border(int(hwnd))
                return native_window_control_hit_at_cursor(
                    int(hwnd),
                    client_rect=standard_window_frame_client_rect(
                        outer,
                        maximized=True,
                        border_x=border_x,
                        border_y=border_y,
                    ),
                )
        return native_window_control_hit_at_cursor(int(hwnd))

    def _complete_tray_hide_presentation_with_native_curtain(self) -> bool:
        """让当前托盘结算接受已经安装的原生安全幕布。"""

        accept = self._tray_hide_presentation_acceptor
        if accept is None:
            return False
        self._tray_hide_presentation_acceptor = None
        accept()
        return True

    def _settle_tray_hide_presentation(self) -> bool:
        """Wait for two renderer frames with neutral native titlebar paint."""

        if getattr(self, "product_titlebar", None) is not None:
            self.product_titlebar.repaint()
            app = QApplication.instance()
            if app is not None:
                app.sync()
            return True
        if (
            not self.ready
            or self.renderer_lifecycle.state
            is not RendererLifecycleState.ACTIVE
            or not self.view.isVisible()
        ):
            return True

        self._tray_hide_presentation_generation += 1
        generation = self._tray_hide_presentation_generation
        source = _ARM_TRAY_HIDE_PRESENTATION.replace(
            "__PDM_GENERATION__",
            str(generation),
        )
        loop = QEventLoop()
        deadline = QTimer()
        deadline.setSingleShot(True)
        completed = False
        accepted = False

        def finish(result: bool) -> None:
            nonlocal completed, accepted
            if completed:
                return
            completed = True
            accepted = result
            loop.quit()

        def probe() -> None:
            if completed:
                return
            self.web.page.runJavaScript(
                "window.__pdmNativeTrayHidePresentationReady || 0",
                on_probe,
            )

        def on_probe(value: object) -> None:
            if completed:
                return
            if value == generation:
                self._tray_hide_presentation_confirmed_generation = generation
                finish(True)
                return
            if value == -generation:
                finish(False)
                return
            QTimer.singleShot(10, probe)

        def on_armed(value: object) -> None:
            if completed:
                return
            if value != generation:
                finish(False)
                return
            probe()

        def accept_native_curtain() -> None:
            finish(True)

        deadline.timeout.connect(lambda: finish(False))
        deadline.start(2_000)
        self._tray_hide_presentation_acceptor = accept_native_curtain
        try:
            self.web.page.runJavaScript(source, on_armed)
            loop.exec()
        except Exception:
            finish(False)
        finally:
            if (
                self._tray_hide_presentation_acceptor
                is accept_native_curtain
            ):
                self._tray_hide_presentation_acceptor = None
            deadline.stop()
            deadline.deleteLater()
        if accepted:
            app = QApplication.instance()
            if app is not None:
                app.sync()
        return accepted

    def _sync_maximize_control(self) -> None:
        """把原生窗口状态投影到所有当前标题栏表面。"""

        maximized = (
            self.isMaximized()
            or self._minimized_restore_maximized
        )
        if getattr(self, "product_titlebar", None) is not None:
            self.product_titlebar.set_maximized(maximized)
        elif not getattr(self, "_exit_cleanup_started", False):
            source = _SYNC_MAXIMIZE_CONTROL.replace(
                "__PDM_MAXIMIZED__",
                "true" if maximized else "false",
            )
            self.web.page.runJavaScript(source)
        if hasattr(self, "renderer_curtain"):
            self.renderer_curtain.set_maximized(maximized)

    def _toggle_maximize(self) -> None:
        if self.isMaximized():
            self.showNormal()
        else:
            self._remember_native_normal_rect()
            self._maximized_from_tray = False
            self.showMaximized()

    def showNormal(self) -> None:  # noqa: N802
        """Return a native-maximized window directly to its saved bounds."""

        if self.standard_window_frame:
            self._maximized_from_tray = False
            super().showNormal()
            return
        restore_native = sys.platform == "win32" and (
            self._maximized_from_tray or self.isMaximized()
        )
        self._maximized_from_tray = False
        if restore_native and show_native_normal_window(
            int(self.winId()),
            normal_rect=self._native_normal_rect,
        ):
            return
        super().showNormal()

    @property
    def close_to_tray(self) -> bool:
        return self._close_to_tray

    @property
    def standard_window_frame(self) -> bool:
        return bool(getattr(self, "_standard_window_frame", False))

    @property
    def exit_cleanup_complete(self) -> bool:
        return self._exit_cleanup_complete

    @property
    def exit_teardown_attempted(self) -> tuple[str, ...]:
        """Return fixed opaque H06 surface steps attempted in this process."""

        return tuple(self._exit_teardown_attempted)

    @property
    def exit_teardown_failures(self) -> tuple[str, ...]:
        """Return fixed opaque H06 surface steps that raised or failed."""

        return tuple(self._exit_teardown_failures)

    @property
    def cleanup_result(self) -> CleanupResult | None:
        return self._last_cleanup_result

    def set_close_to_tray(self, enabled: bool) -> None:
        """Apply the future settings value without reading user config here."""

        self._close_to_tray = bool(enabled)

    def set_native_language(self, language: str) -> None:
        """Project one bounded language into native-only lifecycle surfaces."""

        if type(language) is not str:
            raise ValueError("native language must be zh or en")
        normalized = language.strip().lower()
        if normalized not in _TRAY_FAILURE_TEXT:
            raise ValueError("native language must be zh or en")
        self._native_language = normalized
        self.setWindowTitle("小仓" if normalized == "zh" else "Cangoo")
        if getattr(self, "product_titlebar", None) is not None:
            self.product_titlebar.set_language(normalized)
        if self.tray is not None:
            self.tray.set_language(normalized)

    def set_native_effective_theme(self, effective_theme: str) -> None:
        """Project one validated effective theme into native product chrome."""

        if effective_theme not in {"LIGHT", "DARK"}:
            raise ValueError("native effective theme must be LIGHT or DARK")
        if getattr(self, "product_titlebar", None) is not None:
            self.product_titlebar.set_effective_theme(effective_theme)

    def set_tray_state(self, state: TraySessionState | str) -> None:
        """Update the native status surface without exposing session data."""

        if self.tray is not None:
            try:
                self.tray.set_state(state)
            except Exception:
                # 托盘状态只是可恢复性投影，不能跳过或回滚已经完成的安全
                # 边界。
                pass

    def hide_to_tray(self) -> bool:
        """Hide without destroying the WebEngine page or native session."""
        if getattr(self, "_exit_cleanup_started", False):
            return False

        if self._tray_hide_settling:
            return False
        self._tray_focus_restore_token = 0
        self._tray_hide_settling = True
        try:
            self.web.page.runJavaScript(_CAPTURE_TRAY_FOCUS)
        except Exception:
            # Focus preservation is best effort.  Renderer failure must still
            # converge through the native TO_TRAY/D18 decision.
            pass
        try:
            try:
                recoverable = (
                    self.tray is not None
                    and self.tray.ensure_recoverable_entry()
                )
            except Exception:
                recoverable = False
            if not recoverable:
                return False
            self._tray_restore_maximized = self.isMaximized()
            remembered = (
                self.normalGeometry()
                if self.isMaximized()
                else self.geometry()
            )
            self._tray_restore_geometry = QRect(remembered)
            self.chrome_input.reset()
            self._reset_native_control_state(force=True)
            if not self._settle_tray_hide_presentation():
                return False
            try:
                # 结算可能处理原生事件；真正隐藏前再次确认系统登记仍在。
                if not self.tray.ensure_recoverable_entry():
                    return False
                self.hide()
            except Exception:
                return False
            try:
                hidden_with_entry = (
                    not self.isVisible()
                    and self.tray is not None
                    and self.tray.ensure_recoverable_entry()
                )
            except Exception:
                hidden_with_entry = False
            if not hidden_with_entry:
                return False
            try:
                if (
                    self._tray_restore_maximized
                    and not self.standard_window_frame
                ):
                    self.setWindowState(Qt.WindowState.WindowNoState)
                    if self._tray_restore_geometry.isValid():
                        self.setGeometry(self._tray_restore_geometry)
                self._tray_hidden = True
                self.hidden_to_tray.emit()
                return True
            except Exception:
                self._tray_hidden = False
                return False
        finally:
            self._tray_hide_settling = False
            if self._exit_after_tray_hide_settle:
                self._exit_after_tray_hide_settle = False
                QTimer.singleShot(0, self.close)

    def restore_from_tray(self) -> None:
        if getattr(self, "_exit_cleanup_started", False):
            return None
        """Restore the prior normal/maximized state and the focused DOM field."""

        if self.isVisible() and not self.isMinimized():
            self.raise_()
            self.activateWindow()
            self._schedule_canvas_focus_restore()
            return

        self._native_hover_restore_pending = True
        # A hidden HWND can leave renderer state out of step with our native
        # bookkeeping, so always project one final neutral state before show.
        self._reset_native_control_state(force=True)
        if self.standard_window_frame:
            if self._tray_hidden:
                self.show()
                self._register_standard_surface_refresh(
                    reproject_hover=True
                )
            elif self._minimized_restore_maximized:
                self.showMaximized()
            else:
                QMainWindow.showNormal(self)
            self._maximized_from_tray = False
        elif self._tray_hidden and self._tray_restore_maximized:
            self._maximized_from_tray = True
            restored = show_native_maximized_window(
                int(self.winId()),
                normal_rect=self._native_normal_rect,
            )
            if not restored or not self.isVisible():
                # Synchronize Qt/WebEngine's logical visibility only after
                # the HWND is already maximized, so no normal frame appears.
                self.showMaximized()
        else:
            self._maximized_from_tray = False
            self.showNormal()
            if self._tray_hidden and self._tray_restore_geometry.isValid():
                self.setGeometry(self._tray_restore_geometry)
        self._tray_hidden = False
        self.raise_()
        self.activateWindow()
        self._schedule_canvas_focus_restore()
        self.restored_from_tray.emit()

    def _restore_after_failed_tray_close(
        self,
        *,
        was_maximized: bool,
        normal_geometry: QRect,
    ) -> None:
        """Keep the original top-level recoverable before the D18 choice."""

        self._tray_hidden = False
        if self.standard_window_frame:
            if not self.isVisible():
                self.show()
                self._register_standard_surface_refresh(
                    reproject_hover=True
                )
            elif self.isMinimized():
                if self._minimized_restore_maximized:
                    self.showMaximized()
                else:
                    QMainWindow.showNormal(self)
        elif was_maximized:
            # Keep the visible HWND in its existing maximized placement.
            # Calling setGeometry(normalGeometry()) here can disturb the
            # native maximized frame before D18 is shown and leave Qt's
            # maximize state out of step with the painted titlebar control.
            if not self.isVisible() or not self.isMaximized():
                restored = show_native_maximized_window(
                    int(self.winId()),
                    normal_rect=self._native_normal_rect,
                )
                if not restored or not self.isVisible():
                    self.showMaximized()
        else:
            if self.isMaximized() or self.isMinimized():
                self.showNormal()
            elif not self.isVisible():
                self.show()
            if normal_geometry.isValid():
                self.setGeometry(normal_geometry)
        self.raise_()
        self.activateWindow()
        self._sync_corner_preference()
        self._sync_maximize_control()
        app = QApplication.instance()
        if app is not None:
            app.sync()

    def _confirm_exit_after_tray_failure(self) -> bool:
        """Return true only for an explicit D18 replacement-exit choice."""

        callback = self._tray_failure_confirmation
        if callback is not None:
            try:
                return callback(self._native_language) is True
            except Exception:
                return False

        existing = self._tray_failure_dialog
        if existing is not None:
            existing.raise_()
            existing.activateWindow()
            return False

        dialog: QMessageBox | None = None
        focus_visibility: NativeFocusVisibilityController | None = None
        try:
            labels = _TRAY_FAILURE_TEXT[self._native_language]
            dialog = QMessageBox(self)
            dialog.setObjectName("pdmTrayUnavailableDialog")
            dialog.setIcon(QMessageBox.Icon.Warning)
            dialog.setWindowTitle(labels["title"])
            dialog.setText(labels["message"])
            dialog.setWindowModality(Qt.WindowModality.WindowModal)
            exit_button = dialog.addButton(
                labels["exit"],
                QMessageBox.ButtonRole.DestructiveRole,
            )
            cancel_button = dialog.addButton(
                labels["cancel"],
                QMessageBox.ButtonRole.RejectRole,
            )
            dialog.setDefaultButton(cancel_button)
            dialog.setEscapeButton(cancel_button)
            exit_button.setAutoDefault(False)
            exit_button.setDefault(False)
            cancel_button.setAutoDefault(True)
            cancel_button.setDefault(True)
            dialog.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
            effective_theme = self.renderer_curtain.effective_theme
            focus_accent = (
                "#8b5cf6"
                if effective_theme == "LIGHT"
                else "#6366f1"
            )
            dialog.setStyleSheet(
                "QPushButton[pdmFocusFrameReady=\"false\"]:focus{"
                f"border:2px solid {focus_accent};}}"
            )
            try:
                focus_visibility = NativeFocusVisibilityController(
                    dialog,
                    lambda: (cancel_button, exit_button),
                    effective_theme=effective_theme,
                    safe_anchor=dialog,
                    default_action=cancel_button.click,
                    parent=dialog,
                )
            except Exception:
                focus_visibility = None
                install_managed_focus_fallback(
                    cancel_button,
                    radius=4,
                )
                install_managed_focus_fallback(
                    exit_button,
                    radius=4,
                )
            alt_f4 = QShortcut(QKeySequence("Alt+F4"), dialog)
            alt_f4.setContext(Qt.ShortcutContext.WindowShortcut)
            alt_f4.activated.connect(dialog.reject)
            self._tray_failure_dialog = dialog
            dialog.show()
            if focus_visibility is not None:
                focus_visibility.focus_safe_anchor(
                    Qt.FocusReason.OtherFocusReason
                )
            else:
                cancel_button.setFocus(Qt.FocusReason.OtherFocusReason)
            dialog.exec()
            return (
                self._allow_exit
                or dialog.clickedButton() is exit_button
            )
        except Exception:
            return False
        finally:
            self._tray_failure_dialog = None
            if focus_visibility is not None:
                focus_visibility.dispose()
            if dialog is not None:
                dialog.deleteLater()

    def _settle_close_behavior_before_close(self) -> bool:
        """Extension hook for a candidate's ordered settings authority."""

        return True

    def _prepare_for_true_exit(self) -> None:
        """Extension hook invoked only after native close authorizes H06."""

        HostWindow._cancel_standard_scene_refresh(self)
        HostWindow._clear_renderer_presentation_frame_gate(self)

    def _schedule_canvas_focus_restore(self) -> None:
        generation = self._renderer_page_generation
        self._tray_focus_restore_serial = (
            getattr(self, "_tray_focus_restore_serial", 0) + 1
        )
        token = self._tray_focus_restore_serial
        self._tray_focus_restore_token = token
        QTimer.singleShot(
            0,
            lambda generation=generation, token=token:
            self._restore_canvas_focus(generation, token),
        )
        QTimer.singleShot(
            50,
            lambda generation=generation, token=token:
            self._restore_canvas_focus(generation, token),
        )

    def _restore_canvas_focus(self, generation: int, token: int) -> None:
        if generation != self._renderer_page_generation:
            return
        if token != getattr(self, "_tray_focus_restore_token", 0):
            return
        if not self.isVisible():
            return
        if self.renderer_curtain.isVisible():
            self.renderer_curtain.focus_primary_action(
                Qt.FocusReason.ActiveWindowFocusReason
            )
            if QApplication.focusWidget() is self.renderer_curtain:
                self._tray_focus_restore_token = 0
            return
        try:
            self.view.setFocus(Qt.FocusReason.ActiveWindowFocusReason)
            self.web.page.runJavaScript(_RESTORE_TRAY_FOCUS)
        except Exception:
            pass

    def _attempt_exit_teardown(
        self,
        name: str,
        action: Callable[[], object],
        *,
        require_true: bool = False,
    ) -> object | None:
        """Attempt one fixed H06 surface step and continue after failure."""

        self._exit_teardown_attempted.append(name)
        try:
            result = action()
        except Exception:
            self._exit_teardown_failures.append(name)
            return None
        if require_true and result is not True:
            self._exit_teardown_failures.append(name)
        return result

    def _remove_chrome_filter_for_exit(self) -> None:
        app = QApplication.instance()
        if self._chrome_filter_installed and app is not None:
            app.removeEventFilter(self.chrome_input)
            self._chrome_filter_installed = False

    def _reset_chrome_for_exit(self) -> None:
        self.chrome_input.reset()
        self._reset_native_control_state(force=True)

    def _teardown_qwindow_bindings(self) -> None:
        HostWindow._cancel_standard_scene_refresh(self)
        self._clear_standard_surface_refresh()
        bound = self._standard_surface_refresh_bound_handle
        if bound is not None and isValid(bound):
            bound.removeEventFilter(self)
        self._standard_surface_refresh_bound_handle = None
        screen_bound = self._window_screen_change_bound_handle
        if screen_bound is not None and isValid(screen_bound):
            screen_bound.screenChanged.disconnect(
                self._on_window_screen_changed
            )
        self._window_screen_change_bound_handle = None

    def enter_native_security_boundary(
        self,
        reason: SecurityBoundaryReason,
        *,
        page_revoked: bool,
    ) -> SecurityBoundaryResult:
        """Run an already-authorized native boundary with one serial owner.

        M3 has no attached Bridge, so page/session epochs are zero.  M4 must
        replace this zero-epoch helper with the composite typed-Bridge path;
        it may not use this method to bypass request-authority revocation.
        """

        if not isinstance(reason, SecurityBoundaryReason):
            raise TypeError("native boundary reason must be a fixed enum")
        if self.renderer_lifecycle.state is not RendererLifecycleState.ACTIVE:
            raise RuntimeError(
                "native boundary requires one active candidate page"
            )
        authority_serial = (
            self.renderer_lifecycle.reserve_boundary_serial()
        )
        result = self.security.enter_boundary(
            reason.value,
            authority_serial=authority_serial,
            page_epoch=0,
            session_epoch=0,
            page_revoked=page_revoked,
        )
        self._show_renderer_curtain(
            (
                RendererRecoveryViewState.LOCKED
                if result.complete
                else RendererRecoveryViewState.BLOCKED
            )
        )
        return result

    def request_exit(self) -> None:
        """Take the explicit synchronous-exit path even when currently hidden."""
        if getattr(self, "_exit_clipboard_state", ""):
            self._present_exit_clipboard_surface()
            return

        HostWindow._cancel_standard_scene_refresh(self)
        HostWindow._clear_renderer_presentation_frame_gate(self)
        self._allow_exit = True
        if self._tray_hide_settling:
            self._exit_after_tray_hide_settle = True
            return
        dialog = self._tray_failure_dialog
        if dialog is not None:
            try:
                dialog.reject()
            except Exception:
                pass
            return
        self.close()

    @property
    def resume_health_ok(self) -> bool:
        return self._resume_health_ok

    def _on_power_suspending(self, count: int) -> None:
        """Remember public window/focus state before Windows suspends."""

        self._power_focus_restore_token = 0
        self._power_was_visible = self.isVisible()
        self._power_was_active = self.isActiveWindow()
        self._resume_health_ok = False
        if self.ready:
            self.web.page.runJavaScript(_CAPTURE_POWER_FOCUS)
        self.power_suspending.emit(count)

    def _on_session_locked(self) -> None:
        self.session_locked.emit()

    def _on_session_lock_availability_changed(self, available: bool) -> None:
        self.session_lock_availability_changed.emit(available)

    def _sync_session_lock_registration(self) -> bool:
        lifecycle = getattr(self, "session_lock", None)
        if lifecycle is None:
            return False
        hwnd = int(self.internalWinId())
        if not hwnd or getattr(self, "_exit_cleanup_started", False):
            return lifecycle.unregister_window()
        return lifecycle.register_window(hwnd)

    def _sync_clipboard_window_handle(self) -> None:
        """复用当前原生句柄；首次创建前或销毁后禁用复制，不创建额外窗口。"""
        native = getattr(self, "native", None)
        clipboard = getattr(native, "clipboard", None)
        if clipboard is not None:
            hwnd = 0 if getattr(self, "_exit_cleanup_started", False) else int(self.internalWinId())
            clipboard.bind_window_handle(hwnd)

    def _on_power_registration_failed(self) -> None:
        """产品扩展层在有效窗口失去电源保护时同步停止秘密能力。"""

    def _on_power_registration_lost(self) -> None:
        """在旧订阅解绑前同步撤销不再有电源保护的秘密权限。"""

    def _on_power_registration_available(self) -> None:
        """新句柄订阅成功后，由产品扩展层完成已有锁定呈现。"""

    def _sync_power_registration(self) -> bool:
        lifecycle = getattr(self, "power", None)
        if lifecycle is None:
            return False
        if getattr(self, "_exit_cleanup_started", False):
            return lifecycle.unregister_window()
        hwnd = int(self.internalWinId())
        if lifecycle.registration_active and not lifecycle.is_registered_for(hwnd):
            self._on_power_registration_lost()
            # 清理中的原生呈现可能重建句柄，不能随后注销新建立的订阅。
            hwnd = int(self.internalWinId())
        if not hwnd:
            lifecycle.unregister_window()
            return False
        available = lifecycle.register_window(hwnd)
        if available:
            self._on_power_registration_available()
        else:
            self._on_power_registration_failed()
        return available

    def _on_power_resumed(self, event_name: str, count: int) -> None:
        """Refresh native chrome and verify the existing renderer after wake."""

        self._sync_corner_preference()
        self._sync_maximize_control()
        for delay in (0, 250, 1000):
            QTimer.singleShot(delay, self._probe_resume_health)
        if (
            self._power_was_visible
            and self._power_was_active
            and self.isVisible()
        ):
            generation = self._renderer_page_generation
            self._power_focus_restore_serial = (
                getattr(self, "_power_focus_restore_serial", 0) + 1
            )
            token = self._power_focus_restore_serial
            self._power_focus_restore_token = token
            QTimer.singleShot(
                250,
                lambda generation=generation, token=token:
                self._restore_power_focus(generation, token),
            )
            QTimer.singleShot(
                1000,
                lambda generation=generation, token=token:
                self._restore_power_focus(generation, token),
            )
        self.power_resumed.emit(event_name, count)

    def _restore_power_focus(self, generation: int, token: int) -> None:
        if generation != self._renderer_page_generation:
            return
        if token != getattr(self, "_power_focus_restore_token", 0):
            return
        if not self.isVisible():
            return
        if self.renderer_curtain.isVisible():
            self.renderer_curtain.focus_primary_action(
                Qt.FocusReason.ActiveWindowFocusReason
            )
            if QApplication.focusWidget() is self.renderer_curtain:
                self._power_focus_restore_token = 0
            return
        self.view.setFocus(Qt.FocusReason.ActiveWindowFocusReason)
        self.web.page.runJavaScript(_RESTORE_POWER_FOCUS)

    def _probe_resume_health(self) -> None:
        if not self.ready:
            self._resume_health_ok = False
            self.resume_health_checked.emit(False)
            return
        self.web.page.runJavaScript(
            _PROBE_RESUME_HEALTH,
            lambda healthy, generation=self._renderer_page_generation:
            self._on_resume_health_probe(generation, healthy),
        )

    def _on_resume_health_probe(
        self,
        generation: int,
        healthy: bool,
    ) -> None:
        if generation != self._renderer_page_generation:
            return
        self._resume_health_ok = bool(healthy)
        self.resume_health_checked.emit(self._resume_health_ok)
        if (
            not self._resume_health_ok
            and self.renderer_lifecycle.state
            is RendererLifecycleState.ACTIVE
        ):
            page_epoch, session_epoch = self._renderer_security_epochs()
            transition = self.renderer_lifecycle.handle_resume_timeout(
                self._renderer_page_generation,
                page_epoch=page_epoch,
                session_epoch=session_epoch,
            )
            if transition.recovery_allowed:
                self._show_renderer_curtain(
                    RendererRecoveryViewState.RECOVERY_AVAILABLE
                )
            else:
                self._show_renderer_curtain(
                    RendererRecoveryViewState.BLOCKED
                )

    @property
    def taskbar_restore_count(self) -> int:
        return self._taskbar_restore_count

    @property
    def renderer_presentation_confirmed_generation(self) -> int:
        return self._renderer_presentation_confirmed_generation

    @property
    def renderer_presentation_probe_attempts(self) -> int:
        return self._renderer_presentation_probe_attempts

    @property
    def renderer_surface_refresh_count(self) -> int:
        return self._renderer_surface_refresh_count

    @property
    def dpi_geometry_fit_count(self) -> int:
        return self._dpi_geometry_fit_count

    @property
    def dpi_maximized_settlement_count(self) -> int:
        return self._dpi_maximized_settlement_count

    @property
    def dpi_surface_refresh_count(self) -> int:
        return self._dpi_surface_refresh_count

    @property
    def last_dpi_geometry_fit(self) -> tuple[QRect, QRect]:
        return (
            QRect(self._last_dpi_fit_before),
            QRect(self._last_dpi_fit_after),
        )

    def _request_web_surface_frame_now(self) -> None:
        if (
            not self.isVisible()
            or self.isMinimized()
            or self.renderer_curtain.isVisible()
        ):
            return
        request_surface_frame(self.web.page, self.view, self.windowHandle)

    def _request_web_surface_frame(self, generation: int) -> None:
        if generation != self._renderer_restore_generation:
            return
        self._request_web_surface_frame_now()

    def _nudge_web_surface(self) -> bool:
        if not self.isVisible() or self.isMinimized():
            return False
        original_size = self.view.size()
        if original_size.width() <= 1 or original_size.height() <= 1:
            return False

        nudged_size = QSize(original_size.width() - 1, original_size.height())
        self.view.resize(nudged_size)
        self.view.resize(original_size)
        self._renderer_surface_refresh_count += 1
        self._request_web_surface_frame_now()
        return True

    def _refresh_web_surface_after_taskbar_restore(
        self,
        generation: int,
    ) -> None:
        """Recreate the child surface without moving the top-level window."""

        if (
            generation != self._renderer_restore_generation
            or not self.isVisible()
            or self.isMinimized()
        ):
            return

        # A live switch to fractional Windows DPI can leave Chromium's child
        # surface black after taskbar restore even though the page remains
        # healthy. A same-cycle one-pixel child resize rebuilds that surface
        # while preserving the outer window geometry and the loaded page.
        if self._nudge_web_surface():
            self.restored_from_taskbar.emit(self._taskbar_restore_count)

    def _schedule_taskbar_restore_surface_refresh(self) -> None:
        if self.standard_window_frame:
            self._taskbar_restore_count += 1
            self._renderer_restore_generation += 1
            self._register_standard_surface_refresh(reproject_hover=True)
            self.restored_from_taskbar.emit(self._taskbar_restore_count)
            return
        self._taskbar_restore_count += 1
        self._renderer_restore_generation += 1
        generation = self._renderer_restore_generation
        QTimer.singleShot(
            0,
            lambda: self._request_web_surface_frame(generation),
        )
        QTimer.singleShot(
            80,
            lambda: self._refresh_web_surface_after_taskbar_restore(
                generation
            ),
        )
        QTimer.singleShot(
            250,
            lambda: self._request_web_surface_frame(generation),
        )

    def _bind_geometry_screen(self) -> None:
        handle = self._current_qwindow_handle()
        screen = handle.screen() if handle is not None else None
        if screen is self._geometry_screen:
            return
        if self._geometry_screen is not None:
            try:
                self._geometry_screen.availableGeometryChanged.disconnect(
                    self._on_available_geometry_changed
                )
            except (RuntimeError, TypeError):
                pass
        self._geometry_screen = screen
        if screen is not None:
            screen.availableGeometryChanged.connect(
                self._on_available_geometry_changed
            )

    def _on_window_screen_changed(self, _screen) -> None:
        self._bind_geometry_screen()
        self._schedule_dpi_geometry_fit(refresh_surface=True)

    def _on_available_geometry_changed(self, _geometry: QRect) -> None:
        self._schedule_dpi_geometry_fit(refresh_surface=True)

    def _schedule_dpi_geometry_fit(
        self,
        *,
        refresh_surface: bool = False,
    ) -> None:
        """Apply one DPI/work-area transition without delayed compensation.

        Qt dispatches ``screenChanged``, ``availableGeometryChanged`` and
        ``DevicePixelRatioChange`` after updating the corresponding native
        state.  Applying the work-area constraint in that event turn keeps
        Windows/Qt as the only geometry authority.  A frame request is enough
        for WebEngine; resizing the child by one pixel or revisiting the
        geometry on timers would expose a second, visible correction.
        """

        if not hasattr(self, "_dpi_fit_generation"):
            return
        self._dpi_fit_generation += 1
        generation = self._dpi_fit_generation
        self._settle_dpi_window_geometry(generation)
        if refresh_surface:
            can_refresh = bool(
                self.isVisible()
                and not self.isMinimized()
                and not self.renderer_curtain.isVisible()
            )
            if self.standard_window_frame:
                self._register_standard_surface_refresh()
            else:
                self._request_web_surface_frame_now()
            if can_refresh:
                self._dpi_surface_refresh_count += 1

    def _settle_dpi_window_geometry(
        self,
        generation: int | None = None,
    ) -> bool:
        """Settle one DPI transition without exposing an intermediate state."""

        if (
            generation is not None
            and generation != self._dpi_fit_generation
        ):
            return False
        if not self.isVisible() or self.isMinimized():
            return False
        if not self.isMaximized():
            self._dpi_maximized_settlement_signature = None
            return self._fit_normal_geometry_to_screen(generation)
        if sys.platform != "win32":
            return False

        self._bind_geometry_screen()
        screen = self._geometry_screen
        if screen is None:
            return False
        available = screen.availableGeometry()
        signature = (
            str(screen.name()),
            round(float(self.devicePixelRatioF()) * 1000),
            available.x(),
            available.y(),
            available.width(),
            available.height(),
        )
        if signature == self._dpi_maximized_settlement_signature:
            return True
        if self.standard_window_frame:
            self._dpi_maximized_settlement_signature = signature
            return True

        settled = show_native_maximized_window(
            int(self.winId()),
            normal_rect=self._native_normal_rect,
        )
        if not settled:
            super().showMaximized()
            settled = self.isMaximized()
        if settled:
            self._dpi_maximized_settlement_signature = signature
            self._dpi_maximized_settlement_count += 1
        return settled

    def _fit_normal_geometry_to_screen(
        self,
        generation: int | None = None,
    ) -> bool:
        """Keep a normal window inside the new DPI-dependent work area."""

        if (
            generation is not None
            and generation != self._dpi_fit_generation
        ):
            return False
        if self.standard_window_frame and generation is None:
            return False
        if not self.isVisible() or self.isMinimized() or self.isMaximized():
            return False
        self._bind_geometry_screen()
        screen = self._geometry_screen
        if screen is None:
            return False

        before = self.geometry()
        after = fit_window_rect(
            before,
            screen.availableGeometry(),
            self.minimumSize(),
        )
        if after == before:
            return False
        self._last_dpi_fit_before = QRect(before)
        self._last_dpi_fit_after = QRect(after)
        self.setGeometry(after)
        self._dpi_geometry_fit_count += 1
        return True

    def _restore_maximized_for_caption_drag(
        self,
        cursor_pos: QPoint | None = None,
        start_system_move: bool = True,
    ) -> bool:
        """Restore under the cursor only after the system drag threshold."""

        if not self.isMaximized():
            return False

        cursor = cursor_pos or QCursor.pos()
        maximized_rect = self.frameGeometry()
        normal_rect = self.normalGeometry()
        restore_width = max(self.minimumWidth(), normal_rect.width() or 1200)
        restore_height = max(self.minimumHeight(), normal_rect.height() or 800)
        if maximized_rect.width() > 0:
            horizontal_ratio = (
                cursor.x() - maximized_rect.left()
            ) / maximized_rect.width()
        else:
            horizontal_ratio = 0.5
        horizontal_ratio = max(0.0, min(1.0, horizontal_ratio))
        title_offset = max(
            0,
            min(TITLEBAR_HEIGHT - 1, cursor.y() - maximized_rect.top()),
        )
        target = QRect(
            cursor.x() - round(restore_width * horizontal_ratio),
            cursor.y() - title_offset,
            restore_width,
            restore_height,
        )

        self.showNormal()
        self.setGeometry(target)
        if not start_system_move:
            return True
        handle = self.windowHandle()
        return bool(handle and handle.startSystemMove())

    def _remember_native_normal_rect(self) -> None:
        if (
            sys.platform != "win32"
            or not self.isVisible()
            or self.isMinimized()
            or self.isMaximized()
            or self._maximized_from_tray
            or self._minimized_restore_maximized
        ):
            return
        rect = native_window_rect(int(self.winId()))
        if rect is not None:
            self._native_normal_rect = rect

    def moveEvent(self, event: QMoveEvent) -> None:  # noqa: N802
        super().moveEvent(event)
        self._remember_native_normal_rect()

    def resizeEvent(self, event: QResizeEvent) -> None:  # noqa: N802
        super().resizeEvent(event)
        if hasattr(self, "renderer_curtain"):
            self._sync_renderer_curtain_geometry()
        self._remember_native_normal_rect()
        lifecycle = getattr(self, "renderer_lifecycle", None)
        curtain = getattr(self, "renderer_curtain", None)
        if (
            self.standard_window_frame
            and self.isVisible()
            and not self.isMinimized()
            and self.ready
            and lifecycle is not None
            and lifecycle.state is RendererLifecycleState.ACTIVE
            and curtain is not None
            and not curtain.isVisible()
        ):
            self._register_standard_surface_refresh()

    def showEvent(self, event: QShowEvent) -> None:  # noqa: N802
        super().showEvent(event)
        HostWindow._sync_clipboard_window_handle(self)
        if getattr(self, "_exit_cleanup_started", False):
            self._sync_renderer_curtain_geometry()
            return
        if not self._sync_power_registration():
            self._on_power_registration_failed()
        self._sync_session_lock_registration()
        self._remember_native_normal_rect()
        self._sync_window_screen_change_binding()
        if self.standard_window_frame:
            self._sync_standard_surface_refresh_filter()
        self._bind_geometry_screen()
        self._schedule_dpi_geometry_fit()
        self._sync_corner_preference()
        self._sync_maximize_control()

    def event(self, event: QEvent) -> bool:
        if event.type() == QEvent.Type.Hide:
            HostWindow._cancel_standard_scene_refresh(self)
        result = super().event(event)
        if event.type() == QEvent.Type.WinIdChange:
            HostWindow._sync_clipboard_window_handle(self)
            self._sync_power_registration()
            self._sync_session_lock_registration()
        if (
            hasattr(self, "_dpi_fit_generation")
            and event.type()
            in {
                QEvent.Type.DevicePixelRatioChange,
                QEvent.Type.ScreenChangeInternal,
            }
        ):
            self._bind_geometry_screen()
            self._sync_renderer_curtain_geometry()
            self._schedule_dpi_geometry_fit(refresh_surface=True)
        return result

    def eventFilter(self, watched, event: QEvent) -> bool:  # noqa: N802
        if not isValid(watched):
            return False
        if (
            watched is self._standard_surface_refresh_bound_handle
            and event.type() == QEvent.Type.Expose
        ):
            self._queue_standard_surface_refresh(watched)
        return super().eventFilter(watched, event)

    def changeEvent(self, event: QEvent) -> None:  # noqa: N802
        super().changeEvent(event)
        if getattr(self, "_exit_cleanup_started", False):
            self._sync_renderer_curtain_geometry()
            return
        if event.type() == QEvent.Type.WindowStateChange:
            old_state = event.oldState()
            entering_minimized = self.isMinimized()
            if (
                entering_minimized
                and old_state & Qt.WindowState.WindowMaximized
            ):
                self._minimized_restore_maximized = True
            restored_from_minimized = bool(
                old_state & Qt.WindowState.WindowMinimized
            ) and not entering_minimized
            preserve_maximize_control = (
                entering_minimized
                and self._minimized_restore_maximized
            )
            restored_from_maximized = bool(
                old_state & Qt.WindowState.WindowMaximized
            ) and not entering_minimized and not self.isMaximized()
            if hasattr(self, "chrome_input"):
                self.chrome_input.reset()
            self._reset_native_control_state(force=True)
            if not preserve_maximize_control:
                self._sync_corner_preference()
                self._sync_maximize_control()
                QTimer.singleShot(0, self._sync_corner_preference)
                QTimer.singleShot(0, self._sync_maximize_control)
            if restored_from_minimized:
                self._minimized_restore_maximized = False
                self._schedule_taskbar_restore_surface_refresh()
            if restored_from_maximized:
                self._dpi_maximized_settlement_signature = None
                self._fit_normal_geometry_to_screen()
            if entering_minimized:
                HostWindow._cancel_standard_scene_refresh(self)
            elif bool(old_state & Qt.WindowState.WindowMaximized) != self.isMaximized():
                HostWindow._schedule_standard_scene_refresh(self)
        elif (
            event.type() == QEvent.Type.ActivationChange
            and not self.isActiveWindow()
        ):
            self._reset_renderer_curtain_focus_visibility()
            self._handle_native_control_deactivated()

    def _sync_corner_preference(self) -> None:
        if sys.platform != "win32":
            return
        self._corner_preference_applied = set_win11_corner_preference(
            int(self.winId()),
            self.isMaximized(),
        )

    def nativeEvent(self, event_type, message):  # noqa: N802
        """Return native resize/caption hits for the frameless top-level HWND."""

        if (
            sys.platform == "win32"
            and bytes(event_type)
            in {b"windows_generic_MSG", b"windows_dispatcher_MSG"}
        ):
            try:
                from ctypes.wintypes import MSG

                msg = MSG.from_address(int(message))
                session_lock = getattr(self, "session_lock", None)
                if session_lock is not None:
                    if msg.message == WM_WTSSESSION_CHANGE and session_lock.handle_session_change(
                        int(msg.hWnd or 0), int(msg.wParam)
                    ):
                        return True, 0
                    if msg.message == 0x0002 and int(msg.hWnd or 0) == session_lock.registered_hwnd:
                        # WM_DESTROY 时句柄仍有效，必须在实际销毁前注销。
                        session_lock.unregister_window()
                if (
                    msg.message == WM_NCCALCSIZE
                    and self.standard_window_frame
                    and bool(msg.wParam)
                    and int(msg.lParam)
                ):
                    from ctypes import wintypes

                    class NCCALCSIZE_PARAMS(ctypes.Structure):
                        _fields_ = [
                            ("rgrc", wintypes.RECT * 3),
                            ("lppos", ctypes.c_void_p),
                        ]

                    params = NCCALCSIZE_PARAMS.from_address(
                        int(msg.lParam)
                    )
                    source = params.rgrc[0]
                    border_x, border_y = native_resize_border(int(msg.hWnd))
                    left, top, right, bottom = (
                        standard_window_frame_client_rect(
                            (
                                int(source.left),
                                int(source.top),
                                int(source.right),
                                int(source.bottom),
                            ),
                            maximized=native_window_is_maximized(
                                int(msg.hWnd)
                            ),
                            border_x=border_x,
                            border_y=border_y,
                        )
                    )
                    source.left = left
                    source.top = top
                    source.right = right
                    source.bottom = bottom
                    return True, 0
                if msg.message == WM_NCHITTEST:
                    outer = native_window_rect(int(msg.hWnd))
                    if outer is not None:
                        x = ctypes.c_short(msg.lParam & 0xFFFF).value
                        y = ctypes.c_short((msg.lParam >> 16) & 0xFFFF).value
                        scale = native_dpi_scale(int(msg.hWnd))
                        maximized = self.isMaximized()
                        (
                            chrome_left,
                            chrome_top,
                            chrome_right,
                            chrome_bottom,
                        ) = outer
                        if self.standard_window_frame and maximized:
                            border_x, border_y = native_resize_border(
                                int(msg.hWnd)
                            )
                            (
                                chrome_left,
                                chrome_top,
                                chrome_right,
                                chrome_bottom,
                            ) = standard_window_frame_client_rect(
                                (
                                    chrome_left,
                                    chrome_top,
                                    chrome_right,
                                    chrome_bottom,
                                ),
                                maximized=True,
                                border_x=border_x,
                                border_y=border_y,
                            )
                        control_hit = native_window_control_hit(
                            x,
                            y,
                            chrome_left,
                            chrome_top,
                            chrome_right,
                            scale,
                        )
                        if maximized:
                            if control_hit is not None:
                                return True, control_hit
                            titlebar_bottom = chrome_top + round(
                                TITLEBAR_HEIGHT * scale
                            )
                            controls_width = round(
                                WINDOW_CONTROL_WIDTH
                                * WINDOW_CONTROL_COUNT
                                * scale
                            )
                            if (
                                hasattr(self, "renderer_curtain")
                                and self.renderer_curtain.isVisible()
                                and chrome_top <= y < titlebar_bottom
                                and chrome_left
                                <= x < chrome_right - controls_width
                            ):
                                # 安全表面显示时网页不可接收输入，因此最大化
                                # 拖动和双击必须由原生命中唯一负责。
                                return True, HTCAPTION
                            if self.standard_window_frame and (
                                chrome_top <= y < titlebar_bottom
                                and chrome_left
                                <= x < chrome_right - controls_width
                            ):
                                return True, HTCAPTION
                            return True, HTCLIENT

                        border_x, border_y = native_resize_border(int(msg.hWnd))
                        hit = resize_hit_test(
                            x,
                            y,
                            chrome_left,
                            chrome_top,
                            chrome_right,
                            chrome_bottom,
                            border_x,
                            border_y,
                        )
                        if hit is not None:
                            return True, hit

                        if control_hit is not None:
                            return True, control_hit
                        titlebar_bottom = chrome_top + round(
                            TITLEBAR_HEIGHT * scale
                        )
                        controls_width = round(
                            WINDOW_CONTROL_WIDTH * WINDOW_CONTROL_COUNT * scale
                        )
                        if (
                            chrome_top <= y < titlebar_bottom
                            and chrome_left
                            <= x < chrome_right - controls_width
                        ):
                            return True, HTCAPTION
                if msg.message == WM_NCMOUSEMOVE:
                    if self._native_hover_restore_pending:
                        self._native_hover_restore_pending = False
                    hit = self._native_control_hit_at_cursor(int(msg.hWnd))
                    self._handle_native_control_move(hit)
                    track_non_client_mouse_leave(int(msg.hWnd))
                if msg.message == WM_NCMOUSELEAVE:
                    self._native_hover_restore_pending = False
                    self._handle_native_control_leave()
                    # 继续交给 Qt/Windows 清理 HTMAXBUTTON 的系统 Snap 热态；
                    # 应用侧状态已经在上面同步归零。
                if msg.message in {
                    WM_NCLBUTTONDOWN,
                    WM_NCRBUTTONDOWN,
                    WM_NCMBUTTONDOWN,
                    WM_NCXBUTTONDOWN,
                    WM_NCPOINTERDOWN,
                }:
                    self._reset_web_focus_visibility()
                    self._reset_renderer_curtain_focus_visibility()
                if msg.message == WM_NCLBUTTONDOWN and msg.wParam in {
                    HTMINBUTTON,
                    HTMAXBUTTON,
                    HTCLOSE,
                }:
                    self._handle_native_control_press(int(msg.wParam))
                    return True, 0
                if msg.message == WM_NCLBUTTONUP and (
                    self._native_control_pressed is not None
                    or msg.wParam in {
                        HTMINBUTTON,
                        HTMAXBUTTON,
                        HTCLOSE,
                    }
                ):
                    self._handle_native_control_release(int(msg.wParam))
                    return True, 0
                if msg.message == WM_NCLBUTTONDBLCLK and msg.wParam == HTCAPTION:
                    if not self.standard_window_frame:
                        self._toggle_maximize()
                        return True, 0
                if msg.message == WM_HOTKEY and self.native.handle_hotkey(
                    int(msg.wParam)
                ):
                    return True, 0
                if msg.message == WM_POWERBROADCAST and self.power.handle_broadcast(
                    int(msg.wParam)
                ):
                    return True, 1
            except Exception:
                pass
        return super().nativeEvent(event_type, message)

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        if getattr(self, "_exit_clipboard_state", ""):
            event.ignore()
            self._present_exit_clipboard_surface()
            return
        if self._exit_cleanup_complete:
            event.accept()
            return
        if getattr(self, "_exit_cleanup_started", False):
            event.ignore()
            return

        force_safe_exit = self._full_native_curtain_is_installed()
        if self._tray_hide_settling:
            if force_safe_exit:
                self._allow_exit = True
                self._exit_after_tray_hide_settle = True
            event.ignore()
            return

        # 完整原生安全/失败表面后方没有可安全返回的页面。标题栏、
        # Alt+F4、任务栏和直接关闭事件都必须汇入同步安全退出，不能走
        # 常规的关闭到托盘偏好。
        if force_safe_exit:
            self._allow_exit = True

        if not self._allow_exit:
            try:
                close_behavior_settled = (
                    self._settle_close_behavior_before_close()
                )
            except Exception:
                close_behavior_settled = False
            if not close_behavior_settled:
                event.ignore()
                if not self.isVisible():
                    self.show()
                self.raise_()
                self.activateWindow()
                return

            if self._close_to_tray:
                was_maximized = self.isMaximized()
                normal_geometry = QRect(
                    self.normalGeometry()
                    if was_maximized
                    else self.geometry()
                )
                try:
                    hidden_to_tray = self.hide_to_tray()
                except Exception:
                    hidden_to_tray = False
                if hidden_to_tray:
                    event.ignore()
                    return
                if not self._allow_exit:
                    try:
                        self._restore_after_failed_tray_close(
                            was_maximized=was_maximized,
                            normal_geometry=normal_geometry,
                        )
                    except Exception:
                        try:
                            if was_maximized:
                                self.showMaximized()
                            else:
                                self.showNormal()
                        except Exception:
                            pass
                    if not self._confirm_exit_after_tray_failure():
                        event.ignore()
                        self._schedule_canvas_focus_restore()
                        return
                    self._allow_exit = True

        self._exit_cleanup_started = True
        boundary = False
        try:
            self._attempt_exit_teardown(
                "host.conceal",
                self._prepare_for_true_exit,
            )
            self._attempt_exit_teardown(
                "renderer.begin_exit",
                self.renderer_lifecycle.begin_exit,
            )
            boundary = self._attempt_exit_teardown(
                "security.boundary",
                self._enter_exit_security_boundary,
                require_true=True,
            )
            if boundary is not True:
                self._attempt_exit_teardown(
                    "renderer.blocked_curtain",
                    lambda: self._show_renderer_curtain(
                        RendererRecoveryViewState.BLOCKED
                    ),
                )
            self._attempt_exit_teardown(
                "chrome.filter",
                self._remove_chrome_filter_for_exit,
            )
            self._attempt_exit_teardown(
                "chrome.state",
                self._reset_chrome_for_exit,
            )
            self._attempt_exit_teardown(
                "power.unregister",
                self.power.unregister_window,
                require_true=True,
            )
            self._attempt_exit_teardown(
                "session_lock.unregister",
                self.session_lock.unregister_window,
                require_true=True,
            )
            cleanup = self._attempt_exit_teardown(
                "native.shutdown",
                self.native.shutdown,
            )
            if isinstance(cleanup, CleanupResult):
                self._last_cleanup_result = cleanup
            else:
                self._exit_teardown_failures.append("native.shutdown.result")
            qwindow_teardown = getattr(
                self,
                "_teardown_qwindow_bindings",
                None,
            )
            if callable(qwindow_teardown):
                self._attempt_exit_teardown(
                    "window.handle.bindings",
                    qwindow_teardown,
                )
            self._attempt_exit_teardown(
                "renderer.unbind",
                self._unbind_renderer_page,
            )
            self._attempt_exit_teardown(
                "sensitive_dom.detach",
                self._sensitive_dom.detach,
            )
            self._attempt_exit_teardown(
                "view.stop",
                self.view.stop,
            )
            self._attempt_exit_teardown(
                "page.hide",
                lambda: self.web.page.setVisible(False),
            )
            self._attempt_exit_teardown(
                "page.delete",
                self.web.page.deleteLater,
            )
            self._attempt_exit_teardown(
                "profile.delete",
                self.web.profile.deleteLater,
            )
            if self.tray is not None:
                self._attempt_exit_teardown(
                    "tray.hide",
                    self.tray.hide,
                )
        finally:
            if HostWindow._can_wait_for_clipboard(self, boundary):
                event.ignore()
                self._start_exit_clipboard_retry()
            else:
                self._exit_cleanup_complete = True
                self._attempt_exit_teardown("host.event_accept", event.accept)
                self._attempt_exit_teardown("host.exit_requested", self.exit_requested.emit)

    def _non_clipboard_exit_boundary_complete(self) -> bool:
        result = self.security.last_result
        return bool(result is not None and result.authority_revoked
                    and not (set(result.failed) - {"native.clipboard.force_clear"}))

    def _can_wait_for_clipboard(self, boundary: object) -> bool:
        result = getattr(getattr(self, "security", None), "last_result", None)
        return bool(
            boundary is not True and result is not None
            and result.reason == "exit" and result.authority_revoked
            and set(result.failed) == {"native.clipboard.force_clear"}
            and self._non_clipboard_exit_boundary_complete()
            and not (set(self._exit_teardown_failures) - {"security.boundary"})
        )

    @property
    def exit_clipboard_retry_resolved(self) -> bool:
        """保留首次失败；只认可已验证的剪贴板补偿结果。"""
        return bool(
            self._exit_clipboard_resolved
            and self._non_clipboard_exit_boundary_complete()
            and not (set(self._exit_teardown_failures) - {"security.boundary"})
        )

    def _on_renderer_retry(self) -> None:
        if self._exit_clipboard_state == "blocked":
            self._start_exit_clipboard_retry()
        elif not self._exit_cleanup_started:
            self._begin_renderer_recovery()

    def _start_exit_clipboard_retry(self) -> None:
        if self._exit_clipboard_state == "retrying":
            return
        self._exit_clipboard_state = "retrying"
        self._exit_clipboard_attempts = 0
        HostWindow._show_renderer_curtain(self, RendererRecoveryViewState.CLIPBOARD_EXIT_RETRYING)
        self._present_exit_clipboard_surface()
        self._exit_clipboard_timer.start(100)

    def _present_exit_clipboard_surface(self) -> None:
        if self.isMinimized():
            self.showNormal()
        else:
            self.show()
        self.raise_()
        self.activateWindow()

    def _retry_exit_clipboard(self) -> None:
        if self._exit_clipboard_state != "retrying":
            return
        self._exit_clipboard_attempts += 1
        try:
            cleared = self.native.clipboard.force_clear_if_initialized() is True
        except Exception:
            cleared = False
        if cleared:
            self._exit_clipboard_resolved = True
            self._finish_clipboard_exit()
        elif self._exit_clipboard_attempts < 3:
            self._exit_clipboard_timer.start(100)
        else:
            self._exit_clipboard_state = "blocked"
            HostWindow._show_renderer_curtain(self, RendererRecoveryViewState.CLIPBOARD_EXIT_BLOCKED)

    def _confirm_clipboard_exit(self) -> None:
        if self._exit_clipboard_state == "blocked":
            self._finish_clipboard_exit()

    def _finish_clipboard_exit(self) -> None:
        self._exit_clipboard_timer.stop()
        self._exit_clipboard_state = ""
        # 此标志只表示窗口拆卸完成；安全清理失败事实仍由协调器保存。
        self._exit_cleanup_complete = True
        self._attempt_exit_teardown("host.event_accept", self.close)
        self._attempt_exit_teardown("host.exit_requested", self.exit_requested.emit)

    def _enter_exit_security_boundary(self) -> bool:
        """Run the unattached host's zero-epoch native exit boundary."""

        authority_serial = self.renderer_lifecycle.reserve_boundary_serial()
        result = self.security.enter_boundary(
            "exit",
            authority_serial=authority_serial,
            page_epoch=0,
            session_epoch=0,
            page_revoked=True,
        )
        return (
            result.authority_revoked is True
            and result.complete is True
        )
