# -*- coding: utf-8 -*-
"""批量读取器 —— 目录扫描与批量加载"""

import os
import time


class FileFilter:
    """文件过滤器"""

    def __init__(self):
        self._include_exts = None
        self._exclude_exts = None
        self._min_size = None
        self._max_size = None
        self._ignore_patterns = []

    def include_extensions(self, extensions):
        self._include_exts = set(extensions)
        return self

    def exclude_extensions(self, extensions):
        self._exclude_exts = set(extensions)
        return self

    def size_range(self, min_bytes=None, max_bytes=None):
        self._min_size = min_bytes
        self._max_size = max_bytes
        return self

    def add_ignore_pattern(self, pattern):
        import re
        self._ignore_patterns.append(re.compile(pattern))
        return self

    def accept(self, filepath):
        if not os.path.isfile(filepath):
            return False
        _, ext = os.path.splitext(filepath)
        ext = ext.lower()

        if self._include_exts and ext not in self._include_exts:
            return False
        if self._exclude_exts and ext in self._exclude_exts:
            return False

        if self._min_size is not None and os.path.getsize(filepath) < self._min_size:
            return False
        if self._max_size is not None and os.path.getsize(filepath) > self._max_size:
            return False

        for pattern in self._ignore_patterns:
            if pattern.search(filepath):
                return False

        return True


class DirectoryScanner:
    """目录扫描器"""

    def __init__(self, filter=None):
        self.filter = filter or FileFilter()

    def scan(self, directory, recursive=False):
        results = []
        if not os.path.isdir(directory):
            return results
        if recursive:
            for root, _, files in os.walk(directory):
                for fname in sorted(files):
                    fpath = os.path.join(root, fname)
                    if self.filter.accept(fpath):
                        results.append(fpath)
        else:
            for fname in sorted(os.listdir(directory)):
                fpath = os.path.join(directory, fname)
                if self.filter.accept(fpath):
                    results.append(fpath)
        return results

    def scan_with_metadata(self, directory, recursive=False):
        files = self.scan(directory, recursive)
        return [self._file_metadata(f) for f in files]

    def _file_metadata(self, fpath):
        stat = os.stat(fpath)
        return {
            "path": fpath,
            "name": os.path.basename(fpath),
            "size": stat.st_size,
            "mtime": stat.st_mtime,
            "ext": os.path.splitext(fpath)[1].lower(),
        }


class BatchReader:
    """批量读取器"""

    def __init__(self, input_reader=None):
        self.input_reader = input_reader
        self._progress_callback = None

    def on_progress(self, callback):
        self._progress_callback = callback
        return self

    def read_all(self, filepaths):
        results = []
        total = len(filepaths)
        for i, fpath in enumerate(filepaths):
            try:
                data = self.input_reader.read(fpath) if self.input_reader else None
                results.append({"path": fpath, "data": data, "success": True})
            except Exception as e:
                results.append({"path": fpath, "error": str(e), "success": False})
            if self._progress_callback:
                self._progress_callback(i + 1, total)
        return results

    def read_batch(self, directory, recursive=False):
        scanner = DirectoryScanner()
        files = scanner.scan(directory, recursive)
        return self.read_all(files)
