# -*- coding: utf-8 -*-
"""
Pipeline runner module.

Orchestrates the execution of a built pipeline by scheduling stages
according to the topological order, managing an execution context,
passing results between stages, and propagating errors to dependents.
"""

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set

from pipeline.stage_definition import StageStatus
from pipeline.pipeline_builder import BuildResult


@dataclass
class RunnerStats:
    """Execution statistics collected during a pipeline run.

    Attributes:
        total_stages: Number of stages in the pipeline.
        completed: Number of stages completed successfully.
        failed: Number of stages that failed.
        skipped: Number of stages skipped.
        start_time: Timestamp when the run started.
        end_time: Timestamp when the run ended.
        duration_seconds: Total run duration.
    """

    total_stages: int = 0
    completed: int = 0
    failed: int = 0
    skipped: int = 0
    start_time: float = 0.0
    end_time: float = 0.0
    duration_seconds: float = 0.0


class RunContext:
    """Shared context available to all stages during pipeline execution.

    Stores intermediate results, configuration, and metadata accessible
    by stage executors.
    """

    def __init__(self) -> None:
        self._results: Dict[str, Dict[str, Any]] = {}
        self._metadata: Dict[str, Any] = {}

    def set_result(self, stage_id: str, output_port: str,
                   value: Any) -> None:
        """Store a result produced by a stage output port."""
        if stage_id not in self._results:
            self._results[stage_id] = {}
        self._results[stage_id][output_port] = value

    def get_result(self, stage_id: str,
                   output_port: str = "") -> Any:
        """Retrieve a result from a stage output port."""
        if output_port:
            return self._results.get(stage_id, {}).get(output_port)
        return self._results.get(stage_id)

    def set_metadata(self, key: str, value: Any) -> None:
        """Set a metadata value in the shared context."""
        self._metadata[key] = value

    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Get a metadata value from the shared context."""
        return self._metadata.get(key, default)


class ErrorPropagator:
    """Propagates failure information to dependent stages.

    When a stage fails, this component marks all downstream stages
    that depend on its outputs as skipped.
    """

    def __init__(self, build_result: BuildResult) -> None:
        self._graph = build_result.graph
        self._order = build_result.order
        self._failed: Set[str] = set()

    def mark_failed(self, stage_id: str) -> None:
        """Record a stage as failed and cascade the failure downstream."""
        self._failed.add(stage_id)

    def is_affected(self, stage_id: str) -> bool:
        """Check if a stage depends transitively on any failed stage."""
        visited: Set[str] = set()
        stack = [stage_id]
        while stack:
            current = stack.pop()
            if current in visited:
                continue
            visited.add(current)
            if current in self._failed:
                return True
            for source, targets in self._graph.edges.items():
                if current in targets:
                    stack.append(source)
        return False

    @property
    def failed_stages(self) -> Set[str]:
        return set(self._failed)


class StageExecutor:
    """Executes an individual pipeline stage.

    Wraps a callable that receives the run context and is expected
    to return output data.
    """

    def __init__(self,
                 handler: Optional[Callable[..., Any]] = None,
                 timeout: Optional[float] = None) -> None:
        self._handler = handler
        self._timeout = timeout

    def execute(self, stage_id: str,
                context: RunContext) -> Dict[str, Any]:
        """Invoke the stage handler and return its outputs.

        Raises RuntimeError if the handler fails or timeouts occur.
        """
        if self._handler is None:
            raise RuntimeError(f"No handler registered for stage {stage_id}")

        start = time.monotonic()
        try:
            result = self._handler(context)
            elapsed = time.monotonic() - start
            if self._timeout and elapsed > self._timeout:
                raise RuntimeError(
                    f"Stage {stage_id} timed out after {elapsed:.2f}s")
            if result is None:
                return {}
            if isinstance(result, dict):
                return result
            return {"default": result}
        except Exception as exc:
            raise RuntimeError(
                f"Stage {stage_id} failed: {exc}") from exc


class PipelineRunner:
    """Orchestrates the full execution of a pipeline.

    Schedules stages in topological order, provides a shared context,
    delegates execution to StageExecutor instances, and handles error
    propagation across dependent stages.
    """

    def __init__(self, build_result: BuildResult) -> None:
        self._build_result = build_result
        self._executors: Dict[str, StageExecutor] = {}
        self._context = RunContext()
        self._error_propagator = ErrorPropagator(build_result)
        self._stats = RunnerStats(
            total_stages=len(build_result.order))
        self._stage_statuses: Dict[str, StageStatus] = {}

    def register_executor(self, stage_id: str,
                          executor: StageExecutor) -> "PipelineRunner":
        """Associate an executor with a stage."""
        self._executors[stage_id] = executor
        return self

    def run(self) -> RunnerStats:
        """Execute all stages in topological order.

        Returns RunnerStats with summary information about the run.
        """
        self._stats.start_time = time.time()

        for stage_id in self._build_result.order:
            if self._error_propagator.is_affected(stage_id):
                self._stage_statuses[stage_id] = StageStatus.SKIPPED
                self._stats.skipped += 1
                continue

            executor = self._executors.get(stage_id)
            if executor is None:
                self._stage_statuses[stage_id] = StageStatus.SKIPPED
                self._stats.skipped += 1
                continue

            self._stage_statuses[stage_id] = StageStatus.RUNNING
            try:
                outputs = executor.execute(stage_id, self._context)
                for port, value in outputs.items():
                    self._context.set_result(stage_id, port, value)
                self._stage_statuses[stage_id] = StageStatus.COMPLETED
                self._stats.completed += 1
            except RuntimeError:
                self._stage_statuses[stage_id] = StageStatus.FAILED
                self._error_propagator.mark_failed(stage_id)
                self._stats.failed += 1

        self._stats.end_time = time.time()
        self._stats.duration_seconds = (
            self._stats.end_time - self._stats.start_time)
        return self._stats

    @property
    def context(self) -> RunContext:
        return self._context

    @property
    def stage_statuses(self) -> Dict[str, StageStatus]:
        return dict(self._stage_statuses)

    @property
    def stats(self) -> RunnerStats:
        return self._stats
