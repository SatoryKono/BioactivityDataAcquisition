"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

import ast

from memory.graph.sync_pkg._core_ast import _parse_python_ast
from memory.graph.sync_pkg._core_convert import _module_dotted_name
from memory.graph.sync_pkg.collect_duplication_class_descriptors import (
    _collect_duplication_class_descriptors,
    _collect_duplication_function_descriptor,
)
from memory.graph.sync_pkg.graph_contexts import DuplicationExtractionContext
from memory.graph.sync_pkg.graph_snapshot import GraphNode
from memory.graph.sync_pkg.score_family import _family_for_path

__all__ = [
    "_collect_duplication_descriptors_for_module",
]


def _collect_duplication_descriptors_for_module(
    context: DuplicationExtractionContext,
    module: GraphNode,
) -> None:
    relative_path = module.key.name
    family = _family_for_path(relative_path, context.config)
    if family is None:
        return
    module_path = context.root / relative_path
    tree = _parse_python_ast(module_path)
    if tree is None:
        return
    dotted_path = str(
        module.properties.get("dotted_path") or _module_dotted_name(relative_path)
    )
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            _collect_duplication_class_descriptors(
                context,
                module_key=module.key,
                relative_path=relative_path,
                dotted_path=dotted_path,
                family=family,
                node=node,
            )
            continue
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        _collect_duplication_function_descriptor(
            context,
            module_key=module.key,
            relative_path=relative_path,
            dotted_path=dotted_path,
            family=family,
            node=node,
        )
