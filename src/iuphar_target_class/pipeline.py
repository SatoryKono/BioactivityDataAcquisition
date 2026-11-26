"""Indexed, offline orchestration for target-class stages 0–3."""

from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field, replace
from types import MappingProxyType
from typing import Literal

from .bioetl_input import target_gene_aliases
from .effective_policy import (
    CHANNEL_PRIORITY_RULE,
    ION_CHANNEL,
    TRANSCRIPTION_FACTOR_CLASS,
    ec_categories,
    name_keyword_class,
    select_channel_priority,
    select_ec_class,
    select_keyword_class,
)
from .evidence import (
    ContractDefect,
    EvidenceDraft,
    EvidenceTable,
    build_evidence_table,
    require_class_chain,
)
from .gtopdb_2026_3_1 import FAMILY_ROWS
from .hierarchy import (
    FamilyNode,
    HierarchyResult,
    allowed_subclass_vocabulary,
    hierarchy_for_graph_defect,
    is_synthetic_local_family_id,
    normalize_provider_class,
    validate_family_graph,
)
from .identifier_roles import (
    ANCHOR_PRIORITY_POLICIES,
    EC_EFFECTIVE_POLICIES,
    RANKED_CLASS_POLICIES,
    TRANSCRIPTION_FACTOR_POLICY_VERSION,
    normalize_hgnc_ids,
)
from .iuphar_mapping import approved_class_mappings, approved_subclass_mappings
from .local_layer import apply_local, predictions_from_row
from .matching import (
    METHOD_ORDER,
    Candidate,
    CatalogTarget,
    MatchQuery,
    collect_candidates,
    validate_identity,
)
from .models import (
    ClassificationResult,
    Diagnostic,
    GlueFixture,
    LocalInference,
    MatchResult,
    ProviderAnnotation,
    RawTargetRow,
    RunProvenance,
    ValidatedInput,
)
from .normalization import isolated_invalid_result, validate_input
from .policy import (
    GRAPH_MAX_DEPTH,
    GRAPH_MAX_VISITED_NODES,
    local_evidence_content,
    local_rules,
    validate_rules,
)
from .resolution import Resolution, ResolutionInput, select_effective_class


@dataclass(frozen=True, slots=True)
class IndexedSnapshot:
    """Immutable read projection for one fixed snapshot and mapping release."""

    snapshot_id: str
    mapping_version: str
    complete: bool
    catalog: tuple[CatalogTarget, ...]
    lookup: Mapping[tuple[str, str], tuple[int, ...]]
    annotations: Mapping[str, ProviderAnnotation]
    families: Mapping[str, tuple[FamilyNode, ...]]
    type_to_class: Mapping[str, str]
    family_to_class: Mapping[str, str]
    identifier_catalog: frozenset[str]
    complex_ids: frozenset[str]
    species_annotations: Mapping[tuple[str, str], ProviderAnnotation] = field(
        default_factory=dict
    )
    admission_complete: bool | None = None
    type_to_subclass: Mapping[str, str] = field(default_factory=dict)
    family_to_subclass: Mapping[str, str] = field(default_factory=dict)
    graph_defect: Diagnostic | None = None

    def __post_init__(self) -> None:
        """Copy every mapping so a later edit of the caller's dict is ignored."""
        object.__setattr__(self, "lookup", _frozen_lookup(self.lookup))
        object.__setattr__(self, "annotations", _frozen_annotations(self.annotations))
        object.__setattr__(self, "families", _frozen_families(self.families))
        object.__setattr__(self, "type_to_class", _frozen_strings(self.type_to_class))
        object.__setattr__(
            self, "family_to_class", _frozen_strings(self.family_to_class)
        )
        object.__setattr__(
            self, "species_annotations", _frozen_species(self.species_annotations)
        )
        object.__setattr__(
            self, "type_to_subclass", _frozen_strings(self.type_to_subclass)
        )
        object.__setattr__(
            self, "family_to_subclass", _frozen_strings(self.family_to_subclass)
        )

    @classmethod
    def from_approved_gtopdb(
        cls,
        *,
        snapshot_id: str,
        release: str,
        complete: bool,
        catalog: tuple[CatalogTarget, ...],
        annotations: Mapping[str, ProviderAnnotation],
        complex_ids: frozenset[str] = frozenset(),
        species_annotations: Mapping[tuple[str, str], ProviderAnnotation] | None = None,
        admission_complete: bool | None = None,
    ) -> IndexedSnapshot:
        """Bind a frozen provider snapshot to the exact approved release.

        The full pinned family graph is admitted before the snapshot exists.
        A cycle, a missing parent, or a root distance above the limit blocks
        the snapshot, including a branch that no requested target uses.
        """
        types, families = approved_class_mappings(release)
        type_sub, family_sub = approved_subclass_mappings(release)
        nodes = tuple(
            FamilyNode(str(family), tuple(map(str, parents)), source_type)
            for family, source_type, parents in FAMILY_ROWS
        )
        snapshot = cls.build(
            snapshot_id=snapshot_id,
            mapping_version=release,
            complete=complete,
            catalog=catalog,
            annotations=annotations,
            family_nodes=nodes,
            type_to_class=types,
            family_to_class=families,
            type_to_subclass=type_sub,
            family_to_subclass=family_sub,
            complex_ids=complex_ids,
            species_annotations=species_annotations,
            admission_complete=admission_complete,
        )
        if snapshot.graph_defect is not None:
            raise ValueError(
                "approved family graph is not admitted: "
                + snapshot.graph_defect.message
            )
        return snapshot

    @classmethod
    def build(
        cls,
        *,
        snapshot_id: str,
        mapping_version: str,
        complete: bool,
        catalog: tuple[CatalogTarget, ...],
        annotations: Mapping[str, ProviderAnnotation],
        family_nodes: tuple[FamilyNode, ...],
        type_to_class: Mapping[str, str],
        family_to_class: Mapping[str, str],
        type_to_subclass: Mapping[str, str] | None = None,
        family_to_subclass: Mapping[str, str] | None = None,
        complex_ids: frozenset[str] = frozenset(),
        species_annotations: Mapping[tuple[str, str], ProviderAnnotation] | None = None,
        admission_complete: bool | None = None,
    ) -> IndexedSnapshot:
        """Index all channels once and verify recorded provider payload hashes."""
        lookup, families = _snapshot_indexes(catalog, family_nodes)
        _validate_provider_payloads(annotations)
        scoped = dict(species_annotations or {})
        _validate_species_payloads(scoped)
        admission = validate_family_graph(
            family_nodes,
            (),
            max_depth=GRAPH_MAX_DEPTH,
            max_visited_nodes=GRAPH_MAX_VISITED_NODES,
        )
        return cls(
            snapshot_id,
            mapping_version,
            complete,
            catalog,
            MappingProxyType({key: tuple(value) for key, value in lookup.items()}),
            MappingProxyType(dict(annotations)),
            MappingProxyType({key: tuple(value) for key, value in families.items()}),
            MappingProxyType(dict(type_to_class)),
            MappingProxyType(dict(family_to_class)),
            frozenset(value for (kind, value), _ in lookup.items() if kind != "text"),
            complex_ids,
            MappingProxyType(scoped),
            admission_complete,
            MappingProxyType(dict(type_to_subclass or {})),
            MappingProxyType(dict(family_to_subclass or {})),
            admission,
        )


def _frozen_lookup(
    mapping: Mapping[tuple[str, str], tuple[int, ...]],
) -> Mapping[tuple[str, str], tuple[int, ...]]:
    return MappingProxyType({key: tuple(value) for key, value in mapping.items()})


def _frozen_families(
    mapping: Mapping[str, tuple[FamilyNode, ...]],
) -> Mapping[str, tuple[FamilyNode, ...]]:
    return MappingProxyType({key: tuple(value) for key, value in mapping.items()})


def _frozen_strings(mapping: Mapping[str, str]) -> Mapping[str, str]:
    return MappingProxyType(dict(mapping))


def _frozen_annotations(
    mapping: Mapping[str, ProviderAnnotation],
) -> Mapping[str, ProviderAnnotation]:
    return MappingProxyType(dict(mapping))


def _frozen_species(
    mapping: Mapping[tuple[str, str], ProviderAnnotation],
) -> Mapping[tuple[str, str], ProviderAnnotation]:
    return MappingProxyType(dict(mapping))


def _snapshot_indexes(
    catalog: tuple[CatalogTarget, ...], family_nodes: tuple[FamilyNode, ...]
) -> tuple[dict[tuple[str, str], list[int]], dict[str, list[FamilyNode]]]:
    """Retain source order inside each channel and family bucket."""
    lookup: dict[tuple[str, str], list[int]] = defaultdict(list)
    families: dict[str, list[FamilyNode]] = defaultdict(list)
    for index, record in enumerate(catalog):
        for pair in set(_channels(record)):
            lookup[pair].append(index)
    for node in family_nodes:
        families[node.family_id].append(node)
    return lookup, families


def _validate_provider_payloads(annotations: Mapping[str, ProviderAnnotation]) -> None:
    """Validate identity only after requiring the frozen payload and digest."""
    for key, value in annotations.items():
        if not value.raw_payload or not value.payload_sha256:
            raise ValueError("missing frozen provider payload or digest")
        actual = hashlib.sha256(value.raw_payload.encode()).hexdigest()
        if value.target_id != key or value.payload_sha256 != actual:
            raise ValueError("provider record identity or digest mismatch")


def _validate_species_payloads(
    annotations: Mapping[tuple[str, str], ProviderAnnotation],
) -> None:
    for (target_id, taxon), annotation in annotations.items():
        if annotation.taxon != taxon:
            raise ValueError("provider annotation belongs to another species")
        _validate_provider_payloads({target_id: annotation})


def _annotation(
    snapshot: IndexedSnapshot, target_id: str, taxon: str | None
) -> ProviderAnnotation | None:
    if snapshot.species_annotations:
        return snapshot.species_annotations.get((target_id, taxon or ""))
    return snapshot.annotations.get(target_id)


def _species_match(
    row: ValidatedInput, match: MatchResult, snapshot: IndexedSnapshot
) -> tuple[MatchResult, ProviderAnnotation | None]:
    key = match.matched_target_id
    if key is None or not snapshot.species_annotations or row.taxon is not None:
        return match, _annotation(snapshot, key or "", row.taxon)
    taxa = _variant_taxa(row, snapshot, key)
    if len(taxa) == 1:
        return match, _annotation(snapshot, key, next(iter(taxa)))
    return replace(
        match,
        match_status="insufficient_input",
        matched_target_id=None,
        diagnostics=(
            *match.diagnostics,
            Diagnostic(
                "species_identity_required",
                "warning",
                "provider identity has several species variants",
            ),
        ),
    ), None


def _variant_taxa(
    row: ValidatedInput, snapshot: IndexedSnapshot, key: str
) -> set[str | None]:
    variants = [item for item in snapshot.catalog if item.target_id == key]
    if row.uniprot_accessions:
        variants = [
            item
            for item in variants
            if set(item.uniprot_ids).intersection(row.uniprot_accessions)
        ]
    return {item.species for item in variants}


def _missing_variant(row: ValidatedInput, snapshot: IndexedSnapshot) -> bool:
    explicit = [item for item in snapshot.catalog if item.target_id == row.target_id]
    return bool(explicit) and not any(item.species == row.taxon for item in explicit)


def _scope_match(
    row: ValidatedInput, match: MatchResult, snapshot: IndexedSnapshot
) -> MatchResult:
    """A provider ID cannot establish coverage for a missing species variant."""
    if not snapshot.species_annotations or row.taxon is None:
        return match
    species = {taxon for _, taxon in snapshot.species_annotations}
    missing_variant = _missing_variant(row, snapshot)
    outside_species = row.taxon not in species
    if outside_species or (not snapshot.complete and missing_variant):
        return MatchResult(
            match_status="source_unavailable",
            matched_target_id=None,
            candidate_target_ids=match.candidate_target_ids,
            match_method=match.match_method,
            match_evidence_ids=match.match_evidence_ids,
            diagnostics=(
                *match.diagnostics,
                Diagnostic(
                    "unsupported_taxon"
                    if outside_species
                    and row.provenance.matching_policy_version in EC_EFFECTIVE_POLICIES
                    else "source_unavailable",
                    "warning",
                    "requested species identity is outside verified matching coverage",
                ),
            ),
        )
    return match


@dataclass(frozen=True, slots=True)
class CandidateRow:
    input_row_id: str
    target_id: str
    match_method: str


@dataclass(frozen=True, slots=True)
class RowResult:
    validated: ValidatedInput
    result: ClassificationResult
    evidence: EvidenceTable
    candidates: tuple[CandidateRow, ...]
    direct: HierarchyResult | None = None
    local: LocalInference | None = None
    annotation: ProviderAnnotation | None = None
    match_methods: tuple[str, ...] = ()
    provider_release: str | None = None


@dataclass(frozen=True, slots=True)
class ComponentRow:
    input_row_id: str
    component_id: str
    iuphar_type_raw: str | None
    iuphar_class: str | None
    annotation_status: str
    payload_sha256: str | None = None


@dataclass(frozen=True, slots=True)
class BatchResult:
    status: str
    rows: tuple[RowResult, ...]
    diagnostics: tuple[tuple[str, Diagnostic], ...]
    metrics: Mapping[str, int]
    components: tuple[ComponentRow, ...] = ()


def _channels(row: CatalogTarget) -> tuple[tuple[str, str], ...]:
    return (
        ("id", row.target_id),
        *(("uniprot", value) for value in row.uniprot_ids),
        *(("hgnc", value) for value in row.hgnc_ids),
        *(("text", value) for value in (*row.names, *row.synonyms)),
        *(("gene_id", row.gene_id) for _ in (0,) if row.gene_id),
        *(("gene_symbol", row.gene_symbol) for _ in (0,) if row.gene_symbol),
    )


def _shortlist(query: MatchQuery, ctx: IndexedSnapshot) -> tuple[CatalogTarget, ...]:
    keys = (
        ("id", query.target_id),
        ("gene_id", query.gene_id),
        ("gene_symbol", query.gene_symbol),
        ("text", query.name),
        *(("uniprot", value) for value in query.uniprot_ids),
        *(("hgnc", value) for value in query.hgnc_ids),
        *(("text", value) for value in query.synonyms),
    )
    indexes = {i for k, v in keys if v is not None for i in ctx.lookup.get((k, v), ())}
    return tuple(ctx.catalog[i] for i in sorted(indexes))


def _conflict_catalog(
    shortlist: tuple[CatalogTarget, ...], ctx: IndexedSnapshot
) -> tuple[CatalogTarget, ...]:
    """Keep every species variant of a shortlisted IUPHAR id visible to conflicts."""
    ids = {row.target_id for row in shortlist}
    if not ids:
        return shortlist
    return tuple(row for row in ctx.catalog if row.target_id in ids)


def _auxiliary_diagnostic_catalog(
    query: MatchQuery,
    identity_catalog: tuple[CatalogTarget, ...],
    ctx: IndexedSnapshot,
) -> tuple[CatalogTarget, ...]:
    """Resolve auxiliary UniProt rows without admitting them to identity channels.

    RF-002: primary shortlist omits auxiliary xrefs on purpose. Diagnostics still
    need those catalog rows so a same-species hit becomes
    ``auxiliary_uniprot_divergence`` rather than a false
    ``unknown_auxiliary_uniprot``.
    """
    if not query.auxiliary_uniprot_ids:
        return identity_catalog
    indexes = {
        index
        for accession in query.auxiliary_uniprot_ids
        for index in ctx.lookup.get(("uniprot", accession), ())
    }
    if not indexes:
        return identity_catalog
    seen = {row.target_id for row in identity_catalog}
    extras = tuple(
        ctx.catalog[index]
        for index in sorted(indexes)
        if ctx.catalog[index].target_id not in seen
    )
    if not extras:
        return identity_catalog
    return (*identity_catalog, *extras)


def _ancestor_records(
    ctx: IndexedSnapshot, ids: tuple[str, ...]
) -> tuple[FamilyNode, ...]:
    seen: set[str] = set()
    pending = list(ids)
    records: list[FamilyNode] = []
    while pending and len(seen) <= GRAPH_MAX_VISITED_NODES:
        key = pending.pop()
        if key in seen:
            continue
        seen.add(key)
        if is_synthetic_local_family_id(key):
            continue
        nodes = ctx.families.get(key, ())
        records.extend(nodes)
        pending.extend(parent for node in nodes for parent in node.parent_ids)
    return tuple(records)


def _direct(
    ctx: IndexedSnapshot,
    annotation: ProviderAnnotation | None,
) -> HierarchyResult | None:
    if annotation is None:
        return None
    type_name = annotation.type_raw.strip().lower() if annotation.type_raw else None
    if ctx.graph_defect is not None:
        return hierarchy_for_graph_defect(
            ctx.graph_defect,
            type_name=type_name,
            type_to_class=ctx.type_to_class,
            type_to_subclass=ctx.type_to_subclass,
        )
    return normalize_provider_class(
        type_name=type_name,
        family_ids=annotation.family_ids,
        nodes=_ancestor_records(ctx, annotation.family_ids),
        type_to_class=ctx.type_to_class,
        family_to_class=ctx.family_to_class,
        type_to_subclass=ctx.type_to_subclass,
        family_to_subclass=ctx.family_to_subclass,
    )


def _evidence(
    row: ValidatedInput,
    match: MatchResult,
    hits: tuple[Candidate, ...],
    annotation: ProviderAnnotation | None,
    direct: HierarchyResult | None,
    local: LocalInference,
    *,
    run_id: str,
    rule_id: str | None,
    mapping_version: str,
    policy_evidence: EvidenceDraft | None,
) -> EvidenceTable:
    draft = [
        EvidenceDraft(
            row.input_row_id, "match", hit.target_id, hit.match_method, "match"
        )
        for hit in hits
    ]
    for role, values in (
        ("primary_uniprot", row.uniprot_accessions),
        ("equivalent_uniprot", row.equivalent_uniprot_accessions),
        ("auxiliary_uniprot", row.auxiliary_uniprot_accessions),
    ):
        for accession in values:
            draft.append(
                EvidenceDraft(
                    row.input_row_id,
                    "match",
                    role,
                    accession,
                    "match",
                )
            )
    if annotation is not None and match.matched_target_id and annotation.raw_payload:
        draft.append(
            EvidenceDraft(
                row.input_row_id,
                "iuphar_raw",
                match.matched_target_id,
                annotation.raw_payload,
                "match",
            )
        )
    if rule_id and direct and match.matched_target_id:
        draft.append(
            EvidenceDraft(
                row.input_row_id,
                "iuphar_mapping",
                match.matched_target_id,
                f"{mapping_version}:{rule_id}:{direct.proof}",
                "match",
            )
        )
    rules_for_evidence = dict(local.local_rules_by_evidence)
    draft.extend(
        EvidenceDraft(
            row.input_row_id,
            "local_rule",
            hashlib.sha256(ref.encode()).hexdigest(),
            local_evidence_content(ref, rules_for_evidence[ref]),
            "local",
        )
        for ref in local.local_evidence_ids
    )
    if policy_evidence is not None:
        draft.append(policy_evidence)
    return build_evidence_table(tuple(draft), run_id=run_id)


def classify_target(
    row: ValidatedInput,
    *,
    snapshot: IndexedSnapshot,
    run_id: str,
) -> RowResult:
    """Orchestrate one normalized row without turning component errors into absence."""
    if row.provenance.snapshot_id != snapshot.snapshot_id:
        raise ValueError("row provenance does not match snapshot")
    if row.input_validation_status == "invalid_input":
        return RowResult(
            row,
            isolated_invalid_result(row),
            build_evidence_table((), run_id=run_id),
            (),
        )
    prioritize_anchors = (
        row.provenance.matching_policy_version in ANCHOR_PRIORITY_POLICIES
    )
    ranked = (
        row.provenance.matching_policy_version in RANKED_CLASS_POLICIES
        and row.target_kind == "protein"
    )
    business = (
        _source_business(row)
        if row.provenance.matching_policy_version in EC_EFFECTIVE_POLICIES
        else {}
    )
    query = MatchQuery(
        row.target_id,
        row.uniprot_accessions,
        row.gene_symbol,
        row.gene_id,
        row.taxon,
        row.name,
        row.synonyms,
        auxiliary_uniprot_ids=row.auxiliary_uniprot_accessions,
        hgnc_ids=(
            _row_hgnc_ids(row, business)
            if prioritize_anchors and row.taxon == "9606"
            else ()
        ),
        prioritize_anchors=prioritize_anchors,
        ranked_text=ranked,
        use_synonyms=not ranked or not any(number.valid for number in row.ec_numbers),
        gene_aliases=target_gene_aliases(business) if ranked else (),
    )
    subset = _shortlist(query, snapshot)
    hits = collect_candidates(query, subset)
    identity_catalog = _conflict_catalog(subset, snapshot)
    match = validate_identity(
        query,
        identity_catalog,
        hits,
        snapshot_complete=snapshot.complete,
        auxiliary_catalog=_auxiliary_diagnostic_catalog(
            query, identity_catalog, snapshot
        ),
    )
    match = _scope_match(row, match, snapshot)
    hits = _publication_hits(query, subset, hits, match)
    match = _match_complex_target(row, match, snapshot)
    match, annotation = _species_match(row, match, snapshot)
    if (
        match.match_status == "matched"
        and annotation is not None
        and annotation.taxon
        and row.taxon is None
    ):
        row = replace(row, taxon=annotation.taxon)
    direct = _direct(snapshot, annotation)
    return _complete(row, snapshot, run_id, hits, match, annotation, direct)


def _source_business(row: ValidatedInput) -> Mapping[str, object]:
    business = row.raw_fields.get("source_business_data")
    if not business:
        return {}
    data = json.loads(business)
    return data if isinstance(data, dict) else {}


def _row_hgnc_ids(
    row: ValidatedInput, business: Mapping[str, object]
) -> tuple[str, ...]:
    explicit = row.raw_fields.get("hgnc")
    if (
        explicit is None
        and row.provenance.matching_policy_version in EC_EFFECTIVE_POLICIES
    ):
        value = business.get("target_xref_hgnc_ids")
        explicit = value if isinstance(value, str) else None
    return normalize_hgnc_ids(explicit)


def _match_complex_target(
    row: ValidatedInput, match: MatchResult, snapshot: IndexedSnapshot
) -> MatchResult:
    """A matching component alone cannot establish the complex identity."""
    if (
        row.target_kind == "complex"
        and match.matched_target_id is not None
        and match.matched_target_id not in snapshot.complex_ids
    ):
        match = replace(
            match,
            match_status="ambiguous",
            matched_target_id=None,
            diagnostics=(
                *match.diagnostics,
                Diagnostic(
                    "complex_component_only",
                    "warning",
                    "a component is not a match to the complex",
                ),
            ),
        )
    return match


def _publication_hits(
    query: MatchQuery,
    catalog: tuple[CatalogTarget, ...],
    hits: tuple[Candidate, ...],
    match: MatchResult,
) -> tuple[Candidate, ...]:
    """Expose the conflicting exact channels without confirming cross-species hits."""
    if match.match_status != "identity_conflict":
        return hits
    unfiltered_query = MatchQuery(
        target_id=query.target_id,
        uniprot_ids=query.uniprot_ids,
        gene_symbol=query.gene_symbol,
        gene_id=query.gene_id,
        organism=None,
        name=query.name,
        synonyms=query.synonyms,
        auxiliary_uniprot_ids=query.auxiliary_uniprot_ids,
    )
    unfiltered = collect_candidates(unfiltered_query, catalog)
    conflict = {
        hit
        for hit in unfiltered
        if hit.target_id in match.candidate_target_ids
        and hit.match_method in match.match_method
    }
    return tuple(
        sorted(
            set(hits) | conflict,
            key=lambda hit: (hit.target_id, METHOD_ORDER.index(hit.match_method)),
        )
    )


def _classification_diagnostics(
    row: ValidatedInput,
    match: MatchResult,
    annotation: ProviderAnnotation | None,
    direct: HierarchyResult | None,
    local: LocalInference,
    evidence: EvidenceTable,
) -> tuple[Diagnostic, ...]:
    missing_annotation = (
        (
            Diagnostic(
                "provider_annotation_unavailable",
                "warning",
                "matched record has no frozen annotation",
            ),
        )
        if match.matched_target_id and annotation is None
        else ()
    )
    raw_ref = next(
        (
            item.evidence_id
            for item in evidence.records
            if item.evidence_type == "iuphar_raw"
        ),
        None,
    )
    direct_diagnostics = (
        tuple(replace(item, evidence_id=raw_ref) for item in direct.diagnostics)
        if direct
        else ()
    )
    diagnostics = (
        *row.diagnostics,
        *match.diagnostics,
        *direct_diagnostics,
        *local.diagnostics,
        *missing_annotation,
    )
    return _bound_diagnostics(diagnostics, evidence)


def _bound_diagnostics(
    diagnostics: tuple[Diagnostic, ...], evidence: EvidenceTable
) -> tuple[Diagnostic, ...]:
    """An unverified candidate has no witness until a real child row exists."""
    records = {record.evidence_id for record in evidence.records}
    unverified = {
        "candidate_only",
        "dependent_prediction",
        "prediction_requires_explicit_rule",
        "invalid_ec",
    }
    result = []
    for item in diagnostics:
        if item.evidence_id is not None and item.evidence_id not in records:
            if item.code not in unverified:
                raise ContractDefect("unresolvable diagnostic evidence reference")
            item = replace(item, evidence_id=None)
        result.append(item)
    return tuple(result)


def _partial_basis(
    direct: HierarchyResult | None, annotation_status: str | None
) -> Literal["type", "family_mapping"] | None:
    if annotation_status != "partial":
        return None
    return "type" if direct and direct.proof == "type" else "family_mapping"


def _direct_metadata(
    direct: HierarchyResult | None, match: MatchResult
) -> tuple[str | None, str | None, str | None]:
    """Distinguish an unavailable matched annotation from an unmatched row."""
    direct_class = direct.iuphar_class if direct is not None else None
    rule_id = None
    if direct_class and direct is not None:
        rule_id = (
            f"iuphar_{'type' if direct.proof == 'type' else 'family'}:{direct_class}"
        )
    annotation_status = "not_available" if match.match_status == "matched" else None
    if direct is not None:
        annotation_status = direct.annotation_status
    return direct_class, rule_id, annotation_status


def _resolution_input(
    row: ValidatedInput,
    snapshot: IndexedSnapshot,
    match: MatchResult,
    annotation: ProviderAnnotation | None,
    direct: HierarchyResult | None,
    local: LocalInference,
    annotation_status: str | None,
    candidate_ids: tuple[str, ...],
    direct_class: str | None,
) -> ResolutionInput:
    """Project frozen classification inputs without changing fallback rules."""
    subclass = direct.iuphar_subclass if direct else None
    # Family-only subclass labels must be allowed even when type→subclass is empty.
    direct_vocabulary = allowed_subclass_vocabulary(
        snapshot.type_to_subclass, snapshot.family_to_subclass
    )
    return ResolutionInput(
        match_status=match.match_status or "contract_error",
        iuphar_annotation_status=annotation_status,
        local_status=local.local_status or "not_supported",
        iuphar_class=direct_class,
        iuphar_subclass=subclass,
        local_class=local.local_class,
        local_subclasses=local.local_subclasses,
        # family_only / partial reads confirmed_subclasses, not iuphar_subclass.
        confirmed_subclasses=(subclass,)
        if subclass and annotation_status == "partial"
        else (),
        direct_vocabulary=direct_vocabulary,
        partial_basis=_partial_basis(direct, annotation_status),
        target_kind=row.target_kind or "protein",
        complex_direct_match=match.matched_target_id in snapshot.complex_ids,
        iuphar_class_candidates=direct.iuphar_class_candidates if direct else (),
        local_candidates=local.local_candidates,
        raw_type=annotation.type_raw if annotation else None,
        matched_target_id=match.matched_target_id,
        candidate_target_ids=candidate_ids,
    )


def _has_channel_candidate(
    row: ValidatedInput, snapshot: IndexedSnapshot, outcome: Resolution
) -> bool:
    classes = (
        outcome.iuphar_class,
        outcome.local_class,
        *outcome.iuphar_class_candidates,
        *outcome.local_candidates,
    )
    if ION_CHANNEL in classes:
        return True
    ids = outcome.candidate_target_ids
    annotations: Iterable[ProviderAnnotation | None]
    if row.taxon is None and snapshot.species_annotations:
        annotations = (
            annotation
            for (key, _), annotation in snapshot.species_annotations.items()
            if key in ids
        )
    else:
        annotations = (_annotation(snapshot, key, row.taxon) for key in ids)
    for annotation in annotations:
        direct = _direct(snapshot, annotation)
        if direct and ION_CHANNEL in (
            direct.iuphar_class,
            *direct.iuphar_class_candidates,
        ):
            return True
    return False


def _fallback_effective_class(
    row: ValidatedInput,
    snapshot: IndexedSnapshot,
    match: MatchResult,
    outcome: Resolution,
    *,
    ranked: bool,
) -> tuple[Resolution, str] | None:
    categories = ec_categories(row.ec_numbers)
    if not categories:
        if ranked and not outcome.effective_class:
            keyword = name_keyword_class(
                row.name,
                allow_transcription_factor=(
                    row.provenance.matching_policy_version
                    == TRANSCRIPTION_FACTOR_POLICY_VERSION
                ),
            )
            if keyword is not None:
                label, term = keyword
                if (
                    match.matched_target_id is None
                    or label == TRANSCRIPTION_FACTOR_CLASS
                ):
                    return select_keyword_class(outcome, label), f"{term}: {row.name}"
        return None
    if outcome.effective_class == ION_CHANNEL or outcome.iuphar_class == ION_CHANNEL:
        return None
    if ranked:
        if len(categories) == 1 and outcome.iuphar_class is not None:
            return None
    else:
        outside_scope = any(d.code == "unsupported_taxon" for d in match.diagnostics)
        if (
            len(categories) == 1 and outcome.effective_class and not outside_scope
        ) or _has_channel_candidate(row, snapshot, outcome):
            return None
    content = "|".join(sorted({item.raw for item in row.ec_numbers if item.valid}))
    return select_ec_class(outcome, categories), content


def _effective_policy(
    row: ValidatedInput,
    snapshot: IndexedSnapshot,
    match: MatchResult,
    outcome: Resolution,
) -> tuple[Resolution, EvidenceDraft | None]:
    policy = row.provenance.matching_policy_version
    if (
        policy not in EC_EFFECTIVE_POLICIES
        or row.target_kind != "protein"
        or "contract_error" in outcome.conflict_codes
    ):
        return outcome, None
    selected = select_channel_priority(outcome)
    if selected.rule_id == CHANNEL_PRIORITY_RULE:
        content = "Ion Channel and Enzyme in the matched annotation or supported local evidence"
    else:
        fallback = _fallback_effective_class(
            row, snapshot, match, outcome, ranked=policy in RANKED_CLASS_POLICIES
        )
        if fallback is None:
            return outcome, None
        selected, content = fallback
    witness = EvidenceDraft(
        row.input_row_id,
        "local_rule",
        selected.rule_id,
        f"{policy}:{selected.effective_class}:{content}",
        "local",
    )
    return selected, witness


def _complete(
    row: ValidatedInput,
    snapshot: IndexedSnapshot,
    run_id: str,
    hits: tuple[Candidate, ...],
    match: MatchResult,
    annotation: ProviderAnnotation | None,
    direct: HierarchyResult | None,
) -> RowResult:
    rules = local_rules()
    local = apply_local(
        row.ec_numbers,
        rules=rules,
        keyword_ids=row.keywords,
        free_text=row.name,
        organism=row.taxon,
        predictions=predictions_from_row(
            predicted_l1=row.predicted_l1,
            predicted_l2=row.predicted_l2,
            raw_fields=row.raw_fields,
        ),
    )
    direct_class, rule_id, annotation_status = _direct_metadata(direct, match)
    candidate_ids = tuple(
        sorted(set(match.candidate_target_ids) | {hit.target_id for hit in hits})
    )
    outcome = select_effective_class(
        _resolution_input(
            row,
            snapshot,
            match,
            annotation,
            direct,
            local,
            annotation_status,
            candidate_ids,
            direct_class,
        )
    )
    outcome, policy_evidence = _effective_policy(row, snapshot, match, outcome)
    if outcome.effective_source == "keyword_rule":
        superseded = {"free_text_manual_review", "free_text_substring_ignored"}
        if outcome.effective_class == TRANSCRIPTION_FACTOR_CLASS:
            superseded.add("broad_nhr_rule_excluded")
        local = replace(
            local,
            local_status="supported",
            local_class=outcome.effective_class,
            diagnostics=tuple(
                item for item in local.diagnostics if item.code not in superseded
            ),
        )
    evidence = _evidence(
        row,
        match,
        hits,
        annotation,
        direct,
        local,
        run_id=run_id,
        rule_id=rule_id,
        mapping_version=snapshot.mapping_version,
        policy_evidence=policy_evidence,
    )
    result = ClassificationResult(
        input_row_id=row.input_row_id,
        snapshot_id=snapshot.snapshot_id,
        input_validation_status=row.input_validation_status,
        input_errors=row.input_errors,
        match_status=match.match_status,
        matched_target_id=match.matched_target_id,
        candidate_target_ids=candidate_ids,
        iuphar_annotation_status=annotation_status,
        iuphar_class=direct_class,
        iuphar_subclass=direct.iuphar_subclass if direct else None,
        iuphar_class_candidates=outcome.iuphar_class_candidates,
        iuphar_type_raw=outcome.raw_type,
        iuphar_mapping_rule_id=rule_id,
        iuphar_mapping_version=snapshot.mapping_version if rule_id else None,
        local_status=local.local_status,
        local_class=local.local_class,
        local_subclasses=local.local_subclasses,
        local_rule_ids=(
            (*local.local_rule_ids, policy_evidence.source_id)
            if policy_evidence
            else local.local_rule_ids
        ),
        effective_class=outcome.effective_class,
        effective_subclasses=outcome.effective_subclasses,
        effective_source=outcome.effective_source,
        decision_status=outcome.decision_status,
        conflict_codes=outcome.conflict_codes,
        match_evidence_ids=evidence.match_evidence_ids,
        local_evidence_ids=evidence.local_evidence_ids,
        row_sha256=row.row_sha256,
        provenance=row.provenance,
        diagnostics=(
            *_classification_diagnostics(
                row, match, annotation, direct, local, evidence
            ),
            *(
                (
                    Diagnostic(
                        policy_evidence.source_id,
                        "info",
                        policy_evidence.content,
                        next(
                            item.evidence_id
                            for item in evidence.records
                            if item.source_id == policy_evidence.source_id
                        ),
                    ),
                )
                if policy_evidence
                else ()
            ),
        ),
    )
    require_class_chain(result, annotation=annotation, table=evidence)
    candidates = tuple(
        CandidateRow(row.input_row_id, x.target_id, x.match_method) for x in hits
    )
    return RowResult(
        row,
        result,
        evidence,
        candidates,
        direct,
        local,
        annotation,
        match.match_method,
        snapshot.mapping_version,
    )


def _components(row: RowResult, snapshot: IndexedSnapshot) -> tuple[ComponentRow, ...]:
    if (
        row.validated.input_validation_status != "valid"
        or row.validated.target_kind != "complex"
    ):
        return ()
    raw = row.validated.raw_fields.get("component_ids") or ""
    return tuple(
        _component_row(
            row.result.input_row_id, component_id, snapshot, row.validated.taxon
        )
        for component_id in _component_ids(raw)
    )


def _component_ids(raw: str) -> list[str]:
    return sorted({part.strip() for part in re.split(r"[;|]", raw) if part.strip()})


def _component_row(
    input_row_id: str,
    component_id: str,
    snapshot: IndexedSnapshot,
    taxon: str | None = None,
) -> ComponentRow:
    namespace, sep, key = component_id.partition(":")
    annotation = (
        _annotation(snapshot, key, taxon)
        if sep and namespace.casefold() == "iuphar"
        else None
    )
    direct = _direct(snapshot, annotation)
    return ComponentRow(
        input_row_id,
        component_id,
        annotation.type_raw if annotation else None,
        direct.iuphar_class if direct else None,
        direct.annotation_status if direct else "not_available",
        annotation.payload_sha256 if annotation else None,
    )


def _batch_metrics(results: list[RowResult], invalid: int) -> Mapping[str, int]:
    return MappingProxyType(
        {
            "rows": len(results),
            "invalid_rows": invalid,
            "classified_rows": sum(bool(x.result.effective_class) for x in results),
            "class_null": sum(x.result.effective_class is None for x in results),
        }
    )


def _batch_diagnostics(
    results: list[RowResult],
) -> tuple[tuple[str, Diagnostic], ...]:
    return tuple(
        (x.result.input_row_id, d)
        for x in results
        for d in _bound_diagnostics(
            (*x.validated.diagnostics, *x.result.diagnostics), x.evidence
        )
    )


def _batch_status(results: list[RowResult], invalid: int) -> str:
    if not results:
        return "empty"
    if invalid == len(results):
        return "rejected"
    return "processed"


def classify_batch(
    rows: tuple[RawTargetRow, ...],
    *,
    snapshot: IndexedSnapshot,
    provenance: RunProvenance,
    run_id: str,
    glue_fixtures: tuple[GlueFixture, ...] = (),
) -> BatchResult:
    """Classify a stable order of unique input IDs and keep all row diagnostics."""
    if snapshot.snapshot_id != provenance.snapshot_id or not run_id.strip():
        raise ValueError("missing run ID or mismatched snapshot provenance")
    validate_rules(local_rules())
    identities = [row.input_row_id for row in rows]
    if len(identities) != len(set(identities)):
        raise ValueError("duplicate input row identities")
    results: list[RowResult] = []
    for row in sorted(rows, key=lambda item: item.input_row_id):
        v = validate_input(
            row,
            provenance=provenance,
            glue_fixtures=glue_fixtures,
            catalog=snapshot.identifier_catalog,
        )
        results.append(classify_target(v, snapshot=snapshot, run_id=run_id))
    invalid = sum(x.result.input_validation_status == "invalid_input" for x in results)
    metrics = _batch_metrics(results, invalid)
    diagnostics = _batch_diagnostics(results)
    status = _batch_status(results, invalid)
    return BatchResult(
        status,
        tuple(results),
        tuple(dict.fromkeys(diagnostics)),
        metrics,
        tuple(item for row in results for item in _components(row, snapshot)),
    )
