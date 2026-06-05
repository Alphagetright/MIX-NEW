# -*- coding: utf-8 -*-
"""通用工具函数集"""
import json, os, re, time, hashlib
from datetime import datetime
from typing import Any, Dict, List, Optional


def truncate(text: str, max_length: int = 200, suffix: str = "...") -> str:
    return text if len(text) <= max_length else text[:max_length - len(suffix)] + suffix


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def is_chinese_char(char: str) -> bool:
    return len(char) == 1 and "一" <= char <= "鿿"


def chinese_ratio(text: str) -> float:
    if not text: return 0.0
    return sum(1 for c in text if is_chinese_char(c)) / len(text)


def extract_numbers(text: str) -> List[int]:
    return [int(m) for m in re.findall(r"\d+", text)]


def md5_hash(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def sanitize_filename(filename: str) -> str:
    return re.sub(r'[<>:"/\\|?*]', "_", filename).strip().strip(".") or "unnamed"


def format_file_size(size_bytes: int) -> str:
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024.0: return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"


def format_timestamp(ts: Optional[float] = None, fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    if ts is None: ts = time.time()
    return datetime.fromtimestamp(ts).strftime(fmt)


def ensure_dir(dir_path: str) -> str:
    os.makedirs(dir_path, exist_ok=True)
    return dir_path


def list_files(directory: str, extensions: Optional[List[str]] = None, recursive: bool = False) -> List[str]:
    files = []
    if not os.path.exists(directory): return files
    walker = os.walk(directory) if recursive else [(directory, [], os.listdir(directory))]
    for root, _, fnames in walker:
        for fn in fnames:
            full = os.path.join(root, fn)
            if os.path.isfile(full) and (extensions is None or any(fn.endswith(e) for e in extensions)):
                files.append(full)
    return sorted(files)


def safe_get(d: dict, *keys, default=None) -> Any:
    for key in keys:
        val = d.get(key)
        if val is not None: return val
    return default


def safe_json_loads(text: str, default=None) -> Any:
    try: return json.loads(text)
    except (json.JSONDecodeError, TypeError): return default


def frequency_count(items: List[Any], top_n: Optional[int] = None) -> List[tuple]:
    counts: Dict[Any, int] = {}
    for item in items: counts[item] = counts.get(item, 0) + 1
    return sorted(counts.items(), key=lambda x: x[1], reverse=True)[:top_n] if top_n else sorted(counts.items(), key=lambda x: x[1], reverse=True)


def escape_html(text: str) -> str:
    for c, e in [("&", "&amp;"), ("<", "&lt;"), (">", "&gt;"), ('"', "&quot;"), ("'", "&#x27;")]:
        text = text.replace(c, e)
    return text


def levenshtein_distance(s1: str, s2: str) -> int:
    """编辑距离（Levenshtein）"""
    if len(s1) < len(s2): return levenshtein_distance(s2, s1)
    if len(s2) == 0: return len(s1)
    prev = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        curr = [i + 1]
        for j, c2 in enumerate(s2):
            curr.append(min(curr[j] + 1, prev[j + 1] + 1, prev[j] + (c1 != c2)))
        prev = curr
    return prev[-1]


def text_similarity(text1: str, text2: str) -> float:
    """基于编辑距离的文本相似度"""
    if not text1 and not text2: return 1.0
    if not text1 or not text2: return 0.0
    max_len = max(len(text1), len(text2))
    return round(1 - levenshtein_distance(text1, text2) / max_len, 4)


# ─── 扩展工具 ───

def group_by(items, key):
    result = {}
    for item in items:
        k = str(item.get(key, ""))
        if k not in result: result[k] = []
        result[k].append(item)
    return result

def deduplicate_by_key(items, key):
    seen = set(); result = []
    for item in items:
        val = item.get(key)
        if val not in seen:
            seen.add(val); result.append(item)
    return result

def batch(items, func, max_workers=4):
    from concurrent.futures import ThreadPoolExecutor, as_completed
    results = [None] * len(items)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(func, item): i for i, item in enumerate(items)}
        for future in as_completed(futures):
            i = futures[future]
            try: results[i] = future.result(timeout=120)
            except: results[i] = None
    return results

def jaccard_similarity(set1, set2):
    if not set1 or not set2: return 0.0
    return round(len(set1 & set2) / len(set1 | set2), 4)

def normalize_vector(values):
    if not values: return []
    vmin, vmax = min(values), max(values)
    if vmax == vmin: return [0.5] * len(values)
    return [round((v - vmin) / (vmax - vmin), 4) for v in values]

def merge_dicts(*dicts, deep=True):
    result = {}
    for d in dicts:
        for k, v in d.items():
            if deep and k in result and isinstance(result[k], dict) and isinstance(v, dict):
                result[k] = merge_dicts(result[k], v)
            else: result[k] = v
    return result

def safe_get_deep(d, dotted_key, default=None):
    keys = dotted_key.split(".")
    for key in keys:
        if isinstance(d, dict) and key in d: d = d[key]
        else: return default
    return d

def compare_file_lists(old_list, new_list):
    old_set = set(old_list); new_set = set(new_list)
    return {"added": sorted(new_set - old_set), "removed": sorted(old_set - new_set),
            "unchanged": len(old_set & new_set)}

def csv_to_dicts(csv_path, encoding="utf-8-sig"):
    import csv, io
    with open(csv_path, "r", encoding=encoding) as f:
        content = f.read()
    if content.startswith("﻿"): content = content[1:]
    reader = csv.DictReader(io.StringIO(content))
    return list(reader)

def dicts_to_csv(data, csv_path, encoding="utf-8-sig"):
    import csv
    if not data: return
    with open(csv_path, "w", newline="", encoding=encoding) as f:
        f.write("﻿")
        w = csv.DictWriter(f, fieldnames=list(data[0].keys()))
        w.writeheader(); w.writerows(data)

def split_large_file(file_path, max_bytes=10485760):
    parts = []; part_num = 0
    with open(file_path, "rb") as f:
        while True:
            chunk = f.read(max_bytes)
            if not chunk: break
            part_path = f"{file_path}.part{part_num:03d}"
            with open(part_path, "wb") as out: out.write(chunk)
            parts.append(part_path); part_num += 1
    return parts
