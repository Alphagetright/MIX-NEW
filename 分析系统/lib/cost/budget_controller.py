# -*- coding: utf-8 -*-
"""Budget control with limits, tracking, alerts, and auto-pause capability."""

import enum
import threading
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Callable, Dict, List, Optional


class BudgetPeriod(enum.Enum):
    """Time period for budget limits."""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    TOTAL = "total"


@dataclass
class BudgetLimit:
    """Budget limit configuration."""
    total_budget: Decimal
    period: BudgetPeriod = BudgetPeriod.TOTAL
    alert_threshold: float = 0.8  # 80% triggers alert

    @property
    def alert_amount(self) -> Decimal:
        return self.total_budget * Decimal(str(self.alert_threshold))


@dataclass
class BudgetAlert:
    """Alert raised when approaching or exceeding budget limits."""
    limit: BudgetLimit
    current_spend: Decimal
    usage_ratio: float
    message: str = ""

    def __post_init__(self) -> None:
        if not self.message:
            ratio_pct = self.usage_ratio * 100
            self.message = (
                f"Budget alert: {ratio_pct:.1f}% of {self.limit.period.value} "
                f"budget ({self.limit.total_budget}) used "
                f"({self.current_spend} spent)"
            )


@dataclass
class BudgetReport:
    """Budget status summary at a point in time."""
    limit: BudgetLimit
    spent: Decimal
    remaining: Decimal
    ratio: float
    alerts: List[BudgetAlert] = field(default_factory=list)

    @property
    def is_exceeded(self) -> bool:
        return self.spent >= self.limit.total_budget

    def summary(self) -> str:
        status = "EXCEEDED" if self.is_exceeded else "OK"
        return (
            f"Budget Report [{status}] - {self.limit.period.value}: "
            f"{self.spent}/{self.limit.total_budget} "
            f"({self.ratio:.1%}), remaining: {self.remaining}"
        )


class BudgetTracker:
    """Track spending against a single budget limit."""

    def __init__(self, limit: BudgetLimit) -> None:
        self.limit = limit
        self._spent: Decimal = Decimal("0")
        self._lock = threading.Lock()

    def add_cost(self, cost: Decimal) -> List[BudgetAlert]:
        """Add a cost and return any triggered alerts."""
        alerts: List[BudgetAlert] = []
        with self._lock:
            self._spent += cost
            ratio = self._get_ratio()
            if ratio >= self.limit.alert_threshold:
                alerts.append(BudgetAlert(self.limit, self._spent, ratio))
        return alerts

    @property
    def spent(self) -> Decimal:
        return self._spent

    def _get_ratio(self) -> float:
        if self.limit.total_budget == Decimal("0"):
            return 1.0
        return float(self._spent / self.limit.total_budget)

    def report(self) -> BudgetReport:
        return BudgetReport(
            limit=self.limit,
            spent=self._spent,
            remaining=self.limit.total_budget - self._spent,
            ratio=self._get_ratio(),
        )


class BudgetController:
    """Manage multiple budgets with warning thresholds and auto-pause signaling."""

    def __init__(self) -> None:
        self._trackers: Dict[str, BudgetTracker] = {}
        self._paused: bool = False
        self._on_alert: Optional[Callable[[BudgetAlert], None]] = None

    def add_budget(self, name: str, limit: BudgetLimit) -> None:
        """Register a named budget limit."""
        self._trackers[name] = BudgetTracker(limit)

    def record_cost(self, name: str, cost: Decimal) -> None:
        """Record a cost against a named budget."""
        tracker = self._trackers.get(name)
        if tracker is None:
            raise ValueError(f"No budget registered: {name}")
        alerts = tracker.add_cost(cost)
        for alert in alerts:
            if self._on_alert:
                self._on_alert(alert)
            if alert.usage_ratio >= 1.0:
                self._paused = True

    @property
    def is_paused(self) -> bool:
        return self._paused

    def resume(self) -> None:
        self._paused = False

    def set_alert_callback(self, callback: Callable[[BudgetAlert], None]) -> None:
        self._on_alert = callback

    def report(self, name: str) -> BudgetReport:
        tracker = self._trackers.get(name)
        if tracker is None:
            raise ValueError(f"No budget registered: {name}")
        return tracker.report()

    def all_reports(self) -> Dict[str, BudgetReport]:
        return {name: t.report() for name, t in self._trackers.items()}
