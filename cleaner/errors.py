# -*- coding: utf-8 -*-
"""分层异常体系"""
from typing import Any, Dict, Optional


class AppError(Exception):
    def __init__(self, message: str, code: int = 1000, status_code: int = 500,
                 details: Optional[Dict[str, Any]] = None, cause: Optional[Exception] = None):
        super().__init__(message)
        self.message = message; self.code = code; self.status_code = status_code
        self.details = details or {}; self.cause = cause

    def to_dict(self) -> Dict[str, Any]:
        r = {"error": self.__class__.__name__, "message": self.message,
             "code": self.code, "status_code": self.status_code}
        if self.details: r["details"] = self.details
        if self.cause: r["cause"] = str(self.cause)
        return r


class DataError(AppError):
    def __init__(self, message: str, code: int = 2000, **kwargs):
        super().__init__(message, code=code, status_code=400, **kwargs)


class DataValidationError(DataError):
    def __init__(self, message: str = "数据校验失败", **kwargs):
        super().__init__(message, code=2001, **kwargs)


class DataFormatError(DataError):
    def __init__(self, message: str = "数据格式错误", **kwargs):
        super().__init__(message, code=2002, **kwargs)


class EncodingError(AppError):
    def __init__(self, message: str = "编码错误", encoding: str = "", **kwargs):
        super().__init__(message, code=3000, details={"encoding": encoding}, **kwargs)


class FileSystemError(AppError):
    def __init__(self, message: str, code: int = 4000, file_path: str = "", **kwargs):
        d = kwargs.pop("details", {}); d["file_path"] = file_path
        super().__init__(message, code=code, status_code=500, details=d, **kwargs)


class FileNotFoundError2(FileSystemError):
    def __init__(self, file_path: str = "", **kwargs):
        super().__init__(f"文件未找到: {file_path}" if file_path else "文件未找到",
                         code=4001, file_path=file_path, status_code=404, **kwargs)


class BatchError(AppError):
    def __init__(self, message: str, code: int = 5000, **kwargs):
        super().__init__(message, code=code, status_code=500, **kwargs)


class BatchPartialFailureError(BatchError):
    def __init__(self, total: int = 0, failed: int = 0, **kwargs):
        super().__init__(f"批处理部分失败: {failed}/{total}", code=5001,
                         details={"total": total, "failed": failed}, **kwargs)


def safe_call(func, *args, default=None, **kwargs):
    try: return func(*args, **kwargs)
    except Exception: return default
