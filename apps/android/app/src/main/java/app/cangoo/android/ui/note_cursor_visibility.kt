package app.cangoo.android.ui

import androidx.compose.ui.Modifier
import androidx.compose.foundation.gestures.BringIntoViewSpec
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Rect
import androidx.compose.ui.layout.LayoutCoordinates
import androidx.compose.ui.node.ModifierNodeElement
import androidx.compose.ui.node.LayoutAwareModifierNode
import androidx.compose.ui.node.requireLayoutCoordinates
import androidx.compose.ui.platform.InspectorInfo
import androidx.compose.ui.relocation.BringIntoViewModifierNode
import androidx.compose.ui.relocation.bringIntoView
import androidx.compose.ui.text.TextLayoutResult
import androidx.compose.ui.text.input.TextFieldValue
import kotlinx.coroutines.Job
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.job
import kotlin.math.roundToInt

internal class NoteCursorVisibility {
    var value: () -> TextFieldValue? = { null }
    var layout: TextLayoutResult? = null
    var textCoordinates: LayoutCoordinates? = null
    var focusCoordinates: LayoutCoordinates? = null
    var viewportCoordinates: LayoutCoordinates? = null
    private var focused = false
    private var revealText: String? = null
    private val requests = mutableSetOf<Job>()

    fun focusChanged(value: Boolean) {
        focused = value
        if (!value) { revealText = null; cancelRequests() }
    }

    fun cancelRequests() { requests.toList().forEach { it.cancel() } }

    fun contentChanged(text: String) {
        cancelRequests()
        revealText = text.takeIf { focused }
    }

    fun consumeInputReveal(): Boolean {
        val expected = revealText ?: return false
        if (value()?.text != expected) { revealText = null; return false }
        if (cursor() == null) return false
        revealText = null
        return true
    }

    fun cursor(): Pair<LayoutCoordinates, Rect>? {
        val current = value() ?: return null
        val measured = layout ?: return null
        val coordinates = textCoordinates?.takeIf { it.isAttached } ?: return null
        if (!focused || measured.layoutInput.text.text != current.text) return null
        return coordinates to measured.getCursorRect(current.selection.max)
    }

    fun clear() {
        focusChanged(false)
        value = { null }
        layout = null
        textCoordinates = null
        focusCoordinates = null
        viewportCoordinates = null
    }

    fun resizeSpec(original: BringIntoViewSpec): BringIntoViewSpec = object : BringIntoViewSpec {
        override fun calculateScrollDistance(offset: Float, size: Float, containerSize: Float): Float {
            val focus = focusCoordinates?.takeIf { it.isAttached }
            val viewport = viewportCoordinates?.takeIf { it.isAttached }
            val caret = cursor()
            if (focus != null && viewport != null && caret != null && size.roundToInt() == focus.size.height &&
                offset.roundToInt() == viewport.localPositionOf(focus, Offset.Zero).y.roundToInt()) {
                val top = viewport.localPositionOf(caret.first, caret.second.topLeft).y
                return original.calculateScrollDistance(top, caret.second.height, containerSize)
            }
            return original.calculateScrollDistance(offset, size, containerSize)
        }
    }

    suspend fun track(block: suspend () -> Unit) = coroutineScope {
        val request = coroutineContext.job
        requests += request
        try { block() } finally { requests -= request }
    }
}

internal data class NoteCursorVisibilityElement(val state: NoteCursorVisibility) : ModifierNodeElement<NoteCursorVisibilityNode>() {
    override fun create() = NoteCursorVisibilityNode(state)
    override fun update(node: NoteCursorVisibilityNode) {
        if (node.state !== state) node.state.cancelRequests()
        node.state = state
    }
    override fun InspectorInfo.inspectableProperties() { name = "noteCursorVisibility" }
}

internal class NoteCursorVisibilityNode(var state: NoteCursorVisibility) : Modifier.Node(), BringIntoViewModifierNode, LayoutAwareModifierNode {
    override fun onPlaced(coordinates: LayoutCoordinates) { state.focusCoordinates = coordinates }
    override fun onDetach() { state.cancelRequests() }

    override suspend fun bringIntoView(childCoordinates: LayoutCoordinates, boundsProvider: () -> Rect?) {
        if (!isAttached || !childCoordinates.isAttached) return
        val mapped = state.cursor() != null
        suspend fun forward() {
            bringIntoView {
                if (!isAttached || !childCoordinates.isAttached) return@bringIntoView null
                val target = requireLayoutCoordinates()
                val cursor = if (mapped) state.cursor() ?: return@bringIntoView null else null
                val source = cursor?.first ?: childCoordinates
                val rect = cursor?.second ?: boundsProvider() ?: return@bringIntoView null
                // 每次父层计算都读实时选区，避免焦点时捕获的旧光标把正文拉回起点。
                Rect(target.localPositionOf(source, rect.topLeft), target.localPositionOf(source, rect.bottomRight))
            }
        }
        if (mapped) state.track { forward() } else forward()
    }
}
