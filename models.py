# -*- coding: utf-8 -*-
"""
数据模型层 — 诗歌、意象、分析单元的数据类定义
"""
import json
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field, asdict


@dataclass
class PoemLine:
    """诗行"""
    诗行编号: str = ""
    原文: str = ""
    注释: str = ""

    def to_dict(self):
        return asdict(self)


@dataclass
class AnalysisUnit:
    """分析单元（意象标注单元）"""
    单元编号: str = ""
    诗行编号: str = ""
    文本: str = ""
    行内位置: str = ""
    词性: str = ""
    成分类型: str = ""
    是否意象: str = "0"
    大类编码: str = ""
    子类编码: str = ""
    感知通道: str = ""
    素材类型: str = ""
    内部结构: str = ""
    指涉来源: str = ""
    表现功能: str = ""
    文化流通性: str = ""
    跨文化性: str = ""
    认知强度: str = ""
    核心意象: str = ""
    结构功能组: str = ""
    情感极性: str = ""
    情感类别: str = ""
    情感置信度: str = ""

    def to_dict(self):
        return asdict(self)

    @property
    def is_image(self) -> bool:
        return self.是否意象 == "1"


@dataclass
class EmotionTrajectory:
    """情感轨迹"""
    诗行编号: str = ""
    诗行原文: str = ""
    平均情感极性: str = ""
    主导情感: str = ""
    情感波动值: str = ""

    def to_dict(self):
        return asdict(self)


@dataclass
class ImageRelation:
    """意象关系"""
    关系编号: str = ""
    来源单元编号: str = ""
    来源文本: str = ""
    目标单元编号: str = ""
    目标文本: str = ""
    关系类型: str = ""
    关系强度: str = ""

    def to_dict(self):
        return asdict(self)


@dataclass
class Poem:
    """诗歌完整数据模型"""
    诗歌编号: str = ""
    标题: str = ""
    作者: str = ""
    朝代: str = "唐"
    分类标签: str = ""
    体裁: str = ""
    原文: str = ""
    诗行: List[PoemLine] = field(default_factory=list)
    分析单元: List[AnalysisUnit] = field(default_factory=list)
    情感轨迹: List[EmotionTrajectory] = field(default_factory=list)
    意象关系: List[ImageRelation] = field(default_factory=list)

    def to_dict(self):
        return {
            "诗歌编号": self.诗歌编号,
            "标题": self.标题,
            "作者": self.作者,
            "分类标签": self.分类标签,
            "体裁": self.体裁,
            "原文": self.原文,
            "诗行": [l.to_dict() for l in self.诗行],
            "分析单元": [u.to_dict() for u in self.分析单元],
            "情感轨迹": [t.to_dict() for t in self.情感轨迹],
            "意象关系": [r.to_dict() for r in self.意象关系],
        }

    @property
    def image_units(self) -> List[AnalysisUnit]:
        return [u for u in self.分析单元 if u.is_image]

    @property
    def image_count(self) -> int:
        return len(self.image_units)

    @property
    def summary(self) -> str:
        return f"《{self.标题}》{self.作者} ({self.诗歌编号}) — {self.image_count}个意象"

    @classmethod
    def from_dict(cls, data: dict) -> "Poem":
        lines = [PoemLine(**l) for l in data.get("诗行", []) if isinstance(l, dict)]
        units = [AnalysisUnit(**u) for u in data.get("分析单元", []) if isinstance(u, dict)]
        trajs = [EmotionTrajectory(**t) for t in data.get("情感轨迹", []) if isinstance(t, dict)]
        rels = [ImageRelation(**r) for r in data.get("意象关系", []) if isinstance(r, dict)]
        return cls(
            诗歌编号=data.get("诗歌编号", ""),
            标题=data.get("标题", ""),
            作者=data.get("作者", ""),
            分类标签=data.get("分类标签", ""),
            体裁=data.get("体裁", ""),
            原文=data.get("原文", ""),
            诗行=lines, 分析单元=units,
            情感轨迹=trajs, 意象关系=rels,
        )


@dataclass
class TracebackItem:
    """溯源表条目（前台展示用）"""
    poem_id: str = ""
    title: str = ""
    author: str = ""
    genre: str = ""
    cat: str = ""
    txt: str = ""
    text: str = ""
    dimensions: str = ""
    emotion: str = ""
    emo_cat: str = ""
    line: str = ""
    id: str = ""
    词性: str = ""
    成分类型: str = ""
    感知通道: str = ""
    素材类型: str = ""
    内部结构: str = ""
    指涉来源: str = ""
    表现功能: str = ""
    文化流通性: str = ""
    跨文化性: str = ""
    认知强度: str = ""
    核心意象: str = ""
    结构功能组: str = ""
    情感极性: str = ""
    情感类别: str = ""
    情感置信度: str = ""
    大类编码: str = ""
    子类编码: str = ""

    def to_dict(self):
        return asdict(self)


@dataclass
class AnalysisResult:
    """解析结果"""
    item: Dict[str, Any] = field(default_factory=dict)
    messages: List[Dict] = field(default_factory=list)
    done: bool = False
    is_streaming: bool = False

    def to_dict(self):
        return {
            "done": self.done,
            "is_streaming": self.is_streaming,
            "message_count": len(self.messages),
        }
