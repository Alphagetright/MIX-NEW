# -*- coding: utf-8 -*-
"""文件校验 —— 存在性、可读性、完整性检查"""

import os


class FileValidator:
    """文件校验器"""

    def exists(self, filepath):
        return os.path.exists(filepath)

    def is_file(self, filepath):
        return os.path.isfile(filepath)

    def is_readable(self, filepath):
        return os.access(filepath, os.R_OK)

    def is_writable(self, filepath):
        parent = os.path.dirname(filepath) or "."
        return os.access(parent, os.W_OK)

    def check_size(self, filepath, max_bytes=None):
        if not os.path.exists(filepath):
            return False
        size = os.path.getsize(filepath)
        if max_bytes and size > max_bytes:
            return False
        return True

    def validate(self, filepath):
        issues = []
        if not self.exists(filepath):
            issues.append({"severity": "error", "message": f"File not found: {filepath}"})
            return {"valid": False, "issues": issues}
        if not self.is_file(filepath):
            issues.append({"severity": "error", "message": f"Not a file: {filepath}"})
        if not self.is_readable(filepath):
            issues.append({"severity": "error", "message": f"File not readable: {filepath}"})
        return {"valid": len(issues) == 0, "issues": issues}

    def batch_validate(self, filepaths):
        results = {}
        for fpath in filepaths:
            results[fpath] = self.validate(fpath)
        return {
            "total": len(filepaths),
            "valid": sum(1 for r in results.values() if r["valid"]),
            "invalid": sum(1 for r in results.values() if not r["valid"]),
            "results": results,
        }


class PathValidator:
    """路径校验器"""

    @staticmethod
    def is_absolute(path):
        return os.path.isabs(path)

    @staticmethod
    def is_relative(path):
        return not os.path.isabs(path)

    @staticmethod
    def is_safe(path):
        normalized = os.path.normpath(path)
        if ".." in normalized:
            return False
        if normalized.startswith("~"):
            return False
        return True

    @staticmethod
    def get_extension(path):
        return os.path.splitext(path)[1].lower()

    @staticmethod
    def is_valid_extension(path, allowed_extensions):
        return PathValidator.get_extension(path) in allowed_extensions
