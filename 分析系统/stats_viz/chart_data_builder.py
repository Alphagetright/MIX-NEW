# -*- coding: utf-8 -*-
"""
图表数据构建器
=============
将统计引擎的输出转换为 ECharts 图表所需的数据格式。
支持柱状图、饼图、散点图、热力图等图表类型。
"""

from typing import Any, Dict, List, Optional, Tuple

from .stats_engine import StatsEngine
from .config import CHART_DEFAULT_COLOR, CHART_CATEGORY_COLOR, TOP_IMAGES_N


class ChartDataBuilder:
    """
    图表数据构建器

    将 StatsEngine 的统计结果转换为可视化图表所需的数据结构。

    Usage:
        engine = StatsEngine(); engine.load_data()
        builder = ChartDataBuilder(engine)
        bar_option = builder.build_top_imagery_bar()
        pie_option = builder.build_category_pie()
    """

    def __init__(self, engine: StatsEngine):
        self._engine = engine

    # ─── 柱状图 ───

    def build_top_imagery_bar(self, n: int = TOP_IMAGES_N) -> Dict[str, Any]:
        """核心意象 Top-N 柱状图（横向）"""
        data = self._engine.top_imagery(n)
        return {
            "title": {"text": f"核心意象 Top{n}", "left": "center"},
            "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"}},
            "grid": {"top": "8%", "left": "5%", "right": "5%", "bottom": "15%"},
            "xAxis": {
                "type": "category",
                "data": [x[0] for x in data],
                "axisLabel": {"interval": 0, "rotate": 30},
            },
            "yAxis": {"type": "value"},
            "dataZoom": [
                {"type": "slider", "show": True, "xAxisIndex": [0], "start": 0, "end": 40, "bottom": 0}
            ],
            "series": [{
                "name": "频次", "type": "bar", "barWidth": "60%",
                "data": [x[1] for x in data],
                "itemStyle": {"color": CHART_DEFAULT_COLOR},
            }],
        }

    def build_category_bar(self) -> Dict[str, Any]:
        """意象分类域分布柱状图"""
        dist = self._engine.category_distribution()
        sorted_data = sorted(dist.items(), key=lambda x: x[1], reverse=True)
        return {
            "title": {"text": "意象分类域分布", "left": "center"},
            "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"}},
            "grid": {"top": "8%", "left": "5%", "right": "5%", "bottom": "15%"},
            "xAxis": {
                "type": "category",
                "data": [x[0] for x in sorted_data],
                "axisLabel": {"interval": 0, "rotate": 15},
            },
            "yAxis": {"type": "value"},
            "series": [{
                "name": "频次", "type": "bar", "barWidth": "50%",
                "data": [x[1] for x in sorted_data],
                "itemStyle": {"color": CHART_CATEGORY_COLOR},
            }],
        }

    def build_major_category_bar(self) -> Dict[str, Any]:
        """意象大类分布柱状图（自然/社会/人文）"""
        dist = self._engine.major_category_distribution()
        sorted_data = sorted(dist.items(), key=lambda x: x[1], reverse=True)
        colors = ["#3498db", "#2ecc71", "#e67e22"]
        return {
            "title": {"text": "意象大类分布", "left": "center"},
            "tooltip": {"trigger": "axis"},
            "xAxis": {"type": "category", "data": [x[0] for x in sorted_data]},
            "yAxis": {"type": "value"},
            "series": [{
                "name": "数量", "type": "bar",
                "data": [x[1] for x in sorted_data],
                "itemStyle": {"color": {
                    "type": "linear", "x": 0, "y": 0, "x2": 1, "y2": 0,
                    "colorStops": [
                        {"offset": 0, "color": colors[0]},
                        {"offset": 1, "color": colors[1]},
                    ]
                }},
            }],
        }

    def build_emotion_bar(self) -> Dict[str, Any]:
        """情感类别分布柱状图"""
        dist = self._engine.emotion_distribution()
        sorted_data = sorted(dist.items(), key=lambda x: x[1], reverse=True)
        return {
            "title": {"text": "情感类别分布", "left": "center"},
            "tooltip": {"trigger": "axis"},
            "xAxis": {
                "type": "category",
                "data": [x[0] for x in sorted_data],
                "axisLabel": {"rotate": 20},
            },
            "yAxis": {"type": "value"},
            "series": [{
                "name": "频次", "type": "bar",
                "data": [x[1] for x in sorted_data],
                "itemStyle": {
                    "color": {
                        "type": "linear", "x": 0, "y": 0, "x2": 0, "y2": 1,
                        "colorStops": [
                            {"offset": 0, "color": "#e74c3c"},
                            {"offset": 0.5, "color": "#e67e22"},
                            {"offset": 1, "color": "#f1c40f"},
                        ]
                    }
                },
            }],
        }

    def build_author_bar(self, n: int = 15) -> Dict[str, Any]:
        """诗人意象使用量柱状图"""
        data = self._engine.top_authors_by_imagery(n)
        return {
            "title": {"text": f"诗人意象使用量 Top{n}", "left": "center"},
            "tooltip": {"trigger": "axis"},
            "xAxis": {
                "type": "category",
                "data": [x[0] for x in data],
                "axisLabel": {"rotate": 30},
            },
            "yAxis": {"type": "value"},
            "series": [{
                "name": "意象数", "type": "bar",
                "data": [x[1] for x in data],
                "itemStyle": {"color": "#2ecc71"},
            }],
        }

    # ─── 饼图 ───

    def build_category_pie(self) -> Dict[str, Any]:
        """分类域饼图"""
        dist = self._engine.category_distribution()
        sorted_data = sorted(dist.items(), key=lambda x: x[1], reverse=True)[:8]
        return {
            "title": {"text": "意象分类域占比", "left": "center"},
            "tooltip": {"trigger": "item", "formatter": "{b}: {c} ({d}%)"},
            "series": [{
                "type": "pie",
                "radius": ["30%", "65%"],
                "center": ["50%", "55%"],
                "data": [{"name": k, "value": v} for k, v in sorted_data],
                "label": {"formatter": "{b}\n{d}%"},
                "emphasis": {
                    "itemStyle": {"shadowBlur": 10, "shadowOffsetX": 0, "shadowColor": "rgba(0,0,0,0.5)"},
                },
            }],
        }

    def build_emotion_pie(self) -> Dict[str, Any]:
        """情感极性饼图"""
        dist = self._engine.emotion_polarity_distribution()
        polarity_colors = {"+": "#2ecc71", "-": "#e74c3c", "0": "#95a5a6"}
        data = []
        for k, v in dist.items():
            label = {"+": "正面", "-": "负面", "0": "中性"}.get(k, k)
            data.append({"name": f"{label}({k})", "value": v,
                         "itemStyle": {"color": polarity_colors.get(k, "#999")}})
        return {
            "title": {"text": "情感极性分布", "left": "center"},
            "tooltip": {"trigger": "item"},
            "series": [{
                "type": "pie",
                "radius": "65%",
                "data": data,
                "label": {"formatter": "{b}: {d}%"},
            }],
        }

    def build_perception_pie(self) -> Dict[str, Any]:
        """感知通道饼图"""
        dist = self._engine.perception_channel_distribution()
        sorted_data = sorted(dist.items(), key=lambda x: x[1], reverse=True)
        return {
            "title": {"text": "感知通道分布", "left": "center"},
            "tooltip": {"trigger": "item"},
            "series": [{
                "type": "pie",
                "radius": ["30%", "60%"],
                "data": [{"name": k, "value": v} for k, v in sorted_data[:10]],
                "roseType": "area",
            }],
        }

    # ─── 散点图 ───

    def build_author_imagery_scatter(self) -> Dict[str, Any]:
        """诗人-意象使用散点图（意象总量 vs 去重意象数）"""
        stats = self._engine.author_statistics(30)
        data = [(s["total_imagery_uses"], s["unique_imagery"], s["author"]) for s in stats if s["total_imagery_uses"] > 5]
        return {
            "title": {"text": "诗人意象使用分布", "left": "center"},
            "tooltip": {
                "trigger": "item",
                "formatter": "{c} (总量:{a}, 去重:{b})",
            },
            "xAxis": {"name": "意象总使用量", "nameLocation": "center", "nameGap": 30},
            "yAxis": {"name": "去重意象数"},
            "series": [{
                "type": "scatter",
                "data": [{"value": [a, b], "name": name} for a, b, name in data],
                "symbolSize": lambda val: min(max(val[0] / 5, 8), 40),
                "itemStyle": {"color": "#3498db"},
            }],
        }

    # ─── 汇总数据 ───

    def build_all_charts(self) -> Dict[str, Any]:
        """构建全部图表数据"""
        return {
            "top_imagery_bar": self.build_top_imagery_bar(),
            "category_bar": self.build_category_bar(),
            "major_category_bar": self.build_major_category_bar(),
            "emotion_bar": self.build_emotion_bar(),
            "author_bar": self.build_author_bar(),
            "category_pie": self.build_category_pie(),
            "emotion_pie": self.build_emotion_pie(),
            "perception_pie": self.build_perception_pie(),
            "author_scatter": self.build_author_imagery_scatter(),
        }

    # ─── 扩展图表 ───

    def build_heatmap_data(self) -> Dict[str, Any]:
        """构建情感-分类域热力图数据"""
        from .stats_engine import StatsEngine
        cross = self._engine.cross_analysis_emotion_category()
        categories = sorted(set(c for v in cross.values() for c in v.keys()))
        emotions = sorted(cross.keys())
        data = []
        for ei, emo in enumerate(emotions):
            for ci, cat in enumerate(categories):
                val = cross.get(emo, {}).get(cat, 0)
                if val > 0:
                    data.append([ci, ei, val])
        return {
            "title": {"text": "情感-分类域 热力图", "left": "center"},
            "tooltip": {},
            "xAxis": {"type": "category", "data": categories, "axisLabel": {"rotate": 30}},
            "yAxis": {"type": "category", "data": emotions},
            "visualMap": {"min": 0, "calculable": True, "orient": "horizontal", "left": "center", "bottom": 0},
            "series": [{"type": "heatmap", "data": data, "label": {"show": False}}],
        }

    def build_treemap_data(self) -> Dict[str, Any]:
        """构建分类域树图数据"""
        from .stats_engine import StatsEngine
        from .config import FULL_CATEGORY_HIERARCHY
        dist = self._engine.sub_category_distribution()
        tree_data = []
        for major_code, major_info in FULL_CATEGORY_HIERARCHY.items():
            children = []
            for sub_code, sub_name in major_info["subs"].items():
                count = dist.get(sub_code, 0)
                if count > 0:
                    children.append({"name": sub_name, "value": count})
            if children:
                tree_data.append({"name": major_info["name"], "children": children})
        return {
            "title": {"text": "意象分类层级图", "left": "center"},
            "tooltip": {},
            "series": [{"type": "treemap", "data": tree_data, "width": "90%", "height": "80%"}],
        }

    def build_sankey_data(self) -> Dict[str, Any]:
        """构建情感-大类流向图数据"""
        from .stats_engine import StatsEngine
        cross = self._engine.cross_analysis_emotion_category()
        major_map = {}
        for item in self._engine._data:
            c = item.get("category", "")
            mc = item.get("major_code", "")
            if c and mc:
                major_map[c] = mc
        nodes_set = set()
        links = []
        for emo, cats in cross.items():
            nodes_set.add(emo)
            for cat, cnt in cats.items():
                nodes_set.add(cat)
                links.append({"source": emo, "target": cat, "value": cnt})
        nodes = [{"name": n} for n in sorted(nodes_set)]
        return {"title": {"text": "情感-分类域 流向图", "left": "center"},
                "series": [{"type": "sankey", "layout": "none", "data": nodes, "links": links}]}

    def build_radar_data(self) -> Dict[str, Any]:
        """构建维度雷达图"""
        engine = self._engine
        dims = ["自然意象", "社会意象", "人文意象"]
        major_dist = engine.major_category_distribution()
        max_val = max(major_dist.values()) if major_dist else 1
        values = [round(major_dist.get(d, 0) / max_val * 100, 1) for d in dims]
        return {
            "title": {"text": "意象大类雷达图", "left": "center"},
            "radar": {"indicator": [{"name": d, "max": 100} for d in dims]},
            "series": [{"type": "radar", "data": [{"value": values, "name": "意象分布"}]}],
        }

    def build_extended_charts(self) -> Dict[str, Any]:
        """构建扩展图表集"""
        return {
            "heatmap": self.build_heatmap_data(),
            "treemap": self.build_treemap_data(),
            "sankey": self.build_sankey_data(),
            "radar": self.build_radar_data(),
        }
