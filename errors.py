# -*- coding: utf-8 -*-
"""
统一异常处理模块
"""
import json
from flask import Response, jsonify


class AppError(Exception):
    """应用基础异常"""

    def __init__(self, message: str, status_code: int = 400, details: dict = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details or {}


class DataNotFoundError(AppError):
    """数据未找到"""

    def __init__(self, message="未找到相关数据", details=None):
        super().__init__(message, status_code=404, details=details)


class EmbeddingError(AppError):
    """向量化服务异常"""

    def __init__(self, message="向量化服务请求失败", details=None):
        super().__init__(message, status_code=502, details=details)


class LLMError(AppError):
    """大模型服务异常"""

    def __init__(self, message="大模型服务请求失败", details=None):
        super().__init__(message, status_code=502, details=details)


class ValidationError(AppError):
    """输入校验异常"""

    def __init__(self, message="输入参数校验失败", field=None, details=None):
        d = details or {}
        if field:
            d["field"] = field
        super().__init__(message, status_code=422, details=d)


class CacheError(AppError):
    """缓存异常"""

    def __init__(self, message="缓存操作失败", details=None):
        super().__init__(message, status_code=500, details=details)


class ExportError(AppError):
    """导出异常"""

    def __init__(self, message="数据导出失败", details=None):
        super().__init__(message, status_code=500, details=details)


def sse_error(message: str) -> str:
    """生成 SSE 格式错误消息"""
    return f"data: {json.dumps({'type': 'error', 'message': message}, ensure_ascii=False)}\n\n"


def json_error_response(error: AppError) -> Response:
    """将 AppError 转为 Flask JSON 响应"""
    return jsonify({
        "error": {
            "message": error.message,
            "type": type(error).__name__,
            "details": error.details,
        }
    }), error.status_code


def register_error_handlers(app):
    """在 Flask app 上注册统一异常处理器"""

    @app.errorhandler(AppError)
    def handle_app_error(error):
        return json_error_response(error)

    @app.errorhandler(400)
    def handle_bad_request(e):
        return jsonify({
            "error": {"message": "请求格式不正确", "type": "BadRequest"}
        }), 400

    @app.errorhandler(404)
    def handle_not_found(e):
        return jsonify({
            "error": {"message": "请求的资源不存在", "type": "NotFound"}
        }), 404

    @app.errorhandler(405)
    def handle_method_not_allowed(e):
        return jsonify({
            "error": {"message": "请求方法不允许", "type": "MethodNotAllowed"}
        }), 405

    @app.errorhandler(500)
    def handle_internal_error(e):
        return jsonify({
            "error": {"message": "服务器内部错误", "type": "InternalError"}
        }), 500

    return app
