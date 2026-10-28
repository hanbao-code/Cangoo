package app.cangoo.android.ui

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.core.tween
import androidx.compose.animation.expandVertically
import androidx.compose.animation.shrinkVertically
import androidx.compose.foundation.border
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.key
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.rotate
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalFocusManager
import androidx.compose.ui.res.pluralStringResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.selected
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.stateDescription
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.em
import androidx.compose.ui.unit.sp
import app.cangoo.android.R
import app.cangoo.android.data.BackupScope

// 只呈现当前原生任务并转发意图；认证、权限、快照和传输资格由控制器持有。
@Composable
internal fun BDirectTransferPage(controller: DirectTransferController, onStart: () -> Unit, onCancel: () -> Unit,
                                 onOpenSettings: (DirectTransferSettings) -> Unit, modifier: Modifier = Modifier,
                                 onCopyPairingCode: () -> Unit) {
    val state = controller.state
    val colors = LocalBThemeColors.current
    val focus = LocalFocusManager.current
    val manualMode = state.channel == DirectTransferChannel.LAN && state.role == DirectTransferRole.SENDER &&
        state.manualAddressExpanded && state.phase in setOf(DirectTransferPhase.CONFIG, DirectTransferPhase.DISCOVERING)
    Column(modifier.fillMaxSize()) {
        Column(Modifier.fillMaxWidth().padding(horizontal = 24.dp, vertical = 12.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            TransferValue(stringResource(R.string.transfer_local_vault), state.localVaultName)
            Text(stringResource(transferPhaseTitle(state)), color = colors.ink, fontSize = businessSp(18.sp), lineHeight = 1.4.em,
                fontWeight = FontWeight.SemiBold, modifier = Modifier.fillMaxWidth().semantics { heading(); liveRegion = LiveRegionMode.Polite })
            if (state.phase == DirectTransferPhase.WAITING && state.pairingCode.length == 8) {
                TransferCode(state.pairingCode, onCopyPairingCode)
                TransferCopy(stringResource(R.string.transfer_pairing_validity))
            }
            if (state.phase in setOf(DirectTransferPhase.TRANSFERRING, DirectTransferPhase.VERIFYING)) TransferProgress(state)
        }
        HorizontalDivider(color = colors.line)
        Column(Modifier.weight(1f).fillMaxWidth().verticalScroll(rememberScrollState()).padding(horizontal = 24.dp, vertical = 16.dp),
            verticalArrangement = Arrangement.spacedBy(18.dp)) {
            if (state.phase == DirectTransferPhase.CONFIG) {
                TransferHeading(stringResource(R.string.transfer_role))
                Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    DirectTransferRole.entries.forEach { role ->
                        TransferChoice(stringResource(transferRoleLabel(role)), state.role == role, enabled = !state.manualSearching) { controller.configure(role = role) }
                    }
                }
                TransferHeading(stringResource(R.string.transfer_channel))
                Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    DirectTransferChannel.entries.forEach { channel ->
                        TransferChoice(stringResource(transferChannelLabel(channel)), state.channel == channel, enabled = !state.manualSearching) { controller.configure(channel = channel) }
                    }
                }
                TransferCopy(stringResource(if (state.channel == DirectTransferChannel.LAN) R.string.transfer_lan_hint else R.string.transfer_bluetooth_hint))
            } else {
                TransferValue(stringResource(R.string.transfer_role), stringResource(transferRoleLabel(state.role)))
                TransferValue(stringResource(R.string.transfer_channel), stringResource(transferChannelLabel(state.channel)))
                state.peerName?.let { TransferValue(stringResource(R.string.transfer_peer_device), it) }
                when (state.phase) {
                    DirectTransferPhase.DISCOVERING -> {
                        TransferCopy(stringResource(R.string.transfer_discover_hint))
                        if (state.channel == DirectTransferChannel.BLUETOOTH) TransferCopy(stringResource(R.string.transfer_bluetooth_hint))
                        if (state.peers.isEmpty()) TransferCopy(stringResource(R.string.transfer_empty))
                        else SettingsGroup {
                            state.peers.forEachIndexed { index, peer ->
                                key(peer.key) {
                                    SettingsAction(peer.displayName, stringResource(transferChannelLabel(peer.channel)), state.peersSelectable && !state.manualSearching, "info") { controller.selectPeer(peer) }
                                    if (index < state.peers.lastIndex) HorizontalDivider(Modifier.padding(horizontal = 14.dp), color = colors.line)
                                }
                            }
                        }
                    }
                    DirectTransferPhase.WAITING -> {
                        TransferCopy(stringResource(R.string.transfer_receiver_hint))
                        if (state.channel == DirectTransferChannel.LAN && state.localAddresses.isNotEmpty()) {
                            TransferValue(stringResource(R.string.transfer_local_addresses), state.localAddresses.joinToString("\n"))
                            TransferCopy(stringResource(R.string.transfer_local_addresses_hint))
                        }
                    }
                    DirectTransferPhase.PAIRING_CODE -> {
                        TransferCopy(stringResource(R.string.transfer_pairing_hint))
                        FormField(stringResource(R.string.transfer_pairing_code), state.pairingCode, controller::updatePairingCode,
                            enabled = true, placeholder = "00000000", keyboardType = KeyboardType.NumberPassword,
                            onDone = { focus.clearFocus(); controller.connectWithCode() })
                        if (state.channel == DirectTransferChannel.BLUETOOTH) TransferCopy(stringResource(R.string.transfer_pairing_upgrade_hint))
                    }
                    DirectTransferPhase.CONNECTING -> TransferCopy(stringResource(R.string.transfer_connecting))
                    DirectTransferPhase.WAIT_APPROVAL -> TransferCopy(stringResource(if (state.role == DirectTransferRole.RECEIVER)
                        R.string.transfer_approval_hint else R.string.transfer_wait_approval_hint))
                    DirectTransferPhase.PREPARING, DirectTransferPhase.REVIEW, DirectTransferPhase.TRANSFERRING,
                    DirectTransferPhase.VERIFYING, DirectTransferPhase.RECEIVED, DirectTransferPhase.SENT -> TransferReview(state, controller)
                    DirectTransferPhase.CONFIG, DirectTransferPhase.FAILED -> Unit
                }
                when (state.phase) {
                    DirectTransferPhase.TRANSFERRING, DirectTransferPhase.VERIFYING -> TransferCopy(stringResource(R.string.transfer_foreground_hint))
                    DirectTransferPhase.RECEIVED -> TransferCopy(stringResource(R.string.transfer_received_hint))
                    DirectTransferPhase.SENT -> TransferCopy(stringResource(R.string.transfer_sent_hint))
                    else -> Unit
                }
            }
            if (state.channel == DirectTransferChannel.LAN && state.role == DirectTransferRole.SENDER &&
                state.phase in setOf(DirectTransferPhase.CONFIG, DirectTransferPhase.DISCOVERING)) {
                TransferManualAddress(state, controller)
            }
        }
        HorizontalDivider(color = colors.line)
        Column(Modifier.fillMaxWidth().padding(horizontal = 24.dp, vertical = 12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            if (state.error.isNotEmpty()) TransferCopy(state.error.localized(), color = colors.error,
                modifier = Modifier.semantics { liveRegion = LiveRegionMode.Polite })
            if (manualMode) Text(state.manualError.localized(), Modifier.fillMaxWidth().semantics { liveRegion = LiveRegionMode.Polite },
                color = colors.error, fontSize = businessSp(14.sp), lineHeight = 1.6.em, minLines = 2)
            when (state.phase) {
                DirectTransferPhase.CONFIG, DirectTransferPhase.DISCOVERING -> {
                    val label = stringResource(when {
                        manualMode -> if (state.manualSearching) R.string.transfer_manual_searching else R.string.transfer_manual_find
                        state.phase == DirectTransferPhase.DISCOVERING -> R.string.transfer_refresh
                        state.role == DirectTransferRole.SENDER -> R.string.transfer_find_devices
                        else -> R.string.transfer_start_receive
                    })
                    Button(onClick = {
                        if (manualMode) {
                            controller.findManualAddress()
                            if (controller.state.manualSearching) focus.clearFocus()
                        } else { focus.clearFocus(); onStart() }
                    }, enabled = !state.manualSearching,
                        modifier = Modifier.fillMaxWidth().heightIn(min = 50.dp), shape = RoundedCornerShape(14.dp),
                        contentPadding = PaddingValues(14.dp), colors = ButtonDefaults.buttonColors(
                            containerColor = colors.accentFill, contentColor = colors.onAccent,
                            disabledContainerColor = colors.accentFill, disabledContentColor = colors.onAccent)) {
                        Box(Modifier.size(20.dp))
                        Text(label, Modifier.weight(1f), fontSize = businessSp(16.sp), lineHeight = (20f / 16).em,
                            fontWeight = FontWeight.SemiBold, textAlign = TextAlign.Center)
                        Spacer(Modifier.size(20.dp))
                    }
                }
                DirectTransferPhase.PAIRING_CODE -> PrimaryButton(stringResource(R.string.transfer_pairing_connect), false,
                    enabled = state.pairingCode.length == 8, onClick = { focus.clearFocus(); controller.connectWithCode() })
                DirectTransferPhase.WAIT_APPROVAL -> PrimaryButton(stringResource(if (state.role == DirectTransferRole.RECEIVER)
                    R.string.transfer_approve else R.string.transfer_wait_approval), false,
                    enabled = state.role == DirectTransferRole.RECEIVER, onClick = controller::approvePeer)
                DirectTransferPhase.REVIEW -> {
                    if (state.role == DirectTransferRole.SENDER) PrimaryButton(stringResource(if (state.offerPrepared)
                        R.string.transfer_wait_start else R.string.transfer_start_send), false,
                        enabled = state.peerVaultName != null && !state.offerPrepared, onClick = controller::prepareOffer)
                    else PrimaryButton(stringResource(R.string.transfer_offer_wait), false, enabled = false, onClick = {})
                }
                DirectTransferPhase.FAILED -> PrimaryButton(stringResource(R.string.transfer_restart), false, onClick = controller::reset)
                DirectTransferPhase.SENT -> PrimaryButton(stringResource(R.string.close), false, onClick = onCancel)
                else -> PrimaryButton(stringResource(transferPhaseTitle(state)), false, enabled = false, onClick = {})
            }
            if (state.phase == DirectTransferPhase.FAILED) state.settings?.let { destination ->
                TransferTextButton(stringResource(when (destination) {
                    DirectTransferSettings.APPLICATION -> R.string.transfer_open_app_settings
                    DirectTransferSettings.BLUETOOTH -> R.string.transfer_open_bluetooth
                })) { onOpenSettings(destination) }
            }
            if (state.phase == DirectTransferPhase.WAIT_APPROVAL && state.role == DirectTransferRole.RECEIVER)
                TransferTextButton(stringResource(R.string.transfer_reject), controller::rejectPeer)
            else if (state.phase != DirectTransferPhase.SENT) TransferTextButton(stringResource(if (state.phase == DirectTransferPhase.FAILED)
                R.string.back else R.string.cancel), onCancel)
        }
    }
}

@Composable
private fun TransferManualAddress(state: DirectTransferUiState, controller: DirectTransferController) {
    val colors = LocalBThemeColors.current
    val expandedLabel = stringResource(if (state.manualAddressExpanded) R.string.collapse else R.string.expand)
    Column(Modifier.fillMaxWidth()) {
        TextButton(onClick = controller::toggleManualAddress, enabled = !state.manualSearching,
            modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp).semantics { stateDescription = expandedLabel }) {
            Text(stringResource(R.string.transfer_manual_toggle), Modifier.weight(1f), color = colors.accentInk,
                fontSize = businessSp(14.sp), lineHeight = 1.5.em)
            Icon(bIcon("chevron_down"), null, Modifier.size(18.dp).rotate(if (state.manualAddressExpanded) 180f else 0f), tint = colors.accentInk)
        }
        AnimatedVisibility(visible = state.manualAddressExpanded,
            enter = expandVertically(animationSpec = tween(150), expandFrom = Alignment.Top),
            exit = shrinkVertically(animationSpec = tween(150), shrinkTowards = Alignment.Top)) {
            Column(Modifier.fillMaxWidth().padding(top = 8.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                TransferCopy(stringResource(R.string.transfer_manual_hint))
                // 查询时锁定输入并保留地址原色，避免整页跟随忙态变灰。
                CompositionLocalProvider(LocalBThemeColors provides if (state.manualSearching) colors.copy(muted = colors.ink) else colors) {
                    FormField(stringResource(R.string.transfer_manual_address), state.manualAddress, controller::updateManualAddress,
                        enabled = !state.manualSearching, placeholder = "192.168.1.5", keyboardType = KeyboardType.Ascii)
                }
            }
        }
    }
}

@Composable
private fun TransferReview(state: DirectTransferUiState, controller: DirectTransferController) {
    if (state.peerVaultName == null) {
        TransferCopy(stringResource(R.string.transfer_metadata_wait))
        return
    }
    TransferValue(stringResource(R.string.transfer_peer_vault), state.peerVaultName)
    TransferValue(stringResource(R.string.transfer_direction), stringResource(if (state.role == DirectTransferRole.SENDER)
        R.string.transfer_direction_send else R.string.transfer_direction_receive))
    if (state.role == DirectTransferRole.SENDER && !state.offerPrepared) {
        if (state.phase == DirectTransferPhase.REVIEW) {
            TransferHeading(stringResource(R.string.transfer_scope))
            Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                BackupScope.entries.forEach { scope ->
                    TransferChoice(stringResource(transferScopeLabel(scope)), state.scope == scope) { controller.configure(scope = scope) }
                }
            }
        } else TransferValue(stringResource(R.string.transfer_scope), stringResource(transferScopeLabel(state.scope)))
    } else if (state.offerPrepared) {
        TransferValue(stringResource(R.string.transfer_scope), stringResource(transferScopeLabel(state.scope)))
        state.passwordCount?.let { TransferCopy(pluralStringResource(R.plurals.password_count, it, it)) }
        state.noteCount?.let { TransferCopy(pluralStringResource(R.plurals.note_count, it, it)) }
        if (state.phase == DirectTransferPhase.REVIEW && state.role == DirectTransferRole.SENDER) TransferCopy(stringResource(R.string.transfer_scope_locked))
    } else TransferCopy(stringResource(R.string.transfer_offer_wait))
    if (state.phase == DirectTransferPhase.REVIEW) TransferCopy(stringResource(R.string.transfer_compare_hint))
}

@Composable
private fun TransferCode(code: String, onCopy: () -> Unit) {
    val colors = LocalBThemeColors.current
    Surface(Modifier.fillMaxWidth(), shape = RoundedCornerShape(10.dp), color = colors.soft) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text(code.chunked(4).joinToString(" "), Modifier.weight(1f).padding(horizontal = 12.dp, vertical = 10.dp), color = colors.ink,
                fontSize = businessSp(26.sp), lineHeight = 1.5.em, fontFamily = FontFamily.Monospace,
                fontWeight = FontWeight.SemiBold, textAlign = TextAlign.Center, softWrap = false)
            TextButton(onClick = onCopy) {
                Text(stringResource(R.string.copy), color = colors.accentInk, fontSize = businessSp(14.sp), lineHeight = 1.5.em)
            }
        }
    }
}

@Composable
private fun TransferProgress(state: DirectTransferUiState) {
    val total = state.totalBytes?.takeIf { it > 0 }
    val colors = LocalBThemeColors.current
    if (total != null) {
        LinearProgressIndicator(progress = { (state.completedBytes.toDouble() / total).toFloat().coerceIn(0f, 1f) },
            modifier = Modifier.fillMaxWidth(), color = colors.accentInk, trackColor = colors.soft)
        TransferCopy(stringResource(R.string.transfer_progress, state.completedBytes, total))
    } else {
        LinearProgressIndicator(modifier = Modifier.fillMaxWidth(), color = colors.accentInk, trackColor = colors.soft)
        TransferCopy(stringResource(R.string.transfer_progress_unknown, state.completedBytes))
    }
}

@Composable
private fun TransferChoice(label: String, selected: Boolean, enabled: Boolean = true, onClick: () -> Unit) {
    val colors = LocalBThemeColors.current
    Button(onClick = onClick, enabled = enabled, shape = RoundedCornerShape(14.dp),
        colors = ButtonDefaults.buttonColors(containerColor = colors.soft, contentColor = colors.ink,
            disabledContainerColor = colors.soft, disabledContentColor = colors.ink),
        modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp).semantics { this.selected = selected }
            .then(if (selected) Modifier.border(1.dp, colors.accentInk, RoundedCornerShape(14.dp)) else Modifier)) {
        if (selected) Icon(bIcon("check"), stringResource(R.string.backup_action_selected), Modifier.padding(end = 6.dp).size(18.dp))
        Text(label, fontSize = businessSp(16.sp), lineHeight = 1.5.em)
    }
}

@Composable
private fun TransferValue(label: String, value: String) {
    Column(Modifier.fillMaxWidth(), verticalArrangement = Arrangement.spacedBy(4.dp)) {
        TransferCopy(label, size = 13)
        Text(value, Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()), softWrap = false, color = LocalBThemeColors.current.ink,
            fontSize = businessSp(16.sp), lineHeight = 1.5.em)
    }
}

@Composable
private fun TransferHeading(text: String) {
    Text(text, Modifier.fillMaxWidth().semantics { heading() }, color = LocalBThemeColors.current.ink,
        fontSize = businessSp(16.sp), lineHeight = 1.5.em, fontWeight = FontWeight.SemiBold)
}

@Composable
private fun TransferCopy(text: String, modifier: Modifier = Modifier, size: Int = 14, color: Color = LocalBThemeColors.current.muted) {
    Text(text, modifier.fillMaxWidth(), color = color, fontSize = businessSp(size.sp), lineHeight = 1.6.em)
}

@Composable
private fun TransferTextButton(text: String, onClick: () -> Unit) {
    TextButton(onClick = onClick, modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp)) {
        Text(text, color = LocalBThemeColors.current.accentInk, fontSize = businessSp(14.sp), lineHeight = 1.5.em)
    }
}

private fun transferRoleLabel(role: DirectTransferRole): Int = when (role) {
    DirectTransferRole.SENDER -> R.string.transfer_send
    DirectTransferRole.RECEIVER -> R.string.transfer_receive
}

private fun transferChannelLabel(channel: DirectTransferChannel): Int = when (channel) {
    DirectTransferChannel.LAN -> R.string.transfer_lan
    DirectTransferChannel.BLUETOOTH -> R.string.transfer_bluetooth
}

private fun transferScopeLabel(scope: BackupScope): Int = when (scope) {
    BackupScope.ALL -> R.string.scope_all
    BackupScope.PASSWORDS -> R.string.scope_passwords
    BackupScope.NOTES -> R.string.scope_notes
}

private fun transferPhaseTitle(state: DirectTransferUiState): Int = when (state.phase) {
    DirectTransferPhase.CONFIG -> R.string.transfer_configure
    DirectTransferPhase.DISCOVERING -> R.string.transfer_nearby
    DirectTransferPhase.WAITING -> R.string.transfer_wait_connection
    DirectTransferPhase.CONNECTING -> R.string.transfer_connecting
    DirectTransferPhase.PAIRING_CODE -> R.string.transfer_pairing_title
    DirectTransferPhase.WAIT_APPROVAL -> if (state.role == DirectTransferRole.RECEIVER) R.string.transfer_approval_title else R.string.transfer_wait_approval
    DirectTransferPhase.PREPARING -> R.string.transfer_preparing
    DirectTransferPhase.REVIEW -> R.string.transfer_review
    DirectTransferPhase.TRANSFERRING -> if (state.role == DirectTransferRole.SENDER) R.string.transfer_sending else R.string.transfer_receiving
    DirectTransferPhase.VERIFYING -> if (state.role == DirectTransferRole.SENDER) R.string.transfer_wait_verification else R.string.transfer_verifying
    DirectTransferPhase.RECEIVED -> R.string.transfer_received
    DirectTransferPhase.SENT -> R.string.transfer_sent
    DirectTransferPhase.FAILED -> R.string.transfer_failed
}
