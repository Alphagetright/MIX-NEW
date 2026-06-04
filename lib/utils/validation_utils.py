# -*- coding: utf-8 -*-
"""校验工具函数"""


def is_not_empty(value):
    return value is not None and value != ""


def is_length_in_range(value, min_len=0, max_len=None):
    if not isinstance(value, (str, list, tuple, dict)):
        return False
    if max_len is None:
        return len(value) >= min_len
    return min_len <= len(value) <= max_len


def matches_pattern(value, pattern):
    import re
    if not isinstance(value, str):
        return False
    return bool(re.match(pattern, value))


def is_in_range(value, min_val=None, max_val=None):
    if not isinstance(value, (int, float)):
        return False
    if min_val is not None and value < min_val:
        return False
    if max_val is not None and value > max_val:
        return False
    return True


def is_in_enum(value, enum_values):
    return value in enum_values


def is_type_of(value, expected_type):
    return isinstance(value, expected_type)


def is_valid_path(path):
    import os
    try:
        return os.path.exists(path)
    except Exception:
        return False


def is_valid_url(url):
    import re
    pattern = r"^https?://[^\s/$.?#].[^\s]*$"
    return bool(re.match(pattern, str(url)))


def validate_all(validators):
    errors = []
    for validator in validators:
        try:
            result = validator()
            if result and isinstance(result, str):
                errors.append(result)
        except Exception as e:
            errors.append(str(e))
    return errors


def validate_field(value, rules):
    errors = []
    for rule in rules:
        name = rule.get("name", "field")
        if rule.get("required") and value is None:
            errors.append(f"{name} is required")
            continue
        if value is None:
            continue
        if "type" in rule and not isinstance(value, rule["type"]):
            errors.append(f"{name} must be {rule['type'].__name__}")
        if "min_length" in rule and isinstance(value, (str, list)):
            if len(value) < rule["min_length"]:
                errors.append(f"{name} length < {rule['min_length']}")
        if "max_length" in rule and isinstance(value, (str, list)):
            if len(value) > rule["max_length"]:
                errors.append(f"{name} length > {rule['max_length']}")
        if "enum" in rule and value not in rule["enum"]:
            errors.append(f"{name} must be one of {rule['enum']}")
        if "pattern" in rule and isinstance(value, str):
            import re
            if not re.match(rule["pattern"], value):
                errors.append(f"{name} does not match pattern")
    return errors
