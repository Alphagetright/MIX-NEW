# -*- coding: utf-8 -*-
"""
可视化服务
==========
为前端 ECharts 图表提供数据准备、主题配置、交互行为定义等后端服务。
"""

import json
from typing import Any, Dict, List, Optional, Tuple

from .stats_engine import StatsEngine
from .config import CHART_DEFAULT_COLOR, CHART_CATEGORY_COLOR, TOP_IMAGES_N
from .utils import frequency_count


class VisualizationService:
    """
    可视化服务

    提供完整的图表数据准备和 ECharts 配置生成服务。

    Usage:
        engine = StatsEngine(); engine.load_data()
        viz = VisualizationService(engine)
        option = viz.get_top_imagery_chart(top_n=30)
    """

    def __init__(self, engine: StatsEngine):
        self._engine = engine

    # ─── 配色方案 ───

    COLOR_SCHEMES = {
        "default": ["#3498db", "#2ecc71", "#e67e22", "#9b59b6", "#1abc9c", "#e74c3c", "#f39c12", "#2980b9"],
        "warm": ["#e74c3c", "#e67e22", "#f39c12", "#f1c40f", "#fd79a8", "#d63031", "#fab1a0", "#e17055"],
        "cool": ["#3498db", "#2980b9", "#1abc9c", "#16a085", "#00cec9", "#6c5ce7", "#a29bfe", "#81ecec"],
        "nature": ["#27ae60", "#2ecc71", "#1abc9c", "#16a085", "#00b894", "#55efc4", "#00cec9", "#81ecec"],
        "classical": ["#8B4513", "#D2691E", "#B8860B", "#556B2F", "#800020", "#4A3728", "#6B3A2E", "#2F4F4F"],
    }

    def set_color_scheme(self, scheme_name: str = "default") -> List[str]:
        """获取配色方案"""
        return self.COLOR_SCHEMES.get(scheme_name, self.COLOR_SCHEMES["default"])

    # ─── 通用 ECharts 基础配置 ───

    def _base_option(self, title: str, chart_type: str = "bar") -> Dict[str, Any]:
        return {
            "title": {"text": title, "left": "center", "textStyle": {"color": "#2c3e50", "fontSize": 16}},
            "tooltip": {"trigger": "axis" if chart_type != "pie" else "item"},
            "animation": True,
            "animationDuration": 800,
            "animationEasing": "cubicOut",
        }

    # ─── 柱状图 ───

    def build_bar_chart(self, data: List[Tuple[str, int]], title: str = "",
                        color: str = None, horizontal: bool = False,
                        show_data_zoom: bool = False) -> Dict[str, Any]:
        """通用柱状图构建"""
        option = self._base_option(title or "柱状图", "bar")
        if horizontal:
            option["yAxis"] = {"type": "category", "data": [x[0] for x in data], "inverse": True}
            option["xAxis"] = {"type": "value"}
        else:
            option["xAxis"] = {"type": "category", "data": [x[0] for x in data],
                               "axisLabel": {"interval": 0, "rotate": 30 if len(data) > 8 else 0}}
            option["yAxis"] = {"type": "value"}

        if show_data_zoom:
            option["dataZoom"] = [{"type": "slider", "show": True, "start": 0, "end": 50, "bottom": 0}]
            option["grid"] = {"top": "10%", "left": "5%", "right": "5%", "bottom": "20%"}

        option["series"] = [{
            "type": "bar",
            "data": [x[1] for x in data],
            "itemStyle": {"color": color or CHART_DEFAULT_COLOR,
                           "borderRadius": [4, 4, 0, 0]},
            "barWidth": "60%",
        }]
        return option

    def get_core_imagery_chart(self, n: int = TOP_IMAGES_N) -> Dict[str, Any]:
        """核心意象 Top-N 柱状图"""
        data = self._engine.top_imagery(n)
        return self.build_bar_chart(data, f"核心意象 Top{n}", color=CHART_DEFAULT_COLOR, show_data_zoom=True)

    def get_category_chart(self) -> Dict[str, Any]:
        """分类域分布柱状图"""
        dist = self._engine.category_distribution()
        data = sorted(dist.items(), key=lambda x: x[1], reverse=True)
        return self.build_bar_chart(data, "意象分类域分布", color=CHART_CATEGORY_COLOR)

    def get_emotion_chart(self) -> Dict[str, Any]:
        """情感分布柱状图"""
        dist = self._engine.emotion_distribution()
        data = sorted(dist.items(), key=lambda x: x[1], reverse=True)
        return self.build_bar_chart(data, "情感类别分布", color="#e74c3c")

    def get_author_chart(self, n: int = 15) -> Dict[str, Any]:
        """诗人意象量柱状图（横向）"""
        data = self._engine.top_authors_by_imagery(n)
        return self.build_bar_chart(data, "诗人意象使用量", color="#2ecc71", horizontal=True)

    def get_genre_chart(self) -> Dict[str, Any]:
        """体裁分布柱状图"""
        dist = self._engine.genre_distribution()
        data = sorted(dist.items(), key=lambda x: x[1], reverse=True)
        return self.build_bar_chart(data, "诗歌体裁分布", color="#9b59b6")

    def get_perception_chart(self) -> Dict[str, Any]:
        """感知通道分布柱状图"""
        dist = self._engine.perception_channel_distribution()
        data = sorted(dist.items(), key=lambda x: x[1], reverse=True)
        return self.build_bar_chart(data, "感知通道分布", color="#f39c12")

    # ─── 饼图 ───

    def build_pie_chart(self, data: List[Tuple[str, int]], title: str = "",
                        rose_type: bool = False, colors: List[str] = None) -> Dict[str, Any]:
        """通用饼图构建"""
        option = self._base_option(title or "饼图", "pie")
        option["tooltip"] = {"trigger": "item", "formatter": "{b}: {c} ({d}%)"}

        series_config = {
            "type": "pie",
            "radius": ["30%", "65%"] if rose_type else "65%",
            "center": ["50%", "55%"],
            "data": [{"name": k, "value": v} for k, v in data],
            "label": {"formatter": "{b}\n{d}%"},
        }
        if colors:
            series_config["itemStyle"] = {"color": {
                "type": "linear", "x": 0, "y": 0, "x2": 0, "y2": 1,
                "colorStops": [{"offset": i / (len(colors) - 1), "color": c} for i, c in enumerate(colors)],
            }}
        if rose_type:
            series_config["roseType"] = "area"

        option["series"] = [series_config]
        return option

    def get_major_category_pie(self) -> Dict[str, Any]:
        """大类分布饼图"""
        dist = self._engine.major_category_distribution()
        data = sorted(dist.items(), key=lambda x: x[1], reverse=True)
        return self.build_pie_chart(data, "意象大类占比", colors=["#3498db", "#2ecc71", "#e67e22"])

    def get_emotion_polarity_pie(self) -> Dict[str, Any]:
        """情感极性饼图"""
        dist = self._engine.emotion_polarity_distribution()
        polarity_labels = {"+": "正面", "-": "负面", "0": "中性"}
        data = [(polarity_labels.get(k, k), v) for k, v in dist.items()]
        return self.build_pie_chart(data, "情感极性分布")

    def get_category_pie(self) -> Dict[str, Any]:
        """分类域占比饼图"""
        dist = self._engine.category_distribution()
        data = sorted(dist.items(), key=lambda x: x[1], reverse=True)[:10]
        return self.build_pie_chart(data, "分类域占比", rose_type=True)

    # ─── 多图表配置 ───

    def get_dashboard_config(self) -> Dict[str, Any]:
        """
        获取仪表盘完整图表配置

        返回:
            Dict: 包含多个图表 option 的完整仪表盘配置
        """
        return {
            "charts": {
                "core_imagery": self.get_core_imagery_chart(50),
                "category": self.get_category_chart(),
                "emotion": self.get_emotion_chart(),
                "author": self.get_author_chart(15),
                "genre": self.get_genre_chart(),
                "perception": self.get_perception_chart(),
                "major_pie": self.get_major_category_pie(),
                "polarity_pie": self.get_emotion_polarity_pie(),
            },
            "layout": {
                "row1": ["core_imagery", "category"],
                "row2": ["emotion", "author"],
                "row3": ["genre", "perception"],
                "row4": ["major_pie", "polarity_pie"],
            },
            "stats_summary": self._engine.summary_report(),
        }

    def export_dashboard_json(self, file_path: str = "") -> str:
        """导出仪表盘配置为 JSON 文件"""
        config = self.get_dashboard_config()
        if not file_path:
            from datetime import datetime
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_path = f"dashboard_config_{ts}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        return file_path

    def get_theme_config(self, theme: str = "default") -> Dict[str, Any]:
        """获取 ECharts 主题配置"""
        themes = {
            "default": {"primary": "#3498db", "bg": "#ffffff", "text": "#333333"},
            "dark": {"primary": "#2980b9", "bg": "#1a1a2e", "text": "#c8ccd4"},
            "classical": {"primary": "#8B4513", "bg": "#FFF8DC", "text": "#4A3728"},
        }
        return themes.get(theme, themes["default"])

    def get_interaction_config(self) -> Dict[str, Any]:
        """获取图表交互行为配置"""
        return {
            "toolbox": {"feature": {"saveAsImage": {"title": "保存"}, "dataView": {"title": "数据", "readOnly": True},
                                     "restore": {"title": "还原"}, "magicType": {"type": ["bar", "line"]}}},
            "brush": {"toolbox": ["rect", "polygon", "clear"]},
            "tooltip": {"trigger": "axis", "axisPointer": {"type": "cross"}},
        }

    def generate_html_page(self, charts: List[str] = None, output_path: str = "") -> str:
        """生成包含 ECharts 图表的完整 HTML 页面"""
        if charts is None:
            charts = ["core_imagery", "category", "emotion", "author"]
        configs = self.get_dashboard_config()["charts"]
        chart_divs = []
        for i, name in enumerate(charts):
            if name in configs:
                opt_json = json.dumps(configs[name], ensure_ascii=False)
                chart_divs.append(f"""<div id=\"chart_{i}\" style=\"width:100%;height:450px;margin-bottom:20px;\"></div>
<script>echarts.init(document.getElementById('chart_{i}')).setOption({opt_json});</script>""")

        html = f"""<!DOCTYPE html><html lang=\"zh-CN\"><head><meta charset=\"utf-8\">
<title>诗歌意象统计仪表盘</title>
<script src=\"https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js\"></script>
<style>body{{font-family:Arial,'Microsoft YaHei',sans-serif;margin:20px;background:#f4f7f6}}
h1{{color:#2c3e50;text-align:center}}.grid{{display:grid;grid-template-columns:1fr 1fr;gap:16px}}</style>
</head><body><h1>诗歌意象多维统计仪表盘</h1><div class=\"grid\">
{''.join(f'<div class=\"card\">{div}</div>' for div in chart_divs)}
</div></body></html>"""
        if output_path:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(html)
        return html
