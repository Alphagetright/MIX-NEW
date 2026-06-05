# -*- coding: utf-8 -*-
"""Quality overview metrics, per-dimension scores, trend indicators, and
actionable improvement suggestions for quality control pipelines."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class TrendIndicator(Enum):
    """Direction of quality movement over time."""
    IMPROVING = "improving"
    STABLE = "stable"
    DECLINING = "declining"

    @classmethod
    def from_delta(cls, current: float, previous: float,
                   tolerance: float = 0.02) -> "TrendIndicator":
        delta = current - previous
        if delta > tolerance:
            return cls.IMPROVING
        if delta < -tolerance:
            return cls.DECLINING
        return cls.STABLE

    def __str__(self) -> str:
        return self.value


@dataclass
class QualityScore:
    """A named quality dimension with its score and trend."""
    name: str
    score: float
    weight: float = 1.0
    trend: TrendIndicator = TrendIndicator.STABLE

    @property
    def weighted_score(self) -> float:
        return self.score * self.weight

    def __post_init__(self) -> None:
        self.score = max(0.0, min(1.0, self.score))


@dataclass
class ImprovementSuggestion:
    """An actionable suggestion to improve a quality dimension."""
    dimension: str
    message: str
    priority: int = 0  # lower = more urgent
    estimated_effort: str = "medium"  # low, medium, high

    def __lt__(self, other: "ImprovementSuggestion") -> bool:
        return self.priority < other.priority


@dataclass
class SummaryReport:
    """Formatted summary of the full quality assessment."""
    overall_score: float
    dimension_scores: List[QualityScore]
    trends: Dict[str, str]
    suggestions: List[ImprovementSuggestion]
    total_records: int
    error_count: int
    summary_text: str


class QualitySummary:
    """Aggregate and summarize quality metrics across all dimensions."""

    def __init__(self):
        self._dimensions: List[QualityScore] = []
        self._suggestions: List[ImprovementSuggestion] = []

    def add_dimension(self, dim: QualityScore) -> None:
        self._dimensions.append(dim)

    def add_suggestion(self, suggestion: ImprovementSuggestion) -> None:
        self._suggestions.append(suggestion)

    @property
    def dimensions(self) -> List[QualityScore]:
        return list(self._dimensions)

    @property
    def suggestions(self) -> List[ImprovementSuggestion]:
        return sorted(self._suggestions)

    def overall_score(self) -> float:
        """Compute weighted overall score across all dimensions."""
        if not self._dimensions:
            return 0.0
        total_weight = sum(d.weight for d in self._dimensions)
        if total_weight == 0:
            return 0.0
        return sum(d.weighted_score for d in self._dimensions) / total_weight

    def generate_report(self, total_records: int = 0,
                        error_count: int = 0) -> SummaryReport:
        """Produce a complete SummaryReport from current state."""
        overall = self.overall_score()
        trends = {d.name: str(d.trend) for d in self._dimensions}
        summary_parts = [
            f"Overall quality: {overall:.2%}",
            f"Dimensions assessed: {len(self._dimensions)}",
            f"Total suggestions: {len(self._suggestions)}",
        ]
        return SummaryReport(
            overall_score=overall,
            dimension_scores=list(self._dimensions),
            trends=trends,
            suggestions=sorted(self._suggestions),
            total_records=total_records,
            error_count=error_count,
            summary_text=" | ".join(summary_parts),
        )
