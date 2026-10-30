package app.cangoo.android.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.selection.toggleable
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Checkbox
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalFocusManager
import androidx.compose.ui.platform.LocalResources
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.selected
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.em
import androidx.compose.ui.unit.sp
import app.cangoo.android.R
import app.cangoo.android.data.BackupImportKind

@Composable
internal fun BExportSelectionPage(model: VaultModel) {
    val view = model.exportSelectionState ?: return
    val texts = LocalResources.current
    val colors = LocalBThemeColors.current
    val focus = LocalFocusManager.current
    val listState = rememberLazyListState()
    val rows = view.visibleRows
    LaunchedEffect(view.token, view.query, view.kind) { listState.scrollToItem(0) }
    Column(Modifier.fillMaxSize()) {
        Column(Modifier.fillMaxWidth().padding(start = 20.dp, end = 20.dp, top = 12.dp)) {
            Column(Modifier.padding(bottom = 12.dp)) {
                FormField(texts.getString(R.string.search_password_notes), view.query,
                    { model.queryExportSelection(it, view.token) }, enabled = true, placeholder = texts.getString(R.string.search_items),
                    search = true, onClear = { model.queryExportSelection("", view.token) }, onDone = { focus.clearFocus() })
            }
            Row(Modifier.fillMaxWidth().background(colors.soft, RoundedCornerShape(12.dp)).padding(4.dp)) {
                listOf(BrowseKind.ALL to R.string.all, BrowseKind.PASSWORD to R.string.record_type_passwords,
                    BrowseKind.NOTE to R.string.record_type_notes).forEach { (kind, label) ->
                    TextButton(onClick = { focus.clearFocus(); model.filterExportSelection(kind, view.token) },
                        modifier = Modifier.weight(1f).heightIn(min = 48.dp).semantics { selected = view.kind == kind },
                        shape = RoundedCornerShape(9.dp), colors = ButtonDefaults.textButtonColors(
                            containerColor = if (view.kind == kind) colors.surface else Color.Transparent, contentColor = colors.ink)) {
                        Text(texts.getString(label), fontSize = businessSp(14.sp), lineHeight = 1.5.em)
                    }
                }
            }
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.CenterVertically) {
                TextButton(onClick = { focus.clearFocus(); model.toggleExportFiltered(view.token) }, enabled = !view.loading && rows.isNotEmpty(),
                    modifier = Modifier.weight(1f).heightIn(min = 48.dp)) {
                    Text(texts.getString(if (view.allVisibleSelected) R.string.export_deselect_filtered else R.string.export_select_filtered),
                        fontSize = businessSp(14.sp), lineHeight = 1.5.em, textAlign = TextAlign.Center)
                }
                TextButton(onClick = { focus.clearFocus(); model.clearAllExportSelections(view.token) }, enabled = !view.loading && !view.selected.empty,
                    modifier = Modifier.weight(1f).heightIn(min = 48.dp)) {
                    Text(texts.getString(R.string.export_clear_all), fontSize = businessSp(14.sp), lineHeight = 1.5.em, textAlign = TextAlign.Center)
                }
            }
        }
        LazyColumn(Modifier.weight(1f).fillMaxWidth(), state = listState, contentPadding = PaddingValues(start = 20.dp, end = 20.dp, bottom = 16.dp)) {
            if (view.loading || rows.isEmpty()) item {
                Text(texts.getString(if (view.loading) R.string.searching else R.string.search_empty), color = colors.muted,
                    fontSize = businessSp(14.sp), lineHeight = 1.5.em, modifier = Modifier.padding(vertical = 12.dp))
            }
            items(rows, key = { "${it.kind}:${it.id}" }) { row ->
                val selected = view.isSelected(row)
                Row(Modifier.fillMaxWidth().toggleable(selected, enabled = !view.loading, role = Role.Checkbox) {
                    focus.clearFocus(); model.toggleExportSelection(row, view.token)
                }.padding(vertical = 14.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                    Checkbox(selected, onCheckedChange = null)
                    BRecordMark(row.kind == BackupImportKind.NOTE)
                    Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                        Text(row.title, color = colors.ink, fontSize = businessSp(16.sp), lineHeight = 1.5.em,
                            fontWeight = FontWeight.SemiBold, maxLines = 2, overflow = TextOverflow.Ellipsis)
                        if (row.subtitle.isNotEmpty()) Text(row.subtitle, color = colors.muted, fontSize = businessSp(13.sp),
                            lineHeight = 1.5.em, maxLines = 2, overflow = TextOverflow.Ellipsis)
                    }
                }
                HorizontalDivider(color = colors.line)
            }
        }
        HorizontalDivider(color = colors.line)
        Column(Modifier.fillMaxWidth().padding(horizontal = 24.dp, vertical = 10.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            Text(texts.getString(R.string.export_selection_summary,
                texts.getQuantityString(R.plurals.password_count, view.selected.passwords.size, view.selected.passwords.size),
                texts.getQuantityString(R.plurals.note_count, view.selected.notes.size, view.selected.notes.size)),
                color = colors.ink, fontSize = businessSp(14.sp), lineHeight = 1.5.em,
                modifier = Modifier.semantics { liveRegion = LiveRegionMode.Polite })
            if (view.error.isNotEmpty()) Text(view.error.localized(), color = colors.error, fontSize = businessSp(14.sp), lineHeight = 1.5.em)
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                Button(onClick = { focus.clearFocus(); model.closeExportSelection() }, modifier = Modifier.heightIn(min = 48.dp),
                    shape = RoundedCornerShape(11.dp), contentPadding = PaddingValues(horizontal = 16.dp, vertical = 9.dp),
                    colors = ButtonDefaults.buttonColors(containerColor = colors.soft, contentColor = colors.ink)) {
                    Text(texts.getString(R.string.cancel), fontSize = businessSp(14.sp), lineHeight = 1.5.em)
                }
                Button(onClick = { focus.clearFocus(); model.confirmExportSelection(view.token) },
                    enabled = !view.loading && !view.selected.empty && view.error.isEmpty(),
                    modifier = Modifier.weight(1f).heightIn(min = 50.dp), shape = RoundedCornerShape(14.dp),
                    contentPadding = PaddingValues(horizontal = 18.dp, vertical = 12.dp),
                    colors = ButtonDefaults.buttonColors(containerColor = colors.accentFill, contentColor = colors.onAccent)) {
                    Text(texts.getString(R.string.export_confirm_selection), fontSize = businessSp(16.sp), lineHeight = 1.5.em)
                }
            }
        }
    }
}
