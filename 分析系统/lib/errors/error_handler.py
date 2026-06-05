# -*- coding: utf-8 -*-
"""错误处理 —— 捕获、记录、分类、通知"""

from .exceptions import PipelineError, error_code_to_name


class ErrorHandler:
    """错误处理器 —— 异常捕获链"""

    def __init__(self, logger=None, handlers=None):
        self._logger = logger
        self._handlers = handlers or []

    def register_handler(self, error_class, callback):
        self._handlers.append((error_class, callback))

    def handle(self, error, context=None):
        if isinstance(error, PipelineError):
            self._handle_pipeline_error(error, context)
        else:
            self._handle_generic_error(error, context)

    def _handle_pipeline_error(self, error, context=None):
        info = error.to_dict()
        info["context"] = {**(context or {}), **info["context"]}
        if self._logger:
            self._logger.error(
                f"[{info['code']}] {info['message']}",
                extra=info,
            )
        for exc_cls, callback in self._handlers:
            if isinstance(error, exc_cls):
                try:
                    callback(error)
                except Exception as cb_err:
                    if self._logger:
                        self._logger.warning(f"Error handler callback failed: {cb_err}")

    def _handle_generic_error(self, error, context=None):
        if self._logger:
            self._logger.error(
                f"Unhandled error: {error}",
                extra={"type": type(error).__name__, "context": context or {}},
            )

    def safe_call(self, fn, default=None, log_level="warning"):
        """安全调用 —— 捕获异常返回默认值"""
        try:
            return fn()
        except PipelineError as e:
            self.handle(e)
            return default
        except Exception as e:
            if self._logger:
                getattr(self._logger, log_level)(f"Call failed: {e}")
            return default


class ErrorCollector:
    """错误收集器 —— 收集汇总错误信息"""

    def __init__(self):
        self._errors = []
        self._warnings = []

    def add_error(self, error, source=None):
        entry = {
            "error": str(error),
            "code": getattr(error, "code", 0),
            "source": source,
            "type": type(error).__name__,
        }
        self._errors.append(entry)

    def add_warning(self, message, source=None):
        self._warnings.append({"message": message, "source": source})

    @property
    def error_count(self):
        return len(self._errors)

    @property
    def warning_count(self):
        return len(self._warnings)

    @property
    def has_errors(self):
        return len(self._errors) > 0

    def summary(self):
        return {
            "errors": self.error_count,
            "warnings": self.warning_count,
            "error_list": self._errors[-10:] if self._errors else [],
            "warning_list": self._warnings[-10:] if self._warnings else [],
        }

    def clear(self):
        self._errors.clear()
        self._warnings.clear()
