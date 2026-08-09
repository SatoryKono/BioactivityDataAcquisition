"""Canonical persistence-profile parsing for validation evidence."""

from __future__ import annotations

from bioetl.domain.control_plane import RunManifest

DEFAULT_PERSISTENCE_PROFILE = "degraded_observable"
PERSISTENCE_PROFILES = (
    DEFAULT_PERSISTENCE_PROFILE,
    "replay_ready",
    "forensic_grade",
)
STRICT_PERSISTENCE_PROFILES = frozenset({"replay_ready", "forensic_grade"})


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
