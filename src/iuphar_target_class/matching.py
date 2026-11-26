"""Collect IUPHAR candidates. This component does not use HTTP."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, replace
from typing import cast

from .models import Diagnostic, MatchResult

EXPLICIT = "explicit_target_id"
UNIPROT = "uniprot_xref"
HGNC = "hgnc"
GENE_ID = "gene_id"
GENE_SYMBOL = "gene_symbol"
EXACT_NAME = "exact_name"
EXACT_SYNONYM = "exact_synonym"
METHOD_ORDER = (
    EXPLICIT,
    UNIPROT,
    HGNC,
    GENE_ID,
    GENE_SYMBOL,
    EXACT_NAME,
    EXACT_SYNONYM,
)
UNKNOWN_AUXILIARY = "unknown_auxiliary_uniprot"
AUXILIARY_DIVERGENCE = "auxiliary_uniprot_divergence"


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
    hgnc_ids: tuple[str, ...] = ()
    full_names: tuple[str, ...] | None = None


@dataclass(frozen=True, slots=True)
class MatchQuery:
    """Identifiers already normalized. Original text is not repaired here.

    ``uniprot_ids`` are primary/trusted anchors (exact channels).
    ``auxiliary_uniprot_ids`` are diagnostic-only cross-references (RF-002);
    they must not open empty exact-channels or qualify as identity_conflict.
    """

    target_id: str | None
    uniprot_ids: tuple[str, ...]
    gene_symbol: str | None
    gene_id: str | None
    organism: str | None
    name: str | None
    synonyms: tuple[str, ...]
    auxiliary_uniprot_ids: tuple[str, ...] = ()
    hgnc_ids: tuple[str, ...] = ()
    prioritize_anchors: bool = False
    ranked_text: bool = False
    use_synonyms: bool = True
    gene_aliases: tuple[str, ...] = ()


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
        All channel hits in canonical order. The applicable policy determines
        whether a unique same-species text hit can confirm identity.
    """
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
    if query.uniprot_ids:
        wanted = set(query.uniprot_ids)
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
    hgnc_ids = set(query.hgnc_ids) if query.organism == "9606" else set()
    return (
        *(
            Candidate(target.target_id, HGNC)
            for target in targets
            if hgnc_ids.intersection(target.hgnc_ids)
        ),
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
        names = set(target.names)
        full_names = target.names if target.full_names is None else target.full_names
        exact_name = (
            query.name in full_names if query.ranked_text else bool(names & wanted)
        )
        if exact_name:
            found.append(Candidate(target.target_id, EXACT_NAME))
        if query.use_synonyms and (
            set(target.synonyms) & wanted
            or (
                query.ranked_text
                and (
                    names.intersection(query.synonyms)
                    or (query.name in names and not exact_name)
                )
            )
        ):
            found.append(Candidate(target.target_id, EXACT_SYNONYM))
    return tuple(found)


def validate_identity(
    query: MatchQuery,
    catalog: tuple[CatalogTarget, ...],
    candidates: tuple[Candidate, ...],
    *,
    snapshot_complete: bool,
    auxiliary_catalog: tuple[CatalogTarget, ...] | None = None,
) -> MatchResult:
    """Turn the full candidate list into one match status.

    Parameters
    ----------
    query : MatchQuery
        Normalized query; this function does not validate the input-row schema.
        Primary ``uniprot_ids`` remain strict; ``auxiliary_uniprot_ids`` only
        contribute RF-002 diagnostics (see ``identifier_roles``).
    catalog : tuple[CatalogTarget, ...]
        Targets used for primary identity channels (may be a shortlist).
    candidates : tuple[Candidate, ...]
        Complete channel hits from ``collect_candidates``.
    snapshot_complete : bool
        Whether all required snapshot sources are present.
    auxiliary_catalog : tuple[CatalogTarget, ...] | None
        Optional broader catalog for auxiliary-xref diagnostics only. Defaults
        to ``catalog``. Must include auxiliary UniProt hits that are absent
        from a primary shortlist so divergence is not misreported as unknown.

    Returns
    -------
    MatchResult
        Conservative identity decision retaining all candidate ids. With no
        searchable query fields, ``not_found`` on a complete snapshot means
        no query-channel hits; it does not assert biological absence.
    """
    result = _decide(query, catalog, candidates, snapshot_complete=snapshot_complete)
    return _attach_auxiliary_diagnostics(
        query,
        catalog if auxiliary_catalog is None else auxiliary_catalog,
        result,
    )


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
    preferred = _preferred_identity(query, catalog, candidates)
    if preferred is not None:
        return preferred
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

    if query.ranked_text:
        text_match = _ranked_text_identity(query, catalog, candidates)
        if text_match is not None:
            return text_match
        exact_channels = [
            (method, ids)
            for method, ids in exact_channels
            if method in {EXPLICIT, UNIPROT}
        ]

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


def _ranked_text_identity(
    query: MatchQuery,
    catalog: tuple[CatalogTarget, ...],
    candidates: tuple[Candidate, ...],
) -> MatchResult | None:
    if query.organism is None or query.target_id is not None:
        return None
    for method in (EXACT_NAME, EXACT_SYNONYM):
        ids = _ids_of(candidates, method)
        if not ids:
            continue
        if len(ids) != 1:
            return None
        variants = tuple(
            t for t in _species_targets(query, catalog) if t.target_id == ids[0]
        )
        if variants and all(
            _compatible_text_variant(query, target)
            and (method == EXACT_NAME or _corroborates_synonym(query, target))
            for target in variants
        ):
            return _result("matched", ids[0], ids, (method,), ())
        return None
    return None


def _compatible_text_variant(query: MatchQuery, target: CatalogTarget) -> bool:
    pairs = (
        (query.uniprot_ids, target.uniprot_ids),
        (query.hgnc_ids, target.hgnc_ids),
        (
            (query.gene_id,) if query.gene_id else (),
            (target.gene_id,) if target.gene_id else (),
        ),
    )
    return all(
        not supplied or not recorded or not set(supplied).isdisjoint(recorded)
        for supplied, recorded in pairs
    )


def _corroborates_synonym(query: MatchQuery, target: CatalogTarget) -> bool:
    """A shared alias alone cannot identify a variant with sparse provider IDs."""
    gene_names = {value.casefold() for value in query.gene_aliases}
    if query.gene_symbol:
        gene_names.add(query.gene_symbol.casefold())
    return bool(
        (query.gene_id and query.gene_id == target.gene_id)
        or (target.gene_symbol and target.gene_symbol.casefold() in gene_names)
    )


def _preferred_identity(
    query: MatchQuery,
    catalog: tuple[CatalogTarget, ...],
    candidates: tuple[Candidate, ...],
) -> MatchResult | None:
    """Choose a same-species anchor before consulting lower-priority channels."""
    if not query.prioritize_anchors or query.organism is None:
        return None
    hgnc = _ids_of(candidates, HGNC)
    uniprot = _ids_of(candidates, UNIPROT)
    target_ids = _union(hgnc, uniprot)
    if not target_ids:
        return None
    species_conflict = _variant_species_conflict(query, catalog)
    if species_conflict is not None:
        return species_conflict
    anchor_channels = [(UNIPROT, uniprot), (HGNC, hgnc)]
    identity_conflict = _identity_conflict(
        [(EXPLICIT, _ids_of(candidates, EXPLICIT)), *anchor_channels]
    )
    if identity_conflict is not None:
        return identity_conflict
    methods = tuple(method for method, ids in anchor_channels if ids)
    if len(target_ids) == 1:
        return _result("matched", target_ids[0], target_ids, methods, ())
    return _result("ambiguous", None, target_ids, methods, ("ambiguous_match",))


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
    for accession in query.uniprot_ids:
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
    if query.uniprot_ids:
        variants = [
            item
            for item in variants
            if set(item.uniprot_ids).intersection(query.uniprot_ids)
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
        target for target in catalog if set(target.uniprot_ids) & set(query.uniprot_ids)
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
    if query.organism is None:
        return True
    return any(
        target.target_id == target_id
        and (not query.ranked_text or _compatible_text_variant(query, target))
        for target in _species_targets(query, catalog)
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
    for identifier in query.uniprot_ids:
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


def _attach_auxiliary_diagnostics(
    query: MatchQuery,
    catalog: tuple[CatalogTarget, ...],
    result: MatchResult,
) -> MatchResult:
    """Record unknown/divergent auxiliary UniProt xrefs without changing status.

    Auxiliary hits never open exact channels and never promote name-only rows
    to ``matched`` (RF-002 / ``identifier_roles.MATCHING_POLICY_VERSION``).
    """
    if not query.auxiliary_uniprot_ids:
        return result
    extras: list[Diagnostic] = []
    targets = _species_targets(query, catalog)
    for accession in query.auxiliary_uniprot_ids:
        hits = _ids(
            target.target_id for target in targets if accession in target.uniprot_ids
        )
        if not hits:
            extras.append(
                Diagnostic(
                    UNKNOWN_AUXILIARY,
                    "info",
                    f"{UNKNOWN_AUXILIARY}:{accession}",
                )
            )
            continue
        # RF-002: warn when any catalog hit differs from the primary decision,
        # even if the matched target is also among the hits.
        if result.matched_target_id is not None and any(
            target_id != result.matched_target_id for target_id in hits
        ):
            extras.append(
                Diagnostic(
                    AUXILIARY_DIVERGENCE,
                    "warning",
                    f"{AUXILIARY_DIVERGENCE}:{accession}",
                )
            )
    if not extras:
        return result
    return cast(
        MatchResult, replace(result, diagnostics=(*result.diagnostics, *extras))
    )
