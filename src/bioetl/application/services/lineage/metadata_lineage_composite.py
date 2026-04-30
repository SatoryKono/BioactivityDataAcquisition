"""Composite-lineage helpers pulled out of metadata_lineage_fragments."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import TYPE_CHECKING

from bioetl.domain.behavior.composite_metadata_helpers import (
    extract_composite_lineage_metadata,
    parse_composite_field_sources,
    summarize_composite_cv_dq,
)
from bioetl.domain.lineage import (
    CompositeLineageMetadata,
    LineageEdge,
    LineageEdgeType,
    LineageNodeRef,
    LineageNodeType,
)

if TYPE_CHECKING:
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


def _build_cv_marker_summary(
    records: Sequence[Mapping[str, object]] | None,
) -> dict[str, int]:
    if not records:
        return {}
    cv_summary = summarize_composite_cv_dq(records)
    if not cv_summary["has_signal"]:
        return {}
    return {
        "cv_warn_count": int(cv_summary["warning_records"]),
        "cv_error_count": int(cv_summary["error_records"]),
        "cv_quarantine_count": int(cv_summary["quarantine_records"]),
    }


def _build_provider_field_map(
    records: Sequence[Mapping[str, object]] | None,
) -> dict[str, list[str]]:
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
    dataset_node: LineageNodeRef,
    run_context: RunContext,
    created_at: datetime,
    source_providers: Sequence[str],
    provider_field_map: Mapping[str, list[str]],
    enrichment_status: Mapping[str, str],
    composite_run_id: str | None,
    composite_name: str,
) -> tuple[list[LineageNodeRef], list[LineageEdge]]:
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
                source=dataset_node,
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


def _build_dataset_composite_attributes(
    *,
    composite_run_id: str | None,
    composite_name: str,
    source_providers: Sequence[str],
    enrichment_status: Mapping[str, str],
    field_sources: Mapping[str, str],
    provider_field_map: Mapping[str, list[str]],
    seed_record_id: str | None,
    lineage_created_at: datetime | None,
) -> dict[str, object]:
    """Build one canonical dataset-level composite lineage summary."""
    return {
        "composite_run_id": composite_run_id,
        "composite_name": composite_name,
        "source_providers": list(source_providers),
        "enrichment_status": dict(enrichment_status),
        "field_sources": dict(field_sources),
        "provider_fields": dict(provider_field_map),
        "seed_record_id": seed_record_id,
        "lineage_created_at": (
            None if lineage_created_at is None else lineage_created_at.isoformat()
        ),
    }


def _build_composite_dataset_enrichment(
    *,
    run_context: RunContext,
    dataset_node: LineageNodeRef,
    records: Sequence[Mapping[str, object]] | None,
    composite_lineage: CompositeLineageMetadata,
    created_at: datetime,
) -> tuple[dict[str, object], list[LineageNodeRef], list[LineageEdge]]:
    """Build dataset attributes and source edges for one composite lineage payload."""
    enrichment_status = {
        provider: status.status
        for provider, status in composite_lineage.enrichment_status.items()
    }
    provider_field_map = _build_provider_field_map(records)
    dataset_attributes = _build_dataset_composite_attributes(
        composite_run_id=composite_lineage.composite_run_id or None,
        composite_name=composite_lineage.composite_name,
        source_providers=composite_lineage.source_providers,
        enrichment_status=enrichment_status,
        field_sources=composite_lineage.field_sources,
        provider_field_map=provider_field_map,
        seed_record_id=composite_lineage.seed_record_id,
        lineage_created_at=composite_lineage.created_at,
    )
    composite_nodes, composite_edges = _build_composite_source_nodes_and_edges(
        dataset_node=dataset_node,
        run_context=run_context,
        created_at=created_at,
        source_providers=composite_lineage.source_providers,
        provider_field_map=provider_field_map,
        enrichment_status=enrichment_status,
        composite_run_id=composite_lineage.composite_run_id or None,
        composite_name=composite_lineage.composite_name,
    )
    return dataset_attributes, composite_nodes, composite_edges


def _build_dataset_composite_lineage_components(
    *,
    run_context: RunContext,
    dataset_node: LineageNodeRef,
    records: Sequence[Mapping[str, object]] | None,
    composite_name: str,
    created_at: datetime,
    composite_run_id: str | None = None,
    lineage_created_at: datetime | None = None,
) -> tuple[LineageNodeRef, list[LineageNodeRef], list[LineageEdge]]:
    composite_lineage = extract_composite_lineage_metadata(
        records or [],
        composite_name=composite_name,
        composite_run_id=composite_run_id,
        lineage_created_at=lineage_created_at,
    )
    cv_summary = _build_cv_marker_summary(records)
    if composite_lineage is None and not cv_summary:
        return dataset_node, [], []

    dataset_attributes: dict[str, object] = {}
    composite_nodes: list[LineageNodeRef] = []
    composite_edges: list[LineageEdge] = []

    if composite_lineage is not None:
        (
            composite_attributes,
            composite_nodes,
            composite_edges,
        ) = _build_composite_dataset_enrichment(
            run_context=run_context,
            dataset_node=dataset_node,
            records=records,
            composite_lineage=composite_lineage,
            created_at=created_at,
        )
        dataset_attributes.update(composite_attributes)

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
