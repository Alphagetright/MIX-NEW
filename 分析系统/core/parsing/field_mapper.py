# -*- coding: utf-8 -*-
"""
Field mapping from source structures to target structures
with path resolution, type conversion, and defaults.
"""

from typing import Any, Callable, Dict, List, Optional


class PathResolver:
    """Resolve dotted path strings into nested dictionary values."""
    def __init__(self, delimiter: str = ".") -> None:
        self._delimiter = delimiter

    def resolve(self, data: Dict[str, Any], path: str) -> Any:
        keys = path.split(self._delimiter)
        current: Any = data
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            elif isinstance(current, (list, tuple)) and key.isdigit():
                idx = int(key)
                if 0 <= idx < len(current):
                    current = current[idx]
                else:
                    return None
            else:
                return None
        return current

    def set_value(self, data: Dict[str, Any], path: str, value: Any) -> None:
        keys = path.split(self._delimiter)
        current = data
        for key in keys[:-1]:
            current = current.setdefault(key, {})
        current[keys[-1]] = value


class TypeConverter:
    """Convert values between types with error handling."""
    def __init__(self, strict: bool = False) -> None:
        self._strict = strict

    def convert(self, value: Any, target_type: str) -> Any:
        if value is None:
            return None
        try:
            target = target_type.lower()
            if target == "str":
                return str(value)
            elif target == "int":
                return int(value) if not isinstance(value, bool) else int(value)
            elif target == "float":
                return float(value)
            elif target == "bool":
                if isinstance(value, str):
                    return value.strip().lower() in ("true", "1", "yes", "y")
                return bool(value)
            elif target == "list":
                return list(value) if isinstance(value, (list, tuple)) else [value]
            elif target == "dict":
                return value if isinstance(value, dict) else {}
            return value
        except (ValueError, TypeError, OverflowError):
            if self._strict:
                raise
            return None

    def safe_convert(self, value: Any, target_type: str, default: Any = None) -> Any:
        result = self.convert(value, target_type)
        return result if result is not None else default


class DefaultValueProvider:
    """Provide fallback values when a source field is missing or None."""
    def __init__(self, defaults: Optional[Dict[str, Any]] = None) -> None:
        self._defaults = defaults or {}

    def get(self, field: str, source_value: Any = None) -> Any:
        if source_value is not None:
            return source_value
        if field in self._defaults:
            default = self._defaults[field]
            return default() if callable(default) else default
        return None

    def register_default(self, field: str, value: Any) -> None:
        self._defaults[field] = value


class MappingRule:
    """A single mapping from source path to target path with transformation."""
    def __init__(self, source_path: str, target_path: str, default: Any = None,
                 transformer: Optional[Callable[[Any], Any]] = None, target_type: Optional[str] = None) -> None:
        self.source_path = source_path
        self.target_path = target_path
        self.default = default
        self.transformer = transformer
        self.target_type = target_type


class FieldMapper:
    """Map fields from source dicts to target dicts using configured rules."""
    def __init__(self, rules: Optional[List[MappingRule]] = None,
                 path_resolver: Optional[PathResolver] = None,
                 type_converter: Optional[TypeConverter] = None,
                 default_provider: Optional[DefaultValueProvider] = None) -> None:
        self._rules = rules or []
        self._path_resolver = path_resolver or PathResolver()
        self._type_converter = type_converter or TypeConverter()
        self._default_provider = default_provider or DefaultValueProvider()

    def add_rule(self, rule: MappingRule) -> None:
        self._rules.append(rule)

    def map(self, source: Dict[str, Any]) -> Dict[str, Any]:
        target: Dict[str, Any] = {}
        for rule in self._rules:
            value = self._path_resolver.resolve(source, rule.source_path)
            if value is None:
                value = self._default_provider.get(rule.target_path, rule.default)
            if rule.transformer:
                try:
                    value = rule.transformer(value)
                except Exception:
                    value = self._default_provider.get(rule.target_path, rule.default)
            if rule.target_type:
                value = self._type_converter.safe_convert(value, rule.target_type, rule.default)
            if value is not None:
                self._path_resolver.set_value(target, rule.target_path, value)
        return target

    def map_batch(self, sources: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return [self.map(src) for src in sources]

    def clear_rules(self) -> None:
        self._rules.clear()
