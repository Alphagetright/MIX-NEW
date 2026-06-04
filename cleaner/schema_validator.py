# -*- coding: utf-8 -*-
"""
Schema校验模块 — 诗歌JSON结构严格验证
"""

import os, json, re
from typing import Any, Dict, List, Optional, Tuple

from .config import REQUIRED_POEM_FIELDS, CATEGORY_NAME_MAP, VALIDATION_STRICT_MODE, DIMENSION_KEYS
from .logger import get_logger
from .models import ValidationResult

logger = get_logger("schema_validator")

POEM_SCHEMA = {
    "required_fields": ["诗歌编号", "标题", "作者"],
    "optional_fields": ["朝代", "分类标签", "体裁", "原文"],
    "array_fields": ["诗行", "分析单元"],
    "analysis_unit_fields": {
        "required": ["文本"],
        "recommended": ["是否意象", "词性", "感知通道", "情感类别", "子类编码",
                        "素材类型", "指涉来源", "表现功能", "结构功能组"],
        "optional": ["行内位置", "内部结构", "文化流通性", "跨文化性", "认知强度",
                     "核心意象", "情感极性", "情感置信度", "大类编码"],
    },
    "valid_major_codes": ["1", "2", "3"],
    "valid_sub_codes": ["1-1", "1-2", "1-3", "1-4", "2-1", "2-2", "2-3", "3-1", "3-2", "3-3", "3-4"],
    "valid_imagery_flag": ["0", "1"],
}


class SchemaValidator:
    def __init__(self, strict: bool = None):
        self._strict = strict if strict is not None else VALIDATION_STRICT_MODE

    def validate_poem(self, poem: Dict[str, Any]) -> ValidationResult:
        result = ValidationResult()
        if not isinstance(poem, dict):
            result.is_valid = False; result.issues.append("数据不是dict类型")
            result.issue_count = 1; return result
        for field in POEM_SCHEMA["required_fields"]:
            if field in poem:
                result.required_fields_present.append(field)
                if not isinstance(poem[field], str):
                    result.issues.append(f"类型错误 [{field}]: 期望str")
            else:
                result.required_fields_missing.append(field)
                result.issues.append(f"缺少字段: {field}")
        for field in POEM_SCHEMA["array_fields"]:
            if field in poem and not isinstance(poem[field], list):
                result.issues.append(f"类型错误 [{field}]: 期望list")
        units = poem.get("分析单元", [])
        if isinstance(units, list):
            valid, invalid, issues = self._validate_units(units)
            result.issues.extend(issues)
            result.imagery_count = sum(1 for u in units if isinstance(u, dict) and str(u.get("是否意象", "0")) == "1")
        result.poem_count = 1; result.is_valid = len(result.issues) == 0
        result.issue_count = len(result.issues); return result

    def _validate_units(self, units: List[Dict]) -> Tuple[int, int, List[str]]:
        valid = 0; invalid = 0; issues = []
        for i, unit in enumerate(units):
            if not isinstance(unit, dict):
                invalid += 1; issues.append(f"单元[{i}]不是dict"); continue
            text = unit.get("文本", "")
            if not text or not str(text).strip():
                issues.append(f"单元[{i}]缺少文本")
            if "是否意象" in unit and str(unit["是否意象"]).strip() not in POEM_SCHEMA["valid_imagery_flag"]:
                issues.append(f"单元[{i}]是否意象值非法")
            if "子类编码" in unit:
                code = str(unit["子类编码"]).strip()
                if code and code not in POEM_SCHEMA["valid_sub_codes"]:
                    issues.append(f"单元[{i}]子类编码未知: {code}")
            if self._strict:
                for f in POEM_SCHEMA["analysis_unit_fields"]["recommended"]:
                    if f not in unit or not str(unit[f]).strip():
                        issues.append(f"单元[{i}]缺少推荐字段: {f}")
            valid += 1
            if len(issues) >= 200: return valid, invalid, issues
        return valid, invalid, issues

    def validate_file(self, file_path: str) -> ValidationResult:
        from .preprocessor import safe_parse_json, extract_poems
        result = ValidationResult(file_path=file_path)
        data, errs = safe_parse_json(file_path)
        if data is None:
            result.is_valid = False; result.issues = errs; result.issue_count = len(errs); return result
        poems = extract_poems(data)
        for poem in poems:
            pr = self.validate_poem(poem)
            result.poem_count += 1; result.imagery_count += pr.imagery_count
            if not pr.is_valid:
                result.issues.extend(pr.issues)
                result.required_fields_missing.extend(pr.required_fields_missing)
        result.is_valid = len(result.issues) == 0; result.issue_count = len(result.issues)
        return result

    def validate_directory(self, directory: str = None) -> Dict[str, Any]:
        from .config import DATA_DIR
        from .utils import list_files
        if directory is None: directory = DATA_DIR
        files = list_files(directory, extensions=[".json", ".txt"], recursive=True)
        results = []; total_valid = 0; total_invalid = 0
        all_issues = []; total_poems = 0; total_imagery = 0
        for fp in files:
            r = self.validate_file(fp); results.append(r)
            if r.is_valid: total_valid += 1
            else: total_invalid += 1
            total_poems += r.poem_count; total_imagery += r.imagery_count
            all_issues.extend(r.issues[:20])
        missing_stats: Dict[str, int] = {}
        for r in results:
            for f in r.required_fields_missing: missing_stats[f] = missing_stats.get(f, 0) + 1
        return {"total_files": len(files), "valid_files": total_valid, "invalid_files": total_invalid,
                "total_poems": total_poems, "total_imagery": total_imagery,
                "total_issues": len(all_issues),
                "top_issues": sorted(missing_stats.items(), key=lambda x: x[1], reverse=True),
                "sample_issues": all_issues[:20]}


def quick_validate(file_path: str) -> Tuple[bool, List[str]]:
    validator = SchemaValidator(strict=False); r = validator.validate_file(file_path)
    return r.is_valid, r.issues[:10]


class FieldValidator:
    """单个字段的格式校验器"""

    @staticmethod
    def validate_poem_id(value: str) -> Tuple[bool, str]:
        if not value or not value.strip(): return False, "诗歌编号为空"
        if not re.match(r"^P?\d+", value.strip()): return False, f"编号格式异常: {value}"
        return True, ""

    @staticmethod
    def validate_title(value: str) -> Tuple[bool, str]:
        if not value or not value.strip(): return False, "标题为空"
        if len(value) > 200: return False, f"标题过长({len(value)}字)"
        return True, ""

    @staticmethod
    def validate_author(value: str) -> Tuple[bool, str]:
        if not value or not value.strip(): return False, "作者为空"
        if len(value) > 50: return False, f"作者名过长({len(value)}字)"
        if not any("一" <= c <= "鿿" or c.isalpha() for c in value):
            return False, f"作者名无有效字符: {value}"
        return True, ""

    @staticmethod
    def validate_emotion_polarity(value: str) -> Tuple[bool, str]:
        valid = {"+", "-", "0", ""}
        if str(value).strip() not in valid: return False, f"情感极性非法: {value}"
        return True, ""

    @staticmethod
    def validate_dimension_values(data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        issues = []
        for key in DIMENSION_KEYS:
            val = str(data.get(key, "")).strip()
            if val and val != "None" and len(val) > 50:
                issues.append(f"{key}值过长: {val[:30]}...")
        return len(issues) == 0, issues

    @classmethod
    def validate_all_fields(cls, poem: Dict[str, Any]) -> Dict[str, Any]:
        results = {}
        for field, method in [("诗歌编号", cls.validate_poem_id), ("标题", cls.validate_title),
                               ("作者", cls.validate_author)]:
            value = poem.get(field, "")
            ok, msg = method(value)
            results[field] = {"value": str(value)[:50], "valid": ok, "message": msg}
        return results
