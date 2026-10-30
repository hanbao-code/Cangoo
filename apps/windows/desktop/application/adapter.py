"""产品命令到核心业务的适配器；统一管理当前会话、后台任务与结果交付。"""

from __future__ import annotations

import base64
import copy
from concurrent.futures import Future, ThreadPoolExecutor
from contextvars import ContextVar
from dataclasses import dataclass
import datetime
from functools import partial, wraps
import hashlib
import hmac
import json
import math
import os
from pathlib import Path
import re
import secrets
import threading
import time
from typing import Callable, Protocol

from core.config import ConfigManager, DEFAULT_SETTINGS
from core.backup import BackupError, decrypt_backup_v2, encrypt_backup_v2, backup_note_groups, similar_name_key
from core.database import (
    ChangeKeyResult,
    ChangeKeyStatus,
    CurrentPasswordStatus,
    DatabaseService,
    StrengthEvaluationCancelled,
    StrengthEvaluationError,
)
from core.health import HealthTool
from core.password_tools import PasswordTools
from core.hotkey_parser import (
    check_hotkey_conflict,
    is_hotkey_main_key,
    parse_hotkey,
)
from core.security import SecurityService, SecurityStateCommitError
from core.totp import TOTPTool
from core.recovery_codes import RecoveryCodeError, parse_codes, validate_codes
from core.search import field_matches_query
from desktop.bridge.command_ids import CommandId
from desktop.bridge.protocol import (
    AdapterCompletion,
    AdapterRequest,
    CompletionCallback,
)

from .database_targets import (
    DatabaseTarget,
    DatabaseTargetKind,
    DatabaseTargetSelector,
)
from .backup import (
    BackupController,
    BackupFileSelector,
    BackupPreview,
    BackupPreviewDraft,
    BackupRejected,
    BackupSelection,
    ExportSelection,
    NullBackupFileSelector,
    file_identity as backup_file_identity,
    encode_transfer_payload,
    parse_received_payload,
    publish_envelope,
    read_backup_file,
    source_matches,
)
from .clipboard import ProductClipboardController
from .health_rescan import HealthRescan, SessionStrengthQueue, strength_input_token
from .record_field_reads import (
    FieldReadRejected,
    RecordFieldReads,
    field_is_long,
    field_preview,
)
from desktop.runtime_paths import RuntimePaths
from .settings_store import AtomicSettingsStore, SettingsCommitError
from desktop.ui_font_scale import normalize_ui_font_scale
from .strength_worker import (
    StrengthAnalysisCancelled,
    StrengthWorkerError,
    analyze_strength_in_process,
)

_RATING_QUEUE = ContextVar("record_rating_queue", default=None)
_PENDING_STRENGTHS = {"PENDING", "CHECKING", "FAILED"}


_CONTRACT_VERSION = "1.1.0"
_SELECTION_TTL_MS = 300_000
_MAX_SELECTION_TICKETS = 32
_DELETE_TICKET_TTL_MS = 60_000
_MAX_DELETE_TICKETS = 32
_REVISION_WIDTH = 16
_HOTKEY = re.compile(r"^[A-Za-z0-9+`=\[\]\\;',./ -]{3,64}$")
_CHANGE_KEY_PROGRESS_PHASES = {
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
_MAX_CHANGE_KEY_PROGRESS_RECORDS = 64
_MAX_SETTINGS_PUBLICATIONS = 64
_MAX_GENERATED_SECRET_LEASES = 64
_NATIVE_CHANGE_KEY_SETTLEMENTS = frozenset(
    {
        "SUCCESS",
        "RESTORED",
        "RECOVERY_FAILED",
        "REVERSIBLE_ABORTED",
        "INTERNAL_FAILURE",
    }
)

_ChangeKeyProgressSink = Callable[[str, int, int, str, int, int], None]
_EffectiveThemeProvider = Callable[[], str]
_HotkeyDispatch = Callable[[Callable[[], object]], object]


class _NativeHotkeyPort(Protocol):
    @property
    def registered(self) -> bool: ...

    @property
    def current_hotkey(self) -> str | None: ...

    def register(self, hotkey: str) -> bool: ...

    def replace_preserving(self, hotkey: str) -> bool: ...

    def unregister(self) -> None: ...


@dataclass(frozen=True, slots=True)
class _SelectionTicket:
    value: str
    page_epoch: int
    target: DatabaseTarget
    file_identity: tuple[int, int, int, int] | None
    expires_at: float


@dataclass(frozen=True, slots=True)
class _DeleteTicket:
    value: str
    page_epoch: int
    session_epoch: int
    record_id: int
    revision: str
    entity_label: str
    entity_kind: str
    expires_at: float


@dataclass(slots=True)
class _GeneratedSecret:
    lease_id: str
    page_epoch: int
    expires_at: float
    password: str
    expiry_timer: threading.Timer


@dataclass(frozen=True, slots=True)
class _DeleteTicketDraft:
    record_id: int
    revision: str
    entity_label: str
    entity_kind: str = "RECORD"


@dataclass(slots=True)
class _OpenOperation:
    request_id: str
    token: int
    page_epoch: int
    ticket: _SelectionTicket
    complete: CompletionCallback
    cancelled: threading.Event
    settled: threading.Event
    future: Future["_OpenResult"] | None = None


@dataclass(slots=True)
class _OpenResult:
    database: DatabaseService | None
    path: Path
    error_code: str
    password_count: int = 0
    note_count: int = 0
    file_identity: tuple[int, int, int, int] | None = None


@dataclass(slots=True)
class _SessionReadOperation:
    request_id: str
    token: int
    command_id: CommandId
    page_epoch: int
    session_epoch: int
    database: DatabaseService
    complete: CompletionCallback
    cancelled: threading.Event
    settled: threading.Event
    future: Future["_SessionReadResult"] | None = None
    record_field_read_id: str = ""
    editor_revision_only: bool = False


@dataclass(slots=True)
class _SessionReadResult:
    error_code: str
    result: dict[str, object] | None = None
    error_argument_index: int = 0
    delete_ticket_draft: _DeleteTicketDraft | None = None
    delivery_deadline: float | None = None
    guidance_snapshot: "_HealthGuidanceSnapshot | None" = None
    strength_input_changed: bool = False


@dataclass(slots=True)
class _PageSecretOperation:
    request_id: str
    token: int
    command_id: CommandId
    page_epoch: int
    complete: CompletionCallback
    cancelled: threading.Event
    settled: threading.Event
    future: Future["_SessionReadResult"] | None = None


@dataclass(slots=True)
class _ChangeKeyOperation:
    request_id: str
    token: int
    page_epoch: int
    session_epoch: int
    database: DatabaseService
    complete: CompletionCallback
    cancelled: threading.Event
    settled: threading.Event
    irreversible: bool = False
    commit_started: bool = False
    progress: list[tuple[str, int, int]] | None = None
    recovery_snapshot_path: str | None = None
    future: Future["_ChangeKeyWorkerResult"] | None = None


@dataclass(slots=True)
class _ChangeKeyWorkerResult:
    current_password_status: CurrentPasswordStatus
    change_result: ChangeKeyResult | None = None
    cancelled: bool = False


@dataclass(frozen=True, slots=True)
class _NativeChangeKeySettlement:
    token: int
    outcome: str


@dataclass(slots=True)
class _SettingsOperation:
    request_id: str
    token: int
    command_id: CommandId
    page_epoch: int
    session_epoch: int
    setting_key: str
    setting_value: object
    complete: CompletionCallback
    settled: threading.Event
    future: Future["_SettingsWorkerResult"] | None = None


@dataclass(slots=True)
class _BackupOperation:
    request_id: str
    token: int
    command_id: CommandId
    page_epoch: int
    session_epoch: int
    database: DatabaseService
    complete: CompletionCallback
    cancelled: threading.Event
    settled: threading.Event
    selection: BackupSelection | None = None
    preview: BackupPreview | None = None
    commit_started: bool = False
    future: Future["_BackupWorkerResult"] | None = None
    native_transfer: bool = False


@dataclass(slots=True)
class _BackupWorkerResult:
    error_code: str
    result: dict[str, object] | None = None
    preview_draft: BackupPreviewDraft | None = None
    selection_update: tuple[ExportSelection, int, dict, dict] | None = None


@dataclass(frozen=True, slots=True)
class _HealthGuidanceSnapshot:
    guidance_id: str
    page_epoch: int
    session_epoch: int
    entries: tuple[tuple[int, tuple[str, ...]], ...]


@dataclass(frozen=True, slots=True)
class _SettingsWorkerResult:
    error_code: str
    changed: bool = False
    settings_revision: str = ""
    settings: dict[str, object] | None = None
    warning: str = "NONE"


@dataclass(frozen=True, slots=True)
class SettingsCommitPublication:
    """Native-only evidence that the local public authority changed."""

    command_id: CommandId
    page_epoch: int
    session_epoch: int
    settings_revision: str
    settings: dict[str, object]


@dataclass(frozen=True, slots=True)
class _VaultRecord:
    record_id: int
    revision: str
    platform: str
    account: str
    notes: str
    strength: str
    favorite: bool
    duplicate_group: int
    similar_group: int
    has_password: bool
    has_totp: bool
    long_fields: tuple[str, ...]
    updated_at: str
    updated_date: str
    password_changed_date: str
    health_password_changed_at: str | None


@dataclass(frozen=True, slots=True)
class _NoteRecord:
    note_id: int
    revision: str
    title: str
    content: str
    created_at: str
    updated_at: str
    sort_order: int
    favorite: bool


class ApplicationAdapter:
    """产品命令与核心业务适配。

    只接收已验证的 RuntimePaths 路径端口。数据库创建、派生及有界读取进入既有后台执行器；
    页面或会话失效时等待在途操作并释放产生的核心会话，再向原生安全协调器返回。
    """

    def __init__(
        self,
        isolation: RuntimePaths,
        selector: DatabaseTargetSelector,
        clipboard: ProductClipboardController,
        *,
        hotkey: _NativeHotkeyPort | None = None,
        backup_selector: BackupFileSelector | None = None,
        clock: Callable[[], float] = time.monotonic,
        failure_retry_ms: int,
        effective_theme_provider: _EffectiveThemeProvider | None = None,
        hotkey_dispatch: _HotkeyDispatch | None = None,
    ) -> None:
        self._isolation = isolation
        self._selector = selector
        self._backup_selector = backup_selector or NullBackupFileSelector()
        self._backup = BackupController(self._backup_selector, clock=clock)
        self._clipboard = clipboard
        self._clock = clock
        if (
            type(failure_retry_ms) is not int
            or not 1 <= failure_retry_ms <= 86_400_000
        ):
            raise ValueError("failure_retry_ms must be a bounded integer")
        if (
            effective_theme_provider is not None
            and not callable(effective_theme_provider)
        ):
            raise TypeError("effective_theme_provider must be callable")
        self._failure_retry_ms = failure_retry_ms
        self._effective_theme_provider = (
            effective_theme_provider
            if effective_theme_provider is not None
            else (lambda: "DARK")
        )
        if hotkey_dispatch is not None and not callable(hotkey_dispatch):
            raise TypeError("hotkey_dispatch must be callable")
        self._hotkey_dispatch = hotkey_dispatch or (lambda action: action())
        self._lock = threading.RLock()
        self._executor = ThreadPoolExecutor(
            max_workers=1,
            thread_name_prefix="pdm-m4-core",
        )
        self._settings_executor = ThreadPoolExecutor(
            max_workers=1,
            thread_name_prefix="pdm-m4-settings",
        )
        self._strength_executor = ThreadPoolExecutor(
            max_workers=1,
            thread_name_prefix="pdm-m4-strength",
        )
        self._config = ConfigManager(str(isolation.settings_file))
        source_settings = self._read_m4_settings_source(
            isolation.settings_file
        )
        self._config.load(create_if_missing=False)
        if source_settings is None or "theme" not in source_settings:
            self._config.set("theme", "dark")
        if source_settings is None or "language" not in source_settings:
            self._config.set("language", "zh")
        self._settings_store = AtomicSettingsStore(
            self._config,
            isolation.settings_file,
        )
        self._update_controller = None
        self._hotkey = hotkey
        self._quickbar_registration = "DISABLED"
        if hotkey is not None:
            hotkey.unregister()
        self._native_effective_theme = self._read_effective_theme_provider()
        clipboard_mode = self._clipboard_mode()
        clipboard_seconds = self._clipboard_seconds()
        self._clipboard.configure(clipboard_mode, clipboard_seconds)
        self._security = SecurityService(str(isolation.security_file))
        self._tickets: dict[str, _SelectionTicket] = {}
        self._delete_tickets: dict[str, _DeleteTicket] = {}
        self._record_field_reads = RecordFieldReads(clock=clock)
        self._note_field_reads = RecordFieldReads(clock=clock)
        self._generated_secrets: dict[str, _GeneratedSecret] = {}
        self._operations: dict[
            str,
            _OpenOperation
            | _SessionReadOperation
            | _PageSecretOperation
            | _ChangeKeyOperation
            | _BackupOperation,
        ] = {}
        self._settings_operations: dict[str, _SettingsOperation] = {}
        self._settings_publications: dict[
            str,
            SettingsCommitPublication,
        ] = {}
        self._settings_invalidating_sessions: set[int] = set()
        self._health_guidance: _HealthGuidanceSnapshot | None = None
        self._released_health_guidance_id = ""
        self._health_rescan: HealthRescan | None = None
        self._strength_changed_sink: Callable[[int, int], None] | None = None
        self._health_edit_lock = threading.Lock()
        self._health_edit_leases: dict[str, tuple[int, float]] = {}
        self._editor_occupancy: tuple[str, int, int, str] | None = None
        self._valid_pages: set[int] = set()
        self._recent_ids: dict[str, str] = {}
        self._recent_paths_by_id: dict[str, Path] = {}
        self._expected_existing_paths_by_page: dict[
            int,
            set[str],
        ] = {}
        self._database: DatabaseService | None = None
        self._database_path: Path | None = None
        self._session_token = 0
        self._session_epoch = 0
        self._session_revision_key: bytes | None = None
        self._next_page_epoch = 1
        self._next_session_epoch = 1
        self._revision = 1
        self._last_change_key_progress: tuple[
            tuple[str, int, int], ...
        ] = ()
        self._change_key_recovery_snapshot_path: str | None = None
        self._native_change_key_settlement: (
            _NativeChangeKeySettlement | None
        ) = None
        self._change_key_progress_sink: _ChangeKeyProgressSink | None = None
        self._closed = False

    @property
    def active_database_path(self) -> Path | None:
        with self._lock:
            return self._database_path

    def _submit_worker(self, worker, *arguments, **keywords):
        """将只读评级投影限定在本次后台调用，调用结束立即恢复上下文。"""
        queue = self._health_rescan
        @wraps(worker)
        def run():
            token = _RATING_QUEUE.set(queue if isinstance(queue, SessionStrengthQueue) else None)
            try:
                return worker(*arguments, **keywords)
            finally:
                _RATING_QUEUE.reset(token)
        return self._executor.submit(run)

    def set_strength_changed_sink(self, sink: Callable[[int, int], None]) -> None:
        self._strength_changed_sink = sink

    def publish_strength_change(self, page_epoch: int, session_epoch: int) -> tuple[str, str, str] | None:
        with self._lock:
            if self._closed or page_epoch not in self._valid_pages or session_epoch != self._session_epoch:
                return None
            self._revision += 1
            return self.current_data_revisions()

    def _start_strength_queue(self, page_epoch: int) -> None:
        if self._database is None or self._session_revision_key is None:
            return
        epoch = self._session_epoch
        def changed():
            sink = self._strength_changed_sink
            if sink is not None:
                sink(page_epoch, epoch)
        queue = SessionStrengthQueue(
            self._database, self._executor, self._record_is_being_edited,
            revision_key=self._session_revision_key, on_change=changed)
        self._health_rescan = queue
        queue.start()

    @property
    def has_core_session(self) -> bool:
        with self._lock:
            database = self._database
            return (
                database is not None
                and database.derived_key is not None
            )

    @property
    def pending_operation_count(self) -> int:
        with self._lock:
            scan = self._health_rescan
            scanning = scan.busy if isinstance(scan, SessionStrengthQueue) else scan is not None and not scan.settled.is_set()
            return len(self._operations) + len(self._settings_operations) + int(scanning)

    @property
    def editor_occupancy(self) -> tuple[str, int, int, str] | None:
        with self._health_edit_lock:
            return self._editor_occupancy

    def set_backup_window_parent(self, parent) -> None:
        setter = getattr(self._backup_selector, "set_parent", None)
        if setter is not None:
            setter(parent)

    def close_backup_window(self, page_epoch: int) -> None:
        with self._lock:
            self._backup.clear_page(page_epoch)

    def export_transfer_snapshot(self, page_epoch: int, session_epoch: int, scope: str,
                                 complete: CompletionCallback) -> str:
        """原生发送任务取得固定业务字节；结果不经过网页 Bridge。"""
        return self._submit_transfer_snapshot(page_epoch, session_epoch, CommandId.C51, scope, None, 0, 0, complete)

    def transfer_vault_name(self, page_epoch: int, session_epoch: int) -> str:
        with self._lock:
            if self._closed or page_epoch not in self._valid_pages:
                raise BackupRejected("STALE_PAGE")
            if self._database is None or self._database_path is None or self._session_epoch <= 0:
                raise BackupRejected("SESSION_REQUIRED")
            if session_epoch != self._session_epoch or not self._database.bound_identity_is_current():
                raise BackupRejected("STALE_SESSION")
            name = self._database_path.name
            if not name or "\x00" in name or len(name) > 256 or len(name.encode("utf-8")) > 1024:
                raise BackupRejected("INVALID_ARGUMENT")
            return name

    def install_received_snapshot(self, page_epoch: int, session_epoch: int, encoded: bytes,
                                   expected_scope: str, expected_password_count: int, expected_note_count: int,
                                   complete: CompletionCallback) -> str:
        """仅供已完整认证的原生接收任务安装比较来源。"""
        return self._submit_transfer_snapshot(page_epoch, session_epoch, CommandId.C53, expected_scope, encoded,
                                             expected_password_count, expected_note_count, complete)

    def _submit_transfer_snapshot(self, page_epoch: int, session_epoch: int, command_id: CommandId, scope: str,
                                  encoded: bytes | None, password_count: int, note_count: int,
                                  complete: CompletionCallback) -> str:
        request_id = "transfer_" + secrets.token_urlsafe(24)
        request = AdapterRequest(command_id, request_id, 0, page_epoch, session_epoch, (), ())
        with self._lock:
            error = self._backup_operation_error_locked(request)
            if error:
                complete(self._error(request, error))
                return request_id
            database, revision_key = self._database, self._session_revision_key
            if database is None or revision_key is None:
                complete(self._error(request, "SESSION_REQUIRED"))
                return request_id
            export_selection = None
            if command_id is CommandId.C51:
                try:
                    scope, export_selection = self._backup.export_choice(page_epoch, session_epoch, scope)
                except BackupRejected as exc:
                    complete(self._error(request, str(exc)))
                    return request_id
            operation = _BackupOperation(request_id, 0, command_id, page_epoch, session_epoch, database,
                                         complete, threading.Event(), threading.Event(), native_transfer=True)
            self._operations[request_id] = operation
            future = self._submit_worker(self._transfer_snapshot_worker, database, revision_key, scope, encoded,
                                         password_count, note_count, command_id is CommandId.C53, operation.cancelled,
                                         export_selection)
            operation.future = future
            future.add_done_callback(lambda finished: self._finish_backup_operation(request_id, finished))
        return request_id

    def cancel_transfer_snapshot(self, request_id: str) -> str:
        with self._lock:
            operation = self._operations.get(request_id)
            if not isinstance(operation, _BackupOperation) or not operation.native_transfer:
                return "TOO_LATE"
            operation.cancelled.set()
            if operation.future is not None:
                operation.future.cancel()
            return "REQUESTED"

    def current_data_revisions(self) -> tuple[str, str, str] | None:
        with self._lock:
            if self._closed or self._session_epoch <= 0:
                return None
            return (
                self._revision_value("vault"),
                self._revision_value("notes"),
                self._revision_value("health"),
            )

    def claim_editor(
        self,
        instance_id: str,
        kind: str,
        record_id: int,
        session_epoch: int,
    ) -> bool:
        if (
            type(instance_id) is not str
            or not 16 <= len(instance_id) <= 64
            or kind not in {"PASSWORD", "PASSWORD_CREATE", "NOTE", "NOTE_CREATE"}
            or type(record_id) is not int
            or (
                (kind in {"PASSWORD_CREATE", "NOTE_CREATE"} and record_id != 0)
                or (kind not in {"PASSWORD_CREATE", "NOTE_CREATE"} and record_id <= 0)
            )
            or type(session_epoch) is not int
            or session_epoch <= 0
        ):
            return False
        with self._lock:
            if (
                self._closed
                or self._session_epoch != session_epoch
            ):
                return False
            with self._health_edit_lock:
                if self._editor_occupancy is not None:
                    return False
                self._editor_occupancy = (
                    kind,
                    record_id,
                    session_epoch,
                    instance_id,
                )
                return True

    def release_editor(self, instance_id: str) -> bool:
        with self._health_edit_lock:
            occupancy = self._editor_occupancy
            if occupancy is None or occupancy[3] != instance_id:
                return False
            self._editor_occupancy = None
        if isinstance(self._health_rescan, SessionStrengthQueue):
            self._health_rescan.wake()
        return True

    def clone_generated_secret_for_editor(
        self,
        page_epoch: int,
        lease_id: str,
    ) -> dict[str, object] | None:
        """Create an independently revocable copy of one current C33 lease."""

        with self._lock:
            if (
                self._closed
                or page_epoch not in self._valid_pages
                or self._session_epoch <= 0
                or type(lease_id) is not str
            ):
                return None
            self._prune_generated_secrets_locked()
            source = self._generated_secrets.get(lease_id)
            if source is None or source.page_epoch != page_epoch:
                return None
            remaining_ms = min(
                300_000,
                max(1, int((source.expires_at - self._clock()) * 1000)),
            )
            clone_id = secrets.token_urlsafe(24)
            if (
                clone_id in self._generated_secrets
                or len(self._generated_secrets) >= _MAX_GENERATED_SECRET_LEASES
            ):
                return None
            timer = threading.Timer(
                remaining_ms / 1000.0,
                self.revoke_secret_lease,
                (clone_id,),
            )
            timer.daemon = True
            self._generated_secrets[clone_id] = _GeneratedSecret(
                lease_id=clone_id,
                page_epoch=page_epoch,
                expires_at=self._clock() + remaining_ms / 1000.0,
                password=source.password,
                expiry_timer=timer,
            )
            timer.start()
            return {
                "secretLeaseId": clone_id,
                "password": source.password,
                "expiresInMs": remaining_ms,
            }

    def resolve_editor_revision(
        self,
        instance_id: str,
        page_epoch: int,
        session_epoch: int,
        record_id: int,
        complete: Callable[[str, str], None],
        *,
        kind: str = "PASSWORD",
    ) -> None:
        """Resolve only the claimed editor target on the serialized DB worker."""

        error = ""
        with self._lock:
            with self._health_edit_lock:
                occupied = self._editor_occupancy == (
                    kind, record_id, session_epoch, instance_id
                )
            if kind not in {"PASSWORD", "NOTE"} or not occupied:
                error = "STALE_SESSION"
            elif self._closed or page_epoch not in self._valid_pages:
                error = "STALE_PAGE"
            elif self._database is None or self._session_epoch == 0:
                error = "SESSION_REQUIRED"
            elif session_epoch != self._session_epoch:
                error = "STALE_SESSION"
            elif any(
                isinstance(operation, (_ChangeKeyOperation, _BackupOperation))
                for operation in self._operations.values()
            ):
                error = "REQUEST_BUSY"
            elif not self._database.bound_identity_is_current():
                self._release_session_locked()
                error = "STALE_SESSION"
            else:
                database = self._database
                revision_key = self._session_revision_key
                if revision_key is None:
                    error = "SESSION_REQUIRED"
                else:
                    request_id = secrets.token_urlsafe(24)

                    def settled(completion: AdapterCompletion) -> None:
                        result = completion.result or {}
                        revision = result.get("revision", "")
                        complete(
                            completion.error_code,
                            revision if isinstance(revision, str) else "",
                        )

                    operation = _SessionReadOperation(
                        request_id,
                        0,
                        CommandId.C12 if kind == "PASSWORD" else CommandId.C25,
                        page_epoch,
                        session_epoch,
                        database,
                        settled,
                        threading.Event(),
                        threading.Event(),
                        editor_revision_only=True,
                    )
                    self._operations[request_id] = operation
                    future = self._submit_worker(
                        (
                            self._resolve_editor_revision
                            if kind == "PASSWORD"
                            else self._resolve_note_editor_revision
                        ),
                        database,
                        revision_key,
                        record_id,
                        operation.cancelled,
                    )
                    operation.future = future
                    future.add_done_callback(
                        lambda finished, request_id=request_id:
                        self._finish_session_read(request_id, finished)
                    )
                    return
        complete(error or "INTERNAL_FAILURE", "")

    def _record_is_occupied(self, kind: str, record_id: int) -> bool:
        with self._health_edit_lock:
            occupancy = self._editor_occupancy
            return bool(
                occupancy is not None
                and occupancy[0] == kind
                and occupancy[1] == record_id
                and occupancy[2] == self._session_epoch
            )

    @property
    def ticket_count(self) -> int:
        with self._lock:
            self._prune_tickets_locked()
            return len(self._tickets)

    @property
    def delete_ticket_count(self) -> int:
        with self._lock:
            self._prune_delete_tickets_locked()
            return len(self._delete_tickets)

    def submit(
        self,
        request: AdapterRequest,
        complete: CompletionCallback,
    ) -> None:
        if request.command_id is CommandId.C01:
            self._submit_handshake(request, complete)
            return
        if request.command_id is CommandId.C02:
            self._submit_choose_target(request, complete)
            return
        if request.command_id is CommandId.C03:
            self._submit_select_recent(request, complete)
            return
        if request.command_id is CommandId.C74:
            self._submit_remove_recent_database(request, complete)
            return
        if request.command_id is CommandId.C80:
            self._submit_contact_support(request, complete)
            return
        if request.command_id in {CommandId.C82, CommandId.C83, CommandId.C84, CommandId.C85, CommandId.C86}:
            self._submit_update_action(request, complete)
            return
        if request.command_id is CommandId.C04:
            self._submit_open_database(request, complete)
            return
        if request.command_id is CommandId.C06:
            self._submit_lock(request, complete)
            return
        if request.command_id is CommandId.C08:
            self._submit_release_secret_lease(request, complete)
            return
        if request.command_id is CommandId.C09:
            self._submit_open_quickbar(request, complete)
            return
        if request.command_id is CommandId.C10:
            self._submit_list_vault(request, complete)
            return
        if request.command_id is CommandId.C66:
            self._submit_locate_vault_record(request, complete)
            return
        if request.command_id is CommandId.C11:
            self._submit_record_details(request, complete)
            return
        if request.command_id is CommandId.C24:
            self._submit_list_notes(request, complete)
            return
        if request.command_id is CommandId.C25:
            self._submit_note_details(request, complete)
            return
        if request.command_id is CommandId.C26:
            self._submit_create_note(request, complete)
            return
        if request.command_id is CommandId.C27:
            self._submit_update_note(request, complete)
            return
        if request.command_id is CommandId.C28:
            self._submit_set_note_favorite(request, complete)
            return
        if request.command_id is CommandId.C29:
            self._submit_prepare_delete_note(request, complete)
            return
        if request.command_id is CommandId.C30:
            self._submit_delete_note(request, complete)
            return
        if request.command_id is CommandId.C31:
            self._submit_health_summary(request, complete)
            return
        if request.command_id is CommandId.C32:
            self._submit_list_health_issues(request, complete)
            return
        if request.command_id is CommandId.C67:
            self._submit_health_overview_at(request, complete)
            return
        if request.command_id is CommandId.C68:
            self._submit_health_guidance_page(request, complete)
            return
        if request.command_id is CommandId.C69:
            self._submit_release_health_guidance(request, complete)
            return
        if request.command_id in {CommandId.C70, CommandId.C71, CommandId.C72}:
            self._submit_health_rescan(request, complete)
            return
        if request.command_id is CommandId.C75:
            self._submit_session_worker(request, complete, self._retry_record_strength,
                                        request.arguments[3], request.arguments[4])
            return
        if request.command_id is CommandId.C76:
            self._submit_session_worker(request, complete, self._locate_vault_anchor,
                request.arguments[3], request.arguments[4], request.arguments[5], request.arguments[6])
            return
        if request.command_id is CommandId.C79:
            self._submit_session_worker(
                request, complete, self._set_recovery_code_used,
                request.arguments[3], request.arguments[4], request.arguments[5], request.arguments[6],
            )
            return
        if request.command_id is CommandId.C12:
            self._submit_open_record_editor(request, complete)
            return
        if request.command_id is CommandId.C14:
            self._submit_create_record(request, complete)
            return
        if request.command_id is CommandId.C15:
            self._submit_update_record(request, complete)
            return
        if request.command_id is CommandId.C62:
            self._submit_update_record_fields(request, complete)
            return
        if request.command_id is CommandId.C16:
            self._submit_set_record_favorite(request, complete)
            return
        if request.command_id is CommandId.C60:
            self._submit_record_field_chunk(request, complete)
            return
        if request.command_id is CommandId.C61:
            self._submit_release_record_field_read(request, complete)
            return
        if request.command_id is CommandId.C63:
            self._submit_note_field_chunk(request, complete)
            return
        if request.command_id is CommandId.C64:
            self._submit_release_note_field_read(request, complete)
            return
        if request.command_id is CommandId.C65:
            self._submit_update_note_fields(request, complete)
            return
        if request.command_id is CommandId.C17:
            self._submit_prepare_delete_record(request, complete)
            return
        if request.command_id is CommandId.C18:
            self._submit_delete_record(request, complete)
            return
        if request.command_id in {
            CommandId.C13,
            CommandId.C77,
            CommandId.C78,
            CommandId.C19,
            CommandId.C20,
            CommandId.C21,
            CommandId.C22,
            CommandId.N02,
            CommandId.N03,
        }:
            self._submit_record_secret_action(request, complete)
            return
        if request.command_id is CommandId.N01:
            self._submit_quickbar_search(request, complete)
            return
        if request.command_id is CommandId.N04:
            self._submit_quickbar_generate(request, complete)
            return
        if request.command_id is CommandId.C23:
            self._submit_clear_clipboard(request, complete)
            return
        if request.command_id is CommandId.C33:
            self._submit_generate_password(request, complete)
            return
        if request.command_id is CommandId.C34:
            self._submit_check_password_strength(request, complete)
            return
        if request.command_id is CommandId.C35:
            self._submit_copy_generated_password(request, complete)
            return
        if request.command_id in {
            CommandId.C36,
            CommandId.C37,
            CommandId.C38,
            CommandId.C39,
            CommandId.C40,
            CommandId.C41,
            CommandId.C42,
            CommandId.C43,
            CommandId.C44,
            CommandId.C45,
            CommandId.C46,
            CommandId.C47,
            CommandId.C48,
            CommandId.C73,
        }:
            self._submit_setting(request, complete)
            return
        if request.command_id is CommandId.C49:
            with self._lock:
                self._native_change_key_settlement = None
            self._submit_change_database_password(
                request,
                self._recording_change_key_completion(
                    request.token,
                    complete,
                ),
            )
            return
        if request.command_id in {CommandId.C50, CommandId.C52}:
            self._submit_choose_backup_file(request, complete)
            return
        if request.command_id is CommandId.C51:
            self._submit_export_backup(request, complete)
            return
        if request.command_id is CommandId.C53:
            self._submit_preview_backup(request, complete)
            return
        if request.command_id is CommandId.C54:
            self._submit_list_backup_conflicts(request, complete)
            return
        if request.command_id in {CommandId.C55, CommandId.C56}:
            self._submit_backup_decision(request, complete)
            return
        if request.command_id in {CommandId.C57, CommandId.C81}:
            self._submit_backup_field_chunk(request, complete)
            return
        if request.command_id is CommandId.C58:
            self._submit_import_backup(request, complete)
            return
        if request.command_id is CommandId.C59:
            self._submit_close_backup_preview(request, complete)
            return
        if request.command_id in {CommandId.C87, CommandId.C88, CommandId.C89, CommandId.C90}:
            self._submit_export_selection(request, complete)
            return
        complete(self._error(request, "INTERNAL_FAILURE"))

    def cancel(self, request: AdapterRequest) -> str:
        with self._lock:
            operation = self._operations.get(request.request_id)
            if operation is None:
                return "TOO_LATE"
            if isinstance(operation, _ChangeKeyOperation):
                if operation.irreversible or operation.commit_started:
                    return "TOO_LATE"
                operation.cancelled.set()
                future = operation.future
                if future is not None:
                    future.cancel()
                return "REQUESTED"
            if isinstance(operation, _BackupOperation):
                if operation.commit_started:
                    return "TOO_LATE"
                operation.cancelled.set()
                future = operation.future
                if future is not None:
                    future.cancel()
                return "REQUESTED"
            operation.cancelled.set()
            future = operation.future
            if future is not None:
                future.cancel()
            return "REQUESTED"

    def take_change_key_settlement(self, token: int) -> str | None:
        """按精确 token 一次消费不含秘密的原生 C49 结算。"""

        if type(token) is not int or token <= 0:
            return None
        with self._lock:
            settlement = self._native_change_key_settlement
            if settlement is None or settlement.token != token:
                return None
            self._native_change_key_settlement = None
            return settlement.outcome

    def _recording_change_key_completion(
        self,
        token: int,
        complete: CompletionCallback,
    ) -> CompletionCallback:
        def recorded(value: AdapterCompletion) -> None:
            outcome = self._classify_change_key_settlement(value)
            self._record_change_key_settlement(token, outcome)
            complete(value)

        return recorded

    def _record_change_key_settlement(
        self,
        token: int,
        outcome: str,
        *,
        replace: bool = False,
    ) -> None:
        if (
            type(token) is not int
            or token <= 0
            or outcome not in _NATIVE_CHANGE_KEY_SETTLEMENTS
        ):
            return
        with self._lock:
            current = self._native_change_key_settlement
            if current is not None and not (
                replace and current.token == token
            ):
                return
            self._native_change_key_settlement = (
                _NativeChangeKeySettlement(token, outcome)
            )

    @staticmethod
    def _classify_change_key_settlement(
        completion: AdapterCompletion,
        operation: _ChangeKeyOperation | None = None,
    ) -> str:
        if completion.error_code == "OK" and (
            isinstance(completion.result, dict)
            and completion.result.get("state") == "LOCKED"
            and completion.result.get("sessionEpoch") == 0
        ):
            return "SUCCESS"
        if completion.error_code == "CHANGE_KEY_FAILED_RESTORED":
            return "RESTORED"
        if completion.error_code == "CHANGE_KEY_RECOVERY_FAILED":
            return "RECOVERY_FAILED"
        verified_unchanged = completion.error_code in {
            "AUTH_FAILED",
            "CANCELLED",
            "CHANGE_KEY_FAILED_UNCHANGED",
        }
        request_rejected_before_operation = (
            operation is None
            and completion.error_code
            in {
                "INVALID_ARGUMENT",
                "REQUEST_TOO_LARGE",
                "STALE_PAGE",
                "STALE_SESSION",
                "SESSION_REQUIRED",
                "REQUEST_BUSY",
                "DUPLICATE_REQUEST",
            }
        )
        if verified_unchanged or request_rejected_before_operation:
            return "REVERSIBLE_ABORTED"
        return "INTERNAL_FAILURE"

    def invalidate_page(self, page_epoch: int) -> None:
        operations: list[
            _OpenOperation
            | _SessionReadOperation
            | _PageSecretOperation
            | _ChangeKeyOperation
            | _BackupOperation
        ] = []
        settings_operations: list[_SettingsOperation] = []
        with self._lock:
            self._valid_pages.discard(page_epoch)
            if self._health_rescan is not None:
                self._health_rescan.cancel()
            self._record_field_reads.clear()
            self._note_field_reads.clear()
            self._backup.clear_page(page_epoch)
            self._revoke_generated_secrets_locked(page_epoch=page_epoch)
            self._health_guidance = None
            self._released_health_guidance_id = ""
            self._expected_existing_paths_by_page.pop(page_epoch, None)
            self._tickets = {
                value: ticket
                for value, ticket in self._tickets.items()
                if ticket.page_epoch != page_epoch
            }
            self._delete_tickets = {
                value: ticket
                for value, ticket in self._delete_tickets.items()
                if ticket.page_epoch != page_epoch
            }
            self._recent_ids.clear()
            self._recent_paths_by_id.clear()
            for operation in tuple(self._operations.values()):
                if operation.page_epoch == page_epoch:
                    self._request_operation_cancel_locked(operation)
                    operations.append(operation)
            settings_operations = [
                operation
                for operation in self._settings_operations.values()
                if operation.page_epoch == page_epoch
            ]
        self._wait_for_operations(operations)
        self._wait_for_settings_operations(settings_operations)
        self._release_session()

    def invalidate_session(self, session_epoch: int) -> None:
        operations: list[
            _SessionReadOperation
            | _PageSecretOperation
            | _ChangeKeyOperation
            | _BackupOperation
        ] = []
        settings_operations: list[_SettingsOperation] = []
        with self._lock:
            if self._health_rescan is not None and session_epoch == self._session_epoch:
                self._health_rescan.cancel()
            self._record_field_reads.clear()
            self._note_field_reads.clear()
            self._backup.clear_session(session_epoch)
            self._revoke_generated_secrets_locked()
            self._health_guidance = None
            self._released_health_guidance_id = ""
            self._delete_tickets = {
                value: ticket
                for value, ticket in self._delete_tickets.items()
                if ticket.session_epoch != session_epoch
            }
            for operation in tuple(self._operations.values()):
                if (
                    isinstance(operation, _PageSecretOperation)
                ) or (
                    isinstance(
                        operation,
                        (_SessionReadOperation, _ChangeKeyOperation, _BackupOperation),
                    )
                    and operation.session_epoch == session_epoch
                ):
                    self._request_operation_cancel_locked(operation)
                    operations.append(operation)
            settings_operations = [
                operation
                for operation in self._settings_operations.values()
                if (
                    operation.command_id in {
                        CommandId.C41,
                        CommandId.C38,
                        CommandId.C39,
                        CommandId.C42,
                        CommandId.C43,
                        CommandId.C44,
                        CommandId.C45,
                        CommandId.C46,
                        CommandId.C47,
                        CommandId.C48,
                    }
                    and operation.session_epoch == session_epoch
                )
            ]
        self._wait_for_operations(operations)
        self._wait_for_settings_operations(settings_operations)
        with self._lock:
            self._drop_session_setting_publications_locked(
                session_epoch=session_epoch,
            )
            if self._session_epoch == session_epoch:
                self._release_session_locked()

    def revoke_secret_lease(self, secret_lease_id: str) -> None:
        with self._lock:
            self._revoke_generated_secret_locked(secret_lease_id)
            self._record_field_reads.revoke_lease(secret_lease_id)
        with self._health_edit_lock:
            self._health_edit_leases.pop(secret_lease_id, None)
        if isinstance(self._health_rescan, SessionStrengthQueue):
            self._health_rescan.wake()

    def _release_record_field_read(
        self,
        read_id: object,
        page_epoch: object,
        session_epoch: object,
    ) -> None:
        if (
            type(read_id) is str
            and re.fullmatch(r"[A-Za-z0-9_-]{16,64}", read_id)
            and type(page_epoch) is int
            and type(session_epoch) is int
        ):
            self._record_field_reads.release(
                read_id,
                page_epoch=page_epoch,
                session_epoch=session_epoch,
            )

    def _release_note_field_read(
        self,
        read_id: object,
        page_epoch: object,
        session_epoch: object,
    ) -> None:
        if (
            type(read_id) is str
            and re.fullmatch(r"[A-Za-z0-9_-]{16,64}", read_id)
            and type(page_epoch) is int
            and type(session_epoch) is int
        ):
            self._note_field_reads.release(
                read_id,
                page_epoch=page_epoch,
                session_epoch=session_epoch,
            )

    def _discard_session_read_result(
        self,
        operation: _SessionReadOperation,
        result: _SessionReadResult,
    ) -> None:
        if operation.command_id in {CommandId.C60, CommandId.C63}:
            read_id = operation.record_field_read_id
            if isinstance(result.result, dict):
                read_id = str(result.result.get("readId") or read_id)
            release = (
                self._release_record_field_read
                if operation.command_id is CommandId.C60
                else self._release_note_field_read
            )
            release(read_id, operation.page_epoch, operation.session_epoch)
        self._scrub_editor_result(result)

    def discard(self, completion: AdapterCompletion) -> None:
        with self._lock:
            if isinstance(completion.result, dict) and "rawPayload" in completion.result:
                completion.result.clear()
                return
            if completion.command_id is CommandId.C87 and isinstance(completion.result, dict):
                self._backup.discard_export_draft(str(completion.result.get("selectionTicket", "")))
                completion.result.clear()
                return
            if completion.command_id in {CommandId.C50, CommandId.C52}:
                result = completion.result
                if isinstance(result, dict):
                    self._backup.discard_selection(
                        str(result.get("selectionTicket", ""))
                    )
                return
            if completion.command_id is CommandId.C53:
                result = completion.result
                if isinstance(result, dict):
                    self._backup.discard_preview(
                        str(result.get("previewTicket", ""))
                    )
                return
            if completion.command_id in {CommandId.C57, CommandId.C81}:
                result = completion.result
                if isinstance(result, dict):
                    self._backup.release_read(str(result.get("readId", "")))
                    result["text"] = ""
                    result.clear()
                return
            if completion.command_id in {CommandId.C60, CommandId.C63}:
                result = completion.result
                if isinstance(result, dict):
                    release = (
                        self._release_record_field_read
                        if completion.command_id is CommandId.C60
                        else self._release_note_field_read
                    )
                    release(result.get("readId"), result.get("_discardPageEpoch"), result.get("_discardSessionEpoch"))
                    result.clear()
                return
            if isinstance(completion.result, dict):
                for field in ("password", "value", "code", "text"):
                    if field in completion.result:
                        completion.result[field] = ""
            if completion.command_id in {
                CommandId.C36,
                CommandId.C37,
                CommandId.C38,
                CommandId.C39,
                CommandId.C40,
                CommandId.C41,
                CommandId.C42,
                CommandId.C43,
                CommandId.C44,
                CommandId.C45,
                CommandId.C46,
                CommandId.C47,
                CommandId.C48,
                CommandId.C73,
            }:
                self._settings_publications.pop(
                    completion.request_id,
                    None,
                )
            if completion.command_id is CommandId.C01:
                result = completion.result
                page_epoch = (
                    result.get("pageEpoch")
                    if isinstance(result, dict)
                    else None
                )
                if type(page_epoch) is int:
                    self._valid_pages.discard(page_epoch)
                    self._expected_existing_paths_by_page.pop(
                        page_epoch,
                        None,
                    )
                    self._tickets = {
                        value: ticket
                        for value, ticket in self._tickets.items()
                        if ticket.page_epoch != page_epoch
                    }
                    self._recent_ids.clear()
                    self._recent_paths_by_id.clear()
            elif completion.command_id in {
                CommandId.C02,
                CommandId.C03,
            }:
                result = completion.result
                ticket_value = (
                    result.get("selectionTicket")
                    if isinstance(result, dict)
                    else None
                )
                if type(ticket_value) is str:
                    self._tickets.pop(ticket_value, None)
            elif (
                completion.command_id is CommandId.C04
                and completion.token == self._session_token
            ):
                self._release_session_locked()
            elif completion.command_id in {CommandId.C17, CommandId.C29}:
                result = completion.result
                ticket_value = (
                    result.get("deleteTicket")
                    if isinstance(result, dict)
                    else None
                )
                if type(ticket_value) is str:
                    self._delete_tickets.pop(ticket_value, None)
            elif completion.command_id is CommandId.C13:
                result = completion.result
                if isinstance(result, dict):
                    result["value"] = ""
            elif completion.command_id is CommandId.C12:
                result = completion.result
                if isinstance(result, dict):
                    result["password"] = ""
                    with self._health_edit_lock:
                        self._health_edit_leases.pop(str(result.get("editLeaseId", "")), None)
            elif completion.command_id is CommandId.C33:
                result = completion.result
                if isinstance(result, dict):
                    self._revoke_generated_secret_locked(
                        str(result.get("secretLeaseId", ""))
                    )
                    result["password"] = ""

    def close(self) -> None:
        operations: list[
            _OpenOperation
            | _SessionReadOperation
            | _PageSecretOperation
            | _ChangeKeyOperation
            | _BackupOperation
        ] = []
        with self._lock:
            if self._closed:
                return
            self._closed = True
            if self._health_rescan is not None:
                self._health_rescan.cancel()
            self._tickets.clear()
            self._delete_tickets.clear()
            self._backup.clear()
            self._valid_pages.clear()
            self._revoke_generated_secrets_locked()
            self._health_guidance = None
            self._released_health_guidance_id = ""
            self._expected_existing_paths_by_page.clear()
            self._recent_ids.clear()
            self._recent_paths_by_id.clear()
            for operation in tuple(self._operations.values()):
                self._request_operation_cancel_locked(operation)
                operations.append(operation)
        self._wait_for_operations(operations)
        self._release_session()
        self._executor.shutdown(wait=True, cancel_futures=True)
        self._strength_executor.shutdown(wait=True, cancel_futures=True)
        self._settings_executor.shutdown(wait=True, cancel_futures=False)
        with self._lock:
            self._settings_publications.clear()

    def current_settings_snapshot(self) -> dict[str, object]:
        """Return the current bounded public settings authority."""

        with self._lock:
            return copy.deepcopy(self._settings_snapshot())

    def update_state_store(self):
        from .update_state import UpdateStateStore

        return UpdateStateStore(self._settings_store)

    def submit_update_storage(self, action):
        with self._lock:
            if self._closed:
                raise RuntimeError("adapter is closed")
            return self._settings_executor.submit(action)

    def bind_update_controller(self, controller) -> None:
        self._update_controller = controller

    def _submit_update_action(self, request, complete) -> None:
        with self._lock:
            if self._closed or request.page_epoch not in self._valid_pages:
                complete(self._error(request, "STALE_PAGE"))
                return
            controller = self._update_controller
        if controller is None:
            complete(self._error(request, "INTERNAL_FAILURE"))
            return

        def finished(result, error):
            complete(self._success(request, result) if error == "OK" else self._error(request, error))

        controller.dispatch(request.command_id.value, request.arguments[2:], finished)

    def current_settings_revision(self) -> str:
        """Return the opaque persisted-settings equality token."""

        return str(self.current_settings_authority()["settingsRevision"])

    def current_settings_authority(self) -> dict[str, object]:
        """Return one atomic revision/snapshot pair from native authority."""

        with self._lock:
            settings = self._settings_snapshot()
            return {
                "settingsRevision": self._settings_revision(),
                "settings": copy.deepcopy(settings),
            }

    def activate_quickbar_hotkey_for_session(self) -> str:
        """Register the configured hotkey only for an unlocked session."""

        with self._lock:
            hotkey = self._hotkey
            if hotkey is None or not self._quickbar_enabled():
                if hotkey is not None:
                    hotkey.unregister()
                self._quickbar_registration = "DISABLED"
                return self._quickbar_registration
            self._quickbar_registration = (
                "REGISTERED"
                if hotkey.replace_preserving(self._quickbar_hotkey())
                else "UNAVAILABLE"
            )
            return self._quickbar_registration

    def note_quickbar_hotkey_unregistered(self) -> None:
        """Project H06's authoritative unregister into public settings."""

        with self._lock:
            self._quickbar_registration = "DISABLED"

    def note_settings_session_invalidation(self, session_epoch: int) -> None:
        if type(session_epoch) is not int or session_epoch <= 0:
            return
        with self._lock:
            self._settings_invalidating_sessions.add(session_epoch)

    def clear_settings_session_invalidation(self, session_epoch: int) -> None:
        with self._lock:
            self._settings_invalidating_sessions.discard(session_epoch)

    def settle_settings_projection_for_page(
        self,
        page_epoch: int,
    ) -> dict[str, object]:
        """Wait for accepted page settings commits and return authority.

        Renderer recovery calls this before revoking the page and exposing
        the native curtain.  Accepted public settings writes remain durable,
        while their late Bridge completion is still discarded by the normal
        page boundary.
        """

        if type(page_epoch) is not int or page_epoch <= 0:
            raise ValueError("page_epoch must be a positive integer")
        with self._lock:
            operations = [
                operation
                for operation in self._settings_operations.values()
                if operation.page_epoch == page_epoch
            ]
        self._wait_for_settings_operations(operations)
        return self.current_settings_snapshot()

    def settle_settings_authority(self) -> dict[str, object]:
        """Synchronously converge and atomically read settings authority.

        C36/C37/C41/C43/C44/C45/C47/C73 share one global commit queue. Native close and
        security-lock decisions both call this convergence point before they
        consume the complete policy snapshot.  Publication markers remain
        one-shot for a still-authorized renderer; session/page invalidation
        drops markers that no longer have a live consumer.
        """

        with self._lock:
            operations = list(self._settings_operations.values())
        self._wait_for_settings_operations(operations)
        return self.current_settings_authority()

    def settle_close_behavior_authority(self) -> dict[str, object]:
        """Compatibility name for H01's complete-settings convergence."""

        return self.settle_settings_authority()

    def refresh_effective_theme_from_provider(self) -> str:
        """Refresh the cached native system projection on the calling thread."""

        effective_theme = self._read_effective_theme_provider()
        with self._lock:
            self._native_effective_theme = effective_theme
        return effective_theme

    def take_settings_commit_publication(
        self,
        request_id: str,
        settings_revision: str,
    ) -> SettingsCommitPublication | None:
        """Consume one changed-commit marker after an accepted completion.

        A same-value request never creates a marker.  ``discard`` removes a
        marker when the Bridge rejects a stale/late completion, so S02 cannot
        escape to a replacement renderer page.
        """

        if type(request_id) is not str or type(settings_revision) is not str:
            return None
        with self._lock:
            publication = self._settings_publications.get(request_id)
            if (
                publication is None
                or publication.settings_revision != settings_revision
            ):
                return None
            self._settings_publications.pop(request_id, None)
            return SettingsCommitPublication(
                command_id=publication.command_id,
                page_epoch=publication.page_epoch,
                session_epoch=publication.session_epoch,
                settings_revision=publication.settings_revision,
                settings=copy.deepcopy(publication.settings),
            )

    def release_session(self) -> None:
        """Idempotent native RELEASE_SESSION cleanup step."""

        self._release_session()

    def set_change_key_progress_sink(
        self,
        sink: _ChangeKeyProgressSink | None,
    ) -> None:
        """Install an optional native-only fixed OperationPhase sink."""

        if sink is not None and not callable(sink):
            raise TypeError("change-key progress sink must be callable")
        with self._lock:
            self._change_key_progress_sink = sink

    def set_progress_sink(
        self,
        sink: _ChangeKeyProgressSink | None,
    ) -> None:
        """Compatibility name for the native C49 progress binding."""

        self.set_change_key_progress_sink(sink)

    def _submit_handshake(
        self,
        request: AdapterRequest,
        complete: CompletionCallback,
    ) -> None:
        with self._lock:
            if self._closed:
                completion = self._error(request, "INTERNAL_FAILURE")
            else:
                page_epoch = self._next_page_epoch
                self._next_page_epoch += 1
                self._valid_pages.add(page_epoch)
                self._recent_ids.clear()
                self._recent_paths_by_id.clear()
                try:
                    settings = self._settings_snapshot()
                    startup_path, startup_must_exist = self._startup_path(
                        settings
                    )
                    recent_databases = self._recent_databases()
                except SecurityStateCommitError:
                    self._valid_pages.discard(page_epoch)
                    completion = self._error(
                        request,
                        "INTERNAL_FAILURE",
                    )
                    complete(completion)
                    return
                expected_existing = {
                    self._path_key(
                        Path(str(value["displayPath"]))
                    )
                    for value in recent_databases
                }
                if startup_must_exist:
                    expected_existing.add(
                        self._path_key(Path(startup_path))
                    )
                self._expected_existing_paths_by_page[
                    page_epoch
                ] = expected_existing
                completion = self._success(
                    request,
                    {
                        "contractVersion": _CONTRACT_VERSION,
                        "pageEpoch": page_epoch,
                        "sessionEpoch": 0,
                        "state": "LOCKED",
                        "settingsRevision": self._settings_revision(),
                        "settings": settings,
                        "startupPath": startup_path,
                        "recentDatabases": recent_databases,
                    },
                )
        complete(completion)

    def _submit_contact_support(
        self, request: AdapterRequest, complete: CompletionCallback,
    ) -> None:
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices

        with self._lock:
            if self._closed or request.page_epoch not in self._valid_pages:
                complete(self._error(request, "STALE_PAGE"))
                return
            try:
                opened = QDesktopServices.openUrl(QUrl("https://t.me/+kQEszbuHNEgxOGRh"))
            except Exception:
                opened = False
        complete(self._success(request, {}) if opened else self._error(request, "INTERNAL_FAILURE"))

    def _submit_choose_target(
        self,
        request: AdapterRequest,
        complete: CompletionCallback,
    ) -> None:
        with self._lock:
            if (
                self._closed
                or request.page_epoch not in self._valid_pages
            ):
                complete(self._error(request, "STALE_PAGE"))
                return
            if (
                self._database is not None
                or self._has_non_strength_operation_locked()
            ):
                complete(self._error(request, "REQUEST_BUSY"))
                return
        candidate = str(request.arguments[2]).strip()
        if candidate:
            target, error_code = self._resolve_path_candidate(
                request.page_epoch,
                candidate,
            )
            if error_code:
                complete(self._error(request, error_code))
                return
        else:
            try:
                target = self._selector.choose()
            except Exception:
                complete(self._error(request, "INTERNAL_FAILURE"))
                return
        if target is None:
            complete(
                self._success(
                    request,
                    {
                        "selected": False,
                        "selectionTicket": "",
                        "displayName": "",
                        "displayPath": "",
                        "targetKind": "NONE",
                        "expiresInMs": 0,
                    },
                )
            )
            return
        if not self._target_is_valid(target):
            complete(self._error(request, "INTERNAL_FAILURE"))
            return
        self._complete_target_selection(request, complete, target)

    def _resolve_path_candidate(
        self,
        page_epoch: int,
        candidate: str,
    ) -> tuple[DatabaseTarget | None, str | None]:
        """Turn untrusted display text into one native-bounded target."""

        try:
            raw_path = Path(candidate)
            if not self._isolation.database_candidate_syntax_is_safe(
                raw_path
            ):
                return None, "INVALID_ARGUMENT"
            original_path = raw_path.resolve(strict=False)
            if self._path_was_previously_existing(
                page_epoch,
                original_path,
            ) and not original_path.exists():
                return None, "NOT_FOUND"
            path = self._isolation.normalize_database_candidate(
                raw_path
            )
        except (OSError, RuntimeError, ValueError):
            return None, "INVALID_ARGUMENT"
        if path.exists():
            if not self._isolation.allows_existing_database(path):
                return None, "DATABASE_INVALID"
            return (
                DatabaseTarget(
                    path=path,
                    kind=DatabaseTargetKind.OPEN_EXISTING,
                ),
                None,
            )
        if self._path_was_previously_existing(page_epoch, path):
            return None, "NOT_FOUND"
        if not self._isolation.allows_new_database(path):
            return None, "INVALID_ARGUMENT"
        return (
            DatabaseTarget(
                path=path,
                kind=DatabaseTargetKind.CREATE_NEW,
            ),
            None,
        )

    def _path_was_previously_existing(
        self,
        page_epoch: int,
        path: Path,
    ) -> bool:
        with self._lock:
            expected = self._expected_existing_paths_by_page.get(
                page_epoch,
                set(),
            )
            return self._path_key(path) in expected

    @staticmethod
    def _path_key(path: Path) -> str:
        return os.path.normcase(str(path.resolve(strict=False)))

    def _submit_select_recent(
        self,
        request: AdapterRequest,
        complete: CompletionCallback,
    ) -> None:
        with self._lock:
            if (
                self._closed
                or request.page_epoch not in self._valid_pages
            ):
                complete(self._error(request, "STALE_PAGE"))
                return
            if (
                self._database is not None
                or self._has_non_strength_operation_locked()
            ):
                complete(self._error(request, "REQUEST_BUSY"))
                return
            try:
                self._recent_databases()
            except SecurityStateCommitError:
                complete(self._error(request, "INTERNAL_FAILURE"))
                return
            recent_id = str(request.arguments[2])
            path = self._recent_paths_by_id.get(recent_id)
            if path is None or not path.is_file():
                self._recent_paths_by_id.pop(recent_id, None)
                complete(self._error(request, "NOT_FOUND"))
                return
            try:
                locked_until = self._security.get_lock_until_unix_ms(
                    str(path),
                    strict=True,
                )
            except SecurityStateCommitError:
                complete(self._error(request, "INTERNAL_FAILURE"))
                return
            if locked_until > 0:
                complete(
                    self._error(
                        request,
                        "LOCKED_OUT",
                        retry_after_ms=self._retry_after_ms(
                            locked_until
                        ),
                    )
                )
                return
            target = DatabaseTarget(
                path=path,
                kind=DatabaseTargetKind.OPEN_EXISTING,
            )
        self._complete_target_selection(request, complete, target)

    def _submit_remove_recent_database(
        self,
        request: AdapterRequest,
        complete: CompletionCallback,
    ) -> None:
        with self._lock:
            if self._closed or request.page_epoch not in self._valid_pages:
                complete(self._error(request, "STALE_PAGE"))
                return
            if (
                self._database is not None
                or self._has_non_strength_operation_locked()
            ):
                complete(self._error(request, "REQUEST_BUSY"))
                return
            try:
                recent_databases = self._recent_databases()
            except SecurityStateCommitError:
                complete(self._error(request, "INTERNAL_FAILURE"))
                return
            recent_id = str(request.arguments[2])
            path = self._recent_paths_by_id.get(recent_id)
            if path is None:
                complete(self._error(request, "NOT_FOUND"))
                return
            if not self._security.remove_recent_db_path(str(path)):
                complete(self._error(request, "INTERNAL_FAILURE"))
                return
            recent_databases = [
                value
                for value in recent_databases
                if value["recentDatabaseId"] != recent_id
            ]
        complete(self._success(request, {"recentDatabases": recent_databases}))

    def _complete_target_selection(
        self,
        request: AdapterRequest,
        complete: CompletionCallback,
        target: DatabaseTarget,
    ) -> None:
        file_identity = self._file_identity(target.path)
        if (
            target.kind is DatabaseTargetKind.OPEN_EXISTING
            and file_identity is None
        ):
            complete(self._error(request, "NOT_FOUND"))
            return
        ticket_value = secrets.token_urlsafe(24)
        ticket = _SelectionTicket(
            value=ticket_value,
            page_epoch=request.page_epoch,
            target=target,
            file_identity=file_identity,
            expires_at=self._clock() + (_SELECTION_TTL_MS / 1000),
        )
        with self._lock:
            if self._closed or request.page_epoch not in self._valid_pages:
                complete(self._error(request, "STALE_PAGE"))
                return
            if (
                self._database is not None
                or self._has_non_strength_operation_locked()
            ):
                complete(self._error(request, "REQUEST_BUSY"))
                return
            self._prune_tickets_locked()
            self._tickets[ticket_value] = ticket
            if target.kind is DatabaseTargetKind.OPEN_EXISTING:
                self._expected_existing_paths_by_page.setdefault(
                    request.page_epoch,
                    set(),
                ).add(self._path_key(target.path))
            while len(self._tickets) > _MAX_SELECTION_TICKETS:
                oldest = next(iter(self._tickets))
                self._tickets.pop(oldest, None)
        complete(
            self._success(
                request,
                {
                    "selected": True,
                    "selectionTicket": ticket_value,
                    "displayName": target.path.name,
                    "displayPath": str(target.path),
                    "targetKind": target.kind.value,
                    "expiresInMs": _SELECTION_TTL_MS,
                },
            )
        )

    def _submit_open_database(
        self,
        request: AdapterRequest,
        complete: CompletionCallback,
    ) -> None:
        ticket_value = str(request.arguments[2])
        with self._lock:
            if (
                self._database is not None
                or self._has_non_strength_operation_locked()
            ):
                complete(self._error(request, "REQUEST_BUSY"))
                return
            ticket = self._tickets.pop(ticket_value, None)
            if (
                ticket is None
                or ticket.page_epoch != request.page_epoch
                or ticket.expires_at <= self._clock()
            ):
                complete(self._error(request, "SELECTION_EXPIRED"))
                return
            if self._closed or request.page_epoch not in self._valid_pages:
                complete(self._error(request, "STALE_PAGE"))
                return
            target_error = self._ticket_target_state_error(ticket)
            if target_error:
                complete(self._error(request, target_error))
                return
            if ticket.target.kind is DatabaseTargetKind.OPEN_EXISTING:
                try:
                    pending_lock = (
                        self._security.commit_pending_authentication_lock(
                            str(ticket.target.path)
                        )
                    )
                    if pending_lock is not None:
                        complete(
                            self._error(
                                request,
                                "LOCKED_OUT",
                                retry_after_ms=self._retry_after_ms(
                                    pending_lock.locked_until_unix_ms
                                ),
                            )
                        )
                        return
                    locked_until = self._security.get_lock_until_unix_ms(
                        str(ticket.target.path),
                        strict=True,
                    )
                except SecurityStateCommitError:
                    complete(self._error(request, "INTERNAL_FAILURE"))
                    return
                if locked_until > 0:
                    complete(
                        self._error(
                            request,
                            "LOCKED_OUT",
                            retry_after_ms=self._retry_after_ms(
                                locked_until
                            ),
                        )
                    )
                    return

            operation = _OpenOperation(
                request_id=request.request_id,
                token=request.token,
                page_epoch=request.page_epoch,
                ticket=ticket,
                complete=complete,
                cancelled=threading.Event(),
                settled=threading.Event(),
            )
            self._operations[request.request_id] = operation
            password = request.arguments[3]
            if ticket.target.kind is DatabaseTargetKind.CREATE_NEW:
                future = self._submit_worker(
                    self._create_database,
                    ticket.target.path,
                    password,
                    operation.cancelled,
                )
            else:
                future = self._submit_worker(
                    self._open_existing_database,
                    ticket.target.path,
                    ticket.file_identity,
                    password,
                    operation.cancelled,
                )
            operation.future = future
            future.add_done_callback(
                lambda finished, request_id=request.request_id:
                self._finish_open(request_id, finished)
            )
            password = None

    @staticmethod
    def _create_database(
        path: Path,
        password: object,
        cancelled: threading.Event,
    ) -> _OpenResult:
        if cancelled.is_set():
            return _OpenResult(None, path, "CANCELLED")
        database = DatabaseService()
        try:
            opened = database.create_database(str(path), str(password))
            password = None
            if not opened:
                kind = database.error_kind
                error_code = ApplicationAdapter._database_core_error(
                    database,
                    fallback="DATABASE_IO_FAILED" if kind in {"permission_denied", "path_not_found"} else "DATABASE_INVALID",
                )
                database.disconnect()
                return _OpenResult(None, path, error_code)
            if cancelled.is_set():
                database.disconnect()
                return _OpenResult(None, path, "CANCELLED")
            published_identity = database.opened_file_identity
            if published_identity is None:
                database.disconnect()
                return _OpenResult(None, path, "DATABASE_INVALID")
            final_identity = ApplicationAdapter._file_identity(path)
            if (
                final_identity is None
                or not ApplicationAdapter._same_file_object(
                    published_identity,
                    final_identity,
                )
            ):
                database.disconnect()
                return _OpenResult(None, path, "DATABASE_INVALID")
            counts = database.get_record_counts(should_cancel=cancelled.is_set)
            if counts is None:
                error_code = "CANCELLED" if cancelled.is_set() else ApplicationAdapter._database_core_error(database)
                database.disconnect()
                return _OpenResult(None, path, error_code)
            password_count, note_count = counts
            # M4.3 reads and later writes reopen sqleet through the frozen
            # DatabaseService API. Its db_key is therefore retained only for
            # this native session and is dropped synchronously by disconnect()
            # on lock, page rebuild, renderer failure, or exit.
            return _OpenResult(
                database,
                path,
                "OK",
                password_count=password_count,
                note_count=note_count,
                file_identity=final_identity,
            )
        except Exception:
            password = None
            database.disconnect()
            return _OpenResult(None, path, "INTERNAL_FAILURE")

    @staticmethod
    def _open_existing_database(
        path: Path,
        expected_identity: tuple[int, int, int, int] | None,
        password: object,
        cancelled: threading.Event,
    ) -> _OpenResult:
        if cancelled.is_set():
            return _OpenResult(None, path, "CANCELLED")
        current_identity = ApplicationAdapter._file_identity(path)
        if current_identity is None:
            return _OpenResult(None, path, "NOT_FOUND")
        if (
            expected_identity is None
            or not ApplicationAdapter._same_file_object(
                expected_identity,
                current_identity,
            )
        ):
            return _OpenResult(None, path, "DATABASE_INVALID")

        database = DatabaseService()
        try:
            opened = database.open_existing(
                str(path),
                str(password),
                should_cancel=cancelled.is_set,
                pre_write_guard=lambda: (
                    (current := ApplicationAdapter._file_identity(path))
                    is not None
                    and ApplicationAdapter._same_file_object(
                        expected_identity,
                        current,
                    )
                ),
            )
            password = None
            if not opened:
                kind = database.error_kind
                database.disconnect()
                error_code = {
                    "invalid_password": "AUTH_FAILED",
                    "path_not_found": "NOT_FOUND",
                    "permission_denied": "DATABASE_IO_FAILED",
                    "invalid_path": "DATABASE_INVALID",
                    "corrupt_or_unreadable": "DATABASE_INVALID",
                    "resource_limit": "DATABASE_LIMIT_EXCEEDED",
                    "insufficient_space": "DATABASE_SPACE_INSUFFICIENT",
                    "cancelled": "CANCELLED",
                }.get(str(kind), "DATABASE_INVALID")
                return _OpenResult(None, path, error_code)
            if cancelled.is_set():
                database.disconnect()
                return _OpenResult(None, path, "CANCELLED")
            opened_identity = database.opened_file_identity
            final_identity = ApplicationAdapter._file_identity(path)
            if (
                opened_identity is None
                or final_identity is None
                or not ApplicationAdapter._same_file_object(
                    expected_identity,
                    final_identity,
                )
                or not ApplicationAdapter._same_file_object(
                    opened_identity,
                    final_identity,
                )
            ):
                database.disconnect()
                return _OpenResult(None, path, "DATABASE_INVALID")
            counts = database.get_record_counts(should_cancel=cancelled.is_set)
            if counts is None:
                error_code = "CANCELLED" if cancelled.is_set() else ApplicationAdapter._database_core_error(database)
                database.disconnect()
                return _OpenResult(None, path, error_code)
            password_count, note_count = counts
            # See _create_database: the sqleet key remains native-session
            # state and is never returned to or cached by the renderer.
            return _OpenResult(
                database,
                path,
                "OK",
                password_count=password_count,
                note_count=note_count,
                file_identity=final_identity,
            )
        except Exception:
            password = None
            database.disconnect()
            return _OpenResult(None, path, "INTERNAL_FAILURE")

    def _finish_open(
        self,
        request_id: str,
        future: Future[_OpenResult],
    ) -> None:
        operation: _OpenOperation | None = None
        try:
            try:
                result = future.result()
            except Exception:
                result = _OpenResult(
                    None,
                    Path(),
                    (
                        "CANCELLED"
                        if future.cancelled()
                        else "INTERNAL_FAILURE"
                    ),
                )
            with self._lock:
                operation = self._operations.pop(
                    request_id,
                    None,
                )
                if operation is None:
                    self._destroy_open_result(result)
                    return
                cancelled = (
                    operation.cancelled.is_set()
                    or self._closed
                    or operation.page_epoch not in self._valid_pages
                )
                if cancelled:
                    self._destroy_open_result(result)
                    if (
                        not self._closed
                        and operation.page_epoch in self._valid_pages
                    ):
                        self._restore_ticket_locked(operation.ticket)
                    completion = self._operation_error(
                        operation,
                        "CANCELLED",
                    )
                elif result.error_code == "AUTH_FAILED":
                    self._destroy_open_result(result)
                    completion = self._authentication_failure_locked(
                        operation
                    )
                elif (
                    result.error_code != "OK"
                    or result.database is None
                ):
                    self._destroy_open_result(result)
                    if result.error_code in {
                        "DATABASE_IO_FAILED",
                        "DATABASE_LIMIT_EXCEEDED",
                        "DATABASE_SPACE_INSUFFICIENT",
                        "CANCELLED",
                    }:
                        self._restore_ticket_locked(operation.ticket)
                    completion = self._operation_error(
                        operation,
                        result.error_code,
                    )
                else:
                    current_identity = self._file_identity(result.path)
                    if (
                        result.file_identity is None
                        or current_identity is None
                        or not self._same_file_object(
                            result.file_identity,
                            current_identity,
                        )
                    ):
                        self._destroy_open_result(result)
                        completion = self._operation_error(
                            operation,
                            "DATABASE_INVALID",
                        )
                        operation.complete(completion)
                        return
                    try:
                        path_remembered = self._remember_opened_path(
                            result.path
                        )
                    except SecurityStateCommitError as exc:
                        if str(exc) == "AUTHENTICATION_LOCK_BECAME_ACTIVE":
                            self._destroy_open_result(result)
                            try:
                                locked_until = (
                                    self._security.get_lock_until_unix_ms(
                                        str(result.path),
                                        strict=True,
                                    )
                                )
                            except SecurityStateCommitError:
                                locked_until = 0
                            completion = self._operation_error(
                                operation,
                                (
                                    "LOCKED_OUT"
                                    if locked_until > 0
                                    else "DATABASE_IO_FAILED"
                                ),
                                retry_after_ms=(
                                    self._retry_after_ms(locked_until)
                                    if locked_until > 0
                                    else 0
                                ),
                            )
                            operation.complete(completion)
                            return
                        path_remembered = False
                    except Exception:
                        path_remembered = False
                    if not path_remembered:
                        self._destroy_open_result(result)
                        completion = self._operation_error(
                            operation,
                            "DATABASE_IO_FAILED",
                        )
                    else:
                        try:
                            recent_databases = self._recent_databases()
                        except SecurityStateCommitError:
                            self._destroy_open_result(result)
                            completion = self._operation_error(
                                operation,
                                "DATABASE_IO_FAILED",
                            )
                            operation.complete(completion)
                            return
                        current_identity = self._file_identity(result.path)
                        if (
                            current_identity is None
                            or not self._same_file_object(
                                result.file_identity,
                                current_identity,
                            )
                        ):
                            self._destroy_open_result(result)
                            completion = self._operation_error(
                                operation,
                                "DATABASE_INVALID",
                            )
                            operation.complete(completion)
                            return
                        self._release_session_locked()
                        session_epoch = self._next_session_epoch
                        self._next_session_epoch += 1
                        self._revision += 1
                        self._database = result.database
                        self._database_path = result.path
                        self._session_token = operation.token
                        self._session_epoch = session_epoch
                        self._session_revision_key = secrets.token_bytes(32)
                        self._start_strength_queue(operation.page_epoch)
                        self._expected_existing_paths_by_page.setdefault(
                            operation.page_epoch,
                            set(),
                        ).add(self._path_key(result.path))
                        completion = self._operation_success(
                            operation,
                            {
                                "sessionEpoch": session_epoch,
                                "state": "UNLOCKED",
                                "databaseLabel": result.path.name,
                                "passwordCount": result.password_count,
                                "upgradeBackupName": Path(result.database.migration_snapshot_path).name if result.database.migration_snapshot_path else "",
                                "noteCount": result.note_count,
                                "vaultRevision": self._revision_value(
                                    "vault"
                                ),
                                "noteRevision": self._revision_value(
                                    "note"
                                ),
                                "healthRevision": self._revision_value(
                                    "health"
                                ),
                                "recentDatabases": recent_databases,
                            },
                        )
            operation.complete(completion)
        finally:
            if operation is not None:
                operation.settled.set()

    def _submit_list_vault(
        self,
        request: AdapterRequest,
        complete: CompletionCallback,
    ) -> None:
        with self._lock:
            context_error = self._session_read_error_locked(request, allow_pending_work=True)
            if context_error:
                complete(self._error(request, context_error))
                return
            database = self._database
            revision_key = self._session_revision_key
            if database is None or revision_key is None:
                complete(self._error(request, "SESSION_REQUIRED"))
                return
            operation = _SessionReadOperation(
                request_id=request.request_id,
                token=request.token,
                command_id=request.command_id,
                page_epoch=request.page_epoch,
                session_epoch=request.session_epoch,
                database=database,
                complete=complete,
                cancelled=threading.Event(),
                settled=threading.Event(),
            )
            self._operations[request.request_id] = operation
            future = self._submit_worker(
                self._list_vault,
                database,
                revision_key,
                str(request.arguments[3]),
                str(request.arguments[4]),
                str(request.arguments[5]),
                str(request.arguments[6]),
                int(request.arguments[7]),
                operation.cancelled,
            )
            operation.future = future
            future.add_done_callback(
                lambda finished, request_id=request.request_id:
                self._finish_session_read(request_id, finished)
            )

    def _submit_locate_vault_record(
        self,
        request: AdapterRequest,
        complete: CompletionCallback,
    ) -> None:
        with self._lock:
            context_error = self._session_read_error_locked(
                request,
                allow_pending_work=True,
            )
            if context_error:
                complete(self._error(request, context_error))
                return
            database = self._database
            revision_key = self._session_revision_key
            if database is None or revision_key is None:
                complete(self._error(request, "SESSION_REQUIRED"))
                return
            operation = _SessionReadOperation(
                request_id=request.request_id,
                token=request.token,
                command_id=request.command_id,
                page_epoch=request.page_epoch,
                session_epoch=request.session_epoch,
                database=database,
                complete=complete,
                cancelled=threading.Event(),
                settled=threading.Event(),
            )
            self._operations[request.request_id] = operation
            future = self._submit_worker(
                self._locate_vault_record,
                database,
                revision_key,
                int(request.arguments[3]),
                str(request.arguments[4]),
                str(request.arguments[5]),
                operation.cancelled,
            )
            operation.future = future
            future.add_done_callback(
                lambda finished, request_id=request.request_id:
                self._finish_session_read(request_id, finished)
            )

    def _submit_health_rescan(
        self, request: AdapterRequest, complete: CompletionCallback,
    ) -> None:
        with self._lock:
            error = self._session_read_error_locked(request, allow_pending_work=True)
            if error:
                complete(self._error(request, error))
                return
            scan = self._health_rescan
            if isinstance(scan, SessionStrengthQueue):
                if request.command_id is CommandId.C70:
                    if scan.full_active:
                        complete(self._error(request, "REQUEST_BUSY"))
                        return
                    scan.start_full_scan()
                elif scan.scan_id != request.arguments[3]:
                    complete(self._error(request, "NOT_FOUND"))
                    return
                elif request.command_id is CommandId.C72:
                    scan.cancel_full_scan()
                complete(self._success(request, scan.snapshot()))
                return
            if request.command_id is CommandId.C70:
                if scan is not None and not scan.settled.is_set():
                    complete(self._error(request, "REQUEST_BUSY"))
                    return
                scan = HealthRescan(
                    self._database, self._executor, self._record_is_being_edited,
                )
                self._health_rescan = scan
                try:
                    scan.start()
                except Exception:
                    self._health_rescan = None
                    complete(self._error(request, "INTERNAL_FAILURE"))
                    return
            elif scan is None or scan.scan_id != request.arguments[3]:
                complete(self._error(request, "NOT_FOUND"))
                return
            elif request.command_id is CommandId.C72:
                scan.cancel()
            complete(self._success(request, scan.snapshot()))

    def _record_is_being_edited(self, record_id: int) -> bool:
        """合并窗口占用和短期租约，避免后台体检碰当前记录。"""
        now = self._clock()
        with self._health_edit_lock:
            occupancy = self._editor_occupancy
            occupied = bool(
                occupancy is not None
                and occupancy[0] == "PASSWORD"
                and occupancy[1] == record_id
                and occupancy[2] == self._session_epoch
            )
            self._health_edit_leases = {
                lease_id: entry
                for lease_id, entry in self._health_edit_leases.items()
                if entry[1] > now
            }
            return occupied or any(
                entry[0] == record_id
                for entry in self._health_edit_leases.values()
            )

    @classmethod
    def _retry_record_strength(cls, database, revision_key, record_id, revision, cancelled):
        state = cls._single_record_state(database, revision_key, record_id, cancelled)
        if isinstance(state, str):
            return _SessionReadResult(state)
        row, source, current = state
        try:
            if not hmac.compare_digest(current, revision):
                return _SessionReadResult("REVISION_CONFLICT")
            queue = _RATING_QUEUE.get()
            if queue is None or cancelled.is_set():
                return _SessionReadResult("CANCELLED")
            strength = cls._record_strength(row, revision_key)
            if strength == "CHECKING":
                return _SessionReadResult("REQUEST_BUSY")
            if row.get("strength") is None:
                queue.wake(record_id, retry=True)
                strength = "PENDING"
            return _SessionReadResult("OK", {"recordId": record_id, "revision": current, "strength": strength})
        finally:
            cls._scrub_record_dict(row)
            cls._scrub_revision_source(source)

    def _submit_health_summary(
        self,
        request: AdapterRequest,
        complete: CompletionCallback,
    ) -> None:
        with self._lock:
            context_error = self._session_read_error_locked(
                request,
                allow_pending_work=True,
            )
            if context_error:
                complete(self._error(request, context_error))
                return
            database = self._database
            revision_key = self._session_revision_key
            if database is None or revision_key is None:
                complete(self._error(request, "SESSION_REQUIRED"))
                return
            operation = _SessionReadOperation(
                request_id=request.request_id,
                token=request.token,
                command_id=request.command_id,
                page_epoch=request.page_epoch,
                session_epoch=request.session_epoch,
                database=database,
                complete=complete,
                cancelled=threading.Event(),
                settled=threading.Event(),
            )
            self._operations[request.request_id] = operation
            future = self._submit_worker(
                self._health_summary,
                database,
                revision_key,
                self._stale_days(),
                operation.cancelled,
            )
            operation.future = future
            future.add_done_callback(
                lambda finished, request_id=request.request_id:
                self._finish_session_read(request_id, finished)
            )

    def _submit_health_overview_at(
        self,
        request: AdapterRequest,
        complete: CompletionCallback,
    ) -> None:
        with self._lock:
            context_error = self._session_read_error_locked(
                request,
                allow_pending_work=True,
            )
            if context_error:
                complete(self._error(request, context_error))
                return
            database = self._database
            revision_key = self._session_revision_key
            if database is None or revision_key is None:
                complete(self._error(request, "SESSION_REQUIRED"))
                return
            operation = _SessionReadOperation(
                request_id=request.request_id,
                token=request.token,
                command_id=request.command_id,
                page_epoch=request.page_epoch,
                session_epoch=request.session_epoch,
                database=database,
                complete=complete,
                cancelled=threading.Event(),
                settled=threading.Event(),
            )
            self._operations[request.request_id] = operation
            future = self._submit_worker(
                self._health_overview_at,
                database,
                revision_key,
                self._stale_days(),
                str(request.arguments[3]),
                int(request.arguments[4]),
                operation.cancelled,
            )
            operation.future = future
            future.add_done_callback(
                lambda finished, request_id=request.request_id:
                self._finish_session_read(request_id, finished)
            )

    def _submit_health_guidance_page(
        self,
        request: AdapterRequest,
        complete: CompletionCallback,
    ) -> None:
        guidance_id = str(request.arguments[3])
        cursor = str(request.arguments[4])
        with self._lock:
            context_error = self._session_read_error_locked(
                request,
                allow_pending_work=True,
            )
            if context_error:
                complete(self._error(request, context_error))
                return
            snapshot = self._health_guidance if guidance_id else None
            if not guidance_id and cursor:
                complete(self._error(request, "INVALID_ARGUMENT"))
                return
            if guidance_id and (
                snapshot is None
                or snapshot.guidance_id != guidance_id
                or snapshot.page_epoch != request.page_epoch
                or snapshot.session_epoch != request.session_epoch
            ):
                complete(self._error(request, "NOT_FOUND"))
                return
            database = self._database
            revision_key = self._session_revision_key
            if database is None or revision_key is None:
                complete(self._error(request, "SESSION_REQUIRED"))
                return
            operation = _SessionReadOperation(
                request_id=request.request_id,
                token=request.token,
                command_id=request.command_id,
                page_epoch=request.page_epoch,
                session_epoch=request.session_epoch,
                database=database,
                complete=complete,
                cancelled=threading.Event(),
                settled=threading.Event(),
            )
            self._operations[request.request_id] = operation
            future = self._submit_worker(
                self._health_guidance_page,
                database,
                revision_key,
                self._stale_days(),
                snapshot,
                request.page_epoch,
                request.session_epoch,
                cursor,
                operation.cancelled,
            )
            operation.future = future
            future.add_done_callback(
                lambda finished, request_id=request.request_id:
                self._finish_session_read(request_id, finished)
            )

    def _submit_release_health_guidance(
        self,
        request: AdapterRequest,
        complete: CompletionCallback,
    ) -> None:
        guidance_id = str(request.arguments[3])
        with self._lock:
            context_error = self._session_read_error_locked(request)
            if context_error:
                complete(self._error(request, context_error))
                return
            snapshot = self._health_guidance
            released = self._released_health_guidance_id == guidance_id
            if (
                snapshot is not None
                and snapshot.guidance_id == guidance_id
                and snapshot.page_epoch == request.page_epoch
                and snapshot.session_epoch == request.session_epoch
            ):
                self._health_guidance = None
                self._released_health_guidance_id = guidance_id
                released = True
        complete(self._success(request, {"released": released}))

    def _submit_list_health_issues(
        self,
        request: AdapterRequest,
        complete: CompletionCallback,
    ) -> None:
        with self._lock:
            context_error = self._session_read_error_locked(
                request,
                allow_pending_work=True,
            )
            if context_error:
                complete(self._error(request, context_error))
                return
            database = self._database
            revision_key = self._session_revision_key
            if database is None or revision_key is None:
                complete(self._error(request, "SESSION_REQUIRED"))
                return
            operation = _SessionReadOperation(
                request_id=request.request_id,
                token=request.token,
                command_id=request.command_id,
                page_epoch=request.page_epoch,
                session_epoch=request.session_epoch,
                database=database,
                complete=complete,
                cancelled=threading.Event(),
                settled=threading.Event(),
            )
            self._operations[request.request_id] = operation
            future = self._submit_worker(
                self._list_health_issues,
                database,
                revision_key,
                self._stale_days(),
                str(request.arguments[3]),
                str(request.arguments[4]),
                int(request.arguments[5]),
                operation.cancelled,
            )
            operation.future = future
            future.add_done_callback(
                lambda finished, request_id=request.request_id:
                self._finish_session_read(request_id, finished)
            )

    def _submit_open_quickbar(
        self,
        request: AdapterRequest,
        complete: CompletionCallback,
    ) -> None:
        """Authorize only a fixed native show intent for the current session."""

        with self._lock:
            context_error = self._session_read_error_locked(request)
            if context_error:
                complete(self._error(request, context_error))
                return
            if (
                not self._quickbar_enabled()
            ):
                complete(self._error(request, "UNSUPPORTED_STATE"))
                return
        complete(self._success(request, {}))

    def _submit_quickbar_search(
        self,
        request: AdapterRequest,
        complete: CompletionCallback,
    ) -> None:
        with self._lock:
            context_error = self._native_session_error_locked(request, allow_pending_work=True)
            if context_error:
                complete(self._error(request, context_error))
                return
            database = self._database
            revision_key = self._session_revision_key
            if database is None or revision_key is None:
                complete(self._error(request, "SESSION_REQUIRED"))
                return
            operation = _SessionReadOperation(
                request_id=request.request_id,
                token=request.token,
                command_id=request.command_id,
                page_epoch=0,
                session_epoch=request.session_epoch,
                database=database,
                complete=complete,
                cancelled=threading.Event(),
                settled=threading.Event(),
            )
            self._operations[request.request_id] = operation
            future = self._submit_worker(
                self._quickbar_search,
                database,
                revision_key,
                str(request.arguments[2]),
                int(request.arguments[3]),
                operation.cancelled,
            )
            operation.future = future
            future.add_done_callback(
                lambda finished, request_id=request.request_id:
                self._finish_session_read(request_id, finished)
            )

    def _submit_quickbar_generate(
        self,
        request: AdapterRequest,
        complete: CompletionCallback,
    ) -> None:
        with self._lock:
            context_error = self._native_session_error_locked(request, allow_pending_work=True)
            if context_error:
                complete(self._error(request, context_error))
                return
            operation = _SessionReadOperation(
                request_id=request.request_id,
                token=request.token,
                command_id=request.command_id,
                page_epoch=0,
                session_epoch=request.session_epoch,
                database=self._database,
                complete=complete,
                cancelled=threading.Event(),
                settled=threading.Event(),
            )
            if operation.database is None:
                complete(self._error(request, "SESSION_REQUIRED"))
                return
            self._operations[request.request_id] = operation
            future = self._submit_worker(
                self._quickbar_generate_and_copy,
                int(request.arguments[2]),
                self._clipboard,
                operation.cancelled,
                publication_token=self._clipboard.publication_token(session_epoch=request.session_epoch),
            )
            operation.future = future
            future.add_done_callback(
                lambda finished, request_id=request.request_id:
                self._finish_session_read(request_id, finished)
            )

    def _submit_record_details(
        self,
        request: AdapterRequest,
        complete: CompletionCallback,
    ) -> None:
        with self._lock:
            context_error = self._session_read_error_locked(request, allow_pending_work=True)
            if context_error:
                complete(self._error(request, context_error))
                return
            database = self._database
            revision_key = self._session_revision_key
            if database is None or revision_key is None:
                complete(self._error(request, "SESSION_REQUIRED"))
                return
            operation = _SessionReadOperation(
                request_id=request.request_id,
                token=request.token,
                command_id=request.command_id,
                page_epoch=request.page_epoch,
                session_epoch=request.session_epoch,
                database=database,
                complete=complete,
                cancelled=threading.Event(),
                settled=threading.Event(),
            )
            self._operations[request.request_id] = operation
            future = self._submit_worker(
                self._record_details,
                database,
                revision_key,
                int(request.arguments[3]),
                str(request.arguments[4]),
                operation.cancelled,
            )
            operation.future = future
            future.add_done_callback(
                lambda finished, request_id=request.request_id:
                self._finish_session_read(request_id, finished)
            )

    def _submit_list_notes(
        self,
        request: AdapterRequest,
        complete: CompletionCallback,
    ) -> None:
        with self._lock:
            context_error = self._session_read_error_locked(request, allow_pending_work=True)
            if context_error:
                complete(self._error(request, context_error))
                return
            database = self._database
            revision_key = self._session_revision_key
            if database is None or revision_key is None:
                complete(self._error(request, "SESSION_REQUIRED"))
                return
            operation = _SessionReadOperation(
                request_id=request.request_id,
                token=request.token,
                command_id=request.command_id,
                page_epoch=request.page_epoch,
                session_epoch=request.session_epoch,
                database=database,
                complete=complete,
                cancelled=threading.Event(),
                settled=threading.Event(),
            )
            self._operations[request.request_id] = operation
            future = self._submit_worker(
                self._list_notes,
                database,
                revision_key,
                str(request.arguments[3]),
                str(request.arguments[4]),
                str(request.arguments[5]),
                int(request.arguments[6]),
                operation.cancelled,
                sort_mode=str(request.arguments[7]),
            )
            operation.future = future
            future.add_done_callback(
                lambda finished, request_id=request.request_id:
                self._finish_session_read(request_id, finished)
            )

    def _submit_note_details(
        self,
        request: AdapterRequest,
        complete: CompletionCallback,
    ) -> None:
        with self._lock:
            context_error = self._session_read_error_locked(request, allow_pending_work=True)
            if context_error:
                complete(self._error(request, context_error))
                return
            database = self._database
            revision_key = self._session_revision_key
            if database is None or revision_key is None:
                complete(self._error(request, "SESSION_REQUIRED"))
                return
            operation = _SessionReadOperation(
                request_id=request.request_id,
                token=request.token,
                command_id=request.command_id,
                page_epoch=request.page_epoch,
                session_epoch=request.session_epoch,
                database=database,
                complete=complete,
                cancelled=threading.Event(),
                settled=threading.Event(),
            )
            self._operations[request.request_id] = operation
            future = self._submit_worker(
                self._note_details,
                database,
                revision_key,
                int(request.arguments[3]),
                str(request.arguments[4]),
                operation.cancelled,
            )
            operation.future = future
            future.add_done_callback(
                lambda finished, request_id=request.request_id:
                self._finish_session_read(request_id, finished)
            )

    def _submit_create_note(
        self,
        request: AdapterRequest,
        complete: CompletionCallback,
    ) -> None:
        with self._lock:
            context_error = self._session_read_error_locked(request, allow_pending_work=True)
            if context_error:
                complete(self._error(request, context_error))
                return
            database = self._database
            revision_key = self._session_revision_key
            if database is None or revision_key is None:
                complete(self._error(request, "SESSION_REQUIRED"))
                return
            operation = _SessionReadOperation(
                request_id=request.request_id,
                token=request.token,
                command_id=request.command_id,
                page_epoch=request.page_epoch,
                session_epoch=request.session_epoch,
                database=database,
                complete=complete,
                cancelled=threading.Event(),
                settled=threading.Event(),
            )
            self._operations[request.request_id] = operation
            future = self._submit_worker(
                self._create_note,
                database,
                revision_key,
                str(request.arguments[3]),
                str(request.arguments[4]),
                request.arguments[5],
                operation.cancelled,
            )
            operation.future = future
            future.add_done_callback(
                lambda finished, request_id=request.request_id:
                self._finish_session_read(request_id, finished)
            )

    def _submit_session_worker(
        self,
        request: AdapterRequest,
        complete: CompletionCallback,
        worker: Callable[..., _SessionReadResult],
        *arguments: object,
    ) -> None:
        with self._lock:
            error = self._session_read_error_locked(request, allow_pending_work=True)
            if error:
                complete(self._error(request, error)); return
            database, key = self._database, self._session_revision_key
            if database is None or key is None:
                complete(self._error(request, "SESSION_REQUIRED")); return
            operation = _SessionReadOperation(request.request_id, request.token, request.command_id, request.page_epoch, request.session_epoch, database, complete, threading.Event(), threading.Event())
            self._operations[request.request_id] = operation
            future = self._submit_worker(worker, database, key, *arguments, operation.cancelled)
            operation.future = future
            future.add_done_callback(lambda finished, request_id=request.request_id: self._finish_session_read(request_id, finished))

    def _submit_update_note(self, request: AdapterRequest, complete: CompletionCallback) -> None:
        self._submit_session_worker(request, complete, self._update_note, request.arguments[3], request.arguments[4], request.arguments[5], request.arguments[6], request.arguments[7])

    def _submit_set_note_favorite(self, request: AdapterRequest, complete: CompletionCallback) -> None:
        self._submit_session_worker(request, complete, self._set_note_favorite, request.arguments[3], request.arguments[4], request.arguments[5])

    def _submit_prepare_delete_note(self, request: AdapterRequest, complete: CompletionCallback) -> None:
        self._submit_session_worker(request, complete, self._prepare_delete_note, request.arguments[3], request.arguments[4])

    def _submit_update_note_fields(self, request: AdapterRequest, complete: CompletionCallback) -> None:
        self._submit_session_worker(request, complete, self._update_note_fields, request.arguments[3], request.arguments[4], request.arguments[5], request.arguments[6], request.arguments[7], request.arguments[8], request.arguments[9])

    def _submit_note_field_chunk(self, request: AdapterRequest, complete: CompletionCallback) -> None:
        with self._lock:
            error = self._session_read_error_locked(request, allow_pending_work=True)
            if error:
                complete(self._error(request, error)); return
            database, key = self._database, self._session_revision_key
            if database is None or key is None:
                complete(self._error(request, "SESSION_REQUIRED")); return
            operation = _SessionReadOperation(request.request_id, request.token, request.command_id, request.page_epoch, request.session_epoch, database, complete, threading.Event(), threading.Event())
            operation.record_field_read_id = str(request.arguments[6])
            self._operations[request.request_id] = operation
            future = self._submit_worker(self._read_note_field_chunk, database, key, request.page_epoch, request.session_epoch, request.arguments[3], request.arguments[4], request.arguments[5], request.arguments[6], request.arguments[7], operation.cancelled)
            operation.future = future
            future.add_done_callback(lambda finished, request_id=request.request_id: self._finish_session_read(request_id, finished))

    def _submit_release_note_field_read(self, request: AdapterRequest, complete: CompletionCallback) -> None:
        with self._lock:
            error = self._session_read_error_locked(request, allow_pending_work=True)
            if error:
                complete(self._error(request, error)); return
            released = self._note_field_reads.release(str(request.arguments[3]), page_epoch=request.page_epoch, session_epoch=request.session_epoch)
        complete(self._success(request, {"released": released}))

    def _submit_open_record_editor(
        self,
        request: AdapterRequest,
        complete: CompletionCallback,
    ) -> None:
        with self._lock:
            context_error = self._session_read_error_locked(request, allow_pending_work=True)
            if context_error:
                complete(self._error(request, context_error))
                return
            database = self._database
            revision_key = self._session_revision_key
            if database is None or revision_key is None:
                complete(self._error(request, "SESSION_REQUIRED"))
                return
            operation = _SessionReadOperation(
                request_id=request.request_id,
                token=request.token,
                command_id=request.command_id,
                page_epoch=request.page_epoch,
                session_epoch=request.session_epoch,
                database=database,
                complete=complete,
                cancelled=threading.Event(),
                settled=threading.Event(),
            )
            self._operations[request.request_id] = operation
            future = self._submit_worker(
                self._open_record_editor,
                database,
                revision_key,
                int(request.arguments[3]),
                str(request.arguments[4]),
                operation.cancelled,
            )
            operation.future = future
            future.add_done_callback(
                lambda finished, request_id=request.request_id:
                self._finish_session_read(request_id, finished)
            )

    def _submit_create_record(
        self,
        request: AdapterRequest,
        complete: CompletionCallback,
    ) -> None:
        with self._lock:
            context_error = self._session_read_error_locked(request, allow_pending_work=True)
            if context_error:
                complete(self._error(request, context_error))
                return
            database = self._database
            revision_key = self._session_revision_key
            if database is None or revision_key is None:
                complete(self._error(request, "SESSION_REQUIRED"))
                return
            operation = _SessionReadOperation(
                request_id=request.request_id,
                token=request.token,
                command_id=request.command_id,
                page_epoch=request.page_epoch,
                session_epoch=request.session_epoch,
                database=database,
                complete=complete,
                cancelled=threading.Event(),
                settled=threading.Event(),
            )
            self._operations[request.request_id] = operation
            future = self._submit_worker(
                self._create_record,
                database,
                revision_key,
                str(request.arguments[3]),
                str(request.arguments[4]),
                str(request.arguments[5]),
                str(request.arguments[6]),
                str(request.arguments[7]),
                str(request.arguments[8]),
                bool(request.arguments[9]),
                operation.cancelled,
                recovery_text=request.arguments[10],
            )
            operation.future = future
            future.add_done_callback(
                lambda finished, request_id=request.request_id:
                self._finish_session_read(request_id, finished)
            )

    def _submit_update_record(
        self,
        request: AdapterRequest,
        complete: CompletionCallback,
    ) -> None:
        with self._lock:
            context_error = self._session_read_error_locked(request, allow_pending_work=True)
            if context_error:
                complete(self._error(request, context_error))
                return
            database = self._database
            revision_key = self._session_revision_key
            if database is None or revision_key is None:
                complete(self._error(request, "SESSION_REQUIRED"))
                return
            operation = _SessionReadOperation(
                request_id=request.request_id,
                token=request.token,
                command_id=request.command_id,
                page_epoch=request.page_epoch,
                session_epoch=request.session_epoch,
                database=database,
                complete=complete,
                cancelled=threading.Event(),
                settled=threading.Event(),
            )
            self._operations[request.request_id] = operation
            future = self._submit_worker(
                self._update_record,
                database,
                revision_key,
                int(request.arguments[3]),
                str(request.arguments[4]),
                str(request.arguments[6]),
                str(request.arguments[7]),
                str(request.arguments[8]),
                str(request.arguments[9]),
                str(request.arguments[10]),
                str(request.arguments[11]),
                str(request.arguments[12]),
                request.arguments[13],
                operation.cancelled,
                recovery_action=request.arguments[14],
                recovery_text=request.arguments[15],
            )
            operation.future = future
            future.add_done_callback(
                lambda finished, request_id=request.request_id:
                self._finish_session_read(request_id, finished)
            )

    def _submit_update_record_fields(
        self,
        request: AdapterRequest,
        complete: CompletionCallback,
    ) -> None:
        with self._lock:
            context_error = self._session_read_error_locked(request, allow_pending_work=True)
            if context_error:
                complete(self._error(request, context_error))
                return
            database = self._database
            revision_key = self._session_revision_key
            if database is None or revision_key is None:
                complete(self._error(request, "SESSION_REQUIRED"))
                return
            operation = _SessionReadOperation(
                request_id=request.request_id,
                token=request.token,
                command_id=request.command_id,
                page_epoch=request.page_epoch,
                session_epoch=request.session_epoch,
                database=database,
                complete=complete,
                cancelled=threading.Event(),
                settled=threading.Event(),
            )
            self._operations[request.request_id] = operation
            future = self._submit_worker(
                self._update_record_fields,
                database,
                revision_key,
                request.arguments[3],
                request.arguments[4],
                request.arguments[6],
                request.arguments[7],
                request.arguments[8],
                request.arguments[9],
                request.arguments[10],
                request.arguments[11],
                request.arguments[12],
                request.arguments[13],
                request.arguments[14],
                request.arguments[15],
                request.arguments[16],
                operation.cancelled,
                recovery_action=request.arguments[17],
                recovery_text=request.arguments[18],
            )
            operation.future = future
            future.add_done_callback(
                lambda finished, request_id=request.request_id:
                self._finish_session_read(request_id, finished)
            )

    def _submit_set_record_favorite(
        self,
        request: AdapterRequest,
        complete: CompletionCallback,
    ) -> None:
        record_id = request.arguments[3]
        revision = request.arguments[4]
        favorite = request.arguments[5]
        if type(record_id) is not int or record_id <= 0:
            complete(self._error(request, "INVALID_ARGUMENT", error_argument_index=4))
            return
        if type(revision) is not str or type(favorite) is not bool:
            complete(self._error(request, "INVALID_ARGUMENT"))
            return
        with self._lock:
            context_error = self._session_read_error_locked(request, allow_pending_work=True)
            if context_error:
                complete(self._error(request, context_error))
                return
            if self._record_is_occupied("PASSWORD", record_id):
                complete(self._error(request, "REQUEST_BUSY"))
                return
            database = self._database
            revision_key = self._session_revision_key
            if database is None or revision_key is None:
                complete(self._error(request, "SESSION_REQUIRED"))
                return
            operation = _SessionReadOperation(
                request_id=request.request_id,
                token=request.token,
                command_id=request.command_id,
                page_epoch=request.page_epoch,
                session_epoch=request.session_epoch,
                database=database,
                complete=complete,
                cancelled=threading.Event(),
                settled=threading.Event(),
            )
            self._operations[request.request_id] = operation
            future = self._submit_worker(
                self._set_record_favorite,
                database,
                revision_key,
                record_id,
                revision,
                favorite,
                operation.cancelled,
            )
            operation.future = future
            future.add_done_callback(
                lambda finished, request_id=request.request_id:
                self._finish_session_read(request_id, finished)
            )

    def _submit_record_field_chunk(self, request: AdapterRequest, complete: CompletionCallback) -> None:
        with self._lock:
            error = self._session_read_error_locked(request, allow_pending_work=True)
            if error:
                complete(self._error(request, error)); return
            database, key = self._database, self._session_revision_key
            if database is None or key is None:
                complete(self._error(request, "SESSION_REQUIRED")); return
            operation = _SessionReadOperation(request.request_id, request.token, request.command_id, request.page_epoch, request.session_epoch, database, complete, threading.Event(), threading.Event())
            self._operations[request.request_id] = operation
            operation.record_field_read_id = str(request.arguments[7])
            future = self._submit_worker(self._read_record_field_chunk, database, key, request.page_epoch, request.session_epoch, int(request.arguments[3]), str(request.arguments[4]), str(request.arguments[5]), str(request.arguments[6]), str(request.arguments[7]), request.arguments[8], operation.cancelled)
            operation.future = future
            future.add_done_callback(lambda finished, request_id=request.request_id: self._finish_session_read(request_id, finished))

    def _submit_release_record_field_read(self, request: AdapterRequest, complete: CompletionCallback) -> None:
        with self._lock:
            error = self._session_read_error_locked(request, allow_pending_work=True)
            if error:
                complete(self._error(request, error)); return
            released = self._record_field_reads.release(str(request.arguments[3]), page_epoch=request.page_epoch, session_epoch=request.session_epoch)
        complete(self._success(request, {"released": released}))

    def _submit_prepare_delete_record(
        self,
        request: AdapterRequest,
        complete: CompletionCallback,
    ) -> None:
        with self._lock:
            context_error = self._session_read_error_locked(request, allow_pending_work=True)
            if context_error:
                complete(self._error(request, context_error))
                return
            if self._record_is_occupied(
                "PASSWORD",
                int(request.arguments[3]),
            ):
                complete(self._error(request, "REQUEST_BUSY"))
                return
            database = self._database
            revision_key = self._session_revision_key
            if database is None or revision_key is None:
                complete(self._error(request, "SESSION_REQUIRED"))
                return
            operation = _SessionReadOperation(
                request_id=request.request_id,
                token=request.token,
                command_id=request.command_id,
                page_epoch=request.page_epoch,
                session_epoch=request.session_epoch,
                database=database,
                complete=complete,
                cancelled=threading.Event(),
                settled=threading.Event(),
            )
            self._operations[request.request_id] = operation
            future = self._submit_worker(
                self._prepare_delete_record,
                database,
                revision_key,
                int(request.arguments[3]),
                str(request.arguments[4]),
                operation.cancelled,
            )
            operation.future = future
            future.add_done_callback(
                lambda finished, request_id=request.request_id:
                self._finish_session_read(request_id, finished)
            )

    def _submit_delete_record(
        self,
        request: AdapterRequest,
        complete: CompletionCallback,
    ) -> None:
        with self._lock:
            context_error = self._session_read_error_locked(request, allow_pending_work=True)
            if context_error:
                complete(self._error(request, context_error))
                return
            self._prune_delete_tickets_locked()
            ticket_value = str(request.arguments[3])
            ticket = self._delete_tickets.get(ticket_value)
            if ticket is None or ticket.entity_kind != "RECORD":
                complete(self._error(request, "SECRET_LEASE_EXPIRED"))
                return
            if self._record_is_occupied("PASSWORD", ticket.record_id):
                complete(self._error(request, "REQUEST_BUSY"))
                return
            self._delete_tickets.pop(ticket_value, None)
            if ticket.page_epoch != request.page_epoch:
                complete(self._error(request, "STALE_PAGE"))
                return
            if ticket.session_epoch != request.session_epoch:
                complete(self._error(request, "STALE_SESSION"))
                return
            database = self._database
            revision_key = self._session_revision_key
            if database is None or revision_key is None:
                complete(self._error(request, "SESSION_REQUIRED"))
                return
            operation = _SessionReadOperation(
                request_id=request.request_id,
                token=request.token,
                command_id=request.command_id,
                page_epoch=request.page_epoch,
                session_epoch=request.session_epoch,
                database=database,
                complete=complete,
                cancelled=threading.Event(),
                settled=threading.Event(),
            )
            self._operations[request.request_id] = operation
            future = self._submit_worker(
                self._delete_record,
                database,
                revision_key,
                ticket.record_id,
                ticket.revision,
                operation.cancelled,
            )
            operation.future = future
            future.add_done_callback(
                lambda finished, request_id=request.request_id:
                self._finish_session_read(request_id, finished)
            )

    def _submit_delete_note(self, request: AdapterRequest, complete: CompletionCallback) -> None:
        with self._lock:
            error = self._session_read_error_locked(request, allow_pending_work=True)
            if error:
                complete(self._error(request, error)); return
            self._prune_delete_tickets_locked()
            ticket = self._delete_tickets.pop(str(request.arguments[3]), None)
            if ticket is None or ticket.entity_kind != "NOTE":
                complete(self._error(request, "SECRET_LEASE_EXPIRED")); return
            if ticket.page_epoch != request.page_epoch:
                complete(self._error(request, "STALE_PAGE")); return
            if ticket.session_epoch != request.session_epoch:
                complete(self._error(request, "STALE_SESSION")); return
            database, key = self._database, self._session_revision_key
            if database is None or key is None:
                complete(self._error(request, "SESSION_REQUIRED")); return
            operation = _SessionReadOperation(request.request_id, request.token, request.command_id, request.page_epoch, request.session_epoch, database, complete, threading.Event(), threading.Event())
            self._operations[request.request_id] = operation
            future = self._submit_worker(self._delete_note, database, key, ticket.record_id, ticket.revision, operation.cancelled)
            operation.future = future
            future.add_done_callback(lambda finished, request_id=request.request_id: self._finish_session_read(request_id, finished))

    def _submit_generate_password(
        self,
        request: AdapterRequest,
        complete: CompletionCallback,
    ) -> None:
        with self._lock:
            if self._closed or request.page_epoch not in self._valid_pages:
                complete(self._error(request, "STALE_PAGE"))
                return
            if any(
                isinstance(operation, _ChangeKeyOperation)
                for operation in self._operations.values()
            ):
                complete(self._error(request, "REQUEST_BUSY"))
                return
            operation = _PageSecretOperation(
                request_id=request.request_id,
                token=request.token,
                command_id=request.command_id,
                page_epoch=request.page_epoch,
                complete=complete,
                cancelled=threading.Event(),
                settled=threading.Event(),
            )
            self._operations[request.request_id] = operation
            future = self._submit_worker(
                self._generate_password,
                int(request.arguments[2]),
                bool(request.arguments[3]),
                bool(request.arguments[4]),
                bool(request.arguments[5]),
                bool(request.arguments[6]),
                bool(request.arguments[7]),
                operation.cancelled,
            )
            operation.future = future
            future.add_done_callback(
                lambda finished, request_id=request.request_id:
                self._finish_page_secret(request_id, finished)
            )

    def _submit_release_secret_lease(
        self,
        request: AdapterRequest,
        complete: CompletionCallback,
    ) -> None:
        with self._lock:
            if self._closed or request.page_epoch not in self._valid_pages:
                complete(self._error(request, "STALE_PAGE"))
                return
        complete(self._success(request, {}))

    def _submit_check_password_strength(
        self,
        request: AdapterRequest,
        complete: CompletionCallback,
    ) -> None:
        fields = (
            (request.arguments[2], 1024, 4096, 3),
            (request.arguments[3], 128, 512, 4),
            (request.arguments[4], 512, 2048, 5),
        )
        for value, max_chars, max_bytes, argument_index in fields:
            if type(value) is not str or "\0" in value:
                complete(
                    self._error(
                        request,
                        "INVALID_ARGUMENT",
                        error_argument_index=argument_index,
                    )
                )
                return
            if len(value) > max_chars or len(value.encode("utf-8")) > max_bytes:
                complete(self._error(request, "REQUEST_TOO_LARGE"))
                return
        with self._lock:
            if self._closed or request.page_epoch not in self._valid_pages:
                complete(self._error(request, "STALE_PAGE"))
                return
            if any(
                isinstance(operation, _ChangeKeyOperation)
                for operation in self._operations.values()
            ):
                complete(self._error(request, "REQUEST_BUSY"))
                return
            for operation in tuple(self._operations.values()):
                if (
                    isinstance(operation, _PageSecretOperation)
                    and operation.command_id is CommandId.C34
                    and operation.page_epoch == request.page_epoch
                ):
                    self._request_operation_cancel_locked(operation)
            operation = _PageSecretOperation(
                request_id=request.request_id,
                token=request.token,
                command_id=request.command_id,
                page_epoch=request.page_epoch,
                complete=complete,
                cancelled=threading.Event(),
                settled=threading.Event(),
            )
            self._operations[request.request_id] = operation
            future = self._strength_executor.submit(
                self._check_password_strength,
                request.arguments[2],
                request.arguments[3],
                request.arguments[4],
                operation.cancelled,
            )
            operation.future = future
            future.add_done_callback(
                lambda finished, request_id=request.request_id:
                self._finish_page_secret(request_id, finished)
            )

    def _submit_copy_generated_password(
        self,
        request: AdapterRequest,
        complete: CompletionCallback,
    ) -> None:
        with self._lock:
            if self._closed or request.page_epoch not in self._valid_pages:
                complete(self._error(request, "STALE_PAGE"))
                return
            self._prune_generated_secrets_locked()
            lease_id = str(request.arguments[2])
            secret = self._generated_secrets.get(lease_id)
            if secret is None or secret.page_epoch != request.page_epoch:
                complete(self._error(request, "SECRET_LEASE_EXPIRED"))
                return
            result = self._clipboard.copy(
                secret.password, "PASSWORD",
                publication_token=self._clipboard.publication_token(page_epoch=request.page_epoch),
            )
        if result is None:
            complete(self._error(request, "CLIPBOARD_UNAVAILABLE"))
            return
        complete(self._success(request, result))

    def _submit_record_secret_action(
        self,
        request: AdapterRequest,
        complete: CompletionCallback,
    ) -> None:
        with self._lock:
            native_command = request.command_id in {
                CommandId.N02,
                CommandId.N03,
            }
            context_error = (
                self._native_session_error_locked(request, allow_pending_work=True)
                if native_command
                else self._session_read_error_locked(request, allow_pending_work=True)
            )
            if context_error:
                complete(self._error(request, context_error))
                return
            database = self._database
            revision_key = self._session_revision_key
            if database is None or revision_key is None:
                complete(self._error(request, "SESSION_REQUIRED"))
                return
            operation = _SessionReadOperation(
                request_id=request.request_id,
                token=request.token,
                command_id=request.command_id,
                page_epoch=0 if native_command else request.page_epoch,
                session_epoch=request.session_epoch,
                database=database,
                complete=complete,
                cancelled=threading.Event(),
                settled=threading.Event(),
            )
            self._operations[request.request_id] = operation
            future = self._submit_worker(
                self._record_secret_action,
                database,
                revision_key,
                request.command_id,
                int(request.arguments[2] if native_command else request.arguments[3]),
                str(request.arguments[3] if native_command else request.arguments[4]),
                self._clipboard,
                operation.cancelled,
                wall_clock=time.time,
                monotonic_clock=self._clock,
                publication_token=self._clipboard.publication_token(
                    page_epoch=None if native_command else request.page_epoch,
                    session_epoch=request.session_epoch,
                ) if request.command_id in {CommandId.C19, CommandId.C20, CommandId.C22,
                                           CommandId.C78, CommandId.N02, CommandId.N03} else None,
                code_index=request.arguments[5] if request.command_id in {CommandId.C77, CommandId.C78} else None,
            )
            operation.future = future
            future.add_done_callback(
                lambda finished, request_id=request.request_id:
                self._finish_session_read(request_id, finished)
            )

    def _submit_clear_clipboard(
        self,
        request: AdapterRequest,
        complete: CompletionCallback,
    ) -> None:
        with self._lock:
            if self._closed or request.page_epoch not in self._valid_pages:
                complete(self._error(request, "STALE_PAGE"))
                return
            if self._has_non_strength_operation_locked():
                complete(self._error(request, "REQUEST_BUSY"))
                return
        result = self._clipboard.clear_owned()
        if result is None:
            complete(self._error(request, "CLIPBOARD_UNAVAILABLE"))
            return
        complete(self._success(request, result))

    def _submit_setting(
        self,
        request: AdapterRequest,
        complete: CompletionCallback,
    ) -> None:
        if request.command_id is CommandId.C36:
            setting_key = "theme"
            allowed = {"LIGHT", "DARK", "AUTO"}
            value_index = 2
        elif request.command_id is CommandId.C37:
            setting_key = "language"
            allowed = {"ZH", "EN"}
            value_index = 2
        elif request.command_id is CommandId.C73:
            setting_key = "ui_font_scale"
            allowed = {"90", "100", "110", "125"}
            value_index = 2
        elif request.command_id is CommandId.C38:
            setting_key = "startup_autofill"
            setting_value = request.arguments[3]
            if type(setting_value) is not bool:
                complete(
                    self._error(
                        request,
                        "INVALID_ARGUMENT",
                        error_argument_index=4,
                    )
                )
                return
            allowed = None
            value_index = -1
        elif request.command_id is CommandId.C39:
            setting_key = "view_mode"
            allowed = {"LIST", "SPLIT"}
            value_index = 3
        elif request.command_id is CommandId.C40:
            setting_key = "sidebar_text"
            setting_value = request.arguments[2]
            if type(setting_value) is not bool:
                complete(
                    self._error(
                        request,
                        "INVALID_ARGUMENT",
                        error_argument_index=3,
                    )
                )
                return
            allowed = None
            value_index = -1
        elif request.command_id is CommandId.C41:
            setting_key = "sort_mode"
            allowed = {"UPDATED", "NAME", "STRENGTH"}
            value_index = 3
        elif request.command_id is CommandId.C42:
            setting_key = "clipboard_policy"
            mode = request.arguments[3]
            seconds = request.arguments[4]
            if type(mode) is not str or mode not in {"COUNTDOWN", "MANUAL"}:
                complete(
                    self._error(
                        request,
                        "INVALID_ARGUMENT",
                        error_argument_index=4,
                    )
                )
                return
            if type(seconds) is not int or not 5 <= seconds <= 60:
                complete(
                    self._error(
                        request,
                        "INVALID_ARGUMENT",
                        error_argument_index=5,
                    )
                )
                return
            setting_value = (mode, seconds)
            allowed = None
            value_index = -1
        elif request.command_id is CommandId.C43:
            setting_key = "close_to_tray"
            allowed = {"TO_TRAY", "EXIT"}
            value_index = 3
        elif request.command_id is CommandId.C44:
            setting_key = "quickbar_policy"
            enabled = request.arguments[3]
            idle_seconds = request.arguments[4]
            if type(enabled) is not bool:
                complete(
                    self._error(
                        request,
                        "INVALID_ARGUMENT",
                        error_argument_index=4,
                    )
                )
                return
            if (
                type(idle_seconds) is not int
                or not 10 <= idle_seconds <= 600
            ):
                complete(
                    self._error(
                        request,
                        "INVALID_ARGUMENT",
                        error_argument_index=5,
                    )
                )
                return
            setting_value = (enabled, idle_seconds)
            allowed = None
            value_index = -1
        elif request.command_id is CommandId.C45:
            setting_key = "quick_bar_hotkey"
            normalized_hotkey = self._normalize_hotkey(
                request.arguments[3]
            )
            if normalized_hotkey is None:
                complete(
                    self._error(
                        request,
                        "HOTKEY_INVALID",
                        error_argument_index=4,
                    )
                )
                return
            setting_value = normalized_hotkey
            allowed = None
            value_index = -1
        elif request.command_id is CommandId.C46:
            setting_key = "stale_threshold_days"
            days = request.arguments[3]
            if type(days) is not int or not 30 <= days <= 365:
                complete(
                    self._error(
                        request,
                        "INVALID_ARGUMENT",
                        error_argument_index=4,
                    )
                )
                return
            setting_value = days
            allowed = None
            value_index = -1
        elif request.command_id is CommandId.C47:
            setting_key = "auto_lock_policy"
            enabled = request.arguments[3]
            minutes = request.arguments[4]
            if type(enabled) is not bool:
                complete(
                    self._error(
                        request,
                        "INVALID_ARGUMENT",
                        error_argument_index=4,
                    )
                )
                return
            if type(minutes) is not int or not 1 <= minutes <= 60:
                complete(
                    self._error(
                        request,
                        "INVALID_ARGUMENT",
                        error_argument_index=5,
                    )
                )
                return
            setting_value = (enabled, minutes)
            allowed = None
            value_index = -1
        elif request.command_id is CommandId.C48:
            length = request.arguments[3]
            values = request.arguments[4:9]
            if type(length) is not int or not 1 <= length <= 1024:
                complete(
                    self._error(
                        request,
                        "INVALID_ARGUMENT",
                        error_argument_index=4,
                    )
                )
                return
            for index, value in enumerate(values, start=5):
                if type(value) is not bool:
                    complete(
                        self._error(
                            request,
                            "INVALID_ARGUMENT",
                            error_argument_index=index,
                        )
                    )
                    return
            selected = sum(values[:4])
            if selected == 0:
                complete(self._error(request, "EMPTY_CHARACTER_SET"))
                return
            if length < selected:
                complete(
                    self._error(request, "GENERATOR_LENGTH_TOO_SHORT")
                )
                return
            setting_key = "generator"
            setting_value = {
                "length": length,
                "useLower": values[0],
                "useUpper": values[1],
                "useDigits": values[2],
                "useSymbols": values[3],
                "avoidAmbiguous": values[4],
            }
            allowed = None
            value_index = -1
        else:
            complete(self._error(request, "INTERNAL_FAILURE"))
            return
        if request.command_id not in {
            CommandId.C38,
            CommandId.C40,
            CommandId.C42,
            CommandId.C44,
            CommandId.C45,
            CommandId.C46,
            CommandId.C47,
            CommandId.C48,
        }:
            setting_value = request.arguments[value_index]
        if (
            allowed is not None
            and (
                type(setting_value) is not str
                or setting_value not in allowed
            )
        ):
            complete(
                self._error(
                    request,
                    "INVALID_ARGUMENT",
                    error_argument_index=value_index + 1,
                )
            )
            return
        with self._lock:
            if request.command_id in {
                CommandId.C38,
                CommandId.C39,
                CommandId.C42,
                CommandId.C43,
                CommandId.C44,
                CommandId.C45,
                CommandId.C46,
                CommandId.C47,
                CommandId.C41,
                CommandId.C48,
            }:
                context_error = self._session_read_error_locked(request)
                if context_error:
                    complete(self._error(request, context_error))
                    return
            elif self._closed or request.page_epoch not in self._valid_pages:
                complete(self._error(request, "STALE_PAGE"))
                return
            if request.request_id in self._settings_operations:
                complete(self._error(request, "REQUEST_BUSY"))
                return
            operation = _SettingsOperation(
                request_id=request.request_id,
                token=request.token,
                command_id=request.command_id,
                page_epoch=request.page_epoch,
                session_epoch=request.session_epoch,
                setting_key=setting_key,
                setting_value=setting_value,
                complete=complete,
                settled=threading.Event(),
            )
            self._settings_operations[request.request_id] = operation
            future = self._settings_executor.submit(
                self._commit_setting,
                setting_key,
                setting_value,
            )
            operation.future = future
            future.add_done_callback(
                lambda finished, request_id=request.request_id:
                self._finish_setting(request_id, finished)
            )

    def _commit_setting(
        self,
        setting_key: str,
        setting_value: object,
    ) -> _SettingsWorkerResult:
        if setting_key == "quickbar_policy":
            return self._commit_quickbar_policy(setting_value)
        if setting_key == "quick_bar_hotkey":
            return self._commit_quickbar_hotkey(setting_value)
        with self._lock:
            before_settings = self._settings_snapshot()
            before_revision = self._settings_revision()
        try:
            if setting_key == "theme":
                current_value = lambda: self._theme_preference().lower()
            elif setting_key == "language":
                current_value = lambda: self._language_preference().lower()
            elif setting_key == "ui_font_scale":
                current_value = self._ui_font_scale
            elif setting_key == "startup_autofill":
                current_value = lambda: self._bounded_bool(
                    self._config.get("startup_autofill", False), False
                )
            elif setting_key == "view_mode":
                def current_value() -> str:
                    value = str(
                        self._config.get("view_mode", "list")
                    ).lower()
                    return value if value in {"list", "split"} else "list"
            elif setting_key == "sidebar_text":
                current_value = lambda: self._bounded_bool(
                    self._config.get("sidebar_text", True), True
                )
            elif setting_key == "close_to_tray":
                current_value = self._close_to_tray_preference
            elif setting_key == "sort_mode":
                def current_value() -> str:
                    value = str(
                        self._config.get("sort_mode", "updated")
                    ).lower()
                    return (
                        value
                        if value in {"updated", "name", "strength"}
                        else "updated"
                    )
            elif setting_key == "stale_threshold_days":
                current_value = lambda: self._bounded_int(
                    self._config.get("stale_threshold_days", 180), 30, 365, 180
                )
            elif setting_key == "auto_lock_policy":
                if (
                    not isinstance(setting_value, tuple)
                    or len(setting_value) != 2
                    or type(setting_value[0]) is not bool
                    or type(setting_value[1]) is not int
                ):
                    return _SettingsWorkerResult("INTERNAL_FAILURE")
                current_values = lambda: {
                    "auto_lock_enabled": self._auto_lock_enabled(),
                    "auto_lock_minutes": self._auto_lock_minutes(),
                }
                persisted_values = {
                    "auto_lock_enabled": setting_value[0],
                    "auto_lock_minutes": setting_value[1],
                }
            elif setting_key == "clipboard_policy":
                if (
                    not isinstance(setting_value, tuple)
                    or len(setting_value) != 2
                    or setting_value[0] not in {"COUNTDOWN", "MANUAL"}
                    or type(setting_value[1]) is not int
                ):
                    return _SettingsWorkerResult("INTERNAL_FAILURE")
                current_values = lambda: {
                    "clipboard_clear_mode": self._clipboard_mode().lower(),
                    "clipboard_clear_seconds": self._clipboard_seconds(),
                }
                persisted_values = {
                    "clipboard_clear_mode": setting_value[0].lower(),
                    "clipboard_clear_seconds": setting_value[1],
                }
            elif setting_key == "generator":
                if not self._generator_options_are_valid(setting_value):
                    return _SettingsWorkerResult("INTERNAL_FAILURE")
                current_value = self._generator_preferences
            else:
                return _SettingsWorkerResult("INTERNAL_FAILURE")
            if setting_key in {"auto_lock_policy", "clipboard_policy"}:
                self._settings_store.commit_values(
                    persisted_values,
                    current_values=current_values,
                )
            else:
                if setting_key == "stale_threshold_days":
                    if type(setting_value) is not int:
                        return _SettingsWorkerResult("INTERNAL_FAILURE")
                    persisted_value: object = setting_value
                elif setting_key == "generator":
                    persisted_value = copy.deepcopy(setting_value)
                elif setting_key in {"startup_autofill", "sidebar_text"}:
                    if type(setting_value) is not bool:
                        return _SettingsWorkerResult("INTERNAL_FAILURE")
                    persisted_value = setting_value
                elif type(setting_value) is not str:
                    return _SettingsWorkerResult("INTERNAL_FAILURE")
                else:
                    persisted_value = setting_value.lower()
                    if setting_key == "close_to_tray":
                        persisted_value = setting_value == "TO_TRAY"
                self._settings_store.commit_value(
                    setting_key,
                    persisted_value,
                    current_value=current_value,
                )
            self._reconcile_quickbar_registration()
            with self._lock:
                settings = self._settings_snapshot()
                settings_revision = self._settings_revision()
                changed = (
                    settings_revision != before_revision
                    or settings != before_settings
                )
        except SettingsCommitError:
            return _SettingsWorkerResult("INTERNAL_FAILURE")
        except Exception:
            return _SettingsWorkerResult("INTERNAL_FAILURE")
        return _SettingsWorkerResult(
            "OK",
            changed=changed,
            settings_revision=settings_revision,
            settings=settings,
        )

    def _commit_quickbar_policy(
        self,
        setting_value: object,
    ) -> _SettingsWorkerResult:
        if (
            not isinstance(setting_value, tuple)
            or len(setting_value) != 2
            or type(setting_value[0]) is not bool
            or type(setting_value[1]) is not int
            or not 10 <= setting_value[1] <= 600
            or self._hotkey is None
        ):
            return _SettingsWorkerResult("INTERNAL_FAILURE")
        enabled, idle_seconds = setting_value
        with self._lock:
            before_settings = self._settings_snapshot()
            before_revision = self._settings_revision()
            session_epoch = self._session_epoch
            old_enabled = self._quickbar_enabled()
            old_idle_seconds = self._quickbar_idle_seconds()
            saved_hotkey = self._quickbar_hotkey()
        registration = "SKIPPED"
        try:
            self._settings_store.refresh_authority()
            old_enabled = self._quickbar_enabled()
            old_idle_seconds = self._quickbar_idle_seconds()
            saved_hotkey = self._quickbar_hotkey()
            registration = self._apply_quickbar_registration(
                enabled,
                saved_hotkey,
                session_epoch,
            )
            if registration == "FAILED":
                return _SettingsWorkerResult("HOTKEY_REGISTER_FAILED")
            self._settings_store.commit_values(
                {
                    "quickbar_enabled": enabled,
                    "quickbar_autohide_sec": idle_seconds,
                },
                current_values=lambda: {
                    "quickbar_enabled": self._quickbar_enabled(),
                    "quickbar_autohide_sec": self._quickbar_idle_seconds(),
                },
            )
        except Exception:
            if registration == "APPLIED":
                self._apply_quickbar_registration(
                    old_enabled,
                    saved_hotkey,
                    session_epoch,
                )
            raise
        self._reconcile_quickbar_registration()
        with self._lock:
            settings = self._settings_snapshot()
            settings_revision = self._settings_revision()
        return _SettingsWorkerResult(
            "OK",
            changed=(
                settings_revision != before_revision
                or settings != before_settings
            ),
            settings_revision=settings_revision,
            settings=settings,
        )

    def _commit_quickbar_hotkey(
        self,
        setting_value: object,
    ) -> _SettingsWorkerResult:
        normalized = self._normalize_hotkey(setting_value)
        if self._hotkey is None or normalized is None:
            return _SettingsWorkerResult("HOTKEY_INVALID")
        with self._lock:
            before_settings = self._settings_snapshot()
            before_revision = self._settings_revision()
            session_epoch = self._session_epoch
            old_hotkey = self._quickbar_hotkey()
            enabled = self._quickbar_enabled()
        registration = "SKIPPED"
        warning = (
            "KNOWN_CONFLICT"
            if check_hotkey_conflict(normalized).conflict
            else "NONE"
        )
        try:
            self._settings_store.refresh_authority()
            old_hotkey = self._quickbar_hotkey()
            enabled = self._quickbar_enabled()
            registration = self._apply_quickbar_registration(
                enabled,
                normalized,
                session_epoch,
            )
            if registration == "FAILED":
                return _SettingsWorkerResult("HOTKEY_REGISTER_FAILED")
            self._settings_store.commit_value(
                "quick_bar_hotkey",
                normalized,
                current_value=self._quickbar_hotkey,
            )
        except Exception:
            if registration == "APPLIED":
                self._apply_quickbar_registration(
                    enabled,
                    old_hotkey,
                    session_epoch,
                )
            raise
        self._reconcile_quickbar_registration()
        with self._lock:
            settings = self._settings_snapshot()
            settings_revision = self._settings_revision()
        return _SettingsWorkerResult(
            "OK",
            changed=(
                settings_revision != before_revision
                or settings != before_settings
            ),
            settings_revision=settings_revision,
            settings=settings,
            warning=warning,
        )

    def _apply_quickbar_registration(
        self,
        enabled: bool,
        hotkey_value: str,
        session_epoch: int,
    ) -> str:
        hotkey = self._hotkey
        if hotkey is None:
            self._quickbar_registration = "DISABLED"
            return "APPLIED" if not enabled else "FAILED"
        with self._lock:
            if (
                self._closed
                or self._session_epoch != session_epoch
                or session_epoch <= 0
                or session_epoch in self._settings_invalidating_sessions
            ):
                return "SKIPPED"

        def apply() -> str:
            if (
                self._closed
                or self._session_epoch != session_epoch
                or session_epoch <= 0
                or session_epoch in self._settings_invalidating_sessions
            ):
                return "SKIPPED"
            if not enabled:
                hotkey.unregister()
                self._quickbar_registration = "DISABLED"
                return "APPLIED"
            registered = hotkey.replace_preserving(hotkey_value)
            self._quickbar_registration = (
                "REGISTERED" if registered else "UNAVAILABLE"
            )
            return "APPLIED" if registered else "FAILED"

        result = self._hotkey_dispatch(apply)
        return result if result in {"APPLIED", "SKIPPED", "FAILED"} else "FAILED"

    def _reconcile_quickbar_registration(self) -> None:
        with self._lock:
            session_epoch = self._session_epoch
            if (
                session_epoch <= 0
                or self._closed
                or session_epoch in self._settings_invalidating_sessions
            ):
                return
            enabled = self._quickbar_enabled()
            hotkey_value = self._quickbar_hotkey()
        self._apply_quickbar_registration(
            enabled,
            hotkey_value,
            session_epoch,
        )

    def _finish_setting(
        self,
        request_id: str,
        future: Future[_SettingsWorkerResult],
    ) -> None:
        operation: _SettingsOperation | None = None
        try:
            try:
                worker_result = future.result()
            except Exception:
                worker_result = _SettingsWorkerResult("INTERNAL_FAILURE")
            with self._lock:
                candidate = self._settings_operations.pop(request_id, None)
                if not isinstance(candidate, _SettingsOperation):
                    return
                operation = candidate
                if (
                    worker_result.error_code == "OK"
                    and worker_result.settings is not None
                ):
                    result = {
                        "settingsRevision": worker_result.settings_revision,
                        "settings": copy.deepcopy(worker_result.settings),
                    }
                    if operation.command_id is CommandId.C45:
                        result["warning"] = worker_result.warning
                    if worker_result.changed:
                        self._settings_publications[request_id] = (
                            SettingsCommitPublication(
                                command_id=operation.command_id,
                                page_epoch=operation.page_epoch,
                                session_epoch=operation.session_epoch,
                                settings_revision=(
                                    worker_result.settings_revision
                                ),
                                settings=copy.deepcopy(
                                    worker_result.settings
                                ),
                            )
                        )
                        while (
                            len(self._settings_publications)
                            > _MAX_SETTINGS_PUBLICATIONS
                        ):
                            oldest = next(iter(self._settings_publications))
                            self._settings_publications.pop(oldest, None)
                    completion = AdapterCompletion(
                        command_id=operation.command_id,
                        request_id=operation.request_id,
                        token=operation.token,
                        error_code="OK",
                        result=result,
                    )
                else:
                    completion = AdapterCompletion(
                        command_id=operation.command_id,
                        request_id=operation.request_id,
                        token=operation.token,
                        error_code=worker_result.error_code,
                    )
            operation.complete(completion)
        finally:
            if operation is not None:
                operation.settled.set()

    def _submit_change_database_password(
        self,
        request: AdapterRequest,
        complete: CompletionCallback,
    ) -> None:
        with self._lock:
            context_error = self._session_read_error_locked(request)
            if context_error:
                complete(self._error(request, context_error))
                return
            if self._operations:
                complete(self._error(request, "REQUEST_BUSY"))
                return
            current_password = request.arguments[3]
            new_password = request.arguments[4]
            confirm_password = request.arguments[5]
            if (
                type(current_password) is not str
                or type(new_password) is not str
                or type(confirm_password) is not str
            ):
                complete(self._error(request, "INVALID_ARGUMENT"))
                return
            if new_password != confirm_password:
                complete(
                    self._error(
                        request,
                        "INVALID_ARGUMENT",
                        error_argument_index=5,
                    )
                )
                return
            database = self._database
            if database is None:
                complete(self._error(request, "SESSION_REQUIRED"))
                return
            operation = _ChangeKeyOperation(
                request_id=request.request_id,
                token=request.token,
                page_epoch=request.page_epoch,
                session_epoch=request.session_epoch,
                database=database,
                complete=complete,
                cancelled=threading.Event(),
                settled=threading.Event(),
                progress=[],
            )
            self._last_change_key_progress = ()
            self._change_key_recovery_snapshot_path = None
            self._operations[request.request_id] = operation
            scan = self._health_rescan
            if isinstance(scan, SessionStrengthQueue):
                scan.pause()
            elif scan is not None:
                scan.cancel()
            future = self._submit_worker(
                self._change_database_password_after_health_rescan,
                scan,
                database,
                current_password,
                new_password,
                operation.cancelled.is_set,
                lambda operation=operation: (
                    self._authorize_change_key_commit(operation)
                ),
                lambda phase, completed, total, operation=operation: (
                    self._record_change_key_progress(
                        operation,
                        phase,
                        completed,
                        total,
                    )
                ),
            )
            operation.future = future
            future.add_done_callback(
                lambda finished, request_id=request.request_id:
                self._finish_change_key(request_id, finished)
            )
            current_password = None
            new_password = None
            confirm_password = None

    def _backup_destination_error_locked(self, selection: BackupSelection) -> str | None:
        """拒绝活动数据库自身或其文件别名；路径和身份始终留在原生层。"""
        database = self._database
        if database is None:
            return "SESSION_REQUIRED"
        path = database.db_name
        expected = database.opened_file_identity
        if not isinstance(path, str) or expected is None:
            return "INTERNAL_FAILURE"
        if os.path.normcase(os.path.normpath(str(selection.path))) == os.path.normcase(os.path.normpath(path)):
            return "BACKUP_TARGET_IS_DATABASE"
        actual = backup_file_identity(selection.path)
        if actual is not None and DatabaseService._same_file_identity(expected, actual[:4]):
            return "BACKUP_TARGET_IS_DATABASE"
        return None

    def _submit_choose_backup_file(
        self,
        request: AdapterRequest,
        complete: CompletionCallback,
    ) -> None:
        with self._lock:
            error = self._session_read_error_locked(request)
            if error:
                complete(self._error(request, error))
                return
        kind = "DESTINATION" if request.command_id is CommandId.C50 else "SOURCE"
        try:
            selected = (
                self._backup_selector.choose_destination()
                if kind == "DESTINATION"
                else self._backup_selector.choose_source()
            )
        except Exception:
            complete(self._error(request, "INTERNAL_FAILURE"))
            return
        with self._lock:
            error = self._session_read_error_locked(request)
            if error:
                complete(self._error(request, error))
                return
            try:
                result = self._backup.mint(
                    kind,
                    selected,
                    request.page_epoch,
                    request.session_epoch,
                )
                if kind == "DESTINATION" and result["selected"]:
                    selection = self._backup.selection(
                        str(result["selectionTicket"]), kind, request.page_epoch, request.session_epoch,
                        consume=False,
                    )
                    destination_error = self._backup_destination_error_locked(selection)
                    if destination_error:
                        self._backup.close_capability(selection.ticket, request.page_epoch, request.session_epoch)
                        raise BackupRejected(destination_error)
            except BackupRejected as exc:
                complete(self._error(request, str(exc)))
                return
        complete(self._success(request, result))

    def _submit_export_backup(
        self,
        request: AdapterRequest,
        complete: CompletionCallback,
    ) -> None:
        backup_password = request.arguments[5]
        confirm_password = request.arguments[6]
        if type(backup_password) is not str or type(confirm_password) is not str:
            complete(self._error(request, "INVALID_ARGUMENT"))
            return
        if backup_password != confirm_password:
            complete(self._error(request, "BACKUP_PASSWORD_MISMATCH", error_argument_index=6))
            return
        with self._lock:
            error = self._backup_operation_error_locked(request)
            if error:
                complete(self._error(request, error))
                return
            try:
                scope, export_selection = self._backup.export_choice(
                    request.page_epoch, request.session_epoch, str(request.arguments[4]))
                selection = self._backup.selection(
                    str(request.arguments[3]),
                    "DESTINATION",
                    request.page_epoch,
                    request.session_epoch,
                    consume=True,
                )
            except BackupRejected as exc:
                complete(self._error(request, str(exc)))
                return
            destination_error = self._backup_destination_error_locked(selection)
            if destination_error:
                complete(self._error(request, destination_error))
                return
            database = self._database
            if database is None:
                complete(self._error(request, "SESSION_REQUIRED"))
                return
            operation = _BackupOperation(
                request.request_id,
                request.token,
                request.command_id,
                request.page_epoch,
                request.session_epoch,
                database,
                complete,
                threading.Event(),
                threading.Event(),
                selection=selection,
            )
            self._operations[request.request_id] = operation
            future = self._submit_worker(
                self._export_backup,
                database,
                selection,
                scope,
                backup_password,
                operation.cancelled,
                lambda: self._authorize_backup_commit(operation),
                export_selection,
                self._session_revision_key,
            )
            operation.future = future
            future.add_done_callback(
                lambda finished, request_id=request.request_id:
                self._finish_backup_operation(request_id, finished)
            )

    def _submit_preview_backup(
        self,
        request: AdapterRequest,
        complete: CompletionCallback,
    ) -> None:
        with self._lock:
            error = self._backup_operation_error_locked(request)
            if error:
                complete(self._error(request, error))
                return
            try:
                selection = self._backup.selection(
                    str(request.arguments[3]),
                    "SOURCE",
                    request.page_epoch,
                    request.session_epoch,
                    consume=False,
                )
            except BackupRejected as exc:
                complete(self._error(request, str(exc)))
                return
            self._backup.begin_preview(selection.ticket)
            database = self._database
            revision_key = self._session_revision_key
            if database is None or revision_key is None:
                complete(self._error(request, "SESSION_REQUIRED"))
                return
            operation = _BackupOperation(
                request.request_id,
                request.token,
                request.command_id,
                request.page_epoch,
                request.session_epoch,
                database,
                complete,
                threading.Event(),
                threading.Event(),
                selection=selection,
            )
            self._operations[request.request_id] = operation
            future = self._submit_worker(
                self._preview_backup,
                database,
                selection,
                revision_key,
                request.arguments[4],
                operation.cancelled,
            )
            operation.future = future
            future.add_done_callback(
                lambda finished, request_id=request.request_id:
                self._finish_backup_operation(request_id, finished)
            )

    def backup_read_remaining_ms(self, read_id: str, page_epoch: int, session_epoch: int) -> int:
        with self._lock:
            if self._closed or page_epoch not in self._valid_pages or session_epoch != self._session_epoch:
                return 0
            return self._backup.read_remaining_ms(read_id, page_epoch, session_epoch)

    def _submit_list_backup_conflicts(
        self,
        request: AdapterRequest,
        complete: CompletionCallback,
    ) -> None:
        with self._lock:
            error = self._session_read_error_locked(request)
            if error:
                complete(self._error(request, error))
                return
            try:
                result = self._backup.list_conflicts(
                    str(request.arguments[3]),
                    request.page_epoch,
                    request.session_epoch,
                    str(request.arguments[4]),
                    str(request.arguments[7]),
                    int(request.arguments[8]),
                    str(request.arguments[5]),
                    str(request.arguments[6]),
                )
            except (BackupRejected, TypeError, ValueError) as exc:
                complete(self._error(request, str(exc) if isinstance(exc, BackupRejected) else "INVALID_ARGUMENT"))
                return
        complete(self._success(request, result))

    def _submit_backup_decision(
        self,
        request: AdapterRequest,
        complete: CompletionCallback,
    ) -> None:
        with self._lock:
            error = self._session_read_error_locked(request)
            if error:
                complete(self._error(request, error))
                return
            try:
                if request.command_id is CommandId.C55:
                    result = self._backup.decide(
                        str(request.arguments[3]),
                        request.page_epoch,
                        request.session_epoch,
                        str(request.arguments[4]),
                        str(request.arguments[5]),
                    )
                else:
                    result = self._backup.decide(
                        str(request.arguments[3]),
                        request.page_epoch,
                        request.session_epoch,
                        None,
                        str(request.arguments[6]),
                        kind=str(request.arguments[4]),
                        conflict_ids=request.arguments[5],
                    )
            except BackupRejected as exc:
                complete(self._error(request, str(exc)))
                return
        complete(self._success(request, result))

    def _submit_backup_field_chunk(
        self,
        request: AdapterRequest,
        complete: CompletionCallback,
    ) -> None:
        with self._lock:
            error = self._session_read_error_locked(request)
            if error:
                complete(self._error(request, error))
                return
            try:
                result = self._backup.read_field(
                    str(request.arguments[3]),
                    request.page_epoch,
                    request.session_epoch,
                    str(request.arguments[4]),
                    str(request.arguments[5]),
                    str(request.arguments[6]),
                    str(request.arguments[7]),
                    int(request.arguments[8]),
                    secret=request.command_id is CommandId.C57,
                )
            except (BackupRejected, TypeError, ValueError) as exc:
                complete(self._error(request, str(exc) if isinstance(exc, BackupRejected) else "INVALID_ARGUMENT"))
                return
        complete(
            AdapterCompletion(
                request.command_id,
                request.request_id,
                request.token,
                "OK",
                result=result,
                delivery_deadline=(
                    self._clock() + int(result["expiresInMs"]) / 1000
                ),
            )
        )

    def _submit_import_backup(
        self,
        request: AdapterRequest,
        complete: CompletionCallback,
    ) -> None:
        ticket = str(request.arguments[3])
        with self._lock:
            error = self._backup_operation_error_locked(request)
            if error:
                self._backup.close_capability(
                    ticket,
                    request.page_epoch,
                    request.session_epoch,
                )
                complete(self._error(request, error))
                return
            try:
                preview = self._backup.take_preview(
                    ticket,
                    request.page_epoch,
                    request.session_epoch,
                )
            except BackupRejected as exc:
                complete(self._error(request, str(exc)))
                return
            if any(value.status == "CONFLICT" and value.decision == "UNDECIDED" for value in preview.conflicts):
                self._backup.finish_import(
                    preview,
                    success=False,
                    retryable=False,
                )
                complete(self._error(request, "BACKUP_CONFLICTS_UNRESOLVED"))
                return
            database = self._database
            if database is None:
                complete(self._error(request, "SESSION_REQUIRED"))
                return
            operation = _BackupOperation(
                request.request_id,
                request.token,
                request.command_id,
                request.page_epoch,
                request.session_epoch,
                database,
                complete,
                threading.Event(),
                threading.Event(),
                preview=preview,
            )
            self._operations[request.request_id] = operation
            future = self._submit_worker(
                self._import_backup,
                database,
                preview,
                operation.cancelled,
                lambda: self._authorize_backup_commit(operation),
            )
            operation.future = future
            future.add_done_callback(
                lambda finished, request_id=request.request_id:
                self._finish_backup_operation(request_id, finished)
            )

    def _submit_close_backup_preview(
        self,
        request: AdapterRequest,
        complete: CompletionCallback,
    ) -> None:
        with self._lock:
            if self._closed or request.page_epoch not in self._valid_pages:
                complete(self._error(request, "STALE_PAGE"))
                return
            if self._database is None:
                complete(self._error(request, "SESSION_REQUIRED"))
                return
            if request.session_epoch != self._session_epoch:
                complete(self._error(request, "STALE_SESSION"))
                return
            self._backup.close_capability(
                str(request.arguments[3]),
                request.page_epoch,
                request.session_epoch,
            )
        complete(self._success(request, {}))

    def close_export_selection(self, page_epoch: int, session_epoch: int) -> None:
        with self._lock:
            self._backup.clear_export_selection(page_epoch, session_epoch)

    def _submit_export_selection(self, request: AdapterRequest, complete: CompletionCallback) -> None:
        with self._lock:
            if request.command_id is CommandId.C90:
                error = ("STALE_PAGE" if self._closed or request.page_epoch not in self._valid_pages else
                         "STALE_SESSION" if request.session_epoch != self._session_epoch else
                         "SESSION_REQUIRED" if self._database is None else None)
            else:
                error = self._backup_operation_error_locked(request)
            if error:
                complete(self._error(request, error)); return
            try:
                if request.command_id is CommandId.C87:
                    complete(self._success(request, self._backup.begin_export_selection(request.page_epoch, request.session_epoch)))
                    return
                value = self._backup.export_selection(str(request.arguments[3]), request.page_epoch, request.session_epoch,
                                                     draft=request.command_id is not CommandId.C90)
                if request.command_id is CommandId.C90:
                    complete(self._success(request, self._backup.finish_export_selection(value, str(request.arguments[4]))))
                    return
                bulk_action = ""
                if request.command_id is CommandId.C89:
                    action, kind, record_id, revision = request.arguments[4:8]
                    if action not in ("ALL", "REMOVE_FILTERED"):
                        complete(self._success(request, self._backup.change_export_selection(value, action, kind, record_id, revision)))
                        return
                    if kind != "ALL" or type(record_id) is not int or record_id or revision != "":
                        raise BackupRejected("INVALID_ARGUMENT")
                    bulk_action = action
                    query, kind, offset, limit = value.query, value.kind, value.offset, value.limit
                else:
                    query, kind, offset, limit = request.arguments[4:8]
                if (type(query) is not str or len(query) > 128 or "\x00" in query
                        or kind not in {"ALL", "PASSWORD", "NOTE"} or type(offset) is not int or not 0 <= offset <= 100_000
                        or type(limit) is not int or not 1 <= limit <= 100):
                    raise BackupRejected("INVALID_ARGUMENT")
            except BackupRejected as exc:
                complete(self._error(request, str(exc))); return
            operation = _BackupOperation(request.request_id, request.token, request.command_id, request.page_epoch,
                                         request.session_epoch, self._database, complete, threading.Event(), threading.Event())
            self._operations[request.request_id] = operation
            future = self._submit_worker(self._export_selection_page, self._database, self._session_revision_key,
                                         value, value.generation, dict(value.entries), query, kind, offset, limit,
                                         bulk_action, operation.cancelled)
            operation.future = future
            future.add_done_callback(lambda finished: self._finish_backup_operation(request.request_id, finished))

    @classmethod
    def _export_selection_page(cls, database, revision_key, value, generation, entries,
                               query, kind, offset, limit, bulk_action, cancelled):
        rows = []
        loaded_kinds = {"PASSWORD", "NOTE"} if kind == "ALL" else {kind}
        for current_kind in ("PASSWORD", "NOTE"):
            if current_kind not in loaded_kinds:
                continue
            records = (cls._load_vault_records(database, revision_key, cancelled, detail_record_id=0)
                       if current_kind == "PASSWORD" else cls._load_note_records(database, revision_key, cancelled))
            if isinstance(records, str):
                return _BackupWorkerResult(records)
            for item in records:
                if cancelled.is_set():
                    return _BackupWorkerResult("CANCELLED")
                if current_kind == "PASSWORD":
                    title, detail, record_id = item.platform, item.account, item.record_id
                    matches = not query.strip() or field_matches_query(title, query.strip().casefold()) or field_matches_query(detail, query.strip().casefold())
                    summary_title, summary_detail = field_preview("PLATFORM", title), field_preview("ACCOUNT", detail)
                else:
                    title, detail, record_id = item.title, item.content, item.note_id
                    matches = not query.strip() or field_matches_query(title, query.strip().casefold()) or query.strip().casefold() in detail.casefold()
                    summary_title, summary_detail = field_preview("NOTE_TITLE", title), detail[:160]
                rows.append({"kind": current_kind, "id": record_id, "revision": item.revision,
                             "title": summary_title, "detail": summary_detail, "matches": matches})
            records.clear()
        if len(rows) > 100_000:
            return _BackupWorkerResult("REQUEST_TOO_LARGE")
        current = {(item["kind"], item["id"]): item["revision"] for item in rows}
        changed = [key for key, revision in entries.items() if key[0] in loaded_kinds and current.get(key) != revision]
        for key in changed:
            entries.pop(key)
        filtered = [item for item in rows if item.pop("matches")]
        filtered.sort(key=lambda item: (item["kind"] == "NOTE", item["id"]))
        if bulk_action == "ALL":
            entries.update(((item["kind"], item["id"]), item["revision"]) for item in filtered)
        elif bulk_action == "REMOVE_FILTERED":
            for item in filtered:
                entries.pop((item["kind"], item["id"]), None)
        if len(entries) > 100_000:
            return _BackupWorkerResult("REQUEST_TOO_LARGE")
        offset = min(offset, max(0, (len(filtered) - 1) // limit * limit))
        page = {"query": query, "kind": kind, "offset": offset, "limit": limit, "total": len(filtered),
                "filteredSelectedCount": sum((item["kind"], item["id"]) in entries for item in filtered),
                "items": filtered[offset:offset + limit], "changedCount": min(100_000, value.changed_count + len(changed))}
        if cancelled.is_set():
            return _BackupWorkerResult("CANCELLED")
        return _BackupWorkerResult("OK", selection_update=(value, generation, entries, page))

    @classmethod
    def _export_record_revision(cls, revision_key, kind, row):
        if kind == "NOTE":
            item = cls._note_from_row(revision_key, row)
            if item is None:
                raise BackupRejected("DATABASE_IO_FAILED")
            return item.revision
        return cls._record_revision(revision_key, {
            "record_id": row["id"], "platform": row["platform"], "account": row["account"],
            "password": row["password"], "notes": row["notes"], "totp_secret": row["totp_secret"],
            "recovery_codes": row["recovery_codes"], "favorite": bool(row["is_favorite"]),
            "password_changed_at": cls._timestamp_value(row.get("password_changed_at")),
            "updated_at": cls._timestamp_value(row.get("updated_at")),
        })

    def _backup_operation_error_locked(self, request: AdapterRequest) -> str | None:
        error = self._session_read_error_locked(request)
        if error:
            return error
        scan = self._health_rescan
        if (scan.full_active if isinstance(scan, SessionStrengthQueue)
                else scan is not None and not scan.settled.is_set()):
            return "REQUEST_BUSY"
        return None

    def _authorize_backup_commit(self, operation: _BackupOperation) -> str | None:
        with self._lock:
            if (
                self._operations.get(operation.request_id) is not operation
                or self._closed
                or operation.cancelled.is_set()
                or operation.page_epoch not in self._valid_pages
                or operation.session_epoch != self._session_epoch
                or operation.database is not self._database
            ):
                return "CANCELLED"
            if (
                operation.selection is not None
                and operation.selection.expires_at <= self._clock()
            ):
                return "SELECTION_EXPIRED"
            if operation.selection is not None and operation.selection.kind == "DESTINATION":
                destination_error = self._backup_destination_error_locked(operation.selection)
                if destination_error:
                    return destination_error
            operation.commit_started = True
            return None

    @staticmethod
    def _export_backup(
        database: DatabaseService,
        selection: BackupSelection,
        scope: str,
        password: str,
        cancelled: threading.Event,
        authorize: Callable[[], str | None],
        export_selection=None,
        revision_key=None,
    ) -> _BackupWorkerResult:
        if cancelled.is_set():
            return _BackupWorkerResult("CANCELLED")
        payload = database.export_backup_snapshot(scope, selection=export_selection,
            revision_for_row=lambda kind, row: ApplicationAdapter._export_record_revision(revision_key, kind, row),
            should_cancel=cancelled.is_set)
        if not payload:
            return _BackupWorkerResult(ApplicationAdapter._database_core_error(database))
        if cancelled.is_set():
            return _BackupWorkerResult("CANCELLED")
        try:
            envelope = encrypt_backup_v2(payload, password)
            publish_envelope(selection, envelope, authorize)
        except BackupRejected as exc:
            return _BackupWorkerResult(str(exc))
        except BackupError:
            return _BackupWorkerResult("DATABASE_IO_FAILED")
        finally:
            password = ""
        return _BackupWorkerResult(
            "OK",
            {
                "backupLabel": selection.path.name,
                "passwordCount": len(payload["passwords"]),
                "noteCount": len(payload["notes"]),
            },
        )

    @staticmethod
    def _transfer_snapshot_worker(database: DatabaseService, revision_key: bytes, scope: str,
                                  encoded: bytes | None, password_count: int, note_count: int,
                                  receiving: bool, cancelled: threading.Event, selection=None) -> _BackupWorkerResult:
        def guard() -> None:
            if cancelled.is_set():
                raise BackupRejected("CANCELLED")

        try:
            guard()
            if receiving:
                payload = parse_received_payload(encoded, scope, password_count, note_count)
                guard()
                return ApplicationAdapter._preview_payload(database, None, revision_key, payload,
                                                             hashlib.sha256(encoded).hexdigest(), cancelled)
            payload = database.export_backup_snapshot(scope, selection=selection,
                revision_for_row=lambda kind, row: ApplicationAdapter._export_record_revision(revision_key, kind, row),
                should_cancel=cancelled.is_set)
            if not payload:
                return _BackupWorkerResult(ApplicationAdapter._database_core_error(database))
            try:
                encoded = encode_transfer_payload(payload, guard)
                return _BackupWorkerResult("OK", {"rawPayload": encoded, "scope": scope,
                    "passwordCount": len(payload["passwords"]), "noteCount": len(payload["notes"])})
            finally:
                payload.clear()
        except BackupRejected as exc:
            return _BackupWorkerResult(str(exc))
        except BackupError as exc:
            return _BackupWorkerResult("BACKUP_LIMIT_EXCEEDED" if exc.kind == "size" else "BACKUP_INVALID")

    @staticmethod
    def _preview_backup(
        database: DatabaseService,
        selection: BackupSelection,
        revision_key: bytes,
        password: object,
        cancelled: threading.Event,
    ) -> _BackupWorkerResult:
        if type(password) is not str:
            return _BackupWorkerResult("INVALID_ARGUMENT")
        try:
            envelope, digest = read_backup_file(selection)
            if cancelled.is_set():
                return _BackupWorkerResult("CANCELLED")
            payload = decrypt_backup_v2(envelope, password)
        except BackupRejected as exc:
            return _BackupWorkerResult(str(exc))
        except BackupError as exc:
            return _BackupWorkerResult(
                "BACKUP_AUTH_FAILED"
                if exc.kind == "auth"
                else "BACKUP_LIMIT_EXCEEDED"
                if exc.kind == "size"
                else "BACKUP_INVALID"
            )
        finally:
            password = ""
        return ApplicationAdapter._preview_payload(database, selection, revision_key, payload, digest, cancelled)

    @staticmethod
    def _preview_payload(database: DatabaseService, selection: BackupSelection | None, revision_key: bytes,
                         payload: dict[str, object], digest: str, cancelled: threading.Event) -> _BackupWorkerResult:
        if cancelled.is_set():
            return _BackupWorkerResult("CANCELLED")
        rows = database.get_all_passwords()
        if database.last_error:
            return _BackupWorkerResult(ApplicationAdapter._database_core_error(database))
        if cancelled.is_set():
            return _BackupWorkerResult("CANCELLED")
        by_name = {str(row["platform"]): row for row in rows}
        notes = database.get_all_notes() if payload["notes"] else []
        if database.last_error:
            return _BackupWorkerResult(ApplicationAdapter._database_core_error(database))
        bindings = [
            [item["platform"], by_name[str(item["platform"])], item]
            for item in payload["passwords"]
            if str(item["platform"]) in by_name
        ]
        retry_source = json.dumps(
            [
                digest,
                selection.identity if selection is not None else "RECEIVED_SNAPSHOT",
                database.opened_file_identity,
                bindings,
                backup_note_groups(notes, payload["notes"]),
            ],
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        retry_identity = hashlib.blake2s(
            retry_source,
            key=revision_key,
            digest_size=16,
        ).hexdigest()
        return _BackupWorkerResult(
            "OK",
            preview_draft=BackupPreviewDraft(
                selection,
                digest,
                payload,
                tuple(dict(row) for row in rows),
                retry_identity,
                tuple(notes),
            ),
        )

    @staticmethod
    def _import_backup(
        database: DatabaseService,
        preview: BackupPreview,
        cancelled: threading.Event,
        authorize: Callable[[], str | None],
    ) -> _BackupWorkerResult:
        if cancelled.is_set():
            return _BackupWorkerResult("CANCELLED")
        if not source_matches(preview):
            return _BackupWorkerResult("SECRET_LEASE_EXPIRED")
        authorization_error = authorize()
        if authorization_error is not None:
            return _BackupWorkerResult(authorization_error)
        result = database.import_backup_payload(
            preview.payload,
            {
                value.platform: value.decision
                for value in preview.conflicts
                if value.kind == "PASSWORD" and value.current and value.status == "CONFLICT"
            },
            {
                value.platform: value.current
                for value in preview.conflicts
                if value.kind == "PASSWORD" and value.current
            },
            note_decisions={value.source_index: {
                "decision": value.decision,
                "target_id": value.current["id"] if value.decision == "OVERWRITE" else 0,
            } for value in preview.conflicts if value.kind == "NOTE" and value.status == "CONFLICT"},
            expected_note_groups=preview.note_groups,
        )
        if result is None:
            return _BackupWorkerResult(
                "SECRET_LEASE_EXPIRED"
                if database.last_error_kind == "backup_conflict_changed"
                else ApplicationAdapter._database_core_error(database)
            )
        result["changed"] = (
            int(result["imported"]) + int(result["overwritten"]) > 0
        )
        return _BackupWorkerResult("OK", result)

    def _finish_backup_operation(
        self,
        request_id: str,
        future: Future[_BackupWorkerResult],
    ) -> None:
        operation: _BackupOperation | None = None
        result = _BackupWorkerResult("INTERNAL_FAILURE")
        try:
            try:
                result = future.result()
            except Exception:
                result = _BackupWorkerResult(
                    "CANCELLED" if future.cancelled() else "INTERNAL_FAILURE"
                )
            with self._lock:
                candidate = self._operations.pop(request_id, None)
                if not isinstance(candidate, _BackupOperation):
                    self._scrub_backup_worker_result(result)
                    return
                operation = candidate
                if (operation.command_id in {CommandId.C88, CommandId.C89}
                        and operation.database is self._database and not operation.database.bound_identity_is_current()):
                    self._release_session_locked()
                stale = (
                    self._closed
                    or (operation.native_transfer or operation.command_id in {CommandId.C88, CommandId.C89}) and operation.cancelled.is_set()
                    or operation.page_epoch not in self._valid_pages
                    or operation.session_epoch != self._session_epoch
                    or operation.database is not self._database
                )
                if stale and not operation.commit_started:
                    self._scrub_backup_worker_result(result)
                    completion = AdapterCompletion(
                        operation.command_id,
                        operation.request_id,
                        operation.token,
                        "CANCELLED",
                    )
                elif result.error_code != "OK":
                    if (operation.command_id is CommandId.C51 and operation.selection is not None
                            and result.error_code == "REVISION_CONFLICT" and not operation.commit_started):
                        self._backup.restore_export_destination(operation.selection)
                    if (
                        operation.command_id is CommandId.C53
                        and operation.selection is not None
                        and result.error_code in {
                            "SELECTION_EXPIRED",
                            "BACKUP_INVALID",
                            "BACKUP_LIMIT_EXCEEDED",
                        }
                    ):
                        self._backup.discard_selection(
                            operation.selection.ticket
                        )
                    self._scrub_backup_worker_result(result)
                    completion = AdapterCompletion(
                        operation.command_id,
                        operation.request_id,
                        operation.token,
                        result.error_code,
                    )
                elif operation.command_id in {CommandId.C88, CommandId.C89}:
                    try:
                        value, generation, entries, page = result.selection_update
                        current = self._backup.export_selection(value.ticket, operation.page_epoch, operation.session_epoch, draft=True)
                        if current is not value or generation != value.generation:
                            raise BackupRejected("CANCELLED")
                        value.entries = entries
                        value.generation += 1
                        value.query, value.kind, value.offset, value.limit = page["query"], page["kind"], page["offset"], page["limit"]
                        value.total, value.items, value.changed_count = page["total"], page["items"], page["changedCount"]
                        value.filtered_selected_count = page["filteredSelectedCount"]
                        completion = AdapterCompletion(operation.command_id, operation.request_id, operation.token, "OK", result=value.page())
                        result.selection_update = None
                    except BackupRejected as exc:
                        self._scrub_backup_worker_result(result)
                        completion = AdapterCompletion(operation.command_id, operation.request_id, operation.token, str(exc))
                elif operation.command_id is CommandId.C53:
                    try:
                        preview_result = (
                            self._backup.install_received_preview(result.preview_draft, operation.page_epoch, operation.session_epoch)
                            if operation.native_transfer else self._backup.install_preview(result.preview_draft)
                        )
                    except BackupRejected as exc:
                        self._scrub_backup_worker_result(result)
                        completion = AdapterCompletion(
                            operation.command_id,
                            operation.request_id,
                            operation.token,
                            str(exc),
                        )
                    else:
                        completion = AdapterCompletion(
                            operation.command_id,
                            operation.request_id,
                            operation.token,
                            "OK",
                            result=preview_result,
                        )
                else:
                    if operation.command_id is CommandId.C58:
                        if result.result.get("changed") is True:
                            self._revision += 1
                            if isinstance(self._health_rescan, SessionStrengthQueue):
                                self._health_rescan.wake()
                        result.result.update(
                            {
                                "vaultRevision": self._revision_value("vault"),
                                "noteRevision": self._revision_value("notes"),
                                "healthRevision": self._revision_value("health"),
                            }
                        )
                    completion = AdapterCompletion(
                        operation.command_id,
                        operation.request_id,
                        operation.token,
                        "OK",
                        result=result.result,
                    )
                if operation.preview is not None:
                    self._backup.finish_import(
                        operation.preview,
                        success=completion.error_code == "OK",
                        retryable=(
                            completion.error_code == "DATABASE_IO_FAILED"
                        ),
                    )
            operation.complete(completion)
        finally:
            if operation is not None:
                operation.settled.set()

    @staticmethod
    def _scrub_backup_worker_result(result: _BackupWorkerResult) -> None:
        if result.selection_update is not None:
            result.selection_update[2].clear()
            result.selection_update[3].clear()
            result.selection_update = None
        draft = result.preview_draft
        if draft is not None:
            draft.payload.clear()
            for row in draft.current_records:
                row.clear()
            for row in draft.current_notes:
                row.clear()
            result.preview_draft = None
        if result.result is not None:
            result.result.clear()

    @classmethod
    def _change_database_password_after_health_rescan(
        cls, scan: HealthRescan | None, *arguments,
    ) -> _ChangeKeyWorkerResult:
        if scan is not None:
            scan.wait()
        return cls._change_database_password(*arguments)

    @staticmethod
    def _change_database_password(
        database: DatabaseService,
        current_password: str,
        new_password: str,
        should_cancel: Callable[[], bool],
        authorize_commit: Callable[[], bool],
        progress: Callable[[str, int, int], None],
    ) -> _ChangeKeyWorkerResult:
        try:
            current_status = database.verify_current_password_status(
                current_password
            )
            current_password = ""
            if should_cancel():
                new_password = ""
                return _ChangeKeyWorkerResult(
                    current_password_status=current_status,
                    cancelled=True,
                )
            if current_status is not CurrentPasswordStatus.MATCH:
                new_password = ""
                return _ChangeKeyWorkerResult(
                    current_password_status=current_status,
                )
            result = database.change_key_atomic(
                new_password,
                should_cancel=should_cancel,
                authorize_commit=authorize_commit,
                progress=progress,
            )
            new_password = ""
            return _ChangeKeyWorkerResult(
                current_password_status=current_status,
                change_result=result,
            )
        finally:
            current_password = ""
            new_password = ""

    def _authorize_change_key_commit(
        self,
        operation: _ChangeKeyOperation,
    ) -> bool:
        with self._lock:
            if (
                self._operations.get(operation.request_id) is not operation
                or self._closed
                or operation.page_epoch not in self._valid_pages
                or operation.session_epoch != self._session_epoch
                or operation.database is not self._database
                or operation.cancelled.is_set()
            ):
                return False
            operation.commit_started = True
            operation.irreversible = True
            return True

    def _record_change_key_progress(
        self,
        operation: _ChangeKeyOperation,
        phase: str,
        completed: int,
        total: int,
    ) -> None:
        if (
            phase not in _CHANGE_KEY_PROGRESS_PHASES
            or type(completed) is not int
            or type(total) is not int
            or completed < 0
            or total < 0
            or (total > 0 and completed > total)
        ):
            return
        sink: _ChangeKeyProgressSink | None = None
        with self._lock:
            if self._operations.get(operation.request_id) is not operation:
                return
            if operation.progress is None:
                operation.progress = []
            item = (phase, completed, total)
            if not operation.progress or operation.progress[-1] != item:
                operation.progress.append(item)
                if (
                    len(operation.progress)
                    > _MAX_CHANGE_KEY_PROGRESS_RECORDS
                ):
                    operation.progress = operation.progress[
                        -_MAX_CHANGE_KEY_PROGRESS_RECORDS:
                    ]
            sink = self._change_key_progress_sink
        if sink is None:
            return
        try:
            sink(
                operation.request_id,
                operation.page_epoch,
                operation.session_epoch,
                phase,
                completed,
                total,
            )
        except Exception:
            # Progress presentation is optional and cannot influence the
            # atomic database operation or expose backend exception text.
            pass

    def _finish_change_key(
        self,
        request_id: str,
        future: Future[_ChangeKeyWorkerResult],
    ) -> None:
        operation: _ChangeKeyOperation | None = None
        worker_result: _ChangeKeyWorkerResult | None = None
        future_failed = False
        try:
            try:
                worker_result = future.result()
            except Exception:
                future_failed = True
            with self._lock:
                candidate = self._operations.pop(request_id, None)
                if not isinstance(candidate, _ChangeKeyOperation):
                    return
                operation = candidate
                self._last_change_key_progress = tuple(
                    operation.progress or ()
                )
                recovery_failed_terminal = (
                    worker_result is not None
                    and worker_result.current_password_status
                    is CurrentPasswordStatus.MATCH
                    and worker_result.change_result is not None
                    and worker_result.change_result.status
                    is ChangeKeyStatus.RECOVERY_FAILED
                )
                session_invalidated = (
                    operation.database is self._database
                    and not recovery_failed_terminal
                    and not operation.database.bound_identity_is_current()
                )
                if session_invalidated:
                    # Worker 已经结算，此时可以安全销毁宿主会话。不能把
                    # 核心已失效的文件身份继续呈现为 renderer 解锁态。
                    self._release_session_locked()

                if session_invalidated:
                    completion = self._change_key_error(
                        operation,
                        "STALE_SESSION",
                    )
                elif future_failed:
                    if (
                        not operation.irreversible
                        and not operation.commit_started
                        and (
                            future.cancelled()
                            or operation.cancelled.is_set()
                        )
                    ):
                        completion = self._change_key_error(
                            operation,
                            "CANCELLED",
                        )
                    else:
                        completion = (
                            self._finish_change_key_failure_locked(
                                operation,
                                after_commit=(
                                    operation.irreversible
                                    or operation.commit_started
                                ),
                            )
                        )
                elif worker_result is None:
                    completion = self._finish_change_key_failure_locked(
                        operation,
                        after_commit=(
                            operation.irreversible
                            or operation.commit_started
                        ),
                    )
                elif worker_result.cancelled:
                    completion = self._finish_change_key_cancelled_locked(
                        operation
                    )
                elif (
                    worker_result.current_password_status
                    is CurrentPasswordStatus.MISMATCH
                ):
                    completion = self._change_key_error(
                        operation,
                        "AUTH_FAILED",
                        retry_after_ms=self._failure_retry_ms,
                    )
                elif (
                    worker_result.current_password_status
                    is CurrentPasswordStatus.ERROR
                ):
                    completion = self._change_key_error(
                        operation,
                        "CHANGE_KEY_FAILED_UNCHANGED",
                        retry_after_ms=self._failure_retry_ms,
                    )
                elif (
                    worker_result.current_password_status
                    is not CurrentPasswordStatus.MATCH
                ):
                    completion = self._finish_change_key_failure_locked(
                        operation,
                        after_commit=False,
                    )
                else:
                    completion = self._map_change_key_result_locked(
                        operation,
                        worker_result.change_result,
                    )
                self._record_change_key_settlement(
                    operation.token,
                    self._classify_change_key_settlement(
                        completion,
                        operation,
                    ),
                    replace=True,
                )
                if isinstance(self._health_rescan, SessionStrengthQueue):
                    self._health_rescan.resume()
            operation.complete(completion)
        finally:
            worker_result = None
            if operation is not None:
                operation.settled.set()

    def _map_change_key_result_locked(
        self,
        operation: _ChangeKeyOperation,
        result: ChangeKeyResult | None,
    ) -> AdapterCompletion:
        if result is None or not isinstance(result, ChangeKeyResult):
            return self._finish_change_key_failure_locked(
                operation,
                after_commit=(
                    operation.irreversible or operation.commit_started
                ),
            )
        status = result.status
        if status is ChangeKeyStatus.SUCCESS:
            self._change_key_recovery_snapshot_path = None
            self._release_session_locked()
            return self._change_key_success(operation)
        if status is ChangeKeyStatus.UNCHANGED:
            return self._change_key_error(
                operation,
                "CHANGE_KEY_FAILED_UNCHANGED",
                retry_after_ms=self._failure_retry_ms,
            )
        if status is ChangeKeyStatus.RESTORED:
            self._change_key_recovery_snapshot_path = None
            self._release_session_locked()
            return self._change_key_error(
                operation,
                "CHANGE_KEY_FAILED_RESTORED",
            )
        if status is ChangeKeyStatus.RECOVERY_FAILED:
            recovery_snapshot_retained = (
                self._remember_change_key_recovery_path_locked(
                    operation,
                    result.recovery_snapshot_path,
                )
            )
            self._release_session_locked()
            if not recovery_snapshot_retained:
                return self._change_key_error(
                    operation,
                    "INTERNAL_FAILURE",
                )
            return self._change_key_error(
                operation,
                "CHANGE_KEY_RECOVERY_FAILED",
            )
        if status is ChangeKeyStatus.CANCELLED:
            return self._finish_change_key_cancelled_locked(operation)
        return self._finish_change_key_failure_locked(
            operation,
            after_commit=(
                operation.irreversible or operation.commit_started
            ),
        )

    def _finish_change_key_cancelled_locked(
        self,
        operation: _ChangeKeyOperation,
    ) -> AdapterCompletion:
        if operation.irreversible or operation.commit_started:
            self._release_session_locked()
            return self._change_key_error(
                operation,
                "INTERNAL_FAILURE",
            )
        return self._change_key_error(operation, "CANCELLED")

    def _finish_change_key_failure_locked(
        self,
        operation: _ChangeKeyOperation,
        *,
        after_commit: bool,
    ) -> AdapterCompletion:
        if after_commit:
            self._release_session_locked()
            return self._change_key_error(
                operation,
                "INTERNAL_FAILURE",
            )
        return self._change_key_error(
            operation,
            "CHANGE_KEY_FAILED_UNCHANGED",
            retry_after_ms=self._failure_retry_ms,
        )

    def _remember_change_key_recovery_path_locked(
        self,
        operation: _ChangeKeyOperation,
        value: object,
    ) -> bool:
        if not isinstance(value, (str, Path)):
            return False
        database_value = self._database_path
        if not isinstance(database_value, Path):
            return False
        try:
            resolved = Path(value).resolve(strict=True)
            database_resolved = database_value.resolve(strict=True)
        except (OSError, RuntimeError, ValueError):
            return False
        if resolved == database_resolved:
            return False
        resolved_identity = self._file_identity(resolved)
        database_identity = self._file_identity(database_resolved)
        if (
            resolved.parent != database_resolved.parent
            or resolved_identity is None
            or database_identity is None
            or self._same_file_object(
                database_identity,
                resolved_identity,
            )
            or not self._isolation.allows_recovery_snapshot(resolved)
        ):
            return False
        operation.recovery_snapshot_path = str(resolved)
        self._change_key_recovery_snapshot_path = str(resolved)
        return True

    @staticmethod
    def _change_key_success(
        operation: _ChangeKeyOperation,
    ) -> AdapterCompletion:
        return AdapterCompletion(
            command_id=CommandId.C49,
            request_id=operation.request_id,
            token=operation.token,
            error_code="OK",
            result={"sessionEpoch": 0, "state": "LOCKED"},
        )

    @staticmethod
    def _change_key_error(
        operation: _ChangeKeyOperation,
        error_code: str,
        *,
        retry_after_ms: int = 0,
    ) -> AdapterCompletion:
        return AdapterCompletion(
            command_id=CommandId.C49,
            request_id=operation.request_id,
            token=operation.token,
            error_code=error_code,
            retry_after_ms=retry_after_ms,
        )

    def _session_read_error_locked(
        self,
        request: AdapterRequest,
        *,
        allow_pending_work: bool = False,
    ) -> str | None:
        if self._closed or request.page_epoch not in self._valid_pages:
            return "STALE_PAGE"
        if self._database is None or self._session_epoch == 0:
            return "SESSION_REQUIRED"
        if request.session_epoch != self._session_epoch:
            return "STALE_SESSION"
        if any(
            isinstance(operation, (_ChangeKeyOperation, _BackupOperation))
            or (
                not allow_pending_work
                and (
                    isinstance(operation, _SessionReadOperation)
                    or (
                        isinstance(operation, _PageSecretOperation)
                        and operation.command_id is not CommandId.C34
                    )
                )
            )
            for operation in self._operations.values()
        ):
            return "REQUEST_BUSY"
        if not self._database.bound_identity_is_current():
            self._release_session_locked()
            return "STALE_SESSION"
        return None

    def _has_non_strength_operation_locked(self) -> bool:
        return any(
            not (
                isinstance(operation, _PageSecretOperation)
                and operation.command_id is CommandId.C34
            )
            for operation in self._operations.values()
        )

    def _native_session_error_locked(
        self,
        request: AdapterRequest,
        *,
        allow_pending_work: bool = False,
    ) -> str | None:
        if self._closed:
            return "STALE_SESSION"
        if self._database is None or self._session_epoch == 0:
            return "SESSION_REQUIRED"
        if request.session_epoch != self._session_epoch:
            return "STALE_SESSION"
        if any(
            isinstance(operation, (_ChangeKeyOperation, _BackupOperation))
            or (
                not allow_pending_work
                and isinstance(operation, (_SessionReadOperation, _PageSecretOperation))
            )
            for operation in self._operations.values()
        ):
            return "REQUEST_BUSY"
        if not self._database.bound_identity_is_current():
            self._release_session_locked()
            return "STALE_SESSION"
        return None

    @classmethod
    def _list_vault(
        cls,
        database: DatabaseService,
        revision_key: bytes,
        query: str,
        vault_filter: str,
        sort_mode: str,
        cursor: str,
        limit: int,
        cancelled: threading.Event,
    ) -> _SessionReadResult:
        loaded = cls._load_vault_records(
            database,
            revision_key,
            cancelled,
            detail_record_id=0,
        )
        if isinstance(loaded, str):
            return _SessionReadResult(loaded)
        if cancelled.is_set():
            return _SessionReadResult("CANCELLED")
        records = loaded
        if len(records) > 100_000:
            return _SessionReadResult("REQUEST_TOO_LARGE")

        return cls._vault_page(
            records,
            revision_key,
            query,
            vault_filter,
            sort_mode,
            cursor,
            limit,
        )

    @classmethod
    def _vault_view(
        cls,
        records: list[_VaultRecord],
        query: str,
        vault_filter: str,
        sort_mode: str,
    ) -> tuple[list[_VaultRecord], dict[str, int]]:
        counts = {
            "all": len(records),
            "favorite": sum(item.favorite for item in records),
            "weak": sum(item.strength == "WEAK" for item in records),
            "duplicate": sum(item.duplicate_group > 0 for item in records),
            "similar": sum(item.similar_group > 0 for item in records),
        }
        folded_query = query.strip().casefold()
        filtered = [
            item
            for item in records
            if (
                not folded_query
                or field_matches_query(item.platform, folded_query)
                or field_matches_query(item.account, folded_query)
            )
        ]
        if vault_filter == "FAVORITE":
            filtered = [item for item in filtered if item.favorite]
        elif vault_filter == "WEAK":
            filtered = [item for item in filtered if item.strength == "WEAK"]
        elif vault_filter == "DUPLICATE":
            filtered = [item for item in filtered if item.duplicate_group > 0]
        elif vault_filter == "SIMILAR":
            filtered = [item for item in filtered if item.similar_group > 0]

        strength_order = {"WEAK": 0, "FAIR": 1, "STRONG": 2,
                          "PENDING": 3, "CHECKING": 3, "FAILED": 3}
        favorite_order = (
            (lambda item: 0 if item.favorite else 1)
            if vault_filter == "ALL"
            else (lambda _item: 0)
        )
        if sort_mode == "NAME":
            filtered.sort(
                key=lambda item: (
                    item.platform.casefold(),
                    favorite_order(item),
                    item.account.casefold(),
                    item.record_id,
                )
            )
        elif sort_mode == "STRENGTH":
            filtered.sort(
                key=lambda item: (
                    strength_order[item.strength],
                    0 if item.strength in _PENDING_STRENGTHS else favorite_order(item),
                    "" if item.strength in _PENDING_STRENGTHS else item.platform.casefold(),
                    item.record_id,
                )
            )
        else:
            filtered.sort(
                key=lambda item: (
                    -cls._timestamp_ordinal(item.updated_at),
                    favorite_order(item),
                    -item.record_id,
                )
            )
        return filtered, counts

    @classmethod
    def _vault_page(
        cls,
        records: list[_VaultRecord],
        revision_key: bytes,
        query: str,
        vault_filter: str,
        sort_mode: str,
        cursor: str,
        limit: int,
    ) -> _SessionReadResult:
        filtered, counts = cls._vault_view(
            records,
            query,
            vault_filter,
            sort_mode,
        )
        vault_revision = cls._vault_revision(revision_key, records)
        cursor_scope = json.dumps(
            [vault_revision, query, vault_filter, sort_mode],
            ensure_ascii=False,
            separators=(",", ":"),
        )
        offset = cls._decode_cursor(
            cursor,
            revision_key,
            cursor_scope,
            len(filtered),
        )
        if offset is None:
            return _SessionReadResult("INVALID_ARGUMENT")
        page = filtered[offset:offset + limit]
        next_offset = offset + len(page)
        return _SessionReadResult(
            "OK",
            {
                "items": [cls._vault_summary(item) for item in page],
                "total": len(filtered),
                "nextCursor": (
                    cls._encode_cursor(next_offset, revision_key, cursor_scope)
                    if next_offset < len(filtered)
                    else ""
                ),
                "counts": counts,
                "vaultRevision": vault_revision,
            },
        )

    @classmethod
    def _locate_vault_anchor(cls, database, revision_key, record_id, query, vault_filter, sort_mode, cancelled):
        """评级刷新只按ID定位当前查询范围，不授予编辑或秘密访问权限。"""
        return cls._locate_vault_record(database, revision_key, record_id, None, sort_mode,
                                       cancelled, query=query, vault_filter=vault_filter)

    @classmethod
    def _locate_vault_record(
        cls,
        database: DatabaseService,
        revision_key: bytes,
        record_id: int,
        revision: str | None,
        sort_mode: str,
        cancelled: threading.Event,
        *,
        query: str = "",
        vault_filter: str = "ALL",
    ) -> _SessionReadResult:
        limit = 100
        loaded = cls._load_vault_records(
            database,
            revision_key,
            cancelled,
            detail_record_id=0,
        )
        if isinstance(loaded, str):
            return _SessionReadResult(loaded)
        if cancelled.is_set():
            return _SessionReadResult("CANCELLED")
        target = next(
            (item for item in loaded if item.record_id == record_id),
            None,
        )
        if target is None:
            return _SessionReadResult("NOT_FOUND")
        if revision is not None and not hmac.compare_digest(target.revision, revision):
            return _SessionReadResult("REVISION_CONFLICT")
        filtered, _counts = cls._vault_view(loaded, query, vault_filter, sort_mode)
        if not any(item.record_id == record_id for item in filtered):
            return _SessionReadResult("NOT_FOUND")
        offset = next(
            index
            for index, item in enumerate(filtered)
            if item.record_id == record_id
        )
        page_offset = (offset // limit) * limit
        vault_revision = cls._vault_revision(revision_key, loaded)
        scope = json.dumps(
            [vault_revision, query, vault_filter, sort_mode],
            ensure_ascii=False,
            separators=(",", ":"),
        )
        cursor = (
            ""
            if page_offset == 0
            else cls._encode_cursor(page_offset, revision_key, scope)
        )
        page = cls._vault_page(
            loaded,
            revision_key,
            query,
            vault_filter,
            sort_mode,
            cursor,
            limit,
        )
        if page.error_code != "OK" or page.result is None:
            return _SessionReadResult("INTERNAL_FAILURE")
        return _SessionReadResult(
            "OK",
            {
                "page": page.result,
                "cursor": cursor,
                "cursorHistory": [
                    ""
                    if start == 0
                    else cls._encode_cursor(start, revision_key, scope)
                    for start in range(0, page_offset, limit)
                ],
            },
        )

    @classmethod
    def _health_context(
        cls,
        database: DatabaseService,
        revision_key: bytes,
        stale_days: int,
        today: datetime.date,
        cancelled: threading.Event,
    ) -> tuple[list[_VaultRecord], list[dict[str, object]], str] | str:
        records = cls._load_vault_records(
            database,
            revision_key,
            cancelled,
            # Health never displays account data, so avoid retaining previews.
            detail_record_id=-1,
        )
        if isinstance(records, str):
            return records
        if cancelled.is_set():
            return "CANCELLED"
        projection = [
            {
                "id": item.record_id,
                "strength": item.strength.lower(),
                "duplicate_group": item.duplicate_group,
                "password_changed_at": item.health_password_changed_at,
            }
            for item in records
        ]
        return records, projection, cls._health_revision(
            revision_key,
            records,
            stale_days,
            today,
        )

    @classmethod
    def _health_summary(
        cls,
        database: DatabaseService,
        revision_key: bytes,
        stale_days: int,
        cancelled: threading.Event,
    ) -> _SessionReadResult:
        today = datetime.date.today()
        context = cls._health_context(
            database,
            revision_key,
            stale_days,
            today,
            cancelled,
        )
        if isinstance(context, str):
            return _SessionReadResult(context)
        records, projection, health_revision = context
        return cls._health_overview(
            records,
            projection,
            revision_key,
            stale_days,
            today,
            health_revision,
        )

    @classmethod
    def _health_overview_at(
        cls,
        database: DatabaseService,
        revision_key: bytes,
        stale_days: int,
        kind: str,
        page_index: int,
        cancelled: threading.Event,
    ) -> _SessionReadResult:
        if kind not in {"WEAK", "DUPLICATE", "STALE"}:
            return _SessionReadResult("INVALID_ARGUMENT", error_argument_index=4)
        today = datetime.date.today()
        context = cls._health_context(
            database,
            revision_key,
            stale_days,
            today,
            cancelled,
        )
        if isinstance(context, str):
            return _SessionReadResult(context)
        records, projection, health_revision = context
        return cls._health_overview(
            records,
            projection,
            revision_key,
            stale_days,
            today,
            health_revision,
            selected_kind=kind,
            selected_page_index=page_index,
        )

    @classmethod
    def _health_overview(
        cls,
        records: list[_VaultRecord],
        projection: list[dict[str, object]],
        revision_key: bytes,
        stale_days: int,
        today: datetime.date,
        health_revision: str,
        *,
        selected_kind: str = "",
        selected_page_index: int = 0,
    ) -> _SessionReadResult:
        score = HealthTool.calc_health_score(
            projection,
            stale_days,
            today=today,
        )
        pending = sum(item.strength in _PENDING_STRENGTHS for item in records)
        failed = sum(item.strength == "FAILED" for item in records)
        pages: dict[str, dict[str, object]] = {}
        for kind in ("WEAK", "DUPLICATE", "STALE"):
            index = selected_page_index if kind == selected_kind else 0
            page = cls._health_issue_page_at(
                records,
                projection,
                revision_key,
                stale_days,
                today,
                health_revision,
                kind,
                index,
            )
            if page.error_code != "OK" or page.result is None:
                return _SessionReadResult("INTERNAL_FAILURE")
            pages[kind] = page.result
        return _SessionReadResult(
            "OK",
            {
                "hasRecords": bool(records),
                "score": 0 if pending else score.score or 0,
                "scoreAvailable": bool(records) and pending == 0,
                "pendingCount": pending,
                "failedCount": failed,
                "grade": "EMPTY" if score.grade == "none" else score.grade.upper(),
                "weakCount": score.weak_count,
                "duplicateGroupCount": score.dup_group_count,
                "staleCount": score.stale_count,
                "healthRevision": health_revision,
                "weakPage": pages["WEAK"],
                "duplicatePage": pages["DUPLICATE"],
                "stalePage": pages["STALE"],
            },
        )

    @classmethod
    def _health_issue_page_at(
        cls,
        records: list[_VaultRecord],
        projection: list[dict[str, object]],
        revision_key: bytes,
        stale_days: int,
        today: datetime.date,
        health_revision: str,
        kind: str,
        page_index: int,
    ) -> _SessionReadResult:
        if type(page_index) is not int or page_index < 0:
            return _SessionReadResult("INVALID_ARGUMENT")
        count = cls._health_issue_count(
            records,
            projection,
            stale_days,
            today,
            kind,
        )
        maximum = max(0, (count - 1) // 20)
        offset = min(page_index, maximum) * 20
        scope = json.dumps([health_revision, kind, 20], separators=(",", ":"))
        cursor = (
            "" if offset == 0
            else cls._encode_cursor(offset, revision_key, scope)
        )
        return cls._health_issue_page(
            records,
            projection,
            revision_key,
            stale_days,
            today,
            health_revision,
            kind,
            cursor,
            20,
        )

    @classmethod
    def _health_guidance_page(
        cls,
        database: DatabaseService,
        revision_key: bytes,
        stale_days: int,
        snapshot: _HealthGuidanceSnapshot | None,
        page_epoch: int,
        session_epoch: int,
        cursor: str,
        cancelled: threading.Event,
    ) -> _SessionReadResult:
        records = cls._load_vault_records(
            database,
            revision_key,
            cancelled,
            detail_record_id=-1,
        )
        if isinstance(records, str):
            return _SessionReadResult(records)
        if cancelled.is_set():
            return _SessionReadResult("CANCELLED")
        today = datetime.date.today()
        if snapshot is None:
            projection = [
                {
                    "id": item.record_id,
                    "strength": item.strength.lower(),
                    "duplicate_group": item.duplicate_group,
                    "password_changed_at": item.health_password_changed_at,
                }
                for item in records
            ]
            issues = HealthTool.collect_security_issues(
                projection,
                stale_days,
                today=today,
            )
            snapshot = _HealthGuidanceSnapshot(
                guidance_id=secrets.token_urlsafe(24),
                page_epoch=page_epoch,
                session_epoch=session_epoch,
                entries=tuple(
                    (issue.id, tuple(value.upper() for value in issue.types))
                    for issue in issues
                ),
            )
            draft = snapshot
        else:
            draft = None
        scope = f"guidance:{snapshot.guidance_id}:100"
        offset = cls._decode_cursor(
            cursor,
            revision_key,
            scope,
            len(snapshot.entries),
        )
        if offset is None:
            return _SessionReadResult("INVALID_ARGUMENT")
        current = {item.record_id: item for item in records}
        page = snapshot.entries[offset:offset + 100]
        next_offset = offset + len(page)
        items: list[dict[str, object]] = []
        for record_id, issue_types in page:
            record = current.get(record_id)
            if record is None:
                items.append(
                    {
                        "issueId": cls._health_issue_id(
                            revision_key,
                            snapshot.guidance_id,
                            f"guidance:{record_id}",
                        ),
                        "recordId": record_id,
                        "available": False,
                        "recordRevision": "",
                        "platform": "",
                        "issueTypes": list(issue_types),
                        "duplicateGroup": 0,
                        "daysSinceChange": 0,
                    }
                )
                continue
            items.append(
                {
                    "issueId": cls._health_issue_id(
                        revision_key,
                        snapshot.guidance_id,
                        f"guidance:{record_id}",
                    ),
                    "recordId": record_id,
                    "available": True,
                    "recordRevision": record.revision,
                    "platform": field_preview("PLATFORM", record.platform),
                    "issueTypes": list(issue_types),
                    "duplicateGroup": record.duplicate_group,
                    "daysSinceChange": cls._days_since_change(
                        record.health_password_changed_at,
                        today,
                    ),
                }
            )
        return _SessionReadResult(
            "OK",
            {
                "guidanceId": snapshot.guidance_id,
                "items": items,
                "total": len(snapshot.entries),
                "pageIndex": offset // 100,
                "previousCursor": (
                    cls._encode_cursor(offset - 100, revision_key, scope)
                    if offset >= 100
                    else ""
                ),
                "nextCursor": (
                    cls._encode_cursor(next_offset, revision_key, scope)
                    if next_offset < len(snapshot.entries)
                    else ""
                ),
            },
            guidance_snapshot=draft,
        )

    @staticmethod
    def _health_issue_count(
        records: list[_VaultRecord],
        projection: list[dict[str, object]],
        stale_days: int,
        today: datetime.date,
        kind: str,
    ) -> int:
        if kind == "DUPLICATE":
            return len({item.duplicate_group for item in records if item.duplicate_group > 0})
        return sum(
            kind.lower() in issue.types
            for issue in HealthTool.collect_security_issues(
                projection,
                stale_days,
                today=today,
            )
        )

    @classmethod
    def _list_health_issues(
        cls,
        database: DatabaseService,
        revision_key: bytes,
        stale_days: int,
        kind: str,
        cursor: str,
        limit: int,
        cancelled: threading.Event,
    ) -> _SessionReadResult:
        if kind not in {"ALL", "WEAK", "DUPLICATE", "STALE"}:
            return _SessionReadResult("INVALID_ARGUMENT", error_argument_index=4)
        if type(limit) is not int or limit != 20:
            return _SessionReadResult("INVALID_ARGUMENT", error_argument_index=6)
        today = datetime.date.today()
        context = cls._health_context(
            database,
            revision_key,
            stale_days,
            today,
            cancelled,
        )
        if isinstance(context, str):
            return _SessionReadResult(context)
        records, projection, health_revision = context
        return cls._health_issue_page(
            records,
            projection,
            revision_key,
            stale_days,
            today,
            health_revision,
            kind,
            cursor,
            limit,
        )

    @classmethod
    def _health_issue_page(
        cls,
        records: list[_VaultRecord],
        projection: list[dict[str, object]],
        revision_key: bytes,
        stale_days: int,
        today: datetime.date,
        health_revision: str,
        kind: str,
        cursor: str,
        limit: int,
    ) -> _SessionReadResult:
        scope = json.dumps(
            [health_revision, kind, limit],
            separators=(",", ":"),
        )
        by_id = {item.record_id: item for item in records}
        if kind == "DUPLICATE":
            groups: dict[int, list[_VaultRecord]] = {}
            for item in records:
                if item.duplicate_group > 0:
                    groups.setdefault(item.duplicate_group, []).append(item)
            values = sorted(groups.items())
            offset = cls._decode_cursor(cursor, revision_key, scope, len(values))
            if offset is None:
                return _SessionReadResult("INVALID_ARGUMENT", error_argument_index=5)
            page = values[offset:offset + limit]
            next_offset = offset + len(page)
            return _SessionReadResult(
                "OK",
                {
                    "items": [],
                    "groups": [
                        {
                            "issueId": cls._health_issue_id(
                                revision_key,
                                health_revision,
                                f"group:{group}",
                            ),
                            "duplicateGroup": group,
                            "memberCount": len(members),
                            "members": [
                                {
                                    "recordId": item.record_id,
                                    "recordRevision": item.revision,
                                    "platform": field_preview("PLATFORM", item.platform),
                                }
                                for item in sorted(members, key=lambda item: item.record_id)[:3]
                            ],
                        }
                        for group, members in page
                    ],
                    "total": len(values),
                    "pageIndex": offset // limit,
                    "previousCursor": (
                        cls._encode_cursor(offset - limit, revision_key, scope)
                        if offset >= limit
                        else ""
                    ),
                    "nextCursor": (
                        cls._encode_cursor(next_offset, revision_key, scope)
                        if next_offset < len(values)
                        else ""
                    ),
                    "healthRevision": health_revision,
                },
            )

        issues = HealthTool.collect_security_issues(
            projection,
            stale_days,
            today=today,
        )
        if kind != "ALL":
            issues = [
                issue for issue in issues
                if kind.lower() in issue.types
            ]
        offset = cls._decode_cursor(cursor, revision_key, scope, len(issues))
        if offset is None:
            return _SessionReadResult("INVALID_ARGUMENT", error_argument_index=5)
        page = issues[offset:offset + limit]
        next_offset = offset + len(page)
        return _SessionReadResult(
            "OK",
            {
                "items": [
                    {
                        "issueId": cls._health_issue_id(
                            revision_key,
                            health_revision,
                            f"record:{issue.id}:{by_id[issue.id].revision}",
                        ),
                        "recordId": issue.id,
                        "recordRevision": by_id[issue.id].revision,
                        "platform": field_preview("PLATFORM", by_id[issue.id].platform),
                        "issueTypes": [value.upper() for value in issue.types],
                        "duplicateGroup": by_id[issue.id].duplicate_group,
                        "daysSinceChange": cls._days_since_change(
                            by_id[issue.id].health_password_changed_at,
                            today,
                        ),
                    }
                    for issue in page
                ],
                "groups": [],
                "total": len(issues),
                "pageIndex": offset // limit,
                "previousCursor": (
                    cls._encode_cursor(offset - limit, revision_key, scope)
                    if offset >= limit
                    else ""
                ),
                "nextCursor": (
                    cls._encode_cursor(next_offset, revision_key, scope)
                    if next_offset < len(issues)
                    else ""
                ),
                "healthRevision": health_revision,
            },
        )

    @staticmethod
    def _health_issue_id(
        revision_key: bytes,
        health_revision: str,
        source: str,
    ) -> str:
        return hashlib.blake2s(
            f"health:{health_revision}:{source}".encode("ascii"),
            key=revision_key,
            digest_size=16,
        ).hexdigest()

    @classmethod
    def _health_revision(
        cls,
        revision_key: bytes,
        records: list[_VaultRecord],
        stale_days: int,
        today: datetime.date,
    ) -> str:
        vault_revision = cls._vault_revision(revision_key, records)
        return hashlib.blake2s(
            f"health:{vault_revision}:{stale_days}:{today.isoformat()}".encode("ascii"),
            key=revision_key,
            digest_size=16,
        ).hexdigest()

    @staticmethod
    def _days_since_change(
        value: str | None,
        today: datetime.date,
    ) -> int:
        try:
            if value is None:
                return 0
            return max(
                0,
                (today - datetime.datetime.fromisoformat(value).date()).days,
            )
        except ValueError:
            return 0

    @classmethod
    def _record_details(
        cls,
        database: DatabaseService,
        revision_key: bytes,
        record_id: int,
        revision: str,
        cancelled: threading.Event,
    ) -> _SessionReadResult:
        if cancelled.is_set():
            return _SessionReadResult("CANCELLED")
        row = revision_source = None
        try:
            state = cls._single_record_state(database, revision_key, record_id, cancelled)
            if isinstance(state, str):
                return _SessionReadResult(state)
            row, revision_source, current_revision = state
            if not hmac.compare_digest(current_revision, revision):
                return _SessionReadResult("REVISION_CONFLICT")
            if cancelled.is_set():
                return _SessionReadResult("CANCELLED")
            return _SessionReadResult(
                "OK",
                {
                    "recordId": record_id,
                    "revision": current_revision,
                    "platform": field_preview("PLATFORM", revision_source["platform"]),
                    "account": field_preview("ACCOUNT", row["account"]),
                    "notes": field_preview("NOTES", row["notes"]),
                    "favorite": revision_source["favorite"],
                    "strength": revision_source["strength"],
                    "hasPassword": bool(row["password"]),
                    "hasTotp": bool(row["totp_secret"]),
                    "recoveryUsed": [code["used"] for code in row["recovery_codes"]],
                    "longFields": [
                        field for field, value in (
                            ("PLATFORM", revision_source["platform"]),
                            ("ACCOUNT", row["account"]),
                            ("NOTES", row["notes"]),
                        ) if field_is_long(field, value)
                    ],
                    "updatedDate": cls._date_value(revision_source["updated_at"]),
                    "passwordChangedDate": cls._date_value(revision_source["password_changed_at"]),
                },
            )
        except Exception:
            return _SessionReadResult("DATABASE_IO_FAILED")
        finally:
            if row is not None:
                cls._scrub_record_dict(row)
            if revision_source is not None:
                cls._scrub_revision_source(revision_source)

    @classmethod
    def _list_notes(
        cls,
        database: DatabaseService,
        revision_key: bytes,
        query: str,
        note_filter: str,
        cursor: str,
        limit: int,
        cancelled: threading.Event,
        *,
        sort_mode: str = "UPDATED",
    ) -> _SessionReadResult:
        loaded = cls._load_note_records(
            database,
            revision_key,
            cancelled,
        )
        if isinstance(loaded, str):
            return _SessionReadResult(loaded)
        if cancelled.is_set():
            return _SessionReadResult("CANCELLED")
        records = loaded

        folded_query = query.strip().casefold()
        filtered = [
            item
            for item in records
            if (
                not folded_query
                or field_matches_query(item.title, folded_query)
                or folded_query in item.content.casefold()
            )
        ]
        if note_filter == "FAVORITE":
            filtered = [item for item in filtered if item.favorite]
        elif note_filter != "ALL":
            return _SessionReadResult(
                "INVALID_ARGUMENT",
                error_argument_index=5,
            )

        if sort_mode == "UPDATED":
            filtered.sort(
                key=lambda item: (
                    -cls._timestamp_ordinal(item.updated_at),
                    -item.note_id,
                )
            )
        elif sort_mode == "NAME":
            from pypinyin import lazy_pinyin

            filtered.sort(
                key=lambda item: ("".join(lazy_pinyin(item.title)).casefold(), item.note_id)
            )
        else:
            return _SessionReadResult(
                "INVALID_ARGUMENT",
                error_argument_index=8,
            )

        note_revision = cls._note_revision(revision_key, records)
        cursor_scope = json.dumps(
            [note_revision, query, note_filter, sort_mode],
            ensure_ascii=False,
            separators=(",", ":"),
        )
        offset = cls._decode_cursor(
            cursor,
            revision_key,
            cursor_scope,
            len(filtered),
        )
        if offset is None:
            return _SessionReadResult(
                "INVALID_ARGUMENT",
                error_argument_index=6,
            )
        page = filtered[offset:offset + limit]
        next_offset = offset + len(page)
        next_cursor = ""
        if next_offset < len(filtered):
            next_cursor = cls._encode_cursor(
                next_offset,
                revision_key,
                cursor_scope,
            )
        return _SessionReadResult(
            "OK",
            {
                "items": [cls._note_summary(item) for item in page],
                "total": len(filtered),
                "counts": {
                    "all": len(records),
                    "favorite": sum(item.favorite for item in records),
                },
                "nextCursor": next_cursor,
                "noteRevision": note_revision,
            },
        )

    @classmethod
    def _note_details(
        cls,
        database: DatabaseService,
        revision_key: bytes,
        note_id: int,
        revision: str,
        cancelled: threading.Event,
    ) -> _SessionReadResult:
        state = cls._single_note_state(database, revision_key, note_id, cancelled)
        if isinstance(state, str):
            return _SessionReadResult(state)
        _row, note, current_revision = state
        try:
            if not hmac.compare_digest(current_revision, revision):
                return _SessionReadResult("REVISION_CONFLICT")
            return _SessionReadResult(
                "OK",
                {
                    "noteId": note.note_id,
                    "revision": current_revision,
                    "title": field_preview("NOTE_TITLE", note.title),
                    "content": field_preview("NOTE_CONTENT", note.content),
                    "favorite": note.favorite,
                    "longFields": cls._note_long_fields(note),
                    "updatedDate": cls._date_value(note.updated_at),
                },
            )
        finally:
            cls._scrub_note_dict(_row)

    @classmethod
    def _create_note(
        cls,
        database: DatabaseService,
        revision_key: bytes,
        title: str,
        content: str,
        favorite: object,
        cancelled: threading.Event,
    ) -> _SessionReadResult:
        normalized_title = title.strip()
        if not cls._bounded_text(normalized_title, 1, 256, 1024):
            return _SessionReadResult(
                "INVALID_ARGUMENT",
                error_argument_index=4,
            )
        if not cls._bounded_text(content, 0, 65_536, 262_144):
            return _SessionReadResult(
                "REQUEST_TOO_LARGE",
                error_argument_index=5,
            )
        if type(favorite) is not bool:
            return _SessionReadResult(
                "INVALID_ARGUMENT",
                error_argument_index=6,
            )
        if cancelled.is_set():
            return _SessionReadResult("INTERNAL_FAILURE")
        created = database.insert_note(
            {
                "title": normalized_title,
                "content": content,
                "is_favorite": 1 if favorite else 0,
            },
            return_record=True,
        )
        if not isinstance(created, dict):
            return _SessionReadResult(cls._note_core_error(database))
        return cls._committed_note_result(revision_key, created)

    @classmethod
    def _single_note_state(
        cls,
        database: DatabaseService,
        revision_key: bytes,
        note_id: object,
        cancelled: threading.Event,
    ) -> tuple[dict[str, object], _NoteRecord, str] | str:
        if type(note_id) is not int or note_id <= 0:
            return "INVALID_ARGUMENT"
        row = database.get_note(note_id)
        if row is None:
            return cls._note_core_error(database, missing="NOT_FOUND")
        if cancelled.is_set():
            cls._scrub_note_dict(row)
            return "CANCELLED"
        note = cls._note_from_row(revision_key, row)
        if note is None:
            cls._scrub_note_dict(row)
            return "DATABASE_IO_FAILED"
        return row, note, note.revision

    @classmethod
    def _update_note(
        cls,
        database: DatabaseService,
        revision_key: bytes,
        note_id: object,
        revision: object,
        title: object,
        content: object,
        favorite: object,
        cancelled: threading.Event,
    ) -> _SessionReadResult:
        if (
            not cls._bounded_text(
                title.strip() if type(title) is str else title,
                1,
                256,
                1024,
            )
            or not cls._bounded_text(content, 0, 65_536, 262_144)
        ):
            return _SessionReadResult("INVALID_ARGUMENT")
        return cls._update_note_fields(
            database, revision_key, note_id, revision,
            "REPLACE", title, "REPLACE", content, favorite, cancelled,
            allow_legacy_restore=False,
        )

    @classmethod
    def _update_note_fields(
        cls,
        database: DatabaseService,
        revision_key: bytes,
        note_id: object,
        revision: object,
        title_action: object,
        title: object,
        content_action: object,
        content: object,
        favorite: object,
        cancelled: threading.Event,
        *,
        allow_legacy_restore: bool = True,
    ) -> _SessionReadResult:
        row: dict[str, object] | None = None
        expected: dict[str, object] | None = None
        update: dict[str, object] = {}
        try:
            replacements: dict[str, tuple[str, int, int, int]] = {}
            for name, action, value, minimum, maximum, byte_limit in (
                ("title", title_action, title, 1, 256, 1024),
                ("content", content_action, content, 0, 65_536, 262_144),
            ):
                if type(action) is not str or action not in {"KEEP", "REPLACE"} or type(value) is not str:
                    return _SessionReadResult("INVALID_ARGUMENT")
                if action == "KEEP":
                    if value:
                        return _SessionReadResult("INVALID_ARGUMENT")
                    continue
                replacements[name] = (value, minimum, maximum, byte_limit)
            if type(revision) is not str or type(favorite) is not bool:
                return _SessionReadResult("INVALID_ARGUMENT")
            state = cls._single_note_state(database, revision_key, note_id, cancelled)
            if isinstance(state, str):
                return _SessionReadResult(state)
            row, _note, current_revision = state
            if not hmac.compare_digest(current_revision, revision):
                return _SessionReadResult("REVISION_CONFLICT")
            if cancelled.is_set():
                return _SessionReadResult("CANCELLED")
            expected = dict(row)
            for name, (value, minimum, maximum, byte_limit) in replacements.items():
                if allow_legacy_restore and value == row[name]:
                    continue
                normalized = value.strip() if name == "title" else value
                if not cls._bounded_text(normalized, minimum, maximum, byte_limit):
                    return _SessionReadResult("INVALID_ARGUMENT")
                update[name] = normalized
            update["is_favorite"] = favorite
            updated = database.update_note(int(note_id), update, expected=expected, return_record=True)
            if not isinstance(updated, dict):
                return _SessionReadResult(cls._note_core_error(database))
            return cls._committed_note_result(revision_key, updated)
        except Exception:
            return _SessionReadResult("DATABASE_IO_FAILED")
        finally:
            if row is not None:
                cls._scrub_note_dict(row)
            if expected is not None:
                cls._scrub_note_dict(expected)
            cls._scrub_note_dict(update)

    @classmethod
    def _set_note_favorite(
        cls,
        database: DatabaseService,
        revision_key: bytes,
        note_id: object,
        revision: object,
        favorite: object,
        cancelled: threading.Event,
    ) -> _SessionReadResult:
        row: dict[str, object] | None = None
        expected: dict[str, object] | None = None
        try:
            if type(revision) is not str or type(favorite) is not bool:
                return _SessionReadResult("INVALID_ARGUMENT")
            state = cls._single_note_state(database, revision_key, note_id, cancelled)
            if isinstance(state, str):
                return _SessionReadResult(state)
            row, _note, current_revision = state
            if not hmac.compare_digest(current_revision, revision):
                return _SessionReadResult("REVISION_CONFLICT")
            if cancelled.is_set():
                return _SessionReadResult("CANCELLED")
            expected = dict(row)
            updated = database.set_note_favorite(int(note_id), favorite, expected=expected, return_record=True)
            if not isinstance(updated, dict):
                return _SessionReadResult(cls._note_core_error(database))
            return cls._committed_note_result(revision_key, updated)
        except Exception:
            return _SessionReadResult("DATABASE_IO_FAILED")
        finally:
            if row is not None:
                cls._scrub_note_dict(row)
            if expected is not None:
                cls._scrub_note_dict(expected)

    @classmethod
    def _prepare_delete_note(
        cls,
        database: DatabaseService,
        revision_key: bytes,
        note_id: object,
        revision: object,
        cancelled: threading.Event,
    ) -> _SessionReadResult:
        state = cls._single_note_state(database, revision_key, note_id, cancelled)
        if isinstance(state, str):
            return _SessionReadResult(state)
        row, note, current_revision = state
        try:
            if type(revision) is not str or not hmac.compare_digest(current_revision, revision):
                return _SessionReadResult("REVISION_CONFLICT" if type(revision) is str else "INVALID_ARGUMENT")
            if cancelled.is_set():
                return _SessionReadResult("CANCELLED")
            label = field_preview("NOTE_TITLE", note.title)
            return _SessionReadResult("OK", {"entityLabel": label}, delete_ticket_draft=_DeleteTicketDraft(int(note_id), current_revision, label, "NOTE"))
        finally:
            cls._scrub_note_dict(row)

    @classmethod
    def _delete_note(
        cls,
        database: DatabaseService,
        revision_key: bytes,
        note_id: int,
        revision: str,
        cancelled: threading.Event,
    ) -> _SessionReadResult:
        state = cls._single_note_state(database, revision_key, note_id, cancelled)
        if isinstance(state, str):
            return _SessionReadResult(state)
        row, _note, current_revision = state
        expected: dict[str, object] | None = None
        try:
            if not hmac.compare_digest(current_revision, revision):
                return _SessionReadResult("REVISION_CONFLICT")
            if cancelled.is_set():
                return _SessionReadResult("CANCELLED")
            expected = dict(row)
            if not database.delete_note(note_id, expected=expected):
                return _SessionReadResult(cls._note_core_error(database))
            return _SessionReadResult("OK", {"deletedId": note_id})
        except Exception:
            return _SessionReadResult("DATABASE_IO_FAILED")
        finally:
            cls._scrub_note_dict(row)
            if expected is not None:
                cls._scrub_note_dict(expected)

    def _read_note_field_chunk(self, database: DatabaseService, key: bytes, page_epoch: int, session_epoch: int, note_id: object, revision: object, field: object, read_id: object, offset: object, cancelled: threading.Event) -> _SessionReadResult:
        state = self._single_note_state(database, key, note_id, cancelled)
        if isinstance(state, str):
            return _SessionReadResult(state)
        row, note, current_revision = state
        value = ""
        try:
            if type(revision) is not str or not hmac.compare_digest(current_revision, revision):
                return _SessionReadResult("REVISION_CONFLICT" if type(revision) is str else "INVALID_ARGUMENT")
            field_map = {"TITLE": ("NOTE_TITLE", note.title), "CONTENT": ("NOTE_CONTENT", note.content)}
            selected = field_map.get(field)
            if selected is None or type(offset) is not int:
                return _SessionReadResult("INVALID_ARGUMENT")
            internal_field, value = selected
            try:
                result = self._note_field_reads.take(page_epoch=page_epoch, session_epoch=session_epoch, record_id=int(note_id), revision=current_revision, field=internal_field, authority_lease_id="NOTE_FIELD_READ", read_id=str(read_id), offset=offset, value=value, cancelled=cancelled)
            except FieldReadRejected as exc:
                return _SessionReadResult(str(exc))
            return _SessionReadResult("OK", result)
        finally:
            value = ""
            self._scrub_note_dict(row)

    @classmethod
    def _single_record_state(
        cls,
        database: DatabaseService,
        revision_key: bytes,
        record_id: int,
        cancelled: threading.Event,
    ) -> tuple[dict[str, object], dict[str, object], str] | str:
        row = database.get_password_by_id(record_id)
        if row is None:
            return cls._database_core_error(database, fallback="DATABASE_IO_FAILED" if database.last_error else "NOT_FOUND")
        if cancelled.is_set():
            cls._scrub_record_dict(row)
            return "CANCELLED"
        platform = row.get("platform")
        account = row.get("account")
        password = row.get("password")
        notes = row.get("notes")
        totp_secret = row.get("totp_secret")
        favorite_raw = row.get("is_favorite")
        if (
            row.get("id") != record_id
            or not cls._stored_record_text(platform, required=True)
            or not cls._stored_record_text(account)
            or not cls._stored_record_text(password)
            or not cls._stored_record_text(notes)
            or type(totp_secret) is not str
            or type(favorite_raw) not in {bool, int}
            or int(favorite_raw) not in {0, 1}
        ):
            cls._scrub_record_dict(row)
            return "DATABASE_IO_FAILED"
        platform_value = str(platform)
        if not platform_value.strip():
            cls._scrub_record_dict(row)
            return "DATABASE_IO_FAILED"
        try:
            recovery_codes = validate_codes(row["recovery_codes"])
        except (KeyError, RecoveryCodeError):
            cls._scrub_record_dict(row)
            return "DATABASE_IO_FAILED"
        revision_source = {
            "record_id": record_id,
            "platform": platform_value,
            "account": str(account),
            "password": str(password),
            "notes": str(notes),
            "totp_secret": str(totp_secret),
            "recovery_codes": recovery_codes,
            "strength": cls._record_strength(row, revision_key),
            "favorite": bool(favorite_raw),
            "password_changed_at": cls._timestamp_value(
                row.get("password_changed_at")
            ),
            "updated_at": cls._timestamp_value(row.get("updated_at")),
        }
        current_revision = cls._record_revision(
            revision_key,
            revision_source,
        )
        return row, revision_source, current_revision

    @classmethod
    def _committed_record_result(
        cls,
        revision_key: bytes,
        row: dict[str, object],
        record_id: object,
    ) -> _SessionReadResult:
        """从核心层实际提交的记录构造写入回执，避免提交后回读。"""

        revision_source = {
            "record_id": row["id"],
            "platform": str(row["platform"]),
            "account": str(row["account"]),
            "password": str(row["password"]),
            "notes": str(row["notes"]),
            "totp_secret": str(row["totp_secret"]),
            "recovery_codes": validate_codes(row["recovery_codes"]),
            "strength": cls._record_strength(row, revision_key),
            "favorite": bool(row["is_favorite"]),
            "password_changed_at": cls._timestamp_value(
                row.get("password_changed_at")
            ),
            "updated_at": cls._timestamp_value(row.get("updated_at")),
        }
        try:
            return _SessionReadResult(
                "OK",
                {
                    "item": {
                        "recordId": record_id,
                        "revision": cls._record_revision(
                            revision_key,
                            revision_source,
                        ),
                        "favorite": bool(row["is_favorite"]),
                    },
                },
            )
        finally:
            cls._scrub_record_dict(row)
            cls._scrub_revision_source(revision_source)

    @classmethod
    def _open_record_editor(
        cls,
        database: DatabaseService,
        revision_key: bytes,
        record_id: int,
        revision: str,
        cancelled: threading.Event,
    ) -> _SessionReadResult:
        row: dict[str, object] | None = None
        revision_source: dict[str, object] | None = None
        password = ""
        try:
            state = cls._single_record_state(
                database,
                revision_key,
                record_id,
                cancelled,
            )
            if isinstance(state, str):
                return _SessionReadResult(state)
            row, revision_source, current_revision = state
            if not hmac.compare_digest(current_revision, revision):
                return _SessionReadResult("REVISION_CONFLICT")
            if cancelled.is_set():
                return _SessionReadResult("CANCELLED")
            password = str(row["password"])
            return _SessionReadResult(
                "OK",
                {
                    "recordId": record_id,
                    "revision": current_revision,
                    "platform": field_preview("PLATFORM", str(row["platform"])),
                    "account": field_preview("ACCOUNT", str(row["account"])),
                    "password": field_preview("PASSWORD", password),
                    "notes": field_preview("NOTES", str(row["notes"])),
                    "hasTotp": bool(row["totp_secret"]),
                    "recoveryCount": len(row["recovery_codes"]),
                    "favorite": bool(row["is_favorite"]),
                    "longFields": [
                        field
                        for field, value in (
                            ("PLATFORM", str(row["platform"])),
                            ("ACCOUNT", str(row["account"])),
                            ("PASSWORD", password),
                            ("NOTES", str(row["notes"])),
                        )
                        if field_is_long(field, value)
                    ],
                    "editLeaseId": secrets.token_urlsafe(24),
                    "expiresInMs": 300_000,
                },
            )
        except Exception:
            return _SessionReadResult("DATABASE_IO_FAILED")
        finally:
            password = ""
            if row is not None:
                cls._scrub_record_dict(row)
            if revision_source is not None:
                cls._scrub_revision_source(revision_source)

    @classmethod
    def _resolve_editor_revision(
        cls,
        database: DatabaseService,
        revision_key: bytes,
        record_id: int,
        cancelled: threading.Event,
    ) -> _SessionReadResult:
        row: dict[str, object] | None = None
        revision_source: dict[str, object] | None = None
        try:
            state = cls._single_record_state(
                database,
                revision_key,
                record_id,
                cancelled,
            )
            if isinstance(state, str):
                return _SessionReadResult(state)
            row, revision_source, revision = state
            return _SessionReadResult("OK", {"revision": revision})
        except Exception:
            return _SessionReadResult("DATABASE_IO_FAILED")
        finally:
            if row is not None:
                cls._scrub_record_dict(row)
            if revision_source is not None:
                cls._scrub_revision_source(revision_source)

    @classmethod
    def _resolve_note_editor_revision(
        cls,
        database: DatabaseService,
        revision_key: bytes,
        note_id: int,
        cancelled: threading.Event,
    ) -> _SessionReadResult:
        row: dict[str, object] | None = None
        try:
            state = cls._single_note_state(
                database,
                revision_key,
                note_id,
                cancelled,
            )
            if isinstance(state, str):
                return _SessionReadResult(state)
            row, _note, revision = state
            return _SessionReadResult("OK", {"revision": revision})
        except Exception:
            return _SessionReadResult("DATABASE_IO_FAILED")
        finally:
            if row is not None:
                cls._scrub_note_dict(row)

    @classmethod
    def _update_record(
        cls,
        database: DatabaseService,
        revision_key: bytes,
        record_id: int,
        revision: str,
        platform: str,
        account: str,
        password_action: str,
        password: str,
        notes: str,
        totp_action: str,
        totp_secret: str,
        favorite: object,
        cancelled: threading.Event,
        *,
        recovery_action: str = "KEEP",
        recovery_text: str = "",
    ) -> _SessionReadResult:
        return cls._update_record_fields(
            database,
            revision_key,
            record_id,
            revision,
            "REPLACE",
            platform,
            "REPLACE",
            account,
            password_action,
            password,
            "REPLACE",
            notes,
            totp_action,
            totp_secret,
            favorite,
            cancelled,
            recovery_action=recovery_action, recovery_text=recovery_text,
        )

    @classmethod
    def _update_record_fields(
        cls,
        database: DatabaseService,
        revision_key: bytes,
        record_id: object,
        revision: object,
        platform_action: object,
        platform: object,
        account_action: object,
        account: object,
        password_action: object,
        password: object,
        notes_action: object,
        notes: object,
        totp_action: object,
        totp_secret: object,
        favorite: object,
        cancelled: threading.Event,
        *,
        recovery_action: str = "KEEP",
        recovery_text: str = "",
    ) -> _SessionReadResult:
        row: dict[str, object] | None = None
        revision_source: dict[str, object] | None = None
        expected: dict[str, object] | None = None
        update: dict[str, object] = {}
        try:
            fields = (
                ("platform", platform_action, platform, 1, 128, 512),
                ("account", account_action, account, 0, 512, 2048),
                ("password", password_action, password, 0, 1024, 4096),
                ("notes", notes_action, notes, 0, 8192, 32768),
            )
            replacements: dict[str, str] = {}
            for name, action, value, minimum, maximum, max_bytes in fields:
                if (
                    type(action) is not str
                    or action not in {"KEEP", "REPLACE"}
                    or type(value) is not str
                ):
                    return _SessionReadResult("INVALID_ARGUMENT")
                if action == "KEEP":
                    if value != "":
                        return _SessionReadResult("INVALID_ARGUMENT")
                    continue
                if not cls._bounded_text(value, minimum, maximum, max_bytes):
                    return _SessionReadResult("INVALID_ARGUMENT")
                replacements[name] = value
            if "platform" in replacements:
                if not replacements["platform"].strip():
                    return _SessionReadResult("INVALID_ARGUMENT")
            if type(record_id) is not int or type(revision) is not str:
                return _SessionReadResult("INVALID_ARGUMENT")
            normalized_totp = cls._normalize_totp_update(
                totp_action,
                totp_secret,
            )
            if normalized_totp is None:
                return _SessionReadResult(
                    "INVALID_ARGUMENT",
                    error_argument_index=13,
                )
            if type(favorite) is not bool:
                return _SessionReadResult(
                    "INVALID_ARGUMENT",
                    error_argument_index=14,
                )
            if recovery_action not in {"KEEP", "REPLACE", "CLEAR"} or type(recovery_text) is not str:
                return _SessionReadResult("INVALID_ARGUMENT")
            if recovery_action != "REPLACE" and recovery_text:
                return _SessionReadResult("INVALID_ARGUMENT")
            try:
                codes = parse_codes(recovery_text) if recovery_action == "REPLACE" else []
            except RecoveryCodeError as exc:
                return _SessionReadResult(str(exc))
            if recovery_action == "REPLACE" and not codes:
                return _SessionReadResult("RECOVERY_CODES_INVALID")
            state = cls._single_record_state(
                database,
                revision_key,
                record_id,
                cancelled,
            )
            if isinstance(state, str):
                return _SessionReadResult(state)
            row, revision_source, current_revision = state
            if not hmac.compare_digest(current_revision, revision):
                return _SessionReadResult("REVISION_CONFLICT")
            if cancelled.is_set():
                return _SessionReadResult("CANCELLED")

            expected = dict(row)
            update = dict(replacements)
            update["is_favorite"] = favorite
            if totp_action == "REPLACE":
                update["totp_secret"] = normalized_totp
            elif totp_action == "CLEAR":
                update["totp_secret"] = ""
            if recovery_action != "KEEP":
                update["recovery_codes"] = codes

            updated_row = database.update_password(
                record_id,
                update,
                expected=expected,
                return_record=True,
                defer_strength=True,
            )
            if not isinstance(updated_row, dict):
                return _SessionReadResult(
                    {
                        "platform_conflict": "PLATFORM_CONFLICT",
                        "revision_conflict": "REVISION_CONFLICT",
                        "not_found": "NOT_FOUND",
                        "invalid_argument": "INVALID_ARGUMENT",
                        "cancelled": "CANCELLED",
                        "strength_analysis_failed": "PASSWORD_STRENGTH_FAILED",
                    }.get(
                        str(database.last_error_kind),
                        cls._database_core_error(database),
                    )
                )
            changed = any(updated_row[field] != row[field] for field in ("password", "platform", "account"))
            result = cls._committed_record_result(
                revision_key,
                updated_row,
                record_id,
            )
            result.strength_input_changed = changed
            return result
        except Exception:
            return _SessionReadResult("DATABASE_IO_FAILED")
        finally:
            if row is not None:
                cls._scrub_record_dict(row)
            if expected is not None:
                cls._scrub_record_dict(expected)
            if revision_source is not None:
                cls._scrub_revision_source(revision_source)
            cls._scrub_record_dict(update)

    @classmethod
    def _set_recovery_code_used(cls, database, revision_key, record_id, revision, code_index, used, cancelled):
        """按当前版本原子更新本地使用标记；不验证服务状态。"""
        row = source = None
        codes = []
        try:
            state = cls._single_record_state(database, revision_key, record_id, cancelled)
            if isinstance(state, str):
                return _SessionReadResult(state)
            row, source, current = state
            if type(revision) is not str or not hmac.compare_digest(current, revision):
                return _SessionReadResult("REVISION_CONFLICT")
            codes = validate_codes(row["recovery_codes"])
            if type(code_index) is not int or not 0 <= code_index < len(codes) or type(used) is not bool:
                return _SessionReadResult("INVALID_ARGUMENT")
            if cancelled.is_set():
                return _SessionReadResult("CANCELLED")
            codes[code_index]["used"] = used
            committed = database.update_password(
                record_id, {"recovery_codes": codes}, expected=row, return_record=True,
            )
            if not isinstance(committed, dict):
                return _SessionReadResult("REVISION_CONFLICT" if database.last_error_kind == "revision_conflict" else cls._database_core_error(database))
            return cls._committed_record_result(revision_key, committed, record_id)
        except Exception:
            return _SessionReadResult("DATABASE_IO_FAILED")
        finally:
            if row is not None:
                cls._scrub_record_dict(row)
            if source is not None:
                cls._scrub_revision_source(source)
            for code in codes:
                code["value"] = ""
            codes.clear()

    @classmethod
    def _set_record_favorite(
        cls,
        database: DatabaseService,
        revision_key: bytes,
        record_id: int,
        revision: str,
        favorite: bool,
        cancelled: threading.Event,
    ) -> _SessionReadResult:
        row: dict[str, object] | None = None
        revision_source: dict[str, object] | None = None
        expected: dict[str, object] | None = None
        try:
            if type(favorite) is not bool:
                return _SessionReadResult(
                    "INVALID_ARGUMENT",
                    error_argument_index=6,
                )
            state = cls._single_record_state(
                database,
                revision_key,
                record_id,
                cancelled,
            )
            if isinstance(state, str):
                return _SessionReadResult(state)
            row, revision_source, current_revision = state
            if not hmac.compare_digest(current_revision, revision):
                return _SessionReadResult("REVISION_CONFLICT")
            if cancelled.is_set():
                return _SessionReadResult("CANCELLED")
            expected = dict(row)
            updated_row = database.update_password(
                record_id,
                {"is_favorite": favorite},
                expected=expected,
                return_record=True,
            )
            if not isinstance(updated_row, dict):
                return _SessionReadResult(
                    {
                        "revision_conflict": "REVISION_CONFLICT",
                        "not_found": "NOT_FOUND",
                        "invalid_argument": "INVALID_ARGUMENT",
                    }.get(
                        str(database.last_error_kind),
                        cls._database_core_error(database),
                    )
                )
            return cls._committed_record_result(
                revision_key,
                updated_row,
                record_id,
            )
        except Exception:
            return _SessionReadResult("DATABASE_IO_FAILED")
        finally:
            if row is not None:
                cls._scrub_record_dict(row)
            if expected is not None:
                cls._scrub_record_dict(expected)
            if revision_source is not None:
                cls._scrub_revision_source(revision_source)

    def _read_record_field_chunk(self, database: DatabaseService, key: bytes, page_epoch: int, session_epoch: int, record_id: int, revision: str, field: str, lease_id: str, read_id: str, offset: object, cancelled: threading.Event) -> _SessionReadResult:
        row: dict[str, object] | None = None
        source: dict[str, object] | None = None
        value = ""
        try:
            state = self._single_record_state(database, key, record_id, cancelled)
            if isinstance(state, str):
                return _SessionReadResult(state)
            row, source, current = state
            if not hmac.compare_digest(current, revision):
                return _SessionReadResult("REVISION_CONFLICT")
            field_map = {"PLATFORM": "platform", "ACCOUNT": "account", "PASSWORD": "password", "NOTES": "notes"}
            field_name = field_map.get(field)
            if field_name is None or type(offset) is not int:
                return _SessionReadResult("INVALID_ARGUMENT")
            value = str(row[field_name])
            try:
                result = self._record_field_reads.take(page_epoch=page_epoch, session_epoch=session_epoch, record_id=record_id, revision=revision, field=field, authority_lease_id=lease_id, read_id=read_id, offset=offset, value=value, cancelled=cancelled)
            except FieldReadRejected as exc:
                return _SessionReadResult(str(exc))
            return _SessionReadResult("OK", result)
        finally:
            value = ""
            if row is not None: self._scrub_record_dict(row)
            if source is not None: self._scrub_revision_source(source)

    @classmethod
    def _prepare_delete_record(
        cls,
        database: DatabaseService,
        revision_key: bytes,
        record_id: int,
        revision: str,
        cancelled: threading.Event,
    ) -> _SessionReadResult:
        row: dict[str, object] | None = None
        revision_source: dict[str, object] | None = None
        try:
            state = cls._single_record_state(
                database,
                revision_key,
                record_id,
                cancelled,
            )
            if isinstance(state, str):
                return _SessionReadResult(
                    (
                        "INTERNAL_FAILURE"
                        if state in {"DATABASE_IO_FAILED", "CANCELLED"}
                        else state
                    )
                )
            row, revision_source, current_revision = state
            if not hmac.compare_digest(current_revision, revision):
                return _SessionReadResult("REVISION_CONFLICT")
            if cancelled.is_set():
                return _SessionReadResult("INTERNAL_FAILURE")
            entity_label = str(row["platform"])
            return _SessionReadResult(
                "OK",
                {"entityLabel": entity_label},
                delete_ticket_draft=_DeleteTicketDraft(
                    record_id=record_id,
                    revision=current_revision,
                    entity_label=entity_label,
                ),
            )
        except Exception:
            return _SessionReadResult("INTERNAL_FAILURE")
        finally:
            if row is not None:
                cls._scrub_record_dict(row)
            if revision_source is not None:
                cls._scrub_revision_source(revision_source)

    @classmethod
    def _delete_record(
        cls,
        database: DatabaseService,
        revision_key: bytes,
        record_id: int,
        revision: str,
        cancelled: threading.Event,
    ) -> _SessionReadResult:
        row: dict[str, object] | None = None
        revision_source: dict[str, object] | None = None
        expected: dict[str, object] | None = None
        try:
            state = cls._single_record_state(
                database,
                revision_key,
                record_id,
                cancelled,
            )
            if isinstance(state, str):
                return _SessionReadResult(
                    (
                        "INTERNAL_FAILURE"
                        if state == "CANCELLED"
                        else state
                    )
                )
            row, revision_source, current_revision = state
            if not hmac.compare_digest(current_revision, revision):
                return _SessionReadResult("REVISION_CONFLICT")
            if cancelled.is_set():
                return _SessionReadResult("INTERNAL_FAILURE")
            expected = dict(row)
            if not database.delete_password(
                record_id,
                expected=expected,
            ):
                return _SessionReadResult(
                    {
                        "revision_conflict": "REVISION_CONFLICT",
                        "not_found": "NOT_FOUND",
                        "invalid_argument": "INVALID_ARGUMENT",
                    }.get(
                        str(database.last_error_kind),
                        cls._database_core_error(database),
                    )
                )
            return _SessionReadResult(
                "OK",
                {
                    "deletedId": record_id,
                },
            )
        except Exception:
            return _SessionReadResult("DATABASE_IO_FAILED")
        finally:
            if row is not None:
                cls._scrub_record_dict(row)
            if expected is not None:
                cls._scrub_record_dict(expected)
            if revision_source is not None:
                cls._scrub_revision_source(revision_source)

    @classmethod
    def _create_record(
        cls,
        database: DatabaseService,
        revision_key: bytes,
        platform: str,
        account: str,
        password: str,
        notes: str,
        totp_action: str,
        totp_secret: str,
        favorite: bool,
        cancelled: threading.Event,
        *,
        recovery_text: str = "",
    ) -> _SessionReadResult:
        if not platform.strip():
            return _SessionReadResult("INVALID_ARGUMENT", error_argument_index=4)
        normalized_totp = cls._normalize_totp_secret(
            totp_action,
            totp_secret,
        )
        if normalized_totp is None:
            return _SessionReadResult("INVALID_ARGUMENT", error_argument_index=9)
        if cancelled.is_set():
            return _SessionReadResult("CANCELLED")
        try:
            recovery_codes = parse_codes(recovery_text)
        except RecoveryCodeError as exc:
            return _SessionReadResult(str(exc))
        created_row = database.insert_password(
            {
                "platform": platform,
                "account": account,
                "password": password,
                "notes": notes,
                "totp_secret": normalized_totp,
                "recovery_codes": recovery_codes,
                "is_favorite": 1 if favorite else 0,
            },
            return_record=True,
            defer_strength=True,
        )
        if not isinstance(created_row, dict):
            return _SessionReadResult(
                (
                    {
                        "platform_conflict": "PLATFORM_CONFLICT",
                        "cancelled": "CANCELLED",
                        "strength_analysis_failed": "PASSWORD_STRENGTH_FAILED",
                    }.get(str(database.last_error_kind), cls._database_core_error(database))
                )
            )
        return cls._committed_record_result(
            revision_key,
            created_row,
            created_row["id"],
        )

    @staticmethod
    def _generate_password(
        length: int,
        use_lower: bool,
        use_upper: bool,
        use_digits: bool,
        use_symbols: bool,
        avoid_ambiguous: bool,
        cancelled: threading.Event,
    ) -> _SessionReadResult:
        if type(length) is not int or not 1 <= length <= 1024:
            return _SessionReadResult("INVALID_ARGUMENT")
        selected = sum(
            (use_lower, use_upper, use_digits, use_symbols)
        )
        if selected == 0:
            return _SessionReadResult("EMPTY_CHARACTER_SET")
        if length < selected:
            return _SessionReadResult("GENERATOR_LENGTH_TOO_SHORT")
        if cancelled.is_set():
            return _SessionReadResult("CANCELLED")
        password = ""
        try:
            password = PasswordTools.generate_password(
                length=length,
                use_upper=use_upper,
                use_lower=use_lower,
                use_digits=use_digits,
                use_symbols=use_symbols,
                avoid_ambiguous=avoid_ambiguous,
            )
            if cancelled.is_set():
                return _SessionReadResult("CANCELLED")
            return _SessionReadResult(
                "OK",
                {
                    "secretLeaseId": secrets.token_urlsafe(24),
                    "password": password,
                    "expiresInMs": 300_000,
                },
            )
        except ValueError:
            return _SessionReadResult("INTERNAL_FAILURE")
        except Exception:
            return _SessionReadResult("INTERNAL_FAILURE")
        finally:
            password = ""

    @staticmethod
    def _check_password_strength(
        password: str,
        platform: str,
        account: str,
        cancelled: threading.Event,
    ) -> _SessionReadResult:
        if not password:
            return _SessionReadResult(
                "OK",
                {
                    "level": "WEAK",
                    "score": 0,
                    "feedbackCodes": ["EMPTY"],
                    "crackTimes": {
                        "onlineThrottled": "INSTANT",
                        "onlineUnthrottled": "INSTANT",
                        "offlineSlow": "INSTANT",
                        "offlineFast": "INSTANT",
                    },
                    "guesses": "0",
                    "downgraded": False,
                },
            )
        try:
            return _SessionReadResult(
                "OK",
                analyze_strength_in_process(
                    password,
                    platform,
                    account,
                    cancelled,
                ),
            )
        except StrengthAnalysisCancelled:
            return _SessionReadResult("CANCELLED")
        except StrengthWorkerError:
            return _SessionReadResult("INTERNAL_FAILURE")
        except Exception:
            return _SessionReadResult("INTERNAL_FAILURE")

    @staticmethod
    def _evaluate_record_strength(
        password: str,
        platform: str,
        account: str,
        cancelled: threading.Event,
    ) -> str:
        analysis_platform = platform if len(platform) <= 32 else ""
        analysis_account = account if len(account) <= 32 else ""
        try:
            report = analyze_strength_in_process(
                password,
                analysis_platform,
                analysis_account,
                cancelled,
            )
        except StrengthAnalysisCancelled:
            raise StrengthEvaluationCancelled() from None
        except StrengthWorkerError:
            raise StrengthEvaluationError("密码强度计算失败") from None
        if cancelled.is_set():
            raise StrengthEvaluationCancelled()
        level = report.get("level")
        if type(level) is not str:
            raise StrengthEvaluationError("密码强度计算返回了非法等级")
        return level.lower()

    @classmethod
    def _quickbar_search(
        cls,
        database: DatabaseService,
        revision_key: bytes,
        query: str,
        limit: int,
        cancelled: threading.Event,
    ) -> _SessionReadResult:
        from pypinyin import lazy_pinyin

        loaded = cls._load_vault_records(
            database,
            revision_key,
            cancelled,
            detail_record_id=0,
        )
        if isinstance(loaded, str):
            return _SessionReadResult(loaded)
        if cancelled.is_set():
            return _SessionReadResult("CANCELLED")
        folded = query.strip().casefold()
        matched = [
            item
            for item in loaded
            if (
                not folded
                or field_matches_query(item.platform, folded)
                or field_matches_query(item.account, folded)
            )
        ]
        matched.sort(
            key=lambda item: (
                not item.favorite,
                "".join(lazy_pinyin(item.platform)).casefold(),
                item.account.casefold(),
                item.record_id,
            )
        )
        return _SessionReadResult(
            "OK",
            {
                "items": [
                    {
                        "recordId": item.record_id,
                        "revision": item.revision,
                        "platform": field_preview("PLATFORM", item.platform),
                        "accountDisplay": field_preview("ACCOUNT", item.account),
                        "favorite": item.favorite,
                        "hasTotp": item.has_totp,
                    }
                    for item in matched[:limit]
                ],
                "total": len(matched),
            },
        )

    @staticmethod
    def _quickbar_generate_and_copy(
        length: int,
        clipboard: ProductClipboardController,
        cancelled: threading.Event,
        *,
        publication_token: int | None = None,
    ) -> _SessionReadResult:
        password = ""
        copy_arguments = {} if publication_token is None else {"publication_token": publication_token, "cancelled": cancelled}
        try:
            if cancelled.is_set():
                return _SessionReadResult("CANCELLED")
            if not 4 <= length <= 1024:
                return _SessionReadResult(
                    "INVALID_ARGUMENT",
                    error_argument_index=3,
                )
            password = PasswordTools.generate_password(
                length,
                use_upper=True,
                use_lower=True,
                use_digits=True,
                use_symbols=True,
                avoid_ambiguous=False,
            )
            if cancelled.is_set():
                return _SessionReadResult("CANCELLED")
            copied = clipboard.copy(password, "PASSWORD", **copy_arguments)
            if copied is None:
                return _SessionReadResult("CLIPBOARD_UNAVAILABLE")
            return _SessionReadResult("OK", copied)
        except Exception:
            return _SessionReadResult("INTERNAL_FAILURE")
        finally:
            password = ""

    @classmethod
    def _record_secret_action(
        cls,
        database: DatabaseService,
        revision_key: bytes,
        command_id: CommandId,
        record_id: int,
        revision: str,
        clipboard: ProductClipboardController,
        cancelled: threading.Event,
        *,
        wall_clock: Callable[[], float] = time.time,
        monotonic_clock: Callable[[], float] = time.monotonic,
        code_index: int | None = None,
        publication_token: int | None = None,
    ) -> _SessionReadResult:
        row: dict[str, object] | None = None
        revision_source: dict[str, object] | None = None
        value = ""
        codes = []
        copy_arguments = {} if publication_token is None else {"publication_token": publication_token, "cancelled": cancelled}
        try:
            row = database.get_password_by_id(record_id)
            if row is None:
                return _SessionReadResult(
                    cls._database_core_error(database, fallback="DATABASE_IO_FAILED" if database.last_error else "NOT_FOUND")
                )
            if cancelled.is_set():
                return _SessionReadResult("CANCELLED")
            platform = row.get("platform")
            account = row.get("account")
            password = row.get("password")
            notes = row.get("notes")
            totp_secret = row.get("totp_secret")
            favorite_raw = row.get("is_favorite")
            if (
                row.get("id") != record_id
                or not cls._stored_record_text(platform, required=True)
                or not cls._stored_record_text(account)
                or not cls._stored_record_text(password)
                or not cls._stored_record_text(notes)
                or type(totp_secret) is not str
                or type(favorite_raw) not in {bool, int}
                or int(favorite_raw) not in {0, 1}
            ):
                return _SessionReadResult("DATABASE_IO_FAILED")
            revision_source = {
                "record_id": record_id,
                "platform": str(platform),
                "account": str(account),
                "password": str(password),
                "notes": str(notes),
                "totp_secret": str(totp_secret),
                "recovery_codes": validate_codes(row["recovery_codes"]),
                "strength": cls._record_strength(row, revision_key),
                "favorite": bool(favorite_raw),
                "password_changed_at": cls._timestamp_value(
                    row.get("password_changed_at")
                ),
                "updated_at": cls._timestamp_value(
                    row.get("updated_at")
                ),
            }
            if not revision_source["platform"]:
                return _SessionReadResult("DATABASE_IO_FAILED")
            current_revision = cls._record_revision(
                revision_key,
                revision_source,
            )
            if not hmac.compare_digest(current_revision, revision):
                return _SessionReadResult("REVISION_CONFLICT")
            if cancelled.is_set():
                return _SessionReadResult("CANCELLED")
            if command_id in {CommandId.C77, CommandId.C78}:
                codes = validate_codes(row["recovery_codes"])
                if type(code_index) is not int or not 0 <= code_index < len(codes):
                    return _SessionReadResult("NOT_FOUND")
                value = codes[code_index]["value"]
                if command_id is CommandId.C77:
                    return _SessionReadResult("OK", {
                        "secretLeaseId": secrets.token_urlsafe(24), "value": value,
                        "expiresInMs": 30_000, "longFields": [],
                    })
                if cancelled.is_set():
                    return _SessionReadResult("CANCELLED")
                copied = clipboard.copy(value, "RECOVERY_CODE", **copy_arguments)
                return _SessionReadResult("OK", copied) if copied is not None else _SessionReadResult("CLIPBOARD_UNAVAILABLE")
            if command_id is CommandId.C13:
                value = str(password)
                password_is_long = field_is_long("PASSWORD", value)
                return _SessionReadResult(
                    "OK",
                    {
                        "secretLeaseId": secrets.token_urlsafe(24),
                        "value": "" if password_is_long else value,
                        "expiresInMs": 30_000,
                        "longFields": ["PASSWORD"] if password_is_long else [],
                    },
                )
            if command_id in {CommandId.C21, CommandId.C22}:
                if command_id is CommandId.C21:
                    totp = cls._current_totp(
                        str(totp_secret),
                        wall_clock=wall_clock,
                        monotonic_clock=monotonic_clock,
                    )
                    if totp is None:
                        return _SessionReadResult("TOTP_UNAVAILABLE")
                    value, remaining_seconds, delivery_deadline = totp
                    return _SessionReadResult(
                        "OK",
                        {
                            "code": value,
                            "remainingSeconds": remaining_seconds,
                        },
                        delivery_deadline=delivery_deadline,
                    )
                for _attempt in range(2):
                    if cancelled.is_set():
                        return _SessionReadResult("CANCELLED")
                    totp = cls._current_totp(
                        str(totp_secret),
                        wall_clock=wall_clock,
                        monotonic_clock=monotonic_clock,
                    )
                    if totp is None:
                        return _SessionReadResult("TOTP_UNAVAILABLE")
                    value, _remaining_seconds, deadline = totp
                    if monotonic_clock() >= deadline:
                        value = ""
                        continue
                    clipboard_result = clipboard.copy(value, "TOTP", **copy_arguments)
                    if clipboard_result is None:
                        return _SessionReadResult("CLIPBOARD_UNAVAILABLE")
                    return _SessionReadResult("OK", clipboard_result)
                return _SessionReadResult("TOTP_UNAVAILABLE")
            if command_id in {CommandId.C19, CommandId.N02}:
                value = str(account)
                content_kind = "ACCOUNT"
            elif command_id in {CommandId.C20, CommandId.N03}:
                value = str(password)
                content_kind = "PASSWORD"
            else:
                return _SessionReadResult("INTERNAL_FAILURE")
            if cancelled.is_set():
                return _SessionReadResult("CANCELLED")
            if not value:
                return _SessionReadResult("EMPTY_FIELD")
            clipboard_result = clipboard.copy(value, content_kind, **copy_arguments)
            if clipboard_result is None:
                return _SessionReadResult("CLIPBOARD_UNAVAILABLE")
            return _SessionReadResult("OK", clipboard_result)
        except Exception:
            return _SessionReadResult("DATABASE_IO_FAILED")
        finally:
            value = ""
            for code in codes:
                code["value"] = ""
            codes.clear()
            if row is not None:
                row["account"] = ""
                row["password"] = ""
                row["notes"] = ""
                row["totp_secret"] = ""
                cls._scrub_record_dict(row)
            if revision_source is not None:
                revision_source["account"] = ""
                revision_source["password"] = ""
                revision_source["notes"] = ""
                revision_source["totp_secret"] = ""
                cls._scrub_revision_source(revision_source)

    @classmethod
    def _load_vault_records(
        cls,
        database: DatabaseService,
        revision_key: bytes,
        cancelled: threading.Event,
        *,
        detail_record_id: int,
    ) -> list[_VaultRecord] | str:
        rows: list[dict[str, object]] = []
        normalized: list[dict[str, object]] = []
        try:
            rows = database.get_all_passwords(should_cancel=cancelled.is_set)
            if database.last_error:
                return "CANCELLED" if cancelled.is_set() else cls._database_core_error(database)
            if not isinstance(rows, list):
                return "DATABASE_IO_FAILED"
            if len(rows) > 100_000:
                return "REQUEST_TOO_LARGE"

            seen_ids: set[int] = set()
            duplicate_buckets: dict[bytes, list[int]] = {}
            similar_buckets: dict[str, list[int]] = {}
            for row in rows:
                if cancelled.is_set():
                    return "CANCELLED"
                if not isinstance(row, dict):
                    return "DATABASE_IO_FAILED"
                record_id = row.get("id")
                platform = row.get("platform")
                account = row.get("account")
                password = row.get("password")
                notes = row.get("notes")
                totp_secret = row.get("totp_secret")
                if (
                    type(record_id) is not int
                    or not 1 <= record_id <= 2_147_483_647
                    or record_id in seen_ids
                    or not cls._stored_record_text(platform, required=True)
                    or not cls._stored_record_text(account)
                    or not cls._stored_record_text(password)
                    or not cls._stored_record_text(notes)
                    or type(totp_secret) is not str
                ):
                    return "DATABASE_IO_FAILED"
                favorite_raw = row.get("is_favorite")
                if (
                    type(favorite_raw) not in {bool, int}
                    or int(favorite_raw) not in {0, 1}
                ):
                    return "DATABASE_IO_FAILED"
                seen_ids.add(record_id)
                platform_value = str(platform)
                if not platform_value.strip():
                    return "DATABASE_IO_FAILED"
                password_value = str(password)
                health_password_changed_at = cls._health_timestamp_value(
                    row.get("password_changed_at")
                )
                duplicate_key = hashlib.blake2s(
                    password_value.encode("utf-8"),
                    key=revision_key,
                    digest_size=16,
                ).digest()
                if password_value:
                    duplicate_buckets.setdefault(
                        duplicate_key,
                        [],
                    ).append(record_id)
                similar_buckets.setdefault(
                    cls._similar_name_key(platform_value),
                    [],
                ).append(record_id)
                revision_source = {
                    "record_id": record_id,
                    "platform": platform_value,
                    "account": str(account),
                    "password": password_value,
                    "notes": str(notes),
                    "totp_secret": str(totp_secret),
                    "recovery_codes": validate_codes(row["recovery_codes"]),
                    "strength": cls._record_strength(row, revision_key),
                    "favorite": bool(favorite_raw),
                    "password_changed_at": cls._timestamp_value(
                        row.get("password_changed_at")
                    ),
                    "updated_at": cls._timestamp_value(
                        row.get("updated_at")
                    ),
                }
                normalized.append(
                    {
                        "record_id": record_id,
                        "platform": platform_value,
                        "account": (
                            str(account)
                            if detail_record_id in {0, record_id}
                            else ""
                        ),
                        "notes": (
                            field_preview("NOTES", str(notes))
                            if detail_record_id == record_id
                            else ""
                        ),
                        "long_fields": tuple(
                            field
                            for field, value in (
                                ("PLATFORM", platform_value),
                                ("ACCOUNT", str(account)),
                                ("PASSWORD", password_value),
                                ("NOTES", str(notes)),
                            )
                            if field_is_long(field, value)
                        ),
                        "strength": revision_source["strength"],
                        "favorite": bool(favorite_raw),
                        "password_changed_date": cls._date_value(
                            revision_source["password_changed_at"]
                        ),
                        "health_password_changed_at": (
                            health_password_changed_at
                        ),
                        "updated_date": cls._date_value(
                            revision_source["updated_at"]
                        ),
                        "updated_at": revision_source["updated_at"],
                        "has_password": bool(password_value),
                        "has_totp": bool(totp_secret),
                        "revision": cls._record_revision(
                            revision_key,
                            revision_source,
                        ),
                    }
                )
                revision_source["password"] = ""
                revision_source["totp_secret"] = ""
                revision_source["account"] = ""
                revision_source["notes"] = ""
                cls._scrub_revision_source(revision_source)

            duplicate_groups: dict[int, int] = {}
            repeated = [
                values
                for values in duplicate_buckets.values()
                if len(values) > 1
            ]
            repeated.sort(key=min)
            for group_number, values in enumerate(repeated, start=1):
                for record_id in values:
                    duplicate_groups[record_id] = group_number

            similar_groups: dict[int, int] = {}
            repeated_names = sorted(
                key for key, values in similar_buckets.items() if len(values) > 1
            )
            for group_number, key in enumerate(repeated_names, start=1):
                for record_id in similar_buckets[key]:
                    similar_groups[record_id] = group_number

            records: list[_VaultRecord] = []
            for value in normalized:
                records.append(
                    _VaultRecord(
                        record_id=int(value["record_id"]),
                        revision=str(value["revision"]),
                        platform=str(value["platform"]),
                        account=str(value["account"]),
                        notes=str(value["notes"]),
                        strength=str(value["strength"]),
                        favorite=bool(value["favorite"]),
                        duplicate_group=duplicate_groups.get(
                            int(value["record_id"]),
                            0,
                        ),
                        similar_group=similar_groups.get(
                            int(value["record_id"]),
                            0,
                        ),
                        has_password=bool(value["has_password"]),
                        has_totp=bool(value["has_totp"]),
                        long_fields=tuple(value["long_fields"]),
                        updated_at=str(value["updated_at"]),
                        updated_date=str(value["updated_date"]),
                        password_changed_date=str(
                            value["password_changed_date"]
                        ),
                        health_password_changed_at=value[
                            "health_password_changed_at"
                        ],
                    )
                )
            return records
        except Exception:
            return "DATABASE_IO_FAILED"
        finally:
            for row in rows:
                if isinstance(row, dict):
                    row["password"] = ""
                    row["totp_secret"] = ""
                    row["account"] = ""
                    row["notes"] = ""
                    cls._scrub_record_dict(row)
            for value in normalized:
                value["account"] = ""
                value["notes"] = ""

    @staticmethod
    def _scrub_note_dict(value: dict[str, object]) -> None:
        for field in ("title", "content", "created_at", "updated_at"):
            if field in value:
                value[field] = ""

    @staticmethod
    def _database_core_error(database: DatabaseService, *, fallback: str = "DATABASE_IO_FAILED") -> str:
        """仅传递固定资源类别；各调用方保留原来的业务错误判定。"""
        return {
            "resource_limit": "DATABASE_LIMIT_EXCEEDED",
            "insufficient_space": "DATABASE_SPACE_INSUFFICIENT",
            "cancelled": "CANCELLED",
            "revision_conflict": "REVISION_CONFLICT",
        }.get(str(getattr(database, "last_error_kind", None)), fallback)

    @staticmethod
    def _note_core_error(database: DatabaseService, *, missing: str = "DATABASE_IO_FAILED") -> str:
        if database.last_error is None and database.last_error_kind is None:
            return missing
        return {
            "nonexistent": missing,
            "not_found": missing,
            "revision_conflict": "REVISION_CONFLICT",
            "invalid_argument": "INVALID_ARGUMENT",
            "database_io_failed": "DATABASE_IO_FAILED",
        }.get(str(database.last_error_kind), ApplicationAdapter._database_core_error(database))

    @classmethod
    def _note_from_row(
        cls,
        revision_key: bytes,
        row: dict[str, object],
    ) -> _NoteRecord | None:
        note_id = row.get("id")
        title = row.get("title")
        content = row.get("content")
        created_at = row.get("created_at")
        updated_at = row.get("updated_at")
        sort_order = row.get("sort_order")
        favorite = row.get("is_favorite")
        if (
            type(note_id) is not int or note_id <= 0
            or type(title) is not str or not title.strip() or "\x00" in title
            or type(content) is not str or "\x00" in content
            or type(created_at) is not str or cls._timestamp_value(created_at) != created_at
            or type(updated_at) is not str or cls._timestamp_value(updated_at) != updated_at
            or type(sort_order) is not int or not 0 <= sort_order <= 2_147_483_647
            or type(favorite) not in {bool, int} or int(favorite) not in {0, 1}
        ):
            return None
        source = {
            "note_id": note_id, "title": title, "content": content,
            "created_at": created_at, "updated_at": updated_at,
            "sort_order": sort_order, "favorite": bool(favorite),
        }
        try:
            return _NoteRecord(note_id, cls._note_record_revision(revision_key, source), title, content, created_at, updated_at, sort_order, bool(favorite))
        finally:
            cls._scrub_note_dict(source)

    @staticmethod
    def _note_long_fields(note: _NoteRecord) -> list[str]:
        return [
            field for field, value in (("TITLE", note.title), ("CONTENT", note.content))
            if field_is_long(f"NOTE_{field}", value)
        ]

    @classmethod
    def _committed_note_result(
        cls,
        revision_key: bytes,
        row: dict[str, object],
    ) -> _SessionReadResult:
        note = cls._note_from_row(revision_key, row)
        try:
            if note is None:
                return _SessionReadResult("DATABASE_IO_FAILED")
            return _SessionReadResult(
                "OK",
                {"item": cls._note_summary(note), "noteRevision": note.revision},
            )
        finally:
            cls._scrub_note_dict(row)

    @classmethod
    def _load_note_records(
        cls,
        database: DatabaseService,
        revision_key: bytes,
        cancelled: threading.Event,
    ) -> list[_NoteRecord] | str:
        rows: list[dict[str, object]] = []
        records: list[_NoteRecord] = []
        try:
            rows = database.get_all_notes(should_cancel=cancelled.is_set)
            if database.last_error:
                return "CANCELLED" if cancelled.is_set() else cls._database_core_error(database)
            if not isinstance(rows, list):
                return "DATABASE_IO_FAILED"
            seen_ids: set[int] = set()
            for row in rows:
                if cancelled.is_set():
                    return "CANCELLED"
                if not isinstance(row, dict):
                    return "DATABASE_IO_FAILED"
                note = cls._note_from_row(revision_key, row)
                if note is None or note.note_id in seen_ids:
                    return "DATABASE_IO_FAILED"
                seen_ids.add(note.note_id)
                records.append(note)
            return records
        except Exception:
            return "DATABASE_IO_FAILED"
        finally:
            for row in rows:
                if isinstance(row, dict):
                    row["title"] = ""
                    row["content"] = ""
                    row["created_at"] = ""
                    row["updated_at"] = ""

    @staticmethod
    def _bounded_text(
        value: object,
        minimum_chars: int,
        maximum_chars: int,
        maximum_bytes: int,
    ) -> bool:
        return (
            type(value) is str
            and minimum_chars <= len(value) <= maximum_chars
            and len(value.encode("utf-8")) <= maximum_bytes
            and "\x00" not in value
        )

    @staticmethod
    def _stored_record_text(value: object, *, required: bool = False) -> bool:
        return (
            type(value) is str
            and "\x00" not in value
            and (not required or bool(value.strip()))
        )

    @staticmethod
    def _normalize_totp_secret(
        action: str,
        value: str,
    ) -> str | None:
        if action == "NONE":
            return "" if value == "" else None
        if action != "REPLACE" or not value:
            return None
        compact = "".join(value.split()).replace("-", "").upper()
        unpadded = compact.rstrip("=")
        if not unpadded or "=" in unpadded:
            return None
        padded = unpadded + ("=" * ((-len(unpadded)) % 8))
        try:
            decoded = base64.b32decode(padded, casefold=False)
        except Exception:
            return None
        return unpadded if decoded else None

    @classmethod
    def _normalize_totp_update(
        cls,
        action: object,
        value: object,
    ) -> str | None:
        if type(action) is not str or type(value) is not str:
            return None
        if action in {"KEEP", "CLEAR"}:
            return "" if value == "" else None
        if action != "REPLACE":
            return None
        if not cls._bounded_text(value, 1, 256, 512):
            return None
        return cls._normalize_totp_secret("REPLACE", value)

    @staticmethod
    def _current_totp(
        secret: str,
        *,
        wall_clock: Callable[[], float],
        monotonic_clock: Callable[[], float],
    ) -> tuple[str, int, float] | None:
        """仅在系统时钟处于同一稳定周期内生成验证码。"""

        for _attempt in range(2):
            started_at = wall_clock()
            generated = TOTPTool.generate_totp(secret)
            finished_at = wall_clock()
            deadline_base = monotonic_clock()
            if (
                type(started_at) not in {int, float}
                or type(finished_at) not in {int, float}
                or type(deadline_base) not in {int, float}
                or not math.isfinite(started_at)
                or not math.isfinite(finished_at)
                or not math.isfinite(deadline_base)
                or generated is None
            ):
                return None
            started_period = int(started_at) // TOTPTool.TIME_STEP
            finished_period = int(finished_at) // TOTPTool.TIME_STEP
            expected_remaining = (
                TOTPTool.TIME_STEP
                - (int(finished_at) % TOTPTool.TIME_STEP)
            )
            if (
                started_period != finished_period
                or generated.remaining != expected_remaining
            ):
                continue
            until_period_end = (
                TOTPTool.TIME_STEP
                - (finished_at % TOTPTool.TIME_STEP)
            )
            if (
                not 0.0 < until_period_end <= TOTPTool.TIME_STEP
            ):
                return None
            return (
                generated.code,
                generated.remaining,
                float(deadline_base + until_period_end),
            )
        return None

    @staticmethod
    def _scrub_record_dict(value: dict[str, object]) -> None:
        codes = value.get("recovery_codes")
        if isinstance(codes, list):
            for code in codes:
                if isinstance(code, dict):
                    code["value"] = ""
            codes.clear()
        if "recovery_codes" in value:
            value["recovery_codes"] = []
        for field in ("account", "password", "notes", "totp_secret"):
            if field in value:
                value[field] = ""

    @staticmethod
    def _scrub_revision_source(value: dict[str, object]) -> None:
        ApplicationAdapter._scrub_record_dict(value)

    @staticmethod
    def _vault_summary(item: _VaultRecord) -> dict[str, object]:
        return {
            "recordId": item.record_id,
            "revision": item.revision,
            "platform": field_preview("PLATFORM", item.platform),
            "accountDisplay": field_preview("ACCOUNT", item.account),
            "strength": item.strength,
            "favorite": item.favorite,
            "duplicateGroup": item.duplicate_group,
            "similarGroup": item.similar_group,
            "hasTotp": item.has_totp,
            "longFields": [
                field for field in item.long_fields if field != "PASSWORD"
            ],
            "updatedDate": item.updated_date,
            "passwordChangedDate": item.password_changed_date,
        }

    @staticmethod
    def _note_summary(item: _NoteRecord) -> dict[str, object]:
        return {
            "noteId": item.note_id,
            "revision": item.revision,
            "title": field_preview("NOTE_TITLE", item.title),
            "contentPreview": item.content[:160],
            "favorite": item.favorite,
            "longFields": ApplicationAdapter._note_long_fields(item),
            "previewTruncated": (
                len(item.content) > 160
                or field_is_long("NOTE_TITLE", item.title)
            ),
            "updatedDate": ApplicationAdapter._date_value(
                item.updated_at
            ),
        }

    @staticmethod
    def _scrub_generated_result(result: _SessionReadResult) -> None:
        if isinstance(result.result, dict):
            result.result["password"] = ""

    @staticmethod
    def _scrub_editor_result(result: _SessionReadResult) -> None:
        if not isinstance(result.result, dict):
            return
        for field in ("password", "value", "code", "text"):
            if field in result.result:
                result.result[field] = ""
        if "editLeaseId" in result.result:
            result.result["password"] = ""
        if "content" in result.result:
            result.result["title"] = ""
            result.result["content"] = ""
        item = result.result.get("item")
        if isinstance(item, dict) and "noteId" in item:
            item["title"] = ""
            item["contentPreview"] = ""
        items = result.result.get("items")
        if isinstance(items, list):
            for summary in items:
                if isinstance(summary, dict) and "noteId" in summary:
                    summary["title"] = ""
                    summary["contentPreview"] = ""

    @classmethod
    def _record_strength(cls, row: dict, revision_key: bytes) -> str:
        if row.get("strength") is not None:
            return cls._strength_value(row["strength"])
        if not row.get("password"):
            return "WEAK"
        queue = _RATING_QUEUE.get()
        if queue is None:
            return "PENDING"
        token = strength_input_token(revision_key, int(row["id"]), str(row["platform"]),
                                     str(row["account"]), str(row["password"]))
        return queue.state_for(int(row["id"]), token)

    @staticmethod
    def _strength_value(value: object) -> str:
        normalized = str(value or "").strip().casefold()
        return {
            "weak": "WEAK",
            "fair": "FAIR",
            "medium": "FAIR",
            "strong": "STRONG",
        }.get(normalized, "WEAK")

    @staticmethod
    def _date_value(value: object) -> str:
        candidate = str(value or "")[:10]
        try:
            return datetime.date.fromisoformat(candidate).isoformat()
        except ValueError:
            return "1970-01-01"

    @staticmethod
    def _timestamp_value(value: object) -> str:
        candidate = str(value or "")
        try:
            datetime.datetime.fromisoformat(candidate)
            return candidate
        except ValueError:
            return "1970-01-01T00:00:00"

    @staticmethod
    def _health_timestamp_value(value: object) -> str | None:
        if type(value) is not str:
            return None
        try:
            datetime.datetime.fromisoformat(value)
            return value
        except ValueError:
            return None

    @staticmethod
    def _timestamp_ordinal(value: str) -> float:
        try:
            parsed = datetime.datetime.fromisoformat(value)
        except ValueError:
            return 0.0
        try:
            return parsed.timestamp()
        except (OSError, OverflowError, ValueError):
            # 系统无法转换的合法日期仍按日历比较；无时区按 Q29 使用本机标准偏移。
            offset = parsed.utcoffset()
            if offset is None:
                offset = datetime.timedelta(seconds=-time.timezone)
            elapsed = parsed.replace(tzinfo=None) - datetime.datetime(1970, 1, 1)
            return elapsed.total_seconds() - offset.total_seconds()

    @staticmethod
    def _note_record_revision(
        revision_key: bytes,
        value: dict[str, object],
    ) -> str:
        serialized = json.dumps(
            [
                value["note_id"],
                value["title"],
                value["content"],
                value["created_at"],
                value["updated_at"],
                value["sort_order"],
                value["favorite"],
            ],
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.blake2s(
            serialized,
            key=revision_key,
            digest_size=16,
        ).hexdigest()

    @staticmethod
    def _note_revision(
        revision_key: bytes,
        records: list[_NoteRecord],
    ) -> str:
        serialized = json.dumps(
            [
                [item.note_id, item.revision, item.sort_order]
                for item in sorted(records, key=lambda value: value.note_id)
            ],
            separators=(",", ":"),
        ).encode("ascii")
        return hashlib.blake2s(
            serialized,
            key=revision_key,
            digest_size=16,
        ).hexdigest()

    @staticmethod
    def _record_revision(
        revision_key: bytes,
        value: dict[str, object],
    ) -> str:
        """内容版本供编辑、复制等操作使用；评级刷新不撤销这些操作。"""
        serialized = json.dumps(
            [
                value["record_id"],
                value["platform"],
                value["account"],
                value["password"],
                value["notes"],
                value["totp_secret"],
                value.get("recovery_codes", []),
                value["favorite"],
                value["password_changed_at"],
                value["updated_at"],
            ],
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.blake2s(
            serialized,
            key=revision_key,
            digest_size=16,
        ).hexdigest()

    @staticmethod
    def _vault_revision(
        revision_key: bytes,
        records: list[_VaultRecord],
    ) -> str:
        """列表聚合包含评级，确保强度排序、弱密码筛选及体检游标更新。"""
        serialized = json.dumps(
            [
                [
                    item.record_id,
                    item.revision,
                    item.strength,
                    item.duplicate_group,
                    item.similar_group,
                ]
                for item in sorted(
                    records,
                    key=lambda value: value.record_id,
                )
            ],
            separators=(",", ":"),
        ).encode("ascii")
        return hashlib.blake2s(
            serialized,
            key=revision_key,
            digest_size=16,
        ).hexdigest()

    @staticmethod
    def _encode_cursor(
        offset: int,
        revision_key: bytes,
        scope: str,
    ) -> str:
        signature = hashlib.blake2s(
            f"{scope}:{offset}".encode("utf-8"),
            key=revision_key,
            digest_size=8,
        ).hexdigest()
        return f"{offset}_{signature}"

    @staticmethod
    def _decode_cursor(
        cursor: str,
        revision_key: bytes,
        scope: str,
        total: int,
    ) -> int | None:
        if not cursor:
            return 0
        matched = re.fullmatch(r"(0|[1-9][0-9]{0,5})_([0-9a-f]{16})", cursor)
        if matched is None:
            return None
        offset = int(matched.group(1))
        if offset >= total:
            return None
        expected = ApplicationAdapter._encode_cursor(
            offset,
            revision_key,
            scope,
        ).split("_", 1)[1]
        if not hmac.compare_digest(expected, matched.group(2)):
            return None
        return offset

    def _finish_session_read(
        self,
        request_id: str,
        future: Future[_SessionReadResult],
    ) -> None:
        operation: _SessionReadOperation | None = None
        try:
            try:
                result = future.result()
            except Exception:
                result = _SessionReadResult(
                    (
                        "CANCELLED"
                        if future.cancelled()
                        else "INTERNAL_FAILURE"
                    )
                )
            with self._lock:
                candidate = self._operations.pop(request_id, None)
                if not isinstance(candidate, _SessionReadOperation):
                    self._scrub_editor_result(result)
                    return
                operation = candidate
                session_invalidated = (
                    operation.database is self._database
                    and not operation.database.bound_identity_is_current()
                )
                if session_invalidated:
                    self._release_session_locked()
                native_command = operation.command_id in {
                    CommandId.N01,
                    CommandId.N02,
                    CommandId.N03,
                    CommandId.N04,
                }
                cancelled = (
                    operation.cancelled.is_set()
                    or self._closed
                    or (
                        not native_command
                        and operation.page_epoch not in self._valid_pages
                    )
                    or operation.session_epoch != self._session_epoch
                    or operation.database is not self._database
                )
                if session_invalidated:
                    self._discard_session_read_result(operation, result)
                    completion = self._session_read_error(
                        operation,
                        "STALE_SESSION",
                    )
                elif cancelled:
                    self._discard_session_read_result(operation, result)
                    completion = self._session_read_error(
                        operation,
                        (
                            "CANCELLED"
                            if operation.command_id in {
                                CommandId.C10,
                                CommandId.C14,
                                CommandId.C15,
                                CommandId.C62,
                                CommandId.C66,
                                CommandId.C67,
                                CommandId.C68,
                                CommandId.C75,
                                CommandId.C76,
                                CommandId.C24,
                                CommandId.C31,
                                CommandId.C32,
                                CommandId.N01,
                                CommandId.N02,
                                CommandId.N03,
                                CommandId.N04,
                            }
                            else "INTERNAL_FAILURE"
                        ),
                    )
                elif result.error_code != "OK" or result.result is None:
                    self._discard_session_read_result(operation, result)
                    completion = self._session_read_error(
                        operation,
                        result.error_code,
                        error_argument_index=result.error_argument_index,
                        retry_after_ms=(
                            self._failure_retry_ms
                            if operation.command_id in {
                                CommandId.C14,
                                CommandId.C15,
                                CommandId.C62,
                                CommandId.C26,
                                CommandId.C27,
                                CommandId.C28,
                                CommandId.C30,
                                CommandId.C65,
                            }
                            else 0
                        ),
                    )
                else:
                    if (
                        operation.command_id is CommandId.C12
                        and not operation.editor_revision_only
                    ):
                        with self._health_edit_lock:
                            self._health_edit_leases[str(result.result["editLeaseId"])] = (
                                int(result.result["recordId"]),
                                self._clock() + int(result.result["expiresInMs"]) / 1000,
                            )
                    if (
                        operation.command_id is CommandId.C68
                        and result.guidance_snapshot is not None
                    ):
                        self._health_guidance = result.guidance_snapshot
                        self._released_health_guidance_id = ""
                    if operation.command_id in {CommandId.C17, CommandId.C29}:
                        self._prune_delete_tickets_locked()
                        draft = result.delete_ticket_draft
                        if (
                            draft is None
                            or len(self._delete_tickets)
                            >= _MAX_DELETE_TICKETS
                        ):
                            completion = self._session_read_error(
                                operation,
                                "INTERNAL_FAILURE",
                            )
                        else:
                            ticket_value = secrets.token_urlsafe(24)
                            ticket = _DeleteTicket(
                                value=ticket_value,
                                page_epoch=operation.page_epoch,
                                session_epoch=operation.session_epoch,
                                record_id=draft.record_id,
                                revision=draft.revision,
                                entity_label=draft.entity_label,
                                entity_kind=draft.entity_kind,
                                expires_at=(
                                    self._clock()
                                    + (_DELETE_TICKET_TTL_MS / 1000)
                                ),
                            )
                            self._delete_tickets[ticket_value] = ticket
                            result.result = {
                                "deleteTicket": ticket_value,
                                "entityLabel": draft.entity_label,
                                "expiresInMs": _DELETE_TICKET_TTL_MS,
                            }
                            completion = self._session_read_success(
                                operation,
                                result.result,
                            )
                    else:
                        if operation.command_id in {
                            CommandId.C14,
                            CommandId.C15,
                            CommandId.C16,
                            CommandId.C79,
                            CommandId.C62,
                            CommandId.C18,
                            CommandId.C26,
                            CommandId.C27,
                            CommandId.C28,
                            CommandId.C30,
                            CommandId.C65,
                        }:
                            self._revision += 1
                            if operation.command_id in {
                                CommandId.C14,
                                CommandId.C15,
                                CommandId.C16,
                                CommandId.C79,
                                CommandId.C62,
                            }:
                                result.result["vaultRevision"] = (
                                    self._revision_value("vault")
                                )
                            if operation.command_id is CommandId.C18:
                                result.result["dataRevision"] = (
                                    self._revision_value("vault")
                                )
                            if operation.command_id in {
                                CommandId.C26,
                                CommandId.C27,
                                CommandId.C28,
                                CommandId.C30,
                                CommandId.C65,
                            }:
                                result.result["noteRevision"] = (
                                    self._revision_value("notes")
                                )
                            if operation.command_id not in {
                                CommandId.C26,
                                CommandId.C27,
                                CommandId.C28,
                                CommandId.C30,
                                CommandId.C65,
                            }:
                                result.result["healthRevision"] = (
                                    self._revision_value("health")
                                )
                        completion = self._session_read_success(
                            operation,
                            result.result,
                            delivery_deadline=result.delivery_deadline,
                        )
                        if isinstance(self._health_rescan, SessionStrengthQueue) and operation.command_id in {
                            CommandId.C14, CommandId.C15, CommandId.C62, CommandId.C18,
                        }:
                            item = result.result.get("item", {})
                            record_id = item.get("recordId") if isinstance(item, dict) else None
                            self._health_rescan.wake(record_id, retry=result.strength_input_changed)
            operation.complete(completion)
        finally:
            if operation is not None:
                operation.settled.set()

    def _finish_page_secret(
        self,
        request_id: str,
        future: Future[_SessionReadResult],
    ) -> None:
        operation: _PageSecretOperation | None = None
        result = _SessionReadResult("INTERNAL_FAILURE")
        try:
            try:
                result = future.result()
            except Exception:
                result = _SessionReadResult(
                    "CANCELLED" if future.cancelled() else "INTERNAL_FAILURE"
                )
            with self._lock:
                candidate = self._operations.pop(request_id, None)
                if not isinstance(candidate, _PageSecretOperation):
                    self._scrub_generated_result(result)
                    return
                operation = candidate
                cancelled = (
                    operation.cancelled.is_set()
                    or self._closed
                    or operation.page_epoch not in self._valid_pages
                )
                if cancelled:
                    self._scrub_generated_result(result)
                    completion = AdapterCompletion(
                        command_id=operation.command_id,
                        request_id=operation.request_id,
                        token=operation.token,
                        error_code="CANCELLED",
                    )
                elif result.error_code != "OK" or result.result is None:
                    self._scrub_generated_result(result)
                    completion = AdapterCompletion(
                        command_id=operation.command_id,
                        request_id=operation.request_id,
                        token=operation.token,
                        error_code=result.error_code,
                        error_argument_index=result.error_argument_index,
                    )
                else:
                    if (
                        operation.command_id is CommandId.C33
                        and not self._register_generated_secret_locked(
                            operation.page_epoch,
                            result.result,
                        )
                    ):
                        self._scrub_generated_result(result)
                        completion = AdapterCompletion(
                            command_id=operation.command_id,
                            request_id=operation.request_id,
                            token=operation.token,
                            error_code="INTERNAL_FAILURE",
                        )
                        operation.complete(completion)
                        return
                    completion = AdapterCompletion(
                        command_id=operation.command_id,
                        request_id=operation.request_id,
                        token=operation.token,
                        error_code="OK",
                        result=result.result,
                    )
            operation.complete(completion)
        finally:
            if operation is not None:
                operation.settled.set()

    def _submit_lock(
        self,
        request: AdapterRequest,
        complete: CompletionCallback,
    ) -> None:
        self._release_session()
        complete(
            self._success(
                request,
                {
                    "sessionEpoch": 0,
                    "state": "LOCKED",
                },
            )
        )

    def _remember_opened_path(self, path: Path) -> bool:
        self._security.commit_successful_connection(str(path))
        return True

    def _read_effective_theme_provider(self) -> str:
        try:
            value = self._effective_theme_provider()
        except Exception:
            return "DARK"
        return value if value in {"LIGHT", "DARK"} else "DARK"

    @staticmethod
    def _read_m4_settings_source(
        settings_file: Path,
    ) -> dict[str, object] | None:
        try:
            with settings_file.open("r", encoding="utf-8") as handle:
                value = json.load(handle)
        except (
            FileNotFoundError,
            OSError,
            UnicodeError,
            json.JSONDecodeError,
        ):
            return None
        return value if isinstance(value, dict) else None

    def _theme_preference(self) -> str:
        theme = str(self._config.get("theme", "dark")).upper()
        return theme if theme in {"LIGHT", "DARK", "AUTO"} else "DARK"

    def _language_preference(self) -> str:
        language = str(self._config.get("language", "zh")).upper()
        return language if language in {"ZH", "EN"} else "ZH"

    def _close_to_tray_preference(self) -> bool:
        return self._bounded_bool(
            self._config.get("close_to_tray", True),
            True,
        )

    def _clipboard_mode(self) -> str:
        mode = str(
            self._config.get("clipboard_clear_mode", "countdown")
        ).upper()
        return mode if mode in {"COUNTDOWN", "MANUAL"} else "COUNTDOWN"

    def _clipboard_seconds(self) -> int:
        return self._bounded_int(
            self._config.get("clipboard_clear_seconds", 30),
            5,
            60,
            30,
        )

    def _auto_lock_enabled(self) -> bool:
        return self._bounded_bool(
            self._config.get("auto_lock_enabled", True),
            True,
        )

    def _auto_lock_minutes(self) -> int:
        return self._bounded_int(
            self._config.get("auto_lock_minutes", 5),
            1,
            60,
            5,
        )

    def _quickbar_enabled(self) -> bool:
        return self._bounded_bool(
            self._config.get("quickbar_enabled", True),
            True,
        )

    def _quickbar_hotkey(self) -> str:
        return self._bounded_hotkey(
            self._config.get("quick_bar_hotkey", "Alt+P")
        )

    def _quickbar_idle_seconds(self) -> int:
        return self._bounded_int(
            self._config.get("quickbar_autohide_sec", 30),
            10,
            600,
            30,
        )

    def _stale_days(self) -> int:
        return self._bounded_int(
            self._config.get("stale_threshold_days", 180),
            30,
            365,
            180,
        )

    def _settings_snapshot(self) -> dict[str, object]:
        theme = self._theme_preference()
        language = self._language_preference()
        default_view = str(
            self._config.get("view_mode", "list")
        ).upper()
        if default_view not in {"LIST", "SPLIT"}:
            default_view = "LIST"
        sort_mode = str(
            self._config.get("sort_mode", "updated")
        ).upper()
        if sort_mode not in {"UPDATED", "NAME", "STRENGTH"}:
            sort_mode = "UPDATED"
        clipboard_mode = self._clipboard_mode()
        return {
            "theme": theme,
            "effectiveTheme": (
                self._native_effective_theme
                if theme == "AUTO"
                else theme
            ),
            "language": language,
            "uiFontScale": self._ui_font_scale(),
            "startupAutofill": self._bounded_bool(
                self._config.get("startup_autofill", False),
                False,
            ),
            "defaultView": default_view,
            "sidebarText": self._bounded_bool(
                self._config.get("sidebar_text", True),
                True,
            ),
            "sortMode": sort_mode,
            "clipboardMode": clipboard_mode,
            "clipboardSeconds": self._clipboard_seconds(),
            "closeBehavior": (
                "TO_TRAY" if self._close_to_tray_preference() else "EXIT"
            ),
            "quickbarEnabled": (
                self._quickbar_enabled()
                if self._hotkey is not None
                else False
            ),
            "quickbarIdleSeconds": self._quickbar_idle_seconds(),
            "quickbarHotkey": self._quickbar_hotkey(),
            "quickbarRegistration": (
                self._quickbar_registration
                if self._hotkey is not None
                else "DISABLED"
            ),
            "staleDays": self._stale_days(),
            "autoLockEnabled": self._auto_lock_enabled(),
            "autoLockMinutes": self._auto_lock_minutes(),
            "generator": {
                **self._generator_preferences(),
            },
        }

    def _ui_font_scale(self) -> str:
        return normalize_ui_font_scale(self._config.get("ui_font_scale", "100"))

    def _startup_path(
        self,
        settings: dict[str, object],
    ) -> tuple[str, bool]:
        """Return display text and native expected-existing intent."""

        if settings.get("startupAutofill") is True:
            last = self._security.get_last_db_path(strict=True)
            if last:
                try:
                    raw_path = Path(str(last))
                    path = (
                        raw_path.resolve(strict=False)
                        if self._isolation.database_candidate_syntax_is_safe(
                            raw_path
                        )
                        else None
                    )
                except (OSError, RuntimeError, ValueError):
                    path = None
                if (
                    path is not None
                    and self._isolation.allows_existing_database(path)
                ):
                    return str(path), True
        default_path = self._isolation.default_database.resolve(
            strict=False
        )
        return (
            str(default_path),
            default_path.is_file(),
        )

    def _settings_revision(self) -> str:
        persisted_snapshot = self._settings_snapshot()
        persisted_snapshot.pop("effectiveTheme", None)
        encoded = json.dumps(
            persisted_snapshot,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("ascii")
        return hashlib.sha256(encoded).hexdigest()[:_REVISION_WIDTH]

    def _recent_databases(self) -> list[dict[str, object]]:
        values: list[dict[str, object]] = []
        active_paths_by_id: dict[str, Path] = {}
        active_ids_by_path: dict[str, str] = {}
        for path_value, used_at in self._security.get_recent_db_paths(
            5,
            strict=True,
        ):
            raw_path = Path(path_value)
            if not self._isolation.database_candidate_syntax_is_safe(
                raw_path
            ):
                continue
            path = raw_path.resolve(strict=False)
            if (
                not self._isolation.allows_existing_database(path)
            ):
                continue
            key = str(path)
            recent_id = self._recent_ids.get(key)
            if recent_id is None:
                recent_id = secrets.token_urlsafe(18)
            active_ids_by_path[key] = recent_id
            active_paths_by_id[recent_id] = path
            if used_at is None:
                try:
                    used_ms = int(path.stat().st_mtime * 1000)
                except OSError:
                    used_ms = 0
            else:
                used_ms = max(0, int(used_at.timestamp() * 1000))
            values.append(
                {
                    "recentDatabaseId": recent_id,
                    "displayName": path.name,
                    "displayPath": str(path),
                    "lastUsedUnixMs": used_ms,
                    "lockedUntilUnixMs": (
                        self._security.get_lock_until_unix_ms(
                            str(path),
                            strict=True,
                        )
                    ),
                }
            )
        self._recent_ids = active_ids_by_path
        self._recent_paths_by_id = active_paths_by_id
        return values

    def _authentication_failure_locked(
        self,
        operation: _OpenOperation,
    ) -> AdapterCompletion:
        path_value = str(operation.ticket.target.path)
        try:
            state = self._security.record_authentication_failure(
                path_value
            )
        except SecurityStateCommitError:
            return self._operation_error(operation, "INTERNAL_FAILURE")
        if state.locked_until_unix_ms > 0:
            return self._operation_error(
                operation,
                "LOCKED_OUT",
                retry_after_ms=self._retry_after_ms(
                    state.locked_until_unix_ms
                ),
            )

        error_code = {
            2: "AUTH_FAILED_RETRY_2",
            1: "AUTH_FAILED_RETRY_1",
        }.get(state.remaining_attempts)
        if error_code is None:
            return self._operation_error(
                operation,
                "INTERNAL_FAILURE",
            )
        self._restore_ticket_locked(operation.ticket)
        return self._operation_error(operation, error_code)

    def _restore_ticket_locked(self, ticket: _SelectionTicket) -> None:
        if (
            self._closed
            or ticket.page_epoch not in self._valid_pages
            or ticket.expires_at <= self._clock()
            or self._ticket_target_state_error(ticket) is not None
        ):
            return
        self._tickets[ticket.value] = ticket

    def _ticket_target_state_error(
        self,
        ticket: _SelectionTicket,
    ) -> str | None:
        target = ticket.target
        if (
            not isinstance(target, DatabaseTarget)
            or not isinstance(target.kind, DatabaseTargetKind)
        ):
            return "DATABASE_INVALID"
        if target.kind is DatabaseTargetKind.CREATE_NEW:
            return (
                None
                if self._isolation.allows_new_database(target.path)
                else "DATABASE_INVALID"
            )
        if not self._isolation.allows_existing_database(target.path):
            return "NOT_FOUND" if not target.path.exists() else "DATABASE_INVALID"
        current_identity = self._file_identity(target.path)
        if current_identity is None:
            return "NOT_FOUND"
        if (
            ticket.file_identity is None
            or not self._same_file_object(
                ticket.file_identity,
                current_identity,
            )
        ):
            return "DATABASE_INVALID"
        return None

    @staticmethod
    def _file_identity(
        path: Path,
    ) -> tuple[int, int, int, int] | None:
        try:
            value = path.stat()
        except OSError:
            return None
        if not path.is_file():
            return None
        return (
            int(value.st_dev),
            int(value.st_ino),
            int(value.st_size),
            int(value.st_ctime_ns),
        )

    @staticmethod
    def _same_file_object(
        expected: tuple[int, int, int, int],
        current: tuple[int, int, int, int],
    ) -> bool:
        expected_device, expected_inode, _size, expected_created = (
            expected
        )
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

    @staticmethod
    def _retry_after_ms(locked_until_unix_ms: int) -> int:
        remaining = locked_until_unix_ms - int(time.time() * 1000)
        return min(86_400_000, max(1, remaining))

    def _target_is_valid(self, target: DatabaseTarget) -> bool:
        if (
            not isinstance(target, DatabaseTarget)
            or not isinstance(target.kind, DatabaseTargetKind)
        ):
            return False
        if target.kind is DatabaseTargetKind.OPEN_EXISTING:
            return self._isolation.allows_existing_database(target.path)
        return self._isolation.allows_new_database(target.path)

    def _prune_tickets_locked(self) -> None:
        now = self._clock()
        self._tickets = {
            value: ticket
            for value, ticket in self._tickets.items()
            if ticket.expires_at > now
            and ticket.page_epoch in self._valid_pages
        }

    def _prune_delete_tickets_locked(self) -> None:
        now = self._clock()
        self._delete_tickets = {
            value: ticket
            for value, ticket in self._delete_tickets.items()
            if (
                ticket.expires_at > now
                and ticket.page_epoch in self._valid_pages
                and ticket.session_epoch == self._session_epoch
                and self._database is not None
            )
        }

    def _release_session(self) -> None:
        operations: list[
            _OpenOperation
            | _SessionReadOperation
            | _PageSecretOperation
            | _ChangeKeyOperation
            | _BackupOperation
        ] = []
        with self._lock:
            if self._health_rescan is not None:
                self._health_rescan.cancel()
            self._revoke_generated_secrets_locked()
            for operation in tuple(self._operations.values()):
                if isinstance(
                    operation,
                    (
                        _OpenOperation,
                        _SessionReadOperation,
                        _PageSecretOperation,
                        _ChangeKeyOperation,
                        _BackupOperation,
                    ),
                ):
                    self._request_operation_cancel_locked(operation)
                    operations.append(operation)
        self._wait_for_operations(operations)
        with self._lock:
            self._release_session_locked()

    @staticmethod
    def _request_operation_cancel_locked(
        operation: (
            _OpenOperation
            | _SessionReadOperation
            | _PageSecretOperation
            | _ChangeKeyOperation
            | _BackupOperation
        ),
    ) -> None:
        if isinstance(operation, _ChangeKeyOperation) and (
            operation.irreversible or operation.commit_started
        ):
            return
        if isinstance(operation, _BackupOperation) and operation.commit_started:
            return
        operation.cancelled.set()
        if operation.future is not None:
            operation.future.cancel()

    def _release_session_locked(self) -> None:
        scan = self._health_rescan
        self._health_rescan = None
        if scan is not None:
            scan.close()
        with self._health_edit_lock:
            self._health_edit_leases.clear()
            self._editor_occupancy = None
        database = self._database
        self._record_field_reads.clear()
        self._note_field_reads.clear()
        self._backup.clear()
        self._delete_tickets.clear()
        self._health_guidance = None
        self._released_health_guidance_id = ""
        self._database = None
        self._database_path = None
        self._session_token = 0
        self._session_epoch = 0
        self._session_revision_key = None
        self._settings_invalidating_sessions.clear()
        if database is not None:
            database.disconnect()

    @staticmethod
    def _destroy_open_result(result: _OpenResult) -> None:
        if result.database is not None:
            result.database.disconnect()
            result.database = None

    @staticmethod
    def _wait_for_operations(
        operations: list[
            _OpenOperation
            | _SessionReadOperation
            | _PageSecretOperation
            | _ChangeKeyOperation
            | _BackupOperation
        ],
    ) -> None:
        for operation in operations:
            future = operation.future
            if future is None:
                continue
            try:
                future.result()
            except Exception:
                pass
            operation.settled.wait()

    @staticmethod
    def _wait_for_settings_operations(
        operations: list[_SettingsOperation],
    ) -> None:
        """Wait for accepted config commits without cancelling persistence."""

        for operation in operations:
            future = operation.future
            if future is None:
                continue
            try:
                future.result()
            except Exception:
                pass
            operation.settled.wait()

    def _drop_session_setting_publications_locked(
        self,
        *,
        session_epoch: int | None = None,
    ) -> None:
        self._settings_publications = {
            request_id: publication
            for request_id, publication in self._settings_publications.items()
            if not (
                publication.command_id in {
                    CommandId.C38,
                    CommandId.C39,
                    CommandId.C43,
                    CommandId.C42,
                    CommandId.C44,
                    CommandId.C45,
                    CommandId.C46,
                    CommandId.C47,
                    CommandId.C41,
                    CommandId.C48,
                }
                and (
                    session_epoch is None
                    or publication.session_epoch == session_epoch
                )
            )
        }

    @staticmethod
    def _generator_options_are_valid(value: object) -> bool:
        if not isinstance(value, dict):
            return False
        length = value.get("length")
        flags = tuple(
            value.get(name)
            for name in (
                "useLower",
                "useUpper",
                "useDigits",
                "useSymbols",
                "avoidAmbiguous",
            )
        )
        selected = sum(flag is True for flag in flags[:4])
        return (
            type(length) is int
            and 1 <= length <= 1024
            and all(type(flag) is bool for flag in flags)
            and selected > 0
            and length >= selected
        )

    def _generator_preferences(self) -> dict[str, object]:
        value = self._config.get("generator")
        if self._generator_options_are_valid(value):
            return {
                name: value[name]
                for name in DEFAULT_SETTINGS["generator"]
            }
        return copy.deepcopy(DEFAULT_SETTINGS["generator"])

    def _register_generated_secret_locked(
        self,
        page_epoch: int,
        result: dict[str, object],
    ) -> bool:
        lease_id = result.get("secretLeaseId")
        password = result.get("password")
        expires_in_ms = result.get("expiresInMs")
        if (
            type(lease_id) is not str
            or not lease_id
            or type(password) is not str
            or not password
            or type(expires_in_ms) is not int
            or not 1 <= expires_in_ms <= 300_000
        ):
            return False
        self._prune_generated_secrets_locked()
        if (
            lease_id in self._generated_secrets
            or len(self._generated_secrets) >= _MAX_GENERATED_SECRET_LEASES
        ):
            return False
        expiry_timer = threading.Timer(
            expires_in_ms / 1000.0,
            self.revoke_secret_lease,
            (lease_id,),
        )
        expiry_timer.daemon = True
        self._generated_secrets[lease_id] = _GeneratedSecret(
            lease_id=lease_id,
            page_epoch=page_epoch,
            expires_at=self._clock() + expires_in_ms / 1000.0,
            password=password,
            expiry_timer=expiry_timer,
        )
        expiry_timer.start()
        return True

    def _prune_generated_secrets_locked(self) -> None:
        now = self._clock()
        for lease_id, secret in tuple(self._generated_secrets.items()):
            if secret.expires_at <= now:
                self._revoke_generated_secret_locked(lease_id)

    def _revoke_generated_secret_locked(self, lease_id: str) -> bool:
        secret = self._generated_secrets.pop(lease_id, None)
        if secret is None:
            return False
        secret.password = ""
        secret.expiry_timer.cancel()
        return True

    def _revoke_generated_secrets_locked(
        self,
        *,
        page_epoch: int | None = None,
    ) -> None:
        for lease_id, secret in tuple(self._generated_secrets.items()):
            if page_epoch is None or secret.page_epoch == page_epoch:
                self._revoke_generated_secret_locked(lease_id)

    def _revision_value(self, scope: str) -> str:
        digest = hashlib.sha256(
            f"{scope}:{self._revision}".encode("ascii")
        ).hexdigest()
        return digest[:_REVISION_WIDTH]

    @staticmethod
    def _bounded_int(
        value: object,
        minimum: int,
        maximum: int,
        fallback: int,
    ) -> int:
        if type(value) is not int:
            return fallback
        return min(maximum, max(minimum, value))

    @staticmethod
    def _similar_name_key(value: str) -> str:
        return similar_name_key(value)

    @staticmethod
    def _bounded_bool(value: object, fallback: bool) -> bool:
        return value if type(value) is bool else fallback

    @staticmethod
    def _bounded_hotkey(value: object) -> str:
        normalized = ApplicationAdapter._normalize_hotkey(value)
        return normalized if normalized is not None else "Alt+P"

    @staticmethod
    def _normalize_hotkey(value: object) -> str | None:
        if type(value) is not str or not _HOTKEY.fullmatch(value):
            return None
        parsed = parse_hotkey(value)
        if (
            parsed is None
            or not is_hotkey_main_key(parsed.main)
            or not (
                parsed.ctrl
                or parsed.alt
                or parsed.shift
                or parsed.win
            )
        ):
            return None
        modifiers = []
        if parsed.ctrl:
            modifiers.append("Ctrl")
        if parsed.alt:
            modifiers.append("Alt")
        if parsed.shift:
            modifiers.append("Shift")
        if parsed.win:
            modifiers.append("Win")
        main = parsed.main
        if main.startswith("f") and main[1:].isdigit():
            main = main.upper()
        elif len(main) == 1 and main.isalpha():
            main = main.upper()
        elif main in {"space", "tab", "enter", "backspace"}:
            main = main.capitalize()
        normalized = "+".join((*modifiers, main))
        return normalized if _HOTKEY.fullmatch(normalized) else None

    @staticmethod
    def _success(
        request: AdapterRequest,
        result: dict[str, object],
    ) -> AdapterCompletion:
        return AdapterCompletion(
            command_id=request.command_id,
            request_id=request.request_id,
            token=request.token,
            error_code="OK",
            result=result,
        )

    @staticmethod
    def _error(
        request: AdapterRequest,
        error_code: str,
        *,
        error_argument_index: int = 0,
        retry_after_ms: int = 0,
    ) -> AdapterCompletion:
        return AdapterCompletion(
            command_id=request.command_id,
            request_id=request.request_id,
            token=request.token,
            error_code=error_code,
            error_argument_index=error_argument_index,
            retry_after_ms=retry_after_ms,
        )

    @staticmethod
    def _operation_success(
        operation: _OpenOperation,
        result: dict[str, object],
    ) -> AdapterCompletion:
        return AdapterCompletion(
            command_id=CommandId.C04,
            request_id=operation.request_id,
            token=operation.token,
            error_code="OK",
            result=result,
        )

    @staticmethod
    def _operation_error(
        operation: _OpenOperation,
        error_code: str,
        *,
        retry_after_ms: int = 0,
    ) -> AdapterCompletion:
        return AdapterCompletion(
            command_id=CommandId.C04,
            request_id=operation.request_id,
            token=operation.token,
            error_code=error_code,
            retry_after_ms=retry_after_ms,
        )

    @staticmethod
    def _session_read_success(
        operation: _SessionReadOperation,
        result: dict[str, object],
        *,
        delivery_deadline: float | None = None,
    ) -> AdapterCompletion:
        return AdapterCompletion(
            command_id=operation.command_id,
            request_id=operation.request_id,
            token=operation.token,
            error_code="OK",
            result=result,
            delivery_deadline=delivery_deadline,
        )

    @staticmethod
    def _session_read_error(
        operation: _SessionReadOperation,
        error_code: str,
        *,
        error_argument_index: int = 0,
        retry_after_ms: int = 0,
    ) -> AdapterCompletion:
        return AdapterCompletion(
            command_id=operation.command_id,
            request_id=operation.request_id,
            token=operation.token,
            error_code=error_code,
            error_argument_index=error_argument_index,
            retry_after_ms=retry_after_ms,
        )


__all__ = ["ApplicationAdapter", "SettingsCommitPublication"]
