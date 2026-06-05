# -*- coding: utf-8 -*-
"""
Cost analysis reports for pipeline execution tracking.
"""

import datetime
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class CostSummary:
    """Aggregated cost breakdown by category."""
    total_cost: float = 0.0
    by_category: Dict[str, float] = field(default_factory=dict)
    currency: str = "USD"

    def to_dict(self) -> Dict[str, Any]:
        return {"total_cost": self.total_cost, "by_category": dict(self.by_category),
                "currency": self.currency}


@dataclass
class CostTrend:
    """Daily or weekly cost trend data point."""
    label: str = ""
    cost: float = 0.0
    count: int = 0
    date: Optional[datetime.date] = None

    def to_dict(self) -> Dict[str, Any]:
        d = vars(self)
        d["date"] = self.date.isoformat() if self.date else None
        return d


@dataclass
class UnitCostAnalysis:
    """Per-item or per-record cost breakdown."""
    cost_per_item: float = 0.0
    cost_per_record: float = 0.0
    item_count: int = 0
    record_count: int = 0


@dataclass
class CostReport:
    """Complete cost report for a pipeline run or time period."""
    token_consumption: Dict[str, int] = field(default_factory=dict)
    cost_summary: CostSummary = field(default_factory=CostSummary)
    trends: List[CostTrend] = field(default_factory=list)
    unit_cost: UnitCostAnalysis = field(default_factory=UnitCostAnalysis)

    def to_dict(self) -> Dict[str, Any]:
        return {"token_consumption": dict(self.token_consumption),
                "cost_summary": self.cost_summary.to_dict(),
                "trends": [t.to_dict() for t in self.trends],
                "unit_cost": vars(self.unit_cost)}


class CostReportBuilder:
    """Builds a CostReport from raw cost and token data."""
    def __init__(self) -> None:
        self._tokens: Dict[str, int] = {}
        self._total: float = 0.0
        self._categories: Dict[str, float] = {}
        self._trends: List[CostTrend] = []
        self._unit: UnitCostAnalysis = UnitCostAnalysis()

    def with_token_usage(self, tokens: Dict[str, int]) -> "CostReportBuilder":
        self._tokens = dict(tokens)
        return self

    def with_cost(self, total: float, categories: Optional[Dict[str, float]] = None) -> "CostReportBuilder":
        self._total = total
        self._categories = dict(categories) if categories else {}
        return self

    def with_trends(self, trends: List[CostTrend]) -> "CostReportBuilder":
        self._trends = list(trends)
        return self

    def with_unit_analysis(self, items: int = 0, records: int = 0, total_cost: Optional[float] = None) -> "CostReportBuilder":
        cost = total_cost if total_cost is not None else self._total
        self._unit = UnitCostAnalysis(cost_per_item=cost / items if items else 0.0,
                                      cost_per_record=cost / records if records else 0.0,
                                      item_count=items, record_count=records)
        return self

    def build(self) -> CostReport:
        summary = CostSummary(total_cost=self._total, by_category=self._categories)
        return CostReport(token_consumption=self._tokens, cost_summary=summary,
                          trends=list(self._trends), unit_cost=self._unit)
