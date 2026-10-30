package app.cangoo.android.ui

import androidx.activity.compose.BackHandler
import androidx.compose.animation.core.animateValue
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.keyframes
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.VectorConverter
import androidx.compose.foundation.border
import androidx.compose.foundation.background
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.ScrollState
import androidx.compose.foundation.selection.toggleable
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.IntrinsicSize
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.safeDrawing
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.ModalBottomSheetProperties
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.Checkbox
import app.cangoo.android.R
import androidx.compose.ui.platform.LocalResources
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.key
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.compositeOver
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.platform.LocalSoftwareKeyboardController
import androidx.compose.ui.platform.LocalFocusManager
import androidx.compose.ui.platform.LocalWindowInfo
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.clearAndSetSemantics
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.selected
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.text
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.buildAnnotatedString
import androidx.compose.ui.text.withStyle
import androidx.compose.ui.text.PlatformTextStyle
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.unit.em
import androidx.compose.ui.window.DialogProperties
import androidx.compose.ui.window.SecureFlagPolicy
import app.cangoo.android.data.BackupImportKind
import app.cangoo.android.data.BackupImportRow
import app.cangoo.android.data.BackupComparisonField
import app.cangoo.android.data.BackupComparisonFieldSummary
import app.cangoo.android.data.BackupComparisonValueSummary
import app.cangoo.android.data.BackupComparisonWritePolicy
import app.cangoo.android.data.BackupImportFieldValue
import app.cangoo.android.data.BackupImportFilter
import app.cangoo.android.data.BackupImportBatchAction
import app.cangoo.android.data.BackupPreviewTextField
import app.cangoo.android.data.BackupScope
import app.cangoo.android.data.NoteImportAction
import app.cangoo.android.data.NoteImportChoice
import app.cangoo.android.data.PasswordImportAction
import app.cangoo.android.data.PasswordImportChoice

// 正文只读取当前模型并转发事件；标题、滚动、文件选择及任务资格由父层持有。
@Composable
internal fun BBackupPage(model: VaultModel, onChooseFile: (BackupDocumentKind, Long) -> Unit) {
    val texts = LocalResources.current
    val state = model.state
    if (state.page != Page.BACKUP || !state.unlocked) return
    val input = model.editGeneration
    val backup = model.backupState
    val enabled = !state.busy
    Column(Modifier.fillMaxWidth(), verticalArrangement = Arrangement.spacedBy(20.dp)) {
        if (backup.step == BackupStep.PREVIEW) {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                BackupContextRow(texts.getString(R.string.target_vault_short), state.vault?.name.orEmpty())
                BackupContextRow(texts.getString(if (backup.source == BackupSource.TRANSFER) R.string.transfer_source_device else R.string.file), backup.documentName)
            }
        } else if (backup.step != BackupStep.HOME) {
            BackupCopy(if (backup.step == BackupStep.EXPORT) texts.getString(R.string.current_vault) else texts.getString(R.string.target_vault), size = 13)
            Text(state.vault?.name.orEmpty(), color = LocalBThemeColors.current.ink, lineHeight = (24f / 17).em, fontSize = businessSp(17.sp), softWrap = false,
                modifier = Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()))
        }
        if (backup.documentName.isNotEmpty() && backup.step != BackupStep.PREVIEW) {
            BackupCopy(texts.getString(R.string.selected_file), size = 13)
            Text(backup.documentName, color = LocalBThemeColors.current.ink, lineHeight = (24f / 15).em, fontSize = businessSp(15.sp), softWrap = false,
                modifier = Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()))
        }
        when (backup.step) {
            BackupStep.HOME -> {
                Column {
                    BVaultNameContext(model, Page.BACKUP, input)
                    Column(Modifier.padding(top = 30.dp, bottom = 8.dp)) {
                        Icon(bIcon("tools"), null, Modifier.size(42.dp), tint = LocalBThemeColors.current.accentInk)
                        Spacer(Modifier.height(23.dp))
                        Text(texts.getString(R.string.backup_your_data), color = LocalBThemeColors.current.ink, fontSize = businessSp(26.sp), lineHeight = 1.3.em,
                            letterSpacing = (-0.7).sp, fontWeight = FontWeight.Bold, modifier = Modifier.fillMaxWidth().semantics { heading() },
                            style = TextStyle(platformStyle = PlatformTextStyle(includeFontPadding = false), lineHeightStyle = BLineHeightStyle))
                        BackupCopy(texts.getString(R.string.backup_password_separate), size = 13, modifier = Modifier.padding(top = 14.dp))
                    }
                }
                BackupHomeActions(model, input, enabled)
            }
            BackupStep.EXPORT, BackupStep.IMPORT -> BackupConfigurationBody(model, input, enabled, onChooseFile)
            BackupStep.PREVIEW -> BackupPreviewBody(model, input, enabled)
            BackupStep.RESULT -> {
                backup.result?.let { result ->
                    Icon(bIcon("check"), null, Modifier.size(32.dp), tint = LocalBThemeColors.current.accentInk)
                    BackupHeading(texts.getString(R.string.restore_complete), 25)
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(32.dp)) {
                        listOf(texts.getString(R.string.added) to result.imported, texts.getString(R.string.replaced) to result.overwritten, texts.getString(R.string.skipped) to result.skipped).forEach { (label, count) ->
                            Column(Modifier.weight(1f)) { BackupCopy(label, size = 13); BackupHeading(count.toString(), 25) }
                        }
                    }
                }
                BackupHomeActions(model, input, enabled)
            }
        }
    }
}

@Composable
private fun BackupContextRow(label: String, value: String) {
    val labelWidth = with(LocalDensity.current) { businessSp(13.sp).toDp() * 3.5f }
    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
        Text(label, color = LocalBThemeColors.current.muted, fontSize = businessSp(13.sp), lineHeight = 1.6.em,
            modifier = Modifier.width(labelWidth).alignByBaseline())
        Text(value, color = LocalBThemeColors.current.ink, fontSize = businessSp(15.sp), lineHeight = 1.6.em,
            softWrap = false, modifier = Modifier.weight(1f).alignByBaseline().horizontalScroll(rememberScrollState()))
    }
}

// 父层放在固定底部；这里只转发当前代数的最终操作，不重复正文或错误反馈。
@OptIn(ExperimentalLayoutApi::class)
@Composable
internal fun BBackupFooter(model: VaultModel, onChooseFile: (BackupDocumentKind, Long) -> Unit) {
    val texts = LocalResources.current
    val state = model.state
    if (state.page != Page.BACKUP || !state.unlocked) return
    val backup = model.backupState
    if (backup.step == BackupStep.HOME || backup.step == BackupStep.RESULT) return
    val focus = LocalFocusManager.current
    val keyboard = LocalSoftwareKeyboardController.current
    val input = model.editGeneration
    val exporting = backup.step == BackupStep.EXPORT
    var batchMenu by remember(backup.preview?.id, backup.previewKind) { mutableStateOf(false) }
    var selectionMenu by remember(backup.preview?.id, backup.previewKind) { mutableStateOf(false) }
    val kind = if (exporting) BackupDocumentKind.EXPORT else BackupDocumentKind.IMPORT
    val configured = if (exporting) true else if (backup.step == BackupStep.PREVIEW) backup.preview != null else
        backup.documentName.isNotEmpty() && model.documentIntent?.let {
            it.kind == kind && it.uri != null && it.vaultId == state.vault?.id
        } == true
    if (!state.busy && !configured) return
    val colors = LocalBThemeColors.current
    Surface(color = colors.paper) {
        Column(Modifier.fillMaxWidth()) {
            HorizontalDivider(color = colors.line)
            Column(Modifier.fillMaxWidth().padding(horizontal = 24.dp, vertical = 10.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                val preview = backup.preview
                val summary = backup.planSummary
                if (preview != null && backup.step == BackupStep.PREVIEW) {
                    val count = backup.pageInfo?.matchedCount ?: 0
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.Center, verticalAlignment = Alignment.CenterVertically) {
                        IconButton(onClick = { model.backupPage(backup.previewKind, (backup.offset - 20).coerceAtLeast(0), input) },
                            enabled = !state.busy && backup.offset > 0) {
                            Icon(bIcon("chevron_left"), texts.getString(R.string.previous_page), Modifier.size(20.dp))
                        }
                        BackupCopy(texts.getString(R.string.backup_page_number, backup.offset / 20 + 1, maxOf(1, (count + 19) / 20)), size = 13)
                        IconButton(onClick = { model.backupPage(backup.previewKind, backup.offset + 20, input) },
                            enabled = !state.busy && backup.offset + backup.rows.size < count) {
                            Icon(bIcon("chevron_right"), texts.getString(R.string.next_page), Modifier.size(20.dp))
                        }
                    }
                    FlowRow(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp),
                        verticalArrangement = Arrangement.spacedBy(4.dp)) {
                        TextButton(onClick = { if (model.onUserInteraction()) selectionMenu = true },
                            enabled = !state.busy && (count > 0 || backup.currentGroup.selected.isNotEmpty())) {
                            Text(texts.getString(R.string.backup_selection_scope), fontSize = businessSp(13.sp), lineHeight = 1.5.em)
                            Icon(bIcon("chevron_down"), null, Modifier.size(16.dp))
                        }
                        BackupCopy(texts.getString(R.string.backup_selected_count, backup.currentGroup.selected.size), size = 13,
                            modifier = Modifier.align(Alignment.CenterVertically))
                        if (backup.currentGroup.selected.isNotEmpty()) TextButton(onClick = { if (model.onUserInteraction()) batchMenu = true }, enabled = !state.busy) {
                            Text(texts.getString(R.string.backup_batch_title), fontSize = businessSp(13.sp), lineHeight = 1.5.em)
                        }
                    }
                    if (summary != null) FlowRow(horizontalArrangement = Arrangement.spacedBy(14.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                        listOf(R.string.added to summary.imported, R.string.replaced to summary.overwritten,
                            R.string.skipped to summary.skipped, R.string.backup_filter_pending to summary.pending).forEach { (label, count) ->
                            BackupCopy("${texts.getString(label)} $count", size = 13, color = colors.ink, weight = FontWeight.Medium)
                        }
                    } else if (state.busy) BackupCopy(texts.getString(R.string.reading_ellipsis), size = 13)
                    else TextButton(onClick = { model.refreshBackupPlan(input) }) {
                        Text(texts.getString(R.string.retry), fontSize = businessSp(14.sp))
                    }
                }
                if (state.busy && !backup.reading) {
                    BackupProcessingStatus(texts.getString(R.string.processing_ellipsis))
                    BackupAction(texts.getString(R.string.cancel_operation), true) { model.cancelBackupWork(input) }
                } else if (backup.step == BackupStep.PREVIEW) {
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                        Button(onClick = { model.backupConfiguration(input) }, shape = RoundedCornerShape(11.dp),
                            colors = ButtonDefaults.buttonColors(containerColor = colors.soft, contentColor = colors.ink),
                            contentPadding = PaddingValues(horizontal = 16.dp, vertical = 9.dp), modifier = Modifier.heightIn(min = 48.dp)) {
                            Text(texts.getString(R.string.cancel_restore), fontSize = businessSp(14.sp), lineHeight = 1.5.em)
                        }
                        BackupAction(texts.getString(R.string.confirm_restore), summary?.pending == 0 && (!state.busy || backup.reading), modifier = Modifier.weight(1f), primary = true) { model.reviewBackupCommit(input) }
                    }
                } else {
                    val selected = exporting && model.documentIntent?.uri != null
                    BackupAction(if (exporting) if (selected) texts.getString(R.string.continue_backup) else texts.getString(R.string.create_backup) else texts.getString(R.string.preview_contents),
                        !model.exportSelectionPending && (!selected || backup.documentName.isNotEmpty()) && (!exporting || !backup.custom || !backup.selection.empty), primary = true) {
                        if (exporting) {
                            focus.clearFocus(); keyboard?.hide()
                            if (selected) model.exportBackup(input) else onChooseFile(BackupDocumentKind.EXPORT, input)
                        } else model.previewBackup(input)
                    }
                }
            }
        }
    }
    if (selectionMenu) {
        BackupOptionsDialog(model, texts.getString(R.string.backup_selection_scope),
            listOf(R.string.backup_select_page, R.string.backup_select_filtered, R.string.backup_clear_group_selection).map { texts.getString(it) },
            onDismiss = { selectionMenu = false }) { index ->
            selectionMenu = false
            when (index) {
                0 -> model.selectBackupPage(backup.previewKind, backup.rows.filter { it.decisionRequired }.mapTo(linkedSetOf()) { it.sourceIndex }, input)
                1 -> model.selectBackupFiltered(backup.previewKind, input)
                2 -> model.clearBackupSelection(backup.previewKind, input)
            }
        }
    }
    if (batchMenu) {
        val actions = if (backup.previewKind == BackupImportKind.NOTE) listOf(BackupImportBatchAction.SKIP, BackupImportBatchAction.OVERWRITE, BackupImportBatchAction.KEEP_BOTH)
            else listOf(BackupImportBatchAction.SKIP, BackupImportBatchAction.OVERWRITE)
        BackupOptionsDialog(model, texts.getString(R.string.backup_batch_title), actions.map { texts.getString(when (it) {
            BackupImportBatchAction.SKIP -> R.string.backup_compare_keep_current
            BackupImportBatchAction.OVERWRITE -> R.string.backup_compare_replace_current
            BackupImportBatchAction.KEEP_BOTH -> R.string.backup_batch_keep_both
        }) }, onDismiss = { batchMenu = false }) { index ->
            batchMenu = false
            model.reviewBackupBatch(backup.previewKind, actions[index], input)
        }
    }
    BackupReviewDialogs(model, input)
}

@Composable
private fun BackupHomeActions(model: VaultModel, input: Long, enabled: Boolean) {
    val texts = LocalResources.current
    Surface(color = LocalBThemeColors.current.surface, shape = RoundedCornerShape(17.dp)) {
        Column(Modifier.padding(horizontal = 14.dp)) {
            BackupEntry(texts.getString(R.string.create_backup), texts.getString(R.string.backup_setup_hint), "download", enabled) { model.beginBackup(BackupDocumentKind.EXPORT, input) }
            HorizontalDivider(color = LocalBThemeColors.current.line)
            BackupEntry(texts.getString(R.string.restore_backup), texts.getString(R.string.restore_setup_hint), "upload", enabled) { model.beginBackup(BackupDocumentKind.IMPORT, input) }
        }
    }
}

@Composable
internal fun BVaultNameContext(model: VaultModel, page: Page, input: Long) {
    val texts = LocalResources.current
    val vault = model.state.vault ?: return
    val colors = LocalBThemeColors.current
    val nameFontSize = businessSp(16.sp)
    val iconTop = with(LocalDensity.current) { nameFontSize.toDp() * 0.75f - 9.dp }
    var viewingName by remember(vault.id, page, input) { mutableStateOf(false) }
    Row(Modifier.fillMaxWidth().padding(bottom = 8.dp).heightIn(min = 48.dp),
        verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
        Text(texts.getString(R.string.current_vault), modifier = Modifier.alignByBaseline(), color = colors.muted, fontSize = businessSp(13.sp), lineHeight = 1.5.em)
        TextButton(onClick = {
            if (input == model.editGeneration && model.state.page == page && !model.state.busy && model.onUserInteraction()) viewingName = true
        }, enabled = !model.state.busy, modifier = Modifier.weight(1f).heightIn(min = 48.dp).alignByBaseline(),
            shape = RoundedCornerShape(11.dp), contentPadding = PaddingValues(vertical = 8.dp)) {
            Row(verticalAlignment = Alignment.Top, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Text(vault.name, color = colors.ink, fontSize = nameFontSize, lineHeight = 1.5.em,
                    maxLines = if (page == Page.BACKUP) 1 else 2, overflow = TextOverflow.Ellipsis,
                    modifier = Modifier.weight(1f))
                Icon(bIcon("info"), texts.getString(R.string.view_full_name), Modifier.padding(top = iconTop).size(18.dp), tint = colors.muted)
            }
        }
    }
    if (viewingName) BVaultNameSheet(vault.name, model) { viewingName = false }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
internal fun BVaultNameSheet(name: String, model: VaultModel, onDismiss: () -> Unit) {
    val texts = LocalResources.current
    val colors = LocalBThemeColors.current
    val focus = LocalFocusManager.current
    LaunchedEffect(Unit) { focus.clearFocus() }
    val windowHeight = with(LocalDensity.current) { LocalWindowInfo.current.containerSize.height.toDp() }
    val nameHeight = (windowHeight * 0.4f).coerceAtMost(280.dp)
    ModalBottomSheet(onDismissRequest = { model.onUserInteraction(); onDismiss() },
        sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true),
        modifier = Modifier.recordDialogInteraction(model), containerColor = colors.surface,
        shape = RoundedCornerShape(topStart = 22.dp, topEnd = 22.dp),
        properties = ModalBottomSheetProperties(securePolicy = SecureFlagPolicy.SecureOn),
        dragHandle = {
            Box(Modifier.fillMaxWidth().height(30.dp), contentAlignment = Alignment.Center) {
                Surface(color = colors.muted, shape = RoundedCornerShape(50)) { Spacer(Modifier.width(42.dp).height(5.dp)) }
            }
        }) {
        Column(Modifier.fillMaxWidth().heightIn(min = 230.dp)) {
            Text(texts.getString(R.string.full_vault_name), color = colors.ink, fontSize = businessSp(18.sp), lineHeight = 1.5.em, fontWeight = FontWeight.Bold,
                modifier = Modifier.padding(start = 18.dp, end = 18.dp, bottom = 14.dp).semantics { heading() })
            Column(Modifier.fillMaxWidth().heightIn(max = nameHeight).verticalScroll(rememberScrollState()).padding(horizontal = 18.dp)) {
                Text(name, color = colors.ink, fontSize = businessSp(15.sp), lineHeight = 1.5.em)
            }
            Button(onClick = { model.onUserInteraction(); onDismiss() }, shape = RoundedCornerShape(11.dp),
                colors = ButtonDefaults.buttonColors(containerColor = colors.soft, contentColor = colors.ink),
                modifier = Modifier.padding(start = 18.dp, end = 18.dp, top = 14.dp, bottom = 24.dp).fillMaxWidth().heightIn(min = 48.dp)) {
                Text(texts.getString(R.string.close), fontSize = businessSp(14.sp), lineHeight = 1.5.em)
            }
        }
    }
}

@Composable
private fun BackupConfigurationBody(model: VaultModel, input: Long, enabled: Boolean,
                                    onChooseFile: (BackupDocumentKind, Long) -> Unit) {
    val texts = LocalResources.current
    val focus = LocalFocusManager.current
    val keyboard = LocalSoftwareKeyboardController.current
    val backup = model.backupState
    val exporting = backup.step == BackupStep.EXPORT
    val kind = if (exporting) BackupDocumentKind.EXPORT else BackupDocumentKind.IMPORT
    val selected = model.documentIntent?.let { it.kind == kind && it.uri != null && it.vaultId == model.state.vault?.id } == true
    if (!exporting) {
        BackupAction(if (selected) texts.getString(R.string.reselect_backup_file) else texts.getString(R.string.select_local_backup), enabled) { onChooseFile(kind, input) }
        if (!selected) return
        if (backup.documentName.isEmpty()) {
            BackupAction(texts.getString(R.string.review_selected_file), enabled, primary = true) { model.confirmBackupDocument(input) }
            return
        }
    } else if (selected && !model.exportSelectionPending) {
        BackupAction(texts.getString(R.string.reselect_backup_location), enabled) { focus.clearFocus(); keyboard?.hide(); onChooseFile(kind, input) }
    }
    if (exporting) {
        BackupCopy(texts.getString(R.string.backup_scope), size = 13, color = LocalBThemeColors.current.ink, weight = FontWeight.SemiBold)
        val scopes = listOf(BackupScope.ALL to texts.getString(R.string.scope_all), BackupScope.PASSWORDS to texts.getString(R.string.scope_passwords), BackupScope.NOTES to texts.getString(R.string.scope_notes))
        if (selected) BackupCopy(if (backup.custom) texts.getString(R.string.scope_custom) else scopes.first { it.first == backup.scope }.second, size = 16, color = LocalBThemeColors.current.ink)
        else Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
            scopes.forEach { (scope, label) ->
                BackupAction(label, enabled && !model.exportSelectionPending, selected = !backup.custom && backup.scope == scope) { model.changeBackup(input) { copy(scope = scope, custom = false) } }
            }
            BackupAction(texts.getString(R.string.scope_custom), enabled && !model.exportSelectionPending, selected = backup.custom) {
                focus.clearFocus(); keyboard?.hide(); model.openExportSelection(input)
            }
        }
        if (backup.custom) {
            BackupCopy(texts.getString(R.string.export_selection_summary,
                texts.getQuantityString(R.plurals.password_count, backup.selection.passwords.size, backup.selection.passwords.size),
                texts.getQuantityString(R.plurals.note_count, backup.selection.notes.size, backup.selection.notes.size)), size = 14)
            if (!selected) TextButton(onClick = { focus.clearFocus(); keyboard?.hide(); model.openExportSelection(input) }, enabled = enabled && !model.exportSelectionPending) {
                Text(texts.getString(R.string.export_change_selection), fontSize = businessSp(14.sp), lineHeight = 1.5.em)
            }
        }
    }
    FormField(texts.getString(R.string.backup_password), backup.password, { value -> model.changeBackup(input) { copy(password = value) } },
        required = true, enabled = enabled && !model.exportSelectionPending, secret = true, placeholder = texts.getString(R.string.backup_password_hint))
    if (exporting) FormField(texts.getString(R.string.confirm_backup_password), backup.confirmation,
        { value -> model.changeBackup(input) { copy(confirmation = value) } }, required = true, enabled = enabled && !model.exportSelectionPending, secret = true)
    BackupNotice(texts.getString(R.string.backup_password_lost))
}

@Composable
private fun BackupPreviewBody(model: VaultModel, input: Long, enabled: Boolean) {
    val texts = LocalResources.current
    val backup = model.backupState
    val preview = backup.preview ?: return
    val total = preview.passwordCount + preview.noteCount
    val colors = LocalBThemeColors.current
    BackupCopy(texts.getString(R.string.appearance_summary, texts.getQuantityString(R.plurals.password_count, preview.passwordCount, preview.passwordCount), texts.getQuantityString(R.plurals.note_count, preview.noteCount, preview.noteCount)),
        size = 16, color = colors.ink)
    Row(Modifier.fillMaxWidth().background(colors.soft, RoundedCornerShape(12.dp)).padding(4.dp)) {
        listOf(BackupImportKind.PASSWORD to texts.getString(R.string.record_type_passwords), BackupImportKind.NOTE to texts.getString(R.string.record_type_notes)).forEach { (kind, label) ->
            TextButton(onClick = { model.selectBackupKind(kind, input) }, enabled = enabled,
                modifier = Modifier.weight(1f).heightIn(min = 48.dp).semantics { selected = kind == backup.previewKind },
                shape = RoundedCornerShape(9.dp), colors = ButtonDefaults.textButtonColors(
                    containerColor = if (kind == backup.previewKind) colors.surface else Color.Transparent, contentColor = colors.ink,
                    disabledContainerColor = if (kind == backup.previewKind) colors.surface else Color.Transparent, disabledContentColor = colors.ink)) {
                Text(label, fontSize = businessSp(16.sp), lineHeight = 1.5.em)
            }
        }
    }
    BackupPreviewFilters(model, input)
    if (backup.listReadError.isNotEmpty()) BackupCopy(backup.listReadError.localized(), size = 13, color = colors.error)
    if (total == 0) BackupNotice(texts.getString(R.string.backup_empty))
    Column(verticalArrangement = Arrangement.spacedBy(16.dp)) {
        backup.rows.forEach { row -> key(backup.previewKind, row.sourceIndex) {
            Surface(color = colors.surface, shape = RoundedCornerShape(16.dp)) {
                Row(Modifier.fillMaxWidth().padding(16.dp), verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                    if (row.decisionRequired) {
                        val checked = row.sourceIndex in backup.currentGroup.selected
                        Box(Modifier.size(48.dp).background(colors.soft, RoundedCornerShape(10.dp))
                            .border(1.dp, if (checked) colors.accentInk else colors.line, RoundedCornerShape(10.dp))
                            .toggleable(checked, enabled, Role.Checkbox) { model.selectBackupRow(backup.previewKind, row.sourceIndex, it, input) }
                            .semantics { contentDescription = texts.getString(R.string.backup_select_row, row.sourceIndex + 1) }, contentAlignment = Alignment.Center) {
                            if (checked) Icon(bIcon("check"), null, Modifier.size(18.dp), tint = colors.accentInk)
                        }
                    } else Spacer(Modifier.size(48.dp))
                    Surface(onClick = { model.openBackupDetail(row.sourceIndex, input, backup.previewKind) }, enabled = enabled, color = Color.Transparent, modifier = Modifier.weight(1f)) {
                    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                    Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                        Text(row.title, color = colors.ink, fontWeight = FontWeight.SemiBold, fontSize = businessSp(17.sp),
                            lineHeight = 1.5.em, maxLines = 2, overflow = TextOverflow.Ellipsis)
                        val summary = if (backup.previewKind == BackupImportKind.PASSWORD) row.account.ifEmpty { texts.getString(R.string.account_empty) }
                            else row.preview.ifEmpty { texts.getString(R.string.view_note) }
                        Text(summary, color = colors.muted, fontSize = businessSp(14.sp), lineHeight = 1.5.em,
                            maxLines = 2, overflow = TextOverflow.Ellipsis)
                        val action = if (backup.previewKind == BackupImportKind.PASSWORD) when (backup.decisions.passwords[row.sourceIndex]?.action) {
                            PasswordImportAction.SKIP -> texts.getString(R.string.skipped); PasswordImportAction.OVERWRITE -> texts.getString(R.string.will_replace); null -> null
                        } else when (backup.decisions.notes[row.sourceIndex]?.action) {
                            NoteImportAction.SKIP -> texts.getString(R.string.skipped); NoteImportAction.OVERWRITE -> texts.getString(R.string.will_replace); NoteImportAction.KEEP_BOTH -> texts.getString(R.string.will_add); null -> null
                        }
                        BackupCopy(if (row.alreadyExists) texts.getString(R.string.already_exists) else action ?: if (row.decisionRequired) texts.getString(R.string.choose_action) else texts.getString(R.string.will_add), size = 13, color = colors.accentInk)
                    }
                    Icon(bIcon("chevron_right"), texts.getString(R.string.view_details), Modifier.size(18.dp), tint = colors.muted)
                    }
                    }
                }
            }
        } }
    }
    val count = backup.pageInfo?.matchedCount ?: if (backup.previewKind == BackupImportKind.PASSWORD) preview.passwordCount else preview.noteCount
    val originalCount = if (backup.previewKind == BackupImportKind.PASSWORD) preview.passwordCount else preview.noteCount
    if (count == 0 && total > 0) BackupCopy(texts.getString(if (originalCount > 0) R.string.filter_empty
        else if (backup.previewKind == BackupImportKind.PASSWORD) R.string.backup_no_passwords else R.string.backup_no_notes), size = 13)
    backup.detail?.let { detail -> backup.rows.firstOrNull { it.sourceIndex == detail.sourceIndex }?.let { row ->
        key(detail.token) { BackupDetailSheet(model, row, detail, input) }
    } }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun BackupPreviewFilters(model: VaultModel, input: Long) {
    val texts = LocalResources.current
    val backup = model.backupState
    val group = backup.currentGroup
    var menu by remember(backup.preview?.id, backup.previewKind) { mutableStateOf<String?>(null) }
    val states = BackupImportFilter.entries
    val stateLabels = states.map { texts.getString(when (it) {
        BackupImportFilter.ALL -> R.string.all
        BackupImportFilter.PENDING -> R.string.backup_filter_pending
        BackupImportFilter.DIFFERENT -> R.string.backup_filter_different
        BackupImportFilter.SKIPPED -> R.string.skipped
    }) }
    val fields = listOf<BackupComparisonField?>(null, BackupComparisonField.TITLE) +
        if (backup.previewKind == BackupImportKind.PASSWORD) listOf(BackupComparisonField.ACCOUNT, BackupComparisonField.PASSWORD,
            BackupComparisonField.NOTES, BackupComparisonField.TOTP_SECRET, BackupComparisonField.RECOVERY_CODES, BackupComparisonField.FAVORITE)
        else listOf(BackupComparisonField.NOTES, BackupComparisonField.FAVORITE)
    val fieldLabels = fields.map { texts.getString(it?.let { field -> backupFieldLabel(field, backup.previewKind) } ?: R.string.backup_filter_any_field) }
    Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
        listOf(Triple("status", R.string.backup_filter_status, stateLabels[states.indexOf(group.query.state)]),
            Triple("field", R.string.backup_filter_field, fieldLabels[fields.indexOf(group.query.changedField)])).forEach { (id, label, value) ->
            Surface(onClick = { if (model.onUserInteraction()) menu = id }, enabled = !model.state.busy,
                modifier = Modifier.weight(1f), color = LocalBThemeColors.current.surface, shape = RoundedCornerShape(12.dp)) {
                Row(Modifier.padding(12.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                    Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                        BackupCopy(texts.getString(label), size = 13)
                        BackupCopy(value, size = 14, color = LocalBThemeColors.current.ink, lineHeight = 1.5.em)
                    }
                    Icon(bIcon("chevron_down"), null, Modifier.size(16.dp), tint = LocalBThemeColors.current.muted)
                }
            }
        }
    }
    val unknown = backup.pageInfo?.awaitingTargetCount ?: 0
    if (unknown > 0) Column {
        BackupCopy(texts.getString(R.string.backup_filter_target_pending, unknown), size = 13)
        if (group.query.changedField != null) TextButton(onClick = { model.filterBackup(backup.previewKind, group.query.copy(changedField = null), input) }, enabled = !model.state.busy) {
            Text(texts.getString(R.string.backup_filter_clear_field), fontSize = businessSp(14.sp), lineHeight = 1.5.em)
        }
    }
    menu?.let { selectedMenu ->
        val choosingState = selectedMenu == "status"
        BackupOptionsDialog(model, texts.getString(if (choosingState) R.string.backup_filter_status else R.string.backup_filter_field),
            if (choosingState) stateLabels else fieldLabels, if (choosingState) states.indexOf(group.query.state) else fields.indexOf(group.query.changedField),
            onDismiss = { menu = null }) { index ->
            menu = null
            model.filterBackup(backup.previewKind, if (choosingState) group.query.copy(state = states[index]) else group.query.copy(changedField = fields[index]), input)
        }
    }
}

@Composable
private fun BackupReviewDialogs(model: VaultModel, input: Long) {
    val texts = LocalResources.current
    val backup = model.backupState
    backup.batchReview?.let { review ->
        var acknowledge by remember(review.token) { mutableStateOf(false) }
        val proposal = review.proposal
        val applied = proposal.appliedSourceIndices
        val note = proposal.kind == BackupImportKind.NOTE
        val imported = if (note) applied.count { proposal.decisions.notes[it]?.action == NoteImportAction.KEEP_BOTH } else 0
        val overwritten = applied.count { if (note) proposal.decisions.notes[it]?.action == NoteImportAction.OVERWRITE else proposal.decisions.passwords[it]?.action == PasswordImportAction.OVERWRITE }
        val skipped = applied.count { if (note) proposal.decisions.notes[it]?.action == NoteImportAction.SKIP else proposal.decisions.passwords[it]?.action == PasswordImportAction.SKIP }
        val legacy = proposal.legacyRecoveryRemovalIndices.size
        val cleared = proposal.recoveryRemovalIndices.size
        AlertDialog(modifier = Modifier.recordDialogInteraction(model), properties = DialogProperties(securePolicy = SecureFlagPolicy.SecureOn),
            containerColor = LocalBThemeColors.current.surface, onDismissRequest = { model.dismissBackupReview(input) },
            title = { BackupHeading(texts.getString(R.string.backup_batch_title), 20) },
            text = { Column(Modifier.verticalScroll(rememberScrollState()), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                BackupCopy(texts.getString(R.string.backup_batch_scope, review.selected.size, proposal.selectedOutsideFilterCount), color = LocalBThemeColors.current.ink, lineHeight = 1.8.em)
                BackupCopy(if (proposal.deferred.isEmpty()) texts.getString(R.string.backup_commit_counts, imported, overwritten, skipped)
                    else texts.getString(R.string.backup_batch_counts, imported, overwritten, skipped, proposal.deferred.size),
                    color = LocalBThemeColors.current.ink, lineHeight = 1.8.em)
                if (cleared > 0) BackupCopy(texts.getString(R.string.backup_batch_legacy, cleared), color = LocalBThemeColors.current.ink, lineHeight = 1.8.em)
                if (legacy > 0) {
                    Row(Modifier.fillMaxWidth().toggleable(acknowledge, role = Role.Checkbox) { if (model.onUserInteraction()) acknowledge = it },
                        verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        Checkbox(checked = acknowledge, onCheckedChange = null)
                        BackupCopy(texts.getString(R.string.backup_batch_acknowledge), color = LocalBThemeColors.current.ink, lineHeight = 1.8.em)
                    }
                }
            } }, confirmButton = { TextButton(onClick = { model.applyBackupBatch(review.token, acknowledge, input) },
                enabled = !model.state.busy && applied.isNotEmpty() && (legacy == 0 || acknowledge), modifier = Modifier.heightIn(min = 48.dp)) {
                Text(texts.getString(R.string.backup_batch_confirm), fontSize = businessSp(16.sp), lineHeight = 1.5.em)
            } }, dismissButton = { TextButton(onClick = { model.dismissBackupReview(input) }, modifier = Modifier.heightIn(min = 48.dp)) {
                Text(texts.getString(R.string.cancel), fontSize = businessSp(16.sp), lineHeight = 1.5.em)
            } })
    }
    backup.commitReview?.let { review ->
        val summary = review.summary
        AlertDialog(modifier = Modifier.recordDialogInteraction(model), properties = DialogProperties(securePolicy = SecureFlagPolicy.SecureOn),
            containerColor = LocalBThemeColors.current.surface, onDismissRequest = { model.dismissBackupReview(input) },
            title = { BackupHeading(texts.getString(R.string.backup_commit_title), 20) },
            text = { Column(Modifier.verticalScroll(rememberScrollState()), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                BackupCopy(texts.getString(R.string.backup_commit_counts, summary.imported, summary.overwritten, summary.skipped), color = LocalBThemeColors.current.ink, lineHeight = 1.8.em)
                BackupCopy(texts.getString(R.string.backup_commit_warning), color = LocalBThemeColors.current.ink, lineHeight = 1.8.em)
                if (summary.recoveryRemovalCount > 0) BackupCopy(texts.getString(R.string.backup_batch_legacy, summary.recoveryRemovalCount), color = LocalBThemeColors.current.ink, lineHeight = 1.8.em)
            } }, confirmButton = { TextButton(onClick = { model.confirmBackupCommit(review.token, input) }, enabled = !model.state.busy, modifier = Modifier.heightIn(min = 48.dp)) {
                Text(texts.getString(R.string.confirm_restore), fontSize = businessSp(16.sp), lineHeight = 1.5.em)
            } }, dismissButton = { TextButton(onClick = { model.dismissBackupReview(input) }, modifier = Modifier.heightIn(min = 48.dp)) {
                Text(texts.getString(R.string.cancel), fontSize = businessSp(16.sp), lineHeight = 1.5.em)
            } })
    }
}

@Composable
private fun BackupOptionsDialog(model: VaultModel, title: String, labels: List<String>, selected: Int = -1,
                                onDismiss: () -> Unit, onSelect: (Int) -> Unit) {
    val texts = LocalResources.current
    AlertDialog(modifier = Modifier.recordDialogInteraction(model), properties = DialogProperties(securePolicy = SecureFlagPolicy.SecureOn),
        onDismissRequest = { model.onUserInteraction(); onDismiss() }, containerColor = LocalBThemeColors.current.surface,
        title = { BackupHeading(title, 20) }, text = {
            Column(Modifier.verticalScroll(rememberScrollState())) {
                labels.forEachIndexed { index, label ->
                    TextButton(onClick = { if (model.onUserInteraction()) onSelect(index) }, enabled = !model.state.busy,
                        modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp)) {
                        Text(label, Modifier.weight(1f), color = LocalBThemeColors.current.ink, fontSize = businessSp(16.sp), lineHeight = 1.5.em)
                        if (index == selected) Icon(bIcon("check"), null, tint = LocalBThemeColors.current.accentInk)
                    }
                }
            }
        }, confirmButton = { TextButton(onClick = { model.onUserInteraction(); onDismiss() }) {
            Text(texts.getString(R.string.cancel), fontSize = businessSp(16.sp), lineHeight = 1.5.em)
        } })
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun BackupDetailSheet(model: VaultModel, row: BackupImportRow, detail: BackupDetail, input: Long) {
    val texts = LocalResources.current
    val backup = model.backupState
    val enabled = !model.state.busy && backup.readError.isEmpty()
    val colors = LocalBThemeColors.current
    val bodyScroll = remember(detail.token, backup.comparisonTargetId) { ScrollState(0) }
    val candidateScroll = remember(detail.token, backup.candidateOffset) { ScrollState(0) }
    val expanded = backup.expandedField
    var recoveryConfirmation by remember(detail.token) { mutableStateOf(false) }
    val focus = LocalFocusManager.current
    LaunchedEffect(detail.token) {
        focus.clearFocus()
        model.backupComparison(null, input, detail.token)
    }
    val topSpace = 48.dp
    val panelHeight = with(LocalDensity.current) {
        ((LocalWindowInfo.current.containerSize.height - WindowInsets.safeDrawing.getBottom(this)).toDp() - topSpace) * 0.9f + topSpace
    }
    ModalBottomSheet(onDismissRequest = { model.closeBackupDetail(detail.token) },
        sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true),
        sheetGesturesEnabled = false, dragHandle = null,
        modifier = Modifier.recordDialogInteraction(model), containerColor = colors.surface,
        shape = RoundedCornerShape(topStart = 22.dp, topEnd = 22.dp),
        properties = ModalBottomSheetProperties(securePolicy = SecureFlagPolicy.SecureOn, shouldDismissOnBackPress = false)) {
        BackHandler { model.back() }
        // 保留原顶部留白和外框尺寸，阅读内容的滚动不再传给整张面板。
        Column(Modifier.fillMaxWidth().height(panelHeight).padding(top = topSpace)) {
            Column(Modifier.padding(horizontal = 20.dp)) {
                Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                    Text(texts.getString(expanded?.let { backupFieldLabel(it, detail.kind) } ?: R.string.backup_compare_title), color = colors.ink, fontSize = businessSp(20.sp),
                        lineHeight = 1.4.em, fontWeight = FontWeight.Bold, modifier = Modifier.weight(1f).semantics { heading() })
                    if (backup.reading) BackupCopy(texts.getString(R.string.loading), size = 13, modifier = Modifier.semantics { liveRegion = LiveRegionMode.Polite })
                }
                Text(texts.getString(R.string.backup_item_number, row.sourceIndex + 1) + " · " + row.title,
                    color = colors.muted, fontSize = businessSp(13.sp), lineHeight = 1.5.em, maxLines = 1, overflow = TextOverflow.Ellipsis,
                    modifier = Modifier.padding(top = 8.dp))
                backup.textRequest?.let { request ->
                    val candidateIndex = backup.candidates.indexOfFirst { it.id == request.targetId }
                    val label = if (request.targetId == null) texts.getString(R.string.backup_item_number, row.sourceIndex + 1)
                        else if (candidateIndex >= 0) texts.getString(R.string.current_note_number, backup.candidateOffset + candidateIndex + 1) else texts.getString(R.string.current_matching_password)
                    val title = backup.candidates.getOrNull(candidateIndex)?.title ?: row.title
                    Text("$label · $title", color = colors.muted, fontSize = businessSp(13.sp), lineHeight = 1.5.em,
                        maxLines = 2, overflow = TextOverflow.Ellipsis)
                }
                if (backup.readError.isNotEmpty() && backup.fieldRequest == null) BackupCopy(backup.readError.localized(), size = 13, color = colors.error)
            }
            if (expanded != null) {
                BackupLongText(model, input, detail, expanded, Modifier.weight(1f))
            } else {
                Column(Modifier.weight(1f).verticalScroll(if (backup.choosingTarget) candidateScroll else bodyScroll)
                    .padding(horizontal = 4.dp, vertical = 8.dp)) {
                    BackupComparisonBody(model, input, detail)
                }
                HorizontalDivider(color = colors.line)
                Column(Modifier.fillMaxWidth().padding(horizontal = 20.dp, vertical = 12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    val note = detail.kind == BackupImportKind.NOTE
                    val passwordChoice = backup.decisions.passwords[row.sourceIndex]
                    val noteChoice = backup.decisions.notes[row.sourceIndex]
                    val skipped = if (note) noteChoice?.action == NoteImportAction.SKIP else passwordChoice?.action == PasswordImportAction.SKIP
                    val overwritten = if (note) noteChoice?.action == NoteImportAction.OVERWRITE else passwordChoice?.action == PasswordImportAction.OVERWRITE
                    val target = backup.comparison?.targetId
                    val recovery = backup.comparison?.fields?.firstOrNull { it.field == BackupComparisonField.RECOVERY_CODES }
                    val clearsRecovery = row.legacyRecoveryWillClear || recovery?.source?.hasValue == false && recovery.current?.hasValue == true
                    val occupied = note && target != null && backup.decisions.notes.any { (index, choice) ->
                        index != row.sourceIndex && choice.action == NoteImportAction.OVERWRITE && choice.targetId == target
                    }
                    BackupCopy(texts.getString(when {
                        row.alreadyExists -> R.string.identical_item_skip
                        !row.decisionRequired -> R.string.no_name_conflict
                        overwritten -> R.string.will_replace
                        skipped -> R.string.skipped
                        note && noteChoice?.action == NoteImportAction.KEEP_BOTH -> R.string.will_add
                        else -> R.string.choose_action
                    }), size = 13)
                    if (row.decisionRequired) {
                        if (note) BackupAction(texts.getString(R.string.keep_all_add_backup_note), enabled, selected = noteChoice?.action == NoteImportAction.KEEP_BOTH) {
                            model.chooseBackupNote(row.sourceIndex, NoteImportChoice(NoteImportAction.KEEP_BOTH), input, detail.token)
                        }
                        Row(Modifier.fillMaxWidth().height(IntrinsicSize.Min), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                            BackupAction(texts.getString(R.string.backup_compare_keep_current), enabled,
                                Modifier.weight(1f).fillMaxHeight().semantics { contentDescription = texts.getString(R.string.keep_current_skip) }, selected = skipped) {
                                if (note) model.chooseBackupNote(row.sourceIndex, NoteImportChoice(NoteImportAction.SKIP), input, detail.token)
                                else model.chooseBackupPassword(row.sourceIndex, PasswordImportChoice(PasswordImportAction.SKIP), input, detail.token)
                            }
                            BackupAction(texts.getString(R.string.backup_compare_replace_current), enabled && target != null && !occupied && backup.comparison?.targetReserved != true,
                                Modifier.weight(1f).fillMaxHeight().semantics { contentDescription = texts.getString(R.string.replace_whole_item) }, selected = overwritten && (!note || noteChoice?.targetId == target)) {
                                if (note) model.chooseBackupNote(row.sourceIndex, NoteImportChoice(NoteImportAction.OVERWRITE, target), input, detail.token)
                                else if (row.legacyRecoveryWillClear) recoveryConfirmation = true
                                else model.chooseBackupPassword(row.sourceIndex, PasswordImportChoice(PasswordImportAction.OVERWRITE), input, detail.token)
                            }
                        }
                        if (note && overwritten && noteChoice?.targetId != target) BackupCopy(texts.getString(R.string.backup_compare_other_target_choice), size = 13)
                        if (overwritten) BackupCopy(texts.getString(if (note) R.string.backup_commit_warning else R.string.replace_all_fields) +
                            if (clearsRecovery) " " + texts.getString(R.string.current_codes_cleared) else "", size = 13)
                    }
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                        if (backup.choosingTarget && backup.comparison != null) BackupAction(texts.getString(R.string.back_to_details), true, Modifier.weight(1f)) { model.closeBackupCandidates(detail.token) }
                        BackupAction(texts.getString(R.string.close), true, Modifier.weight(1f)) { model.closeBackupDetail(detail.token) }
                    }
                }
            }
        }
    }
    if (recoveryConfirmation && enabled && row.legacyRecoveryWillClear) {
        AlertDialog(
            modifier = Modifier.recordDialogInteraction(model),
            onDismissRequest = { model.onUserInteraction(); recoveryConfirmation = false },
            title = { Text(texts.getString(R.string.replace_clear_codes_question), lineHeight = (32f / 20).em, fontSize = businessSp(20.sp)) },
            text = { Text(texts.getString(R.string.legacy_codes_warning, row.sourceIndex + 1), fontSize = businessSp(14.sp), lineHeight = (24f / 14).em, modifier = Modifier.verticalScroll(rememberScrollState())) },
            confirmButton = { TextButton(onClick = {
                model.chooseBackupPassword(row.sourceIndex, PasswordImportChoice(PasswordImportAction.OVERWRITE, true), input, requireNotNull(backup.detail).token)
                recoveryConfirmation = false
            }, modifier = Modifier.heightIn(min = 48.dp)) { Text(texts.getString(R.string.confirm_replace_clear), lineHeight = (20f / 16).em, fontSize = businessSp(16.sp), color = LocalBThemeColors.current.error) } },
            dismissButton = { TextButton(onClick = { model.onUserInteraction(); recoveryConfirmation = false }, modifier = Modifier.heightIn(min = 48.dp)) { Text(texts.getString(R.string.cancel), lineHeight = (20f / 16).em, fontSize = businessSp(16.sp)) } },
            containerColor = LocalBThemeColors.current.surface,
            properties = DialogProperties(securePolicy = SecureFlagPolicy.SecureOn),
        )
    }
}

@Composable
private fun BackupLongText(model: VaultModel, input: Long, detail: BackupDetail, field: BackupComparisonField, modifier: Modifier) {
    val texts = LocalResources.current
    val colors = LocalBThemeColors.current
    val backup = model.backupState
    val summary = backup.comparison?.fields?.firstOrNull { it.field == field } ?: return
    val request = backup.fieldRequest?.takeIf { it.field == field }
    val pair = backup.fieldPair?.takeIf { request != null && it.field == field && it.offset == request.offset }
    val offset = pair?.offset ?: request?.offset ?: 0
    val total = maxOf(pair?.source?.total ?: summary.source.codePoints ?: 0, pair?.current?.total ?: summary.current?.codePoints ?: 0)
    val sourceScroll = remember(detail.token, backup.comparisonTargetId, field, pair?.offset) { ScrollState(0) }
    val currentScroll = remember(detail.token, backup.comparisonTargetId, field, pair?.offset) { ScrollState(0) }
    Column(modifier.fillMaxWidth()) {
        Column(Modifier.weight(1f).padding(horizontal = 20.dp, vertical = 12.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            listOf(true, false).forEach { source ->
                Surface(Modifier.weight(1f).fillMaxWidth(), shape = RoundedCornerShape(12.dp), color = colors.surface,
                    border = androidx.compose.foundation.BorderStroke(1.dp, colors.line)) {
                    Column {
                        BackupCopy(texts.getString(if (source) R.string.backup_compare_source else R.string.backup_compare_current),
                            Modifier.fillMaxWidth().background(colors.soft).padding(horizontal = 12.dp, vertical = 8.dp), size = 14,
                            color = colors.ink, lineHeight = 1.5.em)
                        HorizontalDivider(color = colors.line)
                        Column(Modifier.weight(1f).fillMaxWidth().verticalScroll(if (source) sourceScroll else currentScroll)
                            .padding(horizontal = 12.dp, vertical = 10.dp)) {
                            BackupComparisonValue(field, if (source) summary.source else summary.current,
                                if (source) pair?.source else pair?.current, offset, secret = false,
                                waiting = pair == null, reading = backup.reading)
                        }
                    }
                }
            }
        }
        HorizontalDivider(color = colors.line)
        Column(Modifier.fillMaxWidth().padding(horizontal = 20.dp, vertical = 12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            if (backup.readError.isNotEmpty()) {
                BackupCopy(backup.readError.localized(), size = 13, color = colors.error)
                BackupAction(texts.getString(R.string.retry), !model.state.busy) { model.backupField(field, offset, input, detail.token) }
            } else {
                BackupCopy(texts.getString(R.string.section_number, offset / 4096 + 1), size = 13)
                Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                    BackupAction(texts.getString(R.string.previous_segment), !model.state.busy && pair != null && offset > 0, Modifier.weight(1f)) {
                        model.backupField(field, (offset - 4096).coerceAtLeast(0), input, detail.token)
                    }
                    BackupAction(texts.getString(R.string.next_segment), !model.state.busy && pair != null && offset + 4096 < total, Modifier.weight(1f)) {
                        model.backupField(field, offset + 4096, input, detail.token)
                    }
                }
            }
            BackupAction(texts.getString(R.string.back_to_details), true) { model.closeBackupLongText(detail.token) }
        }
    }
}

@Composable
private fun BackupComparisonCandidates(model: VaultModel, row: BackupImportRow, input: Long, detail: BackupDetail) {
    val texts = LocalResources.current
    val colors = LocalBThemeColors.current
    val backup = model.backupState
    BackupHeading(texts.getString(R.string.backup_compare_choose_current), 16)
    backup.candidates.forEachIndexed { index, candidate -> key(candidate.id) {
        val selected = backup.comparison?.targetId == candidate.id
        val occupied = backup.decisions.notes.any { (source, choice) -> source != row.sourceIndex && choice.action == NoteImportAction.OVERWRITE && choice.targetId == candidate.id }
        Column(Modifier.fillMaxWidth().border(1.dp, if (selected) colors.accentInk else colors.line, RoundedCornerShape(12.dp)).padding(12.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp)) {
            BackupCopy(texts.getString(R.string.current_note_matching, backup.candidateOffset + index + 1,
                texts.getString(if (candidate.exactTitle) R.string.exact_name else R.string.similar_name)) +
                if (backup.decisions.notes[row.sourceIndex]?.let { it.action == NoteImportAction.OVERWRITE && it.targetId == candidate.id } == true)
                    texts.getString(R.string.will_be_replaced_suffix) else "", size = 13)
            BackupHeading(candidate.title + if (candidate.titleTruncated) texts.getString(R.string.name_preview_suffix) else "", 16)
            BackupCopy(texts.getString(R.string.note_body_preview, candidate.preview.ifEmpty { texts.getString(R.string.preview_empty) }), color = colors.ink)
            if (occupied) BackupCopy(texts.getString(R.string.target_occupied), color = colors.error, size = 13)
            if (candidate.reserved) BackupCopy(texts.getString(R.string.identical_target_reserved), size = 13)
            BackupAction(texts.getString(R.string.backup_compare_select_current), !model.state.busy, selected = selected) {
                model.backupComparison(candidate.id, input, detail.token)
            }
        }
    } }
    BackupPagination(backup.candidateOffset, backup.candidates.size, row.candidateCount, !model.state.busy) {
        model.backupCandidates(row.sourceIndex, it, input, detail.token)
    }
}

@Composable
private fun BackupComparisonBody(model: VaultModel, input: Long, detail: BackupDetail) {
    val texts = LocalResources.current
    val backup = model.backupState
    val comparison = backup.comparison
    val row = backup.rows.firstOrNull { it.sourceIndex == detail.sourceIndex } ?: return
    Column(Modifier.fillMaxWidth().padding(horizontal = 16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        if (backup.choosingTarget && detail.kind == BackupImportKind.NOTE) {
            BackupComparisonCandidates(model, row, input, detail)
            if (comparison == null) BackupCopy(texts.getString(R.string.backup_compare_target_pending), size = 13)
            return@Column
        }
        if (comparison == null) {
            if (!backup.reading && backup.readError.isNotEmpty()) BackupAction(texts.getString(R.string.reload), !model.state.busy) {
                model.backupComparison(backup.comparisonTargetId, input, detail.token)
            }
            return@Column
        }
        if (detail.kind == BackupImportKind.NOTE && row.candidateCount > 1 && !row.alreadyExists) {
            Text(texts.getString(R.string.backup_compare_current) + " · " + comparison.fields.firstOrNull { it.field == BackupComparisonField.TITLE }?.current?.preview.orEmpty(),
                color = LocalBThemeColors.current.muted, fontSize = businessSp(13.sp), lineHeight = 1.9.em, maxLines = 1, overflow = TextOverflow.Ellipsis)
            BackupAction(texts.getString(R.string.backup_compare_choose_current), !model.state.busy) {
                model.backupCandidates(row.sourceIndex, backup.candidateOffset, input, detail.token)
            }
        }
        if (comparison.alreadyExists) BackupNotice(texts.getString(R.string.backup_compare_metadata_only))
        var metadataHeading = false
        comparison.fields.forEach { field ->
            val metadata = field.field in setOf(BackupComparisonField.STRENGTH, BackupComparisonField.PASSWORD_CHANGED_AT,
                BackupComparisonField.CREATED_AT, BackupComparisonField.UPDATED_AT, BackupComparisonField.SORT_ORDER)
            if (metadata && !metadataHeading) {
                BackupHeading(texts.getString(R.string.backup_compare_metadata), 16)
                metadataHeading = true
            }
            BackupComparisonCard(model, input, detail, field)
        }
    }
}

@Composable
private fun BackupComparisonCard(model: VaultModel, input: Long, detail: BackupDetail, summary: BackupComparisonFieldSummary) {
    val texts = LocalResources.current
    val colors = LocalBThemeColors.current
    val backup = model.backupState
    val field = summary.field
    val secret = field in setOf(BackupComparisonField.PASSWORD, BackupComparisonField.TOTP_SECRET, BackupComparisonField.RECOVERY_CODES)
    val request = backup.fieldRequest?.takeIf { it.field == field }
    val pair = backup.fieldPair?.takeIf { request != null && it.field == field && it.offset == request.offset }
    val fieldLabel = backupFieldLabel(field, detail.kind)
    val different = summary.changed && summary.current != null && !summary.source.missing
    Column(Modifier.fillMaxWidth().background(if (different) colors.accentInk.copy(alpha = 0.06f).compositeOver(colors.surface) else colors.surface, RoundedCornerShape(12.dp))
        .border(1.dp, if (different) colors.accentInk.copy(alpha = 0.35f).compositeOver(colors.line) else colors.line, RoundedCornerShape(12.dp)).padding(12.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            Text(texts.getString(fieldLabel), modifier = Modifier.weight(1f).alignByBaseline(), color = colors.ink, fontWeight = FontWeight.Bold,
                fontSize = businessSp(16.sp), lineHeight = 1.4.em)
            if (!summary.source.missing) BackupCopy(texts.getString(if (summary.current == null) R.string.backup_compare_no_current
                else if (summary.changed) R.string.backup_compare_different else R.string.backup_compare_same), size = 13,
                modifier = Modifier.alignByBaseline(), color = if (different) colors.accentInk else colors.muted,
                weight = if (different) FontWeight.SemiBold else FontWeight.Normal)
        }
        val waiting = request != null && pair == null
        Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            BackupComparisonSide(texts.getString(R.string.backup_compare_source), field, summary.source, pair?.source, pair?.offset ?: 0,
                secret, waiting, backup.reading, Modifier.weight(1f), summaryOnly = field == BackupComparisonField.NOTES)
            BackupComparisonSide(texts.getString(R.string.backup_compare_current), field, summary.current, pair?.current, pair?.offset ?: 0,
                secret, waiting, backup.reading, Modifier.weight(1f), summaryOnly = field == BackupComparisonField.NOTES)
        }
        if (field == BackupComparisonField.NOTES) {
            BackupAction(texts.getString(R.string.backup_read_full_text), !model.state.busy) {
                model.openBackupLongText(field, input, detail.token)
            }
        }
        if (field == BackupComparisonField.CREATED_AT && summary.writePolicy == BackupComparisonWritePolicy.KEEP_CURRENT &&
            summary.current != null && backup.comparison?.alreadyExists == false)
            BackupCopy(texts.getString(R.string.backup_compare_preserve_created), size = 13)
        if (field == BackupComparisonField.SORT_ORDER) BackupCopy(texts.getString(R.string.backup_compare_preserve_sort), size = 13)
        if (secret) {
            val failed = request != null && backup.readError.isNotEmpty()
            val actionLabel = texts.getString(if (failed) R.string.retry else if (request != null) R.string.backup_compare_hide_both else R.string.backup_compare_show_both)
            BackupAction(actionLabel, request != null || !model.state.busy && (summary.source.hasValue || summary.current?.hasValue == true),
                Modifier.semantics { contentDescription = texts.getString(R.string.backup_compare_field_action, texts.getString(fieldLabel), actionLabel) }) {
                if (failed) model.backupField(field, requireNotNull(request).offset, input, detail.token)
                else if (request != null) model.hideBackupField(detail.token) else model.backupField(field, 0, input, detail.token)
            }
        }
        if (request != null && backup.readError.isNotEmpty()) {
            BackupCopy(backup.readError.localized(), color = colors.error)
            if (!secret) BackupAction(texts.getString(R.string.retry), !model.state.busy) {
                model.backupField(field, request.offset, input, detail.token)
            }
        } else if (request != null && backup.reading && !secret) BackupAction(texts.getString(R.string.cancel), true) {
            model.hideBackupField(detail.token)
        }
        val offset = pair?.offset ?: 0
        val step = if (field == BackupComparisonField.RECOVERY_CODES) 20 else 4096
        val total = if (pair != null) maxOf(pair.source.total, pair.current?.total ?: 0)
            else if (!secret) maxOf(summary.source.codePoints ?: 0, summary.current?.codePoints ?: 0) else 0
        if (field != BackupComparisonField.NOTES && !waiting && (pair != null || !secret) && total > step) {
            BackupCopy(if (field == BackupComparisonField.RECOVERY_CODES) texts.getString(R.string.backup_compare_codes_range, offset + 1, minOf(offset + step, total))
                else texts.getString(R.string.section_number, offset / step + 1), size = 13)
            Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                BackupAction(texts.getString(R.string.previous_segment), !model.state.busy && offset > 0, Modifier.weight(1f)) {
                    model.backupField(field, (offset - step).coerceAtLeast(0), input, detail.token)
                }
                BackupAction(texts.getString(R.string.next_segment), !model.state.busy && offset + step < total, Modifier.weight(1f)) {
                    model.backupField(field, offset + step, input, detail.token)
                }
            }
        }
    }
}

@Composable
private fun BackupComparisonSide(label: String, field: BackupComparisonField, summary: BackupComparisonValueSummary?,
                                 value: BackupImportFieldValue?, offset: Int, secret: Boolean, waiting: Boolean, reading: Boolean,
                                 modifier: Modifier = Modifier, summaryOnly: Boolean = false) {
    val scroll = remember(offset, waiting) { ScrollState(0) }
    Column(modifier) {
        BackupCopy(label, size = 13)
        if (summaryOnly) BackupComparisonValue(field, summary, null, 0, secret, waiting, reading, maxLines = 3)
        else Column(Modifier.fillMaxWidth().heightIn(max = 176.dp).verticalScroll(scroll)) {
            BackupComparisonValue(field, summary, value, offset, secret, waiting, reading)
        }
    }
}

@Composable
private fun BackupComparisonValue(field: BackupComparisonField, summary: BackupComparisonValueSummary?, value: BackupImportFieldValue?,
                                  offset: Int, secret: Boolean, waiting: Boolean, reading: Boolean, maxLines: Int = Int.MAX_VALUE) {
    val texts = LocalResources.current
    val colors = LocalBThemeColors.current
    when {
        summary == null -> BackupCopy(texts.getString(R.string.backup_compare_no_current), color = colors.muted)
        waiting -> BackupCopy(texts.getString(if (reading) R.string.loading else R.string.backup_compare_unavailable), color = colors.muted)
        summary.missing || value?.missing == true -> BackupCopy(texts.getString(R.string.backup_compare_not_included), color = colors.muted)
        value != null && offset >= value.total && offset > 0 -> BackupCopy(texts.getString(R.string.backup_compare_end), color = colors.muted)
        value != null && field == BackupComparisonField.RECOVERY_CODES -> {
            if (value.recoveryCodes.isEmpty()) BackupCopy(texts.getString(R.string.not_entered))
            value.recoveryCodes.forEach { code ->
                BackupCopy("${code.index + 1}. ${code.value}", color = colors.ink)
                BackupCopy(texts.getString(if (code.used) R.string.used_locally else R.string.not_marked_used), size = 13)
            }
        }
        value != null -> BackupCopy(value.text?.ifEmpty { texts.getString(R.string.not_entered) } ?: texts.getString(R.string.not_entered), color = colors.ink, maxLines = maxLines)
        secret -> {
            BackupCopy(if (!summary.hasValue) texts.getString(R.string.not_entered) else "••••••", color = if (summary.hasValue) colors.ink else colors.muted)
            if (field == BackupComparisonField.RECOVERY_CODES) BackupCopy(texts.getQuantityString(R.plurals.recovery_codes_count, summary.count ?: 0, summary.count ?: 0), size = 13)
        }
        field == BackupComparisonField.FAVORITE -> BackupCopy(texts.getString(if (summary.preview == "true") R.string.is_favorite else R.string.not_favorite), color = colors.ink)
        field == BackupComparisonField.STRENGTH -> BackupCopy(when (summary.preview) {
            "weak" -> texts.getString(R.string.strength_weak)
            "fair" -> texts.getString(R.string.strength_fair)
            "strong" -> texts.getString(R.string.strength_strong)
            else -> texts.getString(R.string.not_entered)
        }, color = colors.ink)
        else -> BackupCopy(summary.preview?.ifEmpty { texts.getString(R.string.not_entered) } ?: texts.getString(R.string.not_entered), color = colors.ink, maxLines = maxLines)
    }
}

@Composable
private fun BackupPagination(offset: Int, shown: Int, count: Int, enabled: Boolean, onPage: (Int) -> Unit) {
    val texts = LocalResources.current
    if (count == 0 || offset == 0 && shown >= count) return
    BackupCopy(texts.getString(R.string.backup_page_range, offset + 1, offset + shown, count), size = 13)
    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
        BackupAction(texts.getString(R.string.previous_page), enabled && offset > 0, modifier = Modifier.weight(1f)) { onPage((offset - 20).coerceAtLeast(0)) }
        BackupAction(texts.getString(R.string.next_page), enabled && offset + shown < count, modifier = Modifier.weight(1f)) { onPage(offset + 20) }
    }
}

@Composable
private fun BackupAction(label: String, enabled: Boolean, modifier: Modifier = Modifier, selected: Boolean = false,
                         primary: Boolean = false, onClick: () -> Unit) {
    val texts = LocalResources.current
    val colors = LocalBThemeColors.current
    Button(onClick = onClick, enabled = enabled, shape = RoundedCornerShape(14.dp),
        colors = ButtonDefaults.buttonColors(containerColor = if (primary) colors.accentFill else colors.soft,
            contentColor = if (primary) colors.onAccent else colors.ink),
        modifier = modifier.fillMaxWidth().heightIn(min = 48.dp).then(if (selected) Modifier.border(1.dp, colors.accentInk, RoundedCornerShape(14.dp)) else Modifier)) {
        if (selected) Icon(bIcon("check"), texts.getString(R.string.backup_action_selected), Modifier.size(18.dp))
        Text(label, fontSize = businessSp(16.sp), lineHeight = 1.5.em)
    }
}

@Composable
private fun BackupEntry(title: String, subtitle: String, icon: String, enabled: Boolean, onClick: () -> Unit) {
    Surface(onClick = onClick, enabled = enabled, color = Color.Transparent) {
        Row(Modifier.fillMaxWidth().heightIn(min = 85.dp).padding(vertical = 16.dp), verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(14.dp)) {
            Surface(color = LocalBThemeColors.current.soft, shape = RoundedCornerShape(13.dp)) {
                Box(Modifier.size(40.dp), contentAlignment = Alignment.Center) {
                    Icon(bIcon(icon), null, Modifier.size(24.dp), tint = LocalBThemeColors.current.accentInk)
                }
            }
            Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(5.dp)) {
                Text(title, color = LocalBThemeColors.current.ink, fontSize = businessSp(15.sp), lineHeight = 1.5.em, fontWeight = FontWeight.SemiBold)
                Text(subtitle, color = LocalBThemeColors.current.muted, fontSize = businessSp(13.sp), lineHeight = 1.5.em,
                    style = TextStyle(platformStyle = PlatformTextStyle(includeFontPadding = false), lineHeightStyle = BLineHeightStyle))
            }
            Icon(bIcon("chevron_right"), null, Modifier.size(16.dp), tint = LocalBThemeColors.current.muted)
        }
    }
}

@Composable
private fun BackupNotice(text: String) {
    Surface(color = LocalBThemeColors.current.soft, shape = RoundedCornerShape(12.dp)) {
        BackupCopy(text, size = 13, color = LocalBThemeColors.current.ink, modifier = Modifier.fillMaxWidth().padding(14.dp))
    }
}

@Composable
private fun BackupHeading(text: String, size: Int) {
    Text(text, fontSize = businessSp(size.sp), lineHeight = 1.4.em, color = LocalBThemeColors.current.ink, fontWeight = FontWeight.Bold,
        modifier = Modifier.fillMaxWidth().semantics { heading() }, style = TextStyle(platformStyle = PlatformTextStyle(includeFontPadding = false), lineHeightStyle = BLineHeightStyle))
}

@Composable
private fun BackupProcessingStatus(label: String) {
    val dots by rememberInfiniteTransition(label = "备份等待").animateValue(
        initialValue = 1, targetValue = 3, typeConverter = Int.VectorConverter,
        animationSpec = infiniteRepeatable(keyframes {
            durationMillis = 1500
            1 at 0; 1 at 499; 2 at 500; 2 at 999; 3 at 1000
        }), label = "等待省略号",
    )
    val color = LocalBThemeColors.current.muted
    val message = buildAnnotatedString {
        append(label.removeSuffix("…"))
        // 三个点始终占位，动画只改变可见性。
        repeat(3) { index -> withStyle(SpanStyle(color = if (index < dots) color else Color.Transparent)) { append(".") } }
    }
    Text(message, fontSize = businessSp(13.sp), lineHeight = 1.9.em, color = color,
        modifier = Modifier.clearAndSetSemantics { text = AnnotatedString(label); liveRegion = LiveRegionMode.Polite },
        style = TextStyle(platformStyle = PlatformTextStyle(includeFontPadding = false), lineHeightStyle = BLineHeightStyle))
}

@Composable
private fun BackupCopy(text: String, modifier: Modifier = Modifier, size: Int = 14, color: Color = LocalBThemeColors.current.muted,
                       weight: FontWeight = FontWeight.Normal, lineHeight: androidx.compose.ui.unit.TextUnit = 1.9.em, maxLines: Int = Int.MAX_VALUE) {
    Text(text, modifier, fontSize = businessSp(size.sp), lineHeight = lineHeight, color = color, fontWeight = weight,
        maxLines = maxLines, overflow = TextOverflow.Ellipsis,
        style = TextStyle(platformStyle = PlatformTextStyle(includeFontPadding = false), lineHeightStyle = BLineHeightStyle))
}

private fun backupFieldLabel(field: BackupComparisonField, kind: BackupImportKind): Int = when (field) {
    BackupComparisonField.TITLE -> if (kind == BackupImportKind.NOTE) R.string.title else R.string.name
    BackupComparisonField.ACCOUNT -> R.string.account
    BackupComparisonField.PASSWORD -> R.string.password
    BackupComparisonField.NOTES -> if (kind == BackupImportKind.NOTE) R.string.note_body else R.string.notes_field
    BackupComparisonField.TOTP_SECRET -> R.string.backup_compare_totp_secret
    BackupComparisonField.RECOVERY_CODES -> R.string.recovery_codes
    BackupComparisonField.FAVORITE -> R.string.backup_compare_favorite
    BackupComparisonField.STRENGTH -> R.string.backup_compare_rating
    BackupComparisonField.PASSWORD_CHANGED_AT -> R.string.backup_compare_password_changed
    BackupComparisonField.CREATED_AT -> R.string.backup_compare_created
    BackupComparisonField.UPDATED_AT -> R.string.backup_compare_updated
    BackupComparisonField.SORT_ORDER -> R.string.backup_compare_sort
}
