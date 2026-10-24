package app.cangoo.android.data

import com.google.gson.Strictness
import com.google.gson.stream.JsonReader
import com.google.gson.stream.JsonToken
import com.google.gson.stream.MalformedJsonException
import java.io.EOFException
import java.io.FilterInputStream
import java.io.IOException
import java.io.InputStreamReader
import java.net.CookieHandler
import java.net.HttpURLConnection
import java.net.URL
import java.nio.charset.CharacterCodingException
import java.nio.charset.CodingErrorAction
import java.time.Instant
import java.time.format.DateTimeParseException
import java.util.Timer
import java.util.TimerTask
import java.util.concurrent.CancellationException
import java.util.zip.GZIPInputStream
import java.util.zip.ZipException
import javax.net.ssl.HttpsURLConnection

internal data class PublicRelease(val version: String, val tag: String, val publishedAt: String, val notes: String)
internal enum class ReleaseCheckProblem { NETWORK, INCOMPLETE, INVALID_RESPONSE }
internal class ReleaseCheckException(val problem: ReleaseCheckProblem) : IllegalStateException("公开版本查询失败：$problem")

internal class ReleaseRequest(private val nanoTime: () -> Long = System::nanoTime) {
    private var cancelled = false
    private var expired = false
    private var deadline: Long? = null
    private var connection: HttpURLConnection? = null

    fun cancel() {
        val active = synchronized(this) { cancelled = true; connection }
        active?.disconnect()
    }

    @Synchronized fun checkActive() {
        if (cancelled || Thread.currentThread().isInterrupted) throw CancellationException("版本查询已取消")
        if (expired || deadline?.let { nanoTime() - it >= 0 } == true) failRelease(ReleaseCheckProblem.INCOMPLETE)
    }

    @Synchronized internal fun begin() {
        checkActive()
        check(deadline == null)
        deadline = nanoTime() + 20_000_000_000L
    }

    internal fun expire() {
        val active = synchronized(this) { expired = true; connection }
        active?.disconnect()
    }

    @Synchronized internal fun attach(value: HttpURLConnection) {
        checkActive()
        connection = value
    }

    @Synchronized internal fun detach(value: HttpURLConnection) { if (connection === value) connection = null }

    @Synchronized internal fun waitMillis(): Int {
        checkActive()
        return minOf(5000L, ((requireNotNull(deadline) - nanoTime()) / 1_000_000L).coerceAtLeast(1)).toInt()
    }
}

internal interface ReleaseTransport { fun fetch(architecture: String, request: ReleaseRequest): PublicRelease? }

// 只请求固定仓库的公开资料，保留平台证书校验，不携带认证信息或设备标识。
internal class GitHubReleaseTransport(
    private val openConnection: (URL) -> HttpURLConnection = { it.openConnection() as HttpsURLConnection },
) : ReleaseTransport {
    override fun fetch(architecture: String, request: ReleaseRequest): PublicRelease? {
        if (architecture !in setOf("arm64", "x64", "arm32", "x86")) failRelease(ReleaseCheckProblem.INVALID_RESPONSE)
        request.begin()
        val timer = Timer("cangoo_update_deadline", true)
        timer.schedule(object : TimerTask() { override fun run() { request.expire() } }, 20_000L)
        var consumed = 0
        var latest: PublicRelease? = null
        try {
            for (page in 1..10) {
                request.checkActive()
                if (CookieHandler.getDefault() != null) failRelease(ReleaseCheckProblem.NETWORK)
                val connection = openConnection(URL("https://api.github.com/repos/hanbao-code/Cangoo/releases?per_page=100&page=$page"))
                try {
                    request.attach(connection)
                    connection.requestMethod = "GET"
                    connection.instanceFollowRedirects = false
                    connection.useCaches = false
                    connection.allowUserInteraction = false
                    connection.connectTimeout = request.waitMillis()
                    connection.readTimeout = request.waitMillis()
                    connection.setRequestProperty("User-Agent", "Cangoo-Version-Check")
                    connection.setRequestProperty("Accept", "application/vnd.github+json")
                    connection.setRequestProperty("Accept-Encoding", "identity")
                    connection.setRequestProperty("X-GitHub-Api-Version", "2026-03-10")
                    if (connection.responseCode != 200) failRelease(ReleaseCheckProblem.NETWORK)
                    request.checkActive()
                    val input = when (connection.contentEncoding?.lowercase()) {
                        null, "", "identity" -> connection.inputStream
                        "gzip" -> GZIPInputStream(connection.inputStream)
                        else -> failRelease(ReleaseCheckProblem.INVALID_RESPONSE)
                    }
                    val bounded = object : FilterInputStream(input) {
                        override fun read(): Int {
                            val byte = ByteArray(1)
                            return if (read(byte, 0, 1) < 0) -1 else byte[0].toInt() and 255
                        }
                        override fun read(bytes: ByteArray, offset: Int, length: Int): Int {
                            request.checkActive()
                            connection.readTimeout = request.waitMillis()
                            val count = `in`.read(bytes, offset, minOf(length, MAX_RELEASE_BYTES - consumed + 1))
                            request.checkActive()
                            if (count > 0) {
                                consumed += count
                                if (consumed > MAX_RELEASE_BYTES) failRelease(ReleaseCheckProblem.INCOMPLETE)
                            }
                            return count
                        }
                    }
                    val decoder = Charsets.UTF_8.newDecoder().onMalformedInput(CodingErrorAction.REPORT).onUnmappableCharacter(CodingErrorAction.REPORT)
                    val count = JsonReader(InputStreamReader(bounded, decoder)).use { reader ->
                        reader.setStrictness(Strictness.STRICT)
                        reader.setNestingLimit(16)
                        reader.beginArray()
                        var count = 0
                        while (reader.hasNext()) {
                            request.checkActive()
                            if (++count > 100) failRelease(ReleaseCheckProblem.INCOMPLETE)
                            val release = readRelease(reader, architecture)
                            if (release != null && (latest == null || publicVersionCompare(release.version, latest!!.version)!! > 0)) latest = release
                        }
                        reader.endArray()
                        if (reader.peek() != JsonToken.END_DOCUMENT) failRelease(ReleaseCheckProblem.INVALID_RESPONSE)
                        count
                    }
                    val hasNext = connection.headerFields.any { (name, values) ->
                        name?.equals("Link", ignoreCase = true) == true && values.any(::hasNextReleasePage)
                    }
                    request.checkActive()
                    if (count < 100 && !hasNext) return latest
                } finally {
                    request.detach(connection)
                    connection.disconnect()
                }
            }
            failRelease(ReleaseCheckProblem.INCOMPLETE)
        } catch (failure: CancellationException) { throw failure }
        catch (failure: ReleaseCheckException) { request.checkActive(); throw failure }
        catch (_: MalformedJsonException) { request.checkActive(); failRelease(ReleaseCheckProblem.INVALID_RESPONSE) }
        catch (_: EOFException) { request.checkActive(); failRelease(ReleaseCheckProblem.INVALID_RESPONSE) }
        catch (_: CharacterCodingException) { request.checkActive(); failRelease(ReleaseCheckProblem.INVALID_RESPONSE) }
        catch (_: ZipException) { request.checkActive(); failRelease(ReleaseCheckProblem.INVALID_RESPONSE) }
        catch (_: IOException) { request.checkActive(); failRelease(ReleaseCheckProblem.NETWORK) }
        catch (_: IllegalStateException) { request.checkActive(); failRelease(ReleaseCheckProblem.INVALID_RESPONSE) }
        catch (_: IllegalArgumentException) { request.checkActive(); failRelease(ReleaseCheckProblem.INVALID_RESPONSE) }
        catch (_: SecurityException) { request.checkActive(); failRelease(ReleaseCheckProblem.NETWORK) }
        finally { timer.cancel() }
    }
}

private const val MAX_RELEASE_BYTES = 4 * 1024 * 1024
private val PUBLIC_VERSION = Regex("""(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)""")
private val UNSIGNED_INTEGER = Regex("0|[1-9][0-9]*")
private val LINK_PART = Regex("""<[^>]*>|;\s*([^=;\s,]+)\s*=\s*(?:"((?:[^"\\]|\\.)*)"|([^;,\s]+))""")

private fun hasNextReleasePage(header: String): Boolean = LINK_PART.findAll(header).any { part ->
    part.groupValues[1].equals("rel", ignoreCase = true) &&
        (part.groups[2]?.value ?: part.groupValues[3]).split(Regex("\\s+")).any { it.equals("next", ignoreCase = true) }
}

internal fun publicVersionCompare(left: String, right: String): Int? {
    val a = PUBLIC_VERSION.matchEntire(left)?.groupValues ?: return null
    val b = PUBLIC_VERSION.matchEntire(right)?.groupValues ?: return null
    for (index in 1..3) {
        val comparison = a[index].length.compareTo(b[index].length).takeIf { it != 0 } ?: a[index].compareTo(b[index])
        if (comparison != 0) return comparison
    }
    return 0
}

internal fun releasePageUrl(release: PublicRelease): String {
    if (publicVersionCompare(release.version, release.version) == null || release.tag != "android-v${release.version}")
        failRelease(ReleaseCheckProblem.INVALID_RESPONSE)
    return "https://github.com/hanbao-code/Cangoo/releases/tag/${release.tag}"
}

private data class ReleaseAsset(val name: String?, val uploaded: Boolean, val positiveSize: Boolean)

private fun readRelease(reader: JsonReader, architecture: String): PublicRelease? {
    var tag: String? = null
    var draft: Boolean? = null
    var prerelease: Boolean? = null
    var date: String? = null
    var notes = ""
    var assets: List<ReleaseAsset>? = null
    readObject(reader) { name -> when (name) {
        "tag_name" -> tag = readNullableText(reader)
        "draft" -> draft = readNullableBoolean(reader)
        "prerelease" -> prerelease = readNullableBoolean(reader)
        "published_at" -> date = readNullableText(reader)
        "body" -> notes = readNullableText(reader).orEmpty()
        "assets" -> {
            if (reader.peek() == JsonToken.NULL) { reader.nextNull(); return@readObject }
            val values = mutableListOf<ReleaseAsset>()
            reader.beginArray()
            while (reader.hasNext()) {
                var assetName: String? = null
                var uploaded = false
                var positiveSize = false
                readObject(reader) { field -> when (field) {
                    "name" -> assetName = readNullableText(reader)
                    "state" -> uploaded = readNullableText(reader) == "uploaded"
                    "size" -> if (reader.peek() == JsonToken.NULL) reader.nextNull() else {
                        if (reader.peek() != JsonToken.NUMBER) failRelease(ReleaseCheckProblem.INVALID_RESPONSE)
                        val value = reader.nextString()
                        if (!UNSIGNED_INTEGER.matches(value)) failRelease(ReleaseCheckProblem.INVALID_RESPONSE)
                        positiveSize = value != "0"
                    }
                    else -> reader.skipValue()
                } }
                values.add(ReleaseAsset(assetName, uploaded, positiveSize))
            }
            reader.endArray()
            assets = values
        }
        else -> reader.skipValue()
    } }
    if (draft == true || prerelease == true) return null
    val releaseTag = tag ?: failRelease(ReleaseCheckProblem.INCOMPLETE)
    if (!releaseTag.startsWith("android-v")) return null
    val version = releaseTag.removePrefix("android-v")
    if (publicVersionCompare(version, version) == null) failRelease(ReleaseCheckProblem.INVALID_RESPONSE)
    if (draft == null || prerelease == null || date.isNullOrBlank() || assets == null) failRelease(ReleaseCheckProblem.INCOMPLETE)
    try { Instant.parse(date) } catch (_: DateTimeParseException) { failRelease(ReleaseCheckProblem.INVALID_RESPONSE) }
    for (expected in listOf("cangoo-$version-android-$architecture.apk", "sha256sums.txt")) {
        val matches = assets!!.filter { it.name == expected }
        if (matches.size != 1 || !matches.single().uploaded || !matches.single().positiveSize) failRelease(ReleaseCheckProblem.INCOMPLETE)
    }
    return PublicRelease(version, releaseTag, date!!, notes.substring(0, notes.offsetByCodePoints(0, minOf(4000, notes.codePointCount(0, notes.length)))))
}

private fun readObject(reader: JsonReader, field: (String) -> Unit) {
    val seen = mutableSetOf<String>()
    reader.beginObject()
    while (reader.hasNext()) {
        val name = reader.nextName()
        if (!seen.add(name)) failRelease(ReleaseCheckProblem.INVALID_RESPONSE)
        field(name)
    }
    reader.endObject()
}

private fun readNullableText(reader: JsonReader): String? = when (reader.peek()) {
    JsonToken.NULL -> { reader.nextNull(); null }
    JsonToken.STRING -> reader.nextString()
    else -> failRelease(ReleaseCheckProblem.INVALID_RESPONSE)
}

private fun readNullableBoolean(reader: JsonReader): Boolean? {
    if (reader.peek() == JsonToken.NULL) { reader.nextNull(); return null }
    if (reader.peek() != JsonToken.BOOLEAN) failRelease(ReleaseCheckProblem.INVALID_RESPONSE)
    return reader.nextBoolean()
}

private fun failRelease(problem: ReleaseCheckProblem): Nothing = throw ReleaseCheckException(problem)
