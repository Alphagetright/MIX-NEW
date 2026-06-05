# -*- coding: utf-8 -*-
"""日志清理 —— 过期日志的清理与归档"""

import os
import time
import shutil
import glob
import re


class LogCleaner:
    """日志清理器"""

    def __init__(self, retention_days=30, dry_run=False):
        self.retention_days = retention_days
        self.dry_run = dry_run

    def clean_directory(self, log_dir, patterns=None):
        patterns = patterns or ["*.log", "*.log.*", "*.txt"]
        cutoff = time.time() - self.retention_days * 86400
        stats = {"deleted": 0, "skipped": 0, "errors": 0, "freed_bytes": 0}

        for pattern in patterns:
            for filepath in glob.glob(os.path.join(log_dir, pattern)):
                try:
                    if not os.path.isfile(filepath):
                        continue
                    mtime = os.path.getmtime(filepath)
                    if mtime < cutoff:
                        stats["freed_bytes"] += os.path.getsize(filepath)
                        if not self.dry_run:
                            os.remove(filepath)
                        stats["deleted"] += 1
                    else:
                        stats["skipped"] += 1
                except Exception:
                    stats["errors"] += 1

        return stats

    def clean_rotated_files(self, log_dir, base_name):
        pattern = os.path.join(log_dir, f"{base_name}.*")
        stats = {"deleted": 0, "freed_bytes": 0}
        for filepath in glob.glob(pattern):
            try:
                stats["freed_bytes"] += os.path.getsize(filepath)
                if not self.dry_run:
                    os.remove(filepath)
                stats["deleted"] += 1
            except Exception:
                pass
        return stats

    def archive_old_logs(self, log_dir, archive_dir, days_old=7):
        os.makedirs(archive_dir, exist_ok=True)
        cutoff = time.time() - days_old * 86400
        stats = {"archived": 0, "errors": 0}

        for fname in os.listdir(log_dir):
            if not fname.endswith(".log"):
                continue
            fpath = os.path.join(log_dir, fname)
            try:
                if os.path.getmtime(fpath) < cutoff:
                    dest = os.path.join(archive_dir, fname)
                    shutil.move(fpath, dest)
                    stats["archived"] += 1
            except Exception:
                stats["errors"] += 1

        return stats

    def report(self, log_dir):
        total_size = 0
        file_count = 0
        for fname in os.listdir(log_dir):
            fpath = os.path.join(log_dir, fname)
            if os.path.isfile(fpath):
                total_size += os.path.getsize(fpath)
                file_count += 1
        return {
            "directory": log_dir,
            "file_count": file_count,
            "total_size_bytes": total_size,
            "retention_days": self.retention_days,
        }
