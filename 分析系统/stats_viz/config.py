# -*- coding: utf-8 -*-
"""
配置管理模块
============
全局配置常量、环境变量读取、分类体系映射。
"""

import os
import json
from typing import Dict, Any, Optional
from dataclasses import dataclass, field

# ─── 基础路径 ───
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.environ.get("TSV_DATA_DIR", os.path.join(BASE_DIR, "..", "poem_json"))
EXPORT_DIR = os.environ.get("TSV_EXPORT_DIR", os.path.join(BASE_DIR, "..", "exports"))
LOG_DIR = os.environ.get("TSV_LOG_DIR", os.path.join(BASE_DIR, "..", "logs"))
REPORT_DIR = os.environ.get("TSV_REPORT_DIR", os.path.join(BASE_DIR, "..", "reports"))

# ─── 统计配置 ───
TOP_IMAGES_N = int(os.environ.get("TSV_TOP_N", "50"))
CHART_DEFAULT_COLOR = "#3498db"
CHART_CATEGORY_COLOR = "#9b59b6"
STATS_CACHE_TTL = int(os.environ.get("TSV_CACHE_TTL", "300"))

# ─── 导出配置 ───
EXPORT_CSV_ENCODING = "utf-8-sig"
EXPORT_JSON_INDENT = 2
EXPORT_MAX_ROWS = int(os.environ.get("TSV_EXPORT_MAX_ROWS", "50000"))

# ─── 日志配置 ───
LOG_LEVEL = os.environ.get("TSV_LOG_LEVEL", "INFO")
LOG_MAX_BYTES = 10 * 1024 * 1024
LOG_BACKUP_COUNT = 5

# ─── 分页配置 ───
PAGE_SIZE = int(os.environ.get("TSV_PAGE_SIZE", "25"))
RENDER_LIMIT = int(os.environ.get("TSV_RENDER_LIMIT", "5000"))

# ─── 分类名称映射 ───
CATEGORY_NAME_MAP: Dict[str, str] = {
    "1-1": "天文意象", "1-2": "地理意象", "1-3": "植物意象", "1-4": "动物意象",
    "2-1": "生产生活意象", "2-2": "军事战争意象", "2-3": "制度观念意象",
    "3-1": "人造器物意象", "3-2": "人类自身意象", "3-3": "人物角色意象", "3-4": "文化意象",
}

CATEGORY_MAJOR_MAP: Dict[str, str] = {
    "1": "自然意象", "2": "社会意象", "3": "人文意象",
}

DIMENSION_KEYS = ["感知通道", "素材类型", "指涉来源", "表现功能"]

EMOTION_LABELS = ["喜悦", "悲伤", "思乡", "忧愁", "豪迈", "感慨", "闲适", "愤怒", "恐惧", "爱慕", "孤独", "豁达", "未知"]
EMOTION_POLARITIES = {"+": "正面", "-": "负面", "0": "中性"}


# ─── 配置管理器 ───
class ConfigManager:
    """运行时配置管理器，支持环境变量覆盖和快照导出"""

    def __init__(self):
        self._overrides: Dict[str, Any] = {}

    def get(self, key: str, default: Any = None) -> Any:
        if key in self._overrides:
            return self._overrides[key]
        env_val = os.environ.get(f"TSV_{key.upper()}")
        if env_val is not None:
            return env_val
        mod = __import__(__name__)
        if hasattr(mod, key.upper()):
            return getattr(mod, key.upper())
        return default

    def set(self, key: str, value: Any) -> None:
        self._overrides[key] = value

    def reset(self, key: str) -> None:
        self._overrides.pop(key, None)

    def snapshot(self) -> Dict[str, Any]:
        keys = ["DATA_DIR", "EXPORT_DIR", "TOP_IMAGES_N", "CHART_DEFAULT_COLOR",
                "STATS_CACHE_TTL", "PAGE_SIZE", "RENDER_LIMIT", "LOG_LEVEL"]
        return {k: self.get(k) for k in keys}


config_manager = ConfigManager()


# ─── 扩展配置区域 ───

# 可视化默认设置
VIZ_DEFAULTS = {
    "width": 800, "height": 500, "theme": "default",
    "animation": True, "animation_duration": 800,
    "title_font_size": 16, "label_font_size": 12,
}

# 报告默认设置
REPORT_DEFAULTS = {
    "include_charts": True, "include_raw_data": False,
    "max_top_items": 50, "default_format": "text",
    "date_format": "%Y-%m-%d %H:%M:%S",
}

# 数据源配置
DATA_SOURCE_CONFIG = {
    "primary_encoding": "utf-8",
    "fallback_encoding": "gbk",
    "skip_filenames": ["all_data.json", "dashboard_interactive_pro.html",
                       "dashboard_FINAL_DASHBOARD.html", "Thesis_Dashboard.html"],
    "required_poem_fields": ["诗歌编号", "标题", "作者"],
    "imagery_flag_field": "是否意象",
    "imagery_flag_value": "1",
}

# 分类体系完整定义
FULL_CATEGORY_HIERARCHY = {
    "1": {
        "name": "自然意象",
        "subs": {"1-1": "天文意象", "1-2": "地理意象", "1-3": "植物意象", "1-4": "动物意象"},
    },
    "2": {
        "name": "社会意象",
        "subs": {"2-1": "生产生活意象", "2-2": "军事战争意象", "2-3": "制度观念意象"},
    },
    "3": {
        "name": "人文意象",
        "subs": {"3-1": "人造器物意象", "3-2": "人类自身意象", "3-3": "人物角色意象", "3-4": "文化意象"},
    },
}

# 统计维度元信息
DIMENSION_META = {
    "感知通道": {"description": "意象触发的感官通道", "values": ["视觉", "听觉", "嗅觉", "味觉", "触觉", "通感"]},
    "素材类型": {"description": "意象所涉及的素材类别", "values": ["自然物", "人造物", "人事", "抽象"]},
    "指涉来源": {"description": "意象的文化来源", "values": ["神话", "历史", "文学", "民间", "个人"]},
    "表现功能": {"description": "意象的表现功能", "values": ["象征", "比喻", "写实", "渲染", "对比"]},
}

# 已知诗人列表
KNOWN_POETS = [
    "杜甫", "李白", "王维", "白居易", "苏轼", "李商隐", "杜牧", "王昌龄", "孟浩然",
    "柳宗元", "韩愈", "欧阳修", "辛弃疾", "李清照", "陶渊明", "张九龄", "司空曙",
    "刘长卿", "韦应物", "岑参", "高适", "王之涣", "元稹", "温庭筠", "晏殊",
]
