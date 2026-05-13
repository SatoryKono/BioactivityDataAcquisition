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
from bioetl.infrastructure.config.silver_filter_migration import (
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
    contract_ref: str | None,
    contract_version: str | None,
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
        contract_ref=contract_ref,
        contract_version=contract_version,
        effective_config_artifact_id=effective_config_artifact_id,
        exact_replay=exact_replay,
        input_snapshot_fingerprint=input_snapshot_fingerprint,
        silver_filter_compatibility_mode=silver_filter_compatibility_mode,
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
    )
    return tuple(snapshot.snapshot_id for snapshot in snapshot_refs)


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
        "effective_config_artifact_id",
        "composite_run_identity",
        "execution_fingerprint",
        "silver_filter_compatibility_mode",
    )
    return {
        field_name: (
            _coerce_optional_str(getattr(run_context, field_name, None))
            if run_context is not None
            else None
        )
        for field_name in field_names
    }


def build_current_checkpoint_metadata(pipeline: BasePipeline) -> CheckpointMetadata:
    """Build current execution identity metadata for checkpoint compatibility."""
    run_context_metadata = _resolve_run_context_metadata(pipeline)
    exact_replay = bool(getattr(pipeline.runtime, "exact_replay", False))
    input_snapshot_ids = _resolve_input_snapshot_ids(pipeline)
    input_snapshot_fingerprint = compute_input_snapshot_identity_fingerprint(
        list(input_snapshot_ids)
    )

    run_type = pipeline.runtime.run_type
    run_type_value = run_type.value if hasattr(run_type, "value") else str(run_type)
    silver_filter_compatibility_mode = (
        run_context_metadata["silver_filter_compatibility_mode"]
        or _coerce_optional_str(
            getattr(pipeline.runtime, "silver_filter_compatibility_mode", None)
        )
        or resolve_silver_filter_compatibility_mode()
    )
    identity_payload = _normalize_execution_identity_payload(
        pipeline_name=pipeline.config.pipeline_name,
        run_type=run_type_value,
        pipeline_version=run_context_metadata["pipeline_version"],
        git_commit=run_context_metadata["git_commit"],
        dependency_lock_hash=run_context_metadata["dependency_lock_hash"],
        effective_config_hash=run_context_metadata["effective_config_hash"],
        dq_contract_compatibility_hash=run_context_metadata[
            "dq_contract_compatibility_hash"
        ],
        manifest_id=run_context_metadata["manifest_id"],
        contract_ref=run_context_metadata["contract_ref"],
        contract_version=run_context_metadata["contract_version"],
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

    return CheckpointMetadata(
        records_processed=0,
        pipeline_name=pipeline.config.pipeline_name,
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
        exact_replay=exact_replay,
        input_snapshot_ids=input_snapshot_ids,
        input_snapshot_fingerprint=input_snapshot_fingerprint,
        silver_filter_compatibility_mode=silver_filter_compatibility_mode,
        run_context={
            "pipeline_name": pipeline.config.pipeline_name,
            "manifest_id": run_context_metadata["manifest_id"],
            "execution_fingerprint": execution_fingerprint,
            "silver_filter_compatibility_mode": silver_filter_compatibility_mode,
            "git_commit": run_context_metadata["git_commit"],
            "dependency_lock_hash": run_context_metadata["dependency_lock_hash"],
            "effective_config_hash": identity_payload["effective_config_hash"],
            "effective_config_artifact_id": run_context_metadata[
                "effective_config_artifact_id"
            ],
            "dq_contract_compatibility_hash": identity_payload[
                "dq_contract_compatibility_hash"
            ],
        },
    )
