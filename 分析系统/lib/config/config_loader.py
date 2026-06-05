# -*- coding: utf-8 -*-
"""配置加载器 —— 多源合并与优先级控制"""

from .config_source import (
    DefaultConfigSource, FileConfigSource, EnvConfigSource,
    CLIConfigSource, DictConfigSource,
)


class ConfigLoader:
    """配置加载器 —— 多源合并、优先级控制"""

    def __init__(self):
        self._sources = []

    def add_source(self, source):
        self._sources.append(source)
        self._sources.sort(key=lambda s: s.priority)
        return self

    def add_defaults(self, defaults):
        self.add_source(DefaultConfigSource(defaults))
        return self

    def add_file(self, filepath, format=None):
        self.add_source(FileConfigSource(filepath, format))
        return self

    def add_env(self, prefix="AP_"):
        self.add_source(EnvConfigSource(prefix))
        return self

    def add_cli_args(self, args):
        self.add_source(CLIConfigSource(args))
        return self

    def load(self):
        result = {}
        for source in self._sources:
            try:
                data = source.read()
                self._deep_merge(result, data)
            except Exception:
                pass
        return result

    def load_file(self, filepath, format=None):
        source = FileConfigSource(filepath, format)
        return source.read()

    def _deep_merge(self, base, override):
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value

    def clear(self):
        self._sources.clear()


class ConfigAccessor:
    """配置访问器 —— 带默认值的嵌套访问"""

    def __init__(self, config_data):
        self._data = config_data

    def get(self, key, default=None):
        keys = key.split(".")
        current = self._data
        for k in keys:
            if isinstance(current, dict) and k in current:
                current = current[k]
            else:
                return default
        return current

    def set(self, key, value):
        keys = key.split(".")
        current = self._data
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]
        current[keys[-1]] = value

    def has(self, key):
        return self.get(key, _MISSING) is not _MISSING

    def as_dict(self):
        return dict(self._data)

    def flatten(self, prefix=""):
        result = {}
        for key, value in self._data.items():
            full_key = f"{prefix}.{key}" if prefix else key
            if isinstance(value, dict):
                result.update(self._flatten(value, full_key))
            else:
                result[full_key] = value
        return result

    @staticmethod
    def _flatten(data, prefix=""):
        result = {}
        for key, value in data.items():
            full_key = f"{prefix}.{key}" if prefix else key
            if isinstance(value, dict):
                result.update(ConfigAccessor._flatten(value, full_key))
            else:
                result[full_key] = value
        return result


_MISSING = object()


config_loader = ConfigLoader()
config_loader.add_env("AP_")
