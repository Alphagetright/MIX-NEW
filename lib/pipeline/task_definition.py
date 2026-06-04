# -*- coding: utf-8 -*-
"""
Task definition module for pipeline orchestration.

Defines the data structures used to specify discrete units of work
including parameters, input file sets, output target specifications,
and complete task specifications that bind these together.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class TaskParam:
    """A named parameter with type information and optional default.

    Attributes:
        name: Parameter identifier.
        param_type: Expected type of the parameter value.
        default: Optional default value if not provided.
        description: Human-readable description of the parameter.
    """

    name: str
    param_type: type = str
    default: Any = None
    description: str = ""

    def has_default(self) -> bool:
        """Check whether this parameter has a default value."""
        return self.default is not None

    def validate(self, value: Any) -> bool:
        """Check if a value is compatible with the declared type."""
        if value is None and self.has_default():
            return True
        return isinstance(value, self.param_type)


@dataclass
class InputSet:
    """A collection of input files required by a task.

    Attributes:
        files: List of file paths (strings).
        base_path: Optional base directory for relative paths.
        description: Optional description of this input set.
    """

    files: List[str] = field(default_factory=list)
    base_path: str = ""
    description: str = ""

    def add_file(self, filepath: str) -> "InputSet":
        """Add a file path to the input set."""
        self.files.append(filepath)
        return self

    def resolve_paths(self) -> List[str]:
        """Resolve all paths relative to base_path if set."""
        if not self.base_path:
            return list(self.files)
        import os
        return [
            os.path.normpath(os.path.join(self.base_path, f))
            for f in self.files
        ]

    def __len__(self) -> int:
        return len(self.files)


@dataclass
class OutputTarget:
    """Specification of an output destination for a task.

    Attributes:
        path: Target file or directory path.
        format: Expected output format (e.g. "json", "csv", "binary").
        overwrite: Whether to overwrite an existing destination.
        description: Optional description of this output target.
    """

    path: str
    format: str = ""
    overwrite: bool = False
    description: str = ""


@dataclass
class TaskSpec:
    """A complete task specification combining all definition elements.

    Attributes:
        task_type: Discriminator for the kind of task.
        params: Key-value mapping of parameter names to values.
        inputs: InputSet describing required input files.
        outputs: List of OutputTarget destinations.
        config: Arbitrary additional configuration data.
        tags: Optional set of labels for filtering or grouping.
    """

    task_type: str = ""
    params: Dict[str, Any] = field(default_factory=dict)
    inputs: InputSet = field(default_factory=InputSet)
    outputs: List[OutputTarget] = field(default_factory=list)
    config: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)


@dataclass
class TaskDefinition:
    """High-level task definition combining a spec with runtime config.

    TaskDefinition binds a TaskSpec together with parameter defaults,
    configuration bindings, and validation logic.

    Attributes:
        name: Unique name for this task definition.
        spec: The underlying task specification.
        param_defs: List of formal parameter definitions.
        description: Human-readable description.
    """

    name: str
    spec: TaskSpec = field(default_factory=TaskSpec)
    param_defs: List[TaskParam] = field(default_factory=list)
    description: str = ""

    def bind_config(self, config: Dict[str, Any]) -> "TaskDefinition":
        """Bind a configuration dictionary, updating spec params."""
        self.spec.params.update(config)
        return self

    def validate_params(self) -> List[str]:
        """Validate all bound parameters against their definitions.

        Returns a list of validation error messages (empty if valid).
        """
        errors: List[str] = []
        for param_def in self.param_defs:
            value = self.spec.params.get(param_def.name)
            if value is None and not param_def.has_default():
                errors.append(f"Missing required parameter: {param_def.name}")
            elif value is not None and not param_def.validate(value):
                errors.append(
                    f"Parameter {param_def.name}: expected "
                    f"{param_def.param_type.__name__}, "
                    f"got {type(value).__name__}")
        return errors
