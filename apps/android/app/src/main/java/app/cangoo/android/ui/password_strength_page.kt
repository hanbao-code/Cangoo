package app.cangoo.android.ui

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import app.cangoo.android.R
import androidx.compose.ui.platform.LocalResources
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.platform.LocalFocusManager
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.ProgressBarRangeInfo
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.progressBarRangeInfo
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.PlatformTextStyle
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.unit.em

// 只呈现受控正文；输入槽、任务归属、标题与滚动均由父层提供。
@Composable
internal fun BPasswordStrengthPage(
    shown: Boolean,
    hasInput: Boolean,
    overLimit: Boolean,
    result: PasswordStrengthResult?,
    pending: Boolean,
    error: String,
    onReveal: () -> Unit,
    onClear: () -> Unit,
    onCancel: () -> Unit,
    onRetry: () -> Unit,
    inputSlot: @Composable () -> Unit,
    modifier: Modifier = Modifier,
) {
    val texts = LocalResources.current
    val colors = LocalBThemeColors.current
    Column(modifier.fillMaxWidth()) {
        inputSlot()
        Spacer(Modifier.height(20.dp))
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(14.dp, Alignment.CenterHorizontally)) {
            StrengthAction(if (shown) texts.getString(R.string.hide) else texts.getString(R.string.show), if (shown) "eye_closed" else "eye_open", onReveal)
            StrengthAction(texts.getString(R.string.clear), "cross", onClear)
        }
        Spacer(Modifier.height(27.dp))
        when {
            overLimit -> StrengthError(texts.getString(R.string.strength_limit))
            hasInput && pending -> Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.SpaceBetween) {
                Text(texts.getString(R.string.analyzing), color = colors.ink, lineHeight = (24f / 16).em, fontSize = businessSp(16.sp), modifier = Modifier.semantics { liveRegion = LiveRegionMode.Polite })
                StrengthAction(texts.getString(R.string.cancel_analysis), "cross", onCancel)
            }
            hasInput && result != null -> Column(Modifier.fillMaxWidth().background(colors.surface, RoundedCornerShape(18.dp)).padding(24.dp)) {
                Text(texts.getString(result.labelResource), color = colors.ink, fontSize = businessSp(20.sp), lineHeight = 1.4.em, fontWeight = FontWeight.Bold,
                    modifier = Modifier.semantics { heading() }, style = TextStyle(platformStyle = PlatformTextStyle(includeFontPadding = false), lineHeightStyle = BLineHeightStyle))
                Spacer(Modifier.height(18.dp))
                Canvas(Modifier.fillMaxWidth().height(7.dp).semantics {
                    contentDescription = texts.getString(R.string.password_strength)
                    progressBarRangeInfo = ProgressBarRangeInfo(result.score.toFloat(), 0f..4f)
                }) {
                    val radius = CornerRadius(size.height / 2)
                    drawRoundRect(colors.progressTrack, cornerRadius = radius)
                    if (result.score > 0) drawRoundRect(colors.strengthMeter, size = Size(size.width * result.score / 4f, size.height), cornerRadius = radius)
                }
                Spacer(Modifier.height(18.dp))
                Text(texts.getString(result.adviceResource), color = colors.muted, fontSize = businessSp(14.sp), lineHeight = 1.9.em,
                    style = TextStyle(platformStyle = PlatformTextStyle(includeFontPadding = false), lineHeightStyle = BLineHeightStyle))
            }
            else -> Column(Modifier.fillMaxWidth().padding(vertical = 35.dp, horizontal = 10.dp), horizontalAlignment = Alignment.CenterHorizontally) {
                Icon(bIcon("mixer"), null, Modifier.size(34.dp).alpha(0.6f), tint = colors.muted)
                Spacer(Modifier.height(15.dp))
                Text(texts.getString(R.string.strength_empty), color = colors.ink, fontSize = businessSp(16.sp), lineHeight = 1.5.em, fontWeight = FontWeight.Bold, textAlign = TextAlign.Center,
                    style = TextStyle(platformStyle = PlatformTextStyle(includeFontPadding = false), lineHeightStyle = BLineHeightStyle))
                Spacer(Modifier.height(8.dp))
                Text(texts.getString(R.string.strength_local), color = colors.muted, fontSize = businessSp(13.sp), lineHeight = 1.8.em, textAlign = TextAlign.Center,
                    style = TextStyle(platformStyle = PlatformTextStyle(includeFontPadding = false), lineHeightStyle = BLineHeightStyle))
            }
        }
        if (error.isNotEmpty() && !overLimit) StrengthError(error)
        if (hasInput && !overLimit && !pending && result == null) StrengthAction(texts.getString(R.string.reanalyze), "mixer", onRetry)
    }
}

@Composable
private fun StrengthAction(label: String, icon: String, onClick: () -> Unit) {
    val colors = LocalBThemeColors.current
    val focus = LocalFocusManager.current
    Row(
        Modifier.clip(RoundedCornerShape(11.dp)).background(colors.soft)
            .clickable(role = Role.Button) { focus.clearFocus(); onClick() }.heightIn(min = 48.dp).padding(horizontal = 16.dp, vertical = 9.dp),
        verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        Icon(bIcon(icon), null, Modifier.size(18.dp), tint = colors.ink)
        Text(label, color = colors.ink, fontSize = businessSp(14.sp), lineHeight = 1.5.em, style = TextStyle(platformStyle = PlatformTextStyle(includeFontPadding = false), lineHeightStyle = BLineHeightStyle))
    }
}

@Composable
private fun StrengthError(message: String) {
    val colors = LocalBThemeColors.current
    Text(message, color = colors.error, fontSize = businessSp(13.sp), lineHeight = 1.5.em,
        modifier = Modifier.fillMaxWidth().padding(vertical = 14.dp).background(colors.surface).drawBehind {
            val x = 1.5.dp.toPx()
            drawLine(colors.error, Offset(x, 0f), Offset(x, size.height), strokeWidth = 3.dp.toPx())
        }.padding(horizontal = 12.dp, vertical = 8.dp).semantics { liveRegion = LiveRegionMode.Assertive },
        style = TextStyle(platformStyle = PlatformTextStyle(includeFontPadding = false), lineHeightStyle = BLineHeightStyle))
}
