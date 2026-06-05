# -*- coding: utf-8 -*-
"""
通用工具函数集
==============
提供 30+ 个通用工具函数，涵盖字符串处理、文件操作、数据转换、编码安全、
列表操作、字典操作、时间处理等类别。
"""

import json
import os
import re
import hashlib
import time
import datetime
from typing import Any, Dict, List, Optional, Union, Iterable, Callable


# ============================================================================
# 字符串工具
# ============================================================================


def truncate(text: str, max_length: int = 200, suffix: str = "...") -> str:
    """
    截断字符串到指定长度

    参数:
        text: 原始字符串
        max_length: 最大长度
        suffix: 截断后缀

    返回:
        str: 截断后的字符串

    Examples:
        >>> truncate("hello world", 8)
        'hello...'
        >>> truncate("short", 10)
        'short'
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def normalize_whitespace(text: str) -> str:
    """
    规范化空白字符

    将多个空白字符（空格、制表符、换行符）压缩为单个空格。
    """
    return re.sub(r"\s+", " ", text).strip()


def is_chinese_char(char: str) -> bool:
    """判断单个字符是否为中文汉字"""
    return len(char) == 1 and "一" <= char <= "鿿"


def chinese_ratio(text: str) -> float:
    """
    计算字符串中中文字符占比

    返回:
        float: 0.0 ~ 1.0 之间的比值
    """
    if not text:
        return 0.0
    return sum(1 for c in text if is_chinese_char(c)) / len(text)


def split_sentences(text: str) -> List[str]:
    """
    中文分句

    按句号、问号、感叹号、分号等标点分句。
    """
    sentences = re.split(r"[。！？；\n]+", text)
    return [s.strip() for s in sentences if s.strip()]


def extract_numbers(text: str) -> List[int]:
    """提取文本中所有整数"""
    return [int(m) for m in re.findall(r"\d+", text)]


def md5_hash(text: str) -> str:
    """计算字符串的 MD5 哈希值"""
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def sha256_hash(text: str) -> str:
    """计算字符串的 SHA256 哈希值"""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sanitize_filename(filename: str) -> str:
    """
    清理文件名中的非法字符

    移除 Windows/Linux 文件系统不允许的字符。
    """
    illegal_chars = r'[<>:"/\\|?*]'
    cleaned = re.sub(illegal_chars, "_", filename)
    cleaned = cleaned.strip().strip(".")
    return cleaned or "unnamed"


def camel_to_snake(name: str) -> str:
    """驼峰命名转蛇形命名"""
    s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


def snake_to_camel(name: str, upper_first: bool = False) -> str:
    """蛇形命名转驼峰命名"""
    parts = name.split("_")
    if upper_first:
        return "".join(p.capitalize() for p in parts)
    return parts[0] + "".join(p.capitalize() for p in parts[1:])


# ============================================================================
# 文件与路径工具
# ============================================================================


def format_file_size(size_bytes: int) -> str:
    """
    格式化文件大小为人类可读格式

    Examples:
        >>> format_file_size(1024)
        '1.00 KB'
        >>> format_file_size(1048576)
        '1.00 MB'
    """
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"


def format_timestamp(ts: Union[int, float, None] = None,
                     fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    格式化时间戳为字符串

    参数:
        ts: Unix 时间戳，None 表示当前时间
        fmt: 格式化字符串
    """
    if ts is None:
        ts = time.time()
    return datetime.datetime.fromtimestamp(ts).strftime(fmt)


def ensure_dir(dir_path: str) -> str:
    """
    确保目录存在，不存在则创建

    返回:
        str: 目录路径
    """
    os.makedirs(dir_path, exist_ok=True)
    return dir_path


def list_files(directory: str, extensions: Optional[List[str]] = None,
               recursive: bool = False) -> List[str]:
    """
    列出目录中的文件

    参数:
        directory: 目录路径
        extensions: 文件扩展名过滤列表（如 ['.json', '.txt']）
        recursive: 是否递归搜索

    返回:
        List[str]: 文件绝对路径列表
    """
    files = []
    if not os.path.exists(directory):
        return files

    if recursive:
        for root, _, filenames in os.walk(directory):
            for fname in filenames:
                full = os.path.join(root, fname)
                if extensions is None or any(fname.endswith(ext) for ext in extensions):
                    files.append(full)
    else:
        for fname in os.listdir(directory):
            full = os.path.join(directory, fname)
            if os.path.isfile(full):
                if extensions is None or any(fname.endswith(ext) for ext in extensions):
                    files.append(full)

    return sorted(files)


def get_file_age_days(file_path: str) -> Optional[int]:
    """获取文件的年龄（天数）"""
    if not os.path.exists(file_path):
        return None
    age_seconds = time.time() - os.path.getmtime(file_path)
    return int(age_seconds / 86400)


# ============================================================================
# 字典工具
# ============================================================================


def safe_get(d: dict, *keys, default=None) -> Any:
    """
    安全获取嵌套字典值（多键回退）

    依次尝试每个 key，返回第一个存在的值。

    Examples:
        >>> d = {"name": "李白", "title": None}
        >>> safe_get(d, "author", "name", default="未知")
        '李白'
    """
    for key in keys:
        val = d.get(key)
        if val is not None:
            return val
    return default


def dict_pick(d: Dict[str, Any], keys: List[str]) -> Dict[str, Any]:
    """从字典中提取指定键的子集"""
    return {k: d[k] for k in keys if k in d}


def dict_omit(d: Dict[str, Any], keys: List[str]) -> Dict[str, Any]:
    """从字典中排除指定键"""
    return {k: v for k, v in d.items() if k not in keys}


def dict_deep_get(d: Dict[str, Any], dotted_key: str, default=None) -> Any:
    """
    通过点分隔键路径获取嵌套字典值

    Examples:
        >>> d = {"a": {"b": {"c": 42}}}
        >>> dict_deep_get(d, "a.b.c")
        42
    """
    keys = dotted_key.split(".")
    for key in keys:
        if isinstance(d, dict) and key in d:
            d = d[key]
        else:
            return default
    return d


def dict_deep_set(d: Dict[str, Any], dotted_key: str, value: Any) -> None:
    """通过点分隔键路径设置嵌套字典值"""
    keys = dotted_key.split(".")
    for key in keys[:-1]:
        if key not in d:
            d[key] = {}
        d = d[key]
    d[keys[-1]] = value


def merge_dicts(*dicts: Dict[str, Any], deep: bool = True) -> Dict[str, Any]:
    """
    合并多个字典

    参数:
        *dicts: 要合并的字典（后面的覆盖前面的）
        deep: 是否深度合并嵌套字典
    """
    result = {}
    for d in dicts:
        if not deep:
            result.update(d)
        else:
            for k, v in d.items():
                if k in result and isinstance(result[k], dict) and isinstance(v, dict):
                    result[k] = merge_dicts(result[k], v)
                else:
                    result[k] = v
    return result


# ============================================================================
# 列表工具
# ============================================================================


def list_chunk(items: List[Any], chunk_size: int) -> List[List[Any]]:
    """
    将列表分割为固定大小的块

    Examples:
        >>> list_chunk([1,2,3,4,5], 2)
        [[1, 2], [3, 4], [5]]
    """
    return [items[i:i + chunk_size] for i in range(0, len(items), chunk_size)]


def deduplicate_by_key(items: List[Dict[str, Any]], key: str) -> List[Dict[str, Any]]:
    """按键去重，保留第一个出现的条目"""
    seen = set()
    result = []
    for item in items:
        val = item.get(key)
        if val not in seen:
            seen.add(val)
            result.append(item)
    return result


def unique(items: Iterable) -> List[Any]:
    """去重并保持顺序"""
    seen = set()
    result = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def group_by(items: List[Dict[str, Any]], key: str) -> Dict[Any, List[Dict[str, Any]]]:
    """按键分组"""
    result: Dict[Any, List[Dict[str, Any]]] = {}
    for item in items:
        k = item.get(key)
        if k not in result:
            result[k] = []
        result[k].append(item)
    return result


def sort_by_key(items: List[Dict[str, Any]], key: str,
                reverse: bool = False) -> List[Dict[str, Any]]:
    """按键排序"""
    return sorted(items, key=lambda x: x.get(key, ""), reverse=reverse)


# ============================================================================
# JSON 工具
# ============================================================================


def safe_json_loads(text: str, default=None) -> Any:
    """
    安全解析 JSON 字符串

    不会抛出异常，解析失败返回默认值。
    """
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError, ValueError):
        return default


def safe_json_dumps(obj: Any, default: str = "{}", **kwargs) -> str:
    """
    安全序列化为 JSON 字符串

    参数:
        obj: 要序列化的对象
        default: 失败时的默认返回值
        **kwargs: 传递给 json.dumps 的参数（如 indent, ensure_ascii）
    """
    try:
        return json.dumps(obj, ensure_ascii=False, **kwargs)
    except (TypeError, ValueError):
        return default


def json_to_csv_string(data: List[Dict[str, Any]], delimiter: str = ",") -> str:
    """将字典列表转换为 CSV 字符串"""
    if not data:
        return ""
    headers = list(data[0].keys())
    lines = [delimiter.join(headers)]
    for row in data:
        values = [str(row.get(h, "")).replace(delimiter, ";") for h in headers]
        lines.append(delimiter.join(values))
    return "\n".join(lines)


# ============================================================================
# 数据统计工具
# ============================================================================


def frequency_count(items: List[Any], top_n: Optional[int] = None) -> List[tuple]:
    """
    统计元素出现频率并排序

    参数:
        items: 元素列表
        top_n: 返回 Top-N 结果，None 返回全部

    返回:
        List[tuple]: [(元素, 频次), ...] 按频次降序排列
    """
    counts: Dict[Any, int] = {}
    for item in items:
        counts[item] = counts.get(item, 0) + 1
    sorted_items = sorted(counts.items(), key=lambda x: x[1], reverse=True)
    if top_n:
        return sorted_items[:top_n]
    return sorted_items


def percentage_distribution(counts: Dict[str, int]) -> Dict[str, Dict[str, Any]]:
    """
    计算百分比分布

    返回:
        Dict: {key: {"count": int, "pct": float}, ...}
    """
    total = sum(counts.values())
    if total == 0:
        return {}
    return {
        k: {"count": v, "pct": round(v / total * 100, 2)}
        for k, v in counts.items()
    }


def summary_statistics(numbers: List[float]) -> Dict[str, float]:
    """
    计算数值列表的汇总统计

    返回:
        Dict: {"count", "sum", "mean", "min", "max", "median", "std"}
    """
    import statistics
    if not numbers:
        return {"count": 0, "sum": 0, "mean": 0, "min": 0, "max": 0}
    return {
        "count": len(numbers),
        "sum": sum(numbers),
        "mean": round(statistics.mean(numbers), 2),
        "min": min(numbers),
        "max": max(numbers),
        "median": round(statistics.median(numbers), 2),
        "std": round(statistics.stdev(numbers), 2) if len(numbers) > 1 else 0,
    }


# ============================================================================
# 编码与转义工具
# ============================================================================


def escape_html(text: str) -> str:
    """HTML 实体转义，防止 XSS 攻击"""
    replacements = {
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#x27;",
    }
    for char, entity in replacements.items():
        text = text.replace(char, entity)
    return text


def unescape_html(text: str) -> str:
    """HTML 实体反转义"""
    replacements = {
        "&amp;": "&",
        "&lt;": "<",
        "&gt;": ">",
        "&quot;": '"',
        "&#x27;": "'",
    }
    for entity, char in replacements.items():
        text = text.replace(entity, char)
    return text


def byte_size_to_human_friendly_representation_lower_case(
    bytes_count: int, precision: int = 2
) -> str:
    """字节数转人类可读格式（另一种实现）"""
    if bytes_count < 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB", "PB", "EB"]
    unit_index = 0
    value = float(bytes_count)
    while value >= 1024 and unit_index < len(units) - 1:
        value /= 1024
        unit_index += 1
    return f"{value:.{precision}f} {units[unit_index]}"
