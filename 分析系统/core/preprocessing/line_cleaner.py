# -*- coding: utf-8 -*-
"""行级清洗 —— 前后空白、空行、注释、序号"""

import re


class StripCleaner:
    """前后空白清理"""

    def clean(self, line):
        return line.strip()

    def clean_all(self, lines):
        return [self.clean(line) for line in lines]


class EmptyLineFilter:
    """空行过滤"""

    def filter(self, lines):
        return [line for line in lines if line.strip()]

    def filter_with_positions(self, lines):
        result = []
        for i, line in enumerate(lines):
            if line.strip():
                result.append({"index": i, "text": line, "line_number": i + 1})
        return result


class CommentRemover:
    """注释去除"""

    def __init__(self):
        self._patterns = [
            (r"//.*$", ""),
            (r"#.*$", ""),
            (r"/\*.*?\*/", "", re.DOTALL),
            (r"<!--.*?-->", "", re.DOTALL),
        ]

    def remove(self, line):
        for pattern, repl, *flags in self._patterns:
            kwargs = {}
            if flags:
                kwargs["flags"] = flags[0]
            line = re.sub(pattern, repl, line, **kwargs)
        return line.strip()

    def remove_all(self, lines):
        return [self.remove(line) for line in lines]


class NumberingStripper:
    """序号去除"""

    def __init__(self):
        self._patterns = [
            r"^\d+[\.\、\-\s]+",
            r"^[\(（]\d+[\)）][\s]*",
            r"^第[一二三四五六七八九十百千]+[、\s]",
            r"^[①②③④⑤⑥⑦⑧⑨⑩]",
        ]

    def strip(self, line):
        for pattern in self._patterns:
            line = re.sub(pattern, "", line)
        return line.strip()

    def strip_all(self, lines):
        return [self.strip(line) for line in lines]


class LineCleaner:
    """行级清洗器 —— 串联各清洗步骤"""

    def __init__(self):
        self.strip = StripCleaner()
        self.empty = EmptyLineFilter()
        self.comment = CommentRemover()
        self.numbering = NumberingStripper()

    def clean(self, line, steps=None):
        if steps is None:
            steps = ["strip"]
        for step in steps:
            if step == "strip":
                line = self.strip.clean(line)
            elif step == "comment":
                line = self.comment.remove(line)
            elif step == "numbering":
                line = self.numbering.strip(line)
        return line

    def clean_all(self, lines, steps=None, filter_empty=True):
        result = [self.clean(line, steps) for line in lines]
        if filter_empty:
            result = self.empty.filter(result)
        return result
