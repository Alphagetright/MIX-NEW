# -*- coding: utf-8 -*-
"""唐诗意象智能分析系统 配置"""

import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# API
LLM_API_BASE = "http://127.0.0.1:44787"
EMBED_API_URL = f"{LLM_API_BASE}/v1/embeddings"
CHAT_API_URL = f"{LLM_API_BASE}/v1/chat/completions"
EMBED_MODEL = "text-embedding-qwen3-embedding-4b"
CHAT_MODEL = "qwen3.6-35b-a3b"

# 路径
POEMS_JSON_DIR = os.path.join(BASE_DIR, "poem_json")
POEM_JSON_DIR = os.path.join(BASE_DIR, "poem_json")
RAG_DB_DIR = os.path.join(BASE_DIR, "rag_db")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
EXPORT_DIR = os.path.join(BASE_DIR, "exports")
LOG_DIR = os.path.join(BASE_DIR, "logs")
CACHE_DIR = os.path.join(BASE_DIR, "cache")
TESTS_DIR = os.path.join(BASE_DIR, "tests")

# RAG
TOP_K = 5
RAG_COLLECTION_NAME = "poems"
RAG_SPACE_FUNC = "cosine"

# Flask
FLASK_HOST = "0.0.0.0"
FLASK_PORT = 5000
FLASK_DEBUG = True
FLASK_THREADED = True
SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", os.urandom(24).hex())

# 分页
PAGE_SIZE = 25
RENDER_LIMIT = 5000

# 认证
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", os.urandom(12).hex())
SESSION_TIMEOUT = 3600

# 文件处理
MAX_BYTES_PER_CHUNK = 1024
EMBEDDING_RETRIES = 3
EMBEDDING_TIMEOUT = 30
CHAT_TIMEOUT = 300

# 意象分类映射
CATEGORY_NAME_MAP = {
    "1-1": "自然意象-天文意象",
    "1-2": "自然意象-地理意象",
    "1-3": "自然意象-植物意象",
    "1-4": "自然意象-动物意象",
    "2-1": "社会意象-生产生活意象",
    "2-2": "社会意象-军事战争意象",
    "2-3": "社会意象-制度观念意象",
    "3-1": "人文意象-人造器物意象",
    "3-2": "人文意象-人类自身意象",
    "3-3": "人文意象-人物角色意象",
    "3-4": "人文意象-文化意象",
}

CATEGORY_MAJOR_MAP = {
    "1": "自然意象",
    "2": "社会意象",
    "3": "人文意象",
}

# 已知诗人
KNOWN_AUTHORS = [
    "杜甫", "李白", "王维", "白居易", "苏轼", "李商隐", "杜牧",
    "王昌龄", "孟浩然", "柳宗元", "韩愈", "欧阳修", "辛弃疾",
    "李清照", "陶渊明", "张九龄", "司空曙", "刘长卿", "韦应物",
    "岑参", "高适", "王之涣", "元稹", "温庭筠", "晏殊",
]

# 日志
LOG_LEVEL = "INFO"
LOG_MAX_BYTES = 10 * 1024 * 1024
LOG_BACKUP_COUNT = 5
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"

# 缓存
CACHE_DEFAULT_TTL = 300
CACHE_ENABLED = True

# 导出
EXPORT_CSV_ENCODING = "utf-8-sig"
