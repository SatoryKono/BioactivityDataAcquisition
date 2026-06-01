"""Reproducibility profile builder functions.

Extracted from reproducibility_profiles.py to meet file size limits.
"""

from __future__ import annotations

from bioetl.domain.control_plane._reproducibility_profile_types import (
    ReplayFamilyContractName,
    ReplaySupportState,
    ReproducibilityExecutionContext,
    ReproducibilityFamilyProfile,
    StrictReplayRuntimeVerdict,
)

_REGISTERED_SOURCE_FAMILIES = (
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
    "chembl.target_protein_classification",
    "chembl.tissue",
    "crossref.publication",
    "openalex.publication",
    "pubchem.compound",
    "pubmed.publication",
    "semanticscholar.publication",
    "uniprot.idmapping",
    "uniprot.protein",
)
_REGISTERED_COMPOSITE_FAMILIES = (
    "composite.activity",
    "composite.assay",
    "composite.molecule",
    "composite.publication",
    "composite.target",
)
_REGISTERED_STRICT_SOURCE_FAMILIES = _REGISTERED_SOURCE_FAMILIES
_REGISTERED_STRICT_COMPOSITE_FAMILIES = _REGISTERED_COMPOSITE_FAMILIES
_REGISTERED_FAMILY_EXECUTION_CONTEXTS = dict.fromkeys(
    _REGISTERED_SOURCE_FAMILIES,
    "source",
) | dict.fromkeys(
    _REGISTERED_COMPOSITE_FAMILIES,
    "composite",
)

# Compatibility aliases retained for generated docs/tests that still use the
# older published-* naming while the runtime moves to repo-wide certification.
_PUBLISHED_SOURCE_FAMILIES = _REGISTERED_SOURCE_FAMILIES
_PUBLISHED_COMPOSITE_FAMILIES = _REGISTERED_COMPOSITE_FAMILIES
_PUBLISHED_SUPPORTED_SOURCE_FAMILIES = _REGISTERED_STRICT_SOURCE_FAMILIES


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
        lineage_closure_supported=True,
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
        reason="family_within_supported_boundary",
    )


def _build_source_reproducibility_family_profile(
    *,
    family: str | None,
    execution_context: ReproducibilityExecutionContext,
) -> ReproducibilityFamilyProfile:
    supported = family in _REGISTERED_STRICT_SOURCE_FAMILIES
    published = family in _REGISTERED_SOURCE_FAMILIES
    return ReproducibilityFamilyProfile(
        family=family,
        execution_context=execution_context,
        lineage_closure_supported=supported,
        strict_exact_replay_supported=supported,
        support_state=_source_support_state(supported=supported, published=published),
        strict_replay_runtime_verdict=_source_runtime_verdict(supported=supported),
        exact_replay_support_boundary="snapshot_backed_source_runs_only",
        post_capture_replayable_parent_supported=supported,
        post_capture_replayable_parent_boundary=_source_post_capture_boundary(
            supported=supported
        ),
        post_capture_replayable_parent_reason=_source_post_capture_reason(
            supported=supported
        ),
        historical_live_run_upgrade_policy=_source_historical_upgrade_policy(
            supported=supported
        ),
        historical_live_run_upgrade_boundary=_source_historical_upgrade_boundary(
            supported=supported
        ),
        historical_live_run_upgrade_reason=_source_historical_upgrade_reason(
            supported=supported
        ),
        broader_historical_exact_replay_policy=(
            "certified_historical_exact_replay_tranche_supported"
        ),
        broader_historical_exact_replay_boundary=_source_broader_boundary(
            supported=supported
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


def _source_post_capture_boundary(*, supported: bool) -> str | None:
    return "ledger_materialized_live_capture_parent" if supported else None


def _source_post_capture_reason(*, supported: bool) -> str:
    if supported:
        return "family_can_promote_materialized_live_capture_into_replayable_parent_evidence"
    return "family_outside_supported_exact_replay_boundary"


def _source_historical_upgrade_policy(*, supported: bool) -> str:
    return (
        "input_snapshot_published_ledger_evidence_only"
        if supported
        else "outside_supported_boundary"
    )


def _source_historical_upgrade_boundary(*, supported: bool) -> str | None:
    return "input_snapshot_published_ledger_evidence" if supported else None


def _source_historical_upgrade_reason(*, supported: bool) -> str:
    if supported:
        return "historical_live_runs_require_input_snapshot_published_ledger_evidence_before_parent_promotion"
    return "family_outside_supported_exact_replay_boundary"


def _source_broader_boundary(*, supported: bool) -> str | None:
    return "historical_source_snapshot_certification" if supported else None


__all__ = [
    "_PUBLISHED_COMPOSITE_FAMILIES",
    "_PUBLISHED_SOURCE_FAMILIES",
    "_PUBLISHED_SUPPORTED_SOURCE_FAMILIES",
    "_REGISTERED_COMPOSITE_FAMILIES",
    "_REGISTERED_FAMILY_EXECUTION_CONTEXTS",
    "_REGISTERED_SOURCE_FAMILIES",
    "_REGISTERED_STRICT_COMPOSITE_FAMILIES",
    "_REGISTERED_STRICT_SOURCE_FAMILIES",
    "_build_composite_reproducibility_family_profile",
    "_build_source_reproducibility_family_profile",
    "resolve_reproducibility_family",
]
