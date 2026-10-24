"""唯一正式 WebEngine 产品源码入口。

模块顶层只依赖标准库和不导入 Qt 的原生策略模块，确保所有启动拒绝检查
都发生在 ``QApplication`` 与 Qt WebEngine 初始化之前；冻结器可先加载 QtCore。
"""

# Windows自有代码采用AGPL-3.0-only；适用范围与OpenSSL链接附加许可见仓库根LICENSE.md和OPENSSL_EXCEPTION.md。
from __future__ import annotations

import os
from pathlib import Path
import re
import sys

from desktop.host.diagnostics import (
    STARTUP_REFUSAL_EXIT_CODE,
    StartupBlockReason,
    UnsafeWebEngineConfiguration,
    enforce_webengine_startup_policy,
)
from desktop.host.wer_policy import (
    PolicyApplyStatus,
    apply_windows_error_policy,
)
from desktop.runtime_paths import (
    ProductPathError,
    ProductRuntimePaths,
    RuntimePaths,
)


PRODUCT_RUNTIME_FAILURE_EXIT_CODE = 2
_SAFE_DETAIL_CODE = re.compile(r"[A-Z][A-Z0-9_]{0,63}\Z")
_RENDERING_ENVIRONMENT_KEYS = (
    "QT_QUICK_BACKEND",
    "QMLSCENE_DEVICE",
    "QSG_RHI_BACKEND",
    "QT_OPENGL",
    "QT_WIDGETS_RHI",
    "QT_WIDGETS_RHI_BACKEND",
    "QT_D3D_ADAPTER_INDEX",
    "QSG_RHI_ADAPTER_INDEX",
    "QSG_RHI_PREFER_SOFTWARE_RENDERER",
)


def _webengine_is_preinitialized() -> bool:
    return any(
        name.startswith(("PySide6.QtWebEngine", "PySide6.QtQuick"))
        for name in sys.modules
    )


def _preflight(arguments: list[str]) -> StartupBlockReason | None:
    """在应用及 WebEngine 初始化前完成固定、失败关闭的产品启动检查。"""

    if _webengine_is_preinitialized():
        return StartupBlockReason.PREINITIALIZED_WEBENGINE
    try:
        enforce_webengine_startup_policy(
            argv=("desktop.product_app", *arguments)
        )
    except UnsafeWebEngineConfiguration:
        return StartupBlockReason.UNSAFE_CONFIGURATION
    if arguments:
        return StartupBlockReason.UNSUPPORTED_ARGUMENT
    error_policy = apply_windows_error_policy()
    if error_policy.status is not PolicyApplyStatus.APPLIED:
        return StartupBlockReason.WINDOWS_ERROR_POLICY
    if _installation_recovery_pending():
        return StartupBlockReason.INSTALLATION_INCOMPLETE
    if any(os.environ.get(key) for key in _RENDERING_ENVIRONMENT_KEYS):
        return StartupBlockReason.UNSAFE_CONFIGURATION
    return None


def _application_directory() -> Path:
    """区分程序所在目录与冻结包内部只读资源目录。"""

    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def _installation_recovery_pending() -> bool:
    """未完成安装时不初始化业务；已提交的清理残留不拦启动。"""
    if not getattr(sys, "frozen", False):
        return False
    recovery = _application_directory() / ".cangoo-recovery"
    if not os.path.lexists(recovery):
        return False
    try:
        if recovery.lstat().st_file_attributes & 0x400:
            return True
        state = recovery / "state"
        if state.lstat().st_file_attributes & 0x400:
            return True
        with state.open("rb") as handle:
            return handle.read(128) not in {
                b"CANGOO-RECOVERY-1\nCOMMITTED\n",
                b"CANGOO-RECOVERY-1\nRECOVERED\n",
            }
    except (OSError, AttributeError):
        return True


def _create_application():
    """注册固定资源协议后才创建 ``QApplication``。"""

    from desktop.host.web_profile import register_app_scheme

    register_app_scheme()

    from PySide6.QtWidgets import QApplication
    from desktop.host.resources import application_icon

    existing = QApplication.instance()
    if existing is not None and not isinstance(existing, QApplication):
        raise RuntimeError("product entry requires QApplication")
    application = existing or QApplication(sys.argv[:1])
    application.setApplicationName("Cangoo")
    application.setWindowIcon(application_icon())
    application.setQuitOnLastWindowClosed(False)
    return application


def _configure_product_rendering() -> None:
    """统一原生控件与网页的绘制接口，显卡由 Qt/Windows 默认选择。"""

    for key in (
        "QT_QUICK_BACKEND", "QT_D3D_ADAPTER_INDEX",
        "QSG_RHI_ADAPTER_INDEX", "QSG_RHI_PREFER_SOFTWARE_RENDERER",
    ):
        os.environ.pop(key, None)
    os.environ["QSG_RHI_BACKEND"] = "d3d11"
    os.environ["QT_WIDGETS_RHI"] = "1"
    os.environ["QT_WIDGETS_RHI_BACKEND"] = "d3d11"


def _create_product_window(paths: RuntimePaths, *, update_client_factory=None):
    from desktop.m4.window import M4HostWindow

    return M4HostWindow(paths, standard_window_frame=True, startup_update_check=True,
                        update_client_factory=update_client_factory)


def _ensure_terms_accepted(paths: RuntimePaths) -> bool:
    from desktop.host.terms import ensure_terms_accepted

    return ensure_terms_accepted(paths.settings_file)


def _bounded_detail_code(detail_code: str | None) -> str | None:
    if (
        isinstance(detail_code, str)
        and _SAFE_DETAIL_CODE.fullmatch(detail_code) is not None
    ):
        return detail_code
    return None


def _show_startup_failure(
    reason: StartupBlockReason,
    *,
    detail_code: str | None = None,
) -> int:
    """只输出固定诊断码，并尽力显示不依赖 WebEngine 的原生失败面。"""

    if not isinstance(reason, StartupBlockReason):
        raise TypeError("startup block reason must be a fixed enum")
    print(f"PDM_STARTUP_BLOCKED:{reason.value}", file=sys.stderr)
    safe_detail = _bounded_detail_code(detail_code)
    if safe_detail is not None:
        print(f"PDM_STARTUP_DETAIL:{safe_detail}", file=sys.stderr)
    try:
        from desktop.host.startup_surface import show_startup_blocked

        return show_startup_blocked(reason)
    except Exception:
        print("PDM_NATIVE_STARTUP_SURFACE_UNAVAILABLE", file=sys.stderr)
        return STARTUP_REFUSAL_EXIT_CODE


def _run_product_window(application, window) -> int:
    """运行正式宿主；仅完整就绪并完成 H06 安全退出时返回 0。"""

    window.exit_requested.connect(application.quit)
    canvas_ready = False
    canvas_failed = False
    initial_surface_shown = False

    def mark_ready() -> None:
        nonlocal canvas_ready
        canvas_ready = True

    def mark_failed() -> None:
        nonlocal canvas_ready, canvas_failed
        canvas_ready = False
        canvas_failed = True

    def show_initial_surface() -> None:
        nonlocal initial_surface_shown
        if initial_surface_shown:
            return
        initial_surface_shown = True
        window.show()

    window.canvas_ready.connect(mark_ready)
    window.canvas_failed.connect(mark_failed)
    window.initial_surface_ready.connect(show_initial_surface)
    application_exit_code = int(application.exec())

    cleanup = window.security.last_result
    clipboard_resolved = getattr(window, "exit_clipboard_retry_resolved", False) is True
    clean_exit = (
        application_exit_code == 0
        and initial_surface_shown
        and canvas_ready
        and not canvas_failed
        and window.exit_cleanup_complete
        and cleanup is not None
        and cleanup.reason == "exit"
        and (cleanup.complete or clipboard_resolved)
        and (not window.exit_teardown_failures or clipboard_resolved)
    )
    return 0 if clean_exit else PRODUCT_RUNTIME_FAILURE_EXIT_CODE


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if getattr(sys, "frozen", False) is True and arguments in (
        ["--check-local-network"], ["--configure-local-network"], ["--revoke-local-network"],
    ):
        from desktop.host.lan_access import HELPER_ARGUMENTS, run_helper

        return run_helper(HELPER_ARGUMENTS[arguments[0]])
    blocked_reason = _preflight(arguments)
    if blocked_reason is not None:
        return _show_startup_failure(blocked_reason)

    try:
        _configure_product_rendering()
    except Exception:
        return _show_startup_failure(
            StartupBlockReason.HOST_INITIALIZATION
        )

    try:
        application = _create_application()
    except Exception:
        return _show_startup_failure(
            StartupBlockReason.HOST_INITIALIZATION
        )

    try:
        paths = ProductRuntimePaths.resolve(_application_directory())
        paths.prepare()
    except ProductPathError as exc:
        return _show_startup_failure(
            StartupBlockReason.RUNTIME_PATHS,
            detail_code=exc.code,
        )
    except Exception:
        return _show_startup_failure(
            StartupBlockReason.HOST_INITIALIZATION
        )

    try:
        if not _ensure_terms_accepted(paths):
            return 0
        window = _create_product_window(paths)
    except Exception:
        return _show_startup_failure(
            StartupBlockReason.HOST_INITIALIZATION
        )

    try:
        return _run_product_window(application, window)
    except Exception:
        print("PDM_PRODUCT_RUNTIME_FAILED", file=sys.stderr)
        return PRODUCT_RUNTIME_FAILURE_EXIT_CODE


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["main"]
