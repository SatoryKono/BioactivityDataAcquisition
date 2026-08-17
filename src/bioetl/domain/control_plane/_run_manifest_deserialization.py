"""Deserialization helpers for RunManifest."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime


def _load_optional_str(payload: dict[str, object], key: str) -> str | None:
    """Extract an optional string field from a serialized mapping."""
    value = payload.get(key)
    return None if value is None else str(value)


def _load_code_provenance[CodeProvenanceT](
    raw_code: object,
    *,
    provenance_type: Callable[..., CodeProvenanceT],
) -> CodeProvenanceT:
    """Deserialize code provenance payload safely."""
    payload = _load_object_mapping(raw_code)
    return provenance_type(
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


def _load_replay_capability[ReplayCapabilityT](
    raw_value: object,
    *,
    capability_type: Callable[[str], ReplayCapabilityT],
    rebuild_only: ReplayCapabilityT,
) -> ReplayCapabilityT:
    if raw_value is None:
        return rebuild_only
    return capability_type(str(raw_value))


def _load_object_mapping(raw_mapping: object) -> dict[str, object]:
    if not isinstance(raw_mapping, dict):
        return {}
    return {str(key): value for key, value in raw_mapping.items()}


def _require_key(item: dict[str, object], field_name: str, *, context: str) -> object:
    """Return a required mapping field or raise a descriptive ValueError."""
    if field_name not in item:
        raise ValueError(f"Missing required field {field_name!r} in {context}")
    return item[field_name]


def _load_source_refs[SourceRefT, SnapshotRefT](
    raw_sources: object,
    *,
    source_ref_type: Callable[..., SourceRefT],
    snapshot_ref_type: Callable[..., SnapshotRefT],
) -> tuple[SourceRefT, ...]:
    if not isinstance(raw_sources, list):
        return ()
    loaded: list[SourceRefT] = []
    for index, item in enumerate(raw_sources):
        if not isinstance(item, dict):
            raise ValueError(f"source_refs[{index}] must be an object")
        context = f"source_refs[{index}]"
        loaded.append(
            source_ref_type(
                provider=str(_require_key(item, "provider", context=context)),
                entity=str(_require_key(item, "entity", context=context)),
                pipeline_name=str(_require_key(item, "pipeline_name", context=context)),
                query=(None if item.get("query") is None else str(item["query"])),
                input_snapshots=_load_input_snapshots(
                    item.get("input_snapshots"),
                    snapshot_ref_type=snapshot_ref_type,
                ),
            )
        )
    return tuple(loaded)


def _load_input_snapshots[SnapshotRefT](
    raw_snapshots: object,
    *,
    snapshot_ref_type: Callable[..., SnapshotRefT],
) -> tuple[SnapshotRefT, ...]:
    if not isinstance(raw_snapshots, list):
        return ()
    loaded: list[SnapshotRefT] = []
    for index, item in enumerate(raw_snapshots):
        if not isinstance(item, dict):
            raise ValueError(f"input_snapshots[{index}] must be an object")
        loaded.append(
            _load_input_snapshot_ref(item, snapshot_ref_type=snapshot_ref_type)
        )
    return tuple(loaded)


def _load_input_snapshot_ref[SnapshotRefT](
    item: dict[str, object],
    *,
    snapshot_ref_type: Callable[..., SnapshotRefT],
) -> SnapshotRefT:
    context = "input_snapshot_ref"
    return snapshot_ref_type(
        snapshot_id=str(_require_key(item, "snapshot_id", context=context)),
        content_hash=str(_require_key(item, "content_hash", context=context)),
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


def _load_artifacts[ArtifactRefT](
    raw_artifacts: object,
    *,
    artifact_type: Callable[..., ArtifactRefT],
) -> tuple[ArtifactRefT, ...]:
    if not isinstance(raw_artifacts, list):
        return ()
    loaded: list[ArtifactRefT] = []
    for index, item in enumerate(raw_artifacts):
        if not isinstance(item, dict):
            raise ValueError(f"artifacts[{index}] must be an object")
        context = f"artifacts[{index}]"
        loaded.append(
            artifact_type(
                layer=str(_require_key(item, "layer", context=context)),
                path=str(_require_key(item, "path", context=context)),
            )
        )
    return tuple(loaded)
