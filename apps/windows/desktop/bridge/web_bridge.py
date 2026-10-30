"""由 tools/generate_bridge_surface.py 生成；请修改合同来源。"""

from __future__ import annotations

from PySide6.QtCore import Signal, Slot

from .command_ids import CommandId
from .protocol import CompletionEnvelope
from .web_bridge_base import PdmBridgeBase


class PdmBridgeV1(PdmBridgeBase):
    """精确的 Bridge v1.1（通信接口）白名单，不提供通用渲染器调用槽。"""

    handshakeCompletedV1 = Signal(str, int, int, str, int, int, "QVariant")
    chooseDatabaseTargetCompletedV1 = Signal(str, int, int, str, int, int, "QVariant")
    selectRecentDatabaseCompletedV1 = Signal(str, int, int, str, int, int, "QVariant")
    openDatabaseCompletedV1 = Signal(str, int, int, str, int, int, "QVariant")
    switchDatabaseCompletedV1 = Signal(str, int, int, str, int, int, "QVariant")
    lockCompletedV1 = Signal(str, int, int, str, int, int, "QVariant")
    cancelRequestCompletedV1 = Signal(str, int, int, str, int, int, "QVariant")
    releaseSecretLeaseCompletedV1 = Signal(str, int, int, str, int, int, "QVariant")
    openQuickbarCompletedV1 = Signal(str, int, int, str, int, int, "QVariant")
    listVaultSummariesCompletedV1 = Signal(str, int, int, str, int, int, "QVariant")
    getRecordDetailsCompletedV1 = Signal(str, int, int, str, int, int, "QVariant")
    openRecordEditorCompletedV1 = Signal(str, int, int, str, int, int, "QVariant")
    revealRecordPasswordCompletedV1 = Signal(str, int, int, str, int, int, "QVariant")
    createRecordCompletedV1 = Signal(str, int, int, str, int, int, "QVariant")
    updateRecordCompletedV1 = Signal(str, int, int, str, int, int, "QVariant")
    setRecordFavoriteCompletedV1 = Signal(str, int, int, str, int, int, "QVariant")
    prepareDeleteRecordCompletedV1 = Signal(str, int, int, str, int, int, "QVariant")
    deleteRecordCompletedV1 = Signal(str, int, int, str, int, int, "QVariant")
    copyRecordAccountCompletedV1 = Signal(str, int, int, str, int, int, "QVariant")
    copyRecordPasswordCompletedV1 = Signal(str, int, int, str, int, int, "QVariant")
    getRecordTotpCodeCompletedV1 = Signal(str, int, int, str, int, int, "QVariant")
    copyRecordTotpCompletedV1 = Signal(str, int, int, str, int, int, "QVariant")
    clearClipboardCompletedV1 = Signal(str, int, int, str, int, int, "QVariant")
    listNoteSummariesCompletedV1 = Signal(str, int, int, str, int, int, "QVariant")
    getNoteCompletedV1 = Signal(str, int, int, str, int, int, "QVariant")
    createNoteCompletedV1 = Signal(str, int, int, str, int, int, "QVariant")
    updateNoteCompletedV1 = Signal(str, int, int, str, int, int, "QVariant")
    setNoteFavoriteCompletedV1 = Signal(str, int, int, str, int, int, "QVariant")
    prepareDeleteNoteCompletedV1 = Signal(str, int, int, str, int, int, "QVariant")
    deleteNoteCompletedV1 = Signal(str, int, int, str, int, int, "QVariant")
    getHealthSummaryCompletedV1 = Signal(str, int, int, str, int, int, "QVariant")
    listHealthIssuesCompletedV1 = Signal(str, int, int, str, int, int, "QVariant")
    generatePasswordCompletedV1 = Signal(str, int, int, str, int, int, "QVariant")
    checkPasswordStrengthCompletedV1 = Signal(str, int, int, str, int, int, "QVariant")
    copyGeneratedPasswordCompletedV1 = Signal(str, int, int, str, int, int, "QVariant")
    setThemeCompletedV1 = Signal(str, int, int, str, int, int, "QVariant")
    setLanguageCompletedV1 = Signal(str, int, int, str, int, int, "QVariant")
    setStartupAutofillCompletedV1 = Signal(str, int, int, str, int, int, "QVariant")
    setDefaultViewCompletedV1 = Signal(str, int, int, str, int, int, "QVariant")
    setSidebarTextCompletedV1 = Signal(str, int, int, str, int, int, "QVariant")
    setSortModeCompletedV1 = Signal(str, int, int, str, int, int, "QVariant")
    setClipboardPolicyCompletedV1 = Signal(str, int, int, str, int, int, "QVariant")
    setCloseBehaviorCompletedV1 = Signal(str, int, int, str, int, int, "QVariant")
    setQuickbarEnabledCompletedV1 = Signal(str, int, int, str, int, int, "QVariant")
    setQuickbarHotkeyCompletedV1 = Signal(str, int, int, str, int, int, "QVariant")
    setStaleThresholdCompletedV1 = Signal(str, int, int, str, int, int, "QVariant")
    setAutoLockPolicyCompletedV1 = Signal(str, int, int, str, int, int, "QVariant")
    setPasswordGeneratorDefaultsCompletedV1 = Signal(str, int, int, str, int, int, "QVariant")
    changeDatabasePasswordCompletedV1 = Signal(str, int, int, str, int, int, "QVariant")
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
    readRecordFieldChunkCompletedV1 = Signal(str, int, int, str, int, int, "QVariant")
    releaseRecordFieldReadCompletedV1 = Signal(str, int, int, str, int, int, "QVariant")
    updateRecordFieldsCompletedV1 = Signal(str, int, int, str, int, int, "QVariant")
    readNoteFieldChunkCompletedV1 = Signal(str, int, int, str, int, int, "QVariant")
    releaseNoteFieldReadCompletedV1 = Signal(str, int, int, str, int, int, "QVariant")
    updateNoteFieldsCompletedV1 = Signal(str, int, int, str, int, int, "QVariant")
    locateVaultRecordCompletedV1 = Signal(str, int, int, str, int, int, "QVariant")
    getHealthOverviewAtCompletedV1 = Signal(str, int, int, str, int, int, "QVariant")
    getHealthGuidancePageCompletedV1 = Signal(str, int, int, str, int, int, "QVariant")
    releaseHealthGuidanceCompletedV1 = Signal(str, int, int, str, int, int, "QVariant")
    startHealthRescanCompletedV1 = Signal(str, int, int, str, int, int, "QVariant")
    getHealthRescanStatusCompletedV1 = Signal(str, int, int, str, int, int, "QVariant")
    cancelHealthRescanCompletedV1 = Signal(str, int, int, str, int, int, "QVariant")
    setUiFontScaleCompletedV1 = Signal(str, int, int, str, int, int, "QVariant")
    removeRecentDatabaseCompletedV1 = Signal(str, int, int, str, int, int, "QVariant")
    beginExportSelectionCompletedV1 = Signal(str, int, int, str, int, int, "QVariant")
    listExportSelectionCompletedV1 = Signal(str, int, int, str, int, int, "QVariant")
    changeExportSelectionCompletedV1 = Signal(str, int, int, str, int, int, "QVariant")
    finishExportSelectionCompletedV1 = Signal(str, int, int, str, int, int, "QVariant")
    retryRecordStrengthCompletedV1 = Signal(str, int, int, str, int, int, "QVariant")
    locateVaultAnchorCompletedV1 = Signal(str, int, int, str, int, int, "QVariant")
    revealRecoveryCodeCompletedV1 = Signal(str, int, int, str, int, int, "QVariant")
    copyRecoveryCodeCompletedV1 = Signal(str, int, int, str, int, int, "QVariant")
    setRecoveryCodeUsedCompletedV1 = Signal(str, int, int, str, int, int, "QVariant")
    contactSupportCompletedV1 = Signal(str, int, int, str, int, int, "QVariant")
    readBackupComparisonFieldChunkCompletedV1 = Signal(str, int, int, str, int, int, "QVariant")
    getUpdateStateCompletedV1 = Signal(str, int, int, str, int, int, "QVariant")
    checkUpdatesCompletedV1 = Signal(str, int, int, str, int, int, "QVariant")
    setUpdatePolicyCompletedV1 = Signal(str, int, int, str, int, int, "QVariant")
    setUpdateReminderCompletedV1 = Signal(str, int, int, str, int, int, "QVariant")
    openUpdateReleaseCompletedV1 = Signal(str, int, int, str, int, int, "QVariant")

    sessionStateChangedV1 = Signal(int, int, str, str, str)
    settingsChangedV1 = Signal(int, str, "QVariantMap")
    clipboardStateChangedV1 = Signal(int, int, str, str, int, bool)
    requestProgressV1 = Signal(int, int, str, str, int, int)
    systemThemeChangedV1 = Signal(int, str)
    dataRevisionChangedV1 = Signal(int, int, str, str, str)
    updateStateChangedV1 = Signal(int, "QVariantMap")

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
        if command_id is CommandId.C01:
            self.handshakeCompletedV1.emit(*values)
        elif command_id is CommandId.C02:
            self.chooseDatabaseTargetCompletedV1.emit(*values)
        elif command_id is CommandId.C03:
            self.selectRecentDatabaseCompletedV1.emit(*values)
        elif command_id is CommandId.C04:
            self.openDatabaseCompletedV1.emit(*values)
        elif command_id is CommandId.C05:
            self.switchDatabaseCompletedV1.emit(*values)
        elif command_id is CommandId.C06:
            self.lockCompletedV1.emit(*values)
        elif command_id is CommandId.C07:
            self.cancelRequestCompletedV1.emit(*values)
        elif command_id is CommandId.C08:
            self.releaseSecretLeaseCompletedV1.emit(*values)
        elif command_id is CommandId.C09:
            self.openQuickbarCompletedV1.emit(*values)
        elif command_id is CommandId.C10:
            self.listVaultSummariesCompletedV1.emit(*values)
        elif command_id is CommandId.C11:
            self.getRecordDetailsCompletedV1.emit(*values)
        elif command_id is CommandId.C12:
            self.openRecordEditorCompletedV1.emit(*values)
        elif command_id is CommandId.C13:
            self.revealRecordPasswordCompletedV1.emit(*values)
        elif command_id is CommandId.C14:
            self.createRecordCompletedV1.emit(*values)
        elif command_id is CommandId.C15:
            self.updateRecordCompletedV1.emit(*values)
        elif command_id is CommandId.C16:
            self.setRecordFavoriteCompletedV1.emit(*values)
        elif command_id is CommandId.C17:
            self.prepareDeleteRecordCompletedV1.emit(*values)
        elif command_id is CommandId.C18:
            self.deleteRecordCompletedV1.emit(*values)
        elif command_id is CommandId.C19:
            self.copyRecordAccountCompletedV1.emit(*values)
        elif command_id is CommandId.C20:
            self.copyRecordPasswordCompletedV1.emit(*values)
        elif command_id is CommandId.C21:
            self.getRecordTotpCodeCompletedV1.emit(*values)
        elif command_id is CommandId.C22:
            self.copyRecordTotpCompletedV1.emit(*values)
        elif command_id is CommandId.C23:
            self.clearClipboardCompletedV1.emit(*values)
        elif command_id is CommandId.C24:
            self.listNoteSummariesCompletedV1.emit(*values)
        elif command_id is CommandId.C25:
            self.getNoteCompletedV1.emit(*values)
        elif command_id is CommandId.C26:
            self.createNoteCompletedV1.emit(*values)
        elif command_id is CommandId.C27:
            self.updateNoteCompletedV1.emit(*values)
        elif command_id is CommandId.C28:
            self.setNoteFavoriteCompletedV1.emit(*values)
        elif command_id is CommandId.C29:
            self.prepareDeleteNoteCompletedV1.emit(*values)
        elif command_id is CommandId.C30:
            self.deleteNoteCompletedV1.emit(*values)
        elif command_id is CommandId.C31:
            self.getHealthSummaryCompletedV1.emit(*values)
        elif command_id is CommandId.C32:
            self.listHealthIssuesCompletedV1.emit(*values)
        elif command_id is CommandId.C33:
            self.generatePasswordCompletedV1.emit(*values)
        elif command_id is CommandId.C34:
            self.checkPasswordStrengthCompletedV1.emit(*values)
        elif command_id is CommandId.C35:
            self.copyGeneratedPasswordCompletedV1.emit(*values)
        elif command_id is CommandId.C36:
            self.setThemeCompletedV1.emit(*values)
        elif command_id is CommandId.C37:
            self.setLanguageCompletedV1.emit(*values)
        elif command_id is CommandId.C38:
            self.setStartupAutofillCompletedV1.emit(*values)
        elif command_id is CommandId.C39:
            self.setDefaultViewCompletedV1.emit(*values)
        elif command_id is CommandId.C40:
            self.setSidebarTextCompletedV1.emit(*values)
        elif command_id is CommandId.C41:
            self.setSortModeCompletedV1.emit(*values)
        elif command_id is CommandId.C42:
            self.setClipboardPolicyCompletedV1.emit(*values)
        elif command_id is CommandId.C43:
            self.setCloseBehaviorCompletedV1.emit(*values)
        elif command_id is CommandId.C44:
            self.setQuickbarEnabledCompletedV1.emit(*values)
        elif command_id is CommandId.C45:
            self.setQuickbarHotkeyCompletedV1.emit(*values)
        elif command_id is CommandId.C46:
            self.setStaleThresholdCompletedV1.emit(*values)
        elif command_id is CommandId.C47:
            self.setAutoLockPolicyCompletedV1.emit(*values)
        elif command_id is CommandId.C48:
            self.setPasswordGeneratorDefaultsCompletedV1.emit(*values)
        elif command_id is CommandId.C49:
            self.changeDatabasePasswordCompletedV1.emit(*values)
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
        elif command_id is CommandId.C60:
            self.readRecordFieldChunkCompletedV1.emit(*values)
        elif command_id is CommandId.C61:
            self.releaseRecordFieldReadCompletedV1.emit(*values)
        elif command_id is CommandId.C62:
            self.updateRecordFieldsCompletedV1.emit(*values)
        elif command_id is CommandId.C63:
            self.readNoteFieldChunkCompletedV1.emit(*values)
        elif command_id is CommandId.C64:
            self.releaseNoteFieldReadCompletedV1.emit(*values)
        elif command_id is CommandId.C65:
            self.updateNoteFieldsCompletedV1.emit(*values)
        elif command_id is CommandId.C66:
            self.locateVaultRecordCompletedV1.emit(*values)
        elif command_id is CommandId.C67:
            self.getHealthOverviewAtCompletedV1.emit(*values)
        elif command_id is CommandId.C68:
            self.getHealthGuidancePageCompletedV1.emit(*values)
        elif command_id is CommandId.C69:
            self.releaseHealthGuidanceCompletedV1.emit(*values)
        elif command_id is CommandId.C70:
            self.startHealthRescanCompletedV1.emit(*values)
        elif command_id is CommandId.C71:
            self.getHealthRescanStatusCompletedV1.emit(*values)
        elif command_id is CommandId.C72:
            self.cancelHealthRescanCompletedV1.emit(*values)
        elif command_id is CommandId.C73:
            self.setUiFontScaleCompletedV1.emit(*values)
        elif command_id is CommandId.C74:
            self.removeRecentDatabaseCompletedV1.emit(*values)
        elif command_id is CommandId.C87:
            self.beginExportSelectionCompletedV1.emit(*values)
        elif command_id is CommandId.C88:
            self.listExportSelectionCompletedV1.emit(*values)
        elif command_id is CommandId.C89:
            self.changeExportSelectionCompletedV1.emit(*values)
        elif command_id is CommandId.C90:
            self.finishExportSelectionCompletedV1.emit(*values)
        elif command_id is CommandId.C75:
            self.retryRecordStrengthCompletedV1.emit(*values)
        elif command_id is CommandId.C76:
            self.locateVaultAnchorCompletedV1.emit(*values)
        elif command_id is CommandId.C77:
            self.revealRecoveryCodeCompletedV1.emit(*values)
        elif command_id is CommandId.C78:
            self.copyRecoveryCodeCompletedV1.emit(*values)
        elif command_id is CommandId.C79:
            self.setRecoveryCodeUsedCompletedV1.emit(*values)
        elif command_id is CommandId.C80:
            self.contactSupportCompletedV1.emit(*values)
        elif command_id is CommandId.C81:
            self.readBackupComparisonFieldChunkCompletedV1.emit(*values)
        elif command_id is CommandId.C82:
            self.getUpdateStateCompletedV1.emit(*values)
        elif command_id is CommandId.C83:
            self.checkUpdatesCompletedV1.emit(*values)
        elif command_id is CommandId.C84:
            self.setUpdatePolicyCompletedV1.emit(*values)
        elif command_id is CommandId.C85:
            self.setUpdateReminderCompletedV1.emit(*values)
        elif command_id is CommandId.C86:
            self.openUpdateReleaseCompletedV1.emit(*values)
        else:
            raise RuntimeError("unknown frozen command")

    @Slot(
        "QVariant",
        "QVariant",
        "QVariant",
        result="QVariantMap",
    )
    def handshakeV1(
        self,
        requestId: object,
        pageInstanceId: object,
        contractVersion: object,
    ) -> dict[str, object]:
        return self._submit_explicit(
            CommandId.C01,
            (
                requestId,
                pageInstanceId,
                contractVersion,
            ),
        )

    @Slot(
        "QVariant",
        "QVariant",
        "QVariant",
        result="QVariantMap",
    )
    def chooseDatabaseTargetV1(
        self,
        requestId: object,
        pageEpoch: object,
        databasePathCandidate: object,
    ) -> dict[str, object]:
        return self._submit_explicit(
            CommandId.C02,
            (
                requestId,
                pageEpoch,
                databasePathCandidate,
            ),
        )

    @Slot(
        "QVariant",
        "QVariant",
        "QVariant",
        result="QVariantMap",
    )
    def selectRecentDatabaseV1(
        self,
        requestId: object,
        pageEpoch: object,
        recentDatabaseId: object,
    ) -> dict[str, object]:
        return self._submit_explicit(
            CommandId.C03,
            (
                requestId,
                pageEpoch,
                recentDatabaseId,
            ),
        )

    @Slot(
        "QVariant",
        "QVariant",
        "QVariant",
        "QVariant",
        result="QVariantMap",
    )
    def openDatabaseV1(
        self,
        requestId: object,
        pageEpoch: object,
        selectionTicket: object,
        masterPassword: object,
    ) -> dict[str, object]:
        return self._submit_explicit(
            CommandId.C04,
            (
                requestId,
                pageEpoch,
                selectionTicket,
                masterPassword,
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
    def switchDatabaseV1(
        self,
        requestId: object,
        pageEpoch: object,
        sessionEpoch: object,
        selectionTicket: object,
        masterPassword: object,
    ) -> dict[str, object]:
        return self._submit_explicit(
            CommandId.C05,
            (
                requestId,
                pageEpoch,
                sessionEpoch,
                selectionTicket,
                masterPassword,
            ),
        )

    @Slot(
        "QVariant",
        "QVariant",
        "QVariant",
        result="QVariantMap",
    )
    def lockV1(
        self,
        requestId: object,
        pageEpoch: object,
        sessionEpoch: object,
    ) -> dict[str, object]:
        return self._submit_explicit(
            CommandId.C06,
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
    def releaseSecretLeaseV1(
        self,
        requestId: object,
        pageEpoch: object,
        secretLeaseId: object,
    ) -> dict[str, object]:
        return self._submit_explicit(
            CommandId.C08,
            (
                requestId,
                pageEpoch,
                secretLeaseId,
            ),
        )

    @Slot(
        "QVariant",
        "QVariant",
        "QVariant",
        result="QVariantMap",
    )
    def openQuickbarV1(
        self,
        requestId: object,
        pageEpoch: object,
        sessionEpoch: object,
    ) -> dict[str, object]:
        return self._submit_explicit(
            CommandId.C09,
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
    def listVaultSummariesV1(
        self,
        requestId: object,
        pageEpoch: object,
        sessionEpoch: object,
        query: object,
        filter: object,
        sort: object,
        cursor: object,
        limit: object,
    ) -> dict[str, object]:
        return self._submit_explicit(
            CommandId.C10,
            (
                requestId,
                pageEpoch,
                sessionEpoch,
                query,
                filter,
                sort,
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
        result="QVariantMap",
    )
    def getRecordDetailsV1(
        self,
        requestId: object,
        pageEpoch: object,
        sessionEpoch: object,
        recordId: object,
        revision: object,
    ) -> dict[str, object]:
        return self._submit_explicit(
            CommandId.C11,
            (
                requestId,
                pageEpoch,
                sessionEpoch,
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
    def openRecordEditorV1(
        self,
        requestId: object,
        pageEpoch: object,
        sessionEpoch: object,
        recordId: object,
        revision: object,
    ) -> dict[str, object]:
        return self._submit_explicit(
            CommandId.C12,
            (
                requestId,
                pageEpoch,
                sessionEpoch,
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
    def revealRecordPasswordV1(
        self,
        requestId: object,
        pageEpoch: object,
        sessionEpoch: object,
        recordId: object,
        revision: object,
    ) -> dict[str, object]:
        return self._submit_explicit(
            CommandId.C13,
            (
                requestId,
                pageEpoch,
                sessionEpoch,
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
        "QVariant",
        "QVariant",
        "QVariant",
        "QVariant",
        "QVariant",
        "QVariant",
        result="QVariantMap",
    )
    def createRecordV1(
        self,
        requestId: object,
        pageEpoch: object,
        sessionEpoch: object,
        platform: object,
        account: object,
        password: object,
        notes: object,
        totpAction: object,
        totpSecret: object,
        favorite: object,
        recoveryText: object,
    ) -> dict[str, object]:
        return self._submit_explicit(
            CommandId.C14,
            (
                requestId,
                pageEpoch,
                sessionEpoch,
                platform,
                account,
                password,
                notes,
                totpAction,
                totpSecret,
                favorite,
                recoveryText,
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
        "QVariant",
        "QVariant",
        "QVariant",
        "QVariant",
        "QVariant",
        "QVariant",
        "QVariant",
        result="QVariantMap",
    )
    def updateRecordV1(
        self,
        requestId: object,
        pageEpoch: object,
        sessionEpoch: object,
        recordId: object,
        revision: object,
        editLeaseId: object,
        platform: object,
        account: object,
        passwordAction: object,
        password: object,
        notes: object,
        totpAction: object,
        totpSecret: object,
        favorite: object,
        recoveryAction: object,
        recoveryText: object,
    ) -> dict[str, object]:
        return self._submit_explicit(
            CommandId.C15,
            (
                requestId,
                pageEpoch,
                sessionEpoch,
                recordId,
                revision,
                editLeaseId,
                platform,
                account,
                passwordAction,
                password,
                notes,
                totpAction,
                totpSecret,
                favorite,
                recoveryAction,
                recoveryText,
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
    def setRecordFavoriteV1(
        self,
        requestId: object,
        pageEpoch: object,
        sessionEpoch: object,
        recordId: object,
        revision: object,
        favorite: object,
    ) -> dict[str, object]:
        return self._submit_explicit(
            CommandId.C16,
            (
                requestId,
                pageEpoch,
                sessionEpoch,
                recordId,
                revision,
                favorite,
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
    def prepareDeleteRecordV1(
        self,
        requestId: object,
        pageEpoch: object,
        sessionEpoch: object,
        recordId: object,
        revision: object,
    ) -> dict[str, object]:
        return self._submit_explicit(
            CommandId.C17,
            (
                requestId,
                pageEpoch,
                sessionEpoch,
                recordId,
                revision,
            ),
        )

    @Slot(
        "QVariant",
        "QVariant",
        "QVariant",
        "QVariant",
        result="QVariantMap",
    )
    def deleteRecordV1(
        self,
        requestId: object,
        pageEpoch: object,
        sessionEpoch: object,
        deleteTicket: object,
    ) -> dict[str, object]:
        return self._submit_explicit(
            CommandId.C18,
            (
                requestId,
                pageEpoch,
                sessionEpoch,
                deleteTicket,
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
    def copyRecordAccountV1(
        self,
        requestId: object,
        pageEpoch: object,
        sessionEpoch: object,
        recordId: object,
        revision: object,
    ) -> dict[str, object]:
        return self._submit_explicit(
            CommandId.C19,
            (
                requestId,
                pageEpoch,
                sessionEpoch,
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
    def copyRecordPasswordV1(
        self,
        requestId: object,
        pageEpoch: object,
        sessionEpoch: object,
        recordId: object,
        revision: object,
    ) -> dict[str, object]:
        return self._submit_explicit(
            CommandId.C20,
            (
                requestId,
                pageEpoch,
                sessionEpoch,
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
    def getRecordTotpCodeV1(
        self,
        requestId: object,
        pageEpoch: object,
        sessionEpoch: object,
        recordId: object,
        revision: object,
    ) -> dict[str, object]:
        return self._submit_explicit(
            CommandId.C21,
            (
                requestId,
                pageEpoch,
                sessionEpoch,
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
    def copyRecordTotpV1(
        self,
        requestId: object,
        pageEpoch: object,
        sessionEpoch: object,
        recordId: object,
        revision: object,
    ) -> dict[str, object]:
        return self._submit_explicit(
            CommandId.C22,
            (
                requestId,
                pageEpoch,
                sessionEpoch,
                recordId,
                revision,
            ),
        )

    @Slot(
        "QVariant",
        "QVariant",
        result="QVariantMap",
    )
    def clearClipboardV1(
        self,
        requestId: object,
        pageEpoch: object,
    ) -> dict[str, object]:
        return self._submit_explicit(
            CommandId.C23,
            (
                requestId,
                pageEpoch,
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
    def listNoteSummariesV1(
        self,
        requestId: object,
        pageEpoch: object,
        sessionEpoch: object,
        query: object,
        filter: object,
        cursor: object,
        limit: object,
        sortMode: object,
    ) -> dict[str, object]:
        return self._submit_explicit(
            CommandId.C24,
            (
                requestId,
                pageEpoch,
                sessionEpoch,
                query,
                filter,
                cursor,
                limit,
                sortMode,
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
    def getNoteV1(
        self,
        requestId: object,
        pageEpoch: object,
        sessionEpoch: object,
        noteId: object,
        revision: object,
    ) -> dict[str, object]:
        return self._submit_explicit(
            CommandId.C25,
            (
                requestId,
                pageEpoch,
                sessionEpoch,
                noteId,
                revision,
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
    def createNoteV1(
        self,
        requestId: object,
        pageEpoch: object,
        sessionEpoch: object,
        title: object,
        content: object,
        favorite: object,
    ) -> dict[str, object]:
        return self._submit_explicit(
            CommandId.C26,
            (
                requestId,
                pageEpoch,
                sessionEpoch,
                title,
                content,
                favorite,
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
    def updateNoteV1(
        self,
        requestId: object,
        pageEpoch: object,
        sessionEpoch: object,
        noteId: object,
        revision: object,
        title: object,
        content: object,
        favorite: object,
    ) -> dict[str, object]:
        return self._submit_explicit(
            CommandId.C27,
            (
                requestId,
                pageEpoch,
                sessionEpoch,
                noteId,
                revision,
                title,
                content,
                favorite,
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
    def setNoteFavoriteV1(
        self,
        requestId: object,
        pageEpoch: object,
        sessionEpoch: object,
        noteId: object,
        revision: object,
        favorite: object,
    ) -> dict[str, object]:
        return self._submit_explicit(
            CommandId.C28,
            (
                requestId,
                pageEpoch,
                sessionEpoch,
                noteId,
                revision,
                favorite,
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
    def prepareDeleteNoteV1(
        self,
        requestId: object,
        pageEpoch: object,
        sessionEpoch: object,
        noteId: object,
        revision: object,
    ) -> dict[str, object]:
        return self._submit_explicit(
            CommandId.C29,
            (
                requestId,
                pageEpoch,
                sessionEpoch,
                noteId,
                revision,
            ),
        )

    @Slot(
        "QVariant",
        "QVariant",
        "QVariant",
        "QVariant",
        result="QVariantMap",
    )
    def deleteNoteV1(
        self,
        requestId: object,
        pageEpoch: object,
        sessionEpoch: object,
        deleteTicket: object,
    ) -> dict[str, object]:
        return self._submit_explicit(
            CommandId.C30,
            (
                requestId,
                pageEpoch,
                sessionEpoch,
                deleteTicket,
            ),
        )

    @Slot(
        "QVariant",
        "QVariant",
        "QVariant",
        result="QVariantMap",
    )
    def getHealthSummaryV1(
        self,
        requestId: object,
        pageEpoch: object,
        sessionEpoch: object,
    ) -> dict[str, object]:
        return self._submit_explicit(
            CommandId.C31,
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
        result="QVariantMap",
    )
    def listHealthIssuesV1(
        self,
        requestId: object,
        pageEpoch: object,
        sessionEpoch: object,
        kind: object,
        cursor: object,
        limit: object,
    ) -> dict[str, object]:
        return self._submit_explicit(
            CommandId.C32,
            (
                requestId,
                pageEpoch,
                sessionEpoch,
                kind,
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
        "QVariant",
        "QVariant",
        result="QVariantMap",
    )
    def generatePasswordV1(
        self,
        requestId: object,
        pageEpoch: object,
        length: object,
        useLower: object,
        useUpper: object,
        useDigits: object,
        useSymbols: object,
        avoidAmbiguous: object,
    ) -> dict[str, object]:
        return self._submit_explicit(
            CommandId.C33,
            (
                requestId,
                pageEpoch,
                length,
                useLower,
                useUpper,
                useDigits,
                useSymbols,
                avoidAmbiguous,
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
    def checkPasswordStrengthV1(
        self,
        requestId: object,
        pageEpoch: object,
        password: object,
        platform: object,
        account: object,
    ) -> dict[str, object]:
        return self._submit_explicit(
            CommandId.C34,
            (
                requestId,
                pageEpoch,
                password,
                platform,
                account,
            ),
        )

    @Slot(
        "QVariant",
        "QVariant",
        "QVariant",
        result="QVariantMap",
    )
    def copyGeneratedPasswordV1(
        self,
        requestId: object,
        pageEpoch: object,
        secretLeaseId: object,
    ) -> dict[str, object]:
        return self._submit_explicit(
            CommandId.C35,
            (
                requestId,
                pageEpoch,
                secretLeaseId,
            ),
        )

    @Slot(
        "QVariant",
        "QVariant",
        "QVariant",
        result="QVariantMap",
    )
    def setThemeV1(
        self,
        requestId: object,
        pageEpoch: object,
        theme: object,
    ) -> dict[str, object]:
        return self._submit_explicit(
            CommandId.C36,
            (
                requestId,
                pageEpoch,
                theme,
            ),
        )

    @Slot(
        "QVariant",
        "QVariant",
        "QVariant",
        result="QVariantMap",
    )
    def setLanguageV1(
        self,
        requestId: object,
        pageEpoch: object,
        language: object,
    ) -> dict[str, object]:
        return self._submit_explicit(
            CommandId.C37,
            (
                requestId,
                pageEpoch,
                language,
            ),
        )

    @Slot(
        "QVariant",
        "QVariant",
        "QVariant",
        "QVariant",
        result="QVariantMap",
    )
    def setStartupAutofillV1(
        self,
        requestId: object,
        pageEpoch: object,
        sessionEpoch: object,
        enabled: object,
    ) -> dict[str, object]:
        return self._submit_explicit(
            CommandId.C38,
            (
                requestId,
                pageEpoch,
                sessionEpoch,
                enabled,
            ),
        )

    @Slot(
        "QVariant",
        "QVariant",
        "QVariant",
        "QVariant",
        result="QVariantMap",
    )
    def setDefaultViewV1(
        self,
        requestId: object,
        pageEpoch: object,
        sessionEpoch: object,
        viewMode: object,
    ) -> dict[str, object]:
        return self._submit_explicit(
            CommandId.C39,
            (
                requestId,
                pageEpoch,
                sessionEpoch,
                viewMode,
            ),
        )

    @Slot(
        "QVariant",
        "QVariant",
        "QVariant",
        result="QVariantMap",
    )
    def setSidebarTextV1(
        self,
        requestId: object,
        pageEpoch: object,
        enabled: object,
    ) -> dict[str, object]:
        return self._submit_explicit(
            CommandId.C40,
            (
                requestId,
                pageEpoch,
                enabled,
            ),
        )

    @Slot(
        "QVariant",
        "QVariant",
        "QVariant",
        "QVariant",
        result="QVariantMap",
    )
    def setSortModeV1(
        self,
        requestId: object,
        pageEpoch: object,
        sessionEpoch: object,
        sortMode: object,
    ) -> dict[str, object]:
        return self._submit_explicit(
            CommandId.C41,
            (
                requestId,
                pageEpoch,
                sessionEpoch,
                sortMode,
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
    def setClipboardPolicyV1(
        self,
        requestId: object,
        pageEpoch: object,
        sessionEpoch: object,
        mode: object,
        seconds: object,
    ) -> dict[str, object]:
        return self._submit_explicit(
            CommandId.C42,
            (
                requestId,
                pageEpoch,
                sessionEpoch,
                mode,
                seconds,
            ),
        )

    @Slot(
        "QVariant",
        "QVariant",
        "QVariant",
        "QVariant",
        result="QVariantMap",
    )
    def setCloseBehaviorV1(
        self,
        requestId: object,
        pageEpoch: object,
        sessionEpoch: object,
        behavior: object,
    ) -> dict[str, object]:
        return self._submit_explicit(
            CommandId.C43,
            (
                requestId,
                pageEpoch,
                sessionEpoch,
                behavior,
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
    def setQuickbarEnabledV1(
        self,
        requestId: object,
        pageEpoch: object,
        sessionEpoch: object,
        enabled: object,
        idleSeconds: object,
    ) -> dict[str, object]:
        return self._submit_explicit(
            CommandId.C44,
            (
                requestId,
                pageEpoch,
                sessionEpoch,
                enabled,
                idleSeconds,
            ),
        )

    @Slot(
        "QVariant",
        "QVariant",
        "QVariant",
        "QVariant",
        result="QVariantMap",
    )
    def setQuickbarHotkeyV1(
        self,
        requestId: object,
        pageEpoch: object,
        sessionEpoch: object,
        hotkey: object,
    ) -> dict[str, object]:
        return self._submit_explicit(
            CommandId.C45,
            (
                requestId,
                pageEpoch,
                sessionEpoch,
                hotkey,
            ),
        )

    @Slot(
        "QVariant",
        "QVariant",
        "QVariant",
        "QVariant",
        result="QVariantMap",
    )
    def setStaleThresholdV1(
        self,
        requestId: object,
        pageEpoch: object,
        sessionEpoch: object,
        days: object,
    ) -> dict[str, object]:
        return self._submit_explicit(
            CommandId.C46,
            (
                requestId,
                pageEpoch,
                sessionEpoch,
                days,
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
    def setAutoLockPolicyV1(
        self,
        requestId: object,
        pageEpoch: object,
        sessionEpoch: object,
        enabled: object,
        minutes: object,
    ) -> dict[str, object]:
        return self._submit_explicit(
            CommandId.C47,
            (
                requestId,
                pageEpoch,
                sessionEpoch,
                enabled,
                minutes,
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
    def setPasswordGeneratorDefaultsV1(
        self,
        requestId: object,
        pageEpoch: object,
        sessionEpoch: object,
        length: object,
        useLower: object,
        useUpper: object,
        useDigits: object,
        useSymbols: object,
        avoidAmbiguous: object,
    ) -> dict[str, object]:
        return self._submit_explicit(
            CommandId.C48,
            (
                requestId,
                pageEpoch,
                sessionEpoch,
                length,
                useLower,
                useUpper,
                useDigits,
                useSymbols,
                avoidAmbiguous,
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
    def changeDatabasePasswordV1(
        self,
        requestId: object,
        pageEpoch: object,
        sessionEpoch: object,
        currentPassword: object,
        newPassword: object,
        confirmPassword: object,
    ) -> dict[str, object]:
        return self._submit_explicit(
            CommandId.C49,
            (
                requestId,
                pageEpoch,
                sessionEpoch,
                currentPassword,
                newPassword,
                confirmPassword,
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
    def readRecordFieldChunkV1(
        self,
        requestId: object,
        pageEpoch: object,
        sessionEpoch: object,
        recordId: object,
        revision: object,
        field: object,
        authorityLeaseId: object,
        readId: object,
        offset: object,
    ) -> dict[str, object]:
        return self._submit_explicit(
            CommandId.C60,
            (
                requestId,
                pageEpoch,
                sessionEpoch,
                recordId,
                revision,
                field,
                authorityLeaseId,
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
    def releaseRecordFieldReadV1(
        self,
        requestId: object,
        pageEpoch: object,
        sessionEpoch: object,
        readId: object,
    ) -> dict[str, object]:
        return self._submit_explicit(
            CommandId.C61,
            (
                requestId,
                pageEpoch,
                sessionEpoch,
                readId,
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
        "QVariant",
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
    def updateRecordFieldsV1(
        self,
        requestId: object,
        pageEpoch: object,
        sessionEpoch: object,
        recordId: object,
        revision: object,
        editLeaseId: object,
        platformAction: object,
        platform: object,
        accountAction: object,
        account: object,
        passwordAction: object,
        password: object,
        notesAction: object,
        notes: object,
        totpAction: object,
        totpSecret: object,
        favorite: object,
        recoveryAction: object,
        recoveryText: object,
    ) -> dict[str, object]:
        return self._submit_explicit(
            CommandId.C62,
            (
                requestId,
                pageEpoch,
                sessionEpoch,
                recordId,
                revision,
                editLeaseId,
                platformAction,
                platform,
                accountAction,
                account,
                passwordAction,
                password,
                notesAction,
                notes,
                totpAction,
                totpSecret,
                favorite,
                recoveryAction,
                recoveryText,
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
    def readNoteFieldChunkV1(
        self,
        requestId: object,
        pageEpoch: object,
        sessionEpoch: object,
        noteId: object,
        revision: object,
        field: object,
        readId: object,
        offset: object,
    ) -> dict[str, object]:
        return self._submit_explicit(
            CommandId.C63,
            (
                requestId,
                pageEpoch,
                sessionEpoch,
                noteId,
                revision,
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
    def releaseNoteFieldReadV1(
        self,
        requestId: object,
        pageEpoch: object,
        sessionEpoch: object,
        readId: object,
    ) -> dict[str, object]:
        return self._submit_explicit(
            CommandId.C64,
            (
                requestId,
                pageEpoch,
                sessionEpoch,
                readId,
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
        "QVariant",
        result="QVariantMap",
    )
    def updateNoteFieldsV1(
        self,
        requestId: object,
        pageEpoch: object,
        sessionEpoch: object,
        noteId: object,
        revision: object,
        titleAction: object,
        title: object,
        contentAction: object,
        content: object,
        favorite: object,
    ) -> dict[str, object]:
        return self._submit_explicit(
            CommandId.C65,
            (
                requestId,
                pageEpoch,
                sessionEpoch,
                noteId,
                revision,
                titleAction,
                title,
                contentAction,
                content,
                favorite,
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
    def locateVaultRecordV1(
        self,
        requestId: object,
        pageEpoch: object,
        sessionEpoch: object,
        recordId: object,
        revision: object,
        sort: object,
    ) -> dict[str, object]:
        return self._submit_explicit(
            CommandId.C66,
            (
                requestId,
                pageEpoch,
                sessionEpoch,
                recordId,
                revision,
                sort,
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
    def getHealthOverviewAtV1(
        self,
        requestId: object,
        pageEpoch: object,
        sessionEpoch: object,
        kind: object,
        pageIndex: object,
    ) -> dict[str, object]:
        return self._submit_explicit(
            CommandId.C67,
            (
                requestId,
                pageEpoch,
                sessionEpoch,
                kind,
                pageIndex,
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
    def getHealthGuidancePageV1(
        self,
        requestId: object,
        pageEpoch: object,
        sessionEpoch: object,
        guidanceId: object,
        cursor: object,
    ) -> dict[str, object]:
        return self._submit_explicit(
            CommandId.C68,
            (
                requestId,
                pageEpoch,
                sessionEpoch,
                guidanceId,
                cursor,
            ),
        )

    @Slot(
        "QVariant",
        "QVariant",
        "QVariant",
        "QVariant",
        result="QVariantMap",
    )
    def releaseHealthGuidanceV1(
        self,
        requestId: object,
        pageEpoch: object,
        sessionEpoch: object,
        guidanceId: object,
    ) -> dict[str, object]:
        return self._submit_explicit(
            CommandId.C69,
            (
                requestId,
                pageEpoch,
                sessionEpoch,
                guidanceId,
            ),
        )

    @Slot(
        "QVariant",
        "QVariant",
        "QVariant",
        result="QVariantMap",
    )
    def startHealthRescanV1(
        self,
        requestId: object,
        pageEpoch: object,
        sessionEpoch: object,
    ) -> dict[str, object]:
        return self._submit_explicit(
            CommandId.C70,
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
        result="QVariantMap",
    )
    def getHealthRescanStatusV1(
        self,
        requestId: object,
        pageEpoch: object,
        sessionEpoch: object,
        scanId: object,
    ) -> dict[str, object]:
        return self._submit_explicit(
            CommandId.C71,
            (
                requestId,
                pageEpoch,
                sessionEpoch,
                scanId,
            ),
        )

    @Slot(
        "QVariant",
        "QVariant",
        "QVariant",
        "QVariant",
        result="QVariantMap",
    )
    def cancelHealthRescanV1(
        self,
        requestId: object,
        pageEpoch: object,
        sessionEpoch: object,
        scanId: object,
    ) -> dict[str, object]:
        return self._submit_explicit(
            CommandId.C72,
            (
                requestId,
                pageEpoch,
                sessionEpoch,
                scanId,
            ),
        )

    @Slot(
        "QVariant",
        "QVariant",
        "QVariant",
        result="QVariantMap",
    )
    def setUiFontScaleV1(
        self,
        requestId: object,
        pageEpoch: object,
        uiFontScale: object,
    ) -> dict[str, object]:
        return self._submit_explicit(
            CommandId.C73,
            (
                requestId,
                pageEpoch,
                uiFontScale,
            ),
        )

    @Slot(
        "QVariant",
        "QVariant",
        "QVariant",
        result="QVariantMap",
    )
    def removeRecentDatabaseV1(
        self,
        requestId: object,
        pageEpoch: object,
        recentDatabaseId: object,
    ) -> dict[str, object]:
        return self._submit_explicit(
            CommandId.C74,
            (
                requestId,
                pageEpoch,
                recentDatabaseId,
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

    @Slot(
        "QVariant",
        "QVariant",
        "QVariant",
        "QVariant",
        "QVariant",
        result="QVariantMap",
    )
    def retryRecordStrengthV1(
        self,
        requestId: object,
        pageEpoch: object,
        sessionEpoch: object,
        recordId: object,
        revision: object,
    ) -> dict[str, object]:
        return self._submit_explicit(
            CommandId.C75,
            (
                requestId,
                pageEpoch,
                sessionEpoch,
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
        "QVariant",
        "QVariant",
        result="QVariantMap",
    )
    def locateVaultAnchorV1(
        self,
        requestId: object,
        pageEpoch: object,
        sessionEpoch: object,
        recordId: object,
        query: object,
        filter: object,
        sort: object,
    ) -> dict[str, object]:
        return self._submit_explicit(
            CommandId.C76,
            (
                requestId,
                pageEpoch,
                sessionEpoch,
                recordId,
                query,
                filter,
                sort,
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
    def revealRecoveryCodeV1(
        self,
        requestId: object,
        pageEpoch: object,
        sessionEpoch: object,
        recordId: object,
        revision: object,
        codeIndex: object,
    ) -> dict[str, object]:
        return self._submit_explicit(
            CommandId.C77,
            (
                requestId,
                pageEpoch,
                sessionEpoch,
                recordId,
                revision,
                codeIndex,
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
    def copyRecoveryCodeV1(
        self,
        requestId: object,
        pageEpoch: object,
        sessionEpoch: object,
        recordId: object,
        revision: object,
        codeIndex: object,
    ) -> dict[str, object]:
        return self._submit_explicit(
            CommandId.C78,
            (
                requestId,
                pageEpoch,
                sessionEpoch,
                recordId,
                revision,
                codeIndex,
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
    def setRecoveryCodeUsedV1(
        self,
        requestId: object,
        pageEpoch: object,
        sessionEpoch: object,
        recordId: object,
        revision: object,
        codeIndex: object,
        used: object,
    ) -> dict[str, object]:
        return self._submit_explicit(
            CommandId.C79,
            (
                requestId,
                pageEpoch,
                sessionEpoch,
                recordId,
                revision,
                codeIndex,
                used,
            ),
        )

    @Slot(
        "QVariant",
        "QVariant",
        result="QVariantMap",
    )
    def contactSupportV1(
        self,
        requestId: object,
        pageEpoch: object,
    ) -> dict[str, object]:
        return self._submit_explicit(
            CommandId.C80,
            (
                requestId,
                pageEpoch,
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

    @Slot(
        "QVariant",
        "QVariant",
        result="QVariantMap",
    )
    def getUpdateStateV1(
        self,
        requestId: object,
        pageEpoch: object,
    ) -> dict[str, object]:
        return self._submit_explicit(
            CommandId.C82,
            (
                requestId,
                pageEpoch,
            ),
        )

    @Slot(
        "QVariant",
        "QVariant",
        result="QVariantMap",
    )
    def checkUpdatesV1(
        self,
        requestId: object,
        pageEpoch: object,
    ) -> dict[str, object]:
        return self._submit_explicit(
            CommandId.C83,
            (
                requestId,
                pageEpoch,
            ),
        )

    @Slot(
        "QVariant",
        "QVariant",
        "QVariant",
        "QVariant",
        result="QVariantMap",
    )
    def setUpdatePolicyV1(
        self,
        requestId: object,
        pageEpoch: object,
        enabled: object,
        days: object,
    ) -> dict[str, object]:
        return self._submit_explicit(
            CommandId.C84,
            (
                requestId,
                pageEpoch,
                enabled,
                days,
            ),
        )

    @Slot(
        "QVariant",
        "QVariant",
        "QVariant",
        "QVariant",
        result="QVariantMap",
    )
    def setUpdateReminderV1(
        self,
        requestId: object,
        pageEpoch: object,
        tag: object,
        action: object,
    ) -> dict[str, object]:
        return self._submit_explicit(
            CommandId.C85,
            (
                requestId,
                pageEpoch,
                tag,
                action,
            ),
        )

    @Slot(
        "QVariant",
        "QVariant",
        "QVariant",
        result="QVariantMap",
    )
    def openUpdateReleaseV1(
        self,
        requestId: object,
        pageEpoch: object,
        tag: object,
    ) -> dict[str, object]:
        return self._submit_explicit(
            CommandId.C86,
            (
                requestId,
                pageEpoch,
                tag,
            ),
        )
