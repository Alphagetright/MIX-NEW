# -*- coding: utf-8 -*-
"""Error pattern detection, systematic bias analysis, and periodic anomaly
identification for quality control pipelines."""

import math
import statistics
from abc import ABC, abstractmethod
from collections import Counter, defaultdict
from datetime import datetime
from typing import Any, Callable, Dict, List, NamedTuple, Optional, Tuple


class ErrorPattern(NamedTuple):
    """A registered pattern that describes a class of data quality issues."""
    name: str
    description: str
    severity_default: str  # critical, major, minor, warning, info
    match_fn: Callable[[Dict[str, Any]], bool]
    metadata: Dict[str, Any]


class PatternRegistry:
    """Central registry of known error patterns with associated metadata."""

    def __init__(self):
        self._patterns: Dict[str, ErrorPattern] = {}

    def register(self, pattern: ErrorPattern) -> None:
        """Register a new error pattern."""
        self._patterns[pattern.name] = pattern

    def unregister(self, name: str) -> None:
        self._patterns.pop(name, None)

    def get(self, name: str) -> Optional[ErrorPattern]:
        return self._patterns.get(name)

    def list_patterns(self) -> List[ErrorPattern]:
        return list(self._patterns.values())


class BiasDetector:
    """Detect systematic bias in field values across a record set."""

    def __init__(self, threshold: float = 0.15):
        self._threshold = threshold

    def detect_bias(self, records: List[Dict[str, Any]],
                    fields: Optional[List[str]] = None) -> Dict[str, Any]:
        """Check categorical fields for skewed distributions that may indicate bias.

        Returns a dict with field names as keys and bias analysis as values.
        """
        if not records:
            return {}
        field_names = fields or list(records[0].keys())
        results: Dict[str, Any] = {}
        for field in field_names:
            values = [r.get(field) for r in records if r.get(field) is not None]
            if not values:
                continue
            counter = Counter(values)
            total = len(values)
            most_common_count = counter.most_common(1)[0][1]
            ratio = most_common_count / total
            if ratio > (1.0 - self._threshold):
                results[field] = {
                    "bias_detected": True,
                    "dominant_value": counter.most_common(1)[0][0],
                    "dominant_ratio": round(ratio, 4),
                    "total_values": total,
                }
            else:
                entropy = -sum(
                    (c / total) * math.log2(c / total) for c in counter.values()
                )
                max_entropy = math.log2(len(counter)) if len(counter) > 1 else 1.0
                normalized_entropy = entropy / max_entropy if max_entropy else 1.0
                results[field] = {
                    "bias_detected": False,
                    "entropy": round(entropy, 4),
                    "normalized_entropy": round(normalized_entropy, 4),
                }
        return results


class AnomalyDetector:
    """Detect periodic or temporal anomalies in time-series quality metrics."""

    def __init__(self, z_threshold: float = 2.5):
        self._z_threshold = z_threshold

    def detect_anomalies(
        self, timestamps: List[datetime], values: List[float]
    ) -> List[Tuple[int, datetime, float, float]]:
        """Return list of (index, timestamp, value, z_score) for anomalous points."""
        if len(values) < 3:
            return []
        mean = statistics.mean(values)
        std = statistics.stdev(values) if len(values) > 1 else 0.0
        if std == 0.0:
            return []
        anomalies: List[Tuple[int, datetime, float, float]] = []
        for i, (ts, val) in enumerate(zip(timestamps, values)):
            z = (val - mean) / std
            if abs(z) > self._z_threshold:
                anomalies.append((i, ts, val, round(z, 4)))
        return anomalies


class PatternDetector:
    """Orchestrate error pattern detection, bias analysis, and anomaly detection."""

    def __init__(self, registry: Optional[PatternRegistry] = None):
        self._registry = registry or PatternRegistry()
        self._bias_detector = BiasDetector()
        self._anomaly_detector = AnomalyDetector()

    @property
    def registry(self) -> PatternRegistry:
        return self._registry

    def match_patterns(self, record: Dict[str, Any]) -> List[ErrorPattern]:
        """Return all registered patterns that match the given record."""
        return [p for p in self._registry.list_patterns() if p.match_fn(record)]

    def analyze_records(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Run full analysis: pattern matching, bias detection, anomaly detection."""
        matched = defaultdict(list)
        for record in records:
            for pattern in self.match_patterns(record):
                matched[pattern.name].append(record)
        bias = self._bias_detector.detect_bias(records)
        return {
            "matched_patterns": dict(matched),
            "bias_analysis": bias,
        }
