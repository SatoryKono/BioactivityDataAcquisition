"""Checkpoint metadata assembly helpers for pipeline runner composition."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.composition.runtime_builders.config_access import get_settings
from bioetl.composition.runtime_builders.input_snapshot_resolution import (
    resolve_cached_bronze_input_snapshot_refs,
    resolve_manifest_input_snapshot_refs,
)
from bioetl.domain.normalization import (
    build_execution_identity_payload,
    compute_execution_identity_fingerprint,
    compute_input_snapshot_identity_fingerprint,
)
from bioetl.domain.types.checkpoint_metadata import CheckpointMetadata
from bioetl.domain.filtering.silver_filter_identity import (
    resolve_silver_filter_compatibility_mode,
)

if TYPE_CHECKING:
    from bioetl.application.core.base import BasePipeline


def _resolve_run_context_payload(pipeline: BasePipeline) -> object | None:
    """Resolve metadata run_context from pipeline services when available."""
    metadata_coordinator = getattr(pipeline.services, "metadata_coordinator", None)
    if metadata_coordinator is None:
        return None
    return getattr(metadata_coordinator, "run_context", None)


def _coerce_optional_str(value: object | None) -> str | None:
    """Return a string value when present, otherwise None."""
    if value is None:
        return None
    text = str(value)
    return text or None


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


def _serialize_input_snapshot_ref(snapshot: object) -> dict[str, object]:
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
        "captured_at": (
            captured_at.isoformat() if hasattr(captured_at, "isoformat") else None
        ),
    }


def _resolve_input_snapshot_refs(
    pipeline: BasePipeline,
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
    pipeline: BasePipeline,
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
    pipeline: BasePipeline,
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


def _build_checkpoint_run_context(
    *,
    pipeline_name: str,
    run_context_metadata: dict[str, str | None],
    execution_fingerprint: str,
    silver_filter_compatibility_mode: str,
    identity_payload: dict[str, str | None],
) -> dict[str, str | None]:
    """Build the persisted run-context checkpoint fragment."""
    return {
        "pipeline_name": pipeline_name,
        "manifest_id": run_context_metadata["manifest_id"],
        "execution_fingerprint": execution_fingerprint,
        "silver_filter_compatibility_mode": silver_filter_compatibility_mode,
        "required_persistence_profile": run_context_metadata[
            "required_persistence_profile"
        ],
        "git_commit": run_context_metadata["git_commit"],
        "dependency_lock_hash": run_context_metadata["dependency_lock_hash"],
        "effective_config_hash": identity_payload["effective_config_hash"],
        "effective_config_artifact_id": run_context_metadata[
            "effective_config_artifact_id"
        ],
        "dq_contract_compatibility_hash": identity_payload[
            "dq_contract_compatibility_hash"
        ],
        "normalization_profile_ref": identity_payload["normalization_profile_ref"],
        "normalization_profile_version": identity_payload[
            "normalization_profile_version"
        ],
        "normalization_profile_hash": identity_payload["normalization_profile_hash"],
    }


def _build_checkpoint_metadata_from_identity(
    *,
    pipeline_name: str,
    run_type_value: str,
    run_context_metadata: dict[str, str | None],
    identity_payload: dict[str, str | None],
    execution_fingerprint: str,
    exact_replay: bool,
    input_snapshot_refs: tuple[dict[str, object], ...],
    input_snapshot_ids: tuple[str, ...],
    input_snapshot_fingerprint: str | None,
    silver_filter_compatibility_mode: str,
    run_context: dict[str, str | None],
) -> CheckpointMetadata:
    """Build the final checkpoint metadata value object."""
    return CheckpointMetadata(
        records_processed=0,
        pipeline_name=pipeline_name,
        run_type=run_type_value,
        dq_contract_compatibility_hash=identity_payload[
            "dq_contract_compatibility_hash"
        ],
        pipeline_version=identity_payload["pipeline_version"],
        git_commit=identity_payload["git_commit"],
        dependency_lock_hash=run_context_metadata["dependency_lock_hash"],
        effective_config_hash=identity_payload["effective_config_hash"],
        effective_config_artifact_id=run_context_metadata[
            "effective_config_artifact_id"
        ],
        execution_fingerprint=execution_fingerprint,
        composite_run_identity=run_context_metadata["composite_run_identity"],
        manifest_id=run_context_metadata["manifest_id"],
        contract_ref=identity_payload["contract_ref"],
        contract_version=identity_payload["contract_version"],
        normalization_profile_ref=identity_payload["normalization_profile_ref"],
        normalization_profile_version=identity_payload[
            "normalization_profile_version"
        ],
        normalization_profile_hash=identity_payload["normalization_profile_hash"],
        exact_replay=exact_replay,
        required_persistence_profile=run_context_metadata[
            "required_persistence_profile"
        ],
        input_snapshot_refs=input_snapshot_refs,
        input_snapshot_ids=input_snapshot_ids,
        input_snapshot_fingerprint=input_snapshot_fingerprint,
        silver_filter_compatibility_mode=silver_filter_compatibility_mode,
        run_context=run_context,
    )


def build_current_checkpoint_metadata(pipeline: BasePipeline) -> CheckpointMetadata:
    """Build current execution identity metadata for checkpoint compatibility."""
    run_context_metadata = _resolve_run_context_metadata(pipeline)
    exact_replay = bool(getattr(pipeline.runtime, "exact_replay", False))
    (
        input_snapshot_refs,
        input_snapshot_ids,
        input_snapshot_fingerprint,
    ) = _resolve_checkpoint_snapshot_identity(pipeline)

    run_type = pipeline.runtime.run_type
    run_type_value = run_type.value if hasattr(run_type, "value") else str(run_type)
    pipeline_name = pipeline.config.pipeline_name
    silver_filter_compatibility_mode = (
        run_context_metadata["silver_filter_compatibility_mode"]
        or _coerce_optional_str(
            getattr(pipeline.runtime, "silver_filter_compatibility_mode", None)
        )
        or resolve_silver_filter_compatibility_mode()
    )
    identity_payload = _normalize_execution_identity_payload(
        pipeline_name=pipeline_name,
        run_type=run_type_value,
        pipeline_version=run_context_metadata["pipeline_version"],
        git_commit=run_context_metadata["git_commit"],
        dependency_lock_hash=run_context_metadata["dependency_lock_hash"],
        effective_config_hash=run_context_metadata["effective_config_hash"],
        dq_contract_compatibility_hash=run_context_metadata[
            "dq_contract_compatibility_hash"
        ],
        manifest_id=run_context_metadata["manifest_id"],
        contract=(
            run_context_metadata["contract_ref"],
            run_context_metadata["contract_version"],
        ),
        normalization_profile=(
            run_context_metadata["normalization_profile_ref"],
            run_context_metadata["normalization_profile_version"],
            run_context_metadata["normalization_profile_hash"],
        ),
        effective_config_artifact_id=run_context_metadata[
            "effective_config_artifact_id"
        ],
        exact_replay=exact_replay,
        input_snapshot_fingerprint=input_snapshot_fingerprint,
        silver_filter_compatibility_mode=silver_filter_compatibility_mode,
    )
    execution_fingerprint = run_context_metadata["execution_fingerprint"] or (
        compute_execution_identity_fingerprint(identity_payload)
    )
    run_context = _build_checkpoint_run_context(
        pipeline_name=pipeline_name,
        run_context_metadata=run_context_metadata,
        execution_fingerprint=execution_fingerprint,
        silver_filter_compatibility_mode=silver_filter_compatibility_mode,
        identity_payload=identity_payload,
    )

    return _build_checkpoint_metadata_from_identity(
        pipeline_name=pipeline_name,
        run_type_value=run_type_value,
        run_context_metadata=run_context_metadata,
        identity_payload=identity_payload,
        execution_fingerprint=execution_fingerprint,
        exact_replay=exact_replay,
        input_snapshot_refs=input_snapshot_refs,
        input_snapshot_ids=input_snapshot_ids,
        input_snapshot_fingerprint=input_snapshot_fingerprint,
        silver_filter_compatibility_mode=silver_filter_compatibility_mode,
        run_context=run_context,
    )
