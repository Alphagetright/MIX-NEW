# -*- coding: utf-8 -*-
"""Dashboard data preparation: metric formatting, chart data preparation,
hierarchical summaries, and point-in-time dashboard snapshots."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


class MetricFormatter:
    """Format raw quality metrics into human-readable display strings."""

    @staticmethod
    def percentage(value: float, decimal_places: int = 1) -> str:
        """Format a 0-1 float as a percentage string."""
        return f"{value * 100:.{decimal_places}f}%"

    @staticmethod
    def count(value: int) -> str:
        """Format an integer count with thousand separators (underscore)."""
        return f"{value:,}"

    @staticmethod
    def ratio(numerator: int, denominator: int) -> str:
        """Format a ratio like '3 / 10'."""
        return f"{numerator} / {denominator}"

    @staticmethod
    def slug(label: str) -> str:
        """Convert a label to a URL-friendly slug."""
        return label.lower().replace(" ", "_").replace("-", "_")


@dataclass
class ChartDataPrep:
    """Prepare structured data suitable for rendering in charts."""

    labels: List[str] = field(default_factory=list)
    values: List[float] = field(default_factory=list)
    series: Dict[str, List[float]] = field(default_factory=dict)
    chart_type: str = "bar"

    @classmethod
    def from_distribution(cls, distribution: Dict[str, float],
                          top_n: int = 10) -> "ChartDataPrep":
        """Create chart data from a field distribution dict."""
        sorted_items = sorted(
            distribution.items(), key=lambda x: x[1], reverse=True
        )[:top_n]
        return cls(
            labels=[str(k) for k, v in sorted_items],
            values=[v for k, v in sorted_items],
            chart_type="bar",
        )

    def add_series(self, name: str, data: List[float]) -> None:
        self.series[name] = data


class HierarchicalSummarizer:
    """Build drill-down summaries by grouping records along hierarchical axes."""

    def summarize(self, records: List[Dict[str, Any]],
                  group_by: str, metric_field: str,
                  agg: str = "count") -> Dict[str, Any]:
        """Group records by *group_by* and aggregate *metric_field*.

        Supported aggregations: count, sum, mean.
        """
        groups: Dict[str, list] = {}
        for record in records:
            key = str(record.get(group_by, "unknown"))
            groups.setdefault(key, []).append(record.get(metric_field))

        result: Dict[str, Any] = {}
        for key, values in groups.items():
            clean = [v for v in values if isinstance(v, (int, float))]
            if agg == "count":
                result[key] = len(values)
            elif agg == "sum":
                result[key] = sum(clean)
            elif agg == "mean":
                result[key] = sum(clean) / len(clean) if clean else 0.0
        return result


@dataclass
class DashboardSnapshot:
    """A point-in-time capture of all dashboard-relevant data."""
    timestamp: str
    overall_quality: float
    record_count: int
    error_count: int
    dimension_metrics: Dict[str, float]
    charts: Dict[str, ChartDataPrep]
    hierarchy: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert the snapshot to a plain dict for serialization."""
        return {
            "timestamp": self.timestamp,
            "overall_quality": self.overall_quality,
            "record_count": self.record_count,
            "error_count": self.error_count,
            "dimension_metrics": self.dimension_metrics,
            "charts": {
                name: {
                    "labels": c.labels,
                    "values": c.values,
                    "series": c.series,
                    "chart_type": c.chart_type,
                }
                for name, c in self.charts.items()
            },
            "hierarchy": self.hierarchy,
            "metadata": self.metadata,
        }


class DashboardData:
    """Orchestrate dashboard data preparation from raw quality metrics."""

    def __init__(self):
        self._formatter = MetricFormatter()
        self._chart_prep: Dict[str, ChartDataPrep] = {}
        self._summarizer = HierarchicalSummarizer()

    @property
    def formatter(self) -> MetricFormatter:
        return self._formatter

    @property
    def summarizer(self) -> HierarchicalSummarizer:
        return self._summarizer

    def add_chart(self, name: str, chart: ChartDataPrep) -> None:
        self._chart_prep[name] = chart

    def snapshot(self, overall_quality: float, record_count: int,
                 error_count: int, dimension_metrics: Dict[str, float],
                 timestamp: str) -> DashboardSnapshot:
        """Create a point-in-time DashboardSnapshot."""
        return DashboardSnapshot(
            timestamp=timestamp,
            overall_quality=overall_quality,
            record_count=record_count,
            error_count=error_count,
            dimension_metrics=dimension_metrics,
            charts=dict(self._chart_prep),
        )
