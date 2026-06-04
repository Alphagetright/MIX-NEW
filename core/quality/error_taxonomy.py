# -*- coding: utf-8 -*-
"""Hierarchical error classification system including category trees,
severity levels, root-cause mapping, and fix-strategy mapping."""

from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class SeverityLevel(Enum):
    """Standardized severity levels ordered from most to least severe."""
    CRITICAL = 5
    MAJOR = 4
    MINOR = 3
    WARNING = 2
    INFO = 1

    @classmethod
    def from_string(cls, label: str) -> "SeverityLevel":
        mapping = {e.name.lower(): e for e in cls}
        return mapping.get(label.lower(), cls.INFO)

    def __str__(self) -> str:
        return self.name.capitalize()


class ErrorCategory:
    """A node in the error taxonomy tree with optional parent-child links."""

    def __init__(self, name: str, code: str,
                 description: str = "",
                 parent: Optional["ErrorCategory"] = None):
        self.name = name
        self.code = code
        self.description = description
        self.parent = parent
        self.children: List["ErrorCategory"] = []

    def add_child(self, child: "ErrorCategory") -> None:
        """Attach a child category and set its parent reference."""
        child.parent = self
        self.children.append(child)

    def path(self) -> List[str]:
        """Return the full ancestor chain from root to this node."""
        nodes: List[str] = []
        current: Optional[ErrorCategory] = self
        while current is not None:
            nodes.append(current.name)
            current = current.parent
        nodes.reverse()
        return nodes


class RootCauseMapper:
    """Map error codes to probable root cause descriptions."""

    def __init__(self):
        self._mapping: Dict[str, str] = {}

    def register(self, error_code: str, cause: str) -> None:
        self._mapping[error_code] = cause

    def get_cause(self, error_code: str) -> Optional[str]:
        return self._mapping.get(error_code)


class FixStrategyMapper:
    """Map error codes to recommended fix strategies."""

    def __init__(self):
        self._mapping: Dict[str, str] = {}

    def register(self, error_code: str, strategy: str) -> None:
        self._mapping[error_code] = strategy

    def get_strategy(self, error_code: str) -> Optional[str]:
        return self._mapping.get(error_code)


class TaxonomyTree:
    """Full navigation interface for a hierarchical error taxonomy."""

    def __init__(self, root: Optional[ErrorCategory] = None):
        self._root = root

    @property
    def root(self) -> Optional[ErrorCategory]:
        return self._root

    def find_by_code(self, code: str) -> Optional[ErrorCategory]:
        """Depth-first search for a category by its code."""
        return self._find(self._root, code) if self._root else None

    def _find(self, node: Optional[ErrorCategory], code: str) -> Optional[ErrorCategory]:
        if node is None:
            return None
        if node.code == code:
            return node
        for child in node.children:
            result = self._find(child, code)
            if result is not None:
                return result
        return None

    def flatten(self) -> List[ErrorCategory]:
        """Return all categories in a flat list (pre-order traversal)."""
        result: List[ErrorCategory] = []
        self._traverse(self._root, result) if self._root else None
        return result

    def _traverse(self, node: ErrorCategory, acc: List[ErrorCategory]) -> None:
        acc.append(node)
        for child in node.children:
            self._traverse(child, acc)


class ErrorTaxonomy:
    """High-level facade that integrates categories, severity, causes, and fixes."""

    def __init__(self):
        self._tree = TaxonomyTree()
        self._severity_map: Dict[str, SeverityLevel] = {}
        self._root_cause_mapper = RootCauseMapper()
        self._fix_strategy_mapper = FixStrategyMapper()

    @property
    def tree(self) -> TaxonomyTree:
        return self._tree

    @property
    def root_cause_mapper(self) -> RootCauseMapper:
        return self._root_cause_mapper

    @property
    def fix_strategy_mapper(self) -> FixStrategyMapper:
        return self._fix_strategy_mapper

    def set_root(self, root: ErrorCategory) -> None:
        self._tree = TaxonomyTree(root)

    def set_severity(self, error_code: str, level: SeverityLevel) -> None:
        self._severity_map[error_code] = level

    def get_severity(self, error_code: str) -> SeverityLevel:
        return self._severity_map.get(error_code, SeverityLevel.INFO)

    def classify(self, error_code: str) -> Dict[str, Any]:
        """Return full classification for an error code."""
        category = self._tree.find_by_code(error_code)
        return {
            "code": error_code,
            "category": category.name if category else "Unknown",
            "path": category.path() if category else [],
            "severity": str(self.get_severity(error_code)),
            "root_cause": self._root_cause_mapper.get_cause(error_code),
            "fix_strategy": self._fix_strategy_mapper.get_strategy(error_code),
        }
