"""Enhanced checkpoint compatibility service with execution model integration."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from bioetl.application.services.checkpoint_compatibility_runtime import (
    IdentityDetailsRequest,
    build_identity_details,
    check_config_compatibility,
    check_execution_identity_compatibility,
    check_phase_compatibility,
    check_schema_compatibility,
    determine_verdict_value,
    generate_details,
    generate_message,
    generate_recovery_suggestions,
)
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
    pipeline_name: str | None = None
    run_type: str | None = None
    pipeline_version: str | None = None
    source_freshness_markers: dict[str, object] | None = None
    composite_run_identity: str | None = None
    execution_fingerprint: str | None = None
    manifest_id: str | None = None
    dq_contract_compatibility_hash: str | None = None
    contract_ref: str | None = None
    contract_version: str | None = None
    effective_config_artifact_id: str | None = None
    exact_replay: bool | None = None
    input_snapshot_fingerprint: str | None = None


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
        phase_compatibility = check_phase_compatibility(
            current_phase=current_identity.execution_phase,
            checkpoint_phase=checkpoint_identity.execution_phase,
        )
        config_compatibility = check_config_compatibility(
            current_hash=current_identity.effective_config_hash,
            checkpoint_hash=checkpoint_identity.effective_config_hash,
        )
        execution_identity_compatibility = check_execution_identity_compatibility(
            current_composite_run_identity=current_identity.composite_run_identity,
            checkpoint_composite_run_identity=(
                checkpoint_identity.composite_run_identity
            ),
            current_execution_fingerprint=current_identity.execution_fingerprint,
            checkpoint_execution_fingerprint=checkpoint_identity.execution_fingerprint,
            current_pipeline_name=current_identity.pipeline_name,
            checkpoint_pipeline_name=checkpoint_identity.pipeline_name,
            current_run_type=current_identity.run_type,
            checkpoint_run_type=checkpoint_identity.run_type,
            current_pipeline_version=current_identity.pipeline_version,
            checkpoint_pipeline_version=checkpoint_identity.pipeline_version,
            current_manifest_id=current_identity.manifest_id,
            checkpoint_manifest_id=checkpoint_identity.manifest_id,
            current_dq_contract_compatibility_hash=(
                current_identity.dq_contract_compatibility_hash
            ),
            checkpoint_dq_contract_compatibility_hash=(
                checkpoint_identity.dq_contract_compatibility_hash
            ),
            current_contract_ref=current_identity.contract_ref,
            checkpoint_contract_ref=checkpoint_identity.contract_ref,
            current_contract_version=current_identity.contract_version,
            checkpoint_contract_version=checkpoint_identity.contract_version,
            current_effective_config_hash=current_identity.effective_config_hash,
            checkpoint_effective_config_hash=checkpoint_identity.effective_config_hash,
            current_effective_config_artifact_id=current_identity.effective_config_artifact_id,
            checkpoint_effective_config_artifact_id=checkpoint_identity.effective_config_artifact_id,
            current_exact_replay=current_identity.exact_replay,
            checkpoint_exact_replay=checkpoint_identity.exact_replay,
            current_input_snapshot_fingerprint=(
                current_identity.input_snapshot_fingerprint
            ),
            checkpoint_input_snapshot_fingerprint=(
                checkpoint_identity.input_snapshot_fingerprint
            ),
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
        current_identity_details = build_identity_details(
            IdentityDetailsRequest(
                effective_config_hash=current_identity.effective_config_hash,
                execution_phase=current_identity.execution_phase,
                checkpoint_schema_version=current_identity.checkpoint_schema_version,
                composite_run_identity=current_identity.composite_run_identity,
                execution_fingerprint=current_identity.execution_fingerprint,
                pipeline_name=current_identity.pipeline_name,
                run_type=current_identity.run_type,
                pipeline_version=current_identity.pipeline_version,
                manifest_id=current_identity.manifest_id,
                dq_contract_compatibility_hash=(
                    current_identity.dq_contract_compatibility_hash
                ),
                contract_ref=current_identity.contract_ref,
                contract_version=current_identity.contract_version,
                effective_config_artifact_id=current_identity.effective_config_artifact_id,
                exact_replay=current_identity.exact_replay,
                input_snapshot_fingerprint=current_identity.input_snapshot_fingerprint,
            )
        )
        checkpoint_identity_details = build_identity_details(
            IdentityDetailsRequest(
                effective_config_hash=checkpoint_identity.effective_config_hash,
                execution_phase=checkpoint_identity.execution_phase,
                checkpoint_schema_version=checkpoint_identity.checkpoint_schema_version,
                composite_run_identity=checkpoint_identity.composite_run_identity,
                execution_fingerprint=checkpoint_identity.execution_fingerprint,
                pipeline_name=checkpoint_identity.pipeline_name,
                run_type=checkpoint_identity.run_type,
                pipeline_version=checkpoint_identity.pipeline_version,
                manifest_id=checkpoint_identity.manifest_id,
                dq_contract_compatibility_hash=(
                    checkpoint_identity.dq_contract_compatibility_hash
                ),
                contract_ref=checkpoint_identity.contract_ref,
                contract_version=checkpoint_identity.contract_version,
                effective_config_artifact_id=checkpoint_identity.effective_config_artifact_id,
                exact_replay=checkpoint_identity.exact_replay,
                input_snapshot_fingerprint=checkpoint_identity.input_snapshot_fingerprint,
            )
        )

        return CheckpointCompatibilityResult(
            verdict=verdict,
            message=generate_message(
                verdict_value=verdict.value,
                current_phase=current_identity.execution_phase,
                mode=self.config.mode.value,
            ),
            details=generate_details(
                phase_result=phase_compatibility,
                config_result=config_compatibility,
                execution_identity_result=execution_identity_compatibility,
                schema_result=schema_compatibility,
                current_identity_details=current_identity_details,
                checkpoint_identity_details=checkpoint_identity_details,
                mode=self.config.mode.value,
                allow_policy_override=self.config.allow_policy_override,
                max_schema_version_delta=self.config.max_schema_version_delta,
            ),
            execution_phase=current_identity.execution_phase,
            recovery_suggestions=suggestions,
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
