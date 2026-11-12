"""Collect IUPHAR candidates. This component does not use HTTP."""

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
    """Keep UniProt accessions wherever they sit in the provider list."""
    return tuple(
        item.identifier for item in references if item.database.casefold() == "uniprot"
    )


def collect_candidates(
    query: MatchQuery,
    catalog: tuple[CatalogTarget, ...],
) -> tuple[Candidate, ...]:
    """Ask every channel. The first hit does not stop the search."""
    found = (
        *_identifier_candidates(query, catalog),
        *_gene_candidates(query, catalog),
        *_name_candidates(query, catalog),
    )
    return tuple(
        sorted(
            found,
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
    wanted_names = {query.name} if query.name is not None else set()
    wanted_synonyms = set(query.synonyms)
    for target in _species_targets(query, catalog):
        if set(target.names) & wanted_names:
            found.append(Candidate(target.target_id, EXACT_NAME))
        if set(target.synonyms) & wanted_synonyms:
            found.append(Candidate(target.target_id, EXACT_SYNONYM))
    return tuple(found)


def validate_identity(
    query: MatchQuery,
    catalog: tuple[CatalogTarget, ...],
    candidates: tuple[Candidate, ...],
    *,
    snapshot_complete: bool,
) -> MatchResult:
    """Turn the full candidate list into one match status."""
    return _decide(query, catalog, candidates, snapshot_complete=snapshot_complete)


def resolve_match(
    query: MatchQuery,
    catalog: tuple[CatalogTarget, ...],
    *,
    snapshot_complete: bool,
) -> MatchResult:
    """Search every channel, then choose one status. Catalog order is ignored."""
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
    if _missing_identity_input(query, uniprot_species_gap):
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
