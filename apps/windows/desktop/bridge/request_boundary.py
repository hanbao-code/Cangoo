"""Request identity, validation, replay, cancellation, and late-result gate."""

from __future__ import annotations

from collections import OrderedDict
from copy import deepcopy
from dataclasses import dataclass, replace
from enum import Enum
import math
import time
from typing import Callable

from .command_ids import CommandId
from .contract_catalog import (
    CommandSpec,
    ContractCatalog,
    ValueRejected,
)
from .protocol import (
    AdapterCompletion,
    AdapterRequest,
    BridgeAdapter,
    C49_INTERNAL_FAILURE_REASON,
    CompletionCallback,
    CompletionEnvelope,
    NullSessionStateSink,
    NullSecurityBoundarySink,
    SecurityBoundarySink,
    SecretLifecycleSink,
    SessionStateSink,
    RecordFieldReadParentBinding,
)
from .secret_leases import (
    SecretLeaseKind,
    SecretLeaseRegistry,
    SecretLeaseRejected,
    SecretLeaseRule,
)


class Surface(str, Enum):
    WEBCHANNEL = "webchannel"
    NATIVE_QUICKBAR = "native_quickbar_port"


PAGE_BOUNDARY_REASONS = frozenset(
    {
        "bridge_close",
        "bridge_destroyed",
        "exit",
        "page_invalidated",
        "renderer_failure",
    }
)
SESSION_BOUNDARY_REASONS = frozenset(
    {
        "auto_lock",
        "change_key_failed",
        "change_key_restored",
        "change_key_success",
        "manual_lock",
        "renderer_failure",
        "session_invalidated",
        "suspend_lock",
        "switch_database",
    }
)
CLOSE_BOUNDARY_REASONS = frozenset(
    {"bridge_close", "bridge_destroyed", "exit"}
)


@dataclass(frozen=True, slots=True)
class SubmitAck:
    accepted: bool
    error_code: str
    error_argument_index: int

    def to_wire(self) -> dict[str, object]:
        return {
            "accepted": self.accepted,
            "errorCode": self.error_code,
            "errorArgumentIndex": self.error_argument_index,
        }


@dataclass(slots=True)
class _Pending:
    request: AdapterRequest
    spec: CommandSpec
    fingerprint: tuple[object, ...] | None
    authority_serial: int
    record_field_read_parent: RecordFieldReadParentBinding | None = None
    cancel_requested: bool = False
    session_transition: bool = False


@dataclass(frozen=True, slots=True)
class _Completed:
    completed_at: float
    fingerprint: tuple[object, ...] | None
    envelope: CompletionEnvelope | None
    pending_backup_read: tuple[CommandId, str] | None = None


class RequestBoundary:
    """Fail-closed boundary shared by Web and native QuickBar surfaces."""

    def __init__(
        self,
        catalog: ContractCatalog,
        adapter: BridgeAdapter,
        surface: Surface,
        completion_sink: Callable[[CompletionEnvelope], None],
        *,
        adapter_completion_receiver: CompletionCallback | None = None,
        secret_lifecycle_sink: SecretLifecycleSink | None = None,
        security_boundary_sink: SecurityBoundarySink | None = None,
        session_state_sink: SessionStateSink | None = None,
        request_admission: (
            Callable[[CommandId, tuple[object, ...]], str | None] | None
        ) = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._catalog = catalog
        self._adapter = adapter
        self._surface = surface
        self._completion_sink = completion_sink
        self._adapter_completion_receiver = (
            adapter_completion_receiver or self.receive_adapter_completion
        )
        self._clock = clock
        self._security_boundary_sink = (
            security_boundary_sink or NullSecurityBoundarySink()
        )
        self._session_state_sink = (
            session_state_sink or NullSessionStateSink()
        )
        self._request_admission = request_admission
        self._secret_leases = SecretLeaseRegistry(
            {
                CommandId.C12: SecretLeaseRule(
                    SecretLeaseKind.EDITOR,
                    "editLeaseId",
                    catalog.secret_lease_ttl_ms(CommandId.C12),
                ),
                CommandId.C13: SecretLeaseRule(
                    SecretLeaseKind.REVEAL,
                    "secretLeaseId",
                    catalog.secret_lease_ttl_ms(CommandId.C13),
                    retain_after_delivery=True,
                ),
                CommandId.C77: SecretLeaseRule(
                    SecretLeaseKind.REVEAL, "secretLeaseId",
                    catalog.secret_lease_ttl_ms(CommandId.C77), retain_after_delivery=True,
                ),
                CommandId.C33: SecretLeaseRule(
                    SecretLeaseKind.GENERATED,
                    "secretLeaseId",
                    catalog.secret_lease_ttl_ms(CommandId.C33),
                ),
            },
            self._safe_revoke_secret_lease,
            lifecycle_sink=secret_lifecycle_sink,
            clock=clock,
        )
        self._pending: dict[str, _Pending] = {}
        self._completed: OrderedDict[str, _Completed] = OrderedDict()
        self._next_token = 1
        self._active_page_epoch = 0
        self._active_session_epoch = 0
        self._last_page_epoch = 0
        self._last_session_epoch = 0
        self._page_instance_id: str | None = None
        self._retired_page_instances: OrderedDict[str, None] = OrderedDict()
        self._authority_serial = 0
        self._closed = False
        self._close_cleanup_complete: bool | None = None
        self._non_native_cleanup_complete = False
        self._c49_exclusive_request_id: str | None = None

    @property
    def non_native_cleanup_complete(self) -> bool:
        """仅原生宿主读取：租约与适配器清理是否完成。"""
        return self._closed and self._non_native_cleanup_complete

    @property
    def active_page_epoch(self) -> int:
        return self._active_page_epoch

    @property
    def active_session_epoch(self) -> int:
        return self._active_session_epoch

    @property
    def pending_count(self) -> int:
        return len(self._pending)

    @property
    def active_secret_lease_count(self) -> int:
        return self._secret_leases.active_count

    @property
    def pending_change_key_token(self) -> int | None:
        request_id = self._c49_exclusive_request_id
        pending = self._pending.get(request_id) if request_id else None
        if (
            pending is None
            or pending.spec.command_id is not CommandId.C49
        ):
            return None
        return pending.request.token

    def submit(
        self,
        command_id: CommandId,
        arguments: tuple[object, ...],
    ) -> SubmitAck:
        if self._closed:
            return self._reject("STALE_PAGE", 0)
        spec = self._catalog.command(command_id)
        if spec.surface != self._surface.value:
            return self._reject("INVALID_ARGUMENT", 0)
        if len(arguments) != len(spec.arguments):
            return self._reject("INVALID_ARGUMENT", 0)

        for index, (argument, definition) in enumerate(
            zip(arguments, spec.arguments),
            start=1,
        ):
            try:
                self._catalog.validate_value(
                    definition.type_name,
                    argument,
                )
            except ValueRejected:
                return self._reject("INVALID_ARGUMENT", index)
        if (
            self._catalog.wire_size(arguments)
            > self._catalog.max_request_utf8_bytes
        ):
            return self._reject("REQUEST_TOO_LARGE", 0)

        request_id = arguments[0]
        if type(request_id) is not str:
            return self._reject("INVALID_ARGUMENT", 1)
        identity_error = self._identity_error(spec, arguments)
        if identity_error is not None:
            return self._reject(identity_error, 0)
        if self._request_admission is not None:
            try:
                admission_error = self._request_admission(
                    command_id,
                    arguments,
                )
            except Exception:
                admission_error = "INTERNAL_FAILURE"
            if admission_error is not None:
                if admission_error not in spec.errors:
                    admission_error = "INTERNAL_FAILURE"
                return self._reject(admission_error, 0)

        self._prune_completed()
        fingerprint = self._fingerprint(spec, arguments)
        existing = self._completed.get(request_id)
        if request_id in self._pending:
            return self._reject("DUPLICATE_REQUEST", 1)
        if existing is not None:
            if (
                existing.envelope is not None
                and existing.fingerprint == fingerprint
                and self._envelope_is_current(existing.envelope)
            ):
                self._completion_sink(
                    self._clone_envelope(existing.envelope)
                )
                return self._accept()
            return self._reject("DUPLICATE_REQUEST", 1)

        if (
            self._c49_exclusive_request_id is not None
            and command_id is not CommandId.C07
        ):
            return self._reject("REQUEST_BUSY", 0)
        if command_id is CommandId.C49 and any(
            pending.spec.auth in {"SESSION", "NATIVE_SESSION"}
            for pending in self._pending.values()
        ):
            return self._reject("REQUEST_BUSY", 0)

        if len(self._pending) >= self._catalog.max_in_flight_per_page:
            return self._reject("REQUEST_BUSY", 0)
        lifecycle = self._catalog.lifecycle(spec.lifecycle)
        same_command = sum(
            pending.spec.command_id is command_id
            for pending in self._pending.values()
        )
        if same_command >= lifecycle.max_in_flight:
            return self._reject("REQUEST_BUSY", 0)

        page_epoch, session_epoch = self._request_identity(spec, arguments)
        capability_error, record_field_read_parent = self._prepare_lease_action(
            spec,
            arguments,
            page_epoch=page_epoch,
            session_epoch=session_epoch,
        )
        if capability_error is not None:
            return self._reject(capability_error, 0)
        request = AdapterRequest(
            command_id=command_id,
            request_id=request_id,
            token=self._next_token,
            page_epoch=page_epoch,
            session_epoch=session_epoch,
            argument_names=tuple(
                argument.name for argument in spec.arguments
            ),
            arguments=arguments,
        )
        self._next_token += 1
        pending = _Pending(
            request=request,
            spec=spec,
            fingerprint=fingerprint,
            authority_serial=self._authority_serial,
            record_field_read_parent=record_field_read_parent,
        )
        self._pending[request_id] = pending
        if command_id is CommandId.C49:
            self._c49_exclusive_request_id = request_id

        if command_id is CommandId.C07:
            self._complete_cancel_control(pending)
            return self._accept()
        if command_id in {CommandId.C05, CommandId.C06}:
            if not self._begin_session_transition(pending):
                self._adapter_completion_receiver(
                    AdapterCompletion(
                        command_id=command_id,
                        request_id=request_id,
                        token=request.token,
                        error_code="INTERNAL_FAILURE",
                    )
                )
                return self._accept()

        try:
            self._adapter.submit(
                request,
                self._adapter_completion_receiver,
            )
        except Exception:
            self._adapter_completion_receiver(
                AdapterCompletion(
                    command_id=command_id,
                    request_id=request_id,
                    token=request.token,
                    error_code="INTERNAL_FAILURE",
                )
            )
        return self._accept()

    def receive_adapter_completion(self, completion: object) -> None:
        if not isinstance(completion, AdapterCompletion):
            return
        pending = self._pending.get(completion.request_id)
        if (
            pending is None
            or pending.request.command_id is not completion.command_id
            or pending.request.token != completion.token
        ):
            self._safe_discard(completion)
            return
        if pending.authority_serial != self._authority_serial:
            self._remove_pending(completion.request_id)
            self._remember_tombstone(pending)
            self._secret_leases.revoke_result_lease(
                completion.command_id,
                completion.result,
                reason="late_authority_result",
            )
            self._safe_discard_pending(pending, completion)
            return
        if not self._pending_is_current(pending):
            self._remove_pending(completion.request_id)
            self._remember_tombstone(pending)
            self._safe_discard_pending(pending, completion)
            return
        if (
            pending.cancel_requested
            and completion.error_code == "OK"
            and self._catalog.command_has_sensitive_result(pending.spec)
        ):
            self._remove_pending(completion.request_id)
            self._remember_tombstone(pending)
            self._secret_leases.revoke_result_lease(
                pending.spec.command_id,
                completion.result,
                reason="cancelled_result",
            )
            self._safe_discard_pending(pending, completion)
            return

        normalized, adapter_result_valid = self._normalize_completion(
            pending,
            completion,
        )
        if not adapter_result_valid:
            self._safe_discard_pending(pending, completion)
        self._remove_pending(completion.request_id)

        page_epoch = pending.request.page_epoch
        session_epoch = pending.request.session_epoch
        if (
            pending.spec.command_id is CommandId.C49
            and normalized.error_code
            in {
                "OK",
                "CHANGE_KEY_FAILED_RESTORED",
                "CHANGE_KEY_RECOVERY_FAILED",
                "INTERNAL_FAILURE",
            }
        ):
            normalized, page_epoch, session_epoch = (
                self._finalize_c49_terminal(
                    pending,
                    normalized,
                    original_completion=completion,
                )
            )
        elif normalized.error_code == "OK":
            identity = self._apply_success_identity(
                pending,
                normalized.result,
            )
            if identity is None:
                self._safe_discard_pending(pending, completion)
                normalized = AdapterCompletion(
                    command_id=pending.spec.command_id,
                    request_id=pending.request.request_id,
                    token=pending.request.token,
                    error_code="INTERNAL_FAILURE",
                )
            else:
                page_epoch, session_epoch = identity
                if pending.spec.command_id is CommandId.C79:
                    record_id = str(self._argument_value(
                        pending.spec, pending.request.arguments, "recordId",
                    ))
                    self._secret_leases.revoke_parent(
                        record_id, page_epoch=page_epoch, session_epoch=session_epoch,
                        kind=SecretLeaseKind.REVEAL,
                    )
                try:
                    self._register_secret_result(
                        pending,
                        normalized.result,
                        page_epoch=page_epoch,
                        session_epoch=session_epoch,
                    )
                except SecretLeaseRejected:
                    self._safe_discard_pending(pending, completion)
                    normalized = AdapterCompletion(
                        command_id=pending.spec.command_id,
                        request_id=pending.request.request_id,
                        token=pending.request.token,
                        error_code="INTERNAL_FAILURE",
                    )

        record_field_read_parent = pending.record_field_read_parent
        if (
            normalized.error_code == "OK"
            and normalized.result is not None
            and record_field_read_parent is not None
        ):
            record_field_read_parent = replace(
                record_field_read_parent,
                final_chunk=(
                    record_field_read_parent.kind
                    == SecretLeaseKind.REVEAL.value
                    and normalized.result.get("done") is True
                ),
            )
        envelope = CompletionEnvelope(
            command_id=pending.spec.command_id,
            request_id=pending.request.request_id,
            page_epoch=page_epoch,
            session_epoch=session_epoch,
            error_code=normalized.error_code,
            error_argument_index=normalized.error_argument_index,
            retry_after_ms=normalized.retry_after_ms,
            authority_serial=pending.authority_serial,
            result=deepcopy(normalized.result),
            delivery_deadline=normalized.delivery_deadline,
            record_field_read_parent=record_field_read_parent,
        )
        self._remember_completion(pending, envelope)
        self._completion_sink(envelope)

    def invalidate_page(
        self,
        reason: str = "page_invalidated",
        *,
        _close_adapter: bool = False,
    ) -> bool:
        if reason not in PAGE_BOUNDARY_REASONS:
            raise ValueError("unsupported page security-boundary reason")
        self._non_native_cleanup_complete = False
        old_page = self._active_page_epoch
        old_session = self._active_session_epoch
        if self._page_instance_id is not None:
            self._retired_page_instances[self._page_instance_id] = None
            self._retired_page_instances.move_to_end(
                self._page_instance_id
            )
            while (
                len(self._retired_page_instances)
                > self._catalog.retired_page_instance_cache_items
            ):
                self._retired_page_instances.popitem(last=False)
        self._active_page_epoch = 0
        self._active_session_epoch = 0
        self._authority_serial += 1
        self._page_instance_id = None
        native_cleanup_complete = self._safe_enter_security_boundary(
            reason,
            page_epoch=old_page,
            session_epoch=old_session,
            page_revoked=True,
        )
        lease_cleanup_complete = self._secret_leases.revoke_all(
            reason,
            page_id=str(old_page) if old_page else None,
            session_id=str(old_session) if old_session else None,
        )
        self._drop_all_pending()
        # 原生协调器会在阶段 20 安装不透明遮挡。秘密租约回收、请求取消和
        # adapter 失效都可能同步等待工作线程，因此只能在遮挡就位后执行。
        # 对未接入原生阶段 50 清理的 adapter，仍保留下面的兜底调用。
        adapter_cleanup_complete = True
        if old_session:
            adapter_cleanup_complete = (
                self._safe_invalidate_session(old_session)
                and adapter_cleanup_complete
            )
        if old_page:
            adapter_cleanup_complete = (
                self._safe_invalidate_page(old_page)
                and adapter_cleanup_complete
            )
        if _close_adapter:
            adapter_cleanup_complete = (
                self._safe_close_adapter()
                and adapter_cleanup_complete
            )
        self._non_native_cleanup_complete = bool(lease_cleanup_complete and adapter_cleanup_complete)
        return self._non_native_cleanup_complete and native_cleanup_complete

    def invalidate_session(self, reason: str = "manual_lock") -> bool:
        if reason not in SESSION_BOUNDARY_REASONS:
            raise ValueError("unsupported session security-boundary reason")
        old_session = self._active_session_epoch
        self._active_session_epoch = 0
        self._authority_serial += 1
        native_cleanup_complete = self._safe_enter_security_boundary(
            reason,
            page_epoch=self._active_page_epoch,
            session_epoch=old_session,
            page_revoked=False,
        )
        lease_cleanup_complete = self._secret_leases.revoke_all(
            reason,
            page_id=(
                str(self._active_page_epoch)
                if self._active_page_epoch
                else None
            ),
            session_id=str(old_session) if old_session else None,
        )
        for request_id, pending in tuple(self._pending.items()):
            if (
                pending.request.session_epoch
                or pending.spec.command_id is CommandId.C04
            ):
                self._remove_pending(request_id)
                self._cancel_and_remember(pending)
        adapter_cleanup_complete = (
            self._safe_invalidate_session(old_session)
            if old_session
            else True
        )
        return (
            lease_cleanup_complete
            and adapter_cleanup_complete
            and native_cleanup_complete
        )

    def set_native_session_epoch(self, session_epoch: int) -> None:
        if self._surface is not Surface.NATIVE_QUICKBAR:
            raise RuntimeError("native session setter on Web surface")
        self._catalog.validate_value("SessionEpoch", session_epoch)
        if session_epoch == 0:
            self.invalidate_session()
        else:
            if session_epoch == self._active_session_epoch:
                return
            if self._active_session_epoch != 0:
                raise RuntimeError(
                    "native session transition requires invalidation"
                )
            if session_epoch <= self._last_session_epoch:
                raise ValueRejected("SessionEpoch")
            self._active_session_epoch = session_epoch
            self._last_session_epoch = session_epoch

    def bind_borrowed_web_authority(
        self,
        page_epoch: int,
        session_epoch: int,
    ) -> None:
        """Bind one native-created narrow Web surface to current authority.

        The caller owns the surface lifetime.  This does not authorize a new
        adapter page or session; it only lets a second, reduced QWebChannel
        reuse epochs already validated by the primary Web boundary.
        """

        if self._surface is not Surface.WEBCHANNEL:
            raise RuntimeError("borrowed authority requires a Web surface")
        self._catalog.validate_value("PageEpoch", page_epoch)
        self._catalog.validate_value("SessionEpoch", session_epoch)
        if page_epoch <= 0 or session_epoch <= 0:
            raise ValueRejected("borrowed authority")
        if self._active_page_epoch or self._active_session_epoch:
            raise RuntimeError("borrowed authority is already bound")
        self._active_page_epoch = page_epoch
        self._active_session_epoch = session_epoch
        self._last_page_epoch = page_epoch
        self._last_session_epoch = session_epoch

    def generated_lease_is_authorized(
        self,
        lease_id: str,
        page_epoch: int,
    ) -> bool:
        """Check one delivered C33 lease before a native-only editor transfer."""

        return bool(
            not self._closed
            and page_epoch == self._active_page_epoch
            and self._secret_leases.is_authorized(
                lease_id,
                kind=SecretLeaseKind.GENERATED,
                page_epoch=page_epoch,
                session_epoch=0,
            )
        )

    def adopt_generated_secret_result(
        self,
        result: dict[str, object],
    ) -> bool:
        """Register a native-cloned C33 result on this borrowed Web boundary."""

        if (
            self._closed
            or self._surface is not Surface.WEBCHANNEL
            or self._active_page_epoch <= 0
            or self._active_session_epoch <= 0
        ):
            return False
        try:
            spec = self._catalog.command(CommandId.C33)
            self._catalog.validate_value(spec.result_type, result)
            lease_id = self._secret_leases.register_result(
                CommandId.C33,
                result,
                page_epoch=self._active_page_epoch,
                session_epoch=0,
                parent_lease_id=None,
            )
            return bool(
                lease_id
                and self._secret_leases.mark_result_delivered(
                    CommandId.C33,
                    result,
                    page_epoch=self._active_page_epoch,
                    session_epoch=0,
                )
            )
        except (SecretLeaseRejected, ValueRejected):
            self._secret_leases.revoke_result_lease(
                CommandId.C33,
                result,
                reason="queued_completion_revoked",
            )
            return False

    def close(self, reason: str = "bridge_close") -> bool:
        if reason not in CLOSE_BOUNDARY_REASONS:
            raise ValueError("unsupported close security-boundary reason")
        if self._closed:
            return self._close_cleanup_complete is True
        self._closed = True
        self._close_cleanup_complete = self.invalidate_page(
            reason,
            _close_adapter=True,
        )
        return self._close_cleanup_complete

    def authorize_envelope_delivery(
        self,
        envelope: CompletionEnvelope,
    ) -> bool:
        """Re-check authority immediately before a queued Qt signal emit."""

        authorized = (
            not self._closed
            and envelope.authority_serial == self._authority_serial
        )
        if (
            authorized
            and envelope.delivery_deadline is not None
            and self._clock() >= envelope.delivery_deadline
        ):
            authorized = False
        if (
            authorized
            and envelope.error_code == "OK"
            and not self._secret_leases.result_is_authorized(
                envelope.command_id,
                envelope.result,
                page_epoch=envelope.page_epoch,
                session_epoch=envelope.session_epoch,
            )
        ):
            authorized = False
        parent = envelope.record_field_read_parent
        if authorized and envelope.error_code == "OK" and envelope.command_id in {CommandId.C57, CommandId.C81}:
            try:
                remaining = self._adapter.backup_read_remaining_ms(
                    str(envelope.result["readId"]), envelope.page_epoch, envelope.session_epoch,
                )
                authorized = type(remaining) is int and remaining > 0
                if authorized:
                    envelope.result["expiresInMs"] = min(envelope.result["expiresInMs"], remaining)
            except Exception:
                authorized = False
        if (
            authorized
            and envelope.error_code == "OK"
            and parent is not None
            and not self._record_field_read_parent_is_authorized(
                parent,
                page_epoch=envelope.page_epoch,
                session_epoch=envelope.session_epoch,
            )
        ):
            authorized = False
        completed = self._completed.get(envelope.request_id)
        if (completed is not None and completed.pending_backup_read is not None
                and isinstance(envelope.result, dict)
                and completed.pending_backup_read == (envelope.command_id, envelope.result.get("readId"))):
            self._completed[envelope.request_id] = replace(completed, pending_backup_read=None)
        if authorized:
            return True
        if parent is not None:
            self._secret_leases.release(
                parent.lease_id,
                page_epoch=envelope.page_epoch,
                session_epoch=envelope.session_epoch,
                reason="queued_completion_revoked",
            )
        self._secret_leases.revoke_result_lease(
            envelope.command_id,
            envelope.result,
            reason="queued_completion_revoked",
        )
        if envelope.command_id in {CommandId.C57, CommandId.C60, CommandId.C81}:
            self._safe_discard(
                AdapterCompletion(
                    command_id=envelope.command_id,
                    request_id=envelope.request_id,
                    token=0,
                    error_code=envelope.error_code,
                    result=envelope.result,
                ),
                page_epoch=envelope.page_epoch,
                session_epoch=envelope.session_epoch,
            )
        if isinstance(envelope.result, dict):
            envelope.result.clear()
        return False

    def mark_envelope_delivered(
        self,
        envelope: CompletionEnvelope,
    ) -> bool:
        """Commit a successfully emitted secret result's delivery state."""

        if envelope.error_code != "OK":
            return True
        delivered = self._secret_leases.mark_result_delivered(
            envelope.command_id,
            envelope.result,
            page_epoch=envelope.page_epoch,
            session_epoch=envelope.session_epoch,
        )
        parent = envelope.record_field_read_parent
        if (
            delivered
            and parent is not None
            and parent.final_chunk
            and parent.kind == SecretLeaseKind.REVEAL.value
        ):
            delivered = self._secret_leases.mark_deferred_reveal_delivered(
                parent.lease_id,
                page_epoch=envelope.page_epoch,
                session_epoch=envelope.session_epoch,
                parent_lease_id=parent.record_id,
                binding=(parent.record_id, parent.revision),
            )
        if delivered:
            return True
        self._secret_leases.revoke_result_lease(
            envelope.command_id,
            envelope.result,
            reason="queued_completion_revoked",
        )
        if envelope.command_id is CommandId.C60:
            self._safe_discard(
                AdapterCompletion(
                    command_id=CommandId.C60,
                    request_id=envelope.request_id,
                    token=0,
                    error_code=envelope.error_code,
                    result=envelope.result,
                ),
                page_epoch=envelope.page_epoch,
                session_epoch=envelope.session_epoch,
            )
        if isinstance(envelope.result, dict):
            envelope.result.clear()
        return False

    def _prepare_lease_action(
        self,
        spec: CommandSpec,
        arguments: tuple[object, ...],
        *,
        page_epoch: int,
        session_epoch: int,
    ) -> tuple[str | None, RecordFieldReadParentBinding | None]:
        command_id = spec.command_id
        if command_id is CommandId.C08:
            lease_id = str(
                self._argument_value(spec, arguments, "secretLeaseId")
            )
            self._secret_leases.release(
                lease_id,
                page_epoch=page_epoch,
                session_epoch=self._active_session_epoch,
            )
            return None, None
        if command_id in {CommandId.C15, CommandId.C62}:
            lease_id = str(
                self._argument_value(spec, arguments, "editLeaseId")
            )
            record_id = str(
                self._argument_value(spec, arguments, "recordId")
            )
            revision = str(
                self._argument_value(spec, arguments, "revision")
            )
            if not self._secret_leases.consume(
                lease_id,
                kind=SecretLeaseKind.EDITOR,
                page_epoch=page_epoch,
                session_epoch=session_epoch,
                parent_lease_id=record_id,
                binding=(record_id, revision),
            ):
                return "SECRET_LEASE_EXPIRED", None
            return None, None
        if command_id is CommandId.C60:
            record_id = str(
                self._argument_value(spec, arguments, "recordId")
            )
            revision = str(
                self._argument_value(spec, arguments, "revision")
            )
            field = str(self._argument_value(spec, arguments, "field"))
            lease_id = str(
                self._argument_value(
                    spec,
                    arguments,
                    "authorityLeaseId",
                )
            )
            if not lease_id:
                return (
                    ("SECRET_LEASE_EXPIRED", None)
                    if field == "PASSWORD"
                    else (None, None)
                )
            binding = (record_id, revision)
            if self._secret_leases.is_authorized(
                lease_id,
                kind=SecretLeaseKind.EDITOR,
                page_epoch=page_epoch,
                session_epoch=session_epoch,
                parent_lease_id=record_id,
                binding=binding,
                delivered=False,
            ):
                return (
                    None,
                    RecordFieldReadParentBinding(
                        lease_id=lease_id,
                        kind=SecretLeaseKind.EDITOR.value,
                        record_id=record_id,
                        revision=revision,
                        field=field,
                    ),
                )
            if (
                field == "PASSWORD"
                and self._secret_leases.is_authorized(
                    lease_id,
                    kind=SecretLeaseKind.REVEAL,
                    page_epoch=page_epoch,
                    session_epoch=session_epoch,
                    parent_lease_id=record_id,
                    binding=binding,
                    delivered=False,
                )
            ):
                return (
                    None,
                    RecordFieldReadParentBinding(
                        lease_id=lease_id,
                        kind=SecretLeaseKind.REVEAL.value,
                        record_id=record_id,
                        revision=revision,
                        field=field,
                    ),
                )
            return "SECRET_LEASE_EXPIRED", None
        if command_id is CommandId.C35:
            lease_id = str(
                self._argument_value(spec, arguments, "secretLeaseId")
            )
            if not self._secret_leases.is_authorized(
                lease_id,
                kind=SecretLeaseKind.GENERATED,
                page_epoch=page_epoch,
                session_epoch=0,
            ):
                return "SECRET_LEASE_EXPIRED", None
            return None, None
        if command_id is CommandId.C59:
            parent_lease_id = str(
                self._argument_value(spec, arguments, "previewTicket")
            )
            self._secret_leases.revoke_parent(
                parent_lease_id,
                page_epoch=page_epoch,
                session_epoch=session_epoch,
            )
        return None, None

    def _register_secret_result(
        self,
        pending: _Pending,
        result: dict[str, object] | None,
        *,
        page_epoch: int,
        session_epoch: int,
    ) -> None:
        if result is None:
            return
        parent_lease_id: str | None = None
        binding: tuple[str, ...] = ()
        if pending.spec.command_id in {CommandId.C12, CommandId.C13, CommandId.C77}:
            record_id = str(
                self._argument_value(
                    pending.spec,
                    pending.request.arguments,
                    "recordId",
                )
            )
            revision = str(
                self._argument_value(
                    pending.spec,
                    pending.request.arguments,
                    "revision",
                )
            )
            parent_lease_id = record_id
            binding = (record_id, revision)
            if pending.spec.command_id is CommandId.C77:
                binding += (str(self._argument_value(pending.spec, pending.request.arguments, "codeIndex")),)
        self._secret_leases.register_result(
            pending.spec.command_id,
            result,
            page_epoch=page_epoch,
            session_epoch=session_epoch,
            parent_lease_id=parent_lease_id,
            binding=binding,
            defer_delivery=(
                pending.spec.command_id is CommandId.C13
                and result.get("longFields") == ["PASSWORD"]
            ),
        )

    def _record_field_read_parent_is_authorized(
        self,
        parent: RecordFieldReadParentBinding,
        *,
        page_epoch: int,
        session_epoch: int,
    ) -> bool:
        try:
            kind = SecretLeaseKind(parent.kind)
        except ValueError:
            return False
        if kind is SecretLeaseKind.REVEAL and parent.field != "PASSWORD":
            return False
        return self._secret_leases.is_authorized(
            parent.lease_id,
            kind=kind,
            page_epoch=page_epoch,
            session_epoch=session_epoch,
            parent_lease_id=parent.record_id,
            binding=(parent.record_id, parent.revision),
            delivered=False,
        )

    @staticmethod
    def _argument_value(
        spec: CommandSpec,
        arguments: tuple[object, ...],
        name: str,
    ) -> object:
        for index, argument in enumerate(spec.arguments):
            if argument.name == name:
                return arguments[index]
        raise RuntimeError(
            f"{spec.command_id.value} has no argument named {name}"
        )

    def _identity_error(
        self,
        spec: CommandSpec,
        arguments: tuple[object, ...],
    ) -> str | None:
        if spec.auth == "NONE":
            if spec.command_id is not CommandId.C01:
                return "INVALID_ARGUMENT"
            if self._active_page_epoch != 0:
                return "STALE_PAGE"
            page_instance_id = arguments[1]
            if page_instance_id in self._retired_page_instances:
                return "STALE_PAGE"
            return None
        if spec.auth == "PAGE":
            page_epoch = arguments[1]
            if (
                self._active_page_epoch == 0
                or page_epoch != self._active_page_epoch
            ):
                return "STALE_PAGE"
            return None
        if spec.auth == "SESSION":
            page_epoch = arguments[1]
            session_epoch = arguments[2]
            if (
                self._active_page_epoch == 0
                or page_epoch != self._active_page_epoch
            ):
                return "STALE_PAGE"
            if self._active_session_epoch == 0:
                return "SESSION_REQUIRED"
            if session_epoch != self._active_session_epoch:
                return "STALE_SESSION"
            return None
        if spec.auth == "NATIVE_SESSION":
            session_epoch = arguments[1]
            if self._active_session_epoch == 0:
                return "SESSION_REQUIRED"
            if session_epoch != self._active_session_epoch:
                return "STALE_SESSION"
            return None
        return "INVALID_ARGUMENT"

    @staticmethod
    def _request_identity(
        spec: CommandSpec,
        arguments: tuple[object, ...],
    ) -> tuple[int, int]:
        if spec.auth == "PAGE":
            return int(arguments[1]), 0
        if spec.auth == "SESSION":
            return int(arguments[1]), int(arguments[2])
        if spec.auth == "NATIVE_SESSION":
            return 0, int(arguments[1])
        return 0, 0

    def _pending_is_current(self, pending: _Pending) -> bool:
        auth = pending.spec.auth
        if auth == "NONE":
            return (
                pending.spec.command_id is CommandId.C01
                and self._active_page_epoch == 0
            )
        if auth == "PAGE":
            return pending.request.page_epoch == self._active_page_epoch
        if auth == "SESSION":
            if pending.session_transition:
                return (
                    pending.request.page_epoch
                    == self._active_page_epoch
                    and self._active_session_epoch == 0
                )
            return (
                pending.request.page_epoch == self._active_page_epoch
                and pending.request.session_epoch
                == self._active_session_epoch
            )
        if auth == "NATIVE_SESSION":
            return (
                pending.request.session_epoch
                == self._active_session_epoch
            )
        return False

    def _envelope_is_current(self, envelope: CompletionEnvelope) -> bool:
        if self._surface is Surface.NATIVE_QUICKBAR:
            return (
                envelope.session_epoch != 0
                and envelope.session_epoch == self._active_session_epoch
            )
        return (
            envelope.page_epoch != 0
            and envelope.page_epoch == self._active_page_epoch
            and (
                envelope.session_epoch == 0
                or envelope.session_epoch == self._active_session_epoch
            )
        )

    def _normalize_completion(
        self,
        pending: _Pending,
        completion: AdapterCompletion,
    ) -> tuple[AdapterCompletion, bool]:
        valid = True
        if type(completion.error_code) is not str:
            valid = False
        elif (
            completion.delivery_deadline is not None
            and (
                type(completion.delivery_deadline) is not float
                or not math.isfinite(completion.delivery_deadline)
            )
        ):
            valid = False
        elif completion.error_code == "OK":
            if type(completion.result) is not dict:
                valid = False
            else:
                try:
                    self._catalog.validate_value(
                        pending.spec.result_type,
                        completion.result,
                    )
                except ValueRejected:
                    valid = False
            if (
                completion.error_argument_index != 0
                or completion.retry_after_ms != 0
            ):
                valid = False
        else:
            if completion.error_code not in pending.spec.errors:
                valid = False
            if completion.result is not None:
                valid = False
            try:
                self._catalog.validate_value(
                    "ArgumentIndex",
                    completion.error_argument_index,
                )
                self._catalog.validate_value(
                    "RetryAfterMs",
                    completion.retry_after_ms,
                )
            except ValueRejected:
                valid = False
            if (
                type(completion.error_argument_index) is int
                and completion.error_argument_index
                > len(pending.spec.arguments)
            ):
                valid = False
        if valid:
            return completion, True
        return (
            AdapterCompletion(
                command_id=pending.spec.command_id,
                request_id=pending.request.request_id,
                token=pending.request.token,
                error_code="INTERNAL_FAILURE",
            ),
            False,
        )

    def _finalize_c49_terminal(
        self,
        pending: _Pending,
        completion: AdapterCompletion,
        *,
        original_completion: AdapterCompletion,
    ) -> tuple[AdapterCompletion, int, int]:
        """Revoke C49 authority before exposing one terminal completion."""

        normalized = completion
        if normalized.error_code == "OK" and (
            normalized.result is None
            or normalized.result.get("state") != "LOCKED"
            or normalized.result.get("sessionEpoch") != 0
        ):
            self._safe_discard(original_completion)
            normalized = AdapterCompletion(
                command_id=pending.spec.command_id,
                request_id=pending.request.request_id,
                token=pending.request.token,
                error_code="INTERNAL_FAILURE",
            )

        boundary_reason = (
            "change_key_success"
            if normalized.error_code == "OK"
            else (
                "change_key_restored"
                if normalized.error_code == "CHANGE_KEY_FAILED_RESTORED"
                else "change_key_failed"
            )
        )
        cleanup_complete = self.invalidate_session(boundary_reason)
        pending.authority_serial = self._authority_serial
        if not cleanup_complete and normalized.error_code in {
            "OK",
            "CHANGE_KEY_FAILED_RESTORED",
        }:
            normalized = AdapterCompletion(
                command_id=pending.spec.command_id,
                request_id=pending.request.request_id,
                token=pending.request.token,
                error_code="INTERNAL_FAILURE",
            )

        public_reason = {
            "OK": "CHANGE_KEY_SUCCESS",
            "CHANGE_KEY_FAILED_RESTORED": "CHANGE_KEY_RESTORED",
            "CHANGE_KEY_RECOVERY_FAILED": (
                "CHANGE_KEY_RECOVERY_FAILED"
            ),
        }.get(normalized.error_code)
        state_reason = (
            public_reason
            if cleanup_complete and public_reason is not None
            else C49_INTERNAL_FAILURE_REASON
        )
        self._safe_publish_session_state(
            state="LOCKED",
            reason=state_reason,
        )
        return normalized, self._active_page_epoch, 0

    def _apply_success_identity(
        self,
        pending: _Pending,
        result: dict[str, object] | None,
    ) -> tuple[int, int] | None:
        if result is None:
            return None
        spec = pending.spec
        if spec.command_id is CommandId.C01:
            if (
                result.get("contractVersion") != "1.1.0"
                or result.get("state") != "LOCKED"
                or result.get("sessionEpoch") != 0
            ):
                return None
            page_epoch = int(result["pageEpoch"])
            if page_epoch <= self._last_page_epoch:
                return None
            page_instance_id = str(pending.request.arguments[1])
            self._active_page_epoch = page_epoch
            self._active_session_epoch = 0
            self._last_page_epoch = page_epoch
            self._page_instance_id = page_instance_id
            return page_epoch, 0
        if spec.command_id in {CommandId.C04, CommandId.C05}:
            if result.get("state") != "UNLOCKED":
                return None
            session_epoch = int(result["sessionEpoch"])
            if (
                session_epoch == 0
                or session_epoch <= self._last_session_epoch
            ):
                return None
            self._active_session_epoch = session_epoch
            self._last_session_epoch = session_epoch
            return self._active_page_epoch, session_epoch
        if spec.command_id is CommandId.C06:
            if (
                result.get("state") != "LOCKED"
                or result.get("sessionEpoch") != 0
            ):
                return None
            self._active_session_epoch = 0
            return self._active_page_epoch, 0
        page_epoch = (
            self._active_page_epoch
            if self._surface is Surface.WEBCHANNEL
            else 0
        )
        session_epoch = (
            self._active_session_epoch
            if spec.auth in {"SESSION", "NATIVE_SESSION"}
            else 0
        )
        return page_epoch, session_epoch

    def _complete_cancel_control(self, pending: _Pending) -> None:
        target_request_id = str(pending.request.arguments[2])
        try:
            state = self._cancel_state(pending, target_request_id)
            self._catalog.validate_value("CancelState", state)
            completion = AdapterCompletion(
                command_id=pending.spec.command_id,
                request_id=pending.request.request_id,
                token=pending.request.token,
                error_code="OK",
                result={
                    "targetRequestId": target_request_id,
                    "state": state,
                },
            )
        except Exception:
            completion = AdapterCompletion(
                command_id=pending.spec.command_id,
                request_id=pending.request.request_id,
                token=pending.request.token,
                error_code="INTERNAL_FAILURE",
            )
        self.receive_adapter_completion(completion)

    def _cancel_state(
        self,
        cancel_pending: _Pending,
        target_request_id: str,
    ) -> str:
        if target_request_id == cancel_pending.request.request_id:
            return "NOT_CANCELLABLE"
        target = self._pending.get(target_request_id)
        if target is None:
            completed = self._completed.get(target_request_id)
            if completed is not None:
                if completed.pending_backup_read is not None:
                    command, read_id = completed.pending_backup_read
                    self._adapter.discard(AdapterCompletion(
                        command, target_request_id, 0, "OK", result={"readId": read_id},
                    ))
                    self._completed[target_request_id] = replace(completed, pending_backup_read=None)
                    return "REQUESTED"
                return "TOO_LATE"
            return "NOT_FOUND"
        lifecycle = self._catalog.lifecycle(target.spec.lifecycle)
        if lifecycle.cancel.startswith("not_cancellable"):
            return "NOT_CANCELLABLE"
        if target.cancel_requested:
            return "REQUESTED"
        state = self._adapter.cancel(target.request)
        self._catalog.validate_value("CancelState", state)
        # 同步计算已结束不等于结果已交付，比较读取仍可取消其待交付结果。
        if state == "TOO_LATE" and target.spec.command_id in {CommandId.C57, CommandId.C81}:
            state = "REQUESTED"
        if state == "REQUESTED":
            target.cancel_requested = True
        return state

    def _remember_completion(
        self,
        pending: _Pending,
        envelope: CompletionEnvelope,
    ) -> None:
        replayable = (
            envelope.error_code == "OK"
            and self._catalog.command_can_replay(pending.spec)
        )
        self._completed[pending.request.request_id] = _Completed(
            completed_at=self._clock(),
            fingerprint=pending.fingerprint if replayable else None,
            envelope=(
                self._clone_envelope(envelope) if replayable else None
            ),
            pending_backup_read=(
                (pending.spec.command_id, envelope.result["readId"])
                if envelope.error_code == "OK" and pending.spec.command_id in {CommandId.C57, CommandId.C81}
                else None
            ),
        )
        self._completed.move_to_end(pending.request.request_id)
        self._trim_completed()

    def _remember_tombstone(self, pending: _Pending) -> None:
        self._completed[pending.request.request_id] = _Completed(
            completed_at=self._clock(),
            fingerprint=None,
            envelope=None,
        )
        self._completed.move_to_end(pending.request.request_id)
        self._trim_completed()

    def _prune_completed(self) -> None:
        cutoff = self._clock() - self._catalog.completed_cache_seconds
        for request_id, completed in tuple(self._completed.items()):
            if completed.completed_at >= cutoff:
                break
            self._completed.pop(request_id, None)

    def _trim_completed(self) -> None:
        self._prune_completed()
        while len(self._completed) > self._catalog.completed_cache_items:
            self._completed.popitem(last=False)

    def _fingerprint(
        self,
        spec: CommandSpec,
        arguments: tuple[object, ...],
    ) -> tuple[object, ...] | None:
        if self._catalog.command_has_sensitive_input(spec):
            return None
        return (spec.command_id, *arguments)

    @staticmethod
    def _clone_envelope(
        envelope: CompletionEnvelope,
    ) -> CompletionEnvelope:
        return CompletionEnvelope(
            command_id=envelope.command_id,
            request_id=envelope.request_id,
            page_epoch=envelope.page_epoch,
            session_epoch=envelope.session_epoch,
            error_code=envelope.error_code,
            error_argument_index=envelope.error_argument_index,
            retry_after_ms=envelope.retry_after_ms,
            authority_serial=envelope.authority_serial,
            result=deepcopy(envelope.result),
            delivery_deadline=envelope.delivery_deadline,
            record_field_read_parent=envelope.record_field_read_parent,
        )

    def _remove_pending(self, request_id: str) -> _Pending | None:
        pending = self._pending.pop(request_id, None)
        if pending is not None:
            self._clear_c49_exclusive(pending)
        return pending

    def _clear_c49_exclusive(self, pending: _Pending) -> None:
        if (
            pending.spec.command_id is CommandId.C49
            and self._c49_exclusive_request_id
            == pending.request.request_id
        ):
            self._c49_exclusive_request_id = None

    def _drop_all_pending(self) -> None:
        for pending in tuple(self._pending.values()):
            self._cancel_and_remember(pending)
        self._pending.clear()
        self._c49_exclusive_request_id = None

    def _begin_session_transition(self, transition: _Pending) -> bool:
        old_session = self._active_session_epoch
        transition.session_transition = True
        self._active_session_epoch = 0
        self._authority_serial += 1
        transition.authority_serial = self._authority_serial
        reason = (
            "switch_database"
            if transition.spec.command_id is CommandId.C05
            else "manual_lock"
        )
        native_cleanup_complete = self._safe_enter_security_boundary(
            reason,
            page_epoch=self._active_page_epoch,
            session_epoch=old_session,
            page_revoked=False,
        )
        lease_cleanup_complete = self._secret_leases.revoke_all(
            reason,
            page_id=(
                str(self._active_page_epoch)
                if self._active_page_epoch
                else None
            ),
            session_id=str(old_session) if old_session else None,
        )
        for request_id, pending in tuple(self._pending.items()):
            if (
                pending is not transition
                and pending.request.session_epoch == old_session
            ):
                self._remove_pending(request_id)
                self._cancel_and_remember(pending)
        adapter_cleanup_complete = (
            self._safe_invalidate_session(old_session)
            if old_session
            else True
        )
        return (
            lease_cleanup_complete
            and adapter_cleanup_complete
            and native_cleanup_complete
        )

    def _cancel_and_remember(self, pending: _Pending) -> None:
        self._clear_c49_exclusive(pending)
        try:
            self._adapter.cancel(pending.request)
        except Exception:
            pass
        self._remember_tombstone(pending)

    def _safe_invalidate_page(self, page_epoch: int) -> bool:
        try:
            self._adapter.invalidate_page(page_epoch)
            return True
        except Exception:
            return False

    def _safe_invalidate_session(self, session_epoch: int) -> bool:
        try:
            self._adapter.invalidate_session(session_epoch)
            return True
        except Exception:
            return False

    def _safe_close_adapter(self) -> bool:
        try:
            self._adapter.close()
            return True
        except Exception:
            return False

    def _safe_revoke_secret_lease(self, secret_lease_id: str) -> bool:
        try:
            self._adapter.revoke_secret_lease(secret_lease_id)
            return True
        except Exception:
            return False

    def _safe_enter_security_boundary(
        self,
        reason: str,
        *,
        page_epoch: int,
        session_epoch: int,
        page_revoked: bool,
    ) -> bool:
        try:
            result = self._security_boundary_sink.enter_boundary(
                reason,
                authority_serial=self._authority_serial,
                page_epoch=page_epoch,
                session_epoch=session_epoch,
                page_revoked=page_revoked,
            )
        except Exception:
            return False
        return (
            getattr(result, "authority_revoked", None) is True
            and getattr(result, "complete", None) is True
        )

    def _safe_publish_session_state(
        self,
        *,
        state: str,
        reason: str,
    ) -> bool:
        try:
            self._session_state_sink.session_state_changed(
                authority_serial=self._authority_serial,
                page_epoch=self._active_page_epoch,
                session_epoch=0,
                state=state,
                reason=reason,
            )
            return True
        except Exception:
            return False

    def _safe_discard_pending(
        self,
        pending: _Pending,
        completion: AdapterCompletion,
    ) -> None:
        read_id = ""
        if pending.spec.command_id in {CommandId.C60, CommandId.C63}:
            read_id = str(
                self._argument_value(
                    pending.spec,
                    pending.request.arguments,
                    "readId",
                )
            )
        self._safe_discard(
            completion,
            page_epoch=pending.request.page_epoch,
            session_epoch=pending.request.session_epoch,
            read_id=read_id,
        )

    def _safe_discard(
        self,
        completion: AdapterCompletion,
        *,
        page_epoch: int | None = None,
        session_epoch: int | None = None,
        read_id: str = "",
    ) -> None:
        discarded = completion
        if (
            completion.command_id in {CommandId.C60, CommandId.C63}
            and type(page_epoch) is int
            and type(session_epoch) is int
        ):
            result = completion.result
            if not isinstance(result, dict):
                result = {}
                discarded = AdapterCompletion(
                    command_id=completion.command_id,
                    request_id=completion.request_id,
                    token=completion.token,
                    error_code=completion.error_code,
                    error_argument_index=completion.error_argument_index,
                    retry_after_ms=completion.retry_after_ms,
                    result=result,
                    delivery_deadline=completion.delivery_deadline,
                )
            if not result.get("readId") and read_id:
                result["readId"] = read_id
            result["_discardPageEpoch"] = page_epoch
            result["_discardSessionEpoch"] = session_epoch
        try:
            self._adapter.discard(discarded)
        except Exception:
            pass

    @staticmethod
    def _accept() -> SubmitAck:
        return SubmitAck(
            accepted=True,
            error_code="OK",
            error_argument_index=0,
        )

    @staticmethod
    def _reject(error_code: str, index: int) -> SubmitAck:
        return SubmitAck(
            accepted=False,
            error_code=error_code,
            error_argument_index=index,
        )
