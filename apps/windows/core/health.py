"""
core.health — 密码库健康评分与安全问题收集模块

提供密码库整体健康评分计算与逐条安全问题清单收集，用于安全体检页
（hero 区分数/等级 + 问题列表 + 逐个引导修复）。

设计要点：
- core 层纯净，不依赖任何 UI 框架（PyQt5/PySide6），也不依赖 core 层其他
  模块（如 database），仅使用 Python 标准库 + core.i18n（用于 grade_text /
  title / desc 翻译）。
- 评分结果返回结构化 `HealthScoreResult` 对象（dataclass），含分数 / 等级 /
  扣分明细等字段，便于 UI 层渲染与类型安全访问。
- 颜色返回语义键字符串（'success'/'accent'/'warning'/'danger'/'muted'），
  不返回 CSS 变量或 hex；由 UI 层 ThemeManager 映射为实际颜色，core 保持
  主题无关。
- 重复组从 passwords 参数内部按明文分组推算，不依赖 database.get_duplicate_groups()，
  避免与 database 模块耦合，接口更简洁。
- 日期解析容错：datetime.fromisoformat() 解析失败或字段缺失时，该条不计入
  stale（不抛异常），与原型 daysBetween 对非法日期的宽松行为一致。
- 已生成的 `HealthScoreResult` / `SecurityIssue` 不会响应后续语言切换，
  需调用方重新计算。

健康评分模型（0-100，扣分制）：
    起始分 100，按三类问题扣分：
        弱密码扣分 = min(weak_count * 5, 40) + min(weak_ratio * 100, 30)
        重复扣分  = min(dup_group_count * 4, 20) + min(dup_ratio * 100, 15)
        过期扣分  = min(stale_count * 1.5, 15) + min(stale_ratio * 100, 10)
                    - overlap_count * 1.5（弱密码 ∩ 过期 重叠退回，不低于 0）
    最终分 = max(0, min(100, floor(100 - 三项扣分之和 + 0.5)))
    （用 floor(x+0.5) 与原型 JS Math.round 对齐，Python round() 的银行家舍入
     会导致 50/70/90 等级边界 1 分差异）

等级划分（按最终分）：
    ≥90  excellent（color='success'）
    ≥70  good     （color='accent'）
    ≥50  fair     （color='warning'）
    <50  risk     （color='danger'）
    空库 none     （color='muted'）

strength 字段值兼容：core 当前为 'weak'/'medium'/'strong'，G5 迁移后将改为
'weak'/'fair'/'strong'。本模块仅判断 == 'weak'，与两者都兼容。
"""

import datetime
import math
from dataclasses import dataclass
from typing import Optional

from core.i18n import t


@dataclass
class HealthScoreResult:
    """健康评分结果。

    Attributes:
        score: 0-100 整数评分，空库时为 None。
        grade: 等级标识，'none'/'excellent'/'good'/'fair'/'risk'。
        grade_text: 已按当前语言翻译的等级文本（如"优秀"/"风险"）。
        title: hero 区标题（已翻译）。
        desc: hero 区描述（已翻译，含问题汇总或"未发现安全问题"）。
        weak_count: 弱密码数量。
        dup_group_count: 重复组数量（按明文分组，仅计 len>1 的组数，非条目数）。
        stale_count: 长期未更换数量。
        color: 语义颜色键（'success'/'accent'/'warning'/'danger'/'muted'），
            由 UI 层 ThemeManager 映射为实际颜色。
        weak_penalty: 弱密码扣分。
        dup_penalty: 重复扣分。
        stale_penalty: 过期扣分（已含重叠退回）。
    """

    score: Optional[int]
    grade: str
    grade_text: str
    title: str
    desc: str
    weak_count: int
    dup_group_count: int
    stale_count: int
    color: str
    weak_penalty: float
    dup_penalty: float
    stale_penalty: float


@dataclass
class SecurityIssue:
    """单条安全问题。

    Attributes:
        id: 密码记录 id。
        types: 问题类型列表，元素 ∈ {'weak','duplicate','stale'}。
            同一记录命中多个维度时含多个值（用于引导对话框徽章同时展示）。
    """

    id: int
    types: list[str]


class HealthTool:
    """健康评分与安全问题收集工具类（全部为静态方法）。"""

    @staticmethod
    def calc_health_score(
        passwords: list[dict],
        threshold: int = 180,
        *,
        today: Optional[datetime.date] = None,
    ) -> HealthScoreResult:
        """计算密码库健康评分。

        Args:
            passwords: get_all_passwords() 返回的字典列表，每条含
                id / strength / password / password_changed_at。
            threshold: 长期未换阈值（天），默认 180。

        Returns:
            HealthScoreResult: 空库返回 score=None, grade='none'。
        """
        total = len(passwords)

        # 空库处理
        if total == 0:
            return HealthScoreResult(
                score=None,
                grade="none",
                grade_text=t("security.grade.none"),
                title=t("security.hero.title.none"),
                desc=t("security.hero.empty"),
                weak_count=0,
                dup_group_count=0,
                stale_count=0,
                color="muted",
                weak_penalty=0.0,
                dup_penalty=0.0,
                stale_penalty=0.0,
            )

        today = today or datetime.date.today()

        # 1. 弱密码集合（按 id）
        weak_ids = {
            p.get("id") for p in passwords if p.get("strength") == "weak"
        }
        weak_count = len(weak_ids)

        # 2. 重复组：按明文分组，仅计 len>1 的组数（组数，非条目数）
        dup_group_count = len(HealthTool._compute_duplicate_groups(passwords))

        # 3. 过期集合（按 id）：只按密码变更时间判断
        stale_ids = set()
        for p in passwords:
            date_str = p.get("password_changed_at")
            days = HealthTool._days_between(date_str, today)
            if days is not None and days > threshold:
                stale_ids.add(p.get("id"))
        stale_count = len(stale_ids)

        # 4. 重叠退回：弱密码 ∩ 过期 的记录数
        overlap_count = len(weak_ids & stale_ids)

        # 5. 扣分公式（与原型 calcHealthScore 逐字对齐）
        weak_ratio = weak_count / total
        dup_ratio = dup_group_count / total
        stale_ratio = stale_count / total

        weak_penalty = min(weak_count * 5, 40) + min(weak_ratio * 100, 30)
        dup_penalty = min(dup_group_count * 4, 20) + min(dup_ratio * 100, 15)
        stale_penalty = min(stale_count * 1.5, 15) + min(stale_ratio * 100, 10)
        # 重叠退回：弱密码与长期未换重叠的记录，从 stale_penalty 退回单条权重 1.5
        stale_penalty = max(0.0, stale_penalty - overlap_count * 1.5)

        # 使用 floor(x + 0.5) 与原型 JS Math.round 对齐
        # （Python round() 用银行家舍入，.5 时向偶数取整，会导致 50/70/90 边界 1 分差异）
        raw_score = 100 - weak_penalty - dup_penalty - stale_penalty
        score = max(0, min(100, math.floor(raw_score + 0.5)))

        # 6. 等级与颜色
        if score >= 90:
            grade, color = "excellent", "success"
        elif score >= 70:
            grade, color = "good", "accent"
        elif score >= 50:
            grade, color = "fair", "warning"
        else:
            grade, color = "risk", "danger"

        grade_text = t(f"security.grade.{grade}")
        title = t(f"security.hero.title.{grade}")

        # 7. hero 描述组装（原型用顿号 '、' 连接 parts）
        parts = []
        if weak_count > 0:
            parts.append(t("security.hero.weak", weak_count))
        if dup_group_count > 0:
            parts.append(t("security.hero.dup", dup_group_count))
        if stale_count > 0:
            parts.append(t("security.hero.stale", stale_count))

        if not parts:
            desc = t("security.hero.clean")
        else:
            desc = t("security.hero.desc", "、".join(parts))

        return HealthScoreResult(
            score=score,
            grade=grade,
            grade_text=grade_text,
            title=title,
            desc=desc,
            weak_count=weak_count,
            dup_group_count=dup_group_count,
            stale_count=stale_count,
            color=color,
            weak_penalty=weak_penalty,
            dup_penalty=dup_penalty,
            stale_penalty=stale_penalty,
        )

    @staticmethod
    def collect_security_issues(
        passwords: list[dict],
        threshold: int = 180,
        *,
        today: Optional[datetime.date] = None,
    ) -> list[SecurityIssue]:
        """收集安全问题清单，多问题优先排序。

        聚合 weak / duplicate / stale 三类问题。同一记录命中多个类型时
        types 列表含多个值（用于引导对话框徽章同时展示，避免同记录被重复
        引导）。排序：types.length 降序（多问题优先），其次 id 升序。

        Args:
            passwords: get_all_passwords() 返回的字典列表。
            threshold: 长期未换阈值（天），默认 180。

        Returns:
            list[SecurityIssue]: 只含有问题的记录（无问题的记录不返回）。
        """
        today = today or datetime.date.today()

        duplicate_ids = {
            record_id
            for record_ids in HealthTool._compute_duplicate_groups(passwords).values()
            for record_id in record_ids
        }

        issues: dict[int, SecurityIssue] = {}

        def _push(pid: int, issue_type: str) -> None:
            """向指定 id 追加问题类型（去重，保持首次插入顺序）。"""
            if pid not in issues:
                issues[pid] = SecurityIssue(id=pid, types=[])
            if issue_type not in issues[pid].types:
                issues[pid].types.append(issue_type)

        for p in passwords:
            pid = p.get("id")
            # 弱密码
            if p.get("strength") == "weak":
                _push(pid, "weak")
            # 重复密码
            if pid in duplicate_ids:
                _push(pid, "duplicate")
            # 长期未更换（只按 password_changed_at）
            date_str = p.get("password_changed_at")
            days = HealthTool._days_between(date_str, today)
            if days is not None and days > threshold:
                _push(pid, "stale")

        # 排序：types.length 降序，其次 id 升序
        result = list(issues.values())
        result.sort(key=lambda x: (-len(x.types), x.id))
        return result

    # ------------------------------------------------------------------
    # 内部辅助方法
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_duplicate_groups(passwords: list[dict]) -> dict[str, list]:
        """按 password 明文分组，返回 len>1 的组。

        ``duplicate_group`` 存在时使用 Python 原生侧预计算的分组，避免把
        密码明文传给调用方。否则按非空 password 明文分组。

        Returns:
            dict[明文, [id列表]]：仅含出现 >1 次的明文。
        """
        if passwords and all("duplicate_group" in p for p in passwords):
            groups: dict[str, list] = {}
            for p in passwords:
                group = p.get("duplicate_group")
                if type(group) is int and group > 0:
                    groups.setdefault(str(group), []).append(p.get("id"))
            return {key: values for key, values in groups.items() if len(values) > 1}

        groups: dict[str, list] = {}
        for p in passwords:
            pwd = p.get("password")
            if not pwd:
                continue
            groups.setdefault(pwd, []).append(p.get("id"))
        return {k: v for k, v in groups.items() if len(v) > 1}

    @staticmethod
    def _days_between(
        from_iso: Optional[str], to_date: datetime.date
    ) -> Optional[int]:
        """按天取整计算天数差（两个日期都清零时分秒）。

        与原型 daysBetween 一致：两端归一化到本地午夜后相减，返回整数天。
        解析失败或输入为空时返回 None（调用方据此跳过 stale 判定，不抛异常）。

        Args:
            from_iso: ISO 格式日期字符串（如 '2025-01-01T00:00:00'）。
            to_date: 基准日期（通常为 datetime.date.today()）。

        Returns:
            天数差（to - from，可为负），或 None（解析失败）。
        """
        if not from_iso:
            return None
        try:
            from_dt = datetime.datetime.fromisoformat(from_iso)
        except (ValueError, TypeError):
            return None
        return (to_date - from_dt.date()).days
