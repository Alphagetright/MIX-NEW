# -*- coding: utf-8 -*-
"""
Threshold configuration for the validation layer.

Maps field conditions to severity levels (error / warning / info) and
provides a fluent config builder and evaluator.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple, Union


# ---------------------------------------------------------------------------
# Severity levels
# ---------------------------------------------------------------------------


class Severity(Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"

    def __lt__(self, other: Severity) -> bool:
        order = [Severity.ERROR, Severity.WARNING, Severity.INFO]
        return order.index(self) < order.index(other)

    def __str__(self) -> str:
        return self.value


# ---------------------------------------------------------------------------
# Threshold rule
# ---------------------------------------------------------------------------


class ThresholdRule:
    """Associates a condition with a severity level.

    Parameters
    ----------
    field:
        The field name to evaluate.
    condition:
        A callable ``(value) -> bool`` that returns *True* when the
        threshold is breached.
    severity:
        The severity level to assign when breached.
    message:
        Optional human-readable description.
    """

    def __init__(
        self,
        field: str,
        condition: Callable[[Any], bool],
        severity: Severity,
        message: str = "",
    ) -> None:
        if not field:
            raise ValueError("field must not be empty")
        self.field = field
        self.condition = condition
        self.severity = severity
        self.message = message

    def evaluate(self, value: Any) -> Tuple[bool, Severity, str]:
        """Return (breached, severity, message) for the given value."""
        breached = self.condition(value)
        msg = self.message if self.message else f"{self.field} threshold breach"
        return breached, self.severity, msg

    def __repr__(self) -> str:
        return f"ThresholdRule({self.field}, {self.severity})"


# ---------------------------------------------------------------------------
# Threshold configuration
# ---------------------------------------------------------------------------


class ThresholdConfig:
    """Container for a set of threshold rules.

    Parameters
    ----------
    rules:
        Sequence of ThresholdRule instances.
    default_severity:
        Fallback severity when no rule matches (default: ERROR).
    """

    def __init__(
        self,
        rules: Optional[Sequence[ThresholdRule]] = None,
        default_severity: Severity = Severity.ERROR,
    ) -> None:
        self._rules = list(rules) if rules else []
        self.default_severity = default_severity

    def add_rule(self, rule: ThresholdRule) -> None:
        self._rules.append(rule)

    def rules_for_field(self, field: str) -> List[ThresholdRule]:
        return [r for r in self._rules if r.field == field]

    @property
    def rules(self) -> List[ThresholdRule]:
        return list(self._rules)

    def __repr__(self) -> str:
        return f"ThresholdConfig({len(self._rules)} rules)"


# ---------------------------------------------------------------------------
# Fluent config builder
# ---------------------------------------------------------------------------


class ConfigBuilder:
    """Fluent API for constructing a ThresholdConfig.

    Usage::

        config = (ConfigBuilder()
                  .error("age", lambda v: v is not None and v > 120)
                  .warning("score", lambda v: v is not None and v < 50)
                  .info("version", lambda v: v is None)
                  .build())
    """

    def __init__(self) -> None:
        self._rules: List[ThresholdRule] = []

    def error(
        self, field: str, condition: Callable[[Any], bool], msg: str = ""
    ) -> ConfigBuilder:
        self._rules.append(ThresholdRule(field, condition, Severity.ERROR, msg))
        return self

    def warning(
        self, field: str, condition: Callable[[Any], bool], msg: str = ""
    ) -> ConfigBuilder:
        self._rules.append(ThresholdRule(field, condition, Severity.WARNING, msg))
        return self

    def info(
        self, field: str, condition: Callable[[Any], bool], msg: str = ""
    ) -> ConfigBuilder:
        self._rules.append(ThresholdRule(field, condition, Severity.INFO, msg))
        return self

    def build(self) -> ThresholdConfig:
        return ThresholdConfig(self._rules)


# ---------------------------------------------------------------------------
# Threshold evaluator
# ---------------------------------------------------------------------------


class ThresholdEvaluator:
    """Evaluates values against a ThresholdConfig."""

    def __init__(self, config: ThresholdConfig) -> None:
        self._config = config

    def evaluate(
        self, field: str, value: Any
    ) -> List[Tuple[Severity, str]]:
        """Return list of (severity, message) for breached rules on *field*."""
        results: List[Tuple[Severity, str]] = []
        for rule in self._config.rules_for_field(field):
            breached, severity, msg = rule.evaluate(value)
            if breached:
                results.append((severity, msg))
        return results

    def evaluate_record(
        self, record: Dict[str, Any]
    ) -> Dict[str, List[Tuple[Severity, str]]]:
        """Evaluate all fields in *record* against the config."""
        result: Dict[str, List[Tuple[Severity, str]]] = {}
        for field, value in record.items():
            breaches = self.evaluate(field, value)
            if breaches:
                result[field] = breaches
        return result


# ---------------------------------------------------------------------------
# Default thresholds factory
# ---------------------------------------------------------------------------


def default_thresholds() -> ThresholdConfig:
    """Return a ThresholdConfig with sensible default rules."""
    return (
        ConfigBuilder()
        .warning("confidence", lambda v: v is not None and v < 0.5,
                 msg="Low confidence value")
        .warning("score", lambda v: v is not None and v < 0.0,
                 msg="Negative score")
        .error("age", lambda v: v is not None and v < 0,
               msg="Negative age")
        .info("version", lambda v: v is None,
              msg="Missing version field")
        .build()
    )
