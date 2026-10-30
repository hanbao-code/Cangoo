"""设备设置的原子提交、读取及进程间文件协调。"""

from __future__ import annotations

import copy
from contextlib import contextmanager
import ctypes
import hashlib
import json
import math
import os
from pathlib import Path
import tempfile
import threading
from collections.abc import Callable, Iterator

from core.config import ConfigManager, DEFAULT_SETTINGS


class SettingsCommitError(RuntimeError):
    """设置提交失败，尚未发布新的设置权威值。"""


class SettingsReadError(SettingsCommitError):
    """设置读取或锁内计算失败，未开始写入。"""


class AtomicSettingsStore:
    """Serialize, atomically replace, and read back one complete JSON file."""

    def __init__(self, manager: ConfigManager, settings_file: Path) -> None:
        if not isinstance(manager, ConfigManager):
            raise TypeError("manager must be a ConfigManager")
        if not isinstance(settings_file, Path):
            raise TypeError("settings_file must be a Path")
        self._manager = manager
        self._settings_file = settings_file
        self._commit_lock = threading.Lock()
        self._uncertain = False

    def raw_snapshot(self) -> dict[str, object]:
        """Return an isolated copy of the current in-memory authority."""

        with self._commit_lock:
            return copy.deepcopy(self._manager.settings)

    def refresh_authority(self) -> dict[str, object]:
        """Adopt the latest complete disk object without writing it."""

        with self._commit_lock:
            if self._uncertain:
                raise SettingsCommitError("settings authority is uncertain")
            old_settings = copy.deepcopy(self._manager.settings)
            with self._exclusive_file_transaction():
                _exists, _bytes, latest = self._read_latest_settings(old_settings)
            self._manager.settings = copy.deepcopy(latest)
            return copy.deepcopy(latest)

    def commit_value(
        self,
        key: str,
        value: object,
        *,
        current_value: Callable[[], object],
    ) -> tuple[bool, dict[str, object]]:
        """Commit one changed key and publish memory only after readback.

        ``current_value`` reads the normalized public value after the latest
        disk authority has been adopted.  This lets an
        invalid persisted enum behave as its product fallback for same-value
        detection while preserving every unrelated/unknown key byte-for-value
        at the JSON data-model level.
        """

        if type(key) is not str or not key or not callable(current_value):
            raise TypeError("settings key must be a non-empty string")
        with self._commit_lock:
            if self._uncertain:
                raise SettingsCommitError("settings authority is uncertain")
            old_settings = copy.deepcopy(self._manager.settings)
            try:
                with self._exclusive_file_transaction():
                    previous_exists, previous_bytes, latest = (
                        self._read_latest_settings(old_settings)
                    )
                    self._manager.settings = copy.deepcopy(latest)
                    if current_value() == value:
                        return False, copy.deepcopy(latest)
                    candidate = copy.deepcopy(latest)
                    candidate[key] = value
                    readback = self._replace_and_verify(
                        candidate,
                        previous_exists=previous_exists,
                        previous_bytes=previous_bytes,
                    )
            except Exception as exc:
                self._manager.settings = old_settings
                raise SettingsCommitError(
                    "atomic settings commit failed"
                ) from exc
            self._manager.settings = copy.deepcopy(readback)
            return True, copy.deepcopy(readback)

    def commit_values(
        self,
        values: dict[str, object],
        *,
        current_values: Callable[[], dict[str, object]],
    ) -> tuple[bool, dict[str, object]]:
        """Commit one indivisible group of settings keys.

        C44 and C47 each own one policy with two fields. Writing either group
        through separate replacements would expose a mixed QuickBar or lock
        policy to native code, so the complete candidate is verified and
        published with one replacement.
        """

        if (
            not isinstance(values, dict)
            or not values
            or not callable(current_values)
            or any(type(key) is not str or not key for key in values)
        ):
            raise TypeError("settings values must be one non-empty key group")
        with self._commit_lock:
            if self._uncertain:
                raise SettingsCommitError("settings authority is uncertain")
            old_settings = copy.deepcopy(self._manager.settings)
            try:
                with self._exclusive_file_transaction():
                    previous_exists, previous_bytes, latest = (
                        self._read_latest_settings(old_settings)
                    )
                    self._manager.settings = copy.deepcopy(latest)
                    latest_values = current_values()
                    if (
                        not isinstance(latest_values, dict)
                        or set(values) != set(latest_values)
                    ):
                        raise TypeError(
                            "current settings values must match the key group"
                        )
                    if all(
                        latest_values[key] == values[key]
                        for key in values
                    ):
                        return False, copy.deepcopy(latest)
                    candidate = copy.deepcopy(latest)
                    candidate.update(copy.deepcopy(values))
                    readback = self._replace_and_verify(
                        candidate,
                        previous_exists=previous_exists,
                        previous_bytes=previous_bytes,
                    )
            except Exception as exc:
                self._manager.settings = old_settings
                raise SettingsCommitError(
                    "atomic settings commit failed"
                ) from exc
            self._manager.settings = copy.deepcopy(readback)
            return True, copy.deepcopy(readback)

    def _read_previous_file(self) -> tuple[bool, bytes]:
        try:
            return True, self._settings_file.read_bytes()
        except FileNotFoundError:
            return False, b""
        except OSError as exc:
            raise SettingsCommitError(
                "existing settings authority is unreadable"
            ) from exc

    def compute_values(
        self,
        compute: Callable[[dict[str, object]], dict[str, object] | None],
    ) -> tuple[bool, dict[str, object]]:
        """在同一文件锁内严格读取并计算更新；返回 None 时只刷新内存。"""

        if not callable(compute):
            raise TypeError("settings computation must be callable")
        with self._commit_lock:
            if self._uncertain:
                raise SettingsReadError("settings authority is uncertain")
            old_settings = copy.deepcopy(self._manager.settings)
            writing = False
            try:
                with self._exclusive_file_transaction():
                    previous_exists, previous_bytes, latest = (
                        self._read_latest_settings(old_settings, strict=True)
                    )
                    values = compute(copy.deepcopy(latest))
                    if values is not None and (
                        type(values) is not dict
                        or not values
                        or any(type(key) is not str or not key for key in values)
                    ):
                        raise TypeError("computed settings must be a key group or None")
                    candidate = copy.deepcopy(latest)
                    if values is not None:
                        candidate.update(copy.deepcopy(values))
                    changed = not self._exact_json_equal(latest, candidate)
                    if changed:
                        writing = True
                        latest = self._replace_and_verify(
                            candidate,
                            previous_exists=previous_exists,
                            previous_bytes=previous_bytes,
                        )
            except Exception as exc:
                self._manager.settings = old_settings
                error = SettingsCommitError if writing else SettingsReadError
                raise error("atomic settings computation failed") from exc
            self._manager.settings = copy.deepcopy(latest)
            return changed, copy.deepcopy(latest)

    def _read_latest_settings(
        self,
        missing_fallback: dict[str, object],
        *,
        strict: bool = False,
    ) -> tuple[bool, bytes, dict[str, object]]:
        previous_exists, previous_bytes = self._read_previous_file()
        if not previous_exists:
            return False, previous_bytes, copy.deepcopy(missing_fallback)
        try:
            options = (
                {
                    "object_pairs_hook": self._unique_json_object,
                    "parse_constant": self._reject_json_constant,
                    "parse_float": self._finite_json_float,
                }
                if strict else {}
            )
            value = json.loads(previous_bytes.decode("utf-8"), **options)
        except (UnicodeError, ValueError) as exc:
            if strict:
                raise SettingsReadError("existing settings JSON is invalid") from exc
            if not isinstance(exc, (UnicodeError, json.JSONDecodeError)):
                raise
            return True, previous_bytes, copy.deepcopy(missing_fallback)
        if not isinstance(value, dict):
            if strict:
                raise SettingsReadError("existing settings JSON is not an object")
            return True, previous_bytes, copy.deepcopy(missing_fallback)
        merged = copy.deepcopy(DEFAULT_SETTINGS)
        merged["theme"] = "dark"
        merged["language"] = "zh"
        merged.update(value)
        return True, previous_bytes, merged

    @staticmethod
    def _unique_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
        value: dict[str, object] = {}
        for key, item in pairs:
            if key in value:
                raise ValueError("duplicate JSON key")
            value[key] = item
        return value

    @staticmethod
    def _reject_json_constant(_value: str) -> None:
        raise ValueError("non-finite JSON number")

    @staticmethod
    def _finite_json_float(value: str) -> float:
        number = float(value)
        if not math.isfinite(number):
            raise ValueError("non-finite JSON number")
        return number

    @contextmanager
    def _exclusive_file_transaction(self) -> Iterator[None]:
        if os.name != "nt":
            yield
            return
        kernel32 = ctypes.windll.kernel32
        kernel32.CreateMutexW.argtypes = (
            ctypes.c_void_p,
            ctypes.c_int,
            ctypes.c_wchar_p,
        )
        kernel32.CreateMutexW.restype = ctypes.c_void_p
        kernel32.WaitForSingleObject.argtypes = (
            ctypes.c_void_p,
            ctypes.c_uint32,
        )
        kernel32.WaitForSingleObject.restype = ctypes.c_uint32
        kernel32.ReleaseMutex.argtypes = (ctypes.c_void_p,)
        kernel32.ReleaseMutex.restype = ctypes.c_int
        kernel32.CloseHandle.argtypes = (ctypes.c_void_p,)
        kernel32.CloseHandle.restype = ctypes.c_int
        identity = os.path.normcase(
            os.path.abspath(self._settings_file)
        ).encode("utf-8", errors="surrogatepass")
        name = (
            "Local\\PDM.Settings."
            + hashlib.sha256(identity).hexdigest()[:24]
        )
        handle = kernel32.CreateMutexW(None, False, name)
        if not handle:
            raise SettingsCommitError("settings mutex creation failed")
        acquired = False
        try:
            result = int(kernel32.WaitForSingleObject(handle, 10_000))
            if result not in {0x00000000, 0x00000080}:
                raise SettingsCommitError("settings mutex wait failed")
            acquired = True
            yield
        finally:
            if acquired:
                kernel32.ReleaseMutex(handle)
            kernel32.CloseHandle(handle)

    def _replace_and_verify(
        self,
        candidate: dict[str, object],
        *,
        previous_exists: bool,
        previous_bytes: bytes,
    ) -> dict[str, object]:
        settings_file = self._settings_file
        parent = settings_file.parent
        parent.mkdir(parents=True, exist_ok=True)
        replacement_started = False
        temp_path: Path | None = None
        try:
            temp_path = self._write_temp_json(parent, settings_file, candidate)
            temp_readback = self._read_json_object(temp_path)
            if not self._exact_json_equal(temp_readback, candidate):
                raise SettingsCommitError(
                    "temporary settings readback mismatch"
                )
            replacement_started = True
            os.replace(temp_path, settings_file)
            temp_path = None
            readback = self._read_json_object(settings_file)
            if not self._exact_json_equal(readback, candidate):
                raise SettingsCommitError(
                    "settings readback mismatch"
                )
            return readback
        except Exception:
            if replacement_started:
                try:
                    self._restore_previous(
                        parent,
                        settings_file,
                        previous_exists,
                        previous_bytes,
                    )
                except Exception as rollback_exc:
                    self._uncertain = True
                    raise SettingsCommitError(
                        "settings authority rollback could not be confirmed"
                    ) from rollback_exc
            raise
        finally:
            if temp_path is not None:
                try:
                    temp_path.unlink(missing_ok=True)
                except OSError:
                    pass

    @staticmethod
    def _write_temp_json(
        parent: Path,
        settings_file: Path,
        value: dict[str, object],
    ) -> Path:
        descriptor, raw_path = tempfile.mkstemp(
            dir=str(parent),
            prefix=f".{settings_file.name}.",
            suffix=".tmp",
        )
        path = Path(raw_path)
        try:
            with os.fdopen(
                descriptor,
                "w",
                encoding="utf-8",
                newline="\n",
            ) as handle:
                json.dump(
                    value,
                    handle,
                    ensure_ascii=False,
                    indent=2,
                    allow_nan=False,
                )
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
        except Exception:
            try:
                os.close(descriptor)
            except OSError:
                pass
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass
            raise
        return path

    @staticmethod
    def _read_json_object(path: Path) -> dict[str, object]:
        with path.open("r", encoding="utf-8") as handle:
            value = json.load(handle)
        if not isinstance(value, dict):
            raise SettingsCommitError("settings readback is not an object")
        return value

    @staticmethod
    def _exact_json_equal(left: object, right: object) -> bool:
        if type(left) is not type(right):
            return False
        if isinstance(left, dict):
            return left.keys() == right.keys() and all(
                AtomicSettingsStore._exact_json_equal(
                    left[key],
                    right[key],
                )
                for key in left
            )
        if isinstance(left, list):
            return len(left) == len(right) and all(
                AtomicSettingsStore._exact_json_equal(a, b)
                for a, b in zip(left, right)
            )
        return left == right

    def _restore_previous(
        self,
        parent: Path,
        settings_file: Path,
        previous_exists: bool,
        previous_bytes: bytes,
    ) -> None:
        if not previous_exists:
            settings_file.unlink(missing_ok=True)
            if settings_file.exists():
                raise SettingsCommitError(
                    "new settings authority could not be rolled back"
                )
            return
        descriptor, raw_path = tempfile.mkstemp(
            dir=str(parent),
            prefix=f".{settings_file.name}.rollback.",
            suffix=".tmp",
        )
        rollback_path = Path(raw_path)
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(previous_bytes)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(rollback_path, settings_file)
            if settings_file.read_bytes() != previous_bytes:
                raise SettingsCommitError(
                    "previous settings authority was not restored"
                )
        finally:
            try:
                rollback_path.unlink(missing_ok=True)
            except OSError:
                pass


__all__ = ["AtomicSettingsStore", "SettingsCommitError", "SettingsReadError"]
