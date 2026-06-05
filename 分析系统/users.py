# -*- coding: utf-8 -*-
"""
用户管理 — 基于 JSON 文件的简易用户存储
"""
import json
import os
import hashlib
import threading

from config import BASE_DIR
from logger import get_logger

logger = get_logger("users")

USERS_FILE = os.path.join(BASE_DIR, "users.json")
_lock = threading.Lock()


def _hash(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def _load():
    if not os.path.exists(USERS_FILE):
        return {}
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def _save(data: dict):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def init_default_admin():
    """确保至少有一个管理员账号"""
    with _lock:
        users = _load()
        if "admin" not in users:
            import secrets
            default_pw = secrets.token_hex(8)
            users["admin"] = {
                "password": _hash(default_pw),
                "created_at": "",
            }
            _save(users)
            logger.info("已创建默认管理员账号")


def authenticate(username: str, password: str) -> bool:
    """验证用户名密码"""
    with _lock:
        users = _load()
        user = users.get(username)
        if not user:
            return False
        return user.get("password") == _hash(password)


def register(username: str, password: str) -> tuple[bool, str]:
    """注册新用户，返回 (成功, 错误信息)"""
    username = username.strip()
    password = password.strip()

    if not username or len(username) < 2:
        return False, "用户名至少需要 2 个字符"
    if len(username) > 20:
        return False, "用户名不能超过 20 个字符"
    if not password or len(password) < 4:
        return False, "密码至少需要 4 个字符"
    if not username.isalnum():
        return False, "用户名只能包含字母和数字"

    with _lock:
        users = _load()
        if username in users:
            return False, "用户名已存在"
        import time
        users[username] = {
            "password": _hash(password),
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        _save(users)
        logger.info(f"新用户注册: {username}")
    return True, "注册成功"


def user_exists(username: str) -> bool:
    with _lock:
        return username in _load()
