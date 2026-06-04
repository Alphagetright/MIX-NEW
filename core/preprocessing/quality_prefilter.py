# -*- coding: utf-8 -*-
"""质量预过滤 —— 文本质量预检"""

import re


class LengthFilter:
    """长度过滤器"""

    def __init__(self, min_chars=4, max_chars=100000):
        self.min_chars = min_chars
        self.max_chars = max_chars

    def accept(self, text):
        length = len(text)
        return self.min_chars <= length <= self.max_chars

    def filter(self, items):
        return [item for item in items if self.accept(item.get("text", "") if isinstance(item, dict) else item)]


class EmptyFilter:
    """空内容过滤器"""

    def is_empty(self, text):
        return not text or not text.strip()

    def is_blank(self, text):
        return not text.strip()

    def filter(self, items):
        return [item for item in items if not self.is_empty(str(item))]


class GibberishDetector:
    """乱码检测器"""

    def __init__(self, threshold=0.3):
        self.threshold = threshold

    def is_gibberish(self, text):
        if not text:
            return False
        char_checks = 0
        unusual = 0
        for ch in text:
            cp = ord(ch)
            if 0x4E00 <= cp <= 0x9FFF or 0x20 <= cp <= 0x7E:
                char_checks += 1
            elif cp > 0x7F:
                char_checks += 1
            else:
                unusual += 1
        if char_checks == 0:
            return True
        ratio = unusual / char_checks
        return ratio > self.threshold

    def filter(self, items):
        return [item for item in items if not self.is_gibberish(str(item))]


class EncodingQualityChecker:
    """编码质量检查"""

    def __init__(self):
        self._replacement_chars = ["�", "□", "?"]

    def check(self, text):
        for ch in self._replacement_chars:
            count = text.count(ch)
            if count > 0:
                return {"has_encoding_issues": True, "replacement_chars": count, "char": ch}
        return {"has_encoding_issues": False, "replacement_chars": 0}


class QualityPrefilter:
    """质量预过滤器"""

    def __init__(self):
        self.length = LengthFilter()
        self.empty = EmptyFilter()
        self.gibberish = GibberishDetector()
        self.encoding = EncodingQualityChecker()

    def prefilter(self, text):
        issues = []
        if self.empty.is_empty(text):
            issues.append({"type": "empty", "severity": "error", "message": "Text is empty"})
            return {"accepted": False, "issues": issues}
        if self.gibberish.is_gibberish(text):
            issues.append({"type": "gibberish", "severity": "warning", "message": "Text may be gibberish"})
        if not self.length.accept(text):
            issues.append({"type": "length", "severity": "warning", "message": f"Text length {len(text)} out of range"})
        encoding_issues = self.encoding.check(text)
        if encoding_issues["has_encoding_issues"]:
            issues.append({"type": "encoding", "severity": "warning", "message": f"Replacement chars found: {encoding_issues['replacement_chars']}"})
        return {"accepted": len([i for i in issues if i["severity"] == "error"]) == 0, "issues": issues}

    def filter_texts(self, texts):
        accepted = []
        rejected = []
        for text in texts:
            result = self.prefilter(text)
            if result["accepted"]:
                accepted.append(text)
            else:
                rejected.append({"text": text, "issues": result["issues"]})
        return {"accepted": accepted, "rejected": rejected}
