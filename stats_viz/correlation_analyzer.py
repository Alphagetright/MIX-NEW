# -*- coding: utf-8 -*-
"""
关联分析器
==========
意象共现分析、情感-意象关联、诗人-意象偏好分析、意象网络构建。
"""

from collections import defaultdict, Counter
from itertools import combinations
from typing import Any, Dict, List, Optional, Set, Tuple

from .data_loader import get_traceback_data
from .logger import get_logger
from .utils import frequency_count

logger = get_logger("correlation_analyzer")


class CorrelationAnalyzer:
    """
    关联分析器

    分析意象之间的共现关系、情感与意象的关联模式、诗人的意象偏好。

    Usage:
        analyzer = CorrelationAnalyzer()
        co_occurrence = analyzer.imagery_co_occurrence(min_count=3)
        poet_prefs = analyzer.poet_imagery_preferences("李白")
    """

    def __init__(self):
        self._data = get_traceback_data()
        # 按诗歌ID分组
        self._poem_groups: Dict[str, List[Dict]] = defaultdict(list)
        for item in self._data:
            pid = item.get("poem_id", "")
            if pid:
                self._poem_groups[pid].append(item)
        logger.info(f"CorrelationAnalyzer: {len(self._poem_groups)} 首诗歌, {len(self._data)} 条意象")

    # ─── 意象共现分析 ───

    def imagery_co_occurrence(self, min_count: int = 3,
                              max_pairs: int = 100) -> List[Dict[str, Any]]:
        """
        分析同一首诗中意象的共现对

        参数:
            min_count: 最小共现次数
            max_pairs: 最大返回对数

        返回:
            List[Dict]: [{"image1": str, "image2": str, "count": int, "poems": List[str]}, ...]
        """
        pair_counts: Dict[Tuple[str, str], int] = defaultdict(int)
        pair_poems: Dict[Tuple[str, str], Set[str]] = defaultdict(set)

        for pid, items in self._poem_groups.items():
            # 获取该诗中所有去重意象文本
            images = list(set(item.get("imagery_text", "") for item in items if item.get("imagery_text")))
            if len(images) < 2:
                continue
            for img1, img2 in combinations(sorted(images), 2):
                pair_counts[(img1, img2)] += 1
                pair_poems[(img1, img2)].add(pid)

        result = []
        for (img1, img2), cnt in pair_counts.items():
            if cnt >= min_count:
                result.append({
                    "image1": img1, "image2": img2,
                    "count": cnt,
                    "poem_count": len(pair_poems[(img1, img2)]),
                    "strength": round(cnt / len(self._poem_groups) * 100, 2),
                })

        result.sort(key=lambda x: x["count"], reverse=True)
        return result[:max_pairs]

    # ─── 意象聚类 ───

    def imagery_clusters(self, min_co_occurrence: int = 5,
                         max_clusters: int = 10) -> List[Dict[str, Any]]:
        """
        基于共现关系的意象聚类（简单连通分量算法）

        将频繁共现的意象归入同一聚类。
        """
        # 构建共现图
        graph: Dict[str, Set[str]] = defaultdict(set)
        all_images: Set[str] = set()

        for pid, items in self._poem_groups.items():
            images = list(set(item.get("imagery_text", "") for item in items if item.get("imagery_text")))
            all_images.update(images)
            for img1, img2 in combinations(images, 2):
                graph[img1].add(img2)
                graph[img2].add(img1)

        # 简单连通分量
        visited: Set[str] = set()
        clusters = []
        for img in all_images:
            if img in visited:
                continue
            cluster: Set[str] = set()
            stack = [img]
            while stack:
                node = stack.pop()
                if node in visited:
                    continue
                visited.add(node)
                cluster.add(node)
                for neighbor in graph.get(node, set()):
                    if neighbor not in visited:
                        stack.append(neighbor)
            if len(cluster) >= 3:
                clusters.append({"imagery": sorted(cluster), "size": len(cluster)})

        clusters.sort(key=lambda x: x["size"], reverse=True)
        return clusters[:max_clusters]

    # ─── 诗人意象偏好 ───

    def poet_imagery_preferences(self, poet_name: str,
                                 top_n: int = 20) -> Dict[str, Any]:
        """
        分析特定诗人的意象偏好

        返回诗人最常用的意象及其在所有诗人中的独特程度。
        """
        poet_items = [item for item in self._data if item.get("author") == poet_name]
        if not poet_items:
            return {"poet": poet_name, "error": "诗人数据未找到", "top_imagery": []}

        # 该诗人的意象频次
        poet_counts = Counter(item.get("imagery_text", "") for item in poet_items if item.get("imagery_text"))
        poet_total = sum(poet_counts.values())

        # 全体诗人的意象频次
        all_counts = Counter(item.get("imagery_text", "") for item in self._data if item.get("imagery_text"))
        all_total = sum(all_counts.values())

        # 计算 TF-IDF 风格的重要性
        top_imagery = []
        for img, cnt in poet_counts.most_common(top_n):
            poet_freq = cnt / poet_total if poet_total > 0 else 0
            global_freq = all_counts.get(img, 1) / all_total if all_total > 0 else 1
            uniqueness = round(poet_freq / (global_freq + 0.001), 2)
            top_imagery.append({"text": img, "count": cnt, "uniqueness_score": uniqueness})

        return {"poet": poet_name, "total_items": len(poet_items), "unique_imagery": len(poet_counts),
                "top_imagery": top_imagery}

    def poet_similarity_matrix(self, top_poets: int = 15) -> Dict[str, Any]:
        """
        计算诗人之间的意象使用相似度

        基于 Jaccard 相似系数。
        """
        top_authors = [a for a, _ in Counter(
            item.get("author", "") for item in self._data if item.get("author")
        ).most_common(top_poets)]

        # 构建诗人-意象集
        poet_images: Dict[str, Set[str]] = {}
        for author in top_authors:
            items = [item for item in self._data if item.get("author") == author]
            poet_images[author] = set(item.get("imagery_text", "") for item in items if item.get("imagery_text"))

        # 计算相似度矩阵
        similarities = []
        for i, a1 in enumerate(top_authors):
            for a2 in top_authors[i + 1:]:
                set1 = poet_images.get(a1, set())
                set2 = poet_images.get(a2, set())
                if not set1 or not set2:
                    continue
                jaccard = len(set1 & set2) / len(set1 | set2)
                similarities.append({"poet1": a1, "poet2": a2, "similarity": round(jaccard, 4)})

        similarities.sort(key=lambda x: x["similarity"], reverse=True)
        return {"poets": top_poets, "similarities": similarities[:50]}

    # ─── 情感-意象关联 ───

    def emotion_imagery_correlation(self) -> Dict[str, Any]:
        """
        分析不同情感类别下的高频意象
        """
        emotion_images: Dict[str, Counter] = defaultdict(Counter)
        for item in self._data:
            emo = item.get("emo_cat", "未知")
            img = item.get("imagery_text", "")
            if emo and img:
                emotion_images[emo][img] += 1

        result = {}
        for emo, counter in emotion_images.items():
            result[emo] = [{"text": t, "count": c} for t, c in counter.most_common(10)]

        return result

    def cross_dimension_analysis(self, dim1: str = "perception_channel",
                                 dim2: str = "emo_cat") -> Dict[str, Dict[str, int]]:
        """
        交叉维度分析

        参数:
            dim1: 第一个维度字段名
            dim2: 第二个维度字段名

        返回:
            Dict: {dim1_value: {dim2_value: count}, ...}
        """
        cross = defaultdict(lambda: defaultdict(int))
        for item in self._data:
            v1 = item.get(dim1, "未知")
            v2 = item.get(dim2, "未知")
            if v1 and v2:
                cross[v1][v2] += 1
        return {k: dict(v) for k, v in cross.items()}

    # ─── 统计摘要 ───

    def summary(self) -> Dict[str, Any]:
        """关联分析摘要"""
        co_oc = self.imagery_co_occurrence(min_count=5, max_pairs=10)
        clusters = self.imagery_clusters(min_co_occurrence=5, max_clusters=5)
        return {
            "total_poems_analyzed": len(self._poem_groups),
            "total_imagery_items": len(self._data),
            "top_co_occurrence_pairs": co_oc[:10],
            "imagery_clusters": clusters,
            "avg_imagery_per_poem": round(len(self._data) / max(1, len(self._poem_groups)), 1),
        }

    # ─── 进阶分析 ───

    def imagery_network_metrics(self) -> Dict[str, Any]:
        """意象网络度量：计算意象节点的度和中心性"""
        degree: Dict[str, int] = defaultdict(int)
        for pid, items in self._poem_groups.items():
            images = list(set(item.get("imagery_text", "") for item in items if item.get("imagery_text")))
            for img1, img2 in combinations(sorted(images), 2):
                degree[img1] += 1
                degree[img2] += 1
        sorted_degree = sorted(degree.items(), key=lambda x: x[1], reverse=True)
        return {
            "total_nodes": len(degree),
            "total_edges": sum(degree.values()) // 2,
            "avg_degree": round(sum(degree.values()) / max(1, len(degree)), 1),
            "top_central_nodes": [{"node": n, "degree": d} for n, d in sorted_degree[:20]],
        }

    def emotion_transition_pairs(self) -> List[Dict[str, Any]]:
        """
        分析同一首诗中不同情感类别的意象对
        用于研究诗歌情感转换模式
        """
        pairs_count: Dict[Tuple[str, str], int] = defaultdict(int)
        for pid, items in self._poem_groups.items():
            emotions = [item.get("emo_cat", "") for item in items if item.get("emo_cat")]
            unique_emos = list(set(emotions))
            if len(unique_emos) >= 2:
                for e1, e2 in combinations(sorted(unique_emos), 2):
                    if e1 and e2:
                        pairs_count[(e1, e2)] += 1

        result = []
        for (e1, e2), cnt in sorted(pairs_count.items(), key=lambda x: x[1], reverse=True):
            result.append({"emotion_a": e1, "emotion_b": e2, "co_occurrence_count": cnt})
        return result[:30]

    def imagery_uniqueness_by_author(self) -> List[Dict[str, Any]]:
        """
        计算每位诗人使用意象的独特程度
        独特性 = 该诗人独有的意象 / 该诗人总意象文本数
        """
        all_author_images: Dict[str, Counter] = defaultdict(Counter)
        for item in self._data:
            author = item.get("author", "")
            img = item.get("imagery_text", "")
            if author and img:
                all_author_images[author][img] += 1

        result = []
        for author, counter in all_author_images.items():
            if len(counter) < 5:
                continue
            author_images = set(counter.keys())
            others_images = set()
            for other_a, other_counter in all_author_images.items():
                if other_a != author:
                    others_images.update(other_counter.keys())
            unique_to_author = author_images - others_images
            result.append({
                "author": author,
                "total_unique_imagery": len(author_images),
                "exclusive_imagery": len(unique_to_author),
                "uniqueness_pct": round(len(unique_to_author) / len(author_images) * 100, 1),
                "exclusive_examples": sorted(unique_to_author)[:5],
            })
        result.sort(key=lambda x: x["uniqueness_pct"], reverse=True)
        return result

    def full_correlation_report(self) -> Dict[str, Any]:
        """生成完整关联分析报告"""
        return {
            "summary": self.summary(),
            "top_co_occurrence": self.imagery_co_occurrence(min_count=5, max_pairs=30),
            "clusters": self.imagery_clusters(min_co_occurrence=4, max_clusters=15),
            "network_metrics": self.imagery_network_metrics(),
            "emotion_transitions": self.emotion_transition_pairs(),
            "poet_similarities": self.poet_similarity_matrix(top_poets=15),
            "emotion_imagery_map": self.emotion_imagery_correlation(),
            "author_uniqueness": self.imagery_uniqueness_by_author(),
        }
