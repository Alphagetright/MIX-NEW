# -*- coding: utf-8 -*-
"""标注质量评分引擎 — 完整性、合规性、一致性三维评分"""
import json
from collections import Counter


def score_batch_results(results: list, column_mapping: list) -> dict:
    """对一批标注结果进行综合质量评分"""
    total = len(results)
    if total == 0:
        return {"overall": 0, "completeness": 0, "compliance": 0,
                "consistency": 0, "issues": ["无数据"]}

    completeness = _score_completeness(results, column_mapping)
    compliance = _score_compliance(results, column_mapping)
    consistency = _score_consistency(results, column_mapping)

    overall = round(completeness * 0.35 + compliance * 0.40 + consistency * 0.25)
    issues = _collect_issues(results, column_mapping)

    return {
        "overall": overall,
        "completeness": completeness,
        "compliance": compliance,
        "consistency": consistency,
        "total": total,
        "issues": issues,
        "suggestions": _generate_suggestions(completeness, compliance, consistency, issues)
    }


def _score_completeness(results: list, column_mapping: list) -> int:
    """评分：必填列的非空比例"""
    fields = [c.get("field") or c.get("header") for c in column_mapping]
    non_empty_counts = []
    for r in results:
        parsed = r.get("result") or r.get("分析结果") or {}
        if isinstance(parsed, dict):
            filled = sum(1 for f in fields if parsed.get(f) not in (None, "", "N/A", "无"))
            non_empty_counts.append(filled / len(fields) if fields else 0)
        else:
            non_empty_counts.append(0)
    avg = sum(non_empty_counts) / len(non_empty_counts) if non_empty_counts else 0
    return round(avg * 100)


def _score_compliance(results: list, column_mapping: list) -> int:
    """评分：枚举值和类型合规率"""
    total_checks = 0
    passed_checks = 0
    for r in results:
        parsed = r.get("result") or r.get("分析结果") or {}
        if not isinstance(parsed, dict):
            continue
        for col in column_mapping:
            field = col.get("field") or col.get("header")
            dtype = col.get("data_type", "string")
            val = parsed.get(field)
            if val is None or val == "":
                continue  # 空值不计入合规检查（已在完整性中计算）
            total_checks += 1
            try:
                if dtype == "int":
                    int(val)
                    passed_checks += 1
                elif dtype == "float":
                    float(val)
                    passed_checks += 1
                elif dtype == "bool":
                    if isinstance(val, bool) or str(val).lower() in ("true","false","yes","no"):
                        passed_checks += 1
                elif dtype == "enum":
                    enum_vals = col.get("enum_values", [])
                    if not enum_vals or val in enum_vals:
                        passed_checks += 1
                else:  # string
                    if isinstance(val, str):
                        passed_checks += 1
            except (ValueError, TypeError):
                pass
    return round(passed_checks / total_checks * 100) if total_checks > 0 else 100


def _score_consistency(results: list, column_mapping: list) -> int:
    """评分：同作者/同诗体标注结果的一致性"""
    by_author = {}
    for r in results:
        author = r.get("作者", "unknown")
        parsed = r.get("result") or r.get("分析结果") or {}
        if isinstance(parsed, dict):
            by_author.setdefault(author, []).append(parsed)

    if len(results) < 3 or len(by_author) == len(results):
        return 85  # 全散列，无法评估一致性，给基础分

    consistency_scores = []
    for author, parsed_list in by_author.items():
        if len(parsed_list) < 2:
            continue
        for col in column_mapping:
            field = col.get("field") or col.get("header")
            vals = [p.get(field) for p in parsed_list if p.get(field) not in (None, "")]
            if len(vals) >= 2:
                most_common_ratio = Counter(vals).most_common(1)[0][1] / len(vals)
                consistency_scores.append(most_common_ratio)

    avg = sum(consistency_scores) / len(consistency_scores) if consistency_scores else 0.5
    return round(avg * 100)


def _collect_issues(results: list, column_mapping: list) -> list:
    """收集所有质量问题"""
    issues = []
    for i, r in enumerate(results):
        parsed = r.get("result") or r.get("分析结果") or {}
        if not parsed or not isinstance(parsed, dict):
            issues.append(f"第{i+1}条：AI 未返回有效结果")
            continue
        for col in column_mapping:
            field = col.get("field") or col.get("header")
            if field not in parsed:
                issues.append(f"第{i+1}条：缺失字段 [{col.get('header', field)}]")
    return issues[:20]  # Top-20 防止过长


def _generate_suggestions(completeness: int, compliance: int, consistency: int, issues: list) -> list:
    suggestions = []
    if completeness < 70:
        suggestions.append("完整性偏低：建议检查提示词中的必填字段约束，或减小单次标注字段数")
    if compliance < 70:
        suggestions.append("合规性偏低：建议在提示词中增加枚举值示例和类型说明，强化 JSON schema 约束")
    if consistency < 60:
        suggestions.append("一致性偏低：建议在提示词中增加风格一致性要求，或对同作者诗集中标注")
    if not issues:
        suggestions.append("数据质量良好，无需调整")
    return suggestions
