# -*- coding: utf-8 -*-
"""
Meta-Prompting 引擎 — 三段式智能流水线核心

阶段:
  Prompt 0 — 自然语言 → 结构化表头 (Entry B)
  Prompt 1 — 表头 → 专用提示词 + 列映射 + 示例行 + output_schema
  Quality  — 质量验证（试跑验证）

所有 meta-prompt 模板文件存放在 prompts/ 目录，
不硬编码在代码中 —— 用户可以查看和编辑。
"""
import json
from . import config_loader
from .llm_client import call_llm


def parse_requirement(requirement_text: str, sid: str = "") -> dict | None:
    """
    Prompt 0: 用户用自然语言描述需求 → AI 返回结构化表头建议

    输入: "我想分析李白诗里的自然意象和情感倾向"
    输出: {"headers": [{"name": "意象名称", "desc": "..."}, ...], "suggested_name": "李白自然意象情感分析"}
    """
    system_prompt = config_loader.load_prompt("meta_requirement_parser")
    if not system_prompt:
        return None

    user_prompt = f"用户的数据分析需求描述：\n{requirement_text}\n\n请按上述规则输出表头设计。"
    parsed, raw_text = call_llm(system_prompt, user_prompt, return_raw=True)
    if sid:
        from . import persistence
        model = config_loader.get("MODEL_NAME") or "unknown"
        persistence.save_conversation(sid, {"编号": "", "标题": "Meta-Parse", "作者": ""},
                                      system_prompt, user_prompt, raw_text, parsed, model,
                                      len(raw_text) if raw_text else 0)
    return parsed


def design_schema(headers: list, sid: str = "") -> dict | None:
    """
    Prompt 1: 用户定义的表头列表 → AI 生成专用提示词 + 列映射 + 示例

    headers: [{"name": "意象名称", "desc": "诗歌中出现的自然意象"}, ...]
    输出: {
        "generated_prompt": "...(AI生成的system prompt)...",
        "column_mapping": [...],
        "sample_row": {...},
        "output_format": "strict_json",
        "analysis_notes": "...",
        "estimated_tokens_per_poem": 500
    }
    """
    system_prompt = config_loader.load_prompt("meta_schema_designer")
    if not system_prompt:
        return None

    # 格式化表头为可读文本
    headers_text = "\n".join(
        f"{i+1}. {h['name']}" + (f"（{h['desc']}）" if h.get('desc') else "")
        for i, h in enumerate(headers)
    )
    user_prompt = f"用户需要以下数据列：\n{headers_text}\n\n请按规则设计分析方案。"
    parsed, raw_text = call_llm(system_prompt, user_prompt, return_raw=True)
    if sid:
        from . import persistence
        model = config_loader.get("MODEL_NAME") or "unknown"
        persistence.save_conversation(sid, {"编号": "", "标题": "Meta-Design", "作者": ""},
                                      system_prompt, user_prompt, raw_text, parsed, model,
                                      len(raw_text) if raw_text else 0)
    return parsed


def quality_check(generated_prompt: str, sample_poems: list, column_mapping: list, sid: str = "") -> dict | None:
    """
    质量验证: 用生成的提示词试跑 sample_poems，检查输出是否符合 schema
    """
    system_prompt = config_loader.load_prompt("meta_quality_checker")
    if not system_prompt:
        return None

    # 先用 generated_prompt 批量试跑
    from .llm_client import call_llm_batch
    trial_results = call_llm_batch(generated_prompt, sample_poems)

    # 让 AI 评估结果质量
    user_prompt = json.dumps({
        "generated_prompt": generated_prompt,
        "column_mapping": column_mapping,
        "trial_results": trial_results
    }, ensure_ascii=False)

    parsed, raw_text = call_llm(system_prompt, user_prompt, return_raw=True)
    if sid:
        from . import persistence
        model = config_loader.get("MODEL_NAME") or "unknown"
        persistence.save_conversation(sid, {"编号": "", "标题": "Meta-Quality", "作者": ""},
                                      system_prompt, user_prompt, raw_text, parsed, model,
                                      len(raw_text) if raw_text else 0)
    if parsed:
        parsed["trial_results"] = trial_results  # 附带试跑原始数据
    return parsed
