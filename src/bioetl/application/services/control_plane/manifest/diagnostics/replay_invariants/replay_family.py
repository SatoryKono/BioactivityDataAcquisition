"""Replay-family compatibility facade for diagnostics."""

from __future__ import annotations

from bioetl.application.services.control_plane.manifest.diagnostics.replay_invariants.replay_family_context import (
    build_replay_family_context,
)
from bioetl.domain.control_plane import RunManifest


def _resolve_reproducibility_profile(manifest: RunManifest) -> object:
    return build_replay_family_context(manifest).profile


def _resolve_replay_family_contract(manifest: RunManifest) -> dict[str, object]:
    return build_replay_family_context(manifest).replay_family_contract


def _resolve_exact_replay_support_boundary(manifest: RunManifest) -> str:
    return build_replay_family_context(manifest).exact_replay_support_boundary


__all__ = [
    "_resolve_exact_replay_support_boundary",
    "_resolve_replay_family_contract",
    "_resolve_reproducibility_profile",
]
