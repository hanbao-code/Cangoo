"""读取指定 Windows 蓝牙适配器的已配对缓存，不扫描或修改配对。"""

from __future__ import annotations

import ctypes
from ctypes import wintypes
import re
import sys


_NO_MORE_ITEMS = 259
_ADDRESS = re.compile(r"[0-9A-Fa-f]{2}(?::[0-9A-Fa-f]{2}){5}")


class _BluetoothAddress(ctypes.Union):
    _fields_ = [("value", ctypes.c_ulonglong), ("bytes", ctypes.c_ubyte * 6)]


class _RadioParameters(ctypes.Structure):
    _fields_ = [("size", wintypes.DWORD)]


class _RadioInfo(ctypes.Structure):
    _fields_ = [("size", wintypes.DWORD), ("address", _BluetoothAddress),
                ("name", wintypes.WCHAR * 248), ("device_class", wintypes.ULONG),
                ("subversion", wintypes.USHORT), ("manufacturer", wintypes.USHORT)]


class _SystemTime(ctypes.Structure):
    _fields_ = [(name, wintypes.WORD) for name in
                ("year", "month", "weekday", "day", "hour", "minute", "second", "milliseconds")]


class _DeviceInfo(ctypes.Structure):
    _fields_ = [("size", wintypes.DWORD), ("address", _BluetoothAddress),
                ("device_class", wintypes.ULONG), ("connected", wintypes.BOOL),
                ("remembered", wintypes.BOOL), ("authenticated", wintypes.BOOL),
                ("last_seen", _SystemTime), ("last_used", _SystemTime), ("name", wintypes.WCHAR * 248)]


class _SearchParameters(ctypes.Structure):
    _fields_ = [("size", wintypes.DWORD), ("authenticated", wintypes.BOOL),
                ("remembered", wintypes.BOOL), ("unknown", wintypes.BOOL),
                ("connected", wintypes.BOOL), ("inquiry", wintypes.BOOL),
                ("timeout", ctypes.c_ubyte), ("radio", wintypes.HANDLE)]


def _apis():
    if sys.platform != "win32":
        raise OSError("当前平台不提供 Windows 蓝牙缓存")
    api = ctypes.WinDLL("bthprops.cpl", use_last_error=True)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    for name, arguments, result in (
        ("BluetoothFindFirstRadio", [ctypes.POINTER(_RadioParameters), ctypes.POINTER(wintypes.HANDLE)], wintypes.HANDLE),
        ("BluetoothFindNextRadio", [wintypes.HANDLE, ctypes.POINTER(wintypes.HANDLE)], wintypes.BOOL),
        ("BluetoothFindRadioClose", [wintypes.HANDLE], wintypes.BOOL),
        ("BluetoothGetRadioInfo", [wintypes.HANDLE, ctypes.POINTER(_RadioInfo)], wintypes.DWORD),
        ("BluetoothFindFirstDevice", [ctypes.POINTER(_SearchParameters), ctypes.POINTER(_DeviceInfo)], wintypes.HANDLE),
        ("BluetoothFindNextDevice", [wintypes.HANDLE, ctypes.POINTER(_DeviceInfo)], wintypes.BOOL),
        ("BluetoothFindDeviceClose", [wintypes.HANDLE], wintypes.BOOL),
    ):
        function = getattr(api, name)
        function.argtypes, function.restype = arguments, result
    kernel.CloseHandle.argtypes, kernel.CloseHandle.restype = [wintypes.HANDLE], wintypes.BOOL
    return api, kernel


def _finished():
    if ctypes.get_last_error() != _NO_MORE_ITEMS:
        raise OSError("蓝牙缓存枚举未能完成")


def _devices(api, radio, limit):
    parameters = _SearchParameters()
    parameters.size = ctypes.sizeof(parameters)
    parameters.authenticated = True
    parameters.radio = radio
    # 其余标志保持 false，尤其不向空中发出 inquiry。
    info = _DeviceInfo()
    info.size = ctypes.sizeof(info)
    search = api.BluetoothFindFirstDevice(ctypes.byref(parameters), ctypes.byref(info))
    if not search:
        _finished()
        return []
    result = []
    try:
        while True:
            if info.authenticated:
                digits = f"{info.address.value:012X}"
                if len(digits) == 12:
                    result.append((":".join(digits[index:index + 2] for index in range(0, 12, 2)), info.name))
                    if len(result) >= limit:
                        break
            info = _DeviceInfo()
            info.size = ctypes.sizeof(info)
            if not api.BluetoothFindNextDevice(search, ctypes.byref(info)):
                _finished()
                break
        return result
    finally:
        if not api.BluetoothFindDeviceClose(search):
            raise OSError("蓝牙设备枚举句柄未能关闭")


def paired_bluetooth_devices(adapter_address: str, limit: int = 64) -> list[tuple[str, str]]:
    """只返回当前适配器的已认证缓存项；连接前仍须重新检查配对状态。"""
    if type(adapter_address) is not str or not _ADDRESS.fullmatch(adapter_address):
        raise ValueError("无效的本机蓝牙适配器")
    if type(limit) is not int or not 1 <= limit <= 64:
        raise ValueError("无效的蓝牙候选上限")
    requested = int(adapter_address.replace(":", ""), 16)
    api, kernel = _apis()
    parameters = _RadioParameters(ctypes.sizeof(_RadioParameters))
    radio = wintypes.HANDLE()
    search = api.BluetoothFindFirstRadio(ctypes.byref(parameters), ctypes.byref(radio))
    if not search:
        _finished()
        return []
    try:
        while True:
            try:
                info = _RadioInfo()
                info.size = ctypes.sizeof(info)
                if api.BluetoothGetRadioInfo(radio, ctypes.byref(info)) != 0:
                    raise OSError("未能读取本机蓝牙适配器")
                if info.address.value == requested:
                    return _devices(api, radio, limit)
            finally:
                if not kernel.CloseHandle(radio):
                    raise OSError("本机蓝牙适配器句柄未能关闭")
            radio = wintypes.HANDLE()
            if not api.BluetoothFindNextRadio(search, ctypes.byref(radio)):
                _finished()
                return []
    finally:
        if not api.BluetoothFindRadioClose(search):
            raise OSError("蓝牙适配器枚举句柄未能关闭")
