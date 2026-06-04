# -*- coding: utf-8 -*-
"""
Integrity reporting for the validation layer.

Computes coverage statistics, missing-value distributions, and a
weighted completeness score for a collection of data records.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Set, Tuple


# ---------------------------------------------------------------------------
# Integrity report
# ---------------------------------------------------------------------------


class IntegrityReport:
    """Formatted report returned by the IntegrityReporter.

    Attributes
    ----------
    coverage:
        Overall coverage fraction (0.0 – 1.0).
    missing_distribution:
        Map of field name -> count of missing values.
    completeness_score:
        Weighted completeness score (0.0 – 1.0).
    record_count:
        Number of records analysed.
    field_count:
        Number of fields analysed.
    """

    def __init__(
        self,
        coverage: float,
        missing_distribution: Dict[str, int],
        completeness_score: float,
        record_count: int,
        field_count: int,
    ) -> None:
        self.coverage = coverage
        self.missing_distribution = missing_distribution
        self.completeness_score = completeness_score
        self.record_count = record_count
        self.field_count = field_count

    def format_text(self) -> str:
        """Return a human-readable textual report."""
        lines: List[str] = [
            "Integrity Report",
            "================",
            f"Records : {self.record_count}",
            f"Fields  : {self.field_count}",
            f"Coverage: {self.coverage:.1%}",
            f"Completeness: {self.completeness_score:.1%}",
            "",
            "Missing distribution (top 10):",
        ]
        sorted_missing = sorted(
            self.missing_distribution.items(), key=lambda x: -x[1]
        )[:10]
        for field, count in sorted_missing:
            pct = count / self.record_count if self.record_count else 0.0
            lines.append(f"  {field}: {count} ({pct:.1%})")
        if not sorted_missing:
            lines.append("  (none)")
        return "\n".join(lines)

    def __repr__(self) -> str:
        return (
            f"<IntegrityReport coverage={self.coverage:.1%} "
            f"completeness={self.completeness_score:.1%}>"
        )


# ---------------------------------------------------------------------------
# Coverage calculator
# ---------------------------------------------------------------------------


class CoverageCalculator:
    """Computes field-level and record-level coverage."""

    def __init__(self, fields: Sequence[str]) -> None:
        if not fields:
            raise ValueError("At least one field must be specified")
        self._fields = list(fields)

    def field_coverage(self, records: List[Dict[str, Any]]) -> Dict[str, float]:
        """Return per-field coverage as a fraction of non-null values."""
        total = len(records)
        if total == 0:
            return {f: 0.0 for f in self._fields}
        counts: Dict[str, int] = {f: 0 for f in self._fields}
        for record in records:
            for field in self._fields:
                val = record.get(field)
                if val is not None:
                    counts[field] += 1
        return {f: counts[f] / total for f in self._fields}

    def record_coverage(
        self, records: List[Dict[str, Any]]
    ) -> List[float]:
        """Return per-record coverage (fraction of fields present)."""
        if not self._fields:
            return [0.0] * len(records)
        result: List[float] = []
        for record in records:
            present = sum(
                1 for f in self._fields if record.get(f) is not None
            )
            result.append(present / len(self._fields))
        return result

    def overall_coverage(self, records: List[Dict[str, Any]]) -> float:
        """Return the fraction of all field × record cells that are non-null."""
        total_cells = len(self._fields) * len(records)
        if total_cells == 0:
            return 0.0
        filled = 0
        for record in records:
            for field in self._fields:
                if record.get(field) is not None:
                    filled += 1
        return filled / total_cells


# ---------------------------------------------------------------------------
# Missing distribution
# ---------------------------------------------------------------------------


class MissingDistribution:
    """Tracks which fields are most frequently missing."""

    def __init__(self, fields: Sequence[str]) -> None:
        self._fields = list(fields)

    def compute(self, records: List[Dict[str, Any]]) -> Dict[str, int]:
        """Count missing (None or absent) values per field."""
        counts: Dict[str, int] = {f: 0 for f in self._fields}
        for record in records:
            for field in self._fields:
                if field not in record or record[field] is None:
                    counts[field] += 1
        return counts


# ---------------------------------------------------------------------------
# Completeness score
# ---------------------------------------------------------------------------


class CompletenessScore:
    """Weighted completeness calculation.

    Each field can be assigned a weight; fields with higher weight
    contribute more to the final score.
    """

    def __init__(
        self, weights: Optional[Dict[str, float]] = None
    ) -> None:
        self._weights = dict(weights) if weights else {}

    def compute(
        self, records: List[Dict[str, Any]], fields: Sequence[str]
    ) -> float:
        """Weighted completeness over all records and fields.

        Returns a value in [0.0, 1.0].
        """
        if not records or not fields:
            return 0.0
        total_weight = 0.0
        filled_weight = 0.0
        for record in records:
            for field in fields:
                w = self._weights.get(field, 1.0)
                total_weight += w
                if record.get(field) is not None:
                    filled_weight += w
        return filled_weight / total_weight if total_weight > 0 else 0.0


# ---------------------------------------------------------------------------
# Integrity reporter (facade)
# ---------------------------------------------------------------------------


class IntegrityReporter:
    """High-level facade that produces an IntegrityReport."""

    def __init__(
        self,
        fields: Sequence[str],
        weights: Optional[Dict[str, float]] = None,
    ) -> None:
        self._calculator = CoverageCalculator(fields)
        self._missing = MissingDistribution(fields)
        self._score = CompletenessScore(weights)
        self._fields = list(fields)
        self._weights = weights

    def report(self, records: List[Dict[str, Any]]) -> IntegrityReport:
        """Generate a full integrity report for *records*."""
        coverage = self._calculator.overall_coverage(records)
        missing_dist = self._missing.compute(records)
        completeness = self._score.compute(records, self._fields)
        return IntegrityReport(
            coverage=coverage,
            missing_distribution=missing_dist,
            completeness_score=completeness,
            record_count=len(records),
            field_count=len(self._fields),
        )
