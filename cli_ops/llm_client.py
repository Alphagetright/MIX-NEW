# -*- coding: utf-8 -*-
"""
CLI Ops LLM 客户端
==================
为 Agent Loop 提供 LLM 调用能力。

支持两种模式：
  1. Native function-calling（OpenAI 兼容 API，如 DeepSeek /v1）
  2. Prompt-based tool calling（适用于 Anthropic 兼容端点）

配置方式（环境变量，优先级从高到低）：
  TCO_LLM_API_URL  — LLM API 端点
  TCO_LLM_API_KEY  — API 密钥
  TCO_LLM_MODEL    — 模型名称

默认值：
  API_URL  → http://127.0.0.1:1234/v1/chat/completions (LM Studio 本地)
  API_KEY  → "lm-studio" (LM Studio 默认)
  MODEL    → 自动检测（调用 /models 端点）
"""

import json
import uuid
import os
import requests


# ============================================================================
# 配置
# ============================================================================


def _get_api_url() -> str:
    return os.environ.get(
        "TCO_LLM_API_URL",
        "http://127.0.0.1:1234/v1/chat/completions",
    )


def _get_api_key() -> str:
    return os.environ.get("TCO_LLM_API_KEY", "lm-studio")


def _get_model() -> str:
    """获取模型名，优先环境变量，否则自动检测"""
    env_model = os.environ.get("TCO_LLM_MODEL", "")
    if env_model:
        return env_model

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
