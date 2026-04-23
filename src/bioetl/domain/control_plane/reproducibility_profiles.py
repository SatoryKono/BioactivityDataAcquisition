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
_PUBLISHED_SUPPORTED_SOURCE_FAMILIES = (
    "chembl.activity",
    "chembl.molecule",
    "crossref.publication",
    "pubchem.compound",
    "pubmed.publication",
)

ReproducibilityExecutionContext = Literal["source", "composite"]
ReplayFamilyContractName = Literal[
    "snapshot_backed_exact_replay",
    "composite_snapshot_backed_exact_replay",
    "rebuild_only",
]


@dataclass(frozen=True, slots=True)
class ReproducibilityFamilyProfile:
    """Published per-family reproducibility profile."""

    family: str | None
    execution_context: ReproducibilityExecutionContext
    lineage_closure_supported: bool
    strict_exact_replay_supported: bool
    exact_replay_support_boundary: str
    replay_family_contract: ReplayFamilyContractName
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
        return ReproducibilityFamilyProfile(
            family=family,
            execution_context=execution_context,
            lineage_closure_supported=False,
            strict_exact_replay_supported=True,
            exact_replay_support_boundary="composite_snapshot_backed_input_envelope",
            replay_family_contract="composite_snapshot_backed_exact_replay",
            support_scope="snapshot_backed_composite_trace_debug",
            reason="composite_family_requires_full_snapshot_envelope",
        )
    supported = family in _PUBLISHED_SUPPORTED_SOURCE_FAMILIES
    published = family in _PUBLISHED_SOURCE_FAMILIES
    if supported:
        reason = "family_within_supported_boundary"
    elif published:
        reason = "family_within_published_inventory_but_outside_supported_boundary"
    else:
        reason = "family_outside_published_inventory"
    return ReproducibilityFamilyProfile(
        family=family,
        execution_context=execution_context,
        lineage_closure_supported=supported,
        strict_exact_replay_supported=supported,
        exact_replay_support_boundary="snapshot_backed_source_runs_only",
        replay_family_contract=(
            "snapshot_backed_exact_replay" if supported else "rebuild_only"
        ),
        support_scope="operator_grade_trace_debug",
        reason=reason,
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
        "strict_exact_replay_supported": profile.strict_exact_replay_supported,
        "exact_replay_support_boundary": profile.exact_replay_support_boundary,
        "support_scope": profile.support_scope,
        "reason": profile.reason,
        "supported_families": published_supported_reproducibility_families(),
    }
