"""Checkpoint compatibility service for resume safety decisions."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.application.services._checkpoint_compatibility_message_helpers import (
    exact_replay_mismatch_messages,
    execution_fingerprints_present,
    execution_identity_metadata_mismatch_messages,
    execution_identity_reason_messages,
    input_snapshot_mismatch_messages,
)
from bioetl.application.services.checkpoint_compatibility_runtime import (
    CheckpointExecutionIdentityFallbackInput,
    ExecutionIdentityCompatibilityInput,
    check_execution_identity_compatibility,
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


def _validate_dq_contract_compatibility(
    current_metadata: CheckpointMetadata,
    checkpoint_metadata: CheckpointMetadata,
) -> tuple[bool, list[str]]:
    messages: list[str] = []
    dq_compatible = True
    if (
        current_metadata.dq_contract_compatibility_hash
        and checkpoint_metadata.dq_contract_compatibility_hash
    ):
        if (
            current_metadata.dq_contract_compatibility_hash
            != checkpoint_metadata.dq_contract_compatibility_hash
        ):
            dq_compatible = False
            messages.append(
                "DQ contract mismatch: "
                f"current={current_metadata.dq_contract_compatibility_hash}, "
                f"checkpoint={checkpoint_metadata.dq_contract_compatibility_hash}"
            )
        else:
            messages.append("DQ contracts are compatible")
    else:
        messages.append(
            "DQ contract compatibility: not enforced (missing contract info)"
        )
    return dq_compatible, messages


def _validate_pipeline_version_compatibility(
    current_metadata: CheckpointMetadata,
    checkpoint_metadata: CheckpointMetadata,
) -> tuple[bool, list[str]]:
    messages: list[str] = []
    pipeline_compatible = True
    if current_metadata.pipeline_version and checkpoint_metadata.pipeline_version:
        if current_metadata.pipeline_version != checkpoint_metadata.pipeline_version:
            pipeline_compatible = False
            messages.append(
                "Pipeline version mismatch: "
                f"current={current_metadata.pipeline_version}, "
                f"checkpoint={checkpoint_metadata.pipeline_version}"
            )
        else:
            messages.append("Pipeline versions are compatible")
    else:
        messages.append(
            "Pipeline version compatibility: not enforced (missing version info)"
        )
    return pipeline_compatible, messages


def _validate_rule_bundle_compatibility(
    current_metadata: CheckpointMetadata,
    checkpoint_metadata: CheckpointMetadata,
) -> list[str]:
    messages: list[str] = []
    if (
        current_metadata.dq_rule_bundle_version
        and checkpoint_metadata.dq_rule_bundle_version
    ):
        if (
            current_metadata.dq_rule_bundle_version
            != checkpoint_metadata.dq_rule_bundle_version
        ):
            messages.append(
                "DQ rule bundle version changed: "
                f"current={current_metadata.dq_rule_bundle_version}, "
                f"checkpoint={checkpoint_metadata.dq_rule_bundle_version}"
            )
        else:
            messages.append("DQ rule bundle versions are compatible")
    return messages


def _validate_execution_identity_compatibility(
    current_metadata: CheckpointMetadata,
    checkpoint_metadata: CheckpointMetadata,
) -> tuple[bool, list[str]]:
    messages: list[str] = []
    execution_identity_compatible = True
    execution_identity_result = check_execution_identity_compatibility(
        current=ExecutionIdentityCompatibilityInput(
            composite_run_identity=current_metadata.composite_run_identity,
            execution_fingerprint=current_metadata.execution_fingerprint,
            manifest_id=current_metadata.manifest_id,
            fallback=CheckpointExecutionIdentityFallbackInput(
                pipeline_name=current_metadata.pipeline_name,
                run_type=current_metadata.run_type,
                pipeline_version=current_metadata.pipeline_version,
                effective_config_hash=current_metadata.effective_config_hash,
                dq_contract_compatibility_hash=(
                    current_metadata.dq_contract_compatibility_hash
                ),
                contract_ref=current_metadata.contract_ref,
                contract_version=current_metadata.contract_version,
                effective_config_artifact_id=(
                    current_metadata.effective_config_artifact_id
                ),
                exact_replay=current_metadata.exact_replay,
                input_snapshot_fingerprint=(
                    current_metadata.input_snapshot_fingerprint
                ),
            ),
        ),
        checkpoint=ExecutionIdentityCompatibilityInput(
            composite_run_identity=checkpoint_metadata.composite_run_identity,
            execution_fingerprint=checkpoint_metadata.execution_fingerprint,
            manifest_id=checkpoint_metadata.manifest_id,
            fallback=CheckpointExecutionIdentityFallbackInput(
                pipeline_name=checkpoint_metadata.pipeline_name,
                run_type=checkpoint_metadata.run_type,
                pipeline_version=checkpoint_metadata.pipeline_version,
                effective_config_hash=checkpoint_metadata.effective_config_hash,
                dq_contract_compatibility_hash=(
                    checkpoint_metadata.dq_contract_compatibility_hash
                ),
                contract_ref=checkpoint_metadata.contract_ref,
                contract_version=checkpoint_metadata.contract_version,
                effective_config_artifact_id=(
                    checkpoint_metadata.effective_config_artifact_id
                ),
                exact_replay=checkpoint_metadata.exact_replay,
                input_snapshot_fingerprint=(
                    checkpoint_metadata.input_snapshot_fingerprint
                ),
            ),
        ),
    )
    reason_messages = _execution_identity_reason_messages(
        current_metadata,
        checkpoint_metadata,
        execution_identity_result,
    )
    if execution_fingerprints_present(current_metadata, checkpoint_metadata):
        compatible = bool(execution_identity_result["compatible"])
        return compatible, reason_messages
    if (
        current_metadata.execution_fingerprint
        and checkpoint_metadata.execution_fingerprint
    ):
        if not bool(execution_identity_result["compatible"]):
            execution_identity_compatible = False
            messages.append(
                "Execution fingerprint mismatch: "
                f"current={current_metadata.execution_fingerprint}, "
                f"checkpoint={checkpoint_metadata.execution_fingerprint}"
            )
        return execution_identity_compatible, messages
    if execution_identity_result["reason"] == "composite_run_identity_missing":
        execution_identity_compatible = False
        messages.append(
            "Composite run identity missing: "
            f"current={current_metadata.composite_run_identity}, "
            f"checkpoint={checkpoint_metadata.composite_run_identity}"
        )
    elif execution_identity_result["reason"] == "composite_run_identity_mismatch":
        execution_identity_compatible = False
        messages.append(
            "Composite run identity mismatch: "
            f"current={current_metadata.composite_run_identity}, "
            f"checkpoint={checkpoint_metadata.composite_run_identity}"
        )
    if (
        execution_identity_result["reason"]
        == "checkpoint_execution_identity_fallback_mismatch"
    ) or (
        execution_identity_result["reason"]
        == "degraded_runtime_anchor_fingerprint_mismatch"
    ):
        execution_identity_compatible = False

    _validate_mismatch_reasons(
        current_metadata, checkpoint_metadata, execution_identity_result, messages
    )
    _validate_metadata_fields(current_metadata, checkpoint_metadata, messages)
    execution_identity_compatible = _validate_exact_replay_and_snapshots(
        current_metadata, checkpoint_metadata, messages, execution_identity_compatible
    )

    final_messages = [
        *reason_messages,
        *messages,
        *execution_identity_metadata_mismatch_messages(
            current_metadata,
            checkpoint_metadata,
        ),
        *exact_replay_mismatch_messages(current_metadata, checkpoint_metadata),
        *input_snapshot_mismatch_messages(current_metadata, checkpoint_metadata),
    ]
    return execution_identity_compatible and not messages, final_messages


def _validate_mismatch_reasons(
    current_metadata: CheckpointMetadata,
    checkpoint_metadata: CheckpointMetadata,
    execution_identity_result: dict[str, object],
    messages: list[str],
) -> None:
    """Add mismatch reason messages based on execution identity result."""
    reason = execution_identity_result.get("reason")
    if reason == "checkpoint_execution_identity_fallback_mismatch":
        # Only add message if execution fingerprints are actually present
        if _has_execution_fingerprint_metadata(
            current_metadata,
            checkpoint_metadata,
        ):
            messages.append(
                "Checkpoint execution identity fallback mismatch: "
                f"current={current_metadata.execution_fingerprint}, "
                f"checkpoint={checkpoint_metadata.execution_fingerprint}"
            )
    elif reason == "degraded_runtime_anchor_fingerprint_mismatch" and (
        # Runtime anchor fingerprint is computed from metadata fields, not stored directly
        # Add message only if relevant metadata fields are present
        _has_runtime_anchor_metadata(current_metadata, checkpoint_metadata)
    ):
        messages.append("Degraded runtime anchor fingerprint mismatch")


def _has_execution_fingerprint_metadata(
    current_metadata: CheckpointMetadata,
    checkpoint_metadata: CheckpointMetadata,
) -> bool:
    return bool(
        current_metadata.execution_fingerprint
        or checkpoint_metadata.execution_fingerprint
    )


def _has_runtime_anchor_metadata(
    current_metadata: CheckpointMetadata,
    checkpoint_metadata: CheckpointMetadata,
) -> bool:
    return bool(
        current_metadata.manifest_id
        or checkpoint_metadata.manifest_id
        or current_metadata.contract_ref
        or checkpoint_metadata.contract_ref
        or current_metadata.effective_config_hash
        or checkpoint_metadata.effective_config_hash
    )


def _validate_metadata_fields(
    current_metadata: CheckpointMetadata,
    checkpoint_metadata: CheckpointMetadata,
    messages: list[str],
) -> None:
    """Validate metadata field compatibility and add mismatch messages."""
    # Check manifest ID compatibility
    if (
        current_metadata.manifest_id
        and checkpoint_metadata.manifest_id
        and current_metadata.manifest_id != checkpoint_metadata.manifest_id
    ):
        messages.append(
            "Manifest identity mismatch: "
            f"current={current_metadata.manifest_id}, "
            f"checkpoint={checkpoint_metadata.manifest_id}"
        )

    # Check contract reference compatibility
    if (
        current_metadata.contract_ref
        and checkpoint_metadata.contract_ref
        and current_metadata.contract_ref != checkpoint_metadata.contract_ref
    ):
        messages.append(
            "Contract reference mismatch: "
            f"current={current_metadata.contract_ref}, "
            f"checkpoint={checkpoint_metadata.contract_ref}"
        )

    # Check contract version compatibility
    if (
        current_metadata.contract_version
        and checkpoint_metadata.contract_version
        and current_metadata.contract_version != checkpoint_metadata.contract_version
    ):
        messages.append(
            "Contract version mismatch: "
            f"current={current_metadata.contract_version}, "
            f"checkpoint={checkpoint_metadata.contract_version}"
        )


def _validate_exact_replay_and_snapshots(
    current_metadata: CheckpointMetadata,
    checkpoint_metadata: CheckpointMetadata,
    messages: list[str],
    execution_identity_compatible: bool,
) -> bool:
    """Validate exact replay and snapshot compatibility."""
    compatible = execution_identity_compatible

    # Check exact replay requirements
    if current_metadata.exact_replay:
        if checkpoint_metadata.exact_replay is not True:
            messages.append(
                "Exact replay mismatch: current run requires exact replay but "
                "checkpoint was not captured in exact replay mode"
            )
            compatible = False
        elif not checkpoint_metadata.input_snapshot_ids:
            messages.append(
                "Exact replay requires checkpoint input snapshot anchors, but none were persisted"
            )
            compatible = False
        elif (
            current_metadata.input_snapshot_ids
            and current_metadata.input_snapshot_ids
            != checkpoint_metadata.input_snapshot_ids
        ):
            messages.append(
                "Input snapshot identity mismatch: "
                f"current={list(current_metadata.input_snapshot_ids)}, "
                f"checkpoint={list(checkpoint_metadata.input_snapshot_ids)}"
            )
            compatible = False

    return compatible


def _execution_identity_reason_messages(
    current_metadata: CheckpointMetadata,
    checkpoint_metadata: CheckpointMetadata,
    execution_identity_result: dict[str, object],
) -> list[str]:
    """Map compatibility reason codes to user-facing mismatch messages."""
    return execution_identity_reason_messages(
        current_metadata,
        checkpoint_metadata,
        execution_identity_result,
    )


def _validate_lenient_dq_compatibility(
    current_metadata: CheckpointMetadata,
    checkpoint_metadata: CheckpointMetadata,
) -> tuple[bool, list[str]]:
    messages: list[str] = []
    if (
        current_metadata.dq_contract_compatibility_hash
        and checkpoint_metadata.dq_contract_compatibility_hash
    ):
        if (
            current_metadata.dq_contract_compatibility_hash
            != checkpoint_metadata.dq_contract_compatibility_hash
        ):
            messages.append(
                "DQ contract changed (lenient mode): "
                f"current={current_metadata.dq_contract_compatibility_hash}, "
                f"checkpoint={checkpoint_metadata.dq_contract_compatibility_hash}"
            )
        else:
            messages.append("DQ contracts are compatible")
    else:
        # In lenient mode, missing DQ hashes are considered compatible
        messages.append("DQ contracts are compatible")
    return True, messages


def _validate_lenient_pipeline_compatibility(
    current_metadata: CheckpointMetadata,
    checkpoint_metadata: CheckpointMetadata,
) -> tuple[bool, list[str]]:
    messages: list[str] = []
    pipeline_compatible = True
    if current_metadata.pipeline_version and checkpoint_metadata.pipeline_version:
        current_parts = current_metadata.pipeline_version.split(".")
        checkpoint_parts = checkpoint_metadata.pipeline_version.split(".")
        if current_parts and checkpoint_parts:
            if current_parts[0] != checkpoint_parts[0]:
                pipeline_compatible = False
                messages.append(
                    "Major pipeline version mismatch: "
                    f"current={current_metadata.pipeline_version}, "
                    f"checkpoint={checkpoint_metadata.pipeline_version}"
                )
            elif len(current_parts) >= 2 and len(checkpoint_parts) >= 2:
                # Check if minor version changed (allowed in lenient mode)
                if current_parts[1] != checkpoint_parts[1]:
                    messages.append(
                        "Minor pipeline version changed (lenient mode): "
                        f"current={current_metadata.pipeline_version}, "
                        f"checkpoint={checkpoint_metadata.pipeline_version}"
                    )
                # Check if only patch version changed (allowed in lenient mode)
                elif len(current_parts) >= 3 and len(checkpoint_parts) >= 3:
                    if current_parts[2] != checkpoint_parts[2]:
                        messages.append(
                            "Patch pipeline version changed (lenient mode): "
                            f"current={current_metadata.pipeline_version}, "
                            f"checkpoint={checkpoint_metadata.pipeline_version}"
                        )
                    else:
                        messages.append("Pipeline versions are compatible")
                else:
                    messages.append("Pipeline versions are compatible")
            else:
                messages.append("Pipeline versions are compatible")
    return pipeline_compatible, messages


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
        dq_compatible, dq_messages = _validate_dq_contract_compatibility(
            current_metadata,
            checkpoint_metadata,
        )
        pipeline_compatible, pipeline_messages = (
            _validate_pipeline_version_compatibility(
                current_metadata,
                checkpoint_metadata,
            )
        )
        rule_bundle_messages = _validate_rule_bundle_compatibility(
            current_metadata,
            checkpoint_metadata,
        )
        execution_identity_compatible, execution_identity_messages = (
            _validate_execution_identity_compatibility(
                current_metadata,
                checkpoint_metadata,
            )
        )
        messages = (
            dq_messages
            + pipeline_messages
            + rule_bundle_messages
            + execution_identity_messages
        )
        compatible = (
            dq_compatible and pipeline_compatible and execution_identity_compatible
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
            execution_identity_compatible=execution_identity_compatible,
            messages=messages,
        )

    def validate_minimum_compatibility(
        self,
        current_metadata: CheckpointMetadata,
        checkpoint_metadata: CheckpointMetadata,
    ) -> CheckpointCompatibilityResult:
        """Run lenient compatibility checks for best-effort resume scenarios."""
        dq_compatible, dq_messages = _validate_lenient_dq_compatibility(
            current_metadata,
            checkpoint_metadata,
        )
        pipeline_compatible, pipeline_messages = (
            _validate_lenient_pipeline_compatibility(
                current_metadata,
                checkpoint_metadata,
            )
        )
        execution_identity_compatible, execution_identity_messages = (
            _validate_execution_identity_compatibility(
                current_metadata,
                checkpoint_metadata,
            )
        )
        messages = dq_messages + pipeline_messages + execution_identity_messages
        # In lenient mode, allow execution identity mismatch for minor and patch version changes
        has_version_change = any(
            "Minor pipeline version changed" in msg or "Patch pipeline version changed" in msg
            for msg in pipeline_messages
        )
        if (
            len(dq_messages) == 1
            and "DQ contracts are compatible" in dq_messages[0]
            and has_version_change
        ):
            compatible = dq_compatible and pipeline_compatible
        else:
            compatible = (
                dq_compatible and pipeline_compatible and execution_identity_compatible
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
        )


__all__ = ["CheckpointCompatibilityService"]
