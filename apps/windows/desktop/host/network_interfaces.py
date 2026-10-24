"""读取 Windows 网卡硬件及连接标志，仅用于接收地址的展示排序。"""

from __future__ import annotations

import ctypes
from ctypes import wintypes
from functools import lru_cache
import sys


class _Guid(ctypes.Structure):
    _fields_ = [("data1", wintypes.DWORD), ("data2", wintypes.WORD),
                ("data3", wintypes.WORD), ("data4", ctypes.c_ubyte * 8)]


class _MibIfRow2(ctypes.Structure):
    _fields_ = [
        ("interface_luid", ctypes.c_ulonglong), ("interface_index", wintypes.ULONG),
        ("interface_guid", _Guid), ("alias", wintypes.WCHAR * 257),
        ("description", wintypes.WCHAR * 257), ("physical_address_length", wintypes.ULONG),
        ("physical_address", ctypes.c_ubyte * 32), ("permanent_physical_address", ctypes.c_ubyte * 32),
        ("mtu", wintypes.ULONG), ("type", wintypes.ULONG), ("tunnel_type", wintypes.ULONG),
        ("media_type", wintypes.ULONG), ("physical_medium_type", wintypes.ULONG),
        ("access_type", wintypes.ULONG), ("direction_type", wintypes.ULONG),
        ("interface_flags", ctypes.c_ubyte), ("oper_status", wintypes.ULONG),
        ("admin_status", wintypes.ULONG), ("media_connect_state", wintypes.ULONG),
        ("network_guid", _Guid), ("connection_type", wintypes.ULONG),
    ] + [(name, ctypes.c_ulonglong) for name in (
        "transmit_link_speed", "receive_link_speed", "in_octets", "in_ucast_pkts", "in_nucast_pkts",
        "in_discards", "in_errors", "in_unknown_protos", "in_ucast_octets", "in_multicast_octets",
        "in_broadcast_octets", "out_octets", "out_ucast_pkts", "out_nucast_pkts", "out_discards",
        "out_errors", "out_ucast_octets", "out_multicast_octets", "out_broadcast_octets", "out_qlen",
    )]


@lru_cache(maxsize=1)
def _api():
    api = ctypes.WinDLL("iphlpapi.dll", use_last_error=True)
    function = api.GetIfEntry2
    function.argtypes = [ctypes.POINTER(_MibIfRow2)]
    function.restype = wintypes.ULONG
    return function


def interface_status(index: int) -> tuple[bool, bool] | None:
    """返回（硬件网卡、已连接）；读取失败不影响地址使用资格。"""
    if sys.platform != "win32" or type(index) is not int or not 1 <= index <= 0xffffffff:
        return None
    row = _MibIfRow2()
    row.interface_index = index
    try:
        if _api()(ctypes.byref(row)) != 0 or row.interface_index != index:
            return None
    except (OSError, AttributeError):
        return None
    hardware = bool(row.interface_flags & 0x01)
    connected = row.oper_status == 1 and row.media_connect_state == 1 and not row.interface_flags & 0x10
    return hardware, connected
