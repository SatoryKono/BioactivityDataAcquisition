"""Pure runtime helpers for checkpoint manager compatibility handling."""

from __future__ import annotations

from bioetl.application.core.lifecycle.checkpoint_disposition_policy import (
    resolve_incompatible_checkpoint_disposition,
    resolve_missing_compatibility_context_disposition,
)
from bioetl.application.core.lifecycle.checkpoint_disposition_policy import (
    strict_checkpoint_resume_required as strict_checkpoint_resume_required,
)
from bioetl.application.core.lifecycle.checkpoint_identity_overrides import (
    checkpoint_identity_payload,
    enrich_metadata_with_execution_identity,
)
from bioetl.application.core.lifecycle.checkpoint_runtime_types import (
    CheckpointCompatibilityDisposition,
    CheckpointCompatibilityPolicy,
    CheckpointMissingContextDisposition,
)
from bioetl.domain.ports import LoggerPort
from bioetl.domain.types.checkpoint_metadata import CheckpointMetadata

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

def missing_compatibility_context_messages(
    *,
    current_metadata: CheckpointMetadata | None,
    service_available: bool,
) -> list[str]:
    """Return deterministic reasons why checkpoint compatibility cannot run."""
    messages: list[str] = []
    if current_metadata is None:
        messages.append("Missing current checkpoint metadata for resume validation")
    if not service_available:
        messages.append(
            "Missing checkpoint compatibility service for resume validation"
        )
    return messages or ["Missing checkpoint compatibility context"]

def handle_incompatible_checkpoint(
    *,
    logger: LoggerPort,
    pipeline_name: str,
    compatibility_policy: CheckpointCompatibilityPolicy,
    current_metadata: CheckpointMetadata | None,
    checkpoint_metadata: CheckpointMetadata,
    execution_identity_compatible: bool,
    identity_continuity_proven: bool,
    messages: list[str],
) -> CheckpointMetadata | None:
    """Apply configured policy to an incompatible checkpoint."""
    disposition = resolve_incompatible_checkpoint_disposition(
        compatibility_policy=compatibility_policy,
        execution_identity_compatible=execution_identity_compatible,
        identity_continuity_proven=identity_continuity_proven,
        strict_persistence_required=strict_checkpoint_resume_required(
            current_metadata=current_metadata,
            checkpoint_metadata=checkpoint_metadata,
        ),
    )
    forced_resume_rejection = disposition == "observe_blocked_identity"
    degraded_resume_loaded = disposition == "observe_loaded_degraded"
    payload = {
        "pipeline": pipeline_name,
        "compatibility_policy": compatibility_policy,
        "compatibility_disposition": disposition,
        "resume_rejected": not degraded_resume_loaded or forced_resume_rejection,
        "execution_identity_compatible": execution_identity_compatible,
        "identity_continuity_proven": identity_continuity_proven,
        "identity_mismatch_forces_rejection": forced_resume_rejection,
        "messages": messages,
        "checkpoint_metadata": checkpoint_metadata.to_dict(),
        "current_identity": checkpoint_identity_payload(current_metadata),
        "checkpoint_identity": checkpoint_identity_payload(checkpoint_metadata),
    }
    if disposition == "observe_blocked_identity":
        logger.warning(
            "Checkpoint execution identity mismatch observed; resume blocked "
            "despite observe policy (resume blocked despite degraded observe policy).",
            **payload,
        )
        return None
    if disposition == "observe_loaded_degraded":
        logger.warning(
            "Checkpoint non-identity compatibility mismatch observed; resume continues.",
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

def handle_missing_compatibility_context(
    *,
    logger: LoggerPort,
    pipeline_name: str,
    compatibility_policy: CheckpointCompatibilityPolicy,
    current_metadata: CheckpointMetadata | None,
    checkpoint_metadata: CheckpointMetadata,
    service_available: bool,
) -> CheckpointMetadata | None:
    """Apply configured policy when resume compatibility cannot be validated."""
    disposition = resolve_missing_compatibility_context_disposition(
        compatibility_policy=compatibility_policy,
    )
    messages = missing_compatibility_context_messages(
        current_metadata=current_metadata,
        service_available=service_available,
    )
    payload = {
        "pipeline": pipeline_name,
        "compatibility_policy": compatibility_policy,
        "compatibility_disposition": disposition,
        "resume_rejected": True,
        "messages": messages,
        "checkpoint_metadata": checkpoint_metadata.to_dict(),
        "current_identity": checkpoint_identity_payload(current_metadata),
        "checkpoint_identity": checkpoint_identity_payload(checkpoint_metadata),
        "compatibility_service_available": service_available,
    }
    logger.warning(
        "Checkpoint compatibility context missing; resume rejected.",
        **payload,
    )
    raise ValueError(
        "Checkpoint resume requires compatibility context and fails closed when "
        "that context is incomplete: " + "; ".join(messages)
    )

__all__ = [
    "CheckpointCompatibilityDisposition",
    "CheckpointCompatibilityPolicy",
    "CheckpointMissingContextDisposition",
    "enrich_metadata_with_execution_identity",
    "handle_incompatible_checkpoint",
    "handle_missing_compatibility_context",
    "missing_compatibility_context_messages",
    "resolve_current_metadata",
    "resolve_incompatible_checkpoint_disposition",
    "resolve_missing_compatibility_context_disposition",
    "validate_compatibility_policy",
]
