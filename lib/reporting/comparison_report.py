# -*- coding: utf-8 -*-
"""
Comparison reports for side-by-side evaluation of pipeline runs.

Supports comparing two batch runs, configuration variants, or strategy
effectiveness with structured, labeled comparison tables.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ComparisonTable:
    """Side-by-side comparison of two entities across named metrics."""

    label_a: str = ""
    label_b: str = ""
    metrics: Dict[str, Dict[str, float]] = field(default_factory=dict)

    def add_metric(self, name: str, value_a: float, value_b: float) -> None:
        self.metrics[name] = {"a": value_a, "b": value_b, "delta": value_b - value_a}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "label_a": self.label_a,
            "label_b": self.label_b,
            "metrics": dict(self.metrics),
        }


@dataclass
class BatchCompare:
    """Comparison of metrics between two pipeline batch runs."""

    run_id_a: str = ""
    run_id_b: str = ""
    table: ComparisonTable = field(default_factory=ComparisonTable)

    def to_dict(self) -> Dict[str, Any]:
        return {"run_id_a": self.run_id_a, "run_id_b": self.run_id_b, "table": self.table.to_dict()}


@dataclass
class ConfigCompare:
    """Comparison of outcomes between two configuration variants."""

    config_a: Dict[str, Any] = field(default_factory=dict)
    config_b: Dict[str, Any] = field(default_factory=dict)
    table: ComparisonTable = field(default_factory=ComparisonTable)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "config_a": dict(self.config_a),
            "config_b": dict(self.config_b),
            "table": self.table.to_dict(),
        }


@dataclass
class StrategyCompare:
    """Comparison of effectiveness across different strategies."""

    strategies: Dict[str, ComparisonTable] = field(default_factory=dict)

    def add_comparison(self, name: str, table: ComparisonTable) -> None:
        self.strategies[name] = table

    def to_dict(self) -> Dict[str, Any]:
        return {k: v.to_dict() for k, v in self.strategies.items()}


@dataclass
class ComparisonReport:
    """Top-level report containing one or more comparison types."""

    batch: Optional[BatchCompare] = None
    config: Optional[ConfigCompare] = None
    strategy: Optional[StrategyCompare] = None
    title: str = "Comparison Report"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "batch": self.batch.to_dict() if self.batch else None,
            "config": self.config.to_dict() if self.config else None,
            "strategy": self.strategy.to_dict() if self.strategy else None,
        }
