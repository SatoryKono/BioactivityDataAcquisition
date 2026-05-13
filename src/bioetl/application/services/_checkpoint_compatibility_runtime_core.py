"""Core checkpoint compatibility verdict helpers."""

from __future__ import annotations

from typing import Final

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
    severities = (
        phase_result["severity"],
        config_result["severity"],
        execution_identity_result["severity"],
        schema_result["severity"],
    )
    if _SEVERITY_MAJOR in severities:
        return _VERDICT_MAJOR_INCOMPATIBLE
    if _SEVERITY_MINOR in severities:
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
