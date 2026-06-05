# -*- coding: utf-8 -*-
"""文本归一化处理"""

import re
import unicodedata


class WhitespaceNormalizer:
    """空白字符归一"""

    def normalize(self, text):
        text = re.sub(r"[\r\n]+", "\n", text)
        text = re.sub(r"[ \t]+", " ", text)
        text = text.strip()
        return text

    def normalize_lines(self, lines):
        return [self.normalize(line) for line in lines if line.strip()]


class PunctuationNormalizer:
    """标点符号归一"""

    PUNCT_MAP = {
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
        '"': '“',
    }

    def normalize(self, text):
        for en, zh in self.PUNCT_MAP.items():
            text = text.replace(en, zh)
        text = re.sub(r"[、，]+", "，", text)
        text = re.sub(r"[。．]+", "。", text)
        return text

    def normalize_to_english(self, text):
        revers_map = {v: k for k, v in self.PUNCT_MAP.items()}
        for zh, en in revers_map.items():
            text = text.replace(zh, en)
        return text


class UnicodeNormalizer:
    """Unicode归一化"""

    def __init__(self, form="NFKC"):
        self.form = form

    def normalize(self, text):
        return unicodedata.normalize(self.form, text)

    def is_normalized(self, text):
        return text == unicodedata.normalize(self.form, text)


class ControlCharFilter:
    """控制字符过滤"""

    def filter(self, text):
        result = []
        for ch in text:
            cp = ord(ch)
            if cp < 0x20 and cp not in (0x09, 0x0A, 0x0D):
                continue
            if 0x7F <= cp <= 0x9F:
                continue
            result.append(ch)
        return "".join(result)

    def filter_to_ascii(self, text):
        return "".join(ch for ch in text if ord(ch) < 128)


class FullWidthConverter:
    """全角半角转换"""

    def to_halfwidth(self, text):
        result = []
        for ch in text:
            cp = ord(ch)
            if 0xFF01 <= cp <= 0xFF5E:
                result.append(chr(cp - 0xFEE0))
            elif cp == 0x3000:
                result.append(" ")
            else:
                result.append(ch)
        return "".join(result)

    def to_fullwidth(self, text):
        result = []
        for ch in text:
            cp = ord(ch)
            if 0x21 <= cp <= 0x7E:
                result.append(chr(cp + 0xFEE0))
            elif cp == 0x20:
                result.append("　")
            else:
                result.append(ch)
        return "".join(result)


class TextNormalizer:
    """文本归一化器 —— 串联各归一化步骤"""

    def __init__(self):
        self.whitespace = WhitespaceNormalizer()
        self.punctuation = PunctuationNormalizer()
        self.unicode = UnicodeNormalizer()
        self.control = ControlCharFilter()
        self.fullwidth = FullWidthConverter()

    def normalize(self, text, steps=None):
        if steps is None:
            steps = ["unicode", "control", "fullwidth", "whitespace"]
        for step in steps:
            if step == "unicode":
                text = self.unicode.normalize(text)
            elif step == "control":
                text = self.control.filter(text)
            elif step == "fullwidth":
                text = self.fullwidth.to_halfwidth(text)
            elif step == "whitespace":
                text = self.whitespace.normalize(text)
            elif step == "punctuation":
                text = self.punctuation.normalize(text)
        return text

    def normalize_file(self, filepath, output_path=None):
        from .input_reader import TextFileReader
        reader = TextFileReader()
        text = reader.read(filepath)
        normalized = self.normalize(text)
        if output_path:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(normalized)
        return normalized
