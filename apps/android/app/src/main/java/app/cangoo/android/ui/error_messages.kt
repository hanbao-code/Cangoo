package app.cangoo.android.ui

import app.cangoo.android.R
import app.cangoo.android.BuildConfig
import app.cangoo.android.data.*

internal fun VaultError.uiText(): UiText = UiText(when (this) {
    VaultError.BIOMETRIC_UNAVAILABLE -> R.string.vault_error_biometric_unavailable
    VaultError.INVALID_INPUT -> R.string.vault_error_invalid_input
    VaultError.DUPLICATE_NAME -> R.string.vault_error_duplicate_name
    VaultError.AUTHENTICATION_FAILED -> R.string.vault_error_authentication_failed
    VaultError.DATA_UNAVAILABLE -> R.string.vault_error_data_unavailable
    VaultError.STORAGE_FAILED -> R.string.vault_error_storage_failed
    VaultError.COMMIT_UNCERTAIN -> R.string.vault_error_commit_uncertain
    VaultError.SESSION_CLOSED -> R.string.vault_error_session_closed
    VaultError.RECORD_MISSING -> R.string.vault_error_record_missing
    VaultError.REVISION_CONFLICT -> R.string.vault_error_revision_conflict
    VaultError.MIGRATION_PROTECTION_FAILED -> R.string.vault_error_migration_protection_failed
    VaultError.RECOVERY_FAILED -> R.string.vault_error_recovery_failed
    VaultError.INVALID_TOTP -> R.string.vault_error_invalid_totp
    VaultError.INVALID_RECOVERY_CODES -> R.string.vault_error_invalid_recovery_codes
})

internal fun BackupDocumentProblem.uiText(): UiText = UiText(when (this) {
    BackupDocumentProblem.LOCAL_LOCATION -> R.string.document_error_local_location
    BackupDocumentProblem.ACCESS -> R.string.document_error_access
    BackupDocumentProblem.LIMIT -> R.string.document_error_limit
    BackupDocumentProblem.SOURCE -> R.string.document_error_source
    BackupDocumentProblem.NAME -> R.string.document_error_name
    BackupDocumentProblem.CHANGED -> R.string.document_error_changed
    BackupDocumentProblem.IO -> R.string.document_error_io
    BackupDocumentProblem.CANCELLED -> R.string.document_error_cancelled
})

internal fun BackupStoreProblem.uiText(): UiText = UiText(when (this) {
    BackupStoreProblem.STALE -> R.string.backup_store_error_stale
    BackupStoreProblem.DECISIONS -> R.string.backup_store_error_decisions
    BackupStoreProblem.CANCELLED -> R.string.backup_store_error_cancelled
    BackupStoreProblem.LIMIT -> R.string.backup_store_error_limit
    BackupStoreProblem.INPUT -> R.string.backup_store_error_input
    BackupStoreProblem.VERIFICATION -> R.string.backup_store_error_verification
})

internal fun BackupProblem.uiText(): UiText = UiText(when (this) {
    BackupProblem.FORMAT -> R.string.backup_error_format
    BackupProblem.LIMIT -> R.string.backup_error_limit
    BackupProblem.MEMORY -> R.string.backup_error_memory
    BackupProblem.PASSWORD -> R.string.backup_error_password
    BackupProblem.AUTHENTICATION -> R.string.backup_error_authentication
    BackupProblem.IO -> R.string.backup_error_io
})

internal fun DeletionStatus.uiText(): UiText = UiText(when (this) {
    DeletionStatus.NOT_REMOVED -> R.string.deletion_status_not_removed
    DeletionStatus.REMOVED -> R.string.deletion_status_removed
    DeletionStatus.REMOVED_RESIDUAL -> R.string.deletion_status_removed_residual
    DeletionStatus.UNCERTAIN -> R.string.deletion_status_uncertain
})

internal fun BackupDocumentCleanup.uiText(): UiText = UiText(when (this) {
    BackupDocumentCleanup.PUBLISHED -> R.string.document_cleanup_published
    BackupDocumentCleanup.DELETED -> R.string.document_cleanup_deleted
    BackupDocumentCleanup.RESIDUAL -> R.string.document_cleanup_residual
    BackupDocumentCleanup.OWNERSHIP_LOST -> R.string.document_cleanup_ownership_lost
})

internal fun BackupPrivateCleanup.uiText(): UiText = UiText(when (this) {
    BackupPrivateCleanup.REMOVED -> R.string.private_cleanup_removed
    BackupPrivateCleanup.RESIDUAL -> R.string.private_cleanup_residual
})

internal fun RecoveryCodeProblem.uiText(): UiText = UiText(when (this) {
    RecoveryCodeProblem.INVALID -> R.string.recovery_error_invalid
    RecoveryCodeProblem.LIMIT -> R.string.recovery_error_limit
    RecoveryCodeProblem.DUPLICATE -> R.string.recovery_error_duplicate
})

internal fun cleanupText(status: VaultCleanupStatus): UiText {
    if (status.complete) return UiText.Empty
    val categories = status.categories.ifEmpty { setOf(VaultCleanupCategory.UNVERIFIED) }
    return VaultCleanupCategory.entries.filter { it in categories }.map { UiText(when (it) {
        VaultCleanupCategory.OLD_CIPHERTEXT -> R.string.vault_cleanup_old_ciphertext
        VaultCleanupCategory.DEVICE_BINDING -> R.string.vault_cleanup_device_binding
        VaultCleanupCategory.RETAINED_RECOVERY -> R.string.vault_cleanup_retained_recovery
        VaultCleanupCategory.OTHER_FILES -> R.string.vault_cleanup_other_files
        VaultCleanupCategory.UNVERIFIED -> R.string.vault_cleanup_unverified
    }) }.fold(UiText.Empty) { result, message -> result + message }
}

internal fun DeletionOutcome.uiText(): UiText = status.uiText() + cleanupText(bindingCleanup)

internal fun BackupDocumentException.uiText(): UiText = problem.uiText() +
    if (BuildConfig.DEBUG && problem == BackupDocumentProblem.CHANGED && diagnostic != null)
        UiText(R.string.diagnostic_code, listOf(diagnostic.code)) else UiText.Empty
