# -*- coding: utf-8 -*-
"""模板管理器 —— 多模板注册、版本管理、选择策略"""

import time


class TemplateRecord:
    """模板记录"""

    def __init__(self, template_id, content, version=1, metadata=None):
        self.template_id = template_id
        self.content = content
        self.version = version
        self.metadata = metadata or {}
        self.created_at = time.time()
        self.updated_at = time.time()

    def update(self, content, version=None):
        self.content = content
        if version:
            self.version = version
        else:
            self.version += 1
        self.updated_at = time.time()


class TemplateManager:
    """模板管理器"""

    def __init__(self, loader=None, renderer=None):
        self.loader = loader
        self.renderer = renderer
        self._templates = {}
        self._selection_strategies = {
            "latest": self._select_latest,
            "stable": self._select_stable,
        }
        self._active_strategy = "latest"

    def register(self, template_id, content, version=1, metadata=None):
        record = TemplateRecord(template_id, content, version, metadata)
        self._templates[template_id] = record
        return record

    def load_from_source(self, template_name):
        if not self.loader:
            raise ValueError("No loader configured")
        content = self.loader.load(template_name)
        return self.register(template_name, content)

    def get(self, template_id):
        record = self._templates.get(template_id)
        if not record:
            return None
        strategy = self._selection_strategies.get(self._active_strategy)
        if strategy:
            return strategy(record)
        return record.content

    def render(self, template_id, variables):
        template = self.get(template_id)
        if template is None:
            raise ValueError(f"Template not found: {template_id}")
        if self.renderer:
            return self.renderer.render(template, variables)
        return template

    def set_strategy(self, strategy_name):
        if strategy_name in self._selection_strategies:
            self._active_strategy = strategy_name

    def _select_latest(self, record):
        return record.content

    def _select_stable(self, record):
        if record.metadata.get("stable"):
            return record.content
        return record.content

    def list_templates(self):
        return {tid: {"version": r.version, "age": time.time() - r.created_at} for tid, r in self._templates.items()}

    def remove(self, template_id):
        return self._templates.pop(template_id, None) is not None

    def reload_all(self):
        count = 0
        for template_id in list(self._templates.keys()):
            try:
                self.load_from_source(template_id)
                count += 1
            except Exception:
                pass
        return count
