"""Enhanced checkpoint compatibility service with execution model integration."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from bioetl.domain.types import JsonDict
from bioetl.domain.types.execution_phase import ExecutionPhase
from bioetl.domain.types.validation_result import CompositeValidationReport


class CheckpointCompatibilityPolicy(Enum):
    """Compatibility checking modes."""

    STRICT = "strict"
    LENIENT = "lenient"
    LEGACY = "legacy"


class CheckpointCompatibilityReason(Enum):
    """Verdict for checkpoint compatibility checks."""

    COMPATIBLE = "compatible"
    MINOR_INCOMPATIBLE = "minor_incompatible"
    MAJOR_INCOMPATIBLE = "major_incompatible"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class CheckpointIdentityRecord:
    """Identity anchors for checkpoint compatibility."""

    effective_config_hash: str
    execution_phase: ExecutionPhase
    checkpoint_schema_version: str
    source_freshness_markers: dict[str, object] | None = None
    composite_run_identity: str | None = None


@dataclass(frozen=True)
class CheckpointCompatibilityResult:
    """Result of checkpoint compatibility verification."""

    verdict: CheckpointCompatibilityReason
    message: str
    details: JsonDict
    execution_phase: ExecutionPhase
    recovery_suggestions: list[str]


@dataclass(frozen=True)
class CheckpointCompatibilityConfig:
    """Configuration for checkpoint compatibility service."""

    mode: CheckpointCompatibilityPolicy = CheckpointCompatibilityPolicy.STRICT
    allow_policy_override: bool = False
    max_schema_version_delta: int = 1


class CheckpointCompatibilityV2Service:
    """Enhanced checkpoint compatibility service with execution model integration."""

    def __init__(self, config: CheckpointCompatibilityConfig | None = None):
        self.config = config or CheckpointCompatibilityConfig()

    def check_compatibility(
        self,
        current_identity: CheckpointIdentityRecord,
        checkpoint_identity: CheckpointIdentityRecord,
        validation_report: CompositeValidationReport | None = None,
    ) -> CheckpointCompatibilityResult:
        """Check compatibility between current execution and checkpoint."""
        phase_compatibility = _check_phase_compatibility(
            current_phase=current_identity.execution_phase,
            checkpoint_phase=checkpoint_identity.execution_phase,
        )
        config_compatibility = _check_config_compatibility(
            current_hash=current_identity.effective_config_hash,
            checkpoint_hash=checkpoint_identity.effective_config_hash,
        )
        schema_compatibility = _check_schema_compatibility(
            current_version=current_identity.checkpoint_schema_version,
            checkpoint_version=checkpoint_identity.checkpoint_schema_version,
            max_schema_version_delta=self.config.max_schema_version_delta,
        )
        verdict = _determine_verdict(
            mode=self.config.mode,
            phase_result=phase_compatibility,
            config_result=config_compatibility,
            schema_result=schema_compatibility,
            validation_report=validation_report,
        )
        suggestions = _generate_recovery_suggestions(
            phase_result=phase_compatibility,
            config_result=config_compatibility,
            schema_result=schema_compatibility,
            current_phase=current_identity.execution_phase,
            allow_policy_override=self.config.allow_policy_override,
            max_schema_version_delta=self.config.max_schema_version_delta,
        )

        return CheckpointCompatibilityResult(
            verdict=verdict,
            message=_generate_message(
                verdict=verdict,
                current_phase=current_identity.execution_phase,
                mode=self.config.mode,
            ),
            details=_generate_details(
                phase_result=phase_compatibility,
                config_result=config_compatibility,
                schema_result=schema_compatibility,
                current_identity=current_identity,
                checkpoint_identity=checkpoint_identity,
                mode=self.config.mode,
                allow_policy_override=self.config.allow_policy_override,
                max_schema_version_delta=self.config.max_schema_version_delta,
            ),
            execution_phase=current_identity.execution_phase,
            recovery_suggestions=suggestions,
        )


def _check_phase_compatibility(
    *,
    current_phase: ExecutionPhase,
    checkpoint_phase: ExecutionPhase,
) -> JsonDict:
    """Check execution phase compatibility."""
    if current_phase == checkpoint_phase:
        return {
            "compatible": True,
            "reason": "same_execution_phase",
            "severity": "none",
        }

    compatible_transitions = {
        ExecutionPhase.PREFLIGHT: [ExecutionPhase.NOT_STARTED],
        ExecutionPhase.DEPENDENCY_EXECUTION: [
            ExecutionPhase.NOT_STARTED,
            ExecutionPhase.PREFLIGHT,
        ],
        ExecutionPhase.ENRICHMENT: [
            ExecutionPhase.NOT_STARTED,
            ExecutionPhase.PREFLIGHT,
            ExecutionPhase.DEPENDENCY_EXECUTION,
        ],
        ExecutionPhase.MERGE: [
            ExecutionPhase.NOT_STARTED,
            ExecutionPhase.PREFLIGHT,
            ExecutionPhase.DEPENDENCY_EXECUTION,
            ExecutionPhase.ENRICHMENT,
        ],
        ExecutionPhase.CROSS_VALIDATION: [
            ExecutionPhase.NOT_STARTED,
            ExecutionPhase.PREFLIGHT,
            ExecutionPhase.DEPENDENCY_EXECUTION,
            ExecutionPhase.ENRICHMENT,
            ExecutionPhase.MERGE,
        ],
        ExecutionPhase.WRITE_FINALIZE: [
            ExecutionPhase.NOT_STARTED,
            ExecutionPhase.PREFLIGHT,
            ExecutionPhase.DEPENDENCY_EXECUTION,
            ExecutionPhase.ENRICHMENT,
            ExecutionPhase.MERGE,
            ExecutionPhase.CROSS_VALIDATION,
        ],
        ExecutionPhase.COMPLETED_SUCCESS: [],
        ExecutionPhase.COMPLETED_WITH_WARNINGS: [],
        ExecutionPhase.FAILED_VALIDATION: [],
        ExecutionPhase.FAILED_EXECUTION: [],
        ExecutionPhase.FAILED_RECOVERY: [],
        ExecutionPhase.TERMINATED: [],
        ExecutionPhase.NOT_STARTED: [],
    }

    is_compatible = checkpoint_phase in compatible_transitions.get(current_phase, [])
    return {
        "compatible": is_compatible,
        "reason": (
            "compatible_phase_transition"
            if is_compatible
            else "incompatible_phase_transition"
        ),
        "severity": "minor" if is_compatible else "major",
    }


def _check_config_compatibility(*, current_hash: str, checkpoint_hash: str) -> JsonDict:
    """Check configuration hash compatibility."""
    if current_hash == checkpoint_hash:
        return {
            "compatible": True,
            "reason": "identical_config_hash",
            "severity": "none",
        }
    return {
        "compatible": False,
        "reason": "different_config_hash",
        "severity": "major",
    }


def _check_schema_compatibility(
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
            "severity": "major",
        }

    if current_parts == checkpoint_parts:
        return {
            "compatible": True,
            "reason": "identical_schema_version",
            "severity": "none",
        }

    if current_parts[0] != checkpoint_parts[0]:
        return {
            "compatible": False,
            "reason": "incompatible_major_version",
            "severity": "major",
        }

    version_diff = abs(current_parts[1] - checkpoint_parts[1])
    if version_diff <= max_schema_version_delta:
        return {
            "compatible": True,
            "reason": f"compatible_minor_version_delta_{version_diff}",
            "severity": "minor",
        }
    return {
        "compatible": False,
        "reason": f"exceeds_max_version_delta_{version_diff}",
        "severity": "major",
    }


def _determine_verdict(
    *,
    mode: CheckpointCompatibilityPolicy,
    phase_result: JsonDict,
    config_result: JsonDict,
    schema_result: JsonDict,
    validation_report: CompositeValidationReport | None,
) -> CheckpointCompatibilityReason:
    """Determine overall compatibility verdict based on configured mode."""
    if mode == CheckpointCompatibilityPolicy.LENIENT:
        return _determine_lenient_verdict(
            phase_result=phase_result,
            config_result=config_result,
            schema_result=schema_result,
        )
    if mode == CheckpointCompatibilityPolicy.LEGACY:
        return _determine_legacy_verdict(phase_result=phase_result)
    return _determine_strict_verdict(
        phase_result=phase_result,
        config_result=config_result,
        schema_result=schema_result,
        validation_report=validation_report,
    )


def _determine_strict_verdict(
    *,
    phase_result: JsonDict,
    config_result: JsonDict,
    schema_result: JsonDict,
    validation_report: CompositeValidationReport | None,
) -> CheckpointCompatibilityReason:
    """Determine verdict in strict mode."""
    if (
        phase_result["severity"] == "major"
        or config_result["severity"] == "major"
        or schema_result["severity"] == "major"
    ):
        return CheckpointCompatibilityReason.MAJOR_INCOMPATIBLE

    if (
        phase_result["severity"] == "minor"
        or config_result["severity"] == "minor"
        or schema_result["severity"] == "minor"
    ):
        return CheckpointCompatibilityReason.MINOR_INCOMPATIBLE

    if validation_report and validation_report.has_any_blockers():
        return CheckpointCompatibilityReason.MAJOR_INCOMPATIBLE
    return CheckpointCompatibilityReason.COMPATIBLE


def _determine_lenient_verdict(
    *,
    phase_result: JsonDict,
    config_result: JsonDict,
    schema_result: JsonDict,
) -> CheckpointCompatibilityReason:
    """Determine verdict in lenient mode."""
    if phase_result["severity"] == "major":
        return CheckpointCompatibilityReason.MAJOR_INCOMPATIBLE
    if config_result["severity"] == "major" or schema_result["severity"] == "major":
        return CheckpointCompatibilityReason.MINOR_INCOMPATIBLE
    return CheckpointCompatibilityReason.COMPATIBLE


def _determine_legacy_verdict(
    *, phase_result: JsonDict
) -> CheckpointCompatibilityReason:
    """Determine verdict in legacy mode (most permissive)."""
    if phase_result["severity"] == "major":
        return CheckpointCompatibilityReason.MAJOR_INCOMPATIBLE
    return CheckpointCompatibilityReason.COMPATIBLE


def _generate_recovery_suggestions(
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
        if phase_result["severity"] == "major":
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
        if schema_result["severity"] == "major":
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


def _generate_message(
    *,
    verdict: CheckpointCompatibilityReason,
    current_phase: ExecutionPhase,
    mode: CheckpointCompatibilityPolicy,
) -> str:
    """Generate human-readable compatibility message."""
    base_messages = {
        CheckpointCompatibilityReason.COMPATIBLE: "Checkpoint is compatible",
        CheckpointCompatibilityReason.MINOR_INCOMPATIBLE: "Checkpoint has minor incompatibilities",
        CheckpointCompatibilityReason.MAJOR_INCOMPATIBLE: "Checkpoint is incompatible",
        CheckpointCompatibilityReason.UNKNOWN: "Checkpoint compatibility unknown",
    }
    message = base_messages.get(verdict, "Unknown compatibility status")
    if verdict == CheckpointCompatibilityReason.COMPATIBLE:
        message += f" for {current_phase.value} phase"
    else:
        message += f" with current {current_phase.value} phase"
    if mode != CheckpointCompatibilityPolicy.STRICT:
        message += f" (mode: {mode.value})"
    return message


def _generate_details(
    *,
    phase_result: JsonDict,
    config_result: JsonDict,
    schema_result: JsonDict,
    current_identity: CheckpointIdentityRecord,
    checkpoint_identity: CheckpointIdentityRecord,
    mode: CheckpointCompatibilityPolicy,
    allow_policy_override: bool,
    max_schema_version_delta: int,
) -> JsonDict:
    """Generate detailed compatibility information."""
    return {
        "phase_compatibility": phase_result,
        "config_compatibility": config_result,
        "schema_compatibility": schema_result,
        "current_identity": {
            "effective_config_hash": current_identity.effective_config_hash,
            "execution_phase": current_identity.execution_phase.value,
            "checkpoint_schema_version": current_identity.checkpoint_schema_version,
            "composite_run_identity": current_identity.composite_run_identity or "",
        },
        "checkpoint_identity": {
            "effective_config_hash": checkpoint_identity.effective_config_hash,
            "execution_phase": checkpoint_identity.execution_phase.value,
            "checkpoint_schema_version": checkpoint_identity.checkpoint_schema_version,
            "composite_run_identity": checkpoint_identity.composite_run_identity or "",
        },
        "compatibility_mode": mode.value,
        "allow_policy_override": allow_policy_override,
        "max_schema_version_delta": max_schema_version_delta,
    }


def create_checkpoint_compatibility_service_v2(
    config: CheckpointCompatibilityConfig | None = None,
) -> CheckpointCompatibilityV2Service:
    """Factory function for CheckpointCompatibilityV2Service."""
    return CheckpointCompatibilityV2Service(config)


# Backward-compatible aliases kept for existing imports/tests.
CheckpointCompatibilityMode = CheckpointCompatibilityPolicy
CompatibilityVerdict = CheckpointCompatibilityReason
CheckpointIdentity = CheckpointIdentityRecord
CheckpointCompatibilityServiceV2 = CheckpointCompatibilityV2Service
