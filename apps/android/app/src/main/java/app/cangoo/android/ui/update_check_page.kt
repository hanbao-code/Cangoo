package app.cangoo.android.ui

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.core.tween
import androidx.compose.animation.expandVertically
import androidx.compose.animation.shrinkVertically
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.SnackbarDuration
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.SnackbarResult
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.Alignment
import androidx.compose.ui.platform.LocalResources
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.em
import androidx.compose.ui.unit.sp
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import androidx.compose.ui.window.SecureFlagPolicy
import app.cangoo.android.R
import java.time.Instant

@Composable
internal fun UpdateCheckCard(controller: UpdateCheckController, onOpenRelease: () -> Boolean,
                             modifier: Modifier = Modifier, dialogModifier: Modifier = Modifier) {
    val state = controller.state
    val colors = LocalBThemeColors.current
    val automatic = state.pendingPolicy?.enabled ?: state.enabled
    val editable = state.settingsReady && (!state.saving || state.pendingPolicy != null)
    var intervalInput by remember { mutableStateOf<String?>(null) }
    var showDetails by remember(state.release?.tag) { mutableStateOf(false) }
    Surface(modifier.fillMaxWidth(), shape = RoundedCornerShape(17.dp), color = colors.surface) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            UpdateHeading(stringResource(R.string.update_title))
            UpdateCopy(stringResource(R.string.about_version, controller.currentVersion))
            if (controller.isDevelopment) UpdateCopy(stringResource(R.string.update_development))
            Column {
                GeneratorToggle(stringResource(R.string.update_automatic), automatic, editable,
                    note = stringResource(R.string.update_automatic_hint)) { controller.saveSettings(enabled = it) }
                AnimatedVisibility(visible = automatic,
                    enter = expandVertically(animationSpec = tween(150), expandFrom = Alignment.Top),
                    exit = shrinkVertically(animationSpec = tween(150), shrinkTowards = Alignment.Top)) {
                    Column(Modifier.padding(start = 16.dp)) {
                        HorizontalDivider(color = colors.line)
                        SettingsChoice(stringResource(R.string.update_interval), stringResource(R.string.update_interval_value,
                            state.pendingPolicy?.intervalDays ?: state.intervalDays), editable && automatic, horizontalPadding = 0.dp) {
                            intervalInput = (state.pendingPolicy?.intervalDays ?: state.intervalDays).toString()
                        }
                    }
                }
            }
            if (!state.settingsReady) {
                if (state.failure == null) UpdateCopy(stringResource(R.string.loading))
                else UpdateTextButton(stringResource(R.string.update_retry_settings), !state.saving, controller::retrySettings)
            }
            PrimaryButton(stringResource(if (state.checking) R.string.update_checking else R.string.update_check),
                false, editable, controller::checkManually)
            if (!state.checking) UpdateStatus(state)
            state.checkedAtMillis?.let { UpdateCopy(UiText(R.string.update_checked_at, listOf(UiDate(it))).localized()) }
            if (!state.checking && (state.failure != null || state.status == UpdateCheckStatus.FAILED)) {
                state.lastAttemptMillis?.let { UpdateCopy(UiText(R.string.update_attempt_at, listOf(UiDate(it))).localized()) }
            }
            state.release?.let { release ->
                HorizontalDivider(color = colors.line)
                UpdateHeading(stringResource(R.string.update_release_version, release.version))
                UpdateTextButton(stringResource(R.string.view_details), true) { showDetails = true }
            }
        }
    }
    if (showDetails) UpdateReleaseDialog(controller, onOpenRelease, { showDetails = false }, dialogModifier)
    intervalInput?.let { input ->
        val days = input.toIntOrNull()?.takeIf { it > 0 && input.all { char -> char in '0'..'9' } }
        var pending by remember { mutableStateOf(false) }
        LaunchedEffect(pending, state.saving, state.failure, state.intervalDays) {
            if (pending && !state.saving) {
                pending = false
                if (state.failure == null && days != null && state.intervalDays == days) intervalInput = null
            }
        }
        UpdateDialog({ intervalInput = null }, dialogModifier) {
            UpdateHeading(stringResource(R.string.update_interval))
            FormField(stringResource(R.string.update_days), input, { intervalInput = it }, !state.saving && !pending,
                keyboardType = KeyboardType.Number)
            UpdateCopy(stringResource(if (days == null) R.string.update_interval_invalid else R.string.update_interval_hint), error = days == null)
            if (!state.saving && state.failure in setOf(UpdateCheckFailure.SAVE, UpdateCheckFailure.SAVE_UNKNOWN)) UpdateStatus(state)
            PrimaryButton(stringResource(R.string.save), state.saving, days != null && state.settingsReady && !pending) {
                val current = controller.state
                if (days != null && current.settingsReady && !current.saving) {
                    pending = true
                    controller.saveSettings(intervalDays = days)
                }
            }
            UpdateTextButton(stringResource(R.string.cancel), true) { intervalInput = null }
        }
    }
}

@Composable
internal fun UpdateAvailableFeedback(controller: UpdateCheckController, onOpenRelease: () -> Boolean,
                                     modifier: Modifier = Modifier, dialogModifier: Modifier = Modifier) {
    val state = controller.state
    val release = state.release
    val automatic = state.pendingPolicy?.enabled ?: state.enabled
    val host = remember { SnackbarHostState() }
    val resources = LocalResources.current
    var showDetails by remember(release?.tag) { mutableStateOf(false) }
    LaunchedEffect(release?.tag, state.checkedAtMillis, automatic) {
        if (automatic && state.automaticPrompt && release != null) {
            controller.dismissPrompt()
            val result = host.showSnackbar(ShortFeedbackVisuals(UiText(R.string.update_release_version, listOf(release.version)),
                resources, SnackbarDuration.Long, UiText(R.string.view_details)))
            if (result == SnackbarResult.ActionPerformed && controller.state.release?.tag == release.tag) showDetails = true
        }
    }
    ShortFeedbackHost(host, modifier)
    if (showDetails) UpdateReleaseDialog(controller, onOpenRelease, { showDetails = false }, dialogModifier)
}

@Composable
private fun UpdateReleaseDialog(controller: UpdateCheckController, onOpenRelease: () -> Boolean,
                                onDismiss: () -> Unit, modifier: Modifier) {
    val state = controller.state
    val release = state.release ?: return
    var openFailed by remember(release.tag) { mutableStateOf(false) }
    var ignorePending by remember(release.tag) { mutableStateOf(false) }
    fun ignore(forever: Boolean) {
        val current = controller.state
        if (!current.settingsReady || current.saving || current.checking) return
        controller.ignoreVersion(forever)
        ignorePending = controller.state.saving
    }
    LaunchedEffect(ignorePending, state.saving, state.failure) {
        if (ignorePending && !state.saving) {
            ignorePending = false
            if (state.failure == null) onDismiss()
        }
    }
    Dialog(onDismissRequest = onDismiss, properties = DialogProperties(securePolicy = SecureFlagPolicy.SecureOn)) {
        val colors = LocalBThemeColors.current
        Surface(modifier.fillMaxWidth().imePadding().heightIn(max = 600.dp), shape = RoundedCornerShape(20.dp), color = colors.surface) {
            Column(Modifier.fillMaxWidth()) {
                Column(Modifier.padding(horizontal = 20.dp, vertical = 16.dp)) {
                    UpdateHeading(stringResource(R.string.update_title))
                }
                Column(Modifier.weight(1f, fill = false).verticalScroll(rememberScrollState()).padding(horizontal = 20.dp, vertical = 8.dp),
                    verticalArrangement = Arrangement.spacedBy(14.dp)) {
                    UpdateCopy(stringResource(R.string.about_version, controller.currentVersion))
                    if (controller.isDevelopment) UpdateCopy(stringResource(R.string.update_development))
                    UpdateReleaseDetails(state)
                    state.checkedAtMillis?.let { UpdateCopy(UiText(R.string.update_checked_at, listOf(UiDate(it))).localized()) }
                }
                HorizontalDivider(color = colors.line)
                Column(Modifier.fillMaxWidth().padding(horizontal = 20.dp, vertical = 12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    if (state.failure != null) UpdateStatus(state)
                    if (openFailed) UpdateCopy(stringResource(R.string.update_open_failed), error = true)
                    PrimaryButton(stringResource(if (controller.isDevelopment) R.string.update_open_public else R.string.update_open_release), false) {
                        if (onOpenRelease()) onDismiss() else openFailed = true
                    }
                    UpdateTextButton(stringResource(R.string.update_ignore_week), state.settingsReady && !state.saving && !state.checking) { ignore(false) }
                    UpdateTextButton(stringResource(R.string.update_ignore_version), state.settingsReady && !state.saving && !state.checking) { ignore(true) }
                    UpdateTextButton(stringResource(R.string.close), true, onDismiss)
                }
            }
        }
    }
}

@Composable
private fun UpdateStatus(state: UpdateCheckUiState) {
    val message = when (state.failure) {
        UpdateCheckFailure.SETTINGS -> R.string.update_settings_failed
        UpdateCheckFailure.REGISTRATION -> R.string.update_registration_failed
        UpdateCheckFailure.QUERY -> R.string.update_query_failed
        UpdateCheckFailure.SAVE -> R.string.update_save_failed
        UpdateCheckFailure.SAVE_UNKNOWN -> R.string.update_save_unknown
        null -> when (state.status) {
            UpdateCheckStatus.IDLE -> R.string.update_not_checked
            UpdateCheckStatus.AVAILABLE -> R.string.update_available
            UpdateCheckStatus.CURRENT -> R.string.update_current
            UpdateCheckStatus.NO_RELEASE -> R.string.update_no_release
            UpdateCheckStatus.FAILED -> R.string.update_query_failed
        }
    }
    UpdateCopy(stringResource(message), error = state.failure != null || state.status == UpdateCheckStatus.FAILED,
        modifier = Modifier.semantics { liveRegion = LiveRegionMode.Polite })
}

@Composable
private fun UpdateReleaseDetails(state: UpdateCheckUiState) {
    val release = state.release ?: return
    val publishedAt = remember(release.publishedAt) { Instant.parse(release.publishedAt).toEpochMilli() }
    UpdateHeading(stringResource(R.string.update_release_version, release.version))
    UpdateCopy(UiText(R.string.update_published_at, listOf(UiDate(publishedAt))).localized())
    if (release.notes.isNotBlank()) {
        UpdateHeading(stringResource(R.string.update_notes))
        UpdateCopy(release.notes)
    }
}

@Composable
private fun UpdateDialog(onDismiss: () -> Unit, modifier: Modifier, content: @Composable ColumnScope.() -> Unit) {
    Dialog(onDismissRequest = onDismiss, properties = DialogProperties(securePolicy = SecureFlagPolicy.SecureOn)) {
        Surface(modifier.fillMaxWidth().imePadding().heightIn(max = 600.dp), shape = RoundedCornerShape(20.dp), color = LocalBThemeColors.current.surface) {
            Column(Modifier.verticalScroll(rememberScrollState()).padding(20.dp), verticalArrangement = Arrangement.spacedBy(14.dp), content = content)
        }
    }
}

@Composable
private fun UpdateHeading(text: String) {
    Text(text, Modifier.fillMaxWidth().semantics { heading() }, color = LocalBThemeColors.current.ink,
        fontSize = businessSp(17.sp), lineHeight = 1.5.em, fontWeight = FontWeight.SemiBold)
}

@Composable
private fun UpdateCopy(text: String, modifier: Modifier = Modifier, error: Boolean = false) {
    val colors = LocalBThemeColors.current
    Text(text, modifier.fillMaxWidth(), color = if (error) colors.error else colors.muted, fontSize = businessSp(14.sp), lineHeight = 1.6.em)
}

@Composable
private fun UpdateTextButton(text: String, enabled: Boolean, onClick: () -> Unit) {
    TextButton(onClick = onClick, enabled = enabled, modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp)) {
        Text(text, color = if (enabled) LocalBThemeColors.current.accentInk else LocalBThemeColors.current.muted,
            fontSize = businessSp(14.sp), lineHeight = 1.5.em)
    }
}
