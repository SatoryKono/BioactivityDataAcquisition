"""Collect IUPHAR candidates. This component does not use HTTP."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from .models import Diagnostic, MatchResult

EXPLICIT = "explicit_target_id"
UNIPROT = "uniprot"
GENE = "gene"
EXACT_NAME = "exact_name"
EXACT_SYNONYM = "exact_synonym"


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


def resolve_match(
    query: MatchQuery,
    catalog: tuple[CatalogTarget, ...],
    *,
    snapshot_complete: bool,
) -> MatchResult:
    """Search every channel, then choose one status. Catalog order is ignored."""
    explicit = _ids(
        target.target_id
        for target in catalog
        if query.target_id is not None and target.target_id == query.target_id
    )
    uniprot, uniprot_species_gap = _uniprot_ids(query, catalog)
    gene, gene_blocked = _gene_ids(query, catalog)
    named = _name_ids(query, catalog)

    exact_channels: list[tuple[str, tuple[str, ...]]] = []
    if query.target_id is not None:
        exact_channels.append((EXPLICIT, explicit))
    if query.uniprot_ids:
        exact_channels.append((UNIPROT, uniprot))
    if (query.gene_symbol or query.gene_id) and not gene_blocked:
        exact_channels.append((GENE, gene))

    if uniprot_species_gap or (gene_blocked and not _single_agreement(exact_channels)):
        return _result(
            "insufficient_input",
            None,
            _union(explicit, uniprot, gene, named),
            None,
            ("insufficient_input",),
        )

    nonempty = [(method, ids) for method, ids in exact_channels if ids]
    if len(nonempty) >= 2 and not set.intersection(*(set(ids) for _, ids in nonempty)):
        return _result(
            "identity_conflict",
            None,
            _union(*(ids for _, ids in nonempty)),
            None,
            ("identity_conflict",),
        )
    agreed = _single_agreement(exact_channels)
    if agreed is not None:
        method = next(method for method, ids in nonempty if agreed in ids)
        return _result("matched", agreed, (agreed,), method, ())

    if named:
        method = _name_method(query, catalog, named)
        return _result("ambiguous", None, named, method, ("exact_name_or_synonym",))

    if any(ids for _, ids in exact_channels):
        found = _union(*(ids for _, ids in exact_channels))
        return _result("ambiguous", None, found, nonempty[0][0], ("ambiguous_match",))

    if not snapshot_complete:
        return _result("source_unavailable", None, (), None, ("source_unavailable",))
    return _result("not_found", None, (), None, ())


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
            match_method=None,
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


def _gene_ids(
    query: MatchQuery,
    catalog: tuple[CatalogTarget, ...],
) -> tuple[tuple[str, ...], bool]:
    if query.gene_symbol is None and query.gene_id is None:
        return (), False
    if query.organism is None:
        return (), True
    hits = [
        target.target_id
        for target in catalog
        if target.species == query.organism
        and (
            (query.gene_symbol is not None and target.gene_symbol == query.gene_symbol)
            or (query.gene_id is not None and target.gene_id == query.gene_id)
        )
    ]
    return _ids(hits), False


def _name_ids(query: MatchQuery, catalog: tuple[CatalogTarget, ...]) -> tuple[str, ...]:
    wanted_names = {query.name} if query.name is not None else set()
    wanted_synonyms = set(query.synonyms)
    return _ids(
        target.target_id
        for target in catalog
        if set(target.names) & wanted_names or set(target.synonyms) & wanted_synonyms
    )


def _name_method(
    query: MatchQuery,
    catalog: tuple[CatalogTarget, ...],
    named: tuple[str, ...],
) -> str:
    by_id = {target.target_id: target for target in catalog}
    wanted = {query.name} if query.name is not None else set()
    if any(set(by_id[target_id].names) & wanted for target_id in named):
        return EXACT_NAME
    return EXACT_SYNONYM


def _single_agreement(
    channels: list[tuple[str, tuple[str, ...]]],
) -> str | None:
    nonempty = [set(ids) for _, ids in channels if ids]
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
    method: str | None,
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
