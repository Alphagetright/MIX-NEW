# -*- coding: utf-8 -*-
"""通用工具函数集 — 字符串/文件/字典/列表/JSON/统计/编码"""

import json, os, re, time, hashlib
from datetime import datetime
from typing import Any, Dict, List, Optional, Union, Iterable


# ─── 字符串工具 ───
def truncate(text: str, max_length: int = 200, suffix: str = "...") -> str:
    return text if len(text) <= max_length else text[:max_length - len(suffix)] + suffix


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def is_chinese_char(char: str) -> bool:
    return len(char) == 1 and "一" <= char <= "鿿"


def chinese_ratio(text: str) -> float:
    if not text:
        return 0.0
    return sum(1 for c in text if is_chinese_char(c)) / len(text)


def extract_numbers(text: str) -> List[int]:
    return [int(m) for m in re.findall(r"\d+", text)]


def md5_hash(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def sanitize_filename(filename: str) -> str:
    return re.sub(r'[<>:"/\\|?*]', "_", filename).strip().strip(".") or "unnamed"


# ─── 文件工具 ───
def format_file_size(size_bytes: int) -> str:
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"


def format_timestamp(ts: Optional[float] = None, fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    if ts is None:
        ts = time.time()
    return datetime.fromtimestamp(ts).strftime(fmt)


def ensure_dir(dir_path: str) -> str:
    os.makedirs(dir_path, exist_ok=True)
    return dir_path


def list_files(directory: str, extensions: Optional[List[str]] = None,
               recursive: bool = False) -> List[str]:
    files = []
    if not os.path.exists(directory):
        return files
    if recursive:
        for root, _, fnames in os.walk(directory):
            for fn in fnames:
                full = os.path.join(root, fn)
                if extensions is None or any(fn.endswith(e) for e in extensions):
                    files.append(full)
    else:
        for fn in sorted(os.listdir(directory)):
            full = os.path.join(directory, fn)
            if os.path.isfile(full):
                if extensions is None or any(fn.endswith(e) for e in extensions):
                    files.append(full)
    return sorted(files)


# ─── 字典工具 ───
def safe_get(d: dict, *keys, default=None) -> Any:
    for key in keys:
        val = d.get(key)
        if val is not None:
            return val
    return default


def dict_pick(d: Dict[str, Any], keys: List[str]) -> Dict[str, Any]:
    return {k: d[k] for k in keys if k in d}


def dict_omit(d: Dict[str, Any], keys: List[str]) -> Dict[str, Any]:
    return {k: v for k, v in d.items() if k not in keys}


def merge_dicts(*dicts: Dict[str, Any], deep: bool = True) -> Dict[str, Any]:
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


# ─── 列表工具 ───
def list_chunk(items: List[Any], chunk_size: int) -> List[List[Any]]:
    return [items[i:i + chunk_size] for i in range(0, len(items), chunk_size)]


def deduplicate_by_key(items: List[Dict[str, Any]], key: str) -> List[Dict[str, Any]]:
    seen = set()
    result = []
    for item in items:
        val = item.get(key)
        if val not in seen:
            seen.add(val)
            result.append(item)
    return result


def unique(items: Iterable) -> List[Any]:
    seen = set()
    return [x for x in items if not (x in seen or seen.add(x))]


def sort_by_key(items: List[Dict[str, Any]], key: str, reverse: bool = False) -> List[Dict[str, Any]]:
    return sorted(items, key=lambda x: x.get(key, ""), reverse=reverse)


# ─── JSON 工具 ───
def safe_json_loads(text: str, default=None) -> Any:
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return default


def safe_json_dumps(obj: Any, **kwargs) -> str:
    try:
        return json.dumps(obj, ensure_ascii=False, **kwargs)
    except (TypeError, ValueError):
        return "{}"


# ─── 统计工具 ───
def frequency_count(items: List[Any], top_n: Optional[int] = None) -> List[tuple]:
    counts: Dict[Any, int] = {}
    for item in items:
        counts[item] = counts.get(item, 0) + 1
    sorted_items = sorted(counts.items(), key=lambda x: x[1], reverse=True)
    return sorted_items[:top_n] if top_n else sorted_items


def percentage_distribution(counts: Dict[str, int]) -> Dict[str, Dict[str, Any]]:
    total = sum(counts.values())
    if total == 0:
        return {}
    return {k: {"count": v, "pct": round(v / total * 100, 2)} for k, v in counts.items()}


def summary_statistics(numbers: List[float]) -> Dict[str, float]:
    import statistics
    if not numbers:
        return {"count": 0, "sum": 0, "mean": 0, "min": 0, "max": 0}
    return {
        "count": len(numbers), "sum": sum(numbers),
        "mean": round(statistics.mean(numbers), 2),
        "min": min(numbers), "max": max(numbers),
        "median": round(statistics.median(numbers), 2),
        "std": round(statistics.stdev(numbers), 2) if len(numbers) > 1 else 0,
    }


# ─── 编码工具 ───
def escape_html(text: str) -> str:
    for char, entity in [("&", "&amp;"), ("<", "&lt;"), (">", "&gt;"),
                          ('"', "&quot;"), ("'", "&#x27;")]:
        text = text.replace(char, entity)
    return text


# ─── 扩展工具 ───

def group_by(items: List[Dict[str, Any]], key: str) -> Dict[str, List[Dict[str, Any]]]:
    """按键分组"""
    result: Dict[str, List[Dict[str, Any]]] = {}
    for item in items:
        k = str(item.get(key, ""))
        if k not in result:
            result[k] = []
        result[k].append(item)
    return result


def flatten_dict(d: Dict[str, Any], prefix: str = "", sep: str = ".") -> Dict[str, Any]:
    """嵌套字典扁平化"""
    result = {}
    for k, v in d.items():
        full_key = f"{prefix}{sep}{k}" if prefix else k
        if isinstance(v, dict):
            result.update(flatten_dict(v, full_key, sep))
        else:
            result[full_key] = v
    return result


def batch(items: List[Any], func: callable, max_workers: int = 4) -> List[Any]:
    """对列表中的每个元素并发执行函数"""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    results = [None] * len(items)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(func, item): i for i, item in enumerate(items)}
        for future in as_completed(futures):
            i = futures[future]
            try:
                results[i] = future.result(timeout=120)
            except Exception:
                results[i] = None
    return results


def calculate_tfidf(documents: List[List[str]]) -> List[Dict[str, float]]:
    """计算 TF-IDF 权重"""
    import math
    n_docs = len(documents)
    if n_docs == 0:
        return []
    df: Dict[str, int] = {}
    for doc in documents:
        for term in set(doc):
            df[term] = df.get(term, 0) + 1
    results = []
    for doc in documents:
        tf = {}
        total = len(doc)
        if total == 0:
            results.append({})
            continue
        for term in doc:
            tf[term] = tf.get(term, 0) + 1
        tfidf = {}
        for term, count in tf.items():
            idf = math.log((n_docs + 1) / (df.get(term, 0) + 1)) + 1
            tfidf[term] = round(count / total * idf, 4)
        results.append(tfidf)
    return results


def jaccard_similarity(set1: set, set2: set) -> float:
    """计算 Jaccard 相似系数"""
    if not set1 or not set2:
        return 0.0
    return round(len(set1 & set2) / len(set1 | set2), 4)


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """计算余弦相似度"""
    import math
    dot = sum(a * b for a, b in zip(vec1, vec2))
    mag1 = math.sqrt(sum(a * a for a in vec1))
    mag2 = math.sqrt(sum(b * b for b in vec2))
    if mag1 == 0 or mag2 == 0:
        return 0.0
    return round(dot / (mag1 * mag2), 4)


def normalize_vector(values: List[float]) -> List[float]:
    """向量归一化 (min-max)"""
    if not values:
        return []
    v_min = min(values)
    v_max = max(values)
    if v_max == v_min:
        return [0.5] * len(values)
    return [round((v - v_min) / (v_max - v_min), 4) for v in values]


def moving_average(values: List[float], window: int = 7) -> List[float]:
    """计算移动平均"""
    if len(values) < window:
        return []
    return [round(sum(values[i:i + window]) / window, 2) for i in range(len(values) - window + 1)]
