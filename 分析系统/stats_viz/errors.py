# -*- coding: utf-8 -*-
"""分层异常体系"""

from typing import Any, Dict, Optional


class AppError(Exception):
    """应用基础异常"""

    def __init__(self, message: str, code: int = 1000, status_code: int = 500,
                 details: Optional[Dict[str, Any]] = None, cause: Optional[Exception] = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        self.cause = cause

    def to_dict(self) -> Dict[str, Any]:
        result = {"error": self.__class__.__name__, "message": self.message,
                  "code": self.code, "status_code": self.status_code}
        if self.details:
            result["details"] = self.details
        if self.cause:
            result["cause"] = str(self.cause)
        return result


class DataError(AppError):
    """数据层异常"""
    def __init__(self, message: str, code: int = 2000, **kwargs):
        super().__init__(message, code=code, status_code=400, **kwargs)


class DataNotFoundError(DataError):
    def __init__(self, message: str = "数据未找到", **kwargs):
        super().__init__(message, code=2001, status_code=404, **kwargs)


class DataValidationError(DataError):
    def __init__(self, message: str = "数据校验失败", **kwargs):
        super().__init__(message, code=2002, **kwargs)


class DataFormatError(DataError):
    def __init__(self, message: str = "数据格式错误", **kwargs):
        super().__init__(message, code=2003, **kwargs)


class FileSystemError(AppError):
    """文件系统异常"""
    def __init__(self, message: str, code: int = 3000, file_path: str = "", **kwargs):
        details = kwargs.pop("details", {})
        if file_path:
            details["file_path"] = file_path
        super().__init__(message, code=code, status_code=500, details=details, **kwargs)


class FileNotFoundError2(FileSystemError):
    def __init__(self, file_path: str = "", **kwargs):
        msg = f"文件未找到: {file_path}" if file_path else "文件未找到"
        super().__init__(msg, code=3001, file_path=file_path, status_code=404, **kwargs)


class ExportError(AppError):
    """导出异常"""
    def __init__(self, message: str, code: int = 5000, **kwargs):
        super().__init__(message, code=code, status_code=500, **kwargs)


class ExportFormatError(ExportError):
    def __init__(self, fmt: str = "", **kwargs):
        msg = f"不支持的导出格式: {fmt}" if fmt else "不支持的导出格式"
        super().__init__(msg, code=5001, details={"format": fmt}, **kwargs)


class StatsError(AppError):
    """统计异常"""
    def __init__(self, message: str, code: int = 8000, **kwargs):
        super().__init__(message, code=code, status_code=500, **kwargs)


def safe_call(func, *args, default=None, **kwargs):
    """安全调用函数，异常时返回默认值"""
    try:
        return func(*args, **kwargs)
    except Exception:
        return default
