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

    if current_execution_fingerprint and checkpoint_execution_fingerprint:
        if current_execution_fingerprint == checkpoint_execution_fingerprint:
            return {
                "compatible": True,
                "reason": "identical_execution_fingerprint",
                "severity": _SEVERITY_NONE,
            }
        return {
            "compatible": False,
            "reason": "execution_fingerprint_mismatch",
            "severity": _SEVERITY_MAJOR,
        }

    current_checkpoint_execution_identity_fallback = (
        _compute_checkpoint_execution_identity_fallback_fingerprint(
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
    )
    checkpoint_checkpoint_execution_identity_fallback = (
        _compute_checkpoint_execution_identity_fallback_fingerprint(
            pipeline_name=checkpoint_pipeline_name,
            run_type=checkpoint_run_type,
            pipeline_version=checkpoint_pipeline_version,
            effective_config_hash=checkpoint_effective_config_hash,
            dq_contract_compatibility_hash=(
                checkpoint_dq_contract_compatibility_hash
            ),
            contract_ref=checkpoint_contract_ref,
            contract_version=checkpoint_contract_version,
            effective_config_artifact_id=checkpoint_effective_config_artifact_id,
            exact_replay=checkpoint_exact_replay,
            input_snapshot_fingerprint=checkpoint_input_snapshot_fingerprint,
        )
    )
    if (
        current_checkpoint_execution_identity_fallback
        and checkpoint_checkpoint_execution_identity_fallback
        and current_checkpoint_execution_identity_fallback
        == checkpoint_checkpoint_execution_identity_fallback
    ):
        return {
            "compatible": True,
            "reason": "identical_checkpoint_execution_identity_fallback",
            "severity": _SEVERITY_NONE,
        }
    if (
        current_checkpoint_execution_identity_fallback
        and checkpoint_checkpoint_execution_identity_fallback
    ):
        return {
            "compatible": False,
            "reason": "checkpoint_execution_identity_fallback_mismatch",
            "severity": _SEVERITY_MAJOR,
        }

    current_runtime_anchor_fingerprint = _compute_degraded_runtime_anchor_fingerprint(
        manifest_id=current_manifest_id,
        contract_ref=current_contract_ref,
        contract_version=current_contract_version,
        effective_config_hash=current_effective_config_hash,
        effective_config_artifact_id=current_effective_config_artifact_id,
    )
    checkpoint_runtime_anchor_fingerprint = (
        _compute_degraded_runtime_anchor_fingerprint(
            manifest_id=checkpoint_manifest_id,
            contract_ref=checkpoint_contract_ref,
            contract_version=checkpoint_contract_version,
            effective_config_hash=checkpoint_effective_config_hash,
            effective_config_artifact_id=checkpoint_effective_config_artifact_id,
        )
    )
    if (
        current_runtime_anchor_fingerprint
        and checkpoint_runtime_anchor_fingerprint
        and current_runtime_anchor_fingerprint == checkpoint_runtime_anchor_fingerprint
    ):
        return {
            "compatible": True,
            "reason": "identical_degraded_runtime_anchor_fingerprint",
            "severity": _SEVERITY_NONE,
        }
    if current_runtime_anchor_fingerprint and checkpoint_runtime_anchor_fingerprint:
        return {
            "compatible": False,
            "reason": "degraded_runtime_anchor_fingerprint_mismatch",
            "severity": _SEVERITY_MAJOR,
        }
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
        "composite_run_identity": composite_run_identity or "",
        "execution_fingerprint": execution_fingerprint or "",
        "pipeline_name": pipeline_name or "",
        "run_type": run_type or "",
        "pipeline_version": pipeline_version or "",
        "manifest_id": manifest_id or "",
        "dq_contract_compatibility_hash": dq_contract_compatibility_hash or "",
        "contract_ref": contract_ref or "",
        "contract_version": contract_version or "",
        "effective_config_artifact_id": effective_config_artifact_id or "",
        "exact_replay": "" if exact_replay is None else str(exact_replay).lower(),
        "input_snapshot_fingerprint": input_snapshot_fingerprint or "",
        "canonical_execution_identity_payload": canonical_fallback_payload,
        "checkpoint_execution_identity_fallback_fingerprint": (
            compute_execution_identity_fingerprint(canonical_fallback_payload)
            if canonical_fallback_payload
            else ""
        ),
        "degraded_runtime_anchor_fingerprint": _compute_degraded_runtime_anchor_fingerprint(
            manifest_id=manifest_id,
            contract_ref=contract_ref,
            contract_version=contract_version,
            effective_config_hash=effective_config_hash,
            effective_config_artifact_id=effective_config_artifact_id,
        )
        or "",
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
