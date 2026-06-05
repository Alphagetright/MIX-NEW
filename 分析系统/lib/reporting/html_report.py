# -*- coding: utf-8 -*-
"""
HTML report rendering for styled browser-ready output.
"""

import html
from dataclasses import dataclass, field
from typing import Any, Dict, List


_CSS = """
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
       max-width: 960px; margin: 2em auto; padding: 0 1em; color: #333; }
h1 { border-bottom: 2px solid #4A90D9; padding-bottom: 0.3em; }
h2 { color: #4A90D9; margin-top: 1.5em; }
table { border-collapse: collapse; width: 100%; margin: 1em 0; }
th, td { border: 1px solid #ddd; padding: 8px 12px; text-align: left; }
th { background: #4A90D9; color: #fff; }
tr:nth-child(even) { background: #f5f8fc; }
.chart-placeholder { background: #f9f9f9; border: 2px dashed #ccc;
       border-radius: 8px; padding: 2em; text-align: center;
       margin: 1em 0; color: #888; }
.summary { background: #eef4fb; border-left: 4px solid #4A90D9;
       padding: 1em; margin: 1em 0; border-radius: 4px; }
"""


def _html_wrap(title: str, body: str) -> str:
    t = html.escape(title)
    return f"<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n<title>{t}</title>\n<style>{_CSS}</style>\n</head>\n<body>\n<h1>{t}</h1>\n{body}\n</body>\n</html>"


@dataclass
class HtmlTable:
    """Builder for an HTML table with headers and rows."""
    headers: List[str] = field(default_factory=list)
    rows: List[List[str]] = field(default_factory=list)
    caption: str = ""

    def add_row(self, cells: List[Any]) -> None:
        self.rows.append([html.escape(str(c)) for c in cells])

    def render(self) -> str:
        parts = ["<table>"]
        if self.caption:
            parts.append(f"<caption>{html.escape(self.caption)}</caption>")
        if self.headers:
            parts.append("<thead><tr>" + "".join(f"<th>{html.escape(h)}</th>" for h in self.headers) + "</tr></thead>")
        if self.rows:
            body = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in self.rows)
            parts.append(f"<tbody>{body}</tbody>")
        parts.append("</table>")
        return "\n".join(parts)


@dataclass
class ChartPlaceholder:
    """Placeholder div indicating where a chart should render."""
    chart_id: str = ""
    label: str = "Chart"
    width: str = "100%"
    height: str = "300px"

    def render(self) -> str:
        return f'<div class="chart-placeholder" id="{html.escape(self.chart_id)}" style="width:{self.width};height:{self.height}">{html.escape(self.label)}</div>'


@dataclass
class HtmlReport:
    """Complete HTML report with sections, tables, and chart areas."""
    title: str = "Report"
    sections: Dict[str, str] = field(default_factory=dict)
    tables: List[HtmlTable] = field(default_factory=list)
    charts: List[ChartPlaceholder] = field(default_factory=list)
    summary_text: str = ""

    def render(self) -> str:
        parts = []
        if self.summary_text:
            parts.append(f'<div class="summary">{html.escape(self.summary_text)}</div>')
        for heading, content in self.sections.items():
            parts.append(f"<h2>{html.escape(heading)}</h2>\n<p>{html.escape(content)}</p>")
        for table in self.tables:
            parts.append(table.render())
        for chart in self.charts:
            parts.append(chart.render())
        return _html_wrap(self.title, "\n".join(parts))


class HtmlReportBuilder:
    """Builds an HtmlReport progressively."""
    def __init__(self, title: str = "Report") -> None:
        self._report = HtmlReport(title=title)

    def add_section(self, heading: str, content: str) -> "HtmlReportBuilder":
        self._report.sections[heading] = content
        return self

    def add_table(self, table: HtmlTable) -> "HtmlReportBuilder":
        self._report.tables.append(table)
        return self

    def add_chart(self, chart_id: str, label: str = "Chart") -> "HtmlReportBuilder":
        self._report.charts.append(ChartPlaceholder(chart_id=chart_id, label=label))
        return self

    def with_summary(self, text: str) -> "HtmlReportBuilder":
        self._report.summary_text = text
        return self

    def build(self) -> HtmlReport:
        return self._report

    def render(self) -> str:
        return self._report.render()
