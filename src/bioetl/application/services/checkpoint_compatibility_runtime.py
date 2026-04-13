"""Runtime helpers for checkpoint compatibility evaluation."""

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
from bioetl.domain.types.validation_result import CompositeValidationReport

_SEVERITY_MAJOR: Final[str] = "major"
_SEVERITY_MINOR: Final[str] = "minor"
_SEVERITY_NONE: Final[str] = "none"

_VERDICT_COMPATIBLE: Final[str] = "compatible"
_VERDICT_MINOR_INCOMPATIBLE: Final[str] = "minor_incompatible"
_VERDICT_MAJOR_INCOMPATIBLE: Final[str] = "major_incompatible"
_VERDICT_UNKNOWN: Final[str] = "unknown"

_MODE_STRICT: Final[str] = "strict"
_MODE_LENIENT: Final[str] = "lenient"
_MODE_LEGACY: Final[str] = "legacy"

_COMPATIBLE_TRANSITIONS: Final[dict[ExecutionPhase, tuple[ExecutionPhase, ...]]] = {
    ExecutionPhase.PREFLIGHT: (ExecutionPhase.NOT_STARTED,),
    ExecutionPhase.DEPENDENCY_EXECUTION: (
        ExecutionPhase.NOT_STARTED,
        ExecutionPhase.PREFLIGHT,
    ),
    ExecutionPhase.ENRICHMENT: (
        ExecutionPhase.NOT_STARTED,
        ExecutionPhase.PREFLIGHT,
        ExecutionPhase.DEPENDENCY_EXECUTION,
    ),
    ExecutionPhase.MERGE: (
        ExecutionPhase.NOT_STARTED,
        ExecutionPhase.PREFLIGHT,
        ExecutionPhase.DEPENDENCY_EXECUTION,
        ExecutionPhase.ENRICHMENT,
    ),
    ExecutionPhase.CROSS_VALIDATION: (
        ExecutionPhase.NOT_STARTED,
        ExecutionPhase.PREFLIGHT,
        ExecutionPhase.DEPENDENCY_EXECUTION,
        ExecutionPhase.ENRICHMENT,
        ExecutionPhase.MERGE,
    ),
    ExecutionPhase.WRITE_FINALIZE: (
        ExecutionPhase.NOT_STARTED,
        ExecutionPhase.PREFLIGHT,
        ExecutionPhase.DEPENDENCY_EXECUTION,
        ExecutionPhase.ENRICHMENT,
        ExecutionPhase.MERGE,
        ExecutionPhase.CROSS_VALIDATION,
    ),
    ExecutionPhase.COMPLETED_SUCCESS: (),
    ExecutionPhase.COMPLETED_WITH_WARNINGS: (),
    ExecutionPhase.FAILED_VALIDATION: (),
    ExecutionPhase.FAILED_EXECUTION: (),
    ExecutionPhase.FAILED_RECOVERY: (),
    ExecutionPhase.TERMINATED: (),
    ExecutionPhase.NOT_STARTED: (),
}

_BASE_MESSAGES: Final[dict[str, str]] = {
    _VERDICT_COMPATIBLE: "Checkpoint is compatible",
    _VERDICT_MINOR_INCOMPATIBLE: "Checkpoint has minor incompatibilities",
    _VERDICT_MAJOR_INCOMPATIBLE: "Checkpoint is incompatible",
    _VERDICT_UNKNOWN: "Checkpoint compatibility unknown",
}
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


def check_phase_compatibility(
    *,
    current_phase: ExecutionPhase,
    checkpoint_phase: ExecutionPhase,
) -> JsonDict:
    """Check execution phase compatibility."""
    if current_phase == checkpoint_phase:
        return {
            "compatible": True,
            "reason": "same_execution_phase",
            "severity": _SEVERITY_NONE,
        }

    is_compatible = checkpoint_phase in _COMPATIBLE_TRANSITIONS.get(current_phase, ())
    return {
        "compatible": is_compatible,
        "reason": (
            "compatible_phase_transition"
            if is_compatible
            else "incompatible_phase_transition"
        ),
        "severity": _SEVERITY_MINOR if is_compatible else _SEVERITY_MAJOR,
    }


def check_config_compatibility(*, current_hash: str, checkpoint_hash: str) -> JsonDict:
    """Check configuration hash compatibility."""
    if current_hash == checkpoint_hash:
        return {
            "compatible": True,
            "reason": "identical_config_hash",
            "severity": _SEVERITY_NONE,
        }
    return {
        "compatible": False,
        "reason": "different_config_hash",
        "severity": _SEVERITY_MAJOR,
    }


def check_schema_compatibility(
    *,
    current_version: str,
    checkpoint_version: str,
    max_schema_version_delta: int,
) -> JsonDict:
    """Check checkpoint schema version compatibility."""
    try:
        current_parts = [int(part) for part in current_version.split(".")]
        checkpoint_parts = [int(part) for part in checkpoint_version.split(".")]
    except (ValueError, IndexError):
        return {
            "compatible": False,
            "reason": "invalid_version_format",
            "severity": _SEVERITY_MAJOR,
        }

    if current_parts == checkpoint_parts:
        return {
            "compatible": True,
            "reason": "identical_schema_version",
            "severity": _SEVERITY_NONE,
        }

    if current_parts[0] != checkpoint_parts[0]:
        return {
            "compatible": False,
            "reason": "incompatible_major_version",
            "severity": _SEVERITY_MAJOR,
        }

    version_diff = abs(current_parts[1] - checkpoint_parts[1])
    if version_diff <= max_schema_version_delta:
        return {
            "compatible": True,
            "reason": f"compatible_minor_version_delta_{version_diff}",
            "severity": _SEVERITY_MINOR,
        }
    return {
        "compatible": False,
        "reason": f"exceeds_max_version_delta_{version_diff}",
        "severity": _SEVERITY_MAJOR,
    }


def determine_verdict_value(
    *,
    mode: str,
    phase_result: JsonDict,
    config_result: JsonDict,
    execution_identity_result: JsonDict,
    schema_result: JsonDict,
    validation_report: CompositeValidationReport | None,
) -> str:
    """Determine overall compatibility verdict for the configured mode."""
    if mode == _MODE_LENIENT:
        return _determine_lenient_verdict(
            phase_result=phase_result,
            config_result=config_result,
            execution_identity_result=execution_identity_result,
            schema_result=schema_result,
        )
    if mode == _MODE_LEGACY:
        return _determine_legacy_verdict(phase_result=phase_result)
    return _determine_strict_verdict(
        phase_result=phase_result,
        config_result=config_result,
        execution_identity_result=execution_identity_result,
        schema_result=schema_result,
        validation_report=validation_report,
    )


def _determine_strict_verdict(
    *,
    phase_result: JsonDict,
    config_result: JsonDict,
    execution_identity_result: JsonDict,
    schema_result: JsonDict,
    validation_report: CompositeValidationReport | None,
) -> str:
    if (
        phase_result["severity"] == _SEVERITY_MAJOR
        or config_result["severity"] == _SEVERITY_MAJOR
        or execution_identity_result["severity"] == _SEVERITY_MAJOR
        or schema_result["severity"] == _SEVERITY_MAJOR
    ):
        return _VERDICT_MAJOR_INCOMPATIBLE

    if (
        phase_result["severity"] == _SEVERITY_MINOR
        or config_result["severity"] == _SEVERITY_MINOR
        or execution_identity_result["severity"] == _SEVERITY_MINOR
        or schema_result["severity"] == _SEVERITY_MINOR
    ):
        return _VERDICT_MINOR_INCOMPATIBLE

    if validation_report and validation_report.has_any_blockers():
        return _VERDICT_MAJOR_INCOMPATIBLE
    return _VERDICT_COMPATIBLE


def _determine_lenient_verdict(
    *,
    phase_result: JsonDict,
    config_result: JsonDict,
    execution_identity_result: JsonDict,
    schema_result: JsonDict,
) -> str:
    if phase_result["severity"] == _SEVERITY_MAJOR:
        return _VERDICT_MAJOR_INCOMPATIBLE
    if (
        config_result["severity"] == _SEVERITY_MAJOR
        or execution_identity_result["severity"] == _SEVERITY_MAJOR
        or schema_result["severity"] == _SEVERITY_MAJOR
    ):
        return _VERDICT_MINOR_INCOMPATIBLE
    return _VERDICT_COMPATIBLE


def _determine_legacy_verdict(*, phase_result: JsonDict) -> str:
    if phase_result["severity"] == _SEVERITY_MAJOR:
        return _VERDICT_MAJOR_INCOMPATIBLE
    return _VERDICT_COMPATIBLE


def generate_recovery_suggestions(
    *,
    phase_result: JsonDict,
    config_result: JsonDict,
    schema_result: JsonDict,
    current_phase: ExecutionPhase,
    allow_policy_override: bool,
    max_schema_version_delta: int,
) -> list[str]:
    """Generate recovery suggestions for incompatibility."""
    suggestions: list[str] = []

    if not phase_result["compatible"]:
        if phase_result["severity"] == _SEVERITY_MAJOR:
            suggestions.append(
                f"Cannot resume from {current_phase.value} to incompatible phase. "
                "Consider restarting execution from beginning."
            )
        else:
            suggestions.append(
                "Phase transition from checkpoint requires validation. "
                "Use --force-resume flag to override if safe."
            )

    if not config_result["compatible"]:
        suggestions.append(
            "Configuration mismatch detected. Review config changes and update "
            "checkpoint or configuration to match."
        )
        if allow_policy_override:
            suggestions.append(
                "Configuration mismatch can be overridden with "
                "--allow-config-mismatch if changes are backward-compatible."
            )

    if not schema_result["compatible"]:
        if schema_result["severity"] == _SEVERITY_MAJOR:
            suggestions.append(
                "Major schema version incompatibility. Checkpoint cannot be used. "
                "Consider schema migration or starting fresh execution."
            )
        else:
            suggestions.append(
                "Minor schema version difference (delta <= "
                f"{max_schema_version_delta}). Data migration may be required "
                "for full compatibility."
            )

    if current_phase in (
        ExecutionPhase.DEPENDENCY_EXECUTION,
        ExecutionPhase.ENRICHMENT,
    ):
        suggestions.append(
            "For dependency/enrichment phases, consider re-running only affected "
            "sources instead of full resume."
        )

    if current_phase in (
        ExecutionPhase.MERGE,
        ExecutionPhase.CROSS_VALIDATION,
    ):
        suggestions.append(
            "For merge/cross-validation phases, review conflict resolution and "
            "validation rules as they may be affected by config changes."
        )

    return suggestions


def generate_message(
    *,
    verdict_value: str,
    current_phase: ExecutionPhase,
    mode: str,
) -> str:
    """Generate a human-readable compatibility message."""
    message = _BASE_MESSAGES.get(verdict_value, "Unknown compatibility status")
    if verdict_value == _VERDICT_COMPATIBLE:
        message += f" for {current_phase.value} phase"
    else:
        message += f" with current {current_phase.value} phase"
    if mode != _MODE_STRICT:
        message += f" (mode: {mode})"
    return message


def check_execution_identity_compatibility(
    *,
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
