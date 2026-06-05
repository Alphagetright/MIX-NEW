# -*- coding: utf-8 -*-
"""
古典诗词音韵格律分析引擎 — 格律扫描综合引擎
============================================
整合平仄检测、格律检查、韵脚分析、对仗检测四大子引擎，
提供一键全维度诗歌音韵格律扫描。
"""
from typing import Any, Dict, List, Optional, Tuple, Union

from .data_loader import extract_chinese_lines, quick_load
from .duizhang_detector import DuizhangDetector
from .errors import ScansionError, safe_call
from .logger import get_logger, LoggerMixin
from .meter_checker import MeterChecker
from .models import (
    DuizhangReport,
    MeterReport,
    PingzeAnnotation,
    RhymeReport,
    ScansionResult,
    ToneDistribution,
)
from .pingze_engine import PingzeEngine
from .pingshui_db import PingShuiYunDB
from .rhyme_analyzer import RhymeAnalyzer

logger = get_logger("scansion_engine")


class ScansionEngine(LoggerMixin):
    """格律扫描综合引擎 — 一键全维度分析"""

    def __init__(self, db: PingShuiYunDB = None):
        self._db = db or PingShuiYunDB()
        self._pingze = PingzeEngine(self._db)
        self._meter = MeterChecker(self._pingze)
        self._rhyme = RhymeAnalyzer(self._db)
        self._duizhang = DuizhangDetector()

    @property
    def pingze_engine(self) -> PingzeEngine:
        return self._pingze

    @property
    def meter_checker(self) -> MeterChecker:
        return self._meter

    @property
    def rhyme_analyzer(self) -> RhymeAnalyzer:
        return self._rhyme

    @property
    def duizhang_detector(self) -> DuizhangDetector:
        return self._duizhang

    # ─── 文本处理 ───

    def _normalize_input(self, poem_input: Union[str, List[str]]) -> List[str]:
        """将输入统一为诗句列表"""
        if isinstance(poem_input, str):
            lines = extract_chinese_lines(poem_input)
            if not lines:
                raise ScansionError("无法从输入中提取诗句")
            return lines
        if isinstance(poem_input, list):
            return poem_input
        raise ScansionError(f"不支持的输入类型: {type(poem_input)}")

    def _detect_title_author(
        self, poem_input: Union[str, List[str]]
    ) -> Tuple[str, str]:
        """尝试检测标题和作者"""
        if isinstance(poem_input, str):
            lines = poem_input.strip().split("\n")
            if len(lines) >= 2:
                # 第一行可能是标题
                first = lines[0].strip()
                if not any(c in first for c in ("，", "。", "？", "！")):
                    if len(first) <= 20 and " " not in first:
                        return first, ""
        return "", ""

    # ─── 一键扫描 ───

    def scan(
        self, poem_input: Union[str, List[str]], form: str = None
    ) -> ScansionResult:
        """全维度扫描（平仄+格律+韵脚+对仗）

        Args:
            poem_input: 诗歌文本或诗句列表
            form: 指定体裁（None则自动检测）

        Returns:
            ScansionResult: 完整扫描结果
        """
        lines = self._normalize_input(poem_input)
        title, author = self._detect_title_author(poem_input)

        # 1. 平仄标注
        annotations = self._pingze.annotate_poem(lines)
        tone_dist = self._pingze.get_distribution_from_annotations(annotations)

        # 2. 格律检查
        meter_report = self._meter.check_poem(lines, form=form, annotations=annotations)
        meter_report.poem_title = title
        if form:
            meter_report.form = form

        # 3. 韵脚分析
        rhyme_report = self._rhyme.analyze_rhyme_scheme(lines, form=meter_report.form)
        rhyme_report.poem_title = title

        # 4. 对仗检测
        duizhang_report = self._duizhang.analyze_poem(lines, form=meter_report.form)
        duizhang_report.poem_title = title

        # 5. 综合评分
        meter_score = self._meter.get_compliance_score(meter_report)

        # 韵脚基础分
        rhyme_base = 100 if rhyme_report.is_compliant else 30
        if rhyme_report.neighboring_rhyme:
            rhyme_base = 70
        rhyme_penalty = len(rhyme_report.violations) * 10

        # 对仗加分（仅律诗）
        duizhang_bonus = 0
        if meter_report.form in ("五律", "七律") and duizhang_report.couplets:
            required_couplets = duizhang_report.couplets[1:3]  # 颔联、颈联
            for c in required_couplets:
                if c.is_duizhang:
                    if c.duizhang_type == "工对":
                        duizhang_bonus += 15
                    else:
                        duizhang_bonus += 10

        overall = (
            meter_score * 0.50
            + max(0, rhyme_base - rhyme_penalty) * 0.25
            + min(100, duizhang_bonus) * 0.10
            + tone_dist.to_dict()["平声占比"] * 0.15
        )
        overall = max(0, min(100, round(overall, 1)))

        # 6. 摘要
        summary_parts = []
        summary_parts.append(f"体裁: {meter_report.form}")
        summary_parts.append(f"起式: {meter_report.style}")
        summary_parts.append(f"格律: {meter_report.overall_judgment}")
        if rhyme_report.is_compliant:
            summary_parts.append(f"合韵({rhyme_report.rhyme_yunbu})")
        else:
            summary_parts.append(f"出韵({len(rhyme_report.violations)}处)")
        if duizhang_report.overall_score > 50:
            summary_parts.append(f"对仗可用({duizhang_report.overall_score:.0f}分)")

        return ScansionResult(
            poem_title=title,
            poem_author=author,
            form=meter_report.form,
            total_lines=len(lines),
            total_chars=sum(len(l) for l in lines),
            pingze_annotations=annotations,
            tone_distribution=tone_dist,
            meter_report=meter_report,
            rhyme_report=rhyme_report,
            duizhang_report=duizhang_report,
            overall_score=overall,
            summary="，".join(summary_parts),
        )

    def quick_check(
        self, poem_input: Union[str, List[str]]
    ) -> ScansionResult:
        """快速检查（平仄+基本格律，跳过对仗）"""
        lines = self._normalize_input(poem_input)
        title, _ = self._detect_title_author(poem_input)

        annotations = self._pingze.annotate_poem(lines)
        tone_dist = self._pingze.get_distribution_from_annotations(annotations)
        meter_report = self._meter.check_poem(lines, annotations=annotations)
        meter_report.poem_title = title
        rhyme_report = self._rhyme.analyze_rhyme_scheme(lines, form=meter_report.form)
        rhyme_report.poem_title = title
        meter_score = self._meter.get_compliance_score(meter_report)

        return ScansionResult(
            poem_title=title,
            form=meter_report.form,
            total_lines=len(lines),
            total_chars=sum(len(l) for l in lines),
            pingze_annotations=annotations,
            tone_distribution=tone_dist,
            meter_report=meter_report,
            rhyme_report=rhyme_report,
            overall_score=meter_score,
            summary=f"格律{meter_report.overall_judgment}，"
            f"合规率{meter_report.compliance_rate:.0f}%",
        )

    def deep_analyze(
        self, poem_input: Union[str, List[str]], form: str = None
    ) -> ScansionResult:
        """深度分析（完整分析 + 额外细节）"""
        return self.scan(poem_input, form=form)

    # ─── 批量扫描 ───

    def scan_batch(
        self, poems: List[Union[str, List[str]]]
    ) -> List[ScansionResult]:
        """批量扫描"""
        return [self.scan(p) for p in poems]

    # ─── 统计 ───

    def get_pingze_statistics(self) -> Dict[str, Any]:
        """返回平仄引擎统计"""
        return self._pingze.get_statistics()
