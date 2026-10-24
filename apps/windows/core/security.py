"""
安全锁定服务模块

从早期界面实现中剥离的安全锁定相关逻辑，
提供数据库锁定状态管理、错误尝试计数、最近数据库路径记忆、
系统空闲检测、强制清理等功能。

依赖 core.crypto.CryptoHelper 的 encrypt_lock_info / decrypt_lock_info
进行 AES-256-GCM 加密（使用固定 SECURITY_LOCK_KEY，不依赖用户密码）。

security.st 文件格式（行式文本，UTF-8 编码）：
    第 1 行         : AES 加密的上次连接数据库路径
    第 2 ~ N 行     : 锁定记录，格式 `加密数据库路径|加密锁定时间`
                      （支持多数据库独立锁定，每条记录独立 24 小时有效）
    [FAILED_ATTEMPTS] 标记行：文件末尾保存加密规范路径与加密失败次数（1/2），无此段的旧文件按零次读取。
    [RECENT] 标记行 : 到下一区段前为最近使用的数据库路径，格式 `加密路径|加密使用时间`
                      （时间为 ISO 8601 时间戳，记录最近一次连接时间）
                      旧格式仅含加密路径（无 |），读取时自动兼容
                      （时间戳为 None，UI 层回退到文件修改时间）

设计要点：
    - 不依赖任何 UI 框架（PyQt5/PySide6），所有错误静默处理或通过返回值体现
    - 兼容 API 以返回值体现失败；生产宿主使用 strict API 失败关闭
    - 查询只过滤超过 24 小时的过期记录，不在读取路径上改写磁盘
    - 扩展的「最近使用数据库列表」与原有格式兼容：旧文件无 [RECENT] 标记时
      仅解析锁定记录，写入时按需追加 [RECENT] 区段
    - get_idle_seconds() 通过 Win32 GetLastInputInfo 获取系统级空闲时长
      （core 层不依赖 QTimer，轮询由 UI 层负责）
    - force_cleanup() 按序执行清理函数，单个失败不中断后续清理
"""

import os
import sys
import ctypes
import datetime
import hashlib
import tempfile
import threading
from contextlib import contextmanager
from dataclasses import dataclass, field

from core.crypto import CryptoHelper


# 锁定时长（小时）
LOCK_DURATION_HOURS = 24
# 触发锁定的连续失败尝试阈值
FAILED_ATTEMPT_THRESHOLD = 3
# 最近数据库路径最大保存数量
MAX_RECENT_DB_PATHS = 5
# security.st 中「最近使用数据库列表」区段的标记行
RECENT_SECTION_MARKER = "[RECENT]"
FAILED_SECTION_MARKER = "[FAILED_ATTEMPTS]"
# 默认数据库文件名；正式入口只展示候选路径，用户提交前不创建数据库。
DEFAULT_DB_FILENAME = "pdm.db"


def _persisted_path_syntax_is_local(value) -> bool:
    """纯词法拒绝可能触发网络或设备访问的持久化路径。"""

    if not isinstance(value, str) or not value:
        return False
    normalized = value.replace("/", "\\")
    if normalized.startswith(("\\\\", "\\?\\", "\\.\\")):
        return False
    colon_positions = [
        index for index, character in enumerate(value) if character == ":"
    ]
    return colon_positions in ([], [1])


class SecurityStateCommitError(RuntimeError):
    """security.st 严格提交失败；调用方不得继续发布成功状态。"""


@dataclass(frozen=True)
class AuthenticationFailureState:
    """一次认证失败提交后的稳定状态。"""

    remaining_attempts: int
    locked_until_unix_ms: int

# Win32 API 返回类型修正:GetTickCount64 返回 64 位无符号整数,
# ctypes 默认按 c_int(32 位有符号)解析会截断,需显式设置。
# 此为进程级一次性配置,对其他调用者也是正确的(该 API 本就返回 uint64)。
ctypes.windll.kernel32.GetTickCount64.restype = ctypes.c_uint64


class _LASTINPUTINFO(ctypes.Structure):
    """Win32 LASTINPUTINFO 结构体,用于 user32.GetLastInputInfo。

    cbSize: 结构体字节数,调用前必须设置为 sizeof(LASTINPUTINFO)。
    dwTime: 上次输入事件的时间戳(毫秒,与 GetTickCount 同源,32 位,
            在系统运行约 49.7 天后回绕)。
    """
    _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]


@dataclass
class CleanupResult:
    """force_cleanup 执行结果,供 UI 反馈清理状态。

    Attributes:
        success_count: 成功执行的 cleaner 数量。
        failure_count: 失败(抛异常)的 cleaner 数量。
        failures: 失败详情列表,每项为 dict(index/cleaner/error)。
    """
    success_count: int = 0
    failure_count: int = 0
    failures: list = field(default_factory=list)

    @property
    def total(self) -> int:
        """总 cleaner 数量(成功 + 失败)。"""
        return self.success_count + self.failure_count


def _get_entry_dir():
    """返回未显式注入路径时的通用 legacy fallback 目录。

    该函数只保留给历史/独立 core 调用方。正式 WebEngine 产品链始终通过
    ProductRuntimePaths 显式注入 security.st 生产路径，不以本函数作为路径权威。

    - 打包模式(sys.frozen=True 且存在 _MEIPASS):返回 exe 所在目录
      (sys.executable 的 dirname)。onefile 模式下不使用临时解压目录,
      避免程序退出后被 PyInstaller 清理导致数据丢失。
    - 开发模式:返回 __main__.__file__ 对应入口脚本的目录。
    - 兜底:返回 os.getcwd()。
    """
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        # PyInstaller 打包模式:用 exe 所在目录,而非临时解压目录(_MEIPASS)
        return os.path.dirname(sys.executable)
    # 开发模式:取 __main__ 模块的入口脚本目录
    main_file = getattr(sys.modules.get('__main__'), '__file__', None)
    if main_file:
        return os.path.dirname(os.path.abspath(main_file))
    return os.getcwd()


class SecurityService:
    """安全锁定服务，管理数据库锁定、错误计数与最近路径记忆。

    该类不依赖任何 UI 框架，所有错误均通过返回值或静默处理，
    不会向用户弹出任何对话框。

    Attributes:
        security_file: security.st 文件路径。
        wrong_lg: 仅在本实例锁定提交失败时保留的待提交标记；已提交失败次数以文件为权威。
    """

    def __init__(self, security_file=None):
        """初始化安全锁定服务。

        Args:
            security_file: security.st 文件路径。为 None 时默认使用
                           通用 legacy fallback 的入口目录；正式 WebEngine
                           产品链必须由 ProductRuntimePaths 显式传入安装版或
                           便携版路径。fallback 只为历史/独立调用兼容，隐藏
                           文件不构成安全保证。
        """
        if security_file is None:
            # 通用 legacy fallback；正式 WebEngine 链始终显式注入生产路径。
            self.security_file = os.path.join(_get_entry_dir(), "security.st")
        else:
            self.security_file = security_file

        # 待提交锁的失败关闭标记；正常计数持久化在同一安全状态文件。
        self.wrong_lg = {}
        self._state_lock = threading.RLock()

    @contextmanager
    def _exclusive_state(self):
        """串行化同一 security.st 的跨线程、跨进程读改写。"""

        with self._state_lock:
            if os.name != "nt":
                yield
                return
            kernel32 = ctypes.windll.kernel32
            kernel32.CreateMutexW.argtypes = (
                ctypes.c_void_p,
                ctypes.c_int,
                ctypes.c_wchar_p,
            )
            kernel32.CreateMutexW.restype = ctypes.c_void_p
            kernel32.WaitForSingleObject.argtypes = (
                ctypes.c_void_p,
                ctypes.c_uint32,
            )
            kernel32.WaitForSingleObject.restype = ctypes.c_uint32
            kernel32.ReleaseMutex.argtypes = (ctypes.c_void_p,)
            kernel32.ReleaseMutex.restype = ctypes.c_int
            kernel32.CloseHandle.argtypes = (ctypes.c_void_p,)
            kernel32.CloseHandle.restype = ctypes.c_int
            identity = os.path.normcase(
                os.path.abspath(self.security_file)
            ).encode("utf-8", errors="surrogatepass")
            name = (
                "Local\\PDM.SecurityState."
                + hashlib.sha256(identity).hexdigest()[:24]
            )
            handle = kernel32.CreateMutexW(None, False, name)
            if not handle:
                raise SecurityStateCommitError(
                    "SECURITY_STATE_MUTEX_CREATE_FAILED"
                )
            acquired = False
            try:
                wait_result = int(
                    kernel32.WaitForSingleObject(handle, 10_000)
                )
                if wait_result not in {0x00000000, 0x00000080}:
                    raise SecurityStateCommitError(
                        "SECURITY_STATE_MUTEX_WAIT_FAILED"
                    )
                acquired = True
                yield
            finally:
                if acquired:
                    kernel32.ReleaseMutex(handle)
                kernel32.CloseHandle(handle)

    # ------------------------------------------------------------------
    # 内部读写工具
    # ------------------------------------------------------------------

    def _read_lines(self, *, strict=False):
        """读取 security.st；严格读与写入共享同一个跨进程互斥体。"""

        if strict:
            with self._exclusive_state():
                return self._read_lines_unlocked(strict=True)
        return self._read_lines_unlocked(strict=False)

    def _read_lines_unlocked(self, *, strict):
        try:
            if not os.path.lexists(self.security_file):
                return [""]
            with open(self.security_file, "r", encoding="utf-8") as handle:
                content = handle.read()
            if content.endswith("\n"):
                content = content[:-1]
            if not content:
                return [""]
            lines = content.split("\n")
            if strict and lines[0]:
                CryptoHelper.decrypt_lock_info(lines[0])
            if strict:
                self._parse_attempt_counts(lines, strict=True)
            return lines
        except Exception as exc:
            if strict:
                if isinstance(exc, SecurityStateCommitError):
                    raise
                raise SecurityStateCommitError(
                    "SECURITY_STATE_READ_FAILED"
                ) from exc
            return [""]

    def _atomic_write_bytes(self, payload, *, validator=None):
        """同目录原子替换、读回验证，并在提交后故障时恢复旧字节。"""

        target = os.path.abspath(self.security_file)
        directory = os.path.dirname(target) or os.getcwd()
        try:
            os.makedirs(directory, exist_ok=True)
            previous_exists = os.path.lexists(target)
            previous = None
            if previous_exists:
                if not os.path.isfile(target) or os.path.islink(target):
                    raise SecurityStateCommitError(
                        "SECURITY_STATE_TARGET_INVALID"
                    )
                with open(target, "rb") as handle:
                    previous = handle.read()
        except Exception as exc:
            if isinstance(exc, SecurityStateCommitError):
                raise
            raise SecurityStateCommitError(
                "SECURITY_STATE_PREPARE_FAILED"
            ) from exc

        staged = None
        replaced = False
        try:
            fd, staged = tempfile.mkstemp(
                prefix=".security.st.",
                suffix=".commit",
                dir=directory,
            )
            with os.fdopen(fd, "wb") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            with open(staged, "rb") as handle:
                staged_payload = handle.read()
            if staged_payload != payload:
                raise SecurityStateCommitError(
                    "SECURITY_STATE_STAGED_VERIFY_FAILED"
                )
            if validator is not None and not validator(staged_payload):
                raise SecurityStateCommitError(
                    "SECURITY_STATE_SEMANTIC_VERIFY_FAILED"
                )
            os.replace(staged, target)
            staged = None
            replaced = True
            with open(target, "rb") as handle:
                if handle.read() != payload:
                    raise SecurityStateCommitError(
                        "SECURITY_STATE_FINAL_VERIFY_FAILED"
                    )
        except Exception as exc:
            if replaced:
                try:
                    if previous_exists:
                        rollback_fd, rollback_name = tempfile.mkstemp(
                            prefix=".security.st.",
                            suffix=".rollback",
                            dir=directory,
                        )
                        with os.fdopen(rollback_fd, "wb") as handle:
                            handle.write(previous or b"")
                            handle.flush()
                            os.fsync(handle.fileno())
                        try:
                            os.replace(rollback_name, target)
                            with open(target, "rb") as handle:
                                if handle.read() != (previous or b""):
                                    raise SecurityStateCommitError(
                                        "SECURITY_STATE_ROLLBACK_VERIFY_FAILED"
                                    )
                        finally:
                            if os.path.exists(rollback_name):
                                os.remove(rollback_name)
                    elif os.path.exists(target):
                        os.remove(target)
                        if os.path.lexists(target):
                            raise SecurityStateCommitError(
                                "SECURITY_STATE_ROLLBACK_VERIFY_FAILED"
                            )
                except Exception as rollback_exc:
                    raise SecurityStateCommitError(
                        "SECURITY_STATE_ROLLBACK_FAILED"
                    ) from rollback_exc
            if isinstance(exc, SecurityStateCommitError):
                raise
            raise SecurityStateCommitError(
                "SECURITY_STATE_COMMIT_FAILED"
            ) from exc
        finally:
            if staged is not None:
                try:
                    os.remove(staged)
                except OSError:
                    pass

    def _write_lines(self, lines, *, strict=False, validator=None):
        """原子写回 security.st；失败返回 False 或在严格模式抛错。

        写入前自动创建所在目录（首次运行时目录可能尚不存在）。
        """
        try:
            payload = ("\n".join(lines) + "\n").encode("utf-8")
            with self._exclusive_state():
                self._atomic_write_bytes(payload, validator=validator)
            return True
        except SecurityStateCommitError:
            if strict:
                raise
            return False

    def _parse_lock_records(self, lines, *, strict=False):
        """从行列表中解析仍有效的锁定记录。

        解析 lines[1:] 中形如 `加密路径|加密时间` 的记录，
        自动过滤超过 24 小时的过期记录以及解密失败的旧格式记录。
        遇到 [RECENT] 标记行时停止解析（后续行属于最近路径区段）。

        Returns:
            list[tuple[str, str]]: 每个元素为 (原始行, 解密后的数据库路径)。
        """
        current_time = datetime.datetime.now()
        active = []
        for line in lines[1:]:
            if line in {RECENT_SECTION_MARKER, FAILED_SECTION_MARKER}:
                # 进入后续状态区段，锁定记录区段结束
                break
            if "|" not in line:
                if strict and line:
                    raise SecurityStateCommitError(
                        "SECURITY_LOCK_RECORD_INVALID"
                    )
                continue
            try:
                parts = line.split("|", 1)
                locked_db = CryptoHelper.decrypt_lock_info(parts[0])
                lock_time_str = CryptoHelper.decrypt_lock_info(parts[1])
                lock_time = datetime.datetime.fromisoformat(lock_time_str)
                if (current_time - lock_time) < datetime.timedelta(hours=LOCK_DURATION_HOURS):
                    active.append((line, locked_db))
            except Exception as exc:
                if strict:
                    raise SecurityStateCommitError(
                        "SECURITY_LOCK_RECORD_INVALID"
                    ) from exc
                # 解密失败视为无效记录（v2.0 不兼容旧 ECB 格式），跳过
                continue
        return active

    def _parse_recent_paths(self, lines, *, strict=False):
        """解析「最近使用数据库列表」区段。

        Returns:
            list[str]: [RECENT] 标记行之后的加密路径行列表（保持写入顺序）。
        """
        recent_lines = []
        in_recent = False
        for line in lines[1:]:
            if line == FAILED_SECTION_MARKER:
                break
            if line == RECENT_SECTION_MARKER:
                if strict and in_recent:
                    raise SecurityStateCommitError(
                        "SECURITY_RECENT_SECTION_INVALID"
                    )
                in_recent = True
                continue
            if in_recent:
                if line:
                    recent_lines.append(line)
        return recent_lines

    def _decode_recent_entries(self, recent_lines, *, strict=False):
        """统一解析 recent 新旧格式，返回原行、规范路径和时间。"""

        entries = []
        seen = set()
        for raw_line in recent_lines:
            try:
                if "|" in raw_line:
                    encrypted_path, encrypted_time = raw_line.split("|", 1)
                    timestamp = datetime.datetime.fromisoformat(
                        CryptoHelper.decrypt_lock_info(encrypted_time)
                    )
                else:
                    encrypted_path = raw_line
                    timestamp = None
                path = os.path.normpath(
                    CryptoHelper.decrypt_lock_info(encrypted_path)
                )
                key = os.path.normcase(path)
                if path and key not in seen:
                    seen.add(key)
                    entries.append((raw_line, path, timestamp))
            except Exception as exc:
                if strict:
                    raise SecurityStateCommitError(
                        "SECURITY_RECENT_RECORD_INVALID"
                    ) from exc
                continue
        return entries

    @staticmethod
    def _attempt_key(db_path):
        return os.path.normcase(os.path.normpath(db_path))

    def _forget_pending_attempts(self, db_path):
        key = self._attempt_key(db_path)
        for path in tuple(self.wrong_lg):
            if self._attempt_key(path) == key:
                self.wrong_lg.pop(path, None)

    def _parse_attempt_counts(self, lines, *, strict=False):
        """独立解析未达阈值的持久计数；旧文件没有区段时返回空表。"""
        counts = {}
        active = False
        try:
            for line in lines[1:]:
                if line == FAILED_SECTION_MARKER:
                    if active:
                        raise ValueError("duplicate attempts section")
                    active = True
                    continue
                if not active or not line:
                    continue
                encrypted_path, encrypted_count = line.split("|", 1)
                path = CryptoHelper.decrypt_lock_info(encrypted_path)
                raw_count = CryptoHelper.decrypt_lock_info(encrypted_count)
                if not _persisted_path_syntax_is_local(path) or raw_count not in {"1", "2"}:
                    raise ValueError("invalid attempts record")
                key = self._attempt_key(path)
                if key in counts:
                    raise ValueError("duplicate attempts target")
                counts[key] = int(raw_count)
            return counts
        except Exception as exc:
            if strict:
                raise SecurityStateCommitError("SECURITY_ATTEMPTS_INVALID") from exc
            return {}

    def _rewrite(
        self,
        last_connected_line,
        lock_records,
        recent_lines,
        *,
        strict=False,
        validator=None,
        attempt_counts=None,
    ):
        """按统一格式重写 security.st。

        Args:
            last_connected_line: 首行内容（加密的上次连接路径）。
            lock_records: 锁定记录原始行列表。
            recent_lines: 最近路径加密行列表（为空时不写 [RECENT] 区段）。
        """
        if attempt_counts is None:
            attempt_counts = self._parse_attempt_counts(
                self._read_lines(strict=strict), strict=strict,
            )
        new_lines = [last_connected_line]
        new_lines.extend(lock_records)
        if recent_lines:
            new_lines.append(RECENT_SECTION_MARKER)
            new_lines.extend(recent_lines)
        if attempt_counts:
            new_lines.append(FAILED_SECTION_MARKER)
            for path, count in sorted(attempt_counts.items()):
                if type(count) is not int or count not in {1, 2}:
                    raise SecurityStateCommitError("SECURITY_ATTEMPTS_INVALID")
                new_lines.append("{}|{}".format(
                    CryptoHelper.encrypt_lock_info(path),
                    CryptoHelper.encrypt_lock_info(str(count)),
                ))
        return self._write_lines(
            new_lines,
            strict=strict,
            validator=validator,
        )

    def commit_successful_connection(self, db_path):
        """一次原子提交清锁、last path 与 recent 置顶去重。

        任一磁盘步骤失败都会抛出 :class:`SecurityStateCommitError`；
        内存失败次数只在最终语义读回成功后清除。
        """

        normalized = os.path.normpath(db_path)
        normalized_key = os.path.normcase(normalized)
        with self._exclusive_state():
            if any(
                self._attempt_key(path) == normalized_key and int(count) >= FAILED_ATTEMPT_THRESHOLD
                for path, count in self.wrong_lg.items()
            ):
                raise SecurityStateCommitError(
                    "PENDING_AUTHENTICATION_LOCK_MUST_COMMIT"
                )
            lines = self._read_lines(strict=True)
            attempt_counts = self._parse_attempt_counts(lines, strict=True)
            attempt_counts.pop(normalized_key, None)
            active_records = self._parse_lock_records(lines, strict=True)
            if any(
                os.path.normcase(os.path.normpath(locked_path))
                == normalized_key
                for _raw, locked_path in active_records
            ):
                # 认证开始后可能由另一进程写入新锁。成功提交必须重新检查
                # 磁盘事实，不能把并发产生的活动锁当成旧状态清除。
                raise SecurityStateCommitError(
                    "AUTHENTICATION_LOCK_BECAME_ACTIVE"
                )
            kept_locks = [
                raw
                for raw, locked_path in active_records
            ]
            recent_entries = self._decode_recent_entries(
                self._parse_recent_paths(lines, strict=True),
                strict=True,
            )
            kept_recent = [
                raw
                for raw, path, _timestamp in recent_entries
                if os.path.normcase(path) != normalized_key
            ][: MAX_RECENT_DB_PATHS - 1]
            now = datetime.datetime.now().isoformat()
            new_recent = "{}|{}".format(
                CryptoHelper.encrypt_lock_info(normalized),
                CryptoHelper.encrypt_lock_info(now),
            )

            def verify_candidate(payload):
                try:
                    content = payload.decode("utf-8")
                    if content.endswith("\n"):
                        content = content[:-1]
                    candidate_lines = content.split("\n") if content else [""]
                    verified_last = os.path.normpath(
                        CryptoHelper.decrypt_lock_info(candidate_lines[0])
                    )
                    verified_recents = self._decode_recent_entries(
                        self._parse_recent_paths(
                            candidate_lines,
                            strict=True,
                        ),
                        strict=True,
                    )
                    verified_locks = self._parse_lock_records(
                        candidate_lines,
                        strict=True,
                    )
                    return (
                        os.path.normcase(verified_last) == normalized_key
                        and bool(verified_recents)
                        and os.path.normcase(verified_recents[0][1])
                        == normalized_key
                        and sum(
                            os.path.normcase(path) == normalized_key
                            for _raw, path, _timestamp in verified_recents
                        )
                        == 1
                        and not any(
                            os.path.normcase(os.path.normpath(locked_path))
                            == normalized_key
                            for _raw, locked_path in verified_locks
                        )
                    )
                except Exception:
                    return False

            self._rewrite(
                CryptoHelper.encrypt_lock_info(normalized),
                kept_locks,
                [new_recent, *kept_recent],
                strict=True,
                validator=verify_candidate,
                attempt_counts=attempt_counts,
            )
            self._forget_pending_attempts(db_path)

    # ------------------------------------------------------------------
    # 锁定状态查询
    # ------------------------------------------------------------------

    def check_lock(self, db_path, *, strict=False):
        """检查指定数据库是否被锁定。

        读取 security.st 并忽略过期记录；查询本身不改写磁盘。

        Args:
            db_path: 数据库文件绝对路径。

        Returns:
            bool: True 表示该数据库当前被锁定，False 表示未锁定。
        """
        try:
            lines = self._read_lines(strict=strict)
            if not lines:
                return False

            active_records = self._parse_lock_records(
                lines,
                strict=strict,
            )

            # 判断指定数据库是否在有效锁定记录中
            for rec in active_records:
                if self._attempt_key(rec[1]) == self._attempt_key(db_path):
                    return True
            return False
        except Exception as exc:
            if strict:
                if isinstance(exc, SecurityStateCommitError):
                    raise
                raise SecurityStateCommitError(
                    "SECURITY_STATE_QUERY_FAILED"
                ) from exc
            return False

    # ------------------------------------------------------------------
    # 锁定 / 清除
    # ------------------------------------------------------------------

    def lock_database(self, db_path):
        """兼容显式锁定入口；开始新锁期时结束当前失败计数周期。"""
        try:
            with self._exclusive_state():
                self._commit_authentication_lock_unlocked(db_path)
            return True
        except SecurityStateCommitError:
            return False

    def clear_lock(self, db_path):
        """清除指定数据库的锁定记录（成功连接数据库后调用）。

        Args:
            db_path: 数据库文件绝对路径。
        """
        try:
            with self._exclusive_state():
                lines = self._read_lines(strict=True)
                last_connected_db = lines[0] if lines else ""
                active_records = self._parse_lock_records(
                    lines,
                    strict=True,
                )
                recent_lines = self._parse_recent_paths(
                    lines,
                    strict=True,
                )
                kept_records = [
                    rec[0] for rec in active_records
            if self._attempt_key(rec[1]) != self._attempt_key(db_path)
                ]
                self._rewrite(
                    last_connected_db,
                    kept_records,
                    recent_lines,
                    strict=True,
                )
            return True
        except SecurityStateCommitError:
            return False

    def record_authentication_failure(self, db_path):
        """同一跨进程事务累计失败；第三次提交锁定并结束本轮计数。"""
        key = self._attempt_key(db_path)
        with self._exclusive_state():
            locked_until = self.get_lock_until_unix_ms(db_path, strict=True)
            if locked_until:
                return AuthenticationFailureState(0, locked_until)
            lines = self._read_lines(strict=True)
            counts = self._parse_attempt_counts(lines, strict=True)
            count = counts.get(key, 0) + 1
            if count < FAILED_ATTEMPT_THRESHOLD:
                counts[key] = count
                self._rewrite(
                    lines[0],
                    [raw for raw, _path in self._parse_lock_records(lines, strict=True)],
                    self._parse_recent_paths(lines, strict=True),
                    strict=True, attempt_counts=counts,
                )
                self._forget_pending_attempts(db_path)
                return AuthenticationFailureState(FAILED_ATTEMPT_THRESHOLD - count, 0)
            # 锁定提交失败时保留本实例的失败关闭状态，下一次先补交锁。
            self.wrong_lg[db_path] = FAILED_ATTEMPT_THRESHOLD
            return self._commit_authentication_lock_unlocked(db_path)

    def commit_pending_authentication_lock(self, db_path):
        """若达到阈值但上次落盘失败，先补写锁；否则返回 None。"""

        with self._exclusive_state():
            if not any(
                self._attempt_key(path) == self._attempt_key(db_path)
                and int(count) >= FAILED_ATTEMPT_THRESHOLD
                for path, count in self.wrong_lg.items()
            ):
                return None
            return self._commit_authentication_lock_unlocked(db_path)

    def _commit_authentication_lock_unlocked(self, db_path):
        lines = self._read_lines(strict=True)
        counts = self._parse_attempt_counts(lines, strict=True)
        counts.pop(self._attempt_key(db_path), None)
        last_connected_db = lines[0] if lines else ""
        active_records = self._parse_lock_records(lines, strict=True)
        recent_lines = self._parse_recent_paths(lines, strict=True)
        kept_records = [
            rec[0] for rec in active_records
            if self._attempt_key(rec[1]) != self._attempt_key(db_path)
        ]
        lock_time = datetime.datetime.now()
        kept_records.append(
            "{}|{}".format(
                CryptoHelper.encrypt_lock_info(db_path),
                CryptoHelper.encrypt_lock_info(lock_time.isoformat()),
            )
        )
        self._rewrite(
            last_connected_db,
            kept_records,
            recent_lines,
            strict=True,
            attempt_counts=counts,
        )
        self._forget_pending_attempts(db_path)
        locked_until = lock_time + datetime.timedelta(
            hours=LOCK_DURATION_HOURS
        )
        return AuthenticationFailureState(
            remaining_attempts=0,
            locked_until_unix_ms=int(locked_until.timestamp() * 1000),
        )

    # ------------------------------------------------------------------
    # 错误尝试计数
    # ------------------------------------------------------------------

    def record_failed_attempt(self, db_path):
        """兼容入口复用持久累计及锁定，不再维护第二套内存计数。"""
        return bool(self.record_authentication_failure(db_path).locked_until_unix_ms)

    def get_lock_until_unix_ms(self, db_path, *, strict=False):
        """返回指定数据库当前锁定截止时间；未锁定或读取失败返回 0。

        返回值使用 Unix 毫秒，供原生边界生成有界 ``lockedUntilUnixMs``
        和 ``retryAfterMs``。查询不改写磁盘，也不暴露原始锁定文件内容。
        """
        try:
            lines = self._read_lines(strict=strict)
            if not lines:
                return 0

            active_records = self._parse_lock_records(
                lines,
                strict=strict,
            )

            for raw_line, locked_db in active_records:
                if self._attempt_key(locked_db) != self._attempt_key(db_path):
                    continue
                _encrypted_path, encrypted_time = raw_line.split("|", 1)
                lock_time = datetime.datetime.fromisoformat(
                    CryptoHelper.decrypt_lock_info(encrypted_time)
                )
                locked_until = lock_time + datetime.timedelta(
                    hours=LOCK_DURATION_HOURS
                )
                return max(0, int(locked_until.timestamp() * 1000))
            return 0
        except Exception as exc:
            if strict:
                if isinstance(exc, SecurityStateCommitError):
                    raise
                raise SecurityStateCommitError(
                    "SECURITY_STATE_QUERY_FAILED"
                ) from exc
            return 0

    def get_remaining_attempts(self, db_path):
        """读取当前未结束计数周期；锁定期间调用方应先检查锁定截止时间。"""
        with self._exclusive_state():
            counts = self._parse_attempt_counts(self._read_lines(strict=True), strict=True)
            used = max(counts.get(self._attempt_key(db_path), 0),
                       int(self.wrong_lg.get(db_path, 0)))
            return max(0, FAILED_ATTEMPT_THRESHOLD - used)

    def clear_failed_attempts(self, db_path):
        """成功认证后的兼容入口；计数清除与其他状态一同原子提交。"""
        with self._exclusive_state():
            lines = self._read_lines(strict=True)
            counts = self._parse_attempt_counts(lines, strict=True)
            counts.pop(self._attempt_key(db_path), None)
            self._rewrite(
                lines[0],
                [raw for raw, _path in self._parse_lock_records(lines, strict=True)],
                self._parse_recent_paths(lines, strict=True),
                strict=True, attempt_counts=counts,
            )
            self._forget_pending_attempts(db_path)

    # ------------------------------------------------------------------
    # 默认数据库路径
    # ------------------------------------------------------------------

    def get_default_db_path(self):
        """返回 legacy 调用方的默认数据库候选路径。

        此路径仅作为「无上次连接时」的回退候选值，文件存在与否不影响返回，
        本方法不创建文件。正式 WebEngine 产品链由 ProductRuntimePaths 解析
        同一安装版语义，并只在用户提交“连接 / 创建”后发布新库。

        路径推导(与 settings.json 一致,保证卸载/重装不丢数据):
            - Windows:%APPDATA%/cangoo/pdm.db
            - 非 Windows:~/.cangoo/pdm.db

        之所以放 %APPDATA% 而非 exe 同目录,是因为:
            - 打包后卸载/重装会清理 exe 目录,导致用户数据丢失
            - %APPDATA% 是 Windows 标准的漫游应用数据目录,卸载不清理
            - 与 settings.json 共享同一目录,统一管理

        Returns:
            str: 默认数据库文件绝对路径。
        """
        appdata = os.environ.get("APPDATA")
        if appdata:
            return os.path.join(appdata, "cangoo", DEFAULT_DB_FILENAME)
        return os.path.join(os.path.expanduser("~"), ".cangoo", DEFAULT_DB_FILENAME)

    # ------------------------------------------------------------------
    # 上次连接的数据库路径
    # ------------------------------------------------------------------

    def save_last_db_path(self, db_path):
        """保存上次连接的数据库路径（AES 加密存储于首行）。

        Args:
            db_path: 数据库文件绝对路径。
        """
        try:
            with self._exclusive_state():
                lines = self._read_lines(strict=True)
                active_records = self._parse_lock_records(
                    lines,
                    strict=True,
                )
                recent_lines = self._parse_recent_paths(
                    lines,
                    strict=True,
                )
                new_first_line = CryptoHelper.encrypt_lock_info(db_path)
                self._rewrite(
                    new_first_line,
                    [rec[0] for rec in active_records],
                    recent_lines,
                    strict=True,
                )
            return True
        except Exception:
            return False

    def get_last_db_path(self, *, strict=False):
        """获取上次连接的数据库路径。

        Returns:
            str | None: 解密后的数据库路径（已 normpath 且文件存在），
                        若文件不存在、解密失败或路径无效则返回 None。
        """
        try:
            lines = self._read_lines(strict=strict)
            if not lines or not lines[0]:
                return None
            try:
                db_path = CryptoHelper.decrypt_lock_info(lines[0])
                db_path = os.path.normpath(db_path)
                if not _persisted_path_syntax_is_local(db_path):
                    if strict:
                        raise SecurityStateCommitError(
                            "SECURITY_LAST_PATH_INVALID"
                        )
                    return None
                if os.path.exists(db_path):
                    return db_path
            except Exception as exc:
                if strict:
                    raise SecurityStateCommitError(
                        "SECURITY_LAST_PATH_INVALID"
                    ) from exc
                # 解密失败（旧 ECB 格式），v2.0 不兼容
                pass
            return None
        except Exception as exc:
            if strict:
                if isinstance(exc, SecurityStateCommitError):
                    raise
                raise SecurityStateCommitError(
                    "SECURITY_STATE_QUERY_FAILED"
                ) from exc
            return None

    # ------------------------------------------------------------------
    # 最近使用的数据库路径列表
    # ------------------------------------------------------------------

    def get_recent_db_paths(
        self,
        max_count=MAX_RECENT_DB_PATHS,
        *,
        strict=False,
    ):
        """获取最近使用的数据库路径列表（含最近使用时间戳）。

        Args:
            max_count: 最多返回的路径数量，默认 5。

        Returns:
            list[tuple[str, datetime.datetime | None]]: 每个元素为
                (数据库路径, 最近使用时间)。时间为 None 表示旧格式
                记录（无时间信息），调用方可回退到文件修改时间。
                已过滤掉磁盘上不存在的路径并去重，按最近使用顺序排列。
        """
        try:
            lines = self._read_lines(strict=strict)
            recent_lines = self._parse_recent_paths(
                lines,
                strict=strict,
            )
            result = []
            for _raw, path, timestamp in self._decode_recent_entries(
                recent_lines,
                strict=strict,
            ):
                if not _persisted_path_syntax_is_local(path):
                    if strict:
                        raise SecurityStateCommitError(
                            "SECURITY_RECENT_RECORD_INVALID"
                        )
                    continue
                # 词法安全后才允许触碰磁盘。
                if os.path.exists(path):
                    result.append((path, timestamp))
            return result[:max_count]
        except Exception as exc:
            if strict:
                if isinstance(exc, SecurityStateCommitError):
                    raise
                raise SecurityStateCommitError(
                    "SECURITY_STATE_QUERY_FAILED"
                ) from exc
            return []

    def add_recent_db_path(self, db_path):
        """添加一个数据库路径到最近使用列表（置顶，最多保留 5 个）。

        存储格式：加密路径|加密时间戳（ISO 8601），记录最近一次连接时间。
        旧格式（仅加密路径）在读取时自动兼容。若该路径已存在则先移除旧
        位置再置顶，保证最近使用的始终排在最前。

        Args:
            db_path: 数据库文件绝对路径。
        """
        try:
            with self._exclusive_state():
                lines = self._read_lines(strict=True)
                last_connected_db = lines[0] if lines else ""
                active_records = self._parse_lock_records(
                    lines,
                    strict=True,
                )
                entries = self._decode_recent_entries(
                    self._parse_recent_paths(lines, strict=True),
                    strict=True,
                )
                norm_path = os.path.normpath(db_path)
                norm_key = os.path.normcase(norm_path)
                kept = [
                    raw
                    for raw, path, _timestamp in entries
                    if os.path.normcase(path) != norm_key
                ][: MAX_RECENT_DB_PATHS - 1]
                new_line = "{}|{}".format(
                    CryptoHelper.encrypt_lock_info(norm_path),
                    CryptoHelper.encrypt_lock_info(
                        datetime.datetime.now().isoformat()
                    ),
                )
                self._rewrite(
                    last_connected_db,
                    [rec[0] for rec in active_records],
                    [new_line, *kept],
                    strict=True,
                )
            return True
        except Exception:
            return False

    def remove_recent_db_path(self, db_path):
        """从最近使用数据库列表中移除指定路径(不影响上次连接路径与锁定记录)。

        用户在连接面板执行“从最近列表移除”时调用。路径匹配按 normpath
        规范化后比较,大小写/分隔符差异不影响匹配。

        Args:
            db_path: 要移除的数据库文件绝对路径。
        """
        try:
            with self._exclusive_state():
                lines = self._read_lines(strict=True)
                last_connected_db = lines[0] if lines else ""
                active_records = self._parse_lock_records(
                    lines,
                    strict=True,
                )
                norm_key = os.path.normcase(os.path.normpath(db_path))
                new_recent_lines = [
                    raw
                    for raw, path, _timestamp in self._decode_recent_entries(
                        self._parse_recent_paths(lines, strict=True),
                        strict=True,
                    )
                    if os.path.normcase(path) != norm_key
                ]
                self._rewrite(
                    last_connected_db,
                    [rec[0] for rec in active_records],
                    new_recent_lines,
                    strict=True,
                )
            return True
        except Exception:
            return False

    def clear_recent_paths(self):
        """清除最近使用数据库列表(保留上次连接路径与锁定记录)。

        读取 security.st,保留首行(上次连接路径)与所有有效锁定记录,
        清空 [RECENT] 区段。写入时若 recent_lines 为空,_rewrite 不会
        追加 [RECENT] 标记行,符合现有格式约定。
        """
        try:
            with self._exclusive_state():
                lines = self._read_lines(strict=True)
                last_connected_db = lines[0] if lines else ""
                active_records = self._parse_lock_records(
                    lines,
                    strict=True,
                )
                self._rewrite(
                    last_connected_db,
                    [rec[0] for rec in active_records],
                    [],
                    strict=True,
                )
            return True
        except Exception:
            return False

    # ------------------------------------------------------------------
    # 系统空闲检测(新增)
    # ------------------------------------------------------------------

    def get_idle_seconds(self) -> float:
        """获取系统空闲时长(秒)。

        通过 Win32 user32.GetLastInputInfo 获取系统级最后输入时间
        (能感知本应用外的鼠标/键盘活动,比 Qt 事件过滤更准确),
        与 kernel32.GetTickCount64 配合计算空闲秒数。

        实现说明:
            - dwTime(32 位)与 GetTickCount 同源(均自系统启动计毫秒),
              在系统运行约 49.7 天后回绕。
            - GetTickCount64(64 位)不回绕,取其低 32 位与 dwTime
              做模 2^32 减法,正确处理回绕场景。
            - core 层不依赖 QTimer(避免 import PySide6)。
              UI 层(MainWindow)用 QTimer 每秒轮询本方法,
              判断 idle >= timeout_min * 60 则触发锁定回调。

        Returns:
            float: 空闲秒数(非负)。API 调用失败时返回 0.0
                   (视为「刚有输入」,避免误触发锁定)。
        """
        try:
            info = _LASTINPUTINFO()
            info.cbSize = ctypes.sizeof(info)
            if not ctypes.windll.user32.GetLastInputInfo(ctypes.byref(info)):
                return 0.0
            now_ms = ctypes.windll.kernel32.GetTickCount64()
            # 取低 32 位与 dwTime 同尺度,模 2^32 减法处理 32 位回绕
            idle_ms = (now_ms - info.dwTime) & 0xFFFFFFFF
            return idle_ms / 1000.0
        except Exception:
            return 0.0

    # ------------------------------------------------------------------
    # 强制清理(新增)
    # ------------------------------------------------------------------

    def force_cleanup(self, cleaners) -> CleanupResult:
        """按顺序执行清理函数列表,每个用 try/except 包裹确保异常不中断。

        顺序敏感性(重要):
            cleaners 按传入顺序执行。调用方负责安排顺序——典型顺序为
            「停 timer → 清 UI 状态 → 清内存明文 → 清空剪贴板 → 清零派生密钥」。
            派生密钥必须最后清零,否则后续清理步骤(如清空内存中已解密的
            明文密码)若需解密验证会因密钥已清零而失败。
            本函数保证:即使某个 cleaner 抛异常,后续 cleaner 仍会执行,
            不会因单个失败跳过剩余清理步骤。

        用法示例:
            result = services.security.force_cleanup([
                stop_totp_timer,
                clear_ui_state,
                clear_memory_data,
                clipboard.force_clear,
                derived_key.zero,
            ])
            if result.failure_count > 0:
                # UI 提示:部分清理步骤失败,建议重启应用
                ...

        Args:
            cleaners: 清理函数列表(list/tuple of Callable,无参数无返回值要求)。

        Returns:
            CleanupResult: 含 success_count / failure_count / failures 详情。
        """
        result = CleanupResult()
        for idx, cleaner in enumerate(cleaners):
            try:
                cleaner()
                result.success_count += 1
            except Exception as e:
                result.failure_count += 1
                result.failures.append({
                    "index": idx,
                    "cleaner": getattr(cleaner, "__name__", repr(cleaner)),
                    "error": str(e),
                })
        return result
