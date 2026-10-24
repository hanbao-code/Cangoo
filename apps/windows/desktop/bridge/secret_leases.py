"""Native metadata authority for bounded Bridge secret leases.

The registry never stores a raw password or TOTP seed.  It mirrors only the
opaque lease identifier, its authority generations, parent capability, kind,
and delivery/lease lifetime metadata so the Bridge can fail closed before
calling an adapter or emitting a queued completion.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import time
from typing import Callable, Mapping

from .command_ids import CommandId
from .protocol import NullSecretLifecycleSink, SecretLifecycleSink


class SecretLeaseRejected(ValueError):
    """A lease result or capability is outside the bounded authority."""


class SecretLeaseKind(str, Enum):
    EDITOR = "editor"
    REVEAL = "reveal"
    GENERATED = "generated"
    CONFLICT_REVEAL = "conflict_reveal"


@dataclass(frozen=True, slots=True)
class SecretLease:
    """Non-secret lease metadata retained by the native boundary."""

    lease_id: str
    kind: SecretLeaseKind
    command_id: CommandId
    page_epoch: int
    session_epoch: int
    parent_lease_id: str | None
    binding: tuple[str, ...]
    expires_at: float | None
    delivered: bool
    defer_delivery: bool


@dataclass(frozen=True, slots=True)
class SecretLeaseRule:
    kind: SecretLeaseKind
    result_field: str
    ttl_ms: int
    retain_after_delivery: bool = False


class SecretLeaseRegistry:
    """Bounded, synchronous authority for all secret-bearing results."""

    MAX_ACTIVE_ITEMS = 64

    def __init__(
        self,
        rules: Mapping[CommandId, SecretLeaseRule],
        revoke_adapter_lease: Callable[[str], bool],
        *,
        lifecycle_sink: SecretLifecycleSink | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._rules = dict(rules)
        self._revoke_adapter_lease = revoke_adapter_lease
        self._lifecycle_sink = (
            lifecycle_sink or NullSecretLifecycleSink()
        )
        self._clock = clock
        self._leases: dict[str, SecretLease] = {}

    @property
    def active_count(self) -> int:
        self._prune_expired()
        return len(self._leases)

    def active_metadata(self) -> tuple[SecretLease, ...]:
        """Return an immutable, raw-secret-free diagnostic snapshot."""

        self._prune_expired()
        return tuple(self._leases.values())

    def rule(self, command_id: CommandId) -> SecretLeaseRule | None:
        return self._rules.get(command_id)

    def register_result(
        self,
        command_id: CommandId,
        result: dict[str, object],
        *,
        page_epoch: int,
        session_epoch: int,
        parent_lease_id: str | None,
        binding: tuple[str, ...] = (),
        defer_delivery: bool = False,
    ) -> str | None:
        """Validate and register secret-result metadata.

        ``None`` means the command is not a secret-lease producer.  A producer
        must return a unique opaque identifier and a positive TTL no greater
        than its command-specific contract limit.
        """

        rule = self._rules.get(command_id)
        if rule is None:
            return None
        lease_id = result.get(rule.result_field)
        expires_in_ms = result.get("expiresInMs")
        if (
            type(lease_id) is not str
            or type(expires_in_ms) is not int
            or expires_in_ms <= 0
            or expires_in_ms > rule.ttl_ms
            or page_epoch <= 0
            or (rule.kind is not SecretLeaseKind.GENERATED
                and session_epoch <= 0)
            or (defer_delivery and rule.kind is not SecretLeaseKind.REVEAL)
        ):
            if type(lease_id) is str:
                self._safe_revoke_adapter(lease_id)
            raise SecretLeaseRejected(command_id.value)

        self._prune_expired()
        if lease_id in self._leases:
            self._revoke_ids(
                (lease_id,),
                reason="duplicate_lease_id",
                page_id=str(page_epoch),
                session_id=(
                    str(session_epoch) if session_epoch else None
                ),
                parent_lease_id=parent_lease_id,
            )
            raise SecretLeaseRejected(command_id.value)
        if len(self._leases) >= self.MAX_ACTIVE_ITEMS:
            self._safe_revoke_adapter(lease_id)
            raise SecretLeaseRejected(command_id.value)

        self._leases[lease_id] = SecretLease(
            lease_id=lease_id,
            kind=rule.kind,
            command_id=command_id,
            page_epoch=page_epoch,
            session_epoch=session_epoch,
            parent_lease_id=parent_lease_id,
            binding=binding,
            expires_at=self._clock() + expires_in_ms / 1000.0,
            delivered=False,
            defer_delivery=defer_delivery,
        )
        return lease_id

    def mark_result_delivered(
        self,
        command_id: CommandId,
        result: object,
        *,
        page_epoch: int,
        session_epoch: int,
    ) -> bool:
        """Transition a successfully emitted C13 result to display authority.

        For an ordinary secret lease, ``expiresInMs`` remains the lease TTL.
        C13 is different: its 30-second bound is the one-time native-to-renderer
        delivery deadline.  Once the authorized completion has synchronously
        emitted, the same opaque ID represents the current display location
        until C08, a record/view/revision transition, or a security boundary.
        """

        rule = self._rules.get(command_id)
        if rule is None or not rule.retain_after_delivery:
            return True
        if type(result) is not dict:
            return False
        lease_id = result.get(rule.result_field)
        if type(lease_id) is not str:
            return False
        lease = self._leases.get(lease_id)
        if (
            lease is None
            or lease.command_id is not command_id
            or lease.page_epoch != page_epoch
            or lease.session_epoch != session_epoch
            or lease.delivered
        ):
            return False
        if lease.defer_delivery:
            return True
        self._leases[lease_id] = SecretLease(
            lease_id=lease.lease_id,
            kind=lease.kind,
            command_id=lease.command_id,
            page_epoch=lease.page_epoch,
            session_epoch=lease.session_epoch,
            parent_lease_id=lease.parent_lease_id,
            binding=lease.binding,
            expires_at=None,
            delivered=True,
            defer_delivery=False,
        )
        return True

    def mark_deferred_reveal_delivered(
        self,
        lease_id: str,
        *,
        page_epoch: int,
        session_epoch: int,
        parent_lease_id: str,
        binding: tuple[str, ...],
    ) -> bool:
        """仅在最后一段长密码合法交付后转为当前位置显示授权。"""

        self._prune_expired()
        lease = self._leases.get(lease_id)
        if (
            lease is None
            or lease.kind is not SecretLeaseKind.REVEAL
            or not lease.defer_delivery
            or lease.delivered
            or lease.page_epoch != page_epoch
            or lease.session_epoch != session_epoch
            or lease.parent_lease_id != parent_lease_id
            or lease.binding != binding
        ):
            return False
        self._leases[lease_id] = SecretLease(
            lease_id=lease.lease_id,
            kind=lease.kind,
            command_id=lease.command_id,
            page_epoch=lease.page_epoch,
            session_epoch=lease.session_epoch,
            parent_lease_id=lease.parent_lease_id,
            binding=lease.binding,
            expires_at=None,
            delivered=True,
            defer_delivery=False,
        )
        return True

    def is_authorized(
        self,
        lease_id: str,
        *,
        kind: SecretLeaseKind,
        page_epoch: int,
        session_epoch: int,
        parent_lease_id: str | None = None,
        binding: tuple[str, ...] | None = None,
        delivered: bool | None = None,
    ) -> bool:
        self._prune_expired()
        lease = self._leases.get(lease_id)
        return (
            lease is not None
            and lease.kind is kind
            and lease.page_epoch == page_epoch
            and lease.session_epoch == session_epoch
            and (
                parent_lease_id is None
                or lease.parent_lease_id == parent_lease_id
            )
            and (binding is None or lease.binding == binding)
            and (delivered is None or lease.delivered is delivered)
        )

    def release(
        self,
        lease_id: str,
        *,
        page_epoch: int,
        session_epoch: int,
        reason: str = "lease_released",
    ) -> bool:
        """Idempotently revoke a lease owned by the current page/session."""

        self._prune_expired()
        lease = self._leases.get(lease_id)
        if lease is None or lease.page_epoch != page_epoch:
            return False
        if lease.session_epoch not in {0, session_epoch}:
            return False
        self._revoke_ids(
            (lease_id,),
            reason=reason,
            page_id=str(page_epoch),
            session_id=(
                str(lease.session_epoch) if lease.session_epoch else None
            ),
            parent_lease_id=lease.parent_lease_id,
        )
        return True

    def consume(
        self,
        lease_id: str,
        *,
        kind: SecretLeaseKind,
        page_epoch: int,
        session_epoch: int,
        parent_lease_id: str | None = None,
        binding: tuple[str, ...] | None = None,
    ) -> bool:
        """Atomically validate and revoke one single-use capability."""

        if not self.is_authorized(
            lease_id,
            kind=kind,
            page_epoch=page_epoch,
            session_epoch=session_epoch,
            parent_lease_id=parent_lease_id,
            binding=binding,
        ):
            return False
        lease = self._leases[lease_id]
        self._revoke_ids(
            (lease_id,),
            reason="lease_consumed",
            page_id=str(page_epoch),
            session_id=str(session_epoch) if session_epoch else None,
            parent_lease_id=lease.parent_lease_id,
        )
        return True

    def revoke_parent(
        self,
        parent_lease_id: str,
        *,
        page_epoch: int,
        session_epoch: int,
        reason: str = "parent_released",
        kind: SecretLeaseKind | None = None,
    ) -> int:
        """撤销父记录的指定用途租约；缺省撤销全部。"""

        self._prune_expired()
        lease_ids = tuple(
            lease.lease_id
            for lease in self._leases.values()
            if lease.parent_lease_id == parent_lease_id
            and lease.page_epoch == page_epoch
            and lease.session_epoch == session_epoch
            and (kind is None or lease.kind is kind)
        )
        self._revoke_ids(
            lease_ids,
            reason=reason,
            page_id=str(page_epoch),
            session_id=str(session_epoch) if session_epoch else None,
            parent_lease_id=parent_lease_id,
        )
        return len(lease_ids)

    def revoke_all(
        self,
        reason: str,
        *,
        page_id: str | None,
        session_id: str | None,
    ) -> bool:
        """Synchronously revoke every active lease."""

        lease_ids = tuple(self._leases)
        return self._revoke_ids(
            lease_ids,
            reason=reason,
            page_id=page_id,
            session_id=session_id,
            parent_lease_id=None,
            notify_when_empty=True,
        )

    def revoke_result_lease(
        self,
        command_id: CommandId,
        result: object,
        *,
        reason: str,
    ) -> None:
        """Fail-closed cleanup for a result that must not be delivered."""

        rule = self._rules.get(command_id)
        if rule is None or type(result) is not dict:
            return
        lease_id = result.get(rule.result_field)
        if type(lease_id) is not str:
            return
        lease = self._leases.get(lease_id)
        if lease is None:
            self._safe_revoke_adapter(lease_id)
            return
        self._revoke_ids(
            (lease_id,),
            reason=reason,
            page_id=str(lease.page_epoch),
            session_id=(
                str(lease.session_epoch) if lease.session_epoch else None
            ),
            parent_lease_id=lease.parent_lease_id,
        )

    def result_is_authorized(
        self,
        command_id: CommandId,
        result: object,
        *,
        page_epoch: int,
        session_epoch: int,
    ) -> bool:
        """Re-check a queued secret result immediately before Qt emission."""

        rule = self._rules.get(command_id)
        if rule is None:
            return True
        if type(result) is not dict:
            return False
        lease_id = result.get(rule.result_field)
        if type(lease_id) is not str:
            return False
        self._prune_expired()
        lease = self._leases.get(lease_id)
        return (
            lease is not None
            and lease.command_id is command_id
            and lease.page_epoch == page_epoch
            and lease.session_epoch == session_epoch
        )

    def _prune_expired(self) -> None:
        now = self._clock()
        for lease in tuple(self._leases.values()):
            if lease.expires_at is not None and lease.expires_at <= now:
                self._revoke_ids(
                    (lease.lease_id,),
                    reason="expired",
                    page_id=str(lease.page_epoch),
                    session_id=(
                        str(lease.session_epoch)
                        if lease.session_epoch
                        else None
                    ),
                    parent_lease_id=lease.parent_lease_id,
                )

    def _revoke_ids(
        self,
        lease_ids: tuple[str, ...],
        *,
        reason: str,
        page_id: str | None,
        session_id: str | None,
        parent_lease_id: str | None,
        notify_when_empty: bool = False,
    ) -> bool:
        revoked: list[str] = []
        for lease_id in lease_ids:
            if self._leases.pop(lease_id, None) is not None:
                revoked.append(lease_id)
        adapter_cleanup_complete = True
        for lease_id in revoked:
            if not self._safe_revoke_adapter(lease_id):
                adapter_cleanup_complete = False
        if revoked or notify_when_empty:
            try:
                self._lifecycle_sink.revoke_secret_leases(
                    reason,
                    lease_ids=tuple(revoked),
                    page_id=page_id,
                    session_id=session_id,
                    parent_lease_id=parent_lease_id,
                )
            except Exception:
                pass
        return adapter_cleanup_complete

    def _safe_revoke_adapter(self, lease_id: str) -> bool:
        try:
            return self._revoke_adapter_lease(lease_id) is True
        except Exception:
            return False
