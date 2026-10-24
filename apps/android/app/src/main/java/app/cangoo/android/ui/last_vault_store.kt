package app.cangoo.android.ui

import android.content.Context
import android.util.AtomicFile
import java.io.File
import java.util.UUID

internal class LastVaultStore(private val file: AtomicFile) {
    constructor(context: Context) : this(AtomicFile(File(context.noBackupFilesDir, "last_vault")))
    internal constructor(file: File) : this(AtomicFile(file))

    @Synchronized
    fun read(): String? {
        if (!file.baseFile.exists() && !File(file.baseFile.path + ".bak").exists()) return null
        val value = file.openRead().use { input ->
            val bytes = ByteArray(37)
            var size = 0
            while (size < bytes.size) {
                val count = input.read(bytes, size, bytes.size - size)
                if (count < 0) break
                size += count
            }
            require(size == 36)
            bytes.decodeToString(0, size, throwOnInvalidSequence = true)
        }
        require(UUID.fromString(value).toString() == value)
        return value
    }

    @Synchronized
    fun write(id: String) {
        require(UUID.fromString(id).toString() == id)
        val output = file.startWrite()
        try {
            output.write(id.toByteArray(Charsets.US_ASCII))
            output.fd.sync()
        } catch (error: Exception) {
            file.failWrite(output)
            throw error
        }
        file.finishWrite(output)
        check(read() == id)
    }
}
