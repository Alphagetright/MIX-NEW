# -*- coding: utf-8 -*-
"""
Cross-field validation for the validation layer.

Handles inter-field dependencies, reference consistency, and custom
business-rule validation. Includes a dependency graph with cycle
detection.
"""

from __future__ import annotations

import itertools
from typing import (Any, Callable, Dict, List, Optional, Sequence, Set,
                    Tuple, Union)


# ---------------------------------------------------------------------------
# Dependency rule
# ---------------------------------------------------------------------------


class DependencyRule:
    """If field A has a given value, field B must have an expected value.

    Parameters
    ----------
    source_field:
        The field whose value triggers the rule.
    source_value:
        The value (or callable predicate) that activates the rule.
    target_field:
        The field that is constrained.
    target_value:
        The required value (or callable predicate) for *target_field*.
    """

    def __init__(
        self,
        source_field: str,
        source_value: Any,
        target_field: str,
        target_value: Any,
    ) -> None:
        self.source_field = source_field
        self.source_value = source_value
        self.target_field = target_field
        self.target_value = target_value

    def check(self, record: Dict[str, Any]) -> Tuple[bool, str]:
        src_val = record.get(self.source_field)

        activated = (
            callable(self.source_value)
            and bool(self.source_value(src_val))
        ) or (not callable(self.source_value) and src_val == self.source_value)

        if not activated:
            return True, ""

        tgt_val = record.get(self.target_field)
        if callable(self.target_value):
            satisfied = bool(self.target_value(tgt_val))
        else:
            satisfied = tgt_val == self.target_value

        if satisfied:
            return True, ""
        return (
            False,
            f"Dependency: when {self.source_field}={src_val!r}, "
            f"{self.target_field} must be {self.target_value!r} "
            f"(got {tgt_val!r})",
        )

    def __repr__(self) -> str:
        return (
            f"DependencyRule({self.source_field} -> {self.target_field})"
        )


# ---------------------------------------------------------------------------
# Reference rule
# ---------------------------------------------------------------------------


class ReferenceRule:
    """Ensures a field value exists in a reference list.

    Parameters
    ----------
    field:
        The field to check.
    reference_list:
        Sequence of allowed values.
    allow_missing:
        If *True*, a missing or *None* field is considered valid.
    """

    def __init__(
        self,
        field: str,
        reference_list: Sequence[Any],
        allow_missing: bool = True,
    ) -> None:
        if not reference_list:
            raise ValueError("reference_list must not be empty")
        self.field = field
        self.reference = set(reference_list)
        self.allow_missing = allow_missing

    def check(self, record: Dict[str, Any]) -> Tuple[bool, str]:
        value = record.get(self.field)
        if value is None and self.allow_missing:
            return True, ""
        if value not in self.reference:
            return False, f"{self.field}: {value!r} not in reference set"
        return True, ""

    def __repr__(self) -> str:
        return f"ReferenceRule({self.field})"


# ---------------------------------------------------------------------------
# Business rule
# ---------------------------------------------------------------------------


class BusinessRule:
    """Wraps an arbitrary validation function.

    The function receives the full record and returns ``(is_valid, message)``.
    """

    def __init__(
        self,
        name: str,
        func: Callable[[Dict[str, Any]], Tuple[bool, str]],
    ) -> None:
        if not name:
            raise ValueError("BusinessRule name must not be empty")
        self.name = name
        self.func = func

    def check(self, record: Dict[str, Any]) -> Tuple[bool, str]:
        return self.func(record)

    def __repr__(self) -> str:
        return f"BusinessRule({self.name!r})"


# ---------------------------------------------------------------------------
# Validation graph (dependency graph with cycle detection)
# ---------------------------------------------------------------------------


class ValidationGraph:
    """Builds a directed graph of field dependencies and detects cycles.

    Each node is a field name. An edge ``A -> B`` means A depends on B
    (i.e. B must be validated before A).
    """

    def __init__(self) -> None:
        self._edges: Dict[str, Set[str]] = {}

    def add_dependency(self, field: str, depends_on: str) -> None:
        if field not in self._edges:
            self._edges[field] = set()
        self._edges[field].add(depends_on)

    def add_rule(self, rule: DependencyRule) -> None:
        self.add_dependency(rule.target_field, rule.source_field)

    def has_cycle(self) -> bool:
        """Return *True* if the dependency graph contains a cycle."""
        visited: Set[str] = set()
        stack: Set[str] = set()

        def dfs(node: str) -> bool:
            visited.add(node)
            stack.add(node)
            for neighbour in self._edges.get(node, set()):
                if neighbour not in visited:
                    if dfs(neighbour):
                        return True
                elif neighbour in stack:
                    return True
            stack.discard(node)
            return False

        for node in list(self._edges):
            if node not in visited:
                if dfs(node):
                    return True
        return False

    def validation_order(self) -> List[str]:
        """Return fields in topological order (leaves first)."""
        if self.has_cycle():
            raise ValueError("Cannot compute order: graph contains a cycle")
        visited: Set[str] = set()
        order: List[str] = []

        def dfs(node: str) -> None:
            visited.add(node)
            for neighbour in self._edges.get(node, set()):
                if neighbour not in visited:
                    dfs(neighbour)
            order.append(node)

        for node in list(self._edges):
            if node not in visited:
                dfs(node)
        return order


# ---------------------------------------------------------------------------
# Cross validator
# ---------------------------------------------------------------------------


class CrossValidator:
    """Aggregates and runs cross-field validation rules."""

    def __init__(self) -> None:
        self._rules: List[Union[DependencyRule, ReferenceRule, BusinessRule]] = []
        self._graph = ValidationGraph()

    def add_dependency(self, rule: DependencyRule) -> None:
        self._rules.append(rule)
        self._graph.add_rule(rule)

    def add_reference(self, rule: ReferenceRule) -> None:
        self._rules.append(rule)

    def add_business_rule(self, rule: BusinessRule) -> None:
        self._rules.append(rule)

    def validate(self, record: Dict[str, Any]) -> List[Tuple[str, str]]:
        """Run all rules against *record*. Returns list of (rule_name, error)."""
        errors: List[Tuple[str, str]] = []
        for rule in self._rules:
            ok, msg = rule.check(record)
            if not ok:
                errors.append((repr(rule), msg))
        return errors

    def validate_batch(
        self, records: List[Dict[str, Any]]
    ) -> List[List[Tuple[str, str]]]:
        """Run all rules against every record."""
        return [self.validate(rec) for rec in records]

    @property
    def graph(self) -> ValidationGraph:
        return self._graph
