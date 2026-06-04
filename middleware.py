# -*- coding: utf-8 -*-
"""
中间件模块 — 请求标识、计时、CORS、日志追踪
"""
import time
import uuid
import threading
from functools import wraps

from flask import request, g, jsonify

from config import BASE_DIR
from logger import get_logger

logger = get_logger("middleware")


# 请求标识

class RequestContext:
    """线程级请求上下文"""

    def __init__(self):
        self.request_id = None
        self.start_time = None
        self.client_ip = None
        self.endpoint = None
        self.method = None

    def init_from_flask(self):
        self.request_id = request.headers.get("X-Request-ID") or \
                          request.args.get("_rid") or \
                          uuid.uuid4().hex[:12]
        self.start_time = time.time()
        self.client_ip = request.remote_addr or "unknown"
        self.endpoint = request.endpoint or request.path
        self.method = request.method
        return self

    def elapsed(self):
        if self.start_time:
            return round((time.time() - self.start_time) * 1000, 2)
        return 0

    def to_dict(self):
        return {
            "request_id": self.request_id,
            "client_ip": self.client_ip,
            "endpoint": self.endpoint,
            "method": self.method,
            "elapsed_ms": self.elapsed(),
        }


_request_ctx = threading.local()


def get_request_ctx() -> RequestContext:
    if not hasattr(_request_ctx, "current"):
        _request_ctx.current = RequestContext()
    return _request_ctx.current


# 装饰器

def request_context_middleware(app):
    """为 Flask app 注册请求生命周期钩子"""

    @app.before_request
    def before_request():
        ctx = get_request_ctx()
        ctx.init_from_flask()
        g.request_id = ctx.request_id
        logger.info(f"[{ctx.request_id}] {ctx.method} {request.path} from {ctx.client_ip}")

    @app.after_request
    def after_request(response):
        ctx = get_request_ctx()
        elapsed = ctx.elapsed()
        status = response.status_code
        logger.info(f"[{ctx.request_id}] {status} ({elapsed}ms)")
        response.headers.set("X-Request-ID", ctx.request_id)
        response.headers.set("X-Response-Time", f"{elapsed}ms")
        return response

    return app


def cors_middleware(app, origins=None):
    """为 Flask app 添加 CORS 头"""
    if origins is None:
        origins = ["*"]

    @app.after_request
    def add_cors_headers(response):
        origin = request.headers.get("Origin", "")
        if "*" in origins or origin in origins:
            response.headers.set("Access-Control-Allow-Origin", origin)
            response.headers.set("Access-Control-Allow-Methods",
                                 "GET, POST, PUT, DELETE, OPTIONS")
            response.headers.set("Access-Control-Allow-Headers",
                                 "Content-Type, Authorization, X-Request-ID")
            response.headers.set("Access-Control-Allow-Credentials", "true")
        return response

    return app


def rate_limit(max_per_minute=60):
    """简易速率限制装饰器（进程内计数）"""
    records = {}

    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            now = time.time()
            ip = request.remote_addr or "unknown"
            window_start = now - 60
            if ip not in records:
                records[ip] = []
            records[ip] = [t for t in records[ip] if t > window_start]
            if len(records[ip]) >= max_per_minute:
                logger.warning(f"速率限制触发: {ip}")
                return jsonify({"error": "请求过于频繁，请稍后再试"}), 429
            records[ip].append(now)
            return f(*args, **kwargs)
        return wrapper

    return decorator


def timer(f):
    """函数执行计时装饰器"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = f(*args, **kwargs)
        elapsed = round((time.time() - start) * 1000, 2)
        logger.debug(f"{f.__name__} 执行耗时: {elapsed}ms")
        return result
    return wrapper


class PerformanceTracker:
    """性能追踪器——记录接口调用统计"""

    def __init__(self):
        self._lock = threading.Lock()
        self._stats = {}

    def record(self, endpoint: str, elapsed_ms: float, status: int):
        with self._lock:
            if endpoint not in self._stats:
                self._stats[endpoint] = {
                    "count": 0, "total_time": 0, "max_time": 0,
                    "min_time": float("inf"), "error_count": 0,
                }
            s = self._stats[endpoint]
            s["count"] += 1
            s["total_time"] += elapsed_ms
            s["max_time"] = max(s["max_time"], elapsed_ms)
            s["min_time"] = min(s["min_time"], elapsed_ms)
            if status >= 400:
                s["error_count"] += 1

    def summary(self):
        result = {}
        with self._lock:
            for ep, s in self._stats.items():
                avg = round(s["total_time"] / s["count"], 2) if s["count"] else 0
                err_rate = round(s["error_count"] / s["count"] * 100, 1) if s["count"] else 0
                result[ep] = {
                    "calls": s["count"],
                    "avg_ms": avg,
                    "max_ms": round(s["max_time"], 2),
                    "min_ms": round(s["min_time"], 2) if s["min_time"] != float("inf") else 0,
                    "errors": s["error_count"],
                    "error_rate_pct": err_rate,
                }
        return result

    def reset(self):
        with self._lock:
            self._stats.clear()


tracker = PerformanceTracker()
