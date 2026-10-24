# -*- coding: utf-8 -*-
"""
core/database.py — 密码管理器核心数据服务层（T1 扩展版）

本模块从早期界面实现中剥离出全部数据库业务逻辑，
封装为纯 Python 的 DatabaseService 类，不依赖任何 UI 框架（PyQt5/PySide6）。

职责范围：
    - 加密数据库（sqleet）连接与断开 + 新建数据库（决策 D1）
    - Argon2id 密钥派生 + SecureKeyBuffer 安全内存管理
    - 密码记录 CRUD（TTable，按 id 操作）
    - 加密记事本 CRUD（NotesTable，按 id 操作）
    - 重复组检测（get_duplicate_groups，按密码明文分组）
    - 当前密码验证（verify_current_password，决策 D5）
    - 数据导入导出（JSON 结构）
    - 数据库密码修改（全量重加密 + change_key，含 totp_secret 字段）

数据表结构（T1 实现后）：
    TTable    (ID, platform UNIQUE, account, password, notes,
               totp_secret, strength, password_changed_at, updated_at,
               is_favorite)
    NotesTable(ID, title, content, created_at, updated_at, sort_order, is_favorite)
    _meta     (key PRIMARY KEY, value)  — 元数据（盐值）

双层加密结构：
    - 文件级：sqleet 对整个 .db 文件加密（用户密码为密钥）
    - 字段级：AES-256-GCM 对敏感字段加密（派生密钥从 Argon2id 派生）

加密字段清单（共 8 个字段加密）：
    - TTable:    account / password / notes / totp_secret
    - NotesTable: title / content / created_at / updated_at
不加密字段：
    - TTable:    id / platform / strength / password_changed_at / updated_at /
                 is_favorite
    - NotesTable: id / sort_order / is_favorite

password_changed_at 语义：
    - 仅 password 字段值变更时刷新（ISO 8601 时间戳）
    - account / notes / title 等其他字段变更不刷新
    - 用于安全体检的"长期未更换"判定

updated_at 语义：
    - platform / account / password / notes / totp_secret 实际变化时刷新
    - 与 password_changed_at 独立，用于最近更新排序和详情
    - 单独收藏变化当前保持原值，等待 OPEN-DATA-001 的正式裁决

错误处理约定：
    - 所有数据库操作均 try/except，异常信息写入 self.last_error
    - 调用方可通过 error 属性获取最近一次错误信息
    - 本模块不弹窗、不依赖 i18n、不依赖任何 UI 组件
"""

import base64
import datetime
import hashlib
import hmac
import os
import re
import shutil
import tempfile
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Callable

import sqleet

from core.backup import (
    BACKUP_PAYLOAD_TYPE,
    BACKUP_PAYLOAD_VERSION,
    BackupError,
    backup_identical_note_targets,
    backup_note_groups,
    backup_password_content,
    similar_name_key,
    validate_backup_payload,
)
from core.crypto import CryptoHelper, SecureKeyBuffer
from core.password_tools import PasswordTools
from core.recovery_codes import RecoveryCodeError, dump_codes, load_codes, validate_codes


PasswordStrengthEvaluator = Callable[[str, str, str], str]


class StrengthEvaluationCancelled(Exception):
    """密码强度计算在数据库提交前被调用方取消。"""


class StrengthEvaluationError(Exception):
    """密码强度计算失败或返回了非法等级。"""


@dataclass(repr=False)
class PasswordStrengthSnapshot:
    """单条体检输入；加密源列仅用于原子核对，不暴露到界面。"""

    record_id: int
    platform: str
    account: str
    password: str
    source: tuple
    strength: str | None = None

    def clear(self) -> None:
        self.platform = self.account = self.password = ""
        self.source = ()
        self.strength = None


class CurrentPasswordStatus(str, Enum):
    """Structured current-password verification result for native callers."""

    MATCH = "MATCH"
    MISMATCH = "MISMATCH"
    ERROR = "ERROR"


class ChangeKeyStatus(str, Enum):
    """Verified terminal database state after an atomic key change attempt."""

    SUCCESS = "SUCCESS"
    UNCHANGED = "UNCHANGED"
    RESTORED = "RESTORED"
    RECOVERY_FAILED = "RECOVERY_FAILED"
    CANCELLED = "CANCELLED"


class ChangeKeyProgressPhase(str, Enum):
    """Fixed public progress phases compatible with Bridge OperationPhase."""

    READING = "READING"
    VALIDATING = "VALIDATING"
    DERIVING_KEY = "DERIVING_KEY"
    ENCRYPTING = "ENCRYPTING"
    COMMITTING = "COMMITTING"
    WRITING = "WRITING"
    RESTORING = "RESTORING"
    FINALIZING = "FINALIZING"


@dataclass(frozen=True)
class ChangeKeyResult:
    """Native-only structured result; recovery paths stay out of ``repr``."""

    status: ChangeKeyStatus
    recovery_snapshot_path: str | None = field(default=None, repr=False)

    def __bool__(self) -> bool:
        return self.status is ChangeKeyStatus.SUCCESS


class _ChangeKeyCancelled(Exception):
    """Internal control-flow marker; never crosses the core API boundary."""


class _BackupConflictChanged(Exception):
    """目标库的精确冲突集合已不再匹配预览。"""


class _BackupDecisionInvalid(Exception):
    """调用方未裁决全部当前精确名称冲突。"""


class DatabaseService:
    """密码管理器核心数据服务（无 UI 依赖）"""

    # ------------------------------------------------------------------
    # 构造与状态
    # ------------------------------------------------------------------

    def __init__(self):
        """初始化状态变量，不在此处连接数据库"""
        self.db_name = None          # 数据库文件路径
        self.db_key = None           # 数据库密码（sqleet 层密钥，str）
        self.derived_key = None      # SecureKeyBuffer，字段加密派生密钥
        self.last_error = None       # 最近一次错误信息
        self.last_error_kind = None  # 供 UI 安全分流的稳定错误类别
        # 原生宿主用于把会话绑定到核心实际打开/发布的文件对象；不传网页层。
        self.opened_file_identity = None
        self.migration_snapshot_path = None

    @property
    def error(self):
        """返回最近一次错误信息（无错误时为 None）"""
        return self.last_error

    @property
    def error_kind(self):
        """返回稳定错误类别，避免 UI 解析本地化/第三方异常文本。"""
        return self.last_error_kind

    @staticmethod
    def _classify_connection_error(exc) -> str:
        text = str(exc).lower()
        if any(
            marker in text
            for marker in (
                "passed key is incorrect",
                "returned null without setting an exception",
            )
        ):
            return "invalid_password"
        if isinstance(exc, PermissionError) or any(
            marker in text
            for marker in ("permission denied", "access is denied", "readonly", "read-only")
        ):
            return "permission_denied"
        if isinstance(exc, FileNotFoundError):
            return "path_not_found"
        if isinstance(exc, IsADirectoryError):
            return "invalid_path"
        return "corrupt_or_unreadable"

    def is_connected(self) -> bool:
        """是否已成功连接数据库（以派生密钥缓冲区是否存在为准）"""
        return self.derived_key is not None

    @staticmethod
    def _path_identity(path: Path) -> tuple[int, int, int, int]:
        value = path.stat()
        if not path.is_file():
            raise RuntimeError("database path is not a regular file")
        return (
            int(value.st_dev),
            int(value.st_ino),
            int(value.st_size),
            int(value.st_ctime_ns),
        )

    @staticmethod
    def _same_file_identity(
        expected: tuple[int, int, int, int],
        current: tuple[int, int, int, int],
    ) -> bool:
        expected_device, expected_inode, _size, expected_created = expected
        current_device, current_inode, _size, current_created = current
        if expected_inode != 0 or current_inode != 0:
            return (
                expected_device == current_device
                and expected_inode == current_inode
            )
        return (
            expected_device == current_device
            and expected_created == current_created
        )

    # ------------------------------------------------------------------
    # 连接管理
    # ------------------------------------------------------------------

    def connect(self, db_path: str, password: str) -> bool:
        """兼容入口：按目标是否存在严格分流为打开或新建。

        新代码应优先调用 :meth:`open_existing` 或
        :meth:`create_database`，避免把用户输入的路径意图混在一起。
        """
        if db_path and os.path.exists(db_path):
            return self.open_existing(db_path, password)
        return self.create_database(db_path, password)

    def open_existing(
        self,
        db_path: str,
        password: str,
        *,
        pre_write_guard: Callable[[], bool] | None = None,
    ) -> bool:
        """只打开已有产品数据库，不创建文件且不在识别前写入。

        文件名后缀不是数据库身份。连接首先使用 SQLite URI 的
        ``mode=rw``，随后只读检查历史稳定的产品表结构；只有确认属于
        本产品后，才在事务中补齐表、字段和盐值。
        """
        self.last_error = None
        self.last_error_kind = None
        self.opened_file_identity = None
        self.migration_snapshot_path = None
        if not db_path:
            self.last_error = "数据库路径不能为空"
            self.last_error_kind = "path_empty"
            return False
        if password is None:
            self.last_error = "数据库密码缺失"
            self.last_error_kind = "password_missing"
            return False
        if pre_write_guard is not None and not callable(pre_write_guard):
            self.last_error = "数据库写前身份守卫无效"
            self.last_error_kind = "invalid_path"
            return False
        if not os.path.exists(db_path):
            self.last_error = "数据库文件不存在"
            self.last_error_kind = "path_not_found"
            return False
        # sqleet 对“错误密钥”和某些截断/随机文件可能返回同一句
        # ``Passed key is incorrect``。在不接触密钥的前提下先识别可确定的
        # 文件形态错误，避免把明显损坏误计为密码尝试。SQLite 最小页为
        # 512 字节；正常 sqleet 数据库不会小于一页。
        if not os.path.isfile(db_path):
            self.last_error = "数据库路径不是文件"
            self.last_error_kind = "invalid_path"
            return False
        try:
            if os.path.getsize(db_path) < 512:
                self.last_error = "数据库文件过小或已截断"
                self.last_error_kind = "corrupt_or_unreadable"
                return False
        except OSError as exc:
            self.last_error = f"无法读取数据库文件信息: {exc}"
            self.last_error_kind = self._classify_connection_error(exc)
            return False
        inspection = None
        con = None
        pending_key = None
        try:
            resolved = Path(db_path).resolve(strict=True)
            initial_identity = self._path_identity(resolved)

            def require_initial_identity() -> None:
                current_identity = self._path_identity(resolved)
                if not self._same_file_identity(
                    initial_identity,
                    current_identity,
                ):
                    raise RuntimeError(
                        "database identity changed during open"
                    )

            read_only_uri = resolved.as_uri() + "?mode=ro"
            inspection = sqleet.connect(
                read_only_uri,
                key=password,
                uri=True,
            )
            inspection.execute("PRAGMA query_only=ON")
            raw_key, needs_migration = self._inspect_product_schema(
                inspection,
                password,
            )
            require_initial_identity()
            inspection.close()
            inspection = None

            uri = resolved.as_uri() + "?mode=rw"
            con = sqleet.connect(uri, key=password, uri=True)
            require_initial_identity()
            con.execute("PRAGMA query_only=ON")
            try:
                verified_key, verified_needs_migration = (
                    self._inspect_product_schema(con, password)
                )
                if (
                    not hmac.compare_digest(raw_key, verified_key)
                    or needs_migration != verified_needs_migration
                ):
                    raise RuntimeError("database identity changed during open")
                pending_key = SecureKeyBuffer(raw_key)
                if needs_migration:
                    require_initial_identity()
                    if (
                        pre_write_guard is not None
                        and pre_write_guard() is not True
                    ):
                        raise RuntimeError(
                            "database identity changed before migration"
                        )
                    con.execute("PRAGMA query_only=OFF")
                    con.execute("BEGIN IMMEDIATE")
                    locked_key, locked_needs_migration = self._inspect_product_schema(con, password)
                    if (
                        not hmac.compare_digest(raw_key, locked_key)
                        or needs_migration != locked_needs_migration
                    ):
                        raise RuntimeError("database changed before migration")
                    if "recovery_codes" not in self._table_columns(con, "TTable"):
                        if con.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal":
                            raise RuntimeError("WAL database cannot be copied as one file")
                        snapshot_path, snapshot_hash = self._create_change_key_snapshot(
                            str(resolved), purpose="before-recovery-codes",
                        )
                        snapshot_con = None
                        try:
                            snapshot_con = sqleet.connect(
                                Path(snapshot_path).as_uri() + "?mode=ro", key=password, uri=True,
                            )
                            snapshot_key, snapshot_needs_migration = self._inspect_product_schema(
                                snapshot_con, password,
                            )
                            if (
                                not hmac.compare_digest(raw_key, snapshot_key)
                                or snapshot_needs_migration != needs_migration
                            ):
                                raise RuntimeError("upgrade snapshot verification failed")
                        except Exception:
                            if snapshot_con is not None:
                                snapshot_con.close()
                                snapshot_con = None
                            os.remove(snapshot_path)
                            raise
                        finally:
                            if snapshot_con is not None:
                                snapshot_con.close()
                        require_initial_identity()
                        if not hmac.compare_digest(
                            snapshot_hash, self._change_key_file_sha256(str(resolved)),
                        ):
                            raise RuntimeError("database changed during upgrade snapshot")
                        self.migration_snapshot_path = snapshot_path
                    self._prepare_product_schema(con)
                    current_key, still_needs_migration = (
                        self._inspect_product_schema(con, password)
                    )
                    if (
                        still_needs_migration
                        or not hmac.compare_digest(raw_key, current_key)
                    ):
                        raise RuntimeError("database migration verification failed")
                    if (
                        pre_write_guard is not None
                        and pre_write_guard() is not True
                    ):
                        raise RuntimeError(
                            "database identity changed during migration"
                        )
                    require_initial_identity()
                    con.commit()
                require_initial_identity()
                opened_identity = initial_identity
                self._adopt_session(
                    str(resolved),
                    password,
                    pending_key,
                )
                self.opened_file_identity = opened_identity
                pending_key = None
                return True
            except Exception:
                try:
                    con.rollback()
                except Exception:
                    pass
                raise
            finally:
                con.close()
        except Exception as e:
            self.last_error = f"连接数据库失败: {e}"
            if self.last_error_kind is None:
                self.last_error_kind = self._classify_connection_error(e)
            return False
        finally:
            if inspection is not None:
                try:
                    inspection.close()
                except Exception:
                    pass
            if pending_key is not None:
                try:
                    pending_key.destroy()
                except Exception:
                    pass

    @staticmethod
    def _table_columns(con, table: str) -> dict[str, tuple]:
        return {
            str(row[1]).lower(): tuple(row)
            for row in con.execute(
                f'PRAGMA table_xinfo("{table}")'
            ).fetchall()
        }

    @staticmethod
    def _column_signature(row: tuple) -> tuple[str, int, str | None, int, int]:
        if len(row) < 7:
            raise RuntimeError("unsupported product column metadata")
        default = None if row[4] is None else str(row[4]).strip()
        return (
            str(row[2]).strip().upper(),
            int(row[3]),
            default,
            int(row[5]),
            int(row[6]),
        )

    @staticmethod
    def _index_signatures(con, table: str) -> set[tuple]:
        signatures = set()
        for row in con.execute(f'PRAGMA index_list("{table}")').fetchall():
            if len(row) < 5:
                raise RuntimeError("unsupported product index metadata")
            columns = tuple(
                str(value[2]).lower()
                for value in con.execute(
                    f'PRAGMA index_info("{row[1]}")'
                ).fetchall()
            )
            signatures.add(
                (
                    int(row[2]),
                    str(row[3]).lower(),
                    int(row[4]),
                    columns,
                )
            )
        return signatures

    @classmethod
    def _inspect_product_schema(
        cls,
        con,
        password: str,
    ) -> tuple[bytes, bool]:
        """只读认证已知 Argon2id 产品结构，返回密钥和迁移需求。"""

        quick_check = con.execute("PRAGMA quick_check").fetchone()
        if quick_check != ("ok",):
            raise RuntimeError("database integrity check failed")
        object_rows = con.execute(
            "SELECT type, name, sql FROM sqlite_master"
        ).fetchall()
        if any(
            str(kind).lower() in {"view", "trigger"}
            for kind, name, _sql in object_rows
            if not str(name).lower().startswith("sqlite_")
        ):
            raise RuntimeError("unsupported product schema object")
        if any(
            str(kind).lower() == "index"
            and not str(name).lower().startswith("sqlite_autoindex_")
            for kind, name, _sql in object_rows
        ):
            raise RuntimeError("unsupported product index")
        table_sql = {
            str(name).lower(): str(sql or "")
            for kind, name, sql in object_rows
            if str(kind).lower() == "table"
        }
        rows = con.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        tables = {
            str(row[0]).lower()
            for row in rows
            if not str(row[0]).lower().startswith("sqlite_")
        }
        if tables != {"ttable", "notestable", "_meta"}:
            raise RuntimeError("unsupported product table set")

        nullable_text = ("TEXT", 0, None, 0, 0)
        password_specs = {
            "id": ("INTEGER", 0, None, 1, 0),
            "platform": ("TEXT", 1, None, 0, 0),
            "account": nullable_text,
            "password": nullable_text,
            "notes": nullable_text,
            "totp_secret": nullable_text,
            "recovery_codes": nullable_text,
            "strength": nullable_text,
            "password_changed_at": nullable_text,
            "updated_at": nullable_text,
            "is_favorite": ("INTEGER", 1, "0", 0, 0),
        }
        note_specs = {
            "id": ("INTEGER", 0, None, 1, 0),
            "title": nullable_text,
            "content": nullable_text,
            "created_at": nullable_text,
            "updated_at": nullable_text,
            "sort_order": ("INTEGER", 0, "0", 0, 0),
            "is_favorite": ("INTEGER", 1, "0", 0, 0),
        }
        meta_specs = {
            "key": ("TEXT", 0, None, 1, 0),
            "value": nullable_text,
        }
        password_base = {"id", "platform", "account", "password", "notes"}
        note_base = {
            "id",
            "title",
            "content",
            "created_at",
            "updated_at",
            "sort_order",
        }
        schema_stages = (
            (password_base, note_base),
            (
                password_base | {"is_favorite"},
                note_base | {"is_favorite"},
            ),
            (
                password_base
                | {
                    "is_favorite",
                    "totp_secret",
                    "strength",
                    "password_changed_at",
                },
                note_base | {"is_favorite"},
            ),
            (
                password_base
                | {
                    "is_favorite",
                    "totp_secret",
                    "strength",
                    "password_changed_at",
                    "updated_at",
                },
                note_base | {"is_favorite"},
            ),
        )
        schema_stages += ((
            schema_stages[-1][0] | {"recovery_codes"}, schema_stages[-1][1],
        ),)
        password_columns = cls._table_columns(con, "TTable")
        note_columns = cls._table_columns(con, "NotesTable")
        meta_columns = cls._table_columns(con, "_meta")
        stage = (
            set(password_columns),
            set(note_columns),
        )
        if stage not in schema_stages or set(meta_columns) != {"key", "value"}:
            raise RuntimeError("unsupported product column set")
        for columns, specifications in (
            (password_columns, password_specs),
            (note_columns, note_specs),
            (meta_columns, meta_specs),
        ):
            for name, row in columns.items():
                if cls._column_signature(row) != specifications[name]:
                    raise RuntimeError(
                        f"unsupported product column definition: {name}"
                    )
        for table in ("ttable", "notestable"):
            normalized_sql = " ".join(
                table_sql.get(table, "").lower().split()
            )
            if not re.search(
                r"\bid\s+integer\s+primary\s+key\s+autoincrement\b",
                normalized_sql,
            ):
                raise RuntimeError("unsupported product row identity")
            if (
                re.search(
                    r"\b(check|references|collate|generated|constraint|strict)\b",
                    normalized_sql,
                )
                or "without rowid" in normalized_sql
                or "on conflict" in normalized_sql
            ):
                raise RuntimeError("unsupported product table semantics")
            if con.execute(
                f'PRAGMA foreign_key_list("{table}")'
            ).fetchall():
                raise RuntimeError("unsupported product foreign key")
        meta_sql = " ".join(table_sql.get("_meta", "").lower().split())
        if (
            re.search(
                r"\b(check|references|collate|generated|constraint|strict)\b",
                meta_sql,
            )
            or "without rowid" in meta_sql
            or "on conflict" in meta_sql
        ):
            raise RuntimeError("unsupported product metadata semantics")
        if cls._index_signatures(con, "TTable") != {
            (1, "u", 0, ("platform",))
        }:
            raise RuntimeError("unsupported platform uniqueness")
        if cls._index_signatures(con, "NotesTable"):
            raise RuntimeError("unsupported notes indexes")
        if cls._index_signatures(con, "_meta") != {
            (1, "pk", 0, ("key",))
        }:
            raise RuntimeError("unsupported metadata key")

        salt_row = con.execute(
            "SELECT value FROM _meta WHERE key='salt'"
        ).fetchone()
        if con.execute("SELECT key FROM _meta").fetchall() != [("salt",)]:
            raise RuntimeError("unsupported product metadata set")
        if (
            salt_row is None
            or len(salt_row) != 1
            or not isinstance(salt_row[0], str)
        ):
            raise RuntimeError("missing product salt")
        try:
            salt = base64.b64decode(salt_row[0], validate=True)
        except Exception as exc:
            raise RuntimeError("invalid product salt") from exc
        if len(salt) != 16:
            raise RuntimeError("invalid product salt length")
        raw_key = CryptoHelper.derive_key(password, salt)

        encrypted_columns = ["account", "password", "notes"]
        if "totp_secret" in password_columns:
            encrypted_columns.append("totp_secret")
        if "recovery_codes" in password_columns:
            encrypted_columns.append("recovery_codes")
        for row in con.execute(
            "SELECT " + ", ".join(encrypted_columns) + " FROM TTable"
        ).fetchall():
            for field_name, value in zip(encrypted_columns, row):
                if value in {None, ""}:
                    continue
                if not isinstance(value, str):
                    raise RuntimeError("invalid password field ciphertext")
                decoded = base64.b64decode(value, validate=True)
                if len(decoded) < 28:
                    raise RuntimeError("invalid password field ciphertext")
                plaintext = CryptoHelper.decrypt_data(value, raw_key)
                if field_name == "recovery_codes":
                    load_codes(plaintext)
                plaintext = ""
        for row in con.execute(
            "SELECT title, content, created_at, updated_at FROM NotesTable"
        ).fetchall():
            for value in row:
                if value in {None, ""}:
                    continue
                if not isinstance(value, str):
                    raise RuntimeError("invalid note field ciphertext")
                decoded = base64.b64decode(value, validate=True)
                if len(decoded) < 28:
                    raise RuntimeError("invalid note field ciphertext")
                CryptoHelper.decrypt_data(value, raw_key)

        return raw_key, stage != schema_stages[-1]

    def _prepare_product_schema(self, con) -> None:
        """在调用方控制的单个事务内迁移已认证产品结构。"""

        self._migrate_is_favorite(con)
        self._migrate_password_fields(con)

    def _adopt_session(
        self,
        db_path: str,
        password: str,
        key_buffer: SecureKeyBuffer,
    ) -> None:
        if self.derived_key is not None:
            try:
                self.derived_key.destroy()
            except Exception:
                pass
        self.derived_key = key_buffer
        self.db_name = db_path
        self.db_key = password

    def _assert_bound_identity(self) -> None:
        expected = self.opened_file_identity
        path_value = self.db_name
        if expected is None or not isinstance(path_value, str):
            self.disconnect()
            self.last_error_kind = "database_identity_changed"
            raise RuntimeError("database session identity unavailable")
        try:
            current = self._path_identity(Path(path_value))
        except Exception as exc:
            self.disconnect()
            self.last_error_kind = "database_identity_changed"
            raise RuntimeError("database session file unavailable") from exc
        if not self._same_file_identity(expected, current):
            self.disconnect()
            self.last_error_kind = "database_identity_changed"
            raise RuntimeError("database session identity changed")

    def bound_identity_is_current(self) -> bool:
        """快速核对当前会话仍绑定到最初打开的同一文件对象。"""

        try:
            self._assert_bound_identity()
            return True
        except Exception:
            return False

    def _connect_bound(self):
        """连接当前会话文件，并在连接建立前后核对文件身份。"""

        path_value = self.db_name
        key_value = self.db_key
        self._assert_bound_identity()
        con = sqleet.connect(path_value, key=key_value)
        try:
            self._assert_bound_identity()
        except Exception:
            con.close()
            raise
        return con

    def _commit_bound(self, con) -> None:
        """提交写事务前后核对身份；失配时关闭会话并失败关闭。"""

        try:
            self._assert_bound_identity()
            con.commit()
            self._assert_bound_identity()
        except Exception:
            try:
                con.rollback()
            except Exception:
                pass
            try:
                con.close()
            except Exception:
                pass
            raise

    def disconnect(self):
        """断开连接：销毁 SecureKeyBuffer，清理敏感状态"""
        if self.derived_key is not None:
            try:
                self.derived_key.destroy()
            except Exception:
                pass
            self.derived_key = None
        self.db_key = None
        self.opened_file_identity = None
        self.migration_snapshot_path = None

    def create_database(self, db_path: str, password: str) -> bool:
        """在指定路径新建加密数据库（决策 D1）

        与 connect() 区别：
            - connect() 按文件存在状态分流到打开或新建
            - create_database() 对已存在文件拒绝（防误覆盖）

        流程：
            ① 检测文件已存在 → last_error="文件已存在"，返回 False
            ② 在目标同目录创建暂存数据库并完成初始化
            ③ 关闭、刷新并重新打开暂存文件验证产品结构
            ④ 以不覆盖已有目标的方式发布；竞态出现时失败关闭
            ⑤ 发布成功后接管会话状态

        成功返回 True；失败返回 False，错误信息写入 self.last_error。
        """
        self.last_error = None
        self.last_error_kind = None
        self.opened_file_identity = None
        self.migration_snapshot_path = None
        if not db_path:
            self.last_error = "数据库路径不能为空"
            self.last_error_kind = "path_empty"
            return False
        if password is None:
            self.last_error = "数据库密码缺失"
            self.last_error_kind = "password_missing"
            return False
        # ① 检测文件已存在 → 拒绝（防误覆盖，风险 G.8）
        if os.path.exists(db_path):
            self.last_error = "文件已存在"
            self.last_error_kind = "file_exists"
            return False
        # 用户可指定一个尚不存在的目录层级；创建数据库前先确保父目录存在。
        try:
            parent_dir = os.path.dirname(os.path.abspath(db_path))
            if parent_dir:
                os.makedirs(parent_dir, exist_ok=True)
        except OSError as exc:
            self.last_error = f"无法创建数据库目录: {exc}"
            self.last_error_kind = self._classify_connection_error(exc)
            return False
        target = Path(db_path).resolve(strict=False)
        temp_path = None
        con = None
        pending_key = None
        try:
            fd, temp_name = tempfile.mkstemp(
                prefix=f".{target.name}.",
                suffix=".pdm-create",
                dir=str(target.parent),
            )
            os.close(fd)
            temp_path = Path(temp_name)
            con = sqleet.connect(str(temp_path), key=password)
            con.execute("BEGIN IMMEDIATE")
            con.execute(
                "CREATE TABLE TTable ("
                "ID INTEGER PRIMARY KEY AUTOINCREMENT,"
                "platform TEXT NOT NULL UNIQUE,"
                "account TEXT, password TEXT, notes TEXT,"
                "totp_secret TEXT, strength TEXT,"
                "password_changed_at TEXT, updated_at TEXT,"
                "is_favorite INTEGER NOT NULL DEFAULT 0,recovery_codes TEXT)"
            )
            con.execute(
                "CREATE TABLE NotesTable ("
                "ID INTEGER PRIMARY KEY AUTOINCREMENT,"
                "title TEXT, content TEXT, created_at TEXT,"
                "updated_at TEXT, sort_order INTEGER DEFAULT 0,"
                "is_favorite INTEGER NOT NULL DEFAULT 0)"
            )
            con.execute(
                "CREATE TABLE IF NOT EXISTS _meta ("
                "key TEXT PRIMARY KEY, value TEXT)"
            )
            salt = self._get_or_create_salt(con)
            raw_key = CryptoHelper.derive_key(password, salt)
            pending_key = SecureKeyBuffer(raw_key)
            con.commit()
            con.close()
            con = None
            with temp_path.open("r+b") as handle:
                handle.flush()
                os.fsync(handle.fileno())
            verify = sqleet.connect(
                temp_path.resolve(strict=True).as_uri() + "?mode=ro",
                key=password,
                uri=True,
            )
            try:
                verify.execute("PRAGMA query_only=ON")
                verified_key, needs_migration = self._inspect_product_schema(
                    verify,
                    password,
                )
                if (
                    needs_migration
                    or not hmac.compare_digest(raw_key, verified_key)
                ):
                    raise RuntimeError("staged database schema verification failed")
            finally:
                verify.close()
            # 同目录 rename 保留文件对象身份。先在暂存名下记录身份，发布后
            # 立即核对；适配器还会在 worker 返回后再次与此身份比较。
            published_identity = self._path_identity(temp_path)
            # Windows 的 os.rename 不覆盖已存在目标；因此目标若在暂存期
            # 被其他进程创建，本次发布会失败而不会触碰该文件。
            os.rename(temp_path, target)
            temp_path = None
            if not self._same_file_identity(
                published_identity,
                self._path_identity(target),
            ):
                raise RuntimeError("published database identity changed")
            self._adopt_session(str(target), password, pending_key)
            self.opened_file_identity = published_identity
            pending_key = None
            return True
        except FileExistsError:
            self.last_error = "文件已存在"
            self.last_error_kind = "file_exists"
            return False
        except Exception as exc:
            self.last_error = f"创建数据库失败: {exc}"
            self.last_error_kind = self._classify_connection_error(exc)
            return False
        finally:
            if con is not None:
                try:
                    con.close()
                except Exception:
                    pass
            if temp_path is not None:
                try:
                    temp_path.unlink(missing_ok=True)
                except OSError:
                    pass
            if pending_key is not None:
                try:
                    pending_key.destroy()
                except Exception:
                    pass

    def verify_current_password_status(
        self,
        password: str,
    ) -> CurrentPasswordStatus:
        """Return a non-ambiguous D5 verification status.

        ``MISMATCH`` is reserved for a healthy database and a well-formed
        password whose derived key does not match.  Missing session state,
        malformed input, unreadable metadata, or backend failures are
        ``ERROR`` so native callers never turn an internal failure into an
        authentication attempt.  No exception text is returned or written to
        ``last_error``.
        """

        if not self.is_connected() or not isinstance(password, str):
            return CurrentPasswordStatus.ERROR
        con = None
        try:
            con = self._connect_bound()
            row = con.execute(
                "SELECT value FROM _meta WHERE key='salt'"
            ).fetchone()
            if (
                row is None
                or len(row) != 1
                or not isinstance(row[0], str)
            ):
                return CurrentPasswordStatus.ERROR
            salt = base64.b64decode(row[0], validate=True)
            test_key = CryptoHelper.derive_key(password, salt)
            current_key = self.derived_key.use()
            try:
                matches = hmac.compare_digest(test_key, current_key)
            finally:
                self.derived_key.lock()
            return (
                CurrentPasswordStatus.MATCH
                if matches
                else CurrentPasswordStatus.MISMATCH
            )
        except Exception:
            return CurrentPasswordStatus.ERROR
        finally:
            if con is not None:
                try:
                    con.close()
                except Exception:
                    pass

    def verify_current_password(self, password: str) -> bool:
        """Backward-compatible bool wrapper for current-password checks."""

        return (
            self.verify_current_password_status(password)
            is CurrentPasswordStatus.MATCH
        )

    # ------------------------------------------------------------------
    # 加解密（基于 SecureKeyBuffer）
    # ------------------------------------------------------------------

    def _encrypt(self, text):
        """使用 SecureKeyBuffer 中的派生密钥加密文本，返回 Base64 字符串

        空值原样返回；加密失败返回 None 并设置 self.last_error。
        """
        if not text:
            return text
        try:
            key = self.derived_key.use()
            try:
                return CryptoHelper.encrypt_data(text, key)
            finally:
                self.derived_key.lock()
        except Exception as e:
            self.last_error = f"加密失败: {e}"
            return None

    def _decrypt(self, text):
        """使用 SecureKeyBuffer 中的派生密钥解密文本

        空值原样返回；解密失败返回 None 并设置 self.last_error。
        """
        if not text:
            return text
        try:
            key = self.derived_key.use()
            try:
                return CryptoHelper.decrypt_data(text, key)
            finally:
                self.derived_key.lock()
        except Exception as e:
            self.last_error = f"解密失败: {e}"
            return None

    def _compute_strength(
        self,
        password: str,
        platform: str = "",
        account: str = "",
        evaluator: PasswordStrengthEvaluator | None = None,
    ) -> str:
        """计算并严格校验待持久化的密码强度等级。"""
        if not password:
            return "weak"
        try:
            level = (
                evaluator(password, platform, account)
                if evaluator is not None
                else PasswordTools.check_password_strength(
                    password,
                    platform,
                    account,
                    max_length=1024,
                ).level
            )
        except StrengthEvaluationCancelled:
            raise
        except Exception as exc:
            raise StrengthEvaluationError("密码强度计算失败") from exc
        if type(level) is not str or level not in {"weak", "fair", "strong"}:
            raise StrengthEvaluationError("密码强度计算返回了非法等级")
        return level

    # ------------------------------------------------------------------
    # 表结构迁移
    # ------------------------------------------------------------------

    @staticmethod
    def _column_exists(con, table: str, column: str) -> bool:
        """通过 PRAGMA table_info 检测指定列是否已存在（用于幂等迁移）"""
        cur = con.execute(f"PRAGMA table_info({table})")
        for row in cur.fetchall():
            if row[1] == column:
                return True
        return False

    def _migrate_is_favorite(self, con):
        """为旧库的 TTable / NotesTable 幂等补齐 is_favorite 列"""
        for table in ('TTable', 'NotesTable'):
            if not self._column_exists(con, table, 'is_favorite'):
                con.execute(
                    f"ALTER TABLE {table} "
                    "ADD COLUMN is_favorite INTEGER NOT NULL DEFAULT 0"
                )

    def _migrate_password_fields(self, con):
        """为旧库的 TTable 幂等补齐密码记录扩展列。

        T1 新增字段：
            - totp_secret TEXT（加密存储）
            - strength TEXT（明文，存 level: weak/fair/strong）
            - password_changed_at TEXT（明文，ISO 8601 时间戳）
            - updated_at TEXT（明文，ISO 8601 时间戳，独立于换密时间）
        """
        for col, col_type in [
            ('totp_secret', 'TEXT'),
            ('recovery_codes', 'TEXT'),
            ('strength', 'TEXT'),
            ('password_changed_at', 'TEXT'),
            ('updated_at', 'TEXT'),
        ]:
            if not self._column_exists(con, 'TTable', col):
                con.execute(f"ALTER TABLE TTable ADD COLUMN {col} {col_type}")
        now = datetime.datetime.now().isoformat()
        con.execute(
            "UPDATE TTable SET updated_at="
            "COALESCE(updated_at, password_changed_at, ?)"
            " WHERE updated_at IS NULL OR updated_at=''",
            (now,),
        )

    def _ensure_password_table_on(self, con):
        """在给定连接上确保密码表存在并迁移到最新结构（避免双连接导致 SQLITE_BUSY）"""
        con.execute(
            "CREATE TABLE IF NOT EXISTS TTable ("
            "ID INTEGER PRIMARY KEY AUTOINCREMENT,"
            "platform TEXT NOT NULL UNIQUE,"
            "account TEXT,"
            "password TEXT,"
            "notes TEXT,"
            "totp_secret TEXT,"
            "strength TEXT,"
            "password_changed_at TEXT,"
            "updated_at TEXT,"
            "is_favorite INTEGER NOT NULL DEFAULT 0,recovery_codes TEXT)"
        )
        self._migrate_is_favorite(con)
        self._migrate_password_fields(con)

    def _ensure_notes_table_on(self, con):
        """在给定连接上确保记事表存在（避免双连接导致 SQLITE_BUSY）"""
        con.execute(
            "CREATE TABLE IF NOT EXISTS NotesTable ("
            "ID INTEGER PRIMARY KEY AUTOINCREMENT,"
            "title TEXT,"
            "content TEXT,"
            "created_at TEXT,"
            "updated_at TEXT,"
            "sort_order INTEGER DEFAULT 0,"
            "is_favorite INTEGER NOT NULL DEFAULT 0)"
        )
        self._migrate_is_favorite(con)

    def _get_or_create_salt(self, con) -> bytes:
        """从 _meta 表获取盐值，不存在则创建"""
        row = con.execute("SELECT value FROM _meta WHERE key='salt'").fetchone()
        if row:
            return base64.b64decode(row[0])
        salt = CryptoHelper.generate_salt()
        con.execute(
            "INSERT INTO _meta (key, value) VALUES (?, ?)",
            ('salt', base64.b64encode(salt).decode())
        )
        return salt

    # ------------------------------------------------------------------
    # 密码记录 CRUD
    # ------------------------------------------------------------------
    # 显式列顺序（避免旧库迁移后 SELECT * 列顺序不一致）：
    #   ID(0), platform(1), account(2), password(3), notes(4),
    #   totp_secret(5), strength(6), password_changed_at(7), updated_at(8),
    #   is_favorite(9), recovery_codes(10)
    # ------------------------------------------------------------------

    _PASSWORD_SELECT_COLUMNS = (
        "ID, platform, account, password, notes, "
        "totp_secret, strength, password_changed_at, updated_at, is_favorite, recovery_codes"
    )
    _BACKUP_CONFLICT_SNAPSHOT_FIELDS = (
        "id",
        "platform",
        "account",
        "password",
        "notes",
        "totp_secret",
        "recovery_codes",
        "strength",
        "password_changed_at",
        "updated_at",
        "is_favorite",
    )

    def _decrypt_password_row(self, row):
        """解密一行 TTable 数据，返回字典；解密失败返回 None

        显式列顺序见 _PASSWORD_SELECT_COLUMNS。
        is_favorite / strength / password_changed_at / updated_at
        为明文字段，直接取值。
        """
        account = self._decrypt(row[2]) if row[2] else ''
        password = self._decrypt(row[3]) if row[3] else ''
        notes = self._decrypt(row[4]) if row[4] else ''
        totp_secret = self._decrypt(row[5]) if row[5] else ''
        try:
            recovery_codes = load_codes(self._decrypt(row[10])) if row[10] else []
        except RecoveryCodeError:
            self.last_error = "恢复码数据无效"
            self.last_error_kind = "database_io_failed"
            return None
        if self.last_error:
            return None
        # 明文字段
        strength = row[6]  # 明文，可能为 None
        password_changed_at = row[7]  # 明文，可能为 None
        updated_at = row[8]  # 明文，迁移后应始终非空
        is_favorite = row[9] if row[9] is not None else 0
        return {
            'id': row[0],
            'platform': row[1],
            'account': account,
            'password': password,
            'notes': notes,
            'totp_secret': totp_secret,
            'recovery_codes': recovery_codes,
            'strength': strength,
            'password_changed_at': password_changed_at,
            'updated_at': updated_at,
            'is_favorite': is_favorite,
        }

    def get_record_counts(self) -> tuple[int, int] | None:
        """返回密码和记事数量，不读取或解密记录正文；失败返回 None。"""
        self.last_error = None
        self.last_error_kind = None
        if not self.is_connected():
            self.last_error = "数据库未连接"
            self.last_error_kind = "not_connected"
            return None
        try:
            con = self._connect_bound()
            try:
                self._ensure_password_table_on(con)
                self._ensure_notes_table_on(con)
                counts = con.execute(
                    "SELECT (SELECT COUNT(*) FROM TTable), "
                    "(SELECT COUNT(*) FROM NotesTable)"
                ).fetchone()
                return int(counts[0]), int(counts[1])
            finally:
                con.close()
        except Exception as exc:
            self.last_error = f"统计记录数量失败: {exc}"
            self.last_error_kind = "database_io_failed"
            return None

    def get_all_passwords(self) -> list:
        """返回全部密码记录（解密后的字典列表）

        每条字典字段：id / platform / account / password / notes / totp_secret /
                      strength / password_changed_at / updated_at / is_favorite
        """
        self.last_error = None
        if not self.is_connected():
            self.last_error = "数据库未连接"
            return []
        try:
            con = self._connect_bound()
            self._ensure_password_table_on(con)
            cur = con.execute(f'SELECT {self._PASSWORD_SELECT_COLUMNS} FROM TTable')
            rows = cur.fetchall()
            con.close()
        except Exception as e:
            self.last_error = f"查询密码记录失败: {e}"
            return []

        result = []
        for row in rows:
            item = self._decrypt_password_row(row)
            if item is None:
                return []
            result.append(item)
        return result

    def get_password_by_id(self, item_id: int) -> dict | None:
        """Return one decrypted password record by immutable ID.

        This bounded lookup avoids decrypting the whole vault for an explicit
        reveal or native-copy request.  ``None`` means the record was not found
        or the read/decrypt operation failed; callers distinguish those cases
        through ``last_error``.
        """

        self.last_error = None
        self.last_error_kind = None
        if not self.is_connected():
            self.last_error = "数据库未连接"
            self.last_error_kind = "not_connected"
            return None
        if type(item_id) is not int or item_id <= 0:
            self.last_error = "密码记录 ID 无效"
            self.last_error_kind = "invalid_argument"
            return None
        try:
            con = self._connect_bound()
            try:
                self._ensure_password_table_on(con)
                row = con.execute(
                    f"SELECT {self._PASSWORD_SELECT_COLUMNS} "
                    "FROM TTable WHERE ID=?",
                    (item_id,),
                ).fetchone()
            finally:
                con.close()
        except Exception as exc:
            self.last_error = f"查询密码记录失败: {exc}"
            self.last_error_kind = "database_io_failed"
            return None
        if row is None:
            return None
        item = self._decrypt_password_row(row)
        if item is None and self.last_error_kind is None:
            self.last_error_kind = "database_io_failed"
        return item

    def get_password_strength_ids(self) -> list[int] | None:
        """固定一次体检的记录范围，仅查询 ID，不读取或解密整库正文。"""
        self.last_error = self.last_error_kind = None
        try:
            con = self._connect_bound()
            try:
                return [int(row[0]) for row in con.execute(
                    "SELECT ID FROM TTable ORDER BY ID"
                ).fetchall()]
            finally:
                con.close()
        except Exception:
            self.last_error = "读取体检记录范围失败"
            self.last_error_kind = "database_io_failed"
            return None

    def get_pending_strength_ids(self) -> list[int] | None:
        """仅读取未评级记录的标识，供解锁后恢复后台检测。"""
        self.last_error = self.last_error_kind = None
        try:
            con = self._connect_bound()
            try:
                return [int(row[0]) for row in con.execute(
                    "SELECT ID FROM TTable WHERE strength IS NULL ORDER BY ID"
                ).fetchall()]
            finally:
                con.close()
        except Exception:
            self.last_error = "读取待检测记录失败"
            self.last_error_kind = "database_io_failed"
            return None

    def get_password_strength_snapshot(
        self, item_id: int,
    ) -> PasswordStrengthSnapshot | None:
        """读取一条评级所需的输入；不存在返回 None，失败另设 error_kind。"""
        self.last_error = self.last_error_kind = None
        if type(item_id) is not int or item_id <= 0:
            self.last_error = "密码记录 ID 无效"
            self.last_error_kind = "invalid_argument"
            return None
        try:
            con = self._connect_bound()
            try:
                row = con.execute(
                    "SELECT ID, platform, account, password, "
                    "password_changed_at, updated_at, strength FROM TTable WHERE ID=?",
                    (item_id,),
                ).fetchone()
            finally:
                con.close()
            if row is None:
                return None
            account = self._decrypt(row[2]) if row[2] else ""
            password = self._decrypt(row[3]) if row[3] else ""
            if self.last_error or not all(
                type(value) is str for value in (row[1], account, password)
            ):
                raise ValueError("评级输入无效")
            return PasswordStrengthSnapshot(item_id, row[1], account, password, tuple(row[:6]), row[6])
        except Exception:
            self.last_error = "读取体检记录失败"
            self.last_error_kind = "database_io_failed"
            return None

    def update_password_strength(
        self, snapshot: PasswordStrengthSnapshot, level: str,
    ) -> bool | None:
        """仅写回未变化记录的评级；True 成功、False 已变化、None 失败。"""
        self.last_error = self.last_error_kind = None
        if (
            not isinstance(snapshot, PasswordStrengthSnapshot)
            or len(snapshot.source) != 6
            or snapshot.source[0] != snapshot.record_id
            or type(level) is not str
            or level not in {"weak", "fair", "strong"}
        ):
            self.last_error = "体检评级或原记录快照无效"
            self.last_error_kind = "invalid_argument"
            return None
        con = None
        try:
            con = self._connect_bound()
            cursor = con.execute(
                "UPDATE TTable SET strength=? WHERE ID=? AND platform IS ? "
                "AND account IS ? AND password IS ? "
                "AND password_changed_at IS ? AND updated_at IS ?",
                (level, *snapshot.source),
            )
            self._commit_bound(con)
            return cursor.rowcount == 1
        except Exception:
            if con is not None:
                con.rollback()
            self.last_error = "更新体检评级失败"
            self.last_error_kind = "database_io_failed"
            return None
        finally:
            if con is not None:
                con.close()

    def search_passwords(self, keyword: str) -> list:
        """按平台名称模糊查询密码记录（keyword 为空时返回全部）"""
        self.last_error = None
        if not self.is_connected():
            self.last_error = "数据库未连接"
            return []
        if not keyword:
            return self.get_all_passwords()
        try:
            con = self._connect_bound()
            self._ensure_password_table_on(con)
            cur = con.execute(
                f"SELECT {self._PASSWORD_SELECT_COLUMNS} FROM TTable WHERE platform LIKE ?",
                (f'%{keyword}%',)
            )
            rows = cur.fetchall()
            con.close()
        except Exception as e:
            self.last_error = f"搜索密码记录失败: {e}"
            return []

        result = []
        for row in rows:
            item = self._decrypt_password_row(row)
            if item is None:
                return []
            result.append(item)
        return result

    def insert_password(
        self,
        data: dict,
        *,
        return_record: bool = False,
        strength_evaluator: PasswordStrengthEvaluator | None = None,
        defer_strength: bool = False,
    ) -> int | dict | None:
        """新增一条密码记录，成功返回新 ID 或提交时的权威记录。

        data 字段：platform(str,必填) / account / password / notes / totp_secret /
                   is_favorite(int,默认0)
        自动计算 strength（调 PasswordTools.check_password_strength）并分别写入
        password_changed_at / updated_at。
        平台名原样保存，纯空白拒绝，并按原始字符串逐字在当前库内唯一。
        """
        self.last_error = None
        self.last_error_kind = None
        if not self.is_connected():
            self.last_error = "数据库未连接"
            self.last_error_kind = "not_connected"
            return None
        platform_value = data.get('platform', '')
        if not isinstance(platform_value, str):
            self.last_error = "平台名称无效"
            self.last_error_kind = "invalid_argument"
            return None
        platform = platform_value
        if not platform.strip():
            self.last_error = "平台名称不能为空"
            self.last_error_kind = "invalid_argument"
            return None

        account = data.get('account', '') or ''
        password = data.get('password', '') or ''
        notes = data.get('notes', '') or ''
        totp_secret = data.get('totp_secret', '') or ''
        try:
            recovery_codes = validate_codes(data.get("recovery_codes", []))
        except RecoveryCodeError:
            self.last_error = "恢复码格式无效"
            self.last_error_kind = "invalid_argument"
            return None
        is_favorite = data.get('is_favorite', 0)
        if type(is_favorite) not in {bool, int} or int(is_favorite) not in {0, 1}:
            self.last_error = "收藏状态无效"
            self.last_error_kind = "invalid_argument"
            return None
        is_favorite = int(is_favorite)

        con = None
        try:
            con = self._connect_bound()
            self._ensure_password_table_on(con)
            self._commit_bound(con)
            con.execute("BEGIN IMMEDIATE")
            existing = con.execute(
                "SELECT platform FROM TTable"
            ).fetchall()
            if any(
                isinstance(row[0], str) and row[0] == platform
                for row in existing
            ):
                con.rollback()
                self.last_error = f"平台名称「{platform}」已存在"
                self.last_error_kind = "platform_conflict"
                return None

            enc_account = self._encrypt(account) if account else None
            enc_password = self._encrypt(password) if password else None
            enc_notes = self._encrypt(notes) if notes else None
            enc_totp = self._encrypt(totp_secret) if totp_secret else None
            enc_recovery = self._encrypt(dump_codes(recovery_codes)) if recovery_codes else None
            if self.last_error:
                con.rollback()
                self.last_error_kind = "database_io_failed"
                return None

            strength = None if defer_strength and password else self._compute_strength(
                password,
                platform,
                account,
                strength_evaluator,
            )
            now = datetime.datetime.now().isoformat()
            password_changed_at = now
            updated_at = now
            cur = con.execute(
                "INSERT INTO TTable "
                "(platform, account, password, notes, totp_secret, strength, "
                "password_changed_at, updated_at, is_favorite, recovery_codes) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (platform, enc_account, enc_password, enc_notes, enc_totp,
                 strength, password_changed_at, updated_at, is_favorite, enc_recovery)
            )
            new_id = cur.lastrowid
            committed_record = (
                {
                    "id": new_id,
                    "platform": platform,
                    "account": account,
                    "password": password,
                    "notes": notes,
                    "totp_secret": totp_secret,
                    "recovery_codes": recovery_codes,
                    "strength": strength,
                    "password_changed_at": password_changed_at,
                    "updated_at": updated_at,
                    "is_favorite": is_favorite,
                }
                if return_record
                else None
            )
            self._commit_bound(con)
            if return_record:
                return committed_record
            return new_id
        except Exception as e:
            if con is not None:
                try:
                    con.rollback()
                except Exception:
                    pass
            error_msg = str(e)
            if isinstance(e, StrengthEvaluationCancelled):
                self.last_error = "密码强度计算已取消"
                self.last_error_kind = "cancelled"
            elif isinstance(e, StrengthEvaluationError):
                self.last_error = "密码强度计算失败"
                self.last_error_kind = "strength_analysis_failed"
            elif 'UNIQUE constraint failed' in error_msg or 'unique' in error_msg.lower():
                self.last_error = f"平台名称「{platform}」已存在"
                self.last_error_kind = "platform_conflict"
            else:
                self.last_error = f"新增密码记录失败: {e}"
                self.last_error_kind = "database_io_failed"
            return None
        finally:
            if con is not None:
                try:
                    con.close()
                except Exception:
                    pass

    def update_password(
        self,
        item_id: int,
        data: dict,
        *,
        expected: dict | None = None,
        return_record: bool = False,
        strength_evaluator: PasswordStrengthEvaluator | None = None,
        defer_strength: bool = False,
    ) -> bool | dict:
        """按不可变 ID 原子更新一条密码记录。

        ``data`` 中未提供的字段保持原值。``expected`` 为调用方在取得
        revision 时看到的完整解密快照；提供后，本方法会先 ``BEGIN
        IMMEDIATE``，再在同一事务中重新读取并逐字段比较，避免检查
        revision 与 UPDATE 之间的竞态覆盖。派生评级不参与内容版本比较；
        评分输入未变时沿用数据库当前评级。
        """

        self.last_error = None
        self.last_error_kind = None
        if not self.is_connected():
            self.last_error = "数据库未连接"
            self.last_error_kind = "not_connected"
            return False
        if type(item_id) is not int or item_id <= 0 or not isinstance(data, dict):
            self.last_error = "记录 ID 或更新数据无效"
            self.last_error_kind = "invalid_argument"
            return False
        if expected is not None and not isinstance(expected, dict):
            self.last_error = "预期记录快照无效"
            self.last_error_kind = "invalid_argument"
            return False

        con = None
        new_platform = ""
        try:
            con = self._connect_bound()
            self._ensure_password_table_on(con)
            self._commit_bound(con)
            con.execute("BEGIN IMMEDIATE")
            row = con.execute(
                f"SELECT {self._PASSWORD_SELECT_COLUMNS} FROM TTable WHERE ID=?",
                (item_id,),
            ).fetchone()
            if row is None:
                con.rollback()
                self.last_error = f"密码记录 ID={item_id} 不存在"
                self.last_error_kind = "not_found"
                return False
            old_item = self._decrypt_password_row(row)
            if old_item is None:
                con.rollback()
                self.last_error_kind = "database_io_failed"
                return False

            if expected is not None:
                snapshot_fields = (
                    "id",
                    "platform",
                    "account",
                    "password",
                    "notes",
                    "totp_secret",
                    "recovery_codes",
                    "password_changed_at",
                    "updated_at",
                    "is_favorite",
                )
                if any(
                    field not in expected
                    or expected[field] != old_item[field]
                    for field in snapshot_fields
                ):
                    con.rollback()
                    self.last_error = "密码记录已发生变化"
                    self.last_error_kind = "revision_conflict"
                    return False

            platform_value = data.get("platform", old_item["platform"])
            if not isinstance(platform_value, str):
                con.rollback()
                self.last_error = "平台名称无效"
                self.last_error_kind = "invalid_argument"
                return False
            new_platform = platform_value
            if not new_platform.strip():
                con.rollback()
                self.last_error = "平台名称不能为空"
                self.last_error_kind = "invalid_argument"
                return False

            new_account = data.get("account", old_item["account"])
            new_password = data.get("password", old_item["password"])
            new_notes = data.get("notes", old_item["notes"])
            new_totp = data.get("totp_secret", old_item["totp_secret"])
            new_recovery = validate_codes(data.get("recovery_codes", old_item["recovery_codes"]))
            if not all(
                isinstance(value, str)
                for value in (
                    new_account,
                    new_password,
                    new_notes,
                    new_totp,
                )
            ):
                con.rollback()
                self.last_error = "密码记录字段类型无效"
                self.last_error_kind = "invalid_argument"
                return False
            new_is_favorite = data.get(
                "is_favorite",
                old_item["is_favorite"],
            )
            if (
                type(new_is_favorite) not in {bool, int}
                or int(new_is_favorite) not in {0, 1}
            ):
                con.rollback()
                self.last_error = "收藏状态无效"
                self.last_error_kind = "invalid_argument"
                return False

            existing_names = con.execute(
                "SELECT platform FROM TTable WHERE ID!=?",
                (item_id,),
            ).fetchall()
            if any(
                isinstance(value[0], str) and value[0] == new_platform
                for value in existing_names
            ):
                con.rollback()
                self.last_error = f"平台名称「{new_platform}」已存在"
                self.last_error_kind = "platform_conflict"
                return False

            password_changed = new_password != old_item["password"]
            strength_input_changed = (
                password_changed
                or new_platform != old_item["platform"]
                or new_account != old_item["account"]
            )
            content_changed = any(
                (
                    new_platform != old_item["platform"],
                    new_account != old_item["account"],
                    password_changed,
                    new_notes != old_item["notes"],
                    new_totp != old_item["totp_secret"],
                    new_recovery != old_item["recovery_codes"],
                )
            )
            now = datetime.datetime.now().isoformat()
            if strength_input_changed:
                strength = None if defer_strength and new_password else self._compute_strength(
                    new_password,
                    new_platform,
                    new_account,
                    strength_evaluator,
                )
            else:
                strength = old_item["strength"]
            password_changed_at = now if password_changed else old_item["password_changed_at"]
            updated_at = now if content_changed else old_item["updated_at"]

            enc_account = self._encrypt(new_account) if new_account else None
            enc_password = self._encrypt(new_password) if new_password else None
            enc_notes = self._encrypt(new_notes) if new_notes else None
            enc_totp = self._encrypt(new_totp) if new_totp else None
            enc_recovery = self._encrypt(dump_codes(new_recovery)) if new_recovery else None
            if self.last_error:
                con.rollback()
                self.last_error_kind = "database_io_failed"
                return False

            cursor = con.execute(
                "UPDATE TTable SET platform=?, account=?, password=?, notes=?, "
                "totp_secret=?, strength=?, password_changed_at=?, updated_at=?, "
                "is_favorite=?, recovery_codes=? WHERE ID=?",
                (
                    new_platform,
                    enc_account,
                    enc_password,
                    enc_notes,
                    enc_totp,
                    strength,
                    password_changed_at,
                    updated_at,
                    int(new_is_favorite),
                    enc_recovery,
                    item_id,
                ),
            )
            if cursor.rowcount != 1:
                con.rollback()
                self.last_error = f"密码记录 ID={item_id} 不存在"
                self.last_error_kind = "not_found"
                return False
            committed_record = (
                {
                    "id": item_id,
                    "platform": new_platform,
                    "account": new_account,
                    "password": new_password,
                    "notes": new_notes,
                    "totp_secret": new_totp,
                    "recovery_codes": new_recovery,
                    "strength": strength,
                    "password_changed_at": password_changed_at,
                    "updated_at": updated_at,
                    "is_favorite": int(new_is_favorite),
                }
                if return_record
                else None
            )
            self._commit_bound(con)
            if return_record:
                return committed_record
            return True
        except Exception as exc:
            if con is not None:
                try:
                    con.rollback()
                except Exception:
                    pass
            error_msg = str(exc)
            if isinstance(exc, RecoveryCodeError):
                self.last_error = "恢复码格式无效"
                self.last_error_kind = "invalid_argument"
            elif isinstance(exc, StrengthEvaluationCancelled):
                self.last_error = "密码强度计算已取消"
                self.last_error_kind = "cancelled"
            elif isinstance(exc, StrengthEvaluationError):
                self.last_error = "密码强度计算失败"
                self.last_error_kind = "strength_analysis_failed"
            elif (
                "UNIQUE constraint failed" in error_msg
                or "unique" in error_msg.lower()
            ):
                self.last_error = f"平台名称「{new_platform}」已存在"
                self.last_error_kind = "platform_conflict"
            else:
                self.last_error = f"更新密码记录失败: {exc}"
                self.last_error_kind = "database_io_failed"
            return False
        finally:
            if con is not None:
                try:
                    con.close()
                except Exception:
                    pass

    def delete_password(
        self,
        item_id: int,
        *,
        expected: dict,
    ) -> bool:
        """按不可变 ID 和完整预期快照原子删除一条密码记录。

        ``expected`` 必须是调用方取得 revision 时看到的完整解密快照。
        本方法在 ``BEGIN IMMEDIATE`` 后重新读取并逐字段比较，再执行
        ``DELETE``，避免 revision 检查与删除之间的竞态；派生评级不参与比较。
        """

        self.last_error = None
        self.last_error_kind = None
        if not self.is_connected():
            self.last_error = "数据库未连接"
            self.last_error_kind = "not_connected"
            return False
        if (
            type(item_id) is not int
            or item_id <= 0
            or not isinstance(expected, dict)
        ):
            self.last_error = "记录 ID 或预期记录快照无效"
            self.last_error_kind = "invalid_argument"
            return False

        con = None
        current = None
        try:
            con = self._connect_bound()
            self._ensure_password_table_on(con)
            self._commit_bound(con)
            con.execute("BEGIN IMMEDIATE")
            row = con.execute(
                f"SELECT {self._PASSWORD_SELECT_COLUMNS} FROM TTable WHERE ID=?",
                (item_id,),
            ).fetchone()
            if row is None:
                con.rollback()
                self.last_error = f"密码记录 ID={item_id} 不存在"
                self.last_error_kind = "not_found"
                return False
            current = self._decrypt_password_row(row)
            if current is None:
                con.rollback()
                self.last_error_kind = "database_io_failed"
                return False

            snapshot_fields = (
                "id",
                "platform",
                "account",
                "password",
                "notes",
                "totp_secret",
                "recovery_codes",
                "password_changed_at",
                "updated_at",
                "is_favorite",
            )
            if any(
                field not in expected
                or expected[field] != current[field]
                for field in snapshot_fields
            ):
                con.rollback()
                self.last_error = "密码记录已发生变化"
                self.last_error_kind = "revision_conflict"
                return False

            cursor = con.execute(
                "DELETE FROM TTable WHERE ID=?",
                (item_id,),
            )
            if cursor.rowcount != 1:
                con.rollback()
                self.last_error = f"密码记录 ID={item_id} 不存在"
                self.last_error_kind = "not_found"
                return False
            self._commit_bound(con)
            return True
        except Exception as exc:
            if con is not None:
                try:
                    con.rollback()
                except Exception:
                    pass
            self.last_error = f"删除密码记录失败: {exc}"
            self.last_error_kind = "database_io_failed"
            return False
        finally:
            for value in (current, expected):
                if isinstance(value, dict):
                    for field in (
                        "account",
                        "password",
                        "notes",
                        "totp_secret",
                    ):
                        if field in value:
                            value[field] = ""
            if con is not None:
                try:
                    con.close()
                except Exception:
                    pass

    def delete_passwords(self, ids: list) -> int:
        """批量删除密码记录（按 ID），返回实际删除数量"""
        self.last_error = None
        if not self.is_connected():
            self.last_error = "数据库未连接"
            return 0
        if not ids:
            return 0
        try:
            con = self._connect_bound()
            self._ensure_password_table_on(con)
            deleted = 0
            for item_id in ids:
                cur = con.execute("DELETE FROM TTable WHERE ID=?", (item_id,))
                if cur.rowcount > 0:
                    deleted += cur.rowcount
            self._commit_bound(con)
            con.close()
            return deleted
        except Exception as e:
            self.last_error = f"删除密码记录失败: {e}"
            return 0

    def set_password_favorite(self, item_id: int, favorite: int) -> bool:
        """切换密码记录的收藏状态（0=取消收藏，1=收藏），按 ID 操作"""
        self.last_error = None
        self.last_error_kind = None
        if not self.is_connected():
            self.last_error = "数据库未连接"
            self.last_error_kind = "not_connected"
            return False
        if type(item_id) is not int or item_id <= 0:
            self.last_error = "记录 ID 无效"
            self.last_error_kind = "invalid_argument"
            return False
        if type(favorite) not in {bool, int} or int(favorite) not in {0, 1}:
            self.last_error = "收藏状态无效"
            self.last_error_kind = "invalid_argument"
            return False
        favorite = int(favorite)
        try:
            con = self._connect_bound()
            self._ensure_password_table_on(con)
            cur = con.execute(
                "UPDATE TTable SET is_favorite=? WHERE ID=?",
                (favorite, item_id)
            )
            self._commit_bound(con)
            con.close()
            if cur.rowcount <= 0:
                self.last_error = f"密码记录 ID={item_id} 不存在"
                self.last_error_kind = "not_found"
                return False
            return True
        except Exception as e:
            self.last_error = f"设置密码收藏失败: {e}"
            self.last_error_kind = "database_io_failed"
            return False

    def get_duplicate_groups(self) -> dict:
        """返回 {item_id: group_number}，按密码明文分组

        仅 length > 1 的组参与编号；组号按"组内最小 id"升序分配（1, 2, 3...）。
        单条密码或空密码不返回（即不在 dict 中）。
        供安全体检面板检测重复密码用。
        """
        self.last_error = None
        if not self.is_connected():
            self.last_error = "数据库未连接"
            return {}
        try:
            all_passwords = self.get_all_passwords()
            if self.last_error:
                return {}
            # 按密码明文分组
            groups = {}  # password_text -> list of ids
            for p in all_passwords:
                pwd = p.get('password', '')
                if not pwd:  # 空密码不参与分组
                    continue
                groups.setdefault(pwd, []).append(p['id'])
            # 仅 length > 1 的组参与编号
            multi_groups = [ids for ids in groups.values() if len(ids) > 1]
            # 按"组内最小 id"升序排序
            multi_groups.sort(key=lambda ids: min(ids))
            result = {}
            for group_num, ids in enumerate(multi_groups, start=1):
                for item_id in ids:
                    result[item_id] = group_num
            return result
        except Exception as e:
            self.last_error = f"检测重复组失败: {e}"
            return {}

    # ------------------------------------------------------------------
    # 记事本 CRUD
    # ------------------------------------------------------------------

    _NOTE_SELECT_COLUMNS = (
        "ID, title, content, created_at, updated_at, sort_order, is_favorite"
    )
    _NOTE_SNAPSHOT_FIELDS = (
        "id",
        "title",
        "content",
        "created_at",
        "updated_at",
        "sort_order",
        "is_favorite",
    )

    def _decrypt_note(self, row):
        """解密一行 NotesTable 数据，返回字典；解密失败返回 None

        is_favorite 为 INTEGER 明文字段，直接取值，不参与加解密。
        """
        title = self._decrypt(row[1]) if row[1] else ''
        content = self._decrypt(row[2]) if row[2] else ''
        created_at = self._decrypt(row[3]) if row[3] else ''
        updated_at = self._decrypt(row[4]) if row[4] else ''
        if self.last_error:
            return None
        sort_order = row[5] if len(row) > 5 else 0
        is_favorite = row[6] if len(row) > 6 else 0
        return {
            'id': row[0],
            'title': title,
            'content': content,
            'created_at': created_at,
            'updated_at': updated_at,
            'sort_order': sort_order,
            'is_favorite': is_favorite,
        }

    def get_all_notes(self) -> list:
        """返回全部记事（按 sort_order 升序、ID 降序排序，解密后）"""
        self.last_error = None
        if not self.is_connected():
            self.last_error = "数据库未连接"
            return []
        try:
            con = self._connect_bound()
            self._ensure_notes_table_on(con)
            cur = con.execute(
                f'SELECT {self._NOTE_SELECT_COLUMNS} FROM NotesTable '
                'ORDER BY sort_order ASC, ID DESC'
            )
            rows = cur.fetchall()
            con.close()
        except Exception as e:
            self.last_error = f"查询记事失败: {e}"
            return []

        result = []
        for row in rows:
            item = self._decrypt_note(row)
            if item is None:
                return []
            result.append(item)
        return result

    def search_notes(self, keyword: str) -> list:
        """按标题或内容模糊搜索记事（keyword 为空时返回全部）"""
        self.last_error = None
        if not self.is_connected():
            self.last_error = "数据库未连接"
            return []
        if not keyword:
            return self.get_all_notes()
        try:
            con = self._connect_bound()
            self._ensure_notes_table_on(con)
            cur = con.execute(
                f'SELECT {self._NOTE_SELECT_COLUMNS} FROM NotesTable '
                'ORDER BY sort_order ASC, ID DESC'
            )
            rows = cur.fetchall()
            con.close()
        except Exception as e:
            self.last_error = f"搜索记事失败: {e}"
            return []

        result = []
        query_lower = keyword.lower()
        for row in rows:
            item = self._decrypt_note(row)
            if item is None:
                return []
            if query_lower in (item['title'] or "").lower() \
                    or query_lower in (item['content'] or "").lower():
                result.append(item)
        return result

    def get_note(self, item_id: int) -> dict | None:
        """按不可变 ID 读取一条解密记事。"""
        self.last_error = None
        self.last_error_kind = None
        if not self.is_connected():
            self.last_error = "数据库未连接"
            self.last_error_kind = "not_connected"
            return None
        if type(item_id) is not int or item_id <= 0:
            self.last_error = "记事 ID 无效"
            self.last_error_kind = "invalid_argument"
            return None
        try:
            con = self._connect_bound()
            try:
                self._ensure_notes_table_on(con)
                row = con.execute(
                    f"SELECT {self._NOTE_SELECT_COLUMNS} FROM NotesTable WHERE ID=?",
                    (item_id,),
                ).fetchone()
            finally:
                con.close()
        except Exception as exc:
            self.last_error = f"查询记事失败: {exc}"
            self.last_error_kind = "database_io_failed"
            return None
        if row is None:
            return None
        item = self._decrypt_note(row)
        if item is None and self.last_error_kind is None:
            self.last_error_kind = "database_io_failed"
        return item

    def insert_note(
        self,
        data: dict,
        *,
        return_record: bool = False,
    ) -> int | dict | None:
        """新增记事，成功返回新 ID 或提交时的权威记录。

        核心层保留历史超长标题和正文；正式新值的长度限制属于入口层。
        """
        self.last_error = None
        self.last_error_kind = None
        if not self.is_connected():
            self.last_error = "数据库未连接"
            self.last_error_kind = "not_connected"
            return None
        if not isinstance(data, dict):
            self.last_error = "记事数据无效"
            self.last_error_kind = "invalid_argument"
            return None
        title = data.get("title", "")
        content = data.get("content", "")
        if content is None:
            content = ""
        if not isinstance(title, str) or not title:
            self.last_error = "标题不能为空"
            self.last_error_kind = "invalid_argument"
            return None
        if not isinstance(content, str):
            self.last_error = "记事正文字段无效"
            self.last_error_kind = "invalid_argument"
            return None
        is_favorite = data.get("is_favorite", 0)
        if type(is_favorite) not in {bool, int} or int(is_favorite) not in {0, 1}:
            self.last_error = "收藏状态无效"
            self.last_error_kind = "invalid_argument"
            return None
        is_favorite = int(is_favorite)

        con = None
        try:
            con = self._connect_bound()
            self._ensure_notes_table_on(con)
            self._commit_bound(con)
            con.execute("BEGIN IMMEDIATE")
            now = datetime.datetime.now().isoformat()
            enc_title = self._encrypt(title)
            enc_content = self._encrypt(content) if content else None
            enc_created = self._encrypt(now)
            enc_updated = self._encrypt(now)
            if self.last_error:
                con.rollback()
                self.last_error_kind = "database_io_failed"
                return None
            next_order = con.execute(
                "SELECT COALESCE(MAX(sort_order), -1) + 1 FROM NotesTable"
            ).fetchone()[0]
            new_id = con.execute(
                "INSERT INTO NotesTable (title, content, created_at, updated_at, sort_order, is_favorite) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (enc_title, enc_content, enc_created, enc_updated, next_order, is_favorite),
            ).lastrowid
            committed_record = (
                {
                    "id": new_id,
                    "title": title,
                    "content": content,
                    "created_at": now,
                    "updated_at": now,
                    "sort_order": next_order,
                    "is_favorite": is_favorite,
                }
                if return_record
                else None
            )
            self._commit_bound(con)
            return committed_record if return_record else new_id
        except Exception as exc:
            if con is not None:
                try:
                    con.rollback()
                except Exception:
                    pass
            self.last_error = f"新增记事失败: {exc}"
            self.last_error_kind = "database_io_failed"
            return None
        finally:
            if con is not None:
                try:
                    con.close()
                except Exception:
                    pass

    def update_note(
        self,
        item_id: int,
        data: dict,
        *,
        expected: dict | None = None,
        return_record: bool = False,
    ) -> bool | dict:
        """按不可变 ID 原子更新一条记事。"""
        self.last_error = None
        self.last_error_kind = None
        if not self.is_connected():
            self.last_error = "数据库未连接"
            self.last_error_kind = "not_connected"
            return False
        if type(item_id) is not int or item_id <= 0 or not isinstance(data, dict):
            self.last_error = "记事 ID 或更新数据无效"
            self.last_error_kind = "invalid_argument"
            return False
        if expected is not None and not isinstance(expected, dict):
            self.last_error = "预期记事快照无效"
            self.last_error_kind = "invalid_argument"
            return False

        con = None
        try:
            con = self._connect_bound()
            self._ensure_notes_table_on(con)
            self._commit_bound(con)
            con.execute("BEGIN IMMEDIATE")
            row = con.execute(
                f"SELECT {self._NOTE_SELECT_COLUMNS} FROM NotesTable WHERE ID=?",
                (item_id,),
            ).fetchone()
            if row is None:
                con.rollback()
                self.last_error = f"记事 ID={item_id} 不存在"
                self.last_error_kind = "not_found"
                return False
            old_note = self._decrypt_note(row)
            if old_note is None:
                con.rollback()
                self.last_error_kind = "database_io_failed"
                return False
            if expected is not None and any(
                field not in expected or expected[field] != old_note[field]
                for field in self._NOTE_SNAPSHOT_FIELDS
            ):
                con.rollback()
                self.last_error = "记事已发生变化"
                self.last_error_kind = "revision_conflict"
                return False

            new_title = data.get("title", old_note["title"])
            new_content = data.get("content", old_note["content"])
            if new_content is None:
                new_content = ""
            new_is_favorite = data.get("is_favorite", old_note["is_favorite"])
            if not isinstance(new_title, str) or not new_title:
                con.rollback()
                self.last_error = "标题不能为空"
                self.last_error_kind = "invalid_argument"
                return False
            if not isinstance(new_content, str):
                con.rollback()
                self.last_error = "记事正文字段无效"
                self.last_error_kind = "invalid_argument"
                return False
            if (
                type(new_is_favorite) not in {bool, int}
                or int(new_is_favorite) not in {0, 1}
            ):
                con.rollback()
                self.last_error = "收藏状态无效"
                self.last_error_kind = "invalid_argument"
                return False
            new_is_favorite = int(new_is_favorite)
            content_changed = (
                new_title != old_note["title"]
                or new_content != old_note["content"]
            )
            favorite_changed = new_is_favorite != old_note["is_favorite"]
            if not content_changed and not favorite_changed:
                self._commit_bound(con)
                return dict(old_note) if return_record else True

            updated_at = old_note["updated_at"]
            if content_changed:
                updated_at = datetime.datetime.now().isoformat()
                enc_title = self._encrypt(new_title)
                enc_content = self._encrypt(new_content) if new_content else None
                enc_updated = self._encrypt(updated_at)
                if self.last_error:
                    con.rollback()
                    self.last_error_kind = "database_io_failed"
                    return False
                cursor = con.execute(
                    "UPDATE NotesTable SET title=?, content=?, updated_at=?, is_favorite=? WHERE ID=?",
                    (enc_title, enc_content, enc_updated, new_is_favorite, item_id),
                )
            else:
                cursor = con.execute(
                    "UPDATE NotesTable SET is_favorite=? WHERE ID=?",
                    (new_is_favorite, item_id),
                )
            if cursor.rowcount != 1:
                con.rollback()
                self.last_error = f"记事 ID={item_id} 不存在"
                self.last_error_kind = "not_found"
                return False
            committed_record = {
                "id": item_id,
                "title": new_title,
                "content": new_content,
                "created_at": old_note["created_at"],
                "updated_at": updated_at,
                "sort_order": old_note["sort_order"],
                "is_favorite": new_is_favorite,
            }
            self._commit_bound(con)
            return committed_record if return_record else True
        except Exception as exc:
            if con is not None:
                try:
                    con.rollback()
                except Exception:
                    pass
            self.last_error = f"更新记事失败: {exc}"
            self.last_error_kind = "database_io_failed"
            return False
        finally:
            if con is not None:
                try:
                    con.close()
                except Exception:
                    pass

    def delete_notes(self, note_ids: list) -> int:
        """批量删除记事（按 ID），返回实际删除数量"""
        self.last_error = None
        if not self.is_connected():
            self.last_error = "数据库未连接"
            return 0
        if not note_ids:
            return 0
        try:
            con = self._connect_bound()
            self._ensure_notes_table_on(con)
            deleted = 0
            for nid in note_ids:
                cur = con.execute("DELETE FROM NotesTable WHERE ID=?", (nid,))
                if cur.rowcount > 0:
                    deleted += cur.rowcount
            self._commit_bound(con)
            con.close()
            return deleted
        except Exception as e:
            self.last_error = f"删除记事失败: {e}"
            return 0

    def delete_note(
        self,
        item_id: int,
        *,
        expected: dict | None = None,
    ) -> bool:
        """按不可变 ID 原子删除一条记事，可校验完整预期快照。"""
        self.last_error = None
        self.last_error_kind = None
        if not self.is_connected():
            self.last_error = "数据库未连接"
            self.last_error_kind = "not_connected"
            return False
        if type(item_id) is not int or item_id <= 0:
            self.last_error = "记事 ID 无效"
            self.last_error_kind = "invalid_argument"
            return False
        if expected is not None and not isinstance(expected, dict):
            self.last_error = "预期记事快照无效"
            self.last_error_kind = "invalid_argument"
            return False

        con = None
        try:
            con = self._connect_bound()
            self._ensure_notes_table_on(con)
            self._commit_bound(con)
            con.execute("BEGIN IMMEDIATE")
            row = con.execute(
                f"SELECT {self._NOTE_SELECT_COLUMNS} FROM NotesTable WHERE ID=?",
                (item_id,),
            ).fetchone()
            if row is None:
                con.rollback()
                self.last_error = f"记事 ID={item_id} 不存在"
                self.last_error_kind = "not_found"
                return False
            current = self._decrypt_note(row)
            if current is None:
                con.rollback()
                self.last_error_kind = "database_io_failed"
                return False
            if expected is not None and any(
                field not in expected or expected[field] != current[field]
                for field in self._NOTE_SNAPSHOT_FIELDS
            ):
                con.rollback()
                self.last_error = "记事已发生变化"
                self.last_error_kind = "revision_conflict"
                return False
            cursor = con.execute("DELETE FROM NotesTable WHERE ID=?", (item_id,))
            if cursor.rowcount != 1:
                con.rollback()
                self.last_error = f"记事 ID={item_id} 不存在"
                self.last_error_kind = "not_found"
                return False
            self._commit_bound(con)
            return True
        except Exception as exc:
            if con is not None:
                try:
                    con.rollback()
                except Exception:
                    pass
            self.last_error = f"删除记事失败: {exc}"
            self.last_error_kind = "database_io_failed"
            return False
        finally:
            if con is not None:
                try:
                    con.close()
                except Exception:
                    pass

    def update_note_order(self, note_ids: list) -> bool:
        """批量更新记事排序：按 note_ids 顺序依次赋予 sort_order=0,1,2,..."""
        self.last_error = None
        if not self.is_connected():
            self.last_error = "数据库未连接"
            return False
        if not note_ids:
            return True
        try:
            con = self._connect_bound()
            self._ensure_notes_table_on(con)
            for order, nid in enumerate(note_ids):
                con.execute(
                    'UPDATE NotesTable SET sort_order=? WHERE ID=?',
                    (order, nid)
                )
            self._commit_bound(con)
            con.close()
            return True
        except Exception as e:
            self.last_error = f"更新记事排序失败: {e}"
            return False

    def set_note_favorite(
        self,
        note_id: int,
        favorite: int,
        *,
        expected: dict | None = None,
        return_record: bool = False,
    ) -> bool | dict:
        """更新记事收藏状态；收藏本身不刷新 ``updated_at``。"""
        return self.update_note(
            note_id,
            {"is_favorite": favorite},
            expected=expected,
            return_record=return_record,
        )

    # ------------------------------------------------------------------
    # 导入导出
    # ------------------------------------------------------------------

    def export_backup_snapshot(self, scope: str) -> dict:
        """从单个读事务返回一份严格备份载荷。"""

        self.last_error = None
        self.last_error_kind = None
        if scope not in {"ALL", "PASSWORDS", "NOTES"}:
            self.last_error = "备份范围无效"
            self.last_error_kind = "invalid_argument"
            return {}
        if not self.is_connected():
            self.last_error = "数据库未连接"
            self.last_error_kind = "not_connected"
            return {}

        con = None
        try:
            con = self._connect_bound()
            con.execute("BEGIN")
            password_rows = (
                con.execute(
                    f"SELECT {self._PASSWORD_SELECT_COLUMNS} FROM TTable ORDER BY ID"
                ).fetchall()
                if scope in {"ALL", "PASSWORDS"}
                else []
            )
            note_rows = (
                con.execute(
                    f"SELECT {self._NOTE_SELECT_COLUMNS} FROM NotesTable "
                    "ORDER BY sort_order ASC, ID DESC"
                ).fetchall()
                if scope in {"ALL", "NOTES"}
                else []
            )
            passwords = []
            for row in password_rows:
                item = self._decrypt_password_row(row)
                if item is None:
                    raise RuntimeError("密码记录解密失败")
                passwords.append(
                    {
                        "platform": item["platform"],
                        "account": item["account"],
                        "password": item["password"],
                        "notes": item["notes"],
                        "totp_secret": item["totp_secret"],
                        "recovery_codes": item["recovery_codes"],
                        "strength": item["strength"],
                        "password_changed_at": item["password_changed_at"],
                        "updated_at": item["updated_at"],
                        "is_favorite": bool(item["is_favorite"]),
                    }
                )
            notes = []
            for row in note_rows:
                item = self._decrypt_note(row)
                if item is None:
                    raise RuntimeError("记事解密失败")
                notes.append(
                    {
                        "title": item["title"],
                        "content": item["content"],
                        "created_at": item["created_at"],
                        "updated_at": item["updated_at"],
                        "sort_order": item["sort_order"],
                        "is_favorite": bool(item["is_favorite"]),
                    }
                )
            self._assert_bound_identity()
            con.rollback()
            payload = {
                "type": BACKUP_PAYLOAD_TYPE,
                "version": BACKUP_PAYLOAD_VERSION,
                "export_time": datetime.datetime.now().isoformat(),
                "scope": scope,
                "passwords": passwords,
                "notes": notes,
            }
            validate_backup_payload(payload)
            return payload
        except Exception as exc:
            if con is not None:
                try:
                    con.rollback()
                except Exception:
                    pass
            self.last_error = f"导出备份失败: {exc}"
            self.last_error_kind = (
                "backup_invalid"
                if isinstance(exc, BackupError)
                else "database_io_failed"
            )
            return {}
        finally:
            if con is not None:
                try:
                    con.close()
                except Exception:
                    pass

    def import_backup_payload(
        self,
        payload: dict,
        decisions: dict[str, str],
        expected_conflicts: dict[str, dict],
        *,
        note_decisions: dict[int, dict] | None = None,
        expected_note_groups: dict[str, list[dict]] | None = None,
    ) -> dict | None:
        """重验冲突后原子导入一份已校验载荷。"""

        self.last_error = None
        self.last_error_kind = None
        try:
            validate_backup_payload(payload)
        except BackupError as exc:
            self.last_error = str(exc)
            self.last_error_kind = "invalid_argument"
            return None
        if (
            not isinstance(decisions, dict)
            or not isinstance(expected_conflicts, dict)
            or any(
                not isinstance(name, str)
                or "\x00" in name
                or not isinstance(decision, str)
                or decision not in {"OVERWRITE", "SKIP"}
                for name, decision in decisions.items()
            )
            or any(
                not isinstance(name, str)
                or "\x00" in name
                or not isinstance(snapshot, dict)
                or set(snapshot) != set(self._BACKUP_CONFLICT_SNAPSHOT_FIELDS)
                or snapshot.get("platform") != name
                or type(snapshot.get("id")) is not int
                or snapshot["id"] <= 0
                for name, snapshot in expected_conflicts.items()
            )
        ):
            self.last_error = "备份冲突决定无效"
            self.last_error_kind = "invalid_argument"
            return None
        if not self.is_connected():
            self.last_error = "数据库未连接"
            self.last_error_kind = "not_connected"
            return None
        password_items = payload["passwords"]
        note_items = payload["notes"]
        if (note_decisions is None) != (expected_note_groups is None) or (
            note_decisions is not None and (
                not isinstance(note_decisions, dict) or not isinstance(expected_note_groups, dict)
            )
        ) or (not note_items and (note_decisions or expected_note_groups)):
            self.last_error = "记事冲突决定无效"
            self.last_error_kind = "invalid_argument"
            return None
        if not password_items and not note_items:
            if decisions or expected_conflicts:
                self.last_error = "空备份不能包含冲突决定"
                self.last_error_kind = "invalid_argument"
                return None
            return {"imported": 0, "overwritten": 0, "skipped": 0}

        con = None
        try:
            con = self._connect_bound()
            con.execute("BEGIN IMMEDIATE")
            existing = {}
            for row in con.execute(
                f"SELECT {self._PASSWORD_SELECT_COLUMNS} FROM TTable"
            ).fetchall():
                item = self._decrypt_password_row(row)
                if item is None:
                    raise RuntimeError("密码记录解密失败")
                existing[item["platform"]] = item
            actual_conflicts = {
                item["platform"]: existing[item["platform"]]
                for item in password_items
                if item["platform"] in existing
            }
            if set(actual_conflicts) != set(expected_conflicts) or any(
                any(
                    current[field] != expected_conflicts[name][field]
                    for field in self._BACKUP_CONFLICT_SNAPSHOT_FIELDS
                    if field != "strength"
                )
                for name, current in actual_conflicts.items()
            ):
                raise _BackupConflictChanged()
            identical_passwords = {
                item["platform"] for item in password_items
                if item["platform"] in actual_conflicts
                and backup_password_content(item) == backup_password_content(actual_conflicts[item["platform"]])
            }
            if not set(actual_conflicts) - identical_passwords <= set(decisions) <= set(actual_conflicts):
                raise _BackupDecisionInvalid()

            note_targets = {}
            identical_notes = {}
            if note_items:
                rows = [self._decrypt_note(row) for row in con.execute(
                    f"SELECT {self._NOTE_SELECT_COLUMNS} FROM NotesTable"
                ).fetchall()]
                if any(row is None for row in rows):
                    raise RuntimeError("记事记录解密失败")
                identical_notes = backup_identical_note_targets(rows, note_items)
            if expected_note_groups is not None and note_items:
                actual_groups = backup_note_groups(rows, note_items)
                if actual_groups != expected_note_groups:
                    raise _BackupConflictChanged()
                counts = {}
                for item in note_items:
                    key = similar_name_key(item["title"])
                    counts[key] = counts.get(key, 0) + 1
                required = {index for index, item in enumerate(note_items)
                            if actual_groups[similar_name_key(item["title"])] or counts[similar_name_key(item["title"])] > 1}
                if not required - identical_notes.keys() <= set(note_decisions) <= required:
                    raise _BackupDecisionInvalid()
                used = set()
                reserved = set(identical_notes.values())
                for index, choice in note_decisions.items():
                    if type(index) is not int or not isinstance(choice, dict) or set(choice) != {"decision", "target_id"}:
                        raise _BackupDecisionInvalid()
                    action, target_id = choice["decision"], choice["target_id"]
                    if not isinstance(action, str) or action not in {"KEEP", "SKIP", "OVERWRITE"} or type(target_id) is not int:
                        raise _BackupDecisionInvalid()
                    if action != "OVERWRITE":
                        if target_id != 0:
                            raise _BackupDecisionInvalid()
                        continue
                    candidates = actual_groups[similar_name_key(note_items[index]["title"])]
                    target = next((row for row in candidates if row["id"] == target_id), None)
                    if target is None:
                        raise _BackupDecisionInvalid()
                    if index in identical_notes:
                        continue
                    if target_id in used or target_id in reserved:
                        raise _BackupDecisionInvalid()
                    used.add(target_id)
                    note_targets[index] = target

            imported = 0
            overwritten = 0
            skipped = 0
            for item in password_items:
                platform = item["platform"]
                target = actual_conflicts.get(platform)
                if platform in identical_passwords or target is not None and decisions[platform] == "SKIP":
                    skipped += 1
                    continue
                enc_account = self._encrypt(item["account"]) if item["account"] else None
                enc_password = self._encrypt(item["password"]) if item["password"] else None
                enc_notes = self._encrypt(item["notes"]) if item["notes"] else None
                enc_totp = self._encrypt(item["totp_secret"]) if item["totp_secret"] else None
                codes = validate_codes(item.get("recovery_codes", []))
                enc_recovery = self._encrypt(dump_codes(codes)) if codes else None
                if self.last_error:
                    raise RuntimeError(self.last_error)
                values = (
                    platform,
                    enc_account,
                    enc_password,
                    enc_notes,
                    enc_totp,
                    item["strength"],
                    item["password_changed_at"],
                    item["updated_at"],
                    int(item["is_favorite"]),
                    enc_recovery,
                )
                if target is not None:
                    cursor = con.execute(
                        "UPDATE TTable SET platform=?, account=?, password=?, notes=?, "
                        "totp_secret=?, strength=?, password_changed_at=?, updated_at=?, "
                        "is_favorite=?, recovery_codes=? WHERE ID=?",
                        values + (target["id"],),
                    )
                    if cursor.rowcount != 1:
                        raise _BackupConflictChanged()
                    overwritten += 1
                else:
                    con.execute(
                        "INSERT INTO TTable "
                        "(platform, account, password, notes, totp_secret, strength, "
                        "password_changed_at, updated_at, is_favorite, recovery_codes) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        values,
                    )
                    imported += 1

            next_order = int(
                con.execute(
                    "SELECT COALESCE(MAX(sort_order), -1) + 1 FROM NotesTable"
                ).fetchone()[0]
            )
            ordered_notes = sorted(
                enumerate(note_items),
                key=lambda pair: (pair[1]["sort_order"], pair[0]),
            )
            for offset, (source_index, item) in enumerate(ordered_notes):
                choice = (note_decisions or {}).get(source_index, {"decision": "KEEP"})
                if source_index in identical_notes or choice["decision"] == "SKIP":
                    skipped += 1
                    continue
                enc_title = self._encrypt(item["title"])
                enc_content = self._encrypt(item["content"]) if item["content"] else None
                enc_created = self._encrypt(item["created_at"])
                enc_updated = self._encrypt(item["updated_at"])
                if self.last_error:
                    raise RuntimeError(self.last_error)
                target = note_targets.get(source_index)
                values = (enc_title, enc_content, enc_created, enc_updated,
                          target["sort_order"] if target is not None else next_order + offset,
                          int(item["is_favorite"]))
                if target is not None:
                    cursor = con.execute(
                        "UPDATE NotesTable SET title=?, content=?, created_at=?, updated_at=?, sort_order=?, is_favorite=? WHERE ID=?",
                        values + (target["id"],),
                    )
                    if cursor.rowcount != 1:
                        raise _BackupConflictChanged()
                    overwritten += 1
                    continue
                con.execute(
                    "INSERT INTO NotesTable "
                    "(title, content, created_at, updated_at, sort_order, is_favorite) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    values,
                )
                imported += 1
            if imported or overwritten:
                self._commit_bound(con)
            else:
                con.rollback()
                self._assert_bound_identity()
            return {
                "imported": imported,
                "overwritten": overwritten,
                "skipped": skipped,
            }
        except _BackupConflictChanged:
            if con is not None:
                con.rollback()
            self.last_error = "备份冲突已变化"
            self.last_error_kind = "backup_conflict_changed"
            return None
        except _BackupDecisionInvalid:
            if con is not None:
                con.rollback()
            self.last_error = "备份冲突决定不完整"
            self.last_error_kind = "invalid_argument"
            return None
        except Exception as exc:
            if con is not None:
                try:
                    con.rollback()
                except Exception:
                    pass
            self.last_error = f"导入备份失败: {exc}"
            self.last_error_kind = "database_io_failed"
            return None
        finally:
            if con is not None:
                try:
                    con.close()
                except Exception:
                    pass

    def export_everything(self) -> dict:
        """统一导出全部密码与记事

        返回结构：
            {"type":"unified","version":"2.0","export_time":...,
             "passwords":[...],"notes":[...]}
        解密失败返回空字典并通过 self.last_error 反馈错误。
        """
        self.last_error = None
        passwords = self.get_all_passwords()
        if self.last_error:
            return {}
        notes = self.get_all_notes()
        if self.last_error:
            return {}
        return {
            'type': 'unified',
            'version': '2.0',
            'export_time': datetime.datetime.now().isoformat(),
            'passwords': passwords,
            'notes': notes,
        }

    def import_data(self, data: dict, overwrite_platforms: set[str] | None = None) -> dict:
        """导入数据，自动识别格式（密码/记事/统一导出）

        参数 data 为已解析的字典或列表结构。
        返回 {"inserted":int, "overwritten":int, "skipped":int, "errors":list[str]}。
        - inserted: 新插入的密码 + 记事数量
        - skipped: 平台名重复跳过的数量
        - errors: 错误信息列表
        """
        self.last_error = None
        self.last_error_kind = None
        # Keep the historical parameter name for API compatibility.
        overwrite_platforms = {
            str(platform) for platform in (overwrite_platforms or ())
        }
        if not self.is_connected():
            self.last_error = "数据库未连接"
            return {'inserted': 0, 'overwritten': 0, 'skipped': 0, 'errors': ['数据库未连接']}

        # ---- 格式检测 ----
        password_items = []
        note_items = []

        if isinstance(data, dict) and data.get('type') in ('unified', 'password_manager_full_export'):
            password_items = data.get('passwords', []) or []
            note_items = data.get('notes', []) or []
        elif isinstance(data, list):
            if data:
                first_item = data[0]
                if isinstance(first_item, dict) and 'platform' in first_item:
                    password_items = data
                elif isinstance(first_item, dict) and 'title' in first_item:
                    note_items = data
                else:
                    self.last_error = "无法识别的文件格式"
                    return {'inserted': 0, 'overwritten': 0, 'skipped': 0, 'errors': ['无法识别的文件格式']}
        else:
            self.last_error = "无法识别的文件格式"
            return {'inserted': 0, 'overwritten': 0, 'skipped': 0, 'errors': ['无法识别的文件格式']}

        if not password_items and not note_items:
            self.last_error = "文件中没有可导入的数据"
            return {'inserted': 0, 'overwritten': 0, 'skipped': 0, 'errors': ['文件中没有可导入的数据']}

        seen_platforms: set[str] = set()
        for item in password_items:
            if not isinstance(item, dict):
                continue
            platform = item.get('platform', '')
            if not isinstance(platform, str) or not platform.strip():
                continue
            if platform in seen_platforms:
                self.last_error = f"导入包内存在重复平台名称：{platform}"
                self.last_error_kind = "invalid_argument"
                return {
                    'inserted': 0,
                    'overwritten': 0,
                    'skipped': 0,
                    'errors': [self.last_error],
                }
            seen_platforms.add(platform)

            favorite = item.get('is_favorite', 0)
            if type(favorite) not in {bool, int} or int(favorite) not in {0, 1}:
                self.last_error = "收藏状态无效"
                self.last_error_kind = "invalid_argument"
                return {'inserted': 0, 'overwritten': 0, 'skipped': 0, 'errors': ['收藏状态无效']}

        for note in note_items:
            if not isinstance(note, dict):
                self.last_error = "记事导入数据无效"
                self.last_error_kind = "invalid_argument"
                return {'inserted': 0, 'overwritten': 0, 'skipped': 0, 'errors': ['记事导入数据无效']}
            favorite = note.get('is_favorite', 0)
            if type(favorite) not in {bool, int} or int(favorite) not in {0, 1}:
                self.last_error = "收藏状态无效"
                self.last_error_kind = "invalid_argument"
                return {'inserted': 0, 'overwritten': 0, 'skipped': 0, 'errors': ['收藏状态无效']}

        pw_inserted = 0
        pw_overwritten = 0
        pw_skipped = 0
        note_inserted = 0
        errors = []
        con = None
        try:
            con = self._connect_bound()
            self._ensure_password_table_on(con)
            self._ensure_notes_table_on(con)

            # ---- 导入密码 ----
            for item in password_items:
                platform = item.get('platform', '')
                if not isinstance(platform, str) or not platform.strip():
                    pw_skipped += 1
                    continue
                account = item.get('account', '') or ''
                password = item.get('password', '') or ''
                notes = item.get('notes', '') or ''
                totp_secret = item.get('totp_secret', '') or ''
                recovery_codes = validate_codes(item.get('recovery_codes', []))
                is_favorite = int(item.get('is_favorite', 0))
                strength = item.get('strength')  # 明文，直接用
                if strength is None and password:
                    strength = self._compute_strength(password, platform, account)
                password_changed_at = item.get('password_changed_at')
                if password_changed_at is None:
                    password_changed_at = datetime.datetime.now().isoformat()
                updated_at = item.get('updated_at')
                if updated_at is None:
                    updated_at = password_changed_at

                enc_account = self._encrypt(account) if account else None
                enc_password = self._encrypt(password) if password else None
                enc_notes = self._encrypt(notes) if notes else None
                enc_totp = self._encrypt(totp_secret) if totp_secret else None
                enc_recovery = self._encrypt(dump_codes(recovery_codes)) if recovery_codes else None
                if self.last_error:
                    error = self.last_error
                    self.last_error = None
                    raise RuntimeError(f"加密失败（{platform}）: {error}")

                # 平台名重复默认跳过；UI 已确认覆盖时在同一事务内替换，
                # 保留目标记录 ID，并避免“先删后导入失败”的不可逆数据丢失。
                cur = con.execute(
                    "SELECT ID, platform FROM TTable WHERE platform=? LIMIT 1",
                    (platform,),
                )
                existing_row = cur.fetchone()
                exists = existing_row is not None
                if exists:
                    if platform not in overwrite_platforms:
                        pw_skipped += 1
                        continue
                    con.execute(
                        "UPDATE TTable SET platform=?, account=?, password=?, notes=?, "
                        "totp_secret=?, strength=?, password_changed_at=?, updated_at=?, "
                        "is_favorite=?, recovery_codes=? WHERE ID=?",
                        (
                            platform,
                            enc_account,
                            enc_password,
                            enc_notes,
                            enc_totp,
                            strength,
                            password_changed_at,
                            updated_at,
                            is_favorite,
                            enc_recovery,
                            existing_row[0],
                        ),
                    )
                    pw_overwritten += 1
                    continue
                try:
                    con.execute(
                        "INSERT INTO TTable "
                        "(platform, account, password, notes, totp_secret, strength, "
                        "password_changed_at, updated_at, is_favorite, recovery_codes) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (platform, enc_account, enc_password, enc_notes, enc_totp,
                         strength, password_changed_at, updated_at, is_favorite, enc_recovery)
                    )
                    pw_inserted += 1
                except Exception as e:
                    raise RuntimeError(f"插入 {platform} 失败: {e}") from e

            # ---- 导入记事 ----
            if note_items:
                cur = con.execute('SELECT COALESCE(MAX(sort_order), -1) FROM NotesTable')
                max_order = cur.fetchone()[0]
                sorted_notes = sorted(note_items, key=lambda x: x.get('sort_order', 0))

                for idx, note in enumerate(sorted_notes):
                    title = note.get('title', '') or ''
                    content = note.get('content', '') or ''
                    created_at = note.get('created_at', '') or ''
                    updated_at = note.get('updated_at', '') or ''
                    is_favorite = int(note.get('is_favorite', 0))

                    if not title:
                        errors.append("跳过空标题记事")
                        continue

                    enc_title = self._encrypt(title) if title else None
                    enc_content = self._encrypt(content) if content else None
                    enc_created = self._encrypt(created_at) if created_at else None
                    enc_updated = self._encrypt(updated_at) if updated_at else None
                    if self.last_error:
                        error = self.last_error
                        self.last_error = None
                        raise RuntimeError(f"加密记事失败（{title}）: {error}")

                    new_sort_order = max_order + 1 + idx
                    try:
                        con.execute(
                            "INSERT INTO NotesTable (title, content, created_at, updated_at, sort_order, is_favorite) "
                            "VALUES (?, ?, ?, ?, ?, ?)",
                            (enc_title, enc_content, enc_created, enc_updated, new_sort_order, is_favorite)
                        )
                        note_inserted += 1
                    except Exception as e:
                        raise RuntimeError(f"插入记事失败（{title}）: {e}") from e

            self._commit_bound(con)
            con.close()
            con = None
            return {
                'inserted': pw_inserted + note_inserted,
                'overwritten': pw_overwritten,
                'skipped': pw_skipped,
                'errors': errors,
            }
        except Exception as e:
            self.last_error = f"导入数据失败: {e}"
            errors.append(f"导入异常: {e}")
            if con is not None:
                try:
                    con.rollback()
                except Exception:
                    pass
                try:
                    con.close()
                except Exception:
                    pass
            return {
                'inserted': 0,
                'overwritten': 0,
                'skipped': 0,
                'errors': errors,
            }

    # ------------------------------------------------------------------
    # 数据库密码修改
    # ------------------------------------------------------------------

    @staticmethod
    def _emit_change_key_progress(
        callback: Callable[[str, int, int], None] | None,
        phase: ChangeKeyProgressPhase,
        completed: int,
        total: int,
    ) -> None:
        """Emit only a fixed phase plus bounded counters.

        Progress is observational.  A broken observer must neither abort nor
        alter a high-risk database operation.
        """

        if callback is None:
            return
        try:
            callback(phase.value, max(0, int(completed)), max(0, int(total)))
        except Exception:
            pass

    @staticmethod
    def _change_key_cancel_requested(
        callback: Callable[[], bool] | None,
    ) -> bool:
        if callback is None:
            return False
        try:
            return callback() is True
        except Exception:
            # Cancellation is optional input.  An observer failure cannot
            # create an ambiguous database state.
            return False

    @staticmethod
    def _change_key_file_sha256(path: str) -> str:
        digest = hashlib.sha256()
        with open(path, "rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    @staticmethod
    def _fsync_change_key_file(path: str) -> None:
        with open(path, "r+b") as handle:
            handle.flush()
            os.fsync(handle.fileno())

    @staticmethod
    def _verify_encrypted_fields(con, derived_key: bytes) -> None:
        """Authenticate every field ciphertext without retaining plaintext."""

        for row in con.execute(
            "SELECT account, password, notes, totp_secret, recovery_codes FROM TTable"
        ).fetchall():
            for value in row:
                if value:
                    CryptoHelper.decrypt_data(value, derived_key)
        for row in con.execute(
            "SELECT title, content, created_at, updated_at FROM NotesTable"
        ).fetchall():
            for value in row:
                if value:
                    CryptoHelper.decrypt_data(value, derived_key)

    def _verify_change_key_database(
        self,
        path: str,
        password: str,
        *,
        expected_salt: bytes | None = None,
        expected_derived_key: bytes | None = None,
        expected_file_sha256: str | None = None,
    ) -> tuple[bool, bytes | None]:
        """Verify file identity, sqleet key, salt, integrity, and field AEAD."""

        con = None
        try:
            if expected_file_sha256 is not None and not hmac.compare_digest(
                self._change_key_file_sha256(path),
                expected_file_sha256,
            ):
                return False, None
            con = sqleet.connect(path, key=password)
            row = con.execute(
                "SELECT value FROM _meta WHERE key='salt'"
            ).fetchone()
            if (
                row is None
                or len(row) != 1
                or not isinstance(row[0], str)
            ):
                return False, None
            salt = base64.b64decode(row[0], validate=True)
            if expected_salt is not None and not hmac.compare_digest(
                salt,
                expected_salt,
            ):
                return False, None
            derived_key = CryptoHelper.derive_key(password, salt)
            if (
                expected_derived_key is not None
                and not hmac.compare_digest(
                    derived_key,
                    expected_derived_key,
                )
            ):
                return False, None
            integrity_rows = con.execute("PRAGMA integrity_check").fetchall()
            if integrity_rows != [("ok",)]:
                return False, None
            self._verify_encrypted_fields(con, derived_key)
            return True, salt
        except Exception:
            return False, None
        finally:
            if con is not None:
                try:
                    con.close()
                except Exception:
                    pass

    def _create_change_key_snapshot(
        self,
        database_path: str,
        *,
        purpose: str = "change-key",
    ) -> tuple[str, str]:
        """Create and read back an fsynced same-directory encrypted snapshot."""

        snapshot_fd, snapshot_path = tempfile.mkstemp(
            prefix=f".{os.path.basename(database_path)}.{purpose}-",
            suffix=".bak",
            dir=os.path.dirname(database_path),
        )
        os.close(snapshot_fd)
        try:
            source_hash = self._change_key_file_sha256(database_path)
            shutil.copy2(database_path, snapshot_path)
            self._fsync_change_key_file(snapshot_path)
            snapshot_hash = self._change_key_file_sha256(snapshot_path)
            if not hmac.compare_digest(source_hash, snapshot_hash):
                raise OSError("change-key snapshot readback mismatch")
            return snapshot_path, snapshot_hash
        except Exception:
            try:
                os.remove(snapshot_path)
            except OSError:
                pass
            raise

    def _restore_change_key_snapshot(
        self,
        *,
        database_path: str,
        snapshot_path: str,
        snapshot_sha256: str,
        old_password: str,
        old_salt: bytes,
        old_derived_key: bytes,
        progress: Callable[[str, int, int], None] | None,
    ) -> bool:
        """Restore through an independent copy while preserving the original."""

        candidate_path = None
        self._emit_change_key_progress(
            progress,
            ChangeKeyProgressPhase.RESTORING,
            0,
            1,
        )
        try:
            if not os.path.isfile(snapshot_path):
                return False
            candidate_fd, candidate_path = tempfile.mkstemp(
                prefix=f".{os.path.basename(database_path)}.restore-",
                suffix=".candidate",
                dir=os.path.dirname(database_path),
            )
            os.close(candidate_fd)
            shutil.copy2(snapshot_path, candidate_path)
            self._fsync_change_key_file(candidate_path)
            if not hmac.compare_digest(
                self._change_key_file_sha256(candidate_path),
                snapshot_sha256,
            ):
                return False
            os.replace(candidate_path, database_path)
            candidate_path = None
            verified, _ = self._verify_change_key_database(
                database_path,
                old_password,
                expected_salt=old_salt,
                expected_derived_key=old_derived_key,
                expected_file_sha256=snapshot_sha256,
            )
            if verified:
                self._emit_change_key_progress(
                    progress,
                    ChangeKeyProgressPhase.RESTORING,
                    1,
                    1,
                )
            return verified
        except Exception:
            return False
        finally:
            if candidate_path is not None and os.path.exists(candidate_path):
                try:
                    os.remove(candidate_path)
                except OSError:
                    pass

    def _change_key_terminal_result(
        self,
        status: ChangeKeyStatus,
        recovery_snapshot_path: str | None = None,
    ) -> ChangeKeyResult:
        """Set only stable local error state; backend details never escape."""

        if status is ChangeKeyStatus.SUCCESS:
            self.last_error = None
            self.last_error_kind = None
        elif status is ChangeKeyStatus.CANCELLED:
            self.last_error = "修改数据库密码已取消"
            self.last_error_kind = "cancelled"
        elif status is ChangeKeyStatus.UNCHANGED:
            self.last_error = "修改数据库密码失败，数据库尚未修改"
            self.last_error_kind = "change_failed_unchanged"
        elif status is ChangeKeyStatus.RESTORED:
            self.last_error = "修改数据库密码失败，原数据库已恢复"
            self.last_error_kind = "change_failed_restored"
        else:
            self.last_error = "修改数据库密码失败且无法自动恢复"
            self.last_error_kind = "change_failed_recovery_failed"
        return ChangeKeyResult(
            status=status,
            recovery_snapshot_path=(
                recovery_snapshot_path
                if status is ChangeKeyStatus.RECOVERY_FAILED
                else None
            ),
        )

    def _reencrypt_all_data(
        self,
        con,
        old_key: bytes,
        new_key: bytes,
        *,
        should_cancel: Callable[[], bool] | None = None,
        progress: Callable[[str, int, int], None] | None = None,
    ):
        """用旧密钥解密全部数据，再用新密钥重新加密（调用方负责 con 的生命周期）

        必须包含 totp_secret 字段（风险 G.1：双层加密字段同步）。
        is_favorite / strength / password_changed_at 为明文字段，原样回写。
        """
        # TTable: 用显式列名 SELECT，避免列顺序问题
        password_rows = con.execute(
            "SELECT ID, account, password, notes, totp_secret, strength, "
            "password_changed_at, is_favorite, recovery_codes FROM TTable"
        ).fetchall()
        note_rows = con.execute(
            "SELECT ID, title, content, created_at, updated_at, is_favorite FROM NotesTable"
        ).fetchall()
        total = len(password_rows) + len(note_rows)
        completed = 0
        self._emit_change_key_progress(
            progress,
            ChangeKeyProgressPhase.ENCRYPTING,
            completed,
            total,
        )
        for row in password_rows:
            if self._change_key_cancel_requested(should_cancel):
                raise _ChangeKeyCancelled()
            account = CryptoHelper.decrypt_data(row[1], old_key) if row[1] else None
            password = CryptoHelper.decrypt_data(row[2], old_key) if row[2] else None
            notes = CryptoHelper.decrypt_data(row[3], old_key) if row[3] else None
            totp_secret = CryptoHelper.decrypt_data(row[4], old_key) if row[4] else None
            recovery_text = CryptoHelper.decrypt_data(row[8], old_key) if row[8] else None
            if recovery_text is not None:
                load_codes(recovery_text)
            # 明文字段，原样回写
            strength = row[5]
            password_changed_at = row[6]
            is_favorite = row[7] if row[7] is not None else 0
            con.execute(
                "UPDATE TTable SET account=?, password=?, notes=?, totp_secret=?, "
                "strength=?, password_changed_at=?, is_favorite=?, recovery_codes=? WHERE ID=?",
                (CryptoHelper.encrypt_data(account, new_key) if account else None,
                 CryptoHelper.encrypt_data(password, new_key) if password else None,
                 CryptoHelper.encrypt_data(notes, new_key) if notes else None,
                 CryptoHelper.encrypt_data(totp_secret, new_key) if totp_secret else None,
                 strength, password_changed_at, is_favorite,
                 CryptoHelper.encrypt_data(recovery_text, new_key) if recovery_text is not None else None, row[0])
            )
            completed += 1
            self._emit_change_key_progress(
                progress,
                ChangeKeyProgressPhase.ENCRYPTING,
                completed,
                total,
            )
        # NotesTable: title / content / created_at / updated_at 加密
        for row in note_rows:
            if self._change_key_cancel_requested(should_cancel):
                raise _ChangeKeyCancelled()
            title = CryptoHelper.decrypt_data(row[1], old_key) if row[1] else None
            content = CryptoHelper.decrypt_data(row[2], old_key) if row[2] else None
            created = CryptoHelper.decrypt_data(row[3], old_key) if row[3] else None
            updated = CryptoHelper.decrypt_data(row[4], old_key) if row[4] else None
            is_favorite = row[5] if row[5] is not None else 0
            con.execute(
                "UPDATE NotesTable SET title=?, content=?, created_at=?, updated_at=?, is_favorite=? "
                "WHERE ID=?",
                (CryptoHelper.encrypt_data(title, new_key) if title else None,
                 CryptoHelper.encrypt_data(content, new_key) if content else None,
                 CryptoHelper.encrypt_data(created, new_key) if created else None,
                 CryptoHelper.encrypt_data(updated, new_key) if updated else None,
                 is_favorite, row[0])
            )
            completed += 1
            self._emit_change_key_progress(
                progress,
                ChangeKeyProgressPhase.ENCRYPTING,
                completed,
                total,
            )
        if self._change_key_cancel_requested(should_cancel):
            raise _ChangeKeyCancelled()

    def change_key_atomic(
        self,
        new_password: str,
        *,
        should_cancel: Callable[[], bool] | None = None,
        authorize_commit: Callable[[], bool] | None = None,
        progress: Callable[[str, int, int], None] | None = None,
    ) -> ChangeKeyResult:
        """Atomically re-encrypt the database and return its verified state.

        ``should_cancel`` is cooperative only before the first ``commit``.
        ``authorize_commit`` is called exactly once immediately before that
        boundary; anything other than an explicit ``True`` cancels.  Once the
        boundary is authorized, cancellation is deliberately ignored and the
        operation converges to SUCCESS, RESTORED, or RECOVERY_FAILED.

        ``progress`` receives only ``(fixed_phase, completed, total)``.  It is
        observational and cannot affect the database operation.
        """

        self.last_error = None
        self.last_error_kind = None
        if not self.is_connected():
            self.last_error = "数据库未连接"
            self.last_error_kind = "not_connected"
            return ChangeKeyResult(ChangeKeyStatus.UNCHANGED)
        if not self.bound_identity_is_current():
            self.last_error = "数据库文件已消失或被替换"
            self.last_error_kind = "database_identity_changed"
            return ChangeKeyResult(ChangeKeyStatus.UNCHANGED)
        if new_password is None:
            self.last_error = "新密码缺失"
            self.last_error_kind = "new_password_missing"
            return ChangeKeyResult(ChangeKeyStatus.UNCHANGED)
        if not isinstance(new_password, str):
            self.last_error = "新密码类型无效"
            self.last_error_kind = "invalid_argument"
            return ChangeKeyResult(ChangeKeyStatus.UNCHANGED)
        for callback in (should_cancel, authorize_commit, progress):
            if callback is not None and not callable(callback):
                self.last_error = "改密回调无效"
                self.last_error_kind = "invalid_argument"
                return ChangeKeyResult(ChangeKeyStatus.UNCHANGED)

        if self._change_key_cancel_requested(should_cancel):
            return self._change_key_terminal_result(ChangeKeyStatus.CANCELLED)

        database_path = os.path.abspath(self.db_name)
        old_password = self.db_key
        original_buffer = self.derived_key
        old_derived_key = None
        old_salt = None
        new_derived_key = None
        new_buffer = None
        snapshot_path = None
        snapshot_sha256 = None
        con = None
        commit_boundary_crossed = False
        old_buffer_touched = False

        def close_connection(*, rollback: bool) -> None:
            nonlocal con
            if con is None:
                return
            try:
                if rollback:
                    con.rollback()
            except Exception:
                pass
            try:
                con.close()
            except Exception:
                pass
            con = None

        def ensure_old_buffer_after_restore() -> bool:
            nonlocal original_buffer
            if not old_buffer_touched:
                return True
            replacement = None
            try:
                replacement = SecureKeyBuffer(old_derived_key)
                try:
                    original_buffer.destroy()
                except Exception:
                    pass
                self.derived_key = replacement
                self.db_key = old_password
                original_buffer = replacement
                return True
            except Exception:
                if replacement is not None:
                    try:
                        replacement.destroy()
                    except Exception:
                        pass
                return False

        def remove_snapshot() -> bool:
            nonlocal snapshot_path
            if snapshot_path is None:
                return True
            try:
                os.remove(snapshot_path)
                snapshot_path = None
                return True
            except OSError:
                return False

        def refresh_identity_after_restore() -> bool:
            """只在已验证的内部恢复替换后接受新的文件对象身份。"""

            try:
                self.opened_file_identity = self._path_identity(
                    Path(database_path)
                )
                return True
            except Exception:
                return False

        def recover_from_snapshot() -> ChangeKeyResult:
            nonlocal new_buffer
            close_connection(rollback=False)
            if new_buffer is not None:
                try:
                    new_buffer.destroy()
                except Exception:
                    pass
                new_buffer = None
            if (
                snapshot_path is None
                or snapshot_sha256 is None
                or old_salt is None
                or old_derived_key is None
                or not self._restore_change_key_snapshot(
                    database_path=database_path,
                    snapshot_path=snapshot_path,
                    snapshot_sha256=snapshot_sha256,
                    old_password=old_password,
                    old_salt=old_salt,
                    old_derived_key=old_derived_key,
                    progress=progress,
                )
                or not ensure_old_buffer_after_restore()
                or not refresh_identity_after_restore()
                or not remove_snapshot()
            ):
                self._emit_change_key_progress(
                    progress,
                    ChangeKeyProgressPhase.FINALIZING,
                    0,
                    1,
                )
                return self._change_key_terminal_result(
                    ChangeKeyStatus.RECOVERY_FAILED,
                    snapshot_path
                    if snapshot_path is not None
                    and os.path.exists(snapshot_path)
                    else None,
                )
            self._emit_change_key_progress(
                progress,
                ChangeKeyProgressPhase.FINALIZING,
                1,
                1,
            )
            return self._change_key_terminal_result(ChangeKeyStatus.RESTORED)

        def finish_precommit(
            status: ChangeKeyStatus,
        ) -> ChangeKeyResult:
            close_connection(rollback=True)
            verified = False
            if (
                old_salt is not None
                and old_derived_key is not None
                and snapshot_sha256 is not None
            ):
                verified, _ = self._verify_change_key_database(
                    database_path,
                    old_password,
                    expected_salt=old_salt,
                    expected_derived_key=old_derived_key,
                    expected_file_sha256=snapshot_sha256,
                )
            if verified:
                if remove_snapshot():
                    return self._change_key_terminal_result(status)
                return self._change_key_terminal_result(
                    ChangeKeyStatus.RECOVERY_FAILED,
                    snapshot_path,
                )
            return recover_from_snapshot()

        try:
            old_derived_key = original_buffer.use()
            try:
                original_buffer.lock()
            except Exception:
                pass
            self._emit_change_key_progress(
                progress,
                ChangeKeyProgressPhase.VALIDATING,
                0,
                1,
            )
            healthy, old_salt = self._verify_change_key_database(
                database_path,
                old_password,
                expected_derived_key=old_derived_key,
            )
            if not healthy or old_salt is None:
                return self._change_key_terminal_result(
                    ChangeKeyStatus.UNCHANGED
                )
            self._emit_change_key_progress(
                progress,
                ChangeKeyProgressPhase.VALIDATING,
                1,
                1,
            )
            if self._change_key_cancel_requested(should_cancel):
                return self._change_key_terminal_result(
                    ChangeKeyStatus.CANCELLED
                )

            self._emit_change_key_progress(
                progress,
                ChangeKeyProgressPhase.READING,
                0,
                1,
            )
            snapshot_path, snapshot_sha256 = self._create_change_key_snapshot(
                database_path
            )
            self._emit_change_key_progress(
                progress,
                ChangeKeyProgressPhase.READING,
                1,
                1,
            )
            if self._change_key_cancel_requested(should_cancel):
                return finish_precommit(ChangeKeyStatus.CANCELLED)

            con = self._connect_bound()
            salt_row = con.execute(
                "SELECT value FROM _meta WHERE key='salt'"
            ).fetchone()
            if (
                salt_row is None
                or len(salt_row) != 1
                or not isinstance(salt_row[0], str)
            ):
                raise RuntimeError("change-key salt unavailable")
            transaction_salt = base64.b64decode(
                salt_row[0],
                validate=True,
            )
            if not hmac.compare_digest(transaction_salt, old_salt):
                raise RuntimeError("change-key salt changed")

            self._emit_change_key_progress(
                progress,
                ChangeKeyProgressPhase.DERIVING_KEY,
                0,
                1,
            )
            new_derived_key = CryptoHelper.derive_key(
                new_password,
                transaction_salt,
            )
            self._emit_change_key_progress(
                progress,
                ChangeKeyProgressPhase.DERIVING_KEY,
                1,
                1,
            )
            if self._change_key_cancel_requested(should_cancel):
                return finish_precommit(ChangeKeyStatus.CANCELLED)

            con.execute("BEGIN IMMEDIATE")
            self._reencrypt_all_data(
                con,
                old_derived_key,
                new_derived_key,
                should_cancel=should_cancel,
                progress=progress,
            )
            if self._change_key_cancel_requested(should_cancel):
                raise _ChangeKeyCancelled()

            self._emit_change_key_progress(
                progress,
                ChangeKeyProgressPhase.COMMITTING,
                0,
                1,
            )
            if authorize_commit is not None:
                try:
                    authorized = authorize_commit() is True
                except Exception:
                    authorized = False
                if not authorized:
                    raise _ChangeKeyCancelled()

            # No cancellation checks are permitted beyond this assignment.
            commit_boundary_crossed = True
            self._commit_bound(con)
            self._emit_change_key_progress(
                progress,
                ChangeKeyProgressPhase.COMMITTING,
                1,
                1,
            )

            self._emit_change_key_progress(
                progress,
                ChangeKeyProgressPhase.WRITING,
                0,
                1,
            )
            con.change_key(new_password)
            self._assert_bound_identity()
            self._emit_change_key_progress(
                progress,
                ChangeKeyProgressPhase.WRITING,
                1,
                1,
            )
            close_connection(rollback=False)

            self._emit_change_key_progress(
                progress,
                ChangeKeyProgressPhase.FINALIZING,
                0,
                3,
            )
            verified, _ = self._verify_change_key_database(
                database_path,
                new_password,
                expected_salt=old_salt,
                expected_derived_key=new_derived_key,
            )
            if not verified:
                raise RuntimeError("change-key new database verification failed")
            self._emit_change_key_progress(
                progress,
                ChangeKeyProgressPhase.FINALIZING,
                1,
                3,
            )
            new_buffer = SecureKeyBuffer(new_derived_key)
            self._emit_change_key_progress(
                progress,
                ChangeKeyProgressPhase.FINALIZING,
                2,
                3,
            )

            # Keep the verified recovery point until both the new buffer and
            # destruction of the old native buffer have succeeded.
            old_buffer_touched = True
            original_buffer.destroy()
            self.derived_key = None
            if not remove_snapshot():
                raise OSError("change-key snapshot cleanup failed")

            self.db_key = new_password
            self.derived_key = new_buffer
            new_buffer = None
            self._emit_change_key_progress(
                progress,
                ChangeKeyProgressPhase.FINALIZING,
                3,
                3,
            )
            return self._change_key_terminal_result(ChangeKeyStatus.SUCCESS)
        except _ChangeKeyCancelled:
            return finish_precommit(ChangeKeyStatus.CANCELLED)
        except Exception:
            close_connection(rollback=not commit_boundary_crossed)
            if snapshot_path is None or snapshot_sha256 is None:
                return self._change_key_terminal_result(
                    ChangeKeyStatus.UNCHANGED
                )
            if not commit_boundary_crossed:
                return finish_precommit(ChangeKeyStatus.UNCHANGED)
            return recover_from_snapshot()
        finally:
            close_connection(rollback=not commit_boundary_crossed)
            if new_buffer is not None:
                try:
                    new_buffer.destroy()
                except Exception:
                    pass

    def change_key(self, new_password: str) -> bool:
        """Backward-compatible bool wrapper around ``change_key_atomic``."""

        return bool(self.change_key_atomic(new_password))
