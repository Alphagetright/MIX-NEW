# -*- coding: utf-8 -*-
"""
Report archiving with auto-naming, categorized storage, and retention.
"""

import datetime
import hashlib
import os
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List


class NamingStrategy(Enum):
    """Strategies for generating archive file names."""
    TIMESTAMP = "timestamp"
    RUN_ID = "run_id"
    CONTENT_HASH = "content_hash"

    def generate(self, run_id: str = "", content: str = "") -> str:
        now = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        if self == NamingStrategy.TIMESTAMP:
            return f"report_{now}"
        elif self == NamingStrategy.RUN_ID:
            safe = run_id.replace("/", "_").replace("\\", "_") if run_id else "unknown"
            return f"report_{safe}"
        elif self == NamingStrategy.CONTENT_HASH:
            raw = content or f"{now}_{run_id}"
            return f"report_{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:12]}"
        return f"report_{now}"


@dataclass
class RetentionPolicy:
    """Rules for removing old archived reports."""
    keep_last_n: int = 0
    max_age_days: int = 0
    importance_threshold: int = 0

    def should_keep(self, age_days: int, importance: int = 0) -> bool:
        if self.max_age_days > 0 and age_days > self.max_age_days:
            return False
        if self.importance_threshold > 0 and importance < self.importance_threshold:
            return False
        return True


@dataclass
class ArchiveEntry:
    """A single entry in the archive index."""
    filename: str = ""
    path: str = ""
    timestamp: str = ""
    report_type: str = ""
    run_id: str = ""
    importance: int = 0


class ArchiveIndex:
    """Searchable in-memory index of archived reports."""
    def __init__(self) -> None:
        self._entries: List[ArchiveEntry] = []

    def add(self, entry: ArchiveEntry) -> None:
        self._entries.append(entry)

    def find_by_type(self, report_type: str) -> List[ArchiveEntry]:
        return [e for e in self._entries if e.report_type == report_type]

    def find_by_run(self, run_id: str) -> List[ArchiveEntry]:
        return [e for e in self._entries if e.run_id == run_id]

    def list_all(self) -> List[ArchiveEntry]:
        return list(self._entries)


class ReportArchiver:
    """Facade for archiving with naming, storage, retention, and indexing."""

    def __init__(self, base_path: str, naming: NamingStrategy = NamingStrategy.TIMESTAMP) -> None:
        self.index = ArchiveIndex()
        self._base_path = base_path
        self._naming = naming

    def _path_for(self, report_type: str) -> str:
        date_str = datetime.datetime.now().strftime("%Y-%m-%d")
        path = os.path.join(self._base_path, date_str, report_type)
        os.makedirs(path, exist_ok=True)
        return path

    def archive(self, report_type: str, content: str, run_id: str = "",
                importance: int = 0) -> ArchiveEntry:
        dir_path = self._path_for(report_type)
        filename = self._naming.generate(run_id=run_id, content=content)
        filepath = os.path.join(dir_path, f"{filename}.json")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        entry = ArchiveEntry(filename=f"{filename}.json", path=filepath,
                             timestamp=datetime.datetime.now().isoformat(),
                             report_type=report_type, run_id=run_id,
                             importance=importance)
        self.index.add(entry)
        return entry

    def apply_retention(self, policy: RetentionPolicy) -> List[str]:
        removed: List[str] = []
        now = datetime.datetime.now()
        for entry in self.index.list_all():
            age = (now - datetime.datetime.fromisoformat(entry.timestamp)).days
            if not policy.should_keep(age, entry.importance) and os.path.exists(entry.path):
                os.remove(entry.path)
                removed.append(entry.path)
        self._prune_index(policy)
        return removed

    def _prune_index(self, policy: RetentionPolicy) -> None:
        by_type: Dict[str, List[ArchiveEntry]] = {}
        for e in self.index.list_all():
            by_type.setdefault(e.report_type, []).append(e)
        keep: List[ArchiveEntry] = []
        for entries in by_type.values():
            for i, e in enumerate(sorted(entries, key=lambda x: x.timestamp, reverse=True)):
                age = (datetime.datetime.now() - datetime.datetime.fromisoformat(e.timestamp)).days
                if policy.keep_last_n > 0 and i >= policy.keep_last_n:
                    continue
                if policy.should_keep(age, e.importance):
                    keep.append(e)
        self.index._entries = keep
