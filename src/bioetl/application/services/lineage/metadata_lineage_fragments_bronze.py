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
    LineageNodeRef,
    LineageNodeType,
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
    if _is_cached_bronze_source(input_data):
        consumption = _cached_bronze_consumption_node(
            run_context=run_context,
            bronze_batch=bronze_batch,
        )
        nodes.append(consumption)
        edges.extend(
            [
                LineageEdge(
                    edge_type=LineageEdgeType.CONSUMED_BY,
                    source=bronze_batch,
                    target=consumption,
                    run_id=str(run_context.run_id),
                    manifest_id=run_context.manifest_id,
                    created_at=created_at,
                ),
                LineageEdge(
                    edge_type=LineageEdgeType.EXECUTED_IN,
                    source=consumption,
                    target=run,
                    run_id=str(run_context.run_id),
                    manifest_id=run_context.manifest_id,
                    created_at=created_at,
                ),
            ]
        )
    # Cached consumption still writes a new Bronze batch for this run. Trust
    # sidecars require PRODUCED_BY on that written batch; CONSUMED_BY above
    # records cache use without cloning the original cache occurrence.
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


def _is_cached_bronze_source(input_data: object) -> bool:
    """Return True when Bronze input is a cached-Bronze consumption, not a live fetch."""
    source = getattr(input_data, "source_metadata", None)
    return getattr(source, "type", None) == "cached_bronze"


def _cached_bronze_consumption_node(
    *,
    run_context: RunContext,
    bronze_batch: LineageNodeRef,
) -> LineageNodeRef:
    """Occurrence node for the current run consuming an existing Bronze batch."""
    batch_id = str(bronze_batch.attributes.get("batch_id") or bronze_batch.node_id)
    return LineageNodeRef(
        node_type=LineageNodeType.CONSUMPTION,
        node_id=f"consumption:{run_context.run_id}:{batch_id}",
        label=f"{run_context.provider}.{run_context.entity}",
        attributes={
            "run_id": str(run_context.run_id),
            "manifest_id": run_context.manifest_id,
            "batch_id": batch_id,
            "source_type": "cached_bronze",
        },
    )
