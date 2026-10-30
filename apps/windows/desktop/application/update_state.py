"""公开版本检查状态；设置读取、到期判断与登记共用原子文件锁。"""

from __future__ import annotations

import copy
import json
from collections.abc import Callable
from uuid import uuid4

from desktop.application.settings_store import (
    AtomicSettingsStore,
    SettingsCommitError,
    SettingsReadError,
)
from desktop.application.update_feed import parse_version, validate_release_result


DAY_MS = 86_400_000
MAX_INTERVAL_DAYS = 2_147_483_647
MAX_TIMESTAMP_MS = 9_007_199_254_740_991
MAX_STATE_BYTES = 256 * 1024
SNOOZE_MS = 7 * DAY_MS


class UpdateStateError(RuntimeError):
    """供更新界面区分不可读取与未能保存的状态。"""

    def __init__(self, kind: str) -> None:
        self.kind = kind
        super().__init__(kind)


def _integer(value: object, minimum: int, maximum: int) -> bool:
    return type(value) is int and minimum <= value <= maximum


def _timestamp(value: object) -> None:
    if not _integer(value, 0, MAX_TIMESTAMP_MS):
        raise ValueError("invalid update timestamp")


def _version(value: object) -> None:
    if parse_version(value) is None:
        raise ValueError("invalid update version")


def _default_state() -> dict[str, object]:
    return {
        "schema": 1,
        "enabled": True,
        "intervalDays": 1,
        "lastAttemptMs": 0,
        "attemptId": "",
        "lastResult": None,
        "ignoredVersions": {},
    }


def _state(settings: dict[str, object]) -> dict[str, object]:
    value = settings.get("update_check", _default_state())
    if type(value) is not dict or set(value) != set(_default_state()):
        raise ValueError("invalid update state fields")
    if (
        type(value["schema"]) is not int
        or value["schema"] != 1
        or type(value["enabled"]) is not bool
        or not _integer(value["intervalDays"], 1, MAX_INTERVAL_DAYS)
    ):
        raise ValueError("unsupported update state policy")
    _timestamp(value["lastAttemptMs"])
    _attempt_id(value["attemptId"], allow_empty=True)
    if value["attemptId"] == "" and (
        value["lastAttemptMs"] != 0 or value["lastResult"] is not None
    ):
        raise ValueError("missing update attempt identity")
    ignored = value["ignoredVersions"]
    if type(ignored) is not dict:
        raise ValueError("invalid ignored update versions")
    for version, until_ms in ignored.items():
        _version(version)
        _timestamp(until_ms)
    result = value["lastResult"]
    if result is not None:
        if type(result) is not dict or set(result) != {
            "version", "tag", "publishedAt", "notes", "checkedAtMs",
        }:
            raise ValueError("invalid cached update result fields")
        _timestamp(result["checkedAtMs"])
        public = {key: item for key, item in result.items() if key != "checkedAtMs"}
        if not all(type(item) is str and item == "" for item in public.values()):
            validate_release_result(public)
    encoded = json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    if len(encoded.encode("utf-8")) > MAX_STATE_BYTES:
        raise ValueError("update state exceeds size limit")
    return copy.deepcopy(value)


def _attempt_id(value: object, *, allow_empty: bool = False) -> None:
    if type(value) is not str or not (
        (allow_empty and value == "")
        or (len(value) == 32 and all(char in "0123456789abcdef" for char in value))
    ):
        raise ValueError("invalid update attempt identity")


class UpdateStateStore:
    """只保存公开更新资料；网络结果身份由调用方核验。"""

    def __init__(self, store: AtomicSettingsStore) -> None:
        if not isinstance(store, AtomicSettingsStore):
            raise TypeError("update state requires the atomic settings store")
        self._store = store

    def _compute(
        self,
        compute: Callable[[dict[str, object]], dict[str, object] | None],
    ) -> dict[str, object]:
        try:
            _changed, settings = self._store.compute_values(compute)
        except SettingsReadError as exc:
            cause = exc.__cause__
            if isinstance(cause, UpdateStateError) and cause.kind == "SETTINGS_WRITE_FAILED":
                raise UpdateStateError("SETTINGS_WRITE_FAILED") from exc
            raise UpdateStateError("SETTINGS_UNAVAILABLE") from exc
        except SettingsCommitError as exc:
            raise UpdateStateError("SETTINGS_WRITE_FAILED") from exc
        return _state(settings)

    def load(self) -> dict[str, object]:
        def validate(settings: dict[str, object]) -> None:
            _state(settings)

        return self._compute(validate)

    def _update(
        self,
        change: Callable[[dict[str, object]], None],
    ) -> dict[str, object]:
        def compute(settings: dict[str, object]) -> dict[str, object] | None:
            state = _state(settings)
            previous = copy.deepcopy(state)
            change(state)
            try:
                _state({"update_check": state})
            except ValueError as exc:
                raise UpdateStateError("SETTINGS_WRITE_FAILED") from exc
            return {"update_check": state} if state != previous else None

        return self._compute(compute)

    def claim_attempt(
        self,
        now_ms: int,
        manual: bool = False,
    ) -> tuple[bool, dict[str, object]]:
        _timestamp(now_ms)
        if type(manual) is not bool:
            raise ValueError("invalid update attempt intent")
        claimed = False

        def claim(state: dict[str, object]) -> None:
            nonlocal claimed
            last = state["lastAttemptMs"]
            if not manual and (
                not state["enabled"]
                or now_ms == 0
                or now_ms < last
                or (
                    state["attemptId"] != ""
                    and (now_ms - last) // DAY_MS < state["intervalDays"]
                )
            ):
                return
            claimed = True
            state["lastAttemptMs"] = now_ms
            state["attemptId"] = uuid4().hex

        state = self._update(claim)
        return claimed, state

    def set_policy(self, enabled: bool, days: int) -> dict[str, object]:
        if type(enabled) is not bool or not _integer(days, 1, MAX_INTERVAL_DAYS):
            raise ValueError("invalid update policy")

        def change(state: dict[str, object]) -> None:
            state.update(enabled=enabled, intervalDays=days)

        return self._update(change)

    def set_reminder(
        self,
        version: str,
        action: str,
        now_ms: int,
    ) -> dict[str, object]:
        _version(version)
        _timestamp(now_ms)
        if type(action) is not str or action not in {"SNOOZE", "IGNORE"}:
            raise ValueError("invalid update reminder action")
        if action == "SNOOZE" and now_ms > MAX_TIMESTAMP_MS - SNOOZE_MS:
            raise ValueError("update snooze exceeds timestamp limit")

        def change(state: dict[str, object]) -> None:
            state["ignoredVersions"][version] = now_ms + SNOOZE_MS if action == "SNOOZE" else 0

        return self._update(change)

    def save_result(
        self,
        result: dict[str, object] | None,
        now_ms: int,
        attempt_id: str,
    ) -> dict[str, object]:
        _timestamp(now_ms)
        _attempt_id(attempt_id)
        public = (
            {"version": "", "tag": "", "publishedAt": "", "notes": ""}
            if result is None else validate_release_result(result)
        )
        cached = {**copy.deepcopy(public), "checkedAtMs": now_ms}

        def change(state: dict[str, object]) -> None:
            if state["attemptId"] == attempt_id:
                state["lastResult"] = cached

        return self._update(change)


__all__ = [
    "DAY_MS", "MAX_INTERVAL_DAYS", "MAX_TIMESTAMP_MS", "MAX_STATE_BYTES", "SNOOZE_MS",
    "UpdateStateError", "UpdateStateStore",
]
