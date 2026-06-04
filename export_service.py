# -*- coding: utf-8 -*-
"""
数据导出服务 — CSV / JSON / 报告导出
"""
import csv
import json
import os
import time
from typing import List, Dict, Optional

from config import EXPORT_DIR, EXPORT_CSV_ENCODING
from errors import ExportError
from logger import get_logger

logger = get_logger("export")


def ensure_export_dir():
    if not os.path.exists(EXPORT_DIR):
        os.makedirs(EXPORT_DIR, exist_ok=True)


class ExportService:
    """数据导出服务"""

    @staticmethod
    def export_traceback_to_csv(data: List[Dict], filename: str = None) -> str:
        """将溯源数据导出为 CSV"""
        ensure_export_dir()
        filename = filename or f"traceback_export_{int(time.time())}.csv"
        filepath = os.path.join(EXPORT_DIR, filename)

        if not data:
            raise ExportError("没有数据可导出")

        fieldnames = [
            "poem_id", "title", "genre", "cat", "txt",
            "emotion", "line", "词性", "成分类型", "感知通道",
            "素材类型", "内部结构", "指涉来源", "表现功能",
            "文化流通性", "跨文化性", "认知强度", "核心意象",
            "结构功能组", "情感极性", "情感类别", "情感置信度",
            "大类编码", "子类编码",
        ]
        try:
            with open(filepath, "w", encoding=EXPORT_CSV_ENCODING, newline="") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
                writer.writeheader()
                for row in data:
                    writer.writerow(row)
            logger.info(f"CSV 导出成功: {filepath} ({len(data)} 条)")
            return filepath
        except IOError as e:
            raise ExportError(f"CSV 写入失败: {e}")

    @staticmethod
    def export_to_json(data, filename: str = None, indent: int = 2) -> str:
        """将数据导出为 JSON"""
        ensure_export_dir()
        filename = filename or f"export_{int(time.time())}.json"
        filepath = os.path.join(EXPORT_DIR, filename)

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=indent)
            logger.info(f"JSON 导出成功: {filepath}")
            return filepath
        except (IOError, TypeError) as e:
            raise ExportError(f"JSON 写入失败: {e}")

    @staticmethod
    def export_summary_report(report: Dict, filename: str = None) -> str:
        """导出统计分析报告（JSON 格式）"""
        return ExportService.export_to_json(report, filename or f"report_{int(time.time())}.json")

    @staticmethod
    def export_filtered_slice(
        data: List[Dict],
        start: int = 0,
        end: int = None,
        filename: str = None,
    ) -> str:
        """导出数据子集"""
        subset = data[start:end] if end else data[start:]
        return ExportService.export_to_json(
            {"total": len(data), "start": start, "end": end or len(data),
             "count": len(subset), "data": subset},
            filename or f"slice_{start}_{end or len(data)}.json",
        )

    @staticmethod
    def list_exports() -> List[Dict]:
        """列出已导出的文件"""
        ensure_export_dir()
        files = []
        for fname in os.listdir(EXPORT_DIR):
            fpath = os.path.join(EXPORT_DIR, fname)
            if os.path.isfile(fpath):
                files.append({
                    "name": fname,
                    "path": fpath,
                    "size": os.path.getsize(fpath),
                    "mtime": os.path.getmtime(fpath),
                })
        return sorted(files, key=lambda x: -x["mtime"])

    @staticmethod
    def clear_exports() -> int:
        """清空导出目录"""
        ensure_export_dir()
        count = 0
        for fname in os.listdir(EXPORT_DIR):
            fpath = os.path.join(EXPORT_DIR, fname)
            if os.path.isfile(fpath):
                os.remove(fpath)
                count += 1
        logger.info(f"清空导出目录: 移除 {count} 个文件")
        return count
