"""Best-effort Windows error-dialog/WER policy and read-only dump risk.

The policy is intentionally process-local.  It never writes WER registry
configuration, creates a dump, scans a dump directory, or claims that an
administrator/debugger cannot capture process memory.
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes
from dataclasses import dataclass
from enum import Enum
import os


SEM_FAILCRITICALERRORS = 0x0001
SEM_NOGPFAULTERRORBOX = 0x0002
REQUIRED_ERROR_MODE = SEM_FAILCRITICALERRORS | SEM_NOGPFAULTERRORBOX

# Values from the Windows SDK WerApi.h shipped with the supported toolchain.
WER_FAULT_REPORTING_FLAG_NOHEAP = 0x00000001
WER_FAULT_REPORTING_NO_UI = 0x00000020
REQUIRED_WER_FLAGS = (
    WER_FAULT_REPORTING_FLAG_NOHEAP | WER_FAULT_REPORTING_NO_UI
)

_HRESULT_FILE_NOT_FOUND = 0x80070490
_LOCAL_DUMPS_KEY = (
    r"SOFTWARE\Microsoft\Windows\Windows Error Reporting\LocalDumps"
)
_LOCAL_DUMP_VALUE_NAMES = (
    "DumpType",
    "DumpFolder",
    "DumpCount",
    "CustomDumpFlags",
)


class PolicyApplyStatus(str, Enum):
    UNSUPPORTED = "unsupported"
    APPLIED = "applied"
    PARTIAL = "partial"
    FAILED = "failed"


class RegistryReadStatus(str, Enum):
    UNSUPPORTED = "unsupported"
    COMPLETE = "complete"
    PARTIAL = "partial"
    ACCESS_DENIED = "access_denied"
    FAILED = "failed"


class LocalDumpKind(str, Enum):
    ABSENT = "absent"
    DEFAULT_MINI = "default_mini"
    CUSTOM = "custom"
    MINI = "mini"
    FULL = "full"
    UNKNOWN = "unknown"


class LocalDumpTarget(str, Enum):
    PRODUCT = "product"
    CANDIDATE = "candidate"
    PYTHON = "python"
    PYTHONW = "pythonw"
    QTWEBENGINE = "qtwebengine"


_TARGET_EXECUTABLES = {
    LocalDumpTarget.PRODUCT: "Cangoo.exe",
    LocalDumpTarget.CANDIDATE: "CangooWebCandidate.exe",
    LocalDumpTarget.PYTHON: "python.exe",
    LocalDumpTarget.PYTHONW: "pythonw.exe",
    LocalDumpTarget.QTWEBENGINE: "QtWebEngineProcess.exe",
}


@dataclass(frozen=True, slots=True)
class WindowsErrorPolicyResult:
    """Typed result containing no exception text or environment values."""

    platform_supported: bool
    status: PolicyApplyStatus
    error_mode_applied: bool
    child_error_mode_inherited: bool
    wer_flags_applied: bool
    wer_existing_flags_preserved: bool
    wer_get_hresult: int | None
    wer_set_hresult: int | None
    required_error_mode: int
    required_wer_flags: int

    def to_mapping(self) -> dict[str, object]:
        return {
            "platform_supported": self.platform_supported,
            "status": self.status.value,
            "error_mode_applied": self.error_mode_applied,
            "child_error_mode_inherited": (
                self.child_error_mode_inherited
            ),
            "wer_flags_applied": self.wer_flags_applied,
            "wer_existing_flags_preserved": (
                self.wer_existing_flags_preserved
            ),
            "wer_get_hresult": self.wer_get_hresult,
            "wer_set_hresult": self.wer_set_hresult,
            "noheap_requested": bool(
                self.required_wer_flags
                & WER_FAULT_REPORTING_FLAG_NOHEAP
            ),
            "no_ui_requested": bool(
                self.required_wer_flags
                & WER_FAULT_REPORTING_NO_UI
            ),
        }


@dataclass(frozen=True, slots=True)
class LocalDumpTargetRisk:
    target: LocalDumpTarget
    explicit_configuration: LocalDumpKind
    effective_configuration: LocalDumpKind
    dump_folder_configured: bool
    custom_flags_configured: bool

    def to_mapping(self) -> dict[str, object]:
        return {
            "target": self.target.value,
            "explicit_configuration": self.explicit_configuration.value,
            "effective_configuration": self.effective_configuration.value,
            "dump_folder_configured": self.dump_folder_configured,
            "custom_flags_configured": self.custom_flags_configured,
        }


@dataclass(frozen=True, slots=True)
class LocalDumpsRiskSnapshot:
    """Read-only classification; dump folder values are never returned."""

    platform_supported: bool
    read_status: RegistryReadStatus
    global_configuration: LocalDumpKind
    global_dump_folder_configured: bool
    global_custom_flags_configured: bool
    targets: tuple[LocalDumpTargetRisk, ...]
    administrator_override_possible: bool
    dump_folder_recorded: bool = False
    registry_write_attempted: bool = False

    @property
    def configured(self) -> bool:
        return (
            self.global_configuration is not LocalDumpKind.ABSENT
            or any(
                item.explicit_configuration is not LocalDumpKind.ABSENT
                for item in self.targets
            )
        )

    def to_mapping(self) -> dict[str, object]:
        return {
            "platform_supported": self.platform_supported,
            "read_status": self.read_status.value,
            "configured": self.configured,
            "global_configuration": self.global_configuration.value,
            "global_dump_folder_configured": (
                self.global_dump_folder_configured
            ),
            "global_custom_flags_configured": (
                self.global_custom_flags_configured
            ),
            "targets": [target.to_mapping() for target in self.targets],
            "administrator_override_possible": (
                self.administrator_override_possible
            ),
            "dump_folder_recorded": self.dump_folder_recorded,
            "registry_write_attempted": self.registry_write_attempted,
        }


def _unsigned_hresult(value: int) -> int:
    return int(value) & 0xFFFFFFFF


def _hresult_succeeded(value: int) -> bool:
    return not bool(_unsigned_hresult(value) & 0x80000000)


def apply_windows_error_policy() -> WindowsErrorPolicyResult:
    """Set inherited native error mode and preserve existing WER flags."""

    if os.name != "nt":
        return WindowsErrorPolicyResult(
            platform_supported=False,
            status=PolicyApplyStatus.UNSUPPORTED,
            error_mode_applied=False,
            child_error_mode_inherited=False,
            wer_flags_applied=False,
            wer_existing_flags_preserved=False,
            wer_get_hresult=None,
            wer_set_hresult=None,
            required_error_mode=REQUIRED_ERROR_MODE,
            required_wer_flags=REQUIRED_WER_FLAGS,
        )

    error_mode_applied = False
    wer_flags_applied = False
    existing_flags_preserved = False
    wer_get_hresult: int | None = None
    wer_set_hresult: int | None = None

    try:
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        get_error_mode = kernel32.GetErrorMode
        get_error_mode.argtypes = []
        get_error_mode.restype = wintypes.UINT
        set_error_mode = kernel32.SetErrorMode
        set_error_mode.argtypes = [wintypes.UINT]
        set_error_mode.restype = wintypes.UINT

        current_mode = int(get_error_mode())
        set_error_mode(current_mode | REQUIRED_ERROR_MODE)
        observed_mode = int(get_error_mode())
        error_mode_applied = (
            observed_mode & REQUIRED_ERROR_MODE
        ) == REQUIRED_ERROR_MODE
    except (AttributeError, OSError):
        error_mode_applied = False

    try:
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        get_current_process = kernel32.GetCurrentProcess
        get_current_process.argtypes = []
        get_current_process.restype = wintypes.HANDLE
        wer_get_flags = kernel32.WerGetFlags
        wer_get_flags.argtypes = [
            wintypes.HANDLE,
            ctypes.POINTER(wintypes.DWORD),
        ]
        wer_get_flags.restype = ctypes.c_long
        wer_set_flags = kernel32.WerSetFlags
        wer_set_flags.argtypes = [wintypes.DWORD]
        wer_set_flags.restype = ctypes.c_long

        existing = wintypes.DWORD()
        get_result = int(
            wer_get_flags(get_current_process(), ctypes.byref(existing))
        )
        wer_get_hresult = _unsigned_hresult(get_result)
        if _hresult_succeeded(get_result):
            existing_flags = int(existing.value)
        elif wer_get_hresult == _HRESULT_FILE_NOT_FOUND:
            existing_flags = 0
        else:
            existing_flags = None

        if existing_flags is not None:
            requested_flags = existing_flags | REQUIRED_WER_FLAGS
            set_result = int(wer_set_flags(requested_flags))
            wer_set_hresult = _unsigned_hresult(set_result)
            if _hresult_succeeded(set_result):
                observed = wintypes.DWORD()
                verify_result = int(
                    wer_get_flags(
                        get_current_process(),
                        ctypes.byref(observed),
                    )
                )
                if _hresult_succeeded(verify_result):
                    observed_flags = int(observed.value)
                    wer_flags_applied = (
                        observed_flags & REQUIRED_WER_FLAGS
                    ) == REQUIRED_WER_FLAGS
                    existing_flags_preserved = (
                        observed_flags & existing_flags
                    ) == existing_flags
    except (AttributeError, OSError):
        wer_flags_applied = False
        existing_flags_preserved = False

    if error_mode_applied and wer_flags_applied:
        status = PolicyApplyStatus.APPLIED
    elif error_mode_applied or wer_flags_applied:
        status = PolicyApplyStatus.PARTIAL
    else:
        status = PolicyApplyStatus.FAILED
    return WindowsErrorPolicyResult(
        platform_supported=True,
        status=status,
        error_mode_applied=error_mode_applied,
        child_error_mode_inherited=error_mode_applied,
        wer_flags_applied=wer_flags_applied,
        wer_existing_flags_preserved=existing_flags_preserved,
        wer_get_hresult=wer_get_hresult,
        wer_set_hresult=wer_set_hresult,
        required_error_mode=REQUIRED_ERROR_MODE,
        required_wer_flags=REQUIRED_WER_FLAGS,
    )


@dataclass(frozen=True, slots=True)
class _RegistryObservation:
    kind: LocalDumpKind
    dump_folder_configured: bool = False
    custom_flags_configured: bool = False
    access_denied: bool = False
    failed: bool = False


def _classify_dump_type(
    value: object,
    *,
    configuration_present: bool,
) -> LocalDumpKind:
    if not configuration_present:
        return LocalDumpKind.ABSENT
    if value is None:
        return LocalDumpKind.DEFAULT_MINI
    if type(value) is not int:
        return LocalDumpKind.UNKNOWN
    return {
        0: LocalDumpKind.CUSTOM,
        1: LocalDumpKind.MINI,
        2: LocalDumpKind.FULL,
    }.get(value, LocalDumpKind.UNKNOWN)


def _recognized_dump_configuration_present(
    value_presence: dict[str, bool],
) -> bool:
    return any(
        value_presence.get(value_name) is True
        for value_name in _LOCAL_DUMP_VALUE_NAMES
    )


def _read_registry_configuration(
    subkey: str,
    access: int,
) -> _RegistryObservation:
    import winreg

    try:
        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            subkey,
            0,
            winreg.KEY_READ | access,
        ) as key:
            value_presence: dict[str, bool] = {}
            dump_type: object = None
            for value_name in _LOCAL_DUMP_VALUE_NAMES:
                try:
                    value, _value_type = winreg.QueryValueEx(
                        key,
                        value_name,
                    )
                    value_presence[value_name] = True
                    if value_name == "DumpType":
                        dump_type = value
                except FileNotFoundError:
                    value_presence[value_name] = False
            return _RegistryObservation(
                _classify_dump_type(
                    dump_type,
                    # LocalDumps may exist only as a container for unrelated
                    # per-application subkeys. At least one recognized value
                    # is required for this exact key to configure dumps. Once
                    # configured, an omitted DumpType uses the Windows
                    # default minidump type.
                    configuration_present=(
                        _recognized_dump_configuration_present(
                            value_presence
                        )
                    ),
                ),
                dump_folder_configured=value_presence["DumpFolder"],
                custom_flags_configured=value_presence[
                    "CustomDumpFlags"
                ],
            )
    except FileNotFoundError:
        return _RegistryObservation(LocalDumpKind.ABSENT)
    except PermissionError:
        return _RegistryObservation(
            LocalDumpKind.UNKNOWN,
            access_denied=True,
        )
    except OSError:
        return _RegistryObservation(
            LocalDumpKind.UNKNOWN,
            failed=True,
        )


_DUMP_RISK_ORDER = {
    LocalDumpKind.ABSENT: 0,
    LocalDumpKind.MINI: 1,
    LocalDumpKind.DEFAULT_MINI: 1,
    LocalDumpKind.CUSTOM: 2,
    LocalDumpKind.FULL: 3,
    LocalDumpKind.UNKNOWN: 4,
}


def _merge_observations(
    observations: tuple[_RegistryObservation, ...],
) -> _RegistryObservation:
    selected = max(
        observations,
        key=lambda item: _DUMP_RISK_ORDER[item.kind],
    )
    return _RegistryObservation(
        kind=selected.kind,
        dump_folder_configured=any(
            item.dump_folder_configured for item in observations
        ),
        custom_flags_configured=any(
            item.custom_flags_configured for item in observations
        ),
        access_denied=any(item.access_denied for item in observations),
        failed=any(item.failed for item in observations),
    )


def read_local_dumps_risk_snapshot() -> LocalDumpsRiskSnapshot:
    """Inspect fixed LocalDumps keys without reading or returning a folder."""

    if os.name != "nt":
        return LocalDumpsRiskSnapshot(
            platform_supported=False,
            read_status=RegistryReadStatus.UNSUPPORTED,
            global_configuration=LocalDumpKind.ABSENT,
            global_dump_folder_configured=False,
            global_custom_flags_configured=False,
            targets=tuple(
                LocalDumpTargetRisk(
                    target=target,
                    explicit_configuration=LocalDumpKind.ABSENT,
                    effective_configuration=LocalDumpKind.ABSENT,
                    dump_folder_configured=False,
                    custom_flags_configured=False,
                )
                for target in LocalDumpTarget
            ),
            administrator_override_possible=False,
        )

    import winreg

    views = tuple(
        dict.fromkeys(
            (
                getattr(winreg, "KEY_WOW64_64KEY", 0),
                getattr(winreg, "KEY_WOW64_32KEY", 0),
            )
        )
    )
    observations: list[_RegistryObservation] = []

    global_observation = _merge_observations(
        tuple(
            _read_registry_configuration(_LOCAL_DUMPS_KEY, view)
            for view in views
        )
    )
    observations.append(global_observation)

    targets: list[LocalDumpTargetRisk] = []
    for target in LocalDumpTarget:
        executable_name = _TARGET_EXECUTABLES[target]
        explicit = _merge_observations(
            tuple(
                _read_registry_configuration(
                    _LOCAL_DUMPS_KEY + "\\" + executable_name,
                    view,
                )
                for view in views
            )
        )
        observations.append(explicit)
        effective = (
            explicit.kind
            if explicit.kind is not LocalDumpKind.ABSENT
            else global_observation.kind
        )
        targets.append(
            LocalDumpTargetRisk(
                target=target,
                explicit_configuration=explicit.kind,
                effective_configuration=effective,
                dump_folder_configured=explicit.dump_folder_configured,
                custom_flags_configured=explicit.custom_flags_configured,
            )
        )

    if any(item.failed for item in observations):
        read_status = RegistryReadStatus.FAILED
    elif all(item.access_denied for item in observations):
        read_status = RegistryReadStatus.ACCESS_DENIED
    elif any(item.access_denied for item in observations):
        read_status = RegistryReadStatus.PARTIAL
    else:
        read_status = RegistryReadStatus.COMPLETE

    return LocalDumpsRiskSnapshot(
        platform_supported=True,
        read_status=read_status,
        global_configuration=global_observation.kind,
        global_dump_folder_configured=(
            global_observation.dump_folder_configured
        ),
        global_custom_flags_configured=(
            global_observation.custom_flags_configured
        ),
        targets=tuple(targets),
        administrator_override_possible=True,
    )


__all__ = [
    "LocalDumpKind",
    "LocalDumpTarget",
    "LocalDumpTargetRisk",
    "LocalDumpsRiskSnapshot",
    "PolicyApplyStatus",
    "REQUIRED_ERROR_MODE",
    "REQUIRED_WER_FLAGS",
    "RegistryReadStatus",
    "SEM_FAILCRITICALERRORS",
    "SEM_NOGPFAULTERRORBOX",
    "WER_FAULT_REPORTING_FLAG_NOHEAP",
    "WER_FAULT_REPORTING_NO_UI",
    "WindowsErrorPolicyResult",
    "apply_windows_error_policy",
    "read_local_dumps_risk_snapshot",
]
