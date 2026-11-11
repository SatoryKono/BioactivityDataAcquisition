"""TC-07 local layer: EC categories, annotations, and predictions."""

from __future__ import annotations

import pytest

from iuphar_target_class.local_layer import Prediction, apply_local
from iuphar_target_class.normalization import parse_ec_numbers
from iuphar_target_class.policy import PLAN_SOURCE, PLAN_VERSION, RuleRecord

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


def test_broken_rule_blocks_processing() -> None:
    broken = _rule("bad", "annotation", "keyword_id=KW-1", "Enzyme", version="")
    with pytest.raises(ValueError, match="missing version"):
        apply_local((), rules=(broken,), keyword_ids=("KW-1",))
