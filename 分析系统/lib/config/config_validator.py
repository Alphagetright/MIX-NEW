# -*- coding: utf-8 -*-
"""配置校验 —— 配置数据正确性检查"""


class ConfigValidator:
    """配置校验器"""

    def __init__(self):
        self._rules = []

    def add_rule(self, key, required=False, type=None, enum=None, min_val=None, max_val=None):
        self._rules.append({
            "key": key,
            "required": required,
            "type": type,
            "enum": enum,
            "min": min_val,
            "max": max_val,
        })

    def validate(self, config):
        errors = []
        accessor = _ConfigAccessor(config)

        for rule in self._rules:
            key = rule["key"]
            value = accessor.get(key)

            if rule["required"] and value is None:
                errors.append({"key": key, "message": f"Missing required config: {key}"})
                continue

            if value is None:
                continue

            if rule.get("type") and not isinstance(value, rule["type"]):
                errors.append({
                    "key": key,
                    "message": f"Expected {rule['type'].__name__}, got {type(value).__name__}",
                    "value": value,
                })
                continue

            if rule.get("enum") and value not in rule["enum"]:
                errors.append({
                    "key": key,
                    "message": f"Value must be one of {rule['enum']}, got {value}",
                })

            if rule.get("min") is not None and isinstance(value, (int, float)):
                if value < rule["min"]:
                    errors.append({
                        "key": key,
                        "message": f"Value {value} is less than minimum {rule['min']}",
                    })

            if rule.get("max") is not None and isinstance(value, (int, float)):
                if value > rule["max"]:
                    errors.append({
                        "key": key,
                        "message": f"Value {value} exceeds maximum {rule['max']}",
                    })

        return errors

    def is_valid(self, config):
        return len(self.validate(config)) == 0


class _ConfigAccessor:
    def __init__(self, data):
        self._data = data

    def get(self, key):
        keys = key.split(".")
        current = self._data
        for k in keys:
            if isinstance(current, dict) and k in current:
                current = current[k]
            else:
                return None
        return current


class ConfigValidationReport:
    """配置校验报告"""

    def __init__(self, errors=None, warnings=None):
        self.errors = errors or []
        self.warnings = warnings or []

    @property
    def has_errors(self):
        return len(self.errors) > 0

    @property
    def has_warnings(self):
        return len(self.warnings) > 0

    @property
    def is_passed(self):
        return not self.has_errors

    def summary(self):
        return {
            "errors": len(self.errors),
            "warnings": len(self.warnings),
            "error_details": self.errors[:5],
            "warning_details": self.warnings[:5],
        }

    def add_error(self, key, message):
        self.errors.append({"key": key, "message": message})

    def add_warning(self, key, message):
        self.warnings.append({"key": key, "message": message})

    def merge(self, other):
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)
