"""Unit tests for the ChEMBL Assay Parameters normalization profile."""

from __future__ import annotations

from bioetl.domain.normalization.profiles import (
    CHEMBL_ASSAY_PARAMETERS_PROFILE,
    CHEMBL_ASSAY_PARAMETERS_SCHEMA_FIELDS,
)
from bioetl.domain.normalization.profiles.profile_normalizers import (
    normalize_profile_json_string,
)


def test_chembl_assay_parameters_profile_covers_schema_exactly() -> None:
    missing, extra = CHEMBL_ASSAY_PARAMETERS_PROFILE.coverage_gaps(
        CHEMBL_ASSAY_PARAMETERS_SCHEMA_FIELDS
    )

    assert missing == frozenset()
    assert extra == frozenset()


def test_chembl_assay_parameters_profile_centralizes_business_canonicalization() -> (
    None
):
    type_rule = CHEMBL_ASSAY_PARAMETERS_PROFILE.rule_for("type")
    relation_rule = CHEMBL_ASSAY_PARAMETERS_PROFILE.rule_for("relation")
    standard_relation_rule = CHEMBL_ASSAY_PARAMETERS_PROFILE.rule_for(
        "standard_relation"
    )
    units_rule = CHEMBL_ASSAY_PARAMETERS_PROFILE.rule_for("units")
    standard_units_rule = CHEMBL_ASSAY_PARAMETERS_PROFILE.rule_for("standard_units")
    standard_type_rule = CHEMBL_ASSAY_PARAMETERS_PROFILE.rule_for("standard_type")

    assert type_rule is not None
    assert type_rule.normalizer(" conc ") == "CONC"
    assert type_rule.normalizer("unexpected_new_type") == "UNEXPECTED_NEW_TYPE"
    assert "without rejecting unknown" in (type_rule.notes or "")

    assert relation_rule is not None
    assert relation_rule.normalizer("≤") == "<="

    assert standard_relation_rule is not None
    assert standard_relation_rule.normalizer("gte") == ">="

    assert units_rule is not None
    assert units_rule.normalizer("uM") == "µM"
    assert "Canonicalize units" in (units_rule.notes or "")

    assert standard_units_rule is not None
    assert standard_units_rule.normalizer("μM") == "µM"

    assert standard_type_rule is not None
    assert standard_type_rule.normalizer(" conc ") == "CONC"
    assert standard_type_rule.normalizer("unknown") is None


def test_chembl_assay_parameters_comments_are_plain_text_not_json_by_default() -> None:
    comments_rule = CHEMBL_ASSAY_PARAMETERS_PROFILE.rule_for("comments")

    assert comments_rule is not None
    assert comments_rule.normalizer is not normalize_profile_json_string
    assert comments_rule.normalizer(' {"b":2,"a":1} ') == '{"b":2,"a":1}'
    assert "plain text" in (comments_rule.notes or "")
