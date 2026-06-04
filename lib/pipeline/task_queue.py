# -*- coding: utf-8 -*-
"""
Task queue module for pipeline orchestration.

Provides multiple queue implementations (FIFO, priority, LIFO) with
optional disk persistence and concurrency control for managing
concurrent task execution.
"""

import json
import os
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from heapq import heappop, heappush
from typing import Any, Callable, Dict, List, Optional, Tuple


class QueueType(Enum):
    """Supported queue ordering strategies."""
    FIFO = "fifo"
    PRIORITY = "priority"
    LIFO = "lifo"


@dataclass(order=True)
class QueueItem:
    """An item in the task queue with priority metadata.

    Attributes:
        priority: Numeric priority (lower value = higher priority).
        enqueue_time: Timestamp when the item was enqueued.
        task_id: Unique identifier for the task.
        payload: Optional arbitrary data associated with the task.
    """

    priority: int
    enqueue_time: float
    task_id: str
    payload: Any = field(default=None, compare=False)


class PriorityQueue:
    """Heap-based priority queue for task scheduling.

    Supports push, pop, and optional LIFO ordering for tasks
    with equal priority.
    """

    def __init__(self) -> None:
        self._heap: List[Tuple[int, float, str, Any]] = []
        self._counter: int = 0

    def push(self, item: QueueItem) -> None:
        """Enqueue an item with its associated priority."""
        entry = (item.priority, item.enqueue_time, item.task_id, item.payload)
        heappush(self._heap, entry)

    def pop(self) -> Optional[QueueItem]:
        """Dequeue the highest-priority item."""
        if not self._heap:
            return None
        priority, enq_time, task_id, payload = heappop(self._heap)
        return QueueItem(priority, enq_time, task_id, payload)

    def peek(self) -> Optional[QueueItem]:
        """Return the highest-priority item without removing it."""
        if not self._heap:
            return None
        priority, enq_time, task_id, payload = self._heap[0]
        return QueueItem(priority, enq_time, task_id, payload)

    def __len__(self) -> int:
        return len(self._heap)

    def clear(self) -> None:
        """Remove all items from the queue."""
        self._heap.clear()


class PersistentQueue:
    """Queue wrapper that persists items to disk as JSON.

    On initialization, previously persisted items are reloaded.
    Each mutation triggers a save to the backing file.
    """

    def __init__(self, filepath: str) -> None:
        self._filepath = filepath
        self._queue = PriorityQueue()
        self._lock = threading.Lock()
        self._load()

    def push(self, item: QueueItem) -> None:
        """Enqueue an item and persist."""
        with self._lock:
            self._queue.push(item)
            self._save()

    def pop(self) -> Optional[QueueItem]:
        """Dequeue an item and persist the change."""
        with self._lock:
            item = self._queue.pop()
            if item:
                self._save()
            return item

    def _load(self) -> None:
        """Load persisted items from disk."""
        if not os.path.isfile(self._filepath):
            return
        try:
            with open(self._filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            for entry in data:
                item = QueueItem(
                    priority=entry["priority"],
                    enqueue_time=entry["enqueue_time"],
                    task_id=entry["task_id"],
                    payload=entry.get("payload"),
                )
                self._queue.push(item)
        except (json.JSONDecodeError, KeyError):
            pass

    def _save(self) -> None:
        """Write all items to disk as JSON."""
        items = []
        q = PriorityQueue()
        while len(self._queue) > 0:
            item = self._queue.pop()
            if item:
                items.append(item)
                q.push(item)
        self._queue = q
        with open(self._filepath, "w", encoding="utf-8") as f:
            json.dump([
                {"priority": it.priority,
                 "enqueue_time": it.enqueue_time,
                 "task_id": it.task_id,
                 "payload": it.payload}
                for it in items
            ], f, default=str)

    @property
    def filepath(self) -> str:
        return self._filepath


class ConcurrencyController:
    """Limits the number of concurrently executing tasks.

    Uses a semaphore to cap concurrency and provides hooks for
    tracking active task counts.
    """

    def __init__(self, max_concurrent: int = 1) -> None:
        if max_concurrent < 1:
            raise ValueError("max_concurrent must be at least 1")
        self._max_concurrent = max_concurrent
        self._semaphore = threading.Semaphore(max_concurrent)
        self._active_count: int = 0

    def acquire(self, timeout: Optional[float] = None) -> bool:
        """Acquire a concurrency slot. Returns True if acquired."""
        acquired = self._semaphore.acquire(blocking=True,
                                           timeout=timeout)
        if acquired:
            self._active_count += 1
        return acquired

    def release(self) -> None:
        """Release a concurrency slot."""
        self._active_count -= 1
        self._semaphore.release()

    @property
    def max_concurrent(self) -> int:
        return self._max_concurrent

    @property
    def active_count(self) -> int:
        return self._active_count


class TaskQueue:
    """High-level task queue with configurable ordering and concurrency.

    Combines a PriorityQueue with a ConcurrencyController and
    optional disk persistence.
    """

    def __init__(self,
                 queue_type: QueueType = QueueType.FIFO,
                 max_concurrent: int = 1,
                 persist_path: Optional[str] = None) -> None:
        self._queue_type = queue_type
        self._persistent = (
            PersistentQueue(persist_path) if persist_path else None)
        self._concurrency = ConcurrencyController(max_concurrent)
        self._internal: List[QueueItem] = []

    def enqueue(self, item: QueueItem) -> None:
        """Add an item to the queue."""
        if self._persistent:
            self._persistent.push(item)
        else:
            self._internal.append(item)

    def dequeue(self) -> Optional[QueueItem]:
        """Remove and return the next item per queue ordering."""
        if self._persistent:
            return self._persistent.pop()
        if not self._internal:
            return None
        if self._queue_type == QueueType.PRIORITY:
            self._internal.sort(key=lambda x: (x.priority, x.enqueue_time))
            return self._internal.pop(0)
        if self._queue_type == QueueType.LIFO:
            return self._internal.pop()
        return self._internal.pop(0)  # FIFO

    def acquire_slot(self) -> bool:
        """Block until a concurrency slot is available."""
        return self._concurrency.acquire()

    def release_slot(self) -> None:
        """Release a concurrency slot."""
        self._concurrency.release()

    @property
    def active_count(self) -> int:
        return self._concurrency.active_count

    def __len__(self) -> int:
        if self._persistent:
            return len(self._persistent._queue)
        return len(self._internal)
