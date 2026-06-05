# -*- coding: utf-8 -*-
"""
JSON-serializable report structures for machine consumption and export.

Provides hierarchical report trees, flattening utilities, and a builder
for constructing JSON-compatible report representations.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ReportNode:
    """A single node in the report tree with a key, value, and optional children."""

    key: str = ""
    value: Any = None
    children: List["ReportNode"] = field(default_factory=list)

    def add_child(self, child: "ReportNode") -> None:
        self.children.append(child)

    def to_dict(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {"key": self.key}
        if self.value is not None:
            result["value"] = self.value
        if self.children:
            result["children"] = [c.to_dict() for c in self.children]
        return result


@dataclass
class ReportTree:
    """Nested hierarchical structure for organizing report data."""

    root: ReportNode = field(default_factory=lambda: ReportNode(key="root"))

    def to_dict(self) -> Dict[str, Any]:
        return self.root.to_dict()

    def flatten(self, separator: str = ".") -> Dict[str, Any]:
        flattener = ReportFlattener(separator=separator)
        return flattener.flatten(self)


@dataclass
class JsonReport:
    """JSON-serializable report with a tree, summary, and metadata."""

    tree: ReportTree = field(default_factory=ReportTree)
    summary: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tree": self.tree.to_dict(),
            "summary": dict(self.summary),
            "metadata": dict(self.metadata),
        }


class ReportFlattener:
    """Flattens a nested ReportTree into a dot-separated key-value map."""

    def __init__(self, separator: str = ".") -> None:
        self._sep = separator

    def flatten(self, tree: ReportTree) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        self._walk(tree.root, "", result)
        return result

    def _walk(self, node: ReportNode, prefix: str, result: Dict[str, Any]) -> None:
        key = f"{prefix}{self._sep}{node.key}" if prefix else node.key
        if node.children:
            for child in node.children:
                self._walk(child, key, result)
        elif node.value is not None:
            result[key] = node.value


class JsonReportBuilder:
    """Builds a JsonReport by composing trees, summaries, and metadata."""

    def __init__(self) -> None:
        self._tree = ReportTree()
        self._summary: Dict[str, Any] = {}
        self._metadata: Dict[str, Any] = {}

    def add_path(self, path: str, value: Any) -> "JsonReportBuilder":
        parts = path.split(".")
        current = self._tree.root
        for i, part in enumerate(parts):
            found = next((c for c in current.children if c.key == part), None)
            if found is None:
                found = ReportNode(key=part)
                current.add_child(found)
            current = found
            if i == len(parts) - 1:
                current.value = value
        return self

    def with_summary(self, data: Dict[str, Any]) -> "JsonReportBuilder":
        self._summary = dict(data)
        return self

    def with_metadata(self, data: Dict[str, Any]) -> "JsonReportBuilder":
        self._metadata = dict(data)
        return self

    def build(self) -> JsonReport:
        return JsonReport(tree=self._tree, summary=self._summary, metadata=self._metadata)
