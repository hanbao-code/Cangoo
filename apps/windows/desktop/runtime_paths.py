"""原生宿主唯一可写路径端口及生产部署路径解析。

本模块不切换任何应用入口。正式 WebEngine 入口获批后，只需把这里解析出的
``ProductRuntimePaths`` 显式注入现有 Host → Runtime → Adapter 链；M4 隔离
路径继续实现同一端口，避免复制业务栈。
"""

from __future__ import annotations

import ctypes
import os
import tempfile
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Callable, Protocol, runtime_checkable


PORTABLE_MARKER_NAME = "portable.mode"
PORTABLE_MARKER_CONTENT = "Password Manager portable mode v1\n"
_WINDOWS_RESERVED_NAMES = frozenset({"CON", "PRN", "AUX", "NUL"})


class DeploymentMode(str, Enum):
    INSTALLED = "INSTALLED"
    PORTABLE = "PORTABLE"


class ProductPathError(RuntimeError):
    """生产路径不明确、不安全或无法完成原子准备。"""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@runtime_checkable
class RuntimePaths(Protocol):
    """Host、Runtime 与 Adapter 共享的唯一可写路径能力。"""

    settings_file: Path
    security_file: Path
    database_root: Path

    @property
    def default_database(self) -> Path: ...

    @property
    def database_chooser_directory(self) -> Path: ...

    @property
    def database_name_filter(self) -> str: ...

    @property
    def database_default_suffix(self) -> str: ...

    def database_candidate_syntax_is_safe(self, path: Path) -> bool: ...

    def normalize_database_candidate(self, path: Path) -> Path: ...

    def allows_existing_database(self, path: Path) -> bool: ...

    def allows_new_database(self, path: Path) -> bool: ...

    def allows_recovery_snapshot(self, path: Path) -> bool: ...


def _windows_drive_type(path: Path) -> int:
    """返回 Win32 drive type；2/3 分别代表可移动盘和本地固定盘。"""

    if os.name != "nt":
        return 3
    anchor = path.anchor
    if not anchor:
        return 0
    return int(ctypes.windll.kernel32.GetDriveTypeW(str(anchor)))


def _is_windows_reparse_point(path: Path) -> bool:
    """识别符号链接和 Windows junction（目录联接）/reparse point。"""

    if path.is_symlink():
        return True
    if os.name != "nt":
        return False
    get_attributes = ctypes.windll.kernel32.GetFileAttributesW
    get_attributes.argtypes = (ctypes.c_wchar_p,)
    get_attributes.restype = ctypes.c_uint32
    attributes = int(get_attributes(str(path)))
    if attributes == 0xFFFFFFFF:
        raise ProductPathError("PORTABLE_DATA_ATTRIBUTES_UNAVAILABLE")
    return bool(attributes & 0x00000400)


def _default_roaming_root() -> Path:
    appdata = os.environ.get("APPDATA", "")
    if not appdata:
        raise ProductPathError("INSTALLED_ROAMING_ROOT_UNAVAILABLE")
    return Path(appdata) / "cangoo"


def _default_local_state_root() -> Path:
    """按 OPEN-PATH-001 从当前进程的 LOCALAPPDATA 解析状态根。"""

    local_appdata = os.environ.get("LOCALAPPDATA", "")
    if not local_appdata:
        raise ProductPathError("INSTALLED_LOCAL_STATE_ROOT_UNAVAILABLE")
    return Path(local_appdata) / "cangoo" / "State"


def _canonical(path: Path, *, must_exist: bool) -> Path:
    try:
        return path.resolve(strict=must_exist)
    except (OSError, RuntimeError, ValueError) as exc:
        raise ProductPathError("DATABASE_PATH_UNRESOLVABLE") from exc


def _has_unsafe_windows_syntax(path: Path) -> bool:
    raw = str(path)
    normalized = raw.replace("/", "\\")
    if normalized.startswith(("\\\\", "\\?\\", "\\.\\")):
        return True
    # 盘符后的额外冒号表示 NTFS ADS；无盘符冒号同样不接受。
    colon_positions = [index for index, char in enumerate(raw) if char == ":"]
    if colon_positions not in ([], [1]):
        return True
    for part in path.parts:
        if part in {path.anchor, "", ".", ".."}:
            continue
        trimmed = part.rstrip(" .")
        if trimmed != part or not trimmed:
            return True
        stem = trimmed.split(".", 1)[0].upper()
        if (
            stem in _WINDOWS_RESERVED_NAMES
            or (len(stem) == 4 and stem[:3] in {"COM", "LPT"} and stem[3] in "123456789")
        ):
            return True
    return False


def database_candidate_syntax_is_safe(path: Path) -> bool:
    """不访问磁盘，仅判断候选路径是否含禁用的 Windows 语法。"""

    return not _has_unsafe_windows_syntax(path)


def _is_below(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


class _WindowsGuid(ctypes.Structure):
    """供 ``SHGetKnownFolderPath`` 使用的最小 GUID 表示。"""

    _fields_ = (
        ("Data1", ctypes.c_uint32),
        ("Data2", ctypes.c_uint16),
        ("Data3", ctypes.c_uint16),
        ("Data4", ctypes.c_ubyte * 8),
    )

    @classmethod
    def parse(cls, value: str) -> "_WindowsGuid":
        parsed = uuid.UUID(value)
        return cls(
            parsed.time_low,
            parsed.time_mid,
            parsed.time_hi_version,
            (ctypes.c_ubyte * 8)(*parsed.bytes[8:]),
        )


def _windows_directory() -> Path:
    """从 Win32 获取 Windows 目录，不信任进程环境变量。"""

    if os.name != "nt":
        raise ProductPathError("WINDOWS_DIRECTORY_UNAVAILABLE")
    get_directory = ctypes.windll.kernel32.GetWindowsDirectoryW
    get_directory.argtypes = (ctypes.c_wchar_p, ctypes.c_uint32)
    get_directory.restype = ctypes.c_uint32
    size = 260
    while size <= 32768:
        buffer = ctypes.create_unicode_buffer(size)
        length = int(get_directory(buffer, size))
        if length == 0:
            break
        if length < size:
            return _canonical(Path(buffer.value), must_exist=True)
        size = length + 1
    raise ProductPathError("WINDOWS_DIRECTORY_UNAVAILABLE")


def _known_folder(folder_id: str) -> Path:
    """从 Windows Known Folder API 获取受保护目录。"""

    if os.name != "nt":
        raise ProductPathError("WINDOWS_KNOWN_FOLDER_UNAVAILABLE")
    get_folder = ctypes.windll.shell32.SHGetKnownFolderPath
    get_folder.argtypes = (
        ctypes.POINTER(_WindowsGuid),
        ctypes.c_uint32,
        ctypes.c_void_p,
        ctypes.POINTER(ctypes.c_wchar_p),
    )
    get_folder.restype = ctypes.c_long
    free_memory = ctypes.windll.ole32.CoTaskMemFree
    free_memory.argtypes = (ctypes.c_void_p,)
    free_memory.restype = None
    guid = _WindowsGuid.parse(folder_id)
    raw_path = ctypes.c_wchar_p()
    result = int(get_folder(ctypes.byref(guid), 0, None, ctypes.byref(raw_path)))
    if result != 0 or not raw_path.value:
        raise ProductPathError("WINDOWS_KNOWN_FOLDER_UNAVAILABLE")
    try:
        return _canonical(Path(raw_path.value), must_exist=True)
    finally:
        free_memory(ctypes.cast(raw_path, ctypes.c_void_p))


def _protected_roots() -> tuple[Path, ...]:
    roots: list[Path] = []
    if os.name == "nt":
        # 这些路径决定“不得建库”的安全边界，必须来自系统权威接口。
        # 任一接口失败都会使本次候选失败关闭，不能退回可伪造的环境变量。
        roots.extend(
            (
                _windows_directory(),
                _known_folder("905e63b6-c1bf-494e-b29c-65b732d3d21a"),
                _known_folder("7c5a40ef-a0fb-4bfc-874a-c0f2e0b9fa8e"),
                _known_folder("62ab5d82-fdc1-4dc3-a9dd-070d1d495d97"),
            )
        )
    # 环境变量只会增加保护范围，绝不代替上面的权威目录。
    for name in ("WINDIR", "ProgramFiles", "ProgramFiles(x86)", "ProgramData"):
        value = os.environ.get(name, "")
        if not value:
            continue
        try:
            roots.append(Path(value).resolve(strict=False))
        except (OSError, RuntimeError, ValueError):
            continue
    return tuple(dict.fromkeys(roots))


def _publish_without_overwrite(staged: Path, target: Path) -> None:
    """同目录发布且绝不覆盖竞态目标。"""

    if os.name == "nt":
        os.rename(staged, target)
        return
    # 非 Windows 只用于开发验证；硬链接提供与 Windows rename 相同的
    # no-replace 语义，随后移除暂存目录项。
    os.link(staged, target)
    staged.unlink()


@dataclass(frozen=True, slots=True)
class ProductRuntimePaths:
    """安装版或便携版的生产路径值对象。"""

    mode: DeploymentMode
    executable_dir: Path
    settings_file: Path
    security_file: Path
    database_root: Path
    legacy_security_file: Path
    _drive_type: Callable[[Path], int] = field(
        default=_windows_drive_type,
        repr=False,
        compare=False,
    )
    _directory_writable: Callable[[Path], bool] = field(
        default=lambda path: os.access(path, os.R_OK | os.W_OK),
        repr=False,
        compare=False,
    )

    @classmethod
    def resolve(
        cls,
        executable_dir: Path,
        *,
        roaming_root: Path | None = None,
        local_state_root: Path | None = None,
        drive_type: Callable[[Path], int] = _windows_drive_type,
        directory_writable: Callable[[Path], bool] = (
            lambda path: os.access(path, os.R_OK | os.W_OK)
        ),
    ) -> "ProductRuntimePaths":
        executable_dir = _canonical(executable_dir, must_exist=True)
        if not executable_dir.is_dir():
            raise ProductPathError("EXECUTABLE_DIRECTORY_INVALID")
        marker = executable_dir / PORTABLE_MARKER_NAME
        data_root = executable_dir / "data"
        if os.path.lexists(data_root) and _is_windows_reparse_point(
            data_root
        ):
            raise ProductPathError("PORTABLE_DATA_DIRECTORY_REDIRECTED")
        if marker.exists():
            if (
                not marker.is_file()
                or _is_windows_reparse_point(marker)
            ):
                raise ProductPathError("PORTABLE_MARKER_INVALID")
            try:
                marker_content = marker.read_bytes()
            except (OSError, UnicodeError) as exc:
                raise ProductPathError("PORTABLE_MARKER_UNREADABLE") from exc
            if marker_content != PORTABLE_MARKER_CONTENT.encode("ascii"):
                raise ProductPathError("PORTABLE_MARKER_INVALID")
            mode = DeploymentMode.PORTABLE
            settings_file = data_root / "settings.json"
            security_file = data_root / "security.st"
            database_root = data_root
        else:
            try:
                # 便携版允许用户选择任意后缀或无后缀数据库，因此这里不能
                # 仅识别几个固定文件名。只要 data 目录非空，就说明存在可能
                # 属于便携模式的状态；缺少精确标记时必须失败关闭。
                portable_state_detected = data_root.is_dir() and any(
                    data_root.iterdir()
                )
            except OSError as exc:
                raise ProductPathError("PORTABLE_STATE_UNREADABLE") from exc
            if portable_state_detected:
                raise ProductPathError("PORTABLE_MARKER_MISSING_WITH_STATE")
            mode = DeploymentMode.INSTALLED
            roaming = _canonical(
                roaming_root if roaming_root is not None else _default_roaming_root(),
                must_exist=False,
            )
            local_state = _canonical(
                (
                    local_state_root
                    if local_state_root is not None
                    else _default_local_state_root()
                ),
                must_exist=False,
            )
            settings_file = roaming / "settings.json"
            security_file = local_state / "security.st"
            database_root = roaming
        return cls(
            mode=mode,
            executable_dir=executable_dir,
            settings_file=settings_file,
            security_file=security_file,
            database_root=database_root,
            legacy_security_file=executable_dir / "security.st",
            _drive_type=drive_type,
            _directory_writable=directory_writable,
        )

    @property
    def default_database(self) -> Path:
        return self.database_root / "pdm.db"

    @property
    def database_chooser_directory(self) -> Path:
        return self.database_root

    @property
    def database_name_filter(self) -> str:
        return "Password database (*.db);;All files (*)"

    @property
    def database_default_suffix(self) -> str:
        # 生产模式必须先保留用户选择的已有无后缀路径；仅在返回原始路径后，
        # normalize_database_candidate 才会为“不存在且无后缀”补 .db。
        return ""

    def database_candidate_syntax_is_safe(self, path: Path) -> bool:
        return database_candidate_syntax_is_safe(path)

    def prepare(self) -> str:
        """准备本模式目录并迁移旧 security.st；不创建数据库。"""

        if self.mode is DeploymentMode.PORTABLE:
            try:
                self.database_root.mkdir(parents=True, exist_ok=True)
                resolved_data = self.database_root.resolve(strict=True)
            except (OSError, RuntimeError, ValueError) as exc:
                raise ProductPathError(
                    "PORTABLE_DATA_DIRECTORY_INVALID"
                ) from exc
            if (
                _is_windows_reparse_point(self.database_root)
                or resolved_data.parent != self.executable_dir
                or resolved_data.name != "data"
            ):
                raise ProductPathError(
                    "PORTABLE_DATA_DIRECTORY_REDIRECTED"
                )
        for directory in {
            self.settings_file.parent,
            self.security_file.parent,
            self.database_root,
        }:
            try:
                directory.mkdir(parents=True, exist_ok=True)
            except OSError as exc:
                raise ProductPathError("RUNTIME_DIRECTORY_CREATE_FAILED") from exc
            if not directory.is_dir():
                raise ProductPathError("RUNTIME_DIRECTORY_INVALID")
            if not self._directory_writable(directory):
                raise ProductPathError("RUNTIME_DIRECTORY_NOT_WRITABLE")
        return self._migrate_legacy_security_state()

    def _migrate_legacy_security_state(self) -> str:
        target = self.security_file
        source = self.legacy_security_file
        if target.exists():
            if (
                not target.is_file()
                or _is_windows_reparse_point(target)
            ):
                raise ProductPathError("SECURITY_TARGET_INVALID")
            if source.exists():
                try:
                    if os.path.samefile(source, target):
                        raise ProductPathError(
                            "SECURITY_TARGET_ALIASES_LEGACY_SOURCE"
                        )
                except OSError as exc:
                    raise ProductPathError(
                        "SECURITY_STATE_IDENTITY_UNAVAILABLE"
                    ) from exc
            return "TARGET_PRESERVED"
        if not source.exists():
            return "NO_LEGACY_STATE"
        if (
            not source.is_file()
            or _is_windows_reparse_point(source)
        ):
            raise ProductPathError("LEGACY_SECURITY_SOURCE_INVALID")
        try:
            payload = source.read_bytes()
        except OSError as exc:
            raise ProductPathError("LEGACY_SECURITY_READ_FAILED") from exc
        staged: Path | None = None
        published_identity: tuple[int, int] | None = None
        try:
            fd, name = tempfile.mkstemp(
                prefix=".security.st.",
                suffix=".migrate",
                dir=str(target.parent),
            )
            staged = Path(name)
            with os.fdopen(fd, "wb") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            if staged.read_bytes() != payload:
                raise ProductPathError("SECURITY_MIGRATION_READBACK_FAILED")
            _publish_without_overwrite(staged, target)
            staged = None
            published_stat = target.stat()
            published_identity = (
                int(published_stat.st_dev),
                int(published_stat.st_ino),
            )
            if target.read_bytes() != payload:
                raise ProductPathError("SECURITY_MIGRATION_FINAL_VERIFY_FAILED")
            if source.read_bytes() != payload:
                raise ProductPathError("LEGACY_SECURITY_SOURCE_CHANGED")
            return "MIGRATED_SOURCE_PRESERVED"
        except FileExistsError as exc:
            raise ProductPathError("SECURITY_MIGRATION_TARGET_RACE") from exc
        except (ProductPathError, OSError) as exc:
            if published_identity is not None:
                try:
                    current = target.stat()
                    current_identity = (
                        int(current.st_dev),
                        int(current.st_ino),
                    )
                    if current_identity != published_identity:
                        raise ProductPathError(
                            "SECURITY_MIGRATION_TARGET_REPLACED"
                        )
                    target.unlink()
                except FileNotFoundError:
                    pass
                except ProductPathError:
                    raise
                except OSError as rollback_exc:
                    raise ProductPathError(
                        "SECURITY_MIGRATION_ROLLBACK_FAILED"
                    ) from rollback_exc
            if isinstance(exc, ProductPathError):
                raise
            raise ProductPathError("SECURITY_MIGRATION_FAILED") from exc
        finally:
            if staged is not None:
                try:
                    staged.unlink(missing_ok=True)
                except OSError:
                    pass

    def normalize_database_candidate(self, path: Path) -> Path:
        if not self.database_candidate_syntax_is_safe(path):
            raise ProductPathError("DATABASE_PATH_SYNTAX_FORBIDDEN")
        candidate = _canonical(path, must_exist=False)
        if candidate.exists() or candidate.suffix:
            return candidate
        return candidate.with_suffix(".db")

    def _safe_database_location(self, path: Path, *, existing: bool) -> bool:
        if not isinstance(path, Path) or _has_unsafe_windows_syntax(path):
            return False
        try:
            candidate = _canonical(path, must_exist=existing)
            parent = candidate.parent.resolve(strict=True)
        except (ProductPathError, OSError, RuntimeError, ValueError):
            return False
        try:
            if any(_is_below(candidate, root) for root in _protected_roots()):
                return False
        except ProductPathError:
            return False
        try:
            drive_type = int(self._drive_type(candidate))
        except Exception:
            return False
        if drive_type not in {2, 3}:
            return False
        if not self._directory_writable(parent):
            return False
        return True

    def allows_existing_database(self, path: Path) -> bool:
        if (
            not isinstance(path, Path)
            or not self.database_candidate_syntax_is_safe(path)
        ):
            return False
        try:
            return (
                path.is_file()
                and self._safe_database_location(path, existing=True)
            )
        except OSError:
            return False

    def allows_new_database(self, path: Path) -> bool:
        if (
            not isinstance(path, Path)
            or not self.database_candidate_syntax_is_safe(path)
        ):
            return False
        try:
            return (
                not path.exists()
                and path.suffix.lower() == ".db"
                and self._safe_database_location(path, existing=False)
            )
        except OSError:
            return False

    def allows_recovery_snapshot(self, path: Path) -> bool:
        """改密恢复快照必须是当前数据库同目录的普通安全路径。"""

        return self.allows_existing_database(path)


__all__ = [
    "DeploymentMode",
    "PORTABLE_MARKER_CONTENT",
    "PORTABLE_MARKER_NAME",
    "ProductPathError",
    "ProductRuntimePaths",
    "RuntimePaths",
    "database_candidate_syntax_is_safe",
]
