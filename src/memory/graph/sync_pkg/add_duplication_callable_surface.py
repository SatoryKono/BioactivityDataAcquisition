"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

import ast

from memory.graph.sync_pkg._core_ast import (
    _callable_ast_node_count,
    _callable_branch_count,
    _callable_call_count,
    _callable_helper_call_count,
    _callable_max_nesting_depth,
    _normalized_callable_hash,
    _signature_hash,
)
from memory.graph.sync_pkg._core_convert import _coerce_int
from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.graph_contexts import (
    CallableDescriptor,
    DuplicateFamilyConfig,
    DuplicationExtractionContext,
)
from memory.graph.sync_pkg.score_family import _semantic_tags

__all__ = [
    "_add_duplication_callable_surface",
    "_duplication_callable_descriptor",
]


def _add_duplication_callable_surface(
    context: DuplicationExtractionContext,
    *,
    relative_path: str,
    family: DuplicateFamilyConfig,
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    surface_label: str,
    source_kind: str,
    summary: str,
    surface_name: str,
    parent_class: str | None = None,
) -> NodeKey:
    return context.snapshot.add_node(
        surface_label,
        surface_name,
        summary=summary,
        source_path=relative_path,
        source_kind=source_kind,
        family_name=family.name,
        package_family=family.package_family,
        callable_name=node.name,
        parent_class=parent_class,
        signature_hash=_signature_hash(node),
        ast_shape_hash=_normalized_callable_hash(node),
        ast_node_count=_callable_ast_node_count(node),
        branch_count=_callable_branch_count(node),
        nesting_depth=_callable_max_nesting_depth(node),
        call_count=_callable_call_count(node),
        helper_call_count=_callable_helper_call_count(node),
        semantic_tags=list(_semantic_tags(relative_path, node.name)),
        last_verified=context.today,
        ingest_wave="repo_sync_v1",
        confidence="medium",
    )


def _duplication_callable_descriptor(
    context: DuplicationExtractionContext,
    node_key: NodeKey,
    *,
    family: DuplicateFamilyConfig,
    relative_path: str,
    callable_name: str,
    parent_class: str | None,
    surface_kind: str,
) -> CallableDescriptor:
    callable_node = context.snapshot.nodes[node_key]
    return CallableDescriptor(
        node_key=node_key,
        family_name=family.name,
        package_family=family.package_family,
        source_path=relative_path,
        callable_name=callable_name,
        parent_class=parent_class,
        surface_kind=surface_kind,
        ast_shape_hash=str(callable_node.properties["ast_shape_hash"]),
        signature_hash=str(callable_node.properties["signature_hash"]),
        ast_node_count=_coerce_int(callable_node.properties["ast_node_count"]),
        semantic_tags=tuple(_semantic_tags(relative_path, callable_name)),
    )
