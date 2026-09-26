"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from memory.graph.sync_pkg._core_convert import _as_string_list, _coerce_int
from memory.graph.sync_pkg._core_models import ComplexityMetrics, NodeKey
from memory.graph.sync_pkg.graph_contexts import SurfaceRelationIndexes
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot

__all__ = [
    "_aggregate_callable_metrics",
    "_aggregate_surface_complexity_metrics",
    "_callable_surface_complexity_metrics",
    "_casefolded_markers",
    "_class_surface_complexity_metrics",
    "_int_node_property",
    "_module_surface_complexity_metrics",
]


def _int_node_property(
    snapshot: GraphSnapshot, node_key: NodeKey, property_name: str
) -> int:
    node = snapshot.nodes.get(node_key)
    if node is None:
        return 0
    raw_value = node.properties.get(property_name)
    return _coerce_int(raw_value, 0) if isinstance(raw_value, (int, float, str)) else 0


def _aggregate_callable_metrics(
    snapshot: GraphSnapshot, node_key: NodeKey
) -> tuple[int, int, int, int]:
    return (
        _int_node_property(snapshot, node_key, "branch_count"),
        _int_node_property(snapshot, node_key, "nesting_depth"),
        _int_node_property(snapshot, node_key, "call_count"),
        _int_node_property(snapshot, node_key, "helper_call_count"),
    )


def _callable_surface_complexity_metrics(
    snapshot: GraphSnapshot, surface_key: NodeKey
) -> ComplexityMetrics:
    branch_count, nesting_depth, call_count, helper_call_count = (
        _aggregate_callable_metrics(snapshot, surface_key)
    )
    abstraction_fanout = max(1, call_count)
    return ComplexityMetrics(
        branch_count=branch_count,
        nesting_depth=nesting_depth,
        call_count=call_count,
        helper_call_count=helper_call_count,
        abstraction_fanout=abstraction_fanout,
        api_surface_to_logic_ratio=round(
            call_count / max(1, branch_count + nesting_depth), 2
        ),
    )


def _class_surface_complexity_metrics(
    snapshot: GraphSnapshot,
    indexes: SurfaceRelationIndexes,
    surface_key: NodeKey,
) -> ComplexityMetrics:
    methods = [
        child
        for child in indexes.declared_children.get(surface_key, ())
        if child.label == "method_surface"
    ]
    method_metrics = [
        _aggregate_callable_metrics(snapshot, method_key) for method_key in methods
    ]
    branch_count = sum(metric[0] for metric in method_metrics)
    return ComplexityMetrics(
        branch_count=branch_count,
        nesting_depth=max((metric[1] for metric in method_metrics), default=0),
        call_count=sum(metric[2] for metric in method_metrics),
        helper_call_count=sum(metric[3] for metric in method_metrics),
        abstraction_fanout=len(methods),
        api_surface_to_logic_ratio=round(len(methods) / max(1, branch_count + 1), 2),
    )


def _module_surface_complexity_metrics(
    snapshot: GraphSnapshot,
    indexes: SurfaceRelationIndexes,
    surface_key: NodeKey,
) -> ComplexityMetrics:
    children = indexes.declared_children.get(surface_key, ())
    functions = [child for child in children if child.label == "function_surface"]
    classes = [child for child in children if child.label == "class_surface"]
    methods = [
        method_key
        for class_key in classes
        for method_key in indexes.declared_children.get(class_key, ())
        if method_key.label == "method_surface"
    ]
    callable_metrics = [
        *[
            _aggregate_callable_metrics(snapshot, function_key)
            for function_key in functions
        ],
        *[_aggregate_callable_metrics(snapshot, method_key) for method_key in methods],
    ]
    branch_count = sum(metric[0] for metric in callable_metrics)
    abstraction_fanout = len(functions) + len(classes)
    return ComplexityMetrics(
        branch_count=branch_count,
        nesting_depth=max((metric[1] for metric in callable_metrics), default=0),
        call_count=sum(metric[2] for metric in callable_metrics),
        helper_call_count=sum(metric[3] for metric in callable_metrics),
        abstraction_fanout=abstraction_fanout,
        api_surface_to_logic_ratio=round(
            abstraction_fanout / max(1, branch_count + 1), 2
        ),
    )


def _aggregate_surface_complexity_metrics(
    snapshot: GraphSnapshot,
    indexes: SurfaceRelationIndexes,
    surface_key: NodeKey,
) -> ComplexityMetrics:
    if surface_key.label in {"function_surface", "method_surface"}:
        return _callable_surface_complexity_metrics(snapshot, surface_key)

    if surface_key.label == "class_surface":
        return _class_surface_complexity_metrics(snapshot, indexes, surface_key)

    if surface_key.label == "module_surface":
        return _module_surface_complexity_metrics(snapshot, indexes, surface_key)

    return ComplexityMetrics(0, 0, 0, 0, 0, 0.0)


def _casefolded_markers(
    payload: dict[str, object],
    key: str,
    defaults: list[str],
) -> tuple[str, ...]:
    return tuple(
        marker.casefold() for marker in (_as_string_list(payload.get(key)) or defaults)
    )
