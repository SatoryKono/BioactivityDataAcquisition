"""Replay-family context assembly for manifest diagnostics."""

from __future__ import annotations

from dataclasses import dataclass
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


def _build_replay_family_contract_payload(
    replay_family_contract: dict[str, object],
) -> dict[str, object]:
    """Return the bounded replay-family contract projection payload."""
    return {
        "replay_support_state": replay_family_contract.get("support_state"),
        "post_capture_replayable_parent_supported": replay_family_contract.get(
            "post_capture_replayable_parent_supported"
        ),
        "post_capture_replayable_parent_boundary": replay_family_contract.get(
            "post_capture_replayable_parent_boundary"
        ),
        "historical_live_run_upgrade_policy": replay_family_contract.get(
            "historical_live_run_upgrade_policy"
        ),
        "historical_live_run_upgrade_boundary": replay_family_contract.get(
            "historical_live_run_upgrade_boundary"
        ),
        "historical_live_run_upgrade_reason": replay_family_contract.get(
            "historical_live_run_upgrade_reason"
        ),
        "broader_historical_exact_replay_policy": replay_family_contract.get(
            "broader_historical_exact_replay_policy"
        ),
        "broader_historical_exact_replay_boundary": replay_family_contract.get(
            "broader_historical_exact_replay_boundary"
        ),
        "broader_historical_exact_replay_reason": replay_family_contract.get(
            "broader_historical_exact_replay_reason"
        ),
    }


def build_replay_family_context(manifest: RunManifest) -> ReplayFamilyContext:
    """Return replay-family profile and contract for one manifest."""
    execution_context = _resolve_replay_family_execution_context(manifest)
    profile = resolve_reproducibility_family_profile(
        provider=manifest.provider,
        entity=manifest.entity,
        contract_ref=manifest.code_provenance.contract_ref,
        execution_context=execution_context,
    )
    replay_family_contract = build_replay_family_contract(
        provider=manifest.provider,
        entity=manifest.entity,
        contract_ref=manifest.code_provenance.contract_ref,
        execution_context=execution_context,
    )
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
