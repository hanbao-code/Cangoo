package app.cangoo.android.ui

import android.hardware.biometrics.BiometricManager
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import app.cangoo.android.R
import androidx.compose.ui.res.stringResource
import androidx.compose.runtime.getValue
import androidx.compose.runtime.setValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.em
import androidx.compose.ui.unit.sp

@Composable
internal fun SystemAccessPage(snapshot: SystemAccessSnapshot?, guide: Boolean, onOpen: (SystemSettingsDestination) -> Boolean) {
    var failed by remember { mutableStateOf(false) }
    fun open(destination: SystemSettingsDestination) { failed = !onOpen(destination) }
    val colors = LocalBThemeColors.current
    if (guide) Text(stringResource(R.string.system_guide), color = colors.muted, fontSize = businessSp(14.sp), lineHeight = 1.6.em)
    SystemAccessCard(stringResource(R.string.clipboard)) {
        SystemAccessRow(stringResource(R.string.clipboard_read), stringResource(R.string.clipboard_read_hint), snapshot?.clipboardRead?.let { clipboardModeLabel(it) })
        HorizontalDivider(color = colors.line)
        SystemAccessRow(stringResource(R.string.clipboard_write), stringResource(R.string.clipboard_write_hint), snapshot?.clipboardWrite?.let { clipboardModeLabel(it) })
        TextButton(onClick = { open(SystemSettingsDestination.APPLICATION) }, modifier = Modifier.align(Alignment.End)) { Text(stringResource(R.string.open_settings)) }
    }
    SystemAccessCard(stringResource(R.string.background_optional)) {
        SystemAccessRow(stringResource(R.string.background_limit), stringResource(R.string.background_hint), snapshot?.let {
            when (it.backgroundRestricted) { true -> stringResource(R.string.restricted); false -> stringResource(R.string.unrestricted); null -> stringResource(R.string.confirm_system) }
        })
        HorizontalDivider(color = colors.line)
        SystemAccessRow(stringResource(R.string.battery_optimization), stringResource(R.string.battery_hint), snapshot?.let {
            when (it.batteryExempt) { true -> stringResource(R.string.not_optimized); false -> stringResource(R.string.system_managed); null -> stringResource(R.string.confirm_system) }
        })
        Row(Modifier.align(Alignment.End)) {
            TextButton(onClick = { open(SystemSettingsDestination.APPLICATION) }) { Text(stringResource(R.string.app_settings)) }
            TextButton(onClick = { open(SystemSettingsDestination.BATTERY) }) { Text(stringResource(R.string.battery_settings)) }
        }
    }
    SystemAccessCard(stringResource(R.string.system_biometrics)) {
        val status = snapshot?.let {
            when (it.biometricCapability) {
                BiometricManager.BIOMETRIC_SUCCESS -> if (it.strongBiometricQuery) stringResource(R.string.available) else stringResource(R.string.confirm_strong)
                BiometricManager.BIOMETRIC_ERROR_NONE_ENROLLED -> stringResource(R.string.not_enrolled)
                BiometricManager.BIOMETRIC_ERROR_NO_HARDWARE -> stringResource(R.string.not_supported)
                BiometricManager.BIOMETRIC_ERROR_SECURITY_UPDATE_REQUIRED -> stringResource(R.string.update_required)
                BiometricManager.BIOMETRIC_ERROR_HW_UNAVAILABLE -> stringResource(R.string.unavailable_now)
                else -> stringResource(R.string.confirm_system)
            }
        }
        SystemAccessRow(snapshot?.biometricName ?: stringResource(R.string.system_strong), stringResource(R.string.vault_biometric_separate), status)
        if (snapshot?.biometricCapability != BiometricManager.BIOMETRIC_ERROR_NO_HARDWARE) {
            TextButton(onClick = { open(SystemSettingsDestination.BIOMETRIC) }, modifier = Modifier.align(Alignment.End)) { Text(stringResource(R.string.phone_settings)) }
        }
    }
    if (failed) Text(stringResource(R.string.system_settings_failed), color = colors.error, fontSize = businessSp(14.sp), lineHeight = 1.5.em)
}

@Composable
private fun SystemAccessCard(title: String, content: @Composable androidx.compose.foundation.layout.ColumnScope.() -> Unit) {
    val colors = LocalBThemeColors.current
    Surface(shape = RoundedCornerShape(17.dp), color = colors.surface, modifier = Modifier.fillMaxWidth()) {
        Column(Modifier.padding(horizontal = 16.dp, vertical = 12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text(title, color = colors.ink, fontSize = businessSp(17.sp), lineHeight = 1.5.em, fontWeight = FontWeight.SemiBold,
                modifier = Modifier.semantics { heading() })
            content()
        }
    }
}

@Composable
private fun SystemAccessRow(name: String, purpose: String, status: String?) {
    val colors = LocalBThemeColors.current
    Row(Modifier.fillMaxWidth().padding(vertical = 9.dp), horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.CenterVertically) {
        Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(4.dp)) {
            Text(name, color = colors.ink, fontSize = businessSp(15.sp), lineHeight = 1.5.em)
            Text(purpose, color = colors.muted, fontSize = businessSp(12.sp), lineHeight = 1.6.em)
        }
        Text(status ?: stringResource(R.string.reading), color = colors.muted, fontSize = businessSp(13.sp), lineHeight = 1.5.em,
            textAlign = TextAlign.End, modifier = Modifier.widthIn(max = 125.dp))
    }
}

@Composable
private fun clipboardModeLabel(mode: ClipboardAccessMode): String = stringResource(when (mode) {
    ClipboardAccessMode.ALLOWED -> R.string.allowed
    ClipboardAccessMode.FOREGROUND -> R.string.foreground_only
    ClipboardAccessMode.DENIED -> R.string.denied
    ClipboardAccessMode.DEFAULT -> R.string.system_default
    ClipboardAccessMode.UNKNOWN -> R.string.confirm_system
})
