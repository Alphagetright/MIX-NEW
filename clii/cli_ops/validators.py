# -*- coding: utf-8 -*-
"""
输入校验模块
============
提供命令行参数、文件路径、数据格式等各类输入的校验函数。
所有校验函数抛出 ValidationError 或返回 (bool, str) 元组。
"""

import os
import re
from typing import Any, Dict, List, Optional, Tuple, Union


def validate_non_empty(value: str, field_name: str = "值") -> Tuple[bool, str]:
    """
    校验字符串非空

    返回:
        Tuple[bool, str]: (是否通过, 错误消息)
    """
    if not value or not str(value).strip():
        return False, f"{field_name} 不能为空"
    return True, ""


def validate_length(value: str, min_len: int = 0, max_len: int = 10000,
                    field_name: str = "值") -> Tuple[bool, str]:
    """校验字符串长度"""
    v = str(value)
    if len(v) < min_len:
        return False, f"{field_name} 长度不能少于 {min_len} 个字符"
    if len(v) > max_len:
        return False, f"{field_name} 长度不能超过 {max_len} 个字符"
    return True, ""


def validate_regex(value: str, pattern: str, field_name: str = "值") -> Tuple[bool, str]:
    """正则表达式校验"""
    if not re.match(pattern, str(value)):
        return False, f"{field_name} 格式不匹配 (期望格式: {pattern})"
    return True, ""


def validate_file_path(file_path: str, must_exist: bool = False,
                       must_be_file: bool = False,
                       must_be_dir: bool = False) -> Tuple[bool, str]:
    """
    校验文件路径

    参数:
        file_path: 文件/目录路径
        must_exist: 是否必须存在
        must_be_file: 是否必须是文件
        must_be_dir: 是否必须是目录

    返回:
        Tuple[bool, str]: (是否通过, 错误消息)
    """
    path = str(file_path)
    if not path:
        return False, "路径不能为空"

    # 安全检查：禁止包含危险字符
    dangerous_chars = ["..", "|", ";", "&", "$", "`"]
    for char in dangerous_chars:
        if char in path:
            return False, f"路径包含禁止字符: {char}"

    if must_exist and not os.path.exists(path):
        return False, f"路径不存在: {path}"
    if must_be_file and os.path.exists(path) and not os.path.isfile(path):
        return False, f"路径不是文件: {path}"
    if must_be_dir and os.path.exists(path) and not os.path.isdir(path):
        return False, f"路径不是目录: {path}"

    return True, ""


def validate_file_extension(filename: str,
                            allowed_extensions: Optional[List[str]] = None) -> Tuple[bool, str]:
    """校验文件扩展名"""
    if allowed_extensions is None:
        return True, ""
    ext = os.path.splitext(str(filename))[1].lower()
    allowed_lower = [e.lower() for e in allowed_extensions]
    if ext not in allowed_lower:
        return False, f"不支持的文件格式: {ext} (允许: {', '.join(allowed_lower)})"
    return True, ""


def validate_file_size(file_path: str,
                       max_bytes: int = 500 * 1024 * 1024) -> Tuple[bool, str]:
    """校验文件大小不超过上限"""
    if not os.path.exists(file_path):
        return False, f"文件不存在: {file_path}"
    actual = os.path.getsize(file_path)
    if actual > max_bytes:
        from .utils import format_file_size
        return False, (
            f"文件过大: {format_file_size(actual)} "
            f"(最大允许: {format_file_size(max_bytes)})"
        )
    return True, ""


def validate_export_format(fmt: str) -> Tuple[bool, str]:
    """
    校验导出格式

    支持的格式: csv, json, xml, txt, html, report
    """
    supported = {"csv", "json", "xml", "txt", "html", "report"}
    fmt_lower = str(fmt).lower().strip()
    if fmt_lower not in supported:
        return False, f"不支持的导出格式: {fmt} (支持: {', '.join(sorted(supported))})"
    return True, ""


def validate_command_name(command: str) -> Tuple[bool, str]:
    """校验命令名称"""
    valid_commands = {
        "help", "status", "scan", "export", "clear-cache",
        "list-exports", "check-rag", "build-rag", "test",
        "health", "report", "batch", "config-info",
        "clean-logs", "backup",
    }
    if command not in valid_commands:
        suggestions = [c for c in valid_commands if command in c or c.startswith(command[:2])]
        hint = f" 你可能想用: {', '.join(suggestions)}" if suggestions else ""
        return False, (
            f"未知命令: {command} (有效命令: {', '.join(sorted(valid_commands))}){hint}"
        )
    return True, ""


def validate_email(email: str) -> Tuple[bool, str]:
    """校验邮箱格式"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, str(email)):
        return False, "邮箱格式不正确"
    return True, ""


def validate_ip_address(ip: str) -> Tuple[bool, str]:
    """校验 IPv4 地址格式"""
    pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
    if not re.match(pattern, str(ip)):
        return False, "IP 地址格式不正确"
    parts = ip.split(".")
    for part in parts:
        if not 0 <= int(part) <= 255:
            return False, f"IP 地址段超出范围: {part}"
    return True, ""


def validate_port(port: Union[int, str]) -> Tuple[bool, str]:
    """校验端口号"""
    try:
        p = int(port)
    except (ValueError, TypeError):
        return False, "端口号必须是整数"
    if not 1 <= p <= 65535:
        return False, "端口号范围: 1-65535"
    return True, ""


def validate_integer_range(value: Union[int, str], min_val: int = 0,
                           max_val: int = 999999, field_name: str = "值") -> Tuple[bool, str]:
    """校验整数范围"""
    try:
        v = int(value)
    except (ValueError, TypeError):
        return False, f"{field_name} 必须是整数"
    if v < min_val:
        return False, f"{field_name} 不能小于 {min_val}"
    if v > max_val:
        return False, f"{field_name} 不能大于 {max_val}"
    return True, ""


def validate_batch_size(size: Union[int, str], max_val: int = 10000) -> Tuple[bool, str]:
    """校验批处理大小"""
    return validate_integer_range(size, min_val=1, max_val=max_val, field_name="批处理大小")


def validate_thread_count(count: Union[int, str]) -> Tuple[bool, str]:
    """校验线程数"""
    import multiprocessing
    cpu_count = multiprocessing.cpu_count()
    return validate_integer_range(
        count, min_val=1, max_val=cpu_count * 4, field_name="线程数"
    )


def validate_json_structure(data: Any, required_keys: Optional[List[str]] = None) -> Tuple[bool, str]:
    """
    校验 JSON 数据结构

    参数:
        data: JSON 数据（dict）
        required_keys: 必须存在的键列表

    返回:
        Tuple[bool, str]: (是否通过, 错误消息)
    """
    if not isinstance(data, dict):
        return False, "数据必须为 JSON 对象（dict）"
    if required_keys:
        missing = [k for k in required_keys if k not in data]
        if missing:
            return False, f"缺少必要字段: {', '.join(missing)}"
    return True, ""


def sanitize_html(text: str) -> str:
    """
    清理 HTML 标签，保留纯文本

    用于防止 XSS 注入。
    """
    clean = re.sub(r"<[^>]*>", "", str(text))
    clean = clean.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    clean = clean.replace('"', "&quot;").replace("'", "&#x27;")
    return clean
