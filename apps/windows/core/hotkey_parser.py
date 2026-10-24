"""
全局热键解析与冲突检测模块

提供热键字符串的解析、合法性校验、格式化显示与已知冲突检测能力，
用于设置面板的热键录制与冲突警告。Win32 全局热键注册（RegisterHotKey）
仍由 ui 层负责，本模块仅提供纯逻辑计算，不依赖任何 UI 框架。

设计要点：
- 与原型 ../../docs/platforms/windows/prototype.html 第 5667-5751 行的 4 个函数逐字对齐
  （parseHotkey / isHotkeyMainKey / formatHotkeyDisplay / checkHotkeyConflict）。
- 舍弃原型的 matchHotkey：该函数接收 JS KeyboardEvent，Win 端 PySide6
  用 QKeyEvent + Qt.Key，匹配逻辑由 UI 层用 QKeySequence 原生实现更直接。
- 热键字符串存储格式：紧凑格式 'Alt+P'（主键大写，修饰键首字母大写，
  无空格）；显示格式：'Alt + P'（带空格，更易读）。
- 主键统一转小写比较（'P' 与 'p' 归一），存储时主键保留原大小写但
  parse 后 main 字段为小写。

算法规范（与原型 ../../docs/platforms/windows/prototype.html 第 5667-5751 行逐字对齐）：

parse_hotkey:
    空字符串/None → None
    按 '+' 分割，最后一段为主键（转小写），其余为修饰键（Ctrl/Alt/Shift）
    返回 ParsedHotkey(ctrl, alt, shift, main)

is_hotkey_main_key:
    允许：字母 a-z / 数字 0-9 / F1-F12 / ` - = [ ] \\ ; ' , . / Space Tab Enter Backspace
    拒绝：单独按修饰键（Ctrl/Alt/Shift）、其他功能键

format_hotkey_display:
    'Alt+P' → 'Alt + P'（仅显示用，存储仍用紧凑格式）

check_hotkey_conflict:
    查 HOTKEY_CONFLICTS 静态表，返回 HotkeyConflict(conflict, desc)
"""

from dataclasses import dataclass


@dataclass
class ParsedHotkey:
    """解析后的热键结构。

    Attributes:
        ctrl: 是否含 Ctrl 修饰键
        alt: 是否含 Alt 修饰键
        shift: 是否含 Shift 修饰键
        win: 是否含 Windows 修饰键
        main: 主键（小写），如 'p' / 'f1' / 'space'
    """
    ctrl: bool
    alt: bool
    shift: bool
    win: bool
    main: str


@dataclass
class HotkeyConflict:
    """热键冲突检测结果。

    Attributes:
        conflict: 是否冲突
        desc: 冲突描述（冲突时为软件/系统名，无冲突时为空字符串）
    """
    conflict: bool
    desc: str = ""


# 已知冲突热键表 —— 用于录制时检测冲突并警告用户
# 来源：Windows 11 系统 + 1Password/KeePass/Bitwarden + 输入法 + QQ/微信/Snipaste
# ⚠️ 此表为静态参考，无法覆盖所有软件（用户可能装了其他全局热键软件），
#    Win 端 RegisterHotKey 失败时也会提示"热键被占用"——双重保险
HOTKEY_CONFLICTS = {
    # Windows 系统
    'Alt+Tab': 'Windows 任务切换',
    'Alt+F4': 'Windows 关闭窗口',
    'Alt+Space': 'Windows 窗口菜单',
    'Ctrl+Alt+Del': 'Windows 安全选项',
    'Win+L': 'Windows 锁屏',
    'Win+D': 'Windows 显示桌面',
    'Win+E': 'Windows 资源管理器',
    'Win+R': 'Windows 运行',
    'Win+S': 'Windows 搜索',
    'Win+V': 'Windows 剪贴板历史',
    'Win+Shift+S': 'Windows 截图',
    'Win+Space': 'Windows 输入法切换',
    'Win+Tab': 'Windows 任务视图',
    # 输入法
    'Ctrl+Space': '输入法中英切换（常见）',
    'Ctrl+Shift': '输入法切换（部分输入法）',
    # 1Password
    'Ctrl+Shift+Space': '1Password Quick Access',
    # KeePass / QQ（两者共用 Ctrl+Alt+A，合并描述）
    'Ctrl+Alt+A': 'KeePass Auto-Type / QQ 截图',
    # Bitwarden
    'Ctrl+Shift+L': 'Bitwarden 自动填充',
    'Ctrl+Shift+9': 'Bitwarden 生成密码',
    # QQ
    'Ctrl+Alt+Z': 'QQ 提取消息',
    'Ctrl+Alt+O': 'QQ 翻译',
    # 微信
    'Alt+A': '微信截图',
    # Snipaste
    'F1': 'Snipaste 截图',
    'F3': 'Snipaste 贴图',
}

# is_hotkey_main_key 允许的符号/功能键集合（与原型第 5696 行逐字对齐）
_MAIN_KEY_SYMBOLS = frozenset({
    '`', '-', '=', '[', ']', '\\', ';', "'", ',', '.', '/', ' ',
    'tab', 'enter', 'backspace',
})


def parse_hotkey(s: str) -> ParsedHotkey | None:
    """解析热键字符串为 ParsedHotkey 结构。

    - 空字符串 / None → None
    - 按 '+' 分割，最后一段为主键（转小写），其余为修饰键（Ctrl/Alt/Shift/Win）
    - 拒绝空段、未知修饰键和重复修饰键

    Args:
        s: 热键字符串，如 'Alt+P' / 'Ctrl+Shift+L' / 'F1'
    Returns:
        ParsedHotkey 或 None（输入无效时）
    """
    if not s or not isinstance(s, str):
        return None
    parts = [p.strip() for p in s.split('+')]
    if not parts or any(not part for part in parts):
        return None
    main = parts.pop().lower()
    allowed_modifiers = {"Ctrl", "Alt", "Shift", "Win"}
    if (
        not main
        or any(part not in allowed_modifiers for part in parts)
        or len(set(parts)) != len(parts)
    ):
        return None
    return ParsedHotkey(
        ctrl='Ctrl' in parts,
        alt='Alt' in parts,
        shift='Shift' in parts,
        win='Win' in parts,
        main=main,
    )


def is_hotkey_main_key(key: str) -> bool:
    """校验主键合法性：录制时只接受有意义的主键，拒绝单独按修饰键。

    允许：字母 a-z / 数字 0-9 / F1-F12 / ` - = [ ] \\ ; ' , . / Space Tab Enter Backspace
    拒绝：单独按修饰键（Ctrl/Alt/Shift）、其他功能键

    Args:
        key: 主键字符串（如 'a' / 'F1' / 'space'），大小写不敏感。
    Returns:
        True 合法，False 非法。
    """
    if not key or not isinstance(key, str):
        return False
    k = key.lower()
    # 字母数字（单字符）
    if len(k) == 1 and k.isalnum():
        return True
    # F1-F12
    if len(k) >= 2 and k[0] == 'f' and k[1:].isdigit():
        num = int(k[1:])
        if 1 <= num <= 12:
            return True
    # 符号/功能键
    return k in _MAIN_KEY_SYMBOLS


def format_hotkey_display(s: str) -> str:
    """格式化热键字符串为本地化显示：'Alt+P' → 'Alt + P'。

    仅显示用，存储仍用紧凑格式。

    Args:
        s: 热键字符串，如 'Alt+P'
    Returns:
        格式化后的显示字符串，如 'Alt + P'；空输入返回空字符串。
    """
    if not s:
        return ''
    return ' + '.join(p.strip() for p in s.split('+'))


def check_hotkey_conflict(hotkey: str) -> HotkeyConflict:
    """检测热键是否与已知软件/系统冲突。

    查 HOTKEY_CONFLICTS 静态表，命中返回冲突描述。
    ⚠️ 静态表无法覆盖所有软件，Win 端 RegisterHotKey 失败时也应提示
    "热键被占用"——双重保险。

    Args:
        hotkey: 热键字符串，如 'Ctrl+Shift+Space'
    Returns:
        HotkeyConflict(conflict=True, desc='1Password Quick Access') 或
        HotkeyConflict(conflict=False)（无冲突）
    """
    if not hotkey:
        return HotkeyConflict(conflict=False)
    desc = HOTKEY_CONFLICTS.get(hotkey)
    if desc:
        return HotkeyConflict(conflict=True, desc=desc)
    return HotkeyConflict(conflict=False)
