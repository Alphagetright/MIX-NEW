# -*- coding: utf-8 -*-
"""文件工具函数"""

import os
import shutil
import tempfile
import hashlib
import json


def ensure_dir(path):
    os.makedirs(path, exist_ok=True)
    return path


def get_file_size(path):
    if os.path.isfile(path):
        return os.path.getsize(path)
    return 0


def get_file_extension(path):
    _, ext = os.path.splitext(path)
    return ext.lower()


def list_files(directory, extensions=None, recursive=False):
    results = []
    if not os.path.isdir(directory):
        return results
    if recursive:
        for root, _, files in os.walk(directory):
            for fname in files:
                path = os.path.join(root, fname)
                ext = get_file_extension(path)
                if extensions is None or ext in extensions:
                    results.append(path)
    else:
        for fname in os.listdir(directory):
            path = os.path.join(directory, fname)
            if os.path.isfile(path):
                ext = get_file_extension(path)
                if extensions is None or ext in extensions:
                    results.append(path)
    return sorted(results)


def read_text_file(path, encoding="utf-8"):
    with open(path, "r", encoding=encoding) as f:
        return f.read()


def write_text_file(path, text, encoding="utf-8"):
    ensure_dir(os.path.dirname(path))
    with open(path, "w", encoding=encoding) as f:
        f.write(text)


def read_json_file(path, encoding="utf-8"):
    with open(path, "r", encoding=encoding) as f:
        return json.load(f)


def write_json_file(path, data, encoding="utf-8", indent=2):
    ensure_dir(os.path.dirname(path))
    with open(path, "w", encoding=encoding) as f:
        json.dump(data, f, ensure_ascii=False, indent=indent)


def file_hash(path, algorithm="md5"):
    h = hashlib.new(algorithm)
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def copy_file(src, dst):
    ensure_dir(os.path.dirname(dst))
    shutil.copy2(src, dst)


def move_file(src, dst):
    ensure_dir(os.path.dirname(dst))
    shutil.move(src, dst)


def safe_delete(path):
    try:
        if os.path.isfile(path):
            os.remove(path)
            return True
        elif os.path.isdir(path):
            shutil.rmtree(path)
            return True
    except Exception:
        pass
    return False


class TempDir:
    """临时目录上下文管理器"""

    def __init__(self, suffix=None, prefix="tmp_"):
        self.suffix = suffix
        self.prefix = prefix
        self.path = None

    def __enter__(self):
        self.path = tempfile.mkdtemp(suffix=self.suffix, prefix=self.prefix)
        return self.path

    def __exit__(self, *args):
        if self.path and os.path.exists(self.path):
            shutil.rmtree(self.path, ignore_errors=True)


class FileLock:
    """简单的文件锁"""

    def __init__(self, lock_path):
        self.lock_path = lock_path
        self._locked = False

    def acquire(self, timeout=10):
        import time
        start = time.time()
        while time.time() - start < timeout:
            try:
                fd = os.open(self.lock_path, os.O_CREAT | os.O_EXCL | os.O_RDWR)
                os.close(fd)
                self._locked = True
                return True
            except FileExistsError:
                time.sleep(0.1)
        return False

    def release(self):
        if self._locked and os.path.exists(self.lock_path):
            try:
                os.remove(self.lock_path)
            except Exception:
                pass
            self._locked = False

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, *args):
        self.release()
