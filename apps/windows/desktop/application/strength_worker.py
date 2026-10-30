"""在可终止的独立进程中执行长密码强度分析。"""

from __future__ import annotations

import json
from pathlib import Path
import queue
import subprocess
import sys
import threading


_ROOT = Path(__file__).resolve().parents[2]
_MAX_REQUEST_BYTES = 16_384
_POLL_SECONDS = 0.05
_MAX_REPORT_BYTES = 4096

_LEVELS = {"WEAK", "FAIR", "STRONG"}
_FEEDBACK_CODES = {
    "EMPTY",
    "TOO_SHORT",
    "ADD_WORDS",
    "AVOID_REPEATS",
    "AVOID_SEQUENCES",
    "AVOID_RECENT_YEARS",
    "AVOID_DATES",
    "AVOID_COMMON_PASSWORD",
    "AVOID_COMMON_WORD",
    "AVOID_NAMES",
    "AVOID_USER_DATA",
    "AVOID_KEYBOARD_PATTERN",
    "AVOID_LEET_PATTERN",
    "DICTIONARY_MATCH",
}
_BUCKETS = {
    "INSTANT",
    "SECONDS",
    "MINUTES",
    "HOURS",
    "DAYS",
    "MONTHS",
    "YEARS",
    "CENTURIES",
}
_CRACK_TIME_KEYS = {
    "onlineThrottled",
    "onlineUnthrottled",
    "offlineSlow",
    "offlineFast",
}


class StrengthAnalysisCancelled(Exception):
    """调用方撤销了仍在运行的强度分析。"""


class StrengthWorkerError(Exception):
    """强度分析子进程或其固定协议失败。"""


class _WindowsKillJob:
    """父进程最后关闭句柄时由 Windows 终止成员进程。"""

    def __init__(self, process: subprocess.Popen[bytes]) -> None:
        self._handle = None
        if sys.platform != "win32":
            return

        import ctypes
        from ctypes import wintypes

        class _IoCounters(ctypes.Structure):
            _fields_ = [
                ("ReadOperationCount", ctypes.c_ulonglong),
                ("WriteOperationCount", ctypes.c_ulonglong),
                ("OtherOperationCount", ctypes.c_ulonglong),
                ("ReadTransferCount", ctypes.c_ulonglong),
                ("WriteTransferCount", ctypes.c_ulonglong),
                ("OtherTransferCount", ctypes.c_ulonglong),
            ]

        class _BasicLimitInformation(ctypes.Structure):
            _fields_ = [
                ("PerProcessUserTimeLimit", ctypes.c_longlong),
                ("PerJobUserTimeLimit", ctypes.c_longlong),
                ("LimitFlags", wintypes.DWORD),
                ("MinimumWorkingSetSize", ctypes.c_size_t),
                ("MaximumWorkingSetSize", ctypes.c_size_t),
                ("ActiveProcessLimit", wintypes.DWORD),
                ("Affinity", ctypes.c_size_t),
                ("PriorityClass", wintypes.DWORD),
                ("SchedulingClass", wintypes.DWORD),
            ]

        class _ExtendedLimitInformation(ctypes.Structure):
            _fields_ = [
                ("BasicLimitInformation", _BasicLimitInformation),
                ("IoInfo", _IoCounters),
                ("ProcessMemoryLimit", ctypes.c_size_t),
                ("JobMemoryLimit", ctypes.c_size_t),
                ("PeakProcessMemoryUsed", ctypes.c_size_t),
                ("PeakJobMemoryUsed", ctypes.c_size_t),
            ]

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CreateJobObjectW.argtypes = [wintypes.LPVOID, wintypes.LPCWSTR]
        kernel32.CreateJobObjectW.restype = wintypes.HANDLE
        kernel32.SetInformationJobObject.argtypes = [
            wintypes.HANDLE,
            ctypes.c_int,
            wintypes.LPVOID,
            wintypes.DWORD,
        ]
        kernel32.SetInformationJobObject.restype = wintypes.BOOL
        kernel32.AssignProcessToJobObject.argtypes = [
            wintypes.HANDLE,
            wintypes.HANDLE,
        ]
        kernel32.AssignProcessToJobObject.restype = wintypes.BOOL
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel32.CloseHandle.restype = wintypes.BOOL

        handle = kernel32.CreateJobObjectW(None, None)
        if not handle:
            raise OSError(ctypes.get_last_error())
        try:
            information = _ExtendedLimitInformation()
            information.BasicLimitInformation.LimitFlags = 0x00002000
            if not kernel32.SetInformationJobObject(
                handle, 9, ctypes.byref(information), ctypes.sizeof(information)
            ):
                raise OSError(ctypes.get_last_error())
            if not kernel32.AssignProcessToJobObject(handle, process._handle):
                raise OSError(ctypes.get_last_error())
        except BaseException:
            kernel32.CloseHandle(handle)
            raise
        self._handle = handle
        self._close_handle = kernel32.CloseHandle

    def close(self) -> None:
        if self._handle is not None:
            self._close_handle(self._handle)
            self._handle = None


def _validate_input(password: object, platform: object, account: object) -> None:
    fields = (
        (password, 1024, 4096),
        (platform, 128, 512),
        (account, 512, 2048),
    )
    try:
        invalid = any(
            type(value) is not str
            or "\0" in value
            or len(value) > max_chars
            or len(value.encode("utf-8")) > max_bytes
            for value, max_chars, max_bytes in fields
        )
    except UnicodeEncodeError:
        invalid = True
    if invalid:
        raise StrengthWorkerError("强度分析输入无效")


def _bucket(guesses: int, rate_numerator: int, rate_denominator: int = 1) -> str:
    thresholds = (
        (1, "INSTANT"),
        (60, "SECONDS"),
        (3_600, "MINUTES"),
        (86_400, "HOURS"),
        (2_678_400, "DAYS"),
        (32_140_800, "MONTHS"),
        (3_214_080_000, "YEARS"),
    )
    for seconds, name in thresholds:
        if guesses * rate_denominator < seconds * rate_numerator:
            return name
    return "CENTURIES"


def _report(password: str, platform: str, account: str) -> dict[str, object]:
    from core.password_tools import PasswordTools

    result = PasswordTools.check_password_strength(
        password,
        platform,
        account,
        max_length=1024,
    )
    guesses = result.guesses
    return {
        "level": result.level.upper(),
        "score": result.score,
        "feedbackCodes": result.feedback_codes,
        "crackTimes": {
            "onlineThrottled": _bucket(guesses, 100, 3600),
            "onlineUnthrottled": _bucket(guesses, 10),
            "offlineSlow": _bucket(guesses, 10_000),
            "offlineFast": _bucket(guesses, 10_000_000_000),
        },
        "guesses": str(guesses),
        "downgraded": result.downgraded,
    }


def _validate_report(value: object) -> dict[str, object]:
    if not isinstance(value, dict) or set(value) != {
        "level", "score", "feedbackCodes", "crackTimes", "guesses", "downgraded"
    }:
        raise StrengthWorkerError("强度分析结果无效")
    feedback_codes = value["feedbackCodes"]
    crack_times = value["crackTimes"]
    guesses = value["guesses"]
    level = value["level"]
    score = value["score"]
    if (
        type(level) is not str
        or level not in _LEVELS
        or type(score) is not int
        or not 0 <= score <= 4
        or not isinstance(feedback_codes, list)
        or len(feedback_codes) > 16
        or any(type(code) is not str or code not in _FEEDBACK_CODES for code in feedback_codes)
        or len(feedback_codes) != len(set(feedback_codes))
        or not isinstance(crack_times, dict)
        or set(crack_times) != _CRACK_TIME_KEYS
        or any(
            type(bucket) is not str or bucket not in _BUCKETS
            for bucket in crack_times.values()
        )
        or type(guesses) is not str
        or not 1 <= len(guesses) <= 1025
        or not guesses.isascii()
        or not guesses.isdigit()
        or type(value["downgraded"]) is not bool
    ):
        raise StrengthWorkerError("强度分析结果无效")
    return value


def _stop_process(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=2)


def _resume_windows_process(process_id: int) -> None:
    """恢复刚以 CREATE_SUSPENDED 创建、尚未执行的唯一初始线程。"""
    if sys.platform != "win32":
        return
    import ctypes
    from ctypes import wintypes

    class _ThreadEntry(ctypes.Structure):
        _fields_ = [
            ("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD),
            ("th32ThreadID", wintypes.DWORD), ("th32OwnerProcessID", wintypes.DWORD),
            ("tpBasePri", wintypes.LONG), ("tpDeltaPri", wintypes.LONG),
            ("dwFlags", wintypes.DWORD),
        ]

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    kernel32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    for name in ("Thread32First", "Thread32Next"):
        function = getattr(kernel32, name)
        function.argtypes = [wintypes.HANDLE, ctypes.POINTER(_ThreadEntry)]
        function.restype = wintypes.BOOL
    kernel32.OpenThread.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenThread.restype = wintypes.HANDLE
    kernel32.ResumeThread.argtypes = [wintypes.HANDLE]
    kernel32.ResumeThread.restype = wintypes.DWORD
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL
    snapshot = kernel32.CreateToolhelp32Snapshot(0x00000004, 0)
    if snapshot == ctypes.c_void_p(-1).value:
        raise OSError("无法枚举强度分析初始线程")
    thread_ids = []
    try:
        entry = _ThreadEntry()
        entry.dwSize = ctypes.sizeof(entry)
        found = kernel32.Thread32First(snapshot, ctypes.byref(entry))
        while found:
            if entry.th32OwnerProcessID == process_id:
                thread_ids.append(entry.th32ThreadID)
            found = kernel32.Thread32Next(snapshot, ctypes.byref(entry))
        if ctypes.get_last_error() != 18 or len(thread_ids) != 1:
            raise OSError("强度分析初始线程状态无效")
    finally:
        kernel32.CloseHandle(snapshot)
    thread = kernel32.OpenThread(0x0002, False, thread_ids[0])
    if not thread:
        raise OSError("无法访问强度分析初始线程")
    try:
        if kernel32.ResumeThread(thread) != 1:
            raise OSError("无法恢复强度分析初始线程")
    finally:
        kernel32.CloseHandle(thread)


def _start_strength_process(
    *, reusable: bool = False
) -> tuple[subprocess.Popen[bytes], _WindowsKillJob]:
    """先暂停创建并绑定退出回收作业，再允许解释器及其后代开始执行。"""
    if getattr(sys, "frozen", False):
        arguments = [str(Path(sys.executable).resolve().with_name("cangoo_strength_worker.exe"))]
    else:
        arguments = [sys.executable, "-m", "desktop.application.strength_worker"]
    if reusable:
        arguments.append("--reuse")
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    if sys.platform == "win32":
        flags |= 0x00000004  # CREATE_SUSPENDED；Popen 会关闭原始线程句柄。
    if reusable:
        flags |= getattr(subprocess, "BELOW_NORMAL_PRIORITY_CLASS", 0)
    try:
        process = subprocess.Popen(arguments, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=subprocess.DEVNULL, cwd=_ROOT, creationflags=flags)
    except OSError:
        raise StrengthWorkerError("无法启动强度分析子进程") from None
    job = None
    try:
        job = _WindowsKillJob(process)
        _resume_windows_process(process.pid)
        return process, job
    except BaseException as error:
        try:
            _stop_process(process)
        finally:
            if job is not None:
                job.close()
            for pipe in (process.stdin, process.stdout):
                if pipe is not None:
                    pipe.close()
        raise StrengthWorkerError("无法保护强度分析子进程") from error


def _health_machine_capacity() -> tuple[int, int]:
    """读取当前进程可用逻辑核心和当前可用物理内存，不改变系统调度。"""
    if sys.platform != "win32":
        raise OSError("当前平台未提供体检容量探测")
    import ctypes
    from ctypes import wintypes

    class _MemoryStatus(ctypes.Structure):
        _fields_ = [
            ("dwLength", wintypes.DWORD),
            ("dwMemoryLoad", wintypes.DWORD),
            ("ullTotalPhys", ctypes.c_ulonglong),
            ("ullAvailPhys", ctypes.c_ulonglong),
            ("ullTotalPageFile", ctypes.c_ulonglong),
            ("ullAvailPageFile", ctypes.c_ulonglong),
            ("ullTotalVirtual", ctypes.c_ulonglong),
            ("ullAvailVirtual", ctypes.c_ulonglong),
            ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
        ]

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.GetCurrentProcess.restype = wintypes.HANDLE
    kernel32.GetProcessAffinityMask.argtypes = [
        wintypes.HANDLE, ctypes.POINTER(ctypes.c_size_t), ctypes.POINTER(ctypes.c_size_t)
    ]
    kernel32.GetProcessAffinityMask.restype = wintypes.BOOL
    kernel32.GlobalMemoryStatusEx.argtypes = [ctypes.POINTER(_MemoryStatus)]
    kernel32.GlobalMemoryStatusEx.restype = wintypes.BOOL
    process_mask, system_mask = ctypes.c_size_t(), ctypes.c_size_t()
    memory = _MemoryStatus()
    memory.dwLength = ctypes.sizeof(memory)
    if not kernel32.GetProcessAffinityMask(
        kernel32.GetCurrentProcess(), ctypes.byref(process_mask), ctypes.byref(system_mask)
    ) or not kernel32.GlobalMemoryStatusEx(ctypes.byref(memory)):
        raise OSError("无法读取体检容量")
    cpus = process_mask.value.bit_count()
    if cpus < 1 or memory.ullAvailPhys < 1:
        raise OSError("体检容量无效")
    return cpus, int(memory.ullAvailPhys)


def recommended_health_workers(record_count: int) -> int:
    """体检启动时选择保守并发数；空库不启动进程，探测失败退回一个。"""
    if type(record_count) is not int or record_count < 0:
        raise ValueError("体检记录数无效")
    if record_count < 2:
        return record_count
    try:
        cpus, available_memory = _health_machine_capacity()
    except (OSError, ValueError, AttributeError):
        return 1
    # ponytail: 启动时定额，最多四个；确有持续资源压力再增加运行中缩容。
    memory_limit = max(1, (available_memory - 1024**3) // (256 * 1024**2))
    return max(1, min(record_count, cpus // 2, memory_limit, 4))


class StrengthAnalysisWorker:
    """一次体检内复用的评分进程；每个实例只允许一条在途，关闭后不可再用。"""

    def __init__(self) -> None:
        self._closed = threading.Event()
        self._io_failed = threading.Event()
        self._analyzing = threading.Lock()
        self._closing = threading.Lock()
        self._requests: queue.Queue[bytes] = queue.Queue(maxsize=1)
        self._responses: queue.Queue[bytes] = queue.Queue(maxsize=1)
        self._process, self._job = _start_strength_process(reusable=True)
        self._io_thread = threading.Thread(
            target=self._exchange, name="health-strength-pipe", daemon=True
        )
        try:
            self._io_thread.start()
        except RuntimeError as error:
            self.close()
            raise StrengthWorkerError("无法启动强度分析管道") from error

    def __enter__(self) -> StrengthAnalysisWorker:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def _exchange(self) -> None:
        """管道读写均放到同一个线程，写入等待也不会妨碍调用方响应取消。"""
        try:
            while not self._closed.is_set():
                try:
                    payload = self._requests.get(timeout=_POLL_SECONDS)
                except queue.Empty:
                    continue
                try:
                    if self._closed.is_set():
                        return
                    self._process.stdin.write(payload + b"\n")
                    self._process.stdin.flush()
                    response = self._process.stdout.readline(_MAX_REPORT_BYTES + 2)
                    if (
                        not response.endswith(b"\n")
                        or len(response) > _MAX_REPORT_BYTES + 1
                    ):
                        raise StrengthWorkerError("强度分析结果无效")
                    self._responses.put_nowait(response)
                finally:
                    payload = None
        except (OSError, ValueError, queue.Full, StrengthWorkerError):
            self._io_failed.set()

    def analyze(
        self, password: str, platform: str, account: str, cancelled: threading.Event
    ) -> dict[str, object]:
        _validate_input(password, platform, account)
        if not self._analyzing.acquire(blocking=False):
            raise StrengthWorkerError("强度分析进程已有任务")
        try:
            if cancelled.is_set():
                raise StrengthAnalysisCancelled()
            if self._closed.is_set() or self._io_failed.is_set():
                raise StrengthWorkerError("强度分析进程已关闭")
            payload = json.dumps(
                {"password": password, "platform": platform, "account": account},
                ensure_ascii=False,
                separators=(",", ":"),
            ).encode("utf-8")
            if len(payload) > _MAX_REQUEST_BYTES:
                raise StrengthWorkerError("强度分析输入无效")
            self._requests.put_nowait(payload)
            payload = None
            while True:
                if cancelled.is_set():
                    raise StrengthAnalysisCancelled()
                if self._closed.is_set() or self._io_failed.is_set():
                    raise StrengthWorkerError("强度分析子进程失败")
                try:
                    response = self._responses.get(timeout=_POLL_SECONDS)
                    break
                except queue.Empty:
                    continue
            if cancelled.is_set():
                raise StrengthAnalysisCancelled()
            if self._closed.is_set():
                raise StrengthWorkerError("强度分析进程已关闭")
            try:
                return _validate_report(json.loads(response))
            except (UnicodeDecodeError, json.JSONDecodeError) as error:
                raise StrengthWorkerError("强度分析结果无效") from error
        except BaseException:
            self.close()
            raise
        finally:
            self._analyzing.release()

    def close(self) -> None:
        """可从撤销线程调用；先结束实际计算，再回收管道和线程。"""
        with self._closing:
            if self._closed.is_set():
                return
            self._closed.set()
            try:
                _stop_process(self._process)
            finally:
                self._job.close()
                if self._io_thread.ident is not None:
                    self._io_thread.join(timeout=2)
                for pipe in (self._process.stdin, self._process.stdout):
                    if pipe is not None:
                        pipe.close()
                for pending in (self._requests, self._responses):
                    while True:
                        try:
                            pending.get_nowait()
                        except queue.Empty:
                            break


def analyze_strength_in_process(
    password: str,
    platform: str,
    account: str,
    cancelled: threading.Event,
) -> dict[str, object]:
    """执行一次强度分析；撤销时终止实际子进程并释放匿名管道。"""
    _validate_input(password, platform, account)
    if cancelled.is_set():
        raise StrengthAnalysisCancelled()

    payload = json.dumps(
        {"password": password, "platform": platform, "account": account},
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    if len(payload) > _MAX_REQUEST_BYTES:
        raise StrengthWorkerError("强度分析输入无效")

    process, job = _start_strength_process()
    try:
        pending_input: bytes | None = payload
        while True:
            if cancelled.is_set():
                raise StrengthAnalysisCancelled()
            try:
                stdout, _ = process.communicate(
                    input=pending_input,
                    timeout=_POLL_SECONDS,
                )
                break
            except subprocess.TimeoutExpired:
                pending_input = None

        if cancelled.is_set():
            raise StrengthAnalysisCancelled()
        if process.returncode != 0 or len(stdout) > 4096:
            raise StrengthWorkerError("强度分析子进程失败")
        try:
            return _validate_report(json.loads(stdout))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise StrengthWorkerError("强度分析结果无效") from error
    finally:
        try:
            _stop_process(process)
        finally:
            try:
                # 真正的解释器可能位于启动器子层；先关闭整棵作业，才能解除管道读取等待。
                job.close()
            finally:
                for pipe in (process.stdin, process.stdout):
                    if pipe is not None:
                        pipe.close()


def _response_from_payload(payload: bytes) -> bytes:
    if len(payload) > _MAX_REQUEST_BYTES:
        raise StrengthWorkerError("强度分析输入无效")
    request = json.loads(payload)
    if not isinstance(request, dict) or set(request) != {
        "password", "platform", "account"
    }:
        raise StrengthWorkerError("强度分析输入无效")
    password = request["password"]
    platform = request["platform"]
    account = request["account"]
    _validate_input(password, platform, account)
    try:
        report = _report(password, platform, account)
        return json.dumps(report, separators=(",", ":")).encode("ascii")
    finally:
        # 上游将上下文词放进模块字典；复用进程不能让上一条上下文留到下一条。
        matching = sys.modules.get("zxcvbn.matching")
        if matching is not None:
            matching.RANKED_DICTIONARIES.pop("user_inputs", None)


def _worker_main(*, reusable: bool = False) -> int:
    try:
        if reusable:
            while True:
                payload = sys.stdin.buffer.readline(_MAX_REQUEST_BYTES + 2)
                if not payload:
                    return 0
                if not payload.endswith(b"\n"):
                    return 2
                response = _response_from_payload(payload[:-1])
                payload = None
                sys.stdout.buffer.write(response + b"\n")
                sys.stdout.buffer.flush()
                response = None
        payload = sys.stdin.buffer.read(_MAX_REQUEST_BYTES + 1)
        sys.stdout.buffer.write(_response_from_payload(payload))
        return 0
    except BaseException:
        return 2


if __name__ == "__main__":
    raise SystemExit(_worker_main(reusable=sys.argv[1:] == ["--reuse"]))
