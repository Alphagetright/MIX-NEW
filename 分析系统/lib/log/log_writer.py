# -*- coding: utf-8 -*-
"""日志写入器 —— 控制台与文件双输出"""

import sys
import logging


class ConsoleWriter:
    """控制台日志写入器"""

    def __init__(self, out_stream=None, err_stream=None):
        self.out = out_stream or sys.stdout
        self.err = err_stream or sys.stderr

    def write(self, message, level=logging.INFO):
        stream = self.err if level >= logging.WARNING else self.out
        stream.write(message)
        stream.flush()

    def write_line(self, message, level=logging.INFO):
        self.write(message + "\n", level)


class FileWriter:
    """文件日志写入器"""

    def __init__(self, filepath, encoding="utf-8"):
        import os
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        self.filepath = filepath
        self.encoding = encoding
        self._file = None

    def _ensure_open(self):
        if self._file is None or self._file.closed:
            self._file = open(self.filepath, "a", encoding=self.encoding)

    def write(self, message, level=None):
        self._ensure_open()
        self._file.write(message)
        self._file.flush()

    def write_line(self, message, level=None):
        self.write(message + "\n")

    def close(self):
        if self._file and not self._file.closed:
            self._file.close()

    def __del__(self):
        self.close()


class MultiWriter:
    """多输出日志写入器"""

    def __init__(self):
        self._writers = []

    def add_writer(self, writer):
        self._writers.append(writer)

    def remove_writer(self, writer):
        self._writers.remove(writer)

    def write(self, message, level=logging.INFO):
        for w in self._writers:
            try:
                w.write(message, level)
            except Exception:
                pass

    def write_line(self, message, level=logging.INFO):
        for w in self._writers:
            try:
                w.write_line(message, level)
            except Exception:
                pass

    def close_all(self):
        for w in self._writers:
            try:
                if hasattr(w, 'close'):
                    w.close()
            except Exception:
                pass


class LogRotator:
    """日志轮转控制"""

    def __init__(self, max_bytes=10*1024*1024, backup_count=5):
        self.max_bytes = max_bytes
        self.backup_count = backup_count

    def rotate_if_needed(self, filepath):
        import os
        if not os.path.exists(filepath):
            return False
        if os.path.getsize(filepath) < self.max_bytes:
            return False
        self._do_rotate(filepath)
        return True

    def _do_rotate(self, filepath):
        import shutil
        for i in range(self.backup_count - 1, 0, -1):
            src = f"{filepath}.{i}"
            dst = f"{filepath}.{i + 1}"
            if os.path.exists(src):
                shutil.move(src, dst)
        if os.path.exists(filepath):
            shutil.move(filepath, f"{filepath}.1")
