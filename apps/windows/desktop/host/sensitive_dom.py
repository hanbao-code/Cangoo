"""Best-effort DOM cleanup commands with no secret values in native scripts."""

from __future__ import annotations

import json
import re
from typing import Protocol


_OPAQUE_ID = re.compile(r"^[A-Za-z0-9_-]{16,64}$")
_CLEAR_REASONS = frozenset(
    {
        "auto_lock",
        "bridge_close",
        "bridge_destroyed",
        "change_key_failed",
        "change_key_restored",
        "change_key_success",
        "duplicate_lease_id",
        "exit",
        "expired",
        "lease_consumed",
        "lease_expired",
        "lease_released",
        "manual_hide",
        "manual_lock",
        "modal_cancel",
        "modal_close",
        "navigation",
        "parent_released",
        "page_invalidated",
        "renderer_failure",
        "save_complete",
        "session_invalidated",
        "suspend_lock",
        "switch_database",
    }
)


class JavaScriptPage(Protocol):
    def runJavaScript(self, script: str) -> object: ...  # noqa: N802


class SensitiveDomController:
    """Queue fixed cleanup only; native authority never waits for JavaScript."""

    def __init__(self, page: JavaScriptPage) -> None:
        if not callable(getattr(page, "runJavaScript", None)):
            raise TypeError("sensitive DOM page port is invalid")
        self._page: JavaScriptPage | None = page
        self.clear_all_count = 0
        self.clear_lease_count = 0

    def detach(self) -> None:
        self._page = None

    def clear_all(self, reason: str) -> bool:
        page = self._page
        if (
            page is None
            or type(reason) is not str
            or reason not in _CLEAR_REASONS
        ):
            return False
        encoded_reason = json.dumps(reason, ensure_ascii=True)
        page.runJavaScript(
            "window.pdmSensitiveDom?.clearAll(" + encoded_reason + ");"
        )
        self.clear_all_count += 1
        return True

    def clear_lease(self, lease_id: str, reason: str) -> bool:
        page = self._page
        if (
            page is None
            or type(reason) is not str
            or reason not in _CLEAR_REASONS
            or type(lease_id) is not str
            or _OPAQUE_ID.fullmatch(lease_id) is None
        ):
            return False
        encoded_lease = json.dumps(lease_id, ensure_ascii=True)
        encoded_reason = json.dumps(reason, ensure_ascii=True)
        page.runJavaScript(
            "window.pdmSensitiveDom?.clearLease("
            + encoded_lease
            + ","
            + encoded_reason
            + ");"
        )
        self.clear_lease_count += 1
        return True

    def revoke_secret_leases(
        self,
        reason: str,
        *,
        lease_ids: tuple[str, ...],
        page_id: str | None = None,
        session_id: str | None = None,
        parent_lease_id: str | None = None,
    ) -> None:
        """Implement the Bridge metadata sink without receiving a secret."""

        del page_id, session_id, parent_lease_id
        if type(reason) is not str or reason not in _CLEAR_REASONS:
            return
        if (
            type(lease_ids) is not tuple
            or len(lease_ids) > 64
            or any(
                type(lease_id) is not str
                or _OPAQUE_ID.fullmatch(lease_id) is None
                for lease_id in lease_ids
            )
        ):
            self.clear_all(reason)
            return
        if lease_ids:
            for lease_id in lease_ids:
                self.clear_lease(lease_id, reason)
            return
        self.clear_all(reason)


__all__ = ["SensitiveDomController"]
