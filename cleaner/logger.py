# -*- coding: utf-8 -*-
"""日志模块"""
import logging, os, threading
from logging.handlers import RotatingFileHandler
from typing import Dict, Optional
from .config import LOG_DIR, LOG_LEVEL, LOG_MAX_BYTES, LOG_BACKUP_COUNT

os.makedirs(LOG_DIR, exist_ok=True)
_logger_cache: Dict[str, logging.Logger] = {}
_logger_lock = threading.Lock()
_global_level = getattr(logging, LOG_LEVEL.upper(), logging.INFO)


def get_logger(name: str = "tang_cleaner") -> logging.Logger:
    with _logger_lock:
        if name in _logger_cache:
            return _logger_cache[name]
        logger = logging.getLogger(name); logger.setLevel(_global_level)
        logger.propagate = False
        if not logger.handlers:
            fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s", "%Y-%m-%d %H:%M:%S")
            ch = logging.StreamHandler(); ch.setLevel(_global_level); ch.setFormatter(fmt)
            logger.addHandler(ch)
            fh = RotatingFileHandler(os.path.join(LOG_DIR, f"{name}.log"),
                                     maxBytes=LOG_MAX_BYTES, backupCount=LOG_BACKUP_COUNT, encoding="utf-8")
            fh.setLevel(_global_level); fh.setFormatter(fmt)
            logger.addHandler(fh)
        _logger_cache[name] = logger
        return logger
