# -*- coding: utf-8 -*-
"""预处理管线编排器"""


class PreprocessingStep:
    """预处理步骤基类"""

    def __init__(self, name, enabled=True):
        self.name = name
        self.enabled = enabled

    def process(self, data, context=None):
        return data

    def __repr__(self):
        return f"Step({self.name}, enabled={self.enabled})"


class PreprocessingPipeline:
    """预处理管线"""

    def __init__(self):
        self._steps = []

    def add_step(self, step):
        self._steps.append(step)
        return self

    def insert_step(self, index, step):
        self._steps.insert(index, step)
        return self

    def remove_step(self, name):
        self._steps = [s for s in self._steps if s.name != name]
        return self

    def enable_step(self, name):
        for step in self._steps:
            if step.name == name:
                step.enabled = True
        return self

    def disable_step(self, name):
        for step in self._steps:
            if step.name == name:
                step.enabled = False
        return self

    def run(self, data, context=None):
        results = []
        for step in self._steps:
            if not step.enabled:
                continue
            try:
                data = step.process(data, context)
                results.append({"step": step.name, "success": True})
            except Exception as e:
                results.append({"step": step.name, "success": False, "error": str(e)})
                raise
        return {
            "data": data,
            "results": results,
            "steps_run": len(results),
            "all_success": all(r["success"] for r in results),
        }

    def dry_run(self, data, context=None):
        results = []
        current = data
        for step in self._steps:
            if not step.enabled:
                results.append({"step": step.name, "status": "skipped"})
                continue
            try:
                original = current
                current = step.process(current, context)
                results.append({"step": step.name, "status": "ok", "input_size": len(str(original)), "output_size": len(str(current))})
            except Exception as e:
                results.append({"step": step.name, "status": "error", "error": str(e)})
                current = original
        return {"steps": results, "final_size": len(str(current)), "changes": [r for r in results if r.get("status") == "ok"]}

    def list_steps(self):
        return [{"name": s.name, "enabled": s.enabled} for s in self._steps]

    @property
    def step_count(self):
        return len(self._steps)

    @property
    def enabled_count(self):
        return sum(1 for s in self._steps if s.enabled)
