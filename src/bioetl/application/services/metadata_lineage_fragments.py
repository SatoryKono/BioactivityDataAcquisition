"""Helpers for canonical lineage graph fragment assembly."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import TYPE_CHECKING, cast

from bioetl.application.services.metadata_assemblers_helpers import (
    _resolve_source_batch_ids,
    _resolve_transform_metadata,
)
from bioetl.domain.lineage import (
    DatasetRef,
    LineageEdge,
    LineageEdgeType,
    LineageGraphFragment,
    LineageNodeRef,
    LineageNodeType,
    SchemaRef,
    TransformRef,
)
from bioetl.domain.services.schema_metadata_extractor import extract_schema_metadata

if TYPE_CHECKING:
    from bioetl.domain.models.metadata import SourceMetadata
    from bioetl.domain.ports import (
        BronzeMetadataInput,
        GoldMetadataInput,
        SilverMetadataInput,
    )
    from bioetl.domain.value_objects.bronze_result import BronzeWriteResult
    from bioetl.domain.value_objects.run_context import RunContext


def _fragment_timestamp(*values: datetime | None) -> datetime:
    """Resolve one stable fragment timestamp."""
    for value in values:
        if value is not None:
            return value
    return datetime.now(UTC)


def _build_fragment_id(prefix: str, *parts: object) -> str:
    """Build a stable compact fragment identifier from semantic parts."""
    digest = hashlib.sha1(
        "|".join(str(part) for part in parts if part is not None).encode("utf-8")
    ).hexdigest()[:12]
    return f"{prefix}:{digest}"


def _dedupe_nodes(nodes: list[LineageNodeRef]) -> tuple[LineageNodeRef, ...]:
    """Deduplicate nodes by canonical node identifier while preserving order."""
    unique: dict[str, LineageNodeRef] = {}
    for node in nodes:
        unique.setdefault(node.node_id, node)
    return tuple(unique.values())


def _run_node(run_context: RunContext) -> LineageNodeRef:
    """Build run anchor node."""
    return LineageNodeRef(
        node_type=LineageNodeType.RUN,
        node_id=f"run:{run_context.run_id}",
        label=run_context.pipeline_name,
        attributes={
            "run_id": str(run_context.run_id),
            "pipeline_name": run_context.pipeline_name,
            "provider": run_context.provider,
            "entity": run_context.entity,
            "run_type": run_context.run_type.value,
            "started_at": run_context.started_at.isoformat(),
            "manifest_id": run_context.manifest_id,
        },
    )


def _manifest_node(run_context: RunContext) -> LineageNodeRef | None:
    """Build manifest anchor when one exists."""
    if run_context.manifest_id is None:
        return None
    return LineageNodeRef(
        node_type=LineageNodeType.MANIFEST,
        node_id=f"manifest:{run_context.manifest_id}",
        label=run_context.pipeline_name,
        attributes={
            "manifest_id": run_context.manifest_id,
            "pipeline_name": run_context.pipeline_name,
            "provider": run_context.provider,
            "entity": run_context.entity,
        },
    )


def _manifest_edges(
    *,
    manifest: LineageNodeRef | None,
    run: LineageNodeRef,
    created_at: datetime,
    run_context: RunContext,
) -> list[LineageEdge]:
    """Build manifest-to-run edge when manifest exists."""
    if manifest is None:
        return []
    return [
        LineageEdge(
            edge_type=LineageEdgeType.EXPLAINS,
            source=manifest,
            target=run,
            run_id=str(run_context.run_id),
            manifest_id=run_context.manifest_id,
            created_at=created_at,
        )
    ]


def _source_system_node(
    *,
    run_context: RunContext,
    source_metadata: SourceMetadata | None,
) -> LineageNodeRef:
    """Build source-system node from pipeline context and Bronze metadata input."""
    return LineageNodeRef(
        node_type=LineageNodeType.SOURCE_SYSTEM,
        node_id=f"source_system:{run_context.provider}",
        label=run_context.provider,
        attributes={
            "provider": run_context.provider,
            "entity": run_context.entity,
            "source_type": None if source_metadata is None else source_metadata.type,
            "url": None if source_metadata is None else source_metadata.url,
            "file_path": None if source_metadata is None else source_metadata.file_path,
            "api_version": (
                None if source_metadata is None else source_metadata.api_version
            ),
        },
    )


def _source_request_node(
    *,
    run_context: RunContext,
    input_data: BronzeMetadataInput,
) -> LineageNodeRef | None:
    """Build source-request node for Bronze extraction when request data exists."""
    source_metadata = input_data.source_metadata
    query_string = (
        input_data.query_string
        or (None if source_metadata is None else source_metadata.query_string)
    )
    if source_metadata is None and query_string is None:
        return None
    api_request_count = 0 if source_metadata is None else len(source_metadata.api_requests)
    return LineageNodeRef(
        node_type=LineageNodeType.SOURCE_REQUEST,
        node_id=f"source_request:{run_context.run_id}:{input_data.batch_id}",
        label=query_string or run_context.pipeline_name,
        attributes={
            "provider": run_context.provider,
            "entity": run_context.entity,
            "query_string": query_string,
            "url": None if source_metadata is None else source_metadata.url,
            "file_path": None if source_metadata is None else source_metadata.file_path,
            "api_version": (
                None if source_metadata is None else source_metadata.api_version
            ),
            "api_request_count": api_request_count,
            "total_requests": (
                None if source_metadata is None else source_metadata.total_requests
            ),
            "total_response_bytes": (
                None
                if source_metadata is None
                else source_metadata.total_response_bytes
            ),
        },
    )


def _bronze_batch_node_from_input(
    *,
    run_context: RunContext,
    input_data: BronzeMetadataInput,
) -> LineageNodeRef:
    """Build Bronze-batch node from Bronze metadata input."""
    return LineageNodeRef(
        node_type=LineageNodeType.BRONZE_BATCH,
        node_id=f"bronze_batch:{input_data.batch_id}",
        label=f"{run_context.provider}.{run_context.entity}",
        attributes={
            "batch_id": str(input_data.batch_id),
            "provider": run_context.provider,
            "entity": run_context.entity,
            "output_path": input_data.output_path,
            "record_count": input_data.record_count,
            "compressed_size": input_data.compressed_size,
        },
    )


def _bronze_batch_node_from_result(
    ref: BronzeWriteResult,
) -> LineageNodeRef:
    """Build Bronze-batch node from Bronze write result."""
    provider, entity = ref.provider_entity
    return LineageNodeRef(
        node_type=LineageNodeType.BRONZE_BATCH,
        node_id=f"bronze_batch:{ref.batch_id}",
        label=ref.table_name,
        attributes={
            "batch_id": str(ref.batch_id),
            "provider": provider,
            "entity": entity,
            "table_name": ref.table_name,
            "relative_path": ref.relative_path,
            "absolute_path": ref.absolute_path,
            "record_count": ref.record_count,
            "compressed_size": ref.compressed_size,
            "checksum_blake2": ref.checksum_blake2,
        },
    )


def _bronze_batch_nodes_for_silver(
    *,
    run_context: RunContext,
    input_data: SilverMetadataInput,
) -> list[LineageNodeRef]:
    """Build Bronze upstream nodes for Silver lineage."""
    nodes: dict[str, LineageNodeRef] = {}
    source_batch_ids = _resolve_source_batch_ids(input_data)
    for batch_id in source_batch_ids:
        nodes.setdefault(
            batch_id,
            LineageNodeRef(
                node_type=LineageNodeType.BRONZE_BATCH,
                node_id=f"bronze_batch:{batch_id}",
                label=f"{run_context.provider}.{run_context.entity}",
                attributes={
                    "batch_id": batch_id,
                    "provider": run_context.provider,
                    "entity": run_context.entity,
                },
            ),
        )
    if input_data.bronze_refs is None:
        return list(nodes.values())
    bronze_refs = cast("list[BronzeWriteResult]", input_data.bronze_refs)
    for ref in bronze_refs:
        nodes[str(ref.batch_id)] = _bronze_batch_node_from_result(ref)
    return list(nodes.values())


def _silver_dataset_node(
    *,
    run_context: RunContext,
    input_data: SilverMetadataInput,
) -> LineageNodeRef:
    """Build persisted Silver dataset node."""
    dataset = DatasetRef(
        layer="silver",
        logical_name=f"{run_context.provider}.{run_context.entity}",
        version=input_data.version_after,
        provider=run_context.provider,
        entity=run_context.entity,
        path=input_data.table_path,
        manifest_id=run_context.manifest_id,
        run_id=str(run_context.run_id),
    )
    return dataset.to_node_ref()


def _gold_dataset_node(
    *,
    run_context: RunContext,
    input_data: GoldMetadataInput,
) -> LineageNodeRef:
    """Build persisted Gold dataset node."""
    dataset = DatasetRef(
        layer="gold",
        logical_name=input_data.table_name,
        provider=run_context.provider,
        entity=run_context.entity,
        path=input_data.table_path,
        manifest_id=run_context.manifest_id,
        run_id=str(run_context.run_id),
    )
    return dataset.to_node_ref()


def _silver_source_nodes(input_data: GoldMetadataInput) -> list[LineageNodeRef]:
    """Build Silver upstream dataset nodes for Gold lineage."""
    if not input_data.silver_refs:
        return []
    return [
        DatasetRef(
            layer="silver",
            logical_name=ref.table_name,
            version=ref.delta_version,
            path=ref.table_path,
        ).to_node_ref()
        for ref in input_data.silver_refs
    ]


def _schema_node(input_data: GoldMetadataInput) -> LineageNodeRef | None:
    """Build schema node when Gold schema metadata is available."""
    schema_info = extract_schema_metadata(input_data.gold_schema)
    if schema_info.contract_path is None and not schema_info.columns:
        return None
    return SchemaRef(
        contract_path=schema_info.contract_path or "inline_schema",
        version=schema_info.version,
        validation_mode=schema_info.validation,
        dataset_name=None,
    ).to_node_ref()


def _transform_nodes(
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


def _transform_edges(
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


def build_bronze_lineage_fragment(
    *,
    run_context: RunContext,
    input_data: BronzeMetadataInput,
) -> LineageGraphFragment:
    """Build canonical Bronze lineage fragment from metadata input."""
    created_at = _fragment_timestamp(input_data.completed_at, input_data.started_at)
    run = _run_node(run_context)
    manifest = _manifest_node(run_context)
    source_system = _source_system_node(
        run_context=run_context,
        source_metadata=input_data.source_metadata,
    )
    source_request = _source_request_node(run_context=run_context, input_data=input_data)
    bronze_batch = _bronze_batch_node_from_input(
        run_context=run_context,
        input_data=input_data,
    )

    nodes = [run, source_system, bronze_batch]
    edges = _manifest_edges(
        manifest=manifest,
        run=run,
        created_at=created_at,
        run_context=run_context,
    )
    if manifest is not None:
        nodes.append(manifest)
    if source_request is not None:
        nodes.append(source_request)
        edges.append(
            LineageEdge(
                edge_type=LineageEdgeType.DERIVED_FROM,
                source=source_request,
                target=source_system,
                run_id=str(run_context.run_id),
                manifest_id=run_context.manifest_id,
                created_at=created_at,
            )
        )
        edges.append(
            LineageEdge(
                edge_type=LineageEdgeType.DERIVED_FROM,
                source=bronze_batch,
                target=source_request,
                run_id=str(run_context.run_id),
                manifest_id=run_context.manifest_id,
                created_at=created_at,
            )
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
        fragment_id=_build_fragment_id(
            "bronze",
            run_context.run_id,
            input_data.batch_id,
        ),
        nodes=_dedupe_nodes(nodes),
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
    created_at = _fragment_timestamp(input_data.completed_at, input_data.started_at)
    run = _run_node(run_context)
    manifest = _manifest_node(run_context)
    silver_dataset = _silver_dataset_node(run_context=run_context, input_data=input_data)
    bronze_nodes = _bronze_batch_nodes_for_silver(
        run_context=run_context,
        input_data=input_data,
    )
    transform_version, transform_steps = _resolve_transform_metadata(
        run_context=run_context,
        transform_version=input_data.transform_version,
        transform_steps=input_data.transform_steps,
    )
    transform_nodes = _transform_nodes(
        run_context=run_context,
        transform_version=transform_version or None,
        transform_steps=transform_steps,
    )

    nodes = [run, silver_dataset, *bronze_nodes, *transform_nodes]
    edges = _manifest_edges(
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
    if transform_nodes:
        edges.extend(
            _transform_edges(
                run_context=run_context,
                run=run,
                transforms=transform_nodes,
                created_at=created_at,
            )
        )
        edges.append(
            LineageEdge(
                edge_type=LineageEdgeType.PRODUCED_BY,
                source=silver_dataset,
                target=transform_nodes[-1],
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
        fragment_id=_build_fragment_id(
            "silver",
            run_context.run_id,
            input_data.table_path,
            input_data.version_after,
        ),
        nodes=_dedupe_nodes(nodes),
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
    created_at = _fragment_timestamp(input_data.completed_at, input_data.started_at)
    run = _run_node(run_context)
    manifest = _manifest_node(run_context)
    gold_dataset = _gold_dataset_node(run_context=run_context, input_data=input_data)
    silver_nodes = _silver_source_nodes(input_data)
    schema_node = _schema_node(input_data)
    transform_version, transform_steps = _resolve_transform_metadata(
        run_context=run_context,
        transform_version=input_data.transform_version,
        transform_steps=input_data.transform_steps,
    )
    transform_nodes = _transform_nodes(
        run_context=run_context,
        transform_version=transform_version or None,
        transform_steps=transform_steps,
    )

    nodes = [run, gold_dataset, *silver_nodes, *transform_nodes]
    edges = _manifest_edges(
        manifest=manifest,
        run=run,
        created_at=created_at,
        run_context=run_context,
    )
    if manifest is not None:
        nodes.append(manifest)
    if schema_node is not None:
        nodes.append(schema_node)
        edges.append(
            LineageEdge(
                edge_type=LineageEdgeType.USED_SCHEMA,
                source=gold_dataset,
                target=schema_node,
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
    if transform_nodes:
        edges.extend(
            _transform_edges(
                run_context=run_context,
                run=run,
                transforms=transform_nodes,
                created_at=created_at,
            )
        )
        edges.append(
            LineageEdge(
                edge_type=LineageEdgeType.PRODUCED_BY,
                source=gold_dataset,
                target=transform_nodes[-1],
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
        fragment_id=_build_fragment_id(
            "gold",
            run_context.run_id,
            input_data.table_name,
            input_data.table_path,
        ),
        nodes=_dedupe_nodes(nodes),
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
