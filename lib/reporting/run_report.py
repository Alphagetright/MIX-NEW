# -*- coding: utf-8 -*-
"""
Report models and builder for pipeline run summaries.
"""

import datetime
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ReportSection:
    """A named section within a report with a title and structured content."""
    title: str
    content: Dict[str, Any]
    order: int = 0


@dataclass
class RunMetadata:
    """Environment and execution metadata for a pipeline run."""
    timestamp: datetime.datetime
    duration_seconds: float = 0.0
    command: str = ""
    config_snapshot: Dict[str, Any] = field(default_factory=dict)
    host: str = ""
    pipeline_version: str = ""

    def to_dict(self) -> Dict[str, Any]:
        d = vars(self)
        d["timestamp"] = self.timestamp.isoformat()
        return d


@dataclass
class ResultStats:
    """Aggregated statistics for items processed during a run."""
    input_count: int = 0
    success_count: int = 0
    fail_count: int = 0
    avg_time_ms: float = 0.0
    total_time_ms: float = 0.0
    skip_count: int = 0

    @property
    def pass_rate(self) -> float:
        total = self.success_count + self.fail_count
        return (self.success_count / total * 100.0) if total else 0.0

    def to_dict(self) -> Dict[str, Any]:
        d = vars(self)
        d["pass_rate"] = self.pass_rate
        return d


@dataclass
class RunReport:
    """Top-level container for a complete pipeline run report."""
    metadata: RunMetadata
    stats: ResultStats
    sections: List[ReportSection] = field(default_factory=list)
    summary: str = ""

    def add_section(self, section: ReportSection) -> None:
        self.sections.append(section)
        self.sections.sort(key=lambda s: s.order)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "summary": self.summary,
            "metadata": self.metadata.to_dict(),
            "stats": self.stats.to_dict(),
            "sections": [vars(s) for s in self.sections],
        }


class RunReportBuilder:
    """Builds a RunReport by composing metadata, statistics, and sections."""

    def __init__(self) -> None:
        self._metadata: Optional[RunMetadata] = None
        self._stats: Optional[ResultStats] = None
        self._sections: List[ReportSection] = []
        self._summary: str = ""

    def with_metadata(self, timestamp: Optional[datetime.datetime] = None,
                      duration: float = 0.0, command: str = "",
                      config: Optional[Dict[str, Any]] = None) -> "RunReportBuilder":
        self._metadata = RunMetadata(
            timestamp=timestamp or datetime.datetime.now(),
            duration_seconds=duration, command=command,
            config_snapshot=config or {})
        return self

    def with_stats(self, inputs: int = 0, successes: int = 0,
                   failures: int = 0, avg_time: float = 0.0) -> "RunReportBuilder":
        self._stats = ResultStats(
            input_count=inputs, success_count=successes,
            fail_count=failures, avg_time_ms=avg_time)
        return self

    def add_section(self, title: str, content: Dict[str, Any],
                    order: int = 0) -> "RunReportBuilder":
        self._sections.append(ReportSection(title=title, content=content, order=order))
        return self

    def with_summary(self, text: str) -> "RunReportBuilder":
        self._summary = text
        return self

    def build(self) -> RunReport:
        if self._metadata is None:
            self._metadata = RunMetadata(timestamp=datetime.datetime.now())
        if self._stats is None:
            self._stats = ResultStats()
        return RunReport(metadata=self._metadata, stats=self._stats,
                         sections=list(self._sections), summary=self._summary)
