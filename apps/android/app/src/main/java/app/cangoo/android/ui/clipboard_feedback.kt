package app.cangoo.android.ui

import android.os.SystemClock
import android.content.res.Resources
import app.cangoo.android.R
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.IntrinsicSize
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Surface
import androidx.compose.material3.SnackbarDuration
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.SnackbarResult
import androidx.compose.material3.SnackbarVisuals
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.Alignment
import androidx.compose.ui.platform.LocalResources
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.em
import androidx.compose.ui.unit.sp

internal data class ClipboardFeedbackMessage(
    val id: Long,
    val text: UiText,
    val issuedAtElapsedRealtime: Long,
    val retryClear: Boolean = false,
)

internal class ShortFeedbackVisuals(
    val text: UiText,
    resources: Resources,
    override val duration: SnackbarDuration,
    val action: UiText? = null,
) : SnackbarVisuals {
    override val message = text.resolve(resources)
    override val actionLabel = action?.resolve(resources)
    override val withDismissAction = true
}

@Composable
internal fun ClipboardFeedback(model: VaultModel, modifier: Modifier = Modifier) {
    val message = model.clipboardFeedback
    val host = remember { SnackbarHostState() }
    val resources = LocalResources.current
    LaunchedEffect(message?.id) {
        if (message != null) {
            if (SystemClock.elapsedRealtime() - message.issuedAtElapsedRealtime < 4_000L) {
                val result = host.showSnackbar(ShortFeedbackVisuals(message.text, resources, SnackbarDuration.Short,
                    action = if (message.retryClear && model.clipboardDuty != null) UiText(R.string.retry) else null))
                if (result == SnackbarResult.ActionPerformed && model.clipboardFeedback?.id == message.id) model.clearClipboard()
            }
            model.dismissClipboardFeedback(message.id)
        }
    }
    ShortFeedbackHost(host, modifier)
}

@Composable
internal fun ShortFeedbackHost(host: SnackbarHostState, modifier: Modifier = Modifier) {
    val colors = MaterialTheme.colorScheme
    val resources = LocalResources.current
    SnackbarHost(host, modifier.padding(horizontal = 24.dp, vertical = 8.dp)) { data ->
        val localized = data.visuals as? ShortFeedbackVisuals
        Surface(shape = RoundedCornerShape(16.dp), color = colors.inverseSurface, contentColor = colors.inverseOnSurface,
            shadowElevation = 4.dp,
            modifier = Modifier.width(IntrinsicSize.Max).semantics { liveRegion = LiveRegionMode.Polite }) {
            Column(Modifier.padding(start = 16.dp, end = 4.dp, top = 4.dp, bottom = 4.dp)) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text(localized?.text?.resolve(resources) ?: data.visuals.message, Modifier.weight(1f), fontSize = businessSp(14.sp), lineHeight = 1.5.em)
                    IconButton(onClick = data::dismiss, modifier = Modifier.size(48.dp)) {
                        Icon(bIcon("cross"), stringResource(R.string.close_feedback), Modifier.size(18.dp), tint = colors.inverseOnSurface)
                    }
                }
                data.visuals.actionLabel?.let { label ->
                    TextButton(onClick = data::performAction, modifier = Modifier.align(Alignment.End)) {
                        Text(localized?.action?.resolve(resources) ?: label, color = colors.inversePrimary, fontSize = businessSp(14.sp), lineHeight = 1.5.em)
                    }
                }
            }
        }
    }
}
