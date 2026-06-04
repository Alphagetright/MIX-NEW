# -*- coding: utf-8 -*-
"""
日志模块 — 分级日志、文件滚动、上下文跟踪
"""
import logging
import os
import sys
import traceback
from logging.handlers import RotatingFileHandler

from config import LOG_DIR, LOG_LEVEL, LOG_MAX_BYTES, LOG_BACKUP_COUNT, LOG_FORMAT


def ensure_log_dir():
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR, exist_ok=True)


def _create_console_handler(formatter):
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    handler.setLevel(logging.DEBUG)
    return handler


def _create_file_handler(log_path, formatter):
    handler = RotatingFileHandler(
        log_path,
        maxBytes=LOG_MAX_BYTES,
        backupCount=LOG_BACKUP_COUNT,
        encoding="utf-8",
    )
    handler.setFormatter(formatter)
    handler.setLevel(logging.DEBUG)
    return handler


_loggers = {}


def get_logger(name=None):
    if name is None:
        name = __name__
    if name in _loggers:
        return _loggers[name]

    ensure_log_dir()
    level = getattr(logging, LOG_LEVEL.upper(), logging.INFO)
    formatter = logging.Formatter(LOG_FORMAT)

    logger = logging.getLogger(name)
    logger.setLevel(level)

    if not logger.handlers:
        logger.addHandler(_create_console_handler(formatter))
        logger.addHandler(
            _create_file_handler(os.path.join(LOG_DIR, "app.log"), formatter)
        )

    logger.propagate = False
    _loggers[name] = logger
    return logger


class LoggerMixin:
    """混入类，为对象提供便捷日志方法"""

    @property
    def logger(self):
        if not hasattr(self, "_logger"):
            cls_name = type(self).__name__
            self._logger = get_logger(cls_name)
        return self._logger

    def log_debug(self, msg, *args, **kwargs):
        self.logger.debug(msg, *args, **kwargs)

    def log_info(self, msg, *args, **kwargs):
        self.logger.info(msg, *args, **kwargs)

    def log_warning(self, msg, *args, **kwargs):
        self.logger.warning(msg, *args, **kwargs)

    def log_error(self, msg, *args, **kwargs):
        self.logger.error(msg, *args, **kwargs)

    def log_exception(self, msg, *args, **kwargs):
        self.logger.exception(msg, *args, **kwargs)


def format_exception(e: Exception) -> str:
    return "".join(traceback.format_exception(type(e), e, e.__traceback__))
