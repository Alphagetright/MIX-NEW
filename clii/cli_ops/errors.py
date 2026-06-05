# -*- coding: utf-8 -*-
"""
分层异常体系
============
定义系统的异常层次结构，每种异常关联HTTP状态码和错误码。
支持异常序列化、错误链追踪、批量错误聚合。
"""

import traceback
from typing import Any, Dict, List, Optional


# ============================================================================
# 错误码定义
# ============================================================================

class ErrorCode:
    """应用级错误码常量"""
    # 通用错误 1000-1099
    UNKNOWN = 1000
    CONFIG_ERROR = 1001
    PERMISSION_DENIED = 1002
    RATE_LIMITED = 1003

    # 数据错误 2000-2099
    DATA_NOT_FOUND = 2000
    DATA_FORMAT_ERROR = 2001
    DATA_VALIDATION_ERROR = 2002
    DATA_INTEGRITY_ERROR = 2003
    DATA_DUPLICATE = 2004
    DATA_TOO_LARGE = 2005

    # 文件系统错误 3000-3099
    FILE_NOT_FOUND = 3000
    FILE_READ_ERROR = 3001
    FILE_WRITE_ERROR = 3002
    FILE_PERMISSION_ERROR = 3003
    FILE_FORMAT_ERROR = 3004
    DIRECTORY_NOT_FOUND = 3005
    DISK_FULL = 3006

    # 缓存错误 4000-4099
    CACHE_ERROR = 4000
    CACHE_KEY_NOT_FOUND = 4001
    CACHE_EXPIRED = 4002
    CACHE_FULL = 4003

    # 导出错误 5000-5099
    EXPORT_ERROR = 5000
    EXPORT_FORMAT_ERROR = 5001
    EXPORT_SIZE_EXCEEDED = 5002
    EXPORT_ENCODING_ERROR = 5003

    # 监控错误 6000-6099
    MONITOR_ERROR = 6000
    MONITOR_COLLECTION_FAILED = 6001
    MONITOR_THRESHOLD_EXCEEDED = 6002

    # 批处理错误 7000-7099
    BATCH_ERROR = 7000
    BATCH_TASK_FAILED = 7001
    BATCH_TIMEOUT = 7002
    BATCH_PARTIAL_FAILURE = 7003


# ============================================================================
# 异常层次结构
# ============================================================================

class AppError(Exception):
    """
    应用基础异常类

    所有业务异常的基类，提供统一的错误信息、错误码、HTTP状态码和详情字段。

    Attributes:
        message: 错误消息摘要
        code: 应用错误码（见 ErrorCode）
        status_code: HTTP 状态码（用于 REST API 响应）
        details: 错误详情（结构化数据）
        cause: 原始异常（用于异常链追踪）
    """

    def __init__(
        self,
        message: str,
        code: int = ErrorCode.UNKNOWN,
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
        """序列化为字典，用于 JSON 响应或日志"""
        result = {
            "error": self.__class__.__name__,
            "message": self.message,
            "code": self.code,
            "status_code": self.status_code,
        }
        if self.details:
            result["details"] = self.details
        if self.cause:
            result["cause"] = str(self.cause)
        return result

    def __str__(self) -> str:
        base = f"[{self.code}] {self.__class__.__name__}: {self.message}"
        if self.details:
            base += f" | details={self.details}"
        if self.cause:
            base += f" | caused_by={type(self.cause).__name__}"
        return base


# ─── 数据层异常 ──────────────────────────────


class DataError(AppError):
    """数据层异常基类 (code: 2000-2099)"""
    def __init__(self, message: str, code: int = ErrorCode.DATA_FORMAT_ERROR, **kwargs):
        super().__init__(message, code=code, status_code=400, **kwargs)


class DataNotFoundError(DataError):
    """数据未找到"""
    def __init__(self, message: str = "数据未找到", **kwargs):
        super().__init__(message, code=ErrorCode.DATA_NOT_FOUND, status_code=404, **kwargs)


class DataValidationError(DataError):
    """数据校验失败"""
    def __init__(self, message: str = "数据校验失败", **kwargs):
        super().__init__(message, code=ErrorCode.DATA_VALIDATION_ERROR, **kwargs)


class DataIntegrityError(DataError):
    """数据完整性错误"""
    def __init__(self, message: str = "数据完整性错误", **kwargs):
        super().__init__(message, code=ErrorCode.DATA_INTEGRITY_ERROR, **kwargs)


class DataTooLargeError(DataError):
    """数据量过大"""
    def __init__(self, message: str = "数据量超过限制", actual_size: int = 0, max_size: int = 0):
        super().__init__(
            message,
            code=ErrorCode.DATA_TOO_LARGE,
            details={"actual_size": actual_size, "max_size": max_size},
        )


# ─── 文件系统异常 ────────────────────────────


class FileSystemError(AppError):
    """文件系统异常基类 (code: 3000-3099)"""
    def __init__(self, message: str, code: int = ErrorCode.FILE_READ_ERROR, file_path: str = "", **kwargs):
        details = kwargs.pop("details", {})
        if file_path:
            details["file_path"] = file_path
        super().__init__(message, code=code, status_code=500, details=details, **kwargs)


class FileNotFoundError2(FileSystemError):
    """文件未找到"""
    def __init__(self, file_path: str = "", **kwargs):
        super().__init__(
            f"文件未找到: {file_path}" if file_path else "文件未找到",
            code=ErrorCode.FILE_NOT_FOUND,
            file_path=file_path,
            status_code=404,
            **kwargs,
        )


class FilePermissionError2(FileSystemError):
    """文件权限错误"""
    def __init__(self, file_path: str = "", **kwargs):
        super().__init__(
            f"文件权限不足: {file_path}" if file_path else "文件权限不足",
            code=ErrorCode.FILE_PERMISSION_ERROR,
            file_path=file_path,
            status_code=403,
            **kwargs,
        )


class DirectoryNotFoundError(FileSystemError):
    """目录未找到"""
    def __init__(self, dir_path: str = "", **kwargs):
        super().__init__(
            f"目录未找到: {dir_path}" if dir_path else "目录未找到",
            code=ErrorCode.DIRECTORY_NOT_FOUND,
            file_path=dir_path,
            status_code=404,
            **kwargs,
        )


class DiskFullError(FileSystemError):
    """磁盘空间不足"""
    def __init__(self, available_bytes: int = 0, **kwargs):
        super().__init__(
            "磁盘空间不足",
            code=ErrorCode.DISK_FULL,
            details={"available_bytes": available_bytes},
            **kwargs,
        )


# ─── 缓存异常 ──────────────────────────────


class CacheError(AppError):
    """缓存异常基类 (code: 4000-4099)"""
    def __init__(self, message: str, code: int = ErrorCode.CACHE_ERROR, **kwargs):
        super().__init__(message, code=code, status_code=500, **kwargs)


class CacheKeyNotFoundError(CacheError):
    """缓存键未找到"""
    def __init__(self, key: str = "", **kwargs):
        super().__init__(
            f"缓存键不存在: {key}" if key else "缓存键不存在",
            code=ErrorCode.CACHE_KEY_NOT_FOUND,
            details={"key": key},
            **kwargs,
        )


class CacheFullError(CacheError):
    """缓存已满"""
    def __init__(self, max_items: int = 0, **kwargs):
        super().__init__(
            f"缓存已满 (最大 {max_items} 条)",
            code=ErrorCode.CACHE_FULL,
            details={"max_items": max_items},
            **kwargs,
        )


# ─── 导出异常 ──────────────────────────────


class ExportError(AppError):
    """导出异常基类 (code: 5000-5099)"""
    def __init__(self, message: str, code: int = ErrorCode.EXPORT_ERROR, **kwargs):
        super().__init__(message, code=code, status_code=500, **kwargs)


class ExportFormatError(ExportError):
    """不支持的导出格式"""
    def __init__(self, fmt: str = "", **kwargs):
        super().__init__(
            f"不支持的导出格式: {fmt}" if fmt else "不支持的导出格式",
            code=ErrorCode.EXPORT_FORMAT_ERROR,
            details={"format": fmt},
            **kwargs,
        )


class ExportSizeExceededError(ExportError):
    """导出数据量超限"""
    def __init__(self, actual: int = 0, max_rows: int = 0, **kwargs):
        super().__init__(
            f"导出数据量超限 ({actual} > {max_rows})",
            code=ErrorCode.EXPORT_SIZE_EXCEEDED,
            details={"actual": actual, "max_rows": max_rows},
            **kwargs,
        )


# ─── 监控异常 ──────────────────────────────


class MonitorError(AppError):
    """监控异常基类 (code: 6000-6099)"""
    def __init__(self, message: str, code: int = ErrorCode.MONITOR_ERROR, **kwargs):
        super().__init__(message, code=code, status_code=500, **kwargs)


class MonitorThresholdExceededError(MonitorError):
    """监控指标超过阈值"""
    def __init__(self, metric: str = "", current: float = 0, threshold: float = 0, **kwargs):
        super().__init__(
            f"监控指标 [{metric}] 超过阈值: {current} > {threshold}",
            code=ErrorCode.MONITOR_THRESHOLD_EXCEEDED,
            details={"metric": metric, "current": current, "threshold": threshold},
            **kwargs,
        )


# ─── 批处理异常 ──────────────────────────────


class BatchError(AppError):
    """批处理异常基类 (code: 7000-7099)"""
    def __init__(self, message: str, code: int = ErrorCode.BATCH_ERROR, **kwargs):
        super().__init__(message, code=code, status_code=500, **kwargs)


class BatchTaskFailedError(BatchError):
    """批处理单个任务失败"""
    def __init__(self, task_id: str = "", errors: List[str] = None, **kwargs):
        super().__init__(
            f"批处理任务失败: {task_id}" if task_id else "批处理任务失败",
            code=ErrorCode.BATCH_TASK_FAILED,
            details={"task_id": task_id, "errors": errors or []},
            **kwargs,
        )


class BatchTimeoutError(BatchError):
    """批处理超时"""
    def __init__(self, timeout: int = 0, **kwargs):
        super().__init__(
            f"批处理超时 ({timeout}秒)",
            code=ErrorCode.BATCH_TIMEOUT,
            details={"timeout": timeout},
            **kwargs,
        )


class BatchPartialFailureError(BatchError):
    """批处理部分失败"""
    def __init__(self, total: int = 0, failed: int = 0, errors: List[str] = None, **kwargs):
        super().__init__(
            f"批处理部分失败: {failed}/{total} 个任务失败",
            code=ErrorCode.BATCH_PARTIAL_FAILURE,
            details={"total": total, "failed": failed, "errors": errors or []},
            **kwargs,
        )


# ─── 配置异常 ──────────────────────────────


class ConfigError(AppError):
    """配置异常"""
    def __init__(self, message: str, key: str = "", **kwargs):
        details = kwargs.pop("details", {})
        if key:
            details["config_key"] = key
        super().__init__(
            f"配置错误: {message}" if key else message,
            code=ErrorCode.CONFIG_ERROR,
            status_code=500,
            details=details,
            **kwargs,
        )


# ============================================================================
# 异常辅助函数
# ============================================================================


def format_exception(exc: Exception, include_traceback: bool = True) -> str:
    """
    格式化异常为字符串

    参数:
        exc: 异常对象
        include_traceback: 是否包含堆栈跟踪

    返回:
        str: 格式化的异常信息字符串
    """
    if isinstance(exc, AppError):
        parts = [str(exc)]
        if include_traceback and exc.__cause__:
            parts.append("\nCaused by:")
            parts.append(format_exception(exc.__cause__, include_traceback))
        return "\n".join(parts)

    parts = [f"{type(exc).__name__}: {str(exc)}"]
    if include_traceback:
        tb_lines = traceback.format_exception(type(exc), exc, exc.__traceback__)
        parts.append("".join(tb_lines))
    return "\n".join(parts)


def safe_call(func, *args, default=None, error_msg: str = "", **kwargs):
    """
    安全调用函数，捕获异常并返回默认值

    参数:
        func: 要调用的函数
        *args: 位置参数
        default: 发生异常时的默认返回值
        error_msg: 发生异常时的日志消息
        **kwargs: 关键字参数
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        if error_msg:
            import logging
            logging.getLogger("safe_call").warning(f"{error_msg}: {e}")
        return default
