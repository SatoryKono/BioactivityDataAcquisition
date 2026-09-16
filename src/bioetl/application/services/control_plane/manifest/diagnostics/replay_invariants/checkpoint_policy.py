"""Checkpoint compatibility policy resolver for manifest diagnostics."""

from __future__ import annotations

from bioetl.domain.control_plane import RunManifest
from bioetl.domain.control_plane.reproducibility_policy import (
    STRICT_PERSISTENCE_PROFILES,
)
from bioetl.domain.normalization import lookup_mapping_path


def _resolve_requested_checkpoint_compatibility_policy(
    manifest: RunManifest,
) -> str | None:
    allowed = {"observe", "soft_fail", "hard_fail"}
    launch_policy = manifest.launch_context.get("checkpoint_compatibility_policy")
    if isinstance(launch_policy, str) and launch_policy.strip().lower() in allowed:
        return launch_policy.strip().lower()
    for path in (
        ("pipeline", "control_plane", "checkpoint_compatibility_policy"),
        ("control_plane", "checkpoint_compatibility_policy"),
    ):
        value = lookup_mapping_path(manifest.runtime_config, *path)
        if isinstance(value, str) and value.strip().lower() in allowed:
            return value.strip().lower()
    return None


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


__all__ = [
    "_resolve_requested_checkpoint_compatibility_policy",
    "resolve_applied_checkpoint_compatibility_policy",
]
