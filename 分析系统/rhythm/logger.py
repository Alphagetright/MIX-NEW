# -*- coding: utf-8 -*-
"""
古典诗词音韵格律分析引擎 — 分级日志系统
"""
import logging
import os
import threading
from logging.handlers import RotatingFileHandler

from .config import LOG_DIR, LOG_LEVEL, LOG_MAX_BYTES, LOG_BACKUP_COUNT

os.makedirs(LOG_DIR, exist_ok=True)

_logger_cache = {}
_logger_lock = threading.Lock()
_global_level = getattr(logging, LOG_LEVEL.upper(), logging.INFO)


def set_global_level(level: str):
    global _global_level
    _global_level = getattr(logging, level.upper(), logging.INFO)
    with _logger_lock:
        for logger in _logger_cache.values():
            logger.setLevel(_global_level)
            for handler in logger.handlers:
                handler.setLevel(_global_level)


def get_logger(name: str = "poetry_rhythm") -> logging.Logger:
    with _logger_lock:
        if name in _logger_cache:
            return _logger_cache[name]

        logger = logging.getLogger(name)
        logger.setLevel(_global_level)
        logger.propagate = False

        if not logger.handlers:
            fmt = logging.Formatter(
                "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                "%Y-%m-%d %H:%M:%S",
            )
            ch = logging.StreamHandler()
            ch.setLevel(_global_level)
            ch.setFormatter(fmt)
            logger.addHandler(ch)

            safe_name = name.replace(".", "_")
            fh = RotatingFileHandler(
                os.path.join(LOG_DIR, f"{safe_name}.log"),
                maxBytes=LOG_MAX_BYTES,
                backupCount=LOG_BACKUP_COUNT,
                encoding="utf-8",
            )
            fh.setLevel(_global_level)
            fh.setFormatter(fmt)
            logger.addHandler(fh)

        _logger_cache[name] = logger
        return logger


class LoggerMixin:
    """日志混入类 — 自动提供 self.logger"""

    @property
    def logger(self) -> logging.Logger:
        cls = self.__class__
        name = f"{cls.__module__}.{cls.__name__}"
        return get_logger(name)


def structured_log(logger: logging.Logger, level: str, message: str, **kwargs):
    """结构化日志 — key=value 附加数据"""
    extras = " ".join(f"{k}={v}" for k, v in kwargs.items())
    msg = f"{message} | {extras}" if extras else message
    getattr(logger, level.lower(), logger.info)(msg)
