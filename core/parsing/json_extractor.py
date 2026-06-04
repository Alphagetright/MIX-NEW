# -*- coding: utf-8 -*-
"""
JSON extraction from text blocks with code fence detection,
boundary detection, and multi-block extraction support.
"""

import re
from typing import List, Optional


class JsonBlock:
    """Represents a single extracted JSON block with position information."""
    def __init__(self, content: str, start: int, end: int, source: str = "unknown") -> None:
        self.content = content
        self.start = start
        self.end = end
        self.source = source

    def __len__(self) -> int:
        return len(self.content)

    def __repr__(self) -> str:
        return f"JsonBlock(start={self.start}, end={self.end}, source={self.source})"


class ExtractionResult:
    """Container for extracted blocks and associated metadata."""
    def __init__(self) -> None:
        self.blocks: List[JsonBlock] = []
        self.total_blocks: int = 0
        self.characters_processed: int = 0
        self.errors: List[str] = []

    def add_block(self, block: JsonBlock) -> None:
        self.blocks.append(block)
        self.total_blocks = len(self.blocks)

    def merge(self, other: "ExtractionResult") -> None:
        self.blocks.extend(other.blocks)
        self.total_blocks = len(self.blocks)
        self.characters_processed += other.characters_processed
        self.errors.extend(other.errors)

    @property
    def first_block(self) -> Optional[JsonBlock]:
        return self.blocks[0] if self.blocks else None

    @property
    def last_block(self) -> Optional[JsonBlock]:
        return self.blocks[-1] if self.blocks else None

    def is_empty(self) -> bool:
        return len(self.blocks) == 0


class FenceDetector:
    """Detects JSON code fences such as ```json ... ``` in text."""
    FENCE_PATTERNS = [
        re.compile(r"```json\s*\n(.*?)\n```", re.DOTALL),
        re.compile(r"```\s*\n(.*?)\n```", re.DOTALL),
        re.compile(r"~~~json\s*\n(.*?)\n~~~", re.DOTALL),
        re.compile(r"~~~\s*\n(.*?)\n~~~", re.DOTALL),
    ]

    def __init__(self, extra_patterns: Optional[List[re.Pattern]] = None) -> None:
        self._patterns = list(self.FENCE_PATTERNS)
        if extra_patterns:
            self._patterns.extend(extra_patterns)

    def detect(self, text: str) -> ExtractionResult:
        result = ExtractionResult()
        result.characters_processed = len(text)
        seen = set()
        for pattern in self._patterns:
            for match in pattern.finditer(text):
                raw = match.group(1).strip()
                if not raw or raw in seen:
                    continue
                seen.add(raw)
                result.add_block(JsonBlock(raw, match.start(), match.end(), "fence"))
        return result


class JsonExtractor:
    """Extract JSON from text using fence detection and boundary heuristics."""
    BRACKET_PAIR = {"{": "}", "[": "]"}
    OPENERS = set(BRACKET_PAIR.keys())

    def __init__(self, fence_detector: Optional[FenceDetector] = None) -> None:
        self._fence_detector = fence_detector or FenceDetector()

    def extract(self, text: str) -> ExtractionResult:
        if not text or not text.strip():
            return ExtractionResult()
        result = self._fence_detector.detect(text)
        if result.is_empty():
            fallback = self._extract_by_boundary(text)
            result.merge(fallback)
        result.characters_processed = len(text)
        return result

    def extract_first(self, text: str) -> Optional[JsonBlock]:
        result = self.extract(text)
        return result.first_block

    def _extract_by_boundary(self, text: str) -> ExtractionResult:
        result = ExtractionResult()
        depth = 0
        start = -1
        in_string = False
        escape = False
        for i, ch in enumerate(text):
            if escape:
                escape = False
                continue
            if ch == "\\":
                escape = True
                continue
            if ch == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if ch in self.OPENERS:
                if depth == 0:
                    start = i
                depth += 1
            elif ch in ("}", "]"):
                depth -= 1
                if depth == 0 and start != -1:
                    raw = text[start:i + 1].strip()
                    if raw:
                        result.add_block(JsonBlock(raw, start, i + 1, "boundary"))
                    start = -1
        return result


class MultiJsonExtractor:
    """Extract multiple JSON blocks from a single text source."""
    def __init__(self, extractor: Optional[JsonExtractor] = None) -> None:
        self._extractor = extractor or JsonExtractor()

    def extract_all(self, text: str) -> ExtractionResult:
        return self._extractor.extract(text)

    def extract_by_lines(self, lines: List[str]) -> ExtractionResult:
        result = ExtractionResult()
        buffer: List[str] = []
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            buffer.append(stripped)
            if stripped.endswith("```") or stripped in ("}", "}"):
                partial = self._extractor.extract("\n".join(buffer))
                result.merge(partial)
                buffer = []
        if buffer:
            result.merge(self._extractor.extract("\n".join(buffer)))
        return result
