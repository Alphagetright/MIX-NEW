# -*- coding: utf-8 -*-
"""
Schema 引擎 — 表头校验 / 列映射验证 / 输出格式校验 / 模板管理
"""
import json, os
from . import config_loader


def validate_headers(headers: list) -> tuple[bool, str]:
    """校验用户表头定义是否合法"""
    if not headers or not isinstance(headers, list):
        return False, "表头不能为空"
    names = set()
    for i, h in enumerate(headers):
        name = h.get("name", "").strip()
        if not name:
            return False, f"第{i+1}列表头名为空"
        if name in names:
            return False, f"表头名重复: {name}"
        names.add(name)
        if any(c in name for c in [',', '"', "'", '\n', '\t']):
            return False, f"表头名含非法字符: {name}"
    return True, ""


def validate_output(sample_row: dict, column_mapping: list) -> tuple[bool, list]:
    """校验 AI 输出的示例行是否符合列映射定义"""
    issues = []
    for col in column_mapping:
        field = col.get("field")
        header = col.get("header", field)
        dtype = col.get("data_type", "string")

        # sample_row 的 key 可能是 field（英文）或 header（中文），两者都尝试
        if field in sample_row:
            val = sample_row[field]
        elif header in sample_row:
            val = sample_row[header]
        else:
            issues.append(f"缺失字段: {header}")
            continue

        try:
            if dtype == "int":
                int(val)
            elif dtype == "float":
                float(val)
            elif dtype == "bool":
                if not isinstance(val, bool):
                    issues.append(f"{header} 应为布尔值")
            elif dtype == "enum":
                enum_vals = col.get("enum_values", [])
                if enum_vals and val not in enum_vals:
                    issues.append(f"{header} 值'{val}'不在枚举{enum_vals}中")
            elif dtype == "string":
                if not isinstance(val, str):
                    issues.append(f"{header} 应为字符串")
        except (ValueError, TypeError):
            issues.append(f"{header} 类型错误: 期望{dtype}，实际{type(val).__name__}")

    return len(issues) == 0, issues


def rows_to_csv(rows: list, column_mapping: list) -> str:
    """将结果行列表转换为 CSV 字符串"""
    headers = [col["header"] for col in column_mapping]
    fields = [col["field"] for col in column_mapping]
    lines = [",".join(f'"{h}"' for h in headers)]
    for row in rows:
        if not row:
            continue
        vals = []
        for f in fields:
            v = row.get(f, "")
            v = str(v).replace('"', '""')
            vals.append(f'"{v}"')
        lines.append(",".join(vals))
    return "\n".join(lines)


def save_template(name: str, data: dict) -> str:
    """保存用户模板到 user_templates/"""
    tmpl_dir = config_loader.get("TEMPLATES_DIR")
    if not tmpl_dir:
        return ""
    path = os.path.join(tmpl_dir, f"{name}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return path


def load_template(name: str) -> dict | None:
    """加载用户模板"""
    tmpl_dir = config_loader.get("TEMPLATES_DIR")
    if not tmpl_dir:
        return None
    path = os.path.join(tmpl_dir, f"{name}.json")
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def list_templates() -> list:
    """列出所有用户模板"""
    tmpl_dir = config_loader.get("TEMPLATES_DIR")
    if not tmpl_dir or not os.path.exists(tmpl_dir):
        return []
    return sorted(
        [f.replace(".json", "") for f in os.listdir(tmpl_dir) if f.endswith(".json")]
    )
