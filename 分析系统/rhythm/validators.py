# -*- coding: utf-8 -*-
"""
古典诗词音韵格律分析引擎 — 输入校验模块
"""
import os
import re
from typing import Any, List, Optional, Tuple


def validate_non_empty(value: Any, field_name: str = "值") -> Tuple[bool, str]:
    if value is None or (isinstance(value, str) and not value.strip()):
        return False, f"{field_name}不能为空"
    return True, ""


def validate_length(
    value: str, min_len: int = 1, max_len: int = None, field_name: str = "字符串"
) -> Tuple[bool, str]:
    text = str(value).strip()
    if len(text) < min_len:
        return False, f"{field_name}长度不能少于{min_len}个字符"
    if max_len and len(text) > max_len:
        return False, f"{field_name}长度不能超过{max_len}个字符"
    return True, ""


def validate_file_path(
    file_path: str,
    must_exist: bool = True,
    must_be_file: bool = True,
) -> Tuple[bool, str]:
    if must_exist and not os.path.exists(file_path):
        return False, f"文件不存在: {file_path}"
    if must_be_file and os.path.exists(file_path) and not os.path.isfile(file_path):
        return False, f"不是一个文件: {file_path}"
    return True, ""


def validate_directory(dir_path: str, must_exist: bool = True) -> Tuple[bool, str]:
    if must_exist and not os.path.isdir(dir_path):
        return False, f"目录不存在: {dir_path}"
    return True, ""


def validate_file_extension(
    filename: str,
    allowed: List[str] = None,
) -> Tuple[bool, str]:
    allowed = allowed or [".json", ".txt", ".csv"]
    _, ext = os.path.splitext(filename)
    if ext.lower() not in [a.lower() for a in allowed]:
        return False, f"不支持的文件扩展名: {ext}，允许: {', '.join(allowed)}"
    return True, ""


def validate_integer_range(
    value: Any,
    min_val: int = None,
    max_val: int = None,
    field_name: str = "值",
) -> Tuple[bool, str]:
    try:
        v = int(value)
    except (ValueError, TypeError):
        return False, f"{field_name}必须是整数"
    if min_val is not None and v < min_val:
        return False, f"{field_name}不能小于{min_val}"
    if max_val is not None and v > max_val:
        return False, f"{field_name}不能大于{max_val}"
    return True, ""


def validate_poem_text(text: str) -> Tuple[bool, str]:
    """校验诗歌原文：必须包含至少5个汉字"""
    ok, err = validate_non_empty(text, "诗歌原文")
    if not ok:
        return False, err
    chinese = sum(1 for c in text if "一" <= c <= "鿿")
    if chinese < 5:
        return False, f"诗歌原文至少需要5个汉字，当前{chinese}个"
    return True, ""


def validate_poem_lines(lines: List[str]) -> Tuple[bool, str]:
    """校验诗句列表"""
    if not lines:
        return False, "诗句列表不能为空"
    if len(lines) < 2:
        return False, f"至少需要2句诗，当前{len(lines)}句"
    for i, line in enumerate(lines):
        ok, err = validate_non_empty(line, f"第{i+1}句")
        if not ok:
            return False, err
    return True, ""


def validate_form_name(form: str) -> Tuple[bool, str]:
    """校验格律体裁名称"""
    valid_forms = {
        "五绝", "七绝", "五律", "七律", "五排", "七排",
        "五言绝句", "七言绝句", "五言律诗", "七言律诗",
        "wujue", "qijue", "wulv", "qilv",
    }
    if form not in valid_forms:
        return False, f"不支持的格律体裁: {form}，支持: {', '.join(sorted(valid_forms))}"
    return True, ""


def validate_yunbu_name(name: str) -> Tuple[bool, str]:
    """校验韵部名称（单汉字）"""
    if not name or len(name) != 1 or not ("一" <= name <= "鿿"):
        return False, f"无效的韵部名称: {name}（应为单个汉字）"
    return True, ""


def validate_tone_label(tone: str) -> Tuple[bool, str]:
    """校验声调标签"""
    valid = {"平", "仄", "入", "unknown", "未知"}
    if tone not in valid:
        return False, f"无效的声调标签: {tone}，支持: {', '.join(valid)}"
    return True, ""


def validate_export_format(fmt: str) -> Tuple[bool, str]:
    valid = {"text", "json", "html", "csv"}
    if fmt.lower() not in valid:
        return False, f"不支持的导出格式: {fmt}，支持: {', '.join(valid)}"
    return True, ""


def sanitize_html(text: str) -> str:
    text = text.replace("&", "&amp;")
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")
    text = text.replace('"', "&quot;")
    text = text.replace("'", "&#x27;")
    return text
