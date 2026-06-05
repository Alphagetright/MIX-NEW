# -*- coding: utf-8 -*-
"""日志模块 — 分级日志、文件轮转"""

import logging
import os
import threading
from logging.handlers import RotatingFileHandler
from typing import Dict, Optional

from .config import LOG_DIR, LOG_LEVEL, LOG_MAX_BYTES, LOG_BACKUP_COUNT

os.makedirs(LOG_DIR, exist_ok=True)

_logger_cache: Dict[str, logging.Logger] = {}
_logger_lock = threading.Lock()
_global_level = getattr(logging, LOG_LEVEL.upper(), logging.INFO)


def set_global_level(level: str) -> None:
    global _global_level
    _global_level = getattr(logging, level.upper(), logging.INFO)
    with _logger_lock:
        for logger in _logger_cache.values():
            logger.setLevel(_global_level)


def get_logger(name: str = "tang_stats_viz") -> logging.Logger:
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
            ch = logging.StreamHandler(); ch.setLevel(_global_level); ch.setFormatter(fmt)
            logger.addHandler(ch)
            safe_name = name.replace(".", "_")
            fh = RotatingFileHandler(
                os.path.join(LOG_DIR, f"{safe_name}.log"),
                maxBytes=LOG_MAX_BYTES, backupCount=LOG_BACKUP_COUNT, encoding="utf-8",
            )
            fh.setLevel(_global_level); fh.setFormatter(fmt)
            logger.addHandler(fh)
        _logger_cache[name] = logger
        return logger


class LoggerMixin:
    @property
    def logger(self) -> logging.Logger:
        if not hasattr(self, "_logger"):
            cls_name = type(self).__name__
            mod_name = type(self).__module__.split(".")[-1]
            self._logger = get_logger(f"{mod_name}.{cls_name}")
        return self._logger


def structured_log(logger: logging.Logger, level: str, message: str, **kwargs) -> None:
    extra = " | ".join(f"{k}={v}" for k, v in kwargs.items())
    msg = f"{message} [{extra}]" if extra else message
    getattr(logger, level.lower(), logger.info)(msg)


def get_log_stats() -> dict:
    files = []
    if os.path.exists(LOG_DIR):
        for f in sorted(os.listdir(LOG_DIR)):
            fp = os.path.join(LOG_DIR, f)
            if f.endswith(".log") and os.path.isfile(fp):
                files.append({"name": f, "size": os.path.getsize(fp)})
    return {"total_files": len(files), "total_size_bytes": sum(x["size"] for x in files)}
