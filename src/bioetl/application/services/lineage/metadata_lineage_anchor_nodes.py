"""Run, manifest, and source lineage node builders."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from bioetl.application.services.lineage.metadata_lineage_fragment_ids import (
    build_fragment_id,
)
from bioetl.domain.lineage import (
    LineageEdge,
    LineageEdgeType,
    LineageNodeRef,
    LineageNodeType,
)

if TYPE_CHECKING:
    from bioetl.domain.models.metadata import SourceMetadata
    from bioetl.domain.ports import BronzeMetadataInput
    from bioetl.domain.value_objects.run_context import RunContext


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


__all__ = [
    "manifest_edges",
    "manifest_node",
    "run_node",
    "source_request_node",
    "source_system_node",
]
