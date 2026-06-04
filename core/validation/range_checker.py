# -*- coding: utf-8 -*-
"""
Range, length, and enum-membership checking for the validation layer.

Evaluates individual rules and aggregates results into a structured
report. Supports numeric ranges, string/list lengths, and enum sets.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple, Union


# ---------------------------------------------------------------------------
# Rules
# ---------------------------------------------------------------------------


class RangeRule:
    """A numeric range constraint for a single field.

    Parameters
    ----------
    field:
        The field name to check.
    minimum:
        Lower bound (inclusive or exclusive per *inclusive*).
    maximum:
        Upper bound (inclusive or exclusive per *inclusive*).
    inclusive:
        When *True* (default) bounds are ``<=`` / ``>=``;
        when *False* bounds are ``<`` / ``>``.
    """

    def __init__(
        self,
        field: str,
        minimum: Union[int, float],
        maximum: Union[int, float],
        inclusive: bool = True,
    ) -> None:
        if minimum > maximum:
            raise ValueError(f"RangeRule minimum ({minimum}) > maximum ({maximum})")
        self.field = field
        self.minimum = minimum
        self.maximum = maximum
        self.inclusive = inclusive

    def check(self, record: Dict[str, Any]) -> Tuple[bool, str]:
        value = record.get(self.field)
        if value is None:
            return True, ""  # absent fields are handled by RequiredChecker
        if not isinstance(value, (int, float)):
            return False, f"{self.field}: expected numeric, got {type(value).__name__}"
        if self.inclusive:
            ok = self.minimum <= value <= self.maximum
        else:
            ok = self.minimum < value < self.maximum
        if not ok:
            op = "<=" if self.inclusive else "<"
            return False, f"{self.field}: {value} violates {self.minimum} {op} x {op} {self.maximum}"
        return True, ""

    def __repr__(self) -> str:
        return f"RangeRule({self.field}, {self.minimum}, {self.maximum})"


class LengthRule:
    """Length constraint for a string or list field."""

    def __init__(
        self,
        field: str,
        min_length: int = 0,
        max_length: Optional[int] = None,
    ) -> None:
        if min_length < 0:
            raise ValueError(f"min_length ({min_length}) must be >= 0")
        self.field = field
        self.min_length = min_length
        self.max_length = max_length

    def check(self, record: Dict[str, Any]) -> Tuple[bool, str]:
        value = record.get(self.field)
        if value is None:
            return True, ""
        try:
            length = len(value)
        except TypeError:
            return False, f"{self.field}: value has no len()"
        if length < self.min_length:
            return False, f"{self.field}: length {length} < {self.min_length}"
        if self.max_length is not None and length > self.max_length:
            return False, f"{self.field}: length {length} > {self.max_length}"
        return True, ""

    def __repr__(self) -> str:
        return f"LengthRule({self.field}, {self.min_length}, {self.max_length})"


class EnumRule:
    """Ensure the field value is one of the allowed choices."""

    def __init__(self, field: str, allowed: Sequence[Any]) -> None:
        if not allowed:
            raise ValueError("EnumRule requires at least one allowed value")
        self.field = field
        self.allowed = tuple(allowed)

    def check(self, record: Dict[str, Any]) -> Tuple[bool, str]:
        value = record.get(self.field)
        if value is None:
            return True, ""
        if value not in self.allowed:
            return False, f"{self.field}: {value!r} not in {self.allowed}"
        return True, ""

    def __repr__(self) -> str:
        return f"EnumRule({self.field}, {self.allowed})"


# ---------------------------------------------------------------------------
# Check report
# ---------------------------------------------------------------------------


class CheckReport:
    """Aggregated results from running multiple rules against a record.

    Attributes
    ----------
    record_index:
        Optional identifier for the record that was checked.
    passed:
        List of (rule_description, "") tuples for passing rules.
    failed:
        List of (rule_description, error_message) tuples for failing rules.
    """

    def __init__(self, record_index: Optional[int] = None) -> None:
        self.record_index = record_index
        self.passed: List[Tuple[str, str]] = []
        self.failed: List[Tuple[str, str]] = []

    def add_pass(self, rule: str) -> None:
        self.passed.append((rule, ""))

    def add_fail(self, rule: str, message: str) -> None:
        self.failed.append((rule, message))

    @property
    def is_valid(self) -> bool:
        return len(self.failed) == 0

    @property
    def total(self) -> int:
        return len(self.passed) + len(self.failed)

    @property
    def summary(self) -> str:
        return f"{len(self.passed)} passed, {len(self.failed)} failed of {self.total}"

    def merge(self, other: CheckReport) -> CheckReport:
        merged = CheckReport(self.record_index)
        merged.passed = self.passed + other.passed
        merged.failed = self.failed + other.failed
        return merged


# ---------------------------------------------------------------------------
# Range checker
# ---------------------------------------------------------------------------


class RangeChecker:
    """Evaluates range, length, and enum rules against a data record."""

    def __init__(self) -> None:
        self._rules: List[Union[RangeRule, LengthRule, EnumRule]] = []

    def add_range_rule(self, rule: RangeRule) -> None:
        self._rules.append(rule)

    def add_length_rule(self, rule: LengthRule) -> None:
        self._rules.append(rule)

    def add_enum_rule(self, rule: EnumRule) -> None:
        self._rules.append(rule)

    def check(self, record: Dict[str, Any], index: Optional[int] = None) -> CheckReport:
        """Run all registered rules against *record*."""
        report = CheckReport(record_index=index)
        for rule in self._rules:
            ok, msg = rule.check(record)
            if ok:
                report.add_pass(repr(rule))
            else:
                report.add_fail(repr(rule), msg)
        return report

    def check_batch(
        self, records: List[Dict[str, Any]]
    ) -> List[CheckReport]:
        """Run all rules against every record in *records*."""
        return [self.check(rec, idx) for idx, rec in enumerate(records)]
