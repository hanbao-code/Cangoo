"""安全随机生成与完整密码强度分析。

基础 zxcvbn 使用已有中文、拼音、泄露词典和平台/账号上下文分析完整密码。
同一次结果提供评级、猜测次数、时间估算和反馈；0–2 为弱，3 为中，4 为强。
原型共用相同评级语义；Python 与浏览器各自使用既有词典注入方式。
时间是预设攻击速度下的模型估算，不是本产品或目标网站的实测破解耗时。
core 不依赖 UI；兼容字段 downgraded 保留为 False。
"""

import os
import re
import secrets
import string
from dataclasses import dataclass, field
from datetime import datetime
from math import log

from zxcvbn import zxcvbn
from zxcvbn import feedback as zxcvbn_feedback
from zxcvbn import matching as zxcvbn_matching
from zxcvbn import scoring as zxcvbn_scoring
from zxcvbn import time_estimates as zxcvbn_time_estimates
from zxcvbn.matching import add_frequency_lists

from core.i18n import t


# ======================================================================
# 字典加载（模块加载时一次性注入 zxcvbn）
# ======================================================================

_DICT_DIR = os.path.join(os.path.dirname(__file__), "dictionaries")


def _load_dict(filename: str) -> list:
    """从 dictionaries/ 目录加载字典文件，每行一个词条。

    - 文件不存在时返回空列表（不报错，便于字典未就绪时模块仍可导入）
    - 自动跳过空行与以 # 开头的注释行
    - 全部小写化（zxcvbn 内部也会小写化，提前小写避免重复处理）
    """
    path = os.path.join(_DICT_DIR, filename)
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return [
            line.strip().lower()
            for line in f
            if line.strip() and not line.startswith("#")
        ]


# 模块加载时注入自定义字典（全局持久，跨调用生效）
# 三个字典文件位于同目录 dictionaries/ 下，由主代理复制就绪
add_frequency_lists({
    "pinyin_weak": _load_dict("pinyin.txt"),
    "chinese_phrases": _load_dict("phrases.txt"),
    "cn_leaked": _load_dict("leaked_cn.txt"),
})


# ======================================================================
# feedback 中文翻译表（方案文档第四章 4.4 节）
# ======================================================================

# 带 token 的 warning 翻译（{token} 由 sequence 中对应模式的命中子串填充）
_TOKEN_WARNING_MAP = {
    "This is a very common password": "命中常见弱密码: {token}",
    "This is similar to a commonly used password": "与常见弱密码相似: {token}",
    'Repeats like "abcabcabc" are only slightly harder to guess than "abc"': "包含重复模式: {token}",
    'Repeats like "aaa" are slightly harder to guess than "a"': "包含重复模式: {token}",
    "Sequences like abc or 6543 are easy to guess": "包含顺序字符模式: {token}",
    "Short keyboard patterns are easy to guess": "包含键盘走位模式: {token}",
}

# warning → 对应的 zxcvbn sequence 模式类型（用于定位 {token}）
_WARNING_PATTERN = {
    "This is a very common password": "dictionary",
    "This is similar to a commonly used password": "dictionary",
    'Repeats like "abcabcabc" are only slightly harder to guess than "abc"': "repeat",
    'Repeats like "aaa" are slightly harder to guess than "a"': "repeat",
    "Sequences like abc or 6543 are easy to guess": "sequence",
    "Short keyboard patterns are easy to guess": "spatial",
}

# 通用 warning 翻译（不含 token）
_GENERAL_WARNING_MAP = {
    "A word by itself is easy to guess": "单词本身容易猜测",
    "Names are easy to guess": "姓名容易被猜到",
    "Common names are easy to guess": "常见姓名容易被猜到",
    "This is a top-10 common password": "这是前 10 常见密码",
    "This is a top-100 common password": "这是前 100 常见密码",
    "Recent years are easy to guess": "近期年份容易被猜到",
    "Dates are often easy to guess": "日期往往容易猜测",
}

# suggestion 翻译
_SUGGESTION_MAP = {
    "Use a few words, avoid common phrases": "使用多个词，避免常见短语",
    "No need for symbols, digits, or uppercase letters": "无需符号、数字或大写字母",
    "Add another word or two": "增加一两个单词或字符",
    "Avoid repeated words and characters": "避免重复单词和字符",
    "Avoid sequences": "避免顺序字符",
    "Use a longer keyboard pattern with more turns": "使用更长的键盘走位（含更多转向）",
    "Avoid recent years": "避免使用近期年份",
    "Avoid years that are associated with you": "避免与你相关的年份",
    "Avoid dates and years that are associated with you": "避免与你相关的日期和年份",
    "Capitalization doesn't help very much": "仅靠首字母大写帮助不大",
    "All-uppercase is almost as easy to guess as all-lowercase": "全大写几乎和全小写一样容易猜",
    "Reversed words aren't much harder to guess": "反写单词并不能显著增加强度",
    "Predictable substitutions like '@' instead of 'a' don't help very much": "可预测的替换（如 @ 替换 a）帮助不大",
}

# 中文检测正则（CJK 统一表意文字）
_CJK_RE = re.compile(r"[\u4e00-\u9fff]")

@dataclass
class StrengthResult:
    """密码强度检测结果（基于 zxcvbn）。

    与原型 evaluateStrength 对齐，使用 zxcvbn 0-4 原始分 + 3 档严格映射。

    Attributes:
        level: 强度等级，"weak" / "fair" / "strong"（与原型对齐）。
        score: zxcvbn 原始分 0-4。
        feedback: 改进建议列表（中文，已翻译）。
        crack_times: 4 种攻击场景破解时间显示字符串（zxcvbn 原始英文，UI 层翻译）。
            键名与 zxcvbn crack_times_display 一致：
            - online_throttling_100_per_hour（在线攻击，有锁限 100/小时）
            - online_no_throttling_10_per_second（在线攻击，无锁限 10/秒）
            - offline_slow_hashing_1e4_per_second（离线慢哈希 10⁴/秒）
            - offline_fast_hashing_1e10_per_second（离线快哈希 10¹⁰/秒）
            空密码返回空 dict {}。
        guesses: 攻击者所需猜测次数（zxcvbn 估算）。
        downgraded: 保留的兼容字段，新分析结果恒为 False。
        feedback_codes: 不含输入片段的固定反馈码，供跨进程/UI 安全展示。
    """

    level: str
    score: int
    feedback: list[str] = field(default_factory=list)
    crack_times: dict = field(default_factory=dict)
    guesses: int = 0
    downgraded: bool = False
    feedback_codes: list[str] = field(default_factory=list)


class PasswordTools:
    """密码生成与强度检测工具类（基于 zxcvbn，全部为静态方法）。"""

    # 符号字符集（与原界面密码生成器保持一致）
    SYMBOLS = "!@#$%^&*()[]"

    # 易混字符集（avoid_ambiguous=True 时从生成字符集中排除）
    # 0/O、1/l/I 是最高频混淆对
    AMBIGUOUS_CHARS = frozenset("0O1lI")

    # ------------------------------------------------------------------
    # 密码生成（保留现有实现，与强度检测无关）
    # ------------------------------------------------------------------

    @staticmethod
    def generate_password(
        length: int = 16,
        use_upper: bool = True,
        use_lower: bool = True,
        use_digits: bool = True,
        use_symbols: bool = True,
        avoid_ambiguous: bool = False,
    ) -> str:
        """根据指定字符类型生成安全的随机密码。

        使用 secrets 模块（基于操作系统 CSPRNG）生成密码，保证每种选中的
        字符类型至少出现一次，最后用 SystemRandom 洗牌避免可预测模式。

        Args:
            length: 密码长度，默认 16。
            use_upper: 是否包含大写字母，默认 True。
            use_lower: 是否包含小写字母，默认 True。
            use_digits: 是否包含数字，默认 True。
            use_symbols: 是否包含符号，默认 True。
            avoid_ambiguous: 是否排除易混字符（0/O、1/l/I），默认 False。

        Returns:
            生成的随机密码字符串。

        Raises:
            ValueError: 未选择任何字符类型；长度不足以容纳所有必选字符；
                或 avoid_ambiguous 过滤后某选中字符集为空。
        """
        ambiguous = PasswordTools.AMBIGUOUS_CHARS
        chars = ""
        required_chars = []

        def pick(charset: str) -> str:
            """按 avoid_ambiguous 过滤字符集。"""
            if avoid_ambiguous:
                filtered = "".join(c for c in charset if c not in ambiguous)
                return filtered
            return charset

        if use_lower:
            cs = pick(string.ascii_lowercase)
            if not cs:
                raise ValueError("小写字母字符集过滤后为空，请关闭 avoid_ambiguous")
            chars += cs
            required_chars.append(secrets.choice(cs))

        if use_upper:
            cs = pick(string.ascii_uppercase)
            if not cs:
                raise ValueError("大写字母字符集过滤后为空，请关闭 avoid_ambiguous")
            chars += cs
            required_chars.append(secrets.choice(cs))

        if use_digits:
            cs = pick(string.digits)
            if not cs:
                raise ValueError("数字字符集过滤后为空，请关闭 avoid_ambiguous")
            chars += cs
            required_chars.append(secrets.choice(cs))

        if use_symbols:
            cs = pick(PasswordTools.SYMBOLS)
            if not cs:
                raise ValueError("符号字符集过滤后为空，请关闭 avoid_ambiguous")
            chars += cs
            required_chars.append(secrets.choice(cs))

        # 至少需要选择一种字符类型
        if not chars:
            raise ValueError("请至少选择一种字符类型")

        # 长度必须足以容纳每种选中字符类型至少一个
        if length < len(required_chars):
            raise ValueError(f"密码长度至少应为 {len(required_chars)} 位")

        # 先放入每种类型的必选字符，再随机填充剩余长度
        password = "".join(required_chars)
        for _ in range(length - len(required_chars)):
            password += secrets.choice(chars)

        # 洗牌以避免前若干位可预测
        password_list = list(password)
        secrets.SystemRandom().shuffle(password_list)
        return "".join(password_list)

    # ------------------------------------------------------------------
    # 密码强度检测（基于 zxcvbn）
    # ------------------------------------------------------------------

    @staticmethod
    def check_password_strength(
        password: str,
        platform: str = "",
        account: str = "",
        *,
        max_length: int = 1024,
    ) -> StrengthResult:
        """基于 zxcvbn 的密码强度检测。

        Args:
            password: 待检测密码。
            platform: 当前条目的平台名（如 'GitHub'、'淘宝'），用于 user_inputs 上下文。
            account: 当前条目的账号名（如 'user@example.com'），用于 user_inputs 上下文。

        Returns:
            StrengthResult: 结构化强度检测结果。
                空密码返回 level="weak", score=0, feedback=["密码不能为空"],
                crack_times={}（与原型 crackTimes:{} 一致）。

        算法流程（与 prototype.html evaluateStrength 逐字对齐）：
            1. _build_user_inputs(platform, account) — 中文转拼音 + 邮箱本地部分
            2. zxcvbn(password, user_inputs) — 核心评估
            3. _map_to_3levels(zxcvbn_score) — 严格映射 0-2→weak / 3→fair / 4→strong
            4. _build_feedback(zxcvbn_result) — 中文 issues 列表
            5. 从同一结果提取反馈码与四种攻击场景的时间估算
        """
        # 空密码快速返回（zxcvbn 对空串也能返回结果，但此处显式处理便于 UI 提示）
        if not password:
            return StrengthResult(
                level="weak",
                score=0,
                feedback=[t("password.feedback.empty")],
                crack_times={},
                guesses=0,
                downgraded=False,
                feedback_codes=["EMPTY"],
            )

        # 1. 构建 user_inputs（中文转拼音 + 邮箱本地部分 + 去重去空去超长）
        user_inputs = PasswordTools._build_user_inputs(platform, account)

        # 2. 调用 zxcvbn 核心评估
        result = PasswordTools._run_zxcvbn(
            password,
            user_inputs,
            max_length,
        )

        # 3. 评级映射（严格映射：0-2→weak / 3→fair / 4→strong）
        level = PasswordTools._map_to_3levels(result.get("score", 0))

        # 4. 构建中文 feedback
        feedback = PasswordTools._build_feedback(result)

        feedback_codes = PasswordTools._build_feedback_codes(password, result)

        # 5. 提取 4 种攻击场景破解时间（zxcvbn 原始英文，UI 层翻译）
        # 与原型 evaluateStrength 的 crackTimes: result.crack_times_display 对齐
        crack_times = dict(result.get("crack_times_display", {}) or {})

        return StrengthResult(
            level=level,
            score=result.get("score", 0),
            feedback=feedback,
            crack_times=crack_times,
            # zxcvbn 返回 Decimal，统一转为 int（Python int 无限精度，无溢出）
            guesses=int(result.get("guesses", 0)),
            downgraded=False,
            feedback_codes=feedback_codes,
        )

    @staticmethod
    def _run_zxcvbn(
        password: str,
        user_inputs: list[str],
        max_length: int,
    ) -> dict:
        """按原评分公式加速 129–1024 位纯重复串，其余输入运行完整算法。

        当前匹配器只为纯重复串产出整串重复项。排除半串以上的字典词后，
        多段候选代价均高于整串重复的 12*n+1 上界；换行不匹配上游重复正则。
        因此长度、换行和动态字典护栏不可放宽，升级上游算法时须复核差分。
        """
        length = len(password)
        if (
            not 128 < length <= min(max_length, 1024)
            or password[0] == "\n"
            or password.count(password[0]) != length
        ):
            return zxcvbn(
                password,
                user_inputs=user_inputs,
                max_length=max_length,
            )

        started = datetime.now()
        base_result = zxcvbn(
            password[0],
            user_inputs=user_inputs,
            max_length=max_length,
        )
        longest_dictionary_word = max(
            (
                len(word)
                for ranked in zxcvbn_matching.RANKED_DICTIONARIES.values()
                for word in ranked
            ),
            default=0,
        )
        if longest_dictionary_word >= (length + 1) // 2:
            return zxcvbn(
                password,
                user_inputs=user_inputs,
                max_length=max_length,
            )

        match = {
            "pattern": "repeat",
            "i": 0,
            "j": length - 1,
            "token": password,
            "base_token": password[0],
            "base_guesses": base_result["guesses"],
            "base_matches": base_result["sequence"],
            "repeat_count": length / 1,
        }
        guesses = zxcvbn_scoring.estimate_guesses(match, password) + 1
        result = {
            "password": password,
            "guesses": guesses,
            "guesses_log10": log(guesses, 10),
            "sequence": [match],
            "calc_time": datetime.now() - started,
        }
        result.update(zxcvbn_time_estimates.estimate_attack_times(guesses))
        result["feedback"] = zxcvbn_feedback.get_feedback(
            result["score"], result["sequence"]
        )
        return result

    # ------------------------------------------------------------------
    # user_inputs 处理（方案文档第四章 4.2 节）
    # ------------------------------------------------------------------

    @staticmethod
    def _build_user_inputs(platform: str, account: str) -> list:
        """从平台名/账号名构建 zxcvbn user_inputs。

        策略：
        - platform 和 account 都为空 → 返回空列表（zxcvbn 不注入 user_inputs）
        - 中文平台/账号 → 转拼音 + 保留原中文（双重覆盖）
        - 英文平台/账号 → 小写后传入（zxcvbn 内部也会小写化，此处提前小写与边界矩阵对齐）
        - 邮箱账号 → 完整邮箱 + 提取本地部分（@ 前部分）
        - 去重、去空、去超长（>32 字符的忽略，避免噪声）

        边界处理矩阵见方案文档 4.2 节。
        """
        inputs = []
        seen = set()

        def add(text: str) -> None:
            """去重添加（已小写化）。空串与超长（>32）忽略。"""
            if not text or len(text) > 32:
                return
            if text in seen:
                return
            seen.add(text)
            inputs.append(text)

        for field_value in (platform, account):
            if not field_value or len(field_value) > 32:
                continue

            # 中文转拼音：含 CJK 字符时，保留原中文 + 追加拼音
            if _CJK_RE.search(field_value):
                add(field_value.lower())  # 原中文（lower 对中文为 no-op）
                from pypinyin import lazy_pinyin

                pinyin = "".join(lazy_pinyin(field_value)).lower()
                if pinyin:
                    add(pinyin)
            else:
                add(field_value.lower())

            # 邮箱账号：提取本地部分（@ 前部分）
            if "@" in field_value:
                local_part = field_value.split("@", 1)[0].lower()
                if local_part:
                    add(local_part)

        return inputs

    # ------------------------------------------------------------------
    # 评级映射（方案文档第四章 4.3 节）
    # ------------------------------------------------------------------

    @staticmethod
    def _map_to_3levels(zxcvbn_score: int) -> str:
        """整体分析分数映射：0–2 为弱，3 为中，4 为强，不另作模式降级。"""
        if zxcvbn_score <= 2:
            return "weak"
        elif zxcvbn_score == 3:
            return "fair"
        else:  # 4
            return "strong"

    @staticmethod
    def _build_feedback_codes(
        password: str,
        zxcvbn_result: dict,
    ) -> list[str]:
        """从结构化匹配结果生成不含密码片段的固定反馈码。"""
        if not password:
            return ["EMPTY"]

        codes: list[str] = []

        def add(code: str) -> None:
            if code not in codes:
                codes.append(code)

        if len(password) < 8:
            add("TOO_SHORT")

        feedback = zxcvbn_result.get("feedback", {}) or {}
        warning = feedback.get("warning", "") or ""
        suggestions = feedback.get("suggestions", []) or []
        normalized_suggestions = {
            str(suggestion).rstrip(".") for suggestion in suggestions
        }
        if "Add another word or two. Uncommon words are better" in normalized_suggestions:
            add("ADD_WORDS")
        if "Avoid repeated words and characters" in normalized_suggestions:
            add("AVOID_REPEATS")
        if "Avoid sequences" in normalized_suggestions:
            add("AVOID_SEQUENCES")
        if "Avoid recent years" in normalized_suggestions:
            add("AVOID_RECENT_YEARS")
        if "Avoid dates and years that are associated with you" in normalized_suggestions:
            add("AVOID_DATES")

        for match in zxcvbn_result.get("sequence", []) or []:
            pattern = match.get("pattern")
            if pattern == "spatial":
                add("AVOID_KEYBOARD_PATTERN")
            elif pattern == "repeat":
                add("AVOID_REPEATS")
            elif pattern == "sequence":
                add("AVOID_SEQUENCES")
            elif pattern == "date":
                add("AVOID_DATES")
            elif pattern == "regex" and match.get("regex_name") == "recent_year":
                add("AVOID_RECENT_YEARS")
            elif pattern == "dictionary":
                dictionary = match.get("dictionary_name", "")
                if match.get("l33t"):
                    add("AVOID_LEET_PATTERN")
                if dictionary == "user_inputs":
                    add("AVOID_USER_DATA")
                elif dictionary == "passwords":
                    add("AVOID_COMMON_PASSWORD")
                elif dictionary in {"male_names", "female_names", "surnames"}:
                    add("AVOID_NAMES")
                elif dictionary == "english_wikipedia":
                    add("AVOID_COMMON_WORD")
                else:
                    add("DICTIONARY_MATCH")

        if "common password" in warning.lower():
            add("AVOID_COMMON_PASSWORD")
        if "word by itself" in warning.lower():
            add("AVOID_COMMON_WORD")
        if "name" in warning.lower():
            add("AVOID_NAMES")
        return codes

    # ------------------------------------------------------------------
    # feedback 构建（方案文档第四章 4.4 节）
    # ------------------------------------------------------------------

    @staticmethod
    def _build_feedback(zxcvbn_result: dict) -> list:
        """将 zxcvbn 的 feedback + sequence 转换为中文 issues 列表。

        数据源：
        - zxcvbn_result['feedback']['warning']     → 主要警告
        - zxcvbn_result['feedback']['suggestions'] → 改进建议
        - zxcvbn_result['sequence']                → 匹配序列（含字典命中/键盘/重复等模式）

        构建顺序：
        1. 翻译 warning（带 token 的从 sequence 取命中子串，避免重复提取）
        2. 从 sequence 提取命中模式（跳过已被 warning 覆盖的那一项）
        3. 翻译 suggestions
        全程去重，保持顺序。
        """
        feedback = zxcvbn_result.get("feedback", {}) or {}
        warning = feedback.get("warning", "") or ""
        suggestions = feedback.get("suggestions", []) or []
        sequence = zxcvbn_result.get("sequence", []) or []

        issues = []

        # 1. 翻译 warning
        covered_pattern = None
        covered_token = None
        if warning:
            if warning in _TOKEN_WARNING_MAP:
                # 带 token 的 warning：从 sequence 中找到对应模式的第一个命中子串
                covered_pattern = _WARNING_PATTERN[warning]
                for m in sequence:
                    if m.get("pattern") == covered_pattern:
                        covered_token = m.get("token", "")
                        break
                template = _TOKEN_WARNING_MAP[warning]
                issues.append(template.format(token=covered_token))
            elif warning in _GENERAL_WARNING_MAP:
                issues.append(_GENERAL_WARNING_MAP[warning])
            else:
                # 未收录的 warning，保留英文原文（便于后续补充翻译表）
                issues.append(warning)

        # 2. 从 sequence 提取命中模式
        for m in sequence:
            pattern = m.get("pattern", "")
            token = m.get("token", "")
            # 跳过已被 warning 翻译覆盖的那一项（同 pattern + 同 token）
            if (
                covered_pattern
                and pattern == covered_pattern
                and token == covered_token
            ):
                continue
            issue = PasswordTools._sequence_match_to_issue(m)
            if issue and issue not in issues:
                issues.append(issue)

        # 3. 翻译 suggestions
        for suggestion in suggestions:
            translated = _SUGGESTION_MAP.get(suggestion, suggestion)
            if translated not in issues:
                issues.append(translated)

        return issues

    @staticmethod
    def _sequence_match_to_issue(match: dict):
        """将单个 zxcvbn sequence 匹配项转换为中文 issue 字符串。

        - dictionary: 区分 l33t 替换 / 自定义中文词典 / user_inputs / 其他内置词典
        - spatial:    键盘走位
        - repeat:     重复模式
        - sequence:   顺序字符
        - date:       日期
        - regex:      正则（多为近期年份）
        - bruteforce: 不单独提示（熵估算兜底，无具体模式可指）
        """
        pattern = match.get("pattern", "")
        token = match.get("token", "")

        if pattern == "dictionary":
            l33t = match.get("l33t", False)
            dict_name = match.get("dictionary_name", "")
            if l33t:
                return f"包含替换模式弱密码: {token}"
            if dict_name in ("passwords", "cn_leaked", "pinyin_weak", "chinese_phrases"):
                return f"命中常见弱密码: {token}"
            if dict_name == "user_inputs":
                return f"命中上下文相关词: {token}"
            return f"与常见弱密码相似: {token}"
        elif pattern == "spatial":
            return f"包含键盘走位模式: {token}"
        elif pattern == "repeat":
            return f"包含重复模式: {token}"
        elif pattern == "sequence":
            return f"包含顺序字符模式: {token}"
        elif pattern == "date":
            return f"包含日期模式: {token}"
        elif pattern == "regex":
            return f"包含常见模式: {token}"
        # bruteforce / 未知模式：不单独提示
        return None

    # ------------------------------------------------------------------
    # 预热（方案文档第六章 6.4 节）
    # ------------------------------------------------------------------

    @staticmethod
    def _warmup() -> None:
        """应用启动时预热 zxcvbn 字典缓存。

        zxcvbn 首次调用会懒加载内置 30k×6 字典（约几百毫秒），
        在应用启动时主动触发一次，避免首次强度检测出现可感知延迟。
        """
        try:
            zxcvbn("", user_inputs=[])
        except Exception:
            # 预热失败不应影响应用启动，后续真实调用时再由 zxcvbn 自行初始化
            pass
