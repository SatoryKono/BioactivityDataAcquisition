"""Replay-family context assembly for manifest diagnostics."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Literal

from bioetl.domain.control_plane import RunManifest
from bioetl.domain.control_plane.composite_replay import has_composite_replay_bindings
from bioetl.domain.control_plane.execution_context import (
    is_composite_execution_context as _is_composite_execution_context,
)
from bioetl.domain.control_plane.reproducibility_profiles import (
    ReproducibilityFamilyProfile,
    build_replay_family_contract,
    resolve_manifest_reproducibility_profile,
)

from .replay_family_context_build_replay_family_contract_payload import (
    _build_replay_family_contract_payload,
)

is_composite_execution_context = _is_composite_execution_context


@dataclass(frozen=True, slots=True)
class ReplayFamilyContext:
    """Replay-family profile and contract resolved once per manifest."""

    execution_context: Literal["source", "composite"]
    profile: ReproducibilityFamilyProfile
    replay_family_contract: dict[str, object]
    replay_family_contract_payload: dict[str, object]
    exact_replay_support_boundary: str
    strict_exact_replay_supported: bool


def _resolve_replay_family_execution_context(
    manifest: RunManifest,
) -> Literal["source", "composite"]:
    return "composite" if _is_composite_execution_context(manifest) else "source"


def build_replay_family_context(manifest: RunManifest) -> ReplayFamilyContext:
    """Return replay-family profile and contract for one manifest."""
    execution_context = _resolve_replay_family_execution_context(manifest)
    profile = resolve_manifest_reproducibility_profile(manifest)
    replay_family_contract = build_replay_family_contract(
        provider=manifest.provider,
        entity=manifest.entity,
        contract_ref=manifest.code_provenance.contract_ref,
        execution_context=execution_context,
    )
    if execution_context == "composite" and not has_composite_replay_bindings(manifest):
        profile = replace(profile, strict_exact_replay_supported=False)
        replay_family_contract = {
            **replay_family_contract,
            "strict_exact_replay_supported": False,
        }
    return ReplayFamilyContext(
        execution_context=execution_context,
        profile=profile,
        replay_family_contract=replay_family_contract,
        replay_family_contract_payload=_build_replay_family_contract_payload(
            replay_family_contract
        ),
        exact_replay_support_boundary=profile.exact_replay_support_boundary,
        strict_exact_replay_supported=bool(
            replay_family_contract.get("strict_exact_replay_supported", False)
        ),
    )


__all__ = [
    "ReplayFamilyContext",
    "build_replay_family_context",
    "is_composite_execution_context",
]
