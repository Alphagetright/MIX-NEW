# -*- coding: utf-8 -*-
"""
CLI Ops LLM 客户端 — 零配置自动检测
====================================

自动检测 LLM 配置，优先级从高到低：
  1. 环境变量 TCO_LLM_API_URL / TCO_LLM_API_KEY / TCO_LLM_MODEL
  2. poem_lab 的 config.py（如果存在且配置了 MODEL_NAME）
  3. Claude Code settings.json 中的 DeepSeek API 配置
  4. 本地 LM Studio（localhost:1234）
  5. 本地 Ollama（localhost:11434）

支持两种调用模式：
  - Native function-calling（OpenAI 兼容 API）
  - Prompt-based tool calling（fallback）
"""

import json
import uuid
import os
import sys
import requests


# ============================================================================
# 配置缓存
# ============================================================================

_config_cache: dict | None = None


def _detect_config() -> dict:
    """
    自动检测 LLM 配置。只运行一次，结果缓存。

    返回:
        {"api_url": "...", "api_key": "...", "model": "...", "source": "..."}
    """
    global _config_cache
    if _config_cache is not None:
        return _config_cache

    # ── 1. 环境变量（最高优先级） ──
    env_url = os.environ.get("TCO_LLM_API_URL", "")
    env_key = os.environ.get("TCO_LLM_API_KEY", "")
    env_model = os.environ.get("TCO_LLM_MODEL", "")
    if env_url and env_key:
        _config_cache = {
            "api_url": env_url,
            "api_key": env_key,
            "model": env_model or "auto",
            "source": "env:TCO_LLM_*",
        }
        return _config_cache

    # ── 2. poem_lab config ──
    try:
        poem_lab_dir = os.path.join(os.path.dirname(__file__), "..", "poem_lab")
        if poem_lab_dir not in sys.path:
            sys.path.insert(0, poem_lab_dir)
        from lib import config_loader
        poem_url = config_loader.get("API_URL", "")
        poem_model = config_loader.get("MODEL_NAME", "")
        if poem_url and poem_model:
            _config_cache = {
                "api_url": poem_url,
                "api_key": "not-needed",
                "model": poem_model,
                "source": "poem_lab/config.py",
            }
            return _config_cache
    except Exception:
        pass

    # ── 3. Claude Code settings.json → DeepSeek API ──
    try:
        settings_path = os.path.join(
            os.path.expanduser("~"), ".claude", "settings.json"
        )
        if os.path.exists(settings_path):
            with open(settings_path, "r", encoding="utf-8") as f:
                settings = json.load(f)
            env = settings.get("env", {})
            token = env.get("ANTHROPIC_AUTH_TOKEN", "")
            base = env.get("ANTHROPIC_BASE_URL", "")
            if token and "deepseek" in base.lower():
                _config_cache = {
                    "api_url": "https://api.deepseek.com/v1/chat/completions",
                    "api_key": token,
                    "model": "deepseek-chat",
                    "source": "claude settings (DeepSeek)",
                }
                return _config_cache
    except Exception:
        pass

    # ── 4. 本地 LM Studio ──
    try:
        r = requests.get("http://127.0.0.1:1234/v1/models", timeout=2)
        if r.status_code == 200:
            models = r.json().get("data", [])
            if models:
                _config_cache = {
                    "api_url": "http://127.0.0.1:1234/v1/chat/completions",
                    "api_key": "lm-studio",
                    "model": models[0]["id"],
                    "source": "LM Studio (localhost:1234)",
                }
                return _config_cache
    except Exception:
        pass

    # ── 5. 本地 Ollama ──
    try:
        r = requests.get("http://127.0.0.1:11434/api/tags", timeout=2)
        if r.status_code == 200:
            models = r.json().get("models", [])
            if models:
                _config_cache = {
                    "api_url": "http://127.0.0.1:11434/v1/chat/completions",
                    "api_key": "ollama",
                    "model": models[0]["name"],
                    "source": "Ollama (localhost:11434)",
                }
                return _config_cache
    except Exception:
        pass

    # ── 6. 默认 LM Studio（用户可能稍后启动） ──
    _config_cache = {
        "api_url": "http://127.0.0.1:1234/v1/chat/completions",
        "api_key": "lm-studio",
        "model": "auto",
        "source": "default (LM Studio)",
    }
    return _config_cache


def reset_config() -> None:
    """重置配置缓存（切换 LLM 后端时调用）"""
    global _config_cache
    _config_cache = None


def get_config_info() -> dict:
    """获取当前 LLM 配置信息（用于诊断）"""
    cfg = _detect_config()
    return {
        "api_url": cfg["api_url"],
        "model": cfg["model"],
        "source": cfg["source"],
    }


# ============================================================================
# 内部获取函数
# ============================================================================


def _get_api_url() -> str:
    return _detect_config()["api_url"]


def _get_api_key() -> str:
    return _detect_config()["api_key"]


def _get_model() -> str:
    """获取模型名。如果是 'auto'，尝试从 API 自动检测。"""
    model = _detect_config()["model"]
    if model and model != "auto":
        return model

    try:
        base = _get_api_url().replace("/chat/completions", "").replace("/v1", "")
        resp = requests.get(f"{base}/v1/models", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            models = data.get("data", [])
            if models:
                return models[0]["id"]
    except Exception:
        pass
    return "unknown"


# ============================================================================
# LLM 调用
# ============================================================================


def call_llm(
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.1,
    max_tokens: int = 4096,
) -> str:
    """
    非流式 LLM 调用，返回纯文本。

    参数:
        system_prompt: 系统提示词
        user_prompt: 用户提示词
        temperature: 温度参数
        max_tokens: 最大 token 数

    返回:
        str: LLM 响应文本，失败时返回空字符串
    """
    payload = {
        "model": _get_model(),
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False,
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {_get_api_key()}",
    }

    try:
        resp = requests.post(
            _get_api_url(),
            json=payload,
            headers=headers,
            timeout=120,
        )
        if resp.status_code != 200:
            return ""

        data = resp.json()
        if data.get("choices"):
            content = data["choices"][0].get("message", {}).get("content", "")
            return content.strip()
        return ""
    except Exception:
        return ""


def call_llm_messages(
    messages: list,
    temperature: float = 0.1,
    max_tokens: int = 4096,
) -> str:
    """
    多轮对话 LLM 调用 — 发送完整的 messages 数组。

    参数:
        messages: [{"role": "system", "content": "..."},
                   {"role": "user", "content": "..."},
                   {"role": "assistant", "content": "..."}, ...]
        temperature: 温度
        max_tokens: 最大 token 数

    返回:
        str: LLM 响应文本，失败时返回空字符串
    """
    payload = {
        "model": _get_model(),
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False,
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {_get_api_key()}",
    }

    try:
        resp = requests.post(
            _get_api_url(),
            json=payload,
            headers=headers,
            timeout=120,
        )
        if resp.status_code != 200:
            return ""

        data = resp.json()
        if data.get("choices"):
            content = data["choices"][0].get("message", {}).get("content", "")
            return content.strip()
        return ""
    except Exception:
        return ""


def call_llm_with_tools(
    system_prompt: str,
    user_prompt: str,
    tools: list,
    temperature: float = 0.1,
    max_tokens: int = 4096,
) -> dict | None:
    """
    带 function-calling 的 LLM 调用。

    参数:
        system_prompt: 系统提示词
        user_prompt: 用户提示词
        tools: OpenAI 格式的工具定义列表
        temperature: 温度
        max_tokens: 最大 token 数

    返回:
        dict | None: {"tool_name": "...", "tool_args": {...}} 或 {"text": "..."} 或无工具调用时返回文本
        失败时返回 None
    """
    payload = {
        "model": _get_model(),
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False,
        "tools": tools,
        "tool_choice": "auto",
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {_get_api_key()}",
    }

    try:
        resp = requests.post(
            _get_api_url(),
            json=payload,
            headers=headers,
            timeout=120,
        )
        if resp.status_code != 200:
            return None

        data = resp.json()
        if not data.get("choices"):
            return None

        message = data["choices"][0].get("message", {})

        # 检查是否有工具调用
        tool_calls = message.get("tool_calls", [])
        if tool_calls:
            tc = tool_calls[0]
            func = tc.get("function", {})
            try:
                args = json.loads(func.get("arguments", "{}"))
            except json.JSONDecodeError:
                args = {}
            return {
                "tool_name": func.get("name", ""),
                "tool_args": args,
            }

        # 纯文本响应
        content = message.get("content", "")
        if content:
            return {"text": content.strip()}

        return None
    except Exception:
        return None


# ============================================================================
# Prompt-based tool calling（兼容无原生 function-calling 的端点）
# ============================================================================


AGENT_SYSTEM_PROMPT = """You are a CLI operations agent controlling a Tang Poetry Data Operations System.

You have access to these tools. Call them by outputting ONLY a JSON object — no other text:

{"tool": "<tool_name>", "args": {<parameters>}}

When the task is DONE, output ONLY:

{"done": true, "summary": "<what was accomplished>"}

CRITICAL RULES:
- Output ONLY the JSON object. No markdown, no explanations, no code blocks.
- Call ONE tool per response.
- After seeing a result, immediately decide: call another tool OR output done.
- Use EXACT tool names and parameter names from the list below.
- For boolean flags, use JSON true/false.
- If a tool fails, try a different approach or output done with the error.

{TOOLS}

Remember: ONLY output {"tool": ...} or {"done": true, ...}. Nothing else."""  # noqa: E501


def build_agent_prompt(tools_desc: str, task: str) -> tuple:
    """构建 agent 的 system + user prompt"""
    system = AGENT_SYSTEM_PROMPT.replace("{TOOLS}", tools_desc)
    user = f"Task: {task}"
    return system, user


def parse_agent_response(text: str) -> dict | None:
    """
    解析 LLM 响应，提取 JSON 指令。多策略鲁棒解析。

    返回:
        {"tool": "...", "args": {...}}  — 需要执行工具
        {"done": True, "summary": "..."}  — 任务完成
        None  — 解析失败
    """
    if not text:
        return None

    import re

    # Strategy 1: Direct JSON parse (try whole text first)
    cleaned = text.strip()
    try:
        result = json.loads(cleaned)
        if isinstance(result, dict) and ("tool" in result or "done" in result):
            return result
    except json.JSONDecodeError:
        pass

    # Strategy 2: Extract from markdown code blocks (```json ... ``` or ``` ... ```)
    for pattern in [r'```json\s*\n?(.*?)\n?```', r'```\s*\n?(.*?)\n?```']:
        m = re.search(pattern, cleaned, re.DOTALL)
        if m:
            try:
                result = json.loads(m.group(1).strip())
                if isinstance(result, dict) and ("tool" in result or "done" in result):
                    return result
            except json.JSONDecodeError:
                continue

    # Strategy 3: Find JSON-like objects with tool/done keys using balanced braces
    for m in re.finditer(r'\{', cleaned):
        start = m.start()
        depth = 0
        end = start
        for i, ch in enumerate(cleaned[start:], start):
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        candidate = cleaned[start:end]
        try:
            result = json.loads(candidate)
            if isinstance(result, dict) and ("tool" in result or "done" in result):
                return result
        except json.JSONDecodeError:
            continue

    # Strategy 4: Last resort — look for "tool" or "done" keywords and try to extract
    m = re.search(r'\{\s*"(?:tool|done)"\s*[:\}]', cleaned)
    if m:
        # Try to extract from that point using brace matching
        start = m.start()
        depth = 0
        for i, ch in enumerate(cleaned[start:], start):
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    try:
                        result = json.loads(cleaned[start:i+1])
                        if isinstance(result, dict):
                            return result
                    except json.JSONDecodeError:
                        pass
                    break

    return None
