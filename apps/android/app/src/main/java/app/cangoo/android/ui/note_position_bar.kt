package app.cangoo.android.ui

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.MutatePriority
import androidx.compose.foundation.ScrollState
import androidx.compose.foundation.gestures.DragScope
import androidx.compose.foundation.gestures.DraggableState
import androidx.compose.foundation.gestures.Orientation
import androidx.compose.foundation.gestures.ScrollScope
import androidx.compose.foundation.gestures.draggable
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import app.cangoo.android.R
import androidx.compose.ui.platform.LocalResources
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.rememberUpdatedState
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.layout.onSizeChanged
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.semantics.CustomAccessibilityAction
import androidx.compose.ui.semantics.ProgressBarRangeInfo
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.customActions
import androidx.compose.ui.semantics.progressBarRangeInfo
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.setProgress
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.launch

internal data class NotePositionGeometry(val thumb: Float, val travel: Float, val top: Float)

internal fun notePositionGeometry(height: Int, minimum: Float, viewport: Int, maximum: Int, value: Int): NotePositionGeometry? {
    if (height <= minimum || viewport <= 0 || maximum <= 0 || maximum == Int.MAX_VALUE) return null
    val thumb = (height * (viewport.toDouble() / (viewport.toLong() + maximum))).toFloat().coerceIn(minimum, height.toFloat())
    val travel = height - thumb
    return NotePositionGeometry(thumb, travel, travel * (value.coerceIn(0, maximum).toFloat() / maximum))
}

private class NotePositionDrag(
    private val scroll: ScrollState,
    private val scale: () -> Float,
    private val interact: () -> Boolean,
) : DraggableState {
    private var active: ScrollScope? = null
    override suspend fun drag(dragPriority: MutatePriority, block: suspend DragScope.() -> Unit) {
        if (!interact()) throw CancellationException("记事已离开。")
        scroll.scroll(dragPriority) {
            active = this
            try { block(object : DragScope { override fun dragBy(pixels: Float) = dispatchRawDelta(pixels) }) }
            finally { active = null }
        }
    }
    // 只在同一ScrollState的互斥拖动内消费，不能绕过正在执行的滚动。
    override fun dispatchRawDelta(delta: Float) { active?.scrollBy(delta * scale()) }
}

@Composable
internal fun NotePositionBar(scroll: ScrollState, onInteraction: () -> Boolean, modifier: Modifier = Modifier) {
    val texts = LocalResources.current
    if (scroll.viewportSize <= 0 || scroll.maxValue <= 0 || scroll.maxValue == Int.MAX_VALUE) return
    val colors = LocalBThemeColors.current
    val scope = rememberCoroutineScope()
    val minimum = with(LocalDensity.current) { 32.dp.toPx() }
    var height by remember { mutableIntStateOf(0) }
    val geometry = notePositionGeometry(height, minimum, scroll.viewportSize, scroll.maxValue, scroll.value)
    val currentMinimum by rememberUpdatedState(minimum)
    val interaction by rememberUpdatedState(onInteraction)
    val drag = remember(scroll) { NotePositionDrag(scroll, {
        notePositionGeometry(height, currentMinimum, scroll.viewportSize, scroll.maxValue, scroll.value)
            ?.travel?.takeIf { it > 0f }?.let { scroll.maxValue / it } ?: 0f
    }, { interaction() }) }
    fun position(target: Float): Boolean {
        if (!target.isFinite() || !onInteraction()) return false
        scope.launch {
            scroll.scroll(MutatePriority.UserInput) { scrollBy(target.coerceIn(0f, scroll.maxValue.toFloat()) - scroll.value) }
        }
        return true
    }
    Canvas(modifier.width(24.dp).fillMaxHeight().padding(vertical = 8.dp).onSizeChanged { height = it.height }
        .then(if (geometry == null || geometry.travel <= 0f) Modifier else Modifier
            .draggable(drag, Orientation.Vertical, startDragImmediately = scroll.isScrollInProgress)
            .semantics {
                contentDescription = texts.getString(R.string.note_position)
                progressBarRangeInfo = ProgressBarRangeInfo(scroll.value.toFloat(), 0f..scroll.maxValue.toFloat())
                setProgress { position(it) }
                customActions = listOf(
                    CustomAccessibilityAction(texts.getString(R.string.page_up)) { position(scroll.value.toFloat() - scroll.viewportSize) },
                    CustomAccessibilityAction(texts.getString(R.string.page_down)) { position(scroll.value.toFloat() + scroll.viewportSize) },
                )
            })) {
        val actual = notePositionGeometry(size.height.toInt(), minimum, scroll.viewportSize, scroll.maxValue, scroll.value)
        if (actual != null && actual.travel > 0f) {
            val track = 2.dp.toPx()
            val thumb = 4.dp.toPx()
            drawRoundRect(colors.line, Offset((size.width - track) / 2, 0f), Size(track, size.height), CornerRadius(track / 2))
            drawRoundRect(colors.muted, Offset((size.width - thumb) / 2, actual.top), Size(thumb, actual.thumb), CornerRadius(thumb / 2))
        }
    }
}
