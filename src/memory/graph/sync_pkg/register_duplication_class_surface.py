"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

import ast

from memory.graph.sync_pkg._core_ast import _base_name
from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.add_duplication_callable_surface import (
    _add_duplication_callable_surface,
    _duplication_callable_descriptor,
)
from memory.graph.sync_pkg.graph_contexts import (
    ClassDescriptor,
    DuplicateFamilyConfig,
    DuplicationExtractionContext,
)
from memory.graph.sync_pkg.score_family import _semantic_tags

__all__ = [
    "_register_duplication_class_surface",
    "_register_duplication_function_surface",
    "_register_duplication_method_surfaces",
]


def _register_duplication_class_surface(
    context: DuplicationExtractionContext,
    *,
    module_key: NodeKey,
    relative_path: str,
    dotted_path: str,
    family: DuplicateFamilyConfig,
    node: ast.ClassDef,
) -> NodeKey:
    class_key = context.snapshot.add_node(
        "class_surface",
        f"{dotted_path}.{node.name}",
        summary=f"Class surface `{node.name}` from `{dotted_path}`.",
        source_path=relative_path,
        source_kind="python_class_surface",
        family_name=family.name,
        package_family=family.package_family,
        class_name=node.name,
        base_names=sorted(filter(None, (_base_name(base) for base in node.bases))),
        method_count=sum(
            1
            for child in node.body
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
        ),
        is_mixin=node.name.endswith("Mixin"),
        semantic_tags=list(_semantic_tags(relative_path, node.name)),
        last_verified=context.today,
        ingest_wave="repo_sync_v1",
        confidence="medium",
    )
    context.snapshot.add_relation(
        module_key, "DECLARES", class_key, provenance="code_duplication"
    )
    context.class_descriptors[class_key] = ClassDescriptor(
        node_key=class_key,
        family_name=family.name,
        package_family=family.package_family,
        source_path=relative_path,
        class_name=node.name,
        base_names=tuple(
            sorted(filter(None, (_base_name(base) for base in node.bases)))
        ),
        method_names=tuple(
            child.name
            for child in node.body
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
        ),
    )
    context.class_name_index.setdefault(node.name, []).append(class_key)
    return class_key


def _register_duplication_method_surfaces(
    context: DuplicationExtractionContext,
    *,
    relative_path: str,
    dotted_path: str,
    family: DuplicateFamilyConfig,
    class_key: NodeKey,
    class_name: str,
    class_body: list[ast.stmt],
) -> None:
    for child in class_body:
        if not isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        method_key = _add_duplication_callable_surface(
            context,
            relative_path=relative_path,
            family=family,
            node=child,
            surface_label="method_surface",
            source_kind="python_method_surface",
            summary=f"Method surface `{class_name}.{child.name}` from `{dotted_path}`.",
            surface_name=f"{dotted_path}.{class_name}.{child.name}",
            parent_class=class_name,
        )
        context.snapshot.add_relation(
            class_key, "DECLARES", method_key, provenance="code_duplication"
        )
        context.callable_descriptors[method_key] = _duplication_callable_descriptor(
            context,
            method_key,
            family=family,
            relative_path=relative_path,
            callable_name=child.name,
            parent_class=class_name,
            surface_kind="method_surface",
        )


def _register_duplication_function_surface(
    context: DuplicationExtractionContext,
    *,
    module_key: NodeKey,
    relative_path: str,
    dotted_path: str,
    family: DuplicateFamilyConfig,
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> None:
    function_key = _add_duplication_callable_surface(
        context,
        relative_path=relative_path,
        family=family,
        node=node,
        surface_label="function_surface",
        source_kind="python_function_surface",
        summary=f"Function surface `{node.name}` from `{dotted_path}`.",
        surface_name=f"{dotted_path}.{node.name}",
    )
    context.snapshot.add_relation(
        module_key, "DECLARES", function_key, provenance="code_duplication"
    )
    context.callable_descriptors[function_key] = _duplication_callable_descriptor(
        context,
        function_key,
        family=family,
        relative_path=relative_path,
        callable_name=node.name,
        parent_class=None,
        surface_kind="function_surface",
    )
