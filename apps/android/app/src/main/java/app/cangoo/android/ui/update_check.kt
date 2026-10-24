package app.cangoo.android.ui

import android.app.Activity
import android.content.ActivityNotFoundException
import android.content.Context
import android.content.Intent
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.core.net.toUri
import app.cangoo.android.BuildConfig
import app.cangoo.android.data.GitHubReleaseTransport
import app.cangoo.android.data.PublicRelease
import app.cangoo.android.data.ReleaseRequest
import app.cangoo.android.data.ReleaseCheckException
import app.cangoo.android.data.ReleaseTransport
import app.cangoo.android.data.publicVersionCompare
import app.cangoo.android.data.releasePageUrl
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Job
import kotlinx.coroutines.ensureActive
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import kotlinx.coroutines.Dispatchers
import kotlin.coroutines.coroutineContext

internal enum class UpdateCheckStatus { IDLE, AVAILABLE, CURRENT, NO_RELEASE, FAILED }
internal enum class UpdateCheckFailure { SETTINGS, REGISTRATION, QUERY, SAVE, SAVE_UNKNOWN }

internal data class UpdateCheckPolicy(val enabled: Boolean, val intervalDays: Int)

internal data class UpdateCheckUiState(
    val enabled: Boolean = true,
    val intervalDays: Int = 1,
    val pendingPolicy: UpdateCheckPolicy? = null,
    val settingsReady: Boolean = false,
    val saving: Boolean = false,
    val checking: Boolean = false,
    val status: UpdateCheckStatus = UpdateCheckStatus.IDLE,
    val lastAttemptMillis: Long? = null,
    val release: PublicRelease? = null,
    val checkedAtMillis: Long? = null,
    val failure: UpdateCheckFailure? = null,
    val automaticPrompt: Boolean = false,
)

internal class UpdateCheckController(
    private val store: UpdateCheckStore,
    private val scope: CoroutineScope,
    private val transport: ReleaseTransport = GitHubReleaseTransport(),
    val currentVersion: String = BuildConfig.VERSION_NAME,
    val isDevelopment: Boolean = BuildConfig.DEBUG || BuildConfig.APPLICATION_ID != "app.cangoo.android" ||
        publicVersionCompare(currentVersion, currentVersion) == null,
    private val architecture: String = BuildConfig.FLAVOR,
    private val clock: () -> Long = System::currentTimeMillis,
) {
    constructor(context: Context, scope: CoroutineScope) : this(UpdateCheckStore(context), scope)

    var state by mutableStateOf(UpdateCheckUiState())
        private set
    private var started = false
    @Volatile private var closed = false
    @Volatile private var run = 0L
    private var settingsJob: Job? = null
    private var queryJob: Job? = null
    private val cancelledJobs = mutableListOf<Job>()
    private var request: ReleaseRequest? = null
    private var manualRequested = false
    private var pendingManualCheck = false
    private var queuedPolicy: PolicyPatch? = null

    private data class PolicyPatch(val enabled: Boolean?, val intervalDays: Int?)

    fun start() {
        if (started || closed) return
        started = true
        loadSettings(automatic = true)
    }

    fun retrySettings() { if (!closed) loadSettings(automatic = false) }

    private fun loadSettings(automatic: Boolean) {
        if (settingsJob?.isActive == true || queryJob?.isActive == true) return
        state = state.copy(saving = true)
        settingsJob = scope.launch {
            var loaded = false
            try {
                val saved = withContext(Dispatchers.IO) { store.read() }
                if (!closed) {
                    val cachedAt = saved.checkedAtMillis.takeIf { saved.checkedArchitecture == architecture }
                    val cachedRelease = saved.release.takeIf { cachedAt != null }
                    state = state.copy(enabled = saved.enabled, intervalDays = saved.intervalDays, settingsReady = true,
                        lastAttemptMillis = saved.lastAttemptMillis, release = cachedRelease, checkedAtMillis = cachedAt,
                        status = resultStatus(cachedRelease, cachedAt), failure = null)
                    loaded = true
                }
            } catch (cancelled: CancellationException) { throw cancelled }
            catch (_: Exception) {
                if (!closed) state = state.copy(settingsReady = false, status = UpdateCheckStatus.FAILED, failure = UpdateCheckFailure.SETTINGS)
            } finally { if (!closed) state = state.copy(saving = false) }
            if (loaded && automatic) check(manual = false)
        }
    }

    fun checkManually() { check(manual = true) }

    private fun check(manual: Boolean) {
        if (closed || !state.settingsReady) return
        if (state.saving) {
            if (manual && state.pendingPolicy != null) {
                if (queryJob?.isActive == true) manualRequested = true
                else {
                    pendingManualCheck = true
                    state = state.copy(checking = true, automaticPrompt = false)
                }
            }
            return
        }
        if (queryJob?.isActive == true) {
            if (manual) manualRequested = true
            return
        }
        if (!manual && !state.enabled) return
        val serial = ++run
        val activeRequest = ReleaseRequest()
        request = activeRequest
        manualRequested = manual
        state = state.copy(checking = true, failure = null, automaticPrompt = false)
        queryJob = scope.launch {
            var failure = UpdateCheckFailure.REGISTRATION
            try {
                var attempt = withContext(Dispatchers.IO) { store.claimAttempt(clock(), manual) }
                if (attempt == null && current(serial) && manualRequested)
                    attempt = withContext(Dispatchers.IO) { store.claimAttempt(clock(), manual = true) }
                val claimed = attempt ?: return@launch
                if (!current(serial)) return@launch
                state = state.copy(lastAttemptMillis = claimed.lastAttemptMillis)
                failure = UpdateCheckFailure.QUERY
                val release = withContext(Dispatchers.IO) { transport.fetch(architecture, activeRequest) }
                coroutineContext.ensureActive()
                if (!current(serial)) return@launch
                failure = UpdateCheckFailure.SAVE
                val checkedAt = clock()
                val saved = withContext(Dispatchers.IO) {
                    store.completeAttempt(requireNotNull(claimed.attemptId), checkedAt, release, architecture) { current(serial) }
                }
                if (saved == null) {
                    if (current(serial)) state = state.copy(status = UpdateCheckStatus.FAILED, failure = UpdateCheckFailure.QUERY)
                    return@launch
                }
                if (!current(serial)) return@launch
                val status = resultStatus(saved.release, saved.checkedAtMillis)
                state = state.copy(release = saved.release, checkedAtMillis = saved.checkedAtMillis,
                    status = status, failure = null, automaticPrompt = !manualRequested && saved.enabled &&
                        status == UpdateCheckStatus.AVAILABLE && release != null && !saved.suppresses(release.version, checkedAt))
            } catch (cancelled: CancellationException) { throw cancelled }
            catch (error: Exception) {
                if (current(serial)) {
                    if (error is UpdateCheckWriteException && error.outcomeUnverified) invalidateSettings()
                    else state = state.copy(status = UpdateCheckStatus.FAILED, failure = failure,
                        settingsReady = state.settingsReady && failure != UpdateCheckFailure.REGISTRATION, automaticPrompt = false)
                }
            } finally {
                activeRequest.cancel()
                if (current(serial)) {
                    queryJob = null
                    request = null
                    state = state.copy(checking = false)
                }
            }
        }
    }

    fun saveSettings(enabled: Boolean? = null, intervalDays: Int? = null) {
        if (closed || !state.settingsReady || state.saving && state.pendingPolicy == null ||
            intervalDays != null && intervalDays <= 0 || enabled == null && intervalDays == null) return
        val writing = state.pendingPolicy != null
        val intent = state.pendingPolicy ?: UpdateCheckPolicy(state.enabled, state.intervalDays)
        val queued = queuedPolicy
        queuedPolicy = PolicyPatch(enabled ?: queued?.enabled, intervalDays ?: queued?.intervalDays)
        state = state.copy(saving = true, pendingPolicy = UpdateCheckPolicy(enabled ?: intent.enabled, intervalDays ?: intent.intervalDays))
        if (writing) return
        settingsJob = scope.launch {
            var completed = false
            try {
                while (!closed && state.settingsReady) {
                    val patch = queuedPolicy ?: break
                    queuedPolicy = null
                    val saved = withContext(Dispatchers.IO) {
                        store.update { latest -> latest.copy(enabled = patch.enabled ?: latest.enabled,
                            intervalDays = patch.intervalDays ?: latest.intervalDays) }
                    }
                    if (closed || !state.settingsReady) break
                    val next = queuedPolicy
                    val pending = UpdateCheckPolicy(next?.enabled ?: saved.enabled, next?.intervalDays ?: saved.intervalDays)
                    state = state.copy(enabled = saved.enabled, intervalDays = saved.intervalDays, pendingPolicy = pending,
                        failure = null, automaticPrompt = state.automaticPrompt && pending.enabled)
                }
                completed = !closed && state.settingsReady
            } catch (cancelled: CancellationException) { throw cancelled }
            catch (error: Exception) {
                if (!closed) {
                    if (error is UpdateCheckWriteException && error.outcomeUnverified) invalidateSettings()
                    else state = state.copy(failure = UpdateCheckFailure.SAVE)
                }
            } finally {
                val manual = completed && pendingManualCheck
                queuedPolicy = null
                pendingManualCheck = false
                if (!closed) {
                    state = state.copy(saving = false, pendingPolicy = null, checking = queryJob?.isActive == true)
                    if (!state.enabled && !manualRequested && !manual) cancelQuery()
                    if (manual) check(manual = true)
                }
            }
        }
    }

    fun ignoreVersion(forever: Boolean) {
        val release = state.release ?: return
        if (closed || !state.settingsReady || state.saving || state.checking) return
        state = state.copy(saving = true)
        settingsJob = scope.launch {
            try {
                val until = if (forever) 0L else Math.addExact(clock(), 7 * 86_400_000L)
                withContext(Dispatchers.IO) { store.update { it.copy(ignoredVersions = it.ignoredVersions + (release.version to until)) } }
                if (!closed) state = state.copy(automaticPrompt = false, failure = null)
            } catch (cancelled: CancellationException) { throw cancelled }
            catch (error: Exception) {
                if (!closed) {
                    if (error is UpdateCheckWriteException && error.outcomeUnverified) invalidateSettings()
                    else state = state.copy(failure = UpdateCheckFailure.SAVE)
                }
            }
            finally { if (!closed) state = state.copy(saving = false) }
        }
    }

    fun dismissPrompt() { if (!closed) state = state.copy(automaticPrompt = false) }

    fun currentReleaseForOpen(): PublicRelease? = if (closed) null else state.release

    fun close() {
        if (closed) return
        closed = true
        queuedPolicy = null
        pendingManualCheck = false
        cancelQuery()
        settingsJob?.let { if (!it.isCompleted) cancelledJobs.add(it); it.cancel() }
        settingsJob = null
        state = state.copy(checking = false, saving = false, pendingPolicy = null, automaticPrompt = false)
    }

    internal suspend fun awaitClosed() {
        kotlin.check(closed)
        cancelledJobs.toList().forEach { it.join() }
    }

    private fun cancelQuery() {
        run++
        request?.cancel()
        request = null
        cancelledJobs.removeAll { it.isCompleted }
        queryJob?.let { if (!it.isCompleted) cancelledJobs.add(it); it.cancel() }
        queryJob = null
        state = state.copy(checking = false, automaticPrompt = false)
    }

    private fun invalidateSettings() {
        queuedPolicy = null
        pendingManualCheck = false
        cancelQuery()
        state = state.copy(settingsReady = false, pendingPolicy = null, status = UpdateCheckStatus.FAILED, failure = UpdateCheckFailure.SAVE_UNKNOWN)
    }

    private fun current(serial: Long): Boolean = !closed && serial == run

    private fun resultStatus(release: PublicRelease?, checkedAt: Long?): UpdateCheckStatus = when {
        checkedAt == null -> UpdateCheckStatus.IDLE
        release == null -> UpdateCheckStatus.NO_RELEASE
        isDevelopment || publicVersionCompare(release.version, currentVersion)?.let { it > 0 } == true -> UpdateCheckStatus.AVAILABLE
        else -> UpdateCheckStatus.CURRENT
    }
}

internal fun openReleasePage(activity: Activity, release: PublicRelease): Boolean = try {
    activity.startActivity(Intent(Intent.ACTION_VIEW, releasePageUrl(release).toUri()))
    true
} catch (_: ActivityNotFoundException) { false }
catch (_: SecurityException) { false }
catch (_: IllegalArgumentException) { false }
catch (_: ReleaseCheckException) { false }
