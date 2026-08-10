"""Canonical persistence-profile parsing for validation evidence."""

from __future__ import annotations

from bioetl.domain.control_plane import RunManifest
from bioetl.domain.control_plane.reproducibility_policy import (
    DEFAULT_REQUIRED_PERSISTENCE_PROFILE,
    STRICT_PERSISTENCE_PROFILES,
)

DEFAULT_PERSISTENCE_PROFILE = DEFAULT_REQUIRED_PERSISTENCE_PROFILE
PERSISTENCE_PROFILES = (
    "degraded_observable",
    "replay_ready",
    "forensic_grade",
)


def resolve_persistence_profile(manifest: RunManifest) -> tuple[str, bool]:
    """Return normalized profile and whether it belongs to the closed vocabulary."""
    profile = str(
        manifest.launch_context.get("required_persistence_profile")
        or DEFAULT_PERSISTENCE_PROFILE
    ).strip()
    return profile, profile in PERSISTENCE_PROFILES


__all__ = [
    "DEFAULT_PERSISTENCE_PROFILE",
    "PERSISTENCE_PROFILES",
    "STRICT_PERSISTENCE_PROFILES",
    "resolve_persistence_profile",
]
