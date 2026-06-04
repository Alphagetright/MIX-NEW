# -*- coding: utf-8 -*-
"""唐诗意象智能分析系统 Flask Web 主程序"""

import json
import os
import glob
import re

from functools import wraps
from flask import Flask, render_template, request, Response, session, redirect, url_for

from config import (
    BASE_DIR, POEM_JSON_DIR, FLASK_HOST, FLASK_PORT, FLASK_DEBUG, FLASK_THREADED,
    SECRET_KEY, CATEGORY_NAME_MAP, PAGE_SIZE, RENDER_LIMIT,
    SESSION_TIMEOUT,
)
from errors import register_error_handlers, AppError, ValidationError, sse_error
from validators import validate_question, validate_item, validate_history
from logger import get_logger, LoggerMixin
from cache import memory_cache, file_cache, cached

logger = get_logger("app")

app = Flask(__name__)
app.secret_key = SECRET_KEY
app.config["PERMANENT_SESSION_LIFETIME"] = SESSION_TIMEOUT
register_error_handlers(app)

from admin import admin_bp
import users

app.register_blueprint(admin_bp)
users.init_default_admin()


def login_required(f):
    """登录校验装饰器"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("user"):
            return redirect(url_for("login_page"))
        return f(*args, **kwargs)
    return decorated


def clean_and_load_json(file_path):
    """读取并清洗JSON文件"""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read().strip()
    content = re.sub(r"^```json\s*", "", content, flags=re.MULTILINE)
    content = re.sub(r"^```\s*", "", content, flags=re.MULTILINE)
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return None


def extract_poems(node):
    """递归提取诗歌节点"""
    found_poems = []
    if isinstance(node, dict):
        if "分析单元" in node and isinstance(node.get("分析单元"), list):
            found_poems.append(node)
        else:
            for value in node.values():
                found_poems.extend(extract_poems(value))
    elif isinstance(node, list):
        for item in node:
            found_poems.extend(extract_poems(item))
    return found_poems


def build_traceback_dataset():
    """从 poem_json 目录扫描 JSON/TXT，生成溯源表与统计"""
    json_folder = POEM_JSON_DIR
    if not os.path.exists(json_folder):
        os.makedirs(json_folder, exist_ok=True)

    target_files = []
    for ext in ("*.json", "*.txt"):
        target_files.extend(glob.glob(os.path.join(json_folder, ext)))

    logger.info(f"扫描到 {len(target_files)} 个数据文件")

    traceback_data_list = []
    total_poems = 0
    seen_poem_fingerprints = set()

    skip_names = {
        "all_data.json", "dashboard_interactive_pro.html",
        "dashboard_FINAL_DASHBOARD.html", "Thesis_Dashboard.html",
    }

    for file_path in target_files:
        file_name = os.path.basename(file_path)
        if file_name in skip_names:
            continue
        data = clean_and_load_json(file_path)
        if not data:
            continue
        poems = extract_poems(data)
        if not poems:
            continue
        for p in poems:
            if not isinstance(p, dict):
                continue
            title = str(p.get("标题", "未知诗歌")).strip()
            poem_id = str(p.get("诗歌编号", p.get("编号", "-"))).strip()
            lines_data = p.get("诗行", [])
            first_line = ""
            if lines_data and isinstance(lines_data[0], dict):
                first_line = str(lines_data[0].get("原文", "")).strip()
            fingerprint = f"{title}_{first_line}"
            if fingerprint in seen_poem_fingerprints:
                continue
            seen_poem_fingerprints.add(fingerprint)
            total_poems += 1
            genre = str(p.get("分类标签", p.get("体裁", "未分类"))).strip()
            line_map = {}
            for l in lines_data:
                if isinstance(l, dict):
                    line_map[str(l.get("诗行编号", ""))] = l.get("原文", "")
            for u in p.get("分析单元", []):
                if not isinstance(u, dict):
                    continue
                if str(u.get("是否意象", "0")).strip() == "1":
                    text = str(u.get("文本", "")).strip()
                    sub_code = str(u.get("子类编码", "")).strip()
                    line_id = str(u.get("诗行编号", "")).strip()
                    line_text = line_map.get(line_id, "未知诗句")
                    cat_name = CATEGORY_NAME_MAP.get(sub_code, f"其他分类 ({sub_code})")
                    if text:
                        emo_cat = str(u.get("情感类别", "未知")).strip()
                        emo_pol = str(u.get("情感极性", "")).strip()
                        emotion_str = f"{emo_cat} ({emo_pol})" if emo_pol else emo_cat
                        dim_parts = []
                        for key in ["感知通道", "素材类型", "指涉来源", "表现功能"]:
                            val = str(u.get(key, "")).strip()
                            if val and val != "None":
                                dim_parts.append(val)
                        dimensions_str = " | ".join(dim_parts) if dim_parts else "-"
                        major_code = u.get("大类编码", "")
                        if major_code == "" or major_code is None:
                            major_code = (
                                sub_code.split("-")[0]
                                if sub_code and "-" in sub_code
                                else ""
                            )
                        traceback_data_list.append({
                            "poem_id": poem_id,
                            "title": title,
                            "author": p.get("作者", ""),
                            "genre": genre,
                            "cat": cat_name,
                            "txt": text,
                            "文本": text,
                            "dimensions": dimensions_str,
                            "emotion": emotion_str,
                            "emo_cat": emo_cat,
                            "line": line_text,
                            "id": line_id,
                            "词性": u.get("词性", ""),
                            "成分类型": u.get("成分类型", ""),
                            "感知通道": u.get("感知通道", ""),
                            "素材类型": u.get("素材类型", ""),
                            "内部结构": u.get("内部结构", ""),
                            "指涉来源": u.get("指涉来源", ""),
                            "表现功能": u.get("表现功能", ""),
                            "文化流通性": u.get("文化流通性", ""),
                            "跨文化性": u.get("跨文化性", ""),
                            "认知强度": u.get("认知强度", ""),
                            "核心意象": u.get("核心意象", ""),
                            "结构功能组": u.get("结构功能组", ""),
                            "情感极性": u.get("情感极性", ""),
                            "情感类别": u.get("情感类别", emo_cat),
                            "情感置信度": u.get("情感置信度", ""),
                            "大类编码": major_code,
                            "子类编码": sub_code,
                        })

    logger.info(f"数据加载完成: {total_poems} 首诗歌, {len(traceback_data_list)} 条意象")
    return {
        "total_poems": total_poems,
        "total_images": len(traceback_data_list),
        "traceback": traceback_data_list,
    }


_DATA_CACHE = None


def get_data():
    global _DATA_CACHE
    if _DATA_CACHE is None:
        _DATA_CACHE = build_traceback_dataset()
    return _DATA_CACHE


def clear_data_cache():
    global _DATA_CACHE
    _DATA_CACHE = None
    logger.info("数据缓存已清除")


def sse_json(obj):
    return f"data: {json.dumps(obj, ensure_ascii=False)}\n\n"


def build_analyze_system_prompt(item):
    """构建认知诗学解析 Prompt"""
    return f"""你是专精认知诗学与中国古典文学的学者。

当前意象数据：
- 意象文本：{item.get('文本', '')}
- 所属诗歌：{item.get('title', '')}
- 所在诗句：{item.get('line', '')}
- 词性：{item.get('词性', '')} | 成分类型：{item.get('成分类型', '')}
- 感知通道：{item.get('感知通道', '')} | 素材类型：{item.get('素材类型', '')}
- 内部结构：{item.get('内部结构', '')} | 指涉来源：{item.get('指涉来源', '')}
- 表现功能：{item.get('表现功能', '')} | 结构功能组：{item.get('结构功能组', '')}
- 文化流通性：{item.get('文化流通性', '')} | 跨文化性：{item.get('跨文化性', '')}
- 认知强度：{item.get('认知强度', '')} | 核心意象：{item.get('核心意象', '')}
- 情感极性：{item.get('情感极性', '')} | 情感类别：{item.get('情感类别', '')} | 置信度：{item.get('情感置信度', '')}

请按以下维度解析：
1. 感知层：触发的感官体验和通感效果
2. 文化层：典故来源和文化符号意义
3. 情感层：基于情感极性{item.get('情感极性', '')}分析情感功能
4. 结构层：作为{item.get('结构功能组', '')}在诗中的结构作用
5. 跨诗比较：此意象在其他诗歌中的异同

严格基于提供的数据分析，不编造。"""


# ── 页面路由 ──

@app.route("/login", methods=["GET", "POST"])
def login_page():
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        if username and password and users.authenticate(username, password):
            session["user"] = username
            return redirect(url_for("dashboard"))
        error = "用户名或密码错误"
    return render_template("login.html", error=error)


@app.route("/register", methods=["GET", "POST"])
def register_page():
    error = None
    success = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        ok, msg = users.register(username, password)
        if ok:
            success = msg
            session["user"] = username
            return redirect(url_for("dashboard"))
        error = msg
    return render_template("register.html", error=error, success=success)


@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("login_page"))


@app.route("/")
@login_required
def index():
    return redirect(url_for("dashboard"))


@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html")


@app.route("/graph")
@login_required
def graph_page():
    return render_template("graph_charts.html")


@app.route("/graph/table")
@login_required
def graph_table_page():
    return render_template("graph_table.html")


@app.route("/ai")
@login_required
def ai_page():
    return render_template("ai.html")


@app.route("/recycle")
@login_required
def recycle_page():
    return render_template("recycle.html")


# ── 数据 API ──

@app.route("/api/data")
def api_data():
    return Response(
        json.dumps(get_data(), ensure_ascii=False),
        mimetype="application/json; charset=utf-8",
    )


@app.route("/api/stats")
def api_stats_summary():
    from analytics import StatsService, build_analytics_api
    data = get_data()
    traceback = data.get("traceback", [])
    service = StatsService(traceback)
    return Response(
        json.dumps(build_analytics_api(service), ensure_ascii=False),
        mimetype="application/json; charset=utf-8",
    )


@app.route("/api/export", methods=["POST"])
def api_export():
    from export_service import ExportService
    payload = request.get_json(force=True, silent=True) or {}
    fmt = payload.get("format", "csv")
    data = get_data()
    traceback = data.get("traceback", [])

    try:
        if fmt == "csv":
            path = ExportService.export_traceback_to_csv(traceback)
        elif fmt == "json":
            path = ExportService.export_to_json(data)
        else:
            return Response(
                json.dumps({"error": f"不支持格式: {fmt}"}, ensure_ascii=False),
                mimetype="application/json; charset=utf-8",
                status=400,
            )
        return Response(
            json.dumps({"path": path, "file": os.path.basename(path)}, ensure_ascii=False),
            mimetype="application/json; charset=utf-8",
        )
    except Exception as e:
        logger.exception("导出失败")
        return Response(
            json.dumps({"error": str(e)}, ensure_ascii=False),
            mimetype="application/json; charset=utf-8",
            status=500,
        )


# ── AI 问答 API（RAG）──

@app.route("/api/ask", methods=["POST"])
def api_ask():
    payload = request.get_json(force=True, silent=True) or {}
    question = (payload.get("question") or "").strip()
    history = validate_history(payload.get("history"))

    try:
        question = validate_question(question)
    except ValidationError as e:
        def empty():
            yield sse_error(e.message)
        return Response(empty(), mimetype="text/event-stream")

    from query_rag import stream_rag_answer_events

    def generate():
        try:
            for ev in stream_rag_answer_events(question, history):
                if ev.get("type") == "poems":
                    yield sse_json({"type": "poems", "poems": ev.get("poems") or []})
                    if not history and not (ev.get("poems") or []):
                        yield sse_json({
                            "type": "error",
                            "message": "未检索到相关诗歌，请调整提问或检查向量库。",
                        })
                        return
                elif ev.get("type") == "chunk" and ev.get("text"):
                    yield sse_json({"type": "chunk", "text": ev["text"]})
        except Exception as e:
            logger.exception("RAG 问答异常")
            yield sse_json({"type": "error", "message": str(e)})

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── 认知诗学解析 API ──

@app.route("/api/analyze", methods=["POST"])
def api_analyze():
    payload = request.get_json(force=True, silent=True) or {}
    item = payload.get("item") or {}
    history = validate_history(payload.get("history"))
    followup = payload.get("followup")

    try:
        item = validate_item(item)
    except ValidationError as e:
        def err():
            yield sse_error(e.message)
        return Response(err(), mimetype="text/event-stream")

    system_prompt = build_analyze_system_prompt(item)

    from query_rag import stream_cognitive_analysis

    def generate():
        try:
            for chunk in stream_cognitive_analysis(
                system_prompt,
                history=history,
                followup=followup,
            ):
                if chunk:
                    yield sse_json({"type": "chunk", "text": chunk})
        except Exception as e:
            logger.exception("认知解析异常")
            yield sse_json({"type": "error", "message": str(e)})

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── 缓存管理 API ──

@app.route("/api/cache/status")
def api_cache_status():
    return Response(
        json.dumps({
            "memory_entries": memory_cache.size(),
            "file_entries": file_cache.size(),
            "data_cache_active": _DATA_CACHE is not None,
        }),
        mimetype="application/json; charset=utf-8",
    )


if __name__ == "__main__":
    logger.info(f"启动唐诗意象智能分析系统 (http://{FLASK_HOST}:{FLASK_PORT})")
    app.run(host=FLASK_HOST, port=FLASK_PORT, debug=FLASK_DEBUG, threaded=FLASK_THREADED)
