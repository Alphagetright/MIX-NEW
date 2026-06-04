# -*- coding: utf-8 -*-
"""
数据统计分析服务 — 多维度聚合统计
"""
import json
from collections import Counter, defaultdict
from typing import List, Dict, Any

from config import CATEGORY_NAME_MAP, CATEGORY_MAJOR_MAP
from logger import get_logger

logger = get_logger("analytics")


class StatsService:
    """意象数据统计分析服务"""

    def __init__(self, traceback_data: List[Dict] = None):
        self.data = traceback_data or []
        self._cache = {}

    def set_data(self, data: List[Dict]):
        self.data = data
        self._cache.clear()

    # 基础统计

    def total_images(self) -> int:
        return len(self.data)

    def total_poems(self) -> int:
        return len({item.get("poem_id") for item in self.data if item.get("poem_id")})

    def total_authors(self) -> int:
        return len({item.get("author") for item in self.data if item.get("author")})

    # 意象频次统计

    def top_images(self, n: int = 50) -> List[Dict]:
        counter = Counter()
        for item in self.data:
            txt = item.get("文本") or item.get("txt") or ""
            if txt:
                counter[txt] += 1
        return [{"text": txt, "count": cnt} for txt, cnt in counter.most_common(n)]

    # 分类统计

    def category_distribution(self) -> List[Dict]:
        counter = Counter()
        for item in self.data:
            cat = item.get("cat", "未分类")
            counter[cat] += 1
        total = sum(counter.values()) or 1
        return [
            {"category": cat, "count": cnt, "percentage": round(cnt / total * 100, 2)}
            for cat, cnt in counter.most_common()
        ]

    def major_category_distribution(self) -> List[Dict]:
        counter = Counter()
        for item in self.data:
            code = str(item.get("大类编码", ""))
            major = CATEGORY_MAJOR_MAP.get(code, "其他")
            counter[major] += 1
        total = sum(counter.values()) or 1
        return [
            {"category": cat, "count": cnt, "percentage": round(cnt / total * 100, 2)}
            for cat, cnt in counter.most_common()
        ]

    def sub_category_distribution(self, major_code: str = None) -> List[Dict]:
        counter = Counter()
        for item in self.data:
            code = str(item.get("子类编码", ""))
            if major_code and not code.startswith(major_code):
                continue
            cat = CATEGORY_NAME_MAP.get(code, f"未知子类 ({code})")
            counter[cat] += 1
        total = sum(counter.values()) or 1
        return [
            {"category": cat, "count": cnt, "percentage": round(cnt / total * 100, 2)}
            for cat, cnt in counter.most_common()
        ]

    # 诗人统计

    def author_statistics(self) -> List[Dict]:
        author_images = defaultdict(list)
        for item in self.data:
            author = item.get("author") or item.get("作者") or "未知"
            txt = item.get("文本") or item.get("txt") or ""
            if txt:
                author_images[author].append(txt)

        results = []
        for author, images in sorted(author_images.items(), key=lambda x: -len(x[1])):
            unique_images = set(images)
            top = Counter(images).most_common(5)
            results.append({
                "author": author,
                "image_count": len(images),
                "unique_image_count": len(unique_images),
                "poem_count": len({
                    item.get("poem_id") for item in self.data
                    if (item.get("author") or item.get("作者")) == author
                }),
                "top_images": [{"text": t, "count": c} for t, c in top],
            })
        return results

    # 情感分析

    def emotion_distribution(self) -> List[Dict]:
        counter = Counter()
        for item in self.data:
            emo = item.get("情感类别") or item.get("emo_cat") or "未知"
            counter[emo] += 1
        total = sum(counter.values()) or 1
        return [
            {"emotion": emo, "count": cnt, "percentage": round(cnt / total * 100, 2)}
            for emo, cnt in counter.most_common()
        ]

    def emotion_polarity_distribution(self) -> List[Dict]:
        counter = Counter()
        for item in self.data:
            pol = item.get("情感极性") or "未标注"
            counter[pol] += 1
        total = sum(counter.values()) or 1
        return [
            {"polarity": pol, "count": cnt, "percentage": round(cnt / total * 100, 2)}
            for pol, cnt in counter.most_common()
        ]

    # 感知通道统计

    def perception_channel_distribution(self) -> List[Dict]:
        counter = Counter()
        for item in self.data:
            ch = item.get("感知通道") or "未标注"
            counter[ch] += 1
        total = sum(counter.values()) or 1
        return [
            {"channel": ch, "count": cnt, "percentage": round(cnt / total * 100, 2)}
            for ch, cnt in counter.most_common()
        ]

    # 诗词体裁统计

    def genre_distribution(self) -> List[Dict]:
        """按诗歌体裁分类统计"""
        counter = Counter()
        for item in self.data:
            genre = item.get("genre", "未分类")
            if genre:
                counter[genre] += 1
        total = sum(counter.values()) or 1
        return [
            {"genre": g, "count": cnt, "percentage": round(cnt / total * 100, 2)}
            for g, cnt in counter.most_common()
        ]

    # 内部结构统计

    def internal_structure_distribution(self) -> List[Dict]:
        """内部结构维度统计"""
        counter = Counter()
        for item in self.data:
            val = item.get("内部结构") or "未标注"
            counter[val] += 1
        total = sum(counter.values()) or 1
        return [
            {"structure": s, "count": cnt, "percentage": round(cnt / total * 100, 2)}
            for s, cnt in counter.most_common()
        ]

    # 表现功能统计

    def function_distribution(self) -> List[Dict]:
        """表现功能维度统计"""
        counter = Counter()
        for item in self.data:
            val = item.get("表现功能") or "未标注"
            counter[val] += 1
        total = sum(counter.values()) or 1
        return [
            {"function": f, "count": cnt, "percentage": round(cnt / total * 100, 2)}
            for f, cnt in counter.most_common()
        ]

    # 核心意象统计

    def core_image_distribution(self) -> List[Dict]:
        """核心意象标注统计"""
        counter = Counter()
        for item in self.data:
            val = item.get("核心意象") or "未标注"
            counter[val] += 1
        total = sum(counter.values()) or 1
        return [
            {"core_image": c, "count": cnt, "percentage": round(cnt / total * 100, 2)}
            for c, cnt in counter.most_common()
        ]

    # 指涉来源统计

    def reference_source_distribution(self) -> List[Dict]:
        """指涉来源维度统计"""
        counter = Counter()
        for item in self.data:
            val = item.get("指涉来源") or "未标注"
            counter[val] += 1
        total = sum(counter.values()) or 1
        return [
            {"source": s, "count": cnt, "percentage": round(cnt / total * 100, 2)}
            for s, cnt in counter.most_common()
        ]

    # 认知强度统计

    def cognitive_intensity_distribution(self) -> List[Dict]:
        """认知强度维度分布"""
        counter = Counter()
        for item in self.data:
            val = item.get("认知强度") or "未标注"
            counter[val] += 1
        total = sum(counter.values()) or 1
        return [
            {"intensity": c, "count": cnt, "percentage": round(cnt / total * 100, 2)}
            for c, cnt in counter.most_common()
        ]

    # 素材类型统计

    def material_type_distribution(self) -> List[Dict]:
        """素材类型维度统计"""
        counter = Counter()
        for item in self.data:
            val = item.get("素材类型") or "未标注"
            counter[val] += 1
        total = sum(counter.values()) or 1
        return [
            {"material": m, "count": cnt, "percentage": round(cnt / total * 100, 2)}
            for m, cnt in counter.most_common()
        ]

    # 跨文化性统计

    def cross_cultural_distribution(self) -> List[Dict]:
        """跨文化性维度统计"""
        counter = Counter()
        for item in self.data:
            val = item.get("跨文化性") or "未标注"
            counter[val] += 1
        total = sum(counter.values()) or 1
        return [
            {"level": c, "count": cnt, "percentage": round(cnt / total * 100, 2)}
            for c, cnt in counter.most_common()
        ]

    # 综合报告

    def summary_report(self) -> Dict:
        return {
            "total_images": self.total_images(),
            "total_poems": self.total_poems(),
            "total_authors": self.total_authors(),
            "category_count": len(self.category_distribution()),
            "emotion_categories": len(self.emotion_distribution()),
            "top_images": self.top_images(20),
            "category_stats": self.category_distribution(),
            "major_category_stats": self.major_category_distribution(),
            "emotion_stats": self.emotion_distribution(),
            "emotion_polarity_stats": self.emotion_polarity_distribution(),
            "perception_channel_stats": self.perception_channel_distribution(),
            "genre_stats": self.genre_distribution(),
            "internal_structure_stats": self.internal_structure_distribution(),
            "function_stats": self.function_distribution(),
            "core_image_stats": self.core_image_distribution(),
            "reference_source_stats": self.reference_source_distribution(),
            "cognitive_intensity_stats": self.cognitive_intensity_distribution(),
            "material_type_stats": self.material_type_distribution(),
            "cross_cultural_stats": self.cross_cultural_distribution(),
        }

    # 跨表分析

    def cross_analysis(self) -> Dict:
        """情感 × 分类域 交叉分析"""
        cross = defaultdict(lambda: defaultdict(int))
        for item in self.data:
            emo = item.get("情感类别") or "未知"
            cat = item.get("cat", "未分类")
            cross[cat][emo] += 1

        result = {}
        for cat, emotions in cross.items():
            total = sum(emotions.values())
            result[cat] = [
                {"emotion": emo, "count": cnt, "percentage": round(cnt / total * 100, 2)}
                for emo, cnt in sorted(emotions.items(), key=lambda x: -x[1])
            ]
        return result


def build_analytics_api(stats_service: StatsService) -> Dict:
    """生成供 API 返回的分析数据"""
    return {
        "summary": stats_service.summary_report(),
        "cross_analysis": stats_service.cross_analysis(),
    }
