package app.cangoo.android.ui

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.Image
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.TextButton
import androidx.compose.material3.Surface
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import app.cangoo.android.R
import app.cangoo.android.BuildConfig
import androidx.compose.ui.res.stringResource
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.Alignment
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.PlatformTextStyle
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.unit.em
import androidx.compose.ui.res.painterResource
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlinx.coroutines.CancellationException

// 公开帮助的来源和滚动由父层持有，不读取密码库。
@Composable
internal fun BHelpPage(section: String, licenseId: String?, onSection: (String) -> Unit, onLicense: (String?) -> Unit,
                       language: UiLanguage, languageSaving: Boolean, languageError: String, onLanguage: (UiLanguage) -> Unit,
                       onContact: () -> Boolean, modifier: Modifier = Modifier,
                       updates: UpdateCheckController? = null, onOpenRelease: () -> Boolean = { false },
                       updateDialogModifier: Modifier = Modifier) {
    val context = LocalContext.current
    val colors = LocalBThemeColors.current
    var content by remember { mutableStateOf<LegalContent?>(null) }
    var failed by remember { mutableStateOf(false) }
    var retry by remember { mutableStateOf(0) }
    var contactFailed by remember(section, licenseId) { mutableStateOf(false) }
    LaunchedEffect(retry) {
        failed = false
        try { content = withContext(Dispatchers.IO) { LegalContent.read(context) } }
        catch (cancelled: CancellationException) { throw cancelled }
        catch (_: Exception) { failed = true }
    }
    fun contact() { contactFailed = !onContact() }
    Column(modifier.fillMaxWidth(), verticalArrangement = Arrangement.spacedBy(14.dp)) {
        if (section == "menu") {
            Column(Modifier.padding(top = 12.dp)) { SettingsGroup {
                listOf("manual" to R.string.help_manual, "terms" to R.string.help_terms, "about" to R.string.help_about).forEachIndexed { index, (id, title) ->
                    SettingsAction(stringResource(title), "", true, if (id == "about") "info" else "note") { onSection(id) }
                    if (index < 2) HorizontalDivider(Modifier.padding(horizontal = 14.dp), color = colors.line)
                }
            } }
        } else if (section == "manual") ManualSections()
        else {
            val current = content
            if (current == null) {
                Text(stringResource(if (failed) R.string.terms_resource_failed else R.string.loading), color = if (failed) colors.error else colors.muted)
                if (failed) TextButton(onClick = { retry++ }) { Text(stringResource(R.string.retry)) }
            } else when (section) {
                "terms", "agpl", "openssl", "terms_licenses" -> Column {
                    LegalLanguageButtons(language, languageSaving, onLanguage, Modifier.padding(top = 22.dp, bottom = 20.dp))
                    if (languageError.isNotEmpty()) Text(languageError, color = colors.error, fontSize = businessSp(13.sp), lineHeight = 1.5.em)
                    LegalReadingBody(current, when (section) { "terms" -> "home"; "terms_licenses" -> "licenses"; else -> section },
                        licenseId, language, { onSection(if (it == "licenses") "terms_licenses" else it) }, onLicense)
                }
                "about" -> {
                    Box(Modifier.fillMaxWidth().padding(top = 12.dp, bottom = 2.dp), contentAlignment = Alignment.Center) {
                        Image(painterResource(R.drawable.app_icon), null, Modifier.size(72.dp))
                    }
                    Text("小仓", Modifier.fillMaxWidth(), color = colors.ink, fontSize = businessSp(20.sp), lineHeight = 1.4.em,
                        fontWeight = FontWeight.Bold, textAlign = androidx.compose.ui.text.style.TextAlign.Center)
                    Text(stringResource(R.string.about_version, BuildConfig.VERSION_NAME), color = colors.muted)
                    Text(stringResource(R.string.about_author, current.author), color = colors.muted)
                    updates?.let { UpdateCheckCard(it, onOpenRelease, dialogModifier = updateDialogModifier) }
                    Column(Modifier.padding(vertical = 10.dp)) { SettingsGroup {
                        SettingsAction(stringResource(R.string.third_party_licenses), "", true, "note") { onSection("licenses") }
                    } }
                    Text(stringResource(R.string.contact_admin_hint), color = colors.muted, fontSize = businessSp(16.sp), lineHeight = 1.5.em)
                    Text(CONTACT_URL, color = colors.muted, fontSize = businessSp(13.sp), lineHeight = 1.5.em)
                    if (contactFailed) Text(stringResource(R.string.contact_open_failed), color = colors.error, fontSize = businessSp(13.sp), lineHeight = 1.5.em)
                    Button(onClick = ::contact, modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp), shape = RoundedCornerShape(11.dp),
                        colors = ButtonDefaults.buttonColors(containerColor = colors.soft, contentColor = colors.ink)) {
                        Text(stringResource(if (contactFailed) R.string.retry else R.string.contact_admin), fontSize = businessSp(14.sp), lineHeight = 1.5.em)
                    }
                }
                "licenses" -> LegalReadingBody(current, "licenses", licenseId, language, onSection, onLicense)
                else -> Text(stringResource(R.string.terms_resource_failed), color = colors.error)
            }
        }
        if (contactFailed && section != "about") {
            Text(stringResource(R.string.contact_open_failed), color = colors.error, fontSize = businessSp(13.sp), lineHeight = 1.5.em)
            TextButton(onClick = ::contact) { Text(stringResource(R.string.retry)) }
        }
    }
}

@Composable
internal fun LegalReadingBody(content: LegalContent, section: String, licenseId: String?, language: UiLanguage,
                              onSection: (String) -> Unit, onLicense: (String?) -> Unit) {
    val colors = LocalBThemeColors.current
    Column(Modifier.fillMaxWidth(), verticalArrangement = Arrangement.spacedBy(14.dp)) {
        when (section) {
            "home" -> {
                Text(stringResource(R.string.about_version, BuildConfig.VERSION_NAME), color = colors.muted)
                LegalText(content.terms(language), html = true)
                HelpAction(stringResource(R.string.terms_full_license)) { onSection("agpl") }
                HelpAction(stringResource(R.string.terms_openssl_permission)) { onSection("openssl") }
                HelpAction(stringResource(R.string.terms_third_party_notices)) { onSection("licenses") }
            }
            "agpl", "openssl" -> {
                val document = content.documents[section]
                if (document == null) Text(stringResource(R.string.terms_resource_failed), color = colors.error)
                else {
                    Text(document.title.text(language), color = colors.ink, fontSize = businessSp(20.sp), lineHeight = 1.4.em,
                        fontWeight = FontWeight.Bold, modifier = Modifier.semantics { heading() })
                    LegalText(document.intro.text(language), html = false)
                    LegalText(document.text, html = false)
                }
            }
            "licenses" -> {
                if (licenseId == null) {
                    LegalText(content.licenseIntro.text(language), html = true)
                    content.licenses.forEach { license ->
                        HelpAction(listOf(license.title, license.version).filter(String::isNotBlank).joinToString(" · ")) { onLicense(license.id) }
                    }
                } else {
                    val selected = content.licenses.firstOrNull { it.id == licenseId }
                    if (selected == null) Text(stringResource(R.string.terms_resource_failed), color = colors.error)
                    else {
                        Text(selected.title, color = colors.ink, fontSize = businessSp(20.sp), lineHeight = 1.4.em,
                            fontWeight = FontWeight.Bold, modifier = Modifier.semantics { heading() })
                        if (selected.version.isNotBlank()) Text(selected.version, color = colors.muted)
                        LegalText(selected.text, selected.html)
                    }
                }
            }
            else -> Text(stringResource(R.string.terms_resource_failed), color = colors.error)
        }
    }
}

@Composable
private fun HelpAction(label: String, onClick: () -> Unit) {
    Surface(onClick = onClick, color = LocalBThemeColors.current.surface, shape = RoundedCornerShape(17.dp), modifier = Modifier.fillMaxWidth()) {
        Text(label, Modifier.padding(18.dp), color = LocalBThemeColors.current.ink, fontSize = businessSp(16.sp), lineHeight = 1.5.em)
    }
}

@Composable
private fun ManualSections() {
    Column(Modifier.fillMaxWidth()) {
        HelpSection(stringResource(R.string.help_1_title), stringResource(R.string.help_1_body))
        HelpSection(stringResource(R.string.help_2_title), stringResource(R.string.help_2_body))
        HelpSection(stringResource(R.string.help_3_title), stringResource(R.string.help_3_body))
        HelpSection(stringResource(R.string.help_4_title), stringResource(R.string.help_4_body))
        HelpSection(stringResource(R.string.help_5_title), stringResource(R.string.help_5_body))
        HelpSection(stringResource(R.string.help_6_title), stringResource(R.string.help_6_body))
        HelpSection(stringResource(R.string.help_7_title), stringResource(R.string.help_7_body))
        HelpSection(stringResource(R.string.help_8_title), stringResource(R.string.help_8_body))
        HelpSection(stringResource(R.string.help_9_title), stringResource(R.string.help_9_body))
        HelpSection(stringResource(R.string.help_10_title), stringResource(R.string.help_10_body))
        HelpSection(stringResource(R.string.help_11_title), stringResource(R.string.help_11_body))
        HelpSection(stringResource(R.string.help_12_title), stringResource(R.string.help_12_body))
        HelpSection(stringResource(R.string.help_13_title), stringResource(R.string.help_13_body))
        HelpSection(stringResource(R.string.help_14_title), stringResource(R.string.help_14_body))
        HelpSection(stringResource(R.string.help_15_title), stringResource(R.string.help_15_body))
    }
}

@Composable
private fun HelpSection(title: String, body: String) {
    val colors = LocalBThemeColors.current
    val style = TextStyle(platformStyle = PlatformTextStyle(includeFontPadding = false), lineHeightStyle = BLineHeightStyle)
    Column(Modifier.fillMaxWidth().padding(top = 18.dp)) {
        Text(title, color = colors.ink, fontSize = businessSp(19.sp), lineHeight = 1.4.em, letterSpacing = (-0.3).sp, fontWeight = FontWeight.Bold,
            modifier = Modifier.fillMaxWidth().padding(bottom = 10.dp).semantics { heading() }, style = style)
        Text(body, color = colors.muted, fontSize = businessSp(14.sp), lineHeight = 2.em, letterSpacing = 0.sp,
            modifier = Modifier.fillMaxWidth(), style = style)
    }
}
