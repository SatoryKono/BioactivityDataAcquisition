"""Pure runtime helpers for checkpoint manager compatibility handling."""

from __future__ import annotations

from typing import Literal

from bioetl.domain.ports import LoggerPort
from bioetl.domain.types.checkpoint_metadata import CheckpointMetadata

CheckpointCompatibilityPolicy = Literal["observe", "soft_fail", "hard_fail"]
CheckpointCompatibilityDisposition = Literal[
    "observe_blocked_identity",
    "observe_loaded_degraded",
    "soft_fail_blocked",
    "hard_fail_raised",
]


def validate_compatibility_policy(
    policy: CheckpointCompatibilityPolicy,
) -> CheckpointCompatibilityPolicy:
    """Validate supported checkpoint compatibility handling modes."""
    allowed: tuple[CheckpointCompatibilityPolicy, ...] = (
        "observe",
        "soft_fail",
        "hard_fail",
    )
    if policy not in allowed:
        raise ValueError(
            f"Unsupported checkpoint compatibility policy: {policy!r}. "
            f"Expected one of {allowed}."
        )
    return policy


def resolve_current_metadata(
    current_metadata: CheckpointMetadata | None,
    *,
    default_metadata: CheckpointMetadata | None,
) -> CheckpointMetadata | None:
    """Return explicit metadata when provided, otherwise fall back to default."""
    return current_metadata if current_metadata is not None else default_metadata


def enrich_metadata_with_execution_identity(
    metadata: CheckpointMetadata,
    *,
    identity: CheckpointMetadata | None,
) -> CheckpointMetadata:
    """Fill checkpoint metadata gaps from current execution identity."""
    if identity is None:
        return metadata
    return CheckpointMetadata(
        records_processed=metadata.records_processed,
        dq_contract_compatibility_hash=(
            metadata.dq_contract_compatibility_hash
            if metadata.dq_contract_compatibility_hash is not None
            else identity.dq_contract_compatibility_hash
        ),
        dq_policy_hash=(
            metadata.dq_policy_hash
            if metadata.dq_policy_hash is not None
            else identity.dq_policy_hash
        ),
        dq_rule_bundle_version=(
            metadata.dq_rule_bundle_version
            if metadata.dq_rule_bundle_version is not None
            else identity.dq_rule_bundle_version
        ),
        pipeline_version=(
            metadata.pipeline_version
            if metadata.pipeline_version is not None
            else identity.pipeline_version
        ),
        effective_config_hash=(
            metadata.effective_config_hash
            if metadata.effective_config_hash is not None
            else identity.effective_config_hash
        ),
        effective_config_artifact_id=(
            metadata.effective_config_artifact_id
            if metadata.effective_config_artifact_id is not None
            else identity.effective_config_artifact_id
        ),
        execution_fingerprint=(
            metadata.execution_fingerprint
            if metadata.execution_fingerprint is not None
            else identity.execution_fingerprint
        ),
        composite_run_identity=(
            metadata.composite_run_identity
            if metadata.composite_run_identity is not None
            else identity.composite_run_identity
        ),
        manifest_id=(
            metadata.manifest_id
            if metadata.manifest_id is not None
            else identity.manifest_id
        ),
        contract_ref=(
            metadata.contract_ref
            if metadata.contract_ref is not None
            else identity.contract_ref
        ),
        contract_version=(
            metadata.contract_version
            if metadata.contract_version is not None
            else identity.contract_version
        ),
        exact_replay=(
            metadata.exact_replay
            if metadata.exact_replay is not None
            else identity.exact_replay
        ),
        input_snapshot_ids=(
            metadata.input_snapshot_ids
            if metadata.input_snapshot_ids
            else identity.input_snapshot_ids
        ),
        run_context=metadata.run_context
        if metadata.run_context is not None
        else identity.run_context,
    )


def handle_incompatible_checkpoint(
    *,
    logger: LoggerPort,
    pipeline_name: str,
    compatibility_policy: CheckpointCompatibilityPolicy,
    current_metadata: CheckpointMetadata | None,
    checkpoint_metadata: CheckpointMetadata,
    execution_identity_compatible: bool,
    messages: list[str],
) -> CheckpointMetadata | None:
    """Apply configured policy to an incompatible checkpoint."""
    disposition = resolve_incompatible_checkpoint_disposition(
        compatibility_policy=compatibility_policy,
        execution_identity_compatible=execution_identity_compatible,
    )
    forced_resume_rejection = disposition == "observe_blocked_identity"
    payload = {
        "pipeline": pipeline_name,
        "compatibility_policy": compatibility_policy,
        "compatibility_disposition": disposition,
        "resume_rejected": compatibility_policy != "observe"
        or forced_resume_rejection,
        "execution_identity_compatible": execution_identity_compatible,
        "identity_mismatch_forces_rejection": forced_resume_rejection,
        "messages": messages,
        "checkpoint_metadata": checkpoint_metadata.to_dict(),
        "current_identity": _checkpoint_identity_payload(current_metadata),
        "checkpoint_identity": _checkpoint_identity_payload(checkpoint_metadata),
    }
    if disposition == "observe_blocked_identity":
        logger.warning(
            "Checkpoint execution identity mismatch observed; resume blocked "
            "despite observe policy.",
            **payload,
        )
        return None
    if disposition == "observe_loaded_degraded":
        logger.warning(
            "Checkpoint compatibility mismatch observed; resume continues.",
            **payload,
        )
        return checkpoint_metadata
    if disposition == "soft_fail_blocked":
        logger.warning(
            "Checkpoint compatibility mismatch; resume blocked by soft_fail policy.",
            **payload,
        )
        return None
    raise ValueError(
        "Checkpoint compatibility mismatch and hard_fail policy is enabled: "
        + "; ".join(messages)
    )


def _checkpoint_identity_payload(
    metadata: CheckpointMetadata | None,
) -> dict[str, object | None]:
    """Return the compact identity anchors most useful for resume forensics."""
    if metadata is None:
        return {
            "composite_run_identity": None,
            "execution_fingerprint": None,
            "manifest_id": None,
            "effective_config_hash": None,
            "contract_ref": None,
            "contract_version": None,
            "exact_replay": None,
            "input_snapshot_ids": [],
        }
    return {
        "composite_run_identity": metadata.composite_run_identity,
        "execution_fingerprint": metadata.execution_fingerprint,
        "manifest_id": metadata.manifest_id,
        "effective_config_hash": metadata.effective_config_hash,
        "contract_ref": metadata.contract_ref,
        "contract_version": metadata.contract_version,
        "exact_replay": metadata.exact_replay,
        "input_snapshot_ids": list(metadata.input_snapshot_ids),
    }


def resolve_incompatible_checkpoint_disposition(
    *,
    compatibility_policy: CheckpointCompatibilityPolicy,
    execution_identity_compatible: bool,
) -> CheckpointCompatibilityDisposition:
    """Return the bounded incompatibility disposition for telemetry and logging."""
    if compatibility_policy == "observe":
        if execution_identity_compatible:
            return "observe_loaded_degraded"
        return "observe_blocked_identity"
    if compatibility_policy == "soft_fail":
        return "soft_fail_blocked"
    return "hard_fail_raised"


__all__ = [
    "CheckpointCompatibilityDisposition",
    "CheckpointCompatibilityPolicy",
    "enrich_metadata_with_execution_identity",
    "handle_incompatible_checkpoint",
    "resolve_current_metadata",
    "resolve_incompatible_checkpoint_disposition",
    "validate_compatibility_policy",
]
