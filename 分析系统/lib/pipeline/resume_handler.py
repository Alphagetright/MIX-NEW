# -*- coding: utf-8 -*-
"""
Resume handler module for pipeline orchestration.

Provides functionality for detecting existing checkpoints, collecting
partial results from previous runs, and determining which stages can
be skipped during a resumed pipeline execution.
"""

import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from pipeline.checkpoint_store import Checkpoint, CheckpointStore
from pipeline.stage_definition import StageStatus


class ResumeStrategy(Enum):
    """Strategy for resuming a pipeline execution.

    Attributes:
        FULL_RESUME: Restore all state and skip completed stages.
        PARTIAL_RESUME: Restore state but re-execute all stages.
        DRY_RUN: Load checkpoint but do not execute any stage.
    """

    FULL_RESUME = "full_resume"
    PARTIAL_RESUME = "partial_resume"
    DRY_RUN = "dry_run"


@dataclass
class ResumePlan:
    """Describes the plan for resuming execution.

    Attributes:
        strategy: The chosen resume strategy.
        checkpoint: The loaded checkpoint, if any.
        stages_to_skip: Set of stages that can be safely skipped.
        partial_results: Results recovered from the checkpoint.
        warnings: Diagnostic warnings about the resume.
    """

    strategy: ResumeStrategy
    checkpoint: Optional[Checkpoint] = None
    stages_to_skip: Set[str] = field(default_factory=set)
    partial_results: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)


class CheckpointDetector:
    """Searches for the latest valid checkpoint for a given pipeline."""

    def __init__(self, store: CheckpointStore) -> None:
        self._store = store

    def detect(self, pipeline_id: str) -> Optional[Checkpoint]:
        """Find the most recent valid checkpoint for a pipeline."""
        return self._store.latest(pipeline_id)

    def list_checkpoints(self, pipeline_id: str) -> List[str]:
        """List all checkpoint file paths for a given pipeline."""
        pattern = f"checkpoint_{pipeline_id}_"
        directory = ""
        candidates: List[str] = []
        for name in os.listdir("."):
            if name.startswith(pattern) and name.endswith(".json"):
                candidates.append(name)
        return candidates


class ResultCollector:
    """Collects partial results from a previous checkpoint."""

    def collect(self, checkpoint: Checkpoint) -> Dict[str, Dict[str, Any]]:
        """Extract stage results from a checkpoint."""
        return dict(checkpoint.stage_results)


class CompletedChecker:
    """Determines which stages are fully completed from a checkpoint."""

    def check(self, checkpoint: Checkpoint) -> Set[str]:
        """Identify stages whose status is 'completed'."""
        return {
            stage_id
            for stage_id, status in checkpoint.stage_statuses.items()
            if status == StageStatus.COMPLETED.value
        }


class ResumeHandler:
    """Coordinates the detection and application of resume checkpoints.

    Given a pipeline identifier and a resume strategy, the handler
    finds the most recent checkpoint, validates it, and produces
    a ResumePlan describing which stages to skip and what partial
    results are available.
    """

    def __init__(self, store: CheckpointStore) -> None:
        self._store = store
        self._detector = CheckpointDetector(store)
        self._collector = ResultCollector()
        self._checker = CompletedChecker()

    def build_plan(self, pipeline_id: str,
                   strategy: ResumeStrategy = ResumeStrategy.FULL_RESUME
                   ) -> ResumePlan:
        """Build a resume plan for the given pipeline.

        Args:
            pipeline_id: Identifies which pipeline to resume.
            strategy: The resume strategy to apply.

        Returns:
            A fully populated ResumePlan with skip sets and warnings.
        """
        plan = ResumePlan(strategy=strategy)

        checkpoint = self._detector.detect(pipeline_id)
        if checkpoint is None:
            plan.warnings.append(f"No checkpoint found for {pipeline_id}")
            return plan

        plan.checkpoint = checkpoint
        plan.partial_results = self._collector.collect(checkpoint)

        if strategy == ResumeStrategy.DRY_RUN:
            plan.warnings.append("Dry-run mode: no stages will execute")
            return plan

        if strategy in (ResumeStrategy.FULL_RESUME,
                        ResumeStrategy.PARTIAL_RESUME):
            completed = self._checker.check(checkpoint)
            if strategy == ResumeStrategy.FULL_RESUME:
                plan.stages_to_skip = completed
                plan.warnings.append(
                    f"Skipping {len(completed)} completed stage(s)")
            else:
                plan.warnings.append(
                    "Partial resume: will re-execute all stages "
                    "using previous results as input")

        return plan

    def can_resume(self, pipeline_id: str) -> bool:
        """Quick check if a resume-able checkpoint exists."""
        return self._detector.detect(pipeline_id) is not None
