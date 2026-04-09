"""Checkpoint metadata assembly helpers for pipeline runner composition."""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

from bioetl.domain.normalization import (
    normalize_runtime_anchor_payload,
    serialize_json_canonical,
)
from bioetl.domain.types.checkpoint_metadata import CheckpointMetadata

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


def _compute_execution_identity_fingerprint(
    payload: dict[str, str | None],
) -> str:
    """Compute deterministic execution identity fingerprint for checkpoints."""
    encoded = serialize_json_canonical(payload)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _normalize_execution_identity_payload(
    *,
    pipeline_name: str,
    run_type: str,
    pipeline_version: str | None,
    effective_config_hash: str | None,
    dq_contract_compatibility_hash: str | None,
) -> dict[str, str | None]:
    """Return the canonical checkpoint execution-identity payload."""
    return normalize_runtime_anchor_payload(
        {
            "pipeline_name": pipeline_name,
            "run_type": run_type,
            "pipeline_version": pipeline_version,
            "effective_config_hash": effective_config_hash,
            "dq_contract_compatibility_hash": dq_contract_compatibility_hash,
        }
    )


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
    effective_config_artifact_id = (
        _coerce_optional_str(getattr(run_context, "effective_config_artifact_id", None))
        if run_context is not None
        else None
    )

    run_type = pipeline.runtime.run_type
    run_type_value = run_type.value if hasattr(run_type, "value") else str(run_type)
    identity_payload = _normalize_execution_identity_payload(
        pipeline_name=pipeline.config.pipeline_name,
        run_type=run_type_value,
        pipeline_version=pipeline_version,
        effective_config_hash=effective_config_hash,
        dq_contract_compatibility_hash=dq_contract_compatibility_hash,
    )
    execution_fingerprint = _compute_execution_identity_fingerprint(
        identity_payload
    )

    return CheckpointMetadata(
        records_processed=0,
        dq_contract_compatibility_hash=identity_payload["dq_contract_compatibility_hash"],
        pipeline_version=identity_payload["pipeline_version"],
        effective_config_hash=identity_payload["effective_config_hash"],
        effective_config_artifact_id=effective_config_artifact_id,
        execution_fingerprint=execution_fingerprint,
        run_context={
            "pipeline_name": pipeline.config.pipeline_name,
            "manifest_id": (
                None
                if run_context is None
                else _coerce_optional_str(getattr(run_context, "manifest_id", None))
            ),
        },
    )
