# -*- coding: utf-8 -*-
"""
请求校验模块
"""
import re
from typing import Optional

from errors import ValidationError


def validate_question(question: Optional[str]) -> str:
    """校验用户提问"""
    if not question:
        raise ValidationError("问题不能为空", field="question")
    q = question.strip()
    if len(q) > 2000:
        raise ValidationError("问题长度不能超过 2000 字符", field="question")
    if len(q) < 1:
        raise ValidationError("问题不能为空", field="question")
    return q


def validate_item(item: Optional[dict]) -> dict:
    """校验意象解析请求中的 item"""
    if not item or not isinstance(item, dict):
        raise ValidationError("缺少诗歌意象数据", field="item")
    i = item.get("文本") or item.get("txt") or ""
    line = item.get("line") or ""
    if not i and not line:
        raise ValidationError("缺少诗句或意象上下文", field="item")
    return item


def validate_history(history: Optional[list]) -> list:
    """校验对话历史"""
    if not history or not isinstance(history, list):
        return []
    valid = []
    for h in history:
        if isinstance(h, dict) and h.get("role") in ("user", "assistant") and h.get("content"):
            valid.append({
                "role": h["role"],
                "content": str(h["content"])[:5000]
            })
    return valid


def validate_poem_id(poem_id: Optional[str]) -> str:
    """校验诗歌编号"""
    if not poem_id or not poem_id.strip():
        raise ValidationError("诗歌编号不能为空", field="poem_id")
    pid = poem_id.strip()
    if not re.match(r"^P?\d{2,6}$", pid):
        raise ValidationError(f"诗歌编号格式不正确: {pid}", field="poem_id")
    return pid


def validate_filename(filename: Optional[str], allowed_exts=None) -> str:
    """校验导出文件名"""
    if not filename or not filename.strip():
        return "export"
    allowed = allowed_exts or [".csv", ".json", ".xlsx"]
    name = filename.strip()
    has_ext = any(name.lower().endswith(ext) for ext in allowed)
    if not has_ext:
        raise ValidationError(
            f"文件名必须包含合法后缀 ({', '.join(allowed)})",
            field="filename"
        )
    if re.search(r"[\\/:*?\"<>|]", name):
        raise ValidationError("文件名包含非法字符", field="filename")
    return name


def sanitize_html(text: str) -> str:
    """简单的 HTML 转义"""
    if not text:
        return ""
    return (text.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;")
                .replace("'", "&#39;"))
