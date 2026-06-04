# -*- coding: utf-8 -*-
"""
Type-checking utilities for the validation layer.

Provides recursive type checking, safe type conversion with fallback,
and a central registry of supported types.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple, Type, Union


# ---------------------------------------------------------------------------
# Type check result
# ---------------------------------------------------------------------------


class TypeCheckResult:
    """Outcome of a single type-check operation."""

    def __init__(
        self,
        is_valid: bool,
        expected: str,
        actual: str,
        path: str = "",
    ) -> None:
        self.is_valid = is_valid
        self.expected = expected
        self.actual = actual
        self.path = path

    @property
    def error_message(self) -> str:
        if self.is_valid:
            return ""
        return (
            f"Type mismatch at {self.path}: expected {self.expected}, "
            f"got {self.actual}"
        )

    def __bool__(self) -> bool:
        return self.is_valid

    def __repr__(self) -> str:
        status = "valid" if self.is_valid else "invalid"
        return f"<TypeCheckResult {status} at {self.path}>"


# ---------------------------------------------------------------------------
# Type registry
# ---------------------------------------------------------------------------


class TypeRegistry:
    """Maintains the set of types recognised by the type checker.

    Each entry maps a human-readable name to the corresponding Python type.
    """

    def __init__(self) -> None:
        self._types: Dict[str, Type] = {
            "str": str,
            "int": int,
            "float": float,
            "bool": bool,
            "list": list,
            "dict": dict,
            "bytes": bytes,
            "none": type(None),
        }

    def register(self, name: str, typ: Type) -> None:
        """Register a custom type under *name*."""
        self._types[name] = typ

    def resolve(self, name: str) -> Optional[Type]:
        """Return the Python type for the given *name*, or *None*."""
        return self._types.get(name)

    def names(self) -> List[str]:
        return list(self._types)

    def __contains__(self, name: str) -> bool:
        return name in self._types


# ---------------------------------------------------------------------------
# Core type checker
# ---------------------------------------------------------------------------


class TypeChecker:
    """Recursively checks that values conform to expected types.

    Supports nested structures::

        checker = TypeChecker()
        result = checker.check({"name": str, "scores": [float]}, value)
    """

    def __init__(self, registry: Optional[TypeRegistry] = None) -> None:
        self._registry = registry or TypeRegistry()

    def check(
        self,
        expected: Any,
        actual: Any,
        path: str = "$",
    ) -> TypeCheckResult:
        """Recursively check *actual* against *expected* type spec."""
        if isinstance(expected, dict):
            return self._check_dict(expected, actual, path)
        if isinstance(expected, list):
            return self._check_list(expected, actual, path)
        if isinstance(expected, type):
            return self._check_type(expected, actual, path)
        # expected is a string — look it up
        resolved = self._registry.resolve(str(expected))
        if resolved is not None:
            return self._check_type(resolved, actual, path)
        return TypeCheckResult(
            False, str(expected), type(actual).__name__, path
        )

    def _check_type(
        self, expected: Type, actual: Any, path: str
    ) -> TypeCheckResult:
        actual_type = type(actual)
        # Allow int where float is expected
        if expected is float and actual_type is int:
            return TypeCheckResult(True, "float", "int", path)
        valid = isinstance(actual, expected)
        if valid and expected is bool and actual_type is not bool:
            valid = False
        return TypeCheckResult(
            valid,
            expected.__name__,
            actual_type.__name__,
            path,
        )

    def _check_dict(
        self, expected: Dict[str, Any], actual: Any, path: str
    ) -> TypeCheckResult:
        if not isinstance(actual, dict):
            return TypeCheckResult(
                False, "dict", type(actual).__name__, path
            )
        for key, type_spec in expected.items():
            child_path = f"{path}.{key}"
            if key not in actual:
                return TypeCheckResult(
                    False, type_spec.__name__ if isinstance(type_spec, type) else str(type_spec),
                    "missing",
                    child_path,
                )
            child_result = self.check(type_spec, actual[key], child_path)
            if not child_result.is_valid:
                return child_result
        return TypeCheckResult(True, "dict", "dict", path)

    def _check_list(
        self, expected: List[Any], actual: Any, path: str
    ) -> TypeCheckResult:
        if not isinstance(actual, list):
            return TypeCheckResult(
                False, "list", type(actual).__name__, path
            )
        if not expected:
            return TypeCheckResult(True, "list", "list", path)
        elem_spec = expected[0]
        for idx, item in enumerate(actual):
            child_path = f"{path}[{idx}]"
            child_result = self.check(elem_spec, item, child_path)
            if not child_result.is_valid:
                return child_result
        return TypeCheckResult(True, "list", "list", path)


# ---------------------------------------------------------------------------
# Type converter
# ---------------------------------------------------------------------------


class TypeConverter:
    """Safely converts values between types with a fallback default."""

    def __init__(self, registry: Optional[TypeRegistry] = None) -> None:
        self._registry = registry or TypeRegistry()
        self._converters: Dict[Type, Callable[[Any], Any]] = {
            str: self._to_str,
            int: self._to_int,
            float: self._to_float,
            bool: self._to_bool,
        }

    def convert(
        self, value: Any, target_type: Union[str, Type], default: Any = None
    ) -> Any:
        """Convert *value* to *target_type*. Return *default* on failure."""
        typ = self._registry.resolve(target_type) if isinstance(target_type, str) else target_type
        if typ is None:
            return default
        if isinstance(value, typ):
            return value
        converter = self._converters.get(typ)
        if converter is None:
            return default
        try:
            return converter(value)
        except (ValueError, TypeError, OverflowError):
            return default

    @staticmethod
    def _to_str(v: Any) -> str:
        if isinstance(v, bytes):
            return v.decode("utf-8")
        return str(v)

    @staticmethod
    def _to_int(v: Any) -> int:
        if isinstance(v, float) and v != v:
            raise ValueError("Cannot convert NaN to int")
        if isinstance(v, str):
            return int(v.strip())
        return int(v)

    @staticmethod
    def _to_float(v: Any) -> float:
        if isinstance(v, str):
            return float(v.strip())
        return float(v)

    @staticmethod
    def _to_bool(v: Any) -> bool:
        if isinstance(v, str):
            return v.strip().lower() in ("true", "1", "yes")
        return bool(v)


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------

_DEFAULT_CHECKER = TypeChecker()
_DEFAULT_CONVERTER = TypeConverter()


def check_type(expected: Any, actual: Any, path: str = "$") -> TypeCheckResult:
    """Convenience: check *actual* against *expected* using the default checker."""
    return _DEFAULT_CHECKER.check(expected, actual, path)


def convert_type(
    value: Any, target_type: Union[str, Type], default: Any = None
) -> Any:
    """Convenience: convert *value* to *target_type* using the default converter."""
    return _DEFAULT_CONVERTER.convert(value, target_type, default)
