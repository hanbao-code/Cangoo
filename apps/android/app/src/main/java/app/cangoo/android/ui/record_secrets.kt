package app.cangoo.android.ui

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import app.cangoo.android.R
import androidx.compose.ui.platform.LocalResources
import androidx.compose.runtime.Composable
import androidx.compose.runtime.key
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.unit.em

enum class RecordSecretField { TOTP, RECOVERY_CODES }
enum class RecordSecretIntent { KEEP, REPLACE, REMOVE }
data class RecordSecretChange(val field: RecordSecretField, val intent: RecordSecretIntent)

// 新输入和意图只属于当前内存草稿，既有密钥及整组码值不回填。
data class RecordSecretDraft(
    val totpInput: String = "",
    val recoveryInput: String = "",
    val totpIntent: RecordSecretIntent = RecordSecretIntent.KEEP,
    val recoveryIntent: RecordSecretIntent = RecordSecretIntent.KEEP,
    val totpShown: Boolean = false,
    val recoveryShown: Boolean = false,
    val confirmation: RecordSecretChange? = null,
    val reloadLatest: Boolean = false,
) {
    val hasChanges: Boolean get() = totpInput.isNotEmpty() || recoveryInput.isNotEmpty() ||
        totpIntent != RecordSecretIntent.KEEP || recoveryIntent != RecordSecretIntent.KEEP
    override fun toString() = "RecordSecretDraft(内容已隐藏)"
}

data class RecordSecretView(
    val hasTotp: Boolean = false,
    val stale: Boolean = false,
    val recoveryUsed: List<Boolean> = emptyList(),
    val totpCode: String = "",
    val totpRemaining: Int = 0,
    val totpValidUntilEpochSeconds: Long = 0,
    val totpError: UiText = UiText.Empty,
    val recoveryValues: Map<Int, String> = emptyMap(),
    val recoveryPending: Set<Int> = emptySet(),
    val recoveryErrors: Map<Int, UiText> = emptyMap(),
) {
    override fun toString() = "RecordSecretView(内容已隐藏)"
}

@Composable
internal fun BNewTotpSwitchMark(checked: Boolean) {
    val colors = LocalBThemeColors.current
    Canvas(Modifier.size(42.dp, 25.dp)) {
        drawRoundRect(if (checked) colors.controlOn else colors.controlOff, cornerRadius = CornerRadius(size.height / 2))
        val inset = 3.dp.toPx()
        val radius = 9.5.dp.toPx()
        drawCircle(if (checked) colors.onAccent else Color.White, radius, Offset(if (checked) size.width - inset - radius else inset + radius, size.height / 2))
    }
}

@Composable
internal fun BSecretEditSection(
    title: String, status: String, exists: Boolean, intent: RecordSecretIntent, enabled: Boolean,
    onReplace: () -> Unit, onRemove: () -> Unit, onKeep: () -> Unit, input: @Composable () -> Unit,
) {
    val texts = LocalResources.current
    val colors = LocalBThemeColors.current
    Column(Modifier.fillMaxWidth(), verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Text(title, color = colors.ink, lineHeight = (24f / 15).em, fontSize = businessSp(15.sp), fontWeight = FontWeight.SemiBold)
        if (exists) {
            Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                Text(when (intent) {
                    RecordSecretIntent.KEEP -> status
                    RecordSecretIntent.REPLACE -> texts.getString(R.string.replace_after_save)
                    RecordSecretIntent.REMOVE -> texts.getString(R.string.remove_after_save)
                }, Modifier.weight(1f), color = colors.muted, fontSize = businessSp(13.sp), lineHeight = (21f / 13).em)
                if (intent != RecordSecretIntent.KEEP) TextButton(onClick = onKeep, enabled = enabled) { Text(texts.getString(R.string.keep_existing)) }
            }
            if (intent == RecordSecretIntent.KEEP) Row {
                TextButton(onClick = onReplace, enabled = enabled) { Text(texts.getString(R.string.replace)) }
                TextButton(onClick = onRemove, enabled = enabled) { Text(texts.getString(R.string.remove), color = colors.error) }
            }
        }
        if (!exists || intent == RecordSecretIntent.REPLACE) input()
    }
}

@Composable
internal fun BTotpDetails(view: RecordSecretView, enabled: Boolean, onEdit: () -> Unit, onReload: () -> Unit, onCopy: () -> Unit) {
    val texts = LocalResources.current
    val colors = LocalBThemeColors.current
    Surface(color = colors.soft, shape = RoundedCornerShape(17.dp)) {
        Column(Modifier.fillMaxWidth().padding(horizontal = 18.dp, vertical = 17.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                Text(texts.getString(R.string.one_time_code), color = colors.muted, lineHeight = (24f / 14).em, fontSize = businessSp(14.sp))
                Row(verticalAlignment = Alignment.CenterVertically) {
                    if (view.totpCode.isNotEmpty()) Text(texts.getQuantityString(R.plurals.seconds_count, view.totpRemaining, view.totpRemaining), lineHeight = (24f / 13).em, fontSize = businessSp(13.sp),
                        color = if (view.totpRemaining <= 5) colors.warningInk else colors.muted)
                    TextButton(onClick = onCopy, enabled = enabled && view.totpCode.isNotEmpty()) { Text(texts.getString(R.string.copy)) }
                }
            }
            if (view.totpError.isNotEmpty()) {
                Text(view.totpError.localized(), color = colors.error, fontSize = businessSp(13.sp), lineHeight = (22f / 13).em,
                    modifier = Modifier.semantics { liveRegion = LiveRegionMode.Polite })
                Row {
                    TextButton(onClick = onEdit, enabled = enabled) { Text(texts.getString(R.string.edit_setup_key)) }
                    TextButton(onClick = onReload, enabled = enabled) { Text(texts.getString(R.string.reload)) }
                }
            } else {
                val code = view.totpCode
                Text(if (code.length == 6) "${code.take(3)} ${code.drop(3)}" else "••• •••", color = colors.ink,
                    fontFamily = FontFamily.Monospace, fontSize = businessSp(31.sp), letterSpacing = 4.sp, lineHeight = 1.8.em, fontWeight = FontWeight.Medium, softWrap = false)
                Canvas(Modifier.fillMaxWidth().height(3.dp)) {
                    val radius = CornerRadius(size.height / 2)
                    drawRoundRect(colors.progressTrack, cornerRadius = radius)
                    if (view.totpRemaining > 0) drawRoundRect(if (view.totpRemaining <= 5) colors.warningInk else colors.progressFill,
                        size = Size(size.width * view.totpRemaining / 30f, size.height), cornerRadius = radius)
                }
            }
        }
    }
}

@Composable
internal fun BRecoveryCodeDetails(
    view: RecordSecretView, enabled: Boolean, onToggle: (Int) -> Unit, onUsed: (Int, Boolean) -> Unit, onReload: () -> Unit, onCopy: (Int) -> Unit,
) {
    val texts = LocalResources.current
    val colors = LocalBThemeColors.current
    Column(Modifier.fillMaxWidth(), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Text(texts.getQuantityString(R.plurals.recovery_count, view.recoveryUsed.size, view.recoveryUsed.size), color = colors.ink, lineHeight = (24f / 15).em, fontSize = businessSp(15.sp), fontWeight = FontWeight.SemiBold)
        view.recoveryUsed.forEachIndexed { index, used -> key(index) {
            Surface(color = colors.surface, shape = RoundedCornerShape(18.dp), border = BorderStroke(1.dp, colors.line)) {
                Column(Modifier.fillMaxWidth().padding(horizontal = 16.dp).padding(top = 8.dp, bottom = 16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                        Text(texts.getString(R.string.recovery_item_status, index + 1, texts.getString(if (used) R.string.used_locally else R.string.not_marked_used)), Modifier.weight(1f), color = colors.muted, lineHeight = (24f / 13).em, fontSize = businessSp(13.sp))
                        TextButton(onClick = { onToggle(index) }, enabled = enabled && index !in view.recoveryPending) {
                            Text(if (index in view.recoveryPending) texts.getString(R.string.loading) else if (index in view.recoveryValues) texts.getString(R.string.hide) else texts.getString(R.string.show))
                        }
                    }
                    Text(view.recoveryValues[index] ?: "••••••••••••", color = colors.ink, fontSize = businessSp(19.sp), lineHeight = (31f / 19).em,
                        fontFamily = FontFamily.Monospace, softWrap = false, modifier = Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()))
                    Row {
                        TextButton(onClick = { onCopy(index) }, enabled = enabled && index !in view.recoveryPending) { Text(texts.getString(R.string.copy)) }
                        TextButton(onClick = { onUsed(index, !used) }, enabled = enabled && index !in view.recoveryPending) { Text(if (used) texts.getString(R.string.undo_used) else texts.getString(R.string.mark_used)) }
                    }
                    view.recoveryErrors[index]?.let { error ->
                        Text(error.localized(), color = colors.error, fontSize = businessSp(13.sp), lineHeight = (22f / 13).em,
                            modifier = Modifier.semantics { liveRegion = LiveRegionMode.Polite })
                        TextButton(onClick = onReload, enabled = enabled) { Text(texts.getString(R.string.reload_record)) }
                    }
                }
            }
        } }
    }
}
