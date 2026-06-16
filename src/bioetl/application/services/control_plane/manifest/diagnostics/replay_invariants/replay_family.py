"""Replay-family profile and contract invariants for diagnostics."""

from __future__ import annotations

from typing import Literal

from bioetl.domain.control_plane import RunManifest
from bioetl.domain.control_plane.execution_context import (
    is_composite_execution_context as _is_composite_execution_context,
)
from bioetl.domain.control_plane.reproducibility_profiles import (
    ReproducibilityFamilyProfile,
    build_replay_family_contract,
    resolve_reproducibility_family_profile,
)


def _resolve_reproducibility_profile(
    manifest: RunManifest,
) -> ReproducibilityFamilyProfile:
    execution_context: Literal["source", "composite"] = (
        "composite" if _is_composite_execution_context(manifest) else "source"
    )
    return resolve_reproducibility_family_profile(
        provider=manifest.provider,
        entity=manifest.entity,
        contract_ref=manifest.code_provenance.contract_ref,
        execution_context=execution_context,
    )


def _resolve_replay_family_contract(manifest: RunManifest) -> dict[str, object]:
    execution_context: Literal["source", "composite"] = (
        "composite" if _is_composite_execution_context(manifest) else "source"
    )
    return build_replay_family_contract(
        provider=manifest.provider,
        entity=manifest.entity,
        contract_ref=manifest.code_provenance.contract_ref,
        execution_context=execution_context,
    )


def _resolve_exact_replay_support_boundary(manifest: RunManifest) -> str:
    return _resolve_reproducibility_profile(manifest).exact_replay_support_boundary


__all__ = [
    "_resolve_exact_replay_support_boundary",
    "_resolve_replay_family_contract",
    "_resolve_reproducibility_profile",
]
