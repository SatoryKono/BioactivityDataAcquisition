"""Required persistence profile resolver for manifest diagnostics."""

from __future__ import annotations

from bioetl.application.services.control_plane.manifest.diagnostics.replay_invariants.nested_mapping import (
    lookup_mapping_path,
)
from bioetl.domain.control_plane import RunManifest
from bioetl.domain.control_plane.reproducibility_policy import (
    DEFAULT_REQUIRED_PERSISTENCE_PROFILE,
    STRICT_PERSISTENCE_PROFILES,
    normalize_required_persistence_profile,
)


def _resolve_required_persistence_profile(manifest: RunManifest) -> str:
    candidates = (
        manifest.launch_context.get("required_persistence_profile"),
        lookup_mapping_path(
            manifest.runtime_config,
            "pipeline",
            "control_plane",
            "required_persistence_profile",
        ),
        lookup_mapping_path(
            manifest.runtime_config,
            "control_plane",
            "required_persistence_profile",
        ),
        lookup_mapping_path(
            manifest.runtime_config,
            "required_persistence_profile",
        ),
    )
    for candidate in candidates:
        if isinstance(candidate, str):
            normalized = normalize_required_persistence_profile(candidate).lower()
            if normalized in {
                DEFAULT_REQUIRED_PERSISTENCE_PROFILE,
                *STRICT_PERSISTENCE_PROFILES,
            }:
                return normalized
    return DEFAULT_REQUIRED_PERSISTENCE_PROFILE


def _resolve_requested_checkpoint_compatibility_policy(
    manifest: RunManifest,
) -> str | None:
    allowed = {"observe", "soft_fail", "hard_fail"}
    launch_policy = manifest.launch_context.get("checkpoint_compatibility_policy")
    if isinstance(launch_policy, str) and launch_policy.strip().lower() in allowed:
        return launch_policy.strip().lower()
    runtime_paths = (
        ("pipeline", "control_plane", "checkpoint_compatibility_policy"),
        ("control_plane", "checkpoint_compatibility_policy"),
    )
    for path in runtime_paths:
        value = lookup_mapping_path(manifest.runtime_config, *path)
        if isinstance(value, str) and value.strip().lower() in allowed:
            return value.strip().lower()
    return None


__all__ = ["_resolve_requested_checkpoint_compatibility_policy", "_resolve_required_persistence_profile"]
