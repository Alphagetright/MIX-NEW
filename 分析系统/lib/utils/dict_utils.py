# -*- coding: utf-8 -*-
"""字典工具函数"""


def deep_get(d, path, default=None):
    keys = path.split(".") if isinstance(path, str) else path
    current = d
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return default
    return current


def deep_set(d, path, value):
    keys = path.split(".") if isinstance(path, str) else path
    current = d
    for key in keys[:-1]:
        if key not in current:
            current[key] = {}
        current = current[key]
    current[keys[-1]] = value


def deep_merge(base, override):
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def filter_keys(d, keys):
    return {k: d[k] for k in keys if k in d}


def exclude_keys(d, keys):
    return {k: v for k, v in d.items() if k not in keys}


def pick(d, *keys):
    return {k: d[k] for k in keys if k in d}


def flatten(d, prefix="", separator="."):
    result = {}
    for key, value in d.items():
        full_key = f"{prefix}{separator}{key}" if prefix else key
        if isinstance(value, dict):
            result.update(flatten(value, full_key, separator))
        else:
            result[full_key] = value
    return result


def unflatten(d, separator="."):
    result = {}
    for key, value in d.items():
        parts = key.split(separator)
        current = result
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        current[parts[-1]] = value
    return result


def sort_by_key(d, reverse=False):
    return dict(sorted(d.items(), key=lambda x: x[0], reverse=reverse))


def sort_by_value(d, reverse=True):
    return dict(sorted(d.items(), key=lambda x: x[1], reverse=reverse))


def rename_key(d, old_key, new_key):
    if old_key in d:
        d[new_key] = d.pop(old_key)
    return d


class DefaultDict(dict):
    def __init__(self, default_factory=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.default_factory = default_factory

    def __getitem__(self, key):
        try:
            return super().__getitem__(key)
        except KeyError:
            if self.default_factory:
                val = self.default_factory()
                self[key] = val
                return val
            raise
