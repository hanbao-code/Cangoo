"""Qt-only base for the generated explicit WebChannel surface."""

from __future__ import annotations

from typing import Callable

from PySide6.QtCore import QObject, Qt, Signal, Slot

from .command_ids import CommandId
from .contract_catalog import ContractCatalog
from .protocol import (
    AdapterCompletion,
    BridgeAdapter,
    CompletionEnvelope,
    SecretLifecycleSink,
    SecurityBoundarySink,
    SessionStateSink,
)
from .request_boundary import RequestBoundary, Surface


AccessibleRejectionSink = Callable[[CommandId, int, int, str], None]


class _CompletionRelay(QObject):
    """Private completion relay; this object is never registered."""

    completion_ready = Signal(object)

    def __init__(
        self,
        completion_sink: Callable[[object], None],
        parent: QObject,
    ) -> None:
        super().__init__(parent)
        self._completion_sink = completion_sink
        self.completion_ready.connect(
            self._forward_completion,
            Qt.ConnectionType.QueuedConnection,
        )

    @Slot(object)
    def _forward_completion(self, envelope: object) -> None:
        self._completion_sink(envelope)


class _BridgeLifetimeGuard(QObject):
    """Keep the fail-closed adapter callback alive after Bridge deletion."""

    adapter_completion = Signal(object)

    def __init__(self) -> None:
        super().__init__()
        self._boundary: RequestBoundary | None = None
        self.adapter_completion.connect(
            self._forward_adapter_completion,
            Qt.ConnectionType.QueuedConnection,
        )

    def bind_boundary(self, boundary: RequestBoundary) -> None:
        if self._boundary is not None:
            raise RuntimeError("Bridge lifetime guard already bound")
        self._boundary = boundary

    def queue_adapter_completion(
        self,
        completion: AdapterCompletion,
    ) -> None:
        self.adapter_completion.emit(completion)

    @Slot(object)
    def _forward_adapter_completion(self, completion: object) -> None:
        boundary = self._boundary
        if boundary is not None:
            boundary.receive_adapter_completion(completion)

    @Slot()
    def close_boundary(self) -> None:
        boundary = self._boundary
        if boundary is not None:
            boundary.close("bridge_destroyed")


class PdmBridgeBase(QObject):
    """Shared request machinery without any renderer-callable generic slot."""

    def __init__(
        self,
        catalog: ContractCatalog,
        adapter: BridgeAdapter,
        parent: QObject | None = None,
        *,
        secret_lifecycle_sink: SecretLifecycleSink | None = None,
        security_boundary_sink: SecurityBoundarySink | None = None,
        session_state_sink: SessionStateSink | None = None,
        accessible_rejection_sink: AccessibleRejectionSink | None = None,
        request_admission: (
            Callable[[CommandId, tuple[object, ...]], str | None] | None
        ) = None,
    ) -> None:
        super().__init__(parent)
        self._completion_relay = _CompletionRelay(
            self._deliver_completion,
            self,
        )
        self._lifetime_guard = _BridgeLifetimeGuard()
        self._boundary = RequestBoundary(
            catalog,
            adapter,
            Surface.WEBCHANNEL,
            self._queue_completion,
            adapter_completion_receiver=(
                self._lifetime_guard.queue_adapter_completion
            ),
            secret_lifecycle_sink=secret_lifecycle_sink,
            security_boundary_sink=security_boundary_sink,
            session_state_sink=session_state_sink,
            request_admission=request_admission,
        )
        self._lifetime_guard.bind_boundary(self._boundary)
        self._accessible_rejection_sink = accessible_rejection_sink
        self.destroyed.connect(self._lifetime_guard.close_boundary)

    @property
    def non_native_cleanup_complete(self) -> bool:
        return self._boundary.non_native_cleanup_complete

    @property
    def active_page_epoch(self) -> int:
        return self._boundary.active_page_epoch

    @property
    def active_session_epoch(self) -> int:
        return self._boundary.active_session_epoch

    @property
    def pending_count(self) -> int:
        return self._boundary.pending_count

    @property
    def active_secret_lease_count(self) -> int:
        return self._boundary.active_secret_lease_count

    def generated_lease_is_authorized(
        self,
        lease_id: str,
        page_epoch: int,
    ) -> bool:
        """Host-only check for an editor prefill transfer."""

        return self._boundary.generated_lease_is_authorized(
            lease_id,
            page_epoch,
        )

    @property
    def pending_change_key_token(self) -> int | None:
        """返回仅供宿主使用的 C49 token；它不是 Qt 槽或 Qt 属性。"""

        return self._boundary.pending_change_key_token

    def invalidate_page(self, reason: str = "page_invalidated") -> bool:
        """Host-only page revocation; not a Qt slot."""

        return self._boundary.invalidate_page(reason)

    def invalidate_session(self, reason: str = "manual_lock") -> bool:
        """Host-only session revocation; not a Qt slot."""

        return self._boundary.invalidate_session(reason)

    def close_bridge(self, reason: str = "bridge_close") -> bool:
        """Host-only idempotent shutdown; not a Qt slot."""

        return self._boundary.close(reason)

    def _submit_explicit(
        self,
        command_id: CommandId,
        arguments: tuple[object, ...],
    ) -> dict[str, object]:
        ack = self._boundary.submit(command_id, arguments)
        if (
            command_id is CommandId.C35
            and not ack.accepted
            and ack.error_code == "SECRET_LEASE_EXPIRED"
            and self._accessible_rejection_sink is not None
        ):
            try:
                self._accessible_rejection_sink(
                    command_id,
                    int(arguments[1]),
                    0,
                    ack.error_code,
                )
            except Exception:
                pass
        return ack.to_wire()

    def _queue_completion(self, envelope: CompletionEnvelope) -> None:
        self._completion_relay.completion_ready.emit(envelope)

    def _deliver_completion(self, envelope: object) -> None:
        if (
            isinstance(envelope, CompletionEnvelope)
            and self._boundary.authorize_envelope_delivery(envelope)
        ):
            self._emit_completion(envelope.command_id, envelope)
            self._boundary.mark_envelope_delivered(envelope)

    def _emit_completion(
        self,
        command_id: CommandId,
        envelope: CompletionEnvelope,
    ) -> None:
        raise NotImplementedError
