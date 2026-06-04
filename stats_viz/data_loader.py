# -*- coding: utf-8 -*-
"""
数据加载模块
============
从 poem_json/ 目录加载诗歌数据，构建溯源数据集，支持缓存。
"""

import glob
import os
import re
import json
from typing import Any, Dict, List, Optional, Set

from .config import DATA_DIR, CATEGORY_NAME_MAP, DIMENSION_KEYS, STATS_CACHE_TTL
from .logger import get_logger
from .models import ImageryTraceItem, Poem, AnalysisUnit, PoemLine
from .preprocessor import clean_json_content, extract_poems

logger = get_logger("data_loader")

# 全局数据缓存
_data_cache: Optional[Dict[str, Any]] = None
_cache_timestamp: float = 0.0


def clear_cache() -> None:
    """清除数据缓存"""
    global _data_cache, _cache_timestamp
    _data_cache = None
    _cache_timestamp = 0.0
    logger.info("数据缓存已清除")


def is_cache_valid() -> bool:
    """检查缓存是否有效"""
    import time
    global _data_cache, _cache_timestamp
    return _data_cache is not None and (time.time() - _cache_timestamp) < STATS_CACHE_TTL


def parse_json_file(file_path: str) -> List[Dict]:
    """解析单个 JSON 文件，提取诗歌列表"""
    with open(file_path, "r", encoding="utf-8") as f:
        raw = f.read().strip()
    content, _ = clean_json_content(raw)
    try:
        data = json.loads(content)
        return extract_poems(data)
    except json.JSONDecodeError:
        return []


def build_traceback_dataset(force_reload: bool = False) -> Dict[str, Any]:
    """
    构建溯源数据集（带缓存）

    返回:
        Dict: {"total_poems": int, "total_images": int, "total_authors": int, "traceback": List[dict]}
    """
    global _data_cache, _cache_timestamp
    import time
    if not force_reload and is_cache_valid():
        return _data_cache

    logger.info("开始构建溯源数据集...")

    skip_files = {"all_data.json", "dashboard_interactive_pro.html",
                  "dashboard_FINAL_DASHBOARD.html", "Thesis_Dashboard.html"}

    all_poems_data = []
    seen_fingerprints: Set[str] = set()

    # 扫描 JSON/TXT 文件
    json_files = []
    for ext in ("*.json", "*.txt"):
        json_files.extend(glob.glob(os.path.join(DATA_DIR, ext)))

    logger.info(f"扫描到 {len(json_files)} 个数据文件")

    for fp in json_files:
        fname = os.path.basename(fp)
        if fname in skip_files:
            continue
        poems = parse_json_file(fp)
        for poem in poems:
            title = str(poem.get("标题", "")).strip()
            first_line = ""
            lines_data = poem.get("诗行", [])
            if lines_data and isinstance(lines_data[0], dict):
                first_line = str(lines_data[0].get("原文", "")).strip()
            fp_print = f"{title}_{first_line}"
            if fp_print in seen_fingerprints:
                continue
            seen_fingerprints.add(fp_print)
            all_poems_data.append(poem)

    # 构建溯源表
    traceback = []
    all_authors: Set[str] = set()

    for poem in all_poems_data:
        title = str(poem.get("标题", "未知诗歌")).strip()
        poem_id = str(poem.get("诗歌编号", poem.get("编号", "-"))).strip()
        author = str(poem.get("作者", "")).strip()
        if author:
            all_authors.add(author)
        genre = str(poem.get("分类标签", poem.get("体裁", ""))).strip()

        # 构建诗行映射
        line_map: Dict[str, str] = {}
        for line in poem.get("诗行", []):
            if isinstance(line, dict):
                line_map[str(line.get("诗行编号", ""))] = line.get("原文", "")

        for unit in poem.get("分析单元", []):
            if not isinstance(unit, dict):
                continue
            if str(unit.get("是否意象", "0")).strip() != "1":
                continue

            text = str(unit.get("文本", "")).strip()
            if not text:
                continue

            sub_code = str(unit.get("子类编码", "")).strip()
            line_id = str(unit.get("诗行编号", "")).strip()
            line_text = line_map.get(line_id, "")
            cat_name = CATEGORY_NAME_MAP.get(sub_code, f"其他({sub_code})")

            emo_cat = str(unit.get("情感类别", "")).strip()
            emo_pol = str(unit.get("情感极性", "")).strip()
            emotion_str = f"{emo_cat}({emo_pol})" if emo_pol and emo_cat else (emo_cat or "未知")

            dim_parts = []
            for key in DIMENSION_KEYS:
                val = str(unit.get(key, "")).strip()
                if val and val != "None":
                    dim_parts.append(val)
            dimensions_str = " | ".join(dim_parts) if dim_parts else "-"

            major_code = unit.get("大类编码", "")
            if major_code == "" or major_code is None:
                major_code = sub_code.split("-")[0] if sub_code and "-" in sub_code else ""

            traceback.append({
                "poem_id": poem_id, "title": title, "author": author, "genre": genre,
                "category": cat_name, "imagery_text": text,
                "dimensions": dimensions_str, "emotion": emotion_str,
                "emo_cat": emo_cat, "emo_pol": emo_pol,
                "line_text": line_text, "line_id": line_id,
                "pos_tag": unit.get("词性", ""),
                "component_type": unit.get("成分类型", ""),
                "perception_channel": unit.get("感知通道", ""),
                "material_type": unit.get("素材类型", ""),
                "internal_structure": unit.get("内部结构", ""),
                "reference_source": unit.get("指涉来源", ""),
                "expressive_function": unit.get("表现功能", ""),
                "cultural_circulation": unit.get("文化流通性", ""),
                "cross_cultural": unit.get("跨文化性", ""),
                "cognitive_intensity": unit.get("认知强度", ""),
                "core_imagery": unit.get("核心意象", ""),
                "structural_group": unit.get("结构功能组", ""),
                "major_code": major_code, "sub_code": sub_code,
            })

    result = {
        "total_poems": len(all_poems_data),
        "total_images": len(traceback),
        "total_authors": len(all_authors),
        "traceback": traceback,
    }

    _data_cache = result
    _cache_timestamp = time.time()
    logger.info(f"数据集构建完成: {result['total_poems']}首, {result['total_images']}条意象, {result['total_authors']}位诗人")
    return result


def get_traceback_data() -> List[Dict[str, Any]]:
    """获取溯源数据列表"""
    dataset = build_traceback_dataset()
    return dataset.get("traceback", [])


def get_summary_stats() -> Dict[str, Any]:
    """获取数据集概要统计"""
    dataset = build_traceback_dataset()
    return {
        "total_poems": dataset["total_poems"],
        "total_images": dataset["total_images"],
        "total_authors": dataset["total_authors"],
    }


def get_data_by_author(author: str) -> List[Dict[str, Any]]:
    """获取指定诗人的所有意象数据"""
    data = get_traceback_data()
    return [item for item in data if item.get("author") == author]


def get_data_by_category(category: str) -> List[Dict[str, Any]]:
    """获取指定分类域的所有意象数据"""
    data = get_traceback_data()
    return [item for item in data if item.get("category") == category]


def get_data_by_emotion(emotion: str) -> List[Dict[str, Any]]:
    """获取指定情感类别的所有意象数据"""
    data = get_traceback_data()
    return [item for item in data if item.get("emo_cat") == emotion]


def get_unique_values(field: str) -> List[str]:
    """获取指定字段的所有唯一值"""
    data = get_traceback_data()
    return sorted(set(item.get(field, "") for item in data if item.get(field)))


def get_poem_detail(poem_id: str) -> Optional[Dict[str, Any]]:
    """获取指定诗歌的完整信息（包含其所有意象）"""
    data = get_traceback_data()
    items = [item for item in data if item.get("poem_id") == poem_id]
    if not items:
        return None
    return {
        "poem_id": poem_id,
        "title": items[0].get("title", ""),
        "author": items[0].get("author", ""),
        "genre": items[0].get("genre", ""),
        "imagery_count": len(items),
        "imagery_list": [{"text": i.get("imagery_text"), "category": i.get("category"),
                           "emotion": i.get("emotion")} for i in items],
    }


def search_imagery(keyword: str, max_results: int = 100) -> List[Dict[str, Any]]:
    """跨字段搜索意象"""
    data = get_traceback_data()
    kw = keyword.lower()
    results = []
    for item in data:
        if (kw in str(item.get("imagery_text", "")).lower() or
            kw in str(item.get("title", "")).lower() or
            kw in str(item.get("line_text", "")).lower()):
            results.append(item)
            if len(results) >= max_results:
                break
    return results


def get_data_stats() -> Dict[str, Any]:
    """获取数据集详细统计（含字段覆盖度）"""
    data = get_traceback_data()
    if not data:
        return {}
    total = len(data)
    fields = ["perception_channel", "material_type", "internal_structure", "reference_source",
              "expressive_function", "emo_cat", "emo_pol", "pos_tag", "cultural_circulation",
              "cross_cultural", "cognitive_intensity", "core_imagery", "structural_group"]
    coverage = {}
    for f in fields:
        non_empty = sum(1 for item in data if item.get(f))
        coverage[f] = {"count": non_empty, "pct": round(non_empty / total * 100, 1)}
    return {"total_records": total, "field_coverage": coverage,
            "unique_poems": len(set(item.get("poem_id") for item in data)),
            "unique_authors": len(set(item.get("author") for item in data if item.get("author")))}
