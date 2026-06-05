# -*- coding: utf-8 -*-
"""配置序列化 —— 配置的导入/导出"""

import json
import os


class ConfigSerializer:
    """配置序列化器"""

    def __init__(self, indent=2):
        self.indent = indent

    def to_json(self, config, ensure_ascii=False):
        return json.dumps(config, ensure_ascii=ensure_ascii, indent=self.indent)

    def from_json(self, json_str):
        return json.loads(json_str)

    def to_file(self, config, filepath):
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=self.indent)

    def from_file(self, filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)


class ConfigExporter:
    """配置导出器"""

    def __init__(self, serializer=None):
        self.serializer = serializer or ConfigSerializer()

    def export_active(self, config_manager, export_path):
        config = config_manager.as_dict()
        self.serializer.to_file(config, export_path)
        return export_path

    def export_with_meta(self, config, export_path, meta=None):
        package = {
            "config": config,
            "meta": meta or {
                "exported_at": __import__("time").time(),
                "version": 1,
            },
        }
        self.serializer.to_file(package, export_path)
        return export_path


class ConfigImporter:
    """配置导入器"""

    def __init__(self, serializer=None):
        self.serializer = serializer or ConfigSerializer()

    def import_from_file(self, filepath):
        return self.serializer.from_file(filepath)

    def import_with_merge(self, filepath, target_config):
        imported = self.import_from_file(filepath)
        target_config.update(imported)
        return target_config
