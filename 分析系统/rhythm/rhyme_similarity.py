# -*- coding: utf-8 -*-
"""
古典诗词音韵格律分析引擎 — 音韵相似度计算
============================================
支持5维度加权音韵相似度比较、诗人用韵偏好画像、
基于韵脚相似度的聚类分析。
"""
from typing import Any, Dict, List, Optional, Tuple

from .logger import get_logger, LoggerMixin
from .models import AuthorRhymeProfile, ScansionResult, SimilarityResult
from .utils import cosine_similarity, jaccard_similarity

logger = get_logger("rhyme_similarity")

# 五维度权重
_WEIGHTS = {
    "yunbu_overlap": 0.40,
    "tone_similarity": 0.25,
    "density_similarity": 0.15,
    "position_similarity": 0.10,
    "meter_similarity": 0.10,
}


class RhymeComparator(LoggerMixin):
    """音韵相似度比较器"""

    # ─── 单维度比较 ───

    def _yunbu_overlap(self, r1: ScansionResult, r2: ScansionResult) -> float:
        """韵部重叠度 (Jaccard)"""
        if not r1.rhyme_report or not r2.rhyme_report:
            return 0.0
        y1 = set(rc.yunbu for rc in r1.rhyme_report.rhyme_chars if rc.yunbu)
        y2 = set(rc.yunbu for rc in r2.rhyme_report.rhyme_chars if rc.yunbu)
        return jaccard_similarity(y1, y2)

    def _tone_similarity(self, r1: ScansionResult, r2: ScansionResult) -> float:
        """声调分布相似度 (余弦)"""
        d1 = r1.tone_distribution
        d2 = r2.tone_distribution
        vec1 = [d1.ping_count, d1.ze_count, d1.rusheng_count]
        vec2 = [d2.ping_count, d2.ze_count, d2.rusheng_count]
        return cosine_similarity(vec1, vec2)

    def _density_similarity(self, r1: ScansionResult, r2: ScansionResult) -> float:
        """韵脚密度相似度"""
        if not r1.rhyme_report or not r2.rhyme_report:
            return 0.0
        d1 = r1.rhyme_report.rhyme_density
        d2 = r2.rhyme_report.rhyme_density
        if d1 + d2 == 0:
            return 1.0
        return 1.0 - abs(d1 - d2) / max(d1, d2)

    def _position_similarity(self, r1: ScansionResult, r2: ScansionResult) -> float:
        """韵脚位置相似度"""
        if not r1.rhyme_report or not r2.rhyme_report:
            return 0.0
        p1 = [rc.line_number for rc in r1.rhyme_report.rhyme_chars]
        p2 = [rc.line_number for rc in r2.rhyme_report.rhyme_chars]
        if not p1 and not p2:
            return 1.0
        common = len(set(p1) & set(p2))
        total = len(set(p1) | set(p2))
        return common / max(1, total)

    def _meter_similarity(self, r1: ScansionResult, r2: ScansionResult) -> float:
        """格律模板相似度"""
        if r1.form == r2.form:
            return 1.0
        # 同字数（五言/七言）得0.5
        if (r1.form and r2.form and
                r1.form[-1] == r2.form[-1] and
                r1.form[-1] in ("绝", "律")):
            return 0.5
        return 0.0

    # ─── 综合比较 ───

    def compare(self, r1: ScansionResult, r2: ScansionResult) -> SimilarityResult:
        """综合音韵相似度对比"""
        yunbu = self._yunbu_overlap(r1, r2)
        tone = self._tone_similarity(r1, r2)
        density = self._density_similarity(r1, r2)
        position = self._position_similarity(r1, r2)
        meter = self._meter_similarity(r1, r2)

        overall = (
            yunbu * _WEIGHTS["yunbu_overlap"]
            + tone * _WEIGHTS["tone_similarity"]
            + density * _WEIGHTS["density_similarity"]
            + position * _WEIGHTS["position_similarity"]
            + meter * _WEIGHTS["meter_similarity"]
        ) * 100

        return SimilarityResult(
            poem1_title=r1.poem_title,
            poem2_title=r2.poem_title,
            overall_score=round(overall, 1),
            yunbu_overlap=round(yunbu * 100, 1),
            tone_similarity=round(tone * 100, 1),
            density_similarity=round(density * 100, 1),
            position_similarity=round(position * 100, 1),
            meter_similarity=round(meter * 100, 1),
        )

    # ─── 查找相似诗歌 ───

    def find_similar(
        self,
        poem: ScansionResult,
        corpus: List[ScansionResult],
        top_n: int = 10,
    ) -> List[SimilarityResult]:
        """在诗集中找到音韵最相似的诗"""
        results = []
        for other in corpus:
            if other.poem_title == poem.poem_title:
                continue
            results.append(self.compare(poem, other))

        results.sort(key=lambda x: x.overall_score, reverse=True)
        return results[:top_n]

    # ─── 诗人用韵画像 ───

    def author_profile(
        self, poems: List[ScansionResult]
    ) -> List[AuthorRhymeProfile]:
        """计算每位诗人的用韵偏好画像"""
        from collections import Counter, defaultdict

        author_poems = defaultdict(list)
        for p in poems:
            if p.poem_author:
                author_poems[p.poem_author].append(p)

        profiles = []
        for author, ps in author_poems.items():
            yunbu_counter = Counter()
            form_counter = Counter()
            total_ping = 0
            total_ze = 0
            total_ru = 0
            total_density = 0.0

            for p in ps:
                if p.rhyme_report:
                    for rc in p.rhyme_report.rhyme_chars:
                        if rc.yunbu:
                            yunbu_counter[rc.yunbu] += 1
                if p.form:
                    form_counter[p.form] += 1
                dist = p.tone_distribution
                total_ping += dist.ping_count
                total_ze += dist.ze_count
                total_ru += dist.rusheng_count
                if p.rhyme_report:
                    total_density += p.rhyme_report.rhyme_density

            n = len(ps)
            total = total_ping + total_ze + total_ru or 1

            profiles.append(
                AuthorRhymeProfile(
                    author=author,
                    poem_count=n,
                    top_yunbus=yunbu_counter.most_common(10),
                    ping_ratio=round(total_ping / total * 100, 1),
                    ze_ratio=round(total_ze / total * 100, 1),
                    rusheng_ratio=round(total_ru / total * 100, 1),
                    favorite_forms=form_counter.most_common(5),
                    rhyme_density_avg=round(total_density / max(1, n), 2),
                )
            )

        return sorted(profiles, key=lambda x: -x.poem_count)

    # ─── 聚类 ───

    def cluster_by_rhyme(
        self, poems: List[ScansionResult]
    ) -> Dict[str, List[str]]:
        """按主押韵部对诗歌分组"""
        groups = {}
        for p in poems:
            yunbu = p.rhyme_report.rhyme_yunbu if p.rhyme_report else "未知"
            if yunbu not in groups:
                groups[yunbu] = []
            groups[yunbu].append(p.poem_title)
        return groups
