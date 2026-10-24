package app.cangoo.android.ui

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.IntrinsicSize
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.selection.selectable
import androidx.compose.foundation.selection.selectableGroup
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.ColorScheme
import androidx.compose.material3.Icon
import androidx.compose.material3.LocalContentColor
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.Typography
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import app.cangoo.android.R
import androidx.compose.ui.res.stringResource
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.staticCompositionLocalOf
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.PlatformTextStyle
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.LineHeightStyle
import androidx.compose.ui.unit.TextUnit
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.unit.em

internal val BFontOptions = listOf(1f to "标准", 1.25f to "125%", 1.5f to "150%")
internal val BPaletteOptions = listOf("green" to "绿色", "beige" to "米色", "blue" to "蓝色", "yellow" to "黄色")
internal val BThemeOptions = listOf("light" to "浅色", "dark" to "深色", "auto" to "跟随系统")

internal data class BThemeColors(
    val paper: Color,
    val surface: Color,
    val ink: Color,
    val muted: Color,
    val line: Color,
    val soft: Color,
    val accentInk: Color,
    val accentFill: Color,
    val onAccent: Color,
    val error: Color,
    val onAccentMuted: Color = onAccent,
    val searchBackground: Color = soft,
    val searchInk: Color = muted,
    val controlOn: Color = accentFill,
    val controlOff: Color = line,
    val progressTrack: Color = line,
    val progressFill: Color = accentInk,
    val strengthMeter: Color = accentInk,
    val cardShadow: Color = Color(0x03000000),
    val selectionShadow: Color = Color(0x10000000),
    val warningSurface: Color = Color(0xfff4e9d4),
    val warningInk: Color = Color(0xffa27028),
)

internal fun UiPreferences.isDark(systemDark: Boolean): Boolean = theme == "dark" || (theme == "auto" && systemDark)

internal fun bThemeColors(prefs: UiPreferences, systemDark: Boolean): BThemeColors {
    val dark = prefs.isDark(systemDark)
    val error = Color(if (dark) 0xffffb09c else 0xffa74735)
    val colors = when (prefs.palette) {
        "green" -> if (dark) BThemeColors(
            paper = Color(0xff1d2c26), surface = Color(0xff283a31), ink = Color(0xffecf1e7), muted = Color(0xffb4c0b8),
            line = Color(0xff435247), soft = Color(0xff35473c), accentInk = Color(0xff8bbfa0), accentFill = Color(0xff285947),
            onAccent = Color.White, error = error,
        ) else BThemeColors(
            paper = Color(0xfff8f6ef), surface = Color(0xfffffefa), ink = Color(0xff183e33), muted = Color(0xff5f6e64),
            line = Color(0xffe6e8df), soft = Color(0xffecf0e8), accentInk = Color(0xff285947), accentFill = Color(0xff285947),
            onAccent = Color.White, error = error, searchBackground = Color(0xffeceee7), searchInk = Color(0xff738076),
        )
        "beige" -> if (dark) BThemeColors(
            paper = Color(0xff22211d), surface = Color(0xff302e28), ink = Color(0xfff4eee1), muted = Color(0xffb9b2a3),
            line = Color(0xff464238), soft = Color(0xff3a3730), accentInk = Color(0xffefad8f), accentFill = Color(0xffefad8f),
            onAccent = Color(0xff3b241a), error = error,
        ) else BThemeColors(
            paper = Color(0xfffcf9f2), surface = Color(0xfffffdf8), ink = Color(0xff292822), muted = Color(0xff6a665d),
            line = Color(0xffded9cd), soft = Color(0xfff0ebe2), accentInk = Color(0xffa44834), accentFill = Color(0xffa44834),
            onAccent = Color.White, error = error,
        )
        "blue" -> if (dark) BThemeColors(
            paper = Color(0xff0a1525), surface = Color(0xff152b46), ink = Color(0xffecf3ff), muted = Color(0xffa3b6d1),
            line = Color(0xff26394f), soft = Color(0xff1e3654), accentInk = Color(0xff81bbff), accentFill = Color(0xff81bbff),
            onAccent = Color(0xff092441), error = error,
        ) else BThemeColors(
            paper = Color(0xfff1f6ff), surface = Color(0xfffcfdff), ink = Color(0xff102640), muted = Color(0xff566980),
            line = Color(0xffd1deed), soft = Color(0xffe2ebf9), accentInk = Color(0xff245da8), accentFill = Color(0xff245da8),
            onAccent = Color.White, error = error,
        )
        "yellow" -> if (dark) BThemeColors(
            paper = Color(0xff1c1c1a), surface = Color(0xff2b2b27), ink = Color(0xfff3f0e7), muted = Color(0xffb7b4a9),
            line = Color(0xff42423a), soft = Color(0xff35352f), accentInk = Color(0xffe7bb69), accentFill = Color(0xffe7bb69),
            onAccent = Color(0xff2b2110), error = error,
        ) else BThemeColors(
            paper = Color(0xfffaf9f6), surface = Color(0xfffffefb), ink = Color(0xff242321), muted = Color(0xff66645e),
            line = Color(0xffdedbd5), soft = Color(0xfff0eeea), accentInk = Color(0xff8b6118), accentFill = Color(0xffdfa43b),
            onAccent = Color(0xff211b10), error = error,
        )
        else -> throw IllegalArgumentException("配色参数无效。")
    }
    return if (prefs.palette == "green") colors.copy(
        onAccentMuted = Color(0xffd0e3d5), controlOn = Color(0xff4d8064), controlOff = Color(0xffc7cec6),
        progressTrack = Color(0xffd4dfcd), progressFill = Color(0xff6c9373),
        cardShadow = Color(0x03193628), selectionShadow = Color(0x10152f28),
    ) else colors.copy(strengthMeter = Color(if (dark) 0xff8bbfa0 else 0xff285947))
}

internal fun bMaterialScheme(colors: BThemeColors, dark: Boolean): ColorScheme =
    (if (dark) darkColorScheme() else lightColorScheme()).copy(
        primary = colors.accentInk, onPrimary = if (dark) colors.paper else Color.White, primaryContainer = colors.soft, onPrimaryContainer = colors.accentInk,
        secondary = colors.accentFill, onSecondary = colors.onAccent, secondaryContainer = colors.soft, onSecondaryContainer = colors.ink,
        tertiary = colors.accentFill, onTertiary = colors.onAccent, tertiaryContainer = colors.soft, onTertiaryContainer = colors.ink,
        background = colors.paper, onBackground = colors.ink, surface = colors.surface, onSurface = colors.ink,
        surfaceVariant = colors.soft, onSurfaceVariant = colors.muted, outline = colors.line, outlineVariant = colors.line,
        error = colors.error, onError = colors.surface, errorContainer = colors.surface, onErrorContainer = colors.error,
        surfaceTint = colors.accentInk, inverseSurface = colors.ink, inverseOnSurface = colors.paper, inversePrimary = colors.paper,
        surfaceDim = colors.paper, surfaceBright = colors.surface, surfaceContainerLowest = colors.surface,
        surfaceContainerLow = colors.surface, surfaceContainer = colors.surface, surfaceContainerHigh = colors.surface, surfaceContainerHighest = colors.surface,
    )

internal val LocalBThemeColors = staticCompositionLocalOf { bThemeColors(UiPreferences(), false) }

private val LocalBusinessFontScale = staticCompositionLocalOf { 1f }
private val BaseTypography = Typography()
internal val BLineHeightStyle = LineHeightStyle(LineHeightStyle.Alignment.Proportional, LineHeightStyle.Trim.None)

// 原生测量会重建Density；将期望尺寸转回系统sp后交实际文字样式。
@Composable
internal fun businessSp(size: TextUnit): TextUnit {
    val multiplier = LocalBusinessFontScale.current
    return if (multiplier == 1f) size else with(LocalDensity.current) { (size.toDp() * multiplier).toSp() }
}

@Composable
private fun businessStyle(style: TextStyle): TextStyle = style.copy(
    fontSize = businessSp(style.fontSize),
    lineHeight = (style.lineHeight.value / style.fontSize.value).em,
)

@Composable
internal fun CangooTheme(prefs: UiPreferences, content: @Composable () -> Unit) {
    val systemDark = isSystemInDarkTheme()
    val colors = bThemeColors(prefs, systemDark)
    CompositionLocalProvider(
        LocalBThemeColors provides colors,
        LocalContentColor provides colors.ink,
        LocalBusinessFontScale provides prefs.fontScale,
    ) {
        val typography = Typography(
            displayLarge = businessStyle(BaseTypography.displayLarge),
            displayMedium = businessStyle(BaseTypography.displayMedium),
            displaySmall = businessStyle(BaseTypography.displaySmall),
            headlineLarge = businessStyle(BaseTypography.headlineLarge),
            headlineMedium = businessStyle(BaseTypography.headlineMedium),
            headlineSmall = businessStyle(BaseTypography.headlineSmall),
            titleLarge = businessStyle(BaseTypography.titleLarge),
            titleMedium = businessStyle(BaseTypography.titleMedium),
            titleSmall = businessStyle(BaseTypography.titleSmall),
            bodyLarge = businessStyle(BaseTypography.bodyLarge),
            bodyMedium = businessStyle(BaseTypography.bodyMedium),
            bodySmall = businessStyle(BaseTypography.bodySmall),
            labelLarge = businessStyle(BaseTypography.labelLarge),
            labelMedium = businessStyle(BaseTypography.labelMedium),
            labelSmall = businessStyle(BaseTypography.labelSmall),
        )
        MaterialTheme(colorScheme = bMaterialScheme(colors, prefs.isDark(systemDark)), typography = typography, content = content)
    }
}

@Composable
internal fun paletteLabel(id: String): String = stringResource(when (id) {
    "beige" -> R.string.beige
    "blue" -> R.string.blue
    "yellow" -> R.string.yellow
    else -> R.string.green
})

@Composable
internal fun themeLabel(id: String): String = stringResource(when (id) {
    "dark" -> R.string.dark
    "auto" -> R.string.auto_theme
    else -> R.string.light
})

// 仅呈现正文，由父层保留固定标题并管理内容滚动。
@Composable
internal fun BAppearancePage(prefs: UiPreferences, saving: Boolean, error: String, onChange: (UiPreferences) -> Unit) {
    val colors = LocalBThemeColors.current
    val systemDark = isSystemInDarkTheme()
    Column(Modifier.fillMaxWidth()) {
        AppearanceHeading(stringResource(R.string.appearance_mode), Modifier.padding(top = 14.dp))
        Row(Modifier.fillMaxWidth().padding(top = 14.dp).clip(RoundedCornerShape(12.dp)).background(colors.soft).padding(4.dp).height(IntrinsicSize.Min).selectableGroup()) {
            BThemeOptions.forEach { (id, _) ->
                val label = themeLabel(id)
                val selected = prefs.theme == id
                Column(
                    Modifier.weight(1f).fillMaxHeight().clip(RoundedCornerShape(9.dp)).background(if (selected) colors.surface else Color.Transparent)
                        .alpha(if (saving) 0.45f else 1f).selectable(selected, enabled = !saving, role = Role.RadioButton) { if (!selected) onChange(prefs.copy(theme = id)) }
                        .heightIn(min = 48.dp).padding(horizontal = 4.dp, vertical = 8.dp),
                    horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.Center,
                ) { AppearanceText(label, 16, if (selected) colors.ink else colors.muted, weight = if (selected) FontWeight.SemiBold else FontWeight.Normal) }
            }
        }
        if (prefs.theme == "auto") AppearanceText(stringResource(R.string.following_system, themeLabel(if (prefs.isDark(systemDark)) "dark" else "light")), 13, colors.muted, modifier = Modifier.padding(top = 14.dp), lineHeight = 23.4f)
        Spacer(Modifier.height(30.dp))
        AppearanceHeading(stringResource(R.string.palette), Modifier)
        Column(Modifier.fillMaxWidth().padding(top = 16.dp).selectableGroup(), verticalArrangement = Arrangement.spacedBy(14.dp)) {
            BPaletteOptions.chunked(2).forEach { pair ->
                Row(horizontalArrangement = Arrangement.spacedBy(14.dp)) {
                    pair.forEach { (id, _) ->
                        val label = paletteLabel(id)
                        val description = stringResource(R.string.palette_accessibility, label)
                        val selected = prefs.palette == id
                        Column(
                            Modifier.weight(1f).clip(RoundedCornerShape(17.dp)).background(colors.surface)
                                .border(2.dp, if (selected) colors.accentInk else colors.line, RoundedCornerShape(17.dp))
                                .alpha(if (saving) 0.45f else 1f).selectable(selected, enabled = !saving, role = Role.RadioButton) { if (!selected) onChange(prefs.copy(palette = id)) }
                                .semantics { contentDescription = description }.padding(12.dp),
                        ) {
                            AppearancePreview(bThemeColors(prefs.copy(palette = id), systemDark))
                            Row(Modifier.fillMaxWidth().heightIn(min = 44.dp).padding(start = 3.dp, end = 3.dp, top = 10.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.SpaceBetween) {
                                AppearanceText(label, 16, colors.ink)
                                if (selected) Icon(bIcon("check"), null, Modifier.size(20.dp), tint = colors.accentInk)
                            }
                        }
                    }
                }
            }
        }
        AppearanceText(stringResource(R.string.appearance_scope), 13, colors.muted, modifier = Modifier.padding(top = 14.dp, bottom = 30.dp), lineHeight = 23.4f)
        if (saving) AppearanceText(stringResource(R.string.saving_preferences), 13, colors.muted, modifier = Modifier.semantics { liveRegion = LiveRegionMode.Polite })
        if (error.isNotEmpty()) AppearanceText(error, 13, colors.error, modifier = Modifier.semantics { liveRegion = LiveRegionMode.Assertive })
    }
}

@Composable
private fun AppearanceHeading(text: String, modifier: Modifier) =
    AppearanceText(text, 20, LocalBThemeColors.current.ink, modifier.semantics { heading() }, FontWeight.Bold, 28f)

@Composable
private fun AppearanceText(text: String, size: Int, color: Color, modifier: Modifier = Modifier, weight: FontWeight = FontWeight.Normal, lineHeight: Float = size * 1.5f) {
    Text(text, modifier, color = color, fontSize = businessSp(size.sp), fontWeight = weight, lineHeight = (lineHeight / size).em,
        style = TextStyle(platformStyle = PlatformTextStyle(includeFontPadding = false), lineHeightStyle = BLineHeightStyle))
}

@Composable
private fun AppearancePreview(colors: BThemeColors) {
    Canvas(Modifier.fillMaxWidth().height(105.dp)) {
        val inset = 15.dp.toPx()
        val width = size.width - 2 * inset
        val radius = CornerRadius(10.dp.toPx())
        drawRoundRect(colors.paper, cornerRadius = radius)
        drawRoundRect(colors.line, cornerRadius = radius, style = Stroke(1.dp.toPx()))
        drawRoundRect(colors.ink, Offset(inset, inset), Size(width * 0.42f, 4.dp.toPx()), CornerRadius(3.dp.toPx()))
        val cardTop = 29.dp.toPx()
        val cardSize = Size(width, 36.dp.toPx())
        drawRoundRect(colors.surface, Offset(inset, cardTop), cardSize, CornerRadius(7.dp.toPx()))
        drawRoundRect(colors.line, Offset(inset, cardTop), cardSize, CornerRadius(7.dp.toPx()), style = Stroke(1.dp.toPx()))
        drawRoundRect(colors.soft, Offset(inset + 9.dp.toPx(), 38.dp.toPx()), Size(18.dp.toPx(), 18.dp.toPx()), CornerRadius(5.dp.toPx()))
        drawRoundRect(colors.muted, Offset(inset + 35.dp.toPx(), 45.dp.toPx()), Size((width - 18.dp.toPx()) * 0.5f, 4.dp.toPx()), CornerRadius(3.dp.toPx()))
        drawRoundRect(colors.accentFill, Offset(inset, 75.dp.toPx()), Size(width * 0.62f, 15.dp.toPx()), CornerRadius(5.dp.toPx()))
    }
}
