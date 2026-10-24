package app.cangoo.android.ui

import android.app.Activity
import android.content.ActivityNotFoundException
import android.content.Context
import android.content.Intent
import androidx.core.net.toUri
import org.json.JSONObject

internal const val CONTACT_URL = "https://t.me/+kQEszbuHNEgxOGRh"

internal data class ThirdPartyLicense(val id: String, val title: String, val version: String, val text: String, val html: Boolean)

internal data class LegalTranslation(val chinese: String, val english: String) {
    fun text(language: UiLanguage): String = if (language == UiLanguage.ENGLISH) english else chinese
}

internal data class LocalLicenseDocument(val title: LegalTranslation, val intro: LegalTranslation, val text: String)

internal data class LegalContent(val termsVersion: String, val author: String, val chinese: String, val english: String,
                                val licenses: List<ThirdPartyLicense>, val documents: Map<String, LocalLicenseDocument>,
                                val licenseIntro: LegalTranslation) {
    fun terms(language: UiLanguage): String = if (language == UiLanguage.ENGLISH) english else chinese

    companion object {
        fun read(context: Context): LegalContent {
            val bytes = context.assets.open("legal_content.json").use { it.readBytes() }
            require(bytes.size in 1..2_000_000)
            val json = JSONObject(bytes.decodeToString(throwOnInvalidSequence = true))
            fun text(source: JSONObject, name: String): String = (source.get(name) as String).also { require(it.isNotBlank()) }
            fun translated(source: JSONObject) = LegalTranslation(text(source, "zh"), text(source, "en"))
            val version = text(json, "terms_version").also { require(it.length <= 64) }
            val terms = json.getJSONObject("terms")
            val sourceDocuments = json.getJSONObject("license_documents")
            require(sourceDocuments.keys().asSequence().toSet() == setOf("agpl", "openssl"))
            val documents = listOf("agpl", "openssl").associateWith { id ->
                val document = sourceDocuments.getJSONObject(id)
                LocalLicenseDocument(translated(document.getJSONObject("title")), translated(document.getJSONObject("intro")), text(document, "text"))
            }
            val entries = json.getJSONArray("licenses")
            val licenses = (0 until entries.length()).map { index ->
                val entry = entries.getJSONObject(index)
                val format = text(entry, "format").also { require(it in setOf("text", "html")) }
                ThirdPartyLicense(text(entry, "id"), text(entry, "title"), entry.getString("version"), text(entry, "text"), format == "html")
            }
            require(licenses.isNotEmpty() && licenses.map { it.id }.toSet().size == licenses.size)
            return LegalContent(version, text(json, "author"), text(terms, "zh"), text(terms, "en"), licenses, documents,
                translated(json.getJSONObject("licenseIntro")))
        }
    }
}

internal fun openContact(activity: Activity): Boolean = try {
    activity.startActivity(Intent(Intent.ACTION_VIEW, CONTACT_URL.toUri()))
    true
} catch (_: ActivityNotFoundException) { false }
catch (_: SecurityException) { false }
