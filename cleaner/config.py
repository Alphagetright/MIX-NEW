# -*- coding: utf-8 -*-
"""配置管理模块"""
import os
from typing import Dict, Any

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.environ.get("TC_DATA_DIR", os.path.join(BASE_DIR, "..", "poem_json"))
EXPORT_DIR = os.environ.get("TC_EXPORT_DIR", os.path.join(BASE_DIR, "..", "exports"))
LOG_DIR = os.environ.get("TC_LOG_DIR", os.path.join(BASE_DIR, "..", "logs"))
BACKUP_DIR = os.environ.get("TC_BACKUP_DIR", os.path.join(BASE_DIR, "..", "backups"))
REPORT_DIR = os.environ.get("TC_REPORT_DIR", os.path.join(BASE_DIR, "..", "reports"))

LOG_LEVEL = os.environ.get("TC_LOG_LEVEL", "INFO")
LOG_MAX_BYTES = 10 * 1024 * 1024
LOG_BACKUP_COUNT = 5

PREPROC_MAX_ERRORS = int(os.environ.get("TC_MAX_ERRORS", "100"))
PREPROC_AUTO_FIX = os.environ.get("TC_AUTO_FIX", "false").lower() == "true"
SCANNER_MAX_FILE_SIZE_MB = int(os.environ.get("TC_MAX_FILE_SIZE_MB", "500"))

DEDUP_SIMILARITY_THRESHOLD = float(os.environ.get("TC_DEDUP_THRESHOLD", "0.85"))
DEDUP_MAX_PAIRS = int(os.environ.get("TC_DEDUP_MAX_PAIRS", "10000"))

BATCH_MAX_WORKERS = int(os.environ.get("TC_BATCH_WORKERS", "4"))
BATCH_TIMEOUT = int(os.environ.get("TC_BATCH_TIMEOUT", "3600"))

VALIDATION_STRICT_MODE = os.environ.get("TC_STRICT", "false").lower() == "true"
EXPORT_CSV_ENCODING = "utf-8-sig"
EXPORT_JSON_INDENT = 2

CATEGORY_NAME_MAP: Dict[str, str] = {
    "1-1": "天文意象", "1-2": "地理意象", "1-3": "植物意象", "1-4": "动物意象",
    "2-1": "生产生活意象", "2-2": "军事战争意象", "2-3": "制度观念意象",
    "3-1": "人造器物意象", "3-2": "人类自身意象", "3-3": "人物角色意象", "3-4": "文化意象",
}

REQUIRED_POEM_FIELDS = ["诗歌编号", "标题", "作者"]
DIMENSION_KEYS = ["感知通道", "素材类型", "指涉来源", "表现功能"]

COMMON_ENCODINGS = ["utf-8", "gbk", "gb2312", "utf-16", "utf-16-le", "utf-16-be", "latin-1", "cp1252"]


class ConfigManager:
    def __init__(self):
        self._overrides: Dict[str, Any] = {}

    def get(self, key: str, default: Any = None) -> Any:
        if key in self._overrides:
            return self._overrides[key]
        env_val = os.environ.get(f"TC_{key.upper()}")
        if env_val is not None:
            return env_val
        if hasattr(__import__(__name__), key.upper()):
            return getattr(__import__(__name__), key.upper())
        return default

    def set(self, key: str, value: Any) -> None:
        self._overrides[key] = value

    def snapshot(self) -> Dict[str, Any]:
        keys = ["DATA_DIR", "EXPORT_DIR", "PREPROC_MAX_ERRORS", "DEDUP_SIMILARITY_THRESHOLD",
                "BATCH_MAX_WORKERS", "VALIDATION_STRICT_MODE"]
        return {k: self.get(k) for k in keys}


config_manager = ConfigManager()


VALIDATION_RULES = {
    "poem_id_pattern": r"^P?\d+",
    "title_max_length": 200, "author_max_length": 50,
    "max_analysis_units_per_poem": 500, "max_lines_per_poem": 200,
}

CLEANING_PIPELINE_STAGES = [
    "encoding_detect", "content_clean", "json_parse",
    "structure_validate", "dedup_check", "quality_assess",
]

FILE_EXTENSIONS_MAP = {
    "json": "application/json", "txt": "text/plain",
    "csv": "text/csv", "tsv": "text/tab-separated-values",
}

ENCODING_ALIASES = {
    "utf8": "utf-8", "gb2312": "gbk", "cp936": "gbk",
    "unicode": "utf-16", "ansi": "gbk", "utf-8-bom": "utf-8-sig",
}

QUALITY_THRESHOLDS = {
    "excellent": 90, "good": 75, "acceptable": 60,
    "poor": 40, "critical": 20,
}
