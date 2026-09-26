"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from collections.abc import Iterable

from memory.graph.sync_pkg._core_convert import _normalize_workflow_matrix_axis_name
from memory.graph.sync_pkg.workflow_matrix_payload import (
    _workflow_matrix_base_axes,
    _workflow_matrix_payload,
    _workflow_matrix_variants_with_includes,
)

__all__ = [
    "_sorted_string_items",
    "_workflow_environment_mapping_name",
    "_workflow_matrix_axes",
    "_workflow_matrix_variants",
]


def _workflow_environment_mapping_name(environment_payload: object) -> str | None:
    if not isinstance(environment_payload, dict):
        return None
    name = environment_payload.get("name")
    return name if isinstance(name, str) else None


def _sorted_string_items(items: Iterable[object]) -> tuple[str, ...]:
    return tuple(sorted(str(item) for item in items if isinstance(item, str)))


def _workflow_matrix_axes(job_payload: dict[str, object]) -> tuple[str, ...]:
    matrix_payload = _workflow_matrix_payload(job_payload)
    if not isinstance(matrix_payload, dict):
        return ()
    return tuple(
        sorted(
            _normalize_workflow_matrix_axis_name(str(key))
            for key in matrix_payload
            if key not in {"include", "exclude"}
        )
    )


def _workflow_matrix_variants(
    job_payload: dict[str, object],
) -> tuple[dict[str, str], ...]:
    matrix_payload = _workflow_matrix_payload(job_payload)
    if not isinstance(matrix_payload, dict):
        return ()

    base_axes = _workflow_matrix_base_axes(matrix_payload)
    if base_axes is None or not base_axes:
        return ()
    return _workflow_matrix_variants_with_includes(
        base_axes, matrix_payload.get("include")
    )
