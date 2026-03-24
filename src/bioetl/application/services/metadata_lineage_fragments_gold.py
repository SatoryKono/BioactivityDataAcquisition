"""Gold-layer lineage fragment builder."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.application.services.metadata_lineage_composite import (
    _build_dataset_composite_lineage_components,
)
from bioetl.application.services.metadata_lineage_nodes import (
    build_fragment_id,
    dedupe_nodes,
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
)

if TYPE_CHECKING:
    from bioetl.domain.ports import GoldMetadataInput
    from bioetl.domain.value_objects.run_context import RunContext


def build_gold_lineage_fragment(
    *,
    run_context: RunContext,
    input_data: GoldMetadataInput,
) -> LineageGraphFragment:
    """Build canonical Gold lineage fragment from metadata input."""
    created_at = fragment_timestamp(input_data.completed_at, input_data.started_at)
    run = run_node(run_context)
    manifest = manifest_node(run_context)
    gold_dataset, composite_source_nodes, composite_source_edges = (
        _build_dataset_composite_lineage_components(
            run_context=run_context,
            dataset_node=gold_dataset_node(run_context=run_context, input_data=input_data),
            records=input_data.records,
            composite_name=input_data.table_name,
            created_at=created_at,
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
    edges = manifest_edges(
        manifest=manifest,
        run=run,
        created_at=created_at,
        run_context=run_context,
    )
    if manifest is not None:
        nodes.append(manifest)
    if gold_schema_node is not None:
        nodes.append(gold_schema_node)
        edges.append(
            LineageEdge(
                edge_type=LineageEdgeType.USED_SCHEMA,
                source=gold_dataset,
                target=gold_schema_node,
                run_id=str(run_context.run_id),
                manifest_id=run_context.manifest_id,
                created_at=created_at,
            )
        )
    edges.extend(
        LineageEdge(
            edge_type=LineageEdgeType.DERIVED_FROM,
            source=gold_dataset,
            target=silver_node,
            run_id=str(run_context.run_id),
            manifest_id=run_context.manifest_id,
            created_at=created_at,
        )
        for silver_node in silver_nodes
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
                source=gold_dataset,
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
                source=gold_dataset,
                target=run,
                run_id=str(run_context.run_id),
                manifest_id=run_context.manifest_id,
                created_at=created_at,
            )
        )
    return LineageGraphFragment(
        fragment_id=build_fragment_id(
            "gold",
            run_context.run_id,
            input_data.table_name,
            input_data.table_path,
        ),
        nodes=dedupe_nodes(nodes),
        edges=tuple(edges),
        run_id=str(run_context.run_id),
        manifest_id=run_context.manifest_id,
        created_at=created_at,
    )
