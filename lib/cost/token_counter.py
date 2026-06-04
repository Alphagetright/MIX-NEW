# -*- coding: utf-8 -*-
"""Token counting and estimation utilities for pipeline cost tracking."""

import enum
import math
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional


class EstimationStrategy(enum.Enum):
    """Token estimation strategies for different use cases."""
    CHARACTER_BASED = "character_based"
    WORD_BASED = "word_based"
    MODEL_SPECIFIC = "model_specific"


def estimate_tokens(text: str, strategy: EstimationStrategy = EstimationStrategy.CHARACTER_BASED) -> int:
    """Estimate token count using a simple heuristic.

    Character-based: ~1 token per 2 chars for CJK-heavy text,
    ~1 token per 4 chars for general text.
    Word-based: ~1.3 tokens per word on average.
    """
    if not text:
        return 0
    if strategy == EstimationStrategy.CHARACTER_BASED:
        cjk_count = sum(1 for ch in text if '一' <= ch <= '鿿' or '぀' <= ch <= 'ヿ')
        non_cjk = len(text) - cjk_count
        return max(1, math.ceil(cjk_count / 2.0 + non_cjk / 4.0))
    elif strategy == EstimationStrategy.WORD_BASED:
        word_count = len(text.split())
        return max(1, int(word_count * 1.3))
    elif strategy == EstimationStrategy.MODEL_SPECIFIC:
        return max(1, math.ceil(len(text) / 3.0))
    return max(1, math.ceil(len(text) / 4.0))


@dataclass
class TokenStats:
    """Cumulative token usage statistics."""
    total_tokens: int = 0
    per_model: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    per_input_type: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    call_count: int = 0

    def record(self, tokens: int, model: str = "default", input_type: str = "general") -> None:
        """Record a token usage event."""
        self.total_tokens += tokens
        self.per_model[model] += tokens
        self.per_input_type[input_type] += tokens
        self.call_count += 1

    @property
    def average_tokens(self) -> float:
        """Average tokens per call."""
        if self.call_count == 0:
            return 0.0
        return self.total_tokens / self.call_count

    def merge(self, other: "TokenStats") -> "TokenStats":
        """Merge another TokenStats instance into this one."""
        self.total_tokens += other.total_tokens
        self.call_count += other.call_count
        for model, count in other.per_model.items():
            self.per_model[model] += count
        for itype, count in other.per_input_type.items():
            self.per_input_type[itype] += count
        return self


@dataclass
class TokenReport:
    """Formatted report of token usage statistics."""
    stats: TokenStats
    label: str = "Token Usage Report"

    def summary(self) -> str:
        """Generate a human-readable summary string."""
        lines = [
            f"=== {self.label} ===",
            f"Total tokens:      {self.stats.total_tokens:,}",
            f"Call count:        {self.stats.call_count:,}",
            f"Average per call:  {self.stats.average_tokens:.1f}",
            "--- Per Model ---",
        ]
        for model, count in sorted(self.stats.per_model.items()):
            lines.append(f"  {model}: {count:,}")
        lines.append("--- Per Input Type ---")
        for itype, count in sorted(self.stats.per_input_type.items()):
            lines.append(f"  {itype}: {count:,}")
        return "\n".join(lines)


class TokenCounter:
    """Count tokens in strings with estimation and cumulative statistics."""

    def __init__(self, strategy: EstimationStrategy = EstimationStrategy.CHARACTER_BASED) -> None:
        self.strategy = strategy
        self.stats = TokenStats()

    def count(self, text: str, model: str = "default", input_type: str = "general") -> int:
        """Count tokens in the given text and record statistics."""
        tokens = estimate_tokens(text, self.strategy)
        self.stats.record(tokens, model, input_type)
        return tokens

    def count_batch(self, texts: List[str], model: str = "default", input_type: str = "general") -> List[int]:
        """Count tokens for a batch of texts."""
        return [self.count(t, model, input_type) for t in texts]

    def reset_stats(self) -> None:
        """Reset all cumulative statistics."""
        self.stats = TokenStats()

    def report(self, label: str = "Token Usage Report") -> TokenReport:
        """Get a formatted report of current statistics."""
        return TokenReport(stats=self.stats, label=label)
