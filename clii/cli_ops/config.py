# -*- coding: utf-8 -*-
"""
配置管理模块
============
提供全局配置常量、环境变量读取、配置热加载、多环境配置切换。
支持开发、测试、生产三种环境配置。
"""

import os
import json
import threading
from dataclasses import dataclass, field
from typing import Dict, Any, Optional


# ============================================================================
# 基础路径配置
# ============================================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 数据目录
DATA_DIR = os.environ.get("TCO_DATA_DIR", os.path.join(BASE_DIR, "..", "poem_json"))
EXPORT_DIR = os.environ.get("TCO_EXPORT_DIR", os.path.join(BASE_DIR, "..", "exports"))
LOG_DIR = os.environ.get("TCO_LOG_DIR", os.path.join(BASE_DIR, "..", "logs"))
CACHE_DIR = os.environ.get("TCO_CACHE_DIR", os.path.join(BASE_DIR, "..", "cache"))
RAG_DB_DIR = os.environ.get("TCO_RAG_DIR", os.path.join(BASE_DIR, "..", "rag_db"))
REPORT_DIR = os.environ.get("TCO_REPORT_DIR", os.path.join(BASE_DIR, "..", "reports"))
BACKUP_DIR = os.environ.get("TCO_BACKUP_DIR", os.path.join(BASE_DIR, "..", "backups"))

VERSION = "1.0.0"

# ============================================================================
# 运行环境
# ============================================================================

class Environment:
    """运行环境枚举"""
    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"


# 当前环境，可通过环境变量 TCO_ENV 设置
CURRENT_ENV = os.environ.get("TCO_ENV", Environment.DEVELOPMENT)


# ============================================================================
# 日志配置
# ============================================================================

LOG_LEVEL = os.environ.get("TCO_LOG_LEVEL", "INFO")
LOG_MAX_BYTES = int(os.environ.get("TCO_LOG_MAX_BYTES", 10 * 1024 * 1024))  # 10MB
LOG_BACKUP_COUNT = int(os.environ.get("TCO_LOG_BACKUP_COUNT", 10))
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


# ============================================================================
# 缓存配置
# ============================================================================

CACHE_ENABLED = os.environ.get("TCO_CACHE_ENABLED", "true").lower() == "true"
CACHE_DEFAULT_TTL = int(os.environ.get("TCO_CACHE_TTL", 600))  # 10分钟
CACHE_MAX_MEMORY_ITEMS = int(os.environ.get("TCO_CACHE_MAX_MEMORY", 5000))
CACHE_AUTO_CLEANUP_INTERVAL = int(os.environ.get("TCO_CACHE_CLEANUP_INTERVAL", 3600))
CACHE_CLEANUP_STRATEGY = os.environ.get("TCO_CACHE_STRATEGY", "lru")  # lru/lfu/ttl


# ============================================================================
# 导出配置
# ============================================================================

EXPORT_CSV_ENCODING = "utf-8-sig"
EXPORT_CSV_DELIMITER = ","
EXPORT_JSON_INDENT = 2
EXPORT_XML_ROOT_TAG = "tang_poetry_data"
EXPORT_MAX_ROWS = int(os.environ.get("TCO_EXPORT_MAX_ROWS", 50000))
EXPORT_TIMESTAMP_FORMAT = "%Y%m%d_%H%M%S"


# ============================================================================
# 监控配置
# ============================================================================

MONITOR_COLLECTION_INTERVAL = int(os.environ.get("TCO_MONITOR_INTERVAL", 60))  # 秒
MONITOR_HISTORY_MAX_ITEMS = int(os.environ.get("TCO_MONITOR_HISTORY", 200))
MONITOR_DISK_THRESHOLD_PCT = float(os.environ.get("TCO_MONITOR_DISK_THRESHOLD", 90.0))
MONITOR_MEMORY_THRESHOLD_PCT = float(os.environ.get("TCO_MONITOR_MEM_THRESHOLD", 90.0))
MONITOR_CPU_THRESHOLD_PCT = float(os.environ.get("TCO_MONITOR_CPU_THRESHOLD", 85.0))
MONITOR_NETWORK_INTERFACE = os.environ.get("TCO_MONITOR_NET_IFACE", "eth0")


# ============================================================================
# 数据处理配置
# ============================================================================

SCANNER_FILE_EXTENSIONS = [".json", ".txt", ".csv", ".tsv"]
SCANNER_MAX_FILE_SIZE_MB = int(os.environ.get("TCO_SCANNER_MAX_SIZE_MB", 500))
SCANNER_RECURSIVE = os.environ.get("TCO_SCANNER_RECURSIVE", "true").lower() == "true"
SCANNER_SKIP_HIDDEN = True

PREPROCESSOR_MAX_ERRORS = int(os.environ.get("TCO_PREPROC_MAX_ERRORS", 100))
PREPROCESSOR_AUTO_FIX = os.environ.get("TCO_PREPROC_AUTO_FIX", "false").lower() == "true"
PREPROCESSOR_VALIDATE_SCHEMA = True

BATCH_PROCESSOR_MAX_WORKERS = int(os.environ.get("TCO_BATCH_WORKERS", 4))
BATCH_PROCESSOR_CHUNK_SIZE = int(os.environ.get("TCO_BATCH_CHUNK", 100))
BATCH_PROCESSOR_TIMEOUT = int(os.environ.get("TCO_BATCH_TIMEOUT", 3600))


# ============================================================================
# 健康检查配置
# ============================================================================

HEALTH_CHECK_TIMEOUT = int(os.environ.get("TCO_HEALTH_TIMEOUT", 30))
HEALTH_CHECK_RETRIES = int(os.environ.get("TCO_HEALTH_RETRIES", 3))
HEALTH_CHECK_DEPENDENCIES = ["data_dir", "export_dir", "log_dir", "cache_dir"]


# ============================================================================
# 分类名称映射（从唐诗意象系统继承）
# ============================================================================

CATEGORY_NAME_MAP: Dict[str, str] = {
    "1-1": "天文意象",
    "1-2": "地理意象",
    "1-3": "植物意象",
    "1-4": "动物意象",
    "2-1": "生产生活意象",
    "2-2": "军事战争意象",
    "2-3": "制度观念意象",
    "3-1": "人造器物意象",
    "3-2": "人类自身意象",
    "3-3": "人物角色意象",
    "3-4": "文化意象",
}

CATEGORY_MAJOR_MAP: Dict[str, str] = {
    "1": "自然意象",
    "2": "社会意象",
    "3": "人文意象",
}

# 情感类别映射
EMOTION_CATEGORIES = [
    "喜悦", "悲伤", "思乡", "忧愁", "豪迈",
    "感慨", "闲适", "愤怒", "恐惧", "爱慕",
    "孤独", "豁达", "未知",
]

EMOTION_POLARITIES = ["+", "-", "0"]


# ============================================================================
# 配置管理类
# ============================================================================

@dataclass
class ConfigSnapshot:
    """配置快照"""
    values: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = ""
    created_by: str = ""


class ConfigManager:
    """
    配置管理器

    功能特性：
      - 多环境配置切换（开发/测试/生产）
      - 环境变量覆盖默认配置
      - JSON 文件持久化
      - 配置变更历史追踪
      - 线程安全读写
      - 配置快照备份与回滚
    """

    def __init__(self):
        self._lock = threading.RLock()
        self._overrides: Dict[str, Any] = {}
        self._history: list = []
        self._config_file = os.path.join(BASE_DIR, "..", "cli_config.json")

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值，优先级: 运行时覆盖 > 环境变量 > 模块常量 > 默认值"""
        with self._lock:
            if key in self._overrides:
                return self._overrides[key]
        env_val = os.environ.get(f"TCO_{key.upper()}")
        if env_val is not None:
            return env_val
        import sys
        module = sys.modules[__name__]
        if hasattr(module, key.upper()):
            return getattr(module, key.upper())
        return default

    def set(self, key: str, value: Any) -> None:
        """运行时覆盖配置值"""
        with self._lock:
            old_value = self._overrides.get(key, self.get(key))
            self._overrides[key] = value
            self._history.append({
                "action": "set",
                "key": key,
                "old_value": str(old_value),
                "new_value": str(value),
            })

    def reset(self, key: str) -> None:
        """重置某个配置项为默认值"""
        with self._lock:
            if key in self._overrides:
                old = self._overrides.pop(key)
                self._history.append({
                    "action": "reset",
                    "key": key,
                    "old_value": str(old),
                })

    def reset_all(self) -> int:
        """重置全部覆盖"""
        with self._lock:
            count = len(self._overrides)
            self._overrides.clear()
            self._history.append({"action": "reset_all", "count": count})
            return count

    def snapshot(self) -> ConfigSnapshot:
        """生成当前配置快照"""
        with self._lock:
            all_keys = [
                "CURRENT_ENV", "LOG_LEVEL", "CACHE_ENABLED",
                "CACHE_DEFAULT_TTL", "EXPORT_CSV_ENCODING",
                "MONITOR_COLLECTION_INTERVAL", "BATCH_PROCESSOR_MAX_WORKERS",
            ]
            values = {k: self.get(k) for k in all_keys}
            values.update(self._overrides)
            import datetime
            return ConfigSnapshot(
                values=values,
                timestamp=datetime.datetime.now().isoformat(),
                created_by="ConfigManager.snapshot()",
            )

    def save_to_file(self) -> str:
        """持久化配置到 JSON 文件"""
        snapshot = self.snapshot()
        with open(self._config_file, "w", encoding="utf-8") as f:
            json.dump(snapshot.values, f, ensure_ascii=False, indent=2)
        return self._config_file

    def load_from_file(self) -> bool:
        """从 JSON 文件加载配置"""
        if not os.path.exists(self._config_file):
            return False
        with open(self._config_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        with self._lock:
            self._overrides.update(data)
        return True

    def get_history(self, limit: int = 20) -> list:
        """获取配置变更历史"""
        with self._lock:
            return self._history[-limit:]

    def list_all(self) -> Dict[str, Any]:
        """列出所有可配置项及其当前值"""
        keys = [
            "CURRENT_ENV", "DATA_DIR", "EXPORT_DIR", "LOG_DIR", "CACHE_DIR",
            "LOG_LEVEL", "LOG_MAX_BYTES", "LOG_BACKUP_COUNT",
            "CACHE_ENABLED", "CACHE_DEFAULT_TTL", "CACHE_MAX_MEMORY_ITEMS",
            "CACHE_CLEANUP_STRATEGY", "EXPORT_CSV_ENCODING", "EXPORT_MAX_ROWS",
            "MONITOR_COLLECTION_INTERVAL", "MONITOR_DISK_THRESHOLD_PCT",
            "MONITOR_MEMORY_THRESHOLD_PCT", "MONITOR_CPU_THRESHOLD_PCT",
            "SCANNER_FILE_EXTENSIONS", "SCANNER_MAX_FILE_SIZE_MB",
            "BATCH_PROCESSOR_MAX_WORKERS", "BATCH_PROCESSOR_CHUNK_SIZE",
            "HEALTH_CHECK_TIMEOUT", "HEALTH_CHECK_RETRIES",
            "PREPROCESSOR_MAX_ERRORS", "PREPROCESSOR_AUTO_FIX",
        ]
        return {k: self.get(k) for k in keys}


# 全局配置管理器实例
config_manager = ConfigManager()
