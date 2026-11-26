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
from iuphar_target_class.rf008_qualification import (
    _execute_projection,
    evaluate_categories,
)

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
def test_every_supplied_primary_identifier_must_support_a_match(
    query: MatchQuery,
) -> None:
    """Primary/trusted UniProt anchors remain mandatory exact channels (RF-002)."""
    result = resolve_match(
        query, (_target("1", uniprot="P11111"),), snapshot_complete=True
    )
    assert result.match_status == "ambiguous"
    assert result.matched_target_id is None


def test_unknown_auxiliary_uniprot_does_not_force_ambiguous() -> None:
    """RF-002: auxiliary xref is diagnostic-only, not a mandatory exact channel."""
    result = resolve_match(
        MatchQuery(
            None,
            ("P11111",),
            None,
            None,
            "human",
            None,
            (),
            auxiliary_uniprot_ids=("missing",),
        ),
        (_target("1", uniprot="P11111", species="human"),),
        snapshot_complete=True,
    )
    assert result.match_status == "matched"
    assert result.matched_target_id == "1"
    assert "unknown_auxiliary_uniprot" in {item.code for item in result.diagnostics}


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


@pytest.mark.parametrize("snapshot_complete", [True, False])
@pytest.mark.parametrize(
    ("query", "target", "method"),
    [
        (_query(name="shared"), _target("1", synonym="shared"), "exact_synonym"),
        (_query(synonyms=("shared",)), _target("1", name="shared"), "exact_name"),
    ],
)
def test_exact_text_searches_both_catalog_names_and_synonyms(
    query: MatchQuery, target: CatalogTarget, method: str, snapshot_complete: bool
) -> None:
    result = resolve_match(query, (target,), snapshot_complete=snapshot_complete)
    assert result.match_status == "ambiguous"
    assert result.matched_target_id is None
    assert result.candidate_target_ids == ("1",)
    assert result.match_method == (method,)


def test_rf008_anchor_cases_keep_an_evidence_disposition() -> None:
    report = evaluate_categories(
        (
            "primary_anchor",
            "auxiliary_anchor",
            "identity_conflict",
            "name_only",
            "species",
            "complex",
        )
    )
    assert report["unexplained_error_count"] == 0
    cases = report["cases"]
    assert isinstance(cases, list)
    by_id = {str(item["case_id"]): item for item in cases if isinstance(item, dict)}
    auxiliary = by_id["match-auxiliary-unknown-xref"]
    conflict = by_id["match-conflict-two-primaries"]
    named = by_id["match-name-only"]
    assert auxiliary["disposition"] == "verified"
    assert auxiliary["evidence"]
    projection = by_id["match-auxiliary-projection"]
    assert projection["disposition"] == "verified"
    assert projection["observed"] == {
        "uniprot": "P35372",
        "uniprot_equivalent": None,
        "uniprot_xref": "Q99999",
    }
    assert conflict["disposition"] == "verified"
    assert named["observed"] == {
        "match_status": "ambiguous",
        "matched_target_id": None,
    }


def test_rf008_projection_forwards_separated_uniprot_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _separated(_data: object, _taxon: str) -> dict[str, object]:
        return {
            "uniprot": "P35372",
            "uniprot_equivalent": None,
            "uniprot_xref": "Q99999",
        }

    monkeypatch.setattr(
        "iuphar_target_class.rf008_qualification.project_target_fields",
        _separated,
    )
    assert _execute_projection(
        {
            "component_accessions": ["P35372"],
            "target_xref_uniprot_ids": ["Q99999"],
            "taxon": "9606",
        }
    ) == {
        "uniprot": "P35372",
        "uniprot_equivalent": None,
        "uniprot_xref": "Q99999",
    }


@pytest.mark.parametrize(
    ("uniprot", "hgnc"),
    [(("P11111",), ()), ((), ("101",)), (("P11111",), ("101",))],
)
def test_primary_or_hgnc_overrides_same_species_text(
    uniprot: tuple[str, ...], hgnc: tuple[str, ...]
) -> None:
    catalog = (
        replace(
            _target("1", uniprot="P11111", species="9606", name="Original"),
            hgnc_ids=("101",),
        ),
        _target("2", uniprot="P22222", species="9606", synonym="Shared"),
    )
    query = replace(
        _query(uniprot_ids=uniprot, organism="9606", name="Shared"),
        hgnc_ids=hgnc,
        prioritize_anchors=True,
    )
    result = resolve_match(query, catalog, snapshot_complete=False)
    assert result.match_status == "matched"
    assert result.matched_target_id == "1"
    assert result.candidate_target_ids == ("1",)


def test_primary_and_hgnc_disagreement_blocks_confirmation() -> None:
    catalog = (
        replace(_target("1", species="9606"), hgnc_ids=("101",)),
        _target("2", uniprot="P22222", species="9606"),
    )
    query = replace(
        _query(uniprot_ids=("P22222",), organism="9606"),
        hgnc_ids=("101",),
        prioritize_anchors=True,
    )
    result = resolve_match(query, catalog, snapshot_complete=False)
    assert result.match_status == "identity_conflict"
    assert result.matched_target_id is None
    assert result.candidate_target_ids == ("1", "2")


@pytest.mark.parametrize("species", ["9606", "10090"])
@pytest.mark.parametrize("prioritize", [False, True])
@pytest.mark.parametrize("hgnc", [(), ("101",)])
def test_each_primary_accession_retains_its_identity_conflict(
    species: str, prioritize: bool, hgnc: tuple[str, ...]
) -> None:
    catalog = (
        replace(_target("1", uniprot="P11111", species="9606"), hgnc_ids=("101",)),
        _target("2", uniprot="Q22222", species=species),
    )
    query = replace(
        _query(uniprot_ids=("P11111", "Q22222"), organism="9606"),
        hgnc_ids=hgnc,
        prioritize_anchors=prioritize,
    )
    result = resolve_match(query, catalog, snapshot_complete=True)
    assert result.match_status == "identity_conflict"
    assert result.matched_target_id is None
    assert result.candidate_target_ids == ("1", "2")


def test_concordant_primary_accessions_keep_priority_over_text() -> None:
    catalog = (
        replace(_target("1", species="9606"), uniprot_ids=("P11111", "Q22222")),
        _target("2", species="9606", name="Shared"),
    )
    query = replace(
        _query(uniprot_ids=("P11111", "Q22222"), organism="9606", name="Shared"),
        prioritize_anchors=True,
    )
    result = resolve_match(query, catalog, snapshot_complete=True)
    assert result.match_status == "matched"
    assert result.matched_target_id == "1"


def test_shared_primary_accessions_remain_ambiguous_with_anchor_priority() -> None:
    catalog = tuple(
        replace(_target(identifier, species="9606"), uniprot_ids=("P11111", "Q22222"))
        for identifier in ("1", "2")
    )
    query = replace(
        _query(uniprot_ids=("P11111", "Q22222"), organism="9606"),
        prioritize_anchors=True,
    )
    result = resolve_match(query, catalog, snapshot_complete=True)
    assert result.match_status == "ambiguous"
    assert result.matched_target_id is None
    assert result.candidate_target_ids == ("1", "2")


def test_human_hgnc_is_not_a_direct_anchor_for_another_species() -> None:
    catalog = (replace(_target("1", species="9606"), hgnc_ids=("101",)),)
    query = replace(_query(organism="9913"), hgnc_ids=("101",), prioritize_anchors=True)
    assert (
        resolve_match(query, catalog, snapshot_complete=False).matched_target_id is None
    )


@pytest.mark.parametrize(
    ("uniprot", "hgnc"),
    [(("P11111", "Q88888"), ()), (("Q88888",), ("101",))],
)
def test_priority_anchors_do_not_hide_a_species_variant_conflict(
    uniprot: tuple[str, ...], hgnc: tuple[str, ...]
) -> None:
    catalog = (
        replace(_target("1", uniprot="P11111", species="9606"), hgnc_ids=("101",)),
        _target("1", uniprot="Q88888", species="10090"),
    )
    query = replace(
        _query(uniprot_ids=uniprot, organism="9606"),
        hgnc_ids=hgnc,
        prioritize_anchors=True,
    )
    result = resolve_match(query, catalog, snapshot_complete=True)
    assert result.match_status == "identity_conflict"
    assert result.matched_target_id is None


@pytest.mark.parametrize(
    ("explicit", "status", "matched"),
    [
        ("1", "identity_conflict", None),
        ("2", "matched", "2"),
        ("999", "ambiguous", None),
    ],
)
def test_priority_anchors_respect_an_explicit_target_id(explicit, status, matched):
    catalog = (
        _target("1", uniprot="P11111", species="9606"),
        _target("2", uniprot="P22222", species="9606"),
    )
    query = replace(
        _query(target_id=explicit, uniprot_ids=("P22222",), organism="9606"),
        prioritize_anchors=True,
    )
    result = resolve_match(query, catalog, snapshot_complete=True)
    assert result.match_status == status
    assert result.matched_target_id == matched


@pytest.mark.parametrize("hgnc", [(), ("101",)])
@pytest.mark.parametrize("ranked", [False, True])
def test_priority_anchors_keep_an_unknown_primary_mandatory(hgnc, ranked):
    catalog = (
        replace(
            _target("1", uniprot="P11111", species="9606", name="First protein"),
            hgnc_ids=("101",),
        ),
    )
    query = replace(
        _query(
            uniprot_ids=("P11111", "Q99999"),
            organism="9606",
            name="First protein",
        ),
        hgnc_ids=hgnc,
        prioritize_anchors=True,
        ranked_text=ranked,
    )
    result = resolve_match(query, catalog, snapshot_complete=True)
    assert result.match_status == "ambiguous"
    assert result.matched_target_id is None


def test_exact_name_cannot_replace_an_unrecorded_primary():
    catalog = (_target("1", species="9606", name="First protein"),)
    query = replace(
        _query(uniprot_ids=("Q99999",), organism="9606", name="First protein"),
        prioritize_anchors=True,
        ranked_text=True,
    )
    result = resolve_match(query, catalog, snapshot_complete=True)
    assert result.match_status == "ambiguous"
    assert result.matched_target_id is None


@pytest.mark.parametrize(
    ("symbol", "aliases", "status"),
    [
        ("GENE2", (), "ambiguous"),
        ("gene1", (), "matched"),
        ("OLD_GENE1", ("gene1",), "matched"),
        (None, ("unrelated",), "matched"),
    ],
)
def test_full_name_checks_the_gene_symbol_and_accepted_aliases(symbol, aliases, status):
    catalog = (
        _target("1", gene="GENE1", species="9606", name="First protein"),
        _target("2", gene="GENE2", species="9606", name="Second protein"),
    )
    query = replace(
        _query(organism="9606", name="First protein", gene_symbol=symbol),
        prioritize_anchors=True,
        ranked_text=True,
        gene_aliases=aliases,
    )
    result = resolve_match(query, catalog, snapshot_complete=True)
    assert result.match_status == status
    assert result.matched_target_id == ("1" if status == "matched" else None)


def test_full_name_does_not_hide_a_gene_symbol_hit_with_sparse_provider_data():
    catalog = (
        _target("1", species="9606", name="First protein"),
        _target("2", gene="GENE2", species="9606", name="Second protein"),
    )
    query = replace(
        _query(organism="9606", name="First protein", gene_symbol="GENE2"),
        prioritize_anchors=True,
        ranked_text=True,
    )
    result = resolve_match(query, catalog, snapshot_complete=True)
    assert result.match_status == "ambiguous"
    assert result.matched_target_id is None


def test_full_name_does_not_hide_a_gene_id_hit_with_sparse_provider_data():
    catalog = (
        _target("1", species="9606", name="First protein"),
        replace(_target("2", species="9606", name="Second protein"), gene_id="2"),
    )
    query = replace(
        _query(organism="9606", name="First protein"),
        gene_id="2",
        prioritize_anchors=True,
        ranked_text=True,
    )
    result = resolve_match(query, catalog, snapshot_complete=True)
    assert result.match_status == "ambiguous"
    assert result.matched_target_id is None


def test_ranked_matching_without_taxon_keeps_a_unique_uniprot_match():
    catalog = (_target("1", uniprot="P11111", species="9606"),)
    query = replace(
        _query(uniprot_ids=("P11111",), organism=None),
        prioritize_anchors=True,
        ranked_text=True,
    )
    result = resolve_match(query, catalog, snapshot_complete=True)
    assert result.match_status == "matched"
    assert result.matched_target_id == "1"


@pytest.mark.parametrize("ranked_text", [False, True])
@pytest.mark.parametrize("hgnc_ids", [(), ("101",)])
def test_priority_rejects_missing_primary_accession(ranked_text, hgnc_ids):
    catalog = (
        replace(
            _target("1", uniprot="P11111", species="9606", name="First protein"),
            hgnc_ids=("101",),
        ),
    )
    query = replace(
        _query(uniprot_ids=("P11111", "Q22222"), organism="9606", name="First protein"),
        hgnc_ids=hgnc_ids,
        prioritize_anchors=True,
        ranked_text=ranked_text,
    )
    result = resolve_match(query, catalog, snapshot_complete=True)
    assert result.match_status == "ambiguous"
    assert result.matched_target_id is None
    assert result.candidate_target_ids == ("1",)


@pytest.mark.parametrize(
    ("gene_symbol", "gene_aliases", "status", "target_id"),
    [
        ("GENE2", (), "ambiguous", None),
        ("GENE2", ("gene1",), "ambiguous", None),
        ("UNKNOWN", (), "ambiguous", None),
        ("LEGACY", ("gene1",), "matched", "1"),
        ("GENE1", (), "matched", "1"),
    ],
)
def test_ranked_name_checks_explicit_gene_symbol_and_aliases(
    gene_symbol, gene_aliases, status, target_id
):
    catalog = (
        _target("1", gene="GENE1", species="9606", name="First protein"),
        _target("2", gene="GENE2", species="9606", name="Second protein"),
    )
    query = replace(
        _query(gene_symbol=gene_symbol, organism="9606", name="First protein"),
        gene_aliases=gene_aliases,
        ranked_text=True,
    )
    result = resolve_match(query, catalog, snapshot_complete=True)
    assert result.match_status == status
    assert result.matched_target_id == target_id
