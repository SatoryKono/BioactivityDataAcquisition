"""Pure runtime helpers for checkpoint manager compatibility handling."""

from __future__ import annotations

from typing import Literal

from bioetl.domain.ports import LoggerPort
from bioetl.domain.types.checkpoint_metadata import CheckpointMetadata

CheckpointCompatibilityPolicy = Literal["observe", "soft_fail", "hard_fail"]


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
        run_context=metadata.run_context
        if metadata.run_context is not None
        else identity.run_context,
    )


def handle_incompatible_checkpoint(
    *,
    logger: LoggerPort,
    pipeline_name: str,
    compatibility_policy: CheckpointCompatibilityPolicy,
    checkpoint_metadata: CheckpointMetadata,
    messages: list[str],
) -> CheckpointMetadata | None:
    """Apply configured policy to an incompatible checkpoint."""
    payload = {
        "pipeline": pipeline_name,
        "compatibility_policy": compatibility_policy,
        "messages": messages,
        "checkpoint_metadata": checkpoint_metadata.to_dict(),
    }
    if compatibility_policy == "observe":
        logger.warning(
            "Checkpoint compatibility mismatch observed; resume continues.",
            extra=payload,
        )
        return checkpoint_metadata
    if compatibility_policy == "soft_fail":
        logger.warning(
            "Checkpoint compatibility mismatch; resume blocked by soft_fail policy.",
            extra=payload,
        )
        return None
    raise ValueError(
        "Checkpoint compatibility mismatch and hard_fail policy is enabled: "
        + "; ".join(messages)
    )


__all__ = [
    "CheckpointCompatibilityPolicy",
    "enrich_metadata_with_execution_identity",
    "handle_incompatible_checkpoint",
    "resolve_current_metadata",
    "validate_compatibility_policy",
]
