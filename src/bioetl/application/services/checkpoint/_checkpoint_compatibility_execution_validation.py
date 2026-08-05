"""Execution-identity validation helpers for checkpoint compatibility."""

from __future__ import annotations

from bioetl.application.services.checkpoint._checkpoint_compatibility_message_helpers import (
    exact_replay_mismatch_messages,
    execution_fingerprints_present,
    execution_identity_metadata_mismatch_messages,
    execution_identity_reason_messages,
    input_snapshot_mismatch_messages,
)
from bioetl.application.services.checkpoint._checkpoint_compatibility_runtime_identity import (
    CheckpointExecutionIdentityFallbackContext,
    ExecutionIdentityCompatibilityContext,
    check_execution_identity_compatibility,
)
from bioetl.domain.types.checkpoint_metadata import CheckpointMetadata


def validate_execution_identity_compatibility(
    current_metadata: CheckpointMetadata,
    checkpoint_metadata: CheckpointMetadata,
) -> tuple[bool, bool, list[str]]:
    """Validate execution identity continuity for strict checkpoint resume."""
    execution_identity_result = check_execution_identity_compatibility(
        current=_build_execution_identity_context(current_metadata),
        checkpoint=_build_execution_identity_context(checkpoint_metadata),
    )
    reason_messages = execution_identity_reason_messages(
        current_metadata,
        checkpoint_metadata,
        execution_identity_result,
    )
    if execution_fingerprints_present(current_metadata, checkpoint_metadata):
        fingerprint_messages: list[str] = []
        compatible = _validate_exact_replay_and_snapshots(
            current_metadata,
            checkpoint_metadata,
            fingerprint_messages,
            bool(execution_identity_result["compatible"]),
        )
        final_messages = [
            *reason_messages,
            *fingerprint_messages,
            *exact_replay_mismatch_messages(current_metadata, checkpoint_metadata),
            *input_snapshot_mismatch_messages(current_metadata, checkpoint_metadata),
        ]
        return compatible and not fingerprint_messages, True, final_messages

    compatible, continuity_proven, messages = _initial_execution_identity_outcome(
        execution_identity_result,
    )
    _validate_mismatch_reasons(
        current_metadata, checkpoint_metadata, execution_identity_result, messages
    )
    _validate_metadata_fields(current_metadata, checkpoint_metadata, messages)
    compatible = _validate_exact_replay_and_snapshots(
        current_metadata, checkpoint_metadata, messages, compatible
    )
    metadata_mismatch_messages = execution_identity_metadata_mismatch_messages(
        current_metadata,
        checkpoint_metadata,
    )
    if metadata_mismatch_messages:
        continuity_proven = True

    final_messages = [
        *reason_messages,
        *messages,
        *metadata_mismatch_messages,
        *exact_replay_mismatch_messages(current_metadata, checkpoint_metadata),
        *input_snapshot_mismatch_messages(current_metadata, checkpoint_metadata),
    ]
    return compatible and not messages, continuity_proven, final_messages


def validate_lenient_execution_identity_compatibility(
    current_metadata: CheckpointMetadata,
    checkpoint_metadata: CheckpointMetadata,
) -> tuple[bool, bool, list[str]]:
    """Relax degraded identity checks for lenient compatibility mode."""
    if not (
        _has_explicit_execution_identity(current_metadata)
        or _has_explicit_execution_identity(checkpoint_metadata)
    ):
        return True, False, []
    return validate_execution_identity_compatibility(
        current_metadata,
        checkpoint_metadata,
    )


def _build_execution_identity_context(
    metadata: CheckpointMetadata,
) -> ExecutionIdentityCompatibilityContext:
    """Build runtime execution-identity context from checkpoint metadata."""
    return ExecutionIdentityCompatibilityContext(
        composite_run_identity=metadata.composite_run_identity,
        execution_fingerprint=metadata.execution_fingerprint,
        manifest_id=metadata.manifest_id,
        fallback=CheckpointExecutionIdentityFallbackContext(
            pipeline_name=metadata.pipeline_name,
            run_type=metadata.run_type,
            pipeline_version=metadata.pipeline_version,
            git_commit=metadata.git_commit,
            dependency_lock_hash=metadata.dependency_lock_hash,
            effective_config_hash=metadata.effective_config_hash,
            dq_contract_compatibility_hash=metadata.dq_contract_compatibility_hash,
            contract_ref=metadata.contract_ref,
            contract_version=metadata.contract_version,
            normalization_profile_ref=metadata.normalization_profile_ref,
            normalization_profile_version=metadata.normalization_profile_version,
            normalization_profile_hash=metadata.normalization_profile_hash,
            effective_config_artifact_id=metadata.effective_config_artifact_id,
            exact_replay=metadata.exact_replay,
            input_snapshot_fingerprint=metadata.input_snapshot_fingerprint,
            silver_filter_compatibility_mode=(
                metadata.silver_filter_compatibility_mode
            ),
        ),
    )


def _initial_execution_identity_outcome(
    execution_identity_result: dict[str, object],
) -> tuple[bool, bool, list[str]]:
    """Resolve initial strict identity verdict before metadata cross-checks."""
    messages: list[str] = []
    reason = execution_identity_result["reason"]
    continuity_proven = reason != "execution_identity_not_enforced"
    compatible = continuity_proven
    if reason in {
        "checkpoint_execution_identity_fallback_mismatch",
        "degraded_runtime_anchor_fingerprint_mismatch",
    }:
        compatible = False
    return compatible, continuity_proven, messages


def _validate_mismatch_reasons(
    current_metadata: CheckpointMetadata,
    checkpoint_metadata: CheckpointMetadata,
    execution_identity_result: dict[str, object],
    messages: list[str],
) -> None:
    """Add mismatch reason messages based on execution identity result."""
    reason = execution_identity_result.get("reason")
    if reason == "checkpoint_execution_identity_fallback_mismatch":
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
    if current_metadata.exact_replay:
        if checkpoint_metadata.exact_replay is not True:
            messages.append(
                "Exact replay mismatch: current run requires exact replay but "
                "checkpoint was not captured in exact replay mode"
            )
            compatible = False
        elif not checkpoint_metadata.input_snapshot_fingerprint:
            messages.append(
                "Exact replay requires checkpoint input snapshot fingerprint, "
                "but none was persisted"
            )
            messages.append("checkpoint_missing_snapshot_anchor")
            compatible = False
        elif (
            current_metadata.input_snapshot_fingerprint
            and checkpoint_metadata.input_snapshot_fingerprint
            and current_metadata.input_snapshot_fingerprint
            != checkpoint_metadata.input_snapshot_fingerprint
        ):
            messages.append(
                "Input snapshot fingerprint mismatch: "
                f"current={current_metadata.input_snapshot_fingerprint}, "
                f"checkpoint={checkpoint_metadata.input_snapshot_fingerprint}"
            )
            compatible = False
        elif (
            current_metadata.input_snapshot_ids
            and checkpoint_metadata.input_snapshot_ids
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


def _has_explicit_execution_identity(metadata: CheckpointMetadata) -> bool:
    """Return ``True`` when strict execution anchors are explicitly present."""
    return any(
        (
            metadata.execution_fingerprint,
            metadata.manifest_id,
        )
    )
