# -*- coding: utf-8 -*-
"""输入校验模块 — 14个校验函数"""

import os, re
from typing import Any, List, Optional, Tuple, Union


def validate_non_empty(value: str, field_name: str = "值") -> Tuple[bool, str]:
    if not value or not str(value).strip():
        return False, f"{field_name} 不能为空"
    return True, ""


def validate_length(value: str, min_len: int = 0, max_len: int = 10000,
                    field_name: str = "值") -> Tuple[bool, str]:
    v = str(value)
    if len(v) < min_len:
        return False, f"{field_name} 长度不能少于 {min_len} 个字符"
    if len(v) > max_len:
        return False, f"{field_name} 长度不能超过 {max_len} 个字符"
    return True, ""


def validate_regex(value: str, pattern: str, field_name: str = "值") -> Tuple[bool, str]:
    if not re.match(pattern, str(value)):
        return False, f"{field_name} 格式不匹配 (期望: {pattern})"
    return True, ""


def validate_file_path(file_path: str, must_exist: bool = False,
                       must_be_file: bool = False, must_be_dir: bool = False) -> Tuple[bool, str]:
    path = str(file_path)
    if not path:
        return False, "路径不能为空"
    for char in ["..", "|", ";", "&", "$", "`"]:
        if char in path:
            return False, f"路径包含禁止字符: {char}"
    if must_exist and not os.path.exists(path):
        return False, f"路径不存在: {path}"
    if must_be_file and os.path.exists(path) and not os.path.isfile(path):
        return False, f"路径不是文件: {path}"
    if must_be_dir and os.path.exists(path) and not os.path.isdir(path):
        return False, f"路径不是目录: {path}"
    return True, ""


def validate_file_extension(filename: str, allowed: Optional[List[str]] = None) -> Tuple[bool, str]:
    if allowed is None:
        return True, ""
    ext = os.path.splitext(str(filename))[1].lower()
    if ext not in [e.lower() for e in allowed]:
        return False, f"不支持的文件格式: {ext} (允许: {', '.join(allowed)})"
    return True, ""


def validate_export_format(fmt: str) -> Tuple[bool, str]:
    supported = {"csv", "json", "html", "txt"}
    if str(fmt).lower().strip() not in supported:
        return False, f"不支持的导出格式: {fmt} (支持: {', '.join(sorted(supported))})"
    return True, ""


def validate_integer_range(value: Union[int, str], min_val: int = 0,
                           max_val: int = 999999, field_name: str = "值") -> Tuple[bool, str]:
    try:
        v = int(value)
    except (ValueError, TypeError):
        return False, f"{field_name} 必须是整数"
    if v < min_val or v > max_val:
        return False, f"{field_name} 超出范围 [{min_val}, {max_val}]"
    return True, ""


def validate_poem_id(poem_id: str) -> Tuple[bool, str]:
    if not poem_id or not poem_id.strip():
        return False, "诗歌编号不能为空"
    if not re.match(r"^P?\d+", poem_id.strip()):
        return False, "诗歌编号格式应为 P+数字"
    return True, ""


def validate_json_structure(data: Any, required_keys: Optional[List[str]] = None) -> Tuple[bool, str]:
    if not isinstance(data, dict):
        return False, "数据必须为 dict 类型"
    if required_keys:
        missing = [k for k in required_keys if k not in data]
        if missing:
            return False, f"缺少必要字段: {', '.join(missing)}"
    return True, ""


def sanitize_input(text: str, max_length: int = 2000) -> str:
    """清理用户输入，防止注入和过长输入"""
    clean = re.sub(r"<[^>]*>", "", str(text))
    clean = clean.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return clean[:max_length]
