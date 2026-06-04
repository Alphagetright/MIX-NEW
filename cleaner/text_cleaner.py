# -*- coding: utf-8 -*-
"""
文本清洗模块
============
针对中文古典文学数据的专项文本清洗功能。
包括繁简转换、标点规范化、异体字处理、特殊字符清理等。
"""

import re
from typing import Any, Dict, List, Optional, Tuple

from .logger import get_logger

logger = get_logger("text_cleaner")


class TextCleaner:
    """中文文本清洗器"""

    def __init__(self):
        self._replacements: Dict[str, str] = {}
        self._stats: Dict[str, int] = {"cleaned": 0, "fixed": 0, "warnings": 0}

    def normalize_punctuation(self, text: str) -> Tuple[str, int]:
        """
        标点符号规范化

        将英文标点替换为对应的中文标点。
        """
        mapping = {
            ",": "，", ".": "。", "?": "？", "!": "！",
            ";": "；", ":": "：", "(": "（", ")": "）",
            "[": "【", "]": "】", "<": "《", ">": "》",
        }
        count = 0
        for en, zh in mapping.items():
            new = text.replace(en, zh)
            if new != text:
                count += 1
                text = new
        return text, count

    def remove_control_chars(self, text: str) -> Tuple[str, int]:
        """移除控制字符"""
        cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
        count = len(text) - len(cleaned)
        return cleaned, count

    def normalize_whitespace_chinese(self, text: str) -> Tuple[str, int]:
        """
        中文文本空白规范化

        移除中文字符之间的多余空格，保留英文/数字间的空格。
        """
        count = 0
        result = []
        for i, char in enumerate(text):
            if char.isspace():
                prev_is_cjk = i > 0 and ("一" <= text[i - 1] <= "鿿")
                next_is_cjk = i < len(text) - 1 and ("一" <= text[i + 1] <= "鿿")
                if prev_is_cjk and next_is_cjk:
                    count += 1
                    continue
            result.append(char)
        return "".join(result), count

    def remove_special_characters(self, text: str) -> Tuple[str, int]:
        """移除不可见字符和零宽字符"""
        specials = ["​", "‌", "‍", "⁠", "⁡", "⁢", "⁣", "⁤", "‎", "‏", "﻿"]
        count = 0
        for char in specials:
            if char in text:
                count += text.count(char)
                text = text.replace(char, "")
        return text, count

    def normalize_newlines(self, text: str) -> Tuple[str, int]:
        """换行符标准化（\r\n → \n）"""
        cleaned = text.replace("\r\n", "\n").replace("\r", "\n")
        count = (len(text) - len(cleaned)) // 2 + text.count("\r") - cleaned.count("\r")
        return cleaned, count if count > 0 else 0

    def deduplicate_lines(self, text: str, max_consecutive: int = 3) -> Tuple[str, int]:
        """合并连续重复行"""
        lines = text.split("\n")
        result = []
        count = 0
        consecutive = 0
        last_line = None
        for line in lines:
            if line == last_line:
                consecutive += 1
                if consecutive <= max_consecutive:
                    result.append(line)
                else:
                    count += 1
            else:
                consecutive = 1
                last_line = line
                result.append(line)
        return "\n".join(result), count

    def full_clean(self, text: str) -> Tuple[str, Dict[str, int]]:
        """执行完整的文本清洗流水线"""
        results = {}
        text, results["control_chars"] = self.remove_control_chars(text)
        text, results["special_chars"] = self.remove_special_characters(text)
        text, results["newlines"] = self.normalize_newlines(text)
        text, results["punctuation"] = self.normalize_punctuation(text)
        text, results["whitespace"] = self.normalize_whitespace_chinese(text)
        self._stats["cleaned"] += 1
        self._stats["fixed"] += sum(results.values())
        return text, results

    def get_stats(self) -> Dict[str, int]:
        return dict(self._stats)

    def clean_file(self, file_path: str, output_path: str = "",
                   encoding: str = "utf-8") -> str:
        """对单个文件执行完整文本清洗"""
        with open(file_path, "r", encoding=encoding, errors="replace") as f:
            content = f.read()

        cleaned, stats = self.full_clean(content)

        if not output_path:
            output_path = file_path.rsplit(".", 1)[0] + "_cleaned.txt"

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(cleaned)

        logger.info(f"文本清洗: {file_path} ({sum(stats.values())}修复) -> {output_path}")
        return output_path


# ─── 独立函数 ───

def clean_chinese_text(text: str) -> str:
    cleaner = TextCleaner()
    result, _ = cleaner.full_clean(text)
    return result


def strip_markdown_formatting(text: str) -> str:
    """去除Markdown格式标记"""
    # 去除加粗/斜体
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    # 去除行内代码
    text = re.sub(r"`(.+?)`", r"\1", text)
    # 去除链接
    text = re.sub(r"\[(.+?)\]\(.+?\)", r"\1", text)
    # 去除标题标记
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    return text


def fix_comma_splices(text: str) -> Tuple[str, int]:
    """修复逗号拼接错误（中文逗号后缺少空格的地方合并）"""
    fixed = re.sub(r"，\s*，", "，", text)
    return fixed, len(text) - len(fixed) + (text.count("，，") - fixed.count("，，"))


def normalize_chinese_numbers(text: str) -> str:
    """将中文数字统一为阿拉伯数字（特定上下文）"""
    num_map = {"一": "1", "二": "2", "三": "3", "四": "4", "五": "5",
               "六": "6", "七": "7", "八": "8", "九": "9", "零": "0", "十": "10"}
    result = text
    for zh, ar in num_map.items():
        pattern = rf"第{zh}"
        if re.search(pattern, result):
            result = re.sub(pattern, f"第{ar}", result)
    return result


# ─── 扩展清洗功能 ───

class ChineseTextNormalizer:
    """中文文本标准化器"""

    FULL_TO_HALF = str.maketrans("０１２３４５６７８９ＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺａｂｃｄｅｆｇｈｉｊｋｌｍｎｏｐｑｒｓｔｕｖｗｘｙｚ",
                                  "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz")

    def __init__(self):
        self._stats = {"normalized": 0, "chars_fixed": 0}

    def fullwidth_to_halfwidth(self, text: str) -> Tuple[str, int]:
        """全角字符转半角"""
        original = text
        text = text.translate(self.FULL_TO_HALF)
        count = sum(1 for a, b in zip(original, text) if a != b)
        self._stats["chars_fixed"] += count
        return text, count

    def normalize_ellipsis(self, text: str) -> Tuple[str, int]:
        """省略号标准化 (... / 。。。 / ... → ……)"""
        count = 0
        for pat in ["\.\.\.", "。。。", "\.\.\.\."]:
            matches = list(re.finditer(pat, text))
            count += len(matches)
            text = re.sub(pat, "……", text)
        return text, count

    def normalize_dashes(self, text: str) -> Tuple[str, int]:
        """破折号标准化"""
        count = 0
        for pat in ["---", "--", "——", "—"]:
            if pat == "——": continue
            mc = len(re.findall(pat, text))
            count += mc; text = re.sub(pat, "——", text)
        return text, count

    def normalize_quotes_in_chinese(self, text: str) -> Tuple[str, int]:
        """中文引号标准化 (英文引号 → 中文引号)"""
        count = 0
        result = []; in_quote = False
        for char in text:
            if char == '"' and any("一" <= c <= "鿿" for c in text[max(0, len(result)-5):] if result):
                result.append("“" if not in_quote else "”")
                in_quote = not in_quote; count += 1
            elif char == "'" and any("一" <= c <= "鿿" for c in text[max(0, len(result)-5):] if result):
                result.append("'")
                count += 1
            else:
                result.append(char)
        return "".join(result), count

    def full_normalize(self, text: str) -> Tuple[str, Dict[str, int]]:
        """完整标准化"""
        results = {}
        text, results["fullwidth"] = self.fullwidth_to_halfwidth(text)
        text, results["ellipsis"] = self.normalize_ellipsis(text)
        text, results["dashes"] = self.normalize_dashes(text)
        text, results["quotes"] = self.normalize_quotes_in_chinese(text)
        self._stats["normalized"] += 1
        return text, results

    def get_stats(self) -> dict:
        return dict(self._stats)


def batch_clean_texts(texts: List[str]) -> List[Tuple[str, Dict[str, int]]]:
    """批量文本清洗"""
    cleaner = TextCleaner()
    normalizer = ChineseTextNormalizer()
    results = []
    for text in texts:
        text, _ = cleaner.full_clean(text)
        text, stats = normalizer.full_normalize(text)
        results.append((text, stats))
    return results


def clean_and_detect_issues(text: str) -> Dict[str, Any]:
    """清洗文本并报告发现的问题"""
    cleaner = TextCleaner()
    cleaned, cleaning_stats = cleaner.full_clean(text)
    issues = []
    if cleaning_stats.get("control_chars", 0) > 0:
        issues.append(f"发现{cleaning_stats['control_chars']}个控制字符")
    if cleaning_stats.get("special_chars", 0) > 0:
        issues.append(f"发现{cleaning_stats['special_chars']}个特殊字符")
    if cleaning_stats.get("punctuation", 0) > 0:
        issues.append(f"修复{cleaning_stats['punctuation']}处标点")
    return {"cleaned": cleaned, "stats": cleaning_stats, "issues": issues,
            "has_issues": len(issues) > 0}
