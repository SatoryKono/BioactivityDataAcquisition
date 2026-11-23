"""Collect IUPHAR candidates. This component does not use HTTP.

``iuphar-matching-strict-anchors-v1`` treats every supplied UniProt id as a
required exact anchor. ``iuphar-matching-role-separated-v2`` keeps that rule
for primary accessions and proven equivalents. Auxiliary UniProt
cross-references stay in the result as diagnostics. Exact name and synonym
channels are evidence only and cannot confirm identity. A component accession
does not prove a complex or a family.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from .models import Diagnostic, MatchResult

EXPLICIT = "explicit_target_id"
UNIPROT = "uniprot_xref"
GENE_ID = "gene_id"
GENE_SYMBOL = "gene_symbol"
EXACT_NAME = "exact_name"
EXACT_SYNONYM = "exact_synonym"
METHOD_ORDER = (
    EXPLICIT,
    UNIPROT,
    GENE_ID,
    GENE_SYMBOL,
    EXACT_NAME,
    EXACT_SYNONYM,
)
# Name and synonym hits are evidence. They never confirm identity alone.
TEXT_CHANNEL_EVIDENCE_ROLE = "evidence_only"
MATCHING_POLICY_STRICT_ANCHORS_V1 = "iuphar-matching-strict-anchors-v1"
MATCHING_POLICY_ROLE_SEPARATED_V2 = "iuphar-matching-role-separated-v2"
_KNOWN_POLICIES = frozenset(
    {MATCHING_POLICY_STRICT_ANCHORS_V1, MATCHING_POLICY_ROLE_SEPARATED_V2}
)
_OBJECT_SCOPES = frozenset({None, "protein", "complex", "family"})
_COMPONENT_SCOPES = frozenset({"complex", "family"})
# Empty until a reviewed normalization profile explicitly names role-separated matching.
_QUALIFIED_MATCHING_PROFILES: frozenset[tuple[str, str, str, str]] = frozenset()


@dataclass(frozen=True, slots=True)
class CatalogTarget:
    """One snapshot target used by matching."""

    target_id: str
    uniprot_ids: tuple[str, ...]
    gene_symbol: str | None
    gene_id: str | None
    species: str | None
    names: tuple[str, ...]
    synonyms: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class MatchQuery:
    """Identifiers already normalized. Original text is not repaired here."""

    target_id: str | None
    uniprot_ids: tuple[str, ...]
    gene_symbol: str | None
    gene_id: str | None
    organism: str | None
    name: str | None
    synonyms: tuple[str, ...]
    auxiliary_uniprot_ids: tuple[str, ...] = ()
    equivalent_uniprot_ids: tuple[str, ...] = ()
    matching_policy: str = MATCHING_POLICY_STRICT_ANCHORS_V1
    object_scope: str | None = None


@dataclass(frozen=True, slots=True)
class CrossReference:
    """One provider cross-reference. Selection uses the database id, not position."""

    database: str
    identifier: str


@dataclass(frozen=True, slots=True)
class Candidate:
    """One channel hit. The list order does not choose the status."""

    target_id: str
    match_method: str


def profile_qualifies_matching_policy(
    *,
    profile_name: str,
    profile_version: str,
    profile_hash: str,
    matching_policy: str,
) -> bool:
    """Return whether a normalization profile explicitly qualifies a policy.

    Historical ChEMBL target profiles predate role-separated matching. Their
    name, version, and hash do not qualify ``MATCHING_POLICY_ROLE_SEPARATED_V2``.
    """
    if matching_policy != MATCHING_POLICY_ROLE_SEPARATED_V2:
        return False
    binding = (profile_name, profile_version, profile_hash, matching_policy)
    return binding in _QUALIFIED_MATCHING_PROFILES


def explain_policy_change(previous: MatchResult, current: MatchResult) -> str:
    """Explain one old-policy result against the role-separated result.

    Parameters
    ----------
    previous : MatchResult
        Decision under strict merged anchors.
    current : MatchResult
        Decision under role-separated UniProt roles.

    Returns
    -------
    str
        A stable explanation code. Unknown auxiliary links may add a match;
        they never explain a new conflict or a lost reliable match.
    """
    same_target = previous.matched_target_id == current.matched_target_id
    if previous.match_status == current.match_status == "matched" and same_target:
        return "unchanged_reliable_primary"
    current_codes = {item.code for item in current.diagnostics}
    unknown_auxiliary = (
        previous.match_status == "ambiguous"
        and current.match_status == "matched"
        and "auxiliary_uniprot_unresolved" in current_codes
        and "identity_conflict" not in current_codes
    )
    if unknown_auxiliary:
        return "unknown_auxiliary_uniprot_is_not_a_required_anchor"
    if previous.match_status == current.match_status == "ambiguous":
        return "remaining_ambiguous_channel"
    if previous.match_status == current.match_status and same_target:
        return f"unchanged_{previous.match_status}"
    return "unexpected_policy_delta"


def describe_ambiguous_channels(query: MatchQuery, result: MatchResult) -> str:
    """Name the channel pattern that keeps a role-separated row ambiguous.

    Text channels stay evidence. A single resolved primary accession with an
    extra text hit, a shared accession, or a missing required anchor does not
    become a match.
    """
    if result.match_status != "ambiguous":
        message = "ambiguous channel description requires ambiguous status"
        raise ValueError(message)
    methods = set(result.match_method)
    text = methods & {EXACT_NAME, EXACT_SYNONYM}
    if UNIPROT in methods and text and len(result.candidate_target_ids) > 1:
        return "primary_and_other_name"
    if methods == {EXACT_NAME}:
        return "exact_name"
    if methods == {EXACT_SYNONYM}:
        return "exact_synonym"
    if methods == {UNIPROT} and len(result.candidate_target_ids) > 1:
        return "shared_primary"
    if (
        methods == {UNIPROT}
        and len(result.candidate_target_ids) == 1
        and len(_required_uniprot_ids(query)) > 1
    ):
        return "partial_required_anchor"
    return "unclassified"


def select_uniprot_accessions(
    references: tuple[CrossReference, ...],
) -> tuple[str, ...]:
    """Keep UniProt accessions wherever they sit in the provider list.

    Parameters
    ----------
    references : tuple[CrossReference, ...]
        Snapshot cross-references in provider order.

    Returns
    -------
    tuple[str, ...]
        Accessions whose database id is UniProt, in their original order.
    """
    return tuple(
        item.identifier for item in references if item.database.casefold() == "uniprot"
    )


def collect_candidates(
    query: MatchQuery,
    catalog: tuple[CatalogTarget, ...],
) -> tuple[Candidate, ...]:
    """Ask every channel. The first hit does not stop the search.

    Parameters
    ----------
    query : MatchQuery
        Normalized identifiers and text; name and synonyms search both text fields.
    catalog : tuple[CatalogTarget, ...]
        Snapshot targets, without network access.

    Returns
    -------
    tuple[Candidate, ...]
        All channel hits in canonical order. Text hits identify the provider
        field that matched and cannot confirm identity on their own.
    """
    _check_query(query)
    found = (
        *_identifier_candidates(query, catalog),
        *_gene_candidates(query, catalog),
        *_name_candidates(query, catalog),
    )
    return tuple(
        sorted(
            set(found),
            key=lambda item: (item.target_id, METHOD_ORDER.index(item.match_method)),
        )
    )


def _species_targets(
    query: MatchQuery, catalog: tuple[CatalogTarget, ...]
) -> tuple[CatalogTarget, ...]:
    if query.organism is None:
        return catalog
    return tuple(target for target in catalog if target.species == query.organism)


def _identifier_candidates(
    query: MatchQuery, catalog: tuple[CatalogTarget, ...]
) -> tuple[Candidate, ...]:
    found: list[Candidate] = []
    if query.target_id is not None:
        found.extend(
            Candidate(target.target_id, EXPLICIT)
            for target in catalog
            if target.target_id == query.target_id
        )
    required_uniprot = _required_uniprot_ids(query)
    if required_uniprot:
        wanted = set(required_uniprot)
        found.extend(
            Candidate(target.target_id, UNIPROT)
            for target in _species_targets(query, catalog)
            if set(target.uniprot_ids) & wanted
        )
    return tuple(found)


def _gene_candidates(
    query: MatchQuery, catalog: tuple[CatalogTarget, ...]
) -> tuple[Candidate, ...]:
    if query.organism is None:
        return ()
    targets = _species_targets(query, catalog)
    return (
        *(
            Candidate(target.target_id, GENE_ID)
            for target in targets
            if query.gene_id is not None and target.gene_id == query.gene_id
        ),
        *(
            Candidate(target.target_id, GENE_SYMBOL)
            for target in targets
            if query.gene_symbol is not None and target.gene_symbol == query.gene_symbol
        ),
    )


def _name_candidates(
    query: MatchQuery, catalog: tuple[CatalogTarget, ...]
) -> tuple[Candidate, ...]:
    found: list[Candidate] = []
    wanted = set(query.synonyms)
    if query.name is not None:
        wanted.add(query.name)
    for target in _species_targets(query, catalog):
        if set(target.names) & wanted:
            found.append(Candidate(target.target_id, EXACT_NAME))
        if set(target.synonyms) & wanted:
            found.append(Candidate(target.target_id, EXACT_SYNONYM))
    return tuple(found)


def validate_identity(
    query: MatchQuery,
    catalog: tuple[CatalogTarget, ...],
    candidates: tuple[Candidate, ...],
    *,
    snapshot_complete: bool,
) -> MatchResult:
    """Turn the full candidate list into one match status.

    Parameters
    ----------
    query : MatchQuery
        Normalized query; this function does not validate the input-row schema.
    catalog : tuple[CatalogTarget, ...]
        Targets from the same snapshot used to collect candidates.
    candidates : tuple[Candidate, ...]
        Complete channel hits from ``collect_candidates``.
    snapshot_complete : bool
        Whether all required snapshot sources are present.

    Returns
    -------
    MatchResult
        Conservative identity decision retaining all candidate ids. With no
        searchable query fields, ``not_found`` on a complete snapshot means
        no query-channel hits; it does not assert biological absence.
        Role-separated policy keeps auxiliary UniProt links out of required
        exact channels. A component accession does not prove a complex or family.
    """
    _check_query(query)
    decided = _decide(query, catalog, candidates, snapshot_complete=snapshot_complete)
    return _apply_role_policy(query, catalog, decided)


def resolve_match(
    query: MatchQuery,
    catalog: tuple[CatalogTarget, ...],
    *,
    snapshot_complete: bool,
) -> MatchResult:
    """Search every channel, then choose one status. Catalog order is ignored.

    Parameters
    ----------
    query : MatchQuery
        Normalized query, validated separately from this pure matching API.
    catalog : tuple[CatalogTarget, ...]
        Provider targets belonging to one snapshot.
    snapshot_complete : bool
        Whether the snapshot contains all required sources.

    Returns
    -------
    MatchResult
        Complete candidates and their identity decision. Multiple compatible
        candidates remain ambiguous; shared identifiers are not silently
        narrowed into a confirmed match.
    """
    return validate_identity(
        query,
        catalog,
        collect_candidates(query, catalog),
        snapshot_complete=snapshot_complete,
    )


def _decide(
    query: MatchQuery,
    catalog: tuple[CatalogTarget, ...],
    candidates: tuple[Candidate, ...],
    *,
    snapshot_complete: bool,
) -> MatchResult:
    """Choose one status from every channel. Catalog order is ignored."""
    explicit = _ids_of(candidates, EXPLICIT)
    uniprot = _ids_of(candidates, UNIPROT)
    gene_id = _ids_of(candidates, GENE_ID)
    gene_symbol = _ids_of(candidates, GENE_SYMBOL)
    named = _ids_of(candidates, EXACT_NAME, EXACT_SYNONYM)
    _, uniprot_species_gap = _uniprot_ids(query, catalog)
    exact_channels = _exact_channels(query, catalog, candidates)
    conflict_channels = _exact_channels(query, catalog, candidates, unfiltered=True)
    everyone = _union(explicit, uniprot, gene_id, gene_symbol, named)
    conflict = _identity_conflict(conflict_channels)
    if conflict is not None:
        return conflict
    species_conflict = _variant_species_conflict(query, catalog)
    if species_conflict is not None:
        return species_conflict
    if _missing_identity_input(query, uniprot_species_gap) or _explicit_species_gap(
        query, catalog
    ):
        return _result(
            "insufficient_input",
            None,
            everyone,
            _methods(candidates, set(everyone)),
            ("insufficient_input",),
        )

    agreed = _single_agreement(exact_channels)
    if (
        agreed is not None
        and set(everyone) == {agreed}
        and _matches_requested_species(query, catalog, agreed)
    ):
        return _result(
            "matched",
            agreed,
            (agreed,),
            _methods(candidates, {agreed}),
            (),
        )
    if everyone:
        return _result(
            "ambiguous",
            None,
            everyone,
            _methods(candidates, set(everyone)),
            ("ambiguous_match",),
        )
    if not snapshot_complete:
        return _result("source_unavailable", None, (), (), ("source_unavailable",))
    return _result("not_found", None, (), (), ())


def _identity_conflict(
    channels: list[tuple[str, tuple[str, ...]]],
) -> MatchResult | None:
    nonempty = [(method, ids) for method, ids in channels if ids]
    if len(nonempty) >= 2 and not set.intersection(*(set(ids) for _, ids in nonempty)):
        conflict_ids = _union(*(ids for _, ids in nonempty))
        methods = {method for method, _ in nonempty}
        return _result(
            "identity_conflict",
            None,
            conflict_ids,
            tuple(method for method in METHOD_ORDER if method in methods),
            ("identity_conflict",),
        )
    return None


def _variant_species_conflict(
    query: MatchQuery, catalog: tuple[CatalogTarget, ...]
) -> MatchResult | None:
    """A shared public ID cannot hide contradictory species-specific accessions."""
    if query.organism is None:
        return None
    variants = _multiple_species_ids(catalog)
    for accession in _required_uniprot_ids(query):
        hits = _wrong_species_hits(query, catalog, accession)
        if any(item.target_id in variants for item in hits):
            return _result(
                "identity_conflict",
                None,
                _ids(item.target_id for item in hits),
                (UNIPROT,),
                ("identity_conflict",),
            )
    return None


def _multiple_species_ids(catalog: tuple[CatalogTarget, ...]) -> set[str]:
    variants: dict[str, set[str | None]] = {}
    for target in catalog:
        variants.setdefault(target.target_id, set()).add(target.species)
    return {key for key, species in variants.items() if len(species) > 1}


def _wrong_species_hits(
    query: MatchQuery, catalog: tuple[CatalogTarget, ...], accession: str
) -> list[CatalogTarget]:
    hits = [item for item in catalog if accession in item.uniprot_ids]
    if any(item.species == query.organism for item in hits):
        return []
    return hits


def _explicit_species_gap(
    query: MatchQuery, catalog: tuple[CatalogTarget, ...]
) -> bool:
    if query.organism is not None or query.target_id is None:
        return False
    variants = [item for item in catalog if item.target_id == query.target_id]
    required_uniprot = _required_uniprot_ids(query)
    if required_uniprot:
        variants = [
            item
            for item in variants
            if set(item.uniprot_ids).intersection(required_uniprot)
        ]
    return len({item.species for item in variants}) > 1


def _missing_identity_input(
    query: MatchQuery,
    uniprot_species_gap: bool,
) -> bool:
    gene_blocked = query.organism is None and (
        query.gene_symbol is not None or query.gene_id is not None
    )
    return uniprot_species_gap or gene_blocked


def enforce_match_invariant(result: MatchResult) -> MatchResult:
    """Matched requires a target id. Any other status must not carry one."""
    matched_without_id = (
        result.match_status == "matched" and not result.matched_target_id
    )
    id_without_matched = (
        bool(result.matched_target_id) and result.match_status != "matched"
    )
    if matched_without_id or id_without_matched:
        return MatchResult(
            match_status="contract_error",
            matched_target_id=None,
            candidate_target_ids=result.candidate_target_ids,
            match_method=(),
            match_evidence_ids=result.match_evidence_ids,
            diagnostics=(
                Diagnostic(
                    "contract_error",
                    "error",
                    "matched_target_id is inconsistent with match_status",
                ),
            ),
        )
    return result


def _uniprot_ids(
    query: MatchQuery,
    catalog: tuple[CatalogTarget, ...],
) -> tuple[tuple[str, ...], bool]:
    hits = tuple(
        target
        for target in catalog
        if set(target.uniprot_ids) & set(_required_uniprot_ids(query))
    )
    selected = _species_targets(query, hits)
    species_gap = (
        query.organism is None and len({target.species for target in hits}) > 1
    )
    return _ids(target.target_id for target in selected), species_gap


def _ids_of(candidates: tuple[Candidate, ...], *methods: str) -> tuple[str, ...]:
    selected = set(methods)
    return _ids(
        candidate.target_id
        for candidate in candidates
        if candidate.match_method in selected
    )


def _methods(
    candidates: tuple[Candidate, ...], target_ids: set[str]
) -> tuple[str, ...]:
    found = {
        candidate.match_method
        for candidate in candidates
        if candidate.target_id in target_ids
    }
    return tuple(method for method in METHOD_ORDER if method in found)


def _matches_requested_species(
    query: MatchQuery, catalog: tuple[CatalogTarget, ...], target_id: str
) -> bool:
    return query.organism is None or any(
        target.target_id == target_id and target.species == query.organism
        for target in catalog
    )


def _exact_channels(
    query: MatchQuery,
    catalog: tuple[CatalogTarget, ...],
    candidates: tuple[Candidate, ...],
    *,
    unfiltered: bool = False,
) -> list[tuple[str, tuple[str, ...]]]:
    channels: list[tuple[str, tuple[str, ...]]] = []
    if query.target_id is not None:
        channels.append((EXPLICIT, _ids_of(candidates, EXPLICIT)))
    targets = catalog if unfiltered else _species_targets(query, catalog)
    # Text channels stay evidence-only and are intentionally absent here.
    for identifier in _required_uniprot_ids(query):
        hits = _ids(
            target.target_id for target in targets if identifier in target.uniprot_ids
        )
        channels.append((UNIPROT, hits))
    if query.organism is not None:
        channels.extend(
            (method, _ids_of(candidates, method))
            for method, supplied in (
                (GENE_ID, query.gene_id),
                (GENE_SYMBOL, query.gene_symbol),
            )
            if supplied is not None
        )
    return channels


def _single_agreement(
    channels: list[tuple[str, tuple[str, ...]]],
) -> str | None:
    nonempty = [set(ids) for _, ids in channels]
    if not nonempty:
        return None
    shared = set.intersection(*nonempty)
    if len(shared) == 1 and all(item == shared for item in nonempty):
        return next(iter(shared))
    return None


def _ids(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(sorted(set(values)))


def _union(*groups: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(sorted({value for group in groups for value in group}))


def _result(
    status: str,
    matched: str | None,
    candidates: tuple[str, ...],
    method: tuple[str, ...],
    codes: tuple[str, ...],
) -> MatchResult:
    diagnostics = tuple(Diagnostic(code, "warning", code) for code in codes)
    return enforce_match_invariant(
        MatchResult(
            match_status=status,
            matched_target_id=matched,
            candidate_target_ids=candidates,
            match_method=method,
            match_evidence_ids=(),
            diagnostics=diagnostics,
        )
    )


def _check_query(query: MatchQuery) -> None:
    """Reject an unknown policy or object scope before any candidate is kept."""
    if query.matching_policy not in _KNOWN_POLICIES:
        message = f"unknown matching policy: {query.matching_policy}"
        raise ValueError(message)
    if query.object_scope not in _OBJECT_SCOPES:
        message = f"unknown object scope: {query.object_scope}"
        raise ValueError(message)


def _required_uniprot_ids(query: MatchQuery) -> tuple[str, ...]:
    """UniProt anchors that must agree. Auxiliary cross-references are excluded.

    Strict policy keeps every supplied accession required. Role-separated policy
    adds proven equivalents and leaves auxiliary cross-references diagnostic.
    Input order is preserved; matching itself is order-independent.
    """
    if query.matching_policy != MATCHING_POLICY_ROLE_SEPARATED_V2:
        return query.uniprot_ids
    return tuple(dict.fromkeys((*query.uniprot_ids, *query.equivalent_uniprot_ids)))


def _apply_role_policy(
    query: MatchQuery,
    catalog: tuple[CatalogTarget, ...],
    result: MatchResult,
) -> MatchResult:
    """Record auxiliary evidence and refuse component-only complex identity."""
    return _apply_object_scope(query, _apply_auxiliary(query, catalog, result))


def _apply_auxiliary(
    query: MatchQuery,
    catalog: tuple[CatalogTarget, ...],
    result: MatchResult,
) -> MatchResult:
    if query.matching_policy != MATCHING_POLICY_ROLE_SEPARATED_V2:
        return result
    notes, disagree, extra_ids = _auxiliary_findings(query, catalog, result)
    if not notes:
        return result
    status = result.match_status
    matched = result.matched_target_id
    candidates = result.candidate_target_ids
    diagnostics = result.diagnostics
    if extra_ids:
        candidates = _ids((*candidates, *extra_ids))
    # Only a confirmed reliable match can be withdrawn. An auxiliary hit must
    # not turn source_unavailable or not_found into ambiguous: those statuses
    # still carry the incomplete-snapshot and absence decisions.
    if disagree and status == "matched":
        status = "ambiguous"
        matched = None
        if not any(item.code == "ambiguous_match" for item in diagnostics):
            diagnostics = (
                *diagnostics,
                Diagnostic("ambiguous_match", "warning", "ambiguous_match"),
            )
    return enforce_match_invariant(
        MatchResult(
            match_status=status,
            matched_target_id=matched,
            candidate_target_ids=candidates,
            match_method=result.match_method,
            match_evidence_ids=result.match_evidence_ids,
            diagnostics=(*diagnostics, *notes),
        )
    )


def _auxiliary_findings(
    query: MatchQuery,
    catalog: tuple[CatalogTarget, ...],
    result: MatchResult,
) -> tuple[tuple[Diagnostic, ...], bool, tuple[str, ...]]:
    notes: list[Diagnostic] = []
    extra: list[str] = []
    disagree = False
    agreed = result.matched_target_id
    for accession in tuple(sorted(set(query.auxiliary_uniprot_ids))):
        species_hits = [
            item
            for item in _species_targets(query, catalog)
            if accession in item.uniprot_ids
        ]
        any_hits = [item for item in catalog if accession in item.uniprot_ids]
        species_ids = _ids(item.target_id for item in species_hits)
        if not species_ids and any_hits and query.organism is not None:
            notes.append(
                Diagnostic(
                    "auxiliary_uniprot_outside_species",
                    "warning",
                    f"auxiliary UniProt {accession} has no in-species anchor",
                )
            )
            continue
        if not species_ids:
            notes.append(
                Diagnostic(
                    "auxiliary_uniprot_unresolved",
                    "warning",
                    f"auxiliary UniProt {accession} is not a required anchor",
                )
            )
            continue
        if agreed is not None and species_ids == (agreed,):
            notes.append(
                Diagnostic(
                    "auxiliary_uniprot_corroborated",
                    "warning",
                    f"auxiliary UniProt {accession} corroborates {agreed}",
                )
            )
            continue
        disagree = True
        extra.extend(species_ids)
        notes.append(
            Diagnostic(
                "auxiliary_uniprot_disagreement",
                "warning",
                f"auxiliary UniProt {accession} does not confirm the object",
            )
        )
    return tuple(notes), disagree, _ids(extra)


def _apply_object_scope(query: MatchQuery, result: MatchResult) -> MatchResult:
    """A subunit accession is not the identity of a complex or family."""
    if query.object_scope not in _COMPONENT_SCOPES:
        return result
    if result.match_status != "matched" or EXPLICIT in result.match_method:
        return result
    return enforce_match_invariant(
        MatchResult(
            match_status="ambiguous",
            matched_target_id=None,
            candidate_target_ids=result.candidate_target_ids,
            match_method=result.match_method,
            match_evidence_ids=result.match_evidence_ids,
            diagnostics=(
                *result.diagnostics,
                Diagnostic("ambiguous_match", "warning", "ambiguous_match"),
                Diagnostic(
                    "component_accession_not_object_identity",
                    "warning",
                    "a component accession does not prove complex or family identity",
                ),
            ),
        )
    )
