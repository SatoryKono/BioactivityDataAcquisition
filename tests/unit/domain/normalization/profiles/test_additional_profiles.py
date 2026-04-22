"""Tests for additional shipped normalization profiles."""

from __future__ import annotations

from bioetl.domain.normalization.profiles import (
    CHEMBL_TARGET_PROFILE,
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
from bioetl.domain.normalization.profiles._chembl_profile_helpers import (
    CHEMBL_META_FIELDS,
    build_chembl_profile,
    chembl_schema_fields,
)
from bioetl.domain.normalization.profiles.profile_normalizers import (
    normalize_profile_canonical_smiles,
)
from bioetl.domain.schemas.chembl.publication_term import PublicationTermSchema


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


def test_chembl_target_organism_display_normalization_is_profile_visible() -> None:
    organism_rule = CHEMBL_TARGET_PROFILE.rule_for("organism")

    assert organism_rule is not None
    assert organism_rule.apply("  homo   sapiens  ") == "Homo sapiens"
    assert organism_rule.apply("e. coli") == "Escherichia coli"
    assert "organism" in (organism_rule.notes or "").lower()


def test_chembl_profile_helpers_preserve_standard_meta_semantics() -> None:
    schema_fields = chembl_schema_fields(PublicationTermSchema)
    profile = build_chembl_profile(
        entity="helper_probe",
        schema_fields=schema_fields,
    )

    assert profile.meta_fields == CHEMBL_META_FIELDS
    assert "_run_id" in profile.hash_excluded_fields
    assert "term_type" in profile.hash_included_fields


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
