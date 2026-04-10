"""Checkpoint compatibility service for resume safety decisions."""

from __future__ import annotations

from typing import TYPE_CHECKING

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
        "checkpoint_compatibility_events_total",
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
    messages: list[str] = []
    execution_identity_compatible = True
    current_runtime_anchor_fingerprint = current_metadata.runtime_anchor_fingerprint()
    checkpoint_runtime_anchor_fingerprint = (
        checkpoint_metadata.runtime_anchor_fingerprint()
    )
    if (
        current_metadata.execution_fingerprint
        and checkpoint_metadata.execution_fingerprint
    ):
        if (
            current_metadata.execution_fingerprint
            != checkpoint_metadata.execution_fingerprint
        ):
            execution_identity_compatible = False
            messages.append(
                "Execution fingerprint mismatch: "
                f"current={current_metadata.execution_fingerprint}, "
                f"checkpoint={checkpoint_metadata.execution_fingerprint}"
            )
        return execution_identity_compatible, messages
    if (
        current_runtime_anchor_fingerprint
        and checkpoint_runtime_anchor_fingerprint
        and current_runtime_anchor_fingerprint != checkpoint_runtime_anchor_fingerprint
    ):
        execution_identity_compatible = False
        messages.append(
            "Runtime anchor fingerprint mismatch: "
            f"current={current_runtime_anchor_fingerprint}, "
            f"checkpoint={checkpoint_runtime_anchor_fingerprint}"
        )
    if (
        current_metadata.effective_config_hash
        and checkpoint_metadata.effective_config_hash
        and current_metadata.effective_config_hash
        != checkpoint_metadata.effective_config_hash
    ):
        execution_identity_compatible = False
        messages.append(
            "Effective config hash mismatch: "
            f"current={current_metadata.effective_config_hash}, "
            f"checkpoint={checkpoint_metadata.effective_config_hash}"
        )
    if (
        current_metadata.manifest_id
        and checkpoint_metadata.manifest_id
        and current_metadata.manifest_id != checkpoint_metadata.manifest_id
    ):
        execution_identity_compatible = False
        messages.append(
            "Manifest identity mismatch: "
            f"current={current_metadata.manifest_id}, "
            f"checkpoint={checkpoint_metadata.manifest_id}"
        )
    if (
        current_metadata.contract_ref
        and checkpoint_metadata.contract_ref
        and current_metadata.contract_ref != checkpoint_metadata.contract_ref
    ):
        execution_identity_compatible = False
        messages.append(
            "Contract reference mismatch: "
            f"current={current_metadata.contract_ref}, "
            f"checkpoint={checkpoint_metadata.contract_ref}"
        )
    if (
        current_metadata.contract_version
        and checkpoint_metadata.contract_version
        and current_metadata.contract_version != checkpoint_metadata.contract_version
    ):
        execution_identity_compatible = False
        messages.append(
            "Contract version mismatch: "
            f"current={current_metadata.contract_version}, "
            f"checkpoint={checkpoint_metadata.contract_version}"
        )
    if current_metadata.exact_replay:
        if checkpoint_metadata.exact_replay is not True:
            execution_identity_compatible = False
            messages.append(
                "Exact replay mismatch: current run requires exact replay but "
                "checkpoint was not captured in exact replay mode"
            )
        elif not checkpoint_metadata.input_snapshot_ids:
            execution_identity_compatible = False
            messages.append(
                "Exact replay requires checkpoint input snapshot anchors, but none were persisted"
            )
    if (
        current_metadata.input_snapshot_ids
        and checkpoint_metadata.input_snapshot_ids
        and current_metadata.input_snapshot_ids != checkpoint_metadata.input_snapshot_ids
    ):
        execution_identity_compatible = False
        messages.append(
            "Input snapshot identity mismatch: "
            f"current={list(current_metadata.input_snapshot_ids)}, "
            f"checkpoint={list(checkpoint_metadata.input_snapshot_ids)}"
        )
    return execution_identity_compatible, messages


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
