"""当前冻结程序的局域网许可；只在用户动作后启动独立提权进程。"""
from __future__ import annotations

import ctypes
from ctypes import wintypes
import os
from pathlib import Path
import sys
import threading

from PySide6.QtCore import QObject, QProcess, QTimer, Qt, Signal


STATUSES = frozenset({"DEVELOPMENT", "CHECKING", "REQUIRED", "AUTHORIZING", "REVOKING", "READY", "BLOCKED", "FAILED"})
HELPER_ARGUMENTS = {
    "--check-local-network": "check",
    "--configure-local-network": "grant",
    "--revoke-local-network": "revoke",
}
_RESULTS = {0: "READY", 11: "REQUIRED", 12: "BLOCKED", 13: "FAILED"}


def packaged_executable() -> str | None:
    if sys.platform != "win32" or getattr(sys, "frozen", False) is not True:
        return None
    path = os.path.abspath(sys.executable)
    if Path(path).name.casefold() != "cangoo.exe" or not Path(path).is_file():
        return None
    return path


def run_helper(mode: str) -> int:
    """独立冻结子进程只管理自身规则，不初始化产品路径、协议页或密码库。"""
    executable = packaged_executable()
    if executable is None or mode not in HELPER_ARGUMENTS.values():
        return 13
    from desktop.host.lan_access_native import run_native

    return run_native(executable, mode)


class _ShellExecuteInfo(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.DWORD), ("fMask", wintypes.ULONG), ("hwnd", wintypes.HWND),
                ("lpVerb", wintypes.LPCWSTR), ("lpFile", wintypes.LPCWSTR), ("lpParameters", wintypes.LPCWSTR),
                ("lpDirectory", wintypes.LPCWSTR), ("nShow", ctypes.c_int), ("hInstApp", wintypes.HINSTANCE),
                ("lpIDList", ctypes.c_void_p), ("lpClass", wintypes.LPCWSTR), ("hkeyClass", wintypes.HKEY),
                ("dwHotKey", wintypes.DWORD), ("hIcon", wintypes.HANDLE), ("hProcess", wintypes.HANDLE)]


def _elevate(executable: str, argument: str) -> str:
    if argument not in {"--configure-local-network", "--revoke-local-network"}:
        return "FAILED"
    shell = ctypes.WinDLL("shell32", use_last_error=True)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    execute = shell.ShellExecuteExW
    execute.argtypes = [ctypes.POINTER(_ShellExecuteInfo)]
    execute.restype = wintypes.BOOL
    wait = kernel.WaitForSingleObject
    wait.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    wait.restype = wintypes.DWORD
    get_code = kernel.GetExitCodeProcess
    get_code.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
    get_code.restype = wintypes.BOOL
    close = kernel.CloseHandle
    close.argtypes = [wintypes.HANDLE]
    close.restype = wintypes.BOOL
    info = _ShellExecuteInfo()
    info.cbSize, info.fMask = ctypes.sizeof(info), 0x40 | 0x400 | 0x100
    info.lpVerb, info.lpFile, info.lpParameters = "runas", executable, argument
    info.lpDirectory, info.nShow = str(Path(executable).parent), 0
    ole = ctypes.WinDLL("ole32", use_last_error=True)
    ole.CoInitializeEx.argtypes = [ctypes.c_void_p, wintypes.DWORD]
    ole.CoInitializeEx.restype = ctypes.c_long
    ole.CoUninitialize.argtypes = []
    ole.CoUninitialize.restype = None
    if ole.CoInitializeEx(None, 2) not in (0, 1):
        return "FAILED"
    try:
        if not execute(ctypes.byref(info)):
            return "CANCELLED" if ctypes.get_last_error() == 1223 else "FAILED"
        if not info.hProcess:
            return "FAILED"
        if wait(info.hProcess, 0xFFFFFFFF) != 0:
            return "FAILED"
        code = wintypes.DWORD()
        if not get_code(info.hProcess, ctypes.byref(code)):
            return "FAILED"
        return _RESULTS.get(code.value, "FAILED")
    finally:
        if info.hProcess:
            close(info.hProcess)
        ole.CoUninitialize()


class LanAccess(QObject):
    statusChanged = Signal(str)
    _finished = Signal(int, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._executable = packaged_executable()
        self.status = "REQUIRED" if self._executable else "DEVELOPMENT"
        self._generation = 0
        self._process = None
        self._closed = False
        self._previous = self.status
        self._authorize_after_check = False
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._check_timeout)
        self._finished.connect(self._elevated_finished, Qt.ConnectionType.QueuedConnection)
        if parent is not None:
            parent.destroyed.connect(self.close)

    def _set(self, status: str) -> None:
        if not self._closed and status in STATUSES and status != self.status:
            self.status = status
            self.statusChanged.emit(status)

    def refresh(self) -> bool:
        if self._closed or self.status in {"AUTHORIZING", "REVOKING", "CHECKING"}:
            return False
        if self._executable is None:
            self._set("DEVELOPMENT")
            return True
        return self._check(False)

    def _check(self, preserve_status: bool) -> bool:
        if self._process is not None:
            return False
        try:
            process = QProcess(self)
            self._process = process
            process.setProgram(self._executable)
            process.setArguments(["--check-local-network"])
            process.setStandardInputFile(QProcess.nullDevice())
            process.setStandardErrorFile(QProcess.nullDevice())
            process.setStandardOutputFile(QProcess.nullDevice())
            process.errorOccurred.connect(lambda _error: self._check_failed(process))
            process.finished.connect(lambda code, status: self._checked(process, code, status))
            if not preserve_status:
                self._set("CHECKING")
            self._timer.start(20_000)
            process.start()
            return True
        except (OSError, RuntimeError, ValueError, TypeError):
            self._discard_check()
            self._set("FAILED")
            return False

    def _checked(self, process, code: int, exit_status) -> None:
        if process is not self._process:
            return
        expected = _RESULTS.get(code, "FAILED")
        good = exit_status == QProcess.ExitStatus.NormalExit and code in _RESULTS
        self._discard_check()
        authorize, self._authorize_after_check = self._authorize_after_check, False
        if authorize and good and expected == "REQUIRED":
            self._request("--configure-local-network", "AUTHORIZING", previous="REQUIRED")
        else:
            self._set(expected if good else "FAILED")

    def _check_failed(self, process) -> None:
        if process is self._process:
            self._authorize_after_check = False
            self._discard_check()
            self._set("FAILED")

    def _check_timeout(self) -> None:
        if self._process is not None:
            self._check_failed(self._process)

    def _discard_check(self) -> None:
        self._timer.stop()
        process, self._process = self._process, None
        if process is not None:
            if process.state() != QProcess.ProcessState.NotRunning:
                process.kill()
            process.deleteLater()

    def request(self) -> bool:
        if self._closed or self._executable is None or self._process is not None or self.status in {"AUTHORIZING", "REVOKING", "CHECKING"}:
            return False
        self._previous = self.status
        self._authorize_after_check = True
        accepted = self._check(False)
        if not accepted:
            self._authorize_after_check = False
        return accepted

    def cancel_pending(self) -> None:
        """撤销尚未提权的用户意图；已由系统接受的更改继续核对实际结果。"""
        if not self._authorize_after_check:
            return
        self._authorize_after_check = False
        self._discard_check()
        self._set(self._previous)

    def revoke(self) -> bool:
        return self._request("--revoke-local-network", "REVOKING")

    def _request(self, argument: str, status: str, *, previous: str | None = None) -> bool:
        if self._closed or self._executable is None or self._process is not None or self.status in {"AUTHORIZING", "REVOKING"}:
            return False
        if self.status == "CHECKING" and previous is None:
            return False
        self._previous = previous or self.status
        self._generation += 1
        generation, executable = self._generation, self._executable
        self._set(status)

        def work():
            try:
                outcome = _elevate(executable, argument)
            except Exception:
                outcome = "FAILED"
            try:
                self._finished.emit(generation, outcome)
            except RuntimeError:
                pass

        try:
            threading.Thread(target=work, name="cangoo_lan_permission", daemon=True).start()
        except RuntimeError:
            self._set("FAILED")
            return False
        return True

    def _elevated_finished(self, generation: int, outcome: str) -> None:
        if self._closed or generation != self._generation:
            return
        if outcome == "CANCELLED":
            self._set(self._previous)
        elif outcome in {"READY", "REQUIRED"}:
            self._check(True)
        else:
            self._set(outcome if outcome in {"BLOCKED", "FAILED"} else "FAILED")

    def close(self, *_args) -> None:
        self._closed = True
        self._generation += 1
        self._discard_check()
