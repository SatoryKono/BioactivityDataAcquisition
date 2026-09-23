"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

import ast

from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.graph_contexts import (
    CallableDescriptor,
    DuplicateFamilyConfig,
    DuplicationExtractionContext,
)
from memory.graph.sync_pkg.register_duplication_class_surface import (
    _register_duplication_class_surface,
    _register_duplication_function_surface,
    _register_duplication_method_surfaces,
)

__all__ = [
    "_collect_duplication_class_descriptors",
    "_collect_duplication_function_descriptor",
    "_duplication_class_method_index",
]


def _collect_duplication_class_descriptors(
    context: DuplicationExtractionContext,
    *,
    module_key: NodeKey,
    relative_path: str,
    dotted_path: str,
    family: DuplicateFamilyConfig,
    node: ast.ClassDef,
) -> None:
    class_key = _register_duplication_class_surface(
        context,
        module_key=module_key,
        relative_path=relative_path,
        dotted_path=dotted_path,
        family=family,
        node=node,
    )
    _register_duplication_method_surfaces(
        context,
        relative_path=relative_path,
        dotted_path=dotted_path,
        family=family,
        class_key=class_key,
        class_name=node.name,
        class_body=node.body,
    )


def _collect_duplication_function_descriptor(
    context: DuplicationExtractionContext,
    *,
    module_key: NodeKey,
    relative_path: str,
    dotted_path: str,
    family: DuplicateFamilyConfig,
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> None:
    _register_duplication_function_surface(
        context,
        module_key=module_key,
        relative_path=relative_path,
        dotted_path=dotted_path,
        family=family,
        node=node,
    )


def _duplication_class_method_index(
    callable_descriptors: dict[NodeKey, CallableDescriptor],
) -> dict[tuple[NodeKey, str], NodeKey]:
    class_method_index: dict[tuple[NodeKey, str], NodeKey] = {}
    for callable_descriptor in callable_descriptors.values():
        if (
            callable_descriptor.surface_kind != "method_surface"
            or callable_descriptor.parent_class is None
        ):
            continue
        owner_name = callable_descriptor.node_key.name.rsplit(".", 1)[0]
        class_method_index[
            (NodeKey("class_surface", owner_name), callable_descriptor.callable_name)
        ] = callable_descriptor.node_key
    return class_method_index
