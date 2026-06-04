# -*- coding: utf-8 -*-
"""
数据预处理模块
==============
JSON数据清洗、格式校验、结构验证、批量处理、数据备份。

特性：
  - JSON 清洗（去除 Markdown 包裹、修复常见格式错误）
  - 结构校验（必需的顶层键、数据类型检查）
  - 批量目录处理
  - 数据备份与还原
  - 错误收集与报告
"""

import json
import os
import re
import shutil
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

from .config import (
    PREPROCESSOR_MAX_ERRORS,
    PREPROCESSOR_AUTO_FIX,
    PREPROCESSOR_VALIDATE_SCHEMA,
    SCANNER_SKIP_HIDDEN,
)
from .logger import get_logger

logger = get_logger("preprocessor")


# ============================================================================
# JSON 清洗
# ============================================================================


def clean_json_content(content: str) -> Tuple[str, List[str]]:
    """
    清理 JSON 内容中的不规范字符和 Markdown 包裹

    参数:
        content: 原始文本内容

    返回:
        Tuple[str, List[str]]: (清洗后的内容, 应用的修复列表)
    """
    fixes = []
    original = content

    # 去除 BOM
    if content.startswith("﻿"):
        content = content[1:]
        fixes.append("移除 BOM 头")

    # 去除 Markdown 代码块包裹 ```json ... ```
    if content.strip().startswith("```"):
        content = re.sub(r"^```(?:json)?\s*", "", content.strip(), flags=re.MULTILINE)
        content = re.sub(r"```\s*$", "", content, flags=re.MULTILINE)
        fixes.append("移除 Markdown 代码块包裹")

    # 去除前后空白
    stripped = content.strip()
    if len(stripped) != len(original):
        content = stripped
        fixes.append("去除前后无用空白")

    # 修复常见 JSON 错误：单引号转双引号（仅限键名）
    # 这里做保守修复，只修复明显的情况
    if "'" in content and '"' not in content:
        # 这种情况极少，更多是混合使用
        pass

    # 修复尾部多余逗号
    content = re.sub(r",\s*(\}|\])", r"\1", content)
    if content != stripped:
        fixes.append("修复尾部多余逗号")

    return content, fixes


def is_valid_json(text: str) -> bool:
    """快速判断字符串是否为合法 JSON"""
    try:
        json.loads(text)
        return True
    except (json.JSONDecodeError, TypeError, ValueError):
        return False


# ============================================================================
# 安全解析
# ============================================================================


def safe_parse_json(file_path: str) -> Tuple[Optional[Any], List[str]]:
    """
    安全解析 JSON 文件

    参数:
        file_path: JSON 文件路径

    返回:
        Tuple[Optional[Any], List[str]]: (解析结果或 None, 错误列表)
    """
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
            return None, [f"文件编码错误: {file_path} - {e}"]

    content, fixes = clean_json_content(raw)

    try:
        data = json.loads(content)
        logger.debug(f"JSON 解析成功: {file_path} ({len(fixes)} 个修复)")
        return data, errors
    except json.JSONDecodeError as e:
        errors.append(f"JSON 解析失败 [{file_path}]: {e} (位置 line={e.lineno}, col={e.colno})")
        if PREPROCESSOR_AUTO_FIX:
            # 尝试更多修复手段
            try:
                # 尝试移除行注释
                cleaned = re.sub(r"//[^\n]*", "", content)
                data = json.loads(cleaned)
                logger.warning(f"自动修复后解析成功: {file_path}")
                return data, errors
            except json.JSONDecodeError:
                pass
        return None, errors


# ============================================================================
# 结构校验
# ============================================================================


def validate_poem_structure(data: Any) -> Tuple[bool, List[str]]:
    """
    校验诗歌 JSON 结构的完整性

    检查顶层必需字段和数据类型。

    参数:
        data: 解析后的 JSON 数据

    返回:
        Tuple[bool, List[str]]: (是否通过校验, 问题列表)
    """
    issues = []

    if not isinstance(data, dict):
        return False, ["根节点必须是 JSON 对象（dict）"]

    # 必需字段检查
    required_fields = {
        "诗歌编号": str,
        "标题": str,
        "作者": str,
    }

    for field, expected_type in required_fields.items():
        if field not in data:
            issues.append(f"缺少必需字段: {field}")
        elif not isinstance(data[field], expected_type):
            issues.append(f"字段类型错误 [{field}]: 期望 {expected_type.__name__}, 实际 {type(data[field]).__name__}")

    # 可选字段类型检查
    if "诗行" in data:
        lines = data["诗行"]
        if isinstance(lines, list):
            for i, line in enumerate(lines):
                if not isinstance(line, dict):
                    issues.append(f"诗行[{i}] 不是 dict 类型")
                    if len(issues) >= PREPROCESSOR_MAX_ERRORS:
                        break
        else:
            issues.append(f"'诗行' 字段应为 list，实际为 {type(lines).__name__}")

    if "分析单元" in data:
        units = data["分析单元"]
        if isinstance(units, list):
            for i, unit in enumerate(units):
                if not isinstance(unit, dict):
                    issues.append(f"分析单元[{i}] 不是 dict 类型")
                    if len(issues) >= PREPROCESSOR_MAX_ERRORS:
                        break
        else:
            issues.append(f"'分析单元' 字段应为 list，实际为 {type(units).__name__}")

    return len(issues) == 0, issues


def validate_data_file(file_path: str) -> Dict[str, Any]:
    """
    对单个数据文件执行完整的清洗→解析→校验流程

    返回:
        Dict: {"file", "valid", "errors", "fixes", "poem_count", "file_size"}
    """
    result = {
        "file": file_path,
        "valid": False,
        "errors": [],
        "fixes": [],
        "poem_count": 0,
        "file_size": os.path.getsize(file_path) if os.path.exists(file_path) else 0,
    }

    data, parse_errors = safe_parse_json(file_path)
    result["errors"].extend(parse_errors)

    if data is not None:
        is_valid, struct_issues = validate_poem_structure(data)
        if is_valid:
            result["valid"] = True
            # 统计诗歌数（嵌套结构）
            result["poem_count"] = _count_poems_recursive(data)
        result["errors"].extend(struct_issues)

    return result


def _count_poems_recursive(node: Any) -> int:
    """递归统计诗歌数量"""
    if isinstance(node, dict):
        if "分析单元" in node:
            return 1
        return sum(_count_poems_recursive(v) for v in node.values())
    if isinstance(node, list):
        return sum(_count_poems_recursive(item) for item in node)
    return 0


# ============================================================================
# 批量处理
# ============================================================================


def batch_validate_directory(directory: str,
                             file_extensions: Optional[List[str]] = None,
                             recursive: bool = True) -> Dict[str, Any]:
    """
    批量校验目录下所有 JSON/TXT 文件

    参数:
        directory: 目录路径
        file_extensions: 文件扩展名过滤（默认 .json, .txt）
        recursive: 是否递归搜索子目录

    返回:
        Dict: {"total", "valid", "invalid", "errors", "results"}
    """
    if file_extensions is None:
        file_extensions = [".json", ".txt"]

    from .utils import list_files
    files = list_files(directory, extensions=file_extensions, recursive=recursive)

    if SCANNER_SKIP_HIDDEN:
        files = [f for f in files if not os.path.basename(f).startswith(".")]

    results = []
    valid_count = 0
    invalid_count = 0
    all_errors = []

    for file_path in files:
        result = validate_data_file(file_path)
        results.append(result)
        if result["valid"]:
            valid_count += 1
        else:
            invalid_count += 1
        all_errors.extend(result["errors"])
        if len(all_errors) >= PREPROCESSOR_MAX_ERRORS:
            logger.warning(f"达到最大错误数限制 ({PREPROCESSOR_MAX_ERRORS})，停止批量校验")
            break

    return {
        "directory": directory,
        "total": len(files),
        "valid": valid_count,
        "invalid": invalid_count,
        "error_count": len(all_errors),
        "errors": all_errors[:100],
        "results": results,
        "success_rate_pct": round(valid_count / len(files) * 100, 1) if files else 0,
    }


# ============================================================================
# 数据备份
# ============================================================================


def backup_data(source_dir: str, backup_dir: Optional[str] = None) -> str:
    """
    备份数据目录

    参数:
        source_dir: 源目录
        backup_dir: 备份目标目录（None 则自动生成）

    返回:
        str: 备份目录路径
    """
    from .config import BACKUP_DIR
    if backup_dir is None:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = os.path.join(BACKUP_DIR, f"backup_{ts}")

    os.makedirs(backup_dir, exist_ok=True)

    file_count = 0
    total_size = 0
    for fname in os.listdir(source_dir):
        src = os.path.join(source_dir, fname)
        dst = os.path.join(backup_dir, fname)
        if os.path.isfile(src):
            shutil.copy2(src, dst)
            file_count += 1
            total_size += os.path.getsize(src)

    logger.info(f"数据备份完成: {file_count} 个文件 -> {backup_dir}")
    return backup_dir


def extract_image_statistics(data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    从诗歌数据中提取意象统计摘要

    参数:
        data: 诗歌数据列表

    返回:
        Dict: {"total_images", "unique_images", "top10", "category_distribution"}
    """
    image_texts = []
    categories = []

    for poem in data:
        units = poem.get("分析单元", [])
        for unit in units:
            if isinstance(unit, dict) and str(unit.get("是否意象", "0")) == "1":
                text = unit.get("文本", "").strip()
                if text:
                    image_texts.append(text)
                cat = unit.get("子类编码", "").strip()
                if cat:
                    categories.append(cat)

    from .utils import frequency_count
    top10 = frequency_count(image_texts, top_n=10)
    cat_dist = frequency_count(categories)

    return {
        "total_images": len(image_texts),
        "unique_images": len(set(image_texts)),
        "top10_images": [(text, count) for text, count in top10],
        "category_distribution": cat_dist,
        "unique_categories": len(set(categories)),
    }
