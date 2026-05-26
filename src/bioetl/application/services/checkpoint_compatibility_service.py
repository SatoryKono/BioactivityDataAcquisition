"""Checkpoint compatibility service for resume safety decisions."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.application.services._checkpoint_compatibility_execution_validation import (
    validate_execution_identity_compatibility,
    validate_lenient_execution_identity_compatibility,
)
from bioetl.application.services.checkpoint_compatibility_policy import (
    lenient_resume_degraded_messages,
    strict_anchor_policy_requested,
    validate_dq_contract_compatibility,
    validate_lenient_dq_compatibility,
    validate_lenient_pipeline_compatibility,
    validate_pipeline_version_compatibility,
    validate_required_checkpoint_anchors,
    validate_rule_bundle_compatibility,
)
from bioetl.domain.types.checkpoint_metadata import (
    CheckpointCompatibilityResult,
    CheckpointMetadata,
)

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort, MetricsPort


def _emit_checkpoint_metric(
    metrics: MetricsPort | None,
    *,
    pipeline_name: str | None,
    disposition: str,
) -> None:
    """Emit one checkpoint compatibility event metric when metrics are enabled."""
    if metrics is None:
        return
    metrics.increment_counter(
        "bioetl_checkpoint_compatibility_events_total",
        1,
        {
            "pipeline": pipeline_name or "unknown",
            "disposition": disposition,
        },
    )


def _log_result(logger: LoggerPort, *, compatible: bool, messages: list[str]) -> None:
    if compatible:
        logger.info(
            "Checkpoint compatibility validation passed",
            messages=messages,
        )
        return
    logger.warning(
        "Checkpoint compatibility validation failed",
        messages=messages,
    )


def _log_lenient_result(
    logger: LoggerPort, *, compatible: bool, messages: list[str]
) -> None:
    if compatible:
        logger.info(
            "Checkpoint minimum compatibility validation passed (lenient mode)",
            messages=messages,
        )
        return
    logger.warning(
        "Checkpoint minimum compatibility validation failed (lenient mode)",
        messages=messages,
    )


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
        _log_result(self._logger, compatible=compatible, messages=messages)
        _emit_checkpoint_metric(
            self._metrics,
            pipeline_name=self._pipeline_name,
            disposition=("strict_compatible" if compatible else "strict_incompatible"),
        )
        if compatible:
            return CheckpointCompatibilityResult.compatible_result()
        return CheckpointCompatibilityResult.incompatible_result(
            dq_compatible=dq_compatible,
            pipeline_compatible=pipeline_compatible,
            execution_identity_compatible=(
                execution_identity_compatible and required_anchor_compatible
            ),
            identity_continuity_proven=(
                identity_continuity_proven and required_anchor_compatible
            ),
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
        resume_verdict = (
            "resume_only_degraded"
            if degraded_messages
            else ("resume_only" if compatible else "non_replayable")
        )
        _log_lenient_result(self._logger, compatible=compatible, messages=messages)
        _emit_checkpoint_metric(
            self._metrics,
            pipeline_name=self._pipeline_name,
            disposition=(
                "lenient_compatible" if compatible else "lenient_incompatible"
            ),
        )
        return CheckpointCompatibilityResult(
            compatible=compatible,
            dq_compatible=dq_compatible,
            pipeline_compatible=pipeline_compatible,
            messages=messages,
            execution_identity_compatible=execution_identity_compatible,
            identity_continuity_proven=identity_continuity_proven,
            resume_verdict=resume_verdict,
            degraded_resume_reasons=degraded_messages,
        )


__all__ = ["CheckpointCompatibilityService"]
