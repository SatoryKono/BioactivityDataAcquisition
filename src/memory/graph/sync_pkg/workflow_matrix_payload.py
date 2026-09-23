"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from memory.graph.sync_pkg._core_convert import _normalize_workflow_matrix_axis_name
from memory.graph.sync_pkg.workflow_matrix_axis_values import (
    _append_workflow_matrix_include_variants,
    _workflow_matrix_axis_values,
    _workflow_matrix_base_variants,
)

__all__ = [
    "_workflow_matrix_base_axes",
    "_workflow_matrix_payload",
    "_workflow_matrix_variants_with_includes",
]


def _workflow_matrix_payload(job_payload: dict[str, object]) -> object:
    strategy_payload = job_payload.get("strategy")
    if not isinstance(strategy_payload, dict):
        return None
    return strategy_payload.get("matrix")


def _workflow_matrix_variants_with_includes(
    base_axes: list[tuple[str, list[str]]],
    include_payload: object,
) -> tuple[dict[str, str], ...]:
    variants = _workflow_matrix_base_variants(base_axes)
    _append_workflow_matrix_include_variants(variants, include_payload)
    return tuple(variants)


def _workflow_matrix_base_axes(
    matrix_payload: dict[str, object],
) -> list[tuple[str, list[str]]] | None:
    base_axes: list[tuple[str, list[str]]] = []
    for axis_name, axis_values in matrix_payload.items():
        if axis_name in {"include", "exclude"}:
            continue
        normalized = _workflow_matrix_axis_values(axis_values)
        if not normalized:
            return None
        normalized_axis_name = _normalize_workflow_matrix_axis_name(str(axis_name))
        base_axes.append((normalized_axis_name, normalized))
    return base_axes
