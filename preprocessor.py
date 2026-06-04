# -*- coding: utf-8 -*-
"""
数据预处理模块 — JSON 清洗、格式校验、批量转换
"""
import json
import os
import re
import glob
import shutil
from typing import List, Dict, Optional, Tuple

from config import POEM_JSON_DIR, BASE_DIR
from logger import get_logger
from models import Poem, AnalysisUnit

logger = get_logger("preprocessor")


def clean_json_content(content: str) -> str:
    """清理 JSON 文本中的 Markdown 包裹和不规范字符"""
    content = re.sub(r"^```json\s*", "", content, flags=re.MULTILINE)
    content = re.sub(r"^```\s*", "", content, flags=re.MULTILINE)
    content = re.sub(r",\s*}", "}", content)
    content = re.sub(r",\s*]", "]", content)
    content = content.strip()
    return content


def validate_poem_json(data: dict) -> List[str]:
    """验证诗歌 JSON 结构，返回错误列表"""
    errors = []
    if not isinstance(data, dict):
        return ["根节点不是字典"]

    poems = data.get("诗歌集", [data]) if isinstance(data, dict) else data
    if not isinstance(poems, list):
        poems = [poems]

    for i, poem in enumerate(poems):
        prefix = f"[诗歌 #{i+1}]"
        if not poem.get("标题"):
            errors.append(f"{prefix} 缺少标题字段")
        if not poem.get("诗歌编号") and not poem.get("编号"):
            errors.append(f"{prefix} 缺少诗歌编号")
        if not poem.get("原文") and not poem.get("诗行"):
            errors.append(f"{prefix} 缺少原文或诗行")
        if "分析单元" in poem:
            for j, unit in enumerate(poem["分析单元"]):
                if not isinstance(unit, dict):
                    errors.append(f"{prefix} 分析单元 #{j+1} 不是字典")
                    continue
                if not unit.get("文本"):
                    errors.append(f"{prefix} 分析单元 #{j+1} 缺少文本")
                if not unit.get("诗行编号"):
                    errors.append(f"{prefix} 分析单元 #{j+1} 缺少诗行编号")
    return errors


def parse_json_file(filepath: str) -> Tuple[Optional[dict], List[str]]:
    """安全解析 JSON 文件，返回 (data, errors)"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except IOError as e:
        return None, [f"读取失败: {e}"]

    content = clean_json_content(content)
    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        return None, [f"JSON 解析失败: {e}"]
    errors = validate_poem_json(data)
    return data, errors


def batch_validate(directory: str = None) -> Dict:
    """批量校验目录下所有 JSON 文件"""
    directory = directory or POEM_JSON_DIR
    if not os.path.exists(directory):
        return {"total": 0, "valid": 0, "invalid": 0, "details": []}

    files = glob.glob(os.path.join(directory, "*.json"))
    results = {"total": len(files), "valid": 0, "invalid": 0, "details": []}

    for fpath in sorted(files):
        fname = os.path.basename(fpath)
        data, errors = parse_json_file(fpath)
        if errors:
            results["invalid"] += 1
            results["details"].append({"file": fname, "status": "invalid",
                                        "errors": errors})
            logger.warning(f"校验失败: {fname} — {'; '.join(errors)}")
        else:
            results["valid"] += 1
            results["details"].append({"file": fname, "status": "valid",
                                        "poem_count": len(
                                            data.get("诗歌集", [data])
                                            if isinstance(data, dict) else data
                                        )})
            logger.info(f"校验通过: {fname}")

    return results


def backup_data(directory: str = None) -> str:
    """备份数据目录"""
    src = directory or POEM_JSON_DIR
    if not os.path.exists(src):
        logger.warning(f"备份源目录不存在: {src}")
        return ""
    backup_name = f"backup_poem_json_{__import__('time').time():.0f}"
    dst = os.path.join(BASE_DIR, backup_name)
    shutil.copytree(src, dst)
    logger.info(f"数据备份完成: {src} -> {dst}")
    return dst


def convert_raw_poem_to_model(poem_dict: dict) -> Poem:
    """将原始 JSON 字典转为 Poem 模型"""
    return Poem.from_dict(poem_dict)


def extract_image_statistics(poems: List[Poem]) -> Dict:
    """从 Poem 模型列表提取意象统计"""
    total_images = 0
    image_texts = []
    author_images = {}

    for poem in poems:
        images = poem.image_units
        total_images += len(images)
        for u in images:
            image_texts.append(u.文本)
        author = poem.作者 or "未知"
        if author not in author_images:
            author_images[author] = []
        author_images[author].extend(u.文本 for u in images)

    from collections import Counter
    top = Counter(image_texts).most_common(20)

    return {
        "total_poems": len(poems),
        "total_images": total_images,
        "unique_images": len(set(image_texts)),
        "top_images": [{"text": t, "count": c} for t, c in top],
        "authors": len(author_images),
    }
