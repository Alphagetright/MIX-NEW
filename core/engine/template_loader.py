# -*- coding: utf-8 -*-
"""模板加载器 —— 多格式模板加载与解析"""

import os
import json


class TemplateFormatError(Exception):
    pass


class TemplateLoader:
    """模板加载器"""

    def __init__(self, templates_dir=None):
        self.templates_dir = templates_dir

    def set_templates_dir(self, path):
        self.templates_dir = path

    def load(self, template_name, format=None):
        if not self.templates_dir:
            raise TemplateFormatError("No templates directory configured")
        formats = format or self._detect_format(template_name)
        for fmt in formats if isinstance(formats, list) else [formats]:
            filepath = os.path.join(self.templates_dir, f"{template_name}.{fmt}")
            if os.path.exists(filepath):
                return self._load_file(filepath, fmt)
        raise TemplateFormatError(f"Template '{template_name}' not found in {self.templates_dir}")

    def _detect_format(self, template_name):
        return ["yaml", "yml", "json", "txt"]

    def _load_file(self, filepath, fmt):
        if fmt in ("yaml", "yml"):
            return self._load_yaml(filepath)
        elif fmt == "json":
            return self._load_json(filepath)
        else:
            return self._load_text(filepath)

    def _load_yaml(self, filepath):
        try:
            import yaml
            with open(filepath, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        except ImportError:
            return self._load_json(filepath.replace(".yaml", ".json").replace(".yml", ".json"))

    def _load_json(self, filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)

    def _load_text(self, filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()

    def list_templates(self):
        if not self.templates_dir or not os.path.isdir(self.templates_dir):
            return []
        templates = set()
        for fname in os.listdir(self.templates_dir):
            name, ext = os.path.splitext(fname)
            if ext in (".yaml", ".yml", ".json", ".txt"):
                templates.add(name)
        return sorted(templates)

    def template_info(self, template_name):
        try:
            content = self.load(template_name)
            return {
                "name": template_name,
                "type": type(content).__name__,
                "size": len(str(content)),
                "loaded": True,
            }
        except TemplateFormatError as e:
            return {"name": template_name, "loaded": False, "error": str(e)}
