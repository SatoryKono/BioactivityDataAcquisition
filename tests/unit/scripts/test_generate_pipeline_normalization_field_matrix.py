"""Tests for code-derived pipeline normalization field-matrix generation."""

from __future__ import annotations

from pathlib import Path
from typing import cast

import pytest
import yaml

from scripts.docs.generate_pipeline_normalization_field_matrix import (
    CSV_NAME,
    CSV_COLUMNS,
    COMPOSITE_JOIN_KEY_COVERAGE_KPI,
    COMPOSITE_SOURCE_FIELD_COVERAGE_KPI,
    CONTROL_PLANE_NORMALIZATION_COVERAGE_KPI,
    DEFAULT_OUT_DIR,
    ENTITY_SILVER_SCHEMA_REGISTRY,
    ENTITY_RECORD_SURFACE,
    MD_NAME,
    NON_CHEMBL_MD_NAME,
    PROFILE_META_PASSTHROUGH_KPI,
    PROFILE_NON_META_PASSTHROUGH_FREE_KPI,
    PROFILE_SET_LIKE_JSON_STRING_KPI,
    _entity_config_paths,
    _load_yaml,
    build_artifacts,
    build_composite_join_key_policy_coverage_kpi,
    build_composite_sensitive_source_field_profile_coverage_kpi,
    build_control_plane_normalization_coverage_kpi,
    build_entity_profile_coverage_kpi,
    build_field_matrix_rows,
    build_profile_semantic_invariants,
    build_surface_coverage_kpis,
    check_artifacts,
    render_markdown,
    write_artifacts,
)
from bioetl.domain.normalization.profiles.chembl_json_ordering_policy import (
    CHEMBL_JSON_ORDERING_POLICY,
)
from bioetl.domain.normalization.publication_structured_fields import (
    publication_structured_field_policies,
)
from bioetl.domain.normalization.structured_payload_policies import (
    semantic_sensitive_structured_payload_policies,
)
from tests.helpers import (
    assert_check_artifacts_detects_drift,
    assert_check_artifacts_passes_for_fresh_outputs,
    assert_written_core_artifacts_are_deterministic,
)


def _row(
    rows: list[dict[str, str]], pipeline_name: str, field_name: str
) -> dict[str, str]:
    return next(
        row
        for row in rows
        if row["pipeline_name"] == pipeline_name and row["field_name"] == field_name
    )


def _assert_activity_governance_rows(rows: list[dict[str, str]]) -> None:
    standard_relation = _row(rows, "chembl_activity", "standard_relation")
    assert standard_relation["controlled_vocabulary_source"] == (
        "configs/enums/chembl.yaml"
    )
    assert standard_relation["strictness"] == "strict_operator"
    assert "domain_schema:present" in standard_relation["schema_coverage"]
    assert "checks=isin" in standard_relation["schema_coverage"]
    assert standard_relation["dq_coverage"] == "enum:error"

    assay_type = _row(rows, "chembl_activity", "assay_type")
    assert assay_type["controlled_vocabulary_source"] == "configs/enums/chembl.yaml"
    assert assay_type["strictness"] == "strict_enum"
    assert assay_type["dq_coverage"] == "enum:error"
    assert assay_type["policy_scope"] == "project_subset_of_provider_universe"

    standard_flag = _row(rows, "chembl_activity", "standard_flag")
    assert standard_flag["strictness"] == "strict_flag"
    assert standard_flag["controlled_vocabulary_source"] == (
        "configs/vocab/chembl_controlled.yaml"
    )
    assert "checks=isin" in standard_flag["schema_coverage"]
    assert standard_flag["dq_coverage"] == "range:error"
    assert standard_flag["policy_scope"] == "not_applicable"

    activity_properties = _row(rows, "chembl_activity", "activity_properties")
    assert activity_properties["normalizer"] == "normalize_profile_json_string_strict"
    assert activity_properties["hash_ordering"] == "set_like"
    assert activity_properties["strictness"] == "strict_json"
    assert (
        activity_properties["dq_coverage"]
        == "runtime_warning:malformed_json_normalized_to_null"
    )

    activity_units = _row(rows, "chembl_activity", "units")
    assert activity_units["semantic_category"] == "controlled_vocabulary"
    assert activity_units["normalizer"] == "normalize_profile_unit"
    assert activity_units["strictness"] == "controlled_unit"
    assert activity_units["dq_coverage"] == "pattern:error"
    assert activity_units["controlled_vocabulary_source"] == (
        "configs/vocab/chembl_controlled.yaml"
    )

    activity_standard_units = _row(rows, "chembl_activity", "standard_units")
    assert activity_standard_units["normalizer"] == "normalize_activity_standard_units"
    assert activity_standard_units["semantic_category"] == "controlled_vocabulary"
    assert activity_standard_units["strictness"] == "strict_enum"
    assert activity_standard_units["dq_coverage"] == "enum:error"
    assert activity_standard_units["controlled_vocabulary_source"] == (
        "configs/vocab/chembl_controlled.yaml"
    )


def _assert_activity_ontology_rows(rows: list[dict[str, str]]) -> None:
    activity_uo_units = _row(rows, "chembl_activity", "uo_units")
    assert activity_uo_units["semantic_category"] == "ontology_reference_identifier"
    assert activity_uo_units["strictness"] == "controlled_unit"
    assert activity_uo_units["dq_coverage"] == "pattern:error"
    assert activity_uo_units["controlled_vocabulary_source"] == (
        "configs/vocab/chembl_ontology.yaml"
    )

    activity_qudt_units = _row(rows, "chembl_activity", "qudt_units")
    assert activity_qudt_units["semantic_category"] == "ontology_reference_identifier"
    assert activity_qudt_units["strictness"] == "controlled_unit"
    assert activity_qudt_units["dq_coverage"] == "pattern:error"
    assert activity_qudt_units["controlled_vocabulary_source"] == (
        "configs/vocab/chembl_ontology.yaml"
    )

    bao_format = _row(rows, "chembl_activity", "bao_format")
    assert bao_format["semantic_category"] == "ontology_reference_identifier"
    assert bao_format["controlled_vocabulary_source"] == (
        "configs/vocab/chembl_ontology.yaml"
    )
    assert bao_format["strictness"] == "canonical_ontology_id"

    bao_endpoint_iri = _row(rows, "chembl_activity", "bao_endpoint_iri")
    assert (
        bao_endpoint_iri["normalizer"] == "normalize_profile_activity_bao_endpoint_iri"
    )
    assert bao_endpoint_iri["semantic_category"] == "ontology_reference_identifier"
    assert bao_endpoint_iri["controlled_vocabulary_source"] == (
        "configs/vocab/chembl_ontology.yaml"
    )

    bao_ontology_version = _row(rows, "chembl_activity", "bao_ontology_version")
    assert (
        bao_ontology_version["normalizer"]
        == "normalize_profile_activity_bao_ontology_version"
    )
    assert bao_ontology_version["semantic_category"] == "ontology_reference_metadata"
    assert bao_ontology_version["controlled_vocabulary_source"] == (
        "configs/vocab/chembl_ontology.yaml"
    )

    bao_mapping_status = _row(rows, "chembl_activity", "bao_endpoint_mapping_status")
    assert bao_mapping_status["controlled_vocabulary_source"] == (
        "configs/enums/chembl.yaml"
    )
    assert bao_mapping_status["strictness"] == "strict_enum"
    assert bao_mapping_status["policy_scope"] == "provider_full_universe"


def _assert_assay_parameter_rows(rows: list[dict[str, str]]) -> None:
    confidence_description = _row(rows, "chembl_assay", "confidence_description")
    assert confidence_description["semantic_category"] == "controlled_vocabulary"
    assert confidence_description["strictness"] == "strict_enum"
    assert confidence_description["dq_coverage"] == "enum:error"
    assert confidence_description["controlled_vocabulary_source"] == (
        "configs/vocab/chembl_controlled.yaml"
    )

    publication_term_type = _row(rows, "chembl_publication_term", "term_type")
    assert publication_term_type["controlled_vocabulary_source"] == (
        "configs/enums/chembl.yaml"
    )
    assert publication_term_type["strictness"] == "strict_enum"
    assert publication_term_type["dq_coverage"] == "enum:error"
    assert publication_term_type["policy_scope"] == "provider_full_universe"

    assay_parameter_units = _row(rows, "chembl_assay_parameters", "units")
    assert assay_parameter_units["semantic_category"] == "controlled_vocabulary"
    assert assay_parameter_units["strictness"] == "controlled_unit"
    assert assay_parameter_units["dq_coverage"] == "pattern:error"
    assert assay_parameter_units["controlled_vocabulary_source"] == (
        "configs/vocab/chembl_controlled.yaml"
    )

    assay_parameter_standard_type = _row(
        rows, "chembl_assay_parameters", "standard_type"
    )
    assert assay_parameter_standard_type["controlled_vocabulary_source"] == (
        "configs/enums/chembl.yaml"
    )
    assert assay_parameter_standard_type["policy_scope"] == "provider_full_universe"

    assay_parameter_type = _row(rows, "chembl_assay_parameters", "type")
    assert (
        assay_parameter_type["normalizer"]
        == "normalize_profile_assay_parameter_type_field"
    )
    assert assay_parameter_type["semantic_category"] == "controlled_vocabulary"
    assert assay_parameter_type["controlled_vocabulary_source"] == (
        "configs/vocab/chembl_controlled.yaml"
    )
    assert assay_parameter_type["strictness"] == "normalization_only"
    assert assay_parameter_type["dq_coverage"] == "pattern:error"

    assay_parameter_type_raw = _row(rows, "chembl_assay_parameters", "type_raw")
    assert assay_parameter_type_raw["normalizer"] == "normalize_profile_text"
    assert assay_parameter_type_raw["semantic_category"] == "free_text"

    assay_fraction_raw = _row(rows, "chembl_assay", "assay_subcellular_fraction_raw")
    assert assay_fraction_raw["normalizer"] == "normalize_profile_text"

    subcellular_fraction_raw = _row(
        rows, "chembl_subcellular_fraction", "subcellular_fraction_raw"
    )
    assert subcellular_fraction_raw["normalizer"] == "normalize_profile_text"


def _assert_publication_and_target_rows(rows: list[dict[str, str]]) -> None:
    publication_class = _row(rows, "chembl_publication", "publication_class")
    assert publication_class["semantic_category"] == "derived_vocabulary"
    assert publication_class["controlled_vocabulary_source"] == (
        "configs/enums/publication_type_classification.csv"
    )

    publication_doi = _row(rows, "chembl_publication", "publication_doi")
    assert publication_doi["semantic_category"] == "reference_identifier"
    assert publication_doi["controlled_vocabulary_source"] == (
        "configs/vocab/chembl_reference_identifiers.yaml"
    )
    assert publication_doi["normalizer"] == "normalize_profile_doi"
    assert publication_doi["strictness"] == "canonical_identifier"
    assert "domain_schema:present" in publication_doi["schema_coverage"]

    publication_type_raw = _row(rows, "chembl_publication", "publication_type_raw")
    assert "domain_schema:present" in publication_type_raw["schema_coverage"]

    publication_oa_status = _row(rows, "chembl_publication", "oa_status")
    assert "domain_schema:present" in publication_oa_status["schema_coverage"]

    target_cross_references = _row(rows, "chembl_target", "cross_references")
    assert (
        target_cross_references["normalizer"] == "normalize_profile_json_string_strict"
    )
    assert target_cross_references["strictness"] == "strict_json"
    assert (
        target_cross_references["dq_coverage"]
        == "runtime_warning:malformed_json_normalized_to_null"
    )

    target_component_types = _row(rows, "chembl_target", "component_types")
    assert target_component_types["set_like"] == "true"
    assert target_component_types["hash_ordering"] == "set_like"

    target_component_relationships = _row(
        rows, "chembl_target", "component_relationships"
    )
    assert target_component_relationships["set_like"] == "true"
    assert target_component_relationships["hash_ordering"] == "set_like"

    component_type = _row(rows, "chembl_target_component", "component_type")
    assert component_type["controlled_vocabulary_source"] == (
        "configs/enums/chembl.yaml"
    )

    component_accessions = _row(rows, "chembl_target", "component_accessions")
    assert component_accessions["semantic_category"] == "reference_identifier"
    assert component_accessions["controlled_vocabulary_source"] == (
        "configs/vocab/chembl_reference_identifiers.yaml"
    )
    assert component_accessions["normalizer"] == (
        "normalize_profile_uniprot_accessions_ordered"
    )
    assert component_accessions["hash_ordering"] == "order_sensitive"


def _assert_molecule_rows(rows: list[dict[str, str]]) -> None:
    molecule_properties = _row(rows, "chembl_molecule", "molecule_properties")
    assert molecule_properties["normalizer"] == "normalize_profile_json_string_strict"
    assert molecule_properties["strictness"] == "strict_json"
    assert (
        molecule_properties["dq_coverage"]
        == "runtime_warning:malformed_json_normalized_to_null"
    )

    molecule_type = _row(rows, "chembl_molecule", "molecule_type")
    assert molecule_type["policy_scope"] == "project_subset_of_provider_universe"

    ro3_pass = _row(rows, "chembl_molecule", "ro3_pass")
    assert ro3_pass["controlled_vocabulary_source"] == "configs/enums/chembl.yaml"
    assert ro3_pass["strictness"] == "strict_enum"
    assert ro3_pass["dq_coverage"] == "enum:error"

    max_phase = _row(rows, "chembl_molecule", "max_phase")
    assert max_phase["controlled_vocabulary_source"] == "configs/enums/chembl.yaml"
    assert max_phase["strictness"] == "strict_enum"
    assert max_phase["policy_scope"] == "provider_full_universe"


def test_generator_uses_checkpoint_package_facade() -> None:
    source = Path(
        "scripts/docs/generate_pipeline_normalization_field_matrix.py"
    ).read_text(encoding="utf-8")

    assert "from bioetl.application.composite.checkpoint import (" in source
    assert "checkpoint.anchor_context" not in source


def test_checkpoint_governance_import_contract_is_documented() -> None:
    facade_source = Path(
        "src/bioetl/application/composite/checkpoint/__init__.py"
    ).read_text(encoding="utf-8")
    plan_source = Path("docs/05-engineering/normalization_plan_P0_P6.md").read_text(
        encoding="utf-8"
    )

    assert "sanctioned public import surface" in facade_source
    assert "bioetl.application.composite.checkpoint.anchor_context" not in plan_source


def test_entity_schema_registry_matches_entity_config_inventory() -> None:
    expected_pipeline_names = set()
    for path in _entity_config_paths():
        payload = _load_yaml(path)
        pipeline = payload.get("pipeline")
        if not isinstance(pipeline, dict):
            continue
        expected_pipeline_names.add(str(pipeline.get("pipeline_name", "")).strip())

    assert "" not in expected_pipeline_names
    assert set(ENTITY_SILVER_SCHEMA_REGISTRY) == expected_pipeline_names


def test_build_field_matrix_rows_covers_entity_profile_and_generic_rules() -> None:
    rows = build_field_matrix_rows()

    chembl_activity_doi = _row(rows, "chembl_activity", "publication_doi")
    assert chembl_activity_doi["provider"] == "chembl"
    assert chembl_activity_doi["entity"] == "activity"
    assert chembl_activity_doi["normalization_source"] == "profile"
    assert chembl_activity_doi["normalizer"] == "normalize_profile_doi"
    assert chembl_activity_doi["include_in_content_hash"] == "true"
    assert chembl_activity_doi["hash_ordering"] == "order_sensitive"
    assert chembl_activity_doi["semantic_category"] == "reference_identifier"
    assert chembl_activity_doi["controlled_vocabulary_source"] == (
        "configs/vocab/chembl_reference_identifiers.yaml"
    )
    assert chembl_activity_doi["strictness"] == "canonical_identifier"

    crossref_title = _row(rows, "crossref_publication", "title")
    assert crossref_title["normalization_source"] == "profile"
    assert crossref_title["normalizer"] == "normalize_profile_title"

    pubmed_date = _row(rows, "pubmed_publication", "publication_date")
    assert pubmed_date["normalization_source"] == "profile"
    assert pubmed_date["normalizer"] == "normalize_profile_date"

    pubchem_smiles = _row(rows, "pubchem_compound", "canonical_smiles")
    assert pubchem_smiles["normalization_source"] == "profile"
    assert pubchem_smiles["normalizer"] == "normalize_profile_canonical_smiles"

    chembl_activity_smiles = _row(rows, "chembl_activity", "canonical_smiles")
    assert chembl_activity_smiles["normalization_source"] == "profile"
    assert chembl_activity_smiles["normalizer"] == "normalize_profile_canonical_smiles"

    openalex_title = _row(rows, "openalex_publication", "title")
    assert openalex_title["normalization_source"] == "profile"
    assert openalex_title["normalizer"] == "normalize_profile_title"

    semanticscholar_title = _row(rows, "semanticscholar_publication", "title")
    assert semanticscholar_title["normalization_source"] == "profile"
    assert semanticscholar_title["normalizer"] == "normalize_profile_title"

    chembl_molecule_smiles = _row(rows, "chembl_molecule", "canonical_smiles")
    assert chembl_molecule_smiles["normalization_source"] == "profile"
    assert chembl_molecule_smiles["normalizer"] == "normalize_profile_canonical_smiles"

    chembl_assay_title = _row(rows, "chembl_assay", "assay_pref_name")
    assert chembl_assay_title["normalization_source"] == "profile"
    assert chembl_assay_title["normalizer"] == "normalize_profile_title"

    chembl_publication_title = _row(rows, "chembl_publication", "title")
    assert chembl_publication_title["normalization_source"] == "profile"
    assert chembl_publication_title["normalizer"] == "normalize_profile_title"

    chembl_target_name = _row(rows, "chembl_target", "pref_name")
    assert chembl_target_name["normalization_source"] == "profile"
    assert chembl_target_name["normalizer"] == "normalize_profile_title"

    uniprot_idmapping_name = _row(rows, "uniprot_idmapping", "protein_name")
    assert uniprot_idmapping_name["normalization_source"] == "profile"
    assert uniprot_idmapping_name["normalizer"] == "normalize_profile_title"

    uniprot_protein_name = _row(rows, "uniprot_protein", "protein_name")
    assert uniprot_protein_name["normalization_source"] == "profile"
    assert uniprot_protein_name["normalizer"] == "normalize_profile_title"

    chembl_assay_parameters_run_id = _row(rows, "chembl_assay_parameters", "_run_id")
    assert chembl_assay_parameters_run_id["normalization_source"] == "profile"
    assert (
        chembl_assay_parameters_run_id["normalizer"] == "normalize_profile_passthrough"
    )
    assert chembl_assay_parameters_run_id["include_in_content_hash"] == "false"

    chembl_activity_run_id = _row(rows, "chembl_activity", "_run_id")
    assert chembl_activity_run_id["normalization_source"] == "profile"
    assert chembl_activity_run_id["normalizer"] == "normalize_profile_passthrough"
    assert chembl_activity_run_id["include_in_content_hash"] == "false"

    chembl_activity_index = _row(rows, "chembl_activity", "_index")
    assert chembl_activity_index["normalization_source"] == "profile"
    assert chembl_activity_index["normalizer"] == "normalize_profile_passthrough"
    assert chembl_activity_index["include_in_content_hash"] == "false"

    chembl_assay_parameters_json = _row(rows, "chembl_assay", "assay_parameters")
    assert (
        chembl_assay_parameters_json["normalizer"]
        == "normalize_profile_json_string_strict"
    )
    assert chembl_assay_parameters_json["strictness"] == "strict_json"
    assert (
        chembl_assay_parameters_json["dq_coverage"]
        == "runtime_warning:malformed_json_normalized_to_null"
    )

    chembl_publication_type = _row(rows, "chembl_publication", "publication_type")
    assert (
        chembl_publication_type["normalizer"]
        == "normalize_profile_publication_type_field"
    )
    assert chembl_publication_type["strictness"] == "strict_enum"
    assert chembl_publication_type["controlled_vocabulary_source"] == (
        "configs/enums/chembl.yaml"
    )
    assert chembl_publication_type["policy_scope"] == (
        "project_subset_of_provider_universe"
    )

    chembl_publication_is_oa = _row(rows, "chembl_publication", "is_oa")
    assert chembl_publication_is_oa["normalizer"] == "normalize_profile_boolean"
    assert chembl_publication_is_oa["strictness"] == "strict_boolean"
    assert chembl_publication_is_oa["controlled_vocabulary_source"] == (
        "configs/vocab/chembl_controlled.yaml"
    )

    chembl_target_component_organism = _row(rows, "chembl_target_component", "organism")
    assert (
        chembl_target_component_organism["normalizer"]
        == "normalize_profile_chembl_organism_name"
    )

    chembl_cell_line_cellosaurus = _row(rows, "chembl_cell_line", "cellosaurus_id")
    assert (
        chembl_cell_line_cellosaurus["normalizer"] == "normalize_profile_cellosaurus_id"
    )
    assert chembl_cell_line_cellosaurus["strictness"] == "canonical_identifier"

    chembl_assay_description = _row(rows, "chembl_assay", "description")
    assert chembl_assay_description["normalizer"] == "normalize_profile_null"

    chembl_target_component_id = _row(
        rows, "chembl_target_component", "protein_classification_id"
    )
    assert chembl_target_component_id["normalization_source"] == "profile"
    assert chembl_target_component_id["normalizer"] == "normalize_profile_int"

    chembl_publication_similarity_pmid = _row(
        rows, "chembl_publication_similarity", "pubmed_id1"
    )
    assert chembl_publication_similarity_pmid["normalization_source"] == "profile"
    assert chembl_publication_similarity_pmid["normalizer"] == "normalize_profile_pmid"


def test_build_field_matrix_rows_marks_composite_join_keys_and_inherited_fields() -> (
    None
):
    rows = build_field_matrix_rows()

    molecule_id = _row(rows, "composite_activity", "molecule_id")
    assert molecule_id["provider"] == "composite"
    assert molecule_id["entity"] == "activity"
    assert molecule_id["normalization_source"] == "composite_join_key_policy"
    assert molecule_id["normalizer"] == "join_key_policy"
    assert molecule_id["strictness"] == "join_key_policy"

    composite_pmid = _row(rows, "composite_publication", "pmid")
    assert (
        composite_pmid["normalization_summary"]
        == "Validate PMID through the canonical domain identifier contract, then emit digits-only join-canonical text."
    )

    standard_type = _row(rows, "composite_activity", "standard_type")
    assert standard_type["normalization_source"] == "upstream_inherited"
    assert standard_type["normalizer"] == "none"


def test_build_field_matrix_rows_exposes_dq_schema_and_vocab_governance() -> None:
    rows = build_field_matrix_rows()
    _assert_activity_governance_rows(rows)
    _assert_activity_ontology_rows(rows)
    _assert_assay_parameter_rows(rows)
    _assert_publication_and_target_rows(rows)
    _assert_molecule_rows(rows)


@pytest.mark.parametrize("policy", CHEMBL_JSON_ORDERING_POLICY)
def test_build_field_matrix_rows_exposes_reviewed_chembl_json_ordering(
    policy,
) -> None:
    rows = build_field_matrix_rows()
    row = _row(rows, policy.pipeline_name, policy.field_name)

    assert row["semantic_category"] in {
        "structured_json",
        "controlled_vocabulary",
        "reference_identifier",
    }
    assert row["set_like"] == ("true" if policy.is_set_like else "false")
    assert row["hash_ordering"] == policy.order_semantics


def test_build_field_matrix_rows_exposes_non_chembl_governance_sources() -> None:
    rows = build_field_matrix_rows()

    pubchem_standardization_status = _row(
        rows, "pubchem_compound", "chemical_standardization_status"
    )
    assert pubchem_standardization_status["controlled_vocabulary_source"] == (
        "configs/enums/pubchem.yaml"
    )
    assert pubchem_standardization_status["policy_scope"] == "provider_full_universe"

    pubchem_standardization_policy = _row(
        rows, "pubchem_compound", "chemical_standardization_policy_version"
    )
    assert pubchem_standardization_policy["controlled_vocabulary_source"] == (
        "configs/enums/pubchem.yaml"
    )
    assert pubchem_standardization_policy["policy_scope"] == "provider_full_universe"

    crossref_publication_type = _row(rows, "crossref_publication", "publication_type")
    assert crossref_publication_type["controlled_vocabulary_source"] == (
        "configs/vocab/publication_controlled.yaml"
    )
    assert crossref_publication_type["policy_scope"] == "provider_full_universe"

    openalex_publication_type = _row(rows, "openalex_publication", "publication_type")
    assert openalex_publication_type["controlled_vocabulary_source"] == (
        "configs/vocab/publication_controlled.yaml"
    )
    assert openalex_publication_type["policy_scope"] == "provider_full_universe"

    openalex_type_crossref = _row(rows, "openalex_publication", "type_crossref")
    assert openalex_type_crossref["controlled_vocabulary_source"] == (
        "configs/vocab/publication_controlled.yaml"
    )

    openalex_ror_ids = _row(rows, "openalex_publication", "ror_ids")
    assert openalex_ror_ids["normalizer"] == "normalize_profile_openalex_ror_ids"
    assert openalex_ror_ids["controlled_vocabulary_source"] == (
        "domain.normalization.reference_ids"
    )
    assert openalex_ror_ids["semantic_category"] == "ontology_reference_identifier"
    assert openalex_ror_ids["hash_ordering"] == "set_like"

    openalex_author_ids = _row(rows, "openalex_publication", "author_openalex_ids")
    assert openalex_author_ids["normalizer"] == "normalize_profile_openalex_author_ids"
    assert openalex_author_ids["controlled_vocabulary_source"] == (
        "domain.normalization.reference_ids"
    )
    assert openalex_author_ids["hash_ordering"] == "set_like"

    openalex_oa_status = _row(rows, "openalex_publication", "oa_status")
    assert openalex_oa_status["normalizer"] == "normalize_profile_oa_status"
    assert openalex_oa_status["controlled_vocabulary_source"] == (
        "domain.schemas.common.publication_base.OA_STATUS_VALUES"
    )
    assert openalex_oa_status["strictness"] == "strict_enum"

    semanticscholar_author_ids = _row(
        rows,
        "semanticscholar_publication",
        "author_s2_ids",
    )
    assert semanticscholar_author_ids["normalizer"] == (
        "normalize_profile_semantic_scholar_ids"
    )
    assert semanticscholar_author_ids["controlled_vocabulary_source"] == (
        "domain.normalization.reference_ids"
    )

    uniprot_go_terms = _row(rows, "uniprot_protein", "go_terms")
    assert uniprot_go_terms["normalizer"] == "normalize_profile_uniprot_go_references"
    assert uniprot_go_terms["controlled_vocabulary_source"] == (
        "domain.normalization.reference_ids"
    )
    assert uniprot_go_terms["semantic_category"] == "ontology_reference_identifier"

    uniprot_all_mappings = _row(rows, "uniprot_idmapping", "all_mappings")
    assert uniprot_all_mappings["normalizer"] == "normalize_profile_uniprot_accessions"
    assert uniprot_all_mappings["hash_ordering"] == "set_like"


def test_non_chembl_offline_fixture_cases_are_visible_in_matrix() -> None:
    fixture_path = (
        Path(__file__).resolve().parents[2]
        / "fixtures"
        / "normalization"
        / "non_chembl_identifier_cases.yaml"
    )
    cases = yaml.safe_load(fixture_path.read_text(encoding="utf-8"))
    rows = build_field_matrix_rows()

    for case in cases["publication_raw_type_policy"].values():
        row = _row(rows, case["profile"].replace(".", "_"), case["field"])
        assert row["controlled_vocabulary_source"] == (
            "configs/vocab/publication_controlled.yaml"
        )
        assert row["policy_scope"] == "provider_full_universe"
        assert row["strictness"] == "normalization_only"

    for case in cases["publication_oa_status_policy"].values():
        row = _row(rows, case["profile"].replace(".", "_"), case["field"])
        assert row["controlled_vocabulary_source"] == (
            "domain.schemas.common.publication_base.OA_STATUS_VALUES"
        )
        assert row["strictness"] == "strict_enum"

    for case in cases["publication_structured_field_policy"].values():
        row = _row(rows, case["profile"].replace(".", "_"), case["field"])
        assert row["semantic_category"] == "structured_json"
        assert row["hash_ordering"] == "set_like"
        assert row["controlled_vocabulary_source"] == (
            "configs/vocab/publication_controlled.yaml"
        )

    for section in (
        "composite_publication_join_keys",
        "composite_molecule_join_keys",
        "composite_target_join_keys",
    ):
        for case in cases[section].values():
            field_name = case.get("key")
            composite_name = case.get("composite")
            if not isinstance(field_name, str) or not isinstance(composite_name, str):
                continue

            row = _row(rows, composite_name, field_name)
            assert row["normalization_source"] == "composite_join_key_policy"
            assert row["normalizer"] == "join_key_policy"
            assert row["strictness"] == "join_key_policy"


def test_build_field_matrix_rows_exposes_non_chembl_composite_join_key_contracts() -> (
    None
):
    rows = build_field_matrix_rows()

    composite_publication_doi = _row(rows, "composite_publication", "doi")
    assert composite_publication_doi["normalization_summary"] == (
        "Validate DOI through the canonical domain identifier contract, then emit "
        "lowercase join-canonical text."
    )

    composite_molecule_inchi_key = _row(rows, "composite_molecule", "inchi_key")
    assert composite_molecule_inchi_key["normalization_summary"] == (
        "Validate InChIKey through the canonical domain value-object contract, then "
        "emit uppercase join-canonical text."
    )

    composite_target_target_id = _row(rows, "composite_target", "target_id")
    assert composite_target_target_id["normalization_summary"] == (
        "Validate ChEMBL target identifier through the canonical domain value-object "
        "contract, then emit uppercase join-canonical text."
    )

    composite_target_uniprot = _row(rows, "composite_target", "uniprot_accession")
    assert composite_target_uniprot["normalization_summary"] == (
        "Validate UniProt accession through the canonical domain value-object "
        "contract, then emit uppercase join-canonical text."
    )


def test_build_field_matrix_rows_exposes_publication_structured_field_registry() -> (
    None
):
    rows = build_field_matrix_rows()
    rows_by_key = {
        (row["provider"], row["entity"], row["field_name"]): row for row in rows
    }
    matched_policies = 0

    for policy in publication_structured_field_policies():
        provider, entity = policy.profile_name.split(".", maxsplit=1)
        row = rows_by_key.get((provider, entity, policy.field_name))
        if row is None:
            continue
        matched_policies += 1

        assert row["semantic_category"] in {
            "ontology_reference_identifier",
            "structured_json",
        }
        assert row["hash_ordering"] == policy.hash_ordering
        if policy.identifier_family is not None:
            assert row["controlled_vocabulary_source"] == (
                "domain.normalization.reference_ids"
            )

    assert matched_policies > 0


def test_build_field_matrix_rows_documents_structured_payload_sidecar_policy() -> None:
    rows = build_field_matrix_rows()

    for policy in semantic_sensitive_structured_payload_policies():
        pipeline_name = policy.profile_name.replace(".", "_")
        row = _row(rows, pipeline_name, policy.field_name)
        semantics = policy.collection_semantics.value.replace("_", " ")
        raw_row = _row(rows, pipeline_name, policy.raw_sidecar_field)
        canonical_row = _row(rows, pipeline_name, policy.canonical_sidecar_field)

        assert row["normalization_summary"] == row["notes"]
        assert semantics in row["notes"]
        assert policy.raw_sidecar_field in row["notes"]
        assert policy.canonical_sidecar_field in row["notes"]
        assert "not a raw provider substitute" in row["notes"]
        assert raw_row["normalizer"] == "normalize_profile_passthrough"
        assert canonical_row["field_type"] == "string"


def test_build_field_matrix_rows_keeps_chembl_cell_line_policy_fields_visible() -> None:
    rows = build_field_matrix_rows()

    cell_type = _row(rows, "chembl_cell_line", "cell_type")
    assert cell_type["normalization_source"] == "profile"
    assert cell_type["normalizer"] == "normalize_profile_null"
    assert cell_type["dq_coverage"] == "not_configured"

    clo_id = _row(rows, "chembl_cell_line", "clo_id")
    assert clo_id["semantic_category"] == "ontology_reference_identifier"
    assert (
        clo_id["controlled_vocabulary_source"] == "configs/vocab/chembl_ontology.yaml"
    )
    assert clo_id["strictness"] == "canonical_ontology_id"
    assert clo_id["dq_coverage"] == "pattern:error"

    efo_id = _row(rows, "chembl_cell_line", "efo_id")
    assert efo_id["semantic_category"] == "ontology_reference_identifier"
    assert (
        efo_id["controlled_vocabulary_source"] == "configs/vocab/chembl_ontology.yaml"
    )
    assert efo_id["dq_coverage"] == "pattern:error"


def test_build_field_matrix_rows_exposes_target_cross_reference_source_registry() -> (
    None
):
    rows = build_field_matrix_rows()

    cross_references = _row(rows, "chembl_target", "cross_references")
    assert cross_references["controlled_vocabulary_source"] == (
        "configs/vocab/chembl_reference_sources.yaml"
    )
    assert cross_references["strictness"] == "strict_json"

    target_component_xrefs = _row(
        rows, "chembl_target_component", "target_component_xrefs"
    )
    assert target_component_xrefs["controlled_vocabulary_source"] == (
        "configs/vocab/chembl_reference_sources.yaml"
    )
    assert target_component_xrefs["strictness"] == "strict_json"


def test_build_field_matrix_rows_explicitly_shows_no_governed_fields_for_audit_gap_pipelines() -> (
    None
):
    rows = build_field_matrix_rows()
    governed_sources = {
        row["pipeline_name"]: row["controlled_vocabulary_source"]
        for row in rows
        if row["pipeline_name"] in {"chembl_compound_record", "chembl_protein_class"}
        and row["controlled_vocabulary_source"]
    }

    assert governed_sources == {
        "chembl_compound_record": "configs/vocab/chembl_reference_identifiers.yaml",
        "chembl_protein_class": "configs/vocab/chembl_controlled.yaml",
    }


def test_build_field_matrix_rows_aligns_chembl_taxonomy_fields_to_integer_contract() -> (
    None
):
    rows = build_field_matrix_rows()

    for pipeline_name, field_name in [
        ("chembl_activity", "target_taxonomy_id"),
        ("chembl_assay", "assay_taxonomy_id"),
        ("chembl_assay", "variant_taxonomy_id"),
        ("chembl_target", "taxonomy_id"),
        ("chembl_target_component", "taxonomy_id"),
        ("chembl_cell_line", "cell_source_taxonomy_id"),
    ]:
        row = _row(rows, pipeline_name, field_name)
        assert row["normalization_source"] == "profile"
        assert row["normalizer"] == "normalize_profile_ncbi_taxonomy_id"
        assert row["semantic_category"] == "reference_identifier"
        assert row["controlled_vocabulary_source"] == (
            "configs/vocab/chembl_reference_identifiers.yaml"
        )
        assert row["strictness"] == "canonical_identifier"
        assert row["field_type"] == "int64"


def test_chembl_policy_bearing_fields_do_not_silently_stay_dq_not_configured() -> None:
    """Policy-bearing ChEMBL fields must carry an explicit DQ decision in the matrix."""
    rows = build_field_matrix_rows()
    governed_strictness = {
        "strict_enum",
        "strict_json",
        "controlled_unit",
        "ontology_id",
        "bool_like",
        "flag_like",
        "operator_enum",
        "controlled_vocabulary",
    }

    missing = [
        (row["pipeline_name"], row["field_name"], row["strictness"])
        for row in rows
        if row["pipeline_name"].startswith("chembl_")
        and row["strictness"] in governed_strictness
        and row["dq_coverage"] == "not_configured"
    ]

    assert missing == []


def test_build_entity_profile_coverage_kpi_summarizes_entity_rows() -> None:
    kpi = build_entity_profile_coverage_kpi(
        [
            {"pipeline_kind": "entity", "normalization_source": "profile"},
            {"pipeline_kind": "entity", "normalization_source": "profile"},
            {"pipeline_kind": "entity", "normalization_source": "fallback_business"},
            {
                "pipeline_kind": "composite",
                "normalization_source": "upstream_inherited",
            },
        ]
    )

    assert kpi["surface"] == ENTITY_RECORD_SURFACE
    assert kpi["name"] == "explicit_profile_coverage_pct"
    assert kpi["numerator"] == 2
    assert kpi["denominator"] == 3
    assert kpi["value_pct"] == pytest.approx(66.67)


def test_build_composite_join_key_policy_coverage_kpi_reports_configured_keys() -> None:
    kpi = build_composite_join_key_policy_coverage_kpi()

    assert kpi["surface"] == "composite_join_key"
    assert kpi["name"] == COMPOSITE_JOIN_KEY_COVERAGE_KPI
    assert int(cast(int, kpi["denominator"])) > 0
    assert float(cast(float, kpi["value_pct"])) == pytest.approx(100.0)


def test_build_composite_sensitive_source_field_profile_coverage_kpi_reports_governed_fields() -> (
    None
):
    kpi = build_composite_sensitive_source_field_profile_coverage_kpi()

    assert kpi["surface"] == "composite_source_field"
    assert kpi["name"] == COMPOSITE_SOURCE_FIELD_COVERAGE_KPI
    assert int(cast(int, kpi["denominator"])) > 0
    assert float(cast(float, kpi["value_pct"])) == pytest.approx(100.0)
    assert list(kpi["regressions"]) == []


def test_build_control_plane_normalization_coverage_kpi_reports_governed_seams() -> (
    None
):
    kpi = build_control_plane_normalization_coverage_kpi()

    assert kpi["surface"] == "control_plane_reproducibility"
    assert kpi["name"] == CONTROL_PLANE_NORMALIZATION_COVERAGE_KPI
    assert int(cast(int, kpi["denominator"])) == 6
    assert float(cast(float, kpi["value_pct"])) == pytest.approx(100.0)


def test_build_surface_coverage_kpis_lists_entity_composite_and_control_plane() -> None:
    kpis = build_surface_coverage_kpis(
        [
            {"pipeline_kind": "entity", "normalization_source": "profile"},
            {"pipeline_kind": "entity", "normalization_source": "fallback_business"},
        ]
    )

    assert [kpi["surface"] for kpi in kpis] == [
        "entity_record",
        "composite_join_key",
        "composite_source_field",
        "control_plane_reproducibility",
    ]


def test_build_profile_semantic_invariants_report_reviewed_semantics() -> None:
    kpis = build_profile_semantic_invariants()

    assert [kpi["name"] for kpi in kpis] == [
        PROFILE_META_PASSTHROUGH_KPI,
        PROFILE_SET_LIKE_JSON_STRING_KPI,
        PROFILE_NON_META_PASSTHROUGH_FREE_KPI,
    ]
    assert all(
        float(cast(float, kpi["value_pct"])) == pytest.approx(100.0) for kpi in kpis
    )
    assert all(kpi["surface"] == "profile_semantics" for kpi in kpis)
    assert all(list(kpi["regressions"]) == [] for kpi in kpis)


def test_render_markdown_mentions_surface_scoped_coverage_kpis() -> None:
    markdown = render_markdown(
        [
            {
                "pipeline_name": "chembl_activity",
                "pipeline_kind": "entity",
                "field_name": "publication_doi",
                "field_type": "string",
                "normalization_source": "profile",
                "normalizer": "normalize_profile_doi",
                "normalization_summary": "Normalize DOI.",
                "include_in_content_hash": "true",
                "set_like": "false",
                "notes": "",
            },
            {
                "pipeline_name": "chembl_assay_parameters",
                "pipeline_kind": "entity",
                "field_name": "_run_id",
                "field_type": "string",
                "normalization_source": "fallback_technical_passthrough",
                "normalizer": "passthrough",
                "normalization_summary": "Passthrough.",
                "include_in_content_hash": "",
                "set_like": "false",
                "notes": "",
            },
        ]
    )

    assert "## Surface Coverage Summary" in markdown
    assert "## Semantic Invariant Summary" in markdown
    assert "Entity coverage is entity-scoped only" in markdown
    assert "controlled_vocabulary_source" in markdown
    assert "policy_scope" in markdown
    assert "semantic_category" in markdown
    assert "schema_coverage" in markdown
    assert "dq_coverage" in markdown
    assert "classification" in markdown
    assert "identifier_family" in markdown
    assert "raw_sidecar" in markdown
    assert "composite_usage" in markdown
    assert "observed_source" in markdown
    assert (
        "- entity_record / explicit_profile_coverage_pct: `50.00%` (`1` / `2`)"
        in markdown
    )
    assert "composite_join_key / composite_join_key_policy_coverage_pct" in markdown
    assert (
        "composite_source_field / composite_sensitive_source_field_profile_coverage_pct"
        in markdown
    )
    assert (
        "control_plane_reproducibility / control_plane_normalization_coverage_pct"
        in markdown
    )
    assert "profile_semantics / shipped_profile_meta_passthrough_pct" in markdown


def test_write_artifacts_is_deterministic(tmp_path: Path) -> None:
    def _assert_semantic_payload(first_payload: object, second_payload: object) -> None:
        assert isinstance(first_payload, dict)
        assert isinstance(second_payload, dict)
        first_payload_dict = cast(dict[str, object], first_payload)
        second_payload_dict = cast(dict[str, object], second_payload)
        first_kpis = first_payload_dict["semantic_kpis"]
        second_kpis = second_payload_dict["semantic_kpis"]
        assert [kpi["name"] for kpi in first_kpis] == [
            PROFILE_META_PASSTHROUGH_KPI,
            PROFILE_SET_LIKE_JSON_STRING_KPI,
            PROFILE_NON_META_PASSTHROUGH_FREE_KPI,
        ]
        assert first_kpis == second_kpis

    assert_written_core_artifacts_are_deterministic(
        tmp_path,
        write_artifacts=write_artifacts,
        csv_name=CSV_NAME,
        md_name=MD_NAME,
        payload_assertion=_assert_semantic_payload,
    )


def test_check_artifacts_detects_drift(tmp_path: Path) -> None:
    assert_check_artifacts_detects_drift(
        tmp_path,
        build_artifacts=build_artifacts,
        check_artifacts=check_artifacts,
        csv_name=CSV_NAME,
        md_name=MD_NAME,
    )


def test_check_artifacts_returns_zero_for_fresh_outputs(tmp_path: Path) -> None:
    assert_check_artifacts_passes_for_fresh_outputs(
        tmp_path,
        write_artifacts=write_artifacts,
        check_artifacts=check_artifacts,
    )


def test_non_chembl_rows_include_inventory_evidence_columns() -> None:
    rows = build_field_matrix_rows()

    openalex_type = _row(rows, "openalex_publication", "publication_type")
    assert openalex_type["classification"] == "raw_provider_value"
    assert openalex_type["observed_source"]
    assert openalex_type["dq_rule"] == openalex_type["dq_coverage"]

    pubmed_taxonomy = _row(rows, "pubmed_publication", "publication_type_unified")
    assert pubmed_taxonomy["classification"] == "derived_vocabulary"
    assert pubmed_taxonomy["controlled_vocabulary_source"] == (
        "configs/enums/publication_type_classification.csv"
    )

    uniprot_features = _row(rows, "uniprot_protein", "features_json")
    assert uniprot_features["classification"] == "structured_json_sidecar"
    assert uniprot_features["raw_sidecar"] == "features_raw_json"
    assert uniprot_features["canonical_sidecar"] == "features_canonical_json"


def test_build_artifacts_emits_non_chembl_slice() -> None:
    artifacts = build_artifacts()

    assert NON_CHEMBL_MD_NAME in artifacts
    assert "openalex_publication" in artifacts[NON_CHEMBL_MD_NAME]
    assert "chembl_activity" not in artifacts[NON_CHEMBL_MD_NAME]


def test_csv_columns_include_non_chembl_inventory_evidence_fields() -> None:
    assert "classification" in CSV_COLUMNS
    assert "identifier_family" in CSV_COLUMNS
    assert "collection_semantics" in CSV_COLUMNS
    assert "raw_sidecar" in CSV_COLUMNS
    assert "canonical_sidecar" in CSV_COLUMNS
    assert "dq_rule" in CSV_COLUMNS
    assert "composite_usage" in CSV_COLUMNS
    assert "observed_source" in CSV_COLUMNS


def test_committed_artifacts_match_generator_output() -> None:
    assert check_artifacts(DEFAULT_OUT_DIR.resolve()) == 0
