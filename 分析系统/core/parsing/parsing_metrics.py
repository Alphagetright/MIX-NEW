# -*- coding: utf-8 -*-
"""
Metrics collection and reporting for parsing operations including
success rates, error distributions, and field-level outcomes.
"""

import time
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple


class ParsingSummary:
    """Aggregated summary of parsing operations over a window."""
    def __init__(self, total: int = 0, succeeded: int = 0, failed: int = 0, avg_time: float = 0.0) -> None:
        self.total = total
        self.succeeded = succeeded
        self.failed = failed
        self.avg_time = avg_time

    @property
    def success_rate(self) -> float:
        return self.succeeded / self.total if self.total > 0 else 1.0

    @property
    def failure_rate(self) -> float:
        return self.failed / self.total if self.total > 0 else 0.0

    def merge(self, other: "ParsingSummary") -> "ParsingSummary":
        merged_total = self.total + other.total
        merged_avg = ((self.avg_time * self.total + other.avg_time * other.total) / merged_total) if merged_total > 0 else 0.0
        return ParsingSummary(merged_total, self.succeeded + other.succeeded, self.failed + other.failed, merged_avg)

    def __repr__(self) -> str:
        return (f"ParsingSummary(total={self.total}, succeeded={self.succeeded}, "
                f"failed={self.failed}, rate={self.success_rate:.1%}, avg_time={self.avg_time:.3f}s)")


class MetricBucket:
    """Store metrics by category with increment and aggregation support."""
    def __init__(self, name: str) -> None:
        self.name = name
        self._counts: Dict[str, int] = defaultdict(int)
        self._values: List[float] = []

    def increment(self, key: str, count: int = 1) -> None:
        self._counts[key] += count

    def record_value(self, value: float) -> None:
        self._values.append(value)

    @property
    def total_count(self) -> int:
        return sum(self._counts.values())

    def top_items(self, n: int = 5) -> List[Tuple[str, int]]:
        return sorted(self._counts.items(), key=lambda x: -x[1])[:n]

    def merge(self, other: "MetricBucket") -> "MetricBucket":
        merged = MetricBucket(self.name)
        for k, v in self._counts.items():
            merged._counts[k] = v
        for k, v in other._counts.items():
            merged._counts[k] += v
        merged._values = self._values + other._values
        return merged


class MetricsCollector:
    """Collect, aggregate, and report parsing metrics."""
    def __init__(self) -> None:
        self._error_bucket = MetricBucket("error_types")
        self._field_bucket = MetricBucket("fields")
        self._timings: List[float] = []
        self._success_count: int = 0
        self._failure_count: int = 0

    def record_success(self, duration: float) -> None:
        self._success_count += 1
        self._timings.append(duration)

    def record_failure(self, duration: float, error_type: str = "unknown") -> None:
        self._failure_count += 1
        self._timings.append(duration)
        self._error_bucket.increment(error_type)

    def record_field_outcome(self, field: str, success: bool) -> None:
        self._field_bucket.increment(f"{field}:{'ok' if success else 'fail'}")

    def summary(self) -> ParsingSummary:
        total = self._success_count + self._failure_count
        avg_time = sum(self._timings) / len(self._timings) if self._timings else 0.0
        return ParsingSummary(total, self._success_count, self._failure_count, avg_time)

    def field_success_rate(self, field: str) -> float:
        ok = self._field_bucket._counts.get(f"{field}:ok", 0)
        fail = self._field_bucket._counts.get(f"{field}:fail", 0)
        total = ok + fail
        return ok / total if total > 0 else 1.0

    def top_errors(self, n: int = 5) -> List[Tuple[str, int]]:
        return self._error_bucket.top_items(n)

    def reset(self) -> None:
        self._error_bucket = MetricBucket("error_types")
        self._field_bucket = MetricBucket("fields")
        self._timings.clear()
        self._success_count = 0
        self._failure_count = 0

    def merge(self, other: "MetricsCollector") -> "MetricsCollector":
        merged = MetricsCollector()
        merged._error_bucket = self._error_bucket.merge(other._error_bucket)
        merged._field_bucket = self._field_bucket.merge(other._field_bucket)
        merged._timings = self._timings + other._timings
        merged._success_count = self._success_count + other._success_count
        merged._failure_count = self._failure_count + other._failure_count
        return merged


class ParsingMetrics:
    """High-level facade for metrics collection with timing support."""
    def __init__(self, collector: Optional[MetricsCollector] = None) -> None:
        self._collector = collector or MetricsCollector()
        self._timers: Dict[str, float] = {}

    @property
    def collector(self) -> MetricsCollector:
        return self._collector

    def start_timer(self, name: str = "_default") -> None:
        self._timers[name] = time.monotonic()

    def stop_timer(self, name: str = "_default") -> float:
        return time.monotonic() - self._timers.pop(name, 0.0)

    def report(self) -> ParsingSummary:
        return self._collector.summary()
