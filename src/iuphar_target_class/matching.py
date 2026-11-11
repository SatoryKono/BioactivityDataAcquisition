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
            for target in catalog
            if set(target.uniprot_ids) & wanted
            and (query.organism is None or target.species == query.organism)
        )
    if query.organism is not None:
        found.extend(
            Candidate(target.target_id, GENE_ID)
            for target in catalog
            if query.gene_id is not None
            and target.gene_id == query.gene_id
            and target.species == query.organism
        )
        found.extend(
            Candidate(target.target_id, GENE_SYMBOL)
            for target in catalog
            if query.gene_symbol is not None
            and target.gene_symbol == query.gene_symbol
            and target.species == query.organism
        )
    wanted_names = {query.name} if query.name is not None else set()
    wanted_synonyms = set(query.synonyms)
    for target in catalog:
        if query.organism is not None and target.species != query.organism:
            continue
        if set(target.names) & wanted_names:
            found.append(Candidate(target.target_id, EXACT_NAME))
        if set(target.synonyms) & wanted_synonyms:
            found.append(Candidate(target.target_id, EXACT_SYNONYM))
    return tuple(
        sorted(
            found,
            key=lambda item: (item.target_id, METHOD_ORDER.index(item.match_method)),
        )
    )


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
    gene_blocked = query.organism is None and (
        query.gene_symbol is not None or query.gene_id is not None
    )
    exact_channels = _exact_channels(query, catalog, candidates)
    conflict_channels = _exact_channels(query, catalog, candidates, unfiltered=True)
    everyone = _union(explicit, uniprot, gene_id, gene_symbol, named)
    nonempty = [(method, ids) for method, ids in conflict_channels if ids]
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
    if uniprot_species_gap or (gene_blocked and not _single_agreement(exact_channels)):
        return _result(
            "insufficient_input",
            None,
            everyone,
            _methods(candidates, set(everyone)),
            ("insufficient_input",),
        )

    agreed = _single_agreement(exact_channels)
    if agreed is not None and set(everyone) == {agreed}:
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
    hits = [
        target for target in catalog if set(target.uniprot_ids) & set(query.uniprot_ids)
    ]
    if query.organism is not None:
        hits = [target for target in hits if target.species == query.organism]
        return _ids(target.target_id for target in hits), False
    species = {target.species for target in hits}
    if len(species) > 1:
        return _ids(target.target_id for target in hits), True
    return _ids(target.target_id for target in hits), False


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
    for identifier in query.uniprot_ids:
        hits = _ids(
            target.target_id
            for target in catalog
            if identifier in target.uniprot_ids
            and (
                unfiltered or query.organism is None or target.species == query.organism
            )
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
