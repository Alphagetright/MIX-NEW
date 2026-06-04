# -*- coding: utf-8 -*-
"""
去重引擎模块
============
检测和删除重复数据，支持精确匹配、模糊匹配和基于内容的相似度去重。
"""

import os
import time
from collections import defaultdict
from typing import Any, Dict, List, Optional, Set, Tuple

from .config import DEDUP_SIMILARITY_THRESHOLD, DEDUP_MAX_PAIRS
from .logger import get_logger
from .models import DedupResult
from .utils import text_similarity

logger = get_logger("dedup_engine")


class DedupEngine:
    """
    去重引擎

    支持三种去重策略：
      1. 精确去重（exact）：基于标题+首句MD5指纹
      2. 模糊去重（fuzzy）：基于文本相似度（编辑距离）
      3. 内容去重（content）：基于关键字段组合哈希

    Usage:
        engine = DedupEngine()
        result = engine.exact_dedup(poems)
        result = engine.fuzzy_dedup(poems, threshold=0.85)
    """

    def __init__(self):
        self._fingerprints: Set[str] = set()
        self._hash_map: Dict[str, List[int]] = defaultdict(list)

    def exact_dedup(self, items: List[Dict[str, Any]],
                    key_fields: List[str] = None) -> DedupResult:
        """
        精确去重

        基于指定字段组合的MD5哈希进行精确匹配。

        参数:
            items: 数据项列表
            key_fields: 用于生成指纹的字段列表，默认["title", "first_line"]

        返回:
            DedupResult: 去重结果
        """
        if key_fields is None:
            key_fields = ["标题", "第一句"]

        start = time.time()
        result = DedupResult(total_items=len(items))

        seen: Dict[str, int] = {}
        unique_indices: List[int] = []
        dup_groups: Dict[str, List[int]] = defaultdict(list)

        for i, item in enumerate(items):
            parts = []
            for field in key_fields:
                val = str(item.get(field, "")).strip()
                parts.append(val)
            fp = "|".join(parts)

            if fp in seen:
                dup_groups[fp].append(i)
                result.exact_duplicates += 1
            else:
                seen[fp] = i
                unique_indices.append(i)
                dup_groups[fp].append(i)

        result.unique_items = len(unique_indices)
        result.duplicates_removed = result.total_items - result.unique_items
        result.duplicate_groups = sum(1 for g in dup_groups.values() if len(g) > 1)
        result.duration_ms = round((time.time() - start) * 1000)

        # 样本
        for fp, indices in sorted(dup_groups.items(), key=lambda x: len(x[1]), reverse=True)[:5]:
            if len(indices) > 1:
                sample_item = items[indices[0]]
                result.sample_duplicates.append({
                    "fingerprint": fp[:80],
                    "count": len(indices),
                    "sample_title": sample_item.get("标题", sample_item.get("title", "")),
                })

        logger.info(f"精确去重: {result.total_items}→{result.unique_items} "
                     f"({result.duplicates_removed}删除, {result.duration_ms}ms)")
        return result

    def fuzzy_dedup(self, items: List[Dict[str, Any]],
                    text_field: str = "标题",
                    threshold: float = None) -> DedupResult:
        """
        模糊去重

        基于编辑距离/文本相似度进行模糊匹配。
        适用于标题略有不同（如标点差异、繁简体差异）的场景。
        """
        if threshold is None:
            threshold = DEDUP_SIMILARITY_THRESHOLD

        start = time.time()
        result = DedupResult(total_items=len(items))

        # 限制比较对数
        n = len(items)
        max_pairs = min(DEDUP_MAX_PAIRS, n * (n - 1) // 2)
        pairs_checked = 0

        # 先按文本排序以优化比较
        items_with_idx = [(i, str(item.get(text_field, "")).strip())
                          for i, item in enumerate(items)]
        items_with_idx.sort(key=lambda x: x[1])

        removed = set()
        dup_groups: Dict[int, List[int]] = defaultdict(list)

        for i in range(n):
            if i in removed:
                continue
            idx_i, text_i = items_with_idx[i]
            dup_groups[idx_i].append(idx_i)
            for j in range(i + 1, n):
                if j in removed:
                    continue
                pairs_checked += 1
                if pairs_checked > max_pairs:
                    break
                idx_j, text_j = items_with_idx[j]
                # 长度差异太大跳过
                if abs(len(text_i) - len(text_j)) > max(len(text_i), len(text_j)) * 0.3:
                    continue
                sim = text_similarity(text_i, text_j)
                if sim >= threshold:
                    removed.add(j)
                    dup_groups[idx_i].append(idx_j)
                    result.fuzzy_duplicates += 1

            if pairs_checked > max_pairs:
                break

        result.unique_items = result.total_items - len(removed)
        result.duplicates_removed = len(removed)
        result.duplicate_groups = sum(1 for g in dup_groups.values() if len(g) > 1)
        result.duration_ms = round((time.time() - start) * 1000)

        # 样本
        for idx, group in sorted(dup_groups.items(), key=lambda x: len(x[1]), reverse=True)[:5]:
            if len(group) > 1:
                result.sample_duplicates.append({
                    "representative": str(items[group[0]].get(text_field, ""))[:80],
                    "count": len(group),
                })

        logger.info(f"模糊去重: {result.total_items}→{result.unique_items} "
                     f"({result.fuzzy_duplicates}模糊重复, {result.duration_ms}ms)")
        return result

    def full_dedup_pipeline(self, items: List[Dict[str, Any]]) -> DedupResult:
        """完整去重流水线：先精确后模糊"""
        exact_result = self.exact_dedup(items)
        # 获取去重后的项
        unique_items = []
        seen_fps: Set[str] = set()
        for item in items:
            fp = "|".join(str(item.get(f, "")).strip()
                          for f in ["标题", "第一句"] if f in item)
            if fp not in seen_fps:
                unique_items.append(item)
                seen_fps.add(fp)

        fuzzy_result = self.fuzzy_dedup(unique_items)
        return DedupResult(
            total_items=len(items),
            unique_items=fuzzy_result.unique_items,
            duplicates_removed=exact_result.duplicates_removed + fuzzy_result.duplicates_removed,
            exact_duplicates=exact_result.exact_duplicates,
            fuzzy_duplicates=fuzzy_result.fuzzy_duplicates,
            duplicate_groups=exact_result.duplicate_groups + fuzzy_result.duplicate_groups,
            duration_ms=exact_result.duration_ms + fuzzy_result.duration_ms,
        )


# ─── 扩展去重 ───

def content_based_dedup(items, content_field="原文"):
    engine = DedupEngine()
    result = engine.exact_dedup(items, key_fields=[content_field])
    return result

def multi_pass_dedup(items):
    engine = DedupEngine()
    r1 = engine.exact_dedup(items)
    unique = []
    seen = set()
    for item in items:
        fp = "|".join(str(item.get(f, "")) for f in ["标题", "第一句"] if f in item)
        if fp not in seen:
            unique.append(item); seen.add(fp)
    r2 = engine.fuzzy_dedup(unique)
    return {"exact_pass": r1.to_dict(), "fuzzy_pass": r2.to_dict(),
            "total_removed": r1.duplicates_removed + r2.fuzzy_duplicates}

def find_near_duplicates(items, threshold=0.9, max_pairs=500):
    engine = DedupEngine()
    sim_pairs = []
    n = min(len(items), 200)
    for i in range(n):
        for j in range(i + 1, n):
            t1 = str(items[i].get("标题", ""))
            t2 = str(items[j].get("标题", ""))
            if abs(len(t1) - len(t2)) > 5: continue
            sim = text_similarity(t1, t2)
            if sim >= threshold:
                sim_pairs.append({"idx1": i, "idx2": j, "similarity": sim,
                                  "title1": t1[:50], "title2": t2[:50]})
    sim_pairs.sort(key=lambda x: x["similarity"], reverse=True)
    return sim_pairs[:max_pairs]
