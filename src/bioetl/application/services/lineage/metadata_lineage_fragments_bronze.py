"""Bronze-layer lineage fragment builder."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.application.services.lineage._fragment_finalization import (
    finalize_lineage_fragment,
)
from bioetl.application.services.lineage.metadata_lineage_nodes import (
    bronze_batch_node_from_input,
    fragment_timestamp,
    manifest_edges,
    manifest_node,
    run_node,
    source_request_node,
    source_system_node,
)
from bioetl.domain.lineage import (
    LineageEdge,
    LineageEdgeType,
    LineageGraphFragment,
)

if TYPE_CHECKING:
    from bioetl.domain.ports import BronzeMetadataInput
    from bioetl.domain.value_objects.run_context import RunContext


def build_bronze_lineage_fragment(
    *,
    run_context: RunContext,
    input_data: BronzeMetadataInput,
) -> LineageGraphFragment:
    """Build canonical Bronze lineage fragment from metadata input."""
    created_at = fragment_timestamp(input_data.completed_at, input_data.started_at)
    run = run_node(run_context)
    manifest = manifest_node(run_context)
    source_system = source_system_node(
        run_context=run_context,
        source_metadata=input_data.source_metadata,
    )
    source_request = source_request_node(run_context=run_context, input_data=input_data)
    bronze_batch = bronze_batch_node_from_input(
        run_context=run_context,
        input_data=input_data,
    )

    nodes = [run, source_system, bronze_batch]
    edges = manifest_edges(
        manifest=manifest,
        run=run,
        created_at=created_at,
        run_context=run_context,
    )
    if manifest is not None:
        nodes.append(manifest)
    if source_request is not None:
        nodes.append(source_request)
        edges.extend(
            [
                LineageEdge(
                    edge_type=LineageEdgeType.DERIVED_FROM,
                    source=source_request,
                    target=source_system,
                    run_id=str(run_context.run_id),
                    manifest_id=run_context.manifest_id,
                    created_at=created_at,
                ),
                LineageEdge(
                    edge_type=LineageEdgeType.DERIVED_FROM,
                    source=bronze_batch,
                    target=source_request,
                    run_id=str(run_context.run_id),
                    manifest_id=run_context.manifest_id,
                    created_at=created_at,
                ),
            ]
        )
    else:
        edges.append(
            LineageEdge(
                edge_type=LineageEdgeType.DERIVED_FROM,
                source=bronze_batch,
                target=source_system,
                run_id=str(run_context.run_id),
                manifest_id=run_context.manifest_id,
                created_at=created_at,
            )
        )
    edges.append(
        LineageEdge(
            edge_type=LineageEdgeType.PRODUCED_BY,
            source=bronze_batch,
            target=run,
            run_id=str(run_context.run_id),
            manifest_id=run_context.manifest_id,
            created_at=created_at,
        )
    )
    return finalize_lineage_fragment(
        fragment_name="bronze",
        run_context=run_context,
        nodes=nodes,
        edges=edges,
        created_at=created_at,
    )
