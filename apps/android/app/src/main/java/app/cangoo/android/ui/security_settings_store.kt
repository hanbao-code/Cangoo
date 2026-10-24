package app.cangoo.android.ui

import android.content.Context
import android.util.AtomicFile
import org.json.JSONObject
import java.io.File

internal class SecuritySettingsStore(context: Context) {
    private val file = AtomicFile(File(context.noBackupFilesDir, "security_settings.json"))

    fun read(): SecuritySettings {
        if (!file.baseFile.exists() && !File(file.baseFile.path + ".bak").exists()) return SecuritySettings()
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
        val json = JSONObject(bytes.decodeToString(throwOnInvalidSequence = true))
        require(json.keys().asSequence().toSet() == setOf("idle_minutes", "lock_on_leave"))
        return SecuritySettings(json.get("idle_minutes") as Int, json.get("lock_on_leave") as Boolean)
    }

    fun write(value: SecuritySettings) {
        val bytes = JSONObject().put("idle_minutes", value.idleMinutes)
            .put("lock_on_leave", value.lockOnLeave).toString().toByteArray(Charsets.UTF_8)
        val output = file.startWrite()
        try {
            output.write(bytes)
            output.fd.sync()
            file.finishWrite(output)
            check(file.baseFile.isFile)
            check(read() == value)
        } catch (error: Exception) {
            file.failWrite(output)
            throw error
        }
    }
}
