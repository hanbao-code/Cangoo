package app.cangoo.android.ui

import androidx.compose.foundation.text.contextmenu.builder.item
import androidx.compose.foundation.text.contextmenu.data.TextContextMenuKeys
import androidx.compose.foundation.text.contextmenu.modifier.appendTextContextMenuComponents
import androidx.compose.foundation.text.contextmenu.modifier.filterTextContextMenuComponents
import androidx.compose.foundation.text.contextmenu.provider.TextContextMenuProvider
import androidx.compose.foundation.text.contextmenu.provider.TextContextMenuDataProvider
import androidx.compose.foundation.text.contextmenu.provider.LocalTextContextMenuToolbarProvider
import app.cangoo.android.R
import androidx.compose.ui.platform.LocalResources
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.TextRange
import androidx.compose.ui.text.input.TextFieldValue
import kotlinx.coroutines.CancellationException

private data object CancelSelectionKey

internal fun isBasicEditMenuKey(key: Any): Boolean =
    key === TextContextMenuKeys.CutKey || key === TextContextMenuKeys.CopyKey ||
        key === TextContextMenuKeys.PasteKey || key === TextContextMenuKeys.SelectAllKey ||
        key === CancelSelectionKey

internal fun TextFieldValue.cancelSelection(): TextFieldValue =
    copy(selection = TextRange(selection.max))

// 右键沿框架已有原生浮动菜单，避免另一个取焦弹层阻断复制资格。
internal class NativeTextMenuRelay : TextContextMenuProvider {
    var toolbar: TextContextMenuProvider? = null
    override suspend fun showTextContextMenu(dataProvider: TextContextMenuDataProvider) {
        val target = toolbar ?: throw CancellationException("文字菜单尚未就绪。")
        target.showTextContextMenu(dataProvider)
    }
}

@Composable
internal fun BindNativeTextMenu(relay: NativeTextMenuRelay) {
    val toolbar = LocalTextContextMenuToolbarProvider.current
    DisposableEffect(relay, toolbar) {
        relay.toolbar = toolbar
        onDispose { if (relay.toolbar === toolbar) relay.toolbar = null }
    }
}

// 基本操作的可用性由文本框判断；只保留必要菜单项。
@Composable
internal fun Modifier.basicEditMenu(value: TextFieldValue, onSelectionChange: (TextFieldValue) -> Unit): Modifier {
    val texts = LocalResources.current
    return appendTextContextMenuComponents {
        if (!value.selection.collapsed) {
            item(CancelSelectionKey, texts.getString(R.string.cancel_selection)) {
                onSelectionChange(value.cancelSelection())
                close()
            }
        }
    }.filterTextContextMenuComponents { isBasicEditMenuKey(it.key) }
}
