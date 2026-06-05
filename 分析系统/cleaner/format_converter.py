# -*- coding: utf-8 -*-
"""
格式转换模块
============
JSON ↔ CSV ↔ TXT 之间的相互转换。
"""

import csv, json, os
from datetime import datetime
from io import StringIO
from typing import Any, Dict, List, Optional

from .config import EXPORT_CSV_ENCODING, EXPORT_JSON_INDENT
from .logger import get_logger

logger = get_logger("format_converter")


def json_file_to_csv(json_path: str, csv_path: str = "",
                     flatten: bool = True) -> str:
    """将JSON文件转换为CSV文件"""
    from .preprocessor import safe_parse_json, extract_poems
    data, _ = safe_parse_json(json_path)
    if data is None:
        raise ValueError(f"无法解析JSON: {json_path}")

    poems = extract_poems(data)
    rows = []
    for poem in poems:
        for unit in poem.get("分析单元", []):
            if isinstance(unit, dict):
                rows.append({
                    "诗歌编号": poem.get("诗歌编号"), "标题": poem.get("标题"),
                    "作者": poem.get("作者"), "意象文本": unit.get("文本"),
                    "词性": unit.get("词性"), "是否意象": unit.get("是否意象"),
                    "感知通道": unit.get("感知通道"), "情感类别": unit.get("情感类别"),
                })

    if not csv_path:
        csv_path = json_path.rsplit(".", 1)[0] + ".csv"

    with open(csv_path, "w", newline="", encoding=EXPORT_CSV_ENCODING) as f:
        f.write("﻿")
        if not rows:
            return csv_path
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)

    logger.info(f"JSON→CSV: {json_path} → {csv_path} ({len(rows)}行)")
    return csv_path


def csv_file_to_json(csv_path: str, json_path: str = "") -> str:
    """将CSV文件转换为JSON文件"""
    with open(csv_path, "r", encoding=EXPORT_CSV_ENCODING) as f:
        content = f.read()
    if content.startswith("﻿"):
        content = content[1:]

    reader = csv.DictReader(StringIO(content))
    rows = list(reader)

    output = {"converted_from_csv": True, "source": os.path.basename(csv_path),
              "row_count": len(rows), "converted_at": datetime.now().isoformat(),
              "data": rows}

    if not json_path:
        json_path = csv_path.rsplit(".", 1)[0] + ".json"

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=EXPORT_JSON_INDENT)

    logger.info(f"CSV→JSON: {csv_path} → {json_path} ({len(rows)}行)")
    return json_path


def json_to_text(json_path: str, txt_path: str = "") -> str:
    """将JSON文件内容导出为可读TXT"""
    from .preprocessor import safe_parse_json, extract_poems
    data, _ = safe_parse_json(json_path)
    if not txt_path:
        txt_path = json_path.rsplit(".", 1)[0] + ".txt"

    lines = [f"数据文件: {os.path.basename(json_path)}",
             f"导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", "=" * 60]

    poems = extract_poems(data) if data else []
    for i, poem in enumerate(poems, 1):
        lines.append(f"\n诗歌 {i}: {poem.get('标题', '未知')} — {poem.get('作者', '佚名')}")
        for unit in poem.get("分析单元", [])[:20]:
            if isinstance(unit, dict):
                lines.append(f"  [{unit.get('是否意象')=='1' and '意象' or '非意象'}] "
                             f"{unit.get('文本', '')} ({unit.get('词性', '')})")

    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    logger.info(f"JSON→TXT: {json_path} → {txt_path}")
    return txt_path


def normalize_json_format(json_path: str, output_path: str = "") -> str:
    """标准化JSON格式（统一缩进、编码、去除冗余）"""
    from .preprocessor import safe_parse_json
    data, errs = safe_parse_json(json_path)
    if data is None:
        raise ValueError(f"无法解析JSON: {json_path}, 错误: {errs}")

    if not output_path:
        output_path = json_path.rsplit(".", 1)[0] + "_normalized.json"

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    logger.info(f"JSON标准化: {json_path} → {output_path}")
    return output_path


def merge_json_files(file_paths: List[str], output_path: str,
                     key_field: str = "诗歌编号") -> str:
    """合并多个JSON文件，按key_field去重"""
    from .preprocessor import safe_parse_json, extract_poems
    all_poems = {}
    for fp in file_paths:
        data, _ = safe_parse_json(fp)
        if data:
            poems = extract_poems(data)
            for p in poems:
                pid = p.get(key_field, "")
                if pid and pid not in all_poems:
                    all_poems[pid] = p

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(list(all_poems.values()), f, ensure_ascii=False, indent=2)

    logger.info(f"JSON合并: {len(file_paths)}文件 → {output_path} ({len(all_poems)}首诗)")
    return output_path


# ─── 扩展格式转换 ───

def json_to_tsv(json_path, tsv_path=""):
    from .preprocessor import safe_parse_json, extract_poems
    data, _ = safe_parse_json(json_path)
    if not tsv_path: tsv_path = json_path.rsplit(".", 1)[0] + ".tsv"
    poems = extract_poems(data) if data else []
    rows = []
    for poem in poems:
        for unit in poem.get("分析单元", []):
            if isinstance(unit, dict):
                rows.append({
                    "诗歌编号": poem.get("诗歌编号"), "标题": poem.get("标题"),
                    "作者": poem.get("作者"), "文本": unit.get("文本"),
                    "词性": unit.get("词性"), "是否意象": unit.get("是否意象"),
                    "感知通道": unit.get("感知通道"), "情感类别": unit.get("情感类别"),
                    "子类编码": unit.get("子类编码"),
                })
    with open(tsv_path, "w", encoding="utf-8") as f:
        if rows:
            f.write("\t".join(rows[0].keys()) + "\n")
            for r in rows: f.write("\t".join(str(v) for v in r.values()) + "\n")
    logger.info(f"JSON->TSV: {tsv_path}")
    return tsv_path

def batch_convert_directory(directory, source_fmt="json", target_fmt="csv"):
    from .utils import list_files
    files = list_files(directory, extensions=[f".{source_fmt}"], recursive=True)
    results = []
    for fp in files:
        try:
            if target_fmt == "csv": results.append(json_file_to_csv(fp))
            elif target_fmt == "txt": results.append(json_to_text(fp))
            elif target_fmt == "tsv": results.append(json_to_tsv(fp))
            elif target_fmt == "normalize": results.append(normalize_json_format(fp))
        except Exception as e: results.append(None)
    return len([r for r in results if r])

def extract_poems_to_json(raw_json_path, output_path=""):
    from .preprocessor import safe_parse_json, extract_poems
    data, _ = safe_parse_json(raw_json_path)
    poems = extract_poems(data) if data else []
    if not output_path:
        output_path = raw_json_path.rsplit(".", 1)[0] + "_poems.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(poems, f, ensure_ascii=False, indent=2)
    logger.info(f"提取诗歌: {len(poems)}首 -> {output_path}")
    return output_path
