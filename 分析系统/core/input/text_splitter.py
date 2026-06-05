# -*- coding: utf-8 -*-
"""文本分割 —— 诗歌分割、分句、区块识别"""

import re


class LineSplitter:
    """行分割器"""

    def split(self, text):
        lines = text.split("\n")
        return [line.strip() for line in lines if line.strip()]

    def split_preserve_empty(self, text):
        return text.split("\n")


class SentenceSplitter:
    """句分割器 —— 按标点分句"""

    def __init__(self):
        self._delimiters = r"[。！？；\n]"

    def split(self, text):
        sentences = re.split(self._delimiters, text)
        return [s.strip() for s in sentences if s.strip()]

    def split_with_delimiter(self, text):
        parts = re.split(f"({self._delimiters})", text)
        result = []
        current = ""
        for part in parts:
            if re.match(self._delimiters, part):
                current += part
                if current.strip():
                    result.append(current.strip())
                    current = ""
            else:
                current = part
        if current.strip():
            result.append(current.strip())
        return result


class StanzaDetector:
    """联/阙检测器"""

    def __init__(self):
        self._stanza_patterns = [
            r"^\s*$",
            r"^[第卷章].*[联阙节]$",
            r"^-{3,}$",
            r"^\*{3,}$",
        ]

    def detect_stanzas(self, lines):
        stanzas = []
        current = []
        for line in lines:
            if self._is_stanza_break(line):
                if current:
                    stanzas.append(current)
                    current = []
            else:
                current.append(line)
        if current:
            stanzas.append(current)
        return stanzas

    def _is_stanza_break(self, line):
        if not line.strip():
            return True
        for pattern in self._stanza_patterns:
            if re.match(pattern, line.strip()):
                return True
        return False


class PoemBoundaryDetector:
    """诗歌边界检测"""

    def __init__(self):
        self._title_patterns = [
            r"^《.+》$",
            r"^「.+」$",
            r"^.+\s+[·‧•]\s+.+$",
            r"^【.+】$",
        ]

    def detect_poems(self, lines):
        poems = []
        current_title = None
        current_lines = []

        for line in lines:
            line = line.strip()
            if not line:
                continue
            if self._is_title(line):
                if current_title and current_lines:
                    poems.append({"title": current_title, "lines": current_lines})
                current_title = line
                current_lines = []
            else:
                current_lines.append(line)

        if current_title and current_lines:
            poems.append({"title": current_title, "lines": current_lines})

        return poems

    def _is_title(self, line):
        for pattern in self._title_patterns:
            if re.match(pattern, line):
                return True
        return False


class ChunkSplitter:
    """块分割器 —— 按大小/标记分块"""

    def __init__(self, chunk_size=500, overlap=0):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def split_by_size(self, text):
        chunks = []
        start = 0
        while start < len(text):
            end = start + self.chunk_size
            chunk = text[start:end]
            chunks.append(chunk)
            start = end - self.overlap if self.overlap else end
        return chunks

    def split_by_lines(self, lines, lines_per_chunk=20):
        chunks = []
        for i in range(0, len(lines), lines_per_chunk):
            chunks.append(lines[i:i + lines_per_chunk])
        return chunks

    def split_by_marker(self, text, marker):
        parts = text.split(marker)
        return [part.strip() for part in parts if part.strip()]
