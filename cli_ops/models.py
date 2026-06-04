# -*- coding: utf-8 -*-
"""
数据模型模块
============
定义系统的核心数据模型类，使用 Python dataclass 实现。

模型层次：
  - FileInfo: 文件元信息
  - ScanResult: 目录扫描结果
  - ExportRecord: 导出记录
  - CacheEntry: 缓存条目
  - MonitorSnapshot: 监控快照
  - HealthStatus: 健康状态
  - BatchTask: 批处理任务
  - BatchResult: 批处理结果
  - SystemStatus: 系统综合状态
"""

import json
import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Union


# ============================================================================
# 文件信息模型
# ============================================================================


@dataclass
class FileInfo:
    """
    文件元信息

    Attributes:
        path: 文件绝对路径
        name: 文件名
        size: 文件大小（字节）
        modified: 最后修改时间戳
        extension: 文件扩展名
        age_days: 文件年龄（天）
        is_valid_json: 是否为有效 JSON
        line_count: 文件行数
    """
    path: str = ""
    name: str = ""
    size: int = 0
    modified: float = 0.0
    extension: str = ""
    age_days: int = 0
    is_valid_json: bool = False
    line_count: int = 0

    @property
    def size_formatted(self) -> str:
        from .utils import format_file_size
        return format_file_size(self.size)

    @property
    def modified_formatted(self) -> str:
        if self.modified:
            return datetime.fromtimestamp(self.modified).strftime("%Y-%m-%d %H:%M:%S")
        return "未知"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ============================================================================
# 扫描结果模型
# ============================================================================


@dataclass
class ScanResult:
    """
    目录扫描结果

    Attributes:
        directory: 扫描的目录路径
        total_files: 文件总数
        total_size: 总大小（字节）
        files: 文件信息列表
        scan_time: 扫描耗时（秒）
        errors: 扫描过程中遇到的错误
        skipped_count: 跳过的文件数
    """
    directory: str = ""
    total_files: int = 0
    total_size: int = 0
    files: List[FileInfo] = field(default_factory=list)
    scan_time: float = 0.0
    errors: List[str] = field(default_factory=list)
    skipped_count: int = 0

    @property
    def size_formatted(self) -> str:
        from .utils import format_file_size
        return format_file_size(self.total_size)

    @property
    def success_rate(self) -> float:
        if self.total_files == 0:
            return 100.0
        return round((self.total_files - len(self.errors)) / self.total_files * 100, 1)

    def summary(self) -> Dict[str, Any]:
        return {
            "directory": self.directory,
            "total_files": self.total_files,
            "total_size_formatted": self.size_formatted,
            "scan_time_seconds": round(self.scan_time, 2),
            "error_count": len(self.errors),
            "skipped_count": self.skipped_count,
            "success_rate_pct": self.success_rate,
        }

    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result["files"] = [f.to_dict() for f in self.files[:100]]
        return result


# ============================================================================
# 导出记录模型
# ============================================================================


@dataclass
class ExportRecord:
    """
    导出操作记录

    Attributes:
        id: 导出唯一标识
        format: 导出格式 (csv/json/xml/txt/html)
        file_path: 导出的文件路径
        file_size: 文件大小（字节）
        rows_exported: 导出的数据行数
        columns_exported: 导出的列数
        created_at: 创建时间戳
        duration: 导出耗时（秒）
        status: 状态 (success/failed/partial)
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    format: str = ""
    file_path: str = ""
    file_size: int = 0
    rows_exported: int = 0
    columns_exported: int = 0
    created_at: float = field(default_factory=time.time)
    duration: float = 0.0
    status: str = "success"
    error_message: str = ""

    @property
    def file_name(self) -> str:
        import os
        return os.path.basename(self.file_path)

    @property
    def created_formatted(self) -> str:
        return datetime.fromtimestamp(self.created_at).strftime("%Y-%m-%d %H:%M:%S")

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["file_name"] = self.file_name
        d["created_formatted"] = self.created_formatted
        return d


# ============================================================================
# 缓存条目模型
# ============================================================================


@dataclass
class CacheEntry:
    """
    缓存条目

    Attributes:
        key: 缓存键
        value: 缓存值
        created_at: 创建时间戳
        ttl: 生存时间（秒）
        access_count: 被访问次数
        last_accessed: 最后访问时间
        size_bytes: 序列化后的字节大小
    """
    key: str = ""
    value: Any = None
    created_at: float = field(default_factory=time.time)
    ttl: int = 600
    access_count: int = 0
    last_accessed: float = 0.0
    size_bytes: int = 0

    @property
    def is_expired(self) -> bool:
        return (time.time() - self.created_at) > self.ttl

    @property
    def age_seconds(self) -> float:
        return time.time() - self.created_at

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["is_expired"] = self.is_expired
        d["age_seconds"] = round(self.age_seconds, 1)
        d["value"] = str(self.value)[:200]  # 截断显示
        return d


# ============================================================================
# 监控快照模型
# ============================================================================


@dataclass
class MonitorSnapshot:
    """
    系统监控快照

    Attributes:
        timestamp: 采集时间戳
        cpu_percent: CPU 使用率 (%)
        memory_percent: 内存使用率 (%)
        memory_used_gb: 已用内存 (GB)
        memory_total_gb: 总内存 (GB)
        disk_percent: 磁盘使用率 (%)
        disk_used_gb: 已用磁盘 (GB)
        disk_total_gb: 总磁盘 (GB)
        network_bytes_sent: 网络发送字节数
        network_bytes_recv: 网络接收字节数
        process_count: 当前进程数
        python_version: Python 版本
        uptime_seconds: 系统运行时间
    """
    timestamp: float = field(default_factory=time.time)
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    memory_used_gb: float = 0.0
    memory_total_gb: float = 0.0
    disk_percent: float = 0.0
    disk_used_gb: float = 0.0
    disk_total_gb: float = 0.0
    network_bytes_sent: int = 0
    network_bytes_recv: int = 0
    process_count: int = 0
    python_version: str = ""
    uptime_seconds: float = 0.0

    @property
    def timestamp_formatted(self) -> str:
        return datetime.fromtimestamp(self.timestamp).strftime("%Y-%m-%d %H:%M:%S")

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["timestamp_formatted"] = self.timestamp_formatted
        return d


# ============================================================================
# 健康状态模型
# ============================================================================


@dataclass
class HealthStatus:
    """
    系统健康状态

    Attributes:
        is_healthy: 系统是否健康
        check_timestamp: 检查时间戳
        issues: 问题列表
        warnings: 警告列表
        recommendations: 建议操作列表
        check_duration: 检查耗时（秒）
        checks_passed: 通过的检查数
        checks_total: 总检查数
    """
    is_healthy: bool = True
    check_timestamp: float = field(default_factory=time.time)
    issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    check_duration: float = 0.0
    checks_passed: int = 0
    checks_total: int = 0

    @property
    def status_text(self) -> str:
        if self.is_healthy:
            return "健康"
        if len(self.issues) > 0:
            return f"异常 ({len(self.issues)}个问题)"
        return f"警告 ({len(self.warnings)}个警告)"

    @property
    def passed_rate(self) -> float:
        if self.checks_total == 0:
            return 100.0
        return round(self.checks_passed / self.checks_total * 100, 1)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["status_text"] = self.status_text
        d["passed_rate"] = self.passed_rate
        return d


# ============================================================================
# 批处理模型
# ============================================================================


@dataclass
class BatchTask:
    """
    批处理任务

    Attributes:
        id: 任务唯一标识
        name: 任务名称
        command: 执行的命令
        args: 命令参数
        status: 状态 (pending/running/completed/failed/timeout)
        created_at: 创建时间
        started_at: 开始时间
        completed_at: 完成时间
        result: 任务结果
        error: 错误信息
        retry_count: 重试次数
        max_retries: 最大重试次数
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    command: str = ""
    args: Dict[str, Any] = field(default_factory=dict)
    status: str = "pending"
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    result: Any = None
    error: str = ""
    retry_count: int = 0
    max_retries: int = 3

    @property
    def duration_seconds(self) -> Optional[float]:
        if self.started_at and self.completed_at:
            return round(self.completed_at - self.started_at, 2)
        return None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["duration_seconds"] = self.duration_seconds
        return d


@dataclass
class BatchResult:
    """
    批处理执行结果

    Attributes:
        tasks: 所有任务列表
        total: 总任务数
        completed: 完成数
        failed: 失败数
        timeout: 超时数
        started_at: 批处理开始时间
        completed_at: 批处理完成时间
        total_duration: 总耗时（秒）
    """
    tasks: List[BatchTask] = field(default_factory=list)
    total: int = 0
    completed: int = 0
    failed: int = 0
    timeout: int = 0
    started_at: float = 0.0
    completed_at: float = 0.0

    @property
    def total_duration(self) -> float:
        return round(self.completed_at - self.started_at, 2)

    @property
    def success_rate(self) -> float:
        if self.total == 0:
            return 100.0
        return round(self.completed / self.total * 100, 1)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total": self.total,
            "completed": self.completed,
            "failed": self.failed,
            "timeout": self.timeout,
            "success_rate_pct": self.success_rate,
            "total_duration_seconds": self.total_duration,
            "tasks": [t.to_dict() for t in self.tasks[:50]],
        }


# ============================================================================
# 系统状态模型
# ============================================================================


@dataclass
class SystemStatus:
    """
    系统综合状态

    汇总系统运行的全部关键信息。
    """
    checked_at: float = field(default_factory=time.time)
    version: str = "1.0.0"
    python_version: str = ""
    platform: str = ""
    data_dir_exists: bool = False
    data_file_count: int = 0
    data_total_size_gb: float = 0.0
    export_files_count: int = 0
    cache_entries_count: int = 0
    log_files_count: int = 0
    rag_db_exists: bool = False
    disk_free_gb: float = 0.0
    memory_available_gb: float = 0.0
    cpu_percent: float = 0.0
    health: Optional[HealthStatus] = None

    @property
    def checked_at_formatted(self) -> str:
        return datetime.fromtimestamp(self.checked_at).strftime("%Y-%m-%d %H:%M:%S")

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["checked_at_formatted"] = self.checked_at_formatted
        if self.health:
            d["health"] = self.health.to_dict()
        return d

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
