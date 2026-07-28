"""Checkpoint metadata resolution helpers (extracted for hotspot headroom)."""

from __future__ import annotations

from bioetl.composition.runtime_builders.config_access import get_settings
from bioetl.composition.runtime_builders.input_snapshot_resolution import (
    resolve_cached_bronze_input_snapshot_refs,
    resolve_manifest_input_snapshot_refs,
)
from bioetl.domain.normalization import (
    build_execution_identity_payload,
    compute_input_snapshot_identity_fingerprint,
)
from bioetl.domain.control_plane import RunInputSnapshotRef


def _resolve_run_context_payload(pipeline: object) -> object | None:
    """Resolve metadata run_context from pipeline services when available."""
    services = getattr(pipeline, "services", None)
    metadata_coordinator = getattr(services, "metadata_coordinator", None)
    if metadata_coordinator is None:
        return None
    return getattr(metadata_coordinator, "run_context", None)


def _coerce_optional_str(value: object | None) -> str | None:
    if value is None:
        return None
    return str(value) or None


def _normalize_execution_identity_payload(
    *,
    pipeline_name: str,
    run_type: str,
    pipeline_version: str | None,
    git_commit: str | None,
    dependency_lock_hash: str | None,
    effective_config_hash: str | None,
    dq_contract_compatibility_hash: str | None,
    manifest_id: str | None,
    contract: tuple[str | None, str | None],
    normalization_profile: tuple[str | None, str | None, str | None],
    effective_config_artifact_id: str | None,
    exact_replay: bool,
    input_snapshot_fingerprint: str | None,
    silver_filter_compatibility_mode: str | None,
) -> dict[str, str | None]:
    """Return the canonical checkpoint execution-identity payload."""
    del manifest_id
    return build_execution_identity_payload(
        pipeline_name=pipeline_name,
        run_type=run_type,
        pipeline_version=pipeline_version,
        git_commit=git_commit,
        dependency_lock_hash=dependency_lock_hash,
        effective_config_hash=effective_config_hash,
        dq_contract_compatibility_hash=dq_contract_compatibility_hash,
        contract=contract,
        normalization_profile=normalization_profile,
        effective_config_artifact_id=effective_config_artifact_id,
        exact_replay=exact_replay,
        input_snapshot_fingerprint=input_snapshot_fingerprint,
        silver_filter_compatibility_mode=silver_filter_compatibility_mode,
    )


def _serialize_input_snapshot_ref(
    snapshot: RunInputSnapshotRef,
) -> dict[str, object]:
    """Return one checkpoint-safe serialized snapshot ref mapping."""
    captured_at = getattr(snapshot, "captured_at", None)
    return {
        "snapshot_id": str(snapshot.snapshot_id),
        "content_hash": str(snapshot.content_hash),
        "immutable_uri": _coerce_optional_str(getattr(snapshot, "immutable_uri", None)),
        "query_fingerprint": _coerce_optional_str(
            getattr(snapshot, "query_fingerprint", None)
        ),
        "storage_provider": _coerce_optional_str(
            getattr(snapshot, "storage_provider", None)
        ),
        "object_bucket": _coerce_optional_str(getattr(snapshot, "object_bucket", None)),
        "object_key": _coerce_optional_str(getattr(snapshot, "object_key", None)),
        "object_version_id": _coerce_optional_str(
            getattr(snapshot, "object_version_id", None)
        ),
        "etag": _coerce_optional_str(getattr(snapshot, "etag", None)),
        "last_modified": _coerce_optional_str(getattr(snapshot, "last_modified", None)),
        "captured_at": captured_at.isoformat() if captured_at is not None else None,
    }


def _resolve_input_snapshot_refs(
    pipeline: object,
) -> tuple[dict[str, object], ...]:
    """Resolve manifest-aligned snapshot identities for replay-safe checkpoints."""
    run_context_metadata = _resolve_run_context_metadata(pipeline)
    manifest_snapshot_refs = resolve_manifest_input_snapshot_refs(
        settings=get_settings(),
        manifest_id=run_context_metadata["manifest_id"],
    )
    if manifest_snapshot_refs:
        return tuple(
            _serialize_input_snapshot_ref(snapshot)
            for snapshot in manifest_snapshot_refs
        )

    runtime = getattr(pipeline, "runtime", None)
    cached_bronze = None if runtime is None else getattr(runtime, "cached_bronze", None)
    if cached_bronze is None or not getattr(cached_bronze, "enabled", False):
        return ()

    config = getattr(pipeline, "config", None)
    provider = _coerce_optional_str(getattr(config, "provider", None))
    entity = _coerce_optional_str(getattr(config, "entity_type", None))
    if provider is None or entity is None:
        return ()

    snapshot_refs = resolve_cached_bronze_input_snapshot_refs(
        cached_bronze=cached_bronze,
        settings=get_settings(),
        provider=provider,
        entity=entity,
    )
    return tuple(_serialize_input_snapshot_ref(snapshot) for snapshot in snapshot_refs)


def _resolve_run_context_metadata(
    pipeline: object,
) -> dict[str, str | None]:
    """Resolve string metadata fields from the pipeline run context."""
    run_context = _resolve_run_context_payload(pipeline)
    field_names = (
        "pipeline_version",
        "git_commit",
        "dependency_lock_hash",
        "effective_config_hash",
        "dq_contract_compatibility_hash",
        "manifest_id",
        "contract_ref",
        "contract_version",
        "normalization_profile_ref",
        "normalization_profile_version",
        "normalization_profile_hash",
        "effective_config_artifact_id",
        "composite_run_identity",
        "execution_fingerprint",
        "silver_filter_compatibility_mode",
        "required_persistence_profile",
    )
    return {
        field_name: (
            _coerce_optional_str(getattr(run_context, field_name, None))
            if run_context is not None
            else None
        )
        for field_name in field_names
    }


def _resolve_checkpoint_snapshot_identity(
    pipeline: object,
) -> tuple[tuple[dict[str, object], ...], tuple[str, ...], str | None]:
    """Resolve serialized snapshot refs plus their checkpoint identity anchors."""
    input_snapshot_refs = _resolve_input_snapshot_refs(pipeline)
    input_snapshot_ids = tuple(
        str(snapshot["snapshot_id"])
        for snapshot in input_snapshot_refs
        if snapshot.get("snapshot_id") is not None
    )
    input_snapshot_fingerprint = compute_input_snapshot_identity_fingerprint(
        list(input_snapshot_refs)
    )
    return input_snapshot_refs, input_snapshot_ids, input_snapshot_fingerprint


__all__ = [
    "_coerce_optional_str",
    "_normalize_execution_identity_payload",
    "_resolve_checkpoint_snapshot_identity",
    "_resolve_input_snapshot_refs",
    "_resolve_run_context_metadata",
    "_resolve_run_context_payload",
    "_serialize_input_snapshot_ref",
]
