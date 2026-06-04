# -*- coding: utf-8 -*-
"""
缓存管理器
==========
双层缓存体系：内存缓存（LRU/TTL策略）+ 文件缓存（JSON持久化）。

特性：
  - 线程安全（RLock）
  - TTL 自动过期
  - LRU/LFU/TTL 三种淘汰策略
  - 缓存统计信息
  - 自动清理过期条目
  - 装饰器模式支持
"""

import json
import os
import time
import threading
from typing import Any, Callable, Dict, List, Optional, Tuple

from .config import (
    CACHE_DIR, CACHE_ENABLED, CACHE_DEFAULT_TTL,
    CACHE_MAX_MEMORY_ITEMS, CACHE_CLEANUP_STRATEGY,
    CACHE_AUTO_CLEANUP_INTERVAL,
)
from .logger import get_logger

logger = get_logger("cache_manager")


# ============================================================================
# 内存缓存
# ============================================================================


class MemoryCache:
    """
    线程安全的内存缓存

    支持 TTL 过期自动失效，可配置最大条目数。
    当缓存满时根据淘汰策略（LRU/TTL/LFU）移除条目。

    Usage:
        cache = MemoryCache(max_items=1000, default_ttl=600)
        cache.set("key", {"data": "value"})
        value = cache.get("key")
    """

    def __init__(self, max_items: int = CACHE_MAX_MEMORY_ITEMS,
                 default_ttl: int = CACHE_DEFAULT_TTL,
                 eviction_strategy: str = "lru"):
        self._lock = threading.RLock()
        self._store: Dict[str, Dict[str, Any]] = {}
        self._max_items = max_items
        self._default_ttl = default_ttl
        self._eviction_strategy = eviction_strategy.lower()
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        self._set_count = 0
        logger.info(
            f"MemoryCache 初始化: max={max_items}, ttl={default_ttl}s, "
            f"strategy={self._eviction_strategy}"
        )

    def get(self, key: str) -> Optional[Any]:
        """获取缓存值，过期返回 None"""
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                self._misses += 1
                return None
            if time.time() - entry["created_at"] > entry["ttl"]:
                del self._store[key]
                self._misses += 1
                return None
            entry["access_count"] += 1
            entry["last_accessed"] = time.time()
            self._hits += 1
            return entry["value"]

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """设置缓存值"""
        with self._lock:
            if len(self._store) >= self._max_items and key not in self._store:
                self._evict_one()
            item_ttl = ttl if ttl is not None else self._default_ttl
            self._store[key] = {
                "value": value,
                "created_at": time.time(),
                "ttl": item_ttl,
                "access_count": 0,
                "last_accessed": 0,
            }
            self._set_count += 1

    def delete(self, key: str) -> bool:
        """删除缓存条目，返回是否成功"""
        with self._lock:
            if key in self._store:
                del self._store[key]
                return True
            return False

    def clear(self) -> int:
        """清除所有缓存，返回清除的条目数"""
        with self._lock:
            count = len(self._store)
            self._store.clear()
            logger.info(f"MemoryCache: 清除 {count} 条缓存")
            return count

    def size(self) -> int:
        """当前缓存条目数"""
        with self._lock:
            return len(self._store)

    def keys(self) -> List[str]:
        """所有缓存键"""
        with self._lock:
            return list(self._store.keys())

    def stats(self) -> Dict[str, Any]:
        """缓存统计信息"""
        with self._lock:
            total_requests = self._hits + self._misses
            hit_rate = round(self._hits / total_requests * 100, 1) if total_requests > 0 else 0.0
            expired_count = sum(
                1 for e in self._store.values()
                if time.time() - e["created_at"] > e["ttl"]
            )
            return {
                "size": len(self._store),
                "max_items": self._max_items,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate_pct": hit_rate,
                "evictions": self._evictions,
                "set_count": self._set_count,
                "expired_count": expired_count,
                "strategy": self._eviction_strategy,
                "default_ttl": self._default_ttl,
            }

    def clean_expired(self) -> int:
        """清理过期条目，返回清理数量"""
        with self._lock:
            now = time.time()
            expired_keys = [
                k for k, v in self._store.items()
                if now - v["created_at"] > v["ttl"]
            ]
            for k in expired_keys:
                del self._store[k]
            if expired_keys:
                logger.debug(f"MemoryCache: 清理 {len(expired_keys)} 条过期缓存")
            return len(expired_keys)

    def _evict_one(self) -> None:
        """
        淘汰一个条目

        根据淘汰策略选择要移除的条目：
          - lru: 最久未访问
          - lfu: 最少访问
          - ttl: 最早过期
        """
        if not self._store:
            return

        if self._eviction_strategy == "lfu":
            key = min(self._store.items(), key=lambda x: x[1]["access_count"])[0]
        elif self._eviction_strategy == "ttl":
            key = min(
                self._store.items(),
                key=lambda x: x[1]["created_at"] + x[1]["ttl"],
            )[0]
        else:  # lru (默认)
            key = min(self._store.items(), key=lambda x: x[1]["last_accessed"])[0]

        del self._store[key]
        self._evictions += 1

    def get_or_compute(self, key: str, compute_func: Callable[[], Any],
                       ttl: Optional[int] = None) -> Any:
        """获取缓存，不存在则计算并缓存"""
        value = self.get(key)
        if value is not None:
            return value
        value = compute_func()
        self.set(key, value, ttl=ttl)
        return value


# ============================================================================
# 文件缓存
# ============================================================================


class FileCache:
    """
    持久化文件缓存

    每个缓存条目存储为独立的 JSON 文件，位于 cache/ 目录下。
    线程安全，支持 TTL 过期。

    Usage:
        cache = FileCache()
        cache.set("user_data", {"name": "李白"})
        data = cache.get("user_data")
    """

    def __init__(self, cache_dir: str = CACHE_DIR):
        self._lock = threading.RLock()
        self._cache_dir = cache_dir
        os.makedirs(self._cache_dir, exist_ok=True)
        logger.info(f"FileCache 初始化: dir={self._cache_dir}")

    def _key_to_filename(self, key: str) -> str:
        """将缓存键转为安全的文件名"""
        import hashlib
        safe = hashlib.md5(key.encode("utf-8")).hexdigest()
        return os.path.join(self._cache_dir, f"{safe}.json")

    def get(self, key: str) -> Optional[Any]:
        """读取缓存"""
        with self._lock:
            file_path = self._key_to_filename(key)
            if not os.path.exists(file_path):
                return None
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if time.time() - data.get("created_at", 0) > data.get("ttl", self._default_ttl()):
                    os.remove(file_path)
                    return None
                return data.get("value")
            except (json.JSONDecodeError, OSError) as e:
                logger.warning(f"FileCache: 读取失败 key={key}: {e}")
                return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """写入缓存"""
        with self._lock:
            file_path = self._key_to_filename(key)
            data = {
                "value": value,
                "created_at": time.time(),
                "ttl": ttl if ttl is not None else self._default_ttl(),
                "key": key,
            }
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

    def delete(self, key: str) -> bool:
        """删除缓存文件"""
        with self._lock:
            file_path = self._key_to_filename(key)
            if os.path.exists(file_path):
                os.remove(file_path)
                return True
            return False

    def clear(self) -> int:
        """清除所有缓存文件"""
        with self._lock:
            count = 0
            for f in os.listdir(self._cache_dir):
                if f.endswith(".json"):
                    try:
                        os.remove(os.path.join(self._cache_dir, f))
                        count += 1
                    except OSError:
                        pass
            logger.info(f"FileCache: 清除 {count} 个文件")
            return count

    def size(self) -> int:
        """缓存文件数量"""
        with self._lock:
            return len([f for f in os.listdir(self._cache_dir) if f.endswith(".json")])

    def total_size_bytes(self) -> int:
        """缓存总大小（字节）"""
        with self._lock:
            total = 0
            for f in os.listdir(self._cache_dir):
                if f.endswith(".json"):
                    total += os.path.getsize(os.path.join(self._cache_dir, f))
            return total

    def _default_ttl(self) -> int:
        return CACHE_DEFAULT_TTL

    def stats(self) -> Dict[str, Any]:
        """文件缓存统计"""
        return {
            "size": self.size(),
            "total_size_bytes": self.total_size_bytes(),
            "total_size_formatted": (
                f"{self.total_size_bytes() / (1024 * 1024):.2f} MB"
                if self.total_size_bytes() > 1024 * 1024
                else f"{self.total_size_bytes() / 1024:.2f} KB"
            ),
            "cache_directory": self._cache_dir,
        }


# ============================================================================
# 全局缓存实例
# ============================================================================


memory_cache = MemoryCache()
file_cache = FileCache()


# ============================================================================
# 缓存装饰器
# ============================================================================


def cached(backend: str = "memory", ttl: Optional[int] = None, key_prefix: str = ""):
    """
    缓存装饰器

    自动缓存函数返回值，缓存键基于模块名、函数名、参数生成。

    参数:
        backend: 缓存后端 ("memory" 或 "file")
        ttl: 过期时间（秒），None 使用默认值
        key_prefix: 缓存键前缀

    Usage:
        @cached(backend="memory", ttl=300)
        def expensive_computation(x, y):
            return x + y
    """
    def decorator(func: Callable):
        import functools

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if not CACHE_ENABLED:
                return func(*args, **kwargs)

            # 生成缓存键
            mod = func.__module__.split(".")[-1]
            arg_str = "_".join(str(a)[:50] for a in args)
            kw_str = "_".join(f"{k}={str(v)[:30]}" for k, v in sorted(kwargs.items()))
            cache_key = f"{key_prefix}{mod}:{func.__name__}:{arg_str}:{kw_str}"[:200]

            # 选择后端
            cache = memory_cache if backend == "memory" else file_cache

            # 尝试获取缓存
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                logger.debug(f"缓存命中: {cache_key[:80]}")
                return cached_value

            # 计算并缓存
            result = func(*args, **kwargs)
            cache.set(cache_key, result, ttl=ttl)
            logger.debug(f"缓存写入: {cache_key[:80]}")
            return result

        return wrapper
    return decorator


# ============================================================================
# 缓存管理函数
# ============================================================================


def clear_all_caches() -> Dict[str, int]:
    """清除所有缓存（内存+文件）"""
    mem_count = memory_cache.clear()
    file_count = file_cache.clear()
    return {"memory_cleared": mem_count, "file_cleared": file_count}


def get_all_cache_stats() -> Dict[str, Any]:
    """获取全部缓存统计"""
    return {
        "memory": memory_cache.stats(),
        "file": file_cache.stats(),
        "global_enabled": CACHE_ENABLED,
    }
