# -*- coding: utf-8 -*-
"""
古典诗词音韵格律分析引擎 — 格律合规检查引擎
============================================
支持16种格律模板（五绝4 + 七绝4 + 五律4 + 七律4），
自动检测孤平、三平调、三仄尾等特殊违律。
"""
from typing import Any, Dict, List, Optional, Tuple

from .errors import MeterError, safe_call
from .logger import get_logger, LoggerMixin
from .models import (
    MeterReport,
    MeterTemplate,
    MeterViolation,
    PingzeAnnotation,
)
from .pingze_engine import PingzeEngine

logger = get_logger("meter_checker")

# ─── 格律模板标记 ───
# ○ = 平   ● = 仄   ◎ = 应平可仄（一三五灵活）  ◇ = 应仄可平（一三五灵活）
# 押韵位置用 [押] 标记，入韵首句用 [入韵] 标记

# ─── 五言绝句模板 ───
# 五绝仄起首句不入韵
_5JU_ZE_NO = ["● ● ○ ○ ●", "○ ○ ● ● ○", "○ ○ ○ ● ●", "● ● ● ○ ○"]
# 五绝仄起首句入韵
_5JU_ZE_IN = ["● ● ● ○ ○", "○ ○ ● ● ○", "○ ○ ○ ● ●", "● ● ● ○ ○"]
# 五绝平起首句不入韵
_5JU_PING_NO = ["○ ○ ○ ● ●", "● ● ● ○ ○", "● ● ○ ○ ●", "○ ○ ● ● ○"]
# 五绝平起首句入韵
_5JU_PING_IN = ["○ ○ ● ● ○", "● ● ● ○ ○", "● ● ○ ○ ●", "○ ○ ● ● ○"]

# ─── 五言律诗模板 ───
# 五律 = 五绝 × 2
_5LU_ZE_NO = _5JU_ZE_NO * 2
_5LU_ZE_IN = _5JU_ZE_IN * 2
_5LU_PING_NO = _5JU_PING_NO * 2
_5LU_PING_IN = _5JU_PING_IN * 2

# ─── 七言绝句模板 ───
# 七言 = 五言前加两字（仄起加"● ●"，平起加"○ ○"）
_7JU_ZE_NO = ["● ● ○ ○ ○ ● ●", "○ ○ ● ● ● ○ ○", "○ ○ ● ● ○ ○ ●", "● ● ○ ○ ● ● ○"]
_7JU_ZE_IN = ["● ● ○ ○ ● ● ○", "○ ○ ● ● ● ○ ○", "○ ○ ● ● ○ ○ ●", "● ● ○ ○ ● ● ○"]
_7JU_PING_NO = ["○ ○ ● ● ○ ○ ●", "● ● ○ ○ ● ● ○", "● ● ○ ○ ○ ● ●", "○ ○ ● ● ● ○ ○"]
_7JU_PING_IN = ["○ ○ ● ● ● ○ ○", "● ● ○ ○ ● ● ○", "● ● ○ ○ ○ ● ●", "○ ○ ● ● ● ○ ○"]

# ─── 七言律诗模板 ───
_7LU_ZE_NO = _7JU_ZE_NO * 2
_7LU_ZE_IN = _7JU_ZE_IN * 2
_7LU_PING_NO = _7JU_PING_NO * 2
_7LU_PING_IN = _7JU_PING_IN * 2

# ─── 模板注册表 ───

_formats: Dict[str, Any] = {
    "五绝仄起不入": {"form": "五绝", "style": "仄起", "rhyme_start": "不入韵", "templates": _5JU_ZE_NO, "line_count": 4, "chars_per_line": 5, "couplet_indices": []},
    "五绝仄起入韵": {"form": "五绝", "style": "仄起", "rhyme_start": "入韵", "templates": _5JU_ZE_IN, "line_count": 4, "chars_per_line": 5, "couplet_indices": []},
    "五绝平起不入": {"form": "五绝", "style": "平起", "rhyme_start": "不入韵", "templates": _5JU_PING_NO, "line_count": 4, "chars_per_line": 5, "couplet_indices": []},
    "五绝平起入韵": {"form": "五绝", "style": "平起", "rhyme_start": "入韵", "templates": _5JU_PING_IN, "line_count": 4, "chars_per_line": 5, "couplet_indices": []},
    "五律仄起不入": {"form": "五律", "style": "仄起", "rhyme_start": "不入韵", "templates": _5LU_ZE_NO, "line_count": 8, "chars_per_line": 5, "couplet_indices": [0, 2, 4, 6]},
    "五律仄起入韵": {"form": "五律", "style": "仄起", "rhyme_start": "入韵", "templates": _5LU_ZE_IN, "line_count": 8, "chars_per_line": 5, "couplet_indices": [0, 2, 4, 6]},
    "五律平起不入": {"form": "五律", "style": "平起", "rhyme_start": "不入韵", "templates": _5LU_PING_NO, "line_count": 8, "chars_per_line": 5, "couplet_indices": [0, 2, 4, 6]},
    "五律平起入韵": {"form": "五律", "style": "平起", "rhyme_start": "入韵", "templates": _5LU_PING_IN, "line_count": 8, "chars_per_line": 5, "couplet_indices": [0, 2, 4, 6]},
    "七绝仄起不入": {"form": "七绝", "style": "仄起", "rhyme_start": "不入韵", "templates": _7JU_ZE_NO, "line_count": 4, "chars_per_line": 7, "couplet_indices": []},
    "七绝仄起入韵": {"form": "七绝", "style": "仄起", "rhyme_start": "入韵", "templates": _7JU_ZE_IN, "line_count": 4, "chars_per_line": 7, "couplet_indices": []},
    "七绝平起不入": {"form": "七绝", "style": "平起", "rhyme_start": "不入韵", "templates": _7JU_PING_NO, "line_count": 4, "chars_per_line": 7, "couplet_indices": []},
    "七绝平起入韵": {"form": "七绝", "style": "平起", "rhyme_start": "入韵", "templates": _7JU_PING_IN, "line_count": 4, "chars_per_line": 7, "couplet_indices": []},
    "七律仄起不入": {"form": "七律", "style": "仄起", "rhyme_start": "不入韵", "templates": _7LU_ZE_NO, "line_count": 8, "chars_per_line": 7, "couplet_indices": [0, 2, 4, 6]},
    "七律仄起入韵": {"form": "七律", "style": "仄起", "rhyme_start": "入韵", "templates": _7LU_ZE_IN, "line_count": 8, "chars_per_line": 7, "couplet_indices": [0, 2, 4, 6]},
    "七律平起不入": {"form": "七律", "style": "平起", "rhyme_start": "不入韵", "templates": _7LU_PING_NO, "line_count": 8, "chars_per_line": 7, "couplet_indices": [0, 2, 4, 6]},
    "七律平起入韵": {"form": "七律", "style": "平起", "rhyme_start": "入韵", "templates": _7LU_PING_IN, "line_count": 8, "chars_per_line": 7, "couplet_indices": [0, 2, 4, 6]},
}


def _parse_template(template_str: str) -> List[str]:
    """将模板字符串解析为标记列表（去掉空格）"""
    return template_str.replace(" ", "")


def _flexible_positions_for_line(chars_per_line: int) -> List[int]:
    """返回一三五不论的灵活位置列表（1-based）

    五言：位置1, 3 灵活
    七言：位置1, 3, 5 灵活
    """
    if chars_per_line == 5:
        return [1, 3]
    elif chars_per_line == 7:
        return [1, 3, 5]
    return []


_TONE_TO_SYMBOL = {"平": "○", "仄": "●", "仄(入)": "●", "未知": "◆"}


class MeterChecker(LoggerMixin):
    """格律合规检查引擎"""

    def __init__(self, engine: PingzeEngine):
        self._engine = engine

    # ─── 体裁检测 ───

    def detect_form(self, poem_lines: List[str]) -> Optional[str]:
        """自动检测诗歌体裁

        根据句数和每句字数判断：五绝/七绝/五律/七律
        """
        n = len(poem_lines)
        if n < 2:
            return None

        # 统计每句字数
        char_lens = [len(line) for line in poem_lines]
        typical_len = max(set(char_lens), key=char_lens.count) if char_lens else 0

        if typical_len not in (5, 7):
            return None

        if n == 4:
            return "五绝" if typical_len == 5 else "七绝"
        elif n == 8:
            return "五律" if typical_len == 5 else "七律"
        elif n == 12:
            return "五排" if typical_len == 5 else "七排"

        return None

    def detect_style(self, poem_lines: List[str], form: str = None) -> str:
        """自动检测起式（仄起/平起）"""
        if not poem_lines:
            return "未知"

        first_line = poem_lines[0]
        if not first_line:
            return "未知"

        first_char = first_line[0]
        tone = self._engine._db.get_tone(first_char)

        if tone == "平":
            return "平起"
        return "仄起"

    def detect_rhyme_start(self, poem_lines: List[str]) -> str:
        """检测首句是否入韵"""
        if not poem_lines:
            return "不入韵"
        first_line = poem_lines[0]
        if not first_line:
            return "不入韵"
        last_char = first_line[-1]
        # 首句末字如果是平声 → 通常入韵
        tone = self._engine._db.get_tone(last_char)
        return "入韵" if tone == "平" else "不入韵"

    # ─── 模板管理 ───

    def get_all_templates(self) -> List[Dict[str, Any]]:
        """返回所有注册模板"""
        return [
            {
                "key": key,
                "form": v["form"],
                "style": v["style"],
                "rhyme_start": v["rhyme_start"],
                "line_count": v["line_count"],
                "chars_per_line": v["chars_per_line"],
            }
            for key, v in _formats.items()
        ]

    def get_template(
        self, form: str, style: str, rhyme_start: str
    ) -> Optional[MeterTemplate]:
        """获取指定格式的格律模板"""
        candidates = []
        for key, v in _formats.items():
            if v["form"] == form and v["style"] == style and v["rhyme_start"] == rhyme_start:
                candidates.append(v)

        if not candidates:
            return None

        tmpl = candidates[0]

        parsed_templates = [_parse_template(t) for t in tmpl["templates"]]
        chars_per_line = tmpl["chars_per_line"]

        # 根据"一三五不论，二四六分明"规则计算灵活位置
        flex_for_line = _flexible_positions_for_line(chars_per_line)
        flexible_positions = [list(flex_for_line) for _ in parsed_templates]

        return MeterTemplate(
            form=tmpl["form"],
            style=tmpl["style"],
            rhyme_start=tmpl["rhyme_start"],
            line_count=tmpl["line_count"],
            chars_per_line=chars_per_line,
            line_templates=parsed_templates,
            flexible_positions=flexible_positions,
            couplet_indices=tmpl["couplet_indices"],
        )

    def _match_online(self, poem_lines: List[str]) -> Optional[MeterTemplate]:
        """自动匹配最合适的格律模板"""
        form = self.detect_form(poem_lines)
        if form is None:
            return None

        style = self.detect_style(poem_lines)
        rhyme_start = self.detect_rhyme_start(poem_lines)

        # 尝试精确匹配，失败则尝试仅匹配 form+style
        tmpl = self.get_template(form, style, rhyme_start)
        if tmpl:
            return tmpl

        # 尝试匹配 form + style + 相反的 rhyme_start
        alt_rhyme = "不入韵" if rhyme_start == "入韵" else "入韵"
        tmpl = self.get_template(form, style, alt_rhyme)
        if tmpl:
            return tmpl

        # 尝试匹配 form + 相反的 style
        alt_style = "平起" if style == "仄起" else "仄起"
        tmpl = self.get_template(form, alt_style, rhyme_start)
        if tmpl:
            return tmpl

        return None

    # ─── 单句检查 ───

    def check_line(
        self,
        line_ann: List[PingzeAnnotation],
        template_str: str,
        flexible_positions: List[int] = None,
    ) -> List[MeterViolation]:
        """检查单句是否合律

        Args:
            line_ann: 平仄标注结果
            template_str: 格律模板字符串如 "○●○○●"
            flexible_positions: 灵活位置列表 [1,3] 或 [1,3,5]（1-based）

        Returns:
            List[MeterViolation]: 违规列表
        """
        flexible_positions = flexible_positions or []
        violations = []
        for idx, ann in enumerate(line_ann):
            if idx >= len(template_str):
                break

            tpl_sym = template_str[idx]
            is_flex = (idx + 1) in flexible_positions

            # 检查平仄是否匹配（忽略未知字符）
            if ann.tone == "未知":
                continue

            # 灵活位置 — 不计数为违规
            if is_flex:
                continue

            # 严格位置：必须匹配
            if tpl_sym == "○" and ann.tone != "平":
                violations.append(
                    MeterViolation(
                        line_number=ann.line_number,
                        char_position=ann.position,
                        char=ann.char,
                        expected="平",
                        actual=ann.tone,
                        is_flexible=False,
                        severity="严重",
                        description=f"第{ann.line_number}句第{ann.position}字「{ann.char}」应平却{ann.tone}",
                    )
                )
            elif tpl_sym == "●" and ann.tone not in ("仄", "仄(入)"):
                violations.append(
                    MeterViolation(
                        line_number=ann.line_number,
                        char_position=ann.position,
                        char=ann.char,
                        expected="仄",
                        actual=ann.tone,
                        is_flexible=False,
                        severity="严重",
                        description=f"第{ann.line_number}句第{ann.position}字「{ann.char}」应仄却{ann.tone}",
                    )
                )

        return violations

    # ─── 全诗检查 ───

    def check_poem(
        self,
        poem_lines: List[str],
        form: str = None,
        annotations: List[List[PingzeAnnotation]] = None,
    ) -> MeterReport:
        """全诗格律合规检查

        Args:
            poem_lines: 诗句列表
            form: 指定体裁（None则自动检测）
            annotations: 平仄标注（None则自动生成）

        Returns:
            MeterReport: 格律报告
        """
        if annotations is None:
            annotations = self._engine.annotate_poem(poem_lines)

        # 检测体裁
        detected_form = self.detect_form(poem_lines)
        form = form or detected_form or "未知"

        # 匹配模板
        template = self._match_online(poem_lines)
        if template is None:
            # 无法匹配模板，返回基本报告
            total_violations = 0
            compliant = 0
            for i, line_ann in enumerate(annotations):
                n_errors = 0
                for ann in line_ann:
                    if ann.tone == "未知":
                        n_errors += 1
                if n_errors == 0:
                    compliant += 1
                total_violations += n_errors

            report = MeterReport(
                poem_title="",
                form=form,
                style=self.detect_style(poem_lines),
                total_lines=len(poem_lines),
                total_chars=sum(len(l) for l in poem_lines),
                compliant_lines=compliant,
                compliance_rate=compliant / max(1, len(poem_lines)) * 100,
                overall_judgment=self._judge_overall(
                    compliant, len(poem_lines), template
                ),
            )
            return report

        style = template.style
        # 全诗检查
        all_violations = []
        compliant_lines_count = 0
        total_lines = len(poem_lines)

        for i, (line_ann, tpl_str, flex) in enumerate(
            zip(annotations, template.line_templates, template.flexible_positions)
        ):
            if i >= len(poem_lines):
                break
            violations = self.check_line(line_ann, tpl_str, flex)
            all_violations.extend(violations)
            if len(violations) == 0:
                compliant_lines_count += 1

        # 孤平/三平调/三仄尾检查
        guping_lines = self.check_guping(poem_lines, annotations)
        sanpingdiao_lines = self.check_sanpingdiao(annotations)
        sanzewei_lines = self.check_sanzewei(annotations)

        # 从违规中排除孤平/三平调/三仄尾（它们会被单独报告）
        repeat_lines = set(guping_lines + sanpingdiao_lines + sanzewei_lines)
        unique_violations = [
            v
            for v in all_violations
            if not (
                v.line_number in repeat_lines
                and v.line_number > 0
            )
        ]

        # 计算合规率（仅严格位置）
        flex_positions = template.flexible_positions
        total_strict_positions = 0
        correct_strict_positions = 0
        for i, (line_ann, tpl_str) in enumerate(
            zip(annotations, template.line_templates)
        ):
            if i >= len(poem_lines):
                break
            flex_line = set(flex_positions[i]) if i < len(flex_positions) else set()
            for j, ann in enumerate(line_ann):
                if j >= len(tpl_str):
                    break
                pos = j + 1
                if pos in flex_line:
                    continue  # 灵活位置不计入合规率
                tpl_sym = tpl_str[j]
                total_strict_positions += 1
                if tpl_sym == "○" and ann.tone == "平":
                    correct_strict_positions += 1
                elif tpl_sym == "●" and ann.tone in ("仄", "仄(入)"):
                    correct_strict_positions += 1

        compliance_rate = (
            correct_strict_positions / max(1, total_strict_positions) * 100
        )

        report = MeterReport(
            poem_title="",
            form=form,
            style=style,
            total_lines=total_lines,
            total_chars=sum(len(l) for l in poem_lines),
            compliant_lines=compliant_lines_count,
            violations=unique_violations,
            guping_lines=guping_lines,
            sanpingdiao_lines=sanpingdiao_lines,
            sanzewei_lines=sanzewei_lines,
            compliance_rate=compliance_rate,
            overall_judgment=self._judge_overall(
                compliant_lines_count, total_lines, template
            ),
        )

        return report

    # ─── 特殊违律检测 ───

    def check_guping(
        self,
        poem_lines: List[str],
        annotations: List[List[PingzeAnnotation]],
    ) -> List[int]:
        """孤平检测

        孤平定义：一句中（除韵脚外）只剩一个平声字。
        严格定义：在平平仄仄平句式中，第一字若用仄声，
                  则全句除韵脚外只剩一个平声字。
        """
        guping_lines = []
        for i, line_ann in enumerate(annotations):
            line = line_ann
            # 统计平声字（排除最后一个字——韵脚）
            ping_positions = []
            for j, ann in enumerate(line):
                if ann.tone == "平":
                    if j < len(line) - 1:  # 排除句末字
                        ping_positions.append(j)

            # 如果排除韵脚后只剩1个或0个平声字 → 孤平
            if 0 < len(ping_positions) <= 1:
                guping_lines.append(i + 1)

        return guping_lines

    def check_sanpingdiao(
        self,
        annotations: List[List[PingzeAnnotation]],
    ) -> List[int]:
        """三平调检测：句末连续三个平声字"""
        sanping_lines = []
        for i, line_ann in enumerate(annotations):
            if len(line_ann) >= 3:
                last_three = line_ann[-3:]
                if all(a.tone == "平" for a in last_three):
                    sanping_lines.append(i + 1)
        return sanping_lines

    def check_sanzewei(
        self,
        annotations: List[List[PingzeAnnotation]],
    ) -> List[int]:
        """三仄尾检测：句末连续三个仄声字（五言句）"""
        sanze_lines = []
        for i, line_ann in enumerate(annotations):
            if len(line_ann) >= 3:
                last_three = line_ann[-3:]
                if all(a.tone in ("仄", "仄(入)") for a in last_three):
                    sanze_lines.append(i + 1)
        return sanze_lines

    # ─── 评分 ───

    def get_compliance_score(self, report: MeterReport) -> float:
        """计算格律合规评分 0-100"""
        # 基础分：严格位置合规率
        base = report.compliance_rate

        # 孤平扣分
        guping_penalty = len(report.guping_lines) * 15
        # 三平调扣分
        sanping_penalty = len(report.sanpingdiao_lines) * 20
        # 三仄尾扣分
        sanze_penalty = len(report.sanzewei_lines) * 10
        # 违规每条扣分
        violation_penalty = len(report.violations) * 5

        score = base - guping_penalty - sanping_penalty - sanze_penalty - violation_penalty
        return max(0, min(100, score))

    # ─── 内部 ───

    def _judge_overall(
        self,
        compliant_lines: int,
        total_lines: int,
        template: Optional[MeterTemplate],
    ) -> str:
        if total_lines == 0:
            return "不合律"

        ratio = compliant_lines / total_lines
        if ratio >= 0.9:
            return "合律"
        elif ratio >= 0.7:
            return "基本合律"
        elif ratio >= 0.4:
            return "部分合律"
        else:
            return "不合律"
