# -*- coding: utf-8 -*-
"""
Plain-text report formatting utilities for terminal and log output.

Provides table rendering, alignment, dividers, and value formatting
for generating human-readable text reports without external libraries.
"""

import itertools
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class TextAlignment(Enum):
    """Column alignment options for text tables."""

    LEFT = "<"
    CENTER = "^"
    RIGHT = ">"

    def format(self, text: str, width: int, pad: str = " ") -> str:
        fmt = f"{pad}{self.value}{width}"
        return f"{text:{fmt}}"


@dataclass
class TextDivider:
    """Horizontal rule composed of a repeated character."""

    char: str = "-"
    width: int = 80

    def render(self) -> str:
        return self.char * self.width


@dataclass
class TextFormatter:
    """Formats values into display-ready strings."""

    precision: int = 2
    bool_labels: Dict[bool, str] = field(default_factory=lambda: {True: "Yes", False: "No"})

    def format_value(self, value: Any) -> str:
        if isinstance(value, float):
            return f"{value:.{self.precision}f}"
        if isinstance(value, bool):
            return self.bool_labels[value]
        if isinstance(value, (int, str)):
            return str(value)
        if value is None:
            return ""
        return str(value)

    def format_percentage(self, value: float) -> str:
        return f"{value:.{self.precision}f}%"


@dataclass
class TextTable:
    """Column-based text table with headers and alignment per column."""

    headers: List[str] = field(default_factory=list)
    rows: List[List[str]] = field(default_factory=list)
    alignments: List[TextAlignment] = field(default_factory=list)
    formatter: TextFormatter = field(default_factory=TextFormatter)

    def add_row(self, row: List[Any]) -> None:
        self.rows.append([self.formatter.format_value(v) for v in row])

    def _column_widths(self) -> List[int]:
        cols = len(self.headers)
        widths = [len(h) for h in self.headers]
        for row in self.rows:
            padded = row + [""] * (cols - len(row))
            for i, cell in enumerate(padded):
                widths[i] = max(widths[i], len(cell))
        return widths

    def render(self, divider: Optional[TextDivider] = None) -> str:
        if not self.headers:
            return ""
        cols = len(self.headers)
        aligns = self.alignments or [TextAlignment.LEFT] * cols
        if len(aligns) < cols:
            aligns += [TextAlignment.LEFT] * (cols - len(aligns))
        widths = self._column_widths()
        div = divider or TextDivider(width=sum(widths) + 3 * (cols - 1) + 4)
        sep = " | "

        header = sep.join(a.format(h, w) for h, a, w in zip(self.headers, aligns, widths))
        rule = "-+-".join("-" * w for w in widths)

        body_lines = []
        for row in self.rows:
            padded = row + [""] * (cols - len(row))
            body_lines.append(
                sep.join(a.format(p, w) for p, a, w in zip(padded, aligns, widths))
            )

        lines = [div.render(), header, rule, *body_lines, div.render()]
        return "\n".join(lines)


@dataclass
class TextReport:
    """Container for a plain-text report with title, sections, and tables."""

    title: str = ""
    sections: Dict[str, str] = field(default_factory=dict)
    tables: List[TextTable] = field(default_factory=list)

    def add_section(self, heading: str, body: str) -> None:
        self.sections[heading] = body

    def add_table(self, table: TextTable) -> None:
        self.tables.append(table)

    def render(self) -> str:
        div = TextDivider()
        parts = [div.render(), f"  {self.title}", div.render(), ""]
        for heading, body in self.sections.items():
            parts.append(f"## {heading}")
            parts.append(body)
            parts.append("")
        for table in self.tables:
            parts.append(table.render())
            parts.append("")
        return "\n".join(parts)
