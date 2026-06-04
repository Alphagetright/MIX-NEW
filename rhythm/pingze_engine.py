# -*- coding: utf-8 -*-
"""
古典诗词音韵格律分析引擎 — 平仄检测引擎
========================================
基于《平水韵》106韵部数据库对诗句进行逐字平仄标注，
支持多音字检测和声调分布统计。查表复杂度 O(1)/字。
"""
from typing import Any, Dict, List, Optional, Tuple

from .errors import PingzeError, safe_call
from .logger import get_logger, LoggerMixin
from .models import MultiToneChar, PingzeAnnotation, ToneDistribution
from .pingshui_db import PingShuiYunDB

logger = get_logger("pingze_engine")


class PingzeEngine(LoggerMixin):
    """平仄检测引擎 — 对诗句进行逐字平仄标注"""

    def __init__(self, db: PingShuiYunDB):
        self._db = db

    # ─── 单字符平仄判定 ───

    def _determine_tone(self, char: str) -> str:
        """返回声调标记：平 / 仄 / 仄(入) / 未知"""
        raw = self._db.get_tone(char)
        mapping = {"平": "平", "上": "仄", "去": "仄", "入": "仄(入)"}
        return mapping.get(raw, "未知")

    def _get_confidence(self, char: str, is_duoyin: bool) -> float:
        if is_duoyin:
            return 0.5
        if self._db.get_tone(char) == "未知":
            return 0.0
        return 1.0

    # ─── 单句标注 ───

    def annotate_char(
        self, char: str, position: int, line_number: int
    ) -> PingzeAnnotation:
        """标注单字的平仄信息"""
        yunbu_list = self._db.get_all_yunbus(char)
        is_duoyin = len(yunbu_list) > 1

        primary_yunbu = yunbu_list[0] if yunbu_list else None
        yunbu_category = (
            self._db.get_yunbu_category(primary_yunbu) if primary_yunbu else "未知"
        )
        alternatives = yunbu_list[1:] if is_duoyin else []

        return PingzeAnnotation(
            char=char,
            position=position,
            line_number=line_number,
            tone=self._determine_tone(char),
            yunbu=primary_yunbu or "",
            yunbu_category=yunbu_category,
            is_duoyin=is_duoyin,
            alternatives=alternatives,
            confidence=self._get_confidence(char, is_duoyin),
        )

    def annotate_line(self, line: str, line_number: int = 1) -> List[PingzeAnnotation]:
        """对单句进行逐字平仄标注"""
        annotations = []
        for i, char in enumerate(line):
            annotations.append(
                self.annotate_char(char, position=i + 1, line_number=line_number)
            )
        return annotations

    def annotate_poem(
        self, poem_lines: List[str]
    ) -> List[List[PingzeAnnotation]]:
        """对全诗逐句平仄标注"""
        return [
            self.annotate_line(line, line_number=idx + 1)
            for idx, line in enumerate(poem_lines)
        ]

    # ─── 平仄标记串 ───

    def get_pingze_string(self, annotations: List[PingzeAnnotation]) -> str:
        """返回纯平仄标记串（平/仄/仄(入)/未知 → ○/●/◇/◆）"""
        return "".join(a.tone_symbol for a in annotations)

    def get_tone_labels(self, annotations: List[PingzeAnnotation]) -> str:
        """返回可读平仄标记串（平/仄/仄(入)/未知）"""
        return "/".join(a.tone for a in annotations)

    # ─── 多音字检测 ───

    def detect_multi_tone(self, line: str) -> List[MultiToneChar]:
        """检测句中所有多音字"""
        results = []
        for i, char in enumerate(line):
            yunbu_list = self._db.get_all_yunbus(char)
            if len(yunbu_list) > 1:
                possible_tones = [self._determine_tone(char) for char in [char] * len(yunbu_list)]
                # Deduplicate tones by mapping each yunbu to its tone
                tone_map = {}
                for yb in yunbu_list:
                    cat = self._db.get_yunbu_category(yb)
                    t = {"平": "平", "上": "仄", "去": "仄", "入": "仄(入)"}.get(cat, "未知")
                    if t not in tone_map:
                        tone_map[t] = []
                    tone_map[t].append(yb)
                results.append(
                    MultiToneChar(
                        char=char,
                        position=i + 1,
                        line_number=0,
                        possible_tones=list(tone_map.keys()),
                        possible_yunbus=yunbu_list,
                    )
                )
        return results

    # ─── 声调分布 ───

    def get_distribution_from_annotations(
        self, annotations: List[List[PingzeAnnotation]]
    ) -> ToneDistribution:
        """从标注结果统计平/仄/入声分布"""
        dist = ToneDistribution()
        for line_ann in annotations:
            for ann in line_ann:
                dist.total_chars += 1
                if ann.tone == "平":
                    dist.ping_count += 1
                elif ann.tone == "仄":
                    dist.ze_count += 1
                elif ann.tone == "仄(入)":
                    dist.rusheng_count += 1
                    dist.ze_count += 1
                else:
                    dist.unknown_count += 1
        return dist

    def get_distribution_from_text(self, text: str) -> ToneDistribution:
        """直接对文本进行声调分布统计"""
        return self._db.get_tone_distribution(text)

    # ─── 批量标注 ───

    def batch_annotate(
        self, poems: List[Tuple[str, List[str]]]
    ) -> List[Dict[str, Any]]:
        """批量标注多首诗歌

        Args:
            poems: List of (title, lines) tuples

        Returns:
            List of {title, annotations, pingze_strings, distribution}
        """
        results = []
        for title, lines in poems:
            annotations = self.annotate_poem(lines)
            pingze_strs = [self.get_pingze_string(ann) for ann in annotations]
            distribution = self.get_distribution_from_annotations(annotations)
            results.append(
                {
                    "title": title,
                    "annotations": annotations,
                    "pingze_strings": pingze_strs,
                    "distribution": distribution,
                }
            )
        return results

    # ─── 统计信息 ───

    def get_statistics(self) -> Dict[str, Any]:
        """返回引擎统计信息"""
        stats = self._db.get_statistics()
        stats["engine"] = "PingzeEngine"
        return stats
