"""Silver-layer lineage fragment builder."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.application.services.metadata_lineage_composite import (
    _build_dataset_composite_lineage_components,
)
from bioetl.application.services.metadata_lineage_nodes import (
    bronze_batch_nodes_for_silver,
    build_fragment_id,
    dedupe_nodes,
    fragment_timestamp,
    manifest_edges,
    manifest_node,
    resolve_transform_metadata,
    run_node,
    silver_dataset_node,
    transform_edges,
    transform_nodes,
)
from bioetl.domain.lineage import (
    LineageEdge,
    LineageEdgeType,
    LineageGraphFragment,
)

if TYPE_CHECKING:
    from bioetl.domain.ports import SilverMetadataInput
    from bioetl.domain.value_objects.run_context import RunContext





def _build_silver_nodes(
    run_context: RunContext,
    input_data: SilverMetadataInput,
    created_at: str,
) -> tuple[list, list]:
    """Build all nodes for the silver lineage fragment."""
    run = run_node(run_context)
    manifest = manifest_node(run_context)
    silver_dataset, composite_source_nodes, composite_source_edges = (
        _build_dataset_composite_lineage_components(
            run_context=run_context,
            dataset_node=silver_dataset_node(
                run_context=run_context, input_data=input_data
            ),
            records=input_data.records,
            composite_name=f"{run_context.provider}.{run_context.entity}",
            created_at=created_at,
        )
    )
    bronze_nodes = bronze_batch_nodes_for_silver(
        run_context=run_context,
        input_data=input_data,
    )
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
        silver_dataset,
        *bronze_nodes,
        *lineage_transform_nodes,
        *composite_source_nodes,
    ]
    
    if manifest is not None:
        nodes.append(manifest)
    
    return nodes, composite_source_edges


def _build_silver_edges(
    run_context: RunContext,
    input_data: SilverMetadataInput,
    nodes: list,
    created_at: str,
    composite_source_edges: list[LineageEdge],
) -> list[LineageEdge]:
    """Build all edges for the silver lineage fragment."""
    run = next(node for node in nodes if hasattr(node, 'run_id') and node.run_id == run_context.run_id)
    silver_dataset = next(node for node in nodes if hasattr(node, 'table_name') and node.table_name == input_data.table_name)
    bronze_nodes = [node for node in nodes if hasattr(node, 'layer') and node.layer == 'bronze']
    lineage_transform_nodes = [node for node in nodes if hasattr(node, 'transform_type')]
    
    edges = manifest_edges(
        manifest=manifest_node(run_context),
        run=run,
        created_at=created_at,
        run_context=run_context,
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
    created_at = fragment_timestamp(input_data.completed_at, input_data.started_at)
    
    # Build nodes
    nodes, composite_source_edges = _build_silver_nodes(run_context, input_data, created_at)
    
    # Build edges
    edges = _build_silver_edges(run_context, input_data, nodes, created_at, composite_source_edges)
    
    return LineageGraphFragment(
        fragment_id=build_fragment_id(
            "silver",
            run_context.run_id,
            input_data.table_path,
            input_data.version_after,
        ),
        nodes=dedupe_nodes(nodes),
        edges=tuple(edges),
        run_id=str(run_context.run_id),
        manifest_id=run_context.manifest_id,
        created_at=created_at,
    )
