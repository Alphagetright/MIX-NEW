# -*- coding: utf-8 -*-
"""用户认证 — 注册/登录/会话管理/鉴权装饰器"""
import hashlib, os, functools
from flask import session, redirect, url_for, request, jsonify

from . import persistence

DEFAULT_ADMIN = "admin"
DEFAULT_ADMIN_PASS = "poemlab2026"


def hash_password(password: str, salt: str = "") -> tuple:
    """返回 (hash, salt)"""
    if not salt:
        salt = os.urandom(16).hex()
    h = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000)
    return h.hex(), salt


def verify_password(password: str, stored_hash: str, salt: str) -> bool:
    h, _ = hash_password(password, salt)
    return h == stored_hash


def init_default_admin():
    """创建默认管理员账户（如果不存在）"""
    if not persistence.get_user(DEFAULT_ADMIN):
        h, salt = hash_password(DEFAULT_ADMIN_PASS)
        persistence.create_user(DEFAULT_ADMIN, f"{h}:{salt}", "admin")


def register_user(username: str, password: str, role: str = "annotator") -> dict:
    """注册新用户，返回结果"""
    username = username.strip().lower()
    if not username or len(username) < 2:
        return {"ok": False, "error": "用户名至少2个字符"}
    if not password or len(password) < 4:
        return {"ok": False, "error": "密码至少4个字符"}
    if persistence.get_user(username):
        return {"ok": False, "error": "用户名已存在"}

    h, salt = hash_password(password)
    uid = persistence.create_user(username, f"{h}:{salt}", role)
    if uid is None:
        return {"ok": False, "error": "注册失败，请重试"}
    return {"ok": True, "user_id": uid, "username": username, "role": role}


def login_user(username: str, password: str) -> dict:
    """验证登录，设置 session"""
    username = username.strip().lower()
    user = persistence.get_user(username)
    if not user:
        return {"ok": False, "error": "用户名或密码错误"}

    parts = user["password_hash"].split(":", 1)
    if len(parts) != 2:
        return {"ok": False, "error": "账户数据异常，请联系管理员"}

    stored_hash, salt = parts
    if not verify_password(password, stored_hash, salt):
        return {"ok": False, "error": "用户名或密码错误"}

    session["_user_id"] = user["id"]
    session["_username"] = user["username"]
    session["_user_role"] = user["role"]
    return {"ok": True, "username": user["username"], "role": user["role"]}


def logout_user():
    session.pop("_user_id", None)
    session.pop("_username", None)
    session.pop("_user_role", None)


def current_user() -> dict | None:
    uid = session.get("_user_id")
    if not uid:
        return None
    return {
        "id": uid,
        "username": session.get("_username", ""),
        "role": session.get("_user_role", "annotator")
    }


def is_logged_in() -> bool:
    return session.get("_user_id") is not None


def is_admin() -> bool:
    return session.get("_user_role") == "admin"


def login_required(f):
    """装饰器：API 路由需要登录"""
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        if not is_logged_in():
            return jsonify({"ok": False, "error": "请先登录", "need_login": True}), 401
        return f(*args, **kwargs)
    return wrapper


def admin_required(f):
    """装饰器：API 路由需要管理员权限"""
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        if not is_logged_in():
            return jsonify({"ok": False, "error": "请先登录", "need_login": True}), 401
        if not is_admin():
            return jsonify({"ok": False, "error": "需要管理员权限"}), 403
        return f(*args, **kwargs)
    return wrapper


def page_login_required(f):
    """装饰器：页面路由需要登录，未登录重定向到登录页"""
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        if not is_logged_in():
            return redirect(url_for("login_page"))
        return f(*args, **kwargs)
    return wrapper
