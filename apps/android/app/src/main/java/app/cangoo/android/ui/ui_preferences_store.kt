package app.cangoo.android.ui

import android.content.Context
import android.util.AtomicFile
import android.util.JsonReader
import android.util.JsonToken
import android.util.JsonWriter
import java.io.File
import java.io.FileOutputStream
import java.io.IOException
import java.io.OutputStreamWriter
import java.io.StringReader

data class UiPreferences(
    val palette: String = "green",
    val theme: String = "light",
    val fontScale: Float = 1f,
    val clipboardSeconds: Int = 30,
    val generatorAutoClear: Boolean = true,
    val generatorSeconds: Int = 60,
    val generatorOptions: GeneratorOptions = GeneratorOptions(),
    val language: UiLanguage = UiLanguage.CHINESE,
) {
    init {
        require(validatedGeneratorOptions(generatorOptions) == generatorOptions) { "生成参数须为规范有效值。" }
        require(palette in setOf("green", "beige", "blue", "yellow")) { "配色参数无效。" }
        require(theme in setOf("light", "dark", "auto")) { "明暗参数无效。" }
        require(fontScale in setOf(1f, 1.25f, 1.5f)) { "文字大小参数无效。" }
        require(clipboardSeconds in setOf(5, 30, 60)) { "复制保留时间参数无效。" }
        require(generatorSeconds in setOf(30, 60, 300)) { "生成结果保留时间参数无效。" }
    }
}

internal class UiPreferencesWriteException(val outcomeUnverified: Boolean) : IOException(
    if (outcomeUnverified) "无法核验磁盘上的外观设置，请重新读取设置后重试。"
    else "外观设置未保存，请重试；原设置继续生效。",
)

internal class UiPreferencesStore private constructor(private val file: AtomicFile) {
    constructor(context: Context) : this(AtomicFile(File(context.noBackupFilesDir, "ui_preferences.json")))

    // 专项检查使用独立缓存文件；生产入口仍固定在应用不备份目录。
    internal constructor(file: File) : this(AtomicFile(file))

    private companion object { val fileLock = Any() }

    private val numberLiteral = Regex("""-?(0|[1-9][0-9]*)(\.[0-9]+)?([eE][+-]?[0-9]+)?""")

    fun read(): UiPreferences = synchronized(fileLock) {
        try {
            if (!file.baseFile.exists() && !File(file.baseFile.path + ".bak").exists()) return@synchronized UiPreferences()
            val bytes = file.openRead().use { input ->
                val buffer = ByteArray(4097)
                var size = 0
                while (size < buffer.size) {
                    val count = input.read(buffer, size, buffer.size - size)
                    if (count < 0) break
                    size += count
                }
                require(size <= 4096)
                buffer.copyOf(size)
            }
            return@synchronized decode(bytes.decodeToString(throwOnInvalidSequence = true))
        } catch (_: Exception) {
            throw IOException("外观设置读取失败，请重新保存设置。")
        }
    }

    fun write(value: UiPreferences) = synchronized(fileLock) {
        var output: FileOutputStream? = null
        var commitStarted = false
        try {
            output = file.startWrite()
            // 由 AtomicFile 关闭输出流，不能在提交前关闭 JsonWriter 的底层流。
            val writer = JsonWriter(OutputStreamWriter(output, Charsets.UTF_8))
            writer.beginObject()
            writer.name("version").value(4L)
            writer.name("language").value(value.language.tag)
            writer.name("palette").value(value.palette)
            writer.name("theme").value(value.theme)
            writer.name("font_scale").value(value.fontScale.toDouble())
            writer.name("clipboard_seconds").value(value.clipboardSeconds.toLong())
            writer.name("generator_auto_clear").value(value.generatorAutoClear)
            writer.name("generator_seconds").value(value.generatorSeconds.toLong())
            writer.name("generator_length").value(value.generatorOptions.length.toLong())
            writer.name("generator_upper").value(value.generatorOptions.upper)
            writer.name("generator_lower").value(value.generatorOptions.lower)
            writer.name("generator_digits").value(value.generatorOptions.digits)
            writer.name("generator_symbols").value(value.generatorOptions.symbols)
            writer.name("generator_exclude_ambiguous").value(value.generatorOptions.excludeAmbiguous)
            writer.endObject()
            writer.flush()
            output.fd.sync()
            commitStarted = true
            file.finishWrite(output)
            output = null
            check(file.baseFile.isFile)
            check(read() == value)
        } catch (_: Exception) {
            if (commitStarted) {
                try { output?.close() } catch (_: Exception) { /* 后续读取判断实际磁盘状态。 */ }
                throw UiPreferencesWriteException(outcomeUnverified = true)
            }
            try { if (output != null) file.failWrite(output) }
            catch (_: Exception) { throw UiPreferencesWriteException(outcomeUnverified = true) }
            throw UiPreferencesWriteException(outcomeUnverified = false)
        }
    }

    fun update(unreadableFallback: UiPreferences? = null, change: (UiPreferences) -> UiPreferences): UiPreferences = synchronized(fileLock) {
        var readable = true
        val current = try { read() } catch (error: IOException) {
            readable = false
            unreadableFallback ?: throw error
        }
        val next = change(current)
        if (!readable || next != current) write(next)
        next
    }

    private fun decode(text: String): UiPreferences = JsonReader(StringReader(text)).use { reader ->
        // 自产偏好的键与值均为固定基本拉丁字符；不接收转义，避免原生读取器容忍非法转义。
        require('\\' !in text && text.all { it in ' '..'~' || it in "\t\r\n" })
        reader.isLenient = false
        val names = mutableSetOf<String>()
        var version: Int? = null
        var palette: String? = null
        var theme: String? = null
        var language: UiLanguage? = null
        var fontScale: Float? = null
        var clipboardSeconds: Int? = null
        var generatorAutoClear: Boolean? = null
        var generatorSeconds: Int? = null
        var generatorLength: Int? = null
        val generatorFlags = mutableMapOf<String, Boolean>()
        reader.beginObject()
        while (reader.hasNext()) {
            val name = reader.nextName()
            require(names.add(name))
            when (name) {
                "version" -> version = reader.readInteger()
                "palette" -> palette = reader.readString()
                "theme" -> theme = reader.readString()
                "language" -> {
                    val tag = reader.readString()
                    language = UiLanguage.entries.single { it.tag == tag }
                }
                "font_scale" -> {
                    val number = reader.readNumber().toDouble()
                    require(number in setOf(1.0, 1.25, 1.5))
                    fontScale = number.toFloat()
                }
                "clipboard_seconds" -> clipboardSeconds = reader.readInteger()
                "generator_auto_clear" -> { require(reader.peek() == JsonToken.BOOLEAN); generatorAutoClear = reader.nextBoolean() }
                "generator_seconds" -> generatorSeconds = reader.readInteger()
                "generator_length" -> generatorLength = reader.readInteger()
                "generator_upper", "generator_lower", "generator_digits", "generator_symbols", "generator_exclude_ambiguous" -> {
                    require(reader.peek() == JsonToken.BOOLEAN)
                    generatorFlags[name] = reader.nextBoolean()
                }
                else -> throw IllegalArgumentException("未知设置字段。")
            }
        }
        reader.endObject()
        require(reader.peek() == JsonToken.END_DOCUMENT)
        val original = setOf("version", "palette", "theme", "font_scale", "clipboard_seconds")
        require(version in setOf(1, 2, 3, 4))
        val clearing = setOf("generator_auto_clear", "generator_seconds")
        val parameters = setOf("generator_length", "generator_upper", "generator_lower", "generator_digits", "generator_symbols", "generator_exclude_ambiguous")
        require(names == original + (if (version == 1) emptySet() else clearing) + (if (version in setOf(3, 4)) parameters else emptySet()) +
            (if (version == 4) setOf("language") else emptySet()))
        UiPreferences(requireNotNull(palette), requireNotNull(theme), requireNotNull(fontScale), requireNotNull(clipboardSeconds),
            if (version == 1) true else requireNotNull(generatorAutoClear), if (version == 1) 60 else requireNotNull(generatorSeconds),
            if (version !in setOf(3, 4)) GeneratorOptions() else GeneratorOptions(requireNotNull(generatorLength).toString(),
                generatorFlags.getValue("generator_upper"), generatorFlags.getValue("generator_lower"), generatorFlags.getValue("generator_digits"),
                generatorFlags.getValue("generator_symbols"), generatorFlags.getValue("generator_exclude_ambiguous")),
            if (version == 4) requireNotNull(language) else UiLanguage.CHINESE)
    }

    private fun JsonReader.readInteger(): Int {
        return requireNotNull(readNumber().toIntOrNull())
    }

    private fun JsonReader.readNumber(): String {
        require(peek() == JsonToken.NUMBER)
        val literal = nextString()
        require(numberLiteral.matches(literal))
        return literal
    }

    private fun JsonReader.readString(): String {
        require(peek() == JsonToken.STRING)
        return nextString()
    }
}
