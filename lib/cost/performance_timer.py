# -*- coding: utf-8 -*-
"""Performance timing with phase tracking, percentiles, and flame graph data."""

import math
import statistics
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional


class PercentileCalculator:
    """Calculate percentile values from a sorted list of samples."""

    @staticmethod
    def percentile(sorted_samples: List[float], p: float) -> float:
        """Compute the p-th percentile (0-100) from pre-sorted data."""
        if not sorted_samples:
            return 0.0
        n = len(sorted_samples)
        k = (p / 100.0) * (n - 1)
        f = math.floor(k)
        c = math.ceil(k)
        if f == c:
            return sorted_samples[int(k)]
        return sorted_samples[f] * (c - k) + sorted_samples[c] * (k - f)

    @staticmethod
    def p50(samples: List[float]) -> float:
        return PercentileCalculator.percentile(sorted(samples), 50)

    @staticmethod
    def p95(samples: List[float]) -> float:
        return PercentileCalculator.percentile(sorted(samples), 95)

    @staticmethod
    def p99(samples: List[float]) -> float:
        return PercentileCalculator.percentile(sorted(samples), 99)


@dataclass
class FlameNode:
    """A node in a flame graph tree representing a timed phase."""
    name: str
    duration: float = 0.0
    children: List["FlameNode"] = field(default_factory=list)
    start_time: float = 0.0

    def add_child(self, child: "FlameNode") -> None:
        self.children.append(child)

    def total_duration(self) -> float:
        total = self.duration
        for child in self.children:
            total += child.total_duration()
        return total


@dataclass
class TimingReport:
    """Statistics for one or more named timing phases."""
    phase_stats: Dict[str, "PhaseStats"] = field(default_factory=dict)

    @dataclass
    class PhaseStats:
        name: str
        samples: List[float] = field(default_factory=list)

        @property
        def count(self) -> int:
            return len(self.samples)

        @property
        def average(self) -> float:
            if not self.samples:
                return 0.0
            return sum(self.samples) / len(self.samples)

        @property
        def p50(self) -> float:
            return PercentileCalculator.p50(self.samples)

        @property
        def p95(self) -> float:
            return PercentileCalculator.p95(self.samples)

        @property
        def p99(self) -> float:
            return PercentileCalculator.p99(self.samples)

    def add_sample(self, phase: str, duration: float) -> None:
        if phase not in self.phase_stats:
            self.phase_stats[phase] = TimingReport.PhaseStats(name=phase)
        self.phase_stats[phase].samples.append(duration)


class TimerContext:
    """Context manager for timing a block of code."""

    def __init__(self, timer: "PerformanceTimer", phase: str) -> None:
        self.timer = timer
        self.phase = phase
        self.start: float = 0.0

    def __enter__(self) -> "TimerContext":
        self.start = time.perf_counter()
        return self

    def __exit__(self, *exc_info) -> None:
        duration = time.perf_counter() - self.start
        self.timer.record(self.phase, duration)


class PerformanceTimer:
    """Phase timing with average duration, percentiles, and flame graph data."""

    def __init__(self) -> None:
        self.report = TimingReport()
        self._flame_stack: List[FlameNode] = []
        self._root: Optional[FlameNode] = None

    def record(self, phase: str, duration: float) -> None:
        """Record a timing sample for a named phase."""
        self.report.add_sample(phase, duration)

    def context(self, phase: str) -> TimerContext:
        """Get a context manager that times a block for the given phase."""
        return TimerContext(self, phase)

    def begin_flame_phase(self, name: str) -> None:
        """Start a flame graph phase node."""
        node = FlameNode(name=name, start_time=time.perf_counter())
        if not self._root:
            self._root = node
            self._flame_stack = [node]
        else:
            self._flame_stack[-1].add_child(node)
            self._flame_stack.append(node)

    def end_flame_phase(self) -> None:
        """End the current flame graph phase node."""
        if self._flame_stack:
            node = self._flame_stack.pop()
            node.duration = time.perf_counter() - node.start_time

    def get_flame_root(self) -> Optional[FlameNode]:
        return self._root

    def summary(self) -> str:
        lines = ["=== Performance Timing Report ==="]
        for name, stats in sorted(self.report.phase_stats.items()):
            lines.append(
                f"  {name}: count={stats.count}, avg={stats.average:.4f}s, "
                f"P50={stats.p50:.4f}s, P95={stats.p95:.4f}s, P99={stats.p99:.4f}s"
            )
        return "\n".join(lines)
