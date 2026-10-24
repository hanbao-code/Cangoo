package app.cangoo.android.ui

import androidx.activity.compose.BackHandler
import androidx.compose.foundation.background
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.IntrinsicSize
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawingPadding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.selection.selectable
import androidx.compose.foundation.selection.selectableGroup
import androidx.compose.foundation.ScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.SideEffect
import androidx.compose.runtime.remember
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.Alignment
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.text.LinkAnnotation
import androidx.compose.ui.text.LinkInteractionListener
import androidx.compose.ui.text.fromHtml
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.PlatformTextStyle
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.em
import androidx.compose.ui.unit.sp
import app.cangoo.android.R

@Composable
internal fun LegalText(value: String, html: Boolean, onContact: () -> Unit = {}) {
    val text = remember(value, html, onContact) {
        if (html) AnnotatedString.fromHtml(value, linkInteractionListener = LinkInteractionListener { link ->
            if (link is LinkAnnotation.Url && link.url == CONTACT_URL) onContact()
        }) else AnnotatedString(value)
    }
    Text(text, Modifier.fillMaxWidth(), color = LocalBThemeColors.current.ink,
        fontSize = businessSp(14.sp), lineHeight = 1.8.em,
        style = TextStyle(platformStyle = PlatformTextStyle(includeFontPadding = false), lineHeightStyle = BLineHeightStyle))
}

@Composable
internal fun LegalLanguageButtons(language: UiLanguage, busy: Boolean, onLanguage: (UiLanguage) -> Unit, modifier: Modifier = Modifier) {
    val colors = LocalBThemeColors.current
    Row(modifier.fillMaxWidth().clip(RoundedCornerShape(12.dp)).background(colors.soft).padding(4.dp)
        .height(IntrinsicSize.Min).selectableGroup()) {
        UiLanguage.entries.forEach { value ->
            val selected = language == value
            Box(Modifier.weight(1f).fillMaxHeight().clip(RoundedCornerShape(9.dp))
                .background(if (selected) colors.surface else Color.Transparent).alpha(if (busy) 0.45f else 1f)
                .selectable(selected, enabled = !busy, role = Role.RadioButton) { if (!selected) onLanguage(value) }
                .heightIn(min = 40.dp).padding(horizontal = 4.dp, vertical = 2.dp), contentAlignment = Alignment.Center) {
                Text(value.label, color = if (selected) colors.ink else colors.muted, fontSize = businessSp(16.sp), lineHeight = 1.5.em,
                    fontWeight = if (selected) FontWeight.SemiBold else FontWeight.Normal)
            }
        }
    }
}

@Composable
internal fun TermsPage(preferences: UiPreferences, content: LegalContent?, visible: Boolean, busy: Boolean, error: Int?,
                       onLanguage: (UiLanguage) -> Unit, onRetry: () -> Unit, onAccept: () -> Unit, onExit: () -> Unit,
                       onSystemAppearance: (Boolean, Int) -> Unit) {
    LocalizedContent(preferences.language) {
        CangooTheme(preferences) {
            val colors = LocalBThemeColors.current
            val dark = preferences.isDark(isSystemInDarkTheme())
            var section by remember(content?.termsVersion) { mutableStateOf("home") }
            var licenseId by remember(content?.termsVersion) { mutableStateOf<String?>(null) }
            val scrollStates = remember(content?.termsVersion) { mutableMapOf<String, ScrollState>() }
            val scroll = scrollStates.getOrPut("$section/${licenseId.orEmpty()}") { ScrollState(0) }
            fun back() {
                if (licenseId != null) licenseId = null
                else if (section != "home") section = "home"
                else onExit()
            }
            SideEffect { onSystemAppearance(dark, colors.paper.toArgb()) }
            BackHandler(enabled = visible) { back() }
            if (!visible) {
                Box(Modifier.fillMaxSize().background(colors.paper))
                return@CangooTheme
            }
            Column(Modifier.fillMaxSize().background(colors.paper).safeDrawingPadding()) {
                Row(Modifier.fillMaxWidth().heightIn(min = 64.dp).padding(horizontal = 16.dp), verticalAlignment = Alignment.CenterVertically) {
                    IconButton(onClick = ::back) { Icon(bIcon("chevron_left"), stringResource(R.string.back), tint = colors.ink) }
                    Text(stringResource(when (section) {
                        "agpl" -> R.string.terms_full_license
                        "openssl" -> R.string.terms_openssl_permission
                        "licenses" -> R.string.terms_third_party_notices
                        else -> R.string.terms_title
                    }), Modifier.weight(1f).semantics { heading() }, color = colors.ink,
                        fontSize = businessSp(18.sp), lineHeight = 1.4.em, letterSpacing = (-0.3).sp, fontWeight = FontWeight.Bold,
                        textAlign = TextAlign.Center)
                }
                Column(Modifier.weight(1f).fillMaxWidth().verticalScroll(scroll).padding(start = 24.dp, top = 8.dp, end = 24.dp, bottom = 24.dp)) {
                    LegalLanguageButtons(preferences.language, busy, onLanguage, Modifier.padding(top = 22.dp, bottom = 20.dp))
                    if (content != null) LegalReadingBody(content, section, licenseId, preferences.language,
                        { section = it }, { licenseId = it })
                    else Text(stringResource(if (busy) R.string.loading else R.string.terms_resource_failed), color = colors.muted,
                        fontSize = businessSp(14.sp), lineHeight = 1.8.em)
                }
                HorizontalDivider(color = colors.line)
                Column(Modifier.fillMaxWidth().padding(horizontal = 24.dp, vertical = 10.dp)) {
                    if (error != null) Text(stringResource(error), Modifier.padding(bottom = 8.dp).semantics { liveRegion = LiveRegionMode.Polite },
                        color = colors.error, fontSize = businessSp(13.sp), lineHeight = 1.5.em)
                    if (content == null && !busy) TextButton(onClick = onRetry, modifier = Modifier.fillMaxWidth()) {
                        Text(stringResource(R.string.retry))
                    }
                    PrimaryButton(stringResource(R.string.terms_accept), busy, enabled = content != null, onClick = onAccept)
                    TextButton(onClick = onExit, modifier = Modifier.fillMaxWidth().padding(top = 4.dp).heightIn(min = 48.dp)) {
                        Text(stringResource(R.string.terms_decline), color = colors.accentInk, fontSize = businessSp(14.sp), lineHeight = 1.5.em,
                            fontWeight = FontWeight.SemiBold)
                    }
                }
            }
        }
    }
}
