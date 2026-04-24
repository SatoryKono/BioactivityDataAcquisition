"""Concrete lineage-node builders for metadata sidecars."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import TYPE_CHECKING, cast

from bioetl.application.services.lineage.metadata_assemblers_helpers import (
    _resolve_source_batch_ids,
    _resolve_transform_metadata,
)
from bioetl.domain.context import current_utc_time
from bioetl.domain.lineage import (
    DatasetRef,
    LineageEdge,
    LineageEdgeType,
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


def fragment_timestamp(*values: datetime | None) -> datetime:
    """Resolve one stable fragment timestamp."""
    for value in values:
        if value is not None:
            return value
    return current_utc_time()


def build_fragment_id(prefix: str, *parts: object) -> str:
    """Build a stable compact fragment identifier from semantic parts."""
    digest = hashlib.sha256(
        "|".join(str(part) for part in parts if part is not None).encode("utf-8")
    ).hexdigest()[:12]
    return f"{prefix}:{digest}"


def build_semantic_fragment_id(
    prefix: str,
    *,
    nodes: list[LineageNodeRef] | tuple[LineageNodeRef, ...],
    edges: list[LineageEdge] | tuple[LineageEdge, ...],
) -> str:
    """Build a fragment id from semantic topology only.

    Run/manifest anchors are occurrence-scoped and must not influence the
    semantic identity of a lineage fragment.
    """
    semantic_node_ids = sorted(
        node.node_id
        for node in nodes
        if node.node_type not in {LineageNodeType.RUN, LineageNodeType.MANIFEST}
    )
    semantic_edge_ids = sorted(
        ":".join(
            [
                edge.edge_type.value,
                edge.source.node_id,
                edge.target.node_id,
                json.dumps(edge.attributes, sort_keys=True, separators=(",", ":")),
            ]
        )
        for edge in edges
        if edge.source.node_type not in {LineageNodeType.RUN, LineageNodeType.MANIFEST}
        and edge.target.node_type not in {LineageNodeType.RUN, LineageNodeType.MANIFEST}
    )
    return build_fragment_id(prefix, *semantic_node_ids, *semantic_edge_ids)


def dedupe_nodes(nodes: list[LineageNodeRef]) -> tuple[LineageNodeRef, ...]:
    """Deduplicate nodes by canonical node identifier while preserving order."""
    unique: dict[str, LineageNodeRef] = {}
    for node in nodes:
        unique.setdefault(node.node_id, node)
    return tuple(unique.values())


def run_node(run_context: RunContext) -> LineageNodeRef:
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
            "execution_fingerprint": run_context.execution_fingerprint,
            "config_hash": run_context.config_hash,
            "resolved_config_hash": run_context.resolved_config_hash,
            "effective_config_hash": run_context.effective_config_hash,
            "effective_config_artifact_id": run_context.effective_config_artifact_id,
            "contract_ref": run_context.contract_ref,
            "contract_version": run_context.contract_version,
            "contract_schema_hash": run_context.contract_schema_hash,
            "dq_policy_ref": run_context.dq_policy_ref,
            "rule_bundle_version": run_context.rule_bundle_version,
            "dq_contract_compatibility_hash": (
                run_context.dq_contract_compatibility_hash
            ),
        },
    )


def manifest_node(run_context: RunContext) -> LineageNodeRef | None:
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
            "execution_fingerprint": run_context.execution_fingerprint,
            "config_hash": run_context.config_hash,
            "resolved_config_hash": run_context.resolved_config_hash,
            "effective_config_hash": run_context.effective_config_hash,
            "effective_config_artifact_id": run_context.effective_config_artifact_id,
            "contract_ref": run_context.contract_ref,
            "contract_version": run_context.contract_version,
            "contract_schema_hash": run_context.contract_schema_hash,
            "dq_policy_ref": run_context.dq_policy_ref,
            "rule_bundle_version": run_context.rule_bundle_version,
            "dq_contract_compatibility_hash": (
                run_context.dq_contract_compatibility_hash
            ),
        },
    )


def manifest_edges(
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


def source_system_node(
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
            "input_snapshot_count": (
                0 if source_metadata is None else len(source_metadata.input_snapshots)
            ),
        },
    )


def _source_request_attributes(
    source_metadata: SourceMetadata | None,
) -> dict[str, object]:
    """Build canonical source-request attributes from optional source metadata."""
    if source_metadata is None:
        return {
            "url": None,
            "file_path": None,
            "api_version": None,
            "api_request_count": 0,
            "total_requests": None,
            "total_response_bytes": None,
        }
    return {
        "url": source_metadata.url,
        "file_path": source_metadata.file_path,
        "api_version": source_metadata.api_version,
        "api_request_count": len(source_metadata.api_requests),
        "total_requests": source_metadata.total_requests,
        "total_response_bytes": source_metadata.total_response_bytes,
        "input_snapshot_count": len(source_metadata.input_snapshots),
        "input_snapshot_ids": [
            snapshot.snapshot_id for snapshot in source_metadata.input_snapshots
        ],
        "input_snapshot_content_hashes": [
            snapshot.content_hash for snapshot in source_metadata.input_snapshots
        ],
    }


def source_request_node(
    *,
    run_context: RunContext,
    input_data: BronzeMetadataInput,
) -> LineageNodeRef | None:
    """Build source-request node for Bronze extraction when request data exists."""
    source_metadata = input_data.source_metadata
    query_string = input_data.query_string
    if query_string is None and source_metadata is not None:
        query_string = source_metadata.query_string
    if source_metadata is None and query_string is None:
        return None
    attributes = _source_request_attributes(source_metadata)
    attributes.update(
        {
            "provider": run_context.provider,
            "entity": run_context.entity,
            "query_string": query_string,
        }
    )
    input_snapshot_ids = attributes.get("input_snapshot_ids")
    input_snapshot_hashes = attributes.get("input_snapshot_content_hashes")
    return LineageNodeRef(
        node_type=LineageNodeType.SOURCE_REQUEST,
        node_id=build_fragment_id(
            "source_request",
            run_context.provider,
            run_context.entity,
            query_string,
            source_metadata.url if source_metadata is not None else None,
            source_metadata.file_path if source_metadata is not None else None,
            source_metadata.api_version if source_metadata is not None else None,
            input_snapshot_ids,
            input_snapshot_hashes,
        ),
        label=query_string or run_context.pipeline_name,
        attributes=attributes,
    )


def bronze_batch_node_from_input(
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


def _bronze_batch_node_from_result(ref: BronzeWriteResult) -> LineageNodeRef:
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


def bronze_batch_nodes_for_silver(
    *,
    run_context: RunContext,
    input_data: SilverMetadataInput,
) -> list[LineageNodeRef]:
    """Build Bronze upstream nodes for Silver lineage."""
    nodes: dict[str, LineageNodeRef] = {}
    for batch_id in _resolve_source_batch_ids(input_data):
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


def silver_dataset_node(
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


def gold_dataset_node(
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


def silver_source_nodes(input_data: GoldMetadataInput) -> list[LineageNodeRef]:
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


def schema_node(input_data: GoldMetadataInput) -> LineageNodeRef | None:
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


def transform_nodes(
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


def transform_edges(
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


def resolve_transform_metadata(
    *,
    run_context: RunContext,
    transform_version: str | None,
    transform_steps: tuple[str, ...] | list[str] | None,
) -> tuple[str, list[str]]:
    """Resolve transform metadata through the canonical shared helper."""
    resolved = _resolve_transform_metadata(
        run_context=run_context,
        transform_version=transform_version,
        transform_steps=transform_steps,
    )
    return str(resolved[0]), [str(step) for step in resolved[1]]
