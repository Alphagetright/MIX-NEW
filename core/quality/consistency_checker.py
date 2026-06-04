# -*- coding: utf-8 -*-
"""Cross-record consistency checking, duplicate detection, value distribution
analysis, and outlier identification for quality control pipelines."""

import math
import statistics
from collections import Counter, defaultdict
from typing import Any, Dict, List, NamedTuple, Optional, Tuple


class ConsistencyReport(NamedTuple):
    """Summary of all consistency issues discovered during a check cycle."""
    total_records: int
    duplicate_groups: List[List[int]]
    field_distributions: Dict[str, Dict[str, float]]
    outlier_records: List[Tuple[int, str, Any]]
    field_null_counts: Dict[str, int]
    summary: str


class DuplicateDetector:
    """Detect duplicate records based on a set of key fields."""

    def __init__(self, key_fields: List[str], fuzzy: bool = False):
        self._key_fields = key_fields
        self._fuzzy = fuzzy

    def find_duplicates(self, records: List[Dict[str, Any]]) -> List[List[int]]:
        """Return list of groups, where each group is a list of record indices
        that are considered duplicates of one another."""
        groups: Dict[Tuple, List[int]] = defaultdict(list)
        for idx, record in enumerate(records):
            key = tuple(record.get(field) for field in self._key_fields)
            groups[key].append(idx)
        return [indices for indices in groups.values() if len(indices) > 1]


class DistributionAnalyzer:
    """Analyze the value distribution for each field across a record set."""

    def analyze(self, records: List[Dict[str, Any]],
               fields: Optional[List[str]] = None) -> Dict[str, Dict[str, float]]:
        """Compute distribution stats for each field.

        Returns a mapping of field name to a dict with keys:
        'unique', 'null', 'mean' (numeric only), 'std' (numeric only),
        'top_values' (list of (value, count) tuples).
        """
        if not records:
            return {}
        field_names = fields or list(records[0].keys())
        results: Dict[str, Dict[str, float]] = {}
        for field in field_names:
            values = [r.get(field) for r in records]
            cleaned = [v for v in values if v is not None]
            null_count = values.count(None)
            counter = Counter(cleaned)
            top = counter.most_common(5)
            dist: Dict[str, float] = {
                "unique": len(counter),
                "null": null_count,
                "total": len(values),
                "null_pct": round(null_count / len(values) * 100, 2) if values else 0.0,
            }
            if cleaned and all(isinstance(v, (int, float)) for v in cleaned):
                dist["mean"] = round(statistics.mean(cleaned), 4)
                dist["std"] = round(statistics.stdev(cleaned), 4) if len(cleaned) > 1 else 0.0
                dist["min"] = float(min(cleaned))
                dist["max"] = float(max(cleaned))
            dist["top_values"] = [(str(v), c) for v, c in top]
            results[field] = dist
        return results


class OutlierDetector:
    """Identify statistical outliers using the IQR method."""

    def __init__(self, iqr_multiplier: float = 1.5):
        self._iqr_mult = iqr_multiplier

    def find_outliers(
        self, records: List[Dict[str, Any]], numeric_fields: Optional[List[str]] = None
    ) -> List[Tuple[int, str, Any]]:
        """Return list of (record_index, field_name, outlier_value) tuples."""
        if not records:
            return []
        field_names = numeric_fields or [
            k for k in records[0] if records[0].get(k) is not None
            and isinstance(records[0][k], (int, float))
        ]
        outliers: List[Tuple[int, str, Any]] = []
        for field in field_names:
            values = [r.get(field) for r in records if isinstance(r.get(field), (int, float))]
            if len(values) < 4:
                continue
            sorted_vals = sorted(values)
            q1 = sorted_vals[len(sorted_vals) // 4]
            q3 = sorted_vals[(3 * len(sorted_vals)) // 4]
            iqr = q3 - q1
            lower = q1 - self._iqr_mult * iqr
            upper = q3 + self._iqr_mult * iqr
            for idx, record in enumerate(records):
                val = record.get(field)
                if isinstance(val, (int, float)) and (val < lower or val > upper):
                    outliers.append((idx, field, val))
        return outliers


class ConsistencyChecker:
    """Orchestrate cross-record quality checks: duplicates, distributions, outliers."""

    def __init__(self, key_fields: Optional[List[str]] = None):
        self._key_fields = key_fields or ["id"]
        self._duplicate_detector = DuplicateDetector(self._key_fields)
        self._distribution_analyzer = DistributionAnalyzer()
        self._outlier_detector = OutlierDetector()

    def run(self, records: List[Dict[str, Any]]) -> ConsistencyReport:
        """Execute all consistency checks and return a report."""
        if not records:
            return ConsistencyReport(
                total_records=0, duplicate_groups=[], field_distributions={},
                outlier_records=[], field_null_counts={}, summary="No records to check."
            )
        duplicates = self._duplicate_detector.find_duplicates(records)
        distributions = self._distribution_analyzer.analyze(records)
        outliers = self._outlier_detector.find_outliers(records)
        null_counts: Dict[str, int] = {}
        if records:
            for field in records[0]:
                null_counts[field] = sum(1 for r in records if r.get(field) is None)
        parts = [
            f"Checked {len(records)} records.",
            f"Found {len(duplicates)} duplicate group(s).",
            f"Detected {len(outliers)} outlier value(s).",
        ]
        return ConsistencyReport(
            total_records=len(records),
            duplicate_groups=duplicates,
            field_distributions=distributions,
            outlier_records=outliers,
            field_null_counts=null_counts,
            summary=" ".join(parts),
        )
