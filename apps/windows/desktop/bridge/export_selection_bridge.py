"""由 tools/generate_bridge_surface.py 生成；请修改合同来源。"""

from __future__ import annotations

from PySide6.QtCore import Signal, Slot

from .command_ids import CommandId
from .protocol import CompletionEnvelope
from .web_bridge_base import PdmBridgeBase


class ExportSelectionBridgeSurface(PdmBridgeBase):
    """精确的 Bridge v1.1（通信接口）白名单，不提供通用渲染器调用槽。"""

    cancelRequestCompletedV1 = Signal(str, int, int, str, int, int, "QVariant")
    beginExportSelectionCompletedV1 = Signal(str, int, int, str, int, int, "QVariant")
    listExportSelectionCompletedV1 = Signal(str, int, int, str, int, int, "QVariant")
    changeExportSelectionCompletedV1 = Signal(str, int, int, str, int, int, "QVariant")
    finishExportSelectionCompletedV1 = Signal(str, int, int, str, int, int, "QVariant")


    def _emit_completion(
        self,
        command_id: CommandId,
        envelope: CompletionEnvelope,
    ) -> None:
        values = (
            envelope.request_id,
            envelope.page_epoch,
            envelope.session_epoch,
            envelope.error_code,
            envelope.error_argument_index,
            envelope.retry_after_ms,
            envelope.result,
        )
        if command_id is CommandId.C07:
            self.cancelRequestCompletedV1.emit(*values)
        elif command_id is CommandId.C87:
            self.beginExportSelectionCompletedV1.emit(*values)
        elif command_id is CommandId.C88:
            self.listExportSelectionCompletedV1.emit(*values)
        elif command_id is CommandId.C89:
            self.changeExportSelectionCompletedV1.emit(*values)
        elif command_id is CommandId.C90:
            self.finishExportSelectionCompletedV1.emit(*values)
        else:
            raise RuntimeError("unknown frozen command")

    @Slot(
        "QVariant",
        "QVariant",
        "QVariant",
        result="QVariantMap",
    )
    def cancelRequestV1(
        self,
        requestId: object,
        pageEpoch: object,
        targetRequestId: object,
    ) -> dict[str, object]:
        return self._submit_explicit(
            CommandId.C07,
            (
                requestId,
                pageEpoch,
                targetRequestId,
            ),
        )

    @Slot(
        "QVariant",
        "QVariant",
        "QVariant",
        result="QVariantMap",
    )
    def beginExportSelectionV1(
        self,
        requestId: object,
        pageEpoch: object,
        sessionEpoch: object,
    ) -> dict[str, object]:
        return self._submit_explicit(
            CommandId.C87,
            (
                requestId,
                pageEpoch,
                sessionEpoch,
            ),
        )

    @Slot(
        "QVariant",
        "QVariant",
        "QVariant",
        "QVariant",
        "QVariant",
        "QVariant",
        "QVariant",
        "QVariant",
        result="QVariantMap",
    )
    def listExportSelectionV1(
        self,
        requestId: object,
        pageEpoch: object,
        sessionEpoch: object,
        selectionTicket: object,
        query: object,
        kind: object,
        offset: object,
        limit: object,
    ) -> dict[str, object]:
        return self._submit_explicit(
            CommandId.C88,
            (
                requestId,
                pageEpoch,
                sessionEpoch,
                selectionTicket,
                query,
                kind,
                offset,
                limit,
            ),
        )

    @Slot(
        "QVariant",
        "QVariant",
        "QVariant",
        "QVariant",
        "QVariant",
        "QVariant",
        "QVariant",
        "QVariant",
        result="QVariantMap",
    )
    def changeExportSelectionV1(
        self,
        requestId: object,
        pageEpoch: object,
        sessionEpoch: object,
        selectionTicket: object,
        action: object,
        kind: object,
        recordId: object,
        revision: object,
    ) -> dict[str, object]:
        return self._submit_explicit(
            CommandId.C89,
            (
                requestId,
                pageEpoch,
                sessionEpoch,
                selectionTicket,
                action,
                kind,
                recordId,
                revision,
            ),
        )

    @Slot(
        "QVariant",
        "QVariant",
        "QVariant",
        "QVariant",
        "QVariant",
        result="QVariantMap",
    )
    def finishExportSelectionV1(
        self,
        requestId: object,
        pageEpoch: object,
        sessionEpoch: object,
        selectionTicket: object,
        action: object,
    ) -> dict[str, object]:
        return self._submit_explicit(
            CommandId.C90,
            (
                requestId,
                pageEpoch,
                sessionEpoch,
                selectionTicket,
                action,
            ),
        )
