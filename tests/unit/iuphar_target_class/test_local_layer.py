"""TC-07 local layer: EC categories, annotations, and predictions."""

from __future__ import annotations

from dataclasses import dataclass, replace

import pytest

from iuphar_target_class.local_layer import (
    Prediction,
    apply_local,
    predictions_from_row,
)
from iuphar_target_class.normalization import parse_ec_numbers
from iuphar_target_class.policy import (
    EC_CATEGORIES,
    EC_SINGULAR,
    LOCAL_CATALOG_VERSION,
    PLAN_SOURCE,
    PLAN_VERSION,
    RuleRecord,
    local_evidence_content,
    local_rules,
    local_rules_catalog_sha256,
    policy_document,
    validate_rules,
)
from iuphar_target_class.rf008_qualification import evaluate_categories

pytestmark = pytest.mark.unit

_EC_NAMES = {
    1: "Oxidoreductases",
    2: "Transferases",
    3: "Hydrolases",
    4: "Lyases",
    5: "Isomerases",
    6: "Ligases",
    7: "Translocases",
}


def _rule(
    rule_id: str,
    family: str,
    conditions: str,
    output: str,
    *,
    version: str = PLAN_VERSION,
) -> RuleRecord:
    return RuleRecord(
        rule_id,
        family,
        conditions,
        output,
        PLAN_SOURCE,
        version,
        "local layer",
        False,
    )


@pytest.mark.parametrize(("number", "name"), sorted(_EC_NAMES.items()))
def test_ec_categories_1_to_7_are_not_iuphar_classes(number: int, name: str) -> None:
    result = apply_local(parse_ec_numbers(f"{number}.-.-.-"), rules=())
    assert result.ec_categories == (name,)
    assert result.local_class is None
    assert result.local_class != "Transporter"
    assert result.local_class != "Enzyme"


def test_partial_ec_keeps_only_the_confirmed_levels() -> None:
    shallow = parse_ec_numbers("3.-.-.-")[0]
    deeper = parse_ec_numbers("3.1.-.-")[0]
    assert shallow.depth == 1
    assert shallow.confirmed_levels == ("3",)
    assert deeper.depth == 2
    assert deeper.confirmed_levels == ("3", "3.1")
    result = apply_local((deeper,), rules=())
    assert result.ec_categories == ("Hydrolases",)


def test_invalid_or_missing_ec_does_not_block_another_witness() -> None:
    rule = _rule("kw", "annotation", "keyword_id=KW-1", "Enzyme")
    invalid = apply_local(
        parse_ec_numbers("not-an-ec"),
        rules=(rule,),
        keyword_ids=("KW-1",),
    )
    missing = apply_local((), rules=(rule,), keyword_ids=("KW-1",))
    assert invalid.local_class == "Enzyme"
    assert invalid.ec_categories == ()
    assert any(item.code == "invalid_ec" for item in invalid.diagnostics)
    assert missing.local_class == "Enzyme"


def test_ec3_unicellular_target_is_not_filtered() -> None:
    result = apply_local(
        parse_ec_numbers("3.1.1.1"),
        rules=(),
        organism="unicellular",
    )
    assert result.ec_categories == ("Hydrolases",)
    assert any(
        item.code == "organism_not_a_class_filter" for item in result.diagnostics
    )


def test_several_ec_categories_do_not_claim_multiple_functions() -> None:
    same = apply_local(parse_ec_numbers("1.1.1.1; 1.2.1.1"), rules=())
    different = apply_local(parse_ec_numbers("1.-.-.-|3.-.-.-"), rules=())
    assert same.ec_categories == ("Oxidoreductases",)
    assert same.multiple_ec_categories is False
    assert different.ec_categories == ("Oxidoreductases", "Hydrolases")
    assert different.multiple_ec_categories is True
    assert "multifunctional" not in same.__dataclass_fields__


def test_keyword_and_ec_conflict_keeps_both_and_no_subclass() -> None:
    rules = (
        _rule("kw", "annotation", "keyword_id=KW-1", "Receptor"),
        _rule("ec2", "ec_class", "ec_category=2", "Enzyme"),
    )
    forward = apply_local(
        parse_ec_numbers("2.7.1.1"),
        rules=rules,
        keyword_ids=("KW-1",),
    )
    reverse = apply_local(
        parse_ec_numbers("2.7.1.1"),
        rules=(rules[1], rules[0]),
        keyword_ids=("KW-1",),
    )
    assert forward == reverse
    assert forward.local_status == "conflicting"
    assert forward.local_class is None
    assert forward.local_subclasses == ()
    assert forward.ec_categories == ("Transferases",)
    assert forward.local_candidates == ("Enzyme", "Receptor")


def test_unknown_and_dependent_predictions_do_not_support_a_class() -> None:
    result = apply_local(
        (),
        rules=(),
        predictions=(
            Prediction("L1", "Receptor", False, False, "l1"),
            Prediction("L2", "Enzyme", True, True, "l2"),
        ),
    )
    assert result.local_class is None
    assert result.local_status == "not_supported"
    assert "candidate_only" in result.local_candidates
    assert any(item.code == "dependent_prediction" for item in result.diagnostics)


def test_free_text_substrings_do_not_assign_a_class() -> None:
    result = apply_local(
        (),
        rules=(),
        free_text="serine kinase ion channel zinc finger",
    )
    assert result.local_class is None
    assert result.local_class != "Other Protein Target"
    assert "free_text" in result.local_candidates


def test_other_protein_target_requires_a_real_rule() -> None:
    empty = apply_local((), rules=())
    ruled = apply_local(
        (),
        rules=(
            _rule("opt", "annotation", "keyword_id=KW-OPT", "Other Protein Target"),
        ),
        keyword_ids=("KW-OPT",),
    )
    assert empty.local_class is None
    assert ruled.local_class == "Other Protein Target"


def test_local_result_has_no_iuphar_fields() -> None:
    result = apply_local(parse_ec_numbers("7.-.-.-"), rules=())
    assert result.ec_categories == ("Translocases",)
    names = set(result.__dataclass_fields__)
    assert not any(name.startswith("iuphar_") for name in names)


@pytest.mark.parametrize("layer", ("L1", "L2"))
def test_other_protein_prediction_does_not_supply_a_rule(layer: str) -> None:
    result = apply_local(
        (),
        rules=(),
        predictions=(
            Prediction(layer, "Other Protein Target", True, False, "prediction"),
        ),
    )
    assert result.local_status == "not_supported"
    assert result.local_class is None
    assert result.local_rule_ids == ()
    assert result.local_evidence_ids == ()
    assert "candidate_only" in result.local_candidates


def test_other_protein_prediction_keeps_matched_keyword_rule_as_owner() -> None:
    result = apply_local(
        (),
        rules=(
            _rule("opt", "annotation", "keyword_id=KW-OPT", "Other Protein Target"),
        ),
        keyword_ids=("KW-OPT",),
        predictions=(
            Prediction("L1", "Other Protein Target", True, False, "prediction"),
        ),
    )
    assert result.local_status == "supported"
    assert result.local_class == "Other Protein Target"
    assert result.local_rule_ids == ("opt",)
    assert result.local_evidence_ids == ("keyword:KW-OPT",)


def test_independent_receptor_prediction_keeps_existing_support() -> None:
    result = apply_local(
        (),
        rules=(),
        predictions=(Prediction("L1", "Receptor", True, False, "prediction"),),
    )
    assert result.local_status == "supported"
    assert result.local_class == "Receptor"
    assert result.local_rule_ids == ("prediction:L1",)


def test_subclass_parent_outside_the_dictionary_is_rejected() -> None:
    with pytest.raises(ValueError, match="outside the class dictionary"):
        apply_local(
            (),
            rules=(),
            predictions=(Prediction("L1", "Enzyme", True, False, "prediction"),),
            subclass_of={"Enzyme": "not-a-working-class"},
        )


def test_broken_rule_blocks_processing() -> None:
    broken = _rule("bad", "annotation", "keyword_id=KW-1", "Enzyme", version="")
    with pytest.raises(ValueError, match="missing version"):
        apply_local((), rules=(broken,), keyword_ids=("KW-1",))


@pytest.mark.parametrize("family", ["ec_class", "annotation"])
def test_local_rule_families_cannot_claim_a_direct_layer(family: str) -> None:
    rule = replace(
        _rule("local", family, "keyword_id=KW-1", "Enzyme"),
        marks_direct_layer=True,
    )
    with pytest.raises(ValueError, match="must not be marked direct"):
        apply_local((), rules=(rule,), keyword_ids=("KW-1",))


@pytest.mark.parametrize(
    "hierarchy",
    [
        {"Enzyme": "Receptor"},
        {"Enzyme": "Other Protein Target", "Receptor": "Other Protein Target"},
    ],
)
def test_working_classes_cannot_be_reparented_to_erase_a_conflict(
    hierarchy: dict[str, str],
) -> None:
    rules = (
        _rule("ec", "annotation", "keyword_id=KW-E", "Enzyme"),
        _rule("receptor", "annotation", "keyword_id=KW-R", "Receptor"),
    )
    with pytest.raises(ValueError, match="working class"):
        apply_local(
            (), rules=rules, keyword_ids=("KW-E", "KW-R"), subclass_of=hierarchy
        )


def test_catalog_hash_is_stable_and_recorded_on_the_profile() -> None:
    first = local_rules_catalog_sha256()
    second = local_rules_catalog_sha256()
    document = policy_document()
    assert first == second
    assert len(first) == 64
    assert document["local_rule_catalog_sha256"] == first
    assert document["local_rule_catalog_version"] == LOCAL_CATALOG_VERSION
    content = local_evidence_content("ec:1.1.1.1", ("ec-class:1",))
    assert f"catalog={LOCAL_CATALOG_VERSION}" in content
    assert f"catalog_sha256={first}" in content
    assert "rules=ec-class:1" in content


def test_catalog_uses_the_fixed_ec_names_and_rejects_bad_outputs() -> None:
    assert [name for _number, name in EC_SINGULAR] == [
        "Oxidoreductase",
        "Transferase",
        "Hydrolase",
        "Lyase",
        "Isomerase",
        "Ligase",
        "Translocase",
    ]
    assert all(
        plural == singular + "s"
        for (_number, plural), (_same, singular) in zip(
            EC_CATEGORIES, EC_SINGULAR, strict=True
        )
    )
    outputs = {rule.output.casefold() for rule in local_rules()}
    assert "multifunctional" not in outputs
    assert "nuclear hormone receptor" not in outputs
    assert "transporter" not in outputs
    forbidden = _rule("bad-ec7", "ec_class", "ec_category=7", "Transporter")
    broad = _rule("bad-nhr", "annotation", "keyword_id=KW-0863", "Receptor")
    with pytest.raises(ValueError, match="EC 7"):
        validate_rules((forbidden,))
    with pytest.raises(ValueError, match="zinc finger"):
        validate_rules((broad,))


@pytest.mark.parametrize("number", range(1, 7))
def test_each_enzyme_ec_rule_has_three_examples(number: int) -> None:
    rules = local_rules()
    positive = apply_local(parse_ec_numbers(f"{number}.-.-.-"), rules=rules)
    assert positive.local_status == "supported"
    assert positive.local_class == "Enzyme"
    assert positive.local_class != "Transporter"
    assert f"ec:{number}" in positive.local_rule_ids
    assert f"ec-class:{number}" in positive.local_rule_ids
    assert positive.local_evidence_ids
    negative = apply_local(parse_ec_numbers("7.1.1.1"), rules=rules)
    assert f"ec:{number}" not in negative.local_rule_ids
    assert f"ec-class:{number}" not in negative.local_rule_ids
    assert negative.local_class != "Transporter"
    forward = apply_local(
        parse_ec_numbers(f"{number}.1.1.1"),
        rules=rules,
        keyword_ids=("KW-0675",),
    )
    reverse = apply_local(
        parse_ec_numbers(f"{number}.1.1.1"),
        rules=tuple(reversed(rules)),
        keyword_ids=("KW-0675",),
    )
    assert forward == reverse
    assert forward.local_status == "conflicting"
    assert forward.local_class is None
    assert forward.local_candidates == ("Enzyme", "Receptor")


def test_ec7_is_translocase_and_not_transporter() -> None:
    rules = local_rules()
    positive = apply_local(parse_ec_numbers("7.-.-.-"), rules=rules)
    assert positive.ec_categories == ("Translocases",)
    assert positive.local_class is None
    assert positive.local_class != "Transporter"
    assert positive.local_status == "not_supported"
    assert positive.local_rule_ids == ("ec:7",)
    assert "ec-class:7" not in positive.local_rule_ids
    negative = apply_local(parse_ec_numbers("6.1.1.1"), rules=rules)
    assert "ec:7" not in negative.local_rule_ids
    assert negative.local_class == "Enzyme"
    several = apply_local(parse_ec_numbers("7.1.1.1;7.2.2.2"), rules=rules)
    assert several.multiple_ec_categories is False
    assert several.local_class is None
    with_enzyme = apply_local(parse_ec_numbers("1.1.1.1|7.1.1.1"), rules=rules)
    assert with_enzyme.local_class == "Enzyme"
    assert with_enzyme.ec_categories == ("Oxidoreductases", "Translocases")
    assert with_enzyme.local_class != "Transporter"


def test_each_witness_keeps_only_its_own_rules() -> None:
    rules = local_rules()
    forward = apply_local(parse_ec_numbers("1.1.1.1;7.1.1.1"), rules=rules)
    reverse = apply_local(parse_ec_numbers("7.1.1.1|1.1.1.1"), rules=rules)
    assert forward.local_rules_by_evidence == reverse.local_rules_by_evidence
    bound = dict(forward.local_rules_by_evidence)
    assert bound["ec:1.1.1.1"] == ("ec-class:1", "ec:1")
    assert bound["ec:7.1.1.1"] == ("ec:7",)
    mixed = apply_local(
        parse_ec_numbers("3.4.21.1"),
        rules=rules,
        keyword_ids=("KW-0675",),
    )
    mixed_bound = dict(mixed.local_rules_by_evidence)
    assert mixed_bound["ec:3.4.21.1"] == ("ec-class:3", "ec:3")
    assert mixed_bound["keyword:KW-0675"] == ("annotation:KW-0675",)
    assert set(mixed.local_rule_ids) == {
        rule_id for rule_ids in mixed_bound.values() for rule_id in rule_ids
    }


@pytest.mark.parametrize(
    ("keyword_id", "class_name"),
    [
        ("KW-0378", "Enzyme"),
        ("KW-0418", "Enzyme"),
        ("KW-0808", "Enzyme"),
        ("KW-0675", "Receptor"),
    ],
)
def test_each_annotation_rule_has_three_examples(
    keyword_id: str, class_name: str
) -> None:
    rules = local_rules()
    positive = apply_local((), rules=rules, keyword_ids=(keyword_id,))
    assert positive.local_status == "supported"
    assert positive.local_class == class_name
    assert f"annotation:{keyword_id}" in positive.local_rule_ids
    negative = apply_local((), rules=rules, keyword_ids=("KW-0863", "KW-0804"))
    assert f"annotation:{keyword_id}" not in negative.local_rule_ids
    assert negative.local_class is None
    assert negative.local_class != "nuclear hormone receptor"
    if class_name == "Receptor":
        forward = apply_local(
            parse_ec_numbers("4.-.-.-"),
            rules=rules,
            keyword_ids=(keyword_id,),
        )
        reverse = apply_local(
            parse_ec_numbers("4.-.-.-"),
            rules=tuple(reversed(rules)),
            keyword_ids=(keyword_id,),
        )
    else:
        forward = apply_local(
            (),
            rules=rules,
            keyword_ids=(keyword_id, "KW-0675"),
        )
        reverse = apply_local(
            (),
            rules=tuple(reversed(rules)),
            keyword_ids=("KW-0675", keyword_id),
        )
    assert forward == reverse
    assert forward.local_status == "conflicting"
    assert forward.local_class is None


def test_prediction_rules_use_evidence_and_keep_ties() -> None:
    rules = local_rules()
    unknown = predictions_from_row(
        predicted_l1="Receptor",
        predicted_l2="Enzyme",
        raw_fields={"predicted_l1_provenance": "N/A", "predicted_l2_relation": "True"},
    )
    unknown_result = apply_local((), rules=rules, predictions=unknown)
    reversed_unknown = apply_local(
        (), rules=rules, predictions=tuple(reversed(unknown))
    )
    assert unknown_result == reversed_unknown
    assert unknown_result.local_class is None
    assert unknown_result.local_status == "not_supported"
    assert "predicted-l1-l2-unknown" in unknown_result.local_rule_ids
    derived = predictions_from_row(
        predicted_l1="Receptor",
        predicted_l2=None,
        raw_fields={
            "predicted_l1_provenance": "iuphar-copy",
            "predicted_l1_relation": "iuphar",
        },
    )
    derived_result = apply_local(
        parse_ec_numbers("5.-.-.-"), rules=rules, predictions=derived
    )
    assert derived_result.local_class == "Enzyme"
    assert any(
        item.code == "dependent_prediction" for item in derived_result.diagnostics
    )
    assert "predicted-l1-l2-iuphar-derived" in derived_result.local_rule_ids
    assert not any(
        name.startswith("iuphar_") for name in derived_result.__dataclass_fields__
    )
    independent = predictions_from_row(
        predicted_l1="Receptor",
        predicted_l2=None,
        raw_fields={
            "predicted_l1_provenance": "chembl-class-table",
            "predicted_l1_relation": "independent",
        },
    )
    alone = apply_local((), rules=rules, predictions=independent)
    assert alone.local_class == "Receptor"
    assert "chembl-class-table" in alone.local_evidence_ids
    assert "predicted-l1-l2-independent" in alone.local_rule_ids
    conflict = apply_local(
        parse_ec_numbers("2.7.1.1"), rules=rules, predictions=independent
    )
    conflict_again = apply_local(
        parse_ec_numbers("2.7.1.1"),
        rules=tuple(reversed(rules)),
        predictions=independent,
    )
    assert conflict == conflict_again
    assert conflict.local_status == "conflicting"
    assert conflict.local_class is None


def test_free_text_and_rejected_nhr_rule_do_not_assign_a_class() -> None:
    rules = local_rules()
    text = apply_local(
        (),
        rules=rules,
        free_text="zinc finger transcription factor nuclear hormone receptor",
    )
    assert text.local_class is None
    assert "free_text" in text.local_candidates
    assert "rejected:tf-zinc-finger-nhr" not in text.local_rule_ids
    assert any(item.code == "broad_nhr_rule_excluded" for item in text.diagnostics)
    silent = apply_local((), rules=rules)
    assert "free_text" not in silent.local_candidates
    kept = apply_local(
        parse_ec_numbers("3.6.4.13"),
        rules=rules,
        free_text="transcription factor zinc finger",
        keyword_ids=("KW-0804", "KW-0805", "KW-0863"),
    )
    assert kept.local_class == "Enzyme"
    assert kept.local_class != "nuclear hormone receptor"
    assert kept == apply_local(
        parse_ec_numbers("3.6.4.13"),
        rules=tuple(reversed(rules)),
        free_text="transcription factor zinc finger",
        keyword_ids=("KW-0863", "KW-0805", "KW-0804"),
    )


@pytest.mark.parametrize("marker", ["", "N/A", "n/a", "#n/a", "   ", None])
def test_missing_markers_do_not_invent_a_class(marker: str | None) -> None:
    assert (
        apply_local(parse_ec_numbers(marker), rules=local_rules()).local_class is None
    )
    mixed = apply_local(
        parse_ec_numbers("1.1.1.1;n/a;N/A;#n/a"),
        rules=local_rules(),
        keyword_ids=("N/A", "n/a", "", "KW-0808"),
    )
    assert mixed.local_class == "Enzyme"
    assert mixed.ec_categories == ("Oxidoreductases",)
    assert not any(item.code == "invalid_ec" for item in mixed.diagnostics)


def test_several_ec_values_do_not_become_multifunctional() -> None:
    rules = local_rules()
    same = apply_local(parse_ec_numbers("2.7.1.21;2.7.1.74;2.7.1.-"), rules=rules)
    swapped = apply_local(parse_ec_numbers("2.7.1.74|2.7.1.-;2.7.1.21"), rules=rules)
    assert same == swapped
    assert same.local_class == "Enzyme"
    assert same.multiple_ec_categories is False
    different = apply_local(parse_ec_numbers("1.-.-.-;3.-.-.-"), rules=rules)
    assert different.local_class == "Enzyme"
    assert different.multiple_ec_categories is True
    assert different.local_status == "supported"
    for result in (same, swapped, different):
        assert result.local_class != "Multifunctional"
        assert "Multifunctional" not in result.local_candidates


def test_equal_priorities_conflict_and_a_unique_priority_is_order_independent() -> None:
    low = _rule("enzyme", "annotation", "keyword_id=KW-E", "Enzyme")
    high = replace(
        _rule("receptor", "annotation", "keyword_id=KW-R", "Receptor"), priority=200
    )
    tied = replace(high, priority=low.priority)
    winner = apply_local((), rules=(low, high), keyword_ids=("KW-E", "KW-R"))
    winner_again = apply_local((), rules=(high, low), keyword_ids=("KW-R", "KW-E"))
    assert winner == winner_again
    assert winner.local_status == "supported"
    assert winner.local_class == "Receptor"
    assert winner.local_candidates == ("Enzyme",)
    conflict = apply_local((), rules=(low, tied), keyword_ids=("KW-E", "KW-R"))
    conflict_again = apply_local((), rules=(tied, low), keyword_ids=("KW-R", "KW-E"))
    assert conflict == conflict_again
    assert conflict.local_status == "conflicting"
    assert conflict.local_class is None
    assert conflict.local_candidates == ("Enzyme", "Receptor")


@dataclass(frozen=True, slots=True)
class _HistoricalCache:
    """Rejected M outcome. It is not an input to the resolver."""

    local_class: str | None
    reason: str
    source: str = "historical_m_cache"


@dataclass(frozen=True, slots=True)
class _AuditCase:
    chembl_id: str
    ec: str
    keywords: tuple[str, ...]
    organism: str
    free_text: str
    historical_cache: _HistoricalCache
    gold_class: str
    gold_categories: tuple[str, ...]
    multiple: bool


_AUDIT = (
    _AuditCase(
        "CHEMBL4580",
        "2.7.1.-;2.7.1.21;2.7.1.74",
        ("KW-0418", "KW-0808"),
        "Homo sapiens",
        "Thymidine kinase 2, mitochondrial",
        _HistoricalCache(
            "Multifunctional",
            "three EC rows were treated as multiple functions",
        ),
        "Enzyme",
        ("Transferases",),
        False,
    ),
    _AuditCase(
        "CHEMBL5553",
        "3.6.4.13",
        ("KW-0378", "KW-0804", "KW-0805"),
        "Homo sapiens",
        "ATP-dependent RNA helicase DDX3X",
        _HistoricalCache(
            "nuclear hormone receptor",
            "transcription keywords were read as a nuclear receptor",
        ),
        "Enzyme",
        ("Hydrolases",),
        False,
    ),
    _AuditCase(
        "CHEMBL5036",
        "2.7.11.12",
        ("KW-0418", "KW-0808"),
        "unicellular",
        "cGMP-dependent protein kinase",
        _HistoricalCache(
            None,
            "unicellular kinase was dropped instead of classified",
        ),
        "Enzyme",
        ("Transferases",),
        False,
    ),
)


@pytest.mark.parametrize("case", _AUDIT, ids=lambda case: case.chembl_id)
def test_audit_counterexamples_keep_the_historical_cache_separate(
    case: _AuditCase,
) -> None:
    historical = case.historical_cache
    assert historical.source == "historical_m_cache"
    rules = local_rules()
    result = apply_local(
        parse_ec_numbers(case.ec),
        rules=rules,
        keyword_ids=case.keywords,
        free_text=case.free_text,
        organism=case.organism,
    )
    rotated = rules[7:] + rules[:7]
    again = apply_local(
        parse_ec_numbers(case.ec),
        rules=rotated,
        keyword_ids=tuple(reversed(case.keywords)),
        free_text=case.free_text,
        organism=case.organism,
    )
    assert result == again
    assert result.local_status == "supported"
    assert result.local_class == case.gold_class
    assert result.local_class != historical.local_class
    assert result.local_class != "Multifunctional"
    assert result.local_class != "nuclear hormone receptor"
    assert result.ec_categories == case.gold_categories
    assert result.multiple_ec_categories is case.multiple
    assert result.local_rule_ids
    assert result.local_evidence_ids
    assert not any(name.startswith("iuphar_") for name in result.__dataclass_fields__)


def test_pipeline_reads_prediction_evidence_instead_of_constants() -> None:
    from iuphar_target_class import pipeline
    from iuphar_target_class.hierarchy import FamilyNode
    from iuphar_target_class.matching import CatalogTarget
    from iuphar_target_class.models import RawTargetRow, RunProvenance

    snapshot = pipeline.IndexedSnapshot.build(
        snapshot_id="fixture",
        mapping_version="fixture-release",
        complete=True,
        catalog=(CatalogTarget("1", ("P12345",), "R1", "10", "Human", (), ()),),
        annotations={},
        family_nodes=(FamilyNode("family", (), "gpcr"),),
        type_to_class={},
        family_to_class={},
    )
    provenance = RunProvenance("fixture", "n", "r", "s", "t", "t")

    def run(fields: dict[str, str]) -> pipeline.RowResult:
        batch = pipeline.classify_batch(
            (RawTargetRow("row", fields, "protein"),),
            snapshot=snapshot,
            provenance=provenance,
            run_id="fixed",
        )
        return batch.rows[0]

    unknown = run({"predicted_l1": "Receptor", "predicted_l1_provenance": "n/a"})
    derived = run(
        {
            "predicted_l1": "Receptor",
            "predicted_l1_provenance": "iuphar-copy",
            "predicted_l1_relation": "iuphar",
        }
    )
    independent = run(
        {
            "predicted_l1": "Receptor",
            "predicted_l1_provenance": "chembl-class-table",
            "predicted_l1_relation": "independent",
        }
    )
    assert unknown.local is not None and unknown.local.local_class is None
    assert derived.local is not None and derived.local.local_class is None
    assert derived.local.local_class != "Receptor"
    assert independent.local is not None
    assert independent.local.local_class == "Receptor"
    assert "chembl-class-table" in independent.local.local_evidence_ids
    assert any(
        "catalog_sha256=" in record.content for record in independent.evidence.records
    )
    assert independent.result.iuphar_class is None
    mixed = run({"ec": "1.1.1.1;7.1.1.1"})
    local_contents = tuple(
        record.content
        for record in mixed.evidence.records
        if record.evidence_type == "local_rule"
    )
    assert any(
        content.startswith("ec:1.1.1.1; rules=ec-class:1,ec:1;")
        for content in local_contents
    )
    assert any(
        content.startswith("ec:7.1.1.1; rules=ec:7;") for content in local_contents
    )
    assert not any(
        "ec:7.1.1.1" in content and "ec-class:1" in content
        for content in local_contents
    )


def test_rf008_ec_tf_and_missing_markers_follow_the_source_tables() -> None:
    report = evaluate_categories(
        ("ec_category", "multiple_ec", "broad_tf_tag", "missing_marker")
    )
    assert report["unexplained_error_count"] == 0
    cases = report["cases"]
    assert isinstance(cases, list)
    ec_cases = [
        item
        for item in cases
        if isinstance(item, dict) and item["category"] == "ec_category"
    ]
    assert len(ec_cases) == 7
    assert all(item["disposition"] == "verified" for item in ec_cases)
    by_id = {str(item["case_id"]): item for item in cases if isinstance(item, dict)}
    assert by_id["local-tf-broad"]["observed"]["local_class"] is None
    assert by_id["local-tf-broad"]["observed"]["local_status"] == "not_supported"
    assert by_id["local-tf-broad"]["observed"]["free_text_rule_ids"] == ["free-text"]
    assert by_id["local-ec-7"]["observed"]["rule_output"] == "Translocases"
    assert by_id["local-ec-7"]["observed"]["rule_marks_direct_layer"] is False
    assert by_id["local-ec-7"]["observed"]["ec_categories"] == ["Translocases"]
    assert by_id["local-ec-7"]["observed"]["local_class"] is None
    parameters = policy_document()["parameters"]
    assert isinstance(parameters, dict)
    markers = by_id["local-missing-markers"]["observed"]
    assert isinstance(markers, dict)
    assert markers["version"] == parameters["missing_markers_version"]
    assert markers["version_status"] == parameters["missing_markers_version_status"]
