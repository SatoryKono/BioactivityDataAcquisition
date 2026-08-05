"""Checkpoint compatibility service for resume safety decisions."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.application.services.checkpoint._checkpoint_compatibility_execution_validation import (
    validate_execution_identity_compatibility,
    validate_lenient_execution_identity_compatibility,
)
from bioetl.application.services.checkpoint.checkpoint_compatibility_policy import (
    lenient_resume_degraded_messages,
    strict_anchor_policy_requested,
    validate_dq_contract_compatibility,
    validate_lenient_dq_compatibility,
    validate_lenient_pipeline_compatibility,
    validate_pipeline_version_compatibility,
    validate_required_checkpoint_anchors,
    validate_rule_bundle_compatibility,
)
from bioetl.application.services.checkpoint.checkpoint_compatibility_results import (
    build_lenient_checkpoint_compatibility_result,
    build_strict_checkpoint_compatibility_result,
)
from bioetl.application.services.checkpoint.checkpoint_compatibility_telemetry import (
    emit_checkpoint_compatibility_metric,
    log_lenient_checkpoint_compatibility_result,
    log_strict_checkpoint_compatibility_result,
)
from bioetl.domain.types.checkpoint_metadata import (
    CheckpointCompatibilityResult,
    CheckpointMetadata,
)

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort, MetricsPort


class CheckpointCompatibilityService:
    """Application service that validates checkpoint compatibility."""

    def __init__(
        self,
        logger: LoggerPort,
        *,
        metrics: MetricsPort | None = None,
        pipeline_name: str | None = None,
    ) -> None:
        self._logger = logger
        self._metrics = metrics
        self._pipeline_name = pipeline_name

    def validate_checkpoint_compatibility(
        self,
        current_metadata: CheckpointMetadata,
        checkpoint_metadata: CheckpointMetadata,
    ) -> CheckpointCompatibilityResult:
        """Run strict checkpoint compatibility validation for resume safety."""
        strict_required = strict_anchor_policy_requested(
            current_metadata,
            checkpoint_metadata,
        )
        dq_compatible, dq_messages = validate_dq_contract_compatibility(
            current_metadata,
            checkpoint_metadata,
            strict=strict_required,
        )
        pipeline_compatible, pipeline_messages = (
            validate_pipeline_version_compatibility(
                current_metadata,
                checkpoint_metadata,
                strict=strict_required,
            )
        )
        required_anchor_compatible, required_anchor_messages = (
            validate_required_checkpoint_anchors(current_metadata, checkpoint_metadata)
            if strict_required
            else (True, [])
        )
        rule_bundle_messages = validate_rule_bundle_compatibility(
            current_metadata,
            checkpoint_metadata,
        )
        (
            execution_identity_compatible,
            identity_continuity_proven,
            execution_identity_messages,
        ) = validate_execution_identity_compatibility(
            current_metadata,
            checkpoint_metadata,
        )
        messages = (
            required_anchor_messages
            + dq_messages
            + pipeline_messages
            + rule_bundle_messages
            + execution_identity_messages
        )
        compatible = (
            required_anchor_compatible
            and dq_compatible
            and pipeline_compatible
            and execution_identity_compatible
        )
        log_strict_checkpoint_compatibility_result(
            self._logger,
            compatible=compatible,
            messages=messages,
        )
        emit_checkpoint_compatibility_metric(
            self._metrics,
            pipeline_name=self._pipeline_name,
            disposition=("strict_compatible" if compatible else "strict_incompatible"),
        )
        return build_strict_checkpoint_compatibility_result(
            compatible=compatible,
            dq_compatible=dq_compatible,
            pipeline_compatible=pipeline_compatible,
            execution_identity_compatible=execution_identity_compatible,
            identity_continuity_proven=identity_continuity_proven,
            required_anchor_compatible=required_anchor_compatible,
            messages=messages,
        )

    def validate_minimum_compatibility(
        self,
        current_metadata: CheckpointMetadata,
        checkpoint_metadata: CheckpointMetadata,
    ) -> CheckpointCompatibilityResult:
        """Run lenient compatibility checks for best-effort resume scenarios."""
        dq_compatible, dq_messages = validate_lenient_dq_compatibility(
            current_metadata,
            checkpoint_metadata,
        )
        pipeline_compatible, pipeline_messages = (
            validate_lenient_pipeline_compatibility(
                current_metadata,
                checkpoint_metadata,
            )
        )
        (
            execution_identity_compatible,
            identity_continuity_proven,
            execution_identity_messages,
        ) = validate_lenient_execution_identity_compatibility(
            current_metadata,
            checkpoint_metadata,
        )
        messages = dq_messages + pipeline_messages + execution_identity_messages
        compatible = (
            dq_compatible and pipeline_compatible and execution_identity_compatible
        )
        degraded_messages = (
            lenient_resume_degraded_messages(current_metadata, checkpoint_metadata)
            if compatible
            else ()
        )
        messages = [*messages, *degraded_messages]
        log_lenient_checkpoint_compatibility_result(
            self._logger,
            compatible=compatible,
            messages=messages,
        )
        emit_checkpoint_compatibility_metric(
            self._metrics,
            pipeline_name=self._pipeline_name,
            disposition=(
                "lenient_compatible" if compatible else "lenient_incompatible"
            ),
        )
        return build_lenient_checkpoint_compatibility_result(
            compatible=compatible,
            dq_compatible=dq_compatible,
            pipeline_compatible=pipeline_compatible,
            execution_identity_compatible=execution_identity_compatible,
            identity_continuity_proven=identity_continuity_proven,
            messages=messages,
            degraded_messages=degraded_messages,
        )


__all__ = ["CheckpointCompatibilityService"]
