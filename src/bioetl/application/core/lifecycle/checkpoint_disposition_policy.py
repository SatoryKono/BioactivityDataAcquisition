"""Checkpoint resume compatibility disposition policy."""

from __future__ import annotations

from bioetl.application.core.lifecycle.checkpoint_runtime_types import (
    CheckpointCompatibilityDisposition,
    CheckpointCompatibilityPolicy,
    CheckpointMissingContextDisposition,
)
from bioetl.domain.control_plane.reproducibility_policy import (
    STRICT_PERSISTENCE_PROFILES,
)
from bioetl.domain.types.checkpoint_metadata import CheckpointMetadata


def strict_checkpoint_resume_required(
    *,
    current_metadata: CheckpointMetadata | None,
    checkpoint_metadata: CheckpointMetadata,
) -> bool:
    """Return whether resume must remain fail-closed for strict replay profiles."""
    required_profiles = {
        str(profile or "").strip().lower()
        for profile in (
            None
            if current_metadata is None
            else current_metadata.required_persistence_profile,
            checkpoint_metadata.required_persistence_profile,
        )
        if str(profile or "").strip()
    }
    if required_profiles.intersection(STRICT_PERSISTENCE_PROFILES):
        return True
    return bool(
        checkpoint_metadata.exact_replay
        or (current_metadata.exact_replay if current_metadata is not None else False)
    )


def resolve_incompatible_checkpoint_disposition(
    *,
    compatibility_policy: CheckpointCompatibilityPolicy,
    execution_identity_compatible: bool,
    identity_continuity_proven: bool = True,
    strict_persistence_required: bool = False,
) -> CheckpointCompatibilityDisposition:
    """Return the bounded incompatibility disposition for telemetry and logging."""
    if compatibility_policy == "observe":
        if (
            strict_persistence_required
            or not identity_continuity_proven
            or not execution_identity_compatible
        ):
            return "observe_blocked_identity"
        return "observe_loaded_degraded"
    if compatibility_policy == "soft_fail":
        return "soft_fail_blocked"
    return "hard_fail_raised"


def resolve_missing_compatibility_context_disposition(
    *,
    compatibility_policy: CheckpointCompatibilityPolicy,
) -> CheckpointMissingContextDisposition:
    """Return bounded disposition for missing resume compatibility context."""
    return "missing_context_hard_fail_raised"


__all__ = [
    "resolve_incompatible_checkpoint_disposition",
    "resolve_missing_compatibility_context_disposition",
    "strict_checkpoint_resume_required",
]
