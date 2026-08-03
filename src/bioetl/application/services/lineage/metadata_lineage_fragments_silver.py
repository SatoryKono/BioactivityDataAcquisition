"""Silver-layer lineage fragment builder."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from bioetl.application.services.lineage._fragment_assembly import (
    build_dataset_fragment_nodes,
)
from bioetl.application.services.lineage._fragment_finalization import (
    finalize_lineage_fragment,
)
from bioetl.application.services.lineage.metadata_lineage_nodes import (
    bronze_batch_nodes_for_silver,
    fragment_timestamp,
    manifest_edges,
    manifest_node,
    silver_dataset_node,
    transform_edges,
)
from bioetl.domain.lineage import (
    LineageEdge,
    LineageEdgeType,
    LineageGraphFragment,
    LineageNodeRef,
    LineageNodeType,
)

if TYPE_CHECKING:
    from bioetl.domain.ports import SilverMetadataInput
    from bioetl.domain.value_objects.run_context import RunContext


def _find_run_node(
    *,
    nodes: list[LineageNodeRef],
    run_context: RunContext,
) -> LineageNodeRef:
    """Return the canonical run node for this fragment or raise a clear error."""
    run_id = str(run_context.run_id)
    for node in nodes:
        if (
            node.node_type == LineageNodeType.RUN
            and node.attributes.get("run_id") == run_id
        ):
            return node
    raise ValueError(f"Run node missing from silver lineage fragment: {run_id}")


def _find_silver_dataset_node(
    *,
    nodes: list[LineageNodeRef],
    run_context: RunContext,
    version_after: int | None,
) -> LineageNodeRef:
    """Return the persisted Silver dataset node for this fragment."""
    version_suffix = f"@{version_after}" if version_after is not None else ""
    expected_node_id = (
        f"silver:{run_context.provider}.{run_context.entity}{version_suffix}"
    )
    for node in nodes:
        if (
            node.node_type == LineageNodeType.DATASET
            and node.node_id == expected_node_id
        ):
            return node
    raise ValueError(
        f"Silver dataset node missing from lineage fragment: {expected_node_id}"
    )


def _build_silver_nodes(
    run_context: RunContext,
    input_data: SilverMetadataInput,
    created_at: datetime,
) -> tuple[list[LineageNodeRef], list[LineageEdge]]:
    """Build all nodes for the silver lineage fragment."""
    bronze_nodes = bronze_batch_nodes_for_silver(
        run_context=run_context,
        input_data=input_data,
    )
    return build_dataset_fragment_nodes(
        run_context=run_context,
        dataset_node=silver_dataset_node(
            run_context=run_context, input_data=input_data
        ),
        records=tuple(input_data.records or ()),
        composite_name=f"{run_context.provider}.{run_context.entity}",
        created_at=created_at,
        composite_run_id=input_data.composite_run_id,
        lineage_created_at=input_data.lineage_created_at,
        source_nodes=bronze_nodes,
        transform_version=input_data.transform_version,
        transform_steps=input_data.transform_steps,
        extra_nodes=[],
    )


def _build_silver_edges(
    run_context: RunContext,
    input_data: SilverMetadataInput,
    nodes: list[LineageNodeRef],
    created_at: datetime,
    composite_source_edges: list[LineageEdge],
) -> list[LineageEdge]:
    """Build all edges for the silver lineage fragment."""
    run = _find_run_node(nodes=nodes, run_context=run_context)
    silver_dataset = _find_silver_dataset_node(
        nodes=nodes,
        run_context=run_context,
        version_after=input_data.version_after,
    )
    bronze_nodes = [
        node for node in nodes if node.node_type == LineageNodeType.BRONZE_BATCH
    ]
    lineage_transform_nodes = [
        node for node in nodes if node.node_type == LineageNodeType.TRANSFORM
    ]

    edges: list[LineageEdge] = list(
        manifest_edges(
            manifest=manifest_node(run_context),
            run=run,
            created_at=created_at,
            run_context=run_context,
        )
    )

    edges.extend(
        LineageEdge(
            edge_type=LineageEdgeType.DERIVED_FROM,
            source=silver_dataset,
            target=bronze_node,
            run_id=str(run_context.run_id),
            manifest_id=run_context.manifest_id,
            created_at=created_at,
        )
        for bronze_node in bronze_nodes
    )

    edges.extend(composite_source_edges)

    if lineage_transform_nodes:
        edges.extend(
            transform_edges(
                run_context=run_context,
                run=run,
                transforms=lineage_transform_nodes,
                created_at=created_at,
            )
        )
        edges.append(
            LineageEdge(
                edge_type=LineageEdgeType.PRODUCED_BY,
                source=silver_dataset,
                target=lineage_transform_nodes[-1],
                run_id=str(run_context.run_id),
                manifest_id=run_context.manifest_id,
                created_at=created_at,
            )
        )
    else:
        edges.append(
            LineageEdge(
                edge_type=LineageEdgeType.PRODUCED_BY,
                source=silver_dataset,
                target=run,
                run_id=str(run_context.run_id),
                manifest_id=run_context.manifest_id,
                created_at=created_at,
            )
        )

    return edges


def build_silver_lineage_fragment(
    *,
    run_context: RunContext,
    input_data: SilverMetadataInput,
) -> LineageGraphFragment:
    """Build canonical Silver lineage fragment from metadata input."""
    created_at = fragment_timestamp(
        input_data.completed_at,
        input_data.started_at,
        run_context.started_at,
    )

    # Build nodes
    nodes, composite_source_edges = _build_silver_nodes(
        run_context, input_data, created_at
    )

    # Build edges
    edges = _build_silver_edges(
        run_context, input_data, nodes, created_at, composite_source_edges
    )

    return finalize_lineage_fragment(
        fragment_name="silver",
        run_context=run_context,
        nodes=nodes,
        edges=edges,
        created_at=created_at,
    )
