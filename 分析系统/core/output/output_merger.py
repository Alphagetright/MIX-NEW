# -*- coding: utf-8 -*-
"""Merge output files: concat, interleave, key-merge, dedup, version-tag."""

import os, json, hashlib
from typing import Any, Callable, Optional


class VersionTag:
    def __init__(self, version: str = "1.0.0", description: str = "",
                 extra: Optional[dict[str, Any]] = None) -> None:
        self.version, self.description, self.extra = version, description, extra or {}

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = dict(version=self.version)
        if self.description:
            d["description"] = self.description
        d.update(self.extra)
        return d

    def add_to(self, data: Any) -> Any:
        meta = dict(_metadata=self.to_dict())
        if isinstance(data, dict):
            data["_version"] = meta["_metadata"]
        elif isinstance(data, list):
            data.insert(0, meta)
        return data


class MergeManifest:
    def __init__(self) -> None:
        self._files, self._checksums = [], {}

    def add_file(self, fp: str) -> None:
        self._files.append(fp)
        h = hashlib.md5()
        with open(fp, "rb") as fh:
            for chunk in iter(lambda: fh.read(8192), b""):
                h.update(chunk)
        self._checksums[fp] = h.hexdigest()

    @property
    def file_count(self) -> int:
        return len(self._files)

    @property
    def files(self) -> list[str]:
        return list(self._files)

    def to_dict(self) -> dict[str, Any]:
        return dict(merged_files=self._files, checksums=self._checksums, file_count=self.file_count)


class OutputMerger:
    CONCAT, INTERLEAVE, MERGE_BY_KEY = "concat", "interleave", "merge_by_key"
    KEEP_FIRST, KEEP_LAST, KEEP_ALL_UNIQUE = "keep_first", "keep_last", "keep_all_unique"

    def __init__(self, merge_strategy: str = CONCAT,
                 dedup_strategy: str = KEEP_ALL_UNIQUE,
                 key_fn: Optional[Callable[[Any], Any]] = None,
                 sort_output: bool = False) -> None:
        if merge_strategy not in (self.CONCAT, self.INTERLEAVE, self.MERGE_BY_KEY):
            raise ValueError(f"Unknown merge strategy: {merge_strategy}")
        if dedup_strategy not in (self.KEEP_FIRST, self.KEEP_LAST, self.KEEP_ALL_UNIQUE):
            raise ValueError(f"Unknown dedup strategy: {dedup_strategy}")
        self.merge_strategy, self.dedup_strategy = merge_strategy, dedup_strategy
        self.key_fn, self.sort_output = key_fn, sort_output

    def merge(self, sources: list[str], out: str,
              tag: Optional[VersionTag] = None) -> MergeManifest:
        manifest = MergeManifest()
        for fp in sources:
            manifest.add_file(fp)
        records = self._load_all(sources)
        merged = self._apply_strategy(records)
        deduped = self._apply_dedup(merged)
        if self.sort_output and self.key_fn:
            deduped.sort(key=self.key_fn)
        data = tag.add_to(deduped) if tag else deduped
        d = os.path.dirname(out)
        if d and not os.path.exists(d):
            os.makedirs(d, exist_ok=True)
        with open(out, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, ensure_ascii=False)
        return manifest

    def _load_all(self, paths: list[str]) -> list[Any]:
        records: list[Any] = []
        for fp in paths:
            with open(fp, "r", encoding="utf-8") as fh:
                d = json.load(fh)
            records.extend(d if isinstance(d, list) else [d])
        return records

    def _apply_strategy(self, records: list[Any]) -> list[Any]:
        if self.merge_strategy != self.MERGE_BY_KEY:
            return records
        if self.key_fn is None:
            raise ValueError("key_fn required for merge_by_key")
        merged: dict[Any, Any] = {}
        for item in records:
            merged[self.key_fn(item)] = item
        return list(merged.values())

    def _apply_dedup(self, records: list[Any]) -> list[Any]:
        if self.dedup_strategy == self.KEEP_ALL_UNIQUE:
            return self._dedup_unique(records)
        if self.dedup_strategy in (self.KEEP_FIRST, self.KEEP_LAST):
            return self._dedup_first_last(records)
        return records

    def _dedup_unique(self, records: list[Any]) -> list[Any]:
        if self.key_fn is None:
            seen: set[str] = set()
            out: list[Any] = []
            for r in records:
                h = json.dumps(r, sort_keys=True, ensure_ascii=False)
                if h not in seen:
                    seen.add(h)
                    out.append(r)
            return out
        seen_keys: set[Any] = set()
        outk: list[Any] = []
        for r in records:
            k = self.key_fn(r)
            if k not in seen_keys:
                seen_keys.add(k)
                outk.append(r)
        return outk

    def _dedup_first_last(self, records: list[Any]) -> list[Any]:
        if self.key_fn is None:
            return records
        seen: dict[Any, int] = {}
        for idx, item in enumerate(records):
            k = self.key_fn(item)
            if self.dedup_strategy == self.KEEP_FIRST:
                seen.setdefault(k, idx)
            else:
                seen[k] = idx
        keep = set(seen.values())
        return [records[i] for i in range(len(records)) if i in keep]
