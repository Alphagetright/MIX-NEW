# -*- coding: utf-8 -*-
"""
古典诗词音韵格律分析引擎 — 分层异常体系
"""
from typing import Any, Dict, Optional


class AppError(Exception):
    """应用根异常"""

    def __init__(
        self,
        message: str,
        code: int = 1000,
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        self.cause = cause

    def to_dict(self) -> Dict[str, Any]:
        r = {
            "error": self.__class__.__name__,
            "message": self.message,
            "code": self.code,
        }
        if self.details:
            r["details"] = self.details
        if self.cause:
            r["cause"] = str(self.cause)
        return r

    def __str__(self):
        return f"[{self.code}] {self.message}"


# ─────────────────────────────────────────────
# 数据异常 (2000-2099)
# ─────────────────────────────────────────────


class DataError(AppError):
    def __init__(self, message, code=2000, **kwargs):
        super().__init__(message, code=code, status_code=400, **kwargs)


class PingshuiDBError(DataError):
    def __init__(self, message, **kwargs):
        super().__init__(message, code=2001, **kwargs)


class PoemDataError(DataError):
    def __init__(self, message, **kwargs):
        super().__init__(message, code=2002, **kwargs)


class PoemNotFoundError(PoemDataError):
    def __init__(self, message, **kwargs):
        super().__init__(message, code=2003, **kwargs)


class InvalidPoemFormatError(PoemDataError):
    def __init__(self, message, **kwargs):
        super().__init__(message, code=2004, **kwargs)


# ─────────────────────────────────────────────
# 分析异常 (3000-3099)
# ─────────────────────────────────────────────


class AnalysisError(AppError):
    def __init__(self, message, code=3000, **kwargs):
        super().__init__(message, code=code, status_code=422, **kwargs)


class PingzeError(AnalysisError):
    """平仄检测异常"""
    def __init__(self, message, **kwargs):
        super().__init__(message, code=3001, **kwargs)


class MeterError(AnalysisError):
    """格律检查异常"""
    def __init__(self, message, **kwargs):
        super().__init__(message, code=3002, **kwargs)


class RhymeError(AnalysisError):
    """韵脚分析异常"""
    def __init__(self, message, **kwargs):
        super().__init__(message, code=3003, **kwargs)


class DuizhangError(AnalysisError):
    """对仗检测异常"""
    def __init__(self, message, **kwargs):
        super().__init__(message, code=3004, **kwargs)


class ScansionError(AnalysisError):
    """格律扫描异常"""
    def __init__(self, message, **kwargs):
        super().__init__(message, code=3005, **kwargs)


class SimilarityError(AnalysisError):
    """相似度计算异常"""
    def __init__(self, message, **kwargs):
        super().__init__(message, code=3006, **kwargs)


class FormDetectionError(AnalysisError):
    """体裁检测异常"""
    def __init__(self, message, **kwargs):
        super().__init__(message, code=3007, **kwargs)


# ─────────────────────────────────────────────
# 文件系统异常 (4000-4099)
# ─────────────────────────────────────────────


class FileSystemError(AppError):
    def __init__(self, message, code=4000, **kwargs):
        super().__init__(message, code=code, status_code=500, **kwargs)


class FileNotFoundError2(FileSystemError):
    def __init__(self, message, **kwargs):
        super().__init__(message, code=4001, **kwargs)


class DirectoryNotFoundError(FileSystemError):
    def __init__(self, message, **kwargs):
        super().__init__(message, code=4002, **kwargs)


class FileReadError(FileSystemError):
    def __init__(self, message, **kwargs):
        super().__init__(message, code=4003, **kwargs)


# ─────────────────────────────────────────────
# 导出异常 (5000-5099)
# ─────────────────────────────────────────────


class ExportError(AppError):
    def __init__(self, message, code=5000, **kwargs):
        super().__init__(message, code=code, status_code=422, **kwargs)


class UnsupportedFormatError(ExportError):
    def __init__(self, message, **kwargs):
        super().__init__(message, code=5001, **kwargs)


# ─────────────────────────────────────────────
# 配置异常 (6000-6099)
# ─────────────────────────────────────────────


class ConfigError(AppError):
    def __init__(self, message, code=6000, **kwargs):
        super().__init__(message, code=code, status_code=500, **kwargs)


class InvalidConfigError(ConfigError):
    def __init__(self, message, **kwargs):
        super().__init__(message, code=6001, **kwargs)


# ─────────────────────────────────────────────
# 工具函数
# ─────────────────────────────────────────────


def safe_call(func, *args, default=None, error_msg="", **kwargs):
    try:
        return func(*args, **kwargs)
    except Exception:
        return default
