"""Checkpoint metadata assembly helpers for pipeline runner composition."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from bioetl.composition.runtime_builders.cached_bronze_snapshot_support import (
    build_cached_bronze_input_snapshot_refs,
)
from bioetl.domain.normalization import (
    build_execution_identity_payload,
    compute_execution_identity_fingerprint,
    compute_input_snapshot_identity_fingerprint,
)
from bioetl.domain.types.checkpoint_metadata import CheckpointMetadata
from bioetl.infrastructure.config import get_settings

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
    effective_config_hash: str | None,
    dq_contract_compatibility_hash: str | None,
    manifest_id: str | None,
    contract_ref: str | None,
    contract_version: str | None,
    effective_config_artifact_id: str | None,
    exact_replay: bool,
    input_snapshot_fingerprint: str | None,
) -> dict[str, str | None]:
    """Return the canonical checkpoint execution-identity payload."""
    del manifest_id
    return build_execution_identity_payload(
        pipeline_name=pipeline_name,
        run_type=run_type,
        pipeline_version=pipeline_version,
        effective_config_hash=effective_config_hash,
        dq_contract_compatibility_hash=dq_contract_compatibility_hash,
        contract_ref=contract_ref,
        contract_version=contract_version,
        effective_config_artifact_id=effective_config_artifact_id,
        exact_replay=exact_replay,
        input_snapshot_fingerprint=input_snapshot_fingerprint,
    )


def _resolve_input_snapshot_ids(pipeline: BasePipeline) -> tuple[str, ...]:
    """Resolve cached-Bronze snapshot identities for replay-safe checkpoints."""
    runtime = getattr(pipeline, "runtime", None)
    cached_bronze = None if runtime is None else getattr(runtime, "cached_bronze", None)
    if cached_bronze is None or not getattr(cached_bronze, "enabled", False):
        return ()

    config = getattr(pipeline, "config", None)
    provider = _coerce_optional_str(getattr(config, "provider", None))
    entity = _coerce_optional_str(getattr(config, "entity_type", None))
    if provider is None or entity is None:
        return ()

    settings = get_settings()
    bronze_root = (
        Path(cached_bronze.bronze_path)
        if getattr(cached_bronze, "bronze_path", None)
        else settings.bronze_path / provider / entity
    )
    bronze_date = _coerce_optional_str(getattr(cached_bronze, "bronze_date", None))
    snapshot_refs = build_cached_bronze_input_snapshot_refs(
        bronze_root=bronze_root,
        bronze_date=bronze_date,
        pipeline_name=pipeline.config.pipeline_name,
    )
    return tuple(snapshot.snapshot_id for snapshot in snapshot_refs)


def build_current_checkpoint_metadata(pipeline: BasePipeline) -> CheckpointMetadata:
    """Build current execution identity metadata for checkpoint compatibility."""
    run_context = _resolve_run_context_payload(pipeline)
    pipeline_version = (
        _coerce_optional_str(getattr(run_context, "pipeline_version", None))
        if run_context is not None
        else None
    )
    effective_config_hash = (
        _coerce_optional_str(getattr(run_context, "config_hash", None))
        if run_context is not None
        else None
    )
    dq_contract_compatibility_hash = (
        _coerce_optional_str(
            getattr(run_context, "dq_contract_compatibility_hash", None)
        )
        if run_context is not None
        else None
    )
    manifest_id = (
        _coerce_optional_str(getattr(run_context, "manifest_id", None))
        if run_context is not None
        else None
    )
    contract_ref = (
        _coerce_optional_str(getattr(run_context, "contract_ref", None))
        if run_context is not None
        else None
    )
    contract_version = (
        _coerce_optional_str(getattr(run_context, "contract_version", None))
        if run_context is not None
        else None
    )
    effective_config_artifact_id = (
        _coerce_optional_str(getattr(run_context, "effective_config_artifact_id", None))
        if run_context is not None
        else None
    )
    composite_run_identity = (
        _coerce_optional_str(getattr(run_context, "composite_run_identity", None))
        if run_context is not None
        else None
    )
    exact_replay = bool(getattr(pipeline.runtime, "exact_replay", False))
    input_snapshot_ids = _resolve_input_snapshot_ids(pipeline)
    input_snapshot_fingerprint = compute_input_snapshot_identity_fingerprint(
        list(input_snapshot_ids)
    )

    run_type = pipeline.runtime.run_type
    run_type_value = run_type.value if hasattr(run_type, "value") else str(run_type)
    identity_payload = _normalize_execution_identity_payload(
        pipeline_name=pipeline.config.pipeline_name,
        run_type=run_type_value,
        pipeline_version=pipeline_version,
        effective_config_hash=effective_config_hash,
        dq_contract_compatibility_hash=dq_contract_compatibility_hash,
        manifest_id=manifest_id,
        contract_ref=contract_ref,
        contract_version=contract_version,
        effective_config_artifact_id=effective_config_artifact_id,
        exact_replay=exact_replay,
        input_snapshot_fingerprint=input_snapshot_fingerprint,
    )
    execution_fingerprint = compute_execution_identity_fingerprint(identity_payload)

    return CheckpointMetadata(
        records_processed=0,
        pipeline_name=pipeline.config.pipeline_name,
        run_type=run_type_value,
        dq_contract_compatibility_hash=identity_payload[
            "dq_contract_compatibility_hash"
        ],
        pipeline_version=identity_payload["pipeline_version"],
        effective_config_hash=identity_payload["effective_config_hash"],
        effective_config_artifact_id=effective_config_artifact_id,
        execution_fingerprint=execution_fingerprint,
        composite_run_identity=composite_run_identity,
        manifest_id=manifest_id,
        contract_ref=identity_payload["contract_ref"],
        contract_version=identity_payload["contract_version"],
        exact_replay=exact_replay,
        input_snapshot_ids=input_snapshot_ids,
        input_snapshot_fingerprint=input_snapshot_fingerprint,
        run_context={
            "pipeline_name": pipeline.config.pipeline_name,
            "manifest_id": manifest_id,
        },
    )
