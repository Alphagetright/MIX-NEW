# -*- coding: utf-8 -*-
"""
Stage definition module for pipeline orchestration.

Defines the core building blocks for pipeline stages including
input/output declarations, dependency descriptions, configuration
interfaces, and status tracking.
"""

import enum
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


class StageStatus(enum.Enum):
    """Enumeration of possible stage execution states."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class StageIO:
    """Input or output port definition for a pipeline stage.

    Attributes:
        name: Unique identifier for this port within the stage.
        description: Human-readable description of the port.
        required: Whether this port must be connected.
        data_type: Optional type hint for the port data.
    """

    name: str
    description: str = ""
    required: bool = True
    data_type: Optional[type] = None


@dataclass
class StageDependency:
    """Describes a dependency relationship between stages.

    Attributes:
        source_stage: Name of the stage this dependency targets.
        source_output: Specific output port from the source stage.
        target_input: Input port on this stage to receive data.
        optional: Whether this dependency may be absent.
    """

    source_stage: str
    source_output: str = ""
    target_input: str = ""
    optional: bool = False


@dataclass
class StageConfig:
    """Configuration interface for a pipeline stage.

    Provides a typed container for stage-level configuration
    parameters with optional defaults and validation hints.

    Attributes:
        params: Dictionary of configuration parameter names to values.
        allow_extra: Whether extra (unrecognised) params are permitted.
    """

    params: Dict[str, Any] = field(default_factory=dict)
    allow_extra: bool = False

    def get(self, key: str, default: Any = None) -> Any:
        """Retrieve a configuration value by key."""
        return self.params.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a configuration value by key."""
        self.params[key] = value

    def validate(self, known_keys: set) -> List[str]:
        """Validate configuration against a set of known keys.

        Returns a list of validation warning messages (empty if valid).
        """
        warnings: List[str] = []
        for key in self.params:
            if key not in known_keys and not self.allow_extra:
                warnings.append(f"Unknown configuration key: {key}")
        return warnings


@dataclass
class StageDefinition:
    """Complete specification of a pipeline stage.

    A StageDefinition describes what a stage does in terms of its
    inputs, outputs, dependencies, configuration interface, and
    execution semantics without providing the implementation itself.

    Attributes:
        name: Unique name for this stage within the pipeline.
        description: Human-readable description of the stage purpose.
        inputs: List of input port definitions.
        outputs: List of output port definitions.
        dependencies: List of dependency declarations.
        config: Stage-level configuration interface.
        timeout_seconds: Optional execution timeout.
    """

    name: str
    description: str = ""
    inputs: List[StageIO] = field(default_factory=list)
    outputs: List[StageIO] = field(default_factory=list)
    dependencies: List[StageDependency] = field(default_factory=list)
    config: StageConfig = field(default_factory=StageConfig)
    timeout_seconds: Optional[float] = None
    status: StageStatus = StageStatus.PENDING

    def add_input(self, name: str, description: str = "",
                  required: bool = True,
                  data_type: Optional[type] = None) -> "StageDefinition":
        """Add an input port to this stage definition."""
        self.inputs.append(StageIO(name, description, required, data_type))
        return self

    def add_output(self, name: str, description: str = "",
                   required: bool = True,
                   data_type: Optional[type] = None) -> "StageDefinition":
        """Add an output port to this stage definition."""
        self.outputs.append(StageIO(name, description, required, data_type))
        return self

    def add_dependency(self, source_stage: str,
                       source_output: str = "",
                       target_input: str = "",
                       optional: bool = False) -> "StageDefinition":
        """Add a dependency on another stage's output."""
        self.dependencies.append(
            StageDependency(source_stage, source_output,
                            target_input, optional))
        return self
