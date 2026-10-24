package app.cangoo.android.ui

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import app.cangoo.android.R
import androidx.compose.ui.platform.LocalResources
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.PlatformTextStyle
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.unit.em
import app.cangoo.android.data.DeletionPreview
import app.cangoo.android.data.VaultInfo

internal data class VaultDeletionUiState(val target: VaultInfo? = null, val preview: DeletionPreview? = null, val master: String = "") {
    override fun toString() = "VaultDeletionUiState(内容已隐藏)"
}

// 只呈现父层绑定的删除目标；输入、认证、危险确认和滚动均由父层持有。
@Composable
internal fun BVaultDeletionPage(
    targetName: String,
    hasMaster: Boolean,
    preview: DeletionPreview?,
    busy: Boolean,
    inputSlot: @Composable () -> Unit,
    modifier: Modifier = Modifier,
) {
    val texts = LocalResources.current
    val colors = LocalBThemeColors.current
    val textStyle = TextStyle(platformStyle = PlatformTextStyle(includeFontPadding = false), lineHeightStyle = BLineHeightStyle)
    Column(modifier.fillMaxWidth()) {
        Column(Modifier.fillMaxWidth().padding(top = 20.dp, bottom = 4.dp)) {
            Text(targetName, color = colors.ink, fontSize = businessSp(20.sp), lineHeight = 1.4.em,
                letterSpacing = (-0.3).sp, fontWeight = FontWeight.Bold, style = textStyle,
                modifier = Modifier.fillMaxWidth().semantics { heading() })
            Text(
                when {
                    preview != null -> texts.getString(R.string.appearance_summary,
                        texts.getQuantityString(R.plurals.password_count, if (preview.passwordCount == 1L) 1 else 2, preview.passwordCount),
                        texts.getQuantityString(R.plurals.note_count, if (preview.noteCount == 1L) 1 else 2, preview.noteCount))
                    busy -> texts.getString(R.string.verify_count)
                    else -> texts.getString(R.string.verify_before_delete)
                },
                color = colors.muted, fontSize = businessSp(16.sp), lineHeight = 1.5.em, style = textStyle,
                modifier = Modifier.fillMaxWidth().padding(top = 10.dp).semantics { liveRegion = LiveRegionMode.Polite },
            )
        }
        Surface(color = colors.soft, shape = RoundedCornerShape(12.dp),
            modifier = Modifier.fillMaxWidth().padding(vertical = 20.dp)) {
            Text(
                if (preview == null) texts.getString(R.string.delete_vault_before)
                else texts.getString(R.string.delete_vault_after),
                color = colors.ink, fontSize = businessSp(13.sp), lineHeight = 1.8.em, style = textStyle,
                modifier = Modifier.padding(14.dp),
            )
        }
        inputSlot()
        if (!hasMaster) Text(texts.getString(R.string.empty_master_verify),
            color = colors.muted, fontSize = businessSp(13.sp), lineHeight = 1.8.em, style = textStyle,
            modifier = Modifier.fillMaxWidth().padding(top = 14.dp))
    }
}
