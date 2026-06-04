# -*- coding: utf-8 -*-
"""预置标注模板库 — 12套模板的索引、匹配推荐和元数据管理"""
import os, json

from . import config_loader

# 所有预置模板的元数据
TEMPLATE_CATALOG = {
    # ── 6 种分析维度 ──
    "imagery_analysis": {
        "name": "意象分析",
        "category": "analysis_dimension",
        "description": "识别诗歌中的自然意象、人文意象，分析其象征意义与审美功能",
        "tags": ["意象", "物象", "象征", "意境"],
        "output_columns": ["意象名称", "意象类别", "出处句", "象征意义", "情感关联", "审美功能"],
        "template_file": "tmpl_imagery_analysis.txt"
    },
    "sentiment_analysis": {
        "name": "情感倾向分析",
        "category": "analysis_dimension",
        "description": "识别诗歌情感基调和情感变化，标注情感类型与强度",
        "tags": ["情感", "基调", "变化", "强度"],
        "output_columns": ["情感类型", "情感强度", "情感载体", "情感变化线索", "基调判断"],
        "template_file": "tmpl_sentiment_analysis.txt"
    },
    "rhetoric_analysis": {
        "name": "修辞手法分析",
        "category": "analysis_dimension",
        "description": "识别比喻、拟人、对仗、用典等修辞手法及其艺术效果",
        "tags": ["修辞", "比喻", "对仗", "用典", "拟人"],
        "output_columns": ["修辞手法", "出处句", "手法说明", "艺术效果", "使用频率"],
        "template_file": "tmpl_rhetoric_analysis.txt"
    },
    "prosody_analysis": {
        "name": "格律检测",
        "category": "analysis_dimension",
        "description": "检测平仄格律、押韵模式、对仗结构、节奏特点",
        "tags": ["格律", "平仄", "押韵", "对仗", "节奏"],
        "output_columns": ["诗体", "押韵字", "韵部", "平仄标注", "对仗位置", "格律评价"],
        "template_file": "tmpl_prosody_analysis.txt"
    },
    "theme_classification": {
        "name": "主题分类",
        "category": "analysis_dimension",
        "description": "按题材对诗歌进行多级分类标注，识别主题与子主题",
        "tags": ["主题", "题材", "分类", "标签"],
        "output_columns": ["一级主题", "二级主题", "主题关键词", "题材来源", "时代关联"],
        "template_file": "tmpl_theme_classification.txt"
    },
    "intertextual_analysis": {
        "name": "互文关联分析",
        "category": "analysis_dimension",
        "description": "识别诗歌中的化用、引用、呼应关系，建立文本间关联",
        "tags": ["互文", "化用", "引用", "呼应", "影响"],
        "output_columns": ["关联类型", "源文本", "目标句", "关联强度", "变异方式", "互文效果"],
        "template_file": "tmpl_intertextual_analysis.txt"
    },

    # ── 3 种综合维度 ──
    "gaokao_appreciation": {
        "name": "高考诗词鉴赏",
        "category": "comprehensive",
        "description": "按高考评分标准多维度赏析，输出结构化鉴赏报告",
        "tags": ["高考", "鉴赏", "考试", "评分标准"],
        "output_columns": ["内容理解", "语言赏析", "手法分析", "情感把握", "意境描述", "综合评价"],
        "template_file": "tmpl_gaokao_appreciation.txt"
    },
    "academic_paper": {
        "name": "学术论文辅助",
        "category": "comprehensive",
        "description": "生成学术研究所需的文献综述、文本细读和研究视角建议",
        "tags": ["学术", "论文", "文献", "研究"],
        "output_columns": ["研究视角", "文本细读", "前人评述要点", "创新切入点", "参考文献线索"],
        "template_file": "tmpl_academic_paper.txt"
    },
    "creative_writing": {
        "name": "创意写作启发",
        "category": "comprehensive",
        "description": "从诗歌中提取创作元素，为现代创意写作提供灵感素材",
        "tags": ["创作", "灵感", "改写", "续写"],
        "output_columns": ["创作元素", "现代转化方向", "意象借用方式", "情感基调适配", "叙事框架建议"],
        "template_file": "tmpl_creative_writing.txt"
    },

    # ── 3 种特殊场景 ──
    "dialect_detection": {
        "name": "方言入诗识别",
        "category": "special_scene",
        "description": "识别诗中可能存在的方言词汇、方言音韵和地域语言特征",
        "tags": ["方言", "地域", "音韵", "词汇"],
        "output_columns": ["可疑方言词", "所属方言区", "方言含义", "入诗概率", "学术依据"],
        "template_file": "tmpl_dialect_detection.txt"
    },
    "allusion_tracing": {
        "name": "用典溯源",
        "category": "special_scene",
        "description": "识别诗中用典，追溯典故出处，分析用典方式与深层意图",
        "tags": ["用典", "溯源", "出处", "意图"],
        "output_columns": ["典故内容", "原始出处", "用典方式", "化用程度", "意图分析", "读者认知门槛"],
        "template_file": "tmpl_allusion_tracing.txt"
    },
    "imagery_evolution": {
        "name": "意象演变追踪",
        "category": "special_scene",
        "description": "追踪特定意象在不同时代、不同诗人笔下的语义和情感演变",
        "tags": ["演变", "历时", "语义变化", "跨时代"],
        "output_columns": ["意象名称", "时代节点", "代表诗人", "语义内涵", "情感色彩", "演变趋势"],
        "template_file": "tmpl_imagery_evolution.txt"
    }
}


def list_all() -> list:
    """列出所有预置模板的元数据"""
    return [{"key": k, **v} for k, v in TEMPLATE_CATALOG.items()]


def list_by_category(category: str) -> list:
    return [{"key": k, **v} for k, v in TEMPLATE_CATALOG.items()
            if v.get("category") == category]


def get_meta(template_key: str) -> dict | None:
    t = TEMPLATE_CATALOG.get(template_key)
    if not t:
        return None
    return {"key": template_key, **t}


def search(keyword: str) -> list:
    kw = keyword.lower()
    results = []
    for k, v in TEMPLATE_CATALOG.items():
        if kw in v.get("name","") or kw in v.get("description","") or \
           any(kw in tag for tag in v.get("tags",[])):
            results.append({"key": k, **v})
    return results


def recommend(user_requirement: str) -> list:
    """根据用户需求文本推荐最匹配的模板，返回 Top-3"""
    req_lower = user_requirement.lower()
    scored = []
    for k, v in TEMPLATE_CATALOG.items():
        score = 0
        text = v.get("name","") + " " + v.get("description","") + " " + \
               " ".join(v.get("tags",[])) + " " + " ".join(v.get("output_columns",[]))
        for char in req_lower:
            if char in text:
                score += 1
        if score > 0:
            scored.append((score, k))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [{"key": k, "score": s, **TEMPLATE_CATALOG[k]} for s, k in scored[:3]]


def get_prompt_content(template_key: str) -> str | None:
    """加载预置模板的 prompt 文件内容"""
    meta = TEMPLATE_CATALOG.get(template_key)
    if not meta:
        return None
    prompts_dir = config_loader.get("PROMPTS_DIR") or \
                  os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "prompts")
    path = os.path.join(prompts_dir, meta["template_file"])
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def get_template_config(template_key: str) -> dict | None:
    """获取模板完整配置：元数据 + prompt内容 + 默认列映射schema"""
    meta = get_meta(template_key)
    if not meta:
        return None
    prompt = get_prompt_content(template_key)
    if not prompt:
        return None
    return {
        "meta": meta,
        "prompt": prompt,
        "default_headers": [
            {"name": col, "desc": ""} for col in meta.get("output_columns", [])
        ]
    }
