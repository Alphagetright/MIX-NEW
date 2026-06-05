# -*- coding: utf-8 -*-
"""
Schema definition module for the validation layer.

Provides a type system with field specifications, constraints, and a
central registry for managing data schemas. All schema objects are
immutable once constructed.
"""

from __future__ import annotations

import copy
import re
from typing import Any, Callable, Dict, List, Optional, Sequence, Set, Tuple, Union


class SchemaValidationError(Exception):
    """Raised when a schema definition or validation fails."""

    def __init__(self, message: str, path: Optional[str] = None) -> None:
        self.path = path
        full = f"[{path}] {message}" if path else message
        super().__init__(full)


# ---------------------------------------------------------------------------
# Constraint hierarchy
# ---------------------------------------------------------------------------


class Constraint:
    """Base constraint. Subclasses implement a single *check* method."""

    def check(self, value: Any) -> Tuple[bool, str]:
        """Return (is_valid, reason_message)."""
        raise NotImplementedError

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}()"


class RangeConstraint(Constraint):
    """Numeric value must fall within [minimum, maximum]."""

    def __init__(
        self, minimum: Union[int, float], maximum: Union[int, float],
        inclusive: bool = True,
    ) -> None:
        if minimum > maximum:
            raise SchemaValidationError(
                f"RangeConstraint minimum ({minimum}) exceeds maximum ({maximum})"
            )
        self.minimum = minimum
        self.maximum = maximum
        self.inclusive = inclusive

    def check(self, value: Any) -> Tuple[bool, str]:
        if not isinstance(value, (int, float)):
            return False, f"Expected numeric, got {type(value).__name__}"
        if self.inclusive:
            ok = self.minimum <= value <= self.maximum
        else:
            ok = self.minimum < value < self.maximum
        bounds = f"[{self.minimum}, {self.maximum}]" if self.inclusive \
            else f"({self.minimum}, {self.maximum})"
        return ok, f"Value {value} out of range {bounds}"

    def __repr__(self) -> str:
        return f"RangeConstraint({self.minimum}, {self.maximum}, inclusive={self.inclusive})"


class LengthConstraint(Constraint):
    """String or sequence length must be within bounds."""

    def __init__(self, min_length: int = 0, max_length: Optional[int] = None) -> None:
        if min_length < 0:
            raise SchemaValidationError(f"min_length ({min_length}) must be >= 0")
        if max_length is not None and max_length < min_length:
            raise SchemaValidationError(
                f"max_length ({max_length}) < min_length ({min_length})"
            )
        self.min_length = min_length
        self.max_length = max_length

    def check(self, value: Any) -> Tuple[bool, str]:
        try:
            length = len(value)
        except TypeError:
            return False, f"Value has no len()"
        if length < self.min_length:
            return False, f"Length {length} < min {self.min_length}"
        if self.max_length is not None and length > self.max_length:
            return False, f"Length {length} > max {self.max_length}"
        return True, ""

    def __repr__(self) -> str:
        return f"LengthConstraint({self.min_length}, {self.max_length})"


class EnumConstraint(Constraint):
    """Value must be one of the allowed choices."""

    def __init__(self, allowed: Sequence[Any]) -> None:
        if not allowed:
            raise SchemaValidationError("EnumConstraint requires at least one value")
        self.allowed = tuple(allowed)

    def check(self, value: Any) -> Tuple[bool, str]:
        if value not in self.allowed:
            return False, f"Value {value!r} not in {self.allowed}"
        return True, ""

    def __repr__(self) -> str:
        return f"EnumConstraint({self.allowed})"


class PatternConstraint(Constraint):
    """String value must match a regular expression."""

    def __init__(self, pattern: str, flags: int = 0) -> None:
        self._compiled = re.compile(pattern, flags)
        self.pattern = pattern

    def check(self, value: Any) -> Tuple[bool, str]:
        if not isinstance(value, str):
            return False, f"Expected string, got {type(value).__name__}"
        if self._compiled.fullmatch(value) is None:
            return False, f"Value {value!r} does not match pattern {self.pattern!r}"
        return True, ""

    def __repr__(self) -> str:
        return f"PatternConstraint({self.pattern!r})"


# ---------------------------------------------------------------------------
# Field specification
# ---------------------------------------------------------------------------

TYPE_MAP = {
    "str": str,
    "int": int,
    "float": float,
    "bool": bool,
    "list": list,
    "dict": dict,
    "any": object,
}


class FieldSpec:
    """Describes a single field in a schema."""

    def __init__(
        self,
        name: str,
        field_type: Union[str, type],
        required: bool = True,
        default: Any = None,
        constraints: Optional[Sequence[Constraint]] = None,
        description: str = "",
    ) -> None:
        self.name = name
        self.type = TYPE_MAP.get(field_type, field_type) if isinstance(field_type, str) else field_type
        self.required = required
        self.default = default
        self.constraints = tuple(constraints) if constraints else ()
        self.description = description

    def validate(self, value: Any) -> List[str]:
        """Run all constraints against *value*. Return list of error messages."""
        errors: List[str] = []
        for c in self.constraints:
            ok, msg = c.check(value)
            if not ok:
                errors.append(f"{self.name}: {msg}")
        return errors

    def __repr__(self) -> str:
        return (
            f"FieldSpec({self.name!r}, {self.type.__name__}, "
            f"required={self.required})"
        )


# ---------------------------------------------------------------------------
# Schema definition and registry
# ---------------------------------------------------------------------------


class SchemaDefinition:
    """An ordered collection of FieldSpec objects describing a data record."""

    def __init__(self, name: str, fields: Sequence[FieldSpec]) -> None:
        if not name:
            raise SchemaValidationError("Schema name must not be empty")
        self.name = name
        self._fields: Dict[str, FieldSpec] = {}
        for f in fields:
            if f.name in self._fields:
                raise SchemaValidationError(f"Duplicate field name: {f.name}")
            self._fields[f.name] = f
        self._field_list = tuple(fields)

    @property
    def fields(self) -> Tuple[FieldSpec, ...]:
        return self._field_list

    def field(self, name: str) -> Optional[FieldSpec]:
        return self._fields.get(name)

    def field_names(self) -> List[str]:
        return [f.name for f in self._field_list]

    def required_fields(self) -> List[str]:
        return [f.name for f in self._field_list if f.required]

    def __repr__(self) -> str:
        return f"SchemaDefinition({self.name!r}, {len(self._field_list)} fields)"


class SchemaRegistry:
    """Central registry for looking up schemas by name."""

    def __init__(self) -> None:
        self._schemas: Dict[str, SchemaDefinition] = {}

    def register(self, schema: SchemaDefinition) -> None:
        if schema.name in self._schemas:
            raise SchemaValidationError(f"Schema '{schema.name}' already registered")
        self._schemas[schema.name] = schema

    def lookup(self, name: str) -> Optional[SchemaDefinition]:
        return self._schemas.get(name)

    def unregister(self, name: str) -> None:
        self._schemas.pop(name, None)

    def list_schemas(self) -> List[str]:
        return list(self._schemas)

    def __len__(self) -> int:
        return len(self._schemas)

    def __contains__(self, name: str) -> bool:
        return name in self._schemas
