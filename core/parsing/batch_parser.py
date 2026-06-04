# -*- coding: utf-8 -*-
"""
Concurrent batch parsing with worker pool management,
result collection, and progress tracking.
"""

import threading
import time
from queue import Queue
from typing import Any, Callable, Dict, List, Optional, Tuple


class ProgressTracker:
    """Track progress of batch operations with percentage completion."""
    def __init__(self, total: int = 0) -> None:
        self.total = total
        self.completed = 0
        self._lock = threading.Lock()
        self._start_time: Optional[float] = None

    def start(self) -> None:
        self._start_time = time.monotonic()

    def increment(self, n: int = 1) -> None:
        with self._lock:
            self.completed += n

    @property
    def percentage(self) -> float:
        if self.total == 0:
            return 100.0
        with self._lock:
            return (self.completed / self.total) * 100.0

    @property
    def elapsed(self) -> float:
        return time.monotonic() - self._start_time if self._start_time else 0.0

    @property
    def remaining_estimate(self) -> float:
        rate = self.completed / self.elapsed if self.elapsed > 0 else 0.0
        remaining = self.total - self.completed
        return remaining / rate if rate > 0 else 0.0

    def summary(self) -> str:
        return f"{self.completed}/{self.total} ({self.percentage:.1f}%) elapsed={self.elapsed:.1f}s"


class BatchResult:
    """Results, errors, and statistics from a batch parse operation."""
    def __init__(self) -> None:
        self.results: List[Any] = []
        self.errors: List[Tuple[int, str]] = []
        self.stats: Dict[str, int] = {"total": 0, "succeeded": 0, "failed": 0}

    def add_result(self, result: Any) -> None:
        self.results.append(result)
        self.stats["succeeded"] += 1
        self.stats["total"] += 1

    def add_error(self, index: int, error: str) -> None:
        self.errors.append((index, error))
        self.stats["failed"] += 1
        self.stats["total"] += 1

    def merge(self, other: "BatchResult") -> None:
        self.results.extend(other.results)
        self.errors.extend(other.errors)
        for k in self.stats:
            self.stats[k] += other.stats.get(k, 0)

    @property
    def success_rate(self) -> float:
        return self.stats["succeeded"] / self.stats["total"] if self.stats["total"] > 0 else 1.0


class WorkerPool:
    """Manage a pool of worker threads for concurrent parsing."""
    def __init__(self, num_workers: int = 4) -> None:
        self._num_workers = num_workers
        self._work_queue: Queue = Queue()
        self._result_queue: Queue = Queue()
        self._workers: List[threading.Thread] = []
        self._running = False

    def start(self, worker_fn: Callable) -> None:
        self._running = True
        for _ in range(self._num_workers):
            thread = threading.Thread(target=self._worker_loop, args=(worker_fn,), daemon=True)
            thread.start()
            self._workers.append(thread)

    def _worker_loop(self, worker_fn: Callable) -> None:
        while self._running:
            try:
                item = self._work_queue.get(timeout=1.0)
            except Exception:
                continue
            if item is None:
                self._work_queue.task_done()
                break
            index, data = item
            try:
                self._result_queue.put((index, worker_fn(data), None))
            except Exception as exc:
                self._result_queue.put((index, None, str(exc)))
            finally:
                self._work_queue.task_done()

    def submit(self, index: int, data: Any) -> None:
        self._work_queue.put((index, data))

    def results(self) -> List[Tuple[int, Any, Optional[str]]]:
        collected: List[Tuple[int, Any, Optional[str]]] = []
        while not self._result_queue.empty():
            collected.append(self._result_queue.get_nowait())
        return sorted(collected, key=lambda x: x[0])

    def stop(self) -> None:
        self._running = False
        for _ in self._workers:
            self._work_queue.put(None)
        for w in self._workers:
            w.join(timeout=5.0)


class BatchParser:
    """Concurrent batch parser with progress tracking and result collection."""
    def __init__(self, parser_fn: Callable, num_workers: int = 4, worker_pool: Optional[WorkerPool] = None) -> None:
        self._parser_fn = parser_fn
        self._num_workers = num_workers
        self._pool = worker_pool or WorkerPool(num_workers)
        self._progress = ProgressTracker()

    def parse_all(self, items: List[Any]) -> BatchResult:
        batch_result = BatchResult()
        self._progress = ProgressTracker(total=len(items))
        self._progress.start()
        self._pool.start(self._parser_fn)
        for i, item in enumerate(items):
            self._pool.submit(i, item)
        self._pool.stop()
        for index, result, error in self._pool.results():
            if error:
                batch_result.add_error(index, error)
            else:
                batch_result.add_result(result)
            self._progress.increment()
        return batch_result

    def parse_stream(self, items: List[Any]) -> BatchResult:
        return self.parse_all(items)

    @property
    def progress(self) -> ProgressTracker:
        return self._progress
