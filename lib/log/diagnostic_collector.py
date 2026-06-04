# -*- coding: utf-8 -*-
"""诊断信息收集 —— 运行时环境快照"""

import os
import sys
import platform
import time
import json


class DiagnosticCollector:
    """诊断信息收集器"""

    def __init__(self):
        self._snapshots = []

    def collect(self):
        info = {
            "timestamp": time.time(),
            "platform": {
                "system": platform.system(),
                "release": platform.release(),
                "version": platform.version(),
                "machine": platform.machine(),
                "processor": platform.processor(),
                "python_version": sys.version,
                "python_executable": sys.executable,
            },
            "environment": {
                "cwd": os.getcwd(),
                "pid": os.getpid(),
            },
            "paths": self._collect_paths(),
            "packages": self._collect_packages(),
        }
        self._snapshots.append(info)
        if len(self._snapshots) > 100:
            self._snapshots = self._snapshots[-100:]
        return info

    def _collect_paths(self):
        paths = {}
        for key in ["PATH", "PYTHONPATH", "HOME", "TEMP", "TMP"]:
            paths[key] = os.environ.get(key, "")
        return paths

    def _collect_packages(self):
        try:
            import pkg_resources
            packages = {}
            for pkg in pkg_resources.working_set:
                packages[pkg.key] = pkg.version
            return packages
        except Exception:
            return {}

    def get_latest(self):
        return self._snapshots[-1] if self._snapshots else None

    def summary(self):
        latest = self.get_latest()
        if not latest:
            return {"collected": False}
        return {
            "collected": True,
            "timestamp": latest["timestamp"],
            "python": latest["platform"]["python_version"].split()[0],
            "platform": f"{latest['platform']['system']} {latest['platform']['release']}",
            "pid": latest["environment"]["pid"],
            "cwd": latest["environment"]["cwd"],
        }

    def export_json(self, filepath):
        data = {
            "snapshots": self._snapshots,
            "summary": self.summary(),
            "count": len(self._snapshots),
        }
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
