package app.cangoo.android.ui

import android.os.SystemClock
import app.cangoo.android.R
import androidx.compose.material3.SnackbarDuration
import androidx.compose.material3.SnackbarHostState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalResources
import kotlinx.coroutines.withTimeoutOrNull

internal class ExitConfirmation {
    var deadline by mutableStateOf<Long?>(null)
        private set

    fun request(now: Long, duration: Long): Boolean {
        if (deadline?.let { now < it } == true) {
            cancel()
            return true
        }
        deadline = now + duration.coerceIn(1L, Long.MAX_VALUE - now)
        return false
    }

    fun cancel(expected: Long? = deadline) {
        if (deadline == expected) deadline = null
    }
}

@Composable
internal fun ExitConfirmationFeedback(confirmation: ExitConfirmation, modifier: Modifier = Modifier) {
    val host = remember { SnackbarHostState() }
    val deadline = confirmation.deadline
    val resources = LocalResources.current
    LaunchedEffect(deadline) {
        if (deadline != null) {
            withTimeoutOrNull((deadline - SystemClock.elapsedRealtime()).coerceAtLeast(0L)) {
                host.showSnackbar(ShortFeedbackVisuals(UiText(R.string.exit_again), resources, SnackbarDuration.Indefinite))
            }
            confirmation.cancel(deadline)
        }
    }
    ShortFeedbackHost(host, modifier)
}
