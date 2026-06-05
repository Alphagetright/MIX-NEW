# -*- coding: utf-8 -*-
"""配置源 —— 多来源配置读取"""

import os
import json
import configparser


class ConfigSource:
    """配置源基类"""

    def read(self):
        raise NotImplementedError

    @property
    def priority(self):
        return 0


class DefaultConfigSource(ConfigSource):
    """默认配置源"""

    def __init__(self, defaults=None):
        self._defaults = defaults or {}

    def read(self):
        return dict(self._defaults)

    @property
    def priority(self):
        return 0


class FileConfigSource(ConfigSource):
    """文件配置源"""

    def __init__(self, filepath, format=None):
        self.filepath = filepath
        self._format = format or self._detect_format(filepath)

    def _detect_format(self, filepath):
        ext = os.path.splitext(filepath)[1].lower()
        return {"json": "json", "ini": "ini", "cfg": "ini", "conf": "ini"}.get(ext, "json")

    def read(self):
        if not os.path.exists(self.filepath):
            return {}
        try:
            if self._format == "json":
                with open(self.filepath, "r", encoding="utf-8") as f:
                    return json.load(f)
            elif self._format == "ini":
                parser = configparser.ConfigParser()
                parser.read(self.filepath, encoding="utf-8")
                result = {}
                for section in parser.sections():
                    result[section] = dict(parser[section])
                return result
        except Exception:
            pass
        return {}

    @property
    def priority(self):
        return 10


class EnvConfigSource(ConfigSource):
    """环境变量配置源"""

    def __init__(self, prefix="AP_", separator="__"):
        self.prefix = prefix
        self.separator = separator

    def read(self):
        result = {}
        prefix = self.prefix.lower()
        for key, value in sorted(os.environ.items()):
            if key.lower().startswith(prefix):
                config_key = key[len(prefix):].lower()
                result[config_key] = self._cast_value(value)
        return result

    def _cast_value(self, value):
        if value.lower() in ("true", "yes", "1"):
            return True
        if value.lower() in ("false", "no", "0"):
            return False
        if value.lower() == "none":
            return None
        try:
            return int(value)
        except ValueError:
            pass
        try:
            return float(value)
        except ValueError:
            pass
        return value

    @property
    def priority(self):
        return 20


class CLIConfigSource(ConfigSource):
    """命令行参数配置源"""

    def __init__(self, args=None):
        self._args = args or {}

    def read(self):
        return dict(self._args)

    @property
    def priority(self):
        return 30


class DictConfigSource(ConfigSource):
    """字典配置源"""

    def __init__(self, data, priority=15):
        self._data = data
        self._priority = priority

    def read(self):
        return dict(self._data)

    @property
    def priority(self):
        return self._priority
