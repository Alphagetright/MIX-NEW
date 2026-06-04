# -*- coding: utf-8 -*-
"""结构化日志 —— 带上下文字段的日志记录"""

import uuid
import logging
import threading
from .log_config import DEFAULT_LOG_CONFIG as _DEFAULT_CFG


_local = threading.local()


class StructuredLogger:
    """结构化日志器 —— 支持额外字段注入"""

    def __init__(self, name, logger=None):
        self._name = name
        self._logger = logger or _DEFAULT_CFG.configure_logger(name)

    def _log(self, level, message, **kwargs):
        extra = kwargs.pop("extra", {})
        extra.setdefault("logger", self._name)
        extra.setdefault("trace_id", getattr(_local, "trace_id", None))
        try:
            self._logger.log(level, message, extra=extra, **kwargs)
        except Exception:
            pass

    def debug(self, message, **kwargs):
        self._log(logging.DEBUG, message, **kwargs)

    def info(self, message, **kwargs):
        self._log(logging.INFO, message, **kwargs)

    def warning(self, message, **kwargs):
        self._log(logging.WARNING, message, **kwargs)

    def error(self, message, **kwargs):
        self._log(logging.ERROR, message, **kwargs)

    def critical(self, message, **kwargs):
        self._log(logging.CRITICAL, message, **kwargs)

    def set_trace_id(self, trace_id=None):
        _local.trace_id = trace_id or str(uuid.uuid4())[:8]

    def clear_trace_id(self):
        _local.trace_id = None

    @property
    def trace_id(self):
        return getattr(_local, "trace_id", None)


class LoggerManager:
    """日志管理器 —— 统一管理所有日志器"""

    def __init__(self):
        self._loggers = {}
        self._default_config = _DEFAULT_CFG

    def get_logger(self, name):
        if name not in self._loggers:
            self._loggers[name] = StructuredLogger(name)
        return self._loggers[name]

    def set_level(self, name, level):
        logger = self.get_logger(name)
        logger._logger.setLevel(level)

    def set_all_levels(self, level):
        for logger in self._loggers.values():
            logger._logger.setLevel(level)

    def configure(self, name, level=None, handlers=None):
        if handlers:
            cfg_logger = _DEFAULT_CFG.configure_logger(name, handlers=handlers, level=level)
            self._loggers[name] = StructuredLogger(name, cfg_logger)
        elif level:
            self.set_level(name, level)
        return self._loggers[name]


_logger_manager = LoggerManager()


def get_logger(name=None):
    if name is None:
        import inspect
        frame = inspect.currentframe()
        name = frame.f_back.f_globals.get("__name__", "unknown") if frame else "unknown"
    return _logger_manager.get_logger(name)
