"""
core.i18n — 国际化基础设施模块

提供轻量级 i18n 支持：翻译查表 + 语言切换 + 回调通知。

设计要点：
- core 层纯净，不依赖 PySide6（符合 AGENTS.md「core 层无 UI 依赖」原则）。
- 资源文件懒加载：首次访问某语言时从 core/i18n/{lang}.json 读取并缓存到模块级 dict。
- 兜底链：当前语言 → 默认语言（zh）→ key 本身（便于发现遗漏，不抛异常）。
- 占位符替换：资源值用 {0} / {1} 位置占位符，t(key, *args) 用 str.format(*args) 替换；
  args 不足时原样返回模板（含占位符），不抛异常。
- 语言变更通过回调机制通知 UI 层（on_language_changed），core 自己不操作 UI。
- 幂等：重复设置同语言不触发回调。
"""

from __future__ import annotations

import json
import logging
import os
from typing import Callable

logger = logging.getLogger(__name__)

# ── 模块级常量 ──
DEFAULT_LANGUAGE: str = "zh"
SUPPORTED_LANGUAGES: list[str] = ["zh", "en"]

# 资源文件目录（相对于本模块文件：core/i18n/{lang}.json）
_I18N_DIR: str = os.path.join(os.path.dirname(__file__), "i18n")

# ── 模块级状态（单例）──
_current_language: str = DEFAULT_LANGUAGE
_translations_cache: dict[str, dict[str, str]] = {}
_callbacks: list[Callable[[], None]] = []


def _load_translations(lang: str) -> dict[str, str]:
    """内部方法：从 core/i18n/{lang}.json 加载翻译表并缓存。

    文件不存在或解析失败时返回 {} 并记日志（不抛异常，t() 会兜底返回 key 本身）。
    """
    if lang in _translations_cache:
        return _translations_cache[lang]

    file_path = os.path.join(_I18N_DIR, f"{lang}.json")
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            _translations_cache[lang] = data
            return data
        logger.warning(
            "i18n resource file %s is not a JSON object, fallback to empty dict",
            file_path,
        )
        _translations_cache[lang] = {}
        return {}
    except FileNotFoundError:
        logger.warning(
            "i18n resource file not found: %s, fallback to empty dict", file_path
        )
        _translations_cache[lang] = {}
        return {}
    except (json.JSONDecodeError, OSError) as e:
        logger.warning(
            "Failed to load i18n resource %s: %s, fallback to empty dict",
            file_path,
            e,
        )
        _translations_cache[lang] = {}
        return {}


def load_translations(lang: str) -> dict[str, str]:
    """从 core/i18n/{lang}.json 加载翻译表并缓存（公开接口）。

    文件不存在或解析失败时返回 {} 并记日志（不抛异常）。
    重复调用返回缓存值。
    """
    return _load_translations(lang)


def _lookup(key: str) -> str:
    """内部方法：按兜底链查找翻译模板。

    兜底链：当前语言 → 默认语言（zh）→ key 本身。
    """
    current = _translations_cache.get(_current_language)
    if current is None:
        current = _load_translations(_current_language)
    if key in current:
        return current[key]

    # 回退到默认语言
    if _current_language != DEFAULT_LANGUAGE:
        default = _translations_cache.get(DEFAULT_LANGUAGE)
        if default is None:
            default = _load_translations(DEFAULT_LANGUAGE)
        if key in default:
            return default[key]

    # 兜底：返回 key 本身
    return key


def t(key: str, *args) -> str:
    """翻译函数。

    兜底链：当前语言 → 默认语言（zh）→ key 本身（便于发现遗漏，不抛异常）。

    支持占位符替换：t("topbar.button.quickbar", "Alt+P")
      → 资源值 "Quick Bar ({0})" 经 str.format(*args) 替换为 "Quick Bar (Alt+P)"。

    key 用点分命名，如 "topbar.button.quickbar" / "common.ok"。
    如果 args 数量不足导致 str.format 抛 IndexError/KeyError，原样返回模板。
    """
    template = _lookup(key)

    if not args:
        return template

    try:
        return template.format(*args)
    except (IndexError, KeyError, ValueError):
        # args 数量不足或占位符格式错误，原样返回模板
        return template


def set_language(lang: str) -> None:
    """切换当前语言（"zh" / "en"）。

    1. 更新内部 _current_language（传入不支持的语言时回退到 DEFAULT_LANGUAGE 并记日志）。
    2. 懒加载该语言的资源（首次切换时 _load_translations）。
    3. 按注册顺序触发所有已注册的 on_language_changed 回调（通知 UI 层重渲染）。

    幂等：重复设置同语言不触发回调。
    """
    global _current_language

    if lang not in SUPPORTED_LANGUAGES:
        logger.warning(
            "Unsupported language: %s, fallback to %s", lang, DEFAULT_LANGUAGE
        )
        lang = DEFAULT_LANGUAGE

    if lang == _current_language:
        # 幂等：同语言不触发回调
        return

    # 懒加载资源
    if lang not in _translations_cache:
        _load_translations(lang)

    _current_language = lang

    # 按注册顺序触发回调（try/except 包裹避免一个回调失败影响其他）
    for callback in list(_callbacks):
        try:
            callback()
        except Exception as e:  # noqa: BLE001 - 回调内异常不阻塞其他回调
            logger.warning(
                "on_language_changed callback raised: %s", e, exc_info=True
            )


def get_current_language() -> str:
    """返回当前语言代码（"zh" / "en"）。"""
    return _current_language


def on_language_changed(callback: Callable[[], None]) -> None:
    """注册语言变更回调。

    callback 签名：() -> None（无参数，由 ui 层自行遍历控件重渲染）。
    回调存储在内部 list，set_language 时按注册顺序触发。
    重复注册同一回调会被忽略（去重）。
    """
    if callback not in _callbacks:
        _callbacks.append(callback)


def off_language_changed(callback: Callable[[], None]) -> None:
    """注销回调（面板/窗口销毁时调用，避免悬挂引用）。

    callback 不存在时静默忽略。
    """
    try:
        _callbacks.remove(callback)
    except ValueError:
        pass


# ── 模块初始化：预加载默认语言资源 ──
_load_translations(DEFAULT_LANGUAGE)
