"""通用恢复码的有界文本解析与结构校验；不验证服务端有效性。"""

from __future__ import annotations

import json


MAX_CODES = 128
MAX_CHARACTERS = 8192
MAX_BYTES = 32768
MAX_CODE_CHARACTERS = 1024
MAX_CODE_BYTES = 4096


class RecoveryCodeError(ValueError):
    """固定错误原因及行号，不包含码值。"""

    def __init__(self, reason: str, line: int = 0) -> None:
        super().__init__(reason)
        self.line = line


def _bounded(value: str, characters: int, byte_limit: int) -> bool:
    try:
        return len(value) <= characters and len(value.encode("utf-8")) <= byte_limit
    except UnicodeError:
        return False


def validate_codes(value: object) -> list[dict[str, object]]:
    """严格验证集合并返回独立副本，保留原码和本地标记。"""
    if type(value) is not list or len(value) > MAX_CODES:
        raise RecoveryCodeError("RECOVERY_CODES_LIMIT")
    seen: set[str] = set()
    result: list[dict[str, object]] = []
    for line, item in enumerate(value, 1):
        if type(item) is not dict or set(item) != {"value", "used"}:
            raise RecoveryCodeError("RECOVERY_CODES_INVALID", line)
        code = item["value"]
        if (type(code) is not str or not code or code != code.strip()
                or any(ord(character) < 32 or ord(character) == 127 for character in code)
                or type(item["used"]) is not bool):
            raise RecoveryCodeError("RECOVERY_CODES_INVALID", line)
        if not _bounded(code, MAX_CODE_CHARACTERS, MAX_CODE_BYTES):
            raise RecoveryCodeError("RECOVERY_CODES_LIMIT", line)
        if code in seen:
            raise RecoveryCodeError("RECOVERY_CODES_DUPLICATE", line)
        seen.add(code)
        result.append({"value": code, "used": item["used"]})
    text = "\n".join(item["value"] for item in result)
    if not _bounded(text, MAX_CHARACTERS, MAX_BYTES):
        raise RecoveryCodeError("RECOVERY_CODES_LIMIT")
    return result


def parse_codes(text: str) -> list[dict[str, object]]:
    """整组录入：一行一个，忽略空行，新组全部未标记。"""
    if type(text) is not str or not _bounded(text, MAX_CHARACTERS, MAX_BYTES):
        raise RecoveryCodeError("RECOVERY_CODES_LIMIT")
    # 只接受常规换行；其他控制字符仍由结构校验拒绝。
    lines = text.replace("\r\n", "\n").split("\n")
    result = []
    seen: set[str] = set()
    for line, value in enumerate(lines, 1):
        code = value.strip()
        if not code:
            continue
        try:
            validate_codes([{"value": code, "used": False}])
        except RecoveryCodeError as exc:
            raise RecoveryCodeError(str(exc), line) from None
        if code in seen:
            raise RecoveryCodeError("RECOVERY_CODES_DUPLICATE", line)
        seen.add(code)
        result.append({"value": code, "used": False})
        if len(result) > MAX_CODES:
            raise RecoveryCodeError("RECOVERY_CODES_LIMIT", line)
    return validate_codes(result)


def dump_codes(value: object) -> str:
    """生成加密前的规范结构化文本。"""
    return json.dumps(validate_codes(value), ensure_ascii=False, separators=(",", ":"))


def load_codes(text: str) -> list[dict[str, object]]:
    """认证解密后仍严格检查结构；损坏不解释为空。"""
    if type(text) is not str or not _bounded(text, 65536, 65536):
        raise RecoveryCodeError("RECOVERY_CODES_LIMIT")
    try:
        value = json.loads(text)
    except (ValueError, TypeError, RecursionError):
        raise RecoveryCodeError("RECOVERY_CODES_INVALID") from None
    return validate_codes(value)
