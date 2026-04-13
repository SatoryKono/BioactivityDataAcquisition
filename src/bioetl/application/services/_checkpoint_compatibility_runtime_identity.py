"""Execution-identity helpers for checkpoint compatibility runtime."""

from __future__ import annotations

from typing import Final

from bioetl.domain.normalization import (
    build_execution_identity_payload,
    compute_degraded_runtime_anchor_fingerprint,
    compute_execution_identity_fingerprint,
    normalize_runtime_anchor_payload,
)
from bioetl.domain.types import JsonDict
from bioetl.domain.types.execution_phase import ExecutionPhase

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


def check_execution_identity_compatibility(
    *,
    current_composite_run_identity: str | None,
    checkpoint_composite_run_identity: str | None,
    current_execution_fingerprint: str | None,
    checkpoint_execution_fingerprint: str | None,
    current_pipeline_name: str | None,
    checkpoint_pipeline_name: str | None,
    current_run_type: str | None,
    checkpoint_run_type: str | None,
    current_pipeline_version: str | None,
    checkpoint_pipeline_version: str | None,
    current_manifest_id: str | None,
    checkpoint_manifest_id: str | None,
    current_dq_contract_compatibility_hash: str | None,
    checkpoint_dq_contract_compatibility_hash: str | None,
    current_contract_ref: str | None,
    checkpoint_contract_ref: str | None,
    current_contract_version: str | None,
    checkpoint_contract_version: str | None,
    current_effective_config_hash: str | None,
    checkpoint_effective_config_hash: str | None,
    current_effective_config_artifact_id: str | None,
    checkpoint_effective_config_artifact_id: str | None,
    current_exact_replay: bool | None,
    checkpoint_exact_replay: bool | None,
    current_input_snapshot_fingerprint: str | None,
    checkpoint_input_snapshot_fingerprint: str | None,
) -> JsonDict:
    """Check execution identity using canonical manifest and fallback anchors."""
    composite_identity_result = _check_composite_run_identity_compatibility(
        current_composite_run_identity=current_composite_run_identity,
        checkpoint_composite_run_identity=checkpoint_composite_run_identity,
    )
    if composite_identity_result is not None:
        return composite_identity_result

    execution_fingerprint_result = _compare_optional_identity_fingerprints(
        current_execution_fingerprint,
        checkpoint_execution_fingerprint,
        match_reason="identical_execution_fingerprint",
        mismatch_reason="execution_fingerprint_mismatch",
    )
    if execution_fingerprint_result is not None:
        return execution_fingerprint_result

    checkpoint_fallback_result = _check_checkpoint_execution_identity_fallback(
        current_pipeline_name=current_pipeline_name,
        checkpoint_pipeline_name=checkpoint_pipeline_name,
        current_run_type=current_run_type,
        checkpoint_run_type=checkpoint_run_type,
        current_pipeline_version=current_pipeline_version,
        checkpoint_pipeline_version=checkpoint_pipeline_version,
        current_effective_config_hash=current_effective_config_hash,
        checkpoint_effective_config_hash=checkpoint_effective_config_hash,
        current_dq_contract_compatibility_hash=current_dq_contract_compatibility_hash,
        checkpoint_dq_contract_compatibility_hash=(
            checkpoint_dq_contract_compatibility_hash
        ),
        current_contract_ref=current_contract_ref,
        checkpoint_contract_ref=checkpoint_contract_ref,
        current_contract_version=current_contract_version,
        checkpoint_contract_version=checkpoint_contract_version,
        current_effective_config_artifact_id=current_effective_config_artifact_id,
        checkpoint_effective_config_artifact_id=checkpoint_effective_config_artifact_id,
        current_exact_replay=current_exact_replay,
        checkpoint_exact_replay=checkpoint_exact_replay,
        current_input_snapshot_fingerprint=current_input_snapshot_fingerprint,
        checkpoint_input_snapshot_fingerprint=checkpoint_input_snapshot_fingerprint,
    )
    if checkpoint_fallback_result is not None:
        return checkpoint_fallback_result

    runtime_anchor_result = _check_degraded_runtime_anchor_compatibility(
        current_manifest_id=current_manifest_id,
        checkpoint_manifest_id=checkpoint_manifest_id,
        current_contract_ref=current_contract_ref,
        checkpoint_contract_ref=checkpoint_contract_ref,
        current_contract_version=current_contract_version,
        checkpoint_contract_version=checkpoint_contract_version,
        current_effective_config_hash=current_effective_config_hash,
        checkpoint_effective_config_hash=checkpoint_effective_config_hash,
        current_effective_config_artifact_id=current_effective_config_artifact_id,
        checkpoint_effective_config_artifact_id=checkpoint_effective_config_artifact_id,
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
        key: value
        for key, value in normalized_payload.items()
        if value is not None
    }


def _compute_checkpoint_execution_identity_fallback_fingerprint(
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
) -> str | None:
    """Build the canonical checkpoint execution-identity fallback fingerprint."""
    payload = _build_checkpoint_execution_identity_payload(
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
    if not payload or not any(
        field in payload for field in _CANONICAL_ONLY_IDENTITY_FIELDS
    ):
        return None
    return compute_execution_identity_fingerprint(payload)


def _check_checkpoint_execution_identity_fallback(
    *,
    current_pipeline_name: str | None,
    checkpoint_pipeline_name: str | None,
    current_run_type: str | None,
    checkpoint_run_type: str | None,
    current_pipeline_version: str | None,
    checkpoint_pipeline_version: str | None,
    current_effective_config_hash: str | None,
    checkpoint_effective_config_hash: str | None,
    current_dq_contract_compatibility_hash: str | None,
    checkpoint_dq_contract_compatibility_hash: str | None,
    current_contract_ref: str | None,
    checkpoint_contract_ref: str | None,
    current_contract_version: str | None,
    checkpoint_contract_version: str | None,
    current_effective_config_artifact_id: str | None,
    checkpoint_effective_config_artifact_id: str | None,
    current_exact_replay: bool | None,
    checkpoint_exact_replay: bool | None,
    current_input_snapshot_fingerprint: str | None,
    checkpoint_input_snapshot_fingerprint: str | None,
) -> JsonDict | None:
    """Compare canonical checkpoint execution-identity fallback fingerprints."""
    current_fingerprint = _compute_checkpoint_execution_identity_fallback_fingerprint(
        pipeline_name=current_pipeline_name,
        run_type=current_run_type,
        pipeline_version=current_pipeline_version,
        effective_config_hash=current_effective_config_hash,
        dq_contract_compatibility_hash=current_dq_contract_compatibility_hash,
        contract_ref=current_contract_ref,
        contract_version=current_contract_version,
        effective_config_artifact_id=current_effective_config_artifact_id,
        exact_replay=current_exact_replay,
        input_snapshot_fingerprint=current_input_snapshot_fingerprint,
    )
    checkpoint_fingerprint = _compute_checkpoint_execution_identity_fallback_fingerprint(
        pipeline_name=checkpoint_pipeline_name,
        run_type=checkpoint_run_type,
        pipeline_version=checkpoint_pipeline_version,
        effective_config_hash=checkpoint_effective_config_hash,
        dq_contract_compatibility_hash=checkpoint_dq_contract_compatibility_hash,
        contract_ref=checkpoint_contract_ref,
        contract_version=checkpoint_contract_version,
        effective_config_artifact_id=checkpoint_effective_config_artifact_id,
        exact_replay=checkpoint_exact_replay,
        input_snapshot_fingerprint=checkpoint_input_snapshot_fingerprint,
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
    current_manifest_id: str | None,
    checkpoint_manifest_id: str | None,
    current_contract_ref: str | None,
    checkpoint_contract_ref: str | None,
    current_contract_version: str | None,
    checkpoint_contract_version: str | None,
    current_effective_config_hash: str | None,
    checkpoint_effective_config_hash: str | None,
    current_effective_config_artifact_id: str | None,
    checkpoint_effective_config_artifact_id: str | None,
) -> JsonDict | None:
    """Compare degraded runtime-anchor fingerprints when both anchors exist."""
    current_fingerprint = _compute_degraded_runtime_anchor_fingerprint(
        manifest_id=current_manifest_id,
        contract_ref=current_contract_ref,
        contract_version=current_contract_version,
        effective_config_hash=current_effective_config_hash,
        effective_config_artifact_id=current_effective_config_artifact_id,
    )
    checkpoint_fingerprint = _compute_degraded_runtime_anchor_fingerprint(
        manifest_id=checkpoint_manifest_id,
        contract_ref=checkpoint_contract_ref,
        contract_version=checkpoint_contract_version,
        effective_config_hash=checkpoint_effective_config_hash,
        effective_config_artifact_id=checkpoint_effective_config_artifact_id,
    )
    return _compare_optional_identity_fingerprints(
        current_fingerprint,
        checkpoint_fingerprint,
        match_reason="identical_degraded_runtime_anchor_fingerprint",
        mismatch_reason="degraded_runtime_anchor_fingerprint_mismatch",
    )


def _identity_detail_value(value: str | None) -> str:
    """Normalize optional string identity fields for structured detail payloads."""
    return value or ""


def _identity_detail_bool(value: bool | None) -> str:
    """Normalize optional boolean identity fields for structured detail payloads."""
    return "" if value is None else str(value).lower()


def _checkpoint_execution_identity_fallback_detail(payload: JsonDict) -> str:
    """Return the canonical checkpoint fallback fingerprint for diagnostics."""
    if not payload:
        return ""
    return compute_execution_identity_fingerprint(payload)


def _degraded_runtime_anchor_detail(
    *,
    manifest_id: str | None,
    contract_ref: str | None,
    contract_version: str | None,
    effective_config_hash: str,
    effective_config_artifact_id: str | None,
) -> str:
    """Return the degraded runtime-anchor fingerprint for diagnostics."""
    return (
        _compute_degraded_runtime_anchor_fingerprint(
            manifest_id=manifest_id,
            contract_ref=contract_ref,
            contract_version=contract_version,
            effective_config_hash=effective_config_hash,
            effective_config_artifact_id=effective_config_artifact_id,
        )
        or ""
    )


def build_identity_details(
    *,
    effective_config_hash: str,
    execution_phase: ExecutionPhase,
    checkpoint_schema_version: str,
    composite_run_identity: str | None,
    execution_fingerprint: str | None,
    pipeline_name: str | None,
    run_type: str | None,
    pipeline_version: str | None,
    manifest_id: str | None,
    dq_contract_compatibility_hash: str | None,
    contract_ref: str | None,
    contract_version: str | None,
    effective_config_artifact_id: str | None,
    exact_replay: bool | None,
    input_snapshot_fingerprint: str | None,
) -> JsonDict:
    """Build canonical identity details payload."""
    canonical_fallback_payload = _build_checkpoint_execution_identity_payload(
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
        "effective_config_hash": effective_config_hash,
        "execution_phase": execution_phase.value,
        "checkpoint_schema_version": checkpoint_schema_version,
        "composite_run_identity": _identity_detail_value(composite_run_identity),
        "execution_fingerprint": _identity_detail_value(execution_fingerprint),
        "pipeline_name": _identity_detail_value(pipeline_name),
        "run_type": _identity_detail_value(run_type),
        "pipeline_version": _identity_detail_value(pipeline_version),
        "manifest_id": _identity_detail_value(manifest_id),
        "dq_contract_compatibility_hash": _identity_detail_value(
            dq_contract_compatibility_hash
        ),
        "contract_ref": _identity_detail_value(contract_ref),
        "contract_version": _identity_detail_value(contract_version),
        "effective_config_artifact_id": _identity_detail_value(
            effective_config_artifact_id
        ),
        "exact_replay": _identity_detail_bool(exact_replay),
        "input_snapshot_fingerprint": input_snapshot_fingerprint or "",
        "canonical_execution_identity_payload": canonical_fallback_payload,
        "checkpoint_execution_identity_fallback_fingerprint": (
            _checkpoint_execution_identity_fallback_detail(
                canonical_fallback_payload
            )
        ),
        "degraded_runtime_anchor_fingerprint": _degraded_runtime_anchor_detail(
            manifest_id=manifest_id,
            contract_ref=contract_ref,
            contract_version=contract_version,
            effective_config_hash=effective_config_hash,
            effective_config_artifact_id=effective_config_artifact_id,
        )
    }


def generate_details(
    *,
    phase_result: JsonDict,
    config_result: JsonDict,
    execution_identity_result: JsonDict,
    schema_result: JsonDict,
    current_identity_details: JsonDict,
    checkpoint_identity_details: JsonDict,
    mode: str,
    allow_policy_override: bool,
    max_schema_version_delta: int,
) -> JsonDict:
    """Generate detailed compatibility payload."""
    return {
        "phase_compatibility": phase_result,
        "config_compatibility": config_result,
        "execution_identity_compatibility": execution_identity_result,
        "schema_compatibility": schema_result,
        "current_identity": current_identity_details,
        "checkpoint_identity": checkpoint_identity_details,
        "compatibility_mode": mode,
        "allow_policy_override": allow_policy_override,
        "max_schema_version_delta": max_schema_version_delta,
    }
