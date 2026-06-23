"""Transform lineage node and edge builders."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from bioetl.application.services.lineage.metadata_assemblers_helpers import (
    _resolve_transform_metadata,
)
from bioetl.domain.lineage import (
    LineageEdge,
    LineageEdgeType,
    LineageNodeRef,
    TransformRef,
)

if TYPE_CHECKING:
    from bioetl.domain.value_objects.run_context import RunContext


def transform_nodes(
    *,
    run_context: RunContext,
    transform_version: str | None,
    transform_steps: tuple[str, ...] | list[str],
) -> list[LineageNodeRef]:
    """Build ordered transform nodes for lineage fragments."""
    return [
        TransformRef(
            name=step,
            version=transform_version,
            step_index=index,
            pipeline_name=run_context.pipeline_name,
        ).to_node_ref()
        for index, step in enumerate(transform_steps, start=1)
    ]


def transform_edges(
    *,
    run_context: RunContext,
    run: LineageNodeRef,
    transforms: list[LineageNodeRef],
    created_at: datetime,
) -> list[LineageEdge]:
    """Build transform chain edges and run anchors."""
    edges: list[LineageEdge] = []
    previous: LineageNodeRef | None = None
    for transform in transforms:
        edges.append(
            LineageEdge(
                edge_type=LineageEdgeType.EXECUTED_IN,
                source=transform,
                target=run,
                run_id=str(run_context.run_id),
                manifest_id=run_context.manifest_id,
                created_at=created_at,
            )
        )
        if previous is not None:
            edges.append(
                LineageEdge(
                    edge_type=LineageEdgeType.DERIVED_FROM,
                    source=transform,
                    target=previous,
                    run_id=str(run_context.run_id),
                    manifest_id=run_context.manifest_id,
                    created_at=created_at,
                )
            )
        previous = transform
    return edges


def resolve_transform_metadata(
    *,
    run_context: RunContext,
    transform_version: str | None,
    transform_steps: tuple[str, ...] | list[str] | None,
) -> tuple[str, list[str]]:
    """Resolve transform metadata through the canonical shared helper."""
    resolved = _resolve_transform_metadata(
        run_context=run_context,
        transform_version=transform_version,
        transform_steps=transform_steps,
    )
    return str(resolved[0]), [str(step) for step in resolved[1]]


__all__ = [
    "resolve_transform_metadata",
    "transform_edges",
    "transform_nodes",
]
