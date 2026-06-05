# -*- coding: utf-8 -*-
"""Batch writer with buffering, retry, and progress tracking."""

import os, time, threading
from typing import Any, Callable, Optional


class WriteProgress:
    """Track items written vs total with percentage."""

    def __init__(self, total: int) -> None:
        if total < 0:
            raise ValueError("Total must be non-negative")
        self.total = total
        self.written: int = 0

    @property
    def remaining(self) -> int:
        return max(0, self.total - self.written)

    @property
    def percentage(self) -> float:
        return (self.written / self.total * 100.0) if self.total else 100.0

    def advance(self, count: int = 1) -> None:
        self.written += count


class WriteBuffer:
    """Accumulate items and flush at threshold."""

    def __init__(self, threshold: int = 1000) -> None:
        if threshold < 1:
            raise ValueError("Threshold must be >= 1")
        self.threshold = threshold
        self._items: list[Any] = []

    @property
    def size(self) -> int:
        return len(self._items)

    @property
    def is_ready(self) -> bool:
        return self.size >= self.threshold

    def add(self, item: Any) -> None:
        self._items.append(item)

    def drain(self) -> list[Any]:
        items, self._items = self._items, []
        return items


class BatchWriteResult:
    """Outcome with succeeded, failed counts and error details."""

    def __init__(self) -> None:
        self.succeeded = 0
        self.failed = 0
        self.errors: list[tuple[int, str]] = []

    def record_success(self, count: int = 1) -> None:
        self.succeeded += count

    def record_failure(self, index: int, message: str) -> None:
        self.failed += 1
        self.errors.append((index, message))

    @property
    def total_attempted(self) -> int:
        return self.succeeded + self.failed

    @property
    def has_errors(self) -> bool:
        return self.failed > 0


class RetryWriter:
    """Exponential-backoff retry wrapper around a write callable."""

    def __init__(self, writer: Callable[[list[Any]], None],
                 max_retries: int = 3, base_delay: float = 0.5) -> None:
        self._writer = writer
        self.max_retries = max_retries
        self.base_delay = base_delay

    def write(self, items: list[Any]) -> None:
        last: Optional[Exception] = None
        for attempt in range(1, self.max_retries + 1):
            try:
                self._writer(items)
                return
            except (OSError, IOError) as exc:
                last = exc
                if attempt < self.max_retries:
                    time.sleep(self.base_delay * (2 ** (attempt - 1)))
        raise IOError(f"Write failed after {self.max_retries} retries") from last


class BatchWriter:
    """Thread-safe buffered writer with auto-flush, retry, and progress."""

    def __init__(self, write_fn: Callable[[list[Any]], None],
                 buffer_threshold: int = 1000, max_retries: int = 3) -> None:
        self._buffer = WriteBuffer(buffer_threshold)
        self._retry = RetryWriter(write_fn, max_retries=max_retries)
        self._lock = threading.Lock()
        self._progress: Optional[WriteProgress] = None
        self._result = BatchWriteResult()
        self._closed = False

    def set_total(self, total: int) -> None:
        self._progress = WriteProgress(total)

    @property
    def progress(self) -> Optional[WriteProgress]:
        return self._progress

    @property
    def result(self) -> BatchWriteResult:
        return self._result

    def write_one(self, item: Any) -> None:
        if self._closed:
            raise RuntimeError("BatchWriter is closed")
        with self._lock:
            self._buffer.add(item)
            if self._buffer.is_ready:
                self._flush()

    def _flush(self) -> None:
        items = self._buffer.drain()
        if not items:
            return
        try:
            self._retry.write(items)
            self._result.record_success(len(items))
            if self._progress:
                self._progress.advance(len(items))
        except IOError as exc:
            self._result.record_failure(0, str(exc))

    def flush(self) -> BatchWriteResult:
        with self._lock:
            self._flush()
        return self._result

    def close(self) -> BatchWriteResult:
        if self._closed:
            return self._result
        self._closed = True
        return self.flush()

    def __enter__(self) -> "BatchWriter":
        return self

    def __exit__(self, *exc_info: Any) -> None:
        self.close()
