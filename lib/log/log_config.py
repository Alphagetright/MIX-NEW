# -*- coding: utf-8 -*-
"""日志配置 —— 日志级别、格式、输出目标管理"""

import os
import logging
from logging.handlers import RotatingFileHandler


DEFAULT_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
DEFAULT_LEVEL = logging.INFO


class LogConfig:
    """日志配置管理器"""

    def __init__(self):
        self._formatters = {}
        self._handlers = {}
        self._loggers = {}

    def create_formatter(self, name="default", fmt=None, datefmt=None):
        fmt = fmt or DEFAULT_FORMAT
        datefmt = datefmt or DEFAULT_DATE_FORMAT
        formatter = logging.Formatter(fmt, datefmt)
        self._formatters[name] = formatter
        return formatter

    def get_formatter(self, name="default"):
        return self._formatters.get(name)

    def create_console_handler(self, level=None, formatter_name="default"):
        handler = logging.StreamHandler()
        handler.setLevel(level or DEFAULT_LEVEL)
        formatter = self.get_formatter(formatter_name)
        if formatter:
            handler.setFormatter(formatter)
        return handler

    def create_file_handler(self, filepath, level=None, formatter_name="default",
                            max_bytes=10*1024*1024, backup_count=5):
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        handler = RotatingFileHandler(
            filepath, maxBytes=max_bytes, backupCount=backup_count,
            encoding="utf-8",
        )
        handler.setLevel(level or DEFAULT_LEVEL)
        formatter = self.get_formatter(formatter_name)
        if formatter:
            handler.setFormatter(formatter)
        return handler

    def configure_logger(self, name, handlers=None, level=None, propagate=False):
        logger = logging.getLogger(name)
        logger.setLevel(level or DEFAULT_LEVEL)
        logger.propagate = propagate
        if handlers:
            for h in handlers:
                logger.addHandler(h)
        self._loggers[name] = logger
        return logger

    def get_logger(self, name):
        return self._loggers.get(name) or logging.getLogger(name)

    def set_level(self, name, level):
        logger = self.get_logger(name)
        logger.setLevel(level)


DEFAULT_LOG_CONFIG = LogConfig()
DEFAULT_LOG_CONFIG.create_formatter()
DEFAULT_LOG_CONFIG.create_formatter(
    "detailed",
    "%(asctime)s [%(levelname)s] %(name)s (%(filename)s:%(lineno)d): %(message)s",
)
