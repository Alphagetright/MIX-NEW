# -*- coding: utf-8 -*-
"""Cost reporting with detail, trends, comparisons, and ROI estimation."""

import math
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class CostDetail:
    """Cost details for a single item or batch."""
    item_id: str
    cost: Decimal
    tokens_used: int = 0
    model: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CostTrend:
    """Time-series cost data for trend analysis."""
    data_points: List[Tuple[datetime, Decimal]] = field(default_factory=list)

    def add_point(self, timestamp: datetime, cost: Decimal) -> None:
        self.data_points.append((timestamp, cost))

    @property
    def total_cost(self) -> Decimal:
        return sum((c for _, c in self.data_points), Decimal("0"))

    @property
    def average_cost(self) -> Decimal:
        if not self.data_points:
            return Decimal("0")
        return self.total_cost / Decimal(str(len(self.data_points)))

    @property
    def min_cost(self) -> Decimal:
        if not self.data_points:
            return Decimal("0")
        return min(c for _, c in self.data_points)

    @property
    def max_cost(self) -> Decimal:
        if not self.data_points:
            return Decimal("0")
        return max(c for _, c in self.data_points)

    def aggregate_by(self, period: str = "daily") -> Dict[str, Decimal]:
        """Aggregate costs by daily, weekly, or monthly periods."""
        result: Dict[str, Decimal] = defaultdict(Decimal)
        for ts, cost in self.data_points:
            if period == "daily":
                key = ts.strftime("%Y-%m-%d")
            elif period == "weekly":
                key = ts.strftime("%Y-W%W")
            elif period == "monthly":
                key = ts.strftime("%Y-%m")
            else:
                key = ts.strftime("%Y-%m-%d")
            result[key] += cost
        return dict(result)


@dataclass
class CostComparison:
    """Compare costs across different runs or configurations."""
    entries: Dict[str, List[CostDetail]] = field(default_factory=dict)

    def add_run(self, label: str, details: List[CostDetail]) -> None:
        self.entries[label] = details

    def total_by_run(self) -> Dict[str, Decimal]:
        return {
            label: sum((d.cost for d in details), Decimal("0"))
            for label, details in self.entries.items()
        }

    def savings(self, baseline: str, target: str) -> Decimal:
        """Compute savings of target run compared to baseline."""
        totals = self.total_by_run()
        return totals.get(baseline, Decimal("0")) - totals.get(target, Decimal("0"))

    def savings_percentage(self, baseline: str, target: str) -> float:
        totals = self.total_by_run()
        base = totals.get(baseline, Decimal("0"))
        if base == Decimal("0"):
            return 0.0
        return float((base - totals.get(target, Decimal("0"))) / base) * 100.0


@dataclass
class ROICalculator:
    """Estimate return on investment from cost vs quality improvement."""

    def estimate(self, baseline_cost: Decimal, new_cost: Decimal,
                 baseline_quality: float, new_quality: float) -> Dict[str, Any]:
        """Calculate ROI given cost and quality changes.

        Returns a dict with cost_change, quality_change, and roi_pct.
        """
        cost_change = float(new_cost - baseline_cost)
        quality_change = new_quality - baseline_quality
        if baseline_cost == Decimal("0"):
            roi_pct = 0.0
        else:
            cost_pct = float((new_cost - baseline_cost) / baseline_cost) * 100.0
            quality_pct = (quality_change / baseline_quality * 100.0) if baseline_quality > 0 else 0.0
            roi_pct = quality_pct - cost_pct
        return {
            "baseline_cost": baseline_cost,
            "new_cost": new_cost,
            "cost_change": cost_change,
            "baseline_quality": baseline_quality,
            "new_quality": new_quality,
            "quality_change": quality_change,
            "roi_pct": round(roi_pct, 2),
        }


class CostReport:
    """Generate detailed cost reports with trends, comparisons, and ROI."""

    def __init__(self) -> None:
        self._details: List[CostDetail] = []

    def add_detail(self, detail: CostDetail) -> None:
        self._details.append(detail)

    def trend(self) -> CostTrend:
        trend = CostTrend()
        for d in self._details:
            trend.add_point(d.timestamp, d.cost)
        return trend

    def by_model(self) -> Dict[str, Decimal]:
        result: Dict[str, Decimal] = defaultdict(Decimal)
        for d in self._details:
            result[d.model] += d.cost
        return dict(result)

    def by_day(self) -> Dict[str, Decimal]:
        return self.trend().aggregate_by("daily")

    def comparison(self, other: "CostReport", label_self: str = "current",
                   label_other: str = "previous") -> CostComparison:
        comp = CostComparison()
        comp.add_run(label_self, self._details)
        comp.add_run(label_other, other._details)
        return comp

    def summary(self) -> str:
        total = sum((d.cost for d in self._details), Decimal("0"))
        models = self.by_model()
        lines = [
            "=== Cost Report Summary ===",
            f"Total cost:      {total:.4f}",
            f"Total items:     {len(self._details)}",
            "--- By Model ---",
        ]
        for model, cost in sorted(models.items()):
            lines.append(f"  {model}: {cost:.4f}")
        return "\n".join(lines)
