"""TC-05 matching: channels, species, and the matched-id invariant."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, replace

import pytest

from iuphar_target_class.bioetl_input import (
    partition_uniprot_roles,
    project_target_fields,
    target_input_eligibility,
)
from iuphar_target_class.matching import (
    MATCHING_POLICY_ROLE_SEPARATED_V2,
    MATCHING_POLICY_STRICT_ANCHORS_V1,
    CatalogTarget,
    CrossReference,
    MatchQuery,
    describe_ambiguous_channels,
    enforce_match_invariant,
    explain_policy_change,
    resolve_match,
    select_uniprot_accessions,
)
from iuphar_target_class.models import MatchResult, RawTargetRow, RunProvenance

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


def _role_query(
    *,
    policy: str,
    primary: tuple[str, ...] = (),
    auxiliary: tuple[str, ...] = (),
    equivalent: tuple[str, ...] = (),
    name: str | None = None,
    synonyms: tuple[str, ...] = (),
    organism: str | None = "9606",
    object_scope: str | None = None,
) -> MatchQuery:
    uniprot = (
        tuple(dict.fromkeys((*primary, *auxiliary, *equivalent)))
        if policy == MATCHING_POLICY_STRICT_ANCHORS_V1
        else primary
    )
    return MatchQuery(
        None,
        uniprot,
        None,
        None,
        organism,
        name,
        synonyms,
        () if policy == MATCHING_POLICY_STRICT_ANCHORS_V1 else auxiliary,
        () if policy == MATCHING_POLICY_STRICT_ANCHORS_V1 else equivalent,
        policy,
        object_scope,
    )


def test_projection_keeps_primary_aux_and_equivalent_roles() -> None:
    payload = {
        "component_accessions": '["P22222","P11111"]',
        "target_xref_uniprot_ids": "P11111|Q99999|AUX2",
        "proven_uniprot_equivalents": "E33333|P22222",
        "pref_name": "Example",
    }
    projected = project_target_fields(payload, "9606")
    roles = partition_uniprot_roles(payload)
    assert projected["uniprot"] == "P22222|P11111"
    assert roles.primary_ids == ("P22222", "P11111")
    assert roles.equivalent_ids == ("E33333",)
    assert roles.auxiliary_ids == ("Q99999", "AUX2")
    assert roles.evidence_ids == ("AUX2", "E33333", "P11111", "P22222", "Q99999")
    assert "Q99999" in str(projected["source_business_data"])
    reversed_roles = partition_uniprot_roles(
        {
            **payload,
            "component_accessions": '["P11111","P22222"]',
            "target_xref_uniprot_ids": "AUX2|Q99999|P11111",
            "proven_uniprot_equivalents": "P22222|E33333",
        }
    )
    assert set(reversed_roles.primary_ids) == set(roles.primary_ids)
    assert reversed_roles.equivalent_ids == roles.equivalent_ids
    assert reversed_roles.auxiliary_ids == ("AUX2", "Q99999")
    assert reversed_roles.evidence_ids == roles.evidence_ids


def test_unknown_auxiliary_is_distinct_from_reliable_identifier_conflict() -> None:
    catalog = (
        _target("1", uniprot="P11111", species="9606"),
        _target("2", uniprot="E22222", species="9606"),
    )
    unknown = resolve_match(
        _role_query(
            policy=MATCHING_POLICY_ROLE_SEPARATED_V2,
            primary=("P11111",),
            auxiliary=("Q99999",),
        ),
        catalog,
        snapshot_complete=True,
    )
    conflict = resolve_match(
        _role_query(
            policy=MATCHING_POLICY_ROLE_SEPARATED_V2,
            primary=("P11111",),
            equivalent=("E22222",),
        ),
        catalog,
        snapshot_complete=True,
    )
    strict_unknown = resolve_match(
        _role_query(
            policy=MATCHING_POLICY_STRICT_ANCHORS_V1,
            primary=("P11111",),
            auxiliary=("Q99999",),
        ),
        catalog,
        snapshot_complete=True,
    )
    assert unknown.match_status == "matched"
    assert unknown.matched_target_id == "1"
    assert tuple(item.code for item in unknown.diagnostics) == (
        "auxiliary_uniprot_unresolved",
    )
    assert conflict.match_status == "identity_conflict"
    assert conflict.matched_target_id is None
    assert tuple(item.code for item in conflict.diagnostics) == ("identity_conflict",)
    assert strict_unknown.match_status == "ambiguous"
    assert explain_policy_change(strict_unknown, unknown) == (
        "unknown_auxiliary_uniprot_is_not_a_required_anchor"
    )
    flipped = resolve_match(
        _role_query(
            policy=MATCHING_POLICY_ROLE_SEPARATED_V2,
            primary=("P11111",),
            auxiliary=("Q99999", "AUX2"),
            equivalent=("E00000",),
        ),
        (_target("1", uniprot="P11111", species="9606"),),
        snapshot_complete=True,
    )
    flipped_again = resolve_match(
        _role_query(
            policy=MATCHING_POLICY_ROLE_SEPARATED_V2,
            primary=("P11111",),
            auxiliary=("AUX2", "Q99999"),
            equivalent=("E00000",),
        ),
        (_target("1", uniprot="P11111", species="9606"),),
        snapshot_complete=True,
    )
    assert flipped == flipped_again
    assert flipped.match_status == "ambiguous"
    assert "auxiliary_uniprot_unresolved" in {item.code for item in flipped.diagnostics}


def test_component_accession_does_not_prove_complex_or_family() -> None:
    catalog = (_target("subunit", uniprot="P35372", species="9606", name="shared"),)
    for scope in ("complex", "family"):
        result = resolve_match(
            _role_query(
                policy=MATCHING_POLICY_ROLE_SEPARATED_V2,
                primary=("P35372",),
                name="shared",
                object_scope=scope,
            ),
            catalog,
            snapshot_complete=True,
        )
        assert result.match_status == "ambiguous"
        assert result.matched_target_id is None
        assert "component_accession_not_object_identity" in {
            item.code for item in result.diagnostics
        }
    protein = resolve_match(
        _role_query(
            policy=MATCHING_POLICY_ROLE_SEPARATED_V2,
            primary=("P35372",),
            object_scope="protein",
        ),
        catalog,
        snapshot_complete=True,
    )
    explicit = resolve_match(
        replace(
            _role_query(
                policy=MATCHING_POLICY_ROLE_SEPARATED_V2,
                primary=("P35372",),
                object_scope="complex",
            ),
            target_id="subunit",
        ),
        catalog,
        snapshot_complete=True,
    )
    assert protein.match_status == "matched"
    assert explicit.match_status == "matched"
    assert explicit.matched_target_id == "subunit"


def test_name_only_stays_evidence_under_role_separated_policy() -> None:
    result = resolve_match(
        _role_query(
            policy=MATCHING_POLICY_ROLE_SEPARATED_V2,
            name="Mu opioid receptor",
        ),
        (_target("1", name="Mu opioid receptor", species="9606"),),
        snapshot_complete=True,
    )
    assert result.match_status == "ambiguous"
    assert result.match_method == ("exact_name",)
    assert (
        describe_ambiguous_channels(
            _role_query(
                policy=MATCHING_POLICY_ROLE_SEPARATED_V2, name="Mu opioid receptor"
            ),
            result,
        )
        == "exact_name"
    )


@dataclass(frozen=True, slots=True)
class _ControlCase:
    group: str
    primary: tuple[str, ...]
    auxiliary: tuple[str, ...] = ()
    name: str | None = None
    synonyms: tuple[str, ...] = ()
    complete: bool = True
    channel: str | None = None


def _control_cases() -> tuple[_ControlCase, ...]:
    """Fixed offline cohort with the reported 1000-row outcome shape."""
    matched = tuple(
        _ControlCase("legacy_matched", (f"PM{index:05d}",)) for index in range(117)
    )
    blocked = tuple(
        _ControlCase("auxiliary_blocked", (f"PX{index:05d}",), (f"UX{index:05d}",))
        for index in range(516)
    )
    shared = tuple(
        _ControlCase("ambiguous", (f"PS{index:02d}",), channel="shared_primary")
        for index in range(9)
    )
    names = tuple(
        _ControlCase("ambiguous", (), name=f"NAME{index:02d}", channel="exact_name")
        for index in range(8)
    )
    synonyms = tuple(
        _ControlCase(
            "ambiguous",
            (),
            synonyms=(f"SYN{index:02d}",),
            channel="exact_synonym",
        )
        for index in range(7)
    )
    other_name = tuple(
        _ControlCase(
            "ambiguous",
            (f"PN{index:02d}",),
            name=f"OTHER{index:02d}",
            channel="primary_and_other_name",
        )
        for index in range(4)
    )
    partial = tuple(
        _ControlCase(
            "ambiguous",
            (f"PP{index:02d}", f"MISSING{index:02d}"),
            channel="partial_required_anchor",
        )
        for index in range(3)
    )
    unavailable = tuple(
        _ControlCase("source_unavailable", (f"SU{index:05d}",), complete=False)
        for index in range(189)
    )
    cases = (
        *matched,
        *blocked,
        *shared,
        *names,
        *synonyms,
        *other_name,
        *partial,
        *unavailable,
    )
    assert len(cases) == 853
    return cases


def _control_catalog(cases: tuple[_ControlCase, ...]) -> tuple[CatalogTarget, ...]:
    targets: list[CatalogTarget] = []
    for case in cases:
        if case.group == "source_unavailable":
            continue
        if case.channel == "shared_primary":
            accession = case.primary[0]
            targets.append(_target(f"{accession}-a", uniprot=accession, species="9606"))
            targets.append(_target(f"{accession}-b", uniprot=accession, species="9606"))
            continue
        if case.channel == "exact_name":
            assert case.name is not None
            targets.append(_target(f"name-{case.name}", species="9606", name=case.name))
            continue
        if case.channel == "exact_synonym":
            synonym = case.synonyms[0]
            targets.append(_target(f"syn-{synonym}", species="9606", synonym=synonym))
            continue
        if case.channel == "primary_and_other_name":
            assert case.name is not None
            accession = case.primary[0]
            targets.append(
                _target(f"pri-{accession}", uniprot=accession, species="9606")
            )
            targets.append(_target(f"name-{case.name}", species="9606", name=case.name))
            continue
        if case.channel == "partial_required_anchor":
            targets.append(
                _target(
                    f"part-{case.primary[0]}", uniprot=case.primary[0], species="9606"
                )
            )
            continue
        targets.append(
            _target(f"id-{case.primary[0]}", uniprot=case.primary[0], species="9606")
        )
    return tuple(targets)


def test_fixed_cohort_separates_unknown_auxiliary_from_remaining_ambiguity() -> None:
    cases = _control_cases()
    catalog = _control_catalog(cases)
    species = frozenset({"9606", "10090", "10116"})
    taxa = tuple(
        target_input_eligibility(
            {
                "target_type": "SINGLE PROTEIN",
                "taxonomy_id": 7227,
                "organism": "Drosophila melanogaster",
                "component_accessions": f'["TX{index:05d}"]',
            },
            species,
        )
        for index in range(147)
    )
    assert len(cases) + len(taxa) == 1000
    assert {reason for _taxon, reason in taxa} == {"unsupported_taxon"}

    old_counts: Counter[str] = Counter()
    new_counts: Counter[str] = Counter()
    explanations: Counter[str] = Counter()
    channels: Counter[str] = Counter()
    for case in cases:
        old = resolve_match(
            _role_query(
                policy=MATCHING_POLICY_STRICT_ANCHORS_V1,
                primary=case.primary,
                auxiliary=case.auxiliary,
                name=case.name,
                synonyms=case.synonyms,
            ),
            catalog,
            snapshot_complete=case.complete,
        )
        current_query = _role_query(
            policy=MATCHING_POLICY_ROLE_SEPARATED_V2,
            primary=case.primary,
            auxiliary=case.auxiliary,
            name=case.name,
            synonyms=case.synonyms,
        )
        current = resolve_match(current_query, catalog, snapshot_complete=case.complete)
        permuted = resolve_match(
            _role_query(
                policy=MATCHING_POLICY_ROLE_SEPARATED_V2,
                primary=tuple(reversed(case.primary)),
                auxiliary=tuple(reversed(case.auxiliary)),
                name=case.name,
                synonyms=tuple(reversed(case.synonyms)),
            ),
            catalog,
            snapshot_complete=case.complete,
        )
        assert permuted == current
        old_counts[old.match_status or ""] += 1
        new_counts[current.match_status or ""] += 1
        explanations[explain_policy_change(old, current)] += 1
        if case.group == "legacy_matched":
            assert current.match_status == "matched"
            assert current.matched_target_id == old.matched_target_id
        if case.group == "auxiliary_blocked":
            assert old.match_status == "ambiguous"
            assert current.match_status == "matched"
            assert current.matched_target_id == old.candidate_target_ids[0]
            assert tuple(item.code for item in current.diagnostics) == (
                "auxiliary_uniprot_unresolved",
            )
        if case.group == "ambiguous":
            assert current.match_status == "ambiguous"
            assert current.matched_target_id is None
            assert case.channel == describe_ambiguous_channels(current_query, current)
            channels[case.channel or ""] += 1
    assert old_counts == Counter(matched=117, ambiguous=547, source_unavailable=189)
    assert new_counts == Counter(matched=633, ambiguous=31, source_unavailable=189)
    assert explanations["unchanged_reliable_primary"] == 117
    assert explanations["unknown_auxiliary_uniprot_is_not_a_required_anchor"] == 516
    assert explanations["remaining_ambiguous_channel"] == 31
    assert explanations["unchanged_source_unavailable"] == 189
    assert "unexpected_policy_delta" not in explanations
    assert channels == Counter(
        shared_primary=9,
        exact_name=8,
        exact_synonym=7,
        primary_and_other_name=4,
        partial_required_anchor=3,
    )


def test_runtime_projection_records_unknown_auxiliary_without_false_ambiguity() -> None:
    from iuphar_target_class.pipeline import IndexedSnapshot, classify_batch

    payload = {
        "target_id": "CHEMBL9",
        "target_type": "SINGLE PROTEIN",
        "component_accessions": '["P35372"]',
        "target_xref_uniprot_ids": "Q99999",
        "proven_uniprot_equivalents": "E35372",
        "pref_name": "mu opioid receptor",
    }
    fields = project_target_fields(payload, "9606")
    assert fields["uniprot"] == "P35372"
    snapshot = IndexedSnapshot.build(
        snapshot_id="fixture",
        mapping_version="fixture",
        complete=True,
        catalog=(
            _target("1", uniprot="P35372", species="9606"),
            _target("2", uniprot="E35372", species="9606"),
        ),
        annotations={},
        family_nodes=(),
        type_to_class={},
        family_to_class={},
    )
    batch = classify_batch(
        (RawTargetRow("row-1", fields, "protein"),),
        snapshot=snapshot,
        provenance=RunProvenance("fixture", "n", "r", "s", "t", "t"),
        run_id="run-1",
    )
    result = batch.rows[0].result
    assert result.match_status == "identity_conflict"
    assert result.matched_target_id is None
    retained = {record.content for record in batch.rows[0].evidence.records}
    assert retained >= {
        "uniprot_role=primary",
        "uniprot_role=equivalent",
    }

    unknown_fields = project_target_fields(
        {
            "target_id": "CHEMBL8",
            "component_accessions": '["P35372"]',
            "target_xref_uniprot_ids": "Q99999",
            "pref_name": "mu opioid receptor",
        },
        "9606",
    )
    unknown = classify_batch(
        (RawTargetRow("row-2", unknown_fields, "protein"),),
        snapshot=snapshot,
        provenance=RunProvenance("fixture", "n", "r", "s", "t", "t"),
        run_id="run-2",
    )
    unknown_result = unknown.rows[0].result
    assert unknown_result.match_status == "matched"
    assert unknown_result.matched_target_id == "1"
    assert any(
        item.code == "auxiliary_uniprot_unresolved"
        for item in unknown_result.diagnostics
    )
    unknown_retained = {record.content for record in unknown.rows[0].evidence.records}
    assert "uniprot_role=auxiliary" in unknown_retained
    assert "uniprot_role=primary" in unknown_retained
