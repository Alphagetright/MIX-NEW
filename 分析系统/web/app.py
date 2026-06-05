# -*- coding: utf-8 -*-
"""Web应用入口 —— 基于Flask的轻量级前端"""

import hashlib
import json
import os
import time

try:
    from flask import (
        Flask, render_template, request, redirect, session,
        jsonify, url_for, flash, send_file
    )
except ImportError:
    Flask = None


app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET", "pipeline-dev-secret-key-2024")

# 模拟用户数据库
_users_db = {}
_pipeline_history = []
_annotations_store = []


# ─── 工具函数 ───

def _hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def _require_login():
    return "user_id" not in session


# ─── 登录注册 ───

@app.route("/")
def index():
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        user = _users_db.get(username)
        if user and user["password"] == _hash_password(password):
            session["user_id"] = username
            return redirect(url_for("home"))
        return render_template("login.html", error="用户名或密码错误")
    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")
        if not username or not password:
            return render_template("register.html", error="用户名和密码不能为空")
        if password != confirm:
            return render_template("register.html", error="两次密码不一致")
        if username in _users_db:
            return render_template("register.html", error="用户名已存在")
        _users_db[username] = {
            "password": _hash_password(password),
            "created_at": time.time(),
        }
        session["user_id"] = username
        return redirect(url_for("home"))
    return render_template("register.html")


@app.route("/logout")
def logout():
    session.pop("user_id", None)
    return redirect(url_for("login"))


# ─── 主页 ───

@app.route("/home")
def home():
    if _require_login():
        return redirect(url_for("login"))
    return render_template("home.html", username=session["user_id"])


@app.route("/dashboard")
def dashboard():
    if _require_login():
        return redirect(url_for("login"))
    stats = {
        "total_annotations": len(_annotations_store),
        "total_pipelines": len(_pipeline_history),
        "recent_runs": _pipeline_history[-5:] if _pipeline_history else [],
    }
    return render_template("dashboard.html", username=session["user_id"], stats=stats)


# ─── 一二级接口：数据管线管理 ───

@app.route("/api/v1/pipeline/run", methods=["POST"])
def api_pipeline_run():
    if _require_login():
        return jsonify({"error": "未登录"}), 401
    data = request.get_json() or {}
    task_id = f"task_{int(time.time())}_{hashlib.md5(str(data).encode()).hexdigest()[:8]}"
    _pipeline_history.append({
        "task_id": task_id,
        "status": "running",
        "created_at": time.time(),
        "params": data,
    })
    return jsonify({"task_id": task_id, "status": "running"})


@app.route("/api/v1/pipeline/status/<task_id>")
def api_pipeline_status(task_id):
    if _require_login():
        return jsonify({"error": "未登录"}), 401
    for task in _pipeline_history:
        if task["task_id"] == task_id:
            return jsonify(task)
    return jsonify({"error": "任务不存在"}), 404


@app.route("/api/v1/pipeline/list")
def api_pipeline_list():
    if _require_login():
        return jsonify({"error": "未登录"}), 401
    return jsonify({"pipelines": _pipeline_history[-20:]})


@app.route("/api/v1/pipeline/stats")
def api_pipeline_stats():
    if _require_login():
        return jsonify({"error": "未登录"}), 401
    total = len(_pipeline_history)
    running = sum(1 for t in _pipeline_history if t["status"] == "running")
    completed = sum(1 for t in _pipeline_history if t["status"] == "completed")
    return jsonify({
        "total": total,
        "running": running,
        "completed": completed,
    })


# ─── 二二级接口：标注数据管理 ───

@app.route("/api/v1/annotations/submit", methods=["POST"])
def api_annotations_submit():
    if _require_login():
        return jsonify({"error": "未登录"}), 401
    data = request.get_json() or {}
    record = {
        "id": f"ann_{int(time.time())}_{len(_annotations_store)}",
        "data": data,
        "created_at": time.time(),
        "user": session["user_id"],
    }
    _annotations_store.append(record)
    return jsonify({"id": record["id"], "status": "submitted"})


@app.route("/api/v1/annotations/list")
def api_annotations_list():
    if _require_login():
        return jsonify({"error": "未登录"}), 401
    limit = int(request.args.get("limit", 50))
    return jsonify({"annotations": _annotations_store[-limit:]})


@app.route("/api/v1/annotations/<ann_id>")
def api_annotations_get(ann_id):
    if _require_login():
        return jsonify({"error": "未登录"}), 401
    for ann in _annotations_store:
        if ann["id"] == ann_id:
            return jsonify(ann)
    return jsonify({"error": "不存在"}), 404


@app.route("/api/v1/annotations/export/<fmt>")
def api_annotations_export(fmt):
    if _require_login():
        return jsonify({"error": "未登录"}), 401
    if fmt == "json":
        return jsonify({"annotations": _annotations_store})
    return jsonify({"error": f"不支持的格式: {fmt}"}), 400


# ─── 系统信息接口 ───

@app.route("/api/v1/system/info")
def api_system_info():
    if _require_login():
        return jsonify({"error": "未登录"}), 401
    return jsonify({
        "version": "1.0.0",
        "name": "古典诗歌文本结构化标注生产系统",
        "uptime": time.time(),
        "users": len(_users_db),
        "annotations": len(_annotations_store),
        "pipelines": len(_pipeline_history),
    })


@app.route("/api/v1/system/health")
def api_system_health():
    return jsonify({"status": "ok", "timestamp": time.time()})


# ─── 标注结果展示页面 ───

_DEMO_POEM = {
    "verses": [
        {"text": "床前明月光", "pos": 1},
        {"text": "疑是地上霜", "pos": 2},
        {"text": "举头望明月", "pos": 3},
        {"text": "低头思故乡", "pos": 4},
    ]
}

_DEMO_ANNOTATIONS = {
    "imagery": [
        {"word": "明月", "category": "天文", "intensity": 0.92},
        {"word": "霜", "category": "自然", "intensity": 0.85},
        {"word": "月光", "category": "天文", "intensity": 0.78},
        {"word": "故乡", "category": "地理", "intensity": 0.90},
    ],
    "emotion": {"sentiment": "nostalgia", "intensity": 0.88},
    "structure": {"pattern": "五言绝句", "rhyme": "AABA"},
}

_DEMO_QUALITY = {"completeness": 1.0, "confidence": 0.94}

_DEMO_JSON = '''{\n  "pipeline_run": {\n    "id": "run_20260520_143022",\n    "status": "success",\n    "duration_ms": 3420\n  },\n  "poem": {\n    "title": "静夜思",\n    "author": "李白",\n    "verses": [\n      {"text": "床前明月光", "pos": 1},\n      {"text": "疑是地上霜", "pos": 2}\n    ]\n  },\n  "annotations": {\n    "imagery": [\n      {"word": "明月", "intensity": 0.92},\n      {"word": "霜", "intensity": 0.85}\n    ],\n    "emotion": {"sentiment": "nostalgia", "intensity": 0.88},\n    "structure": {"pattern": "五言绝句", "rhyme": "AABA"}\n  },\n  "quality": {\n    "completeness": 1.0,\n    "confidence": 0.94\n  }\n}'''


@app.route("/annotations")
def annotations():
    if _require_login():
        return redirect(url_for("login"))
    return render_template("annotations.html",
                           poem=_DEMO_POEM,
                           annotations=_DEMO_ANNOTATIONS,
                           quality=_DEMO_QUALITY,
                           json_data=_DEMO_JSON)


# ─── 启动入口 ───

def create_app():
    return app


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"启动Web服务: http://127.0.0.1:{port}")
    app.run(host="127.0.0.1", port=port, debug=True)
