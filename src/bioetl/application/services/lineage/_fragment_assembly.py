"""Shared assembly helpers for dataset-oriented lineage fragments."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from bioetl.application.services.lineage.metadata_lineage_composite import (
    _build_dataset_composite_lineage_components,
)
from bioetl.application.services.lineage.metadata_lineage_nodes import (
    manifest_node,
    resolve_transform_metadata,
    run_node,
    transform_nodes,
)
from bioetl.domain.lineage import LineageEdge, LineageNodeRef

if TYPE_CHECKING:
    from bioetl.domain.value_objects.run_context import RunContext


def build_dataset_fragment_nodes(
    *,
    run_context: RunContext,
    dataset_node: LineageNodeRef,
    records: list[dict[str, object]],
    composite_name: str,
    created_at: datetime,
    composite_run_id: str | None,
    lineage_created_at: datetime | None,
    source_nodes: list[LineageNodeRef],
    transform_version: str | None,
    transform_steps: tuple[str, ...] | list[str] | None,
    extra_nodes: list[LineageNodeRef],
) -> tuple[list[LineageNodeRef], list[LineageEdge]]:
    """Build the common node shell for Silver/Gold dataset fragments."""
    run = run_node(run_context)
    manifest = manifest_node(run_context)
    dataset, composite_source_nodes, composite_source_edges = (
        _build_dataset_composite_lineage_components(
            run_context=run_context,
            dataset_node=dataset_node,
            records=records,
            composite_name=composite_name,
            created_at=created_at,
            composite_run_id=composite_run_id,
            lineage_created_at=lineage_created_at,
        )
    )
    resolved_transform_version, resolved_transform_steps = resolve_transform_metadata(
        run_context=run_context,
        transform_version=transform_version,
        transform_steps=transform_steps,
    )
    lineage_transform_nodes = transform_nodes(
        run_context=run_context,
        transform_version=resolved_transform_version,
        transform_steps=resolved_transform_steps,
    )

    nodes = [
        run,
        dataset,
        *source_nodes,
        *lineage_transform_nodes,
        *composite_source_nodes,
        *extra_nodes,
    ]
    if manifest is not None:
        nodes.append(manifest)
    return nodes, composite_source_edges
