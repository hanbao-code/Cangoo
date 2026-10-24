"""Fixed, bounded diagnostics and the pre-WebEngine startup policy.

This module is deliberately standard-library-only.  The candidate entry point
must be able to import it and reject an unsafe inherited environment before
PySide6 imports any Qt WebEngine module.

No API in this module accepts console text, source URLs, exception objects, or
other arbitrary diagnostic strings.  Renderer-controlled input is reduced to
fixed enums and bounded integers at the call site.
"""

from __future__ import annotations

from collections import Counter, deque
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
import math
import os
from threading import RLock
import time


STARTUP_REFUSAL_EXIT_CODE = 78


class StartupBlockReason(str, Enum):
    """启动失败的封闭原因；值只允许作为固定诊断码。"""

    PREINITIALIZED_WEBENGINE = "PREINITIALIZED_WEBENGINE"
    UNSAFE_CONFIGURATION = "UNSAFE_CONFIGURATION"
    UNSUPPORTED_ARGUMENT = "UNSUPPORTED_ARGUMENT"
    WINDOWS_ERROR_POLICY = "WINDOWS_ERROR_POLICY"
    RUNTIME_PATHS = "RUNTIME_PATHS"
    HOST_INITIALIZATION = "HOST_INITIALIZATION"
    INSTALLATION_INCOMPLETE = "INSTALLATION_INCOMPLETE"


class ConsoleLevel(str, Enum):
    """The only console metadata retained by the native host."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class RendererTerminationStatus(str, Enum):
    """Qt-independent normalization of renderer termination states."""

    NORMAL = "normal"
    ABNORMAL = "abnormal"
    CRASHED = "crashed"
    KILLED = "killed"


class DiagnosticEventCode(str, Enum):
    """Closed diagnostic vocabulary; values contain no renderer text."""

    CONSOLE_INFO = "console_info"
    CONSOLE_WARNING = "console_warning"
    CONSOLE_ERROR = "console_error"
    RENDERER_TERMINATED_NORMAL = "renderer_terminated_normal"
    RENDERER_TERMINATED_ABNORMAL = "renderer_terminated_abnormal"
    RENDERER_TERMINATED_CRASHED = "renderer_terminated_crashed"
    RENDERER_TERMINATED_KILLED = "renderer_terminated_killed"
    RENDERER_RESUME_TIMEOUT = "renderer_resume_timeout"
    RENDERER_STALE_EVENT_IGNORED = "renderer_stale_event_ignored"
    SECURITY_BOUNDARY_BLOCKED = "security_boundary_blocked"
    RECOVERY_AVAILABLE = "recovery_available"
    RECOVERY_STARTED = "recovery_started"
    RECOVERY_READY = "recovery_ready"
    RECOVERY_FAILED = "recovery_failed"
    RECOVERY_CRASH_STORM_BLOCKED = "recovery_crash_storm_blocked"
    STARTUP_POLICY_REJECTED = "startup_policy_rejected"
    WINDOWS_ERROR_POLICY_APPLIED = "windows_error_policy_applied"
    WINDOWS_ERROR_POLICY_PARTIAL = "windows_error_policy_partial"


_CONSOLE_EVENTS = {
    ConsoleLevel.INFO: DiagnosticEventCode.CONSOLE_INFO,
    ConsoleLevel.WARNING: DiagnosticEventCode.CONSOLE_WARNING,
    ConsoleLevel.ERROR: DiagnosticEventCode.CONSOLE_ERROR,
}

_TERMINATION_EVENTS = {
    RendererTerminationStatus.NORMAL: (
        DiagnosticEventCode.RENDERER_TERMINATED_NORMAL
    ),
    RendererTerminationStatus.ABNORMAL: (
        DiagnosticEventCode.RENDERER_TERMINATED_ABNORMAL
    ),
    RendererTerminationStatus.CRASHED: (
        DiagnosticEventCode.RENDERER_TERMINATED_CRASHED
    ),
    RendererTerminationStatus.KILLED: (
        DiagnosticEventCode.RENDERER_TERMINATED_KILLED
    ),
}

_MAX_GENERATION = (1 << 63) - 1
_MAX_COUNTER = (1 << 63) - 1
_MIN_EXIT_CODE = -(1 << 31)
_MAX_EXIT_CODE = (1 << 31) - 1


@dataclass(frozen=True, slots=True)
class DiagnosticEvent:
    """One safe event containing only fixed or bounded scalar metadata."""

    sequence: int
    timestamp_ms_utc: int
    code: DiagnosticEventCode
    page_generation: int
    termination_status: RendererTerminationStatus | None = None
    exit_code: int | None = None

    def to_mapping(self) -> dict[str, object]:
        return {
            "sequence": self.sequence,
            "timestamp_ms_utc": self.timestamp_ms_utc,
            "code": self.code.value,
            "page_generation": self.page_generation,
            "termination_status": (
                self.termination_status.value
                if self.termination_status is not None
                else None
            ),
            "exit_code": self.exit_code,
        }


@dataclass(frozen=True, slots=True)
class DiagnosticSnapshot:
    """Immutable bounded snapshot suitable for a redacted support report."""

    capacity: int
    dropped_events: int
    events: tuple[DiagnosticEvent, ...]
    counts: tuple[tuple[DiagnosticEventCode, int], ...]

    def to_mapping(self) -> dict[str, object]:
        return {
            "capacity": self.capacity,
            "stored_event_count": len(self.events),
            "dropped_event_count": self.dropped_events,
            "events": [event.to_mapping() for event in self.events],
            "counts": {
                code.value: count
                for code, count in self.counts
            },
        }


class FixedDiagnosticRecorder:
    """Thread-safe fixed-event recorder with an explicit memory bound."""

    DEFAULT_CAPACITY = 64
    MAX_CAPACITY = 256

    def __init__(
        self,
        capacity: int = DEFAULT_CAPACITY,
        *,
        clock: Callable[[], float] = time.time,
    ) -> None:
        if type(capacity) is not int or not 1 <= capacity <= self.MAX_CAPACITY:
            raise ValueError("diagnostic capacity is outside the fixed bound")
        if not callable(clock):
            raise TypeError("diagnostic clock must be callable")
        self._capacity = capacity
        self._clock = clock
        self._events: deque[DiagnosticEvent] = deque(maxlen=capacity)
        self._counts: Counter[DiagnosticEventCode] = Counter()
        self._next_sequence = 1
        self._dropped_events = 0
        self._lock = RLock()

    @property
    def capacity(self) -> int:
        return self._capacity

    def record(
        self,
        code: DiagnosticEventCode,
        *,
        page_generation: int = 0,
        termination_status: RendererTerminationStatus | None = None,
        exit_code: int | None = None,
    ) -> DiagnosticEvent:
        """Record only the closed schema; there is no arbitrary-text field."""

        if not isinstance(code, DiagnosticEventCode):
            raise TypeError("diagnostic code must be a fixed enum")
        if (
            type(page_generation) is not int
            or not 0 <= page_generation <= _MAX_GENERATION
        ):
            raise ValueError("page generation is outside the fixed bound")
        if (
            termination_status is not None
            and not isinstance(
                termination_status,
                RendererTerminationStatus,
            )
        ):
            raise TypeError("termination status must be a fixed enum")
        if exit_code is not None and (
            type(exit_code) is not int
            or not _MIN_EXIT_CODE <= exit_code <= _MAX_EXIT_CODE
        ):
            raise ValueError("renderer exit code is outside int32")

        timestamp = self._clock()
        if not isinstance(timestamp, (int, float)) or not math.isfinite(
            float(timestamp)
        ):
            raise ValueError("diagnostic clock returned an invalid value")
        timestamp_ms = min(
            _MAX_COUNTER,
            max(0, int(float(timestamp) * 1000)),
        )

        with self._lock:
            event = DiagnosticEvent(
                sequence=self._next_sequence,
                timestamp_ms_utc=timestamp_ms,
                code=code,
                page_generation=page_generation,
                termination_status=termination_status,
                exit_code=exit_code,
            )
            self._next_sequence = min(
                _MAX_COUNTER,
                self._next_sequence + 1,
            )
            if len(self._events) == self._capacity:
                self._dropped_events = min(
                    _MAX_COUNTER,
                    self._dropped_events + 1,
                )
            self._events.append(event)
            self._counts[code] = min(
                _MAX_COUNTER,
                self._counts[code] + 1,
            )
            return event

    def record_console(
        self,
        level: ConsoleLevel,
        *,
        page_generation: int = 0,
    ) -> DiagnosticEvent:
        """Reduce a console callback to its severity before recording."""

        if not isinstance(level, ConsoleLevel):
            raise TypeError("console level must be a fixed enum")
        return self.record(
            _CONSOLE_EVENTS[level],
            page_generation=page_generation,
        )

    def record_renderer_termination(
        self,
        status: RendererTerminationStatus,
        *,
        page_generation: int,
        exit_code: int,
    ) -> DiagnosticEvent:
        if not isinstance(status, RendererTerminationStatus):
            raise TypeError("termination status must be a fixed enum")
        return self.record(
            _TERMINATION_EVENTS[status],
            page_generation=page_generation,
            termination_status=status,
            exit_code=exit_code,
        )

    def snapshot(self) -> DiagnosticSnapshot:
        with self._lock:
            counts = tuple(
                (code, self._counts[code])
                for code in DiagnosticEventCode
                if self._counts[code]
            )
            return DiagnosticSnapshot(
                capacity=self._capacity,
                dropped_events=self._dropped_events,
                events=tuple(self._events),
                counts=counts,
            )


class StartupPolicyViolation(str, Enum):
    """Fixed reasons for rejecting an unsafe inherited startup surface."""

    REMOTE_DEBUGGING_ENVIRONMENT = "remote_debugging_environment"
    CHROMIUM_FLAGS_ENVIRONMENT = "chromium_flags_environment"
    SANDBOX_OVERRIDE_ENVIRONMENT = "sandbox_override_environment"
    CHROMIUM_LOGGING_ENVIRONMENT = "chromium_logging_environment"
    HELPER_PATH_OVERRIDE_ENVIRONMENT = "helper_path_override_environment"
    RESOURCE_PATH_OVERRIDE_ENVIRONMENT = "resource_path_override_environment"
    WEBENGINE_ARGUMENT_PASSTHROUGH = "webengine_argument_passthrough"
    REMOTE_DEBUGGING_ARGUMENT = "remote_debugging_argument"
    CHROMIUM_LOGGING_ARGUMENT = "chromium_logging_argument"
    SANDBOX_OVERRIDE_ARGUMENT = "sandbox_override_argument"
    HELPER_RESOURCE_OVERRIDE_ARGUMENT = "helper_resource_override_argument"


_ENVIRONMENT_POLICIES: tuple[tuple[str, StartupPolicyViolation], ...] = (
    (
        "QTWEBENGINE_REMOTE_DEBUGGING",
        StartupPolicyViolation.REMOTE_DEBUGGING_ENVIRONMENT,
    ),
    (
        "QTWEBENGINE_CHROMIUM_FLAGS",
        StartupPolicyViolation.CHROMIUM_FLAGS_ENVIRONMENT,
    ),
    (
        "QTWEBENGINE_DISABLE_SANDBOX",
        StartupPolicyViolation.SANDBOX_OVERRIDE_ENVIRONMENT,
    ),
    (
        "QT_LOGGING_RULES",
        StartupPolicyViolation.CHROMIUM_LOGGING_ENVIRONMENT,
    ),
    (
        "CHROME_LOG_FILE",
        StartupPolicyViolation.CHROMIUM_LOGGING_ENVIRONMENT,
    ),
    (
        "QTWEBENGINEPROCESS_PATH",
        StartupPolicyViolation.HELPER_PATH_OVERRIDE_ENVIRONMENT,
    ),
    (
        "QTWEBENGINE_RESOURCES_PATH",
        StartupPolicyViolation.RESOURCE_PATH_OVERRIDE_ENVIRONMENT,
    ),
    (
        "QTWEBENGINE_LOCALES_PATH",
        StartupPolicyViolation.RESOURCE_PATH_OVERRIDE_ENVIRONMENT,
    ),
    (
        "QTWEBENGINE_DICTIONARIES_PATH",
        StartupPolicyViolation.RESOURCE_PATH_OVERRIDE_ENVIRONMENT,
    ),
)

_REMOTE_DEBUG_ARGUMENTS = (
    "--remote-debugging-port",
    "--remote-debugging-pipe",
    "--remote-allow-origins",
    "--auto-open-devtools-for-tabs",
)
_CHROMIUM_LOG_ARGUMENTS = (
    "--enable-logging",
    "--log-file",
    "--log-level",
    "--v=",
    "--vmodule",
    "--trace-startup",
    "--crash-dumps-dir",
)
_SANDBOX_ARGUMENTS = (
    "--no-sandbox",
    "--disable-gpu-sandbox",
    "--disable-setuid-sandbox",
    "--single-process",
)
_HELPER_RESOURCE_ARGUMENTS = (
    "--browser-subprocess-path",
    "--webengine-resources-path",
    "--webengine-locales-path",
    "--resources-dir-path",
)


def webengine_startup_environment_keys() -> tuple[str, ...]:
    """返回启动审计使用的固定环境键名，不读取或返回对应值。"""

    return tuple(key for key, _violation in _ENVIRONMENT_POLICIES)


@dataclass(frozen=True, slots=True)
class StartupPolicyResult:
    """Redacted result: violations name fixed classes, never input values."""

    allowed: bool
    violations: tuple[StartupPolicyViolation, ...]

    def to_mapping(self) -> dict[str, object]:
        return {
            "allowed": self.allowed,
            "violations": [
                violation.value for violation in self.violations
            ],
        }


class UnsafeWebEngineConfiguration(RuntimeError):
    """Fixed-message failure raised before any Qt WebEngine import."""

    def __init__(
        self,
        violations: tuple[StartupPolicyViolation, ...],
    ) -> None:
        super().__init__("unsafe WebEngine startup configuration")
        self.violations = violations


def audit_webengine_startup(
    *,
    environ: Mapping[str, str] | None = None,
    argv: Sequence[str] | None = None,
) -> StartupPolicyResult:
    """Classify unsafe startup controls without retaining their values."""

    environment = os.environ if environ is None else environ
    arguments = tuple(os.sys.argv if argv is None else argv)
    found: set[StartupPolicyViolation] = set()

    for key, violation in _ENVIRONMENT_POLICIES:
        if key == "QTWEBENGINE_DISABLE_SANDBOX":
            if key in environment:
                found.add(violation)
            continue
        value = environment.get(key)
        if value is not None and str(value).strip():
            found.add(violation)

    for argument in arguments[1:]:
        if not isinstance(argument, str):
            found.add(StartupPolicyViolation.WEBENGINE_ARGUMENT_PASSTHROUGH)
            continue
        lowered = argument.strip().lower()
        if (
            lowered == "--webengineargs"
            or lowered.startswith("--webengineargs=")
        ):
            found.add(StartupPolicyViolation.WEBENGINE_ARGUMENT_PASSTHROUGH)
        if any(
            lowered == prefix or lowered.startswith(prefix + "=")
            for prefix in _REMOTE_DEBUG_ARGUMENTS
        ):
            found.add(StartupPolicyViolation.REMOTE_DEBUGGING_ARGUMENT)
        if any(
            lowered == prefix
            or lowered.startswith(prefix + "=")
            or lowered.startswith(prefix)
            for prefix in _CHROMIUM_LOG_ARGUMENTS
        ):
            found.add(StartupPolicyViolation.CHROMIUM_LOGGING_ARGUMENT)
        if any(
            lowered == prefix or lowered.startswith(prefix + "=")
            for prefix in _SANDBOX_ARGUMENTS
        ):
            found.add(StartupPolicyViolation.SANDBOX_OVERRIDE_ARGUMENT)
        if any(
            lowered == prefix or lowered.startswith(prefix + "=")
            for prefix in _HELPER_RESOURCE_ARGUMENTS
        ):
            found.add(
                StartupPolicyViolation.HELPER_RESOURCE_OVERRIDE_ARGUMENT
            )

    violations = tuple(
        violation
        for violation in StartupPolicyViolation
        if violation in found
    )
    return StartupPolicyResult(
        allowed=not violations,
        violations=violations,
    )


def enforce_webengine_startup_policy(
    *,
    environ: Mapping[str, str] | None = None,
    argv: Sequence[str] | None = None,
) -> StartupPolicyResult:
    """Fail closed with a fixed message before Qt WebEngine initialization."""

    result = audit_webengine_startup(environ=environ, argv=argv)
    if not result.allowed:
        raise UnsafeWebEngineConfiguration(result.violations)
    return result


__all__ = [
    "ConsoleLevel",
    "DiagnosticEvent",
    "DiagnosticEventCode",
    "DiagnosticSnapshot",
    "FixedDiagnosticRecorder",
    "RendererTerminationStatus",
    "STARTUP_REFUSAL_EXIT_CODE",
    "StartupBlockReason",
    "StartupPolicyResult",
    "StartupPolicyViolation",
    "UnsafeWebEngineConfiguration",
    "audit_webengine_startup",
    "enforce_webengine_startup_policy",
    "webengine_startup_environment_keys",
]
