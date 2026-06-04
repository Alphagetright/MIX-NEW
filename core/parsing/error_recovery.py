# -*- coding: utf-8 -*-
"""
Error recovery strategies for parsing failures including retry,
partial result extraction, and graceful degradation.
"""

import json
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional, Tuple


class RecoveryReport:
    """Report of what was recovered and what failed during error recovery."""
    def __init__(self) -> None:
        self.recovered: List[str] = []
        self.failed: List[str] = []
        self.skipped: List[str] = []
        self.original_errors: List[str] = []

    def add_recovered(self, field: str) -> None:
        self.recovered.append(field)

    def add_failed(self, field: str, error: str) -> None:
        self.failed.append(field)
        self.original_errors.append(f"{field}: {error}")

    def add_skipped(self, field: str) -> None:
        self.skipped.append(field)

    @property
    def total_attempted(self) -> int:
        return len(self.recovered) + len(self.failed)

    @property
    def success_rate(self) -> float:
        total = self.total_attempted
        return 1.0 if total == 0 else len(self.recovered) / total

    def summary(self) -> str:
        return (f"recovered={len(self.recovered)}, failed={len(self.failed)}, "
                f"skipped={len(self.skipped)}, rate={self.success_rate:.1%}")


class RecoveryStrategy(ABC):
    """Base class for recovery strategies."""
    @abstractmethod
    def recover(self, data: Any, context: Optional[Dict[str, Any]] = None) -> Tuple[Any, RecoveryReport]:
        ...


class RetryStrategy(RecoveryStrategy):
    """Retry a parsing operation with configurable attempts and cleaners."""
    def __init__(self, parser: Callable[[str], Any], max_retries: int = 3,
                 cleaners: Optional[List[Callable[[str], str]]] = None) -> None:
        self._parser = parser
        self._max_retries = max_retries
        self._cleaners = cleaners or []

    def recover(self, data: Any, context: Optional[Dict[str, Any]] = None) -> Tuple[Any, RecoveryReport]:
        report = RecoveryReport()
        text = data if isinstance(data, str) else str(data)
        for attempt in range(self._max_retries):
            try:
                cleaned = text
                for cleaner in self._cleaners:
                    cleaned = cleaner(cleaned)
                result = self._parser(cleaned)
                report.add_recovered("json_parse")
                return result, report
            except (json.JSONDecodeError, ValueError, TypeError) as exc:
                report.original_errors.append(f"attempt {attempt + 1}: {exc}")
        report.add_failed("json_parse", str(report.original_errors[-1]) if report.original_errors else "unknown")
        return None, report


class PartialResultStrategy(RecoveryStrategy):
    """Extract partial results from a failed parse wherever possible."""
    def __init__(self, field_extractors: Optional[Dict[str, Callable[[str], Any]]] = None) -> None:
        self._field_extractors = field_extractors or {}

    def recover(self, data: Any, context: Optional[Dict[str, Any]] = None) -> Tuple[Any, RecoveryReport]:
        report = RecoveryReport()
        partial: Dict[str, Any] = {}
        text = data if isinstance(data, str) else str(data)
        for field, extractor in self._field_extractors.items():
            try:
                value = extractor(text)
                if value is not None:
                    partial[field] = value
                    report.add_recovered(field)
                else:
                    report.add_skipped(field)
            except Exception as exc:
                report.add_failed(field, str(exc))
        return partial, report


class DegradeStrategy(RecoveryStrategy):
    """Return a degraded minimal result when full parsing is not possible."""
    def __init__(self, fallback_factory: Callable[[], Any]) -> None:
        self._fallback_factory = fallback_factory

    def recover(self, data: Any, context: Optional[Dict[str, Any]] = None) -> Tuple[Any, RecoveryReport]:
        report = RecoveryReport()
        try:
            fallback = self._fallback_factory()
            report.add_recovered("degraded_fallback")
            return fallback, report
        except Exception as exc:
            report.add_failed("degraded_fallback", str(exc))
            return None, report


class RecoveryChain:
    """Chain multiple recovery strategies, trying each in order."""
    def __init__(self, strategies: Optional[List[RecoveryStrategy]] = None) -> None:
        self._strategies = strategies or []

    def add_strategy(self, strategy: RecoveryStrategy) -> None:
        self._strategies.append(strategy)

    def execute(self, data: Any, context: Optional[Dict[str, Any]] = None) -> Tuple[Any, RecoveryReport]:
        combined = RecoveryReport()
        for strategy in self._strategies:
            try:
                result, report = strategy.recover(data, context)
                for f in report.recovered:
                    combined.add_recovered(f)
                for f, e in zip(report.failed, report.original_errors):
                    combined.add_failed(f, e)
                if result is not None:
                    return result, combined
            except Exception as exc:
                combined.add_failed(type(strategy).__name__, str(exc))
        return None, combined


class ErrorRecovery:
    """High-level error recovery coordinator with configurable strategy chain."""
    def __init__(self, chain: Optional[RecoveryChain] = None) -> None:
        self._chain = chain or RecoveryChain()
        self._history: List[RecoveryReport] = []

    def recover(self, data: Any, context: Optional[Dict[str, Any]] = None) -> Tuple[Any, RecoveryReport]:
        result, report = self._chain.execute(data, context)
        self._history.append(report)
        return result, report

    @property
    def history(self) -> List[RecoveryReport]:
        return list(self._history)

    def clear_history(self) -> None:
        self._history.clear()
