"""固定助手使用 Windows 防火墙 COM 接口；不加载产品数据或界面。"""
from __future__ import annotations

import ctypes
import hashlib
import os
import sys
import types


RULE_GROUP = "Cangoo.LocalTransfer.v1"
RULE_DESCRIPTION = "Cangoo local device transfer; this executable; LocalSubnet; Private/Public."
RESULT_CODES = {"READY": 0, "REQUIRED": 11, "BLOCKED": 12, "FAILED": 13}


def rule_names(executable: str) -> tuple[str, str]:
    digest = hashlib.sha256(os.path.normcase(executable).encode("utf-8")).hexdigest()[:24]
    return tuple(f"{RULE_GROUP}.{digest}.{protocol}" for protocol in ("TCP", "UDP"))


def _dynamic_client():
    import comtypes

    # 在 client 初始化前隔离生成包，提权进程不搜索用户缓存中的 Python 代码。
    generated = types.ModuleType("comtypes.gen")
    generated.__path__ = []
    sys.modules["comtypes.gen"] = generated
    comtypes.gen = generated
    import comtypes.client as client

    client.gen_dir = None
    generated.__path__ = []
    return client


def _profiles_blocked(client) -> bool:
    locator = client.CreateObject("WbemScripting.SWbemLocator", dynamic=True)
    service = locator.ConnectServer(".", r"root\standardcimv2")
    context = client.CreateObject("WbemScripting.SWbemNamedValueSet", dynamic=True)
    # NetSecurity CDXML 的 PolicyStore 查询选项，传给同一 CIM 提供器。
    context.Add("PolicyStore", "ActiveStore", 0)
    rows = service.ExecQuery(
        "SELECT * FROM MSFT_NetFirewallProfile WHERE Name='Private' OR Name='Public'",
        "WQL", 48, context,
    )
    profiles = {}
    for row in rows:
        name = row.Properties_.Item("Name").Value
        values = tuple(row.Properties_.Item(key).Value
                       for key in ("AllowLocalFirewallRules", "AllowInboundRules"))
        if name not in {"Private", "Public"} or name in profiles or any(value not in (0, 1, 2) for value in values):
            raise ValueError("PROFILE_UNAVAILABLE")
        profiles[name] = values
    if set(profiles) != {"Private", "Public"}:
        raise ValueError("PROFILE_UNAVAILABLE")
    return any(0 in values for values in profiles.values())


def _same_application(rule, executable: str) -> bool:
    return os.path.normcase(os.path.expandvars(rule.ApplicationName or "")) == os.path.normcase(executable)


def _is_owned(rule, executable: str, index: int) -> bool:
    return (
        rule is not None and _same_application(rule, executable)
        and rule.Grouping == RULE_GROUP and rule.Description == RULE_DESCRIPTION
        and rule.Protocol == (6, 17)[index] and rule.Direction == 1
        and rule.Action == 1 and rule.Profiles == 6
        and not rule.ServiceName and rule.InterfaceTypes == "All" and not rule.Interfaces
        and not rule.EdgeTraversal and rule.LocalPorts in ("", "*")
        and rule.RemotePorts in ("", "*") and rule.LocalAddresses in ("", "*")
        and rule.RemoteAddresses == "LocalSubnet"
    )


def _blocks_application(rule, executable: str) -> bool:
    # 只判断明确覆盖完整通信范围的阻止项，不猜测局部端口、地址或接口规则。
    return (
        rule.Enabled and rule.Direction == 1 and rule.Action == 0
        and rule.Profiles & 6 and rule.Protocol in (6, 17, 256)
        and (_same_application(rule, executable) or rule.ApplicationName in ("", "*"))
        and not rule.ServiceName and rule.InterfaceTypes == "All" and not rule.Interfaces
        and rule.LocalAddresses in ("", "*")
        and (rule.Protocol == 256 or (rule.LocalPorts in ("", "*") and rule.RemotePorts in ("", "*")))
        and rule.RemoteAddresses in ("", "*", "LocalSubnet")
    )


class _RuleCollision(Exception):
    pass


def _owned_rule(rules, executable: str, index: int):
    name = rule_names(executable)[index].casefold()
    owned = None
    for rule in rules:
        if rule.Name.casefold() != name:
            continue
        if owned is not None or not _is_owned(rule, executable, index):
            raise _RuleCollision()
        owned = rule
    return owned


def _read_owned(rules, executable: str):
    return [_owned_rule(rules, executable, index) for index in range(2)]


def _read_state(policy, client, executable: str) -> str:
    if _profiles_blocked(client) or any(policy.BlockAllInboundTraffic[index] for index in (2, 4)):
        return "BLOCKED"
    if any(_blocks_application(rule, executable) for rule in policy.Rules):
        return "BLOCKED"
    owned = _read_owned(policy.Rules, executable)
    return "READY" if all(rule is not None and rule.Enabled for rule in owned) else "REQUIRED"


def _new_owned(client, executable: str, index: int):
    rule = client.CreateObject("HNetCfg.FWRule", dynamic=True)
    values = {
        "Name": rule_names(executable)[index], "Description": RULE_DESCRIPTION,
        "ApplicationName": executable, "Grouping": RULE_GROUP, "Protocol": (6, 17)[index],
        "LocalPorts": "*", "RemotePorts": "*", "LocalAddresses": "*",
        "RemoteAddresses": "LocalSubnet", "Direction": 1, "Profiles": 6,
        "InterfaceTypes": "All", "EdgeTraversal": False, "Action": 1, "Enabled": True,
    }
    for name, value in values.items():
        setattr(rule, name, value)
    return rule


def _change(policy, client, executable: str, mode: str) -> str:
    rules = policy.Rules
    names = rule_names(executable)
    original = _read_owned(rules, executable)
    enabled = [bool(rule.Enabled) if rule is not None else False for rule in original]
    changed = []
    try:
        for index in range(2):
            current = _owned_rule(rules, executable, index)
            if mode == "grant":
                if current is None:
                    fresh = _new_owned(client, executable, index)
                    changed.append(index)
                    rules.Add(fresh)
                elif not current.Enabled:
                    changed.append(index)
                    current.Enabled = True
            elif current is not None:
                changed.append(index)
                rules.Remove(names[index])
        if mode == "grant":
            if _read_state(policy, client, executable) != "READY":
                raise ValueError("NOT_EFFECTIVE")
            return "READY"
        if any(rule is not None for rule in _read_owned(rules, executable)):
            raise ValueError("NOT_REMOVED")
        return "REQUIRED"
    except Exception:
        # 包含调用失败但实际已生效的情况；回滚前仍重新验证完整自有范围。
        for index in reversed(changed):
            try:
                current = _owned_rule(rules, executable, index)
                if original[index] is None:
                    if current is not None:
                        rules.Remove(names[index])
                elif mode == "revoke":
                    if current is None:
                        rules.Add(original[index])
                elif current is not None:
                    current.Enabled = enabled[index]
            except Exception:
                pass
        return "FAILED"


def run_native(executable: str, mode: str) -> int:
    """只在固定助手主线程调用；对象释放后由 comtypes 的进程退出钩子结束 COM。"""
    if mode not in {"check", "grant", "revoke"}:
        return RESULT_CODES["FAILED"]
    try:
        if mode != "check":
            shell = ctypes.WinDLL("shell32", use_last_error=True)
            shell.IsUserAnAdmin.argtypes = []
            shell.IsUserAnAdmin.restype = ctypes.c_int
            if not shell.IsUserAnAdmin():
                return RESULT_CODES["FAILED"]
        client = _dynamic_client()
        policy = client.CreateObject("HNetCfg.FwPolicy2", dynamic=True)
        if mode == "check":
            result = _read_state(policy, client, executable)
        elif mode == "grant" and _read_state(policy, client, executable) == "BLOCKED":
            result = "BLOCKED"
        else:
            result = _change(policy, client, executable, mode)
        return RESULT_CODES[result]
    except _RuleCollision:
        return RESULT_CODES["BLOCKED"]
    except Exception:
        return RESULT_CODES["FAILED"]
