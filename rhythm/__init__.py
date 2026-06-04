# -*- coding: utf-8 -*-
"""
古典诗词音韵格律自动分析引擎
============================
基于《平水韵》106韵部体系的古典诗词音韵格律分析 Python 库。
零外部依赖，纯标准库实现。

Features:
    - 平仄检测（基于平水韵106韵部数据库，5000+汉字）
    - 格律合规检查（16种模板：五绝/七绝/五律/七律 × 4起式）
    - 特殊违律检测（孤平、三平调、三仄尾）
    - 韵脚分析（韵部归属、邻韵通押检测）
    - 对仗检测（词性标注 + 逐字对齐 + 质量评分）
    - 音韵相似度（5维度加权比较）
    - 批量分析管线
    - 多格式报告（Text/JSON/HTML/CSV）
"""
__version__ = "1.0.0"
__version_info__ = (1, 0, 0)
__author__ = "Poetry Rhythm Team"
__description__ = "古典诗词音韵格律自动分析引擎"

from .batch_processor import BatchProcessor
from .data_loader import (
    extract_chinese_lines,
    load_poem_from_csv,
    load_poem_from_json,
    load_poem_from_text,
    load_poems_from_directory,
    quick_load,
    split_into_lines,
)
from .duizhang_detector import DuizhangDetector
from .meter_checker import MeterChecker
from .models import (
    AuthorRhymeProfile,
    BatchResult,
    CharAlignment,
    CoupletAnalysis,
    DuizhangReport,
    MeterReport,
    MeterTemplate,
    MeterViolation,
    MultiToneChar,
    PingzeAnnotation,
    PoemMetadata,
    RhymeChar,
    RhymeReport,
    ScansionResult,
    SimilarityResult,
    ToneDistribution,
)
from .pingze_engine import PingzeEngine
from .pingshui_db import PingShuiYunDB
from .report_generator import ReportGenerator
from .rhyme_analyzer import RhymeAnalyzer
from .rhyme_similarity import RhymeComparator
from .scansion_engine import ScansionEngine
from .tone_visualizer import ToneVisualizer
from .utils import (
    cosine_similarity,
    extract_chinese,
    is_chinese_char,
    levenshtein_distance,
    text_similarity,
)

__all__ = [
    "PingShuiYunDB",
    "PingzeEngine",
    "MeterChecker",
    "RhymeAnalyzer",
    "DuizhangDetector",
    "ScansionEngine",
    "ToneVisualizer",
    "RhymeComparator",
    "BatchProcessor",
    "ReportGenerator",
    "PingzeAnnotation",
    "MultiToneChar",
    "ToneDistribution",
    "MeterTemplate",
    "MeterViolation",
    "MeterReport",
    "RhymeChar",
    "RhymeReport",
    "CharAlignment",
    "CoupletAnalysis",
    "DuizhangReport",
    "ScansionResult",
    "SimilarityResult",
    "AuthorRhymeProfile",
    "BatchResult",
    "PoemMetadata",
    "load_poem_from_json",
    "load_poem_from_text",
    "load_poem_from_csv",
    "load_poems_from_directory",
    "quick_load",
    "extract_chinese_lines",
    "split_into_lines",
    "is_chinese_char",
    "extract_chinese",
    "cosine_similarity",
    "levenshtein_distance",
    "text_similarity",
]
