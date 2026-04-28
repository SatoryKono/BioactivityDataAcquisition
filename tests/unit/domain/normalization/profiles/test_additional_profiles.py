"""Tests for additional shipped normalization profiles."""

from __future__ import annotations

from bioetl.domain.normalization.profiles import (
    CHEMBL_ACTIVITY_PROFILE,
    CHEMBL_ASSAY_PARAMETERS_PROFILE,
    CHEMBL_ASSAY_PROFILE,
    CHEMBL_CELL_LINE_PROFILE,
    CHEMBL_MOLECULE_PROFILE,
    CHEMBL_PUBLICATION_PROFILE,
    CHEMBL_SUBCELLULAR_FRACTION_PROFILE,
    CHEMBL_TARGET_PROFILE,
    CHEMBL_TARGET_COMPONENT_PROFILE,
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
    ChemblProfileFieldGroups,
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


def test_chembl_target_component_organism_display_normalization_is_profile_visible() -> (
    None
):
    organism_rule = CHEMBL_TARGET_COMPONENT_PROFILE.rule_for("organism")

    assert organism_rule is not None
    assert organism_rule.apply("  homo   sapiens  ") == "Homo sapiens"
    assert organism_rule.apply("e. coli") == "Escherichia coli"
    assert "organism" in (organism_rule.notes or "").lower()


def test_chembl_cell_line_cellosaurus_id_uses_canonical_identifier_rule() -> None:
    cellosaurus_rule = CHEMBL_CELL_LINE_PROFILE.rule_for("cellosaurus_id")

    assert cellosaurus_rule is not None
    assert cellosaurus_rule.apply(" cvcl:0030 ") == "CVCL_0030"
    assert cellosaurus_rule.apply("CVCL-0031") == "CVCL_0031"
    assert "Cellosaurus" in (cellosaurus_rule.notes or "")


def test_chembl_molecule_ro3_pass_is_registry_governed_strict_enum() -> None:
    ro3_pass_rule = CHEMBL_MOLECULE_PROFILE.rule_for("ro3_pass")

    assert ro3_pass_rule is not None
    assert ro3_pass_rule.apply(" y ") == "Y"
    assert ro3_pass_rule.apply("n") == "N"
    assert ro3_pass_rule.apply("maybe") is None


def test_chembl_molecule_max_phase_preserves_quasi_enum_numeric_codes() -> None:
    max_phase_rule = CHEMBL_MOLECULE_PROFILE.rule_for("max_phase")

    assert max_phase_rule is not None
    assert max_phase_rule.apply(" 0.5 ") == 0.5
    assert max_phase_rule.apply("4.0") == 4
    assert max_phase_rule.apply("5") is None
    assert "quasi-enum" in (max_phase_rule.notes or "")


def test_chembl_publication_profile_normalizes_publication_type_and_open_access() -> (
    None
):
    publication_type_rule = CHEMBL_PUBLICATION_PROFILE.rule_for("publication_type")
    publication_type_raw_rule = CHEMBL_PUBLICATION_PROFILE.rule_for(
        "publication_type_raw"
    )
    is_oa_rule = CHEMBL_PUBLICATION_PROFILE.rule_for("is_oa")
    authors_rule = CHEMBL_PUBLICATION_PROFILE.rule_for("authors")

    assert publication_type_rule is not None
    assert publication_type_raw_rule is not None
    assert publication_type_raw_rule.apply(" publication ") == "PUBLICATION"
    assert "provider-native uppercase token" in (publication_type_raw_rule.notes or "")
    assert publication_type_rule.apply(" PUBLICATION ") == "journal-article"
    assert publication_type_rule.apply("BOOK") == "book"
    assert is_oa_rule is not None
    assert is_oa_rule.apply("1") is True
    assert is_oa_rule.apply("false") is False
    assert authors_rule is not None
    assert authors_rule.apply(' {"b":2,"a":1} ') == '{"a":1,"b":2}'
    assert authors_rule.apply("not-json") is None


def test_chembl_assay_parameter_type_preserves_unknown_for_raw_review() -> None:
    assay_parameter_type_rule = CHEMBL_ASSAY_PARAMETERS_PROFILE.rule_for("type")

    assert assay_parameter_type_rule is not None
    assert assay_parameter_type_rule.apply(" conc ") == "CONC"
    assert assay_parameter_type_rule.apply("novel assay tag") == "NOVEL ASSAY TAG"
    assert assay_parameter_type_rule.apply("   ") is None
    assert "raw-vs-canonical review" in (assay_parameter_type_rule.notes or "")


def test_chembl_activity_mapping_status_companions_use_shared_enum_family() -> None:
    bao_mapping_rule = CHEMBL_ACTIVITY_PROFILE.rule_for("bao_endpoint_mapping_status")
    qudt_mapping_rule = CHEMBL_ACTIVITY_PROFILE.rule_for("qudt_unit_mapping_status")

    assert bao_mapping_rule is not None
    assert bao_mapping_rule.apply(" Mapped ") == "mapped"
    assert bao_mapping_rule.apply("unknown") is None
    assert qudt_mapping_rule is not None
    assert qudt_mapping_rule.apply("UNMAPPED") == "unmapped"


def test_chembl_subcellular_fraction_profiles_preserve_unknown_but_not_blank() -> None:
    assay_fraction_rule = CHEMBL_ASSAY_PROFILE.rule_for("assay_subcellular_fraction")
    aggregate_fraction_rule = CHEMBL_SUBCELLULAR_FRACTION_PROFILE.rule_for(
        "subcellular_fraction"
    )

    assert assay_fraction_rule is not None
    assert assay_fraction_rule.apply(" membrane ") == "Membrane"
    assert assay_fraction_rule.apply("microsome fraction") == "microsome fraction"
    assert assay_fraction_rule.apply("   ") is None

    assert aggregate_fraction_rule is not None
    assert aggregate_fraction_rule.apply(" nucleus ") == "Nucleus"
    assert (
        aggregate_fraction_rule.apply("custom fraction label")
        == "custom fraction label"
    )
    assert aggregate_fraction_rule.apply("   ") is None


def test_chembl_target_component_vocab_lists_fail_closed_on_unknown_members() -> None:
    component_types_rule = CHEMBL_TARGET_PROFILE.rule_for("component_types")
    component_relationships_rule = CHEMBL_TARGET_PROFILE.rule_for(
        "component_relationships"
    )

    assert component_types_rule is not None
    assert component_types_rule.apply('["protein","RNA"]') == '["PROTEIN","RNA"]'
    assert component_types_rule.apply('["protein","mystery"]') is None

    assert component_relationships_rule is not None
    assert (
        component_relationships_rule.apply('["single protein","INTERACTING PROTEIN"]')
        == '["SINGLE PROTEIN","INTERACTING PROTEIN"]'
    )
    assert component_relationships_rule.apply('["SINGLE PROTEIN","UNKNOWN"]') is None


def test_chembl_profile_helpers_preserve_standard_meta_semantics() -> None:
    schema_fields = chembl_schema_fields(PublicationTermSchema)
    profile = build_chembl_profile(
        entity="helper_probe",
        schema_fields=schema_fields,
        field_groups=ChemblProfileFieldGroups(),
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


def test_standard_profile_builder_applies_strict_json_family() -> None:
    profile = build_standard_profile(
        profile_name="test.strict_json_rule_family",
        description="Regression profile for strict JSON normalization fields.",
        schema_fields=("payload",),
        meta_fields=(),
        strict_json_fields=("payload",),
    )

    payload_rule = profile.rule_for("payload")

    assert payload_rule is not None
    assert payload_rule.apply(' {"b":2,"a":1} ') == '{"a":1,"b":2}'
    assert payload_rule.apply("not-json") is None
    assert "malformed JSON" in (payload_rule.notes or "")
