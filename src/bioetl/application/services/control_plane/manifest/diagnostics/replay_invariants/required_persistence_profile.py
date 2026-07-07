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


__all__ = ["_resolve_required_persistence_profile"]
