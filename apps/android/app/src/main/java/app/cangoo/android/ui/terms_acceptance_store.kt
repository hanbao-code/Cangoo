package app.cangoo.android.ui

import android.content.Context
import android.util.AtomicFile
import java.io.File

internal class TermsAcceptanceStore(private val file: AtomicFile) {
    constructor(context: Context) : this(AtomicFile(File(context.noBackupFilesDir, "accepted_terms_version")))
    internal constructor(file: File) : this(AtomicFile(file))
    private companion object { val fileLock = Any() }

    fun accepted(version: String): Boolean = synchronized(fileLock) {
        require(validVersion(version))
        if (!file.baseFile.exists() && !File(file.baseFile.path + ".bak").exists()) return@synchronized false
        val bytes = file.openRead().use { input ->
            val buffer = ByteArray(65)
            var count = 0
            while (count < buffer.size) {
                val read = input.read(buffer, count, buffer.size - count)
                if (read < 0) break
                count += read
            }
            require(count <= 64)
            buffer.copyOf(count)
        }
        val saved = bytes.decodeToString(throwOnInvalidSequence = true)
        require(validVersion(saved))
        saved == version
    }

    fun accept(version: String) = synchronized(fileLock) {
        require(validVersion(version))
        val output = file.startWrite()
        try { output.write(version.toByteArray(Charsets.UTF_8)); output.fd.sync() }
        catch (error: Exception) { file.failWrite(output); throw error }
        file.finishWrite(output)
        check(accepted(version))
    }

    private fun validVersion(value: String): Boolean = value.isNotEmpty() && value.length <= 64 &&
        value.all { it.isLetterOrDigit() && it.code < 128 || it in "._-" }
}
