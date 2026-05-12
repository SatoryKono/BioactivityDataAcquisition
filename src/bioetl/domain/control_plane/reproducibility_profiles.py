"""Canonical per-family reproducibility profiles for published run-manifest contracts."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal

_PUBLISHED_SOURCE_FAMILIES = (
    "chembl.activity",
    "chembl.assay",
    "chembl.assay_parameters",
    "chembl.cell_line",
    "chembl.compound_record",
    "chembl.molecule",
    "chembl.protein_class",
    "chembl.publication",
    "chembl.publication_similarity",
    "chembl.publication_term",
    "chembl.subcellular_fraction",
    "chembl.target",
    "chembl.target_component",
    "chembl.tissue",
    "crossref.publication",
    "openalex.publication",
    "pubchem.compound",
    "pubmed.publication",
    "semanticscholar.publication",
    "uniprot.idmapping",
    "uniprot.protein",
)
_PUBLISHED_COMPOSITE_FAMILIES = (
    "composite.activity",
    "composite.assay",
    "composite.molecule",
    "composite.publication",
    "composite.target",
)
_PUBLISHED_SUPPORTED_SOURCE_FAMILIES = _PUBLISHED_SOURCE_FAMILIES

ReproducibilityExecutionContext = Literal["source", "composite"]
ReplayFamilyContractName = Literal[
    "snapshot_backed_exact_replay",
    "composite_snapshot_backed_exact_replay",
    "rebuild_only",
]
ReplaySupportState = Literal[
    "exact_replay_supported",
    "rebuild_only",
    "debug_only",
]
StrictReplayRuntimeVerdict = Literal[
    "allowed_with_snapshot_backed_source_refs",
    "requires_full_composite_snapshot_envelope",
    "blocked_outside_supported_boundary",
]


@dataclass(frozen=True, slots=True)
class ReproducibilityFamilyProfile:
    """Published per-family reproducibility profile."""

    family: str | None
    execution_context: ReproducibilityExecutionContext
    lineage_closure_supported: bool
    strict_exact_replay_supported: bool
    support_state: ReplaySupportState
    strict_replay_runtime_verdict: StrictReplayRuntimeVerdict
    exact_replay_support_boundary: str
    post_capture_replayable_parent_supported: bool
    post_capture_replayable_parent_boundary: str | None
    post_capture_replayable_parent_reason: str
    historical_live_run_upgrade_policy: str
    historical_live_run_upgrade_boundary: str | None
    historical_live_run_upgrade_reason: str
    broader_historical_exact_replay_policy: str
    broader_historical_exact_replay_boundary: str | None
    broader_historical_exact_replay_reason: str
    replay_family_contract: ReplayFamilyContractName
    default_required_persistence_profile: str
    support_scope: str
    reason: str


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


def _normalized_text(value: object) -> str:
    """Return stripped text for one manifested context value."""
    return str(value or "").strip()


def resolve_reproducibility_family(
    *,
    provider: object,
    entity: object,
    contract_ref: object,
) -> str | None:
    """Resolve the canonical family anchor from manifested provider/entity context."""
    contract_text = _normalized_text(contract_ref)
    if contract_text:
        return contract_text
    family_parts = [
        part for part in (_normalized_text(provider), _normalized_text(entity)) if part
    ]
    if not family_parts:
        return None
    return ".".join(family_parts)


def _resolve_source_profile_reason(*, supported: bool, published: bool) -> str:
    if supported:
        return "family_within_supported_boundary"
    if published:
        return "family_within_published_inventory_but_outside_supported_boundary"
    return "family_outside_published_inventory"


def _build_composite_reproducibility_family_profile(
    *,
    family: str | None,
    execution_context: ReproducibilityExecutionContext,
) -> ReproducibilityFamilyProfile:
    return ReproducibilityFamilyProfile(
        family=family,
        execution_context=execution_context,
        lineage_closure_supported=False,
        strict_exact_replay_supported=True,
        support_state="exact_replay_supported",
        strict_replay_runtime_verdict="requires_full_composite_snapshot_envelope",
        exact_replay_support_boundary="composite_snapshot_backed_input_envelope",
        post_capture_replayable_parent_supported=False,
        post_capture_replayable_parent_boundary=None,
        post_capture_replayable_parent_reason=(
            "composite_launches_do_not_use_post_capture_parent_promotion"
        ),
        historical_live_run_upgrade_policy="not_applicable",
        historical_live_run_upgrade_boundary=None,
        historical_live_run_upgrade_reason=(
            "composite_launches_do_not_define_historical_live_source_upgrade_path"
        ),
        broader_historical_exact_replay_policy=(
            "certified_historical_exact_replay_tranche_supported"
        ),
        broader_historical_exact_replay_boundary=(
            "historical_composite_certified_source_lineage"
        ),
        broader_historical_exact_replay_reason=(
            "historical_composite_runs_can_gain_certified_exact_replay_parent_evidence_via_certified_source_lineage"
        ),
        replay_family_contract="composite_snapshot_backed_exact_replay",
        default_required_persistence_profile="replay_ready",
        support_scope="snapshot_backed_composite_trace_debug",
        reason="composite_family_requires_full_snapshot_envelope",
    )


def _build_source_reproducibility_family_profile(
    *,
    family: str | None,
    execution_context: ReproducibilityExecutionContext,
) -> ReproducibilityFamilyProfile:
    supported = family in _PUBLISHED_SUPPORTED_SOURCE_FAMILIES
    published = family in _PUBLISHED_SOURCE_FAMILIES
    return ReproducibilityFamilyProfile(
        family=family,
        execution_context=execution_context,
        lineage_closure_supported=supported,
        strict_exact_replay_supported=supported,
        support_state=_source_support_state(supported=supported, published=published),
        strict_replay_runtime_verdict=_source_runtime_verdict(supported=supported),
        exact_replay_support_boundary="snapshot_backed_source_runs_only",
        post_capture_replayable_parent_supported=supported,
        post_capture_replayable_parent_boundary=(
            "ledger_materialized_live_capture_parent" if supported else None
        ),
        post_capture_replayable_parent_reason=(
            "family_can_promote_materialized_live_capture_into_replayable_parent_evidence"
            if supported
            else "family_outside_supported_exact_replay_boundary"
        ),
        historical_live_run_upgrade_policy=(
            "input_snapshot_published_ledger_evidence_only"
            if supported
            else "outside_supported_boundary"
        ),
        historical_live_run_upgrade_boundary=(
            "input_snapshot_published_ledger_evidence" if supported else None
        ),
        historical_live_run_upgrade_reason=(
            "historical_live_runs_require_input_snapshot_published_ledger_evidence_before_parent_promotion"
            if supported
            else "family_outside_supported_exact_replay_boundary"
        ),
        broader_historical_exact_replay_policy=(
            "certified_historical_exact_replay_tranche_supported"
        ),
        broader_historical_exact_replay_boundary=(
            "historical_source_snapshot_certification" if supported else None
        ),
        broader_historical_exact_replay_reason=(
            "retained_historical_source_runs_can_gain_certified_exact_replay_parent_evidence_via_backfilled_snapshot_certification"
        ),
        replay_family_contract=_source_replay_family_contract(supported=supported),
        default_required_persistence_profile=_source_default_required_profile(
            supported=supported
        ),
        support_scope="operator_grade_trace_debug",
        reason=_resolve_source_profile_reason(
            supported=supported,
            published=published,
        ),
    )


def _source_support_state(
    *,
    supported: bool,
    published: bool,
) -> ReplaySupportState:
    if supported:
        return "exact_replay_supported"
    if published:
        return "rebuild_only"
    return "debug_only"


def _source_runtime_verdict(
    *,
    supported: bool,
) -> StrictReplayRuntimeVerdict:
    if supported:
        return "allowed_with_snapshot_backed_source_refs"
    return "blocked_outside_supported_boundary"


def _source_replay_family_contract(
    *,
    supported: bool,
) -> ReplayFamilyContractName:
    if supported:
        return "snapshot_backed_exact_replay"
    return "rebuild_only"


def _source_default_required_profile(*, supported: bool) -> str:
    if supported:
        return "replay_ready"
    return "degraded_observable"


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
