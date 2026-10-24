package app.cangoo.android.ui

import android.content.Context
import android.content.ContextWrapper
import android.content.res.Configuration
import android.content.res.Resources
import androidx.annotation.AnyRes
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.remember
import androidx.compose.ui.platform.LocalConfiguration
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalResources
import java.util.Locale
import java.text.DateFormat
import java.util.Date
import app.cangoo.android.R

enum class UiLanguage(val tag: String, val label: String) {
    CHINESE("zh-Hans", "简体中文"),
    ENGLISH("en", "English");

    val locale: Locale get() = Locale.forLanguageTag(tag)
}

data class UiText(@param:AnyRes val resource: Int, val arguments: List<Any> = emptyList(), val quantity: Int? = null) {
    fun resolve(resources: Resources): String {
        if (isEmpty()) return ""
        val values = arguments.map { value -> when (value) {
            is UiText -> value.resolve(resources)
            is UiDate -> DateFormat.getDateTimeInstance(DateFormat.SHORT, DateFormat.SHORT, resources.configuration.locales[0]).format(Date(value.epochMillis))
            else -> value
        } }
        return if (quantity == null) resources.getString(resource, *values.toTypedArray())
            else resources.getQuantityString(resource, quantity, *values.toTypedArray())
    }
    fun isEmpty(): Boolean = resource == 0
    fun isNotEmpty(): Boolean = !isEmpty()
    fun ifEmpty(other: () -> UiText): UiText = if (isEmpty()) other() else this
    operator fun plus(other: UiText): UiText = when {
        isEmpty() -> other
        other.isEmpty() -> this
        else -> UiText(R.string.message_join, listOf(this, other))
    }
    override fun toString(): String = "UiText(resource=$resource)"
    companion object { val Empty = UiText(0) }
}

internal data class UiDate(val epochMillis: Long)

@Composable
internal fun UiText.localized(): String = resolve(LocalResources.current)

internal fun localizedResources(context: Context, language: UiLanguage, configuration: Configuration = context.resources.configuration): Resources =
    context.createConfigurationContext(Configuration(configuration).apply { setLocale(language.locale) }).resources

internal class LocalizedResourceContext(base: Context, private val localized: Resources) : ContextWrapper(base) {
    override fun getResources(): Resources = localized
    override fun getAssets() = localized.assets
}

@Composable
internal fun LocalizedContent(language: UiLanguage, content: @Composable () -> Unit) {
    val context = LocalContext.current
    val configuration = LocalConfiguration.current
    val resources = remember(context, configuration, language) { localizedResources(context, language, configuration) }
    val resourceContext = remember(context, resources) { LocalizedResourceContext(context, resources) }
    // 原生文字菜单也从Context读取文字；其余宿主能力仍委托原上下文。
    CompositionLocalProvider(LocalContext provides resourceContext, LocalConfiguration provides resources.configuration,
        LocalResources provides resources, content = content)
}
