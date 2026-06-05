# -*- coding: utf-8 -*-
"""
JSON string cleaning and repair utilities for common formatting
issues such as comments, trailing commas, bad quotes, and truncation.
"""

import re
from typing import List, Optional, Protocol


class Cleaner(Protocol):
    """Protocol for individual cleaning operations."""
    def clean(self, text: str) -> str:
        ...


class CommentRemover:
    """Strip single-line (//) and block (/* */) comments from JSON text."""
    _SINGLE_LINE = re.compile(r"//[^\n]*")
    _BLOCK = re.compile(r"/\*.*?\*/", re.DOTALL)

    def __init__(self, preserve_lines: bool = False) -> None:
        self._preserve_lines = preserve_lines

    def clean(self, text: str) -> str:
        result = self._BLOCK.sub("", text)
        result = self._SINGLE_LINE.sub("", result)
        if self._preserve_lines:
            delta = text.count("\n") - result.count("\n")
            if delta > 0:
                result += "\n" * delta
        return result


class TrailingCommaFixer:
    """Remove trailing commas before closing braces or brackets."""
    _PATTERNS = [re.compile(r",\s*\}"), re.compile(r",\s*\]")]

    def clean(self, text: str) -> str:
        result = text
        for _ in range(3):
            prev = result
            for pat in self._PATTERNS:
                result = pat.sub("}", result)
            if result == prev:
                break
        return result


class QuoteFixer:
    """Fix common quote issues: unescaped inner quotes and mismatched quotes."""
    def __init__(self, preferred_quote: str = '"') -> None:
        self._preferred = preferred_quote

    def clean(self, text: str) -> str:
        if self._preferred != '"':
            text = text.replace('"', self._preferred)
        result: List[str] = []
        in_string = False
        escape = False
        for ch in text:
            if escape:
                result.append(ch)
                escape = False
                continue
            if ch == "\\":
                result.append(ch)
                escape = True
                continue
            if ch == '"':
                if in_string:
                    pass
                in_string = not in_string
            result.append(ch)
        return "".join(result)


class TruncationRecovery:
    """Detect and heal truncated JSON by appending missing closing brackets."""
    _BRACKET_MAP = {"{": "}", "[": "]", '"': '"'}
    _OPENERS = set(_BRACKET_MAP.keys())

    def __init__(self, max_repair_depth: int = 20) -> None:
        self._max_depth = max_repair_depth

    def _bracket_stack(self, text: str) -> List[str]:
        stack: List[str] = []
        in_string = False
        escape = False
        for ch in text:
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
            if ch in self._OPENERS:
                stack.append(ch)
            elif ch in ("}", "]"):
                if stack and self._BRACKET_MAP.get(stack[-1]) == ch:
                    stack.pop()
        return stack

    def clean(self, text: str) -> str:
        stack = self._bracket_stack(text)
        if not stack:
            return text
        closing = []
        depth = 0
        while stack and depth < self._max_depth:
            closer = self._BRACKET_MAP.get(stack.pop())
            if closer:
                closing.append(closer)
            depth += 1
        return text + "".join(reversed(closing))


class CleanerPipeline:
    """Chain multiple cleaners and apply them in sequence."""
    def __init__(self, cleaners: Optional[List[Cleaner]] = None) -> None:
        self._cleaners = cleaners or [
            CommentRemover(), TrailingCommaFixer(),
            QuoteFixer(), TruncationRecovery(),
        ]

    def run(self, text: str) -> str:
        result = text
        for cleaner in self._cleaners:
            result = cleaner.clean(result)
        return result

    def append(self, cleaner: Cleaner) -> None:
        self._cleaners.append(cleaner)


class JsonCleaner:
    """High-level JSON cleaner that delegates to a CleanerPipeline."""
    def __init__(self, pipeline: Optional[CleanerPipeline] = None) -> None:
        self._pipeline = pipeline or CleanerPipeline()

    def clean(self, text: str) -> str:
        return self._pipeline.run(text)

    @property
    def pipeline(self) -> CleanerPipeline:
        return self._pipeline
