"""Gold-layer lineage fragment builder."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from bioetl.application.services.lineage.metadata_lineage_composite import (
    _build_dataset_composite_lineage_components,
)
from bioetl.application.services.lineage._fragment_finalization import (
    finalize_lineage_fragment,
)
from bioetl.application.services.lineage.metadata_lineage_nodes import (
    fragment_timestamp,
    gold_dataset_node,
    manifest_edges,
    manifest_node,
    resolve_transform_metadata,
    run_node,
    schema_node,
    silver_source_nodes,
    transform_edges,
    transform_nodes,
)
from bioetl.domain.lineage import (
    LineageEdge,
    LineageEdgeType,
    LineageGraphFragment,
    LineageNodeRef,
    LineageNodeType,
)

if TYPE_CHECKING:
    from bioetl.domain.ports import GoldMetadataInput
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
    raise ValueError(f"Run node missing from gold lineage fragment: {run_id}")


def _find_gold_dataset_node(
    *,
    nodes: list[LineageNodeRef],
    table_name: str,
) -> LineageNodeRef:
    """Return the persisted Gold dataset node for this fragment."""
    expected_node_id = f"gold:{table_name}"
    for node in nodes:
        if (
            node.node_type == LineageNodeType.DATASET
            and node.node_id == expected_node_id
        ):
            return node
    raise ValueError(
        f"Gold dataset node missing from lineage fragment: {expected_node_id}"
    )


def _build_gold_nodes(
    run_context: RunContext,
    input_data: GoldMetadataInput,
    created_at: datetime,
) -> tuple[list[LineageNodeRef], list[LineageEdge]]:
    """Build all nodes for the gold lineage fragment."""
    run = run_node(run_context)
    manifest = manifest_node(run_context)
    gold_dataset, composite_source_nodes, composite_source_edges = (
        _build_dataset_composite_lineage_components(
            run_context=run_context,
            dataset_node=gold_dataset_node(
                run_context=run_context, input_data=input_data
            ),
            records=input_data.records,
            composite_name=input_data.table_name,
            created_at=created_at,
            composite_run_id=input_data.composite_run_id,
            lineage_created_at=input_data.lineage_created_at,
        )
    )
    silver_nodes = silver_source_nodes(input_data)
    gold_schema_node = schema_node(input_data)
    transform_version, transform_steps = resolve_transform_metadata(
        run_context=run_context,
        transform_version=input_data.transform_version,
        transform_steps=input_data.transform_steps,
    )
    lineage_transform_nodes = transform_nodes(
        run_context=run_context,
        transform_version=transform_version,
        transform_steps=transform_steps,
    )

    nodes = [
        run,
        gold_dataset,
        *silver_nodes,
        *lineage_transform_nodes,
        *composite_source_nodes,
    ]

    if manifest is not None:
        nodes.append(manifest)
    if gold_schema_node is not None:
        nodes.append(gold_schema_node)

    return nodes, composite_source_edges


def _build_gold_edges(
    run_context: RunContext,
    input_data: GoldMetadataInput,
    nodes: list[LineageNodeRef],
    created_at: datetime,
    composite_source_edges: list[LineageEdge],
) -> list[LineageEdge]:
    """Build all edges for the gold lineage fragment."""
    run = _find_run_node(nodes=nodes, run_context=run_context)
    gold_dataset = _find_gold_dataset_node(
        nodes=nodes, table_name=input_data.table_name
    )
    silver_nodes = [
        node
        for node in nodes
        if node.node_type == LineageNodeType.DATASET
        and node.attributes.get("layer") == "silver"
    ]
    lineage_transform_nodes = [
        node for node in nodes if node.node_type == LineageNodeType.TRANSFORM
    ]
    gold_schema_node = next(
        (node for node in nodes if node.node_type == LineageNodeType.SCHEMA),
        None,
    )
    manifest = manifest_node(run_context)

    edges = list(
        manifest_edges(
            manifest=manifest,
            run=run,
            created_at=created_at,
            run_context=run_context,
        )
    )
    schema_edge = _build_gold_schema_edge(
        run_context=run_context,
        gold_dataset=gold_dataset,
        gold_schema_node=gold_schema_node,
        created_at=created_at,
    )
    if schema_edge is not None:
        edges.append(schema_edge)
    edges.extend(
        _build_gold_dataset_input_edges(
            run_context=run_context,
            gold_dataset=gold_dataset,
            silver_nodes=silver_nodes,
            composite_source_edges=composite_source_edges,
            created_at=created_at,
        )
    )
    edges.extend(
        _build_gold_production_edges(
            run_context=run_context,
            gold_dataset=gold_dataset,
            run=run,
            lineage_transform_nodes=lineage_transform_nodes,
            created_at=created_at,
        )
    )
    return edges


def _build_gold_schema_edge(
    *,
    run_context: RunContext,
    gold_dataset: LineageNodeRef,
    gold_schema_node: LineageNodeRef | None,
    created_at: datetime,
) -> LineageEdge | None:
    """Return the schema edge for a Gold dataset when a schema node exists."""
    if gold_schema_node is None:
        return None
    return LineageEdge(
        edge_type=LineageEdgeType.USED_SCHEMA,
        source=gold_dataset,
        target=gold_schema_node,
        run_id=str(run_context.run_id),
        manifest_id=run_context.manifest_id,
        created_at=created_at,
    )


def _build_gold_dataset_input_edges(
    *,
    run_context: RunContext,
    gold_dataset: LineageNodeRef,
    silver_nodes: list[LineageNodeRef],
    composite_source_edges: list[LineageEdge],
    created_at: datetime,
) -> list[LineageEdge]:
    """Return all dataset-input edges feeding the Gold dataset."""
    edges = [
        LineageEdge(
            edge_type=LineageEdgeType.DERIVED_FROM,
            source=gold_dataset,
            target=silver_node,
            run_id=str(run_context.run_id),
            manifest_id=run_context.manifest_id,
            created_at=created_at,
        )
        for silver_node in silver_nodes
    ]
    edges.extend(composite_source_edges)
    return edges


def _build_gold_production_edges(
    *,
    run_context: RunContext,
    gold_dataset: LineageNodeRef,
    run: LineageNodeRef,
    lineage_transform_nodes: list[LineageNodeRef],
    created_at: datetime,
) -> list[LineageEdge]:
    """Return transform/run edges that explain Gold dataset production."""
    if not lineage_transform_nodes:
        return [
            LineageEdge(
                edge_type=LineageEdgeType.PRODUCED_BY,
                source=gold_dataset,
                target=run,
                run_id=str(run_context.run_id),
                manifest_id=run_context.manifest_id,
                created_at=created_at,
            )
        ]
    edges = list(
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
            source=gold_dataset,
            target=lineage_transform_nodes[-1],
            run_id=str(run_context.run_id),
            manifest_id=run_context.manifest_id,
            created_at=created_at,
        )
    )
    return edges


def build_gold_lineage_fragment(
    *,
    run_context: RunContext,
    input_data: GoldMetadataInput,
) -> LineageGraphFragment:
    """Build canonical Gold lineage fragment from metadata input."""
    created_at = fragment_timestamp(
        input_data.completed_at,
        input_data.started_at,
        run_context.started_at,
    )

    # Build nodes
    nodes, composite_source_edges = _build_gold_nodes(
        run_context, input_data, created_at
    )

    # Build edges
    edges = _build_gold_edges(
        run_context, input_data, nodes, created_at, composite_source_edges
    )

    return finalize_lineage_fragment(
        fragment_name="gold",
        run_context=run_context,
        nodes=nodes,
        edges=edges,
        created_at=created_at,
    )
