# -*- coding: utf-8 -*-
"""
管理后台 Blueprint — 系统状态、数据管理、导出操作
"""
import json
import os
import sys
import time
import threading
import subprocess
import uuid

from functools import wraps
from flask import Blueprint, render_template, jsonify, request, Response, session, redirect, url_for

from config import (
    BASE_DIR, RAG_DB_DIR, POEM_JSON_DIR, EXPORT_DIR,
    EMBED_MODEL, CHAT_MODEL, FLASK_PORT,
    CATEGORY_NAME_MAP, KNOWN_AUTHORS, PAGE_SIZE, TOP_K,
)
from analytics import StatsService
from cache import memory_cache, file_cache
from export_service import ExportService
from logger import get_logger

logger = get_logger("admin")

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.before_request
def _check_admin_login():
    """管理后台所有路由需要登录"""
    if not session.get("user"):
        return redirect(url_for("login_page"))


def _get_data_provider():
    """延迟导入以避免循环引用"""
    from app import get_data
    return get_data()


@admin_bp.route("/")
def admin_index():
    return render_template("admin.html")


@admin_bp.route("/api/status")
def api_status():
    """系统状态总览"""
    data = _get_data_provider()
    total_images = len(data.get("traceback", []))
    total_poems = data.get("total_poems", 0)

    rag_exists = os.path.exists(RAG_DB_DIR) and os.path.isdir(RAG_DB_DIR)
    rag_file_count = 0
    if rag_exists:
        for root, dirs, files in os.walk(RAG_DB_DIR):
            rag_file_count += len(files)

    chunk_count = 0
    if os.path.exists(POEM_JSON_DIR):
        chunk_count = len([f for f in os.listdir(POEM_JSON_DIR)
                          if f.endswith((".json", ".txt"))])

    cache_info = {
        "memory_entries": memory_cache.size(),
        "file_entries": file_cache.size(),
    }

    export_files = ExportService.list_exports()

    return jsonify({
        "status": "running",
        "timestamp": time.time(),
        "data": {
            "total_poems": total_poems,
            "total_images": total_images,
            "category_count": len(CATEGORY_NAME_MAP),
            "known_authors_count": len(KNOWN_AUTHORS),
        },
        "rag_database": {
            "exists": rag_exists,
            "file_count": rag_file_count,
            "path": RAG_DB_DIR,
        },
        "poem_json": {
            "file_count": chunk_count,
            "path": POEM_JSON_DIR,
        },
        "cache": cache_info,
        "exports": {
            "file_count": len(export_files),
            "directory": EXPORT_DIR,
        },
        "config": {
            "embed_model": EMBED_MODEL,
            "chat_model": CHAT_MODEL,
            "port": FLASK_PORT,
            "top_k": TOP_K,
            "page_size": PAGE_SIZE,
        },
    })


@admin_bp.route("/api/stats")
def api_stats():
    """统计分析数据"""
    data = _get_data_provider()
    traceback = data.get("traceback", [])
    service = StatsService(traceback)

    report = service.summary_report()
    report["cross_analysis"] = service.cross_analysis()
    report["author_stats"] = service.author_statistics()
    report["perception_stats"] = service.perception_channel_distribution()
    return jsonify(report)


@admin_bp.route("/api/exports", methods=["GET"])
def api_list_exports():
    """列出导出文件"""
    return jsonify({"exports": ExportService.list_exports()})


@admin_bp.route("/api/exports", methods=["POST"])
def api_create_export():
    """创建导出"""
    payload = request.get_json(force=True, silent=True) or {}
    fmt = payload.get("format", "csv")
    data = _get_data_provider()
    traceback = data.get("traceback", [])

    try:
        if fmt == "csv":
            path = ExportService.export_traceback_to_csv(traceback)
        elif fmt == "json":
            path = ExportService.export_to_json(data)
        elif fmt == "report":
            service = StatsService(traceback)
            path = ExportService.export_summary_report(service.summary_report())
        else:
            return jsonify({"error": f"不支持的导出格式: {fmt}"}), 400

        fname = os.path.basename(path)
        fsize = os.path.getsize(path)
        return jsonify({"message": "导出成功", "file": fname, "size": fsize, "path": path})
    except Exception as e:
        logger.exception("导出失败")
        return jsonify({"error": str(e)}), 500


@admin_bp.route("/api/exports/clear", methods=["POST"])
def api_clear_exports():
    """清空导出目录"""
    count = ExportService.clear_exports()
    return jsonify({"message": f"已移除 {count} 个导出文件", "count": count})


@admin_bp.route("/api/cache/clear", methods=["POST"])
def api_clear_cache():
    """清理缓存"""
    cache_type = (request.get_json(force=True, silent=True) or {}).get("type", "all")
    if cache_type in ("memory", "all"):
        memory_cache.clear()
    if cache_type in ("file", "all"):
        file_cache.clear()

    from app import clear_data_cache
    clear_data_cache()

    logger.info(f"缓存已清理 (type={cache_type})")
    return jsonify({"message": "缓存已清理", "type": cache_type})


# 后台任务追踪
_BG_TASKS = {}
_BG_TASKS_LOCK = threading.Lock()


def _run_bg_task(task_id, target, **kwargs):
    """在后台线程中执行任务并记录结果"""
    try:
        result = target(**kwargs)
        with _BG_TASKS_LOCK:
            _BG_TASKS[task_id] = {"status": "done", "result": result}
    except Exception as e:
        logger.exception(f"后台任务 {task_id} 失败")
        with _BG_TASKS_LOCK:
            _BG_TASKS[task_id] = {"status": "error", "error": str(e)}


@admin_bp.route("/api/tasks/<task_id>")
def api_task_status(task_id):
    """查询后台任务状态"""
    with _BG_TASKS_LOCK:
        task = _BG_TASKS.get(task_id)
    if task is None:
        return jsonify({"status": "unknown", "task_id": task_id}), 404
    return jsonify({"task_id": task_id, **task})


@admin_bp.route("/api/scan")
def api_scan():
    """扫描数据目录"""
    if not os.path.exists(POEM_JSON_DIR):
        return jsonify({"error": f"数据目录不存在: {POEM_JSON_DIR}"}), 404

    files = [f for f in os.listdir(POEM_JSON_DIR)
             if f.endswith((".json", ".txt"))]
    total_poems = 0
    total_units = 0
    file_list = []

    for fname in sorted(files):
        fpath = os.path.join(POEM_JSON_DIR, fname)
        size_kb = round(os.path.getsize(fpath) / 1024, 1)
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
            poems = data.get("诗歌集", [data]) if isinstance(data, dict) else data
            pcount = len(poems)
            ucount = sum(len(p.get("分析单元", [])) for p in poems)
            total_poems += pcount
            total_units += ucount
            file_list.append({
                "name": fname, "size_kb": size_kb,
                "poems": pcount, "units": ucount,
            })
        except Exception as e:
            file_list.append({
                "name": fname, "size_kb": size_kb,
                "poems": 0, "units": 0, "error": str(e),
            })

    return jsonify({
        "files": file_list,
        "total_poems": total_poems,
        "total_units": total_units,
        "file_count": len(file_list),
    })


@admin_bp.route("/api/rag/check")
def api_rag_check():
    """检查向量库状态"""
    import chromadb
    if not os.path.exists(RAG_DB_DIR):
        return jsonify({"exists": False, "error": "向量库不存在，请先构建"})

    try:
        client = chromadb.PersistentClient(path=RAG_DB_DIR)
        collection = client.get_collection(name="poems")
        count = collection.count()
        samples = []
        if count > 0:
            sample = collection.peek()
            for i, doc in enumerate(sample["documents"][:5]):
                meta = sample["metadatas"][i]
                samples.append({
                    "title": meta.get("标题", ""),
                    "author": meta.get("作者", ""),
                    "length": len(doc),
                })
        return jsonify({
            "exists": True,
            "path": RAG_DB_DIR,
            "collection": "poems",
            "vector_count": count,
            "samples": samples,
        })
    except Exception as e:
        return jsonify({"exists": True, "error": str(e)})


@admin_bp.route("/api/rag/build", methods=["POST"])
def api_rag_build():
    """构建向量库（后台运行）"""
    task_id = "rag_build_" + uuid.uuid4().hex[:8]
    with _BG_TASKS_LOCK:
        _BG_TASKS[task_id] = {"status": "running"}

    def _build():
        from build_rag import main as build_main
        build_main()

    t = threading.Thread(target=_run_bg_task, args=(task_id, _build))
    t.daemon = True
    t.start()

    return jsonify({
        "message": "向量库构建任务已启动",
        "task_id": task_id,
    })


@admin_bp.route("/api/test", methods=["POST"])
def api_run_tests():
    """运行单元测试（后台运行）"""
    task_id = "test_" + uuid.uuid4().hex[:8]
    with _BG_TASKS_LOCK:
        _BG_TASKS[task_id] = {"status": "running"}

    def _run():
        test_path = os.path.join(BASE_DIR, "tests")
        result = subprocess.run(
            [sys.executable, "-m", "pytest", test_path, "-v"],
            cwd=BASE_DIR,
            capture_output=True, text=True, timeout=300,
        )
        output = result.stdout
        if result.stderr:
            output += "\n--- stderr ---\n" + result.stderr
        return {
            "returncode": result.returncode,
            "output": output,
            "passed": result.returncode == 0,
        }

    t = threading.Thread(target=_run_bg_task, args=(task_id, _run))
    t.daemon = True
    t.start()

    return jsonify({
        "message": "测试任务已启动",
        "task_id": task_id,
    })


@admin_bp.route("/api/refresh", methods=["POST"])
def api_refresh_data():
    """刷新数据缓存"""
    from app import clear_data_cache, get_data
    clear_data_cache()
    data = get_data()
    return jsonify({
        "message": "数据已刷新",
        "total_poems": data.get("total_poems", 0),
        "total_images": len(data.get("traceback", [])),
    })
