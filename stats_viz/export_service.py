# -*- coding: utf-8 -*-
"""
数据导出服务
============
支持 CSV (UTF-8-BOM)、JSON (indent)、HTML 报告三种格式的统计结果导出。
"""

import csv
import json
import os
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from .config import EXPORT_DIR, EXPORT_CSV_ENCODING, EXPORT_JSON_INDENT, EXPORT_MAX_ROWS
from .logger import get_logger
from .models import ExportRecord

logger = get_logger("export_service")
os.makedirs(EXPORT_DIR, exist_ok=True)

_export_history: List[ExportRecord] = []


def _gen_filename(prefix: str, ext: str) -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return os.path.join(EXPORT_DIR, f"{prefix}_{ts}.{ext}")


def _create_record(fmt: str, path: str, rows: int, cols: int, dur: float,
                   status: str = "success", error: str = "") -> ExportRecord:
    record = ExportRecord(
        format=fmt, file_path=path, file_size=os.path.getsize(path) if os.path.exists(path) else 0,
        rows_exported=rows, columns_exported=cols, duration=dur, status=status, error_message=error,
    )
    _export_history.append(record)
    return record


# ─── CSV 导出 ───

def export_to_csv(rows: List[Dict[str, Any]], prefix: str = "stats_export",
                  fields: Optional[List[str]] = None) -> ExportRecord:
    """导出为 CSV 文件 (UTF-8-BOM)"""
    start = time.time()
    fp = _gen_filename(prefix, "csv")
    try:
        data = rows
        if fields:
            data = [{k: row.get(k, "") for k in fields} for row in rows]
        if not data:
            return _create_record("csv", fp, 0, 0, round(time.time() - start, 2), "failed", "无数据")
        if len(data) > EXPORT_MAX_ROWS:
            data = data[:EXPORT_MAX_ROWS]
        headers = list(data[0].keys())
        with open(fp, "w", newline="", encoding=EXPORT_CSV_ENCODING) as f:
            f.write("﻿")  # BOM
            w = csv.writer(f)
            w.writerow(headers)
            for row in data:
                w.writerow([row.get(h, "") for h in headers])
        dur = round(time.time() - start, 2)
        logger.info(f"CSV导出: {fp} ({len(data)}行, {dur}s)")
        return _create_record("csv", fp, len(data), len(headers), dur)
    except Exception as e:
        return _create_record("csv", fp, 0, 0, round(time.time() - start, 2), "failed", str(e))


# ─── JSON 导出 ───

def export_to_json(data: Any, prefix: str = "stats_export") -> ExportRecord:
    """导出为 JSON 文件"""
    start = time.time()
    fp = _gen_filename(prefix, "json")
    try:
        output = {"exported_at": datetime.now().isoformat(), "version": "1.0", "data": data}
        with open(fp, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=EXPORT_JSON_INDENT)
        dur = round(time.time() - start, 2)
        logger.info(f"JSON导出: {fp} ({dur}s)")
        return _create_record("json", fp, 1, 1, dur)
    except Exception as e:
        return _create_record("json", fp, 0, 0, round(time.time() - start, 2), "failed", str(e))


# ─── HTML 导出 ───

def export_stats_to_html(engine: Any, prefix: str = "stats_report") -> ExportRecord:
    """导出统计结果为 HTML 报告"""
    start = time.time()
    fp = _gen_filename(prefix, "html")
    try:
        summary = engine.summary_report()
        top = engine.top_imagery(20)
        cat = engine.category_distribution()
        emo = engine.emotion_distribution()
        authors = engine.top_authors_by_imagery(15)

        html = f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<title>诗歌意象统计报告</title>
<style>
body{{font-family:Arial,'Microsoft YaHei',sans-serif;margin:24px;color:#333}}
h1{{color:#2c3e50;border-bottom:3px solid #3498db;padding-bottom:10px}}
h2{{color:#2c3e50;margin-top:24px}}
.meta{{color:#888;font-size:13px}}
table{{border-collapse:collapse;width:100%;margin:8px 0}}
th{{background:#3498db;color:#fff;padding:8px 10px;text-align:left;font-size:13px}}
td{{padding:8px 10px;border-bottom:1px solid #eee;font-size:13px}}
tr:hover{{background:#f5f8fa}}
</style></head><body>
<h1>诗歌意象多维统计分析报告</h1>
<p class="meta">生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
<h2>基础统计</h2>
<table><tr><th>指标</th><th>数值</th></tr>"""

        base = summary["基础统计"]
        for k, v in base.items():
            html += f"<tr><td>{k}</td><td>{v}</td></tr>"
        html += "</table>"

        html += "<h2>高频意象 Top20</h2><table><tr><th>意象</th><th>频次</th></tr>"
        for t, c in top:
            html += f"<tr><td>{t}</td><td>{c}</td></tr>"
        html += "</table>"

        html += "<h2>分类域分布</h2><table><tr><th>分类</th><th>数量</th></tr>"
        for k, v in sorted(cat.items(), key=lambda x: x[1], reverse=True):
            html += f"<tr><td>{k}</td><td>{v}</td></tr>"
        html += "</table>"

        html += "<h2>情感类别分布</h2><table><tr><th>情感</th><th>数量</th></tr>"
        for k, v in sorted(emo.items(), key=lambda x: x[1], reverse=True):
            html += f"<tr><td>{k}</td><td>{v}</td></tr>"
        html += "</table>"

        html += "<h2>诗人意象使用量 Top15</h2><table><tr><th>诗人</th><th>意象数</th></tr>"
        for a, c in authors:
            html += f"<tr><td>{a}</td><td>{c}</td></tr>"
        html += "</table>"

        html += "<p style='color:#999;font-size:12px;margin-top:20px'>由 诗歌意象多维统计与可视化系统 V1.0 生成</p></body></html>"

        with open(fp, "w", encoding="utf-8") as f:
            f.write(html)
        dur = round(time.time() - start, 2)
        logger.info(f"HTML导出: {fp} ({dur}s)")
        return _create_record("html", fp, 1, 1, dur)
    except Exception as e:
        return _create_record("html", fp, 0, 0, round(time.time() - start, 2), "failed", str(e))


# ─── 导出管理 ───

def list_exports() -> List[ExportRecord]:
    """列出所有导出文件"""
    records = []
    if os.path.exists(EXPORT_DIR):
        for fn in sorted(os.listdir(EXPORT_DIR), reverse=True):
            fp = os.path.join(EXPORT_DIR, fn)
            if os.path.isfile(fp):
                records.append(ExportRecord(
                    file_path=fp, file_size=os.path.getsize(fp),
                    format=os.path.splitext(fn)[1][1:], created_at=os.path.getmtime(fp),
                ))
    return records


def clear_exports() -> int:
    """清空导出目录"""
    count = 0
    if os.path.exists(EXPORT_DIR):
        for fn in os.listdir(EXPORT_DIR):
            try:
                os.remove(os.path.join(EXPORT_DIR, fn))
                count += 1
            except OSError:
                pass
    logger.info(f"导出目录已清空: {count} 文件")
    return count


# ─── 批量导出 ───

def batch_export(data: Dict[str, Any], formats: List[str] = None) -> List[ExportRecord]:
    """批量多格式导出"""
    if formats is None:
        formats = ["csv", "json", "html"]
    records = []
    rows = data.get("traceback", [])
    for fmt in formats:
        if fmt == "csv":
            records.append(export_to_csv(rows, prefix="batch_export"))
        elif fmt == "json":
            records.append(export_to_json(data, prefix="batch_export"))
        elif fmt == "html":
            from .stats_engine import StatsEngine
            engine = StatsEngine()
            engine.load_data(rows)
            records.append(export_stats_to_html(engine, prefix="batch_report"))
    return records


def export_summary_report(engine: Any, include_charts: bool = True) -> str:
    """导出含图表配置的完整分析报告"""
    summary = engine.summary_report()
    output = {"metadata": {"exported_at": datetime.now().isoformat(), "version": "2.0",
                           "format": "summary_report"}, "statistics": summary}
    if include_charts:
        from .chart_data_builder import ChartDataBuilder
        builder = ChartDataBuilder(engine)
        output["charts"] = builder.build_all_charts()
    fp = _gen_filename("full_report", "json")
    with open(fp, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    return fp


def export_filtered_slice(data: List[Dict[str, Any]], start: int = 0, end: int = 100,
                          fmt: str = "csv", fields: List[str] = None) -> str:
    """导出数据子集"""
    slice_data = data[start:end]
    if fmt == "csv":
        return export_to_csv(slice_data, prefix="data_slice", fields=fields).file_path
    else:
        return export_to_json(slice_data, prefix="data_slice").file_path


def get_export_directory_info() -> Dict[str, Any]:
    """获取导出目录详细信息"""
    if not os.path.exists(EXPORT_DIR):
        return {"exists": False, "path": EXPORT_DIR}
    files = []
    total_size = 0
    for fn in os.listdir(EXPORT_DIR):
        fp = os.path.join(EXPORT_DIR, fn)
        if os.path.isfile(fp):
            sz = os.path.getsize(fp)
            total_size += sz
            files.append({"name": fn, "size_bytes": sz, "ext": os.path.splitext(fn)[1]})
    from .utils import format_file_size
    return {
        "exists": True, "path": EXPORT_DIR,
        "total_files": len(files), "total_size": format_file_size(total_size),
        "by_extension": dict(Counter(f["ext"] for f in files)),
        "files": sorted(files, key=lambda x: x["size_bytes"], reverse=True)[:20],
    }
