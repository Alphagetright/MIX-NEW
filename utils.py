# -*- coding: utf-8 -*-
"""
通用工具函数模块 — 文本处理、格式化、系统辅助
"""
import json
import re
import math
import hashlib
from typing import List, Optional, Any
from datetime import datetime


def truncate(text: str, max_len: int = 100, suffix: str = "...") -> str:
    """截断字符串到指定长度"""
    if not text:
        return ""
    if len(text) <= max_len:
        return text
    return text[:max_len].rstrip() + suffix


def extract_numbers(text: str) -> List[int]:
    """从文本中提取所有整数"""
    return [int(x) for x in re.findall(r"\d+", text)]


def is_chinese_char(ch: str) -> bool:
    """判断是否为中文字符"""
    if len(ch) != 1:
        return False
    cp = ord(ch)
    return (
        0x4E00 <= cp <= 0x9FFF
        or 0x3400 <= cp <= 0x4DBF
        or 0x20000 <= cp <= 0x2A6DF
        or 0x2A700 <= cp <= 0x2B73F
    )


def chinese_ratio(text: str) -> float:
    """计算字符串中中文字符占比"""
    if not text:
        return 0.0
    chinese_chars = sum(1 for ch in text if is_chinese_char(ch))
    return round(chinese_chars / len(text), 4)


def split_sentences(text: str) -> List[str]:
    """按中文句号、问号、感叹号、分句"""
    if not text:
        return []
    parts = re.split(r"([。！？\n])", text)
    sentences = []
    buf = ""
    for part in parts:
        buf += part
        if part in ("。", "！", "？", "\n"):
            buf = buf.strip()
            if buf:
                sentences.append(buf)
                buf = ""
    buf = buf.strip()
    if buf:
        sentences.append(buf)
    return sentences


def format_file_size(size_bytes: int) -> str:
    """格式化文件大小（B/KB/MB/GB）"""
    if size_bytes <= 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB"]
    i = int(math.floor(math.log(size_bytes, 1024))) if size_bytes > 0 else 0
    i = min(i, len(units) - 1)
    size = size_bytes / (1024 ** i)
    return f"{size:.1f} {units[i]}"


def format_timestamp(ts: float, fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    """格式化时间戳"""
    return datetime.fromtimestamp(ts).strftime(fmt)


def safe_get(data: dict, key: str, default: Any = "") -> Any:
    """安全获取字典值"""
    if not isinstance(data, dict):
        return default
    value = data.get(key)
    if value is None:
        return default
    return value


def dict_pick(data: dict, keys: List[str]) -> dict:
    """从字典中提取指定键的子集"""
    return {k: data[k] for k in keys if k in data}


def dict_omit(data: dict, keys: List[str]) -> dict:
    """从字典中排除指定键"""
    return {k: v for k, v in data.items() if k not in keys}


def md5_hash(text: str) -> str:
    """计算 MD5 哈希"""
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def safe_json_loads(text: str, default: Any = None) -> Any:
    """安全解析 JSON，失败返回默认值"""
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return default


def list_chunk(items: list, size: int) -> List[list]:
    """将列表按指定大小分块"""
    return [items[i : i + size] for i in range(0, len(items), size)]


def deduplicate_by_key(items: List[dict], key: str) -> List[dict]:
    """按字典的某个键去重（保留第一个）"""
    seen = set()
    result = []
    for item in items:
        val = item.get(key)
        if val not in seen:
            seen.add(val)
            result.append(item)
    return result


def merge_dicts(base: dict, override: dict) -> dict:
    """合并字典，override 覆盖 base"""
    result = base.copy()
    result.update(override)
    return result


def normalize_whitespace(text: str) -> str:
    """规范化空白字符"""
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip()
