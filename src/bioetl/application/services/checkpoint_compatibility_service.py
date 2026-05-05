"""Checkpoint compatibility service for resume safety decisions."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.application.services._checkpoint_compatibility_execution_validation import (
    validate_execution_identity_compatibility,
    validate_lenient_execution_identity_compatibility,
)
from bioetl.domain.types.checkpoint_metadata import (
    CheckpointCompatibilityResult,
    CheckpointMetadata,
)

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort, MetricsPort


DQ_CONTRACTS_COMPATIBLE_MESSAGE = "DQ contracts are compatible"
PIPELINE_VERSIONS_COMPATIBLE_MESSAGE = "Pipeline versions are compatible"
_STRICT_REQUIRED_CHECKPOINT_FIELDS: tuple[str, ...] = (
    "execution_fingerprint",
    "manifest_id",
    "effective_config_hash",
    "effective_config_artifact_id",
    "contract_ref",
    "contract_version",
    "dq_contract_compatibility_hash",
    "pipeline_version",
    "git_commit",
    "exact_replay",
)


def _strict_anchor_policy_requested(
    current_metadata: CheckpointMetadata,
    checkpoint_metadata: CheckpointMetadata,
) -> bool:
    """Return ``True`` when resume validation has enough strict context to fail closed."""
    if bool(current_metadata.exact_replay):
        return True
    return any(
        (
            current_metadata.manifest_id,
            checkpoint_metadata.manifest_id,
            current_metadata.effective_config_artifact_id,
            checkpoint_metadata.effective_config_artifact_id,
            current_metadata.contract_ref,
            checkpoint_metadata.contract_ref,
            current_metadata.contract_version,
            checkpoint_metadata.contract_version,
            current_metadata.git_commit,
            checkpoint_metadata.git_commit,
        )
    )


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
    *,
    strict: bool,
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
            messages.append(DQ_CONTRACTS_COMPATIBLE_MESSAGE)
    elif strict:
        dq_compatible = False
        messages.append(
            "DQ contract compatibility: checkpoint_missing_required_execution_anchor"
        )
    else:
        messages.append(
            "DQ contract compatibility: not enforced (missing contract info)"
        )
    return dq_compatible, messages


def _validate_pipeline_version_compatibility(
    current_metadata: CheckpointMetadata,
    checkpoint_metadata: CheckpointMetadata,
    *,
    strict: bool,
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
            messages.append(PIPELINE_VERSIONS_COMPATIBLE_MESSAGE)
    elif strict:
        pipeline_compatible = False
        messages.append(
            "Pipeline version compatibility: checkpoint_missing_required_execution_anchor"
        )
    else:
        messages.append(
            "Pipeline version compatibility: not enforced (missing version info)"
        )
    return pipeline_compatible, messages


def _validate_required_checkpoint_anchors(
    current_metadata: CheckpointMetadata,
    checkpoint_metadata: CheckpointMetadata,
) -> tuple[bool, list[str]]:
    """Reject strict resume when checkpoint metadata omits required anchors."""
    required_fields = list(_STRICT_REQUIRED_CHECKPOINT_FIELDS)
    if bool(current_metadata.exact_replay):
        if current_metadata.input_snapshot_ids:
            required_fields.append("input_snapshot_ids")
        else:
            required_fields.append("input_snapshot_fingerprint")
    missing = checkpoint_metadata.missing_required_anchors(tuple(required_fields))
    if not missing:
        return True, []
    messages = [
        f"checkpoint_missing_required_execution_anchor: {field_name}"
        for field_name in missing
    ]
    if "manifest_id" in missing:
        messages.append("checkpoint_missing_manifest_anchor")
    if "input_snapshot_ids" in missing or "input_snapshot_fingerprint" in missing:
        messages.append("checkpoint_missing_snapshot_anchor")
    return False, messages


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
            messages.append(DQ_CONTRACTS_COMPATIBLE_MESSAGE)
    else:
        # In lenient mode, missing DQ hashes are considered compatible
        messages.append(DQ_CONTRACTS_COMPATIBLE_MESSAGE)
    return True, messages


def _lenient_pipeline_version_message(
    current_version: str,
    checkpoint_version: str,
) -> tuple[bool, str]:
    current_parts = current_version.split(".")
    checkpoint_parts = checkpoint_version.split(".")
    if current_parts[0] != checkpoint_parts[0]:
        return (
            False,
            "Major pipeline version mismatch: "
            f"current={current_version}, "
            f"checkpoint={checkpoint_version}",
        )
    if len(current_parts) < 2 or len(checkpoint_parts) < 2:
        return True, PIPELINE_VERSIONS_COMPATIBLE_MESSAGE
    if current_parts[1] != checkpoint_parts[1]:
        return (
            True,
            "Minor pipeline version changed (lenient mode): "
            f"current={current_version}, "
            f"checkpoint={checkpoint_version}",
        )
    if (
        len(current_parts) >= 3
        and len(checkpoint_parts) >= 3
        and current_parts[2] != checkpoint_parts[2]
    ):
        return (
            True,
            "Patch pipeline version changed (lenient mode): "
            f"current={current_version}, "
            f"checkpoint={checkpoint_version}",
        )
    return True, PIPELINE_VERSIONS_COMPATIBLE_MESSAGE


def _validate_lenient_pipeline_compatibility(
    current_metadata: CheckpointMetadata,
    checkpoint_metadata: CheckpointMetadata,
) -> tuple[bool, list[str]]:
    messages: list[str] = []
    if not (current_metadata.pipeline_version and checkpoint_metadata.pipeline_version):
        return True, messages
    pipeline_compatible, message = _lenient_pipeline_version_message(
        current_metadata.pipeline_version,
        checkpoint_metadata.pipeline_version,
    )
    return pipeline_compatible, [message]


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
        strict_required = _strict_anchor_policy_requested(
            current_metadata,
            checkpoint_metadata,
        )
        dq_compatible, dq_messages = _validate_dq_contract_compatibility(
            current_metadata,
            checkpoint_metadata,
            strict=strict_required,
        )
        pipeline_compatible, pipeline_messages = (
            _validate_pipeline_version_compatibility(
                current_metadata,
                checkpoint_metadata,
                strict=strict_required,
            )
        )
        required_anchor_compatible, required_anchor_messages = (
            _validate_required_checkpoint_anchors(current_metadata, checkpoint_metadata)
            if strict_required
            else (True, [])
        )
        rule_bundle_messages = _validate_rule_bundle_compatibility(
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
        )


__all__ = ["CheckpointCompatibilityService"]
