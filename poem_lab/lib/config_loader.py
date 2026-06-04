# -*- coding: utf-8 -*-
"""
配置热加载 — 单例模式，从 config.py 和 prompts/ 目录读取
"""
import os, json, threading

_locked_config = {}
_lock = threading.Lock()

DEFAULTS = {
    "API_URL": "http://127.0.0.1:44787/v1/chat/completions",
    "MODEL_NAME": "",
    "TIMEOUT": None,
    "MAX_POEMS_PER_BATCH": 5,
    "BATCH_CHAR_LIMIT": 200,
    "TEST_RUN_COUNT": 5,
    "BATCH_WORKERS": 5,
    "CHECKPOINT_EVERY": 5,
    "PROMPTS_DIR": "",
    "TEMPLATES_DIR": "",
    "EXPORTS_DIR": "",
}


def _init():
    global _locked_config
    if _locked_config:
        return
    with _lock:
        if _locked_config:
            return
        try:
            import config as cfg
            for key in DEFAULTS:
                val = getattr(cfg, key, DEFAULTS[key])
                _locked_config[key] = val
        except ImportError:
            _locked_config = dict(DEFAULTS)


def get(key: str, default=None):
    _init()
    return _locked_config.get(key, default)


def reload():
    global _locked_config
    _locked_config = {}
    _init()


def load_prompt(name: str) -> str | None:
    """从 prompts/ 目录加载提示词文件"""
    prompts_dir = get("PROMPTS_DIR")
    if not prompts_dir:
        return None
    path = os.path.join(prompts_dir, f"{name}.txt")
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return f.read()
