"""Generated explicit QWebChannel surface; do not edit by hand."""

from __future__ import annotations

from PySide6.QtCore import Signal, Slot

from .command_ids import CommandId
from .protocol import CompletionEnvelope
from .web_bridge_base import PdmBridgeBase


class BackupBridgeSurface(PdmBridgeBase):
    """精确的 Bridge v1.1（通信接口）白名单，不提供通用渲染器调用槽。"""

    cancelRequestCompletedV1 = Signal(str, int, int, str, int, int, "QVariant")
    chooseBackupDestinationCompletedV1 = Signal(str, int, int, str, int, int, "QVariant")
    exportEncryptedBackupCompletedV1 = Signal(str, int, int, str, int, int, "QVariant")
    chooseBackupSourceCompletedV1 = Signal(str, int, int, str, int, int, "QVariant")
    previewEncryptedBackupCompletedV1 = Signal(str, int, int, str, int, int, "QVariant")
    listBackupConflictsCompletedV1 = Signal(str, int, int, str, int, int, "QVariant")
    setBackupConflictDecisionCompletedV1 = Signal(str, int, int, str, int, int, "QVariant")
    setAllBackupConflictDecisionsCompletedV1 = Signal(str, int, int, str, int, int, "QVariant")
    readBackupConflictFieldChunkCompletedV1 = Signal(str, int, int, str, int, int, "QVariant")
    executeEncryptedBackupImportCompletedV1 = Signal(str, int, int, str, int, int, "QVariant")
    closeBackupPreviewCompletedV1 = Signal(str, int, int, str, int, int, "QVariant")
    readBackupComparisonFieldChunkCompletedV1 = Signal(str, int, int, str, int, int, "QVariant")


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
        elif command_id is CommandId.C50:
            self.chooseBackupDestinationCompletedV1.emit(*values)
        elif command_id is CommandId.C51:
            self.exportEncryptedBackupCompletedV1.emit(*values)
        elif command_id is CommandId.C52:
            self.chooseBackupSourceCompletedV1.emit(*values)
        elif command_id is CommandId.C53:
            self.previewEncryptedBackupCompletedV1.emit(*values)
        elif command_id is CommandId.C54:
            self.listBackupConflictsCompletedV1.emit(*values)
        elif command_id is CommandId.C55:
            self.setBackupConflictDecisionCompletedV1.emit(*values)
        elif command_id is CommandId.C56:
            self.setAllBackupConflictDecisionsCompletedV1.emit(*values)
        elif command_id is CommandId.C57:
            self.readBackupConflictFieldChunkCompletedV1.emit(*values)
        elif command_id is CommandId.C58:
            self.executeEncryptedBackupImportCompletedV1.emit(*values)
        elif command_id is CommandId.C59:
            self.closeBackupPreviewCompletedV1.emit(*values)
        elif command_id is CommandId.C81:
            self.readBackupComparisonFieldChunkCompletedV1.emit(*values)
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
    def chooseBackupDestinationV1(
        self,
        requestId: object,
        pageEpoch: object,
        sessionEpoch: object,
    ) -> dict[str, object]:
        return self._submit_explicit(
            CommandId.C50,
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
        result="QVariantMap",
    )
    def exportEncryptedBackupV1(
        self,
        requestId: object,
        pageEpoch: object,
        sessionEpoch: object,
        selectionTicket: object,
        scope: object,
        backupPassword: object,
        confirmPassword: object,
    ) -> dict[str, object]:
        return self._submit_explicit(
            CommandId.C51,
            (
                requestId,
                pageEpoch,
                sessionEpoch,
                selectionTicket,
                scope,
                backupPassword,
                confirmPassword,
            ),
        )

    @Slot(
        "QVariant",
        "QVariant",
        "QVariant",
        result="QVariantMap",
    )
    def chooseBackupSourceV1(
        self,
        requestId: object,
        pageEpoch: object,
        sessionEpoch: object,
    ) -> dict[str, object]:
        return self._submit_explicit(
            CommandId.C52,
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
        result="QVariantMap",
    )
    def previewEncryptedBackupV1(
        self,
        requestId: object,
        pageEpoch: object,
        sessionEpoch: object,
        selectionTicket: object,
        backupPassword: object,
    ) -> dict[str, object]:
        return self._submit_explicit(
            CommandId.C53,
            (
                requestId,
                pageEpoch,
                sessionEpoch,
                selectionTicket,
                backupPassword,
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
        "QVariant",
        result="QVariantMap",
    )
    def listBackupConflictsV1(
        self,
        requestId: object,
        pageEpoch: object,
        sessionEpoch: object,
        previewTicket: object,
        kind: object,
        statusFilter: object,
        fieldFilter: object,
        cursor: object,
        limit: object,
    ) -> dict[str, object]:
        return self._submit_explicit(
            CommandId.C54,
            (
                requestId,
                pageEpoch,
                sessionEpoch,
                previewTicket,
                kind,
                statusFilter,
                fieldFilter,
                cursor,
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
        result="QVariantMap",
    )
    def setBackupConflictDecisionV1(
        self,
        requestId: object,
        pageEpoch: object,
        sessionEpoch: object,
        previewTicket: object,
        conflictId: object,
        decision: object,
    ) -> dict[str, object]:
        return self._submit_explicit(
            CommandId.C55,
            (
                requestId,
                pageEpoch,
                sessionEpoch,
                previewTicket,
                conflictId,
                decision,
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
        result="QVariantMap",
    )
    def setAllBackupConflictDecisionsV1(
        self,
        requestId: object,
        pageEpoch: object,
        sessionEpoch: object,
        previewTicket: object,
        kind: object,
        conflictIds: object,
        decision: object,
    ) -> dict[str, object]:
        return self._submit_explicit(
            CommandId.C56,
            (
                requestId,
                pageEpoch,
                sessionEpoch,
                previewTicket,
                kind,
                conflictIds,
                decision,
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
        "QVariant",
        result="QVariantMap",
    )
    def readBackupConflictFieldChunkV1(
        self,
        requestId: object,
        pageEpoch: object,
        sessionEpoch: object,
        previewTicket: object,
        conflictId: object,
        side: object,
        field: object,
        readId: object,
        offset: object,
    ) -> dict[str, object]:
        return self._submit_explicit(
            CommandId.C57,
            (
                requestId,
                pageEpoch,
                sessionEpoch,
                previewTicket,
                conflictId,
                side,
                field,
                readId,
                offset,
            ),
        )

    @Slot(
        "QVariant",
        "QVariant",
        "QVariant",
        "QVariant",
        result="QVariantMap",
    )
    def executeEncryptedBackupImportV1(
        self,
        requestId: object,
        pageEpoch: object,
        sessionEpoch: object,
        previewTicket: object,
    ) -> dict[str, object]:
        return self._submit_explicit(
            CommandId.C58,
            (
                requestId,
                pageEpoch,
                sessionEpoch,
                previewTicket,
            ),
        )

    @Slot(
        "QVariant",
        "QVariant",
        "QVariant",
        "QVariant",
        result="QVariantMap",
    )
    def closeBackupPreviewV1(
        self,
        requestId: object,
        pageEpoch: object,
        sessionEpoch: object,
        previewTicket: object,
    ) -> dict[str, object]:
        return self._submit_explicit(
            CommandId.C59,
            (
                requestId,
                pageEpoch,
                sessionEpoch,
                previewTicket,
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
        "QVariant",
        result="QVariantMap",
    )
    def readBackupComparisonFieldChunkV1(
        self,
        requestId: object,
        pageEpoch: object,
        sessionEpoch: object,
        previewTicket: object,
        conflictId: object,
        side: object,
        field: object,
        readId: object,
        offset: object,
    ) -> dict[str, object]:
        return self._submit_explicit(
            CommandId.C81,
            (
                requestId,
                pageEpoch,
                sessionEpoch,
                previewTicket,
                conflictId,
                side,
                field,
                readId,
                offset,
            ),
        )
