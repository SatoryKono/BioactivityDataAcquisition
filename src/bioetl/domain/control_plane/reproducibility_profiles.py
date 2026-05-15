"""Canonical per-family reproducibility profiles for published run-manifest contracts."""

from __future__ import annotations

from dataclasses import asdict

from bioetl.domain.control_plane._reproducibility_profile_builders import (
    _PUBLISHED_SUPPORTED_SOURCE_FAMILIES,
    _REGISTERED_COMPOSITE_FAMILIES,
    _REGISTERED_FAMILY_EXECUTION_CONTEXTS,
    _REGISTERED_SOURCE_FAMILIES,
    _build_composite_reproducibility_family_profile,
    _build_source_reproducibility_family_profile,
    resolve_reproducibility_family,
)
from bioetl.domain.control_plane._reproducibility_profile_types import (
    ReproducibilityExecutionContext,
    ReproducibilityFamilyProfile,
)


def registered_reproducibility_families() -> list[str]:
    """Return every registered reproducibility family in the repository."""
    return list(_REGISTERED_SOURCE_FAMILIES + _REGISTERED_COMPOSITE_FAMILIES)


def registered_reproducibility_family_inventory() -> list[dict[str, object]]:
    """Return certification verdicts for every registered pipeline family."""
    inventory: list[dict[str, object]] = []
    for family, execution_context in sorted(
        _REGISTERED_FAMILY_EXECUTION_CONTEXTS.items(),
        key=lambda item: (str(item[1]), str(item[0])),
    ):
        provider, entity = family.split(".", maxsplit=1)
        inventory.append(
            asdict(
                resolve_reproducibility_family_profile(
                    provider=provider,
                    entity=entity,
                    contract_ref=family,
                    execution_context=execution_context,
                )
            )
        )
    return inventory


def published_supported_reproducibility_families() -> list[str]:
    """Return the authoritative strict exact-replay source-family inventory."""
    return list(_PUBLISHED_SUPPORTED_SOURCE_FAMILIES)


def published_production_reproducibility_families() -> list[str]:
    """Return the authoritative production-family inventory."""
    return registered_reproducibility_families()


def published_supported_boundary_families() -> list[str]:
    """Return all published families that satisfy the supported replay boundary."""
    return [
        str(item["family"])
        for item in registered_reproducibility_family_inventory()
        if bool(item["strict_exact_replay_supported"])
    ]


def published_reproducibility_family_inventory() -> list[dict[str, object]]:
    """Return reproducibility-profile verdicts for every published family."""
    return registered_reproducibility_family_inventory()


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
        "supported_families": published_supported_boundary_families(),
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
        "supported_families": published_supported_boundary_families(),
    }
