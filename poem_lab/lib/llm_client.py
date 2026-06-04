# -*- coding: utf-8 -*-
"""
LLM API 客户端 — 流式推理 + JSON 提取
Adapted from npwf_harvest_v28.py, generalized for meta-prompting pipeline.
"""
import json, re, uuid, requests
from . import config_loader

def _api_url():
    return config_loader.get("API_URL")

def _model_name():
    return config_loader.get("MODEL_NAME") or _detect_model()

def _detect_model():
    try:
        resp = requests.get(_api_url().replace("/chat/completions", "/models"), timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("data"):
                return data["data"][0]["id"]
    except Exception:
        pass
    return "unknown"


def call_llm(system_prompt: str, user_prompt: str, temperature: float = 0.1, return_raw: bool = False) -> dict | None | tuple:
    """
    单次 LLM 调用，流式接收，返回解析后的 JSON dict。
    适用于 meta-prompting 阶段（Prompt 0/1/quality check）。
    若 return_raw=True，返回 (parsed_dict, raw_text)。
    """
    payload = {
        "model": _model_name(),
        "messages": [
            {"role": "system", "content": system_prompt + f"\n\n[Cache_Buster: {uuid.uuid4().hex}]"},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": temperature,
        "max_tokens": 80000,
        "stream": True,
        "stream_options": {"include_usage": True}
    }
    headers = {"Content-Type": "application/json", "Connection": "close"}

    raw_text = ""
    with requests.Session() as session:
        try:
            resp = session.post(_api_url(), json=payload, headers=headers,
                               timeout=config_loader.get("TIMEOUT"), stream=True)
            if resp.status_code != 200:
                return (None, "") if return_raw else None

            for line in resp.iter_lines():
                if not line:
                    continue
                line_text = line.decode('utf-8')
                if line_text.startswith('data: '):
                    line_text = line_text[6:].strip()
                if line_text == "[DONE]":
                    break
                try:
                    chunk = json.loads(line_text)
                    if chunk.get('choices'):
                        delta = chunk['choices'][0].get('delta', {})
                        content = delta.get('content', '')
                        reasoning = delta.get('reasoning_content', '')
                        if content and not reasoning and '<think>' not in content:
                            raw_text += content
                except (json.JSONDecodeError, KeyError):
                    continue

        except Exception:
            return (None, raw_text) if return_raw else None

    parsed = _extract_json(raw_text)
    if return_raw:
        return parsed, raw_text
    return parsed


def call_llm_batch(system_prompt: str, poems: list, progress_callback=None) -> list:
    """
    批量 LLM 调用，每首诗独立请求。
    poems: [{"编号": "P01", "标题": "静夜思", "作者": "李白", "原文": "..."}, ...]
    返回: [{"编号": "P01", "标题": "静夜思", "分析结果": {...}}, ...]
    """
    results = []
    for i, poem in enumerate(poems):
        user_prompt = f"诗歌编号：{poem['编号']}\n标题：《{poem['标题']}》\n作者：{poem['作者']}\n原文：{poem['原文']}"
        parsed = call_llm(system_prompt, user_prompt)
        results.append({
            "编号": poem["编号"],
            "标题": poem["标题"],
            "作者": poem.get("作者", ""),
            "分析结果": parsed
        })
        if progress_callback:
            progress_callback(i + 1, len(poems), poem["编号"], parsed is not None)
    return results


def _extract_json(raw: str) -> dict | None:
    """多层 JSON 提取与修复"""
    # 去除 think 标签
    text = re.sub(r'<think>.*?</think>', '', raw, flags=re.DOTALL).strip()
    # 去除代码围栏
    text = re.sub(r'```(?:json)?\s*|```\s*', '', text).strip()

    start = text.find('{')
    end = text.rfind('}')
    if start == -1:
        return None

    json_str = text[start:end + 1]

    try:
        return json.loads(json_str, strict=False)
    except json.JSONDecodeError:
        pass

    # 二次修复
    try:
        json_str = re.sub(r'(?<!\\)\n(?=(?:[^"]*"[^"]*")*[^"]*$)', '', json_str)
        json_str = json_str.replace('\n', '\\n').replace('\t', '')
        repaired = re.sub(r'}\s*{', '},{', json_str)
        if not repaired.endswith('}'):
            repaired += "}"
        return json.loads(repaired, strict=False)
    except Exception:
        return None
