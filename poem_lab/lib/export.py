# -*- coding: utf-8 -*-
"""
数据导出 — CSV / JSON / HTML
"""
import os, json, time
from . import config_loader


def export_csv(filename: str, csv_content: str) -> str:
    """导出 CSV 文件，UTF-8 BOM 确保 Excel 兼容"""
    export_dir = config_loader.get("EXPORTS_DIR", "")
    if not os.path.exists(export_dir):
        os.makedirs(export_dir)
    path = os.path.join(export_dir, filename)
    with open(path, "w", encoding="utf-8-sig") as f:
        f.write(csv_content)
    return path


def export_json(filename: str, data: dict) -> str:
    """导出 JSON 文件"""
    export_dir = config_loader.get("EXPORTS_DIR", "")
    if not os.path.exists(export_dir):
        os.makedirs(export_dir)
    path = os.path.join(export_dir, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return path


def list_exports() -> list:
    """列出所有导出文件"""
    export_dir = config_loader.get("EXPORTS_DIR", "")
    if not os.path.exists(export_dir):
        return []
    files = []
    for f in os.listdir(export_dir):
        path = os.path.join(export_dir, f)
        files.append({
            "name": f,
            "size": os.path.getsize(path),
            "mtime": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(os.path.getmtime(path)))
        })
    return sorted(files, key=lambda x: x["mtime"], reverse=True)
