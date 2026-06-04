# -*- coding: utf-8 -*-
"""ZIP archiver: compression, timestamp naming, glob patterns, cleanup, report."""

import os, zipfile, datetime, fnmatch
from typing import Any, Optional


class ArchiveConfig:
    def __init__(self, compression_level: int = zipfile.ZIP_DEFLATED,
                 include_patterns: Optional[list[str]] = None,
                 exclude_patterns: Optional[list[str]] = None) -> None:
        valid = (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED, zipfile.ZIP_BZIP2, zipfile.ZIP_LZMA)
        if compression_level not in valid:
            raise ValueError(f"Unsupported compression: {compression_level}")
        self.compression_level = compression_level
        self.include_patterns = include_patterns or ["*"]
        self.exclude_patterns = exclude_patterns or []


class _ManifestEntry:
    __slots__ = ("source", "archive_path", "size_bytes", "compressed_bytes")

    def __init__(self, source: str, archive_path: str, size: int, compressed: int) -> None:
        self.source = source
        self.archive_path = archive_path
        self.size_bytes = size
        self.compressed_bytes = compressed


class ArchiveManifest:
    def __init__(self) -> None:
        self._entries: list[_ManifestEntry] = []

    def add_entry(self, source: str, archive_path: str, size: int, compressed: int) -> None:
        self._entries.append(_ManifestEntry(source, archive_path, size, compressed))

    @property
    def file_count(self) -> int:
        return len(self._entries)

    @property
    def total_size(self) -> int:
        return sum(e.size_bytes for e in self._entries)

    @property
    def total_compressed(self) -> int:
        return sum(e.compressed_bytes for e in self._entries)

    def to_dict(self) -> list[dict[str, Any]]:
        return [dict(source=e.source, archive_path=e.archive_path,
                     size_bytes=e.size_bytes, compressed_bytes=e.compressed_bytes)
                for e in self._entries]


class ArchiveReport:
    def __init__(self, archive_path: str, manifest: ArchiveManifest,
                 created_at: Optional[str] = None) -> None:
        self.archive_path = archive_path
        self.manifest = manifest
        self.created_at = created_at or datetime.datetime.now().isoformat()

    @property
    def compression_ratio(self) -> float:
        t = self.manifest.total_size
        return 0.0 if t == 0 else 1.0 - (self.manifest.total_compressed / t)

    def to_dict(self) -> dict[str, Any]:
        return dict(archive_path=self.archive_path, created_at=self.created_at,
                    file_count=self.manifest.file_count,
                    total_size_bytes=self.manifest.total_size,
                    total_compressed_bytes=self.manifest.total_compressed,
                    compression_ratio=round(self.compression_ratio, 4),
                    entries=self.manifest.to_dict())


class CleanupPolicy:
    def __init__(self, max_age_days: Optional[float] = None,
                 max_count: Optional[int] = None,
                 max_total_size_mb: Optional[float] = None) -> None:
        self.max_age_days, self.max_count, self.max_total_size_mb = max_age_days, max_count, max_total_size_mb

    def files_to_remove(self, archive_dir: str) -> list[str]:
        if not os.path.isdir(archive_dir):
            return []
        files: list[tuple[str, float, int]] = []
        for fname in os.listdir(archive_dir):
            fp = os.path.join(archive_dir, fname)
            if os.path.isfile(fp):
                files.append((fp, os.path.getmtime(fp), os.path.getsize(fp)))
        if not files:
            return []
        files.sort(key=lambda x: x[1], reverse=True)
        to_remove: set[str] = set()
        if self.max_age_days is not None:
            cutoff = datetime.datetime.now().timestamp() - (self.max_age_days * 86400)
            to_remove.update(fp for fp, mt, _ in files if mt < cutoff)
        if self.max_count is not None and len(files) > self.max_count:
            keep = {x[0] for x in files[:self.max_count]}
            to_remove.update(fp for fp, _, _ in files if fp not in keep)
        if self.max_total_size_mb is not None:
            max_bytes = int(self.max_total_size_mb * 1024 * 1024)
            acc = 0
            for fp, _, sz in files:
                if acc + sz > max_bytes:
                    to_remove.add(fp)
                else:
                    acc += sz
        return list(to_remove)


class FileArchiver:
    """Create timestamped ZIP archives with pattern filtering and cleanup."""

    def __init__(self, config: Optional[ArchiveConfig] = None) -> None:
        self.config = config or ArchiveConfig()

    def create_archive(self, source_dir: str, output_dir: str,
                       archive_name: Optional[str] = None) -> ArchiveReport:
        if not os.path.isdir(source_dir):
            raise NotADirectoryError(f"Not a directory: {source_dir}")
        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        name = (archive_name or f"archive_{ts}")
        if not name.endswith(".zip"):
            name += ".zip"
        ap = os.path.join(output_dir, name)
        manifest = ArchiveManifest()
        with zipfile.ZipFile(ap, "w", compression=self.config.compression_level) as zf:
            for root, _dirs, files in os.walk(source_dir):
                for fname in files:
                    fp = os.path.join(root, fname)
                    rel = os.path.relpath(fp, source_dir)
                    if not any(fnmatch.fnmatch(rel, p) for p in self.config.include_patterns):
                        continue
                    if any(fnmatch.fnmatch(rel, p) for p in self.config.exclude_patterns):
                        continue
                    arc = rel.replace(os.sep, "/")
                    zf.write(fp, arc)
                    info = zf.getinfo(arc)
                    manifest.add_entry(fp, arc, info.file_size, info.compress_size)
        return ArchiveReport(ap, manifest)

    def cleanup(self, archive_dir: str, policy: CleanupPolicy) -> list[str]:
        removed = policy.files_to_remove(archive_dir)
        for fp in removed:
            try:
                os.remove(fp)
            except OSError:
                pass
        return removed
