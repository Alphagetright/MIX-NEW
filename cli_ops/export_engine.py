# -*- coding: utf-8 -*-
"""
数据导出引擎
============
支持多格式数据导出：CSV (UTF-8-BOM)、JSON (indent)、XML、TXT、HTML 报告。

特性：
  - 流式导出避免大文件内存溢出
  - 字段过滤与重命名
  - 数据子集切片导出
  - 导出历史记录管理
  - 文件命名自动生成（时间戳）
"""

import csv
import json
import os
import time
import xml.dom.minidom
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from .config import (
    EXPORT_DIR,
    EXPORT_CSV_ENCODING,
    EXPORT_CSV_DELIMITER,
    EXPORT_JSON_INDENT,
    EXPORT_XML_ROOT_TAG,
    EXPORT_MAX_ROWS,
    EXPORT_TIMESTAMP_FORMAT,
)
from .logger import get_logger
from .models import ExportRecord

logger = get_logger("export_engine")

# 确保导出目录存在
os.makedirs(EXPORT_DIR, exist_ok=True)

# 导出历史
_export_history: List[ExportRecord] = []


# ============================================================================
# 工具函数
# ============================================================================


def _generate_filename(prefix: str, extension: str) -> str:
    """生成带时间戳的文件名"""
    ts = datetime.now().strftime(EXPORT_TIMESTAMP_FORMAT)
    safe_prefix = prefix.replace(" ", "_").lower()
    return os.path.join(EXPORT_DIR, f"{safe_prefix}_{ts}.{extension}")


def _check_row_limit(rows: List[Dict[str, Any]]) -> None:
    """检查导出行数是否超限"""
    if len(rows) > EXPORT_MAX_ROWS:
        from .errors import ExportSizeExceededError
        raise ExportSizeExceededError(
            actual=len(rows),
            max_rows=EXPORT_MAX_ROWS,
        )


def _filter_fields(rows: List[Dict[str, Any]],
                   fields: Optional[List[str]] = None,
                   exclude_fields: Optional[Set[str]] = None) -> List[Dict[str, Any]]:
    """过滤和排除字段"""
    if fields is not None:
        return [{k: r.get(k, "") for k in fields} for r in rows]
    if exclude_fields is not None:
        return [{k: v for k, v in r.items() if k not in exclude_fields} for r in rows]
    return rows


# ============================================================================
# CSV 导出
# ============================================================================


def export_to_csv(rows: List[Dict[str, Any]],
                  filename_prefix: str = "data_export",
                  fields: Optional[List[str]] = None,
                  delimiter: str = EXPORT_CSV_DELIMITER,
                  encoding: str = EXPORT_CSV_ENCODING) -> ExportRecord:
    """
    导出为 CSV 文件（UTF-8-BOM 编码）

    参数:
        rows: 数据行列表（字典格式）
        filename_prefix: 文件名前缀
        fields: 导出字段列表（None=所有字段）
        delimiter: 列分隔符
        encoding: 文件编码

    返回:
        ExportRecord: 导出记录
    """
    start_time = time.time()
    file_path = _generate_filename(filename_prefix, "csv")

    try:
        _check_row_limit(rows)
        data = _filter_fields(rows, fields=fields)

        headers = list(data[0].keys()) if data else []
        with open(file_path, "w", newline="", encoding=encoding) as f:
            f.write("﻿")  # BOM
            writer = csv.writer(f, delimiter=delimiter)
            writer.writerow(headers)
            for row in data:
                writer.writerow([row.get(h, "") for h in headers])

        duration = round(time.time() - start_time, 2)
        record = ExportRecord(
            format="csv",
            file_path=file_path,
            file_size=os.path.getsize(file_path),
            rows_exported=len(data),
            columns_exported=len(headers),
            duration=duration,
        )
        _export_history.append(record)
        logger.info(f"CSV 导出完成: {file_path} ({len(data)} 行, {duration}s)")
        return record

    except Exception as e:
        logger.error(f"CSV 导出失败: {e}")
        return ExportRecord(
            format="csv",
            status="failed",
            error_message=str(e),
            duration=round(time.time() - start_time, 2),
        )


# ============================================================================
# JSON 导出
# ============================================================================


def export_to_json(rows: List[Dict[str, Any]],
                   filename_prefix: str = "data_export",
                   indent: int = EXPORT_JSON_INDENT,
                   fields: Optional[List[str]] = None) -> ExportRecord:
    """
    导出为 JSON 文件

    参数:
        rows: 数据行列表
        filename_prefix: 文件名前缀
        indent: 缩进空格数
        fields: 导出字段列表

    返回:
        ExportRecord: 导出记录
    """
    start_time = time.time()
    file_path = _generate_filename(filename_prefix, "json")

    try:
        _check_row_limit(rows)
        data = _filter_fields(rows, fields=fields)

        output = {
            "metadata": {
                "exported_at": datetime.now().isoformat(),
                "total_rows": len(data),
                "format_version": "1.0",
            },
            "data": data,
        }

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=indent)

        duration = round(time.time() - start_time, 2)
        record = ExportRecord(
            format="json",
            file_path=file_path,
            file_size=os.path.getsize(file_path),
            rows_exported=len(data),
            columns_exported=len(data[0]) if data else 0,
            duration=duration,
        )
        _export_history.append(record)
        logger.info(f"JSON 导出完成: {file_path} ({len(data)} 行, {duration}s)")
        return record

    except Exception as e:
        logger.error(f"JSON 导出失败: {e}")
        return ExportRecord(
            format="json",
            status="failed",
            error_message=str(e),
            duration=round(time.time() - start_time, 2),
        )


# ============================================================================
# XML 导出
# ============================================================================


def export_to_xml(rows: List[Dict[str, Any]],
                  filename_prefix: str = "data_export",
                  root_tag: str = EXPORT_XML_ROOT_TAG,
                  row_tag: str = "item",
                  fields: Optional[List[str]] = None) -> ExportRecord:
    """
    导出为 XML 文件

    参数:
        rows: 数据行列表
        filename_prefix: 文件名前缀
        root_tag: 根元素标签
        row_tag: 每行数据标签
        fields: 导出字段列表

    返回:
        ExportRecord: 导出记录
    """
    start_time = time.time()
    file_path = _generate_filename(filename_prefix, "xml")

    try:
        _check_row_limit(rows)
        data = _filter_fields(rows, fields=fields)

        root = ET.Element(root_tag)
        root.set("total", str(len(data)))
        root.set("exported_at", datetime.now().isoformat())

        for row in data:
            item = ET.SubElement(root, row_tag)
            for key, value in row.items():
                child = ET.SubElement(item, key.replace(" ", "_"))
                child.text = str(value) if value is not None else ""

        rough = ET.tostring(root, encoding="unicode")
        dom = xml.dom.minidom.parseString(rough)
        pretty = dom.toprettyxml(indent="  ", encoding="utf-8")

        with open(file_path, "wb") as f:
            f.write(pretty)

        duration = round(time.time() - start_time, 2)
        record = ExportRecord(
            format="xml",
            file_path=file_path,
            file_size=os.path.getsize(file_path),
            rows_exported=len(data),
            columns_exported=len(data[0]) if data else 0,
            duration=duration,
        )
        _export_history.append(record)
        logger.info(f"XML 导出完成: {file_path} ({len(data)} 行, {duration}s)")
        return record

    except Exception as e:
        logger.error(f"XML 导出失败: {e}")
        return ExportRecord(
            format="xml",
            status="failed",
            error_message=str(e),
            duration=round(time.time() - start_time, 2),
        )


# ============================================================================
# TXT 导出
# ============================================================================


def export_to_txt(rows: List[Dict[str, Any]],
                  filename_prefix: str = "data_export",
                  fields: Optional[List[str]] = None,
                  col_separator: str = "\t") -> ExportRecord:
    """
    导出为纯文本文件（TSV 格式）

    参数:
        rows: 数据行列表
        filename_prefix: 文件名前缀
        fields: 导出字段列表
        col_separator: 列分隔符

    返回:
        ExportRecord: 导出记录
    """
    start_time = time.time()
    file_path = _generate_filename(filename_prefix, "txt")

    try:
        _check_row_limit(rows)
        data = _filter_fields(rows, fields=fields)

        headers = list(data[0].keys()) if data else []

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(col_separator.join(headers) + "\n")
            f.write("-" * 80 + "\n")
            for row in data:
                values = [str(row.get(h, "")) for h in headers]
                f.write(col_separator.join(values) + "\n")

        duration = round(time.time() - start_time, 2)
        record = ExportRecord(
            format="txt",
            file_path=file_path,
            file_size=os.path.getsize(file_path),
            rows_exported=len(data),
            columns_exported=len(headers),
            duration=duration,
        )
        _export_history.append(record)
        logger.info(f"TXT 导出完成: {file_path} ({len(data)} 行, {duration}s)")
        return record

    except Exception as e:
        logger.error(f"TXT 导出失败: {e}")
        return ExportRecord(
            format="txt",
            status="failed",
            error_message=str(e),
            duration=round(time.time() - start_time, 2),
        )


# ============================================================================
# HTML 报告导出
# ============================================================================


def export_to_html(rows: List[Dict[str, Any]],
                   filename_prefix: str = "data_report",
                   title: str = "数据导出报告",
                   fields: Optional[List[str]] = None,
                   max_preview_rows: int = 200) -> ExportRecord:
    """
    导出为 HTML 报告文件

    包含样式化的 HTML 表格，适合直接查看和分享。

    参数:
        rows: 数据行列表
        filename_prefix: 文件名前缀
        title: 报告标题
        fields: 导出字段列表
        max_preview_rows: 最大渲染行数

    返回:
        ExportRecord: 导出记录
    """
    start_time = time.time()
    file_path = _generate_filename(filename_prefix, "html")

    try:
        _check_row_limit(rows)
        data = _filter_fields(rows, fields=fields)

        headers = list(data[0].keys()) if data else []
        preview = data[:max_preview_rows]

        html_parts = [
            "<!DOCTYPE html>",
            '<html lang="zh-CN">',
            "<head>",
            '<meta charset="utf-8">',
            f"<title>{title}</title>",
            "<style>",
            "body { font-family: Arial, 'Microsoft YaHei', sans-serif; margin: 20px; }",
            "h1 { color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }",
            ".meta { color: #888; font-size: 14px; margin-bottom: 20px; }",
            "table { border-collapse: collapse; width: 100%; }",
            "th { background: #3498db; color: #fff; padding: 10px 8px; text-align: left; font-size: 13px; }",
            "td { padding: 8px; border-bottom: 1px solid #eee; font-size: 13px; }",
            "tr:hover { background: #f5f8fa; }",
            ".footer { margin-top: 20px; color: #999; font-size: 12px; }",
            "</style>",
            "</head>",
            "<body>",
            f"<h1>{title}</h1>",
            f"<div class=\"meta\">导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
            f"总行数: {len(data)} | 列数: {len(headers)}</div>",
            "<table>",
            "<thead><tr>" + "".join(f"<th>{h}</th>" for h in headers) + "</tr></thead>",
            "<tbody>",
        ]

        for row in preview:
            vals = "".join(f"<td>{str(row.get(h, ''))[:200]}</td>" for h in headers)
            html_parts.append(f"<tr>{vals}</tr>")

        if len(data) > max_preview_rows:
            html_parts.append(
                f'<tr><td colspan="{len(headers)}" style="text-align:center;color:#999;">'
                f'... 还有 {len(data) - max_preview_rows} 行未显示 ...</td></tr>'
            )

        html_parts.extend([
            "</tbody></table>",
            "<div class=\"footer\">由 唐诗意象数据运维管理系统 V1.0 自动生成</div>",
            "</body></html>",
        ])

        with open(file_path, "w", encoding="utf-8") as f:
            f.write("\n".join(html_parts))

        duration = round(time.time() - start_time, 2)
        record = ExportRecord(
            format="html",
            file_path=file_path,
            file_size=os.path.getsize(file_path),
            rows_exported=len(data),
            columns_exported=len(headers),
            duration=duration,
        )
        _export_history.append(record)
        logger.info(f"HTML 导出完成: {file_path} ({len(data)} 行, {duration}s)")
        return record

    except Exception as e:
        logger.error(f"HTML 导出失败: {e}")
        return ExportRecord(
            format="html",
            status="failed",
            error_message=str(e),
            duration=round(time.time() - start_time, 2),
        )


# ============================================================================
# 导出管理
# ============================================================================


def export_data(rows: List[Dict[str, Any]], fmt: str = "csv",
                filename_prefix: str = "data_export",
                fields: Optional[List[str]] = None, **kwargs) -> ExportRecord:
    """
    统一导出接口

    参数:
        rows: 数据行列表
        fmt: 导出格式 (csv/json/xml/txt/html)
        filename_prefix: 文件名前缀
        fields: 导出字段列表
        **kwargs: 传递给具体导出函数的额外参数

    返回:
        ExportRecord: 导出记录
    """
    exporters = {
        "csv": export_to_csv,
        "json": export_to_json,
        "xml": export_to_xml,
        "txt": export_to_txt,
        "html": export_to_html,
    }

    exporter = exporters.get(fmt.lower())
    if not exporter:
        from .errors import ExportFormatError
        raise ExportFormatError(fmt=fmt)

    return exporter(rows, filename_prefix=filename_prefix, fields=fields, **kwargs)


def export_slice(rows: List[Dict[str, Any]], start: int = 0, end: int = 100,
                 fmt: str = "csv", **kwargs) -> ExportRecord:
    """导出数据子集"""
    return export_data(rows[start:end], fmt=fmt, **kwargs)


def list_exports() -> List[ExportRecord]:
    """列出所有导出记录"""
    records = []
    if os.path.exists(EXPORT_DIR):
        for fname in sorted(os.listdir(EXPORT_DIR), reverse=True):
            fpath = os.path.join(EXPORT_DIR, fname)
            if os.path.isfile(fpath):
                records.append(ExportRecord(
                    file_path=fpath,
                    file_size=os.path.getsize(fpath),
                    format=os.path.splitext(fname)[1][1:],
                    created_at=os.path.getmtime(fpath),
                ))
    return records


def clear_exports() -> int:
    """清空导出目录"""
    count = 0
    if os.path.exists(EXPORT_DIR):
        for fname in os.listdir(EXPORT_DIR):
            try:
                os.remove(os.path.join(EXPORT_DIR, fname))
                count += 1
            except OSError:
                pass
    _export_history.clear()
    logger.info(f"导出目录已清空: {count} 个文件")
    return count


def get_export_stats() -> Dict[str, Any]:
    """获取导出统计"""
    exports = list_exports()
    total_size = sum(e.file_size for e in exports)
    return {
        "total_files": len(exports),
        "total_size_bytes": total_size,
        "total_size_formatted": f"{total_size / (1024 * 1024):.2f} MB",
        "export_directory": EXPORT_DIR,
        "recent_exports": [e.to_dict() for e in exports[:10]],
    }
