# -*- coding: utf-8 -*-
"""
古典诗词音韵格律分析引擎 — 全局配置
"""
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ─────────────────────────────────────────────
# 路径配置
# ─────────────────────────────────────────────
POEM_JSON_DIR = os.environ.get(
    "PR_DATA_DIR",
    os.path.join(BASE_DIR, "..", "poem_json"),
)
EXPORT_DIR = os.environ.get(
    "PR_EXPORT_DIR",
    os.path.join(BASE_DIR, "..", "exports"),
)
LOG_DIR = os.environ.get(
    "PR_LOG_DIR",
    os.path.join(BASE_DIR, "..", "logs"),
)
REPORT_DIR = os.environ.get(
    "PR_REPORT_DIR",
    os.path.join(BASE_DIR, "..", "reports"),
)

# ─────────────────────────────────────────────
# 平水韵数据库配置
# ─────────────────────────────────────────────
PINGSHUI_STRICT_MODE = True          # 严格模式：仅标准韵书用字
PINGSHUI_ALLOW_NEIGHBORING = True    # 允许邻韵通押
PINGSHUI_DEFAULT_YUN = "unknown"     # 未知字的默认韵部

# ─────────────────────────────────────────────
# 平仄检测配置
# ─────────────────────────────────────────────
DEFAULT_TONE_CONFIDENCE = 1.0        # 单韵部字的默认置信度
MULTI_TONE_CONFIDENCE = 0.7          # 多音字的默认置信度
UNKNOWN_CHAR_CONFIDENCE = 0.0        # 未知字的置信度

# ─────────────────────────────────────────────
# 格律检查配置
# ─────────────────────────────────────────────
METER_STRICT_FLEXIBLE = False        # 严格模式：灵活位置也严格检查
METER_CHECK_GUPING = True            # 检测孤平
METER_CHECK_SANPINGDIAO = True       # 检测三平调
METER_CHECK_SANZEWEI = True          # 检测三仄尾
AUTO_DETECT_FORM = True              # 自动检测体裁

# ─────────────────────────────────────────────
# 韵脚分析配置
# ─────────────────────────────────────────────
RHYME_CHECK_FIRST_LINE = True        # 检查首句是否押韵
RHYME_ALLOW_NEIGHBORING = True       # 允许邻韵通押
RHYME_STRICT_MODE = False            # 严格模式：禁止邻韵通押

# ─────────────────────────────────────────────
# 对仗检测配置
# ─────────────────────────────────────────────
DUIZHANG_MIN_SCORE = 30              # 最低对仗判定分数
DUIZHANG_STRICT_SCORE = 70           # 工对分数阈值
DUIZHANG_LOOSE_SCORE = 50            # 宽对分数阈值

# ─────────────────────────────────────────────
# 音韵相似度权重
# ─────────────────────────────────────────────
SIM_YUNBU_WEIGHT = 0.40              # 韵部重叠度权重
SIM_TONE_WEIGHT = 0.25               # 声调分布权重
SIM_DENSITY_WEIGHT = 0.15            # 韵脚密度权重
SIM_POSITION_WEIGHT = 0.10           # 韵脚位置权重
SIM_METER_WEIGHT = 0.10              # 格律模板权重

# ─────────────────────────────────────────────
# 批处理配置
# ─────────────────────────────────────────────
BATCH_MAX_WORKERS = 4
BATCH_CHUNK_SIZE = 50
BATCH_TASK_TIMEOUT = 30              # 单任务超时秒数
BATCH_RETRY_COUNT = 3

# ─────────────────────────────────────────────
# 导出配置
# ─────────────────────────────────────────────
EXPORT_CSV_ENCODING = "utf-8-sig"
EXPORT_JSON_INDENT = 2
EXPORT_MAX_ROWS = 50000

# ─────────────────────────────────────────────
# 日志配置
# ─────────────────────────────────────────────
LOG_LEVEL = os.environ.get("PR_LOG_LEVEL", "INFO")
LOG_MAX_BYTES = 10 * 1024 * 1024
LOG_BACKUP_COUNT = 5
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"

# ─────────────────────────────────────────────
# 缓存
# ─────────────────────────────────────────────
CACHE_ENABLED = True
CACHE_DEFAULT_TTL = 600


class ConfigManager:
    """配置管理器 — 运行时覆盖与环境变量"""

    def __init__(self):
        self._overrides = {}

    def get(self, key, default=None):
        if key in self._overrides:
            return self._overrides[key]
        env_key = f"PR_{key}"
        if env_key in os.environ:
            return os.environ[env_key]
        val = globals().get(key)
        return val if val is not None else default

    def set(self, key, value):
        self._overrides[key] = value

    def reset(self, key):
        self._overrides.pop(key, None)

    def reset_all(self):
        self._overrides.clear()

    def snapshot(self):
        keys = [
            k for k in dir()
            if k.isupper() and not k.startswith("_")
        ]
        result = {}
        for k in sorted(keys):
            val = globals().get(k)
            if val is not None and not callable(val) and not isinstance(val, type):
                result[k] = val
        return result

    def list_all(self):
        return self.snapshot()


config_manager = ConfigManager()
