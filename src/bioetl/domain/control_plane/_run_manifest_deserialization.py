"""Deserialization helpers for RunManifest."""

from __future__ import annotations

from datetime import datetime

# Forward declarations to avoid circular imports
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.domain.control_plane.run_manifest import (
        ReplayCapability,
        RunArtifactRef,
        RunCodeProvenance,
        RunInputSnapshotRef,
        RunSourceRef,
    )


def _load_optional_str(payload: dict[str, object], key: str) -> str | None:
    """Extract an optional string field from a serialized mapping."""
    value = payload.get(key)
    return None if value is None else str(value)


def _load_code_provenance(raw_code: object) -> RunCodeProvenance:
    """Deserialize code provenance payload safely."""
    from bioetl.domain.control_plane.run_manifest import RunCodeProvenance

    payload = _load_object_mapping(raw_code)
    return RunCodeProvenance(
        pipeline_version=_load_optional_str(payload, "pipeline_version"),
        git_commit=_load_optional_str(payload, "git_commit"),
        source_revision_state=_load_optional_str(payload, "source_revision_state"),
        dependency_lock_hash=_load_optional_str(payload, "dependency_lock_hash"),
        config_hash=_load_optional_str(payload, "config_hash"),
        resolved_config_hash=_load_optional_str(payload, "resolved_config_hash"),
        effective_config_hash=_load_optional_str(payload, "effective_config_hash"),
        source_fingerprint=_load_optional_str(payload, "source_fingerprint"),
        contract_ref=_load_optional_str(payload, "contract_ref"),
        contract_version=_load_optional_str(payload, "contract_version"),
        contract_schema_hash=_load_optional_str(payload, "contract_schema_hash"),
        dq_policy_ref=_load_optional_str(payload, "dq_policy_ref"),
        rule_bundle_version=_load_optional_str(payload, "rule_bundle_version"),
        normalization_profile_ref=_load_optional_str(
            payload, "normalization_profile_ref"
        ),
        normalization_profile_version=_load_optional_str(
            payload, "normalization_profile_version"
        ),
        normalization_profile_hash=_load_optional_str(
            payload, "normalization_profile_hash"
        ),
        dq_contract_compatibility_hash=_load_optional_str(
            payload, "dq_contract_compatibility_hash"
        ),
        effective_config_artifact_id=_load_optional_str(
            payload, "effective_config_artifact_id"
        ),
    )


def _load_replay_capability(raw_value: object) -> ReplayCapability:
    from bioetl.domain.control_plane.run_manifest import ReplayCapability

    if raw_value is None:
        return ReplayCapability.REBUILD_ONLY
    return ReplayCapability(str(raw_value))


def _load_object_mapping(raw_mapping: object) -> dict[str, object]:
    if not isinstance(raw_mapping, dict):
        return {}
    return {str(key): value for key, value in raw_mapping.items()}


def _load_source_refs(raw_sources: object) -> tuple[RunSourceRef, ...]:
    from bioetl.domain.control_plane.run_manifest import RunSourceRef

    if not isinstance(raw_sources, list):
        return ()
    return tuple(
        RunSourceRef(
            provider=str(item["provider"]),
            entity=str(item["entity"]),
            pipeline_name=str(item["pipeline_name"]),
            query=(None if item.get("query") is None else str(item["query"])),
            input_snapshots=_load_input_snapshots(item.get("input_snapshots")),
        )
        for item in raw_sources
        if isinstance(item, dict)
    )


def _load_input_snapshots(raw_snapshots: object) -> tuple[RunInputSnapshotRef, ...]:
    if not isinstance(raw_snapshots, list):
        return ()
    return tuple(
        _load_input_snapshot_ref(item)
        for item in raw_snapshots
        if isinstance(item, dict)
    )


def _load_input_snapshot_ref(item: dict[str, object]) -> RunInputSnapshotRef:
    from bioetl.domain.control_plane.run_manifest import RunInputSnapshotRef

    return RunInputSnapshotRef(
        snapshot_id=str(item["snapshot_id"]),
        content_hash=str(item["content_hash"]),
        immutable_uri=_load_optional_snapshot_text(item, "immutable_uri"),
        query_fingerprint=_load_optional_snapshot_text(item, "query_fingerprint"),
        storage_provider=_load_optional_snapshot_text(item, "storage_provider"),
        object_bucket=_load_optional_snapshot_text(item, "object_bucket"),
        object_key=_load_optional_snapshot_text(item, "object_key"),
        object_version_id=_load_optional_snapshot_text(item, "object_version_id"),
        etag=_load_optional_snapshot_text(item, "etag"),
        last_modified=_load_optional_snapshot_text(item, "last_modified"),
        captured_at=_load_optional_snapshot_datetime(item, "captured_at"),
    )


def _load_optional_snapshot_text(
    item: dict[str, object],
    field_name: str,
) -> str | None:
    raw_value = item.get(field_name)
    return None if raw_value is None else str(raw_value)


def _load_optional_snapshot_datetime(
    item: dict[str, object],
    field_name: str,
) -> datetime | None:
    raw_value = item.get(field_name)
    return None if raw_value is None else datetime.fromisoformat(str(raw_value))


def _load_artifacts(raw_artifacts: object) -> tuple[RunArtifactRef, ...]:
    from bioetl.domain.control_plane.run_manifest import RunArtifactRef

    if not isinstance(raw_artifacts, list):
        return ()
    return tuple(
        RunArtifactRef(layer=str(item["layer"]), path=str(item["path"]))
        for item in raw_artifacts
        if isinstance(item, dict)
    )
