# -*- coding: utf-8 -*-
"""
数据质量评估模块
================
对数据目录进行全面的质量评估，生成包含编码统计、字段覆盖度、
常见问题分析的质量报告。
"""

import os, json, time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from .config import DATA_DIR, CATEGORY_NAME_MAP, DIMENSION_KEYS
from .logger import get_logger
from .models import QualityReport
from .utils import format_file_size, frequency_count

logger = get_logger("data_profiler")


class DataProfiler:
    """
    数据质量评估器

    对数据目录进行扫描，评估各维度数据质量。

    Usage:
        profiler = DataProfiler()
        report = profiler.generate_quality_report("./poem_json")
        print(f"质量评分: {report.overall_score}/100")
    """

    def __init__(self):
        pass

    def generate_quality_report(self, directory: str = None,
                                sample_size: int = 100) -> QualityReport:
        """生成数据质量报告"""
        if directory is None: directory = DATA_DIR
        report = QualityReport(
            data_directory=directory,
            generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )

        if not os.path.exists(directory):
            return report

        from .utils import list_files
        from .encoding_detector import detect_encoding
        from .preprocessor import safe_parse_json, extract_poems, validate_poem_structure

        files = list_files(directory, extensions=[".json", ".txt"], recursive=True)
        report.total_files = len(files)
        report.total_size_bytes = sum(os.path.getsize(f) for f in files)

        if not files:
            return report

        # 编码统计
        encoding_stats: Dict[str, int] = {}
        for fp in files[:sample_size]:
            enc, _ = detect_encoding(fp)
            encoding_stats[enc] = encoding_stats.get(enc, 0) + 1
        report.encoding_stats = encoding_stats

        # 解析成功率
        parse_success = 0; parse_fail = 0
        field_coverage: Dict[str, int] = {}
        all_units_count = 0; imagery_count = 0

        for fp in files[:min(sample_size, len(files))]:
            data, errs = safe_parse_json(fp)
            if data is not None:
                parse_success += 1
                poems = extract_poems(data)
                for poem in poems:
                    units = poem.get("分析单元", [])
                    for unit in units:
                        if isinstance(unit, dict):
                            all_units_count += 1
                            if str(unit.get("是否意象", "0")) == "1":
                                imagery_count += 1
                            for key in DIMENSION_KEYS + ["情感类别", "词性", "成分类型"]:
                                val = str(unit.get(key, "")).strip()
                                if val and val != "None":
                                    field_coverage[key] = field_coverage.get(key, 0) + 1
            else:
                parse_fail += 1

        report.valid_json_count = parse_success
        report.invalid_json_count = parse_fail

        # 字段覆盖度
        for key in field_coverage:
            field_coverage[key] = round(field_coverage[key] / max(1, all_units_count) * 100, 1)
        report.field_coverage = field_coverage

        # 常见问题
        issues = []
        if parse_fail > 0:
            issues.append({"issue": "JSON解析失败", "count": parse_fail,
                           "pct": round(parse_fail / report.total_files * 100, 1)})
        if "情感类别" in field_coverage:
            issues.append({"issue": "情感类别标注覆盖度",
                           "coverage_pct": field_coverage["情感类别"]})
        if imagery_count == 0:
            issues.append({"issue": "未检测到意象条目",
                           "suggestion": "检查分析单元中'是否意象'字段"})
        report.common_issues = issues

        # 质量评分 0-100
        score = 0
        score += min(25, parse_success / max(1, report.total_files) * 25)
        avg_coverage = sum(field_coverage.values()) / max(1, len(field_coverage))
        score += min(25, avg_coverage / 100 * 25)
        score += 25 if imagery_count > 0 else 0
        score += 25 if report.invalid_json_count < report.total_files * 0.1 else 15
        report.overall_score = int(score)

        logger.info(f"质量评估完成: {report.total_files}文件, 评分{report.overall_score}/100")
        return report

    def quick_stats(self, directory: str = None) -> Dict[str, Any]:
        """快速数据统计"""
        if directory is None: directory = DATA_DIR
        from .utils import list_files
        files = list_files(directory, extensions=[".json", ".txt"], recursive=True)
        total_size = sum(os.path.getsize(f) for f in files)

        # 统计前5个文件
        sample_encodings = {}
        from .encoding_detector import detect_encoding
        for fp in files[:10]:
            enc, _ = detect_encoding(fp)
            sample_encodings[enc] = sample_encodings.get(enc, 0) + 1

        return {
            "total_files": len(files),
            "total_size": format_file_size(total_size),
            "total_size_bytes": total_size,
            "sample_encodings": sample_encodings,
            "extensions": frequency_count([os.path.splitext(f)[1] for f in files]),
        }


# ─── 扩展分析 ───

def profile_single_file(file_path):
    profiler = DataProfiler()
    report = profiler.generate_quality_report(os.path.dirname(file_path), sample_size=1)
    from .encoding_detector import get_file_meta
    meta = get_file_meta(file_path)
    return {"quality_report": report.to_dict(), "file_meta": meta.to_dict()}

def compare_directories(dir1, dir2):
    profiler = DataProfiler()
    r1 = profiler.generate_quality_report(dir1, sample_size=50)
    r2 = profiler.generate_quality_report(dir2, sample_size=50)
    return {
        "dir1": {"path": dir1, "score": r1.overall_score, "files": r1.total_files},
        "dir2": {"path": dir2, "score": r2.overall_score, "files": r2.total_files},
        "score_diff": r2.overall_score - r1.overall_score,
    }

def generate_detailed_report(directory=None):
    profiler = DataProfiler()
    report = profiler.generate_quality_report(directory, sample_size=200)
    stats = profiler.quick_stats(directory)
    return {**report.to_dict(), **stats}
