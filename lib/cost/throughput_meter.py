# -*- coding: utf-8 -*-
"""Throughput measurement with sliding window rate calculation."""

import math
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Dict, List, Optional, Tuple


@dataclass
class SlidingWindow:
    """Time-based sliding window for tracking events and calculating rates."""
    window_seconds: float = 60.0
    _events: Deque[Tuple[float, float]] = field(default_factory=deque)

    def add(self, quantity: float = 1.0) -> None:
        """Record an event with the given quantity at the current time."""
        now = time.monotonic()
        self._events.append((now, quantity))
        self._prune(now)

    def _prune(self, now: float) -> None:
        """Remove events outside the window."""
        cutoff = now - self.window_seconds
        while self._events and self._events[0][0] < cutoff:
            self._events.popleft()

    @property
    def total_quantity(self) -> float:
        return sum(q for _, q in self._events)

    @property
    def event_count(self) -> int:
        return len(self._events)

    def rate(self) -> float:
        """Compute rate as quantity per second over the window."""
        if not self._events:
            return 0.0
        elapsed = min(self.window_seconds, time.monotonic() - self._events[0][0])
        if elapsed <= 0:
            return 0.0
        return self.total_quantity / elapsed

    def reset(self) -> None:
        self._events.clear()


@dataclass
class ThroughputSnapshot:
    """Current throughput state with rate, average, and peak."""
    current_rate: float = 0.0
    average_rate: float = 0.0
    peak_rate: float = 0.0
    total_units: float = 0.0
    elapsed_seconds: float = 0.0


class RateCalculator:
    """Calculate throughput rates over a sliding time window."""

    def __init__(self, window_seconds: float = 60.0) -> None:
        self.window = SlidingWindow(window_seconds=window_seconds)
        self._peak: float = 0.0
        self._total: float = 0.0
        self._start_time: float = time.monotonic()

    def record(self, quantity: float = 1.0) -> None:
        """Record a throughput event."""
        self.window.add(quantity)
        self._total += quantity
        current = self.window.rate()
        if current > self._peak:
            self._peak = current

    @property
    def current_rate(self) -> float:
        return self.window.rate()

    @property
    def peak_rate(self) -> float:
        return self._peak

    def snapshot(self) -> ThroughputSnapshot:
        elapsed = time.monotonic() - self._start_time
        avg = self._total / elapsed if elapsed > 0 else 0.0
        return ThroughputSnapshot(
            current_rate=self.current_rate,
            average_rate=avg,
            peak_rate=self._peak,
            total_units=self._total,
            elapsed_seconds=elapsed,
        )


class ThroughputMeter:
    """Measure throughput in items, characters, or tokens per second."""

    def __init__(self, window_seconds: float = 60.0) -> None:
        self._items = RateCalculator(window_seconds)
        self._chars = RateCalculator(window_seconds)
        self._tokens = RateCalculator(window_seconds)

    def record(self, items: int = 1, chars: int = 0, tokens: int = 0) -> None:
        """Record throughput event with item/char/token counts."""
        if items > 0:
            self._items.record(items)
        if chars > 0:
            self._chars.record(chars)
        if tokens > 0:
            self._tokens.record(tokens)

    @property
    def items_per_second(self) -> float:
        return self._items.current_rate

    @property
    def chars_per_second(self) -> float:
        return self._chars.current_rate

    @property
    def tokens_per_second(self) -> float:
        return self._tokens.current_rate

    def snapshot(self) -> Dict[str, ThroughputSnapshot]:
        return {
            "items": self._items.snapshot(),
            "chars": self._chars.snapshot(),
            "tokens": self._tokens.snapshot(),
        }
