"""
TOTP 生成模块

提供基于 RFC 6238 的 TOTP（基于时间的一次性密码）生成能力，用于密码记录
中绑定的两步验证（2FA）密钥的实时验证码生成。

设计要点：
- core 层纯净，不依赖任何 UI 框架（PyQt5/PySide6），也不依赖 core 层其他
  模块，仅使用 Python 标准库（hmac / hashlib / base64 / struct / time）。
- 生成结果为结构化 `TOTPResult` 对象（dataclass），含 code（6 位数字字符串）
  与 remaining（当前 30s 周期剩余秒数）两字段，便于调用方倒计时展示。
- HMAC-SHA1 使用标准库 hmac + hashlib 实现（原型因浏览器环境限制手写 SHA1，
  Python 有标准库，禁止手写）。
- Base32 解码使用标准库 base64.b32decode，对非法字符严格报错并返回 None。
  原型 base32Decode 对非法字符采用 `continue` 跳过的宽松行为，此处改为
  严格校验——静默跳过会从损坏的密钥生成错误验证码，存在安全风险，且任务
  约定明确要求含非法字符时返回 None。

算法规范（与原型 ../../docs/platforms/windows/prototype.html generateTOTP 逐字对齐）：
- 时间步长：30 秒
- 验证码位数：6 位
- counter  = floor(unix_time / 30)
- remaining = 30 - (unix_time % 30)
- HOTP：counter 转 8 字节大端（struct.pack('>Q', counter)）
        → HMAC-SHA1(key, msg)
        → 动态截取：offset = hash[-1] & 0x0f
          binary = ((hash[offset]   & 0x7f) << 24)
                 | ((hash[offset+1] & 0xff) << 16)
                 | ((hash[offset+2] & 0xff) <<  8)
                 |  (hash[offset+3] & 0xff)
        → code = str(binary % 1000000).zfill(6)
"""

import base64
import hashlib
import hmac
import struct
import time
from dataclasses import dataclass
from typing import Optional


@dataclass
class TOTPResult:
    """TOTP 生成结果。

    Attributes:
        code: 6 位数字字符串（如 "123456"），左填充 0。
        remaining: 当前 30s 周期剩余秒数（1-30）。
    """

    code: str
    remaining: int


class TOTPTool:
    """TOTP 生成工具类（全部为静态方法）。"""

    # 时间步长（秒），与 RFC 6238 / 原型一致
    TIME_STEP = 30
    # 验证码位数
    DIGITS = 6

    @staticmethod
    def generate_totp(secret: str) -> Optional[TOTPResult]:
        """生成当前 TOTP 码 + 剩余秒数。

        Args:
            secret: Base32 编码的 TOTP 密钥（如 "JBSWY3DPEHPK3PXP"）。
                支持小写、含空格、含 '=' 填充（内部自动清理）。
        Returns:
            TOTPResult 或 None（secret 为空或 Base32 解码失败时返回 None）。
        """
        if not secret:
            return None

        key = TOTPTool._base32_decode(secret)
        if key is None:
            return None

        now = int(time.time())
        counter = now // TOTPTool.TIME_STEP
        remaining = TOTPTool.TIME_STEP - (now % TOTPTool.TIME_STEP)

        code = TOTPTool._hotp(key, counter)
        return TOTPResult(code=code, remaining=remaining)

    @staticmethod
    def format_totp_code(code: str) -> str:
        """格式化 6 位码为 "123 456"（两组，空格分隔，易读）。

        非 6 位码原样返回（不处理）。
        """
        if not code or len(code) != 6:
            return code
        return code[:3] + ' ' + code[3:]

    # ------------------------------------------------------------------
    # 内部辅助方法
    # ------------------------------------------------------------------

    @staticmethod
    def _base32_decode(secret: str) -> Optional[bytes]:
        """解码 Base32 密钥为原始字节。

        清理流程：转大写 → 去除所有空白 → 去除 '=' 填充 → 补齐到 8 的倍数
        长度 → base64.b32decode。任何非法字符（如 '1'/'0'/'8'/'9'）或
        长度异常均返回 None。

        Args:
            secret: Base32 编码字符串（含可能的空格/小写/填充）。
        Returns:
            解码后的原始字节，或 None（解码失败）。
        """
        # 转大写 + 去除所有空白字符 + 去除 '=' 填充
        cleaned = ''.join(secret.split()).upper().replace('=', '')
        if not cleaned:
            return None
        # 补齐 Base32 标准填充（长度需为 8 的倍数）
        pad_len = (-len(cleaned)) % 8
        cleaned += '=' * pad_len
        try:
            return base64.b32decode(cleaned)
        except Exception:
            return None

    @staticmethod
    def _hotp(key: bytes, counter: int) -> str:
        """HOTP 核心算法（RFC 4226）。

        Args:
            key: 解码后的密钥字节。
            counter: 计数器值（TOTP 中为 time // 30）。
        Returns:
            6 位数字字符串（左填充 0）。
        """
        # counter 转 8 字节大端
        msg = struct.pack('>Q', counter)
        # HMAC-SHA1
        h = hmac.new(key, msg, hashlib.sha1).digest()
        # 动态截取
        offset = h[-1] & 0x0f
        binary = (
            ((h[offset] & 0x7f) << 24)
            | ((h[offset + 1] & 0xff) << 16)
            | ((h[offset + 2] & 0xff) << 8)
            | (h[offset + 3] & 0xff)
        )
        return str(binary % (10 ** TOTPTool.DIGITS)).zfill(TOTPTool.DIGITS)
