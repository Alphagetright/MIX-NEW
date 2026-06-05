# -*- coding: utf-8 -*-
"""
JSON数据清洗模块
================
核心预处理功能：JSON内容清洗、安全解析、结构校验、批量处理、数据备份。
"""

import json, os, re, shutil
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from .config import DATA_DIR, CATEGORY_NAME_MAP, DIMENSION_KEYS, PREPROC_MAX_ERRORS
from .logger import get_logger
from .models import CleaningResult

logger = get_logger("preprocessor")


# ─── JSON 清洗 ───

def clean_json_content(content: str, aggressive: bool = False) -> Tuple[str, List[str]]:
    """清洗JSON内容，返回(清洗后内容, 修复列表)"""
    fixes = []
    if content.startswith("﻿"):
        content = content[1:]; fixes.append("移除BOM")

    stripped = content.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped, flags=re.MULTILINE)
        stripped = re.sub(r"```\s*$", "", stripped, flags=re.MULTILINE)
        fixes.append("移除Markdown包裹")

    content = stripped  # 使用strip后的结果
    content = re.sub(r",\s*(\}|\])", r"\1", content)
    if content != stripped:
        fixes.append("修复尾部逗号")

    # 单引号转双引号（保守）
    if aggressive:
        content = _fix_quotes(content)
        fixes.append("修复引号格式")

    return content, fixes


def _fix_quotes(content: str) -> str:
    """保守修复引号问题"""
    # 仅修复明显在键名位置的单引号
    return re.sub(r"'([a-zA-Z_]\w*)'\s*:", r'"\1":', content)


def fix_common_json_errors(content: str) -> Tuple[str, int]:
    """修复常见JSON格式错误，返回(修复后, 修复次数)"""
    count = 0
    # 尾部逗号
    new_content = re.sub(r",\s*(\}|\])", r"\1", content)
    count += (new_content != content)
    # 注释去除
    new_content = re.sub(r"//[^\n]*", "", new_content)
    count += (new_content != content)
    # 多行字符串未闭合引号
    new_content = re.sub(r':\s*"([^"]*\n[^"]*)"', r': "\1"', new_content)
    count += (new_content != content)
    # 多余的逗号（连续逗号）
    new_content = re.sub(r",\s*,", ",", new_content)
    count += (new_content != content)
    return new_content, count


# ─── JSON 解析 ───

def safe_parse_json(file_path: str) -> Tuple[Optional[Any], List[str]]:
    """安全解析JSON文件"""
    errors = []
    if not os.path.exists(file_path):
        return None, [f"文件不存在: {file_path}"]
    if os.path.getsize(file_path) == 0:
        return None, [f"文件为空: {file_path}"]

    raw = _read_file_with_encoding_detection(file_path)
    if raw is None:
        return None, ["无法读取文件编码"]

    content, fixes = clean_json_content(raw)
    try:
        return json.loads(content), errors
    except json.JSONDecodeError as e:
        # 尝试aggressive修复
        content2, fixes2 = clean_json_content(raw, aggressive=True)
        try:
            return json.loads(content2), errors
        except json.JSONDecodeError:
            errors.append(f"JSON解析失败: line={e.lineno}, col={e.colno}")
            return None, errors


def _read_file_with_encoding_detection(file_path: str) -> Optional[str]:
    """使用编码检测读取文件"""
    from .encoding_detector import detect_encoding
    enc, _ = detect_encoding(file_path)
    if enc == "unknown":
        enc = "utf-8"
    try:
        with open(file_path, "r", encoding=enc) as f:
            return f.read()
    except UnicodeDecodeError:
        # 回退到gbk
        try:
            with open(file_path, "r", encoding="gbk") as f:
                return f.read()
        except Exception:
            return None


# ─── 诗歌提取 ───

def extract_poems(node: Any) -> List[Dict]:
    """递归提取诗歌节点"""
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


# ─── 结构校验 ───

def validate_poem_structure(data: Any) -> Tuple[bool, List[str]]:
    """校验诗歌JSON结构完整性"""
    issues = []
    if not isinstance(data, dict):
        return False, ["根节点必须是dict"]
    for field in ["诗歌编号", "标题", "作者"]:
        if field not in data:
            issues.append(f"缺少必需字段: {field}")
        elif not isinstance(data[field], str):
            issues.append(f"字段类型错误 [{field}]: 期望str")
    if "诗行" in data and not isinstance(data["诗行"], list):
        issues.append("'诗行'应为list")
    if "分析单元" in data and not isinstance(data["分析单元"], list):
        issues.append("'分析单元'应为list")
    return len(issues) == 0, issues


def validate_analysis_units(units: List[Dict]) -> Tuple[int, int, List[str]]:
    """批量校验分析单元，返回(有效数, 无效数, 问题列表)"""
    valid = 0; invalid = 0; issues = []
    expected_fields = ["文本", "是否意象", "子类编码", "感知通道", "情感类别"]
    for i, unit in enumerate(units):
        if not isinstance(unit, dict):
            invalid += 1; issues.append(f"单元[{i}]不是dict")
            continue
        missing = [f for f in expected_fields if f not in unit]
        if missing:
            invalid += 1
            issues.append(f"单元[{i}]缺少字段: {missing}")
        else:
            valid += 1
        if len(issues) >= PREPROC_MAX_ERRORS:
            break
    return valid, invalid, issues


# ─── 批量处理 ───

def batch_validate_directory(directory: str = None) -> Dict[str, Any]:
    """批量校验目录下所有JSON文件"""
    if directory is None:
        directory = DATA_DIR
    from .utils import list_files
    files = list_files(directory, extensions=[".json", ".txt"], recursive=True)
    results = []; valid = 0; invalid = 0; all_issues = []
    for fp in files:
        data, errs = safe_parse_json(fp)
        if data is not None:
            ok, issues = validate_poem_structure(data)
            if ok: valid += 1
            else: invalid += 1; all_issues.extend(issues)
        else:
            invalid += 1; all_issues.extend(errs)
        results.append({"file": fp, "valid": data is not None})
        if len(all_issues) >= PREPROC_MAX_ERRORS * 5:
            break
    return {"total": len(files), "valid": valid, "invalid": invalid,
            "error_count": len(all_issues), "errors": all_issues[:100]}


def get_cleaning_stats(file_path: str) -> CleaningResult:
    """获取文件清洗统计"""
    import time
    start = time.time()
    result = CleaningResult(file_path=file_path, file_name=os.path.basename(file_path))
    result.original_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
    data, errs = safe_parse_json(file_path)
    if data is not None:
        result.parse_success = True
        result.fixes_applied = [f"JSON解析成功"] if not errs else errs
        result.fix_count = sum(1 for e in errs if "JSON解析成功" in str(e))
    else:
        result.errors = errs
        result.error_count = len(errs)
    result.duration_ms = round((time.time() - start) * 1000, 2)
    return result


def backup_data(source_dir: str, backup_dir: str = None) -> str:
    """备份数据目录"""
    from .config import BACKUP_DIR as default_backup
    if backup_dir is None:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = os.path.join(default_backup, f"backup_{ts}")
    os.makedirs(backup_dir, exist_ok=True)
    count = 0; total_size = 0
    for fn in os.listdir(source_dir):
        src = os.path.join(source_dir, fn); dst = os.path.join(backup_dir, fn)
        if os.path.isfile(src):
            shutil.copy2(src, dst); count += 1
            total_size += os.path.getsize(src)
    logger.info(f"备份完成: {count}文件 -> {backup_dir}")
    return backup_dir


# ─── 高级清洗 ───

def normalize_poem_data(poem):
    normalized = dict(poem)
    for key in ["诗歌编号", "标题", "作者"]:
        if key in normalized and isinstance(normalized[key], str):
            normalized[key] = normalized[key].strip()
    if "诗行" in normalized and isinstance(normalized["诗行"], list):
        normalized["诗行"] = [l for l in normalized["诗行"] if isinstance(l, dict)]
    if "分析单元" in normalized and isinstance(normalized["分析单元"], list):
        normalized["分析单元"] = [u for u in normalized["分析单元"] if isinstance(u, dict)]
    return normalized

def detect_json_issues(file_path):
    from .encoding_detector import detect_encoding
    issues = {"file": file_path, "problems": [], "severity": "info"}
    enc, _ = detect_encoding(file_path); issues["encoding"] = enc
    try:
        with open(file_path, "r", encoding=enc or "utf-8", errors="replace") as f:
            content = f.read()
    except Exception: return issues
    checks = [
        (content.startswith("﻿"), "info", "包含BOM头"),
        (content.strip().startswith("```"), "warning", "包含Markdown包裹"),
        ("//" in content, "info", "包含JavaScript注释"),
        (len(content) < 10, "error", "文件内容过短"),
        ("\t" in content[:1000], "info", "包含制表符"),
    ]
    for condition, severity, desc in checks:
        if condition: issues["problems"].append({"severity": severity, "description": desc})
    issues["severity"] = "error" if any(p["severity"] == "error" for p in issues["problems"]) else                           "warning" if any(p["severity"] == "warning" for p in issues["problems"]) else "info"
    issues["problem_count"] = len(issues["problems"]); return issues

def remove_trailing_commas_in_file(file_path):
    with open(file_path, "r", encoding="utf-8") as f: content = f.read()
    cleaned, count = re.subn(r",(\s*[}\]]), r"\1", content)
    if count > 0:
        with open(file_path, "w", encoding="utf-8") as f: f.write(cleaned)
    return file_path, count

def compute_file_hash(file_path, algorithm="md5"):
    import hashlib
    h = hashlib.new(algorithm)
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""): h.update(chunk)
    return h.hexdigest()

def find_duplicate_files(directory):
    from .utils import list_files
    files = list_files(directory, extensions=[".json", ".txt"], recursive=True)
    hashes = {}; duplicates = []
    for fp in files:
        h = compute_file_hash(fp)
        if h in hashes: duplicates.append({"file1": hashes[h], "file2": fp, "hash": h[:16]})
        else: hashes[h] = fp
    return duplicates


# ─── 批量修复工具 ───

def batch_fix_json_files(directory: str) -> Dict[str, Any]:
    """批量修复目录下所有JSON文件的常见格式错误"""
    from .utils import list_files
    files = list_files(directory, extensions=[".json", ".txt"], recursive=True)
    results = {"total": len(files), "fixed": 0, "already_ok": 0, "errors": []}
    for fp in files:
        try:
            with open(fp, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            original = content
            content, fixes = clean_json_content(content)
            content, fix_count = fix_common_json_errors(content)
            if content != original:
                with open(fp, "w", encoding="utf-8") as f:
                    f.write(content)
                results["fixed"] += 1
            else:
                results["already_ok"] += 1
        except Exception as e:
            results["errors"].append({"file": fp, "error": str(e)})
    logger.info(f"批量修复: {results['fixed']}/{results['total']}个文件已修复")
    return results


def analyze_json_depth(data: Any, max_depth: int = 20) -> int:
    """分析JSON数据的嵌套深度"""
    if isinstance(data, dict):
        return 1 + max((analyze_json_depth(v, max_depth) for v in data.values()), default=0)
    elif isinstance(data, list):
        return 1 + max((analyze_json_depth(item, max_depth) for item in data), default=0)
    return 0


def count_nodes(data: Any) -> Dict[str, int]:
    """递归统计JSON节点数量"""
    result = {"dicts": 0, "lists": 0, "strings": 0, "numbers": 0, "others": 0}
    if isinstance(data, dict):
        result["dicts"] += 1
        for v in data.values():
            sub = count_nodes(v)
            for k in result: result[k] += sub[k]
    elif isinstance(data, list):
        result["lists"] += 1
        for item in data: sub = count_nodes(item); [result.update({k: result[k] + sub[k]}) for k in result]
    elif isinstance(data, str): result["strings"] += 1
    elif isinstance(data, (int, float)): result["numbers"] += 1
    else: result["others"] += 1
    return result
