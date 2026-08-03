"""Shared helpers for finalizing lineage graph fragments."""

from __future__ import annotations

from datetime import datetime

from bioetl.application.services.lineage.metadata_lineage_nodes import (
    build_semantic_fragment_id,
    dedupe_nodes,
)
from bioetl.domain.lineage import LineageEdge, LineageGraphFragment, LineageNodeRef
from bioetl.domain.value_objects.run_context import RunContext


def finalize_lineage_fragment(
    *,
    fragment_name: str,
    run_context: RunContext,
    nodes: list[LineageNodeRef],
    edges: list[LineageEdge],
    created_at: datetime,
) -> LineageGraphFragment:
    """Build the canonical lineage fragment envelope for one layer."""
    deduped_nodes = dedupe_nodes(nodes)
    return LineageGraphFragment(
        fragment_id=build_semantic_fragment_id(
            fragment_name,
            nodes=deduped_nodes,
            edges=edges,
        ),
        nodes=deduped_nodes,
        edges=tuple(edges),
        run_id=str(run_context.run_id),
        manifest_id=run_context.manifest_id,
        created_at=created_at,
    )
