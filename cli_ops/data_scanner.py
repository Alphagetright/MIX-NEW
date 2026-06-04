# -*- coding: utf-8 -*-
"""
数据目录扫描器
==============
服务器数据目录扫描、文件清单生成、完整性检查、变更检测。

特性：
  - 按扩展名递归扫描
  - 文件大小与修改时间统计
  - JSON 有效性快速检测
  - 新旧文件变更对比
  - 大文件/异常文件标记
  - 扫描结果缓存
"""

import os
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

from .config import (
    SCANNER_FILE_EXTENSIONS,
    SCANNER_MAX_FILE_SIZE_MB,
    SCANNER_RECURSIVE,
    SCANNER_SKIP_HIDDEN,
)
from .logger import get_logger
from .models import FileInfo, ScanResult
from .cache_manager import memory_cache

logger = get_logger("data_scanner")


# ============================================================================
# 文件信息收集
# ============================================================================


def get_file_info(file_path: str, check_json: bool = True) -> FileInfo:
    """
    获取单个文件的详细元信息

    参数:
        file_path: 文件绝对路径
        check_json: 是否检测 JSON 有效性

    返回:
        FileInfo: 文件元信息对象
    """
    info = FileInfo()
    info.path = file_path
    info.name = os.path.basename(file_path)
    info.extension = os.path.splitext(file_path)[1].lower()

    try:
        stat = os.stat(file_path)
        info.size = stat.st_size
        info.modified = stat.st_mtime
        info.age_days = int((time.time() - stat.st_mtime) / 86400)
    except OSError:
        return info

    # 检测 JSON 有效性
    if check_json and info.extension in (".json", ".txt"):
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read(1024 * 1024)  # 只读前 1MB 检测
            import json
            json.loads(content)
            info.is_valid_json = True
        except (json.JSONDecodeError, UnicodeDecodeError):
            info.is_valid_json = False

    # 粗略行数统计（仅对小文件准确）
    if info.size < 100 * 1024 * 1024:  # < 100MB
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                info.line_count = sum(1 for _ in f)
        except (OSError, UnicodeDecodeError):
            pass

    return info


# ============================================================================
# 目录扫描
# ============================================================================


def scan_directory(directory: str,
                   extensions: Optional[List[str]] = None,
                   recursive: bool = True,
                   check_json: bool = True,
                   skip_hidden: bool = True) -> ScanResult:
    """
    扫描目录，生成完整文件清单

    参数:
        directory: 要扫描的目录路径
        extensions: 文件扩展名过滤列表
        recursive: 是否递归搜索
        check_json: 是否检测 JSON 有效性
        skip_hidden: 是否跳过隐藏文件

    返回:
        ScanResult: 扫描结果对象
    """
    start_time = time.time()
    result = ScanResult(directory=os.path.abspath(directory))

    if extensions is None:
        extensions = SCANNER_FILE_EXTENSIONS

    if not os.path.exists(directory):
        result.errors.append(f"目录不存在: {directory}")
        return result

    if not os.path.isdir(directory):
        result.errors.append(f"路径不是目录: {directory}")
        return result

    try:
        files_to_scan = []
        if recursive:
            for root, dirs, filenames in os.walk(directory):
                if skip_hidden:
                    dirs[:] = [d for d in dirs if not d.startswith(".")]
                for fname in filenames:
                    if skip_hidden and fname.startswith("."):
                        continue
                    ext = os.path.splitext(fname)[1].lower()
                    if extensions is None or ext in extensions:
                        files_to_scan.append(os.path.join(root, fname))
        else:
            for fname in sorted(os.listdir(directory)):
                full = os.path.join(directory, fname)
                if os.path.isfile(full):
                    if skip_hidden and fname.startswith("."):
                        continue
                    ext = os.path.splitext(fname)[1].lower()
                    if extensions is None or ext in extensions:
                        files_to_scan.append(full)

        result.total_files = len(files_to_scan)

        for file_path in files_to_scan:
            try:
                # 检查文件大小是否超限
                file_size = os.path.getsize(file_path)
                max_bytes = SCANNER_MAX_FILE_SIZE_MB * 1024 * 1024
                if file_size > max_bytes:
                    result.skipped_count += 1
                    logger.warning(f"跳过大文件: {file_path} ({file_size / (1024**2):.1f}MB)")
                    continue

                info = get_file_info(file_path, check_json=check_json)
                result.files.append(info)
                result.total_size += info.size
            except Exception as e:
                result.errors.append(f"扫描文件失败 [{file_path}]: {e}")
                if len(result.errors) >= 1000:
                    result.errors.append("... 达到最大错误数限制")
                    break

    except Exception as e:
        result.errors.append(f"扫描过程异常: {e}")
        logger.error(f"目录扫描异常: {e}")

    result.scan_time = round(time.time() - start_time, 2)
    logger.info(
        f"目录扫描完成: {result.total_files} 个文件, "
        f"{result.size_formatted}, 耗时 {result.scan_time}s"
    )
    return result


# ============================================================================
# 统计与分类
# ============================================================================


def classify_files_by_type(scan_result: ScanResult) -> Dict[str, List[FileInfo]]:
    """按文件扩展名分类"""
    groups: Dict[str, List[FileInfo]] = {}
    for f in scan_result.files:
        ext = f.extension or "无扩展名"
        if ext not in groups:
            groups[ext] = []
        groups[ext].append(f)
    return groups


def classify_files_by_size(scan_result: ScanResult) -> Dict[str, List[FileInfo]]:
    """
    按文件大小分类

    分类: tiny (<1KB), small (<100KB), medium (<1MB), large (<10MB), huge (>=10MB)
    """
    groups = {"tiny": [], "small": [], "medium": [], "large": [], "huge": []}
    for f in scan_result.files:
        kb = f.size / 1024
        if kb < 1:
            groups["tiny"].append(f)
        elif kb < 100:
            groups["small"].append(f)
        elif kb < 1024:
            groups["medium"].append(f)
        elif kb < 10240:
            groups["large"].append(f)
        else:
            groups["huge"].append(f)
    return groups


def classify_files_by_age(scan_result: ScanResult) -> Dict[str, List[FileInfo]]:
    """
    按文件年龄分类

    分类: recent (<7天), week_old (<30天), month_old (<90天), old (>=90天)
    """
    groups = {"recent": [], "week_old": [], "month_old": [], "old": []}
    for f in scan_result.files:
        if f.age_days < 7:
            groups["recent"].append(f)
        elif f.age_days < 30:
            groups["week_old"].append(f)
        elif f.age_days < 90:
            groups["month_old"].append(f)
        else:
            groups["old"].append(f)
    return groups


def get_scan_summary(scan_result: ScanResult) -> Dict[str, Any]:
    """
    生成扫描摘要报告

    返回:
        Dict: 包含分类统计的摘要信息
    """
    type_groups = classify_files_by_type(scan_result)
    size_groups = classify_files_by_size(scan_result)
    age_groups = classify_files_by_age(scan_result)

    invalid_json_count = sum(1 for f in scan_result.files if not f.is_valid_json)

    return {
        "scan_time": scan_result.scan_time,
        "total_files": scan_result.total_files,
        "total_size_formatted": scan_result.size_formatted,
        "skipped_count": scan_result.skipped_count,
        "error_count": len(scan_result.errors),
        "by_extension": {k: len(v) for k, v in type_groups.items()},
        "by_size": {k: len(v) for k, v in size_groups.items()},
        "by_age": {k: len(v) for k, v in age_groups.items()},
        "invalid_json_count": invalid_json_count,
        "largest_file": max(scan_result.files, key=lambda f: f.size).name if scan_result.files else "N/A",
        "oldest_file": max(scan_result.files, key=lambda f: f.age_days).name if scan_result.files else "N/A",
    }


# ============================================================================
# 变更检测
# ============================================================================


class ChangeDetector:
    """
    文件变更检测器

    对比两次扫描结果，检测文件的增删改。

    Usage:
        detector = ChangeDetector()
        result1 = detector.snapshot(scan_directory("/data"))
        # ... 一段时间后 ...
        result2 = detector.snapshot(scan_directory("/data"))
        changes = detector.compare()
    """

    def __init__(self):
        self._previous: Optional[Dict[str, float]] = None  # {path: mtime}
        self._current: Optional[Dict[str, float]] = None

    def snapshot(self, scan_result: ScanResult) -> None:
        """记录扫描快照"""
        self._previous = self._current
        self._current = {
            f.path: f.modified for f in scan_result.files
        }

    def compare(self) -> Dict[str, List[str]]:
        """
        比较两次快照，检测变更

        返回:
            Dict: {"added": [...], "removed": [...], "modified": [...], "unchanged": int}
        """
        if not self._previous or not self._current:
            return {"added": [], "removed": [], "modified": [], "unchanged": 0}

        prev_set = set(self._previous.keys())
        curr_set = set(self._current.keys())

        added = sorted(curr_set - prev_set)
        removed = sorted(prev_set - curr_set)

        modified = []
        unchanged = 0
        for path in prev_set & curr_set:
            if self._previous[path] != self._current[path]:
                modified.append(path)
            else:
                unchanged += 1

        return {
            "added": added,
            "removed": removed,
            "modified": sorted(modified),
            "unchanged": unchanged,
        }


# 全局变更检测器
change_detector = ChangeDetector()
