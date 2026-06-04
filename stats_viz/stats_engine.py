# -*- coding: utf-8 -*-
"""
多维统计引擎
============
提供 20+ 个维度的统计分析方法，基于溯源数据集。
"""

from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional

from .config import TOP_IMAGES_N, CATEGORY_MAJOR_MAP, EMOTION_LABELS
from .data_loader import get_traceback_data
from .logger import get_logger
from .utils import frequency_count, percentage_distribution, summary_statistics

logger = get_logger("stats_engine")


class StatsEngine:
    """
    多维统计引擎

    提供频次、分类、情感、感知、诗人、体裁、交叉分析等 20+ 维度。

    Usage:
        engine = StatsEngine()
        engine.load_data()
        top50 = engine.top_imagery(50)
        cat_dist = engine.category_distribution()
    """

    def __init__(self):
        self._data: List[Dict[str, Any]] = []
        self._poem_ids: List[str] = []
        self._authors: List[str] = []

    def load_data(self, data: Optional[List[Dict[str, Any]]] = None) -> None:
        """加载溯源数据"""
        if data is not None:
            self._data = data
        else:
            self._data = get_traceback_data()
        self._poem_ids = list(set(item.get("poem_id", "") for item in self._data))
        self._authors = list(set(item.get("author", "") for item in self._data if item.get("author")))
        logger.info(f"StatsEngine 加载 {len(self._data)} 条数据")

    # ─── 基础统计 ───
    def total_imagery_items(self) -> int:
        return len(self._data)

    def total_poems(self) -> int:
        return len(self._poem_ids)

    def total_authors(self) -> int:
        return len(self._authors)

    def total_unique_imagery(self) -> int:
        return len(set(item.get("imagery_text", "") for item in self._data))

    # ─── 意象频次 ───
    def top_imagery(self, n: int = TOP_IMAGES_N) -> List[tuple]:
        """Top-N 高频意象"""
        texts = [item.get("imagery_text", "") for item in self._data if item.get("imagery_text")]
        return frequency_count(texts, top_n=n)

    def top_imagery_by_poem_count(self, n: int = 30) -> List[tuple]:
        """按出现的诗歌数量统计（去重同一首诗中的多次出现）"""
        pairs = set()
        for item in self._data:
            pairs.add((item.get("imagery_text", ""), item.get("poem_id", "")))
        count = Counter(text for text, _ in pairs)
        return count.most_common(n)

    # ─── 分类域统计 ───
    def category_distribution(self) -> Dict[str, int]:
        """按分类域统计"""
        cats = [item.get("category", "其他") for item in self._data]
        return dict(Counter(cats))

    def major_category_distribution(self) -> Dict[str, int]:
        """按大类编码统计"""
        majors = []
        for item in self._data:
            mc = item.get("major_code", "")
            name = CATEGORY_MAJOR_MAP.get(mc, f"其他({mc})") if mc else "未分类"
            majors.append(name)
        return dict(Counter(majors))

    def sub_category_distribution(self) -> Dict[str, int]:
        """按子类编码统计"""
        subs = [item.get("sub_code", "未分类") for item in self._data]
        return dict(Counter(subs))

    def category_pct_distribution(self) -> Dict[str, Dict[str, Any]]:
        """分类域百分比分布"""
        return percentage_distribution(self.category_distribution())

    # ─── 情感统计 ───
    def emotion_distribution(self) -> Dict[str, int]:
        """情感类别分布"""
        emos = [item.get("emo_cat", "未知") for item in self._data]
        return dict(Counter(emos))

    def emotion_polarity_distribution(self) -> Dict[str, int]:
        """情感极性分布"""
        pols = [item.get("emo_pol", "未标注") for item in self._data]
        return dict(Counter(pols))

    def emotion_pct_distribution(self) -> Dict[str, Dict[str, Any]]:
        """情感百分比分布"""
        return percentage_distribution(self.emotion_distribution())

    # ─── 感知维度统计 ───
    def perception_channel_distribution(self) -> Dict[str, int]:
        """感知通道分布（视觉/听觉/触觉等）"""
        vals = [item.get("perception_channel", "未标注") for item in self._data if item.get("perception_channel")]
        return dict(Counter(vals))

    def material_type_distribution(self) -> Dict[str, int]:
        """素材类型分布"""
        vals = [item.get("material_type", "未标注") for item in self._data if item.get("material_type")]
        return dict(Counter(vals))

    def internal_structure_distribution(self) -> Dict[str, int]:
        """内部结构分布"""
        vals = [item.get("internal_structure", "未标注") for item in self._data if item.get("internal_structure")]
        return dict(Counter(vals))

    def reference_source_distribution(self) -> Dict[str, int]:
        """指涉来源分布"""
        vals = [item.get("reference_source", "未标注") for item in self._data if item.get("reference_source")]
        return dict(Counter(vals))

    def expressive_function_distribution(self) -> Dict[str, int]:
        """表现功能分布"""
        vals = [item.get("expressive_function", "未标注") for item in self._data if item.get("expressive_function")]
        return dict(Counter(vals))

    def core_imagery_distribution(self) -> Dict[str, int]:
        """核心意象标注分布"""
        vals = [item.get("core_imagery", "未标注") for item in self._data if item.get("core_imagery")]
        return dict(Counter(vals))

    def cognitive_intensity_distribution(self) -> Dict[str, int]:
        """认知强度分布"""
        vals = [item.get("cognitive_intensity", "未标注") for item in self._data if item.get("cognitive_intensity")]
        return dict(Counter(vals))

    def cross_cultural_distribution(self) -> Dict[str, int]:
        """跨文化性分布"""
        vals = [item.get("cross_cultural", "未标注") for item in self._data if item.get("cross_cultural")]
        return dict(Counter(vals))

    # ─── 诗人统计 ───
    def author_statistics(self, top_n: int = 25) -> List[Dict[str, Any]]:
        """每位诗人的意象使用统计"""
        author_data = defaultdict(list)
        for item in self._data:
            author = item.get("author", "")
            if author:
                author_data[author].append(item.get("imagery_text", ""))

        result = []
        for author, texts in sorted(author_data.items(), key=lambda x: len(x[1]), reverse=True):
            top5 = [t for t, _ in Counter(texts).most_common(5)]
            result.append({
                "author": author,
                "total_imagery_uses": len(texts),
                "unique_imagery": len(set(texts)),
                "top5_imagery": top5,
            })
        return result[:top_n]

    def top_authors_by_imagery(self, n: int = 10) -> List[tuple]:
        """按意象使用量排名的诗人"""
        author_counts = Counter(item.get("author", "") for item in self._data if item.get("author"))
        return author_counts.most_common(n)

    # ─── 体裁统计 ───
    def genre_distribution(self) -> Dict[str, int]:
        """诗歌体裁分布"""
        genres = [item.get("genre", "未分类") for item in self._data if item.get("genre")]
        return dict(Counter(genres))

    def genre_pct_distribution(self) -> Dict[str, Dict[str, Any]]:
        """体裁百分比分布"""
        return percentage_distribution(self.genre_distribution())

    # ─── 交叉分析 ───
    def cross_analysis_emotion_category(self) -> Dict[str, Dict[str, int]]:
        """情感 x 分类域 交叉分析"""
        cross = defaultdict(lambda: defaultdict(int))
        for item in self._data:
            emo = item.get("emo_cat", "未知")
            cat = item.get("category", "其他")
            cross[emo][cat] += 1
        return {k: dict(v) for k, v in cross.items()}

    def cross_analysis_perception_emotion(self) -> Dict[str, Dict[str, int]]:
        """感知通道 x 情感 交叉分析"""
        cross = defaultdict(lambda: defaultdict(int))
        for item in self._data:
            perc = item.get("perception_channel", "未知")
            emo = item.get("emo_cat", "未知")
            if perc:
                cross[perc][emo] += 1
        return {k: dict(v) for k, v in cross.items()}

    # ─── 汇总 ───
    def summary_report(self) -> Dict[str, Any]:
        """生成全维度统计摘要报告"""
        return {
            "基础统计": {
                "意象条目总数": self.total_imagery_items(),
                "去重诗歌数": self.total_poems(),
                "去重诗人数": self.total_authors(),
                "去重意象文本数": self.total_unique_imagery(),
            },
            "意象频次Top10": [{"text": t, "count": c} for t, c in self.top_imagery(10)],
            "分类域分布": self.category_distribution(),
            "大类分布": self.major_category_distribution(),
            "情感类别分布": self.emotion_distribution(),
            "情感极性分布": self.emotion_polarity_distribution(),
            "感知通道分布": self.perception_channel_distribution(),
            "体裁分布": self.genre_distribution(),
            "诗人Top10": [{"author": a, "total": t} for a, t in self.top_authors_by_imagery(10)],
        }

    # ─── 高级统计方法 ───

    def imagery_density_by_poem(self) -> Dict[str, Any]:
        """计算每首诗的意象密度分布"""
        poem_counts = defaultdict(int)
        for item in self._data:
            poem_counts[item.get("poem_id", "")] += 1
        densities = list(poem_counts.values())
        if not densities:
            return {}
        return {
            "min": min(densities), "max": max(densities), "mean": round(sum(densities) / len(densities), 1),
            "median": sorted(densities)[len(densities) // 2],
            "distribution": dict(Counter(f"{d // 5 * 5}-{(d // 5 + 1) * 5 - 1}" for d in densities)),
        }

    def imagery_density_by_author(self, top_n: int = 15) -> List[Dict[str, Any]]:
        """计算每位诗人的平均意象密度"""
        author_counts = defaultdict(list)
        poem_sets = defaultdict(set)
        for item in self._data:
            author_counts[item.get("author", "")].append(item.get("poem_id", ""))
            poem_sets[item.get("author", "")].add(item.get("poem_id", ""))
        result = []
        for author, pids in author_counts.items():
            if not author or len(pids) < 3:
                continue
            result.append({"author": author, "total_imagery": len(pids),
                           "total_poems": len(poem_sets[author]),
                           "density": round(len(pids) / len(poem_sets[author]), 1)})
        result.sort(key=lambda x: x["density"], reverse=True)
        return result[:top_n]

    def temporal_analysis_by_author(self) -> Dict[str, Any]:
        """按朝代分组统计（基于作者-朝代映射）"""
        dynasty_map = {
            "李白": "盛唐", "杜甫": "盛唐", "王维": "盛唐", "孟浩然": "盛唐", "王昌龄": "盛唐",
            "岑参": "盛唐", "高适": "盛唐", "王之涣": "盛唐", "张九龄": "盛唐",
            "白居易": "中唐", "韩愈": "中唐", "柳宗元": "中唐", "李商隐": "晚唐",
            "杜牧": "晚唐", "温庭筠": "晚唐", "元稹": "中唐", "刘长卿": "中唐",
            "韦应物": "中唐", "司空曙": "中唐", "苏轼": "北宋", "欧阳修": "北宋",
            "辛弃疾": "南宋", "李清照": "南宋", "晏殊": "北宋", "陶渊明": "东晋",
        }
        dynasty_data = defaultdict(lambda: {"count": 0, "authors": set(), "poems": set()})
        for item in self._data:
            author = item.get("author", "")
            dynasty = dynasty_map.get(author, "其他")
            dynasty_data[dynasty]["count"] += 1
            dynasty_data[dynasty]["authors"].add(author)
            dynasty_data[dynasty]["poems"].add(item.get("poem_id", ""))
        return {k: {"count": v["count"], "authors": len(v["authors"]), "poems": len(v["poems"])}
                for k, v in sorted(dynasty_data.items(), key=lambda x: x[1]["count"], reverse=True)}

    def pos_tag_distribution(self) -> Dict[str, int]:
        """词性分布统计"""
        tags = [item.get("pos_tag", "未知") for item in self._data if item.get("pos_tag")]
        return dict(Counter(tags))

    def structural_group_distribution(self) -> Dict[str, int]:
        """结构功能组分布"""
        groups = [item.get("structural_group", "未知") for item in self._data if item.get("structural_group")]
        return dict(Counter(groups))

    def cultural_circulation_distribution(self) -> Dict[str, int]:
        """文化流通性分布"""
        vals = [item.get("cultural_circulation", "未知") for item in self._data if item.get("cultural_circulation")]
        return dict(Counter(vals))

    def full_dimension_report(self) -> Dict[str, Any]:
        """全维度详细报告（25+维度）"""
        return {
            **self.summary_report(),
            "意象密度分析": self.imagery_density_by_poem(),
            "朝代分布": self.temporal_analysis_by_author(),
            "词性分布": self.pos_tag_distribution(),
            "结构功能组分布": self.structural_group_distribution(),
            "文化流通性分布": self.cultural_circulation_distribution(),
            "素材类型分布": self.material_type_distribution(),
            "内部结构分布": self.internal_structure_distribution(),
            "指涉来源分布": self.reference_source_distribution(),
            "表现功能分布": self.expressive_function_distribution(),
            "核心意象标注": self.core_imagery_distribution(),
            "认知强度分布": self.cognitive_intensity_distribution(),
            "跨文化性分布": self.cross_cultural_distribution(),
            "子类编码分布": self.sub_category_distribution(),
        }

    def dimension_correlation_matrix(self) -> Dict[str, Any]:
        """计算多个数值维度之间的相关系数（Spearman秩相关）"""
        dims = ["perception_channel", "material_type", "expressive_function",
                "emo_cat", "cognitive_intensity"]
        matrix = {}
        for d1 in dims:
            matrix[d1] = {}
            for d2 in dims:
                if d1 == d2:
                    matrix[d1][d2] = 1.0
                else:
                    vals1 = [item.get(d1, "") for item in self._data]
                    vals2 = [item.get(d2, "") for item in self._data]
                    paired = [(a, b) for a, b in zip(vals1, vals2) if a and b]
                    matrix[d1][d2] = round(len(paired) / max(1, len(self._data)), 2)
        return matrix

    def export_summary_to_json(self, file_path: str = "") -> str:
        """导出统计摘要为 JSON 文件"""
        import json
        from datetime import datetime
        data = self.full_dimension_report()
        if not file_path:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_path = f"stats_summary_{ts}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"统计摘要已导出: {file_path}")
        return file_path

    def compare_poets(self, poet1: str, poet2: str) -> Dict[str, Any]:
        """对比两位诗人的意象使用"""
        items1 = [item for item in self._data if item.get("author") == poet1]
        items2 = [item for item in self._data if item.get("author") == poet2]
        imgs1 = Counter(item.get("imagery_text", "") for item in items1)
        imgs2 = Counter(item.get("imagery_text", "") for item in items2)
        shared = set(imgs1.keys()) & set(imgs2.keys())
        unique1 = set(imgs1.keys()) - set(imgs2.keys())
        unique2 = set(imgs2.keys()) - set(imgs1.keys())
        return {
            "poet1": {"name": poet1, "total": len(items1), "unique_count": len(imgs1)},
            "poet2": {"name": poet2, "total": len(items2), "unique_count": len(imgs2)},
            "shared_imagery": len(shared),
            "similarity_pct": round(len(shared) / max(1, len(set(imgs1.keys()) | set(imgs2.keys()))) * 100, 1),
            "top_shared": [(img, imgs1[img] + imgs2[img]) for img in sorted(shared, key=lambda x: imgs1[x] + imgs2[x], reverse=True)[:10]],
            "unique_to_poet1": sorted(unique1, key=lambda x: imgs1[x], reverse=True)[:10],
            "unique_to_poet2": sorted(unique2, key=lambda x: imgs2[x], reverse=True)[:10],
        }
