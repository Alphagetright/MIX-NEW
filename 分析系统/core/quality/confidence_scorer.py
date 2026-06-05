# -*- coding: utf-8 -*-
"""Composite confidence scoring based on field completeness, cross-record
consistency, and historical accuracy for quality control pipelines."""

from typing import Any, Dict, List, Optional


class ScoreNormalizer:
    """Normalize raw scores to a 0-1 range using configurable bounds."""

    def __init__(self, lower_bound: float = 0.0, upper_bound: float = 1.0):
        self._lower = lower_bound
        self._upper = upper_bound

    def normalize(self, raw: float) -> float:
        """Clamp and scale *raw* into [self._lower, self._upper]."""
        if raw < self._lower:
            return 0.0
        if raw > self._upper:
            return 1.0
        if self._upper == self._lower:
            return 1.0
        return (raw - self._lower) / (self._upper - self._lower)


class CompletenessFactor:
    """Score based on the ratio of present fields versus required fields."""

    def __init__(self, required_fields: Optional[List[str]] = None):
        self._required = required_fields or []

    def score(self, record: Dict[str, Any]) -> float:
        """Return completeness as a float in [0, 1]."""
        if not self._required:
            return 1.0
        present = sum(1 for f in self._required if record.get(f) is not None)
        return present / len(self._required)


class ConsistencyFactor:
    """Score based on how consistent values are for a record relative to a
    reference distribution (e.g., the most common value per field)."""

    def __init__(self, reference_records: Optional[List[Dict[str, Any]]] = None):
        self._reference = reference_records or []

    def set_reference(self, records: List[Dict[str, Any]]) -> None:
        """Set the reference distribution from a baseline set of records."""
        self._reference = records

    def score(self, record: Dict[str, Any]) -> float:
        """Return consistency score in [0, 1] for a single record.

        Heuristic: for each field, +1 if the record value matches the mode
        of the reference set; otherwise +0.5 if the value exists; otherwise 0.
        """
        if not self._reference or not record:
            return 1.0
        from collections import Counter

        total_score = 0.0
        field_count = 0
        for field in record:
            field_count += 1
            values = [r.get(field) for r in self._reference if r.get(field) is not None]
            if not values:
                total_score += 0.5 if record.get(field) is not None else 0.0
                continue
            mode_val = Counter(values).most_common(1)[0][0]
            val = record.get(field)
            if val is not None and val == mode_val:
                total_score += 1.0
            elif val is not None:
                total_score += 0.5
        return total_score / field_count if field_count else 1.0


class HistoricalFactor:
    """Score based on accuracy derived from historical comparison data."""

    def __init__(self, accuracy_history: Optional[List[float]] = None):
        self._history = accuracy_history or []

    def record_accuracy(self, accuracy: float) -> None:
        """Append a new accuracy observation (0.0 to 1.0)."""
        self._history.append(max(0.0, min(1.0, accuracy)))

    def score(self) -> float:
        """Return the moving average of historical accuracies, or 1.0 if empty."""
        if not self._history:
            return 1.0
        return sum(self._history) / len(self._history)


class ConfidenceScorer:
    """Produce a composite confidence score for a record.

    Composite = completeness * consistency * historical_accuracy
    """

    def __init__(self, normalizer: Optional[ScoreNormalizer] = None,
                 completeness: Optional[CompletenessFactor] = None,
                 consistency: Optional[ConsistencyFactor] = None,
                 historical: Optional[HistoricalFactor] = None):
        self._normalizer = normalizer or ScoreNormalizer()
        self._completeness = completeness or CompletenessFactor()
        self._consistency = consistency or ConsistencyFactor()
        self._historical = historical or HistoricalFactor()

    @property
    def completeness(self) -> CompletenessFactor:
        return self._completeness

    @property
    def consistency(self) -> ConsistencyFactor:
        return self._consistency

    @property
    def historical(self) -> HistoricalFactor:
        return self._historical

    def score_record(self, record: Dict[str, Any]) -> float:
        """Compute the composite confidence score for a single record."""
        c = self._completeness.score(record)
        s = self._consistency.score(record)
        h = self._historical.score()
        raw = c * s * h
        return self._normalizer.normalize(raw)

    def score_records(self, records: List[Dict[str, Any]]) -> List[float]:
        """Compute composite scores for a batch of records."""
        return [self.score_record(r) for r in records]
