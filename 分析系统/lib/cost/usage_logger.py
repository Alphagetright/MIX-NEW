# -*- coding: utf-8 -*-
"""Structured usage logging with query and trend analysis."""

import json
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional


@dataclass
class UsageRecord:
    """A single usage event record."""
    timestamp: datetime
    action: str
    quantity: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result["timestamp"] = self.timestamp.isoformat()
        return result


@dataclass
class UsageQuery:
    """Query parameters for filtering usage records."""
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    actions: Optional[List[str]] = None
    metadata_filter: Optional[Dict[str, Any]] = None

    def matches(self, record: UsageRecord) -> bool:
        if self.start_time and record.timestamp < self.start_time:
            return False
        if self.end_time and record.timestamp > self.end_time:
            return False
        if self.actions and record.action not in self.actions:
            return False
        if self.metadata_filter:
            for key, value in self.metadata_filter.items():
                if record.metadata.get(key) != value:
                    return False
        return True


@dataclass
class UsageTrend:
    """Aggregated usage trend over a time period."""
    period: str  # daily, weekly, monthly
    data: Dict[str, float] = field(default_factory=dict)  # period_key -> total_quantity


class UsageStore:
    """In-memory usage store with optional file persistence."""

    def __init__(self, file_path: Optional[Path] = None) -> None:
        self._records: List[UsageRecord] = []
        self.file_path = file_path
        if file_path and file_path.exists():
            self._load()

    def add(self, record: UsageRecord) -> None:
        self._records.append(record)
        if self.file_path:
            self._append_to_file(record)

    def query(self, query: UsageQuery) -> List[UsageRecord]:
        return [r for r in self._records if query.matches(r)]

    def _load(self) -> None:
        with open(self.file_path, "r", encoding="utf-8") as f:
            for line in f:
                data = json.loads(line.strip())
                data["timestamp"] = datetime.fromisoformat(data["timestamp"])
                self._records.append(UsageRecord(**data))

    def _append_to_file(self, record: UsageRecord) -> None:
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.file_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record.to_dict()) + "\n")


class UsageLogger:
    """Structured logging with queries and usage trends."""

    def __init__(self, store: Optional[UsageStore] = None) -> None:
        self.store = store or UsageStore()

    def log(self, action: str, quantity: float = 1.0,
            metadata: Optional[Dict[str, Any]] = None) -> UsageRecord:
        """Log a structured usage event."""
        record = UsageRecord(
            timestamp=datetime.utcnow(),
            action=action,
            quantity=quantity,
            metadata=metadata or {},
        )
        self.store.add(record)
        return record

    def query(self, query: UsageQuery) -> List[UsageRecord]:
        return self.store.query(query)

    def trend(self, period: str = "daily", query: Optional[UsageQuery] = None) -> UsageTrend:
        """Aggregate records into a usage trend."""
        records = self.store.query(query or UsageQuery())
        trend = UsageTrend(period=period)
        for record in records:
            if period == "daily":
                key = record.timestamp.strftime("%Y-%m-%d")
            elif period == "weekly":
                key = record.timestamp.strftime("%Y-W%W")
            elif period == "monthly":
                key = record.timestamp.strftime("%Y-%m")
            else:
                key = record.timestamp.strftime("%Y-%m-%d")
            trend.data[key] = trend.data.get(key, 0.0) + record.quantity
        return trend
