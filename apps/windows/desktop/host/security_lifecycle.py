"""Single native coordinator for fail-closed security boundaries.

The typed Bridge owns request authorization.  This module is the native
side-effect coordinator invoked *after* that authority has synchronously been
revoked and before an adapter can release its session.  It intentionally has
no dependency on a database, configuration, clipboard implementation, or
renderer so M3 can verify the ordering with injected public-state callbacks.
"""

from __future__ import annotations

from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum, IntEnum
import re


_STEP_NAME = re.compile(r"^[a-z][a-z0-9_.]{0,63}$")


class SecurityBoundaryReason(str, Enum):
    """Fixed native reasons; renderer text can never select one."""

    MANUAL_LOCK = "manual_lock"
    AUTO_LOCK = "auto_lock"
    SUSPEND_LOCK = "suspend_lock"
    SWITCH_DATABASE = "switch_database"
    CHANGE_KEY_FAILED = "change_key_failed"
    CHANGE_KEY_RESTORED = "change_key_restored"
    CHANGE_KEY_SUCCESS = "change_key_success"
    PAGE_INVALIDATED = "page_invalidated"
    SESSION_INVALIDATED = "session_invalidated"
    RENDERER_FAILURE = "renderer_failure"
    BRIDGE_CLOSE = "bridge_close"
    BRIDGE_DESTROYED = "bridge_destroyed"
    EXIT = "exit"


class SecurityCleanupPhase(IntEnum):
    """Mandatory synchronous order after request authority is gone."""

    STOP_ACTIVITY = 10
    CONCEAL_RENDERER = 20
    CLEAR_NATIVE_SECRETS = 30
    CLEAR_CLIPBOARD = 40
    RELEASE_SESSION = 50


@dataclass(frozen=True, slots=True)
class SecurityBoundaryContext:
    reason: SecurityBoundaryReason
    authority_serial: int
    page_epoch: int
    session_epoch: int
    page_revoked: bool

    @property
    def boundary_key(self) -> tuple[str, int, int, int, bool]:
        return (
            self.reason.value,
            self.authority_serial,
            self.page_epoch,
            self.session_epoch,
            self.page_revoked,
        )


@dataclass(frozen=True, slots=True)
class SecurityBoundaryResult:
    reason: str
    authority_serial: int
    page_epoch: int
    session_epoch: int
    page_revoked: bool
    attempted: tuple[str, ...]
    failed: tuple[str, ...]
    authority_revoked: bool
    complete: bool


SecurityStep = Callable[[SecurityBoundaryContext], object]


class SecurityBoundaryCoordinator:
    """Repeatable, idempotent, exception-isolated native cleanup owner.

    ``RequestBoundary`` remains the sole request authority.  It calls
    :meth:`enter_boundary` only after setting the active page/session epoch to
    zero, so callbacks cannot accidentally restore access even when one fails.
    Results are retained in a small bounded tombstone cache solely to make a
    duplicate native notification idempotent.  The strictly increasing
    authority serial distinguishes boundaries that occur before a page has
    obtained a non-zero epoch.
    """

    _RESULT_CACHE_ITEMS = 32

    def __init__(self) -> None:
        self._steps: list[
            tuple[SecurityCleanupPhase, str, SecurityStep]
        ] = []
        self._results: OrderedDict[
            tuple[str, int, int, int, bool],
            SecurityBoundaryResult,
        ] = OrderedDict()
        self._active_key: tuple[str, int, int, int, bool] | None = None
        self._last_result: SecurityBoundaryResult | None = None
        self._highest_authority_serial = 0
        self._sealed = False

    @property
    def last_result(self) -> SecurityBoundaryResult | None:
        return self._last_result

    @property
    def highest_authority_serial(self) -> int:
        return self._highest_authority_serial

    @property
    def cached_result_count(self) -> int:
        return len(self._results)

    def register(
        self,
        phase: SecurityCleanupPhase,
        name: str,
        callback: SecurityStep,
    ) -> None:
        if self._sealed:
            raise RuntimeError("security cleanup registration is sealed")
        if (
            type(name) is not str
            or _STEP_NAME.fullmatch(name) is None
            or any(existing == name for _, existing, _ in self._steps)
        ):
            raise ValueError("security step name is invalid or duplicated")
        if not callable(callback):
            raise TypeError("security cleanup callback must be callable")
        self._steps.append((SecurityCleanupPhase(phase), name, callback))

    def enter_boundary(
        self,
        reason: str,
        *,
        authority_serial: int,
        page_epoch: int,
        session_epoch: int,
        page_revoked: bool,
    ) -> SecurityBoundaryResult:
        """Run the one native transaction for a revoked authorization epoch."""

        if (
            type(authority_serial) is not int
            or authority_serial <= 0
            or type(page_epoch) is not int
            or page_epoch < 0
            or type(session_epoch) is not int
            or session_epoch < 0
            or type(page_revoked) is not bool
        ):
            raise ValueError("invalid native security-boundary identity")
        context = SecurityBoundaryContext(
            reason=SecurityBoundaryReason(reason),
            authority_serial=authority_serial,
            page_epoch=page_epoch,
            session_epoch=session_epoch,
            page_revoked=page_revoked,
        )
        key = context.boundary_key
        previous = self._results.get(key)
        if previous is not None:
            self._results.move_to_end(key)
            self._last_result = previous
            return previous
        if self._active_key is not None:
            # Cleanup callbacks must never interleave another native
            # transaction. Authority is already gone, so an explicit
            # incomplete result keeps all recovery fail-closed.
            return SecurityBoundaryResult(
                reason=context.reason.value,
                authority_serial=context.authority_serial,
                page_epoch=context.page_epoch,
                session_epoch=context.session_epoch,
                page_revoked=context.page_revoked,
                attempted=(),
                failed=("reentrant_boundary",),
                authority_revoked=True,
                complete=False,
            )
        if authority_serial <= self._highest_authority_serial:
            raise ValueError(
                "authority serial must strictly increase"
            )

        self._sealed = True
        self._highest_authority_serial = authority_serial
        self._active_key = key
        attempted: list[str] = []
        failed: list[str] = []
        try:
            for _phase, name, callback in sorted(
                self._steps,
                key=lambda item: (item[0], item[1]),
            ):
                attempted.append(name)
                try:
                    callback(context)
                except Exception:
                    failed.append(name)
            result = SecurityBoundaryResult(
                reason=context.reason.value,
                authority_serial=context.authority_serial,
                page_epoch=context.page_epoch,
                session_epoch=context.session_epoch,
                page_revoked=context.page_revoked,
                attempted=tuple(attempted),
                failed=tuple(failed),
                authority_revoked=True,
                complete=not failed,
            )
            self._results[key] = result
            self._results.move_to_end(key)
            while len(self._results) > self._RESULT_CACHE_ITEMS:
                self._results.popitem(last=False)
            self._last_result = result
            return result
        finally:
            self._active_key = None

    def page_authorized(self, page_epoch: int) -> None:
        """Observer hook; request authority remains in ``RequestBoundary``."""

        if type(page_epoch) is not int or page_epoch <= 0:
            raise ValueError("page epoch must be a positive integer")

    def session_authorized(self, session_epoch: int) -> None:
        """Observer hook; native activities may be attached in M4."""

        if type(session_epoch) is not int or session_epoch <= 0:
            raise ValueError("session epoch must be a positive integer")


__all__ = [
    "SecurityBoundaryContext",
    "SecurityBoundaryCoordinator",
    "SecurityBoundaryReason",
    "SecurityBoundaryResult",
    "SecurityCleanupPhase",
]
