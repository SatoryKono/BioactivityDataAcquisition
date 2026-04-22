"""Tests for additional shipped normalization profiles."""

from __future__ import annotations

from bioetl.domain.normalization.profiles import (
    CROSSREF_PUBLICATION_PROFILE,
    CROSSREF_PUBLICATION_SCHEMA_FIELDS,
    PUBCHEM_COMPOUND_PROFILE,
    PUBCHEM_COMPOUND_SCHEMA_FIELDS,
    PUBMED_PUBLICATION_PROFILE,
    PUBMED_PUBLICATION_SCHEMA_FIELDS,
)
from bioetl.domain.normalization.profiles._standard_profile_builder import (
    build_standard_profile,
)
from bioetl.domain.normalization.profiles.profile_normalizers import (
    normalize_profile_canonical_smiles,
)


def test_crossref_publication_profile_covers_schema_exactly() -> None:
    CROSSREF_PUBLICATION_PROFILE.assert_covers_schema(
        CROSSREF_PUBLICATION_SCHEMA_FIELDS
    )


def test_pubmed_publication_profile_covers_schema_exactly() -> None:
    PUBMED_PUBLICATION_PROFILE.assert_covers_schema(PUBMED_PUBLICATION_SCHEMA_FIELDS)


def test_pubchem_compound_profile_covers_schema_exactly() -> None:
    PUBCHEM_COMPOUND_PROFILE.assert_covers_schema(PUBCHEM_COMPOUND_SCHEMA_FIELDS)


def test_meta_fields_are_excluded_from_hash_across_shipped_profiles() -> None:
    assert "_run_id" in CROSSREF_PUBLICATION_PROFILE.hash_excluded_fields
    assert "_run_id" in PUBMED_PUBLICATION_PROFILE.hash_excluded_fields
    assert "_run_id" in PUBCHEM_COMPOUND_PROFILE.hash_excluded_fields


def test_pubchem_smiles_rules_use_domain_smiles_normalization() -> None:
    canonical_rule = PUBCHEM_COMPOUND_PROFILE.rule_for("canonical_smiles")
    isomeric_rule = PUBCHEM_COMPOUND_PROFILE.rule_for("isomeric_smiles")

    assert canonical_rule is not None
    assert canonical_rule.apply(" C ") == "C"
    assert isomeric_rule is not None
    assert isomeric_rule.apply(" C ") == "C"


def test_standard_profile_builder_accepts_legacy_single_item_special_rules() -> None:
    profile = build_standard_profile(
        profile_name="test.legacy_special_rule",
        description="Regression profile for single-item custom rule components.",
        schema_fields=("canonical_smiles",),
        meta_fields=(),
        special_rules={
            "canonical_smiles": (normalize_profile_canonical_smiles,),
        },
    )

    canonical_rule = profile.rule_for("canonical_smiles")

    assert canonical_rule is not None
    assert canonical_rule.apply(" C ") == "C"
    assert canonical_rule.notes == (
        "Apply custom normalization rule for field 'canonical_smiles'."
    )


def test_standard_profile_builder_applies_boolean_flag_and_operator_families() -> None:
    profile = build_standard_profile(
        profile_name="test.rule_families",
        description="Regression profile for shared normalization rule families.",
        schema_fields=("reviewed", "standard_flag", "standard_relation", "bto_id"),
        meta_fields=(),
        boolean_fields=("reviewed",),
        flag_fields=("standard_flag",),
        operator_fields=("standard_relation",),
        ontology_id_fields=("bto_id",),
    )

    reviewed_rule = profile.rule_for("reviewed")
    flag_rule = profile.rule_for("standard_flag")
    relation_rule = profile.rule_for("standard_relation")
    bto_rule = profile.rule_for("bto_id")

    assert reviewed_rule is not None
    assert reviewed_rule.apply("Y") is True
    assert reviewed_rule.apply("false") is False
    assert flag_rule is not None
    assert flag_rule.apply("yes") == 1
    assert flag_rule.apply("0") == 0
    assert relation_rule is not None
    assert relation_rule.apply("≤") == "<="
    assert relation_rule.apply("approx") == "~"
    assert bto_rule is not None
    assert bto_rule.apply("bto:0000089") == "BTO_0000089"
    assert "ontology ID" in (bto_rule.notes or "")
