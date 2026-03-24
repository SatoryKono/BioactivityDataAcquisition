"""Helpers for canonical lineage graph fragment assembly."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import TYPE_CHECKING

from bioetl.application.services.metadata_lineage_nodes import (
    bronze_batch_node_from_input,
    bronze_batch_nodes_for_silver,
    build_fragment_id,
    dedupe_nodes,
    fragment_timestamp,
    gold_dataset_node,
    manifest_edges,
    manifest_node,
    resolve_transform_metadata,
    run_node,
    schema_node,
    silver_dataset_node,
    silver_source_nodes,
    source_request_node,
    source_system_node,
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
from bioetl.domain.services.composite_metadata_helpers import (
    extract_composite_lineage_metadata,
    parse_composite_field_sources,
)

if TYPE_CHECKING:
    from bioetl.domain.ports import (
        BronzeMetadataInput,
        GoldMetadataInput,
        SilverMetadataInput,
    )
    from bioetl.domain.value_objects.run_context import RunContext


def _merge_gold_dataset_attributes(
    node: LineageNodeRef,
    extra_attributes: Mapping[str, object],
) -> LineageNodeRef:
    """Return a copy of the Gold dataset node with merged lineage attributes."""
    attributes = dict(node.attributes)
    attributes.update(extra_attributes)
    return LineageNodeRef(
        node_type=node.node_type,
        node_id=node.node_id,
        label=node.label,
        attributes=attributes,
    )


def _is_truthy_marker(value: object) -> bool:
    """Normalize record marker payloads into boolean truthiness."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes"}
    if isinstance(value, int):
        return value != 0
    return False


def _build_cv_marker_summary(
    records: Sequence[Mapping[str, object]] | None,
) -> dict[str, int]:
    """Summarize composite cross-validation marker counts across records."""
    if not records:
        return {}
    marker_map = {
        "_cv_warn": "cv_warn_count",
        "_cv_error": "cv_error_count",
        "_cv_quarantine": "cv_quarantine_count",
    }
    summary: dict[str, int] = {}
    for raw_key, summary_key in marker_map.items():
        if any(raw_key in record for record in records):
            summary[summary_key] = sum(
                1 for record in records if _is_truthy_marker(record.get(raw_key))
            )
    return summary


def _build_provider_field_map(
    records: Sequence[Mapping[str, object]] | None,
) -> dict[str, list[str]]:
    """Aggregate composite field-source markers into provider-to-fields mapping."""
    if not records:
        return {}
    fields_by_provider: dict[str, set[str]] = {}
    for record in records:
        for field_name, provider in parse_composite_field_sources(
            record.get("_field_sources")
        ).items():
            fields_by_provider.setdefault(provider, set()).add(field_name)
    return {
        provider: sorted(fields)
        for provider, fields in sorted(fields_by_provider.items())
    }


def _build_composite_source_nodes_and_edges(
    *,
    gold_dataset: LineageNodeRef,
    run_context: RunContext,
    created_at: datetime,
    source_providers: Sequence[str],
    provider_field_map: Mapping[str, list[str]],
    enrichment_status: Mapping[str, str],
    composite_run_id: str | None,
    composite_name: str,
) -> tuple[list[LineageNodeRef], list[LineageEdge]]:
    """Build composite source-system nodes and provider summary edges."""
    provider_names = sorted(
        set(source_providers)
        | set(provider_field_map.keys())
        | set(enrichment_status.keys())
    )
    nodes: list[LineageNodeRef] = []
    edges: list[LineageEdge] = []
    for provider in provider_names:
        selected_fields = list(provider_field_map.get(provider, ()))
        node = LineageNodeRef(
            node_type=LineageNodeType.SOURCE_SYSTEM,
            node_id=f"source_system:{provider}",
            label=provider,
            attributes={
                "provider": provider,
                "composite_source": True,
                "composite_run_id": composite_run_id,
                "composite_name": composite_name,
                "selected_fields": selected_fields,
                "selected_field_count": len(selected_fields),
                "enrichment_status": enrichment_status.get(provider),
            },
        )
        nodes.append(node)
        edges.append(
            LineageEdge(
                edge_type=LineageEdgeType.DERIVED_FROM,
                source=gold_dataset,
                target=node,
                run_id=str(run_context.run_id),
                manifest_id=run_context.manifest_id,
                created_at=created_at,
                attributes={
                    "composite_run_id": composite_run_id,
                    "composite_name": composite_name,
                    "selected_fields": selected_fields,
                    "selected_field_count": len(selected_fields),
                    "enrichment_status": enrichment_status.get(provider),
                },
            )
        )
    return nodes, edges


def _build_dataset_composite_lineage_components(
    *,
    run_context: RunContext,
    dataset_node: LineageNodeRef,
    records: Sequence[Mapping[str, object]] | None,
    composite_name: str,
    created_at: datetime,
) -> tuple[LineageNodeRef, list[LineageNodeRef], list[LineageEdge]]:
    """Enrich one dataset lineage fragment with composite summary signals."""
    composite_lineage = extract_composite_lineage_metadata(
        records or [],
        composite_name=composite_name,
    )
    cv_summary = _build_cv_marker_summary(records)
    if composite_lineage is None and not cv_summary:
        return dataset_node, [], []

    provider_field_map = _build_provider_field_map(records)
    dataset_attributes: dict[str, object] = {}
    composite_nodes: list[LineageNodeRef] = []
    composite_edges: list[LineageEdge] = []

    if composite_lineage is not None:
        enrichment_status = {
            provider: status.status
            for provider, status in composite_lineage.enrichment_status.items()
        }
        dataset_attributes.update(
            {
                "composite_run_id": (
                    composite_lineage.composite_run_id or None
                ),
                "composite_name": composite_lineage.composite_name,
                "source_providers": list(composite_lineage.source_providers),
                "enrichment_status": enrichment_status,
                "field_sources": dict(composite_lineage.field_sources),
                "provider_fields": provider_field_map,
                "seed_record_id": composite_lineage.seed_record_id,
                "lineage_created_at": (
                    None
                    if composite_lineage.created_at is None
                    else composite_lineage.created_at.isoformat()
                ),
            }
        )
        composite_nodes, composite_edges = _build_composite_source_nodes_and_edges(
            gold_dataset=dataset_node,
            run_context=run_context,
            created_at=created_at,
            source_providers=composite_lineage.source_providers,
            provider_field_map=provider_field_map,
            enrichment_status=enrichment_status,
            composite_run_id=composite_lineage.composite_run_id or None,
            composite_name=composite_lineage.composite_name,
        )

    dataset_attributes.update(cv_summary)
    enriched_dataset = _merge_gold_dataset_attributes(dataset_node, dataset_attributes)
    if composite_edges:
        composite_edges = [
            LineageEdge(
                edge_type=edge.edge_type,
                source=enriched_dataset,
                target=edge.target,
                run_id=edge.run_id,
                manifest_id=edge.manifest_id,
                created_at=edge.created_at,
                attributes=edge.attributes,
            )
            for edge in composite_edges
        ]
    return enriched_dataset, composite_nodes, composite_edges


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
    return LineageGraphFragment(
        fragment_id=build_fragment_id("bronze", run_context.run_id, input_data.batch_id),
        nodes=dedupe_nodes(nodes),
        edges=tuple(edges),
        run_id=str(run_context.run_id),
        manifest_id=run_context.manifest_id,
        created_at=created_at,
    )


def build_silver_lineage_fragment(
    *,
    run_context: RunContext,
    input_data: SilverMetadataInput,
) -> LineageGraphFragment:
    """Build canonical Silver lineage fragment from metadata input."""
    created_at = fragment_timestamp(input_data.completed_at, input_data.started_at)
    run = run_node(run_context)
    manifest = manifest_node(run_context)
    silver_dataset, composite_source_nodes, composite_source_edges = (
        _build_dataset_composite_lineage_components(
            run_context=run_context,
            dataset_node=silver_dataset_node(run_context=run_context, input_data=input_data),
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
    edges = manifest_edges(
        manifest=manifest,
        run=run,
        created_at=created_at,
        run_context=run_context,
    )
    if manifest is not None:
        nodes.append(manifest)
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


__all__ = [
    "build_bronze_lineage_fragment",
    "build_gold_lineage_fragment",
    "build_silver_lineage_fragment",
]
