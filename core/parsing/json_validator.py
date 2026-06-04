# -*- coding: utf-8 -*-
"""
JSON structural validation, type checking, and schema conformance.
"""

from typing import Any, Dict, List, Optional


class ValidationResult:
    """Captures validation outcome with success flag, errors, and warnings."""
    def __init__(self) -> None:
        self.success: bool = True
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self._field_errors: Dict[str, List[str]] = {}

    def add_error(self, message: str, field: Optional[str] = None) -> None:
        self.errors.append(message)
        self.success = False
        if field:
            self._field_errors.setdefault(field, []).append(message)

    def add_warning(self, message: str) -> None:
        self.warnings.append(message)

    def merge(self, other: "ValidationResult", prefix: str = "") -> None:
        if not other.success:
            self.success = False
        for err in other.errors:
            self.errors.append(f"{prefix}: {err}" if prefix else err)
        for warn in other.warnings:
            self.warnings.append(f"{prefix}: {warn}" if prefix else warn)

    def has_field_errors(self, field: str) -> bool:
        return field in self._field_errors

    @property
    def is_valid(self) -> bool:
        return self.success and len(self.errors) == 0


class FieldValidator:
    """Per-field type and constraint validation."""
    _TYPE_MAP = {"str": str, "int": int, "float": float, "bool": bool, "list": list, "dict": dict, "any": object}

    def __init__(self, allow_none: bool = False) -> None:
        self._allow_none = allow_none

    def validate(self, value: Any, expected_type: str, field_name: str) -> ValidationResult:
        result = ValidationResult()
        py_type = self._TYPE_MAP.get(expected_type, object)
        if value is None:
            if not self._allow_none:
                result.add_error(f"Field '{field_name}' is None but None is not allowed", field=field_name)
            return result
        if not isinstance(value, py_type):
            result.add_error(f"Field '{field_name}' expected {expected_type}, got {type(value).__name__}", field=field_name)
        return result

    def validate_strict(self, value: Any, expected_type: type, field_name: str) -> ValidationResult:
        result = ValidationResult()
        if value is None:
            return result
        if type(value) is not expected_type:
            result.add_error(f"Field '{field_name}' expected strict {expected_type.__name__}, got {type(value).__name__}", field=field_name)
        return result


class SchemaValidator:
    """Validate JSON data against a schema dictionary."""
    def __init__(self, schema: Dict[str, Any], field_validator: Optional[FieldValidator] = None) -> None:
        self._schema = schema
        self._field_validator = field_validator or FieldValidator()

    def validate(self, data: Dict[str, Any]) -> ValidationResult:
        result = ValidationResult()
        self._validate_dict(data, self._schema, result, "")
        return result

    def _validate_dict(self, data: Dict[str, Any], schema: Dict[str, Any], result: ValidationResult, path: str) -> None:
        for key, rules in schema.items():
            full_path = f"{path}.{key}" if path else key
            if key not in data:
                if rules.get("required", False):
                    result.add_error(f"Missing required field '{full_path}'", field=full_path)
                continue
            value = data[key]
            expected = rules.get("type")
            if expected:
                result.merge(self._field_validator.validate(value, expected, full_path))
            nested = rules.get("schema")
            if nested and isinstance(value, dict):
                self._validate_dict(value, nested, result, full_path)
            items_rules = rules.get("items")
            if items_rules and isinstance(value, list):
                for i, item in enumerate(value):
                    item_path = f"{full_path}[{i}]"
                    if isinstance(item, dict) and "schema" in items_rules:
                        self._validate_dict(item, items_rules["schema"], result, item_path)


class NestedValidation:
    """Recursive validation for deeply nested JSON structures."""
    def __init__(self, schema_validator: Optional[SchemaValidator] = None) -> None:
        self._schema_validator = schema_validator

    def validate(self, data: Any, schema: Optional[Dict[str, Any]] = None, path: str = "$") -> ValidationResult:
        result = ValidationResult()
        if schema and isinstance(data, dict):
            validator = self._schema_validator or SchemaValidator(schema)
            result.merge(validator.validate(data))
        result.merge(self._recurse(data, schema or {}, path))
        return result

    def _recurse(self, data: Any, schema: Dict[str, Any], path: str) -> ValidationResult:
        result = ValidationResult()
        if isinstance(data, dict):
            for key, value in data.items():
                child_path = f"{path}.{key}"
                result.merge(self._recurse(value, schema, child_path))
                if isinstance(value, dict):
                    child_schema = schema.get(key, {}) if isinstance(schema, dict) else {}
                    if isinstance(child_schema, dict) and "schema" in child_schema:
                        result.merge(SchemaValidator(child_schema["schema"]).validate(value))
        elif isinstance(data, list):
            for i, item in enumerate(data):
                result.merge(self._recurse(item, schema, f"{path}[{i}]"))
        return result


class JsonValidator:
    """Top-level validator combining schema, field, and nested validation."""
    def __init__(self, schema: Optional[Dict[str, Any]] = None, field_validator: Optional[FieldValidator] = None) -> None:
        self._schema = schema
        self._field_validator = field_validator or FieldValidator()
        self._schema_validator = SchemaValidator(schema or {}, field_validator)
        self._nested_validator = NestedValidation(self._schema_validator)

    def validate(self, data: Dict[str, Any]) -> ValidationResult:
        result = ValidationResult()
        if self._schema:
            result.merge(self._schema_validator.validate(data))
        result.merge(self._nested_validator.validate(data, self._schema))
        return result
