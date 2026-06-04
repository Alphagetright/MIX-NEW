# -*- coding: utf-8 -*-
"""
Build nested structures from flat mappings and assemble
hierarchical data using configurable rules.
"""

from typing import Any, Dict, List, Optional, Set, Tuple


class NestingConfig:
    """Configuration for nesting rules including key mappings and depth limits."""
    def __init__(self, list_keys: Optional[Set[str]] = None, max_depth: int = 10, merge_arrays: bool = False) -> None:
        self.list_keys = list_keys or set()
        self.max_depth = max_depth
        self.merge_arrays = merge_arrays

    def is_list_key(self, key: str) -> bool:
        return key in self.list_keys


class ListAssembler:
    """Assemble individual items into a list, optionally grouped by a key."""
    def __init__(self, group_key: Optional[str] = None) -> None:
        self._group_key = group_key

    def assemble(self, items: List[Any]) -> List[Any]:
        return list(items)

    def assemble_grouped(self, items: List[Dict[str, Any]]) -> Dict[str, List[Any]]:
        result: Dict[str, List[Any]] = {}
        for item in items:
            if isinstance(item, dict):
                key = str(item.get(self._group_key, "_ungrouped"))
                result.setdefault(key, []).append(item)
        return result

    def deduplicate(self, items: List[Any]) -> List[Any]:
        seen: Set[Any] = set()
        result: List[Any] = []
        for item in items:
            key = id(item) if isinstance(item, dict) else item
            if key not in seen:
                seen.add(key)
                result.append(item)
        return result


class DictMerger:
    """Merge multiple dictionaries with configurable conflict resolution."""
    def __init__(self, overwrite: bool = True, deep: bool = True) -> None:
        self._overwrite = overwrite
        self._deep = deep

    def merge(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        result = base.copy()
        for key, value in override.items():
            if key not in result:
                result[key] = value
            elif self._overwrite:
                if self._deep and isinstance(result[key], dict) and isinstance(value, dict):
                    result[key] = self.merge(result[key], value)
                else:
                    result[key] = value
        return result

    def merge_all(self, dicts: List[Dict[str, Any]]) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        for d in dicts:
            result = self.merge(result, d)
        return result


class TreeBuilder:
    """Build a tree from flat items with parent-child relationships."""
    def __init__(self, id_field: str = "id", parent_field: str = "parent_id", children_field: str = "children") -> None:
        self._id_field = id_field
        self._parent_field = parent_field
        self._children_field = children_field

    def build(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        nodes: Dict[str, Dict[str, Any]] = {}
        roots: List[Dict[str, Any]] = []
        for item in items:
            node_id = str(item.get(self._id_field, ""))
            if node_id:
                nodes[node_id] = dict(item)
                nodes[node_id][self._children_field] = []
        for item in items:
            node_id = str(item.get(self._id_field, ""))
            parent_id = str(item.get(self._parent_field, ""))
            if parent_id and parent_id in nodes:
                nodes[parent_id][self._children_field].append(nodes[node_id])
            elif node_id in nodes:
                roots.append(nodes[node_id])
        return roots

    def flatten(self, tree: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        result: List[Dict[str, Any]] = []
        def _walk(node: Dict[str, Any]) -> None:
            result.append({k: v for k, v in node.items() if k != self._children_field})
            for child in node.get(self._children_field, []):
                _walk(child)
        for root in tree:
            _walk(root)
        return result


class NestedBuilder:
    """Build nested structures from flat mappings using configurable rules."""
    def __init__(self, config: Optional[NestingConfig] = None,
                 list_assembler: Optional[ListAssembler] = None,
                 dict_merger: Optional[DictMerger] = None,
                 tree_builder: Optional[TreeBuilder] = None) -> None:
        self._config = config or NestingConfig()
        self._list_assembler = list_assembler or ListAssembler()
        self._dict_merger = dict_merger or DictMerger()
        self._tree_builder = tree_builder or TreeBuilder()

    def build_nested(self, flat: Dict[str, Any], depth: int = 0) -> Any:
        if depth > self._config.max_depth:
            return flat
        result: Dict[str, Any] = {}
        for key, value in flat.items():
            if self._config.is_list_key(key) and isinstance(value, list):
                result[key] = self._list_assembler.assemble(value)
            elif isinstance(value, dict):
                result[key] = self.build_nested(value, depth + 1)
            else:
                result[key] = value
        return result

    def merge_and_build(self, dicts: List[Dict[str, Any]]) -> Dict[str, Any]:
        return self.build_nested(self._dict_merger.merge_all(dicts))

    def build_tree(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return self._tree_builder.build(items)
