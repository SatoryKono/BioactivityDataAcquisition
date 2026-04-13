"""Checkpoint compatibility service for resume safety decisions."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.application.services.checkpoint_compatibility_runtime import (
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


def _strict_disposition(compatible: bool) -> str:
    """Return the strict-policy checkpoint compatibility disposition label."""
    return "strict_compatible" if compatible else "strict_incompatible"


def _lenient_disposition(compatible: bool) -> str:
    """Return the lenient-policy checkpoint compatibility disposition label."""
    return "lenient_compatible" if compatible else "lenient_incompatible"


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
    execution_identity_result = check_execution_identity_compatibility(
        current_composite_run_identity=current_metadata.composite_run_identity,
        checkpoint_composite_run_identity=checkpoint_metadata.composite_run_identity,
        current_execution_fingerprint=current_metadata.execution_fingerprint,
        checkpoint_execution_fingerprint=checkpoint_metadata.execution_fingerprint,
        current_pipeline_name=current_metadata.pipeline_name,
        checkpoint_pipeline_name=checkpoint_metadata.pipeline_name,
        current_run_type=current_metadata.run_type,
        checkpoint_run_type=checkpoint_metadata.run_type,
        current_pipeline_version=current_metadata.pipeline_version,
        checkpoint_pipeline_version=checkpoint_metadata.pipeline_version,
        current_manifest_id=current_metadata.manifest_id,
        checkpoint_manifest_id=checkpoint_metadata.manifest_id,
        current_dq_contract_compatibility_hash=(
            current_metadata.dq_contract_compatibility_hash
        ),
        checkpoint_dq_contract_compatibility_hash=(
            checkpoint_metadata.dq_contract_compatibility_hash
        ),
        current_contract_ref=current_metadata.contract_ref,
        checkpoint_contract_ref=checkpoint_metadata.contract_ref,
        current_contract_version=current_metadata.contract_version,
        checkpoint_contract_version=checkpoint_metadata.contract_version,
        current_effective_config_hash=current_metadata.effective_config_hash,
        checkpoint_effective_config_hash=checkpoint_metadata.effective_config_hash,
        current_effective_config_artifact_id=current_metadata.effective_config_artifact_id,
        checkpoint_effective_config_artifact_id=checkpoint_metadata.effective_config_artifact_id,
        current_exact_replay=current_metadata.exact_replay,
        checkpoint_exact_replay=checkpoint_metadata.exact_replay,
        current_input_snapshot_fingerprint=current_metadata.input_snapshot_fingerprint,
        checkpoint_input_snapshot_fingerprint=(
            checkpoint_metadata.input_snapshot_fingerprint
        ),
    )
    reason_messages = _execution_identity_reason_messages(
        current_metadata,
        checkpoint_metadata,
        execution_identity_result,
    )
    if _execution_fingerprints_present(current_metadata, checkpoint_metadata):
        compatible = bool(execution_identity_result["compatible"])
        return compatible, reason_messages
    messages = [
        *reason_messages,
        *_execution_identity_metadata_mismatch_messages(
            current_metadata,
            checkpoint_metadata,
        ),
        *_exact_replay_mismatch_messages(current_metadata, checkpoint_metadata),
        *_input_snapshot_mismatch_messages(current_metadata, checkpoint_metadata),
    ]
    return not messages, messages


def _execution_fingerprints_present(
    current_metadata: CheckpointMetadata,
    checkpoint_metadata: CheckpointMetadata,
) -> bool:
    """Return whether execution fingerprint compatibility is strictly enforced."""
    return bool(
        current_metadata.execution_fingerprint
        and checkpoint_metadata.execution_fingerprint
    )


def _execution_identity_reason_messages(
    current_metadata: CheckpointMetadata,
    checkpoint_metadata: CheckpointMetadata,
    execution_identity_result: dict[str, object],
) -> list[str]:
    """Map compatibility reason codes to user-facing mismatch messages."""
    return [
        *_composite_identity_reason_messages(
            current_metadata,
            checkpoint_metadata,
            execution_identity_result,
        ),
        *_runtime_anchor_reason_messages(
            current_metadata,
            checkpoint_metadata,
            execution_identity_result,
        ),
        *_execution_fingerprint_reason_messages(
            current_metadata,
            checkpoint_metadata,
            execution_identity_result,
        ),
    ]


def _composite_identity_reason_messages(
    current_metadata: CheckpointMetadata,
    checkpoint_metadata: CheckpointMetadata,
    execution_identity_result: dict[str, object],
) -> list[str]:
    """Return composite-run-identity mismatch messages in stable order."""
    reason = str(execution_identity_result["reason"])
    if reason == "composite_run_identity_missing":
        return [
            "Composite run identity missing: "
            f"current={current_metadata.composite_run_identity}, "
            f"checkpoint={checkpoint_metadata.composite_run_identity}"
        ]
    if reason == "composite_run_identity_mismatch":
        return [
            "Composite run identity mismatch: "
            f"current={current_metadata.composite_run_identity}, "
            f"checkpoint={checkpoint_metadata.composite_run_identity}"
        ]
    return []


def _runtime_anchor_reason_messages(
    current_metadata: CheckpointMetadata,
    checkpoint_metadata: CheckpointMetadata,
    execution_identity_result: dict[str, object],
) -> list[str]:
    """Return canonical fallback or degraded-anchor mismatch messages."""
    reason = str(execution_identity_result["reason"])
    if reason == "checkpoint_execution_identity_fallback_mismatch":
        return [
            "Canonical checkpoint execution identity mismatch: "
            f"current={current_metadata.checkpoint_execution_identity_fingerprint()}, "
            f"checkpoint={checkpoint_metadata.checkpoint_execution_identity_fingerprint()}"
        ]
    if reason == "degraded_runtime_anchor_fingerprint_mismatch":
        return [
            "Degraded runtime-anchor fingerprint mismatch: "
            f"current_manifest={current_metadata.manifest_id}, "
            f"checkpoint_manifest={checkpoint_metadata.manifest_id}"
        ]
    return []


def _execution_fingerprint_reason_messages(
    current_metadata: CheckpointMetadata,
    checkpoint_metadata: CheckpointMetadata,
    execution_identity_result: dict[str, object],
) -> list[str]:
    """Return direct execution-fingerprint mismatch messages when applicable."""
    if str(execution_identity_result["reason"]) != "execution_fingerprint_mismatch":
        return []
    return [
        "Execution fingerprint mismatch: "
        f"current={current_metadata.execution_fingerprint}, "
        f"checkpoint={checkpoint_metadata.execution_fingerprint}"
    ]


def _execution_identity_metadata_mismatch_messages(
    current_metadata: CheckpointMetadata,
    checkpoint_metadata: CheckpointMetadata,
) -> list[str]:
    """Return mismatch messages for runtime anchors stored directly on metadata."""
    return [
        *_optional_mismatch_message(
            current_metadata.effective_config_hash,
            checkpoint_metadata.effective_config_hash,
            label="Effective config hash mismatch",
        ),
        *_optional_mismatch_message(
            current_metadata.manifest_id,
            checkpoint_metadata.manifest_id,
            label="Manifest identity mismatch",
        ),
        *_optional_mismatch_message(
            current_metadata.contract_ref,
            checkpoint_metadata.contract_ref,
            label="Contract reference mismatch",
        ),
        *_optional_mismatch_message(
            current_metadata.contract_version,
            checkpoint_metadata.contract_version,
            label="Contract version mismatch",
        ),
    ]


def _optional_mismatch_message(
    current_value: str | None,
    checkpoint_value: str | None,
    *,
    label: str,
) -> list[str]:
    """Return one mismatch message only when both values exist and differ."""
    if not current_value or not checkpoint_value or current_value == checkpoint_value:
        return []
    return [f"{label}: current={current_value}, checkpoint={checkpoint_value}"]


def _exact_replay_mismatch_messages(
    current_metadata: CheckpointMetadata,
    checkpoint_metadata: CheckpointMetadata,
) -> list[str]:
    """Return exact-replay contract mismatch messages."""
    if not current_metadata.exact_replay:
        return []
    if checkpoint_metadata.exact_replay is not True:
        return [
            "Exact replay mismatch: current run requires exact replay but "
            "checkpoint was not captured in exact replay mode"
        ]
    if checkpoint_metadata.input_snapshot_ids:
        return []
    return [
        "Exact replay requires checkpoint input snapshot anchors, but none were persisted"
    ]


def _input_snapshot_mismatch_messages(
    current_metadata: CheckpointMetadata,
    checkpoint_metadata: CheckpointMetadata,
) -> list[str]:
    """Return persisted input snapshot mismatch messages."""
    if (
        not current_metadata.input_snapshot_ids
        or not checkpoint_metadata.input_snapshot_ids
        or current_metadata.input_snapshot_ids == checkpoint_metadata.input_snapshot_ids
    ):
        return []
    return [
        "Input snapshot identity mismatch: "
        f"current={list(current_metadata.input_snapshot_ids)}, "
        f"checkpoint={list(checkpoint_metadata.input_snapshot_ids)}"
    ]


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
            elif (
                current_metadata.pipeline_version
                != checkpoint_metadata.pipeline_version
            ):
                messages.append(
                    "Minor pipeline version changed (lenient mode): "
                    f"current={current_metadata.pipeline_version}, "
                    f"checkpoint={checkpoint_metadata.pipeline_version}"
                )
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
            disposition=_strict_disposition(compatible),
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
        compatible = (
            dq_compatible and pipeline_compatible and execution_identity_compatible
        )
        _log_lenient_result(self._logger, compatible=compatible, messages=messages)
        _emit_checkpoint_metric(
            self._metrics,
            pipeline_name=self._pipeline_name,
            disposition=_lenient_disposition(compatible),
        )
        return CheckpointCompatibilityResult(
            compatible=compatible,
            dq_compatible=dq_compatible,
            pipeline_compatible=pipeline_compatible,
            messages=messages,
            execution_identity_compatible=execution_identity_compatible,
        )


__all__ = ["CheckpointCompatibilityService"]
