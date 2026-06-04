# -*- coding: utf-8 -*-
"""
Checkpoint store module for pipeline orchestration.

Provides mechanisms for serialising pipeline execution state to
checkpoint files, restoring from checkpoints, and verifying the
integrity and consistency of persisted state.
"""

import hashlib
import json
import os
import threading
import time
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


@dataclass
class Checkpoint:
    """A snapshot of pipeline execution state at a point in time.

    Attributes:
        pipeline_id: Identifier of the pipeline being checkpointed.
        stage_statuses: Mapping of stage IDs to their status strings.
        stage_results: Mapping of stage IDs to their output data.
        context_metadata: Arbitrary metadata from the run context.
        timestamp: Unix timestamp when this checkpoint was created.
        version: Checkpoint format version for forward compatibility.
    """

    pipeline_id: str
    stage_statuses: Dict[str, str] = field(default_factory=dict)
    stage_results: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    context_metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = 0.0
    version: int = 1


class ConsistencyCheck:
    """Verifies the integrity and internal consistency of a checkpoint.

    Performs structural validation, hash verification, and semantic
    consistency checks on checkpoint data.
    """

    def __init__(self, checkpoint: Checkpoint) -> None:
        self._checkpoint = checkpoint
        self._errors: List[str] = []
        self._warnings: List[str] = []

    def run(self) -> bool:
        """Execute all consistency checks. Returns True if all pass."""
        self._errors.clear()
        self._warnings.clear()
        self._check_structure()
        self._check_timestamps()
        self._check_status_consistency()
        return len(self._errors) == 0

    def _check_structure(self) -> None:
        """Validate that required fields are present and well-typed."""
        if not self._checkpoint.pipeline_id:
            self._errors.append("Checkpoint missing pipeline_id")
        if not isinstance(self._checkpoint.stage_statuses, dict):
            self._errors.append("stage_statuses must be a dict")
        if not isinstance(self._checkpoint.timestamp, (int, float)):
            self._errors.append("timestamp must be numeric")

    def _check_timestamps(self) -> None:
        """Warn if the timestamp is in the future or too far in the past."""
        now = time.time()
        if self._checkpoint.timestamp > now + 10:
            self._warnings.append("Checkpoint timestamp is in the future")
        if self._checkpoint.timestamp > 0 and now - self._checkpoint.timestamp > 86400 * 7:
            self._warnings.append("Checkpoint is more than one week old")

    def _check_status_consistency(self) -> None:
        """Warn if completed stages have no results stored."""
        valid_statuses = {"pending", "running", "completed", "failed", "skipped"}
        for stage_id, status in self._checkpoint.stage_statuses.items():
            if status not in valid_statuses:
                self._warnings.append(f"Unknown status '{status}' for {stage_id}")
            if status == "completed" and stage_id not in self._checkpoint.stage_results:
                self._warnings.append(
                    f"Stage {stage_id} completed but has no results")

    @property
    def errors(self) -> List[str]:
        return list(self._errors)

    @property
    def warnings(self) -> List[str]:
        return list(self._warnings)


class CheckpointWriter:
    """Serialises a Checkpoint to a file with integrity metadata."""

    def __init__(self, directory: str) -> None:
        self._directory = directory
        os.makedirs(directory, exist_ok=True)

    def write(self, checkpoint: Checkpoint) -> str:
        """Write checkpoint to a JSON file. Returns the file path."""
        checkpoint.timestamp = checkpoint.timestamp or time.time()
        data = asdict(checkpoint)
        data["_integrity"] = self._compute_hash(data)
        filename = f"checkpoint_{checkpoint.pipeline_id}_{int(time.time())}.json"
        filepath = os.path.join(self._directory, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)
        return filepath

    @staticmethod
    def _compute_hash(data: Dict[str, Any]) -> str:
        """Compute a SHA-256 hash over the serialisable content."""
        raw = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class CheckpointReader:
    """Deserialises a Checkpoint from a file with integrity verification."""

    def read(self, filepath: str) -> Optional[Checkpoint]:
        """Read and verify a checkpoint file. Returns None on failure."""
        if not os.path.isfile(filepath):
            return None
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, IOError):
            return None

        integrity = data.pop("_integrity", "")
        if integrity:
            expected = CheckpointWriter._compute_hash(data)
            if integrity != expected:
                return None

        return Checkpoint(
            pipeline_id=data.get("pipeline_id", ""),
            stage_statuses=data.get("stage_statuses", {}),
            stage_results=data.get("stage_results", {}),
            context_metadata=data.get("context_metadata", {}),
            timestamp=data.get("timestamp", 0.0),
            version=data.get("version", 1),
        )


class CheckpointStore:
    """Manages checkpoint lifecycle: create, persist, load, and verify.

    Provides a thread-safe interface for saving snapshots of pipeline
    state and restoring from the most recent valid checkpoint.
    """

    def __init__(self, directory: str) -> None:
        self._writer = CheckpointWriter(directory)
        self._reader = CheckpointReader()
        self._lock = threading.Lock()

    def save(self, checkpoint: Checkpoint) -> str:
        """Persist a checkpoint to disk. Returns the file path."""
        with self._lock:
            return self._writer.write(checkpoint)

    def load(self, filepath: str) -> Optional[Checkpoint]:
        """Load a checkpoint from a specific file path."""
        with self._lock:
            checkpoint = self._reader.read(filepath)
            if checkpoint and ConsistencyCheck(checkpoint).run():
                return checkpoint
        return None

    def latest(self, pipeline_id: str) -> Optional[Checkpoint]:
        """Find and load the most recent checkpoint for a pipeline."""
        pattern = f"checkpoint_{pipeline_id}_"
        candidates: List[tuple] = []
        for name in os.listdir(self._writer._directory):
            if name.startswith(pattern) and name.endswith(".json"):
                path = os.path.join(self._writer._directory, name)
                candidates.append((os.path.getmtime(path), path))
        if not candidates:
            return None
        candidates.sort(reverse=True)
        return self.load(candidates[0][1])
