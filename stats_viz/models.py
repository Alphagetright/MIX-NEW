# -*- coding: utf-8 -*-
"""
数据模型模块
============
定义诗歌意象数据的核心模型类。
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional
import time
import uuid


@dataclass
class PoemLine:
    """诗行模型"""
    line_id: str = ""
    text: str = ""
    annotation: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AnalysisUnit:
    """分析单元模型 — 包含 25 个标注字段"""
    unit_id: str = ""
    line_id: str = ""
    text: str = ""
    position: int = 0
    pos_tag: str = ""            # 词性
    component_type: str = ""     # 成分类型
    is_imagery: bool = False     # 是否意象
    major_code: str = ""         # 大类编码
    sub_code: str = ""           # 子类编码
    perception_channel: str = "" # 感知通道
    material_type: str = ""      # 素材类型
    internal_structure: str = "" # 内部结构
    reference_source: str = ""   # 指涉来源
    expressive_function: str = "" # 表现功能
    cultural_circulation: str = "" # 文化流通性
    cross_cultural: str = ""     # 跨文化性
    cognitive_intensity: str = "" # 认知强度
    core_imagery: str = ""       # 核心意象
    structural_group: str = ""   # 结构功能组
    emotion_polarity: str = ""   # 情感极性
    emotion_category: str = ""   # 情感类别
    emotion_confidence: str = "" # 情感置信度

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Poem:
    """诗歌模型"""
    poem_id: str = ""
    title: str = "未知诗歌"
    author: str = ""
    dynasty: str = ""
    genre: str = ""
    full_text: str = ""
    lines: List[PoemLine] = field(default_factory=list)
    analysis_units: List[AnalysisUnit] = field(default_factory=list)
    emotion_trajectory: List[Dict[str, Any]] = field(default_factory=list)
    imagery_relations: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def imagery_count(self) -> int:
        return sum(1 for u in self.analysis_units if u.is_imagery)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["imagery_count"] = self.imagery_count
        return d


@dataclass
class ImageryTraceItem:
    """意象溯源条目 — 扁平化用于前端展示和统计"""
    poem_id: str = ""
    title: str = ""
    author: str = ""
    genre: str = ""
    category: str = ""           # 分类域（中文名）
    imagery_text: str = ""       # 意象文本
    line_text: str = ""          # 所在诗句
    dimensions: str = ""         # 四层摘要
    emotion: str = ""            # 情感描述
    emotion_category: str = ""
    emotion_polarity: str = ""
    pos_tag: str = ""
    component_type: str = ""
    perception_channel: str = ""
    material_type: str = ""
    internal_structure: str = ""
    reference_source: str = ""
    expressive_function: str = ""
    cultural_circulation: str = ""
    cross_cultural: str = ""
    cognitive_intensity: str = ""
    core_imagery: str = ""
    structural_group: str = ""
    major_code: str = ""
    sub_code: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class StatsSummary:
    """统计分析摘要"""
    total_poems: int = 0
    total_imagery_items: int = 0
    total_unique_imagery: int = 0
    total_authors: int = 0
    total_categories: int = 0
    top_imagery: List[tuple] = field(default_factory=list)
    category_distribution: Dict[str, int] = field(default_factory=dict)
    emotion_distribution: Dict[str, int] = field(default_factory=dict)
    perception_distribution: Dict[str, int] = field(default_factory=dict)
    genre_distribution: Dict[str, int] = field(default_factory=dict)
    generated_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["top_imagery"] = [{"text": t, "count": c} for t, c in self.top_imagery]
        return d


@dataclass
class ExportRecord:
    """导出记录"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    format: str = ""
    file_path: str = ""
    file_size: int = 0
    rows_exported: int = 0
    columns_exported: int = 0
    created_at: float = field(default_factory=time.time)
    duration: float = 0.0
    status: str = "success"
    error_message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["created_formatted"] = datetime.fromtimestamp(self.created_at).strftime("%Y-%m-%d %H:%M:%S")
        return d


@dataclass
class ChartData:
    """图表数据结构"""
    chart_type: str = ""         # bar/line/pie/scatter
    title: str = ""
    categories: List[str] = field(default_factory=list)
    values: List[float] = field(default_factory=list)
    colors: List[str] = field(default_factory=list)
    labels: Dict[str, str] = field(default_factory=dict)

    def to_echarts_option(self) -> Dict[str, Any]:
        """转换为 ECharts 配置"""
        return {
            "title": {"text": self.title, "left": "center"},
            "xAxis": {"type": "category", "data": self.categories},
            "yAxis": {"type": "value"},
            "series": [{"data": self.values, "type": self.chart_type}],
        }

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ─── 扩展模型 ───

@dataclass
class CrossAnalysisResult:
    """交叉分析结果"""
    dimension1: str = ""
    dimension2: str = ""
    data: Dict[str, Dict[str, int]] = field(default_factory=dict)
    row_totals: Dict[str, int] = field(default_factory=dict)
    col_totals: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {"dimension1": self.dimension1, "dimension2": self.dimension2,
                "data": self.data, "row_totals": self.row_totals, "col_totals": self.col_totals}


@dataclass
class CoOccurrencePair:
    """意象共现对"""
    image_a: str = ""; image_b: str = ""
    co_count: int = 0; poem_ids: List[str] = field(default_factory=list)
    strength_pct: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {"image_a": self.image_a, "image_b": self.image_b,
                "co_count": self.co_count, "strength_pct": self.strength_pct}


@dataclass
class PoetProfile:
    """诗人意象画像"""
    name: str = ""; total_poems: int = 0; total_imagery_uses: int = 0
    unique_imagery: int = 0; avg_imagery_per_poem: float = 0.0
    top_imagery: List[Dict[str, Any]] = field(default_factory=list)
    preferred_categories: Dict[str, int] = field(default_factory=dict)
    dominant_emotions: List[tuple] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ClusterResult:
    """聚类结果"""
    cluster_id: int = 0; size: int = 0; centroid: str = ""
    members: List[str] = field(default_factory=list); cohesion_score: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DashboardConfig:
    """仪表盘配置"""
    title: str = "诗歌意象统计仪表盘"
    charts: Dict[str, Any] = field(default_factory=dict)
    layout: Dict[str, List[str]] = field(default_factory=dict)
    theme: str = "default"; auto_refresh: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


@dataclass
class AnalysisReport:
    """综合分析报告"""
    report_id: str = field(default_factory=lambda: str(__import__('uuid').uuid4())[:8])
    title: str = "诗歌意象分析报告"; created_at: str = ""
    stats_summary: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
