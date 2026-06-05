# -*- coding: utf-8 -*-
"""
Pipeline builder module.

Provides the PipelineBuilder for constructing execution pipelines
by registering stages, resolving their dependencies, and producing
a topological execution order via DAG analysis.
"""

from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from pipeline.stage_definition import StageDefinition, StageDependency


@dataclass
class StageNode:
    """Node in the execution graph representing a single stage.

    Attributes:
        definition: The StageDefinition this node wraps.
        stage_id: Unique identifier (defaults to definition name).
    """

    definition: StageDefinition
    stage_id: str = ""

    def __post_init__(self) -> None:
        if not self.stage_id:
            self.stage_id = self.definition.name


@dataclass
class BuildResult:
    """Result produced by the pipeline builder.

    Attributes:
        graph: The constructed dependency graph.
        order: Topologically sorted list of stage identifiers.
        warnings: List of diagnostic warnings from the build.
    """

    graph: "DependencyGraph"
    order: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class DependencyGraph:
    """Directed acyclic graph representing stage dependencies.

    Supports adding edges between stages and detecting cycles
    that would prevent a valid execution order.
    """

    def __init__(self) -> None:
        self._nodes: Dict[str, StageNode] = {}
        self._edges: Dict[str, Set[str]] = defaultdict(set)

    def add_node(self, node: StageNode) -> None:
        """Register a node in the graph."""
        self._nodes[node.stage_id] = node

    def add_edge(self, source: str, target: str) -> None:
        """Add a directed edge from source to target stage."""
        if source in self._nodes and target in self._nodes:
            self._edges[source].add(target)

    def has_node(self, stage_id: str) -> bool:
        """Check if a stage exists in the graph."""
        return stage_id in self._nodes

    def get_node(self, stage_id: str) -> Optional[StageNode]:
        """Retrieve a node by its identifier."""
        return self._nodes.get(stage_id)

    def get_edges(self, stage_id: str) -> Set[str]:
        """Get all outgoing edges from a given stage."""
        return self._edges.get(stage_id, set())

    @property
    def nodes(self) -> Dict[str, StageNode]:
        return dict(self._nodes)

    @property
    def edges(self) -> Dict[str, Set[str]]:
        return {k: set(v) for k, v in self._edges.items()}


class TopologicalSorter:
    """Produces a topological ordering of stages in a DAG.

    Uses Kahn's algorithm for O(V + E) sorting with cycle detection.
    """

    def __init__(self, graph: DependencyGraph) -> None:
        self._graph = graph

    def sort(self) -> Tuple[List[str], List[str]]:
        """Return (ordered_stages, warnings).

        Raises ValueError if the graph contains a cycle.
        """
        in_degree: Dict[str, int] = {}
        adjacency: Dict[str, List[str]] = defaultdict(list)

        for node_id in self._graph.nodes:
            in_degree.setdefault(node_id, 0)

        for source, targets in self._graph.edges.items():
            for target in targets:
                adjacency[source].append(target)
                in_degree[target] = in_degree.get(target, 0) + 1

        queue = deque([n for n, d in in_degree.items() if d == 0])
        ordered: List[str] = []

        while queue:
            node = queue.popleft()
            ordered.append(node)
            for neighbour in adjacency[node]:
                in_degree[neighbour] -= 1
                if in_degree[neighbour] == 0:
                    queue.append(neighbour)

        warnings: List[str] = []
        if len(ordered) != len(self._graph.nodes):
            missing = set(self._graph.nodes) - set(ordered)
            raise ValueError(
                f"Cycle detected involving stages: {missing}")

        return ordered, warnings


class PipelineBuilder:
    """Builder for constructing executable pipelines from stage definitions.

    Provides a fluent interface for registering stages, resolving
    inter-stage dependencies, building the execution graph, and
    producing a topologically sorted execution order.
    """

    def __init__(self) -> None:
        self._graph = DependencyGraph()

    def register_stage(self, definition: StageDefinition,
                       stage_id: Optional[str] = None) -> "PipelineBuilder":
        """Register a stage definition with the pipeline."""
        node = StageNode(definition=definition,
                         stage_id=stage_id or definition.name)
        self._graph.add_node(node)
        return self

    def resolve_dependencies(self) -> "PipelineBuilder":
        """Walk all registered stages and add dependency edges to the graph."""
        for stage_id, node in self._graph.nodes.items():
            for dep in node.definition.dependencies:
                target_id = dep.source_stage
                if self._graph.has_node(target_id):
                    self._graph.add_edge(target_id, stage_id)
        return self

    def build(self) -> BuildResult:
        """Construct the execution graph and produce a build result.

        Returns a BuildResult containing the graph, topological order,
        and any warnings discovered during the build.
        """
        self.resolve_dependencies()
        sorter = TopologicalSorter(self._graph)
        warnings: List[str] = []

        order: List[str] = []
        try:
            order, sort_warnings = sorter.sort()
            warnings.extend(sort_warnings)
        except ValueError as exc:
            warnings.append(f"Sorting failed: {exc}")
            order = list(self._graph.nodes.keys())

        return BuildResult(graph=self._graph, order=order, warnings=warnings)
