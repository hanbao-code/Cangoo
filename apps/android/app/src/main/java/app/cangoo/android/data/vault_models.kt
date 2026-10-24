package app.cangoo.android.data

import java.nio.charset.CharacterCodingException

data class VaultInfo(
    val id: String,
    val name: String,
    val hasMasterPassword: Boolean,
    val available: Boolean = true,
    val biometricEnabled: Boolean = false,
)

data class PasswordDraft(
    val title: String,
    val account: String = "",
    val password: String = "",
    val notes: String = "",
    val favorite: Boolean = false,
) {
    override fun toString() = "PasswordDraft(内容已隐藏)"
}

data class PasswordSummary(
    val id: String,
    val title: String,
    val account: String,
    val updatedAt: String,
    val favorite: Boolean = false,
    val revision: Long = 1,
    val hasTotp: Boolean = false,
    val recoveryCodeCount: Int = 0,
    val titleTruncated: Boolean = false,
    val accountTruncated: Boolean = false,
) {
    override fun toString() = "PasswordSummary(内容已隐藏)"
}

data class NoteDraft(val title: String, val content: String = "", val favorite: Boolean = false) {
    override fun toString() = "NoteDraft(内容已隐藏)"
}

data class NoteSummary(
    val id: String,
    val title: String,
    val preview: String,
    val updatedAt: String,
    val favorite: Boolean,
    val revision: Long,
    val titleTruncated: Boolean = false,
) {
    override fun toString() = "NoteSummary(内容已隐藏)"
}

data class PasswordChecks(
    val checkedCount: Int = 0,
    val weakIds: Set<String> = emptySet(),
    val repeatedIds: Set<String> = emptySet(),
    val pendingEpochs: Map<String, Long> = emptyMap(),
    val revision: Long = 0L,
) {
    val ratedCount: Int get() = checkedCount - pendingEpochs.size
    val warningIds: Set<String> get() = weakIds + repeatedIds
}

internal class PasswordStrengthSnapshot(val vaultId: String, val session: Long, val id: String, val epoch: Long,
    var title: String, var account: String, var password: String) {
    fun clear() { title = ""; account = ""; password = "" }
    override fun toString() = "PasswordStrengthSnapshot(内容已隐藏)"
}

enum class VaultError(val text: String) {
    BIOMETRIC_UNAVAILABLE("快捷解锁未能完成，请改用本库主密码。"),
    INVALID_INPUT("输入为空、包含无效字符或超出长度限制，请检查后重试。"),
    DUPLICATE_NAME("名称已存在，请换一个名称。"),
    AUTHENTICATION_FAILED("主密码不正确，或密码库认证信息已损坏。"),
    DATA_UNAVAILABLE("密码库文件缺失、损坏或版本不受支持，原文件已保留。"),
    STORAGE_FAILED("未能完成存储操作，请检查可用空间后重试。"),
    COMMIT_UNCERTAIN("提交结果暂时无法核实，请重新读取密码库列表确认实际名称，再重新认证。"),
    SESSION_CLOSED("密码库已锁定，请重新解锁。"),
    RECORD_MISSING("这条记录已不存在，请返回列表重试。"),
    REVISION_CONFLICT("这条记录已变化，请重新读取后再确认修改；本次内容未保存。"),
    MIGRATION_PROTECTION_FAILED("旧结构升级前未能核实加密恢复副本或日志一致性，原库已保留。"),
    RECOVERY_FAILED("未能核实密码库的原生回滚恢复，请保留现存文件后重试。"),
    INVALID_TOTP("动态口令密钥格式无效，请检查后重试。"),
    INVALID_RECOVERY_CODES("恢复码格式、数量或长度无效，请检查后重试。"),
}

class VaultException(val code: VaultError) : Exception(code.text)

internal fun vaultCleanupNotice(status: VaultCleanupStatus): String {
    if (status.complete) return ""
    val categories = status.categories.ifEmpty { setOf(VaultCleanupCategory.UNVERIFIED) }
    return VaultCleanupCategory.entries.filter { it in categories }.joinToString("") {
        when (it) {
            VaultCleanupCategory.OLD_CIPHERTEXT -> "使用旧主密码的加密文件仍有残留。"
            VaultCleanupCategory.DEVICE_BINDING -> "旧快捷解锁绑定尚未清理完成。"
            VaultCleanupCategory.RETAINED_RECOVERY -> "当前主密码对应的恢复配套仍保留。"
            VaultCleanupCategory.OTHER_FILES -> "其他文件尚未清理完成。"
            VaultCleanupCategory.UNVERIFIED -> "部分安全清理结果暂时无法核实。"
        }
    }
}

internal fun validatedUtf8(value: String, maxCharacters: Int, maxBytes: Int = maxCharacters * 4): ByteArray {
    if ('\u0000' in value || value.codePointCount(0, value.length) > maxCharacters) {
        throw VaultException(VaultError.INVALID_INPUT)
    }
    val bytes = try {
        value.encodeToByteArray(throwOnInvalidSequence = true)
    } catch (_: CharacterCodingException) {
        throw VaultException(VaultError.INVALID_INPUT)
    }
    if (bytes.size > maxBytes) {
        bytes.fill(0)
        throw VaultException(VaultError.INVALID_INPUT)
    }
    return bytes
}

internal fun validateDraft(draft: PasswordDraft, previous: PasswordRecord? = null) {
    if (draft.title != previous?.title) {
        if (draft.title.isBlank()) throw VaultException(VaultError.INVALID_INPUT)
        validatedUtf8(draft.title, 256).fill(0)
    }
    listOf(Triple(draft.account, previous?.account, 256), Triple(draft.password, previous?.password, 1024), Triple(draft.notes, previous?.notes, 8192))
        .forEach { (text, original, limit) -> if (text != original) validatedUtf8(text, limit).fill(0) }
}

internal fun validateDraft(draft: NoteDraft, previous: NoteRecord? = null) {
    if (draft.title != previous?.title) {
        if (draft.title.isBlank()) throw VaultException(VaultError.INVALID_INPUT)
        validatedUtf8(draft.title, 256).fill(0)
    }
    if (draft.content != previous?.content) validatedUtf8(draft.content, 65536).fill(0)
}

internal fun textPreview(value: String): String = value.substring(0, value.offsetByCodePoints(0, minOf(128, value.codePointCount(0, value.length))))

fun PasswordRecord.toSummary(): PasswordSummary = PasswordSummary(
    id, textPreview(title), textPreview(account), updatedAt, favorite, revision,
    totpSecret.isNotEmpty(), checkedRecoveryCodes(recoveryCodesJson).size,
    title.codePointCount(0, title.length) > 128, account.codePointCount(0, account.length) > 128,
)

fun NoteRecord.toSummary(): NoteSummary = NoteSummary(id, textPreview(title), textPreview(content.substringBefore('\n').substringBefore('\r')), updatedAt, favorite, revision,
    title.codePointCount(0, title.length) > 128)

internal fun checkedRecoveryCodes(json: String): List<RecoveryCode> = try { decodeRecoveryCodes(json) }
catch (_: RecoveryCodeException) { throw VaultException(VaultError.DATA_UNAVAILABLE) }
