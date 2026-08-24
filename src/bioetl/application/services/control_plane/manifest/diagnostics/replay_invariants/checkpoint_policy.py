"""Checkpoint compatibility policy resolver for manifest diagnostics."""

from __future__ import annotations

from importlib import import_module

from bioetl.domain.control_plane import RunManifest
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


def _resolve_requested_checkpoint_compatibility_policy(
    manifest: RunManifest,
) -> str | None:
    lookup_mapping_path = import_module(
        "bioetl.application.services.control_plane.manifest.diagnostics.nested_mapping"
    ).lookup_mapping_path
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
    )
    for candidate in candidates:
        if isinstance(candidate, str):
            normalized = candidate.strip().lower()
            if normalized in {"observe", "soft_fail", "hard_fail"}:
                return normalized
    return None


__all__ = [
    "_resolve_requested_checkpoint_compatibility_policy",
    "resolve_applied_checkpoint_compatibility_policy",
]
