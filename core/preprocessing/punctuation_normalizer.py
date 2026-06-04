# -*- coding: utf-8 -*-
"""标点归一化 —— 中英文标点统一处理"""

import re


class ChinesePunctuationNormalizer:
    """中文标点标准化"""

    EN_TO_ZH = {
        ",": "，",
        ".": "。",
        "!": "！",
        "?": "？",
        ":": "：",
        ";": "；",
        "(": "（",
        ")": "）",
        "[": "【",
        "]": "】",
        "{": "｛",
        "}": "｝",
        "'": "‘",
        '"': "“",
        "~": "～",
        "@": "＠",
        "#": "＃",
        "$": "＄",
        "%": "％",
        "^": "＾",
        "&": "＆",
        "*": "＊",
    }

    ZH_TO_EN = {v: k for k, v in EN_TO_ZH.items()}

    def to_chinese(self, text):
        for en, zh in self.EN_TO_ZH.items():
            text = text.replace(en, zh)
        return text

    def to_english(self, text):
        for zh, en in self.ZH_TO_EN.items():
            text = text.replace(zh, en)
        return text


class RepeatedPunctuationCompressor:
    """连续标点压缩"""

    def __init__(self):
        self._patterns = {
            "，+": "，",
            "。+": "。",
            "！+": "！",
            "？+": "？",
            "、+": "、",
            "；+": "；",
            "…{2,}": "……",
            "~{2,}": "～",
            "-{2,}": "——",
        }

    def compress(self, text):
        for pattern, replacement in self._patterns.items():
            text = re.sub(pattern, replacement, text)
        return text


class QuoteNormalizer:
    """引号归一化"""

    QUOTE_PAIRS = {
        "「": "「",
        "」": "」",
        "『": "『",
        "』": "』",
        "‘": "'",
        "’": "'",
        "“": '"',
        "”": '"',
        "《": "《",
        "》": "》",
    }

    def normalize(self, text, style="chinese"):
        if style == "chinese":
            return text
        elif style == "simple":
            for zh, en in self.QUOTE_PAIRS.items():
                text = text.replace(zh, en)
        return text


class PunctuationNormalizer:
    """综合标点归一化器"""

    def __init__(self):
        self.chinese = ChinesePunctuationNormalizer()
        self.compressor = RepeatedPunctuationCompressor()
        self.quotes = QuoteNormalizer()

    def normalize(self, text, to_chinese=True):
        if to_chinese:
            text = self.chinese.to_chinese(text)
        text = self.compressor.compress(text)
        return text

    def normalize_to_ascii(self, text):
        text = self.chinese.to_english(text)
        text = self.compressor.compress(text)
        return text

    def stats(self, text):
        chinese_punct = len(re.findall(r"[，。！？、；：""''（）【】《》「」～…—·]", text))
        ascii_punct = len(re.findall(r"[,\\.!?:;'\"()\[\]{}~@#\$%\^&\*\-]", text))
        return {
            "chinese_punctuation": chinese_punct,
            "ascii_punctuation": ascii_punct,
            "total_punctuation": chinese_punct + ascii_punct,
            "chinese_ratio": round(chinese_punct / max(1, chinese_punct + ascii_punct), 2),
        }
