# -*- coding: utf-8 -*-
"""
Pipeline metrics module for pipeline orchestration.

Provides facilities for collecting, aggregating, and reporting
execution metrics such as phase timing, throughput, success rates,
and resource utilisation across pipeline runs.
"""

import os
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class PipelineMetrics:
    """Aggregated metrics for a single or multi-run pipeline view.

    Attributes:
        pipeline_id: Identifier for the pipeline.
        stage_timings: Mapping of stage ID to list of durations (seconds).
        phase_timings: Named phase start/end timestamps.
        total_duration: Total duration of the pipeline run (seconds).
        success_count: Number of successful runs.
        failure_count: Number of failed runs.
        total_tasks: Number of tasks processed.
        throughput: Tasks per second.
    """

    pipeline_id: str = ""
    stage_timings: Dict[str, List[float]] = field(default_factory=lambda: defaultdict(list))
    phase_timings: Dict[str, float] = field(default_factory=dict)
    total_duration: float = 0.0
    success_count: int = 0
    failure_count: int = 0
    total_tasks: int = 0
    throughput: float = 0.0


class ResourceMonitor:
    """Tracks CPU and memory usage during pipeline execution.

    Provides periodic sampling of system resource utilisation
    that can be queried at any point during a run.
    """

    def __init__(self) -> None:
        self._samples: List[Dict[str, float]] = []

    def sample(self) -> Dict[str, float]:
        """Collect a single resource usage sample.

        Returns a dict with 'cpu_percent' and 'memory_mb' keys
        where available, or 0.0 if the data cannot be obtained.
        """
        sample: Dict[str, float] = {"cpu_percent": 0.0, "memory_mb": 0.0}
        try:
            import psutil
            sample["cpu_percent"] = psutil.cpu_percent(interval=0.1)
            proc = psutil.Process(os.getpid())
            sample["memory_mb"] = proc.memory_info().rss / (1024 * 1024)
        except (ImportError, AttributeError):
            sample["cpu_percent"] = self._fallback_cpu()
        self._samples.append(sample)
        return sample

    @staticmethod
    def _fallback_cpu() -> float:
        """Fallback CPU measurement when psutil is unavailable."""
        try:
            # Use os.times() as a basic CPU time measurement
            times = os.times()
            return times.user + times.system
        except AttributeError:
            return 0.0

    @property
    def samples(self) -> List[Dict[str, float]]:
        return list(self._samples)

    @property
    def avg_cpu(self) -> float:
        """Average CPU usage across all samples."""
        if not self._samples:
            return 0.0
        return sum(s["cpu_percent"] for s in self._samples) / len(self._samples)

    @property
    def avg_memory_mb(self) -> float:
        """Average memory usage across all samples."""
        if not self._samples:
            return 0.0
        valid = [s["memory_mb"] for s in self._samples if s["memory_mb"] > 0]
        return sum(valid) / len(valid) if valid else 0.0


class MetricsCollector:
    """Collects metrics during a pipeline run.

    Records stage-level timings, phase boundaries, and resource
    samples in a MetricsReport-ready format.
    """

    def __init__(self, pipeline_id: str = "") -> None:
        self._metrics = PipelineMetrics(pipeline_id=pipeline_id)
        self._phase_starts: Dict[str, float] = {}
        self._resource_monitor = ResourceMonitor()

    def start_phase(self, phase: str) -> None:
        """Record the start of a named phase."""
        self._phase_starts[phase] = time.time()

    def end_phase(self, phase: str) -> None:
        """Record the end of a named phase."""
        start = self._phase_starts.get(phase, time.time())
        duration = time.time() - start
        self._metrics.phase_timings[phase] = duration

    def record_stage(self, stage_id: str, duration: float) -> None:
        """Record timing for a single stage execution."""
        self._metrics.stage_timings[stage_id].append(duration)

    def record_success(self) -> None:
        """Increment the success counter."""
        self._metrics.success_count += 1

    def record_failure(self) -> None:
        """Increment the failure counter."""
        self._metrics.failure_count += 1

    def sample_resources(self) -> Dict[str, float]:
        """Take a resource usage sample."""
        return self._resource_monitor.sample()

    def finalise(self, duration: float,
                 total_tasks: int) -> PipelineMetrics:
        """Finalise metrics after a run completes."""
        self._metrics.total_duration = duration
        self._metrics.total_tasks = total_tasks
        self._metrics.throughput = (
            total_tasks / duration if duration > 0 else 0.0)
        return self._metrics


class MetricsAggregator:
    """Aggregates metrics from multiple pipeline runs.

    Combines individual PipelineMetrics instances into
    summary statistics with averages and totals.
    """

    def __init__(self) -> None:
        self._all_metrics: List[PipelineMetrics] = []

    def add(self, metrics: PipelineMetrics) -> None:
        """Add metrics from a single run."""
        self._all_metrics.append(metrics)

    def aggregate(self) -> Dict[str, Any]:
        """Compute aggregate statistics across all collected metrics.

        Returns a dict containing total runs, average duration,
        total tasks, average throughput, and success rate.
        """
        if not self._all_metrics:
            return {}
        total_runs = len(self._all_metrics)
        total_duration = sum(m.total_duration for m in self._all_metrics)
        total_tasks = sum(m.total_tasks for m in self._all_metrics)
        total_success = sum(m.success_count for m in self._all_metrics)
        total_failures = sum(m.failure_count for m in self._all_metrics)
        return {
            "total_runs": total_runs,
            "avg_duration": total_duration / total_runs if total_runs else 0.0,
            "total_tasks": total_tasks,
            "avg_throughput": total_tasks / total_duration if total_duration else 0.0,
            "success_rate": total_success / (total_success + total_failures)
                           if (total_success + total_failures) else 0.0,
        }


class MetricsReport:
    """Formats pipeline metrics into readable string output.

    Converts PipelineMetrics objects into human-readable report
    strings suitable for logging or console display.
    """

    def format(self, metrics: PipelineMetrics) -> str:
        """Produce a formatted report string from metrics data."""
        lines = [
            f"Pipeline Metrics: {metrics.pipeline_id}",
            f"  Duration: {metrics.total_duration:.2f}s",
            f"  Tasks: {metrics.total_tasks}",
            f"  Throughput: {metrics.throughput:.2f} tasks/s",
            f"  Successes: {metrics.success_count}",
            f"  Failures: {metrics.failure_count}",
        ]
        if metrics.stage_timings:
            lines.append("  Stage Timings:")
            for stage_id, timings in metrics.stage_timings.items():
                avg = sum(timings) / len(timings) if timings else 0.0
                lines.append(f"    {stage_id}: avg {avg:.3f}s "
                             f"({len(timings)} runs)")
        if metrics.phase_timings:
            lines.append("  Phase Timings:")
            for phase, duration in metrics.phase_timings.items():
                lines.append(f"    {phase}: {duration:.3f}s")
        return "\n".join(lines)
