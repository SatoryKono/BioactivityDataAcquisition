"""Persistence policy facade for manifest diagnostics."""

from __future__ import annotations

import sys

from bioetl.application.services.control_plane.manifest.diagnostics.replay_invariants import (
    replay_family_context,
    required_persistence_profile,
)
from bioetl.application.services.control_plane.manifest.diagnostics.replay_invariants.checkpoint_policy import (
    _resolve_applied_checkpoint_compatibility_policy,
    _resolve_requested_checkpoint_compatibility_policy,
)
from bioetl.domain.control_plane import RunManifest
from bioetl.domain.control_plane.execution_context import (
    is_composite_execution_context as _is_composite_execution_context,
)

_resolve_required_persistence_profile = (
    required_persistence_profile._resolve_required_persistence_profile
)


def _resolve_reproducibility_profile(manifest: RunManifest) -> object:
    return replay_family_context.build_replay_family_context(manifest).profile


def _resolve_replay_family_contract(manifest: RunManifest) -> dict[str, object]:
    return replay_family_context.build_replay_family_context(
        manifest
    ).replay_family_contract


def _resolve_exact_replay_support_boundary(manifest: RunManifest) -> str:
    return replay_family_context.build_replay_family_context(
        manifest
    ).exact_replay_support_boundary


persistence_policy = sys.modules[__name__]

__all__ = [
    "_is_composite_execution_context",
    "_resolve_applied_checkpoint_compatibility_policy",
    "_resolve_exact_replay_support_boundary",
    "_resolve_replay_family_contract",
    "_resolve_reproducibility_profile",
    "_resolve_requested_checkpoint_compatibility_policy",
    "_resolve_required_persistence_profile",
    "persistence_policy",
]
