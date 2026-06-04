# -*- coding: utf-8 -*-
"""
CLI运维管理系统 Web前端
========================
设计初衷：CLI命令行可直接被AI AGENT操控，
通过远程hook实现AI提效，无需人工逐条输入命令。
Web界面提供人类可读的运维看板和API接口，
AI AGENT可通过API直接调用CLI底层能力。

核心优势：
  - AGENT可直接调用CLI命令（通过API代理）
  - 远程hook机制：AI通过HTTP触发运维任务
  - 人类+AI双模式：Web给人看，API给AI用
"""

import os
import sys
import json
import time
import hashlib

_package_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _package_dir not in sys.path:
    sys.path.insert(0, _package_dir)

try:
    from flask import (
        Flask, render_template, request, redirect, session,
        jsonify, url_for
    )
except ImportError:
    Flask = None

from ..config import (
    DATA_DIR, EXPORT_DIR, LOG_DIR, CACHE_DIR, REPORT_DIR,
    VERSION
)
from ..health_checker import HealthChecker
from ..cache_manager import MemoryCache
from ..tools import registry as tool_registry
from ..agent_loop import AgentLoop, AgentResult

app = Flask(__name__)
app.secret_key = os.urandom(24).hex()

_users_db = {}
_operation_log = []


def _hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def _require_login():
    return "user_id" not in session


def _get_cli_ops():
    hc = HealthChecker()
    health_result = hc.check_all()
    return {
        "version": VERSION,
        "health": health_result,
        "directories": {
            "data_dir": DATA_DIR,
            "export_dir": EXPORT_DIR,
            "log_dir": LOG_DIR,
            "cache_dir": CACHE_DIR,
            "report_dir": REPORT_DIR,
        },
    }


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
            return redirect(url_for("dashboard"))
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
        _operation_log.append({
            "time": time.time(), "user": username,
            "action": "register", "status": "success"
        })
        return redirect(url_for("dashboard"))
    return render_template("register.html")


@app.route("/logout")
def logout():
    session.pop("user_id", None)
    return redirect(url_for("login"))


# ─── 主页与控制台 ───

@app.route("/dashboard")
def dashboard():
    if _require_login():
        return redirect(url_for("login"))
    ops = _get_cli_ops()
    return render_template("dashboard.html", username=session["user_id"], ops=ops)


@app.route("/home")
def home():
    if _require_login():
        return redirect(url_for("login"))
    return render_template("home.html", username=session["user_id"])


# ─── 一级接口：CLI命令代理（AGENT可直接调用） ───

@app.route("/api/v1/cli/run", methods=["POST"])
def api_cli_run():
    """
    AI AGENT 远程执行 CLI 命令（真实执行）

    请求体:
        {"command": "status", "args": {}}
        {"command": "scan", "args": {"dir": "./poem_json"}}
        {"command": "export", "args": {"format": "csv"}}

    返回:
        {"ok": true, "tool": "status", "output": "...", "duration_ms": 42.1}
    """
    if _require_login():
        return jsonify({"error": "未认证"}), 401

    data = request.get_json() or {}
    command = data.get("command", "")
    args = data.get("args", {})

    if not command:
        return jsonify({"ok": False, "error": "缺少 command 参数"}), 400

    # 如果传了数组格式的 args，转为 dict（兼容旧版 API）
    if isinstance(args, list):
        args = {}

    task_id = f"task_{int(time.time())}_{hashlib.md5(str(data).encode()).hexdigest()[:8]}"

    # 真实执行
    result = tool_registry.execute(command, args)

    _operation_log.append({
        "time": time.time(), "task_id": task_id,
        "command": command, "args": args,
        "status": "success" if result.ok else "failed",
    })

    return jsonify({
        "task_id": task_id,
        "tool": command,
        "ok": result.ok,
        "output": result.output[:5000],
        "error": result.error,
        "duration_ms": result.duration_ms,
    })


@app.route("/api/v1/cli/health")
def api_cli_health():
    """AGENT可调用的健康检查接口"""
    if _require_login():
        return jsonify({"error": "未认证"}), 401
    hc = HealthChecker()
    result = hc.check_all()
    return jsonify({
        "status": "ok" if result.all_passed else "degraded",
        "checks": result.to_dict() if hasattr(result, 'to_dict') else str(result),
        "timestamp": time.time(),
    })


@app.route("/api/v1/cli/status")
def api_cli_status():
    """AGENT可调用的系统状态接口"""
    if _require_login():
        return jsonify({"error": "未认证"}), 401
    ops = _get_cli_ops()
    return jsonify({
        "version": ops["version"],
        "directories": {k: str(v) for k, v in ops["directories"].items()},
        "health_status": "ok",
        "timestamp": time.time(),
    })


@app.route("/api/v1/cli/history")
def api_cli_history():
    """操作历史查询接口"""
    if _require_login():
        return jsonify({"error": "未认证"}), 401
    limit = int(request.args.get("limit", 50))
    return jsonify({
        "total": len(_operation_log),
        "operations": _operation_log[-limit:],
    })


@app.route("/api/v1/cli/tools")
def api_cli_tools():
    """
    工具发现接口 — 返回所有可被 AI Agent 调用的工具

    返回: OpenAI function-calling 兼容格式的工具列表
    """
    if _require_login():
        return jsonify({"error": "未认证"}), 401

    category = request.args.get("category", "")
    if category:
        tools_by_cat = tool_registry.list_by_category()
        tools = tools_by_cat.get(category, [])
    else:
        tools = tool_registry.list_all()

    return jsonify({
        "total": len(tools),
        "tools": [
            {
                "name": t.name,
                "description": t.description,
                "category": t.category,
                "parameters": t.parameters,
            }
            for t in tools
        ],
        "categories": list(tool_registry.list_by_category().keys()),
    })


# ─── 二级接口：数据管理 ───

@app.route("/api/v1/data/scan", methods=["POST"])
def api_data_scan():
    """数据扫描接口"""
    if _require_login():
        return jsonify({"error": "未认证"}), 401
    data = request.get_json() or {}
    target_dir = data.get("dir", str(DATA_DIR))
    return jsonify({
        "status": "completed",
        "target": target_dir,
        "message": f"扫描完成（模拟）",
        "timestamp": time.time(),
    })


@app.route("/api/v1/data/export", methods=["POST"])
def api_data_export():
    """数据导出接口"""
    if _require_login():
        return jsonify({"error": "未认证"}), 401
    data = request.get_json() or {}
    fmt = data.get("format", "json")
    return jsonify({
        "status": "completed",
        "format": fmt,
        "output": str(EXPORT_DIR),
        "timestamp": time.time(),
    })


@app.route("/api/v1/data/info")
def api_data_info():
    """数据目录信息接口"""
    if _require_login():
        return jsonify({"error": "未认证"}), 401
    info = {}
    if os.path.isdir(DATA_DIR):
        files = os.listdir(DATA_DIR)
        info = {
            "path": str(DATA_DIR),
            "file_count": len(files),
            "exists": True,
        }
    else:
        info = {"path": str(DATA_DIR), "exists": False}
    return jsonify(info)


@app.route("/api/v1/system/info")
def api_system_info():
    """系统信息接口"""
    if _require_login():
        return jsonify({"error": "未认证"}), 401
    return jsonify({
        "name": "唐诗意象数据运维管理系统",
        "version": VERSION,
        "type": "CLI运维工具（AGENT可操控）",
        "design_philosophy": "CLI设计使AGENT可直接操控，通过远程hook实现AI提效",
        "users": len(_users_db),
        "timestamp": time.time(),
    })


@app.route("/api/v1/system/health")
def api_system_health():
    """公开健康检查（免认证）"""
    return jsonify({"status": "ok", "server_time": time.time()})


# ─── 三级接口：Agent 自主执行 ───

@app.route("/api/v1/agent/run", methods=["POST"])
def api_agent_run():
    """
    Agent 自主执行接口 — 输入自然语言，自动完成多步操作

    请求体:
        {
            "goal": "检查系统状态，扫描数据目录，导出 CSV",
            "max_steps": 10
        }

    返回:
        {
            "success": true,
            "goal": "...",
            "steps": [{"step": 1, "tool": "status", "ok": true, ...}, ...],
            "final_summary": "...",
            "total_duration_ms": 1234.5
        }
    """
    if _require_login():
        return jsonify({"error": "未认证"}), 401

    data = request.get_json() or {}
    goal = data.get("goal", "")
    max_steps = int(data.get("max_steps", 10))

    if not goal:
        return jsonify({"error": "缺少 goal 参数"}), 400

    # 限制 max_steps 范围
    max_steps = min(max(max_steps, 1), 20)

    loop = AgentLoop(max_steps=max_steps, verbose=False)
    result = loop.run(goal)

    _operation_log.append({
        "time": time.time(),
        "action": "agent_run",
        "goal": goal,
        "success": result.success,
        "steps": result.step_count,
    })

    return jsonify(result.to_dict())


@app.route("/api/v1/agent/tools")
def api_agent_tools():
    """Agent 可用工具列表（免认证，供外部 Agent 发现）"""
    return jsonify({
        "agent": "唐诗意象数据运维管理系统 — AI Agent",
        "tools_llm": tool_registry.list_for_llm(),
        "tools_simple": [
            {"name": t.name, "description": t.description, "category": t.category}
            for t in tool_registry.list_all()
        ],
    })


# ─── 启动 ───

def create_app():
    return app


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    print(f"CLI运维Web服务: http://127.0.0.1:{port}")
    print(f"API文档: http://127.0.0.1:{port}/home")
    print(f"工具发现: http://127.0.0.1:{port}/api/v1/agent/tools")
    print(f"Agent执行: POST http://127.0.0.1:{port}/api/v1/agent/run")
    print("设计初衷: CLI可供AGENT直接操控，现已支持真实工具执行 + 自主Agent Loop")
    app.run(host="127.0.0.1", port=port, debug=True)
