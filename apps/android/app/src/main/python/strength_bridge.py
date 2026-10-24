"""只校验通信边界并返回有限分数，评分核心直接来自Windows。"""
from core.password_tools import PasswordTools
import importlib.metadata
import sys


def runtime():
    return "/".join((sys.version.split()[0], importlib.metadata.version("zxcvbn"), importlib.metadata.version("pypinyin")))


def evaluate(password, platform, account):
    if (not all(type(value) is str for value in (password, platform, account))
            or not 0 <= len(password) <= 1024 or len(password.encode("utf-8")) > 4096
            or len(platform) > 32 or len(account) > 32
            or any("\0" in value for value in (password, platform, account))):
        raise ValueError("输入无效")
    result = PasswordTools.check_password_strength(password, platform, account, max_length=1024)
    expected = "weak" if result.score < 3 else "fair" if result.score == 3 else "strong"
    if type(result.score) is not int or result.score not in range(5) or result.level != expected:
        raise ValueError("结果无效")
    return str(result.score)
