# -*- coding: utf-8 -*-
"""
缓存模块 — 文件缓存 + 内存缓存，支持 TTL
"""
import json
import os
import time
import threading

from config import CACHE_DIR, CACHE_DEFAULT_TTL, CACHE_ENABLED
from logger import get_logger

logger = get_logger("cache")


class MemoryCache:
    """线程安全的内存缓存"""

    def __init__(self, default_ttl: int = CACHE_DEFAULT_TTL):
        self._store = {}
        self._lock = threading.RLock()
        self.default_ttl = default_ttl

    def get(self, key: str):
        if not CACHE_ENABLED:
            return None
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            if entry["expires"] is not None and time.time() > entry["expires"]:
                del self._store[key]
                return None
            return entry["value"]

    def set(self, key: str, value, ttl: int = None):
        if not CACHE_ENABLED:
            return
        expires = None
        if ttl is None and self.default_ttl > 0:
            expires = time.time() + self.default_ttl
        elif ttl and ttl > 0:
            expires = time.time() + ttl
        with self._lock:
            self._store[key] = {"value": value, "expires": expires}

    def delete(self, key: str):
        with self._lock:
            self._store.pop(key, None)

    def clear(self):
        with self._lock:
            self._store.clear()

    def size(self) -> int:
        with self._lock:
            return len(self._store)

    def keys(self):
        with self._lock:
            return list(self._store.keys())


class FileCache:
    """文件缓存 — 持久化到磁盘"""

    def __init__(self, cache_dir: str = None, default_ttl: int = CACHE_DEFAULT_TTL):
        self.cache_dir = cache_dir or CACHE_DIR
        self.default_ttl = default_ttl
        self._lock = threading.RLock()
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir, exist_ok=True)

    def _path(self, key: str) -> str:
        safe = key.replace("/", "_").replace("\\", "_").replace(":", "_")
        return os.path.join(self.cache_dir, f"{safe}.json")

    def get(self, key: str):
        if not CACHE_ENABLED:
            return None
        path = self._path(key)
        try:
            with open(path, "r", encoding="utf-8") as f:
                entry = json.load(f)
            if entry.get("expires") and time.time() > entry["expires"]:
                os.remove(path)
                return None
            return entry["value"]
        except (FileNotFoundError, json.JSONDecodeError, KeyError):
            return None

    def set(self, key: str, value, ttl: int = None):
        if not CACHE_ENABLED:
            return
        expires = None
        if ttl is None and self.default_ttl > 0:
            expires = time.time() + self.default_ttl
        elif ttl and ttl > 0:
            expires = time.time() + ttl
        with self._lock:
            path = self._path(key)
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"value": value, "expires": expires}, f, ensure_ascii=False)

    def delete(self, key: str):
        path = self._path(key)
        try:
            os.remove(path)
        except FileNotFoundError:
            pass

    def clear(self):
        with self._lock:
            for fname in os.listdir(self.cache_dir):
                if fname.endswith(".json"):
                    os.remove(os.path.join(self.cache_dir, fname))

    def size(self) -> int:
        return len([f for f in os.listdir(self.cache_dir) if f.endswith(".json")])


# 全局单例
memory_cache = MemoryCache()
file_cache = FileCache()


class cached:
    """装饰器：缓存函数返回值"""

    def __init__(self, ttl: int = None, cache_backend: str = "memory"):
        self.ttl = ttl
        self.cache = memory_cache if cache_backend == "memory" else file_cache

    def __call__(self, func):
        def wrapper(*args, **kwargs):
            key = f"{func.__module__}:{func.__name__}:{repr(args)}:{repr(sorted(kwargs.items()))}"
            result = self.cache.get(key)
            if result is not None:
                return result
            result = func(*args, **kwargs)
            self.cache.set(key, result, ttl=self.ttl)
            return result
        return wrapper
