# -*- coding: utf-8 -*-
"""Auto-fix plan generation, batch fix strategies, and fix suggestion
management for quality control pipelines."""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple


@dataclass
class FixSuggestion:
    """An individual fix suggestion for a specific record and field."""
    record_index: int
    field: str
    original_value: Any
    suggested_value: Any
    strategy: str
    confidence: float = 1.0
    applied: bool = False

    def apply(self, records: List[Dict[str, Any]]) -> bool:
        """Apply this fix to the given record list in-place."""
        try:
            records[self.record_index][self.field] = self.suggested_value
            self.applied = True
            return True
        except (IndexError, KeyError):
            return False


@dataclass
class BatchFixPlan:
    """Group fixes by strategy for efficient batch application."""
    strategy: str
    fixes: List[FixSuggestion] = field(default_factory=list)
    description: str = ""

    def add(self, fix: FixSuggestion) -> None:
        self.fixes.append(fix)

    def apply_all(self, records: List[Dict[str, Any]]) -> Tuple[int, int]:
        """Apply all fixes in the plan. Returns (succeeded, failed)."""
        success = 0
        failed = 0
        for fix in self.fixes:
            if fix.apply(records):
                success += 1
            else:
                failed += 1
        return (success, failed)

    @property
    def count(self) -> int:
        return len(self.fixes)


@dataclass
class CorrectionReport:
    """Summary of all applied and suggested fixes from a correction cycle."""
    total_suggested: int = 0
    total_applied: int = 0
    total_failed: int = 0
    plans: List[BatchFixPlan] = field(default_factory=list)
    summary: str = ""

    def merge(self, other: "CorrectionReport") -> None:
        self.total_suggested += other.total_suggested
        self.total_applied += other.total_applied
        self.total_failed += other.total_failed
        self.plans.extend(other.plans)


class AutoFixer:
    """Apply common automatic fixes based on registered fix functions."""

    def __init__(self):
        self._fix_fns: Dict[str, Callable[[Any], Any]] = {}

    def register_fix(self, field_pattern: str,
                     fn: Callable[[Any], Any]) -> None:
        """Register a fix function for fields matching *field_pattern*."""
        self._fix_fns[field_pattern] = fn

    def auto_fix(self, record: Dict[str, Any]) -> List[FixSuggestion]:
        """Run registered fix functions on the record and return suggestions."""
        suggestions: List[FixSuggestion] = []
        for field, value in record.items():
            for pattern, fn in self._fix_fns.items():
                if pattern in field or field == pattern:
                    try:
                        fixed = fn(value)
                        if fixed is not None and fixed != value:
                            suggestions.append(FixSuggestion(
                                record_index=0,
                                field=field,
                                original_value=value,
                                suggested_value=fixed,
                                strategy="auto_fix",
                            ))
                    except Exception:
                        pass
        return suggestions


class CorrectionBuilder:
    """Coordinate fix suggestions into batch plans and produce a report."""

    def __init__(self, auto_fixer: Optional[AutoFixer] = None):
        self._auto_fixer = auto_fixer or AutoFixer()

    @property
    def auto_fixer(self) -> AutoFixer:
        return self._auto_fixer

    def build_plan(self, records: List[Dict[str, Any]],
                   suggestions: Optional[List[FixSuggestion]] = None) -> BatchFixPlan:
        """Build a single batch fix plan from suggestions or auto-fix results."""
        if suggestions is None:
            suggestions = []
            for idx, record in enumerate(records):
                for fix in self._auto_fixer.auto_fix(record):
                    fix.record_index = idx
                    suggestions.append(fix)
        plan = BatchFixPlan(
            strategy="auto_fix",
            fixes=suggestions,
            description=f"Auto-fix plan with {len(suggestions)} suggestion(s)",
        )
        return plan

    def execute(self, records: List[Dict[str, Any]],
                plans: Optional[List[BatchFixPlan]] = None) -> CorrectionReport:
        """Execute fix plans and return a correction report."""
        if plans is None:
            plans = [self.build_plan(records)]
        report = CorrectionReport()
        for plan in plans:
            succeeded, failed = plan.apply_all(records)
            report.plans.append(plan)
            report.total_suggested += plan.count
            report.total_applied += succeeded
            report.total_failed += failed
        report.summary = (
            f"Suggested {report.total_suggested} fixes, "
            f"applied {report.total_applied}, "
            f"failed {report.total_failed}."
        )
        return report
