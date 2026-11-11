"""TC-05 matching: channels, species, and the matched-id invariant."""

from __future__ import annotations

import pytest

from iuphar_target_class.matching import (
    CatalogTarget,
    CrossReference,
    MatchQuery,
    enforce_match_invariant,
    resolve_match,
    select_uniprot_accessions,
)
from iuphar_target_class.models import MatchResult

pytestmark = pytest.mark.unit


def _target(
    target_id: str,
    *,
    uniprot: str | None = None,
    gene: str | None = None,
    species: str | None = None,
    name: str | None = None,
    synonym: str | None = None,
) -> CatalogTarget:
    return CatalogTarget(
        target_id=target_id,
        uniprot_ids=(uniprot,) if uniprot else (),
        gene_symbol=gene,
        gene_id=None,
        species=species,
        names=(name,) if name else (),
        synonyms=(synonym,) if synonym else (),
    )


def _query(
    *,
    target_id: str | None = None,
    uniprot_ids: tuple[str, ...] = (),
    gene_symbol: str | None = None,
    organism: str | None = None,
    name: str | None = None,
    synonyms: tuple[str, ...] = (),
) -> MatchQuery:
    return MatchQuery(
        target_id,
        uniprot_ids,
        gene_symbol,
        None,
        organism,
        name,
        synonyms,
    )


def test_catalog_order_does_not_change_the_result() -> None:
    first = (
        _target("2", uniprot="P35372", species="human"),
        _target("1", uniprot="P35372", species="human"),
    )
    second = (first[1], first[0])
    query = _query(uniprot_ids=("P35372",))
    assert resolve_match(query, first, snapshot_complete=True) == resolve_match(
        query, second, snapshot_complete=True
    )


def test_one_uniprot_with_several_targets_is_ambiguous() -> None:
    catalog = (
        _target("1", uniprot="P35372", species="human"),
        _target("2", uniprot="P35372", species="human"),
    )
    result = resolve_match(
        _query(uniprot_ids=("P35372",), organism="human"),
        catalog,
        snapshot_complete=True,
    )
    assert result.match_status == "ambiguous"
    assert result.matched_target_id is None
    assert result.candidate_target_ids == ("1", "2")


def test_same_gene_symbol_in_different_species() -> None:
    catalog = (
        _target("human-id", gene="OPRM1", species="human"),
        _target("mouse-id", gene="OPRM1", species="mouse"),
    )
    human = resolve_match(
        _query(gene_symbol="OPRM1", organism="human"),
        catalog,
        snapshot_complete=True,
    )
    assert human.match_status == "matched"
    assert human.matched_target_id == "human-id"
    missing_species = resolve_match(
        _query(gene_symbol="OPRM1"),
        catalog,
        snapshot_complete=True,
    )
    assert missing_species.match_status == "insufficient_input"


def test_explicit_target_id_conflicting_with_uniprot() -> None:
    catalog = (
        _target("1", uniprot="P11111", species="human"),
        _target("2", uniprot="P22222", species="human"),
    )
    result = resolve_match(
        _query(target_id="1", uniprot_ids=("P22222",), organism="human"),
        catalog,
        snapshot_complete=True,
    )
    assert result.match_status == "identity_conflict"
    assert result.matched_target_id is None
    assert result.candidate_target_ids == ("1", "2")


def test_exact_name_does_not_become_matched() -> None:
    catalog = (_target("1", name="Mu opioid receptor", species="human"),)
    result = resolve_match(
        _query(name="Mu opioid receptor"),
        catalog,
        snapshot_complete=True,
    )
    assert result.match_status == "ambiguous"
    assert result.match_method == ("exact_name",)
    assert result.matched_target_id is None
    assert result.candidate_target_ids == ("1",)


def test_exact_synonym_does_not_become_matched() -> None:
    catalog = (_target("1", synonym="MOR", species="human"),)
    result = resolve_match(
        _query(synonyms=("MOR",)),
        catalog,
        snapshot_complete=True,
    )
    assert result.match_method == ("exact_synonym",)
    assert result.match_status == "ambiguous"
    assert result.matched_target_id is None


def test_absence_follows_snapshot_completeness() -> None:
    query = _query(target_id="missing")
    assert resolve_match(query, (), snapshot_complete=True).match_status == "not_found"
    assert (
        resolve_match(query, (), snapshot_complete=False).match_status
        == "source_unavailable"
    )


def test_uniprot_accession_is_not_taken_from_index_zero() -> None:
    references = (
        CrossReference("Ensembl", "ENSG00000112038"),
        CrossReference("UniProt", "P35372"),
    )
    assert select_uniprot_accessions(references) == ("P35372",)


def test_substring_name_is_not_a_candidate() -> None:
    catalog = (_target("1", name="protein kinase"),)
    result = resolve_match(_query(name="kinase"), catalog, snapshot_complete=True)
    assert result.match_status == "not_found"
    assert result.candidate_target_ids == ()


def test_several_channels_are_recorded_without_a_priority_order() -> None:
    catalog = (_target("1", uniprot="P35372", name="Mu opioid receptor"),)
    result = resolve_match(
        _query(target_id="1", uniprot_ids=("P35372",), name="Mu opioid receptor"),
        catalog,
        snapshot_complete=True,
    )
    assert result.match_status == "matched"
    assert result.match_method == ("explicit_target_id", "uniprot_xref", "exact_name")


def test_same_class_does_not_confirm_identity() -> None:
    catalog = (
        _target("1", uniprot="P35372", species="human", name="Receptor"),
        _target("2", uniprot="P35372", species="human", name="Receptor"),
    )
    result = resolve_match(
        _query(uniprot_ids=("P35372",), organism="human", name="Receptor"),
        catalog,
        snapshot_complete=True,
    )
    assert result.match_status == "ambiguous"
    assert result.matched_target_id is None


def test_matched_id_invariant() -> None:
    broken = MatchResult(
        match_status="ambiguous",
        matched_target_id="1",
        candidate_target_ids=("1",),
        match_method=("uniprot_xref",),
        match_evidence_ids=(),
    )
    assert enforce_match_invariant(broken).match_status == "contract_error"
