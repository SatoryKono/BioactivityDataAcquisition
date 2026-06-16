"""Required persistence and checkpoint-policy invariants for diagnostics."""

from __future__ import annotations

from bioetl.application.services.control_plane.manifest.diagnostics.nested_mapping import (
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


def _resolve_applied_checkpoint_compatibility_policy(
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


def _resolve_requested_checkpoint_compatibility_policy(
    manifest: RunManifest,
) -> str | None:
    candidates = (
        manifest.launch_context.get("checkpoint_compatibility_policy"),
        lookup_mapping_path(
            manifest.runtime_config,
            "pipeline",
            "control_plane",
            "checkpoint_compatibility_policy",
        ),
        lookup_mapping_path(
            manifest.runtime_config,
            "control_plane",
            "checkpoint_compatibility_policy",
        ),
        lookup_mapping_path(
            manifest.runtime_config,
            "checkpoint_compatibility_policy",
        ),
    )
    for candidate in candidates:
        if isinstance(candidate, str):
            normalized = candidate.strip().lower()
            if normalized in {"observe", "soft_fail", "hard_fail"}:
                return normalized
    return None


__all__ = [
    "_resolve_applied_checkpoint_compatibility_policy",
    "_resolve_requested_checkpoint_compatibility_policy",
    "_resolve_required_persistence_profile",
]
