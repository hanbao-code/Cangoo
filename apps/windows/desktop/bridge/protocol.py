"""Typed adapter protocol for the isolated M3.3 Bridge boundary.

The renderer never supplies a command identifier.  Explicit Bridge methods
select a :class:`CommandId`, and only that enum value reaches an adapter.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Protocol

from .command_ids import CommandId


@dataclass(frozen=True, slots=True)
class AdapterRequest:
    """One validated request passed from the boundary to an adapter."""

    command_id: CommandId
    request_id: str
    token: int
    page_epoch: int
    session_epoch: int
    argument_names: tuple[str, ...]
    arguments: tuple[object, ...] = field(repr=False)


@dataclass(frozen=True, slots=True)
class AdapterCompletion:
    """A bounded adapter completion with no free-form backend message."""

    command_id: CommandId
    request_id: str
    token: int
    error_code: str
    error_argument_index: int = 0
    retry_after_ms: int = 0
    result: dict[str, object] | None = field(default=None, repr=False)
    delivery_deadline: float | None = field(default=None, repr=False)


@dataclass(frozen=True, slots=True)
class RecordFieldReadParentBinding:
    """保留至 Qt 信号实际发射的 C60 私有父授权元数据。"""

    lease_id: str
    kind: str
    record_id: str
    revision: str
    field: str
    final_chunk: bool = False


@dataclass(frozen=True, slots=True)
class CompletionEnvelope:
    """Validated values emitted by one method-specific completion signal."""

    command_id: CommandId
    request_id: str
    page_epoch: int
    session_epoch: int
    error_code: str
    error_argument_index: int
    retry_after_ms: int
    authority_serial: int
    result: dict[str, object] | None = field(default=None, repr=False)
    delivery_deadline: float | None = field(default=None, repr=False)
    record_field_read_parent: RecordFieldReadParentBinding | None = field(
        default=None,
        repr=False,
    )


CompletionCallback = Callable[[AdapterCompletion], None]
C49_INTERNAL_FAILURE_REASON = "C49_INTERNAL_FAILURE"


class BridgeAdapter(Protocol):
    """Typed application-port protocol; M3 supplies only memory fakes."""

    def submit(
        self,
        request: AdapterRequest,
        complete: CompletionCallback,
    ) -> None:
        """Start one already validated enum-selected request."""

    def cancel(self, request: AdapterRequest) -> str:
        """Return one frozen ``CancelState`` value for a pending request."""

    def backup_read_remaining_ms(self, read_id: str, page_epoch: int, session_epoch: int) -> int:
        """只在原比较查看仍有效时返回未延长的剩余交付期限。"""

    def invalidate_page(self, page_epoch: int) -> None:
        """Revoke adapter work owned by a renderer page."""

    def invalidate_session(self, session_epoch: int) -> None:
        """Revoke adapter work owned by an unlocked session."""

    def revoke_secret_lease(self, secret_lease_id: str) -> None:
        """Synchronously destroy one adapter-owned secret lease."""

    def discard(self, completion: AdapterCompletion) -> None:
        """Destroy a rejected or late adapter result, including secrets."""

    def close(self) -> None:
        """Stop accepting work and release adapter-owned state."""


class SecretLifecycleSink(Protocol):
    """Metadata-only observer for bounded secret-lease revocation."""

    def revoke_secret_leases(
        self,
        reason: str,
        *,
        lease_ids: tuple[str, ...],
        page_id: str | None = None,
        session_id: str | None = None,
        parent_lease_id: str | None = None,
    ) -> None:
        """Observe a synchronous revocation without receiving raw secrets."""


class NullSecretLifecycleSink:
    """Backward-compatible no-op secret lifecycle observer."""

    def revoke_secret_leases(
        self,
        reason: str,
        *,
        lease_ids: tuple[str, ...],
        page_id: str | None = None,
        session_id: str | None = None,
        parent_lease_id: str | None = None,
    ) -> None:
        del reason, lease_ids, page_id, session_id, parent_lease_id


@dataclass(frozen=True, slots=True)
class SecurityBoundaryOutcome:
    """Minimal result required before a Bridge transition may continue."""

    authority_revoked: bool
    complete: bool


class SecurityBoundarySink(Protocol):
    """Host cleanup hook entered only after Bridge authority is revoked."""

    def enter_boundary(
        self,
        reason: str,
        *,
        authority_serial: int,
        page_epoch: int,
        session_epoch: int,
        page_revoked: bool,
    ) -> SecurityBoundaryOutcome:
        """Synchronously run native cleanup for one security boundary."""


class NullSecurityBoundarySink:
    """Fail-closed placeholder when no native coordinator is attached."""

    def enter_boundary(
        self,
        reason: str,
        *,
        authority_serial: int,
        page_epoch: int,
        session_epoch: int,
        page_revoked: bool,
    ) -> SecurityBoundaryOutcome:
        del (
            reason,
            authority_serial,
            page_epoch,
            session_epoch,
            page_revoked,
        )
        return SecurityBoundaryOutcome(
            authority_revoked=True,
            complete=False,
        )


class SessionStateSink(Protocol):
    """Receive bounded session state after a C49 authority transition.

    ``C49_INTERNAL_FAILURE`` is a native-only curtain reason and must never
    be forwarded to the renderer as an S01 ``SessionReason`` value.
    """

    def session_state_changed(
        self,
        *,
        authority_serial: int,
        page_epoch: int,
        session_epoch: int,
        state: str,
        reason: str,
    ) -> None:
        """Publish bounded state metadata without receiving a secret."""


class NullSessionStateSink:
    """Backward-compatible no-op session-state observer."""

    def session_state_changed(
        self,
        *,
        authority_serial: int,
        page_epoch: int,
        session_epoch: int,
        state: str,
        reason: str,
    ) -> None:
        del authority_serial, page_epoch, session_epoch, state, reason
