package app.cangoo.android.ui

import androidx.compose.animation.core.animateDpAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.ScrollState
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.interaction.collectIsFocusedAsState
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.IntrinsicSize
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.ime
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.selection.toggleable
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.foundation.text.contextmenu.provider.LocalTextContextMenuDropdownProvider
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.LocalContentColor
import androidx.compose.material3.Slider
import androidx.compose.material3.Text
import app.cangoo.android.R
import androidx.compose.ui.platform.LocalResources
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.SideEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.platform.LocalFocusManager
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.PlatformTextStyle
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.TextFieldValue
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.IntOffset
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.unit.em
import java.security.SecureRandom
import kotlin.math.roundToInt

data class GeneratorOptions(
    val length: String = "20",
    val upper: Boolean = true,
    val lower: Boolean = true,
    val digits: Boolean = true,
    val symbols: Boolean = true,
    val excludeAmbiguous: Boolean = false,
)

private val passwordRandom = SecureRandom()

private fun generatorLength(value: String): Int? = try {
    value.trim().toBigDecimalOrNull()?.intValueExact()
} catch (_: ArithmeticException) { null }

internal class GeneratorValidationException(val reason: UiText) : IllegalArgumentException()

internal fun validatedGeneratorOptions(options: GeneratorOptions): GeneratorOptions {
    val length = generatorLength(options.length)
    if (length == null || length !in 1..1024) throw GeneratorValidationException(UiText(R.string.generator_length_invalid))
    val count = listOf(options.upper, options.lower, options.digits, options.symbols).count { it }
    if (count == 0) throw GeneratorValidationException(UiText(R.string.generator_classes_required))
    if (length < count) throw GeneratorValidationException(UiText(R.string.generator_length_classes))
    return options.copy(length = length.toString())
}

internal fun generatePassword(options: GeneratorOptions): String {
    val length = validatedGeneratorOptions(options).length.toInt()
    val groups = listOf(
        options.upper to "ABCDEFGHIJKLMNOPQRSTUVWXYZ",
        options.lower to "abcdefghijklmnopqrstuvwxyz",
        options.digits to "0123456789",
        options.symbols to "!@#$%^&*()-_=+[]{};:,.?",
    ).filter { it.first }.map { (_, characters) ->
        if (options.excludeAmbiguous) characters.filterNot { it in "Il1O0o" } else characters
    }
    val pool = groups.joinToString("")
    val output = CharArray(length) { index ->
        val characters = groups.getOrNull(index) ?: pool
        characters[passwordRandom.nextInt(characters.length)]
    }
    for (index in output.lastIndex downTo 1) {
        val other = passwordRandom.nextInt(index + 1)
        val value = output[index]
        output[index] = output[other]
        output[other] = value
    }
    return output.concatToString().also { output.fill('\u0000') }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
internal fun BGeneratorPage(
    options: GeneratorOptions,
    result: String,
    busy: Boolean,
    onOptions: (GeneratorOptions) -> Unit,
    onGenerate: () -> Unit,
    onUse: (String) -> Unit,
    error: String = "",
    expanded: Boolean,
    onExpanded: (Boolean) -> Unit,
    scrollState: ScrollState,
    fontScale: Float = 1f,
    onCopy: () -> Unit,
) {
    val texts = LocalResources.current
    val focus = LocalFocusManager.current
    val colors = LocalBThemeColors.current
    val keyboardVisible = WindowInsets.ime.getBottom(LocalDensity.current) > 0
    val previewLimit = if (fontScale == 1.5f) 28 else 64
    Column(Modifier.fillMaxSize().background(BPaper)) {
        Column(
            Modifier.weight(1f).fillMaxWidth().verticalScroll(scrollState)
                .padding(start = 24.dp, end = 24.dp, top = 8.dp, bottom = 24.dp),
        ) {
            Column(Modifier.fillMaxWidth().padding(bottom = 20.dp).background(BSurface, RoundedCornerShape(17.dp)).padding(horizontal = 18.dp, vertical = 16.dp)) {
                Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    GeneratorText(
                        if (result.isEmpty()) texts.getString(R.string.waiting_generate) else texts.getQuantityString(R.plurals.generated_count, result.length, result.length).let { if (result.length > previewLimit && !expanded) texts.getString(R.string.result_preview, it) else it },
                        13, modifier = Modifier.weight(1f), color = BMuted, lineHeight = 24f / 13,
                    )
                    if (result.length > previewLimit) {
                        Box(
                            Modifier.widthIn(min = 48.dp).heightIn(min = 48.dp).semantics { contentDescription = if (expanded) texts.getString(R.string.collapse_full) else texts.getString(R.string.expand_full) }
                                .clickable(enabled = !busy, role = Role.Button) {
                                    focus.clearFocus()
                                    onExpanded(!expanded)
                                }.padding(vertical = 12.dp),
                            contentAlignment = Alignment.Center,
                        ) { GeneratorText(if (expanded) texts.getString(R.string.collapse) else texts.getString(R.string.expand), 16, color = BAccent) }
                    }
                }
                if (!keyboardVisible && result.isNotEmpty()) {
                    Spacer(Modifier.height(12.dp))
                    GeneratedText(if (expanded || result.length <= previewLimit) result else "${result.take(previewLimit)}…")
                }
            }
            BGeneratorParameters(options, !busy, onOptions)
        }
        HorizontalDivider(color = BLine)
        Column(Modifier.fillMaxWidth().padding(horizontal = 24.dp, vertical = 10.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            if (error.isNotEmpty()) {
                Box(Modifier.fillMaxWidth().background(BSurface).drawBehind {
                    val x = 1.5.dp.toPx()
                    drawLine(colors.error, Offset(x, 0f), Offset(x, size.height), strokeWidth = 3.dp.toPx())
                }.semantics { liveRegion = LiveRegionMode.Assertive }) {
                    GeneratorText(error, 13, color = BRed, modifier = Modifier.padding(horizontal = 12.dp, vertical = 8.dp))
                }
            }
            Row(Modifier.height(IntrinsicSize.Min), horizontalArrangement = Arrangement.spacedBy(if (fontScale == 1.5f) 8.dp else 10.dp)) {
                GeneratorButton(if (result.isEmpty()) texts.getString(R.string.generate) else texts.getString(R.string.regenerate), !busy, result.isEmpty(), Modifier.weight(1f)) {
                    focus.clearFocus()
                    onGenerate()
                }
                GeneratorButton(texts.getString(R.string.copy), !busy && result.isNotEmpty(), result.isNotEmpty(),
                    if (fontScale == 1.5f) Modifier.width(IntrinsicSize.Max) else Modifier.weight(0.75f), onCopy)
                GeneratorButton(texts.getString(R.string.use_new_record), !busy && result.isNotEmpty(), false, Modifier.weight(1.25f)) {
                    focus.clearFocus()
                    onUse(result)
                }
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
internal fun BGeneratorParameters(options: GeneratorOptions, enabled: Boolean, onOptions: (GeneratorOptions) -> Unit) {
    val texts = LocalResources.current
    val focus = LocalFocusManager.current
    val colors = LocalBThemeColors.current
    fun change(next: GeneratorOptions) { focus.clearFocus(); onOptions(next) }
    Column {
        Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.SpaceBetween) {
            Text(fieldLabel(texts.getString(R.string.password_length), true), color = BInk, fontSize = businessSp(14.sp),
                fontWeight = FontWeight.Medium, lineHeight = 1.5.em,
                modifier = Modifier.semantics { contentDescription = texts.getString(R.string.password_length_required) })
            GeneratorLengthField(options.length, enabled) { onOptions(options.copy(length = it)) }
        }
        Spacer(Modifier.height(8.dp))
        Slider(
            value = (generatorLength(options.length) ?: 1).coerceIn(1, 128).toFloat(),
            onValueChange = { change(options.copy(length = it.roundToInt().toString())) },
            enabled = enabled, steps = 126, valueRange = 1f..128f,
            modifier = Modifier.fillMaxWidth().height(44.dp).semantics { contentDescription = texts.getString(R.string.length_slider) },
            thumb = { Box(Modifier.size(16.dp).background(if (!enabled) colors.muted else colors.controlOn, CircleShape)) },
            track = { slider ->
                Canvas(Modifier.fillMaxWidth().height(4.dp)) {
                    val ratio = (slider.value - 1f) / 127f
                    val start = Offset(2.dp.toPx(), size.height / 2)
                    val end = Offset(size.width - 2.dp.toPx(), start.y)
                    drawLine(colors.line, start, end, strokeWidth = size.height, cap = StrokeCap.Round)
                    drawLine(if (!enabled) colors.muted else colors.controlOn, start, Offset(start.x + (end.x - start.x) * ratio, start.y), strokeWidth = size.height, cap = StrokeCap.Round)
                }
            },
        )
        Row(Modifier.fillMaxWidth().padding(bottom = 20.dp), horizontalArrangement = Arrangement.SpaceBetween) {
            GeneratorText("1", 13, color = BMuted)
            GeneratorText("128", 13, color = BMuted)
        }
        Column(Modifier.fillMaxWidth().clip(RoundedCornerShape(17.dp)).background(BSurface).padding(horizontal = 14.dp)) {
            GeneratorToggle(texts.getString(R.string.uppercase), options.upper, enabled, divider = true) { change(options.copy(upper = it)) }
            GeneratorToggle(texts.getString(R.string.lowercase), options.lower, enabled, divider = true) { change(options.copy(lower = it)) }
            GeneratorToggle(texts.getString(R.string.digits), options.digits, enabled, divider = true) { change(options.copy(digits = it)) }
            GeneratorToggle(texts.getString(R.string.symbols), options.symbols, enabled, divider = true) { change(options.copy(symbols = it)) }
            GeneratorToggle(texts.getString(R.string.exclude_ambiguous), options.excludeAmbiguous, enabled, note = texts.getString(R.string.ambiguous_examples)) { change(options.copy(excludeAmbiguous = it)) }
        }
    }
}

@Composable
private fun GeneratorLengthField(value: String, enabled: Boolean, onChange: (String) -> Unit) {
    val texts = LocalResources.current
    val focus = LocalFocusManager.current
    val textSize = businessSp(17.sp)
    val fieldWidth = with(LocalDensity.current) { (textSize.toDp() * 4).coerceAtLeast(76.dp) }
    val interaction = remember { MutableInteractionSource() }
    val focused by interaction.collectIsFocusedAsState()
    val nativeMenu = remember { NativeTextMenuRelay() }
    var editingValue by remember { mutableStateOf(TextFieldValue(value)) }
    val fieldValue = editingValue.copy(text = value)
    var lastText by remember(value) { mutableStateOf(value) }
    SideEffect { editingValue = fieldValue }
    CompositionLocalProvider(LocalTextContextMenuDropdownProvider provides nativeMenu) {
    BasicTextField(
        value = fieldValue,
        onValueChange = { next ->
            editingValue = next
            if (next.text != lastText) {
                lastText = next.text
                onChange(next.text)
            }
        },
        enabled = enabled, singleLine = true,
        modifier = Modifier.width(fieldWidth).heightIn(min = 44.dp).background(BSurface, RoundedCornerShape(9.dp))
            .border(1.dp, if (focused) BAccent else BLine, RoundedCornerShape(9.dp)).padding(8.dp)
            .semantics { contentDescription = texts.getString(R.string.password_length_required) }.basicEditMenu(fieldValue) { editingValue = it; focus.clearFocus() },
        textStyle = TextStyle(color = BInk, fontSize = textSize, lineHeight = 1.5.em, textAlign = TextAlign.Center,
            lineHeightStyle = BLineHeightStyle,
            platformStyle = PlatformTextStyle(includeFontPadding = false)),
        cursorBrush = SolidColor(BAccent),
        interactionSource = interaction,
        keyboardOptions = KeyboardOptions(autoCorrectEnabled = false, keyboardType = KeyboardType.Number, imeAction = ImeAction.Done),
        keyboardActions = KeyboardActions(onDone = { focus.clearFocus() }),
        decorationBox = { input -> BindNativeTextMenu(nativeMenu); input() },
    )
    }
}

@Composable
internal fun GeneratorToggle(label: String, checked: Boolean, enabled: Boolean, divider: Boolean = false, note: String = "", onChange: (Boolean) -> Unit) {
    val colors = LocalBThemeColors.current
    val position by animateDpAsState(if (checked) 17.dp else 0.dp, tween(150), label = "字符开关")
    Row(
        Modifier.fillMaxWidth().heightIn(min = 65.dp).alpha(if (enabled) 1f else 0.45f)
            .drawBehind { if (divider) drawLine(colors.line, Offset(0f, size.height - 0.5.dp.toPx()), Offset(size.width, size.height - 0.5.dp.toPx()), strokeWidth = 1.dp.toPx()) }
            .toggleable(value = checked, enabled = enabled, role = Role.Switch, onValueChange = onChange).padding(vertical = 14.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(4.dp)) {
            GeneratorText(label, 14, weight = FontWeight.Medium)
            if (note.isNotEmpty()) GeneratorText(note, 13, color = BMuted)
        }
        Box(Modifier.size(42.dp, 25.dp).background(if (checked) colors.controlOn else colors.controlOff, RoundedCornerShape(16.dp)).padding(3.dp)) {
            Box(Modifier.offset { IntOffset(position.roundToPx(), 0) }.size(19.dp).background(if (checked) colors.onAccent else Color.White, CircleShape))
        }
    }
}

@Composable
private fun GeneratedText(value: String) {
    Text(value, color = BInk, fontSize = businessSp(22.sp), lineHeight = 1.7.em, fontFamily = FontFamily.Monospace, letterSpacing = 0.5.sp,
        style = TextStyle(lineHeightStyle = BLineHeightStyle,
            platformStyle = PlatformTextStyle(includeFontPadding = false)))
}

@Composable
private fun GeneratorText(text: String, size: Int, modifier: Modifier = Modifier, color: Color = BInk, weight: FontWeight = FontWeight.Normal,
                          lineHeight: Float = 1.5f, textAlign: TextAlign = TextAlign.Start) {
    Text(text, modifier, color = color, fontSize = businessSp(size.sp), lineHeight = lineHeight.em, fontWeight = weight, textAlign = textAlign,
        style = TextStyle(platformStyle = PlatformTextStyle(includeFontPadding = false), lineHeightStyle = BLineHeightStyle))
}

@Composable
private fun GeneratorButton(label: String, enabled: Boolean, primary: Boolean, modifier: Modifier, onClick: () -> Unit) {
    val colors = LocalBThemeColors.current
    val container = if (primary) colors.accentFill else colors.soft
    val content = if (primary) colors.onAccent else colors.ink
    Button(onClick = onClick, enabled = enabled, modifier = modifier.fillMaxHeight().heightIn(min = 50.dp),
        shape = RoundedCornerShape(if (primary) 14.dp else 11.dp),
        contentPadding = PaddingValues(horizontal = 10.dp, vertical = 12.dp),
        colors = ButtonDefaults.buttonColors(containerColor = container, contentColor = content,
            disabledContainerColor = container, disabledContentColor = content.copy(alpha = 0.45f))) {
        GeneratorText(label, 16, color = LocalContentColor.current, weight = if (primary) FontWeight.SemiBold else FontWeight.Normal, textAlign = TextAlign.Center)
    }
}
