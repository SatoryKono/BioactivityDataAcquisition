"""Canonical per-family reproducibility profiles for published run-manifest contracts."""

from __future__ import annotations

from dataclasses import asdict

from bioetl.domain.control_plane._reproducibility_profile_builders import (
    _PUBLISHED_COMPOSITE_FAMILIES,
    _PUBLISHED_SOURCE_FAMILIES,
    _PUBLISHED_SUPPORTED_SOURCE_FAMILIES,
    _build_composite_reproducibility_family_profile,
    _build_source_reproducibility_family_profile,
    resolve_reproducibility_family,
)
from bioetl.domain.control_plane._reproducibility_profile_types import (
    ReproducibilityExecutionContext,
    ReproducibilityFamilyProfile,
)


def published_supported_reproducibility_families() -> list[str]:
    """Return the authoritative published source-family inventory."""
    return list(_PUBLISHED_SUPPORTED_SOURCE_FAMILIES)


def published_production_reproducibility_families() -> list[str]:
    """Return the authoritative production-family inventory."""
    return list(_PUBLISHED_SOURCE_FAMILIES + _PUBLISHED_COMPOSITE_FAMILIES)


def published_reproducibility_family_inventory() -> list[dict[str, object]]:
    """Return reproducibility-profile verdicts for every published family."""
    inventory: list[dict[str, object]] = []
    for family in _PUBLISHED_SOURCE_FAMILIES:
        provider, entity = family.split(".", maxsplit=1)
        inventory.append(
            asdict(
                resolve_reproducibility_family_profile(
                    provider=provider,
                    entity=entity,
                    contract_ref=family,
                    execution_context="source",
                )
            )
        )
    for family in _PUBLISHED_COMPOSITE_FAMILIES:
        provider, entity = family.split(".", maxsplit=1)
        inventory.append(
            asdict(
                resolve_reproducibility_family_profile(
                    provider=provider,
                    entity=entity,
                    contract_ref=family,
                    execution_context="composite",
                )
            )
        )
    return inventory


def resolve_reproducibility_family_profile(
    *,
    provider: object,
    entity: object,
    contract_ref: object,
    execution_context: ReproducibilityExecutionContext,
) -> ReproducibilityFamilyProfile:
    """Resolve the authoritative reproducibility profile for one run family."""
    family = resolve_reproducibility_family(
        provider=provider,
        entity=entity,
        contract_ref=contract_ref,
    )
    if execution_context == "composite":
        return _build_composite_reproducibility_family_profile(
            family=family,
            execution_context=execution_context,
        )
    return _build_source_reproducibility_family_profile(
        family=family,
        execution_context=execution_context,
    )


def build_lineage_closure_boundary(
    *,
    provider: object,
    entity: object,
    contract_ref: object,
    execution_context: ReproducibilityExecutionContext,
) -> dict[str, object]:
    """Build the published lineage-closure boundary for one manifested run."""
    profile = resolve_reproducibility_family_profile(
        provider=provider,
        entity=entity,
        contract_ref=contract_ref,
        execution_context=execution_context,
    )
    return {
        "family": profile.family,
        "support_scope": profile.support_scope,
        "supported": profile.lineage_closure_supported,
        "reason": profile.reason,
        "supported_families": published_supported_reproducibility_families(),
    }


def build_replay_family_contract(
    *,
    provider: object,
    entity: object,
    contract_ref: object,
    execution_context: ReproducibilityExecutionContext,
) -> dict[str, object]:
    """Build the published per-family exact-replay contract for one manifested run."""
    profile = resolve_reproducibility_family_profile(
        provider=provider,
        entity=entity,
        contract_ref=contract_ref,
        execution_context=execution_context,
    )
    return {
        "family": profile.family,
        "execution_context": profile.execution_context,
        "contract": profile.replay_family_contract,
        "default_required_persistence_profile": (
            profile.default_required_persistence_profile
        ),
        "support_state": profile.support_state,
        "strict_exact_replay_supported": profile.strict_exact_replay_supported,
        "strict_replay_runtime_verdict": profile.strict_replay_runtime_verdict,
        "exact_replay_support_boundary": profile.exact_replay_support_boundary,
        "post_capture_replayable_parent_supported": (
            profile.post_capture_replayable_parent_supported
        ),
        "post_capture_replayable_parent_boundary": (
            profile.post_capture_replayable_parent_boundary
        ),
        "post_capture_replayable_parent_reason": (
            profile.post_capture_replayable_parent_reason
        ),
        "historical_live_run_upgrade_policy": (
            profile.historical_live_run_upgrade_policy
        ),
        "historical_live_run_upgrade_boundary": (
            profile.historical_live_run_upgrade_boundary
        ),
        "historical_live_run_upgrade_reason": (
            profile.historical_live_run_upgrade_reason
        ),
        "broader_historical_exact_replay_policy": (
            profile.broader_historical_exact_replay_policy
        ),
        "broader_historical_exact_replay_boundary": (
            profile.broader_historical_exact_replay_boundary
        ),
        "broader_historical_exact_replay_reason": (
            profile.broader_historical_exact_replay_reason
        ),
        "support_scope": profile.support_scope,
        "reason": profile.reason,
        "supported_families": published_supported_reproducibility_families(),
    }
