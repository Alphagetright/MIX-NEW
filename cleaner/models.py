# -*- coding: utf-8 -*-
"""数据模型模块"""
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional
import time, uuid


@dataclass
class FileMeta:
    """文件元信息"""
    path: str = ""; name: str = ""; size: int = 0; modified: float = 0.0
    extension: str = ""; encoding: str = "unknown"; encoding_confidence: float = 0.0
    line_count: int = 0; is_valid_json: bool = False
    has_bom: bool = False; has_markdown_wrap: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CleaningResult:
    """单文件清洗结果"""
    file_path: str = ""; file_name: str = ""; original_size: int = 0; cleaned_size: int = 0
    fixes_applied: List[str] = field(default_factory=list); fix_count: int = 0
    errors: List[str] = field(default_factory=list); error_count: int = 0
    parse_success: bool = False; duration_ms: float = 0.0
    encoding_detected: str = ""; encoding_original: str = ""

    @property
    def success(self) -> bool:
        return self.parse_success and self.error_count == 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ValidationResult:
    """结构校验结果"""
    file_path: str = ""; is_valid: bool = False
    issues: List[str] = field(default_factory=list); issue_count: int = 0
    warnings: List[str] = field(default_factory=list)
    required_fields_present: List[str] = field(default_factory=list)
    required_fields_missing: List[str] = field(default_factory=list)
    poem_count: int = 0; imagery_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DedupResult:
    """去重结果"""
    total_items: int = 0; unique_items: int = 0; duplicate_groups: int = 0
    duplicates_removed: int = 0
    exact_duplicates: int = 0; fuzzy_duplicates: int = 0
    sample_duplicates: List[Dict[str, Any]] = field(default_factory=list)
    duration_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class BatchReport:
    """批量处理报告"""
    batch_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    started_at: float = field(default_factory=time.time); completed_at: float = 0.0
    total_files: int = 0; processed: int = 0; succeeded: int = 0; failed: int = 0
    total_fixes: int = 0; total_errors: int = 0
    results: List[CleaningResult] = field(default_factory=list)
    encoding_distribution: Dict[str, int] = field(default_factory=dict)

    @property
    def success_rate(self) -> float:
        return round(self.succeeded / max(1, self.processed) * 100, 1)

    @property
    def duration_seconds(self) -> float:
        return round((self.completed_at or time.time()) - self.started_at, 2)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["success_rate"] = self.success_rate
        d["duration_seconds"] = self.duration_seconds
        return d


@dataclass
class QualityReport:
    """数据质量报告"""
    report_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    generated_at: str = ""; data_directory: str = ""
    total_files: int = 0; total_size_bytes: int = 0
    valid_json_count: int = 0; invalid_json_count: int = 0
    encoding_stats: Dict[str, int] = field(default_factory=dict)
    field_coverage: Dict[str, float] = field(default_factory=dict)
    common_issues: List[Dict[str, Any]] = field(default_factory=list)
    overall_score: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class EncodingReport:
    file_path: str = ""; detected_encoding: str = ""; confidence: float = 0.0
    has_bom: bool = False; bom_type: str = ""; file_size: int = 0
    line_count: int = 0; quality: str = "unknown"
    def to_dict(self): return asdict(self)

@dataclass
class ConversionResult:
    source_file: str = ""; target_file: str = ""; source_format: str = ""
    target_format: str = ""; row_count: int = 0; duration_ms: float = 0.0
    success: bool = True; error: str = ""
    def to_dict(self): return asdict(self)

@dataclass
class CleaningSummary:
    total_files: int = 0; cleaned_files: int = 0; failed_files: int = 0
    total_fixes: int = 0; total_errors: int = 0; duration_seconds: float = 0.0
    encoding_fixed: int = 0; json_fixed: int = 0; duplicates_removed: int = 0
    @property
    def success_rate(self): return round(self.cleaned_files / max(1, self.total_files) * 100, 1)
    def to_dict(self): return asdict(self)
