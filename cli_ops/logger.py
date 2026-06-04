# -*- coding: utf-8 -*-
"""
日志模块
========
基于 Python logging 的分级日志系统，支持：
  - RotatingFileHandler 自动轮转
  - 控制台 + 文件双输出
  - Logger 实例缓存
  - LoggerMixin 混入类
  - 结构化日志辅助函数
  - 日志级别动态调整
"""

import logging
import os
import threading
from logging.handlers import RotatingFileHandler
from typing import Optional, Dict

from .config import (
    LOG_DIR, LOG_LEVEL, LOG_MAX_BYTES, LOG_BACKUP_COUNT,
    LOG_FORMAT, LOG_DATE_FORMAT,
)

# 确保日志目录存在
os.makedirs(LOG_DIR, exist_ok=True)

# Logger 缓存
_logger_cache: Dict[str, logging.Logger] = {}
_logger_lock = threading.Lock()

# 全局日志级别
_global_level = getattr(logging, LOG_LEVEL.upper(), logging.INFO)

# 控制台输出开关（REPL 模式下关闭，避免与 Rich 输出混叠）
_console_enabled = True


def set_console_logging(enabled: bool) -> None:
    """启用/禁用所有 logger 的控制台输出（REPL 模式使用）"""
    global _console_enabled
    _console_enabled = enabled
    with _logger_lock:
        for logger in _logger_cache.values():
            if enabled:
                # 重新启用：检查是否已有 console handler，没有则添加
                has_console = any(
                    isinstance(h, logging.StreamHandler) and not isinstance(h, RotatingFileHandler)
                    for h in logger.handlers
                )
                if not has_console:
                    formatter = logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT)
                    ch = logging.StreamHandler()
                    ch.setLevel(logger.level)
                    ch.setFormatter(formatter)
                    logger.addHandler(ch)
            else:
                # 禁用：移除 console handler
                to_remove = [
                    h for h in logger.handlers
                    if isinstance(h, logging.StreamHandler) and not isinstance(h, RotatingFileHandler)
                ]
                for h in to_remove:
                    logger.removeHandler(h)


def set_global_level(level: str) -> None:
    """动态调整全局日志级别"""
    global _global_level
    new_level = getattr(logging, level.upper(), logging.INFO)
    _global_level = new_level
    with _logger_lock:
        for logger in _logger_cache.values():
            logger.setLevel(new_level)


def get_logger(name: str = "tang_cli_ops") -> logging.Logger:
    """
    获取或创建 logger 实例（带缓存）

    参数:
        name: logger 名称，默认 'tang_cli_ops'

    返回:
        logging.Logger: 配置好的 logger 实例
    """
    with _logger_lock:
        if name in _logger_cache:
            return _logger_cache[name]

        logger = logging.getLogger(name)
        logger.setLevel(_global_level)
        logger.propagate = False

        # 避免重复添加 handler
        if not logger.handlers:
            formatter = logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT)

            # 控制台处理器（REPL 模式下不添加）
            if _console_enabled:
                console_handler = logging.StreamHandler()
                console_handler.setLevel(_global_level)
                console_handler.setFormatter(formatter)
                logger.addHandler(console_handler)

            # 文件处理器（按名称分文件）
            safe_name = name.replace(".", "_")
            log_file = os.path.join(LOG_DIR, f"{safe_name}.log")
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=LOG_MAX_BYTES,
                backupCount=LOG_BACKUP_COUNT,
                encoding="utf-8",
            )
            file_handler.setLevel(_global_level)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

        _logger_cache[name] = logger
        return logger


class LoggerMixin:
    """
    Logger 混入类

    为任意对象提供便捷的日志方法。
    日志名称默认为 `模块名.类名`。

    Usage:
        class MyService(LoggerMixin):
            def do_something(self):
                self.logger.info("doing something")
                self.logger.error("something went wrong")
    """

    @property
    def logger(self) -> logging.Logger:
        if not hasattr(self, "_logger"):
            cls_name = type(self).__name__
            mod_name = type(self).__module__.split(".")[-1]
            self._logger = get_logger(f"{mod_name}.{cls_name}")
        return self._logger


def log_function_call(logger: Optional[logging.Logger] = None):
    """
    函数调用日志装饰器

    自动记录函数调用参数和返回值（debug 级别）。

    参数:
        logger: 使用的 logger，默认自动获取
    """
    def decorator(func):
        import functools
        _logger = logger or get_logger(func.__module__.split(".")[-1])

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            _logger.debug(f"调用 {func.__name__}(args={args[1:] if len(args) > 1 else ''}, kwargs={kwargs})")
            try:
                result = func(*args, **kwargs)
                _logger.debug(f"{func.__name__} 返回成功")
                return result
            except Exception as e:
                _logger.debug(f"{func.__name__} 抛出异常: {type(e).__name__}")
                raise

        return wrapper
    return decorator


def structured_log(logger: logging.Logger, level: str, message: str, **kwargs):
    """
    结构化日志输出

    参数:
        logger: logger 实例
        level: 日志级别 (debug/info/warning/error/critical)
        message: 日志消息
        **kwargs: 附加的结构化字段
    """
    extra_info = " | ".join(f"{k}={v}" for k, v in kwargs.items())
    full_message = f"{message} [{extra_info}]" if extra_info else message
    log_func = getattr(logger, level.lower(), logger.info)
    log_func(full_message)


def get_all_log_files() -> list:
    """获取所有日志文件列表"""
    files = []
    if os.path.exists(LOG_DIR):
        for f in sorted(os.listdir(LOG_DIR)):
            if f.endswith(".log"):
                path = os.path.join(LOG_DIR, f)
                files.append({
                    "name": f,
                    "size": os.path.getsize(path),
                    "modified": os.path.getmtime(path),
                })
    return files


def clean_old_logs(keep_days: int = 30) -> int:
    """
    清理超过指定天数的日志文件

    参数:
        keep_days: 保留天数

    返回:
        int: 删除的文件数量
    """
    import time
    cutoff = time.time() - keep_days * 86400
    deleted = 0
    if os.path.exists(LOG_DIR):
        for f in os.listdir(LOG_DIR):
            path = os.path.join(LOG_DIR, f)
            if f.endswith(".log") and os.path.getmtime(path) < cutoff:
                try:
                    os.remove(path)
                    deleted += 1
                except OSError:
                    pass
    return deleted


def get_log_stats() -> dict:
    """获取日志统计信息"""
    files = get_all_log_files()
    total_size = sum(f["size"] for f in files)
    return {
        "total_files": len(files),
        "total_size_bytes": total_size,
        "total_size_mb": round(total_size / (1024 * 1024), 2),
        "log_directory": LOG_DIR,
        "global_level": logging.getLevelName(_global_level),
        "files": files,
    }
