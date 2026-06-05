# -*- coding: utf-8 -*-
"""Cost estimation for pipeline token usage across models."""

import enum
from collections import defaultdict
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Dict, List, Optional


class CostCurrency(enum.Enum):
    """Configurable currency unit for cost calculations."""
    USD = "USD"
    EUR = "EUR"
    JPY = "JPY"
    CNY = "CNY"

    def symbol(self) -> str:
        symbols = {CostCurrency.USD: "$", CostCurrency.EUR: "€",
                   CostCurrency.JPY: "¥", CostCurrency.CNY: "¥"}
        return symbols.get(self, "$")


@dataclass
class PriceConfig:
    """Per-model pricing configuration.

    Prices are per 1,000 tokens (input and output).
    """
    model_name: str
    input_cost_per_1k: Decimal
    output_cost_per_1k: Decimal
    currency: CostCurrency = CostCurrency.USD

    def input_price_per_token(self) -> Decimal:
        return self.input_cost_per_1k / Decimal("1000")

    def output_price_per_token(self) -> Decimal:
        return self.output_cost_per_1k / Decimal("1000")


@dataclass
class CostBreakdown:
    """Detailed cost breakdown for a single operation."""
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    input_cost: Decimal = Decimal("0")
    output_cost: Decimal = Decimal("0")
    currency: CostCurrency = CostCurrency.USD

    @property
    def total_cost(self) -> Decimal:
        return self.input_cost + self.output_cost

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


@dataclass
class BatchCostSummary:
    """Aggregate costs across multiple operations."""
    breakdowns: List[CostBreakdown] = field(default_factory=list)
    currency: CostCurrency = CostCurrency.USD

    @property
    def total_cost(self) -> Decimal:
        return sum((b.total_cost for b in self.breakdowns), Decimal("0"))

    @property
    def total_input_tokens(self) -> int:
        return sum(b.input_tokens for b in self.breakdowns)

    @property
    def total_output_tokens(self) -> int:
        return sum(b.output_tokens for b in self.breakdowns)

    def by_model(self) -> Dict[str, Decimal]:
        result: Dict[str, Decimal] = defaultdict(Decimal)
        for b in self.breakdowns:
            result[b.model] += b.total_cost
        return dict(result)

    def summary(self) -> str:
        sym = self.currency.symbol()
        lines = [
            f"Batch Cost Summary ({self.currency.value})",
            f"  Total cost:         {sym}{self.total_cost:.4f}",
            f"  Total input tokens: {self.total_input_tokens:,}",
            f"  Total output tokens:{self.total_output_tokens:,}",
            f"  Operations:         {len(self.breakdowns)}",
        ]
        return "\n".join(lines)


class CostEstimator:
    """Estimate costs using per-model pricing with input/output breakdown."""

    def __init__(self, currency: CostCurrency = CostCurrency.USD) -> None:
        self.currency = currency
        self._price_configs: Dict[str, PriceConfig] = {}

    def register_model(self, config: PriceConfig) -> None:
        """Register pricing for a model."""
        self._price_configs[config.model_name] = config

    def estimate(self, model: str, input_tokens: int, output_tokens: int) -> CostBreakdown:
        """Calculate cost breakdown for a single operation."""
        config = self._price_configs.get(model)
        if config is None:
            raise ValueError(f"No price config registered for model: {model}")
        input_cost = config.input_price_per_token() * Decimal(str(input_tokens))
        output_cost = config.output_price_per_token() * Decimal(str(output_tokens))
        return CostBreakdown(
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            input_cost=input_cost,
            output_cost=output_cost,
            currency=self.currency,
        )

    def batch_summary(self, estimates: List[CostBreakdown]) -> BatchCostSummary:
        """Aggregate multiple cost estimates into a summary."""
        return BatchCostSummary(breakdowns=estimates, currency=self.currency)
