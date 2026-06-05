# -*- coding: utf-8 -*-
"""
系统监控模块 — 资源使用、接口统计、健康检查
"""
import os
import time
import threading

from config import BASE_DIR
from logger import get_logger, LoggerMixin

logger = get_logger("monitor")


class SystemMonitor(LoggerMixin):
    """系统资源监控"""

    def __init__(self, interval: int = 60):
        self.interval = interval
        self._running = False
        self._thread = None
        self._snapshots = []
        self._lock = threading.Lock()

    @property
    def disk_usage(self) -> dict:
        """磁盘使用情况"""
        try:
            import shutil
            total, used, free = shutil.disk_usage(BASE_DIR)
            return {
                "total_gb": round(total / (1024**3), 2),
                "used_gb": round(used / (1024**3), 2),
                "free_gb": round(free / (1024**3), 2),
                "usage_pct": round(used / total * 100, 1) if total else 0,
            }
        except Exception:
            return {"error": "无法获取磁盘信息"}

    @property
    def memory_info(self) -> dict:
        """内存使用信息"""
        try:
            import psutil
            mem = psutil.virtual_memory()
            return {
                "total_gb": round(mem.total / (1024**3), 2),
                "available_gb": round(mem.available / (1024**3), 2),
                "usage_pct": mem.percent,
            }
        except ImportError:
            return {"note": "需安装 psutil (pip install psutil)"}
        except Exception as e:
            return {"error": str(e)}

    @property
    def cpu_info(self) -> dict:
        """CPU 使用信息"""
        try:
            import psutil
            return {
                "cpu_percent": psutil.cpu_percent(interval=0.5),
                "cpu_count": psutil.cpu_count(),
                "load_avg": os.getloadavg() if hasattr(os, "getloadavg") else None,
            }
        except ImportError:
            return {"note": "需安装 psutil"}
        except Exception as e:
            return {"error": str(e)}

    @property
    def python_info(self) -> dict:
        """Python 运行时信息"""
        import sys
        return {
            "version": sys.version,
            "executable": sys.executable,
            "platform": sys.platform,
        }

    @property
    def project_info(self) -> dict:
        """项目文件信息"""
        py_files = 0
        py_lines = 0
        for root, dirs, files in os.walk(BASE_DIR):
            dirs[:] = [d for d in dirs if d not in ("__pycache__", "rag_db",
                                                      "node_modules", ".git")]
            for f in files:
                if f.endswith(".py"):
                    py_files += 1
                    fpath = os.path.join(root, f)
                    try:
                        with open(fpath, "r", encoding="utf-8") as fh:
                            py_lines += sum(1 for _ in fh)
                    except Exception:
                        pass

        return {
            "python_files": py_files,
            "python_lines": py_lines,
            "project_dir": BASE_DIR,
        }

    def snapshot(self) -> dict:
        """获取当前系统快照"""
        snap = {
            "timestamp": time.time(),
            "time_str": time.strftime("%Y-%m-%d %H:%M:%S"),
            "disk": self.disk_usage,
            "memory": self.memory_info,
            "cpu": self.cpu_info,
            "python": self.python_info,
            "project": self.project_info,
        }
        self.log_debug(f"系统快照已记录")
        return snap

    def collect(self) -> dict:
        """收集并记录快照"""
        snap = self.snapshot()
        with self._lock:
            self._snapshots.append(snap)
            if len(self._snapshots) > 100:
                self._snapshots = self._snapshots[-100:]
        return snap

    def start_background_collection(self):
        """启动后台定时收集"""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        self.log_info(f"后台监控已启动 (间隔 {self.interval}s)")

    def stop_background_collection(self):
        """停止后台收集"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None
        self.log_info("后台监控已停止")

    def _run_loop(self):
        while self._running:
            try:
                self.collect()
            except Exception as e:
                self.log_error(f"监控采集异常: {e}")
            time.sleep(self.interval)

    def get_history(self, count: int = 10) -> list:
        """获取最近 N 次快照"""
        with self._lock:
            return self._snapshots[-count:]

    def health_check(self) -> dict:
        """健康检查"""
        snap = self.collect()
        issues = []

        disk = snap.get("disk", {})
        if disk.get("usage_pct", 0) > 90:
            issues.append(f"磁盘使用率过高: {disk['usage_pct']}%")
        mem = snap.get("memory", {})
        if mem.get("usage_pct", 0) > 90:
            issues.append(f"内存使用率过高: {mem['usage_pct']}%")

        return {
            "status": "unhealthy" if issues else "healthy",
            "timestamp": snap["timestamp"],
            "time_str": snap["time_str"],
            "issues": issues,
            "disk_usage_pct": disk.get("usage_pct"),
            "memory_usage_pct": mem.get("usage_pct"),
        }


# 全局单例
system_monitor = SystemMonitor()


def get_system_monitor() -> SystemMonitor:
    return system_monitor
