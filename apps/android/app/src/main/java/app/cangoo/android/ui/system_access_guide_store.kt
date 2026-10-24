package app.cangoo.android.ui

import android.content.Context
import android.util.AtomicFile
import java.io.File

internal fun shouldOfferSystemGuide(completed: Boolean, firstInstall: Long, lastUpdate: Long, existingData: Boolean): Boolean =
    !completed && firstInstall > 0L && firstInstall == lastUpdate && !existingData

internal class SystemAccessGuideStore(private val file: AtomicFile) {
    constructor(context: Context) : this(AtomicFile(File(context.noBackupFilesDir, "system_settings_guide")))
    internal constructor(file: File) : this(AtomicFile(file))
    private companion object { val fileLock = Any() }

    private fun state(): Int? = synchronized(fileLock) {
        try {
            if (!file.baseFile.exists() && !File(file.baseFile.path + ".bak").exists()) -1
            else file.openRead().use { input -> input.read().takeIf { it in 0..1 && input.read() == -1 } }
        } catch (_: Exception) { null }
    }

    fun completed(): Boolean? = state()?.let { it == 1 }

    @Suppress("DEPRECATION")
    fun shouldOffer(context: Context): Boolean = try {
        val info = context.packageManager.getPackageInfo(context.packageName, 0)
        shouldOffer(info.firstInstallTime, info.lastUpdateTime)
    } catch (_: Exception) { false }

    internal fun shouldOffer(firstInstall: Long, lastUpdate: Long): Boolean = synchronized(fileLock) {
        try {
            val state = state()
            if (state == null) false else {
                val files = file.baseFile.parentFile?.listFiles()
                val existing = files == null || files.any {
                    it != file.baseFile && it.name != file.baseFile.name + ".bak" && it.name != file.baseFile.name + ".new" &&
                        (it.isFile || (it.isDirectory && it.list()?.isNotEmpty() != false))
                }
                shouldOfferSystemGuide(state == 1, firstInstall, lastUpdate, state != 0 && existing)
            }
        } catch (_: Exception) { false }
    }

    @Suppress("DEPRECATION")
    fun prepareBeforeTerms(context: Context) {
        val info = runCatching { context.packageManager.getPackageInfo(context.packageName, 0) }.getOrNull() ?: return
        prepareBeforeTerms(info.firstInstallTime, info.lastUpdateTime)
    }

    internal fun prepareBeforeTerms(firstInstall: Long, lastUpdate: Long) = synchronized(fileLock) {
        // 在协议或语言写入前保留真实新装资格，进程重启后仍能完成原引导。
        if (state() == -1 && shouldOffer(firstInstall, lastUpdate)) write(0)
    }

    fun complete() = synchronized(fileLock) { write(1) }

    private fun write(value: Int) {
        val output = file.startWrite()
        try { output.write(value); output.fd.sync() }
        catch (error: Exception) { file.failWrite(output); throw error }
        file.finishWrite(output)
        check(state() == value)
    }
}
