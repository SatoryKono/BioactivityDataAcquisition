"""Data-root policy validation for strict runner control-plane modes."""

from __future__ import annotations

from bioetl.composition.runtime_builders._run_manifest_data_roots import (
    is_explicit_data_root_configured,
    resolve_data_root_mode,
)
from bioetl.domain.control_plane.reproducibility_policy import (
    STRICT_PERSISTENCE_PROFILES,
    normalize_required_persistence_profile,
)
from bioetl.infrastructure.config.settings_api import Settings


def validate_strict_data_root_policy(
    *,
    settings: Settings,
    required_profile: object,
    exact_replay: bool = False,
) -> None:
    """Fail closed when strict reproducibility relies on fallback data roots."""
    profile = normalize_required_persistence_profile(required_profile)
    if not (exact_replay or profile in STRICT_PERSISTENCE_PROFILES):
        return
    if is_explicit_data_root_configured(settings):
        return
    mode = resolve_data_root_mode(settings)
    raise RuntimeError(
        "Strict reproducibility contexts require an explicit settings.data_dir; "
        f"resolved fallback data root mode '{mode}' is not allowed for required "
        f"persistence profile '{profile}'"
    )
