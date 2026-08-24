"""Persistence policy facade for manifest diagnostics."""

from __future__ import annotations

from bioetl.application.services.control_plane.manifest.diagnostics.replay_invariants import (
    checkpoint_policy,
    replay_family,
    required_persistence_profile,
)
from bioetl.domain.control_plane.execution_context import (
    is_composite_execution_context as _is_composite_execution_context,
)

_resolve_applied_checkpoint_compatibility_policy = (
    checkpoint_policy.resolve_applied_checkpoint_compatibility_policy
)
_resolve_exact_replay_support_boundary = (
    replay_family._resolve_exact_replay_support_boundary
)
_resolve_replay_family_contract = replay_family._resolve_replay_family_contract
_resolve_reproducibility_profile = replay_family._resolve_reproducibility_profile
_resolve_requested_checkpoint_compatibility_policy = (
    required_persistence_profile._resolve_requested_checkpoint_compatibility_policy
)
_resolve_required_persistence_profile = (
    required_persistence_profile._resolve_required_persistence_profile
)

__all__ = [
    "_is_composite_execution_context",
    "_resolve_applied_checkpoint_compatibility_policy",
    "_resolve_exact_replay_support_boundary",
    "_resolve_replay_family_contract",
    "_resolve_reproducibility_profile",
    "_resolve_requested_checkpoint_compatibility_policy",
    "_resolve_required_persistence_profile",
]
