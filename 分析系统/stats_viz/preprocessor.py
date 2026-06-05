# -*- coding: utf-8 -*-
"""
数据预处理模块
==============
JSON 数据清洗、解析、校验、批量处理、去重。
"""

import json
import os
import re
import shutil
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from .config import DATA_DIR
from .logger import get_logger

logger = get_logger("preprocessor")


def clean_json_content(content: str) -> Tuple[str, List[str]]:
    """清洗 JSON 内容：去 BOM、去 Markdown 包裹、修复尾部逗号"""
    fixes = []
    if content.startswith("﻿"):
        content = content[1:]
        fixes.append("移除 BOM")

    stripped = content.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped, flags=re.MULTILINE)
        stripped = re.sub(r"```\s*$", "", stripped, flags=re.MULTILINE)
        fixes.append("移除 Markdown 包裹")

    if len(stripped) != len(content):
        content = stripped
        fixes.append("去除空白")

    content = re.sub(r",\s*(\}|\])", r"\1", content)
    return content, fixes


def safe_parse_json(file_path: str) -> Tuple[Optional[Any], List[str]]:
    """安全解析 JSON 文件"""
    errors = []
    if not os.path.exists(file_path):
        return None, [f"文件不存在: {file_path}"]
    if os.path.getsize(file_path) == 0:
        return None, [f"文件为空: {file_path}"]

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            raw = f.read()
    except UnicodeDecodeError:
        try:
            with open(file_path, "r", encoding="gbk") as f:
                raw = f.read()
        except Exception as e:
            return None, [f"编码错误 [{file_path}]: {e}"]

    content, fixes = clean_json_content(raw)
    try:
        return json.loads(content), errors
    except json.JSONDecodeError as e:
        errors.append(f"JSON 解析失败 [{file_path}]: line={e.lineno}, col={e.colno}")
        return None, errors


def extract_poems(node: Any) -> List[Dict]:
    """递归提取诗歌节点（包含'分析单元'字段的 dict）"""
    found = []
    if isinstance(node, dict):
        if "分析单元" in node and isinstance(node.get("分析单元"), list):
            found.append(node)
        else:
            for v in node.values():
                found.extend(extract_poems(v))
    elif isinstance(node, list):
        for item in node:
            found.extend(extract_poems(item))
    return found


def validate_poem_structure(data: Any) -> Tuple[bool, List[str]]:
    """校验诗歌 JSON 结构完整性"""
    issues = []
    if not isinstance(data, dict):
        return False, ["根节点必须是 dict"]
    for field in ["诗歌编号", "标题", "作者"]:
        if field not in data:
            issues.append(f"缺少: {field}")
        elif not isinstance(data[field], str):
            issues.append(f"类型错误 [{field}]: 期望 str")
    if "诗行" in data and not isinstance(data["诗行"], list):
        issues.append("'诗行' 应为 list")
    if "分析单元" in data and not isinstance(data["分析单元"], list):
        issues.append("'分析单元' 应为 list")
    return len(issues) == 0, issues


def batch_validate_directory(directory: str, extensions: List[str] = None) -> Dict[str, Any]:
    """批量校验目录下所有数据文件"""
    from .utils import list_files
    if extensions is None:
        extensions = [".json", ".txt"]
    files = list_files(directory, extensions=extensions, recursive=True)
    results = []
    valid = 0
    all_errors = []
    for fp in files:
        data, errs = safe_parse_json(fp)
        if data is not None:
            is_ok, issues = validate_poem_structure(data)
            if is_ok:
                valid += 1
            else:
                all_errors.extend(issues)
        else:
            all_errors.extend(errs)
        results.append({"file": fp, "valid": data is not None})
        if len(all_errors) >= 200:
            break
    return {
        "total": len(files), "valid": valid, "invalid": len(files) - valid,
        "error_count": len(all_errors), "errors": all_errors[:100],
    }


def backup_data(source_dir: str, backup_dir: Optional[str] = None) -> str:
    """备份数据目录"""
    if backup_dir is None:
        from .config import BASE_DIR
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = os.path.join(BASE_DIR, "..", "backups", f"backup_{ts}")
    os.makedirs(backup_dir, exist_ok=True)
    count = 0
    for fn in os.listdir(source_dir):
        src = os.path.join(source_dir, fn)
        dst = os.path.join(backup_dir, fn)
        if os.path.isfile(src):
            shutil.copy2(src, dst)
            count += 1
    logger.info(f"备份完成: {count} 文件 -> {backup_dir}")
    return backup_dir


# ─── 数据转换工具 ───

def convert_raw_to_imagery_items(poems: List[Dict]) -> List[Dict[str, Any]]:
    """将原始诗歌数据批量转换为扁平意象条目"""
    from .config import CATEGORY_NAME_MAP, DIMENSION_KEYS
    items = []
    for poem in poems:
        if not isinstance(poem, dict):
            continue
        title = str(poem.get("标题", "")).strip()
        poem_id = str(poem.get("诗歌编号", poem.get("编号", "-"))).strip()
        author = str(poem.get("作者", "")).strip()
        genre = str(poem.get("分类标签", poem.get("体裁", ""))).strip()
        line_map = {}
        for line in poem.get("诗行", []):
            if isinstance(line, dict):
                line_map[str(line.get("诗行编号", ""))] = line.get("原文", "")
        for unit in poem.get("分析单元", []):
            if not isinstance(unit, dict):
                continue
            if str(unit.get("是否意象", "0")).strip() != "1":
                continue
            text = str(unit.get("文本", "")).strip()
            if not text:
                continue
            sub_code = str(unit.get("子类编码", "")).strip()
            cat = CATEGORY_NAME_MAP.get(sub_code, f"其他({sub_code})")
            emo_cat = str(unit.get("情感类别", "")).strip()
            emo_pol = str(unit.get("情感极性", "")).strip()
            dims = []
            for k in DIMENSION_KEYS:
                v = str(unit.get(k, "")).strip()
                if v and v != "None":
                    dims.append(v)
            items.append({
                "poem_id": poem_id, "title": title, "author": author, "genre": genre,
                "category": cat, "imagery_text": text,
                "dimensions": " | ".join(dims) if dims else "-",
                "emotion": f"{emo_cat}({emo_pol})" if emo_pol and emo_cat else (emo_cat or "未知"),
                "emo_cat": emo_cat, "emo_pol": emo_pol,
                "perception_channel": unit.get("感知通道", ""),
                "material_type": unit.get("素材类型", ""),
                "internal_structure": unit.get("内部结构", ""),
                "reference_source": unit.get("指涉来源", ""),
                "expressive_function": unit.get("表现功能", ""),
            })
    return items


def compute_data_statistics(data_dir: str = None) -> Dict[str, Any]:
    """计算数据目录的统计信息"""
    if data_dir is None:
        data_dir = DATA_DIR
    if not os.path.exists(data_dir):
        return {"error": f"目录不存在: {data_dir}"}
    file_count = 0; total_size = 0; json_valid = 0; json_invalid = 0
    for fn in os.listdir(data_dir):
        fp = os.path.join(data_dir, fn)
        if os.path.isfile(fp):
            file_count += 1; total_size += os.path.getsize(fp)
            if fn.endswith((".json", ".txt")):
                data, errs = safe_parse_json(fp)
                if data is not None and not errs:
                    json_valid += 1
                else:
                    json_invalid += 1
    from .utils import format_file_size
    return {"file_count": file_count, "total_size": format_file_size(total_size),
            "json_valid": json_valid, "json_invalid": json_invalid,
            "directory": data_dir, "valid_rate_pct": round(json_valid / max(1, json_valid + json_invalid) * 100, 1)}


def find_duplicate_poems(directory: str = None) -> List[Dict[str, Any]]:
    """检测重复诗歌"""
    import glob
    if directory is None:
        directory = DATA_DIR
    seen = {}
    duplicates = []
    for fp in glob.glob(os.path.join(directory, "*.json")):
        data, _ = safe_parse_json(fp)
        if not data:
            continue
        poems = extract_poems(data)
        for poem in poems:
            title = str(poem.get("标题", "")).strip()
            lines = poem.get("诗行", [])
            first_line = ""
            if lines and isinstance(lines[0], dict):
                first_line = str(lines[0].get("原文", "")).strip()
            key = f"{title}_{first_line}"
            if key in seen:
                duplicates.append({"key": key, "file1": seen[key], "file2": fp, "title": title})
            else:
                seen[key] = fp
    return duplicates
