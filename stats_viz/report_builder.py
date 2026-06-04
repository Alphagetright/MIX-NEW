# -*- coding: utf-8 -*-
"""
统计报告生成器
=============
生成格式化的多维统计分析报告，支持文本、JSON、HTML 三种格式。
"""

import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from .config import REPORT_DIR
from .logger import get_logger
from .data_loader import get_summary_stats

logger = get_logger("report_builder")
os.makedirs(REPORT_DIR, exist_ok=True)


def generate_text_report(stats_summary: Dict[str, Any]) -> str:
    """生成纯文本格式统计分析报告"""
    w = 65
    L = []
    L.append("=" * w)
    L.append("  诗歌意象多维统计分析报告")
    L.append("=" * w)
    L.append(f"  生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    base = stats_summary.get("基础统计", {})
    L.append(f"\n{'─' * w}")
    L.append("  [一] 基础统计")
    L.append(f"{'─' * w}")
    for k, v in base.items():
        L.append(f"    {k}: {v}")

    L.append(f"\n{'─' * w}")
    L.append("  [二] 高频意象 Top10")
    L.append(f"{'─' * w}")
    for item in stats_summary.get("意象频次Top10", []):
        L.append(f"    {item['text']:20s}  {item['count']:5d}")

    L.append(f"\n{'─' * w}")
    L.append("  [三] 分类域分布")
    L.append(f"{'─' * w}")
    for k, v in sorted(stats_summary.get("分类域分布", {}).items(), key=lambda x: x[1], reverse=True):
        L.append(f"    {k:20s}  {v:5d}")

    L.append(f"\n{'─' * w}")
    L.append("  [四] 大类分布")
    L.append(f"{'─' * w}")
    for k, v in stats_summary.get("大类分布", {}).items():
        L.append(f"    {k:20s}  {v:5d}")

    L.append(f"\n{'─' * w}")
    L.append("  [五] 情感类别分布")
    L.append(f"{'─' * w}")
    for k, v in sorted(stats_summary.get("情感类别分布", {}).items(), key=lambda x: x[1], reverse=True):
        L.append(f"    {k:20s}  {v:5d}")

    L.append(f"\n{'─' * w}")
    L.append("  [六] 情感极性分布")
    L.append(f"{'─' * w}")
    for k, v in stats_summary.get("情感极性分布", {}).items():
        L.append(f"    {k:20s}  {v:5d}")

    L.append(f"\n{'─' * w}")
    L.append("  [七] 感知通道分布")
    L.append(f"{'─' * w}")
    for k, v in stats_summary.get("感知通道分布", {}).items():
        L.append(f"    {k:20s}  {v:5d}")

    L.append(f"\n{'─' * w}")
    L.append("  [八] 诗人 Top10")
    L.append(f"{'─' * w}")
    for item in stats_summary.get("诗人Top10", []):
        L.append(f"    {item['author']:20s}  {item['total']:5d}")

    L.append(f"\n{'=' * w}")
    L.append("  报告结束")
    L.append("=" * w)
    return "\n".join(L)


def generate_json_report(stats_summary: Dict[str, Any]) -> str:
    """生成 JSON 格式统计分析报告"""
    report = {
        "title": "诗歌意象多维统计分析报告",
        "generated_at": datetime.now().isoformat(),
        "generator": "诗歌意象多维统计与可视化系统 V1.0",
        "data": stats_summary,
    }
    return json.dumps(report, ensure_ascii=False, indent=2)


def generate_html_report(stats_summary: Dict[str, Any]) -> str:
    """生成 HTML 格式统计分析报告"""
    base = stats_summary.get("基础统计", {})
    top10 = stats_summary.get("意象频次Top10", [])
    cat = stats_summary.get("分类域分布", {})
    emo = stats_summary.get("情感类别分布", {})
    pol = stats_summary.get("情感极性分布", {})
    perc = stats_summary.get("感知通道分布", {})
    poets = stats_summary.get("诗人Top10", [])

    html = f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<title>诗歌意象统计分析报告</title>
<style>
body{{font-family:Arial,'Microsoft YaHei',sans-serif;margin:28px;max-width:900px;color:#333}}
h1{{color:#2c3e50;border-bottom:3px solid #3498db;padding-bottom:10px}}
h2{{color:#2c3e50;margin-top:28px;border-left:4px solid #3498db;padding-left:12px}}
.meta{{color:#888;font-size:13px;margin-bottom:20px}}
table{{border-collapse:collapse;width:100%;margin:10px 0}}
th{{background:#3498db;color:#fff;padding:8px 10px;text-align:left;font-size:13px}}
td{{padding:8px 10px;border-bottom:1px solid #eee;font-size:13px}}
tr:hover{{background:#f5f8fa}}
.footer{{margin-top:30px;color:#999;font-size:12px;border-top:1px solid #eee;padding-top:12px}}
</style></head><body>
<h1>诗歌意象多维统计分析报告</h1>
<p class="meta">生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>

<h2>基础统计</h2>
<table><tr><th width="250">指标</th><th>数值</th></tr>"""

    for k, v in base.items():
        html += f"<tr><td>{k}</td><td><strong>{v}</strong></td></tr>"
    html += "</table>"

    html += "<h2>高频意象 Top10</h2><table><tr><th>意象</th><th>频次</th></tr>"
    for item in top10:
        html += f"<tr><td>{item['text']}</td><td>{item['count']}</td></tr>"
    html += "</table>"

    html += "<h2>分类域分布</h2><table><tr><th>分类</th><th>数量</th></tr>"
    for k, v in sorted(cat.items(), key=lambda x: x[1], reverse=True):
        html += f"<tr><td>{k}</td><td>{v}</td></tr>"
    html += "</table>"

    html += "<h2>情感类别分布</h2><table><tr><th>情感</th><th>数量</th></tr>"
    for k, v in sorted(emo.items(), key=lambda x: x[1], reverse=True):
        html += f"<tr><td>{k}</td><td>{v}</td></tr>"
    html += "</table>"

    html += "<h2>情感极性分布</h2><table><tr><th>极性</th><th>数量</th></tr>"
    for k, v in pol.items():
        html += f"<tr><td>{k}</td><td>{v}</td></tr>"
    html += "</table>"

    html += "<h2>感知通道分布</h2><table><tr><th>通道</th><th>数量</th></tr>"
    for k, v in sorted(perc.items(), key=lambda x: x[1], reverse=True):
        html += f"<tr><td>{k}</td><td>{v}</td></tr>"
    html += "</table>"

    html += "<h2>诗人意象使用量 Top10</h2><table><tr><th>诗人</th><th>意象数</th></tr>"
    for item in poets:
        html += f"<tr><td>{item['author']}</td><td>{item['total']}</td></tr>"
    html += "</table>"

    html += '<div class="footer">由 诗歌意象多维统计与可视化系统 V1.0 自动生成</div></body></html>'
    return html


def save_report(stats_summary: Dict[str, Any], fmt: str = "text") -> str:
    """保存统计报告到文件"""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    generators = {"json": (generate_json_report, "json"), "html": (generate_html_report, "html")}
    gen, ext = generators.get(fmt, (generate_text_report, "txt"))
    content = gen(stats_summary)
    fp = os.path.join(REPORT_DIR, f"stats_report_{ts}.{ext}")
    with open(fp, "w", encoding="utf-8") as f:
        f.write(content)
    logger.info(f"统计报告已保存: {fp}")
    return fp


def list_reports() -> List[Dict[str, Any]]:
    """列出所有统计报告"""
    reports = []
    if os.path.exists(REPORT_DIR):
        for fn in sorted(os.listdir(REPORT_DIR), reverse=True):
            fp = os.path.join(REPORT_DIR, fn)
            if os.path.isfile(fp):
                reports.append({"name": fn, "size_kb": round(os.path.getsize(fp) / 1024, 1),
                                "modified": datetime.fromtimestamp(os.path.getmtime(fp)).strftime("%Y-%m-%d %H:%M:%S")})
    return reports


# ─── 扩展报告格式 ───

def generate_markdown_report(stats_summary: Dict[str, Any]) -> str:
    """生成 Markdown 格式统计分析报告"""
    base = stats_summary.get("基础统计", {})
    top10 = stats_summary.get("意象频次Top10", [])
    cat = stats_summary.get("分类域分布", {})
    emo = stats_summary.get("情感类别分布", {})

    md = []
    md.append("# 诗歌意象多维统计分析报告\n")
    md.append(f"> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    md.append("## 基础统计\n")
    md.append("| 指标 | 数值 |")
    md.append("|------|------|")
    for k, v in base.items():
        md.append(f"| {k} | {v} |")

    md.append("\n## 高频意象 Top10\n")
    md.append("| 意象 | 频次 |")
    md.append("|------|------|")
    for item in top10:
        md.append(f"| {item['text']} | {item['count']} |")

    md.append("\n## 分类域分布\n")
    md.append("| 分类 | 数量 |")
    md.append("|------|------|")
    for k, v in sorted(cat.items(), key=lambda x: x[1], reverse=True):
        md.append(f"| {k} | {v} |")

    md.append("\n## 情感分布\n")
    md.append("| 情感 | 数量 |")
    md.append("|------|------|")
    for k, v in sorted(emo.items(), key=lambda x: x[1], reverse=True):
        md.append(f"| {k} | {v} |")

    md.append(f"\n---\n*由 诗歌意象多维统计与可视化系统 V1.0 生成*")
    return "\n".join(md)


def generate_csv_report(stats_summary: Dict[str, Any]) -> str:
    """生成 CSV 格式统计摘要"""
    import csv, io
    output = io.StringIO()
    w = csv.writer(output)
    w.writerow(["章节", "项目", "数值"])
    for section, data in stats_summary.items():
        if isinstance(data, dict):
            for k, v in data.items():
                w.writerow([section, k, v])
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    vals = "; ".join(f"{ik}={iv}" for ik, iv in item.items())
                    w.writerow([section, "", vals])
    return output.getvalue()


def export_all_formats(stats_summary: Dict[str, Any],
                       output_dir: Optional[str] = None) -> Dict[str, str]:
    """一次性导出所有格式的报告"""
    if output_dir is None:
        output_dir = REPORT_DIR
    os.makedirs(output_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    files = {}

    formats = {
        "txt": generate_text_report,
        "json": generate_json_report,
        "html": generate_html_report,
        "md": generate_markdown_report,
    }
    for ext, generator in formats.items():
        fp = os.path.join(output_dir, f"full_report_{ts}.{ext}")
        content = generator(stats_summary)
        encoding = "utf-8" if ext != "csv" else "utf-8-sig"
        with open(fp, "w", encoding=encoding) as f:
            f.write(content)
        files[ext] = fp

    logger.info(f"全格式报告已导出: {len(files)} 种格式")
    return files


def clear_reports() -> int:
    """清空报告目录"""
    count = 0
    if os.path.exists(REPORT_DIR):
        for fn in os.listdir(REPORT_DIR):
            try:
                os.remove(os.path.join(REPORT_DIR, fn))
                count += 1
            except OSError:
                pass
    return count
