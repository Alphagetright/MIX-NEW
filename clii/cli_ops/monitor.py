# -*- coding: utf-8 -*-
"""
系统监控模块
============
采集系统资源使用情况，支持 CPU、内存、磁盘、网络、进程等多个维度的监控。
支持快照采集、历史记录、阈值告警、健康度评分。

依赖: psutil (可选，不可用时降级为基础监控)
"""

import os
import sys
import time
import threading
import platform
from datetime import datetime
from typing import Any, Dict, List, Optional

from .config import (
    MONITOR_COLLECTION_INTERVAL,
    MONITOR_HISTORY_MAX_ITEMS,
    MONITOR_DISK_THRESHOLD_PCT,
    MONITOR_MEMORY_THRESHOLD_PCT,
    MONITOR_CPU_THRESHOLD_PCT,
)
from .logger import get_logger

logger = get_logger("monitor")

# 尝试导入 psutil
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False
    logger.warning("psutil 未安装，监控功能受限（仅支持基础磁盘监控）")


class SystemMonitor:
    """
    系统资源监控器

    采集系统级指标并记录历史快照。
    支持后台定时采集、阈值检查、健康度评分。

    Usage:
        monitor = SystemMonitor()
        snapshot = monitor.snapshot()
        print(monitor.health_score())
        monitor.start_background_collection(interval=60)
    """

    def __init__(self):
        self._lock = threading.RLock()
        self._history: List[Dict[str, Any]] = []
        self._max_history = MONITOR_HISTORY_MAX_ITEMS
        self._collection_thread: Optional[threading.Thread] = None
        self._running = False
        self._alert_callbacks: List[callable] = []
        self._start_time = time.time()

    # ─── 数据采集 ──────────────────────────────

    def disk_usage(self, path: str = ".") -> Dict[str, Any]:
        """
        获取磁盘使用情况

        返回:
            Dict: {"total_gb", "used_gb", "free_gb", "percent"}
        """
        try:
            import shutil
            usage = shutil.disk_usage(path)
            total = usage.total
            free = usage.free
            used = usage.used
            percent = round(used / total * 100, 1) if total > 0 else 0.0
            return {
                "total_gb": round(total / (1024 ** 3), 2),
                "used_gb": round(used / (1024 ** 3), 2),
                "free_gb": round(free / (1024 ** 3), 2),
                "percent": percent,
                "path": os.path.abspath(path),
            }
        except Exception as e:
            logger.error(f"磁盘监控失败: {e}")
            return {"error": str(e), "total_gb": 0, "used_gb": 0, "free_gb": 0, "percent": 0}

    def memory_info(self) -> Dict[str, Any]:
        """获取内存使用信息"""
        if not HAS_PSUTIL:
            return {"available": True, "note": "psutil 未安装，仅提供基础信息"}

        try:
            mem = psutil.virtual_memory()
            swap = psutil.swap_memory()
            return {
                "total_gb": round(mem.total / (1024 ** 3), 2),
                "available_gb": round(mem.available / (1024 ** 3), 2),
                "used_gb": round(mem.used / (1024 ** 3), 2),
                "percent": mem.percent,
                "free_gb": round(mem.free / (1024 ** 3), 2),
                "swap_total_gb": round(swap.total / (1024 ** 3), 2),
                "swap_used_gb": round(swap.used / (1024 ** 3), 2),
                "swap_percent": swap.percent,
            }
        except Exception as e:
            logger.error(f"内存监控失败: {e}")
            return {"error": str(e), "percent": 0}

    def cpu_info(self) -> Dict[str, Any]:
        """获取 CPU 使用信息"""
        if not HAS_PSUTIL:
            return {"available": True, "note": "psutil 未安装，仅提供基础信息"}

        try:
            return {
                "percent": psutil.cpu_percent(interval=0.5),
                "count": psutil.cpu_count(),
                "count_physical": psutil.cpu_count(logical=False),
                "freq_current_mhz": (
                    round(psutil.cpu_freq().current, 0)
                    if psutil.cpu_freq() else "N/A"
                ),
                "load_avg_1min": round(os.getloadavg()[0], 2) if hasattr(os, "getloadavg") else "N/A",
            }
        except Exception as e:
            logger.error(f"CPU 监控失败: {e}")
            return {"error": str(e), "percent": 0, "count": os.cpu_count()}

    def network_info(self) -> Dict[str, Any]:
        """获取网络使用信息"""
        if not HAS_PSUTIL:
            return {"available": True, "note": "psutil 未安装，仅提供基础信息"}

        try:
            net = psutil.net_io_counters()
            connections = psutil.net_connections()
            return {
                "bytes_sent_mb": round(net.bytes_sent / (1024 ** 2), 2),
                "bytes_recv_mb": round(net.bytes_recv / (1024 ** 2), 2),
                "packets_sent": net.packets_sent,
                "packets_recv": net.packets_recv,
                "error_in": net.errin,
                "error_out": net.errout,
                "drop_in": net.dropin,
                "drop_out": net.dropout,
                "active_connections": len(connections),
            }
        except Exception as e:
            logger.error(f"网络监控失败: {e}")
            return {"error": str(e)}

    def process_info(self) -> Dict[str, Any]:
        """获取当前进程信息"""
        pid = os.getpid()
        info = {
            "pid": pid,
            "python_version": sys.version.split()[0],
            "platform": platform.platform(),
            "processor": platform.processor(),
            "cwd": os.getcwd(),
            "thread_count": threading.active_count(),
            "uptime_seconds": round(time.time() - self._start_time, 1),
        }
        if HAS_PSUTIL:
            try:
                proc = psutil.Process(pid)
                info.update({
                    "memory_rss_mb": round(proc.memory_info().rss / (1024 ** 2), 2),
                    "memory_vms_mb": round(proc.memory_info().vms / (1024 ** 2), 2),
                    "cpu_percent": proc.cpu_percent(interval=0.1),
                    "open_files": len(proc.open_files()),
                    "connections": len(proc.connections()),
                    "create_time": datetime.fromtimestamp(proc.create_time()).isoformat(),
                })
            except Exception as e:
                logger.debug(f"进程信息采集部分失败: {e}")
        return info

    # ─── 快照与历史 ────────────────────────────

    def snapshot(self) -> Dict[str, Any]:
        """采集当前系统完整快照"""
        snap = {
            "timestamp": time.time(),
            "timestamp_formatted": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "disk": self.disk_usage(),
            "memory": self.memory_info(),
            "cpu": self.cpu_info(),
            "network": self.network_info(),
            "process": self.process_info(),
        }
        return snap

    def collect(self) -> Dict[str, Any]:
        """
        采集快照并存入历史

        返回:
            Dict: 当前采集的快照数据
        """
        snap = self.snapshot()
        with self._lock:
            self._history.append(snap)
            if len(self._history) > self._max_history:
                self._history = self._history[-self._max_history:]
        self._check_thresholds(snap)
        return snap

    def get_history(self, n: int = 20) -> List[Dict[str, Any]]:
        """获取最近 N 次快照"""
        with self._lock:
            return self._history[-n:]

    def clear_history(self) -> int:
        """清除历史快照"""
        with self._lock:
            count = len(self._history)
            self._history.clear()
            return count

    # ─── 阈值检查 ──────────────────────────────

    def _check_thresholds(self, snap: Dict[str, Any]) -> List[str]:
        """检查监控指标是否超过阈值，触发告警"""
        alerts = []

        disk_pct = snap.get("disk", {}).get("percent", 0)
        if disk_pct > MONITOR_DISK_THRESHOLD_PCT:
            msg = f"磁盘使用率告警: {disk_pct}% > {MONITOR_DISK_THRESHOLD_PCT}%"
            alerts.append(msg)
            logger.warning(msg)

        mem_pct = snap.get("memory", {}).get("percent", 0)
        if mem_pct > MONITOR_MEMORY_THRESHOLD_PCT:
            msg = f"内存使用率告警: {mem_pct}% > {MONITOR_MEMORY_THRESHOLD_PCT}%"
            alerts.append(msg)
            logger.warning(msg)

        cpu_pct = snap.get("cpu", {}).get("percent", 0)
        if cpu_pct > MONITOR_CPU_THRESHOLD_PCT:
            msg = f"CPU 使用率告警: {cpu_pct}% > {MONITOR_CPU_THRESHOLD_PCT}%"
            alerts.append(msg)
            logger.warning(msg)

        if alerts:
            for callback in self._alert_callbacks:
                try:
                    callback(alerts, snap)
                except Exception as e:
                    logger.error(f"告警回调执行失败: {e}")

        return alerts

    def register_alert_callback(self, callback: callable) -> None:
        """注册告警回调函数"""
        self._alert_callbacks.append(callback)

    def check_now(self) -> Dict[str, Any]:
        """立即执行一次完整检查"""
        snap = self.collect()
        alerts = self._check_thresholds(snap)
        return {
            "snapshot": snap,
            "alerts": alerts,
            "alert_count": len(alerts),
            "is_healthy": len(alerts) == 0,
        }

    # ─── 健康度评分 ────────────────────────────

    def health_score(self) -> Dict[str, Any]:
        """
        计算系统综合健康度评分 (0-100)

        评分维度：
          - 磁盘使用 (30分): 使用率越低越好
          - 内存使用 (30分): 使用率越低越好
          - CPU 使用 (20分): 使用率越低越好
          - 系统稳定性 (20分): 无告警得分
        """
        snap = self.snapshot()

        disk_pct = snap.get("disk", {}).get("percent", 100)
        disk_score = max(0, 30 - (disk_pct / 100) * 30)

        mem_pct = snap.get("memory", {}).get("percent", 100)
        mem_score = max(0, 30 - (mem_pct / 100) * 30)

        cpu_pct = snap.get("cpu", {}).get("percent", 100)
        cpu_score = max(0, 20 - (cpu_pct / 100) * 20)

        alerts = self._check_thresholds(snap)
        stability_score = max(0, 20 - len(alerts) * 5)

        total = round(disk_score + mem_score + cpu_score + stability_score, 1)
        grade = "A" if total >= 80 else "B" if total >= 60 else "C" if total >= 40 else "D"

        return {
            "total_score": total,
            "grade": grade,
            "disk_score": round(disk_score, 1),
            "memory_score": round(mem_score, 1),
            "cpu_score": round(cpu_score, 1),
            "stability_score": round(stability_score, 1),
            "alerts": alerts,
            "timestamp": snap["timestamp_formatted"],
        }

    # ─── 后台采集 ──────────────────────────────

    def start_background_collection(self, interval: int = MONITOR_COLLECTION_INTERVAL) -> None:
        """启动后台定时采集"""
        if self._running:
            logger.warning("后台采集已在运行中")
            return

        self._running = True

        def _collect_loop():
            logger.info(f"后台监控采集启动，间隔={interval}秒")
            while self._running:
                try:
                    self.collect()
                except Exception as e:
                    logger.error(f"后台采集异常: {e}")
                time.sleep(interval)

        self._collection_thread = threading.Thread(target=_collect_loop, daemon=True)
        self._collection_thread.start()

    def stop_background_collection(self) -> None:
        """停止后台采集"""
        self._running = False
        if self._collection_thread:
            self._collection_thread.join(timeout=5)
        logger.info("后台监控采集已停止")

    def is_collecting(self) -> bool:
        """是否正在后台采集"""
        return self._running and (self._collection_thread is not None and self._collection_thread.is_alive())

    # ─── 汇总 ────────────────────────────────

    def summary(self) -> Dict[str, Any]:
        """生成监控摘要"""
        snap = self.snapshot()
        health = self.health_score()
        return {
            "snapshot": {
                "disk_percent": snap["disk"]["percent"],
                "disk_free_gb": snap["disk"]["free_gb"],
                "memory_percent": snap["memory"].get("percent", "N/A"),
                "cpu_percent": snap["cpu"].get("percent", "N/A"),
                "uptime_seconds": snap["process"]["uptime_seconds"],
                "timestamp": snap["timestamp_formatted"],
            },
            "health": health,
            "history_count": len(self._history),
            "is_collecting": self.is_collecting(),
        }


# 全局监控器实例
system_monitor = SystemMonitor()
