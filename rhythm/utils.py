# -*- coding: utf-8 -*-
"""
古典诗词音韵格律分析引擎 — 通用工具函数集
"""
import hashlib
import json
import os
import re
from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional, Tuple, Union


# ─── 字符串工具 ───


def truncate(text: str, max_length: int, suffix: str = "..."):
    return text[:max_length] + suffix if len(text) > max_length else text


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", "", text)


def is_chinese_char(char: str) -> bool:
    return "一" <= char <= "鿿" or "㐀" <= char <= "䶿"


def chinese_ratio(text: str) -> float:
    if not text:
        return 0.0
    chinese = sum(1 for c in text if is_chinese_char(c))
    return chinese / len(text)


def extract_chinese(text: str) -> str:
    return "".join(c for c in text if is_chinese_char(c))


def split_chinese_chars(text: str) -> List[str]:
    return [c for c in text if is_chinese_char(c)]


def md5_hash(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def sanitize_filename(filename: str) -> str:
    return re.sub(r'[\\/*?:"<>|]', "_", filename)


# ─── 文件与路径工具 ───


def format_file_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    if size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


def format_timestamp(ts: float, fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    import time
    return time.strftime(fmt, time.localtime(ts))


def ensure_dir(dir_path: str) -> str:
    os.makedirs(dir_path, exist_ok=True)
    return dir_path


def list_files(
    directory: str,
    extensions: List[str] = None,
    recursive: bool = True,
) -> List[str]:
    files = []
    if not os.path.exists(directory):
        return files
    if recursive:
        for root, _, filenames in os.walk(directory):
            for fn in filenames:
                fp = os.path.join(root, fn)
                if extensions:
                    if any(fn.endswith(ext) for ext in extensions):
                        files.append(fp)
                else:
                    files.append(fp)
    else:
        for fn in os.listdir(directory):
            fp = os.path.join(directory, fn)
            if os.path.isfile(fp):
                if extensions:
                    if any(fn.endswith(ext) for ext in extensions):
                        files.append(fp)
                else:
                    files.append(fp)
    return sorted(files)


# ─── 字典工具 ───


def safe_get(d: Dict, *keys, default=None):
    for key in keys:
        if key in d:
            return d[key]
    return default


def dict_pick(d: Dict, keys: List[str]) -> Dict:
    return {k: d[k] for k in keys if k in d}


def dict_omit(d: Dict, keys: List[str]) -> Dict:
    return {k: v for k, v in d.items() if k not in keys}


def merge_dicts(*dicts, deep: bool = False) -> Dict:
    result = {}
    for d in dicts:
        if not d:
            continue
        if deep:
            for k, v in d.items():
                if k in result and isinstance(result[k], dict) and isinstance(v, dict):
                    result[k] = merge_dicts(result[k], v, deep=True)
                else:
                    result[k] = v
        else:
            result.update(d)
    return result


# ─── 列表工具 ───


def unique(items: List) -> List:
    seen = set()
    result = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def group_by(items: List, key_func) -> Dict[Any, List]:
    groups = defaultdict(list)
    for item in items:
        groups[key_func(item)].append(item)
    return dict(groups)


def list_chunk(items: List, size: int) -> List[List]:
    return [items[i : i + size] for i in range(0, len(items), size)]


def sort_by_key(items: List, key: str, reverse: bool = False) -> List:
    return sorted(items, key=lambda x: x.get(key, 0), reverse=reverse)


def deduplicate_by_key(items: List[Dict], key: str) -> List[Dict]:
    seen = set()
    result = []
    for item in items:
        val = item.get(key)
        if val not in seen:
            seen.add(val)
            result.append(item)
    return result


# ─── 统计工具 ───


def frequency_count(items: List, top_n: int = None) -> List[Tuple[Any, int]]:
    counter = Counter(items)
    result = counter.most_common()
    return result[:top_n] if top_n else result


def percentage_distribution(counts: Dict[Any, int]) -> Dict[Any, float]:
    total = sum(counts.values()) or 1
    return {k: round(v / total * 100, 2) for k, v in counts.items()}


def summary_statistics(numbers: List[float]) -> Dict[str, float]:
    if not numbers:
        return {"count": 0, "min": 0, "max": 0, "mean": 0, "median": 0}
    s = sorted(numbers)
    n = len(s)
    return {
        "count": n,
        "min": s[0],
        "max": s[-1],
        "mean": round(sum(s) / n, 2),
        "median": s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2,
    }


# ─── 相似度工具 ───


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    if not vec1 or not vec2 or len(vec1) != len(vec2):
        return 0.0
    dot = sum(a * b for a, b in zip(vec1, vec2))
    mag1 = sum(a * a for a in vec1) ** 0.5
    mag2 = sum(b * b for b in vec2) ** 0.5
    if mag1 == 0 or mag2 == 0:
        return 0.0
    return dot / (mag1 * mag2)


def jaccard_similarity(set1: set, set2: set) -> float:
    if not set1 and not set2:
        return 1.0
    intersection = len(set1 & set2)
    union = len(set1 | set2)
    return intersection / union if union else 0.0


def levenshtein_distance(s1: str, s2: str) -> int:
    m, n = len(s1), len(s2)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m + 1):
        dp[i][0] = i
    for j in range(n + 1):
        dp[0][j] = j
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            cost = 0 if s1[i - 1] == s2[j - 1] else 1
            dp[i][j] = min(dp[i - 1][j] + 1, dp[i][j - 1] + 1, dp[i - 1][j - 1] + cost)
    return dp[m][n]


def text_similarity(text1: str, text2: str) -> float:
    if not text1 and not text2:
        return 1.0
    max_len = max(len(text1), len(text2))
    if max_len == 0:
        return 0.0
    return 1.0 - levenshtein_distance(text1, text2) / max_len


# ─── JSON 工具 ───


def safe_json_loads(text: str, default=None):
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return default


def safe_json_dumps(obj, **kwargs) -> str:
    kwargs.setdefault("ensure_ascii", False)
    kwargs.setdefault("indent", 2)
    try:
        return json.dumps(obj, **kwargs)
    except (TypeError, ValueError):
        return str(obj)


# ─── 数学工具 ───


def normalize_vector(values: List[float]) -> List[float]:
    if not values:
        return []
    min_v, max_v = min(values), max(values)
    if max_v == min_v:
        return [0.5] * len(values)
    return [(v - min_v) / (max_v - min_v) for v in values]


def moving_average(values: List[float], window: int = 3) -> List[float]:
    if len(values) < window:
        return values
    result = []
    for i in range(len(values) - window + 1):
        result.append(sum(values[i : i + window]) / window)
    return result
