package app.cangoo.android.ui

import app.cangoo.android.R
import android.app.Activity
import android.app.ActivityManager
import android.app.AppOpsManager
import android.content.Context
import android.content.Intent
import android.hardware.biometrics.BiometricManager
import android.net.Uri
import android.os.Build
import android.os.PowerManager
import android.os.Process
import android.provider.Settings

internal enum class ClipboardAccessMode(val label: String) {
    ALLOWED("允许"), FOREGROUND("仅前台"), DENIED("未允许"), DEFAULT("系统默认"), UNKNOWN("需到系统设置确认"),
}

internal fun clipboardAccessMode(mode: Int?): ClipboardAccessMode = when (mode) {
    AppOpsManager.MODE_ALLOWED -> ClipboardAccessMode.ALLOWED
    AppOpsManager.MODE_FOREGROUND -> ClipboardAccessMode.FOREGROUND
    AppOpsManager.MODE_IGNORED, AppOpsManager.MODE_ERRORED -> ClipboardAccessMode.DENIED
    AppOpsManager.MODE_DEFAULT -> ClipboardAccessMode.DEFAULT
    else -> ClipboardAccessMode.UNKNOWN
}

internal data class SystemAccessSnapshot(
    val clipboardRead: ClipboardAccessMode = ClipboardAccessMode.UNKNOWN,
    val clipboardWrite: ClipboardAccessMode = ClipboardAccessMode.UNKNOWN,
    val backgroundRestricted: Boolean? = null,
    val batteryExempt: Boolean? = null,
    val biometricCapability: Int? = null,
    val biometricName: String? = null,
    val strongBiometricQuery: Boolean = Build.VERSION.SDK_INT >= 30,
)

internal fun readSystemAccess(context: Context, biometricCapability: Int, biometricName: String? = null): SystemAccessSnapshot {
    @Suppress("DEPRECATION")
    fun clipboardMode(operation: String): ClipboardAccessMode = clipboardAccessMode(runCatching {
        check(context.applicationInfo.uid == Process.myUid())
        val manager = context.getSystemService(AppOpsManager::class.java) ?: return@runCatching null
        // 操作标识不是开发工具包公开常量；只经公开方法查询自身，系统不识别或拒绝时降级未知。
        if (Build.VERSION.SDK_INT >= 36) manager.checkOpRawNoThrow(operation, Process.myUid(), context.packageName, null)
        else manager.unsafeCheckOpRawNoThrow(operation, Process.myUid(), context.packageName)
    }.getOrNull())
    return SystemAccessSnapshot(
        clipboardRead = clipboardMode("android:read_clipboard"),
        clipboardWrite = clipboardMode("android:write_clipboard"),
        backgroundRestricted = runCatching { context.getSystemService(ActivityManager::class.java)?.isBackgroundRestricted }.getOrNull(),
        batteryExempt = runCatching { context.getSystemService(PowerManager::class.java)?.isIgnoringBatteryOptimizations(context.packageName) }.getOrNull(),
        biometricCapability = biometricCapability,
        biometricName = biometricName,
    )
}

internal enum class SystemSettingsDestination { APPLICATION, BATTERY, BIOMETRIC }

internal fun openSystemSettings(activity: Activity, destination: SystemSettingsDestination, language: UiLanguage = UiLanguage.CHINESE): Boolean {
    val details = Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS, Uri.fromParts("package", activity.packageName, null))
    val primary = when (destination) {
        SystemSettingsDestination.APPLICATION -> details
        SystemSettingsDestination.BATTERY -> Intent(Settings.ACTION_IGNORE_BATTERY_OPTIMIZATION_SETTINGS)
        SystemSettingsDestination.BIOMETRIC -> Intent(Settings.ACTION_SETTINGS)
    }
    val destinations = if (destination == SystemSettingsDestination.BIOMETRIC) listOf(primary)
        else listOf(primary, details, Intent(Settings.ACTION_SETTINGS))
    for ((index, intent) in destinations.distinctBy { it.action to it.dataString }.withIndex()) {
        try {
            activity.startActivity(intent)
            if (index > 0 && destination != SystemSettingsDestination.BIOMETRIC) android.widget.Toast.makeText(activity,
                localizedResources(activity, language).getString(R.string.find_system_option), android.widget.Toast.LENGTH_SHORT).show()
            return true
        }
        catch (_: android.content.ActivityNotFoundException) { /* 尝试下一公开入口。 */ }
        catch (_: SecurityException) { /* 系统拒绝此入口时保留人工设置路径。 */ }
    }
    return false
}
