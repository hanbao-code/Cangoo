"""Qt-independent fail-closed renderer lifecycle state machine.

The controller deliberately does not import the typed Bridge package or
PySide6.
The host supplies a security-boundary port that has already revoked Bridge
authority.  A new renderer may be created only when that synchronous boundary
reports both ``authority_revoked`` and ``complete`` as the literal value
``True``.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
import math
import time
from typing import Protocol

from .diagnostics import (
    DiagnosticEventCode,
    FixedDiagnosticRecorder,
    RendererTerminationStatus,
)


class SecurityBoundaryOutcome(Protocol):
    authority_revoked: bool
    complete: bool


class SecurityBoundaryPort(Protocol):
    def enter_boundary(
        self,
        reason: str,
        *,
        page_epoch: int,
        session_epoch: int,
        page_revoked: bool,
        authority_serial: int,
    ) -> SecurityBoundaryOutcome:
        """Enter the already-revoked native security boundary."""


class RendererLifecycleState(str, Enum):
    NEW = "new"
    STARTING = "starting"
    ACTIVE = "active"
    SECURING = "securing"
    RECOVERY_READY = "recovery_ready"
    RECOVERING = "recovering"
    BLOCKED = "blocked"
    EXITING = "exiting"


class RendererFailureKind(str, Enum):
    TERMINATED = "terminated"
    RESUME_TIMEOUT = "resume_timeout"


class RendererDecision(str, Enum):
    INITIAL_PAGE_REQUIRED = "initial_page_required"
    ACTIVE = "active"
    RECOVERY_AVAILABLE = "recovery_available"
    RECOVERY_PAGE_REQUIRED = "recovery_page_required"
    SECURITY_BOUNDARY_BLOCKED = "security_boundary_blocked"
    CRASH_STORM_BLOCKED = "crash_storm_blocked"
    IGNORED_STALE = "ignored_stale"
    IGNORED_DUPLICATE = "ignored_duplicate"
    IGNORED_EXITING = "ignored_exiting"
    NOT_ALLOWED = "not_allowed"
    EXITING = "exiting"


@dataclass(frozen=True, slots=True)
class RendererTransition:
    previous_state: RendererLifecycleState
    state: RendererLifecycleState
    decision: RendererDecision
    page_generation: int
    boundary_serial: int
    failure_count_in_window: int
    authority_revoked: bool
    security_cleanup_complete: bool

    @property
    def recovery_allowed(self) -> bool:
        return (
            self.state is RendererLifecycleState.RECOVERY_READY
            and self.decision is RendererDecision.RECOVERY_AVAILABLE
            and self.authority_revoked
            and self.security_cleanup_complete
        )

    def to_mapping(self) -> dict[str, object]:
        return {
            "previous_state": self.previous_state.value,
            "state": self.state.value,
            "decision": self.decision.value,
            "page_generation": self.page_generation,
            "boundary_serial": self.boundary_serial,
            "failure_count_in_window": self.failure_count_in_window,
            "authority_revoked": self.authority_revoked,
            "security_cleanup_complete": (
                self.security_cleanup_complete
            ),
            "recovery_allowed": self.recovery_allowed,
        }


class RendererLifecycleController:
    """Own page generation, recovery admission, and crash-storm bounds."""

    MAX_RECOVERY_ATTEMPTS_LIMIT = 8
    MAX_CRASH_WINDOW_SECONDS = 600.0
    MAX_BOUNDARY_SERIAL = (1 << 63) - 1

    def __init__(
        self,
        security_boundary: SecurityBoundaryPort,
        *,
        diagnostics: FixedDiagnosticRecorder | None = None,
        max_recovery_attempts: int = 2,
        crash_window_seconds: float = 60.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if not callable(getattr(security_boundary, "enter_boundary", None)):
            raise TypeError("security boundary port is invalid")
        if (
            type(max_recovery_attempts) is not int
            or not 1
            <= max_recovery_attempts
            <= self.MAX_RECOVERY_ATTEMPTS_LIMIT
        ):
            raise ValueError("recovery attempt limit is outside the bound")
        if (
            not isinstance(crash_window_seconds, (int, float))
            or not math.isfinite(float(crash_window_seconds))
            or not 1.0
            <= float(crash_window_seconds)
            <= self.MAX_CRASH_WINDOW_SECONDS
        ):
            raise ValueError("crash window is outside the bound")
        if not callable(clock):
            raise TypeError("renderer lifecycle clock must be callable")

        self._security_boundary = security_boundary
        self._diagnostics = diagnostics
        self._max_recovery_attempts = max_recovery_attempts
        self._crash_window_seconds = float(crash_window_seconds)
        self._clock = clock
        self._state = RendererLifecycleState.NEW
        self._page_generation = 0
        self._boundary_serial = 0
        self._failure_times: deque[float] = deque(
            maxlen=self.MAX_RECOVERY_ATTEMPTS_LIMIT + 1
        )

    @property
    def state(self) -> RendererLifecycleState:
        return self._state

    @property
    def page_generation(self) -> int:
        return self._page_generation

    @property
    def recovery_attempt_limit(self) -> int:
        return self._max_recovery_attempts

    @property
    def boundary_serial(self) -> int:
        return self._boundary_serial

    def bind_security_boundary(
        self,
        security_boundary: SecurityBoundaryPort,
    ) -> None:
        """Replace the boundary port before any page becomes active.

        M4 uses this one-time hook to route renderer failure through the
        long-lived typed-Bridge authority. M2/M3 retain the coordinator passed
        to ``__init__``. Rebinding later would create competing authorities.
        """

        if self._state is not RendererLifecycleState.STARTING:
            raise RuntimeError(
                "renderer security boundary can only bind while starting"
            )
        if not callable(getattr(security_boundary, "enter_boundary", None)):
            raise TypeError("renderer security boundary port is invalid")
        self._security_boundary = security_boundary

    def reserve_boundary_serial(self) -> int:
        """Allocate the next native-only security transaction identity."""

        if self._boundary_serial >= self.MAX_BOUNDARY_SERIAL:
            raise RuntimeError("security boundary serial is exhausted")
        self._boundary_serial += 1
        return self._boundary_serial

    def start_initial_page(self) -> RendererTransition:
        previous = self._state
        if previous is not RendererLifecycleState.NEW:
            return self._transition(
                previous,
                RendererDecision.NOT_ALLOWED,
            )
        self._page_generation = 1
        self._state = RendererLifecycleState.STARTING
        return self._transition(
            previous,
            RendererDecision.INITIAL_PAGE_REQUIRED,
        )

    def mark_page_ready(self, page_generation: int) -> RendererTransition:
        self._validate_generation(page_generation)
        previous = self._state
        if page_generation != self._page_generation:
            self._record(
                DiagnosticEventCode.RENDERER_STALE_EVENT_IGNORED,
                page_generation=page_generation,
            )
            return self._transition(
                previous,
                RendererDecision.IGNORED_STALE,
            )
        if previous not in {
            RendererLifecycleState.STARTING,
            RendererLifecycleState.RECOVERING,
        }:
            return self._transition(
                previous,
                (
                    RendererDecision.IGNORED_EXITING
                    if previous is RendererLifecycleState.EXITING
                    else RendererDecision.NOT_ALLOWED
                ),
            )
        self._state = RendererLifecycleState.ACTIVE
        if previous is RendererLifecycleState.RECOVERING:
            self._record(
                DiagnosticEventCode.RECOVERY_READY,
                page_generation=page_generation,
            )
        return self._transition(previous, RendererDecision.ACTIVE)

    def handle_termination(
        self,
        page_generation: int,
        status: RendererTerminationStatus,
        exit_code: int,
        *,
        page_epoch: int,
        session_epoch: int,
    ) -> RendererTransition:
        self._validate_generation(page_generation)
        self._validate_epoch(page_epoch)
        self._validate_epoch(session_epoch)
        if not isinstance(status, RendererTerminationStatus):
            raise TypeError("termination status must be a fixed enum")
        if (
            type(exit_code) is not int
            or not -(1 << 31) <= exit_code <= (1 << 31) - 1
        ):
            raise ValueError("renderer exit code is outside int32")

        previous = self._state
        if page_generation != self._page_generation:
            self._record(
                DiagnosticEventCode.RENDERER_STALE_EVENT_IGNORED,
                page_generation=page_generation,
            )
            return self._transition(
                previous,
                RendererDecision.IGNORED_STALE,
            )
        if previous is RendererLifecycleState.EXITING:
            return self._transition(
                previous,
                RendererDecision.IGNORED_EXITING,
            )
        if previous in {
            RendererLifecycleState.SECURING,
            RendererLifecycleState.RECOVERY_READY,
            RendererLifecycleState.BLOCKED,
        }:
            return self._transition(
                previous,
                RendererDecision.IGNORED_DUPLICATE,
            )

        if self._diagnostics is not None:
            self._diagnostics.record_renderer_termination(
                status,
                page_generation=page_generation,
                exit_code=exit_code,
            )
        return self._handle_current_failure(
            previous,
            page_epoch=page_epoch,
            session_epoch=session_epoch,
        )

    def handle_resume_timeout(
        self,
        page_generation: int,
        *,
        page_epoch: int,
        session_epoch: int,
    ) -> RendererTransition:
        self._validate_generation(page_generation)
        self._validate_epoch(page_epoch)
        self._validate_epoch(session_epoch)
        previous = self._state
        if page_generation != self._page_generation:
            self._record(
                DiagnosticEventCode.RENDERER_STALE_EVENT_IGNORED,
                page_generation=page_generation,
            )
            return self._transition(
                previous,
                RendererDecision.IGNORED_STALE,
            )
        if previous is RendererLifecycleState.EXITING:
            return self._transition(
                previous,
                RendererDecision.IGNORED_EXITING,
            )
        if previous in {
            RendererLifecycleState.SECURING,
            RendererLifecycleState.RECOVERY_READY,
            RendererLifecycleState.BLOCKED,
        }:
            return self._transition(
                previous,
                RendererDecision.IGNORED_DUPLICATE,
            )
        self._record(
            DiagnosticEventCode.RENDERER_RESUME_TIMEOUT,
            page_generation=page_generation,
        )
        return self._handle_current_failure(
            previous,
            page_epoch=page_epoch,
            session_epoch=session_epoch,
        )

    def begin_recovery(self) -> RendererTransition:
        previous = self._state
        if previous is not RendererLifecycleState.RECOVERY_READY:
            return self._transition(
                previous,
                (
                    RendererDecision.IGNORED_EXITING
                    if previous is RendererLifecycleState.EXITING
                    else RendererDecision.NOT_ALLOWED
                ),
            )
        self._page_generation += 1
        self._state = RendererLifecycleState.RECOVERING
        self._record(
            DiagnosticEventCode.RECOVERY_STARTED,
            page_generation=self._page_generation,
        )
        return self._transition(
            previous,
            RendererDecision.RECOVERY_PAGE_REQUIRED,
            authority_revoked=True,
            security_cleanup_complete=True,
        )

    def mark_recovery_failed(
        self,
        page_generation: int,
    ) -> RendererTransition:
        self._validate_generation(page_generation)
        previous = self._state
        if page_generation != self._page_generation:
            self._record(
                DiagnosticEventCode.RENDERER_STALE_EVENT_IGNORED,
                page_generation=page_generation,
            )
            return self._transition(
                previous,
                RendererDecision.IGNORED_STALE,
            )
        if previous is RendererLifecycleState.EXITING:
            return self._transition(
                previous,
                RendererDecision.IGNORED_EXITING,
            )
        self._state = RendererLifecycleState.BLOCKED
        self._record(
            DiagnosticEventCode.RECOVERY_FAILED,
            page_generation=page_generation,
        )
        return self._transition(
            previous,
            RendererDecision.SECURITY_BOUNDARY_BLOCKED,
        )

    def begin_exit(self) -> RendererTransition:
        previous = self._state
        self._state = RendererLifecycleState.EXITING
        return self._transition(
            previous,
            RendererDecision.EXITING,
        )

    def _handle_current_failure(
        self,
        previous: RendererLifecycleState,
        *,
        page_epoch: int,
        session_epoch: int,
    ) -> RendererTransition:
        self._state = RendererLifecycleState.SECURING
        failure_count = self._remember_failure()
        authority_serial = self.reserve_boundary_serial()
        authority_revoked = False
        cleanup_complete = False
        try:
            result = self._security_boundary.enter_boundary(
                "renderer_failure",
                page_epoch=page_epoch,
                session_epoch=session_epoch,
                page_revoked=True,
                authority_serial=authority_serial,
            )
            authority_revoked = (
                getattr(result, "authority_revoked", None) is True
            )
            cleanup_complete = getattr(result, "complete", None) is True
        except Exception:
            authority_revoked = False
            cleanup_complete = False

        if not authority_revoked or not cleanup_complete:
            self._state = RendererLifecycleState.BLOCKED
            self._record(
                DiagnosticEventCode.SECURITY_BOUNDARY_BLOCKED,
                page_generation=self._page_generation,
            )
            return self._transition(
                previous,
                RendererDecision.SECURITY_BOUNDARY_BLOCKED,
                failure_count=failure_count,
                authority_revoked=authority_revoked,
                security_cleanup_complete=cleanup_complete,
            )
        if failure_count > self._max_recovery_attempts:
            self._state = RendererLifecycleState.BLOCKED
            self._record(
                DiagnosticEventCode.RECOVERY_CRASH_STORM_BLOCKED,
                page_generation=self._page_generation,
            )
            return self._transition(
                previous,
                RendererDecision.CRASH_STORM_BLOCKED,
                failure_count=failure_count,
                authority_revoked=True,
                security_cleanup_complete=True,
            )

        self._state = RendererLifecycleState.RECOVERY_READY
        self._record(
            DiagnosticEventCode.RECOVERY_AVAILABLE,
            page_generation=self._page_generation,
        )
        return self._transition(
            previous,
            RendererDecision.RECOVERY_AVAILABLE,
            failure_count=failure_count,
            authority_revoked=True,
            security_cleanup_complete=True,
        )

    def _remember_failure(self) -> int:
        now = self._clock()
        if not isinstance(now, (int, float)) or not math.isfinite(float(now)):
            raise ValueError("renderer lifecycle clock returned invalid value")
        current = float(now)
        cutoff = current - self._crash_window_seconds
        while self._failure_times and self._failure_times[0] < cutoff:
            self._failure_times.popleft()
        self._failure_times.append(current)
        return len(self._failure_times)

    def _transition(
        self,
        previous: RendererLifecycleState,
        decision: RendererDecision,
        *,
        failure_count: int | None = None,
        authority_revoked: bool = False,
        security_cleanup_complete: bool = False,
    ) -> RendererTransition:
        return RendererTransition(
            previous_state=previous,
            state=self._state,
            decision=decision,
            page_generation=self._page_generation,
            boundary_serial=self._boundary_serial,
            failure_count_in_window=(
                len(self._failure_times)
                if failure_count is None
                else failure_count
            ),
            authority_revoked=authority_revoked,
            security_cleanup_complete=security_cleanup_complete,
        )

    def _record(
        self,
        code: DiagnosticEventCode,
        *,
        page_generation: int,
    ) -> None:
        if self._diagnostics is not None:
            self._diagnostics.record(
                code,
                page_generation=page_generation,
            )

    @staticmethod
    def _validate_generation(value: int) -> None:
        if type(value) is not int or value <= 0:
            raise ValueError("page generation must be a positive integer")

    @staticmethod
    def _validate_epoch(value: int) -> None:
        if type(value) is not int or value < 0:
            raise ValueError("epoch must be a non-negative integer")

__all__ = [
    "RendererDecision",
    "RendererFailureKind",
    "RendererLifecycleController",
    "RendererLifecycleState",
    "RendererTransition",
    "SecurityBoundaryOutcome",
    "SecurityBoundaryPort",
]
