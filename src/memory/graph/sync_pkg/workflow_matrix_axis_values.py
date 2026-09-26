"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

import itertools
import re
from pathlib import Path

from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.default_batch_size import GITHUB_WORKFLOWS_PREFIX
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot
from memory.graph.sync_pkg.workflow_output_expression import _workflow_output_expression

__all__ = [
    "_append_workflow_matrix_include_variants",
    "_attach_workflow_file_backing",
    "_workflow_action_key",
    "_workflow_matrix_axis_values",
    "_workflow_matrix_base_variants",
    "_workflow_output_specs",
    "_workflow_reusable_target",
    "_workflow_secret_refs",
]


def _workflow_matrix_axis_values(axis_values: object) -> list[str]:
    if isinstance(axis_values, list):
        return [
            str(item.get("name"))
            if isinstance(item, dict) and item.get("name") is not None
            else str(item)
            for item in axis_values
        ]
    return [str(axis_values)]


def _workflow_matrix_base_variants(
    base_axes: list[tuple[str, list[str]]],
) -> list[dict[str, str]]:
    variants: list[dict[str, str]] = []
    axis_names = [axis_name for axis_name, _ in base_axes]
    axis_values_product = itertools.product(*(values for _, values in base_axes))
    for values in axis_values_product:
        variants.append(dict(zip(axis_names, values, strict=False)))
        if len(variants) >= 16:
            break
    return variants


def _append_workflow_matrix_include_variants(
    variants: list[dict[str, str]],
    include_payload: object,
) -> None:
    if not isinstance(include_payload, list):
        return
    for include_item in include_payload:
        if not isinstance(include_item, dict):
            continue
        include_variant = {str(key): str(value) for key, value in include_item.items()}
        if include_variant and include_variant not in variants:
            variants.append(include_variant)
            if len(variants) >= 16:
                break


def _workflow_secret_refs(payload: object) -> tuple[str, ...]:
    secret_pattern = re.compile(r"secrets\.(\w+)")
    found: set[str] = set()

    def _visit(value: object) -> None:
        if isinstance(value, str):
            for match in secret_pattern.finditer(value):
                found.add(match.group(1))
            return
        if isinstance(value, dict):
            for nested in value.values():
                _visit(nested)
            return
        if isinstance(value, list):
            for nested in value:
                _visit(nested)

    _visit(payload)
    return tuple(sorted(found))


def _workflow_action_key(uses_ref: str) -> str:
    return uses_ref.split("@", 1)[0]


def _workflow_reusable_target(uses_ref: str) -> tuple[str | None, str]:
    normalized = _workflow_action_key(uses_ref)
    if normalized.startswith(f"./{GITHUB_WORKFLOWS_PREFIX}"):
        return Path(normalized).stem, "local_reusable_workflow"
    if GITHUB_WORKFLOWS_PREFIX in normalized:
        workflow_name = Path(normalized.split(GITHUB_WORKFLOWS_PREFIX, 1)[1]).stem
        return workflow_name, "remote_reusable_workflow"
    return None, "github_action"


def _workflow_output_specs(
    workflow_name: str,
    owner_name: str,
    outputs_payload: object,
    *,
    scope: str,
) -> tuple[tuple[str, str | None], ...]:
    if not isinstance(outputs_payload, dict):
        return ()
    return tuple(
        (
            f"{workflow_name}::{scope}::{owner_name}::{output_name}",
            _workflow_output_expression(output_value),
        )
        for output_name, output_value in outputs_payload.items()
    )


def _attach_workflow_file_backing(
    snapshot: GraphSnapshot, workflow: NodeKey, relative_path: str
) -> None:
    parent_dir_relative = Path(relative_path).parent.as_posix()
    parent_dir_candidates = {
        parent_dir_relative,
        parent_dir_relative.replace("\\", "/"),
    }
    for candidate in sorted(parent_dir_candidates):
        parent_dir_key = NodeKey("directory_surface", candidate)
        if parent_dir_key in snapshot.nodes:
            snapshot.add_relation(
                parent_dir_key,
                "HOUSES",
                workflow,
                provenance="file_structure",
            )

    file_surface_candidates = {
        relative_path,
        relative_path.replace("\\", "/"),
    }
    for candidate in sorted(file_surface_candidates):
        file_surface_key = NodeKey("file_surface", candidate)
        if file_surface_key in snapshot.nodes:
            snapshot.add_relation(
                file_surface_key,
                "BACKS",
                workflow,
                provenance="workflow_graph",
            )
