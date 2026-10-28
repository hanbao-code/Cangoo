"""数据库操作的内存、取消及磁盘预算；不限制整个数据库容量。"""

from contextlib import contextmanager
import ctypes
from ctypes import wintypes
import shutil

import sqleet

from core.crypto import ARGON2_MEMORY_COST


_MIB = 1024 * 1024
COPY_CHUNK_BYTES = _MIB
SQLITE_CACHE_KIB = 8192


class _MemoryStatus(ctypes.Structure):
    _fields_ = [
        ("length", wintypes.DWORD), ("load", wintypes.DWORD),
        ("total_physical", ctypes.c_ulonglong), ("available_physical", ctypes.c_ulonglong),
        ("total_commit", ctypes.c_ulonglong), ("available_commit", ctypes.c_ulonglong),
        ("total_virtual", ctypes.c_ulonglong), ("available_virtual", ctypes.c_ulonglong),
        ("available_extended", ctypes.c_ulonglong),
    ]


class DatabaseResourceError(RuntimeError):
    """固定资源错误，不携带数据库路径或内容。"""

    kind = "resource_limit"


class DatabaseSpaceError(DatabaseResourceError):
    kind = "insufficient_space"


class DatabaseOperationCancelled(RuntimeError):
    kind = "cancelled"


def native_resource_failure(error) -> bool:
    # 固定版本驱动的 DataError 仅映射 SQLITE_TOOBIG，包含原生语句长度失败。
    return isinstance(error, (MemoryError, sqleet.DataError))


def check_cancelled(should_cancel=None) -> None:
    if should_cancel is not None and should_cancel() is True:
        raise DatabaseOperationCancelled("数据库操作已取消")


def available_memory() -> int:
    """复用项目现有 Windows 容量探测方式，同时约束提交额度和地址空间。"""
    status = _MemoryStatus()
    status.length = ctypes.sizeof(status)
    kernel32 = ctypes.windll.kernel32
    kernel32.GlobalMemoryStatusEx.argtypes = [ctypes.POINTER(_MemoryStatus)]
    kernel32.GlobalMemoryStatusEx.restype = wintypes.BOOL
    if not kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
        raise DatabaseResourceError("无法确定数据库处理所需内存")
    return min(status.available_physical, status.available_commit, status.available_virtual)


class DatabaseMemoryBudget:
    """流式扫描只计当前行；必须返回集合时累计所有仍被保留的行。"""

    # 覆盖 SQLite/密文、Base64 和 GCM 中间值、最坏四字节 Python 文本及返回对象。
    EXPANSION = 16
    ROW_OVERHEAD = 4096

    def __init__(self, should_cancel=None):
        self.should_cancel = should_cancel
        self.retained = 0
        self.limit = self._current_limit()

    @staticmethod
    def _current_limit() -> int:
        # KDF、固定页缓存及复制缓冲先预留，剩余只占四分之一供并发和界面使用。
        reserve = (ARGON2_MEMORY_COST + SQLITE_CACHE_KIB) * 1024 + 2 * COPY_CHUNK_BYTES
        return max(0, (available_memory() - reserve) // 4)

    @property
    def row_bytes(self) -> int:
        return max(0, (self.limit - self.ROW_OVERHEAD) // self.EXPANSION)

    def charge(self, stored_bytes: int, *, retain: bool = False) -> None:
        required = self.ROW_OVERHEAD + stored_bytes * self.EXPANSION
        self.require(required)
        if retain:
            self.retained += required

    def require(self, required: int) -> None:
        """核对已知原生分配或估算后的行峰值，不提前分配内存。"""
        check_cancelled(self.should_cancel)
        if required > self.limit - self.retained or required > self._current_limit():
            raise DatabaseResourceError("当前可用内存不足以安全处理数据库资料")


def connect_database(path, *, key, uri=False):
    """首次密钥验证前即约束 SQLite 原生记录分配，旧驱动不能静默降级。"""
    budget = DatabaseMemoryBudget()
    budget.require(budget.ROW_OVERHEAD)
    con = None
    try:
        con = sqleet.connect(path, key=key, uri=uri, max_length=min(budget.row_bytes, 2**31 - 1))
        # 产品 SQL 均为固定短语句，数据只通过参数传入。
        con.setlimit(sqleet.SQLITE_LIMIT_SQL_LENGTH, 64 * 1024)
        return con
    except Exception as error:
        if con is not None:
            con.close()
        if native_resource_failure(error):
            raise DatabaseResourceError("当前可用内存不足以安全处理数据库资料") from None
        raise


@contextmanager
def database_operation(con, should_cancel=None):
    """SQLite 扫描和 Python 解密共享取消；离开后不影响提交及恢复。"""
    budget = DatabaseMemoryBudget(should_cancel)
    check_cancelled(should_cancel)
    interrupted = None

    def progress():
        nonlocal interrupted
        try:
            check_cancelled(should_cancel)
            # 结构加载也会累计许多小对象；内存消耗达到本次份额时中断原生扫描。
            if budget._current_limit() < budget.limit * 3 // 4:
                raise DatabaseResourceError("当前可用内存不足以安全处理数据库资料")
            return 0
        except Exception as error:
            interrupted = error
            return 1

    previous_limit = con.setlimit(sqleet.SQLITE_LIMIT_LENGTH,
                                 min(con.getlimit(sqleet.SQLITE_LIMIT_LENGTH), budget.row_bytes))
    con.set_progress_handler(progress, 1000)
    try:
        con.execute(f"PRAGMA cache_size=-{SQLITE_CACHE_KIB}")
        yield budget
        check_cancelled(should_cancel)
    except Exception as error:
        if interrupted is not None:
            raise interrupted from None
        check_cancelled(should_cancel)
        if native_resource_failure(error):
            raise DatabaseResourceError("当前可用内存不足以安全处理数据库资料") from None
        raise
    finally:
        con.set_progress_handler(None, 0)
        con.setlimit(sqleet.SQLITE_LIMIT_LENGTH, previous_limit)


def bounded_rows(con, table: str, columns: str, *, budget: DatabaseMemoryBudget,
                 suffix: str = "", parameters: tuple = (), retain: bool = False):
    """固定 SQL 配合原生记录限制，随后核算保留集合的工作内存。"""
    previous_limit = con.setlimit(sqleet.SQLITE_LIMIT_LENGTH,
                                 min(con.getlimit(sqleet.SQLITE_LIMIT_LENGTH), budget.row_bytes))
    cursor = None
    try:
        cursor = con.execute(f'SELECT {columns} FROM "{table}" {suffix}', parameters)
        for row in cursor:
            size = sum(len(value.encode("utf-8")) if isinstance(value, str)
                       else len(value) if isinstance(value, bytes) else 8 for value in row)
            budget.charge(size, retain=retain)
            yield row
    except Exception as error:
        if native_resource_failure(error):
            raise DatabaseResourceError("当前可用内存不足以安全处理数据库资料") from None
        raise
    finally:
        if cursor is not None:
            cursor.close()
        con.setlimit(sqleet.SQLITE_LIMIT_LENGTH, previous_limit)


def require_copy_space(path, size: int, *, copies: int) -> None:
    # 最小页的日志逐页开销及文件头另留余量；空间变化仍由实际写失败兜底。
    required = size * copies + max(_MIB, size // 32)
    if shutil.disk_usage(path).free < required:
        raise DatabaseSpaceError("磁盘空间不足以保存数据库副本和恢复资料")
