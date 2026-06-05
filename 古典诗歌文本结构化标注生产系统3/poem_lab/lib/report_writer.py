# -*- coding: utf-8 -*-
"""批处理报告生成器 — 结构化文本/JSON 报告，含摘要、耗时、质量、token 估算"""
import json, time, os
from datetime import datetime

from . import config_loader, persistence


def generate_text_report(rid: str) -> str:
    """生成纯文本格式批处理报告"""
    run = persistence.get_batch_run(rid)
    if not run:
        return "批次不存在"

    results = persistence.get_batch_results(rid)
    lines = []
    lines.append("=" * 60)
    lines.append("  古典诗歌标注批处理报告")
    lines.append("=" * 60)
    lines.append(f"  批处理ID   : {rid}")
    lines.append(f"  启动时间   : {run.get('started_at', '-')}")
    lines.append(f"  完成时间   : {run.get('updated_at', '-')}")
    lines.append(f"  状态       : {_status_cn(run.get('status', 'unknown'))}")
    lines.append(f"  总数       : {run.get('total', 0)} 首")
    lines.append(f"  成功       : {run.get('completed', 0)} 首")
    lines.append(f"  失败       : {run.get('failed', 0)} 首")
    lines.append(f"  成功率     : {_success_rate(run)}%")
    lines.append("-" * 60)

    # 逐首结果
    lines.append(f"  {'编号':<8s} {'标题':<16s} {'状态':<6s} {'输出字段数':>8s}")
    lines.append("  " + "-" * 44)
    for r in results:
        status = "OK" if r.get("success") else "FAIL"
        parsed = r.get("result") or {}
        field_count = len(parsed) if isinstance(parsed, dict) else 0
        no = r.get("编号", "")[:6]
        title = r.get("标题", "")[:14]
        lines.append(f"  {no:<8s} {title:<16s} {status:<6s} {field_count:>8d}")

    lines.append("-" * 60)

    # Token 估算
    col_mapping = run.get("column_mapping", [])
    if isinstance(col_mapping, str):
        try:
            col_mapping = json.loads(col_mapping)
        except json.JSONDecodeError:
            col_mapping = []
    est_per_poem = 500
    total_success = run.get("completed", 0)
    total_est = total_success * est_per_poem
    lines.append(f"  预估Token消耗: ~{total_est:,} ({total_success}首 × ~{est_per_poem}/首)")

    # 导出文件
    csv_path = run.get("csv_path")
    json_path = run.get("json_path")
    if csv_path:
        lines.append(f"  CSV 导出: {csv_path}")
    if json_path:
        lines.append(f"  JSON导出: {json_path}")

    # 时间统计
    try:
        start = datetime.strptime(run.get("started_at", ""), "%Y-%m-%d %H:%M:%S")
        end = datetime.strptime(run.get("updated_at", ""), "%Y-%m-%d %H:%M:%S")
        duration = (end - start).total_seconds()
        rate = total_success / (duration / 60) if duration > 0 else 0
        lines.append(f"  总耗时: {duration:.1f}秒 | 速率: {rate:.1f} 首/分钟")
    except (ValueError, TypeError):
        pass

    lines.append("=" * 60)
    return "\n".join(lines)


def generate_json_report(rid: str) -> dict:
    """生成 JSON 格式结构化报告"""
    run = persistence.get_batch_run(rid)
    if not run:
        return {"error": "批次不存在"}

    results = persistence.get_batch_results(rid)
    return {
        "report_type": "batch_annotation_report",
        "batch_id": rid,
        "started_at": run.get("started_at"),
        "updated_at": run.get("updated_at"),
        "status": run.get("status"),
        "statistics": {
            "total": run.get("total", 0),
            "completed": run.get("completed", 0),
            "failed": run.get("failed", 0),
            "success_rate_pct": _success_rate(run)
        },
        "sample_results": [
            {"编号": r.get("编号"), "标题": r.get("标题"), "作者": r.get("作者"),
             "success": bool(r.get("success")), "result": r.get("result")}
            for r in results[:5]
        ],
        "export_files": {
            "csv": run.get("csv_path"),
            "json": run.get("json_path")
        }
    }


def generate_executive_summary(rid: str) -> dict:
    """生成执行摘要（用于 dashboard 展示）"""
    run = persistence.get_batch_run(rid)
    if not run:
        return {"error": "批次不存在"}

    results = persistence.get_batch_results(rid)
    total = run.get("total", 0)
    completed = run.get("completed", 0)
    failed = run.get("failed", 0)

    return {
        "batch_id": rid,
        "status": run.get("status"),
        "rate": round(completed / max(total, 1) * 100, 1),
        "total": total,
        "completed": completed,
        "failed": failed,
        "failed_list": [
            {"编号": r.get("编号"), "标题": r.get("标题")}
            for r in results if not r.get("success")
        ][:10],
        "export_csv": run.get("csv_path"),
        "export_json": run.get("json_path"),
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }


def _success_rate(run: dict) -> int:
    total = run.get("total", 1) or 1
    completed = run.get("completed", 0)
    return round(completed / total * 100)


def _status_cn(status: str) -> str:
    return {"running": "运行中", "completed": "已完成", "failed": "失败", "paused": "已暂停"}.get(status, status)
