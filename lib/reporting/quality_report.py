# -*- coding: utf-8 -*-
"""
Quality assessment report for pipeline output validation.
"""

from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class QualityMetrics:
    """Per-dimension quality scores between 0.0 and 1.0."""
    completeness: float = 0.0
    accuracy: float = 0.0
    consistency: float = 0.0
    timeliness: float = 0.0
    custom: Dict[str, float] = field(default_factory=dict)

    @property
    def average(self) -> float:
        values = [self.completeness, self.accuracy, self.consistency, self.timeliness]
        values.extend(self.custom.values())
        return sum(values) / len(values) if values else 0.0

    def to_dict(self) -> Dict[str, Any]:
        d = vars(self)
        d["custom"] = dict(self.custom)
        d["average"] = self.average
        return d


@dataclass
class ErrorDistribution:
    """Counts and percentages of error types encountered during validation."""
    counts: Dict[str, int] = field(default_factory=dict)

    @property
    def total(self) -> int:
        return sum(self.counts.values())

    def percentage(self, error_type: str) -> float:
        return (self.counts.get(error_type, 0) / self.total * 100.0) if self.total else 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {"total": self.total, "distribution": {
            k: {"count": v, "percentage": self.percentage(k)} for k, v in self.counts.items()
        }}


@dataclass
class CompletenessTable:
    """Field-level completeness statistics for each monitored field."""
    fields: Dict[str, Dict[str, float]] = field(default_factory=dict)

    def add_field(self, name: str, filled: int, total: int) -> None:
        rate = (filled / total * 100.0) if total else 0.0
        self.fields[name] = {"filled": float(filled), "total": float(total), "rate": rate}


@dataclass
class QualityReport:
    """Composite report of data quality for a pipeline run."""
    validation_pass_rate: float = 0.0
    error_distribution: ErrorDistribution = field(default_factory=ErrorDistribution)
    completeness: CompletenessTable = field(default_factory=CompletenessTable)
    quality_score: float = 0.0
    metrics: QualityMetrics = field(default_factory=QualityMetrics)

    def to_dict(self) -> Dict[str, Any]:
        return {"validation_pass_rate": self.validation_pass_rate,
                "error_distribution": self.error_distribution.to_dict(),
                "completeness": self.completeness.fields,
                "quality_score": self.quality_score,
                "metrics": self.metrics.to_dict()}


class QualityReportBuilder:
    """Assembles a QualityReport from raw validation and quality data."""
    def __init__(self) -> None:
        self._pass_rate: float = 0.0
        self._error_counts: Dict[str, int] = {}
        self._field_data: Dict[str, Dict[str, float]] = {}
        self._metrics: QualityMetrics = QualityMetrics()

    def with_pass_rate(self, rate: float) -> "QualityReportBuilder":
        self._pass_rate = rate
        return self

    def with_error_distribution(self, counts: Dict[str, int]) -> "QualityReportBuilder":
        self._error_counts = dict(counts)
        return self

    def with_field_completeness(self, data: Dict[str, Dict[str, float]]) -> "QualityReportBuilder":
        self._field_data = dict(data)
        return self

    def with_quality_metrics(self, metrics: QualityMetrics) -> "QualityReportBuilder":
        self._metrics = metrics
        return self

    def build(self) -> QualityReport:
        dist = ErrorDistribution(counts=self._error_counts)
        table = CompletenessTable()
        for name, info in self._field_data.items():
            table.add_field(name, int(info.get("filled", 0)), int(info.get("total", 0)))
        score = self._metrics.average if self._metrics.average > 0 else self._pass_rate
        return QualityReport(validation_pass_rate=self._pass_rate,
                             error_distribution=dist, completeness=table,
                             quality_score=score, metrics=self._metrics)
