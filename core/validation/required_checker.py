# -*- coding: utf-8 -*-
"""
Required-fields checker for the validation layer.

Validates that mandatory fields are present in a data record, supports
nested (recursive) required-field checks, and conditional requirements
based on the value of other fields.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Sequence, Set, Tuple, Union


# ---------------------------------------------------------------------------
# Check result
# ---------------------------------------------------------------------------


class CheckResult:
    """Holds the list of missing and present fields after a check."""

    def __init__(
        self,
        missing: Optional[Sequence[str]] = None,
        present: Optional[Sequence[str]] = None,
    ) -> None:
        self.missing = set(missing) if missing else set()
        self.present = set(present) if present else set()

    def is_valid(self) -> bool:
        return len(self.missing) == 0

    def merge(self, other: CheckResult) -> CheckResult:
        """Combine two check results."""
        return CheckResult(
            missing=self.missing | other.missing,
            present=self.present | other.present,
        )

    def __repr__(self) -> str:
        return f"<CheckResult missing={len(self.missing)} present={len(self.present)}>"


# ---------------------------------------------------------------------------
# Required rule
# ---------------------------------------------------------------------------


class RequiredRule:
    """A rule describing when a field is mandatory.

    Parameters
    ----------
    field_name:
        The name of the field that is required.
    nested_fields:
        If set, the rule applies to sub-fields inside *field_name*
        (used for nested dict checks).
    condition:
        An optional callable ``(record: dict) -> bool``. When provided,
        the field is required only if the callable returns *True*.
    """

    def __init__(
        self,
        field_name: str,
        nested_fields: Optional[Sequence[str]] = None,
        condition: Optional[Callable[[Dict[str, Any]], bool]] = None,
    ) -> None:
        if not field_name:
            raise ValueError("field_name must not be empty")
        self.field_name = field_name
        self.nested_fields = tuple(nested_fields) if nested_fields else ()
        self.condition = condition

    def applies(self, record: Dict[str, Any]) -> bool:
        """Return *True* if this rule is active for the given *record*."""
        if self.condition is None:
            return True
        return bool(self.condition(record))

    def __repr__(self) -> str:
        cond = " conditional" if self.condition else ""
        nested = f" nested={self.nested_fields}" if self.nested_fields else ""
        return f"RequiredRule({self.field_name!r}{cond}{nested})"


# ---------------------------------------------------------------------------
# Condition builder (fluent API)
# ---------------------------------------------------------------------------


class ConditionBuilder:
    """Fluent builder for conditional required rules.

    Usage::

        builder = ConditionBuilder()
        rule = (builder
                .when("status", equals="active")
                .then("activation_date"))
    """

    def __init__(self) -> None:
        self._conditions: List[Callable[[Dict[str, Any]], bool]] = []
        self._field_name: Optional[str] = None

    def when(
        self,
        field: str,
        equals: Any = None,
        in_values: Optional[Sequence[Any]] = None,
    ) -> ConditionBuilder:
        """Add a condition based on *field*."""
        if equals is not None:

            def _eq(rec: Dict[str, Any], _f=field, _v=equals) -> bool:
                return rec.get(_f) == _v

            self._conditions.append(_eq)
        elif in_values is not None:
            vals = set(in_values)

            def _in(rec: Dict[str, Any], _f=field, _v=vals) -> bool:
                return rec.get(_f) in _v

            self._conditions.append(_in)
        return self

    def then(self, field_name: str) -> RequiredRule:
        """Finalise and return the RequiredRule."""
        if not self._conditions:
            raise ValueError("At least one condition must be set before .then()")

        def _combined(rec: Dict[str, Any]) -> bool:
            return all(c(rec) for c in self._conditions)

        return RequiredRule(field_name, condition=_combined)


# ---------------------------------------------------------------------------
# Required checker
# ---------------------------------------------------------------------------


class RequiredChecker:
    """Validates required fields in a data record."""

    def __init__(self, rules: Optional[Sequence[RequiredRule]] = None) -> None:
        self._rules = list(rules) if rules else []

    def add_rule(self, rule: RequiredRule) -> None:
        self._rules.append(rule)

    def check(self, record: Dict[str, Any]) -> CheckResult:
        """Check all applicable rules against *record*."""
        missing: Set[str] = set()
        present: Set[str] = set()

        for rule in self._rules:
            if not rule.applies(record):
                continue
            if rule.nested_fields:
                nested_result = nested_required_check(
                    record, rule.field_name, rule.nested_fields
                )
                missing |= nested_result.missing
                present |= nested_result.present
            else:
                if rule.field_name in record and record[rule.field_name] is not None:
                    present.add(rule.field_name)
                else:
                    missing.add(rule.field_name)

        return CheckResult(missing=sorted(missing), present=sorted(present))


# ---------------------------------------------------------------------------
# Nested required check
# ---------------------------------------------------------------------------


def nested_required_check(
    record: Dict[str, Any],
    parent_key: str,
    nested_fields: Sequence[str],
) -> CheckResult:
    """Recursively check that *nested_fields* exist under *parent_key*.

    If *parent_key* is missing or not a dict, all nested fields are
    reported as missing.
    """
    missing: Set[str] = set()
    present: Set[str] = set()

    parent = record.get(parent_key)
    if not isinstance(parent, dict):
        prefix = f"{parent_key}."
        for field in nested_fields:
            missing.add(prefix + field)
        return CheckResult(missing=sorted(missing), present=sorted(present))

    for field in nested_fields:
        full_path = f"{parent_key}.{field}"
        if field in parent and parent[field] is not None:
            present.add(full_path)
        else:
            missing.add(full_path)
    return CheckResult(missing=sorted(missing), present=sorted(present))
