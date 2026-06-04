# -*- coding: utf-8 -*-
"""
古典诗词音韵格律分析引擎 — 核心数据模型
"""
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple


# ─── 平仄标注 ───


@dataclass
class PingzeAnnotation:
    """单字平仄标注"""
    char: str = ""                      # 原字
    position: int = 0                   # 在句中的位置 (1-based)
    line_number: int = 0                # 所属句号 (1-based)
    tone: str = ""                      # "平" | "仄" | "仄(入)" | "未知"
    yunbu: str = ""                     # 所属韵部名称
    yunbu_category: str = ""            # 韵部声调类别（平/上/去/入）
    is_duoyin: bool = False             # 是否多音字
    alternatives: List[str] = field(default_factory=list)  # 多音字其他可能声调
    confidence: float = 1.0             # 置信度 0-1

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @property
    def tone_symbol(self) -> str:
        return {"平": "○", "仄": "●", "仄(入)": "◇", "未知": "◆"}.get(self.tone, "?")


@dataclass
class MultiToneChar:
    """多音字检测结果"""
    char: str = ""
    position: int = 0
    line_number: int = 0
    possible_tones: List[str] = field(default_factory=list)
    possible_yunbus: List[str] = field(default_factory=list)


@dataclass
class ToneDistribution:
    """声调分布统计"""
    total_chars: int = 0
    ping_count: int = 0
    ze_count: int = 0
    rusheng_count: int = 0
    unknown_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "总字数": self.total_chars,
            "平声": self.ping_count,
            "仄声": self.ze_count,
            "入声": self.rusheng_count,
            "未知": self.unknown_count,
            "平声占比": round(self.ping_count / max(1, self.total_chars) * 100, 1),
            "仄声占比": round(self.ze_count / max(1, self.total_chars) * 100, 1),
            "入声占比": round(self.rusheng_count / max(1, self.total_chars) * 100, 1),
        }


# ─── 格律模板 ───


@dataclass
class MeterTemplate:
    """格律模板"""
    form: str = ""                      # 体裁：五绝/七绝/五律/七律
    style: str = ""                     # 起式：仄起/平起
    rhyme_start: str = ""               # 首句：入韵/不入韵
    line_count: int = 4                 # 总句数
    chars_per_line: int = 5             # 每句字数
    line_templates: List[str] = field(default_factory=list)  # 每句平仄模板
    flexible_positions: List[List[int]] = field(default_factory=list)  # 每句灵活位置
    couplet_indices: List[int] = field(default_factory=list)  # 对仗联的起始句号

    def to_dict(self) -> Dict[str, Any]:
        return {
            "form": self.form,
            "style": self.style,
            "rhyme_start": self.rhyme_start,
            "line_count": self.line_count,
            "chars_per_line": self.chars_per_line,
            "line_templates": self.line_templates,
            "flexible_positions": [[p for p in ps] for ps in self.flexible_positions],
            "couplet_indices": self.couplet_indices,
        }


# ─── 格律检查 ───


@dataclass
class MeterViolation:
    """格律违规记录"""
    line_number: int = 0
    char_position: int = 0
    char: str = ""
    expected: str = ""                  # 期望平仄
    actual: str = ""                    # 实际平仄
    is_flexible: bool = False           # 是否在灵活位置
    severity: str = ""                  # "严重" | "轻微" | "可忽略"
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MeterReport:
    """格律合规报告"""
    poem_title: str = ""
    form: str = ""                      # 检测/指定的体裁
    style: str = ""                     # 起式
    total_lines: int = 0
    total_chars: int = 0
    compliant_lines: int = 0
    violations: List[MeterViolation] = field(default_factory=list)
    guping_lines: List[int] = field(default_factory=list)      # 孤平所在句
    sanpingdiao_lines: List[int] = field(default_factory=list)  # 三平调所在句
    sanzewei_lines: List[int] = field(default_factory=list)     # 三仄尾所在句
    compliance_rate: float = 0.0
    overall_judgment: str = ""          # "合律" / "基本合律" / "部分合律" / "不合律"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "诗歌": self.poem_title,
            "体裁": self.form,
            "起式": self.style,
            "总句数": self.total_lines,
            "总字数": self.total_chars,
            "合律句数": self.compliant_lines,
            "违规数": len(self.violations),
            "违规详情": [v.to_dict() for v in self.violations],
            "孤平": self.guping_lines,
            "三平调": self.sanpingdiao_lines,
            "三仄尾": self.sanzewei_lines,
            "合规率": round(self.compliance_rate, 1),
            "判定": self.overall_judgment,
        }


# ─── 韵脚分析 ───


@dataclass
class RhymeChar:
    """韵脚字"""
    char: str = ""
    line_number: int = 0                # 所在句号
    position: int = 0                   # 在句中的位置
    yunbu: str = ""                     # 所属韵部
    yunbu_category: str = ""            # 韵部声调类别
    is_rhyme_required: bool = True      # 该位置是否必须押韵

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RhymeReport:
    """韵脚分析报告"""
    poem_title: str = ""
    form: str = ""
    rhyme_chars: List[RhymeChar] = field(default_factory=list)
    rhyme_yunbu: str = ""               # 主押韵部
    yunbu_description: str = ""         # 韵部可读描述
    is_compliant: bool = True           # 是否合韵
    neighboring_rhyme: bool = False     # 是否邻韵通押
    violations: List[str] = field(default_factory=list)   # 出韵详情
    rhyme_density: float = 0.0         # 韵脚密度
    unique_rhyme_count: int = 0        # 去重韵脚字数

    def to_dict(self) -> Dict[str, Any]:
        return {
            "诗歌": self.poem_title,
            "体裁": self.form,
            "韵脚字": [r.char for r in self.rhyme_chars],
            "主押韵部": self.rhyme_yunbu,
            "韵部描述": self.yunbu_description,
            "合韵": self.is_compliant,
            "邻韵通押": self.neighboring_rhyme,
            "出韵详情": self.violations,
            "韵脚密度": round(self.rhyme_density, 2),
            "去重韵脚数": self.unique_rhyme_count,
        }


# ─── 对仗检测 ───


@dataclass
class CharAlignment:
    """对仗逐字对应"""
    position: int = 0
    char1: str = ""
    char2: str = ""
    pos1: str = ""                      # 字1词性
    pos2: str = ""                      # 字2词性
    matched: bool = False               # 词性是否匹配

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CoupletAnalysis:
    """对仗联分析"""
    couplet_name: str = ""              # "首联"/"颔联"/"颈联"/"尾联"
    line1: str = ""                     # 出句
    line2: str = ""                     # 对句
    is_duizhang: bool = False
    duizhang_type: str = ""             # "工对"/"宽对"/"流水对"/"非对仗"
    char_alignments: List[CharAlignment] = field(default_factory=list)
    score: float = 0.0                  # 0-100
    highlights: List[str] = field(default_factory=list)   # 高亮匹配
    issues: List[str] = field(default_factory=list)        # 对仗问题

    def to_dict(self) -> Dict[str, Any]:
        return {
            "联名": self.couplet_name,
            "出句": self.line1,
            "对句": self.line2,
            "对仗": self.is_duizhang,
            "类型": self.duizhang_type,
            "逐字对应": [a.to_dict() for a in self.char_alignments],
            "评分": self.score,
            "亮点": self.highlights,
            "问题": self.issues,
        }


@dataclass
class DuizhangReport:
    """对仗检测报告"""
    poem_title: str = ""
    form: str = ""
    couplets: List[CoupletAnalysis] = field(default_factory=list)
    overall_score: float = 0.0
    best_couplet: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "诗歌": self.poem_title,
            "体裁": self.form,
            "各联分析": [c.to_dict() for c in self.couplets],
            "综合评分": self.overall_score,
            "最佳对仗": self.best_couplet,
        }


# ─── 综合扫描结果 ───


@dataclass
class ScansionResult:
    """全维度格律扫描结果"""
    poem_title: str = ""
    poem_author: str = ""
    form: str = ""
    total_lines: int = 0
    total_chars: int = 0
    pingze_annotations: List[List[PingzeAnnotation]] = field(default_factory=list)
    tone_distribution: ToneDistribution = field(default_factory=ToneDistribution)
    meter_report: Optional[MeterReport] = None
    rhyme_report: Optional[RhymeReport] = None
    duizhang_report: Optional[DuizhangReport] = None
    overall_score: float = 0.0
    summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "诗歌": self.poem_title,
            "作者": self.poem_author,
            "体裁": self.form,
            "总句数": self.total_lines,
            "总字数": self.total_chars,
            "声调分布": self.tone_distribution.to_dict(),
            "综合评分": round(self.overall_score, 1),
            "总结": self.summary,
        }
        if self.meter_report:
            d["格律检查"] = self.meter_report.to_dict()
        if self.rhyme_report:
            d["韵脚分析"] = self.rhyme_report.to_dict()
        if self.duizhang_report:
            d["对仗检测"] = self.duizhang_report.to_dict()
        return d


# ─── 相似度 ───


@dataclass
class SimilarityResult:
    """音韵相似度计算结果"""
    poem1_title: str = ""
    poem2_title: str = ""
    overall_score: float = 0.0          # 0-100
    yunbu_overlap: float = 0.0          # 韵部重叠度
    tone_similarity: float = 0.0        # 声调分布相似度
    density_similarity: float = 0.0     # 韵脚密度相似度
    position_similarity: float = 0.0    # 韵脚位置相似度
    meter_similarity: float = 0.0       # 格律模板相似度

    def to_dict(self) -> Dict[str, Any]:
        return {
            "诗歌1": self.poem1_title,
            "诗歌2": self.poem2_title,
            "综合分": round(self.overall_score, 1),
            "韵部重叠": round(self.yunbu_overlap, 1),
            "声调相似": round(self.tone_similarity, 1),
            "密度相似": round(self.density_similarity, 1),
            "位置相似": round(self.position_similarity, 1),
            "格律相似": round(self.meter_similarity, 1),
        }


@dataclass
class AuthorRhymeProfile:
    """诗人用韵偏好画像"""
    author: str = ""
    poem_count: int = 0
    top_yunbus: List[Tuple[str, int]] = field(default_factory=list)
    ping_ratio: float = 0.0
    ze_ratio: float = 0.0
    rusheng_ratio: float = 0.0
    favorite_forms: List[Tuple[str, int]] = field(default_factory=list)
    rhyme_density_avg: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "诗人": self.author,
            "诗歌数": self.poem_count,
            "常用韵部": [{"韵部": y, "次数": c} for y, c in self.top_yunbus],
            "平声比例": round(self.ping_ratio, 1),
            "仄声比例": round(self.ze_ratio, 1),
            "入声比例": round(self.rusheng_ratio, 1),
            "常用体裁": [{"体裁": f, "次数": c} for f, c in self.favorite_forms],
            "平均韵脚密度": round(self.rhyme_density_avg, 2),
        }


# ─── 批处理 ───


@dataclass
class BatchResult:
    """批量分析结果"""
    total_poems: int = 0
    processed: int = 0
    succeeded: int = 0
    failed: int = 0
    results: List[ScansionResult] = field(default_factory=list)
    errors: List[Dict[str, str]] = field(default_factory=list)
    duration_seconds: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "总诗歌数": self.total_poems,
            "已处理": self.processed,
            "成功": self.succeeded,
            "失败": self.failed,
            "成功率": round(self.succeeded / max(1, self.processed) * 100, 1),
            "耗时秒": self.duration_seconds,
        }

    @property
    def success_rate(self) -> float:
        return round(self.succeeded / max(1, self.processed) * 100, 1)


# ─── 诗歌元信息 ───


@dataclass
class PoemMetadata:
    """诗歌元信息（从JSON数据中提取）"""
    poem_id: str = ""
    title: str = ""
    author: str = ""
    dynasty: str = "唐"
    genre: str = ""
    text: str = ""                      # 全文
    lines: List[str] = field(default_factory=list)  # 诗句列表
    line_count: int = 0
    char_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "编号": self.poem_id,
            "标题": self.title,
            "作者": self.author,
            "朝代": self.dynasty,
            "体裁": self.genre,
            "句数": self.line_count,
            "字数": self.char_count,
        }

    @property
    def display_name(self) -> str:
        return f"《{self.title}》{self.author}"
