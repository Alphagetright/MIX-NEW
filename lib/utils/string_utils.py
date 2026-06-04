# -*- coding: utf-8 -*-
"""字符串工具函数"""

import re
import unicodedata


def truncate(text, max_length=100, suffix="..."):
    if not text:
        return text
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def pad(text, width, char=" ", align="left"):
    if align == "left":
        return text.ljust(width, char)
    elif align == "right":
        return text.rjust(width, char)
    elif align == "center":
        return text.center(width, char)
    return text


def strip_all(text):
    if not text:
        return text
    return "".join(text.split())


def normalize_spaces(text):
    if not text:
        return text
    return re.sub(r"\s+", " ", text).strip()


def split_lines(text, max_line_length=None):
    lines = text.split("\n")
    if max_line_length:
        result = []
        for line in lines:
            while len(line) > max_line_length:
                result.append(line[:max_line_length])
                line = line[max_line_length:]
            result.append(line)
        return result
    return lines


def escape_regex(text):
    return re.escape(text)


def unicode_normalize(text, form="NFKC"):
    return unicodedata.normalize(form, text)


def count_chars(text):
    if not text:
        return 0
    chinese = len(re.findall(r"[一-鿿]", text))
    english = len(re.findall(r"[a-zA-Z]", text))
    digits = len(re.findall(r"[0-9]", text))
    spaces = text.count(" ")
    punctuation = len(text) - chinese - english - digits - spaces
    return {
        "total": len(text),
        "chinese": chinese,
        "english": english,
        "digits": digits,
        "spaces": spaces,
        "punctuation": punctuation,
    }


def extract_chinese(text):
    return "".join(re.findall(r"[一-鿿]+", text))


def is_chinese_char(char):
    if len(char) != 1:
        return False
    return "一" <= char <= "鿿"


def contains_chinese(text):
    return bool(re.search(r"[一-鿿]", text))


def split_by_punctuation(text):
    parts = re.split(r"([，。！？、；：""''（）\[\]{}（）])", text)
    result = []
    for part in parts:
        part = part.strip()
        if part:
            result.append(part)
    return result


class StringBuilder:
    """字符串构建器"""

    def __init__(self, sep=""):
        self._parts = []
        self._sep = sep

    def append(self, text):
        self._parts.append(str(text))

    def append_line(self, text=""):
        self._parts.append(str(text) + "\n")

    def clear(self):
        self._parts.clear()

    def build(self):
        return self._sep.join(self._parts)

    def lines(self):
        return list(self._parts)

    def __len__(self):
        return len(self.build())

    def __str__(self):
        return self.build()
