# -*- coding: utf-8 -*-
"""古典诗歌文本结构化标注生产系统 — Flask 主应用 (v2: SQLite + 并行 + 断点续传)"""
import os, json, re, time, uuid, io
from flask import Flask, render_template, request, jsonify, session, Response, send_file

from lib import config_loader, persistence
from lib.auth import init_default_admin, register_user, login_user, logout_user, current_user, is_logged_in, login_required, admin_required, page_login_required
from lib.llm_client import call_llm
from lib.meta_prompts import parse_requirement, design_schema, quality_check
from lib.schema_engine import validate_headers, validate_output, rows_to_csv, save_template, load_template, list_templates
from lib.export import export_csv, export_json, list_exports
from lib.parallel import run_batch_parallel
from lib.template_library import list_all as list_all_templates, recommend, get_template_config, get_meta
from lib.corpus import get_index as get_corpus_index, build_index
from lib.quality_scorer import score_batch_results
from lib.report_writer import generate_text_report, generate_json_report, generate_executive_summary
from lib.annotation_tools import detect_imagery, detect_allusions, sentiment_polarity, word_frequency, imagery_evolution_stats
from lib.preprocessor import normalize_text, deduplicate_poems, batch_validate, split_by_dynasty, split_by_author, estimate_reading_level
from lib.annotation_tools import author_style_fingerprint, compare_authors, extract_rhyme_pattern, imagery_cooccurrence

app = Flask(__name__)
app.secret_key = config_loader.get("SECRET_KEY", "dev-secret")
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024


def _sid():
    """Get or create session ID stored in Flask session cookie."""
    if "_poemlab_sid" not in session:
        session["_poemlab_sid"] = persistence.create_session()
    return session["_poemlab_sid"]


# ─── Helpers ─────────────────────────────────────────────────────────

def _parse_poems(text: str) -> list:
    poems = []
    # Split on separator lines (======) or use blank-line splitting as fallback
    if re.search(r'={5,}', text):
        blocks = re.split(r'\n\s*={5,}\s*\n', text.strip())
    else:
        blocks = re.split(r'\n\s*\n', text.strip())
    for block in blocks:
        block = block.strip()
        if not block or block.startswith('='):
            continue
        poem = {"编号": "", "标题": "", "作者": "", "朝代": "", "原文": ""}
        # Try explicit KV format
        kv = re.findall(r'(?:^|\n)(编号|标题|作者|朝代|原文)[：:]\s*(.*?)(?=\n(?:编号|标题|作者|朝代|原文)[：:]|\Z)', block, re.DOTALL)
        if kv:
            for k, v in kv:
                poem[k] = v.strip()
        else:
            # Strip leading number prefix like "1. " or "1、"
            lines = block.split('\n')
            num_prefix = re.match(r'^(\d+)[\.\、\)）]\s*', lines[0])
            if num_prefix:
                poem["编号"] = f"P{int(num_prefix.group(1)):03d}"
                lines[0] = lines[0][num_prefix.end():].strip()
                block = '\n'.join(lines)

            # Match 《Title》 pattern — title in guillemets
            m = re.match(r'[《「](.+?)[》」]\s*(.*)', block, re.DOTALL)
            if m:
                poem["标题"] = m.group(1).strip()
                rest = m.group(2).strip()
                # Split rest: first line is author (if short), remaining is content
                rest_lines = rest.split('\n')
                if rest_lines:
                    # First non-empty line that's short = author name
                    author_line = rest_lines[0].strip()
                    if author_line and len(author_line) <= 6:
                        poem["作者"] = author_line
                        content_lines = [l for l in rest_lines[1:] if l.strip()]
                        poem["原文"] = '\n'.join(content_lines).strip()
                    else:
                        # No separate author line — all is content
                        poem["原文"] = rest
            else:
                # No title markers — treat as plain content
                # First short line might be title
                lines = [l.strip() for l in block.split('\n') if l.strip()]
                if lines:
                    if len(lines[0]) <= 20 and not poem["标题"]:
                        poem["标题"] = lines[0]
                        lines = lines[1:]
                    # Next short line = author
                    if lines and len(lines[0]) <= 6:
                        poem["作者"] = lines[0]
                        lines = lines[1:]
                    poem["原文"] = '\n'.join(lines)

        if poem["原文"]:
            poems.append(poem)

    for i, p in enumerate(poems):
        if not p["编号"]:
            p["编号"] = f"P{i+1:03d}"
    return poems


# ─── Page Routes ──────────────────────────────────────────────────────

@app.route("/")
@page_login_required
def index():
    return render_template("index.html", api_url=config_loader.get("API_URL"))


@app.route("/history")
@page_login_required
def history_page():
    return render_template("history.html")


@app.route("/login")
def login_page():
    return render_template("login.html")


@app.route("/register")
def register_page():
    return render_template("register.html")


@app.route("/conversations")
@page_login_required
def conversations_page():
    return render_template("conversations.html")


# ─── Auth Routes ───────────────────────────────────────────────────────

@app.route("/api/auth/register", methods=["POST"])
def api_register():
    data = request.get_json() or {}
    result = register_user(data.get("username", ""), data.get("password", ""))
    if not result["ok"]:
        return jsonify(result), 400
    return jsonify(result)


@app.route("/api/auth/login", methods=["POST"])
def api_login():
    data = request.get_json() or {}
    result = login_user(data.get("username", ""), data.get("password", ""))
    if not result["ok"]:
        return jsonify(result), 401
    return jsonify(result)


@app.route("/api/auth/logout", methods=["POST"])
def api_logout():
    logout_user()
    return jsonify({"ok": True})


@app.route("/api/auth/me")
def api_me():
    user = current_user()
    if not user:
        return jsonify({"ok": False, "logged_in": False})
    return jsonify({"ok": True, "logged_in": True, "user": user})


# ─── Conversation Routes ───────────────────────────────────────────────

@app.route("/api/conversations")
@login_required
def api_list_conversations():
    q = request.args.get("q", "").strip()
    limit = request.args.get("limit", 50, type=int)
    offset = request.args.get("offset", 0, type=int)
    if q:
        conversations = persistence.search_all_conversations(q, limit)
        total = len(conversations)
    else:
        conversations = persistence.get_all_conversations(limit, offset)
        total = persistence.count_all_conversations()
    return jsonify({"ok": True, "conversations": conversations, "total": total})


@app.route("/api/conversations/<int:conv_id>")
@login_required
def api_get_conversation(conv_id):
    c = persistence.get_conversation(conv_id)
    if not c:
        return jsonify({"ok": False, "error": "对话记录不存在"}), 404
    return jsonify({"ok": True, "conversation": c})


# ─── Session Routes ───────────────────────────────────────────────────

@app.route("/api/sessions")
@login_required
def api_list_sessions():
    return jsonify({"ok": True, "sessions": persistence.list_sessions()})


@app.route("/api/sessions/create", methods=["POST"])
@login_required
def api_create_session():
    data = request.get_json() or {}
    sid = persistence.create_session(data.get("name", ""))
    session.pop("_poemlab_sid", None)
    session["_poemlab_sid"] = sid
    return jsonify({"ok": True, "session_id": sid})


@app.route("/api/sessions/resume/<sid>", methods=["POST"])
@login_required
def api_resume_session(sid):
    s = persistence.get_session(sid)
    if not s:
        return jsonify({"ok": False, "error": "会话不存在"}), 404
    session["_poemlab_sid"] = sid
    poem_count = persistence.get_poem_count(sid)
    parsed_headers = persistence.get_schema(sid, "parsed_headers")
    schema_result = persistence.get_schema(sid, "designed_schema")
    quality_report = persistence.get_schema(sid, "quality_checked")
    return jsonify({
        "ok": True, "session_id": sid,
        "poem_count": poem_count,
        "parsed_headers": parsed_headers,
        "schema_result": schema_result,
        "quality_report": quality_report
    })


# ─── API Routes: Poems ────────────────────────────────────────────────

@app.route("/api/poems/upload", methods=["POST"])
@login_required
def api_upload_poems():
    if "file" in request.files:
        f = request.files["file"]
        text = f.read().decode("utf-8")
    elif "text" in request.form:
        text = request.form["text"]
    else:
        return jsonify({"ok": False, "error": "请上传文件或粘贴文本"}), 400

    poems = _parse_poems(text)
    persistence.save_poems(_sid(), poems)
    return jsonify({"ok": True, "count": len(poems), "preview": poems[:5]})


# ─── API Routes: Meta-Prompting Pipeline ──────────────────────────────

@app.route("/api/parse-requirement", methods=["POST"])
@login_required
def api_parse_requirement():
    data = request.get_json()
    requirement = data.get("requirement", "").strip()
    if not requirement:
        return jsonify({"ok": False, "error": "需求描述不能为空"}), 400

    result = parse_requirement(requirement, _sid())
    if not result:
        return jsonify({"ok": False, "error": "AI 响应解析失败，请重试"}), 500

    persistence.save_schema(_sid(), "parsed_headers", result)
    return jsonify({"ok": True, "data": result})


@app.route("/api/design-schema", methods=["POST"])
@login_required
def api_design_schema():
    data = request.get_json()
    headers = data.get("headers", [])

    ok, msg = validate_headers(headers)
    if not ok:
        return jsonify({"ok": False, "error": msg}), 400

    result = design_schema(headers, _sid())
    if not result:
        return jsonify({"ok": False, "error": "AI 响应解析失败，请重试"}), 500

    cm = result.get("column_mapping", [])
    sr = result.get("sample_row", {})
    sample_ok, sample_issues = validate_output(sr, cm)
    result["sample_validation"] = {"ok": sample_ok, "issues": sample_issues}

    persistence.save_schema(_sid(), "designed_schema", result)
    return jsonify({"ok": True, "data": result})


@app.route("/api/validate-headers", methods=["POST"])
@login_required
def api_validate_headers():
    data = request.get_json()
    headers = data.get("headers", [])
    ok, msg = validate_headers(headers)
    return jsonify({"ok": ok, "message": msg})


@app.route("/api/quality-check", methods=["POST"])
@login_required
def api_quality_check():
    data = request.get_json()
    generated_prompt = data.get("generated_prompt", "")
    column_mapping = data.get("column_mapping", [])
    test_count = int(data.get("test_count", config_loader.get("TEST_RUN_COUNT", 5)))

    poems = persistence.get_poems(_sid())
    if not poems:
        return jsonify({"ok": False, "error": "请先上传诗歌数据"}), 400

    sample_poems = poems[:test_count]
    report = quality_check(generated_prompt, sample_poems, column_mapping, _sid())
    persistence.save_schema(_sid(), "quality_checked", report or {})

    return jsonify({"ok": True, "data": report})


@app.route("/api/sync-schema", methods=["POST"])
@login_required
def api_sync_schema():
    """Save frontend-edited prompt/mapping back to server before batch run."""
    data = request.get_json()
    sid = _sid()
    current = persistence.get_schema(sid, "designed_schema") or {}
    if data.get("generated_prompt"):
        current["generated_prompt"] = data["generated_prompt"]
    if data.get("column_mapping"):
        current["column_mapping"] = data["column_mapping"]
    persistence.save_schema(sid, "designed_schema", current)
    return jsonify({"ok": True})


# ─── API Routes: Batch Run (SSE, Parallel, Checkpointed) ─────────────

@app.route("/api/batch-run")
@login_required
def api_batch_run():
    sid = _sid()
    poems = persistence.get_poems(sid)
    schema_result = persistence.get_schema(sid, "designed_schema")
    generated_prompt = schema_result.get("generated_prompt", "") if schema_result else ""
    column_mapping = schema_result.get("column_mapping", []) if schema_result else []

    if not poems or not generated_prompt:
        return Response("data: {\"error\": \"缺少诗歌数据或提示词\"}\n\n",
                       mimetype="text/event-stream")

    rid = persistence.create_batch_run(sid, generated_prompt, column_mapping, len(poems))

    def generate():
        for evt in run_batch_parallel(rid, poems, generated_prompt, column_mapping):
            yield evt

        # Export CSV/JSON after completion
        results = persistence.get_batch_results(rid)
        parsed_results = [r["result"] for r in results if r.get("result")]
        if parsed_results and column_mapping:
            csv_content = rows_to_csv(parsed_results, column_mapping)
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            csv_path = export_csv(f"batch_{timestamp}.csv", csv_content)
            json_path = export_json(f"batch_{timestamp}.json", {"results": results, "column_mapping": column_mapping})
            persistence.set_run_export_paths(rid, os.path.basename(csv_path), os.path.basename(json_path))
            yield f"data: {json.dumps({'exports_ready': True, 'csv_file': os.path.basename(csv_path), 'json_file': os.path.basename(json_path)}, ensure_ascii=False)}\n\n"
        else:
            yield f"data: {json.dumps({'exports_ready': True, 'csv_file': '', 'json_file': ''}, ensure_ascii=False)}\n\n"

    return Response(generate(), mimetype="text/event-stream")


@app.route("/api/batch-resume/<rid>")
@login_required
def api_batch_resume(rid):
    """Resume an interrupted batch run."""
    run = persistence.get_batch_run(rid)
    if not run:
        return Response("data: {\"error\": \"批次不存在\"}\n\n", mimetype="text/event-stream")

    poems = persistence.get_poems(run["session_id"])
    generated_prompt = run["generated_prompt"]
    column_mapping = run["column_mapping"]

    def generate():
        for evt in run_batch_parallel(rid, poems, generated_prompt, column_mapping):
            yield evt

        results = persistence.get_batch_results(rid)
        parsed_results = [r["result"] for r in results if r.get("result")]
        if parsed_results and column_mapping:
            csv_content = rows_to_csv(parsed_results, column_mapping)
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            csv_path = export_csv(f"batch_{timestamp}.csv", csv_content)
            json_path = export_json(f"batch_{timestamp}.json", {"results": results, "column_mapping": column_mapping})
            persistence.set_run_export_paths(rid, os.path.basename(csv_path), os.path.basename(json_path))
            yield f"data: {json.dumps({'exports_ready': True, 'csv_file': os.path.basename(csv_path), 'json_file': os.path.basename(json_path)}, ensure_ascii=False)}\n\n"
        else:
            yield f"data: {json.dumps({'exports_ready': True, 'csv_file': '', 'json_file': ''}, ensure_ascii=False)}\n\n"

    return Response(generate(), mimetype="text/event-stream")


@app.route("/api/batch-runs")
@login_required
def api_list_batch_runs():
    # Load batch runs from ALL sessions (single-user desktop app)
    runs = persistence.get_all_batch_runs()
    return jsonify({"ok": True, "runs": runs})


# ─── API Routes: Templates ───────────────────────────────────────────

@app.route("/api/list-templates")
@login_required
def api_list_templates():
    return jsonify({"ok": True, "templates": list_templates()})


@app.route("/api/load-template/<name>")
@login_required
def api_load_template(name):
    data = load_template(name)
    if data is None:
        return jsonify({"ok": False, "error": "模板不存在"}), 404
    return jsonify({"ok": True, "data": data})


@app.route("/api/save-template", methods=["POST"])
@login_required
def api_save_template():
    data = request.get_json()
    name = data.get("name", "").strip()
    tmpl_data = data.get("data", {})
    if not name or not tmpl_data:
        return jsonify({"ok": False, "error": "模板名称和数据不能为空"}), 400
    path = save_template(name, tmpl_data)
    if not path:
        return jsonify({"ok": False, "error": "保存失败"}), 500
    return jsonify({"ok": True, "path": path})


# ─── API Routes: Exports ─────────────────────────────────────────────

@app.route("/api/list-exports")
@login_required
def api_list_exports():
    return jsonify({"ok": True, "exports": list_exports()})


@app.route("/api/export/csv/<filename>")
@login_required
def api_download_csv(filename):
    export_dir = config_loader.get("EXPORTS_DIR", "")
    path = os.path.join(export_dir, filename)
    if not os.path.exists(path):
        return jsonify({"ok": False, "error": "文件不存在"}), 404
    return send_file(path, mimetype="text/csv", as_attachment=True,
                    download_name=filename)


@app.route("/api/export/json/<filename>")
@login_required
def api_download_json(filename):
    export_dir = config_loader.get("EXPORTS_DIR", "")
    path = os.path.join(export_dir, filename)
    if not os.path.exists(path):
        return jsonify({"ok": False, "error": "文件不存在"}), 404
    return send_file(path, mimetype="application/json", as_attachment=True,
                    download_name=filename)


@app.route("/dashboard")
@page_login_required
def dashboard_page():
    return render_template("dashboard.html")


@app.route("/corpus")
@page_login_required
def corpus_page():
    return render_template("corpus.html")


# ─── API Routes: Template Library ─────────────────────────────────────

@app.route("/api/template-library")
@login_required
def api_template_library():
    category = request.args.get("category", "")
    keyword = request.args.get("keyword", "")
    if keyword:
        return jsonify({"ok": True, "templates": recommend(keyword)})
    if category:
        from lib.template_library import list_by_category
        return jsonify({"ok": True, "templates": list_by_category(category)})
    return jsonify({"ok": True, "templates": list_all_templates()})


@app.route("/api/template-library/recommend", methods=["POST"])
@login_required
def api_template_recommend():
    data = request.get_json()
    requirement = data.get("requirement", "").strip()
    if not requirement:
        return jsonify({"ok": False, "error": "需求描述不能为空"}), 400
    recs = recommend(requirement)
    return jsonify({"ok": True, "recommendations": recs})


@app.route("/api/template-library/<template_key>")
@login_required
def api_template_detail(template_key):
    config = get_template_config(template_key)
    if not config:
        return jsonify({"ok": False, "error": "模板不存在"}), 404
    return jsonify({"ok": True, "data": config})


@app.route("/api/template-library/<template_key>/apply", methods=["POST"])
@login_required
def api_template_apply(template_key):
    """Apply a pre-built template: pre-fill headers and prompt for the current session."""
    config = get_template_config(template_key)
    if not config:
        return jsonify({"ok": False, "error": "模板不存在"}), 404
    default_headers = config.get("default_headers", [])
    prompt = config.get("prompt", "")
    meta = config.get("meta", {})

    # Save schema with the template's default setup
    schema_data = {
        "generated_prompt": prompt,
        "column_mapping": [
            {"header": h["name"], "field": h["name"], "dimension": meta.get("name", ""),
             "data_type": "string", "enum_values": []}
            for h in default_headers
        ],
        "sample_row": {},
        "analysis_notes": f'使用预置模板：{meta.get("name", "")}',
        "from_template": template_key
    }
    persistence.save_schema(_sid(), "designed_schema", schema_data)
    return jsonify({"ok": True, "data": schema_data})


# ─── API Routes: Corpus ──────────────────────────────────────────────

@app.route("/api/corpus/stats")
@login_required
def api_corpus_stats():
    idx = get_corpus_index()
    if idx.total == 0:
        # Load ALL poems from ALL sessions (single-user desktop app)
        poems = persistence.get_all_poems()
        if poems:
            idx = build_index(poems)
    summary = idx.summary()
    return jsonify({
        "ok": True,
        "stats": {
            "total": summary.get("总诗歌数", 0),
            "authors": summary.get("作者数", 0),
            "dynasties": len(summary.get("朝代分布", {})),
            "forms": len(summary.get("诗体分布", {})),
            "dynasty_list": list(summary.get("朝代分布", {}).keys()),
            "dynasty_counts": summary.get("朝代分布", {}),
            "form_counts": summary.get("诗体分布", {})
        }
    })


@app.route("/api/corpus/poems")
@login_required
def api_corpus_poems():
    idx = get_corpus_index()
    if idx.total == 0:
        poems = persistence.get_all_poems()
        if poems:
            idx = build_index(poems)
    return jsonify({"ok": True, "poems": idx.poems, "total": idx.total})


@app.route("/api/corpus/author/<author>")
@login_required
def api_corpus_by_author(author):
    idx = get_corpus_index()
    poems = idx.get_by_author(author)
    return jsonify({"ok": True, "author": author, "count": len(poems), "poems": poems})


@app.route("/api/corpus/search")
@login_required
def api_corpus_search():
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify({"ok": False, "error": "请提供关键词"}), 400
    idx = get_corpus_index()
    if idx.total == 0:
        poems = persistence.get_poems(_sid())
        if poems:
            idx = build_index(poems)
    results = idx.search(q)
    return jsonify({"ok": True, "keyword": q, "count": len(results), "poems": results})


# ─── API Routes: Quality Scoring ─────────────────────────────────────

@app.route("/api/quality-score/<rid>")
@login_required
def api_quality_score(rid):
    results = persistence.get_batch_results(rid)
    run = persistence.get_batch_run(rid)
    if not run:
        return jsonify({"ok": False, "error": "批次不存在"}), 404
    cm = run.get("column_mapping", [])
    score = score_batch_results(results, cm)
    return jsonify({"ok": True, "score": score})


# ─── API Routes: Reports ─────────────────────────────────────────────

@app.route("/api/report/<rid>")
@login_required
def api_report(rid):
    fmt = request.args.get("format", "json")
    if fmt == "text":
        report = generate_text_report(rid)
        return Response(report, mimetype="text/plain; charset=utf-8")
    report = generate_json_report(rid)
    return jsonify({"ok": True, "report": report})


@app.route("/api/report/<rid>/summary")
@login_required
def api_report_summary(rid):
    summary = generate_executive_summary(rid)
    return jsonify({"ok": True, "summary": summary})


# ─── API Routes: Annotation Tools ────────────────────────────────────

@app.route("/api/tools/detect-imagery", methods=["POST"])
@login_required
def api_detect_imagery():
    data = request.get_json()
    text = data.get("text", "").strip()
    if not text:
        return jsonify({"ok": False, "error": "文本不能为空"}), 400
    results = detect_imagery(text)
    return jsonify({"ok": True, "count": len(results), "imagery": results})


@app.route("/api/tools/detect-allusions", methods=["POST"])
@login_required
def api_detect_allusions():
    data = request.get_json()
    text = data.get("text", "").strip()
    if not text:
        return jsonify({"ok": False, "error": "文本不能为空"}), 400
    results = detect_allusions(text)
    return jsonify({"ok": True, "count": len(results), "allusions": results})


@app.route("/api/tools/sentiment", methods=["POST"])
@login_required
def api_sentiment():
    data = request.get_json()
    text = data.get("text", "").strip()
    if not text:
        return jsonify({"ok": False, "error": "文本不能为空"}), 400
    result = sentiment_polarity(text)
    return jsonify({"ok": True, "sentiment": result})


@app.route("/api/tools/word-frequency")
@login_required
def api_word_frequency():
    poems = persistence.get_poems(_sid())
    if not poems:
        return jsonify({"ok": False, "error": "请先上传诗歌数据"}), 400
    top_n = request.args.get("top", 50, type=int)
    freq = word_frequency(poems, top_n)
    return jsonify({"ok": True, "frequency": [{"char": c, "count": n} for c, n in freq]})


@app.route("/api/tools/imagery-evolution/<imagery_word>")
@login_required
def api_imagery_evolution(imagery_word):
    poems = persistence.get_poems(_sid())
    if not poems:
        return jsonify({"ok": False, "error": "请先上传诗歌数据"}), 400
    stats = imagery_evolution_stats(poems, imagery_word)
    return jsonify({"ok": True, "imagery": imagery_word, "evolution": stats})


# ─── API Routes: Preprocessor ────────────────────────────────────────

@app.route("/api/preprocess/normalize", methods=["POST"])
@login_required
def api_normalize():
    data = request.get_json()
    text = data.get("text", "").strip()
    if not text:
        return jsonify({"ok": False, "error": "文本不能为空"}), 400
    normalized = normalize_text(text)
    return jsonify({"ok": True, "result": normalized, "len_before": len(text), "len_after": len(normalized)})


@app.route("/api/preprocess/dedup")
@login_required
def api_dedup_poems():
    poems = persistence.get_poems(_sid())
    if not poems:
        return jsonify({"ok": False, "error": "请先上传诗歌数据"}), 400
    unique, dups = deduplicate_poems(poems)
    return jsonify({"ok": True, "total": len(poems), "unique": len(unique), "duplicates": len(dups), "dup_list": dups[:10]})


@app.route("/api/preprocess/validate")
@login_required
def api_batch_validate():
    poems = persistence.get_poems(_sid())
    if not poems:
        return jsonify({"ok": False, "error": "请先上传诗歌数据"}), 400
    result = batch_validate(poems)
    return jsonify({"ok": True, "validation": result})


@app.route("/api/preprocess/groups/<by>")
@login_required
def api_groups(by):
    poems = persistence.get_poems(_sid())
    if not poems:
        return jsonify({"ok": False, "error": "请先上传诗歌数据"}), 400
    if by == "dynasty":
        groups = split_by_dynasty(poems)
    elif by == "author":
        groups = split_by_author(poems)
    else:
        return jsonify({"ok": False, "error": "请使用 dynasty 或 author"}), 400
    summary = {k: len(v) for k, v in groups.items()}
    return jsonify({"ok": True, "group_by": by, "groups": summary, "total_groups": len(groups)})


@app.route("/api/preprocess/reading-level", methods=["POST"])
@login_required
def api_reading_level():
    data = request.get_json()
    text = data.get("text", "").strip()
    if not text:
        return jsonify({"ok": False, "error": "文本不能为空"}), 400
    result = estimate_reading_level(text)
    return jsonify({"ok": True, "level": result})


@app.route("/api/tools/author-style/<author>")
@login_required
def api_author_style(author):
    poems = persistence.get_poems(_sid())
    if not poems:
        return jsonify({"ok": False, "error": "请先上传诗歌数据"}), 400
    fp = author_style_fingerprint(poems, author)
    return jsonify({"ok": True, "style": fp})


@app.route("/api/tools/compare-authors")
@login_required
def api_compare_authors():
    a = request.args.get("a", "").strip()
    b = request.args.get("b", "").strip()
    if not a or not b:
        return jsonify({"ok": False, "error": "请提供两个作者名（?a=李白&b=杜甫）"}), 400
    poems = persistence.get_poems(_sid())
    if not poems:
        return jsonify({"ok": False, "error": "请先上传诗歌数据"}), 400
    result = compare_authors(poems, a, b)
    return jsonify({"ok": True, "comparison": result})


@app.route("/api/tools/rhyme", methods=["POST"])
@login_required
def api_rhyme():
    data = request.get_json()
    text = data.get("text", "").strip()
    if not text:
        return jsonify({"ok": False, "error": "文本不能为空"}), 400
    result = extract_rhyme_pattern(text)
    return jsonify({"ok": True, "rhyme": result})


@app.route("/api/tools/cooccurrence/<word>")
@login_required
def api_cooccurrence(word):
    poems = persistence.get_poems(_sid())
    if not poems:
        return jsonify({"ok": False, "error": "请先上传诗歌数据"}), 400
    top_n = request.args.get("top", 20, type=int)
    result = imagery_cooccurrence(poems, word, top_n)
    return jsonify({"ok": True, "word": word, "cooccurrence": [{"char": c, "count": n} for c, n in result]})


# ─── Main ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    init_default_admin()
    host = config_loader.get("FLASK_HOST", "0.0.0.0")
    port = int(config_loader.get("FLASK_PORT", 5100))
    print(f"古典诗歌文本结构化标注生产系统 v2 启动: http://{host}:{port}")
    app.run(host=host, port=port, debug=True)
