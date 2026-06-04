# -*- coding: utf-8 -*-
"""
数据探索器
==========
提供交互式数据探索功能：文本搜索、多维度筛选、排序、分页、统计摘要。
"""

from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from .data_loader import get_traceback_data
from .logger import get_logger
from .utils import truncate

logger = get_logger("data_explorer")


class DataExplorer:
    """
    意象数据探索器

    支持多维筛选、全文搜索、分页浏览、统计摘要。
    为前端溯源数据表和筛选栏提供后端数据支持。

    Usage:
        explorer = DataExplorer()
        result = explorer.search("月亮").filter_by_category("天文意象").get_page(1)
    """

    def __init__(self, data: Optional[List[Dict[str, Any]]] = None):
        self._all_data = data if data is not None else get_traceback_data()
        self._filtered: List[Dict[str, Any]] = list(self._all_data)
        self._filters_applied: List[str] = []
        logger.info(f"DataExplorer 初始化: {len(self._all_data)} 条记录")

    # ─── 数据操作 ───

    def reload(self) -> "DataExplorer":
        """重新加载数据（清除所有筛选）"""
        self._all_data = get_traceback_data()
        self._filtered = list(self._all_data)
        self._filters_applied = []
        return self

    def reset_filters(self) -> "DataExplorer":
        """重置所有筛选条件"""
        self._filtered = list(self._all_data)
        self._filters_applied = []
        return self

    # ─── 搜索 ───

    def search(self, keyword: str, fields: Optional[List[str]] = None) -> "DataExplorer":
        """
        全文搜索

        参数:
            keyword: 搜索关键词
            fields: 搜索字段列表（None=搜索全部字段）
        """
        if not keyword or not keyword.strip():
            return self

        kw = keyword.strip().lower()
        if fields is None:
            fields = ["imagery_text", "title", "author", "category", "line_text"]

        self._filtered = [
            item for item in self._filtered
            if any(kw in str(item.get(f, "")).lower() for f in fields)
        ]
        self._filters_applied.append(f"search:{keyword}")
        logger.debug(f"搜索 '{keyword}': {len(self._filtered)} 条匹配")
        return self

    # ─── 筛选 ───

    def filter_by_category(self, category: str) -> "DataExplorer":
        """按分类域筛选"""
        if not category or category == "全部":
            return self
        self._filtered = [item for item in self._filtered if item.get("category") == category]
        self._filters_applied.append(f"category:{category}")
        return self

    def filter_by_genre(self, genre: str) -> "DataExplorer":
        """按体裁筛选"""
        if not genre or genre == "全部":
            return self
        self._filtered = [item for item in self._filtered if item.get("genre") == genre]
        self._filters_applied.append(f"genre:{genre}")
        return self

    def filter_by_emotion(self, emotion: str) -> "DataExplorer":
        """按情感类别筛选"""
        if not emotion or emotion == "全部":
            return self
        self._filtered = [item for item in self._filtered if item.get("emo_cat") == emotion]
        self._filters_applied.append(f"emotion:{emotion}")
        return self

    def filter_by_author(self, author: str) -> "DataExplorer":
        """按诗人筛选"""
        if not author or author == "全部":
            return self
        self._filtered = [item for item in self._filtered if item.get("author") == author]
        self._filters_applied.append(f"author:{author}")
        return self

    def filter_by_perception(self, channel: str) -> "DataExplorer":
        """按感知通道筛选"""
        if not channel or channel == "全部":
            return self
        self._filtered = [item for item in self._filtered if item.get("perception_channel") == channel]
        self._filters_applied.append(f"perception:{channel}")
        return self

    def filter_by_emotion_polarity(self, polarity: str) -> "DataExplorer":
        """按情感极性筛选"""
        if not polarity or polarity == "全部":
            return self
        self._filtered = [item for item in self._filtered if item.get("emo_pol") == polarity]
        self._filters_applied.append(f"polarity:{polarity}")
        return self

    def filter_custom(self, predicate: Callable[[Dict[str, Any]], bool],
                      label: str = "custom") -> "DataExplorer":
        """自定义筛选条件"""
        self._filtered = [item for item in self._filtered if predicate(item)]
        self._filters_applied.append(label)
        return self

    # ─── 排序 ───

    def sort_by(self, key: str, reverse: bool = True) -> "DataExplorer":
        """按指定字段排序"""
        self._filtered.sort(key=lambda x: x.get(key, ""), reverse=reverse)
        return self

    # ─── 分页 ───

    def get_page(self, page: int = 1, page_size: int = 25) -> Dict[str, Any]:
        """
        获取分页数据

        返回:
            Dict: {"rows": [...], "total": int, "page": int, "total_pages": int, "page_size": int}
        """
        total = len(self._filtered)
        total_pages = max(1, (total + page_size - 1) // page_size)
        page = max(1, min(page, total_pages))
        start = (page - 1) * page_size
        end = min(start + page_size, total)
        return {
            "rows": self._filtered[start:end],
            "total": total,
            "page": page,
            "total_pages": total_pages,
            "page_size": page_size,
            "filters_applied": self._filters_applied,
        }

    def get_all_filtered(self) -> List[Dict[str, Any]]:
        """获取所有筛选后的数据"""
        return self._filtered

    def get_count(self) -> int:
        """获取筛选后数据量"""
        return len(self._filtered)

    # ─── 统计 ───

    def get_filtered_summary(self) -> Dict[str, Any]:
        """获取筛选结果摘要"""
        categories = set()
        genres = set()
        emotions = set()
        authors = set()
        for item in self._filtered:
            if item.get("category"):
                categories.add(item["category"])
            if item.get("genre"):
                genres.add(item["genre"])
            if item.get("emo_cat"):
                emotions.add(item["emo_cat"])
            if item.get("author"):
                authors.add(item["author"])
        return {
            "total": len(self._filtered),
            "unique_categories": len(categories),
            "unique_genres": len(genres),
            "unique_emotions": len(emotions),
            "unique_authors": len(authors),
            "categories": sorted(categories),
            "genres": sorted(genres),
            "emotions": sorted(emotions),
            "filters": self._filters_applied,
        }

    def get_available_filter_values(self) -> Dict[str, List[str]]:
        """
        获取当前筛选结果中可用的筛选值（用于前端动态生成下拉菜单）

        返回:
            Dict: {"categories": [...], "genres": [...], "emotions": [...], "authors": [...]}
        """
        base = self._all_data if len(self._filters_applied) <= 1 else self._filtered
        cats = sorted(set(item.get("category", "") for item in base if item.get("category")))
        genres = sorted(set(item.get("genre", "") for item in base if item.get("genre")))
        emos = sorted(set(item.get("emo_cat", "") for item in base if item.get("emo_cat")))
        authors = sorted(set(item.get("author", "") for item in base if item.get("author")))
        return {"categories": cats, "genres": genres, "emotions": emos, "authors": authors}

    # ─── 导出 ───

    def export_filtered(self, fmt: str = "csv", fields: Optional[List[str]] = None) -> str:
        """导出当前筛选结果"""
        from .export_service import export_to_csv, export_to_json
        from datetime import datetime
        if fmt == "csv":
            record = export_to_csv(self._filtered, prefix="filtered_export", fields=fields)
        else:
            record = export_to_json(self._filtered, prefix="filtered_export")
        return record.file_path if record.status == "success" else ""


# ─── 便捷函数 ───

def quick_search(keyword: str, max_results: int = 100) -> List[Dict[str, Any]]:
    """快速搜索意象文本"""
    explorer = DataExplorer()
    return explorer.search(keyword, fields=["imagery_text"]).get_all_filtered()[:max_results]


def list_all_categories() -> List[str]:
    """列出所有分类域"""
    explorer = DataExplorer()
    vals = explorer.get_available_filter_values()
    return vals["categories"]


def list_all_genres() -> List[str]:
    """列出所有体裁"""
    explorer = DataExplorer()
    return explorer.get_available_filter_values()["genres"]


def list_all_authors() -> List[str]:
    """列出所有诗人"""
    explorer = DataExplorer()
    return explorer.get_available_filter_values()["authors"]
