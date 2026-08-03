"""Detail payload helpers for checkpoint compatibility runtime."""

from __future__ import annotations

from dataclasses import dataclass

from bioetl.application.services._checkpoint_execution_identity_payload import (
    build_checkpoint_execution_identity_payload,
)
from bioetl.domain.config.runtime import CANONICAL_SILVER_FILTER_COMPATIBILITY_MODE
from bioetl.domain.normalization import (
    compute_execution_identity_fingerprint,
    normalize_runtime_anchor_payload,
)
from bioetl.domain.types import JsonDict
from bioetl.domain.types.execution_phase import ExecutionPhase


@dataclass(frozen=True, slots=True)
class IdentityDetailsSpec:
    """Inputs required to build one structured identity-details payload."""

    effective_config_hash: str
    execution_phase: ExecutionPhase
    checkpoint_schema_version: str
    composite_run_identity: str | None = None
    execution_fingerprint: str | None = None
    pipeline_name: str | None = None
    run_type: str | None = None
    pipeline_version: str | None = None
    git_commit: str | None = None
    manifest_id: str | None = None
    dq_contract_compatibility_hash: str | None = None
    contract_ref: str | None = None
    contract_version: str | None = None
    normalization_profile_ref: str | None = None
    normalization_profile_version: str | None = None
    normalization_profile_hash: str | None = None
    effective_config_artifact_id: str | None = None
    exact_replay: bool | None = None
    input_snapshot_fingerprint: str | None = None
    dependency_lock_hash: str | None = None
    silver_filter_compatibility_mode: str | None = (
        CANONICAL_SILVER_FILTER_COMPATIBILITY_MODE
    )


def _identity_detail_value(value: str | None) -> str:
    """Normalize optional string identity fields for structured detail payloads."""
    return value or ""


def _identity_detail_bool(value: bool | None) -> str:
    """Normalize optional boolean identity fields for structured detail payloads."""
    return "" if value is None else str(value).lower()


def _checkpoint_execution_identity_fallback_detail(payload: JsonDict) -> str:
    """Return canonical checkpoint fallback fingerprint for diagnostics."""
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
        return ""
    if manifest_id is not None:
        raw_payload["manifest_id"] = manifest_id
    return compute_execution_identity_fingerprint(
        normalize_runtime_anchor_payload(raw_payload)
    )


def build_identity_details(request: IdentityDetailsSpec) -> JsonDict:
    """Build canonical identity details payload."""
    canonical_fallback_payload = build_checkpoint_execution_identity_payload(
        pipeline_name=request.pipeline_name,
        run_type=request.run_type,
        pipeline_version=request.pipeline_version,
        git_commit=request.git_commit,
        dependency_lock_hash=request.dependency_lock_hash,
        effective_config_hash=request.effective_config_hash,
        dq_contract_compatibility_hash=request.dq_contract_compatibility_hash,
        contract=(request.contract_ref, request.contract_version),
        normalization_profile=(
            request.normalization_profile_ref,
            request.normalization_profile_version,
            request.normalization_profile_hash,
        ),
        effective_config_artifact_id=request.effective_config_artifact_id,
        exact_replay=request.exact_replay,
        input_snapshot_fingerprint=request.input_snapshot_fingerprint,
        silver_filter_compatibility_mode=request.silver_filter_compatibility_mode,
    )
    return {
        "effective_config_hash": request.effective_config_hash,
        "execution_phase": request.execution_phase.value,
        "checkpoint_schema_version": request.checkpoint_schema_version,
        "composite_run_identity": _identity_detail_value(
            request.composite_run_identity
        ),
        "execution_fingerprint": _identity_detail_value(request.execution_fingerprint),
        "pipeline_name": _identity_detail_value(request.pipeline_name),
        "run_type": _identity_detail_value(request.run_type),
        "pipeline_version": _identity_detail_value(request.pipeline_version),
        "git_commit": _identity_detail_value(request.git_commit),
        "dependency_lock_hash": _identity_detail_value(request.dependency_lock_hash),
        "manifest_id": _identity_detail_value(request.manifest_id),
        "dq_contract_compatibility_hash": _identity_detail_value(
            request.dq_contract_compatibility_hash
        ),
        "contract_ref": _identity_detail_value(request.contract_ref),
        "contract_version": _identity_detail_value(request.contract_version),
        "normalization_profile_ref": _identity_detail_value(
            request.normalization_profile_ref
        ),
        "normalization_profile_version": _identity_detail_value(
            request.normalization_profile_version
        ),
        "normalization_profile_hash": _identity_detail_value(
            request.normalization_profile_hash
        ),
        "effective_config_artifact_id": _identity_detail_value(
            request.effective_config_artifact_id
        ),
        "exact_replay": _identity_detail_bool(request.exact_replay),
        "input_snapshot_fingerprint": request.input_snapshot_fingerprint or "",
        "silver_filter_compatibility_mode": _identity_detail_value(
            request.silver_filter_compatibility_mode
        ),
        "canonical_execution_identity_payload": canonical_fallback_payload,
        "checkpoint_execution_identity_fallback_fingerprint": (
            _checkpoint_execution_identity_fallback_detail(canonical_fallback_payload)
        ),
        "degraded_runtime_anchor_fingerprint": _degraded_runtime_anchor_detail(
            manifest_id=request.manifest_id,
            contract_ref=request.contract_ref,
            contract_version=request.contract_version,
            effective_config_hash=request.effective_config_hash,
            effective_config_artifact_id=request.effective_config_artifact_id,
        ),
    }


IdentityDetailsRequest = IdentityDetailsSpec


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
