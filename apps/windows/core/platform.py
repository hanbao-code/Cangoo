"""
平台视觉标识生成模块

提供平台名（如 "GitHub" / "淘宝"）的视觉标识生成能力，用于密码列表
头像位的"首字母 + 哈希色块"渲染：同一平台名始终生成相同的首字母与
背景色，便于用户在列表中快速定位。

设计要点：
- core 层纯净，不依赖任何 UI 框架（PyQt5/PySide6），也不依赖 core 层其他
  模块，仅使用 Python 标准库（math）。
- 两个函数均为纯函数（无副作用、无状态），适合直接调用或包裹为静态方法。
- 颜色生成与原型 ../../docs/platforms/windows/prototype.html 的 platformColor 逐字对齐，包括
  JS 32 位有符号整数 `<<` 运算的溢出截断行为（详见 platform_color 文档）。
- 首字母取 name 的第一个字符（Python `name[0]`，对 BMP 字符与 JS
  `charAt(0)` 等价；对 BMP 外字符（如部分 emoji）Python 返回完整码点，
  JS 返回高代理项，但平台名极少含此类字符，差异可忽略）。

算法规范（与原型 ../../docs/platforms/windows/prototype.html 第 3952-3985 行逐字对齐）：

platformIcon:
    空字符串/None → '?'
    否则取首字符并转大写（ASCII 字母转大写，其余字符原样返回）

platformColor:
    空字符串/None → '#6366f1'（默认紫色）
    哈希：
        hash = 0
        for ch in name:
            hash = ord(ch) + ((hash << 5) - hash)
        hue = abs(hash) % 360
    HSL→hex（s=0.55, l=0.52，6 档 hue 分支）：
        c = (1 - abs(2*l - 1)) * s
        x = c * (1 - abs((hue/60) % 2 - 1))
        m = l - c/2
        根据 hue 区间分配 (r,g,b) ∈ {(c,x,0),(x,c,0),(0,c,x),
                                     (0,x,c),(x,0,c),(c,0,x)}
        hex = '#rrggbb'（每通道 round((v+m)*255) 转 2 位小写 hex）
"""

import math


def platform_icon(name: str) -> str:
    """返回平台名的首字母大写作为视觉标识。

    - 空字符串 / None → '?'
    - 否则取 name 的第一个字符（与 JS `name.charAt(0)` 等价），转大写。
      ASCII 字母转大写，非 cased 字符（中文/数字/符号）原样返回。
    - 不做长度截断，仅取首字符。

    Args:
        name: 平台名（如 "GitHub" / "淘宝" / "Gmail"）。
    Returns:
        单字符标识（大写），或 '?'（输入为空）。
    """
    if not name:
        return '?'
    return name[0].upper()


def platform_color(name: str) -> str:
    """基于平台名哈希生成稳定的 HSL 颜色，返回 hex 字符串。

    - 空字符串 / None → '#6366f1'（默认紫色）
    - 哈希算法与原型 ../../docs/platforms/windows/prototype.html platformColor 逐字对齐：
        hash = 0
        for ch in name:
            hash = ord(ch) + ((hash << 5) - hash)
        hue = abs(hash) % 360
    - HSL→hex：s=0.55, l=0.52，标准 RGB 转换，返回 '#rrggbb'（小写 hex）。
    - 稳定性：同一名称始终返回相同颜色（纯函数，无随机性）。

    JS 32 位整数运算对齐说明：
        JS 的 `<<` 是 32 位有符号整数运算：先将左操作数 ToInt32，左移后
        再截断到 32 位有符号整数。Python int 无限精度，若不模拟此截断，
        相同名称会因累积溢出差异生成不同 hue，导致与原型颜色不一致。
        本实现用 `_js_to_int32` + `_js_lshift5` 精确模拟：仅 `<<` 操作
        截断到 32 位有符号整数，hash 累加本身不截断（与 JS Number 行为一致）。

    Args:
        name: 平台名。
    Returns:
        '#rrggbb' 格式的小写 hex 颜色字符串。
    """
    if not name:
        return '#6366f1'

    # 哈希：与 JS 逐字对齐（仅 << 5 做 32 位有符号截断）
    hash_val = 0
    for ch in name:
        hash_val = ord(ch) + (_js_lshift5(hash_val) - hash_val)
    hue = abs(hash_val) % 360

    # HSL → RGB（s=0.55, l=0.52，与原型逐字对齐）
    s = 0.55
    l = 0.52
    c = (1 - abs(2 * l - 1)) * s
    x = c * (1 - abs((hue / 60) % 2 - 1))
    m = l - c / 2

    if hue < 60:
        r, g, b = c, x, 0
    elif hue < 120:
        r, g, b = x, c, 0
    elif hue < 180:
        r, g, b = 0, c, x
    elif hue < 240:
        r, g, b = 0, x, c
    elif hue < 300:
        r, g, b = x, 0, c
    else:
        r, g, b = c, 0, x

    # JS Math.round 是 round-half-up；Python round() 用银行家舍入，
    # 用 math.floor(v + 0.5) 对齐（参考 core/health.py 的处理方式）。
    # '%02x' 等价于 JS toString(16).padStart(2, '0')。
    def _hex(v: float) -> str:
        return '%02x' % math.floor((v + m) * 255 + 0.5)

    return f'#{_hex(r)}{_hex(g)}{_hex(b)}'


# ------------------------------------------------------------------
# 内部辅助：JS 32 位有符号整数运算模拟
# ------------------------------------------------------------------


def _js_to_int32(value: int) -> int:
    """模拟 JS ToInt32：将值转为 32 位有符号整数。

    JS 的位运算符（如 `<<`）会先把操作数通过 ToInt32 转为 32 位有符号
    整数再运算。Python int 无限精度，需手动截断：

        1. 取低 32 位（& 0xFFFFFFFF）
        2. 若 ≥ 0x80000000（即最高位为 1），减 0x100000000 转为负数

    Args:
        value: 任意整数（可能超出 32 位范围）。
    Returns:
        32 位有符号整数（范围 -2147483648 ~ 2147483647）。
    """
    value = int(value) & 0xFFFFFFFF
    if value >= 0x80000000:
        value -= 0x100000000
    return value


def _js_lshift5(value: int) -> int:
    """模拟 JS `value << 5`（32 位有符号整数左移 5 位）。

    JS `<<` 流程：ToInt32(value) → 左移 5 位 → 结果截断到 32 位有符号整数。
    本实现两次调用 `_js_to_int32`：第一次对输入 ToInt32，第二次对左移
    结果（可能超出 32 位）截断回 32 位有符号整数。

    Args:
        value: 左移前的值（JS 侧为 Number，本实现接受任意 int）。
    Returns:
        左移 5 位后的 32 位有符号整数。
    """
    return _js_to_int32(_js_to_int32(value) << 5)
