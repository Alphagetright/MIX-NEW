# -*- coding: utf-8 -*-
"""结构检测 —— 行数统计、字数统计、联/阙模式"""

import re
from collections import Counter


class LineCounter:
    """行数统计"""

    def count(self, lines):
        return len(lines)

    def count_non_empty(self, lines):
        return len([l for l in lines if l.strip()])

    def count_by_length(self, lines, max_length=None):
        if max_length:
            return len([l for l in lines if len(l) <= max_length])
        return {len(l): sum(1 for l in lines if len(l) == length) for length in set(len(l) for l in lines)}


class CharCounter:
    """字数统计"""

    def count_total(self, text):
        return len(text)

    def count_chinese(self, text):
        return len(re.findall(r"[一-鿿]", text))

    def count_by_line(self, lines):
        return [len(re.findall(r"[一-鿿]", line)) for line in lines]

    def count_frequency(self, text):
        return Counter(re.findall(r"[一-鿿]", text))

    def top_frequency(self, text, n=10):
        return self.count_frequency(text).most_common(n)


class PatternDetector:
    """模式检测"""

    def detect_duplicate_lines(self, lines):
        seen = {}
        duplicates = []
        for i, line in enumerate(lines):
            if line in seen:
                duplicates.append((i, line, seen[line]))
            else:
                seen[line] = i
        return duplicates

    def detect_uneven_lines(self, lines):
        if not lines:
            return []
        lengths = [len(line) for line in lines]
        if len(set(lengths)) <= 1:
            return []
        avg_len = sum(lengths) / len(lengths)
        return [i for i, l in enumerate(lengths) if abs(l - avg_len) > 2]

    def detect_short_lines(self, lines, min_length=2):
        return [(i, line) for i, line in enumerate(lines) if len(line) < min_length]


class CoupletDetector:
    """联/阙结构检测"""

    def __init__(self):
        self.couplet_lengths = {4: 2, 8: 2}
        self.stanza_sizes = {4: 2, 8: 2, 12: 3, 16: 4}

    def detect_couplets(self, lines):
        count = len(lines)
        if count in self.couplet_lengths:
            num_pairs = self.couplet_lengths[count]
            couplets = []
            for i in range(num_pairs):
                idx = i * 2
                if idx + 1 < len(lines):
                    couplets.append((lines[idx], lines[idx + 1], i + 1))
            return couplets
        return []

    def detect_stanzas(self, lines):
        count = len(lines)
        if count in self.stanza_sizes:
            stanza_size = self.stanza_sizes[count]
            stanzas = []
            for i in range(0, count, stanza_size):
                stanzas.append(lines[i:i + stanza_size])
            return stanzas
        return [lines]


class StructureDetector:
    """综合结构检测器"""

    def __init__(self):
        self.line_counter = LineCounter()
        self.char_counter = CharCounter()
        self.pattern = PatternDetector()
        self.couplet = CoupletDetector()

    def analyze(self, lines):
        text = "".join(lines)
        return {
            "line_count": self.line_counter.count(lines),
            "total_chars": self.char_counter.count_total(text),
            "chinese_chars": self.char_counter.count_chinese(text),
            "chars_per_line": self.char_counter.count_by_line(lines),
            "avg_line_length": sum(len(l) for l in lines) / max(1, len(lines)),
            "duplicates": len(self.pattern.detect_duplicate_lines(lines)),
            "uneven_lines": len(self.pattern.detect_uneven_lines(lines)),
            "couplets": len(self.couplet.detect_couplets(lines)),
        }
