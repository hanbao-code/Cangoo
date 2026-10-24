package app.cangoo.android.ui

import androidx.compose.foundation.ScrollState
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.selection.selectable
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import app.cangoo.android.R
import androidx.compose.ui.platform.LocalResources
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.PlatformTextStyle
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.unit.em

internal val BPaper: Color
    @Composable get() = LocalBThemeColors.current.paper
internal val BSurface: Color
    @Composable get() = LocalBThemeColors.current.surface
internal val BInk: Color
    @Composable get() = LocalBThemeColors.current.ink
internal val BMuted: Color
    @Composable get() = LocalBThemeColors.current.muted
internal val BLine: Color
    @Composable get() = LocalBThemeColors.current.line
internal val BSoft: Color
    @Composable get() = LocalBThemeColors.current.soft
internal val BAccent: Color
    @Composable get() = LocalBThemeColors.current.accentInk
internal val BRed: Color
    @Composable get() = LocalBThemeColors.current.error

internal data class HomeEntry(
    val id: String,
    val title: String,
    val subtitle: String,
    val isNote: Boolean,
    val favorite: Boolean,
) {
    override fun toString() = "HomeEntry(内容已隐藏)"
}

@Composable
internal fun BLookupToolbar(busy: Boolean, onSearch: () -> Unit, onAdd: () -> Unit, onLock: () -> Unit) {
    val texts = LocalResources.current
    val colors = LocalBThemeColors.current
    Row(
        Modifier.fillMaxWidth().height(64.dp).background(BPaper).padding(horizontal = 24.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        Row(
            Modifier.weight(1f).heightIn(min = 48.dp).clip(RoundedCornerShape(15.dp))
                .background(colors.searchBackground).alpha(if (busy) 0.45f else 1f)
                .clickable(enabled = !busy, role = Role.Button, onClick = onSearch)
                .semantics { contentDescription = texts.getString(R.string.search_password_notes) }.padding(horizontal = 16.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Icon(bIcon("search"), null, Modifier.size(23.dp), tint = BInk)
            BText(texts.getString(R.string.search_items), 16, modifier = Modifier.weight(1f), maxLines = 1)
        }
        BIconButton(bIcon("add"), texts.getString(R.string.add_item), !busy, colors.accentFill, colors.onAccent, onAdd)
        // 锁定始终可用，不能因普通业务操作正在执行而阻止撤权。
        BIconButton(bIcon("lock"), texts.getString(R.string.lock_vault), true, Color.Transparent, BInk, onLock)
    }
}

@Composable
internal fun BHomeContent(
    favorites: List<HomeEntry>,
    recent: List<HomeEntry>,
    warningCount: Int,
    checkedCount: Int,
    busy: Boolean,
    onRecord: (String, Boolean) -> Unit,
    onFavorites: () -> Unit,
    onLibrary: () -> Unit,
    onWarnings: () -> Unit,
    modifier: Modifier = Modifier,
    favoriteCount: Int = favorites.size,
    scrollState: ScrollState = rememberScrollState(),
    topContent: @Composable () -> Unit = {},
    contextPresent: Boolean = false,
    pendingCount: Int = 0,
) {
    val texts = LocalResources.current
    Column(modifier.fillMaxWidth().verticalScroll(scrollState).padding(start = 24.dp, end = 24.dp, top = 8.dp, bottom = 24.dp)) {
        topContent()
        Row(
            Modifier.fillMaxWidth().padding(top = if (contextPresent) 0.dp else 8.dp, bottom = 9.dp).heightIn(min = 32.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.SpaceBetween,
        ) {
            BSectionTitle(texts.getString(R.string.favorites))
            BTextButton(texts.getQuantityString(R.plurals.all_items_count, favoriteCount, favoriteCount), texts.getString(R.string.all_favorites), !busy, onFavorites, arrow = true)
        }
        Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
            favorites.take(4).chunked(2).forEach { pair ->
                Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                    pair.forEach { entry -> BFavoriteCard(entry, !busy, Modifier.weight(1f)) { onRecord(entry.id, entry.isNote) } }
                    if (pair.size == 1) Spacer(Modifier.weight(1f))
                }
            }
        }
        if (favorites.isEmpty()) {
            Column(
                Modifier.fillMaxWidth().padding(vertical = 35.dp, horizontal = 10.dp),
                horizontalAlignment = Alignment.CenterHorizontally,
            ) {
                Icon(bIcon("star"), null, Modifier.size(34.dp), tint = BMuted.copy(alpha = 0.6f))
                Spacer(Modifier.height(21.dp))
                BText(texts.getString(R.string.favorites_empty), 16, weight = FontWeight.Bold)
                Spacer(Modifier.height(8.dp))
                BText(texts.getString(R.string.favorites_hint), 13, color = BMuted, lineHeight = 23.4f)
                BTextButton(texts.getString(R.string.view_all_items), texts.getString(R.string.view_all_items), !busy, onLibrary)
            }
        }
        if (recent.isNotEmpty()) {
            Row(Modifier.fillMaxWidth().padding(top = 18.dp, bottom = 9.dp).heightIn(min = 32.dp), verticalAlignment = Alignment.CenterVertically) {
                BSectionTitle(texts.getString(R.string.recent))
            }
            Column(Modifier.fillMaxWidth().clip(RoundedCornerShape(17.dp)).background(BSurface).padding(horizontal = 14.dp)) {
                recent.take(3).forEachIndexed { index, entry ->
                    BRecentRow(entry, !busy) { onRecord(entry.id, entry.isNote) }
                    if (index < minOf(recent.size, 3) - 1) HorizontalDivider(color = BLine)
                }
            }
        }
        val hasWarnings = checkedCount > 0 && warningCount > 0
        val message = when {
            checkedCount < 0 -> texts.getString(R.string.checks_unavailable)
            checkedCount == 0 -> texts.getString(R.string.checks_empty)
            hasWarnings -> texts.getQuantityString(R.plurals.warning_count, warningCount, warningCount)
            pendingCount > 0 -> texts.getQuantityString(R.plurals.pending_count, pendingCount, pendingCount)
            else -> texts.getString(R.string.checks_clear)
        }
        Row(
            Modifier.fillMaxWidth().padding(top = 12.dp).clip(RoundedCornerShape(17.dp))
                .background(BSurface).alpha(if (busy) 0.45f else 1f)
                .clickable(enabled = !busy, role = Role.Button, onClick = onWarnings)
                .heightIn(min = 51.dp).padding(horizontal = 13.dp, vertical = 10.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(13.dp),
        ) {
            Icon(if (hasWarnings) bIcon("warning") else bIcon("info"), null, Modifier.size(22.dp), tint = if (hasWarnings) BRed else BMuted)
            BText(message, 13, weight = FontWeight.Bold, modifier = Modifier.weight(1f))
            Icon(bIcon("chevron_right"), null, Modifier.size(16.dp), tint = BMuted)
        }
    }
}

@Composable
internal fun BVaultContext(name: String, busy: Boolean, onChoose: () -> Unit) {
    val texts = LocalResources.current
    val iconTop = with(LocalDensity.current) { businessSp(16.sp).toDp() * 0.75f - 9.dp }
    Row(Modifier.fillMaxWidth().padding(bottom = 8.dp).heightIn(min = 48.dp),
        verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
        BText(texts.getString(R.string.current_vault), 13, modifier = Modifier.alignByBaseline(), color = BMuted, lineHeight = 19.5f)
        Row(Modifier.weight(1f).heightIn(min = 48.dp).clickable(enabled = !busy, role = Role.Button, onClick = onChoose)
            .semantics { contentDescription = texts.getString(R.string.current_vault_name, name) }.padding(vertical = 8.dp).alignByBaseline(),
            verticalAlignment = Alignment.Top, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            BText(name, 16, modifier = Modifier.weight(1f), color = BAccent, maxLines = 2)
            Icon(bIcon("chevron_down"), null, Modifier.padding(top = iconTop).size(18.dp), tint = BMuted)
        }
    }
}

@Composable
internal fun BBottomNavigation(selected: String, onSelect: (String) -> Unit) {
    val texts = LocalResources.current
    Column(Modifier.fillMaxWidth().background(BSurface)) {
        HorizontalDivider(color = BLine)
        Row(Modifier.fillMaxWidth().padding(start = 12.dp, end = 12.dp, top = 5.dp), horizontalArrangement = Arrangement.spacedBy(4.dp)) {
            listOf("home" to texts.getString(R.string.home), "library" to texts.getString(R.string.all), "tools" to texts.getString(R.string.tools), "settings" to texts.getString(R.string.settings)).forEach { (id, label) ->
                val active = id == selected
                val tint = if (active) BAccent else BMuted
                Column(
                    Modifier.weight(1f).heightIn(min = 65.dp).clip(RoundedCornerShape(14.dp))
                        .selectable(selected = active, role = Role.Tab, onClick = { onSelect(id) }),
                    verticalArrangement = Arrangement.spacedBy(5.dp, Alignment.CenterVertically),
                    horizontalAlignment = Alignment.CenterHorizontally,
                ) {
                    Icon(bIcon(id), null, Modifier.size(24.dp), tint = tint)
                    BText(label, 13, color = tint, weight = if (active) FontWeight.Bold else FontWeight.Normal)
                }
            }
        }
    }
}

@Composable
private fun BFavoriteCard(entry: HomeEntry, enabled: Boolean, modifier: Modifier, onClick: () -> Unit) {
    val texts = LocalResources.current
    Box(modifier.clip(RoundedCornerShape(20.dp)).background(BSurface).alpha(if (enabled) 1f else 0.45f).clickable(enabled = enabled, role = Role.Button, onClick = onClick)) {
        Column(Modifier.fillMaxWidth().heightIn(min = 118.dp).padding(start = 14.dp, end = 14.dp, top = 14.dp, bottom = 13.dp)) {
            BRecordMark(entry.isNote, size = 38)
            Spacer(Modifier.height(9.dp))
            BText(entry.title, 17, weight = FontWeight.Bold, maxLines = 1)
            Spacer(Modifier.height(2.dp))
            BText(if (entry.isNote) texts.getString(R.string.note_preview, entry.subtitle.ifEmpty { texts.getString(R.string.empty_note) }) else entry.subtitle.ifEmpty { texts.getString(R.string.account_empty) }, 13, color = BMuted, maxLines = 1)
        }
        if (entry.favorite) Icon(bIcon("star_filled"), null, Modifier.align(Alignment.TopEnd).padding(top = 18.dp, end = 13.dp).size(16.dp), tint = Color(0xffdcab4b))
    }
}

@Composable
private fun BRecentRow(entry: HomeEntry, enabled: Boolean, onClick: () -> Unit) {
    val texts = LocalResources.current
    Row(
        Modifier.fillMaxWidth().alpha(if (enabled) 1f else 0.45f).clickable(enabled = enabled, role = Role.Button, onClick = onClick)
            .heightIn(min = 61.dp).padding(vertical = 9.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        BRecordMark(entry.isNote, size = 38)
        Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
            BText(entry.title, 16, weight = FontWeight.Bold, maxLines = 1)
            BText(if (entry.isNote) entry.subtitle else entry.subtitle.ifEmpty { texts.getString(R.string.account_empty) }, 13, color = BMuted, maxLines = 1)
        }
        if (entry.favorite) Icon(bIcon("star_filled"), null, Modifier.size(13.dp), tint = Color(0xffbf9538))
        Icon(bIcon("chevron_right"), null, Modifier.size(16.dp), tint = BMuted)
    }
}

@Composable
private fun BSectionTitle(text: String) = BText(text, 20, weight = FontWeight.Bold, lineHeight = 28f, modifier = Modifier.semantics { heading() })

@Composable
private fun BTextButton(text: String, label: String, enabled: Boolean, onClick: () -> Unit, arrow: Boolean = false) {
    Row(
        Modifier.clip(RoundedCornerShape(8.dp)).alpha(if (enabled) 1f else 0.45f)
            .clickable(enabled = enabled, role = Role.Button, onClick = onClick)
            .semantics { contentDescription = label }.heightIn(min = 48.dp).padding(horizontal = 3.dp, vertical = 8.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(7.dp),
    ) {
        BText(text, 14, color = BAccent, weight = FontWeight.SemiBold)
        if (arrow) Icon(bIcon("chevron_right"), null, Modifier.size(17.dp), tint = BAccent)
    }
}

@Composable
private fun BIconButton(icon: ImageVector, label: String, enabled: Boolean, background: Color, tint: Color, onClick: () -> Unit) {
    Box(
        Modifier.size(48.dp).clip(RoundedCornerShape(15.dp)).background(background).alpha(if (enabled) 1f else 0.45f)
            .clickable(enabled = enabled, role = Role.Button, onClick = onClick),
        contentAlignment = Alignment.Center,
    ) { Icon(icon, label, Modifier.size(24.dp), tint = tint) }
}

@Composable
private fun BText(
    text: String,
    size: Int,
    modifier: Modifier = Modifier,
    color: Color = BInk,
    weight: FontWeight = FontWeight.Normal,
    lineHeight: Float = size * 1.5f,
    maxLines: Int = Int.MAX_VALUE,
) {
    Text(text, modifier, color = color, fontSize = businessSp(size.sp), fontWeight = weight, lineHeight = (lineHeight / size).em,
        maxLines = maxLines, overflow = TextOverflow.Ellipsis, style = TextStyle(platformStyle = PlatformTextStyle(includeFontPadding = false), lineHeightStyle = BLineHeightStyle))
}

@Composable
internal fun BRecordMark(note: Boolean, size: Int = 39) {
    Box(Modifier.size(size.dp).background(Color(0xffe2f1e7), RoundedCornerShape(if (size == 44) 15.dp else 13.dp)), contentAlignment = Alignment.Center) {
        Icon(bIcon(if (note) "note" else "lock"), null, Modifier.size(if (size == 39) 22.dp else 24.dp), tint = Color(0xff318257))
    }
}
