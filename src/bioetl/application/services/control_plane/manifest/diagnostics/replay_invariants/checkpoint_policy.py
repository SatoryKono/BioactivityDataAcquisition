"""Checkpoint compatibility policy resolver for manifest diagnostics."""

from __future__ import annotations

from bioetl.domain.control_plane.reproducibility_policy import (
    STRICT_PERSISTENCE_PROFILES,
)


def resolve_applied_checkpoint_compatibility_policy(
    *,
    requested_exact_replay: bool,
    requested_policy: str | None,
    required_persistence_profile: str,
) -> str:
    if requested_exact_replay:
        return "hard_fail"
    if required_persistence_profile in STRICT_PERSISTENCE_PROFILES:
        return "hard_fail" if requested_policy != "hard_fail" else requested_policy
    return requested_policy or "observe"


__all__ = ["resolve_applied_checkpoint_compatibility_policy"]
