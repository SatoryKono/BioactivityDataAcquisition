"""Enhanced checkpoint compatibility service with execution model integration."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from bioetl.application.services._checkpoint_compatibility_runtime_core import (
    check_config_compatibility,
    check_phase_compatibility,
    check_schema_compatibility,
    determine_verdict_value,
    generate_message,
    generate_recovery_suggestions,
)
from bioetl.application.services._checkpoint_compatibility_runtime_identity import (
    CheckpointExecutionIdentityFallbackContext,
    ExecutionIdentityCompatibilityContext,
    check_execution_identity_compatibility,
)
from bioetl.application.services._checkpoint_compatibility_runtime_identity_details import (
    IdentityDetailsRequest,
    build_identity_details,
    generate_details,
)
from bioetl.domain.types import JsonDict
from bioetl.domain.types.execution_phase import ExecutionPhase
from bioetl.domain.types.validation_result import CompositeValidationReport


class CheckpointCompatibilityPolicy(Enum):
    """Compatibility checking modes."""

    STRICT = "strict"
    LENIENT = "lenient"


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
    pipeline_name: str | None = None
    run_type: str | None = None
    pipeline_version: str | None = None
    git_commit: str | None = None
    dependency_lock_hash: str | None = None
    source_freshness_markers: dict[str, object] | None = None
    composite_run_identity: str | None = None
    execution_fingerprint: str | None = None
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
    silver_filter_compatibility_mode: str | None = None


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


@dataclass(frozen=True)
class _CompatibilityEvaluation:
    """Intermediate compatibility results reused across final payload builders."""

    phase_compatibility: JsonDict
    config_compatibility: JsonDict
    execution_identity_compatibility: JsonDict
    schema_compatibility: JsonDict
    verdict: CheckpointCompatibilityReason
    suggestions: list[str]
    current_identity_details: JsonDict
    checkpoint_identity_details: JsonDict


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
        evaluation = self._evaluate_compatibility(
            current_identity=current_identity,
            checkpoint_identity=checkpoint_identity,
            validation_report=validation_report,
        )
        return CheckpointCompatibilityResult(
            verdict=evaluation.verdict,
            message=generate_message(
                verdict_value=evaluation.verdict.value,
                current_phase=current_identity.execution_phase,
                mode=self.config.mode.value,
            ),
            details=generate_details(
                phase_result=evaluation.phase_compatibility,
                config_result=evaluation.config_compatibility,
                execution_identity_result=evaluation.execution_identity_compatibility,
                schema_result=evaluation.schema_compatibility,
                current_identity_details=evaluation.current_identity_details,
                checkpoint_identity_details=evaluation.checkpoint_identity_details,
                mode=self.config.mode.value,
                allow_policy_override=self.config.allow_policy_override,
                max_schema_version_delta=self.config.max_schema_version_delta,
            ),
            execution_phase=current_identity.execution_phase,
            recovery_suggestions=evaluation.suggestions,
        )

    def _evaluate_compatibility(
        self,
        *,
        current_identity: CheckpointIdentityRecord,
        checkpoint_identity: CheckpointIdentityRecord,
        validation_report: CompositeValidationReport | None,
    ) -> _CompatibilityEvaluation:
        """Compute reusable compatibility intermediates for the final response."""
        phase_compatibility = check_phase_compatibility(
            current_phase=current_identity.execution_phase,
            checkpoint_phase=checkpoint_identity.execution_phase,
        )
        config_compatibility = check_config_compatibility(
            current_hash=current_identity.effective_config_hash,
            checkpoint_hash=checkpoint_identity.effective_config_hash,
        )
        execution_identity_compatibility = check_execution_identity_compatibility(
            current=self._build_execution_identity_context(current_identity),
            checkpoint=self._build_execution_identity_context(checkpoint_identity),
        )
        schema_compatibility = check_schema_compatibility(
            current_version=current_identity.checkpoint_schema_version,
            checkpoint_version=checkpoint_identity.checkpoint_schema_version,
            max_schema_version_delta=self.config.max_schema_version_delta,
        )
        verdict = CheckpointCompatibilityReason(
            determine_verdict_value(
                mode=self.config.mode.value,
                phase_result=phase_compatibility,
                config_result=config_compatibility,
                execution_identity_result=execution_identity_compatibility,
                schema_result=schema_compatibility,
                validation_report=validation_report,
            )
        )
        suggestions = generate_recovery_suggestions(
            phase_result=phase_compatibility,
            config_result=config_compatibility,
            schema_result=schema_compatibility,
            current_phase=current_identity.execution_phase,
            allow_policy_override=self.config.allow_policy_override,
            max_schema_version_delta=self.config.max_schema_version_delta,
        )
        return _CompatibilityEvaluation(
            phase_compatibility=phase_compatibility,
            config_compatibility=config_compatibility,
            execution_identity_compatibility=execution_identity_compatibility,
            schema_compatibility=schema_compatibility,
            verdict=verdict,
            suggestions=suggestions,
            current_identity_details=self._build_identity_details(current_identity),
            checkpoint_identity_details=self._build_identity_details(
                checkpoint_identity
            ),
        )

    @staticmethod
    def _build_execution_identity_context(
        identity: CheckpointIdentityRecord,
    ) -> ExecutionIdentityCompatibilityContext:
        """Translate checkpoint identity records into runtime compatibility contexts."""
        return ExecutionIdentityCompatibilityContext(
            composite_run_identity=identity.composite_run_identity,
            execution_fingerprint=identity.execution_fingerprint,
            manifest_id=identity.manifest_id,
            fallback=CheckpointExecutionIdentityFallbackContext(
                pipeline_name=identity.pipeline_name,
                run_type=identity.run_type,
                pipeline_version=identity.pipeline_version,
                git_commit=identity.git_commit,
                dependency_lock_hash=identity.dependency_lock_hash,
                effective_config_hash=identity.effective_config_hash,
                dq_contract_compatibility_hash=identity.dq_contract_compatibility_hash,
                contract_ref=identity.contract_ref,
                contract_version=identity.contract_version,
                normalization_profile_ref=identity.normalization_profile_ref,
                normalization_profile_version=identity.normalization_profile_version,
                normalization_profile_hash=identity.normalization_profile_hash,
                effective_config_artifact_id=identity.effective_config_artifact_id,
                exact_replay=identity.exact_replay,
                input_snapshot_fingerprint=identity.input_snapshot_fingerprint,
                silver_filter_compatibility_mode=(
                    identity.silver_filter_compatibility_mode
                ),
            ),
        )

    @staticmethod
    def _build_identity_details(identity: CheckpointIdentityRecord) -> JsonDict:
        """Return compatibility detail payloads for one checkpoint identity record."""
        return build_identity_details(
            IdentityDetailsRequest(
                effective_config_hash=identity.effective_config_hash,
                execution_phase=identity.execution_phase,
                checkpoint_schema_version=identity.checkpoint_schema_version,
                composite_run_identity=identity.composite_run_identity,
                execution_fingerprint=identity.execution_fingerprint,
                pipeline_name=identity.pipeline_name,
                run_type=identity.run_type,
                pipeline_version=identity.pipeline_version,
                git_commit=identity.git_commit,
                dependency_lock_hash=identity.dependency_lock_hash,
                manifest_id=identity.manifest_id,
                dq_contract_compatibility_hash=identity.dq_contract_compatibility_hash,
                contract_ref=identity.contract_ref,
                contract_version=identity.contract_version,
                normalization_profile_ref=identity.normalization_profile_ref,
                normalization_profile_version=identity.normalization_profile_version,
                normalization_profile_hash=identity.normalization_profile_hash,
                effective_config_artifact_id=identity.effective_config_artifact_id,
                exact_replay=identity.exact_replay,
                input_snapshot_fingerprint=identity.input_snapshot_fingerprint,
                silver_filter_compatibility_mode=(
                    identity.silver_filter_compatibility_mode
                ),
            )
        )


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
