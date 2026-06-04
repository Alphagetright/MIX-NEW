# -*- coding: utf-8 -*-
"""系统工具函数"""

import os
import sys
import platform


def get_platform():
    return platform.system()


def is_windows():
    return platform.system() == "Windows"


def is_linux():
    return platform.system() == "Linux"


def is_macos():
    return platform.system() == "Darwin"


def get_cpu_count():
    return os.cpu_count() or 1


def get_pid():
    return os.getpid()


def get_env(key, default=None):
    return os.environ.get(key, default)


def set_env(key, value):
    os.environ[key] = str(value)


def get_python_version():
    return sys.version


def get_python_executable():
    return sys.executable


def get_cwd():
    return os.getcwd()


def get_memory_usage():
    try:
        import psutil
        process = psutil.Process(os.getpid())
        mem = process.memory_info()
        return {
            "rss": mem.rss,
            "vms": mem.vms,
            "rss_mb": mem.rss / 1024 / 1024,
            "vms_mb": mem.vms / 1024 / 1024,
        }
    except ImportError:
        return {}


class SystemInfo:
    """系统信息收集"""

    @staticmethod
    def collect():
        return {
            "platform": platform.system(),
            "platform_release": platform.release(),
            "python_version": sys.version.split()[0],
            "python_executable": sys.executable,
            "cpu_count": get_cpu_count(),
            "pid": get_pid(),
            "cwd": os.getcwd(),
            "memory": get_memory_usage(),
        }

    @staticmethod
    def summary():
        return f"{platform.system()} {platform.release()} | Python {sys.version.split()[0]} | PID {os.getpid()}"
