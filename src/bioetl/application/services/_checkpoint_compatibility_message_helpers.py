"""Message helpers for checkpoint execution-identity compatibility."""

from __future__ import annotations

from bioetl.domain.types.checkpoint_metadata import CheckpointMetadata


def execution_fingerprints_present(
    current_metadata: CheckpointMetadata,
    checkpoint_metadata: CheckpointMetadata,
) -> bool:
    """Return whether execution fingerprint compatibility is strictly enforced."""
    return bool(
        current_metadata.execution_fingerprint
        and checkpoint_metadata.execution_fingerprint
    )


def execution_identity_reason_messages(
    current_metadata: CheckpointMetadata,
    checkpoint_metadata: CheckpointMetadata,
    execution_identity_result: dict[str, object],
) -> list[str]:
    """Map compatibility reason codes to user-facing mismatch messages."""
    return [
        *composite_identity_reason_messages(
            current_metadata,
            checkpoint_metadata,
            execution_identity_result,
        ),
        *runtime_anchor_reason_messages(
            current_metadata,
            checkpoint_metadata,
            execution_identity_result,
        ),
        *execution_fingerprint_reason_messages(
            current_metadata,
            checkpoint_metadata,
            execution_identity_result,
        ),
        *unenforced_execution_identity_reason_messages(execution_identity_result),
    ]


def composite_identity_reason_messages(
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


def runtime_anchor_reason_messages(
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


def execution_fingerprint_reason_messages(
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


def unenforced_execution_identity_reason_messages(
    execution_identity_result: dict[str, object],
) -> list[str]:
    """Return fail-closed diagnostics when no comparable identity proof exists."""
    if str(execution_identity_result["reason"]) != "execution_identity_not_enforced":
        return []
    return [
        "Execution identity continuity not proven: missing or inconclusive "
        "execution_fingerprint, composite_run_identity, canonical checkpoint "
        "execution identity fallback, and degraded runtime-anchor fingerprints"
    ]


def execution_identity_metadata_mismatch_messages(
    current_metadata: CheckpointMetadata,
    checkpoint_metadata: CheckpointMetadata,
) -> list[str]:
    """Return mismatch messages for runtime anchors stored directly on metadata."""
    return [
        *optional_mismatch_message(
            current_metadata.effective_config_hash,
            checkpoint_metadata.effective_config_hash,
            label="Effective config hash mismatch",
        ),
        *optional_mismatch_message(
            current_metadata.manifest_id,
            checkpoint_metadata.manifest_id,
            label="Manifest identity mismatch",
        ),
        *optional_mismatch_message(
            current_metadata.contract_ref,
            checkpoint_metadata.contract_ref,
            label="Contract reference mismatch",
        ),
        *optional_mismatch_message(
            current_metadata.contract_version,
            checkpoint_metadata.contract_version,
            label="Contract version mismatch",
        ),
    ]


def optional_mismatch_message(
    current_value: str | None,
    checkpoint_value: str | None,
    *,
    label: str,
) -> list[str]:
    """Return one mismatch message only when both values exist and differ."""
    if not current_value or not checkpoint_value or current_value == checkpoint_value:
        return []
    return [f"{label}: current={current_value}, checkpoint={checkpoint_value}"]


def exact_replay_mismatch_messages(
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


def input_snapshot_mismatch_messages(
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
