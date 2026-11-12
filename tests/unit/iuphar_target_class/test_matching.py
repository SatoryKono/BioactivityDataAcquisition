"""TC-05 matching: channels, species, and the matched-id invariant."""

from __future__ import annotations

from dataclasses import replace

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


@pytest.mark.parametrize("gene_field", ["gene_symbol", "gene_id"])
@pytest.mark.parametrize("anchor", ["target_id", "uniprot"])
@pytest.mark.parametrize("same_target", [False, True])
@pytest.mark.parametrize("snapshot_complete", [False, True])
def test_unverified_gene_requires_species_despite_exact_anchor(
    gene_field: str,
    anchor: str,
    same_target: bool,
    snapshot_complete: bool,
) -> None:
    catalog = (
        replace(
            _target("1", uniprot="P11111", gene="GENE_1", species="human"),
            gene_id="101",
        ),
        replace(
            _target("2", uniprot="P22222", gene="GENE_2", species="human"),
            gene_id="202",
        ),
    )
    target = catalog[0] if same_target else catalog[1]
    query = replace(
        _query(
            target_id="1" if anchor == "target_id" else None,
            uniprot_ids=("P11111",) if anchor == "uniprot" else (),
        ),
        **{gene_field: getattr(target, gene_field)},
    )
    result = resolve_match(query, catalog, snapshot_complete=snapshot_complete)
    assert result.match_status == "insufficient_input"
    assert result.matched_target_id is None
    assert result.candidate_target_ids == ("1",)
    assert tuple(item.code for item in result.diagnostics) == ("insufficient_input",)
    checked = resolve_match(
        replace(query, organism="human"), catalog, snapshot_complete=snapshot_complete
    )
    assert checked.match_status == ("matched" if same_target else "identity_conflict")
    assert checked.matched_target_id == ("1" if same_target else None)


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


@pytest.mark.parametrize("field", ["name", "synonyms"])
def test_name_channels_respect_query_species(field: str) -> None:
    catalog = (
        _target("1", gene="GENE", species="human", name="shared", synonym="shared"),
        _target("2", gene="GENE", species="mouse", name="shared", synonym="shared"),
    )
    query = _query(
        gene_symbol="GENE",
        organism="human",
        **{field: "shared" if field == "name" else ("shared",)},
    )
    result = resolve_match(query, catalog, snapshot_complete=True)
    assert result.match_status == "matched"
    assert result.matched_target_id == "1"
    assert result.candidate_target_ids == ("1",)


def test_species_filter_cannot_hide_exact_identifier_conflict() -> None:
    catalog = (
        _target("1", uniprot="P11111", species="human"),
        _target("2", uniprot="P22222", species="mouse"),
    )
    result = resolve_match(
        _query(target_id="1", uniprot_ids=("P22222",), organism="human"),
        catalog,
        snapshot_complete=True,
    )
    assert result.match_status == "identity_conflict"
    assert result.matched_target_id is None
    assert result.candidate_target_ids == ("1", "2")


@pytest.mark.parametrize(
    "query",
    [
        _query(target_id="missing", uniprot_ids=("P11111",)),
        _query(target_id="1", uniprot_ids=("missing",)),
        _query(uniprot_ids=("P11111", "missing")),
    ],
)
def test_every_supplied_identifier_must_support_a_match(query: MatchQuery) -> None:
    result = resolve_match(
        query, (_target("1", uniprot="P11111"),), snapshot_complete=True
    )
    assert result.match_status == "ambiguous"
    assert result.matched_target_id is None


def test_gene_without_species_cannot_hide_an_existing_identity_conflict() -> None:
    catalog = (
        _target("1", uniprot="P11111", species="human"),
        _target("2", uniprot="P22222", species="human"),
    )
    result = resolve_match(
        _query(target_id="1", uniprot_ids=("P22222",), gene_symbol="GENE"),
        catalog,
        snapshot_complete=True,
    )
    assert result.match_status == "identity_conflict"
    assert result.matched_target_id is None
    assert result.candidate_target_ids == ("1", "2")


@pytest.mark.parametrize("species", ["human", None])
def test_explicit_id_cannot_confirm_a_target_outside_the_requested_species(
    species: str | None,
) -> None:
    result = resolve_match(
        _query(target_id="1", organism="mouse"),
        (_target("1", species=species),),
        snapshot_complete=True,
    )
    assert result.match_status != "matched"
    assert result.matched_target_id is None
    assert result.diagnostics


def test_explicit_id_with_compatible_species_is_still_matched() -> None:
    result = resolve_match(
        _query(target_id="1", organism="human"),
        (_target("1", species="human"),),
        snapshot_complete=True,
    )
    assert result.match_status == "matched"
    assert result.matched_target_id == "1"
