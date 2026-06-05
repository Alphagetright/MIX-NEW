# -*- coding: utf-8 -*-
"""
Validation summary and statistics for the validation layer.

Aggregates pass/fail rates, classifies and ranks errors by type,
and supports trend comparison between current and previous runs.
"""

from __future__ import annotations

from typing import (Any, Counter, Dict, List, Optional, Sequence, Set,
                    Tuple, Union)

from collections import Counter


# ---------------------------------------------------------------------------
# Summary statistics
# ---------------------------------------------------------------------------


class SummaryStats:
    """Aggregate validation statistics for a single run.

    Attributes
    ----------
    total:
        Total number of checks performed.
    passed:
        Number of checks that passed.
    failed:
        Number of checks that failed.
    warnings:
        Number of checks that produced a warning (non-fatal).
    pass_rate:
        Fraction of checks that passed (0.0 – 1.0).
    """

    def __init__(
        self,
        total: int = 0,
        passed: int = 0,
        failed: int = 0,
        warnings: int = 0,
    ) -> None:
        self.total = total
        self.passed = passed
        self.failed = failed
        self.warnings = warnings

    @property
    def pass_rate(self) -> float:
        if self.total == 0:
            return 0.0
        return self.passed / self.total

    def merge(self, other: SummaryStats) -> SummaryStats:
        return SummaryStats(
            total=self.total + other.total,
            passed=self.passed + other.passed,
            failed=self.failed + other.failed,
            warnings=self.warnings + other.warnings,
        )

    def __repr__(self) -> str:
        return (
            f"<SummaryStats total={self.total} passed={self.passed} "
            f"failed={self.failed} rate={self.pass_rate:.1%}>"
        )


# ---------------------------------------------------------------------------
# Error classifier
# ---------------------------------------------------------------------------


class ErrorClassifier:
    """Categorises error messages by type.

    Classification is based on keyword matching against the error text.
    """

    CATEGORY_KEYWORDS: Dict[str, Set[str]] = {
        "type_error": {"type mismatch", "expected", "got "},
        "missing_field": {"missing", "required", "absent"},
        "range_error": {"out of range", "violates", "min", "max"},
        "length_error": {"length", "too long", "too short"},
        "enum_error": {"not in", "not one of", "invalid choice"},
        "pattern_error": {"does not match", "pattern"},
        "dependency_error": {"dependency", "must be", "when "},
        "reference_error": {"not in reference", "unknown"},
        "threshold_error": {"threshold", "exceeded", "breach"},
    }

    def classify(self, error_message: str) -> str:
        """Return the category name for the given error message."""
        lower = error_message.lower()
        for category, keywords in self.CATEGORY_KEYWORDS.items():
            if any(kw in lower for kw in keywords):
                return category
        return "other"

    def classify_many(
        self, errors: Sequence[str]
    ) -> Dict[str, List[str]]:
        """Group a list of error messages by category.

        Returns a mapping of category -> list of error messages.
        """
        groups: Dict[str, List[str]] = {}
        for err in errors:
            cat = self.classify(err)
            groups.setdefault(cat, []).append(err)
        return groups


# ---------------------------------------------------------------------------
# Top errors
# ---------------------------------------------------------------------------


class TopErrors:
    """Ranks error messages by their frequency of occurrence."""

    def __init__(self, top_n: int = 10) -> None:
        if top_n < 1:
            raise ValueError("top_n must be >= 1")
        self._top_n = top_n

    def rank(self, errors: Sequence[str]) -> List[Tuple[str, int]]:
        """Return the *top_n* most frequent (error_message, count) pairs."""
        counter: Counter[str] = Counter(errors)
        return counter.most_common(self._top_n)


# ---------------------------------------------------------------------------
# Trend comparison
# ---------------------------------------------------------------------------


class TrendCompare:
    """Compares validation results between a current and a previous run."""

    def __init__(
        self,
        current: SummaryStats,
        previous: Optional[SummaryStats] = None,
    ) -> None:
        self.current = current
        self.previous = previous

    @property
    def pass_rate_change(self) -> Optional[float]:
        """Absolute change in pass rate (current – previous).

        Returns *None* if there is no previous run.
        """
        if self.previous is None:
            return None
        return self.current.pass_rate - self.previous.pass_rate

    @property
    def failure_delta(self) -> Optional[int]:
        """Absolute change in failure count (current – previous)."""
        if self.previous is None:
            return None
        return self.current.failed - self.previous.failed

    @property
    def summary_line(self) -> str:
        """A one-line summary of the trend."""
        parts = [f"Current pass rate: {self.current.pass_rate:.1%}"]
        if self.previous is not None:
            change = self.pass_rate_change
            if change is not None and change >= 0:
                parts.append(f"(+{change:.1%} vs previous)")
            elif change is not None:
                parts.append(f"({change:.1%} vs previous)")
        return " | ".join(parts)


# ---------------------------------------------------------------------------
# Validation summary (facade)
# ---------------------------------------------------------------------------


class ValidationSummary:
    """High-level summary generator for validation runs.

    Aggregates pass/fail statistics, classifies errors, ranks them,
    and optionally compares against a previous run.
    """

    def __init__(
        self,
        classifier: Optional[ErrorClassifier] = None,
        top_errors: Optional[TopErrors] = None,
    ) -> None:
        self._classifier = classifier or ErrorClassifier()
        self._top_errors = top_errors or TopErrors()

    def build(
        self,
        errors: Sequence[str],
        warnings: Sequence[str],
        total_checks: int,
        previous_stats: Optional[SummaryStats] = None,
    ) -> Tuple[SummaryStats, Dict[str, List[str]], List[Tuple[str, int]], TrendCompare]:
        """Build a complete summary tuple from raw data.

        Returns
        -------
        (stats, classified_errors, ranked_errors, trend)
        """
        passed = total_checks - len(errors)
        stats = SummaryStats(
            total=total_checks,
            passed=passed,
            failed=len(errors),
            warnings=len(warnings),
        )
        classified = self._classifier.classify_many(errors)
        ranked = self._top_errors.rank(errors)
        trend = TrendCompare(stats, previous_stats)
        return stats, classified, ranked, trend

    def format_text(
        self,
        stats: SummaryStats,
        classified: Dict[str, List[str]],
        ranked: List[Tuple[str, int]],
        trend: TrendCompare,
    ) -> str:
        """Return a human-readable summary string."""
        lines: List[str] = [
            "Validation Summary",
            "==================",
            f"  Total checks  : {stats.total}",
            f"  Passed        : {stats.passed}",
            f"  Failed        : {stats.failed}",
            f"  Warnings      : {stats.warnings}",
            f"  Pass rate     : {stats.pass_rate:.1%}",
            "",
            trend.summary_line,
            "",
            "Errors by category:",
        ]
        for cat, msgs in sorted(classified.items()):
            lines.append(f"  {cat}: {len(msgs)}")
        lines.extend(["", "Top errors:"])
        for msg, count in ranked:
            truncated = msg if len(msg) < 80 else msg[:77] + "..."
            lines.append(f"  [{count}] {truncated}")
        if not ranked:
            lines.append("  (none)")
        return "\n".join(lines)
