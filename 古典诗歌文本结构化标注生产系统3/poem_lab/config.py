# -*- coding: utf-8 -*-
"""古典诗歌文本结构化标注生产系统 — 全局配置"""
import os
import secrets

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# LLM API
API_URL = os.environ.get("POEMLAB_API_URL", "http://127.0.0.1:44787/v1/chat/completions")
MODEL_NAME = os.environ.get("POEMLAB_MODEL", "")
TIMEOUT = None  # None = 不限

# Flask
SECRET_KEY = os.environ.get("POEMLAB_SECRET", secrets.token_hex(24))
FLASK_HOST = "0.0.0.0"
FLASK_PORT = 5100  # 不跟 System A (5000) 冲突

# Paths
PROMPTS_DIR = os.path.join(BASE_DIR, "prompts")
TEMPLATES_DIR = os.path.join(BASE_DIR, "user_templates")
EXPORTS_DIR = os.path.join(BASE_DIR, "exports")

# Batch limits
MAX_POEMS_PER_BATCH = 5
BATCH_CHAR_LIMIT = 200
TEST_RUN_COUNT = 5  # 试跑的诗数
BATCH_WORKERS = 5  # 并行worker数
CHECKPOINT_EVERY = 5  # 每N首落盘一次
