# -*- coding: utf-8 -*-
"""
运维报告生成器
==============
自动生成系统运维报告，支持纯文本、JSON、HTML 三种输出格式。

报表内容：系统概览、目录状态、资源使用、健康检查、缓存统计、导出文件列表。
"""

import os
import json
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from .config import BASE_DIR, REPORT_DIR
from .logger import get_logger

logger = get_logger("report_generator")
os.makedirs(REPORT_DIR, exist_ok=True)


def _uuid_short() -> str:
    import uuid
    return str(uuid.uuid4())[:8]


def _collect_system_info() -> Dict[str, Any]:
    import sys, platform
    return {
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "processor": platform.processor(),
        "arch": platform.architecture()[0],
        "implementation": platform.python_implementation(),
        "cwd": os.getcwd(),
    }


def _collect_directory_status() -> Dict[str, Any]:
    from .config import DATA_DIR, EXPORT_DIR, LOG_DIR, CACHE_DIR, RAG_DB_DIR
    dirs = {
        "data": DATA_DIR, "export": EXPORT_DIR,
        "log": LOG_DIR, "cache": CACHE_DIR, "rag_db": RAG_DB_DIR,
    }
    result = {}
    from .utils import format_file_size
    for name, path in dirs.items():
        exists = os.path.exists(path) and os.path.isdir(path)
        count = 0
        size = 0
        if exists:
            for fn in os.listdir(path):
                fp = os.path.join(path, fn)
                if os.path.isfile(fp):
                    count += 1
                    size += os.path.getsize(fp)
        result[name] = {
            "path": path, "exists": exists,
            "file_count": count, "size_formatted": format_file_size(size),
        }
    return result


def _collect_resource_usage() -> Dict[str, Any]:
    from .monitor import system_monitor, HAS_PSUTIL
    snap = system_monitor.snapshot()
    return {
        "disk": snap.get("disk", {}),
        "memory": snap.get("memory", {}),
        "cpu": snap.get("cpu", {}),
        "psutil_available": HAS_PSUTIL,
        "collected_at": snap.get("timestamp_formatted", ""),
    }


def _collect_health() -> Dict[str, Any]:
    from .health_checker import run_health_check
    return run_health_check().to_dict()


def _collect_cache_stats() -> Dict[str, Any]:
    from .cache_manager import get_all_cache_stats
    return get_all_cache_stats()


def _collect_export_files() -> List[Dict[str, Any]]:
    from .config import EXPORT_DIR
    files = []
    if os.path.exists(EXPORT_DIR):
        for fn in sorted(os.listdir(EXPORT_DIR), reverse=True):
            fp = os.path.join(EXPORT_DIR, fn)
            if os.path.isfile(fp):
                files.append({
                    "name": fn,
                    "size_kb": round(os.path.getsize(fp) / 1024, 1),
                    "modified": datetime.fromtimestamp(os.path.getmtime(fp)).strftime("%Y-%m-%d %H:%M:%S"),
                })
    return files[:20]


def gather_report_data() -> Dict[str, Any]:
    """收集完整报告数据"""
    return {
        "meta": {
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "uuid": _uuid_short(),
            "version": "1.0.0",
        },
        "system": _collect_system_info(),
        "directories": _collect_directory_status(),
        "resources": _collect_resource_usage(),
        "health": _collect_health(),
        "cache": _collect_cache_stats(),
        "exports": _collect_export_files(),
    }


# ============================================================================
# 文本报告
# ============================================================================

def generate_text_report(data: Optional[Dict[str, Any]] = None) -> str:
    if data is None:
        data = gather_report_data()

    w = 62
    L = []
    def sec(title):
        L.append(f"\n{'='*w}")
        L.append(f"  {title}")
        L.append(f"{'='*w}")

    m = data["meta"]
    L.append("=" * w)
    L.append("  唐诗意象数据运维管理系统 — 运维报告")
    L.append("=" * w)
    L.append(f"  生成时间: {m['generated_at']}    报告编号: {m['uuid']}")

    sec("系统信息")
    for k, v in data["system"].items():
        L.append(f"  {k:20s}: {v}")

    sec("目录状态")
    for name, info in data["directories"].items():
        s = "OK" if info["exists"] else "MISSING"
        L.append(f"  {name:12s} [{s:7s}] files={info['file_count']:4d}  size={info['size_formatted']}")

    sec("资源使用")
    r = data["resources"]
    d = r.get("disk", {})
    m2 = r.get("memory", {})
    c = r.get("cpu", {})
    L.append(f"  磁盘: {d.get('percent','?'):5}% used  |  free={d.get('free_gb','?'):7}GB / total={d.get('total_gb','?'):7}GB")
    L.append(f"  内存: {m2.get('percent','?'):5}% used  |  avail={m2.get('available_gb','?'):7}GB / total={m2.get('total_gb','?'):7}GB")
    L.append(f"  CPU : {c.get('percent','?'):5}% used  |  cores={c.get('count','?'):4}")

    sec("健康检查")
    h = data["health"]
    L.append(f"  状态: {h.get('status_text','?')}    通过率: {h.get('passed_rate',0)}% "
             f"({h.get('checks_passed',0)}/{h.get('checks_total',0)})")
    if h.get("issues"):
        for i, issue in enumerate(h["issues"], 1):
            L.append(f"    [FAIL] {issue}")
    if h.get("warnings"):
        for i, w2 in enumerate(h["warnings"], 1):
            L.append(f"    [WARN] {w2}")
    if h.get("recommendations"):
        for i, rec in enumerate(h["recommendations"], 1):
            L.append(f"    [TIP]  {rec}")

    sec("缓存统计")
    mc = data["cache"].get("memory", {})
    fc = data["cache"].get("file", {})
    L.append(f"  内存缓存: {mc.get('size',0)} items  |  hit_rate={mc.get('hit_rate_pct',0)}%")
    L.append(f"  文件缓存: {fc.get('size',0)} files  |  size={fc.get('total_size_formatted','?')}")

    sec("导出文件")
    exps = data["exports"]
    if exps:
        for e in exps[:10]:
            L.append(f"  {e['name']:35s} {str(e['size_kb'])+' KB':>12s}  {e['modified']}")
    else:
        L.append("  (无导出文件)")

    L.append(f"\n{'='*w}")
    L.append("  报告结束")
    L.append("=" * w)
    return "\n".join(L)


def generate_json_report(data: Optional[Dict[str, Any]] = None) -> str:
    if data is None:
        data = gather_report_data()
    return json.dumps(data, ensure_ascii=False, indent=2)


def generate_html_report(data: Optional[Dict[str, Any]] = None) -> str:
    if data is None:
        data = gather_report_data()

    m = data["meta"]
    s = data["system"]
    ds = data["directories"]
    r = data["resources"]
    h = data["health"]
    disk = r.get("disk", {})
    mem = r.get("memory", {})
    cpu = r.get("cpu", {})
    mc = data["cache"].get("memory", {})
    fc = data["cache"].get("file", {})

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>运维报告 — {m['generated_at']}</title>
<style>
body{{font-family:Arial,'Microsoft YaHei',sans-serif;margin:30px;color:#333}}
h1{{color:#2c3e50;border-bottom:3px solid #3498db;padding-bottom:10px}}
h2{{color:#2c3e50;margin-top:28px}}
.meta{{color:#888;font-size:14px}}
table{{border-collapse:collapse;width:100%;margin:10px 0}}
th{{background:#3498db;color:#fff;padding:8px 10px;text-align:left}}
td{{padding:8px 10px;border-bottom:1px solid #eee}}
.ok{{color:#27ae60;font-weight:bold}}
.warn{{color:#e67e22;font-weight:bold}}
.err{{color:#e74c3c;font-weight:bold}}
.footer{{margin-top:30px;color:#999;font-size:12px}}
</style>
</head>
<body>
<h1>唐诗意象数据运维管理系统 — 运维报告</h1>
<p class="meta">生成: {m['generated_at']} | 编号: {m['uuid']} | 版本: {m['version']}</p>

<h2>系统信息</h2>
<table>
<tr><th width="200">项目</th><th>值</th></tr>
<tr><td>Python</td><td>{s['python_version']}</td></tr>
<tr><td>操作系统</td><td>{s['platform']}</td></tr>
<tr><td>架构</td><td>{s['arch']}</td></tr>
</table>

<h2>目录状态</h2>
<table>
<tr><th>目录</th><th>状态</th><th>文件数</th><th>大小</th></tr>"""
    for name, info in ds.items():
        cls = "ok" if info["exists"] else "err"
        txt = "正常" if info["exists"] else "缺失"
        html += f'<tr><td>{name}</td><td class="{cls}">{txt}</td><td>{info["file_count"]}</td><td>{info["size_formatted"]}</td></tr>'

    html += f"""</table>
<h2>资源使用</h2>
<table>
<tr><th>资源</th><th>使用率</th><th>可用/总量</th></tr>
<tr><td>磁盘</td><td>{disk.get('percent','?')}%</td><td>{disk.get('free_gb','?')}GB / {disk.get('total_gb','?')}GB</td></tr>
<tr><td>内存</td><td>{mem.get('percent','?')}%</td><td>{mem.get('available_gb','?')}GB / {mem.get('total_gb','?')}GB</td></tr>
<tr><td>CPU</td><td>{cpu.get('percent','?')}%</td><td>{cpu.get('count','?')} 核</td></tr>
</table>

<h2>健康检查</h2>
<p>状态: <span class="{'ok' if h.get('is_healthy') else 'err'}">{h.get('status_text','?')}</span> | 通过率: {h.get('passed_rate',0)}% ({h.get('checks_passed',0)}/{h.get('checks_total',0)})</p>
<p>检查耗时: {h.get('check_duration',0)}秒</p>
"""
    if h.get("issues"):
        html += "<ul>" + "".join(f'<li class="err">{i}</li>' for i in h["issues"]) + "</ul>"
    if h.get("recommendations"):
        html += "<h3>建议操作</h3><ul>" + "".join(f"<li>{r2}</li>" for r2 in h["recommendations"]) + "</ul>"

    html += f"""<h2>缓存统计</h2>
<p>内存缓存: {mc.get('size',0)} 条 | 命中率: {mc.get('hit_rate_pct',0)}%</p>
<p>文件缓存: {fc.get('size',0)} 个 | 大小: {fc.get('total_size_formatted','?')}</p>

<div class="footer">由 唐诗意象数据运维管理系统 V1.0 自动生成</div>
</body></html>"""
    return html


def save_report(fmt: str = "text", out_dir: Optional[str] = None) -> str:
    if out_dir is None:
        out_dir = REPORT_DIR
    os.makedirs(out_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    generators = {"json": (generate_json_report, "json"), "html": (generate_html_report, "html")}
    gen, ext = generators.get(fmt, (generate_text_report, "txt"))
    content = gen()
    fpath = os.path.join(out_dir, f"ops_report_{ts}.{ext}")
    with open(fpath, "w", encoding="utf-8") as f:
        f.write(content)
    logger.info(f"运维报告已保存: {fpath}")
    return fpath


def list_reports() -> List[Dict[str, Any]]:
    reports = []
    if os.path.exists(REPORT_DIR):
        for fn in sorted(os.listdir(REPORT_DIR), reverse=True):
            fp = os.path.join(REPORT_DIR, fn)
            if os.path.isfile(fp):
                reports.append({
                    "name": fn,
                    "size_kb": round(os.path.getsize(fp) / 1024, 1),
                    "modified": datetime.fromtimestamp(os.path.getmtime(fp)).strftime("%Y-%m-%d %H:%M:%S"),
                })
    return reports
