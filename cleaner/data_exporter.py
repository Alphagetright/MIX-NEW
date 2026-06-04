# -*- coding: utf-8 -*-
"""
数据导出模块
============
支持清洗后的数据以多种格式导出：CSV (UTF-8-BOM)、JSON (结构化)、Excel (xlsx)、
TXT (文本报告)、HTML (可视化报告)。导出结果包含完整的元数据和清洗记录。
"""

import csv, json, os, time
from datetime import datetime
from typing import Any, Dict, List, Optional

from .config import EXPORT_DIR, EXPORT_CSV_ENCODING, EXPORT_JSON_INDENT
from .logger import get_logger
from .utils import format_file_size, sanitize_filename

logger = get_logger("data_exporter")
os.makedirs(EXPORT_DIR, exist_ok=True)

_export_history: List[Dict[str, Any]] = []


def _gen_filename(prefix: str, ext: str) -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return os.path.join(EXPORT_DIR, f"{prefix}_{ts}.{ext}")


def _add_history(fmt: str, path: str, rows: int, cols: int, dur: float, status: str = "success"):
    _export_history.append({
        "format": fmt, "file_path": path, "file_size": os.path.getsize(path) if os.path.exists(path) else 0,
        "rows_exported": rows, "columns_exported": cols, "duration": round(dur, 2),
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "status": status,
    })


# ─── CSV 导出 ───

def export_to_csv(rows: List[Dict[str, Any]], prefix: str = "clean_export",
                  fields: Optional[List[str]] = None, delimiter: str = ",") -> str:
    """导出为CSV文件 (UTF-8-BOM, Excel兼容)"""
    start = time.time()
    fp = _gen_filename(prefix, "csv")
    if fields:
        data = [{k: row.get(k, "") for k in fields} for row in rows]
    else:
        data = rows
    if not data:
        _add_history("csv", fp, 0, 0, time.time() - start, "failed")
        return fp
    headers = list(data[0].keys())
    with open(fp, "w", newline="", encoding=EXPORT_CSV_ENCODING) as f:
        f.write("﻿")  # BOM
        w = csv.writer(f, delimiter=delimiter)
        w.writerow(headers)
        for row in data:
            w.writerow([str(row.get(h, "")) for h in headers])
    dur = time.time() - start
    _add_history("csv", fp, len(data), len(headers), dur)
    logger.info(f"CSV导出: {fp} ({len(data)}行, {dur:.2f}s)")
    return fp


# ─── JSON 导出 ───

def export_to_json(data: Any, prefix: str = "clean_export",
                   include_metadata: bool = True) -> str:
    """导出为JSON文件"""
    start = time.time()
    fp = _gen_filename(prefix, "json")
    if include_metadata:
        output = {
            "metadata": {"exported_at": datetime.now().isoformat(), "generator": "tang_cleaner V1.0",
                         "record_count": len(data) if isinstance(data, list) else 1},
            "data": data,
        }
    else:
        output = data
    with open(fp, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=EXPORT_JSON_INDENT)
    dur = time.time() - start
    _add_history("json", fp, len(data) if isinstance(data, list) else 1, 0, dur)
    logger.info(f"JSON导出: {fp} ({dur:.2f}s)")
    return fp


# ─── TXT导出 ───

def export_to_text_report(stats: Dict[str, Any], batch_report: Any = None,
                          prefix: str = "clean_report") -> str:
    """导出为文本格式的清洗报告"""
    start = time.time()
    fp = _gen_filename(prefix, "txt")
    lines = []
    w = 65
    lines.append("=" * w)
    lines.append("  古典文学数据预处理与清洗 — 处理报告")
    lines.append("=" * w)
    lines.append(f"  生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")

    if stats:
        lines.append(f"[系统统计]")
        for k, v in stats.items():
            lines.append(f"  {k:20s}: {v}")
        lines.append("")

    if batch_report:
        lines.append(f"[批量处理]")
        if hasattr(batch_report, 'to_dict'):
            for k, v in batch_report.to_dict().items():
                lines.append(f"  {k:20s}: {v}")
        lines.append("")

    lines.append("=" * w)
    lines.append("  由 古典文学数据预处理与清洗系统 V1.0 生成")
    lines.append("=" * w)

    with open(fp, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    dur = time.time() - start
    _add_history("txt", fp, 0, 0, dur)
    logger.info(f"TXT报告: {fp}")
    return fp


# ─── HTML 报告导出 ───

def export_to_html_report(quality_report: Any, cleaning_results: List[Any] = None,
                          prefix: str = "clean_report") -> str:
    """导出为HTML格式的可视化报告"""
    start = time.time()
    fp = _gen_filename(prefix, "html")
    qr = quality_report.to_dict() if hasattr(quality_report, 'to_dict') else quality_report

    html = f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<title>数据预处理报告</title>
<style>
body{{font-family:Arial,'Microsoft YaHei',sans-serif;margin:24px;max-width:1000px;color:#333}}
h1{{color:#2c3e50;border-bottom:3px solid #3498db;padding-bottom:10px}}
h2{{color:#2c3e50;margin-top:24px;border-left:4px solid #3498db;padding-left:12px}}
.meta{{color:#888;font-size:13px}}
table{{border-collapse:collapse;width:100%;margin:10px 0}}
th{{background:#3498db;color:#fff;padding:8px 10px;text-align:left;font-size:13px}}
td{{padding:8px 10px;border-bottom:1px solid #eee;font-size:13px}}
.good{{color:#27ae60;font-weight:bold}}.warn{{color:#e67e22}}.bad{{color:#e74c3c}}
.card{{background:#fff;border-radius:8px;padding:16px;margin:12px 0;box-shadow:0 2px 8px rgba(0,0,0,0.06)}}
.footer{{margin-top:30px;color:#999;font-size:12px;border-top:1px solid #eee;padding-top:12px}}
</style></head><body>
<h1>古典文学数据预处理与清洗报告</h1>
<p class="meta">生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>

<div class="card"><h2>数据概览</h2>
<table><tr><th>指标</th><th>数值</th></tr>
<tr><td>总文件数</td><td>{qr.get('total_files', 'N/A')}</td></tr>
<tr><td>质量评分</td><td class="{'good' if qr.get('overall_score', 0) >= 80 else 'warn' if qr.get('overall_score', 0) >= 60 else 'bad'}">{qr.get('overall_score', 'N/A')}/100</td></tr>
<tr><td>有效JSON</td><td>{qr.get('valid_json_count', 'N/A')}</td></tr>
<tr><td>无效JSON</td><td>{qr.get('invalid_json_count', 'N/A')}</td></tr>
</table></div>
"""

    if qr.get('encoding_stats'):
        html += '<div class="card"><h2>编码分布</h2><table><tr><th>编码</th><th>文件数</th></tr>'
        for enc, cnt in sorted(qr['encoding_stats'].items(), key=lambda x: x[1], reverse=True):
            html += f"<tr><td>{enc}</td><td>{cnt}</td></tr>"
        html += "</table></div>"

    if qr.get('field_coverage'):
        html += '<div class="card"><h2>字段覆盖度</h2><table><tr><th>字段</th><th>覆盖度</th></tr>'
        for field, pct in qr['field_coverage'].items():
            cls = "good" if pct >= 90 else "warn" if pct >= 70 else "bad"
            html += f'<tr><td>{field}</td><td class="{cls}">{pct}%</td></tr>'
        html += "</table></div>"

    html += '<div class="footer">由 古典文学数据预处理与清洗系统 V1.0 自动生成</div></body></html>'

    with open(fp, "w", encoding="utf-8") as f:
        f.write(html)
    dur = time.time() - start
    _add_history("html", fp, 0, 0, dur)
    logger.info(f"HTML报告: {fp}")
    return fp


# ─── 批量导出 ───

def batch_export(data: Dict[str, Any], formats: List[str] = None,
                 prefix: str = "full_export") -> Dict[str, str]:
    """批量多格式导出"""
    if formats is None:
        formats = ["csv", "json", "html"]
    results = {}
    for fmt in formats:
        try:
            if fmt == "csv":
                results[fmt] = export_to_csv(data.get("rows", []), prefix=f"{prefix}_{fmt}")
            elif fmt == "json":
                results[fmt] = export_to_json(data, prefix=f"{prefix}_{fmt}")
            elif fmt == "html":
                results[fmt] = export_to_html_report(data.get("quality_report", {}), prefix=f"{prefix}_{fmt}")
            elif fmt == "txt":
                results[fmt] = export_to_text_report(data.get("stats", {}), prefix=f"{prefix}_{fmt}")
        except Exception as e:
            logger.error(f"批量导出失败 [{fmt}]: {e}")
            results[fmt] = f"ERROR: {e}"
    return results


def list_exports() -> List[Dict[str, Any]]:
    """列出所有导出历史"""
    records = []
    if os.path.exists(EXPORT_DIR):
        for fn in sorted(os.listdir(EXPORT_DIR), reverse=True):
            fp = os.path.join(EXPORT_DIR, fn)
            if os.path.isfile(fp):
                records.append({"name": fn, "size": format_file_size(os.path.getsize(fp)),
                                "modified": datetime.fromtimestamp(os.path.getmtime(fp)).strftime("%Y-%m-%d %H:%M:%S")})
    return records + _export_history


def clear_exports() -> int:
    """清空导出目录"""
    count = 0
    if os.path.exists(EXPORT_DIR):
        for fn in os.listdir(EXPORT_DIR):
            try: os.remove(os.path.join(EXPORT_DIR, fn)); count += 1
            except OSError: pass
    _export_history.clear()
    logger.info(f"导出目录已清空: {count}文件")
    return count
