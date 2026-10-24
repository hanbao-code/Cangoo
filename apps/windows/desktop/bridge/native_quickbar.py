"""Typed native QuickBar port that is never registered on QWebChannel."""

from __future__ import annotations

from typing import Callable

from .command_ids import CommandId
from .contract_catalog import ContractCatalog
from .protocol import (
    BridgeAdapter,
    CompletionEnvelope,
    SecretLifecycleSink,
    SecurityBoundarySink,
)
from .request_boundary import RequestBoundary, Surface


class NativeQuickbarPort:
    """Four explicit native methods backed by the same bounded validator."""

    def __init__(
        self,
        catalog: ContractCatalog,
        adapter: BridgeAdapter,
        completion_sink: Callable[[CompletionEnvelope], None],
        *,
        adapter_completion_receiver: Callable[[object], None] | None = None,
        secret_lifecycle_sink: SecretLifecycleSink | None = None,
        security_boundary_sink: SecurityBoundarySink | None = None,
    ) -> None:
        self._boundary = RequestBoundary(
            catalog,
            adapter,
            Surface.NATIVE_QUICKBAR,
            completion_sink,
            adapter_completion_receiver=adapter_completion_receiver,
            secret_lifecycle_sink=secret_lifecycle_sink,
            security_boundary_sink=security_boundary_sink,
        )

    def set_session_epoch(self, session_epoch: int) -> None:
        self._boundary.set_native_session_epoch(session_epoch)

    @property
    def pending_count(self) -> int:
        return self._boundary.pending_count

    def receive_adapter_completion(self, completion: object) -> None:
        self._boundary.receive_adapter_completion(completion)

    def mark_envelope_delivered(self, envelope: CompletionEnvelope) -> None:
        self._boundary.mark_envelope_delivered(envelope)

    def invalidate_session(self, reason: str = "manual_lock") -> bool:
        return self._boundary.invalidate_session(reason)

    def close(self, reason: str = "bridge_close") -> bool:
        return self._boundary.close(reason)

    def quickbarSearchV1(
        self,
        requestId: str,
        sessionEpoch: int,
        query: str,
        limit: int,
    ) -> dict[str, object]:
        return self._boundary.submit(
            CommandId.N01,
            (requestId, sessionEpoch, query, limit),
        ).to_wire()

    def quickbarCopyAccountV1(
        self,
        requestId: str,
        sessionEpoch: int,
        recordId: int,
        revision: str,
    ) -> dict[str, object]:
        return self._boundary.submit(
            CommandId.N02,
            (requestId, sessionEpoch, recordId, revision),
        ).to_wire()

    def quickbarCopyPasswordV1(
        self,
        requestId: str,
        sessionEpoch: int,
        recordId: int,
        revision: str,
    ) -> dict[str, object]:
        return self._boundary.submit(
            CommandId.N03,
            (requestId, sessionEpoch, recordId, revision),
        ).to_wire()

    def quickbarGenerateAndCopyV1(
        self,
        requestId: str,
        sessionEpoch: int,
        length: int,
    ) -> dict[str, object]:
        return self._boundary.submit(
            CommandId.N04,
            (requestId, sessionEpoch, length),
        ).to_wire()
