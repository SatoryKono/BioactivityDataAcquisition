"""Execution-identity helpers for checkpoint compatibility runtime."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from bioetl.domain.normalization import (
    build_execution_identity_payload,
    compute_degraded_runtime_anchor_fingerprint,
    compute_execution_identity_fingerprint,
    normalize_runtime_anchor_payload,
)
from bioetl.domain.types import JsonDict

_SEVERITY_MAJOR: Final[str] = "major"
_SEVERITY_NONE: Final[str] = "none"

_CANONICAL_ONLY_IDENTITY_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "pipeline_name",
        "run_type",
        "pipeline_version",
        "dq_contract_compatibility_hash",
        "exact_replay",
        "input_snapshot_fingerprint",
    }
)


@dataclass(frozen=True, slots=True)
class CheckpointExecutionIdentityFallbackContext:
    """Canonical inputs for checkpoint execution-identity fallback comparison."""

    pipeline_name: str | None
    run_type: str | None
    pipeline_version: str | None
    effective_config_hash: str | None
    dq_contract_compatibility_hash: str | None
    contract_ref: str | None
    contract_version: str | None
    effective_config_artifact_id: str | None
    exact_replay: bool | None
    input_snapshot_fingerprint: str | None


@dataclass(frozen=True, slots=True)
class ExecutionIdentityCompatibilityContext:
    """Canonical runtime/checkpoint identity input bundle."""

    composite_run_identity: str | None
    execution_fingerprint: str | None
    manifest_id: str | None
    fallback: CheckpointExecutionIdentityFallbackContext


def check_execution_identity_compatibility(
    *,
    current: ExecutionIdentityCompatibilityContext,
    checkpoint: ExecutionIdentityCompatibilityContext,
) -> JsonDict:
    """Check execution identity using canonical manifest and fallback anchors."""
    composite_identity_result = _check_composite_run_identity_compatibility(
        current_composite_run_identity=current.composite_run_identity,
        checkpoint_composite_run_identity=checkpoint.composite_run_identity,
    )
    if composite_identity_result is not None:
        return composite_identity_result

    execution_fingerprint_result = _compare_optional_identity_fingerprints(
        current.execution_fingerprint,
        checkpoint.execution_fingerprint,
        match_reason="identical_execution_fingerprint",
        mismatch_reason="execution_fingerprint_mismatch",
    )
    if execution_fingerprint_result is not None:
        return execution_fingerprint_result

    checkpoint_fallback_result = _check_checkpoint_execution_identity_fallback(
        current=current.fallback,
        checkpoint=checkpoint.fallback,
    )
    if checkpoint_fallback_result is not None:
        return checkpoint_fallback_result

    runtime_anchor_result = _check_degraded_runtime_anchor_compatibility(
        current=current,
        checkpoint=checkpoint,
    )
    if runtime_anchor_result is not None:
        return runtime_anchor_result
    return {
        "compatible": True,
        "reason": "execution_identity_not_enforced",
        "severity": _SEVERITY_NONE,
    }


def _check_composite_run_identity_compatibility(
    *,
    current_composite_run_identity: str | None,
    checkpoint_composite_run_identity: str | None,
) -> JsonDict | None:
    """Return an enforced compatibility verdict for composite run identity."""
    normalized = normalize_runtime_anchor_payload(
        {
            "current": current_composite_run_identity,
            "checkpoint": checkpoint_composite_run_identity,
        }
    )
    current_identity = normalized["current"] or ""
    checkpoint_identity = normalized["checkpoint"] or ""
    if not current_identity and not checkpoint_identity:
        return None
    if not current_identity or not checkpoint_identity:
        return {
            "compatible": False,
            "reason": "composite_run_identity_missing",
            "severity": _SEVERITY_MAJOR,
        }
    if current_identity != checkpoint_identity:
        return {
            "compatible": False,
            "reason": "composite_run_identity_mismatch",
            "severity": _SEVERITY_MAJOR,
        }
    return {
        "compatible": True,
        "reason": "identical_composite_run_identity",
        "severity": _SEVERITY_NONE,
    }


def _compatibility_verdict(*, compatible: bool, reason: str) -> JsonDict:
    """Build a normalized execution-identity compatibility verdict."""
    return {
        "compatible": compatible,
        "reason": reason,
        "severity": _SEVERITY_NONE if compatible else _SEVERITY_MAJOR,
    }


def _compare_optional_identity_fingerprints(
    current_value: str | None,
    checkpoint_value: str | None,
    *,
    match_reason: str,
    mismatch_reason: str,
) -> JsonDict | None:
    """Compare two optional fingerprints only when both are available."""
    if not current_value or not checkpoint_value:
        return None
    return _compatibility_verdict(
        compatible=current_value == checkpoint_value,
        reason=match_reason if current_value == checkpoint_value else mismatch_reason,
    )


def _build_checkpoint_execution_identity_payload(
    *,
    pipeline_name: str | None,
    run_type: str | None,
    pipeline_version: str | None,
    effective_config_hash: str | None,
    dq_contract_compatibility_hash: str | None,
    contract_ref: str | None,
    contract_version: str | None,
    effective_config_artifact_id: str | None,
    exact_replay: bool | None,
    input_snapshot_fingerprint: str | None,
) -> JsonDict:
    """Build the canonical checkpoint execution-identity fallback payload."""
    if all(
        value is None
        for value in (
            pipeline_name,
            run_type,
            pipeline_version,
            dq_contract_compatibility_hash,
            exact_replay,
            input_snapshot_fingerprint,
        )
    ):
        return {}
    normalized_payload = build_execution_identity_payload(
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
    return {
        key: value for key, value in normalized_payload.items() if value is not None
    }


def _compute_checkpoint_execution_identity_fallback_fingerprint(
    request: CheckpointExecutionIdentityFallbackContext,
) -> str | None:
    """Build the canonical checkpoint execution-identity fallback fingerprint."""
    payload = _build_checkpoint_execution_identity_payload(
        pipeline_name=request.pipeline_name,
        run_type=request.run_type,
        pipeline_version=request.pipeline_version,
        effective_config_hash=request.effective_config_hash,
        dq_contract_compatibility_hash=request.dq_contract_compatibility_hash,
        contract_ref=request.contract_ref,
        contract_version=request.contract_version,
        effective_config_artifact_id=request.effective_config_artifact_id,
        exact_replay=request.exact_replay,
        input_snapshot_fingerprint=request.input_snapshot_fingerprint,
    )
    if not payload or not any(
        field in payload for field in _CANONICAL_ONLY_IDENTITY_FIELDS
    ):
        return None
    return compute_execution_identity_fingerprint(payload)


def _check_checkpoint_execution_identity_fallback(
    *,
    current: CheckpointExecutionIdentityFallbackContext,
    checkpoint: CheckpointExecutionIdentityFallbackContext,
) -> JsonDict | None:
    """Compare canonical checkpoint execution-identity fallback fingerprints."""
    current_fingerprint = _compute_checkpoint_execution_identity_fallback_fingerprint(
        current
    )
    checkpoint_fingerprint = (
        _compute_checkpoint_execution_identity_fallback_fingerprint(checkpoint)
    )
    return _compare_optional_identity_fingerprints(
        current_fingerprint,
        checkpoint_fingerprint,
        match_reason="identical_checkpoint_execution_identity_fallback",
        mismatch_reason="checkpoint_execution_identity_fallback_mismatch",
    )


def _compute_degraded_runtime_anchor_fingerprint(
    *,
    manifest_id: str | None,
    contract_ref: str | None,
    contract_version: str | None,
    effective_config_hash: str | None,
    effective_config_artifact_id: str | None,
) -> str | None:
    """Build the degraded runtime-anchor fallback fingerprint via domain seam."""
    raw_payload = {
        key: value
        for key, value in {
            "effective_config_hash": effective_config_hash,
            "effective_config_artifact_id": effective_config_artifact_id,
            "contract_ref": contract_ref,
            "contract_version": contract_version,
        }.items()
        if value is not None
    }
    if not raw_payload:
        return None
    if manifest_id is not None:
        raw_payload["manifest_id"] = manifest_id
    normalized_payload = normalize_runtime_anchor_payload(raw_payload)
    return compute_degraded_runtime_anchor_fingerprint(normalized_payload)


def _check_degraded_runtime_anchor_compatibility(
    *,
    current: ExecutionIdentityCompatibilityContext,
    checkpoint: ExecutionIdentityCompatibilityContext,
) -> JsonDict | None:
    """Compare degraded runtime-anchor fingerprints when both anchors exist."""
    current_fingerprint = _compute_degraded_runtime_anchor_fingerprint(
        manifest_id=current.manifest_id,
        contract_ref=current.fallback.contract_ref,
        contract_version=current.fallback.contract_version,
        effective_config_hash=current.fallback.effective_config_hash,
        effective_config_artifact_id=current.fallback.effective_config_artifact_id,
    )
    checkpoint_fingerprint = _compute_degraded_runtime_anchor_fingerprint(
        manifest_id=checkpoint.manifest_id,
        contract_ref=checkpoint.fallback.contract_ref,
        contract_version=checkpoint.fallback.contract_version,
        effective_config_hash=checkpoint.fallback.effective_config_hash,
        effective_config_artifact_id=checkpoint.fallback.effective_config_artifact_id,
    )
    return _compare_optional_identity_fingerprints(
        current_fingerprint,
        checkpoint_fingerprint,
        match_reason="identical_degraded_runtime_anchor_fingerprint",
        mismatch_reason="degraded_runtime_anchor_fingerprint_mismatch",
    )
