# -*- coding: utf-8 -*-
"""
Progress tracker module for pipeline orchestration.

Provides real-time tracking of pipeline execution progress including
percentage completion, per-stage status, estimated time remaining,
and callback-based event notifications for progress display.
"""

import sys
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class ProgressState:
    """Snapshot of current pipeline progress.

    Attributes:
        total_stages: Number of stages in the pipeline.
        completed_stages: Number of stages completed.
        running_stage: Identifier of the currently running stage.
        failed_stages: Number of failed stages.
        skipped_stages: Number of skipped stages.
        percentage: Completion percentage (0.0 to 100.0).
        elapsed_seconds: Time elapsed since tracking started.
    """

    total_stages: int = 0
    completed_stages: int = 0
    running_stage: str = ""
    failed_stages: int = 0
    skipped_stages: int = 0
    percentage: float = 0.0
    elapsed_seconds: float = 0.0


class Estimator:
    """Estimates time remaining for pipeline completion.

    Uses a simple linear projection based on current completion
    rate to calculate estimated time of arrival.
    """

    def __init__(self) -> None:
        self._start_time: float = 0.0

    def start(self) -> None:
        """Mark the beginning of estimation."""
        self._start_time = time.time()

    def eta(self, completed: int, total: int) -> float:
        """Calculate estimated seconds remaining.

        Returns 0.0 if insufficient data is available.
        """
        if completed <= 0 or total <= 0:
            return 0.0
        elapsed = time.time() - self._start_time
        rate = completed / elapsed if elapsed > 0 else 0
        if rate <= 0:
            return 0.0
        remaining = total - completed
        return remaining / rate


class CallbackManager:
    """Manages and dispatches progress event callbacks.

    Supports registration of listeners for various progress events
    such as stage start, stage complete, and pipeline finish.
    """

    def __init__(self) -> None:
        self._callbacks: Dict[str, List[Callable[..., None]]] = {}

    def on(self, event: str, callback: Callable[..., None]) -> None:
        """Register a callback for a named event."""
        if event not in self._callbacks:
            self._callbacks[event] = []
        self._callbacks[event].append(callback)

    def emit(self, event: str, **kwargs: Any) -> None:
        """Dispatch an event to all registered callbacks."""
        for cb in self._callbacks.get(event, []):
            cb(**kwargs)

    def remove(self, event: str, callback: Callable[..., None]) -> None:
        """Unregister a specific callback from an event."""
        if event in self._callbacks:
            self._callbacks[event] = [
                cb for cb in self._callbacks[event] if cb is not callback
            ]


class ProgressBar:
    """Simple text-based progress bar for console output.

    Displays a visual progress indicator with percentage, elapsed
    time, and estimated time remaining.
    """

    def __init__(self, width: int = 40) -> None:
        self._width = width

    def render(self, state: ProgressState) -> str:
        """Render the progress bar as a string."""
        filled = int(self._width * state.percentage / 100.0)
        bar = "=" * filled + ">" + " " * (self._width - filled - 1)
        return (
            f"[{bar}] {state.percentage:.1f}% "
            f"({state.completed_stages}/{state.total_stages}) "
            f"[{state.elapsed_seconds:.1f}s]"
        )

    def display(self, state: ProgressState) -> None:
        """Write the progress bar to stderr and flush."""
        line = self.render(state)
        sys.stderr.write(f"\r{line}")
        sys.stderr.flush()


class ProgressTracker:
    """Tracks and reports pipeline execution progress.

    Combines a ProgressState, Estimator, CallbackManager, and
    ProgressBar to provide comprehensive progress tracking with
    event-driven notifications.
    """

    def __init__(self, total_stages: int) -> None:
        self._state = ProgressState(total_stages=total_stages)
        self._estimator = Estimator()
        self._callbacks = CallbackManager()
        self._bar = ProgressBar()
        self._stage_times: Dict[str, float] = {}

    def start(self) -> None:
        """Begin tracking progress."""
        self._estimator.start()
        self._callbacks.emit("pipeline_start", total=self._state.total_stages)

    def stage_started(self, stage_id: str) -> None:
        """Record that a stage has started execution."""
        self._state.running_stage = stage_id
        self._stage_times[stage_id] = time.time()
        self._callbacks.emit("stage_start", stage_id=stage_id)

    def stage_completed(self, stage_id: str) -> None:
        """Record that a stage has completed."""
        self._state.completed_stages += 1
        self._update_percentage()
        self._callbacks.emit("stage_complete", stage_id=stage_id,
                             elapsed=self._stage_times.get(stage_id, 0))
        self._display()

    def stage_failed(self, stage_id: str) -> None:
        """Record that a stage has failed."""
        self._state.failed_stages += 1
        self._update_percentage()
        self._callbacks.emit("stage_fail", stage_id=stage_id)
        self._display()

    def stage_skipped(self, stage_id: str) -> None:
        """Record that a stage has been skipped."""
        self._state.skipped_stages += 1
        self._state.completed_stages += 1
        self._update_percentage()
        self._callbacks.emit("stage_skip", stage_id=stage_id)

    def finish(self) -> ProgressState:
        """Mark tracking as complete and return final state."""
        self._state.elapsed_seconds = time.time() - self._estimator._start_time
        self._state.running_stage = ""
        self._callbacks.emit("pipeline_finish", state=self._state)
        return self._state

    def on(self, event: str, callback: Callable[..., None]) -> None:
        """Register a progress event callback."""
        self._callbacks.on(event, callback)

    def _update_percentage(self) -> None:
        """Recalculate the completion percentage."""
        if self._state.total_stages > 0:
            done = self._state.completed_stages
            self._state.percentage = (done / self._state.total_stages) * 100.0
        elapsed = time.time() - self._estimator._start_time
        self._state.elapsed_seconds = elapsed

    def _display(self) -> None:
        """Update the console progress display."""
        self._bar.display(self._state)

    @property
    def state(self) -> ProgressState:
        return self._state

    @property
    def eta(self) -> float:
        return self._estimator.eta(
            self._state.completed_stages, self._state.total_stages)
