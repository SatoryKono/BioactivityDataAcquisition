"""Tests for code-derived pipeline normalization field-matrix generation."""

from __future__ import annotations

from pathlib import Path
from typing import cast

import pytest

from scripts.docs.generate_pipeline_normalization_field_matrix import (
    CSV_NAME,
    COMPOSITE_JOIN_KEY_COVERAGE_KPI,
    COMPOSITE_SOURCE_FIELD_COVERAGE_KPI,
    CONTROL_PLANE_NORMALIZATION_COVERAGE_KPI,
    DEFAULT_OUT_DIR,
    ENTITY_SILVER_SCHEMA_REGISTRY,
    ENTITY_RECORD_SURFACE,
    MD_NAME,
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
    shim_source = Path(
        "src/bioetl/application/composite/checkpoint/anchor_context.py"
    ).read_text(encoding="utf-8")
    plan_source = Path("docs/05-engineering/normalization_plan_P0_P6.md").read_text(
        encoding="utf-8"
    )

    assert "sanctioned public import surface" in facade_source
    assert "compatibility-only shim" in shim_source
    assert "bioetl.application.composite.checkpoint.anchor_context" in plan_source


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

    chembl_publication_type = _row(rows, "chembl_publication", "publication_type")
    assert (
        chembl_publication_type["normalizer"]
        == "normalize_profile_publication_type_field"
    )
    assert chembl_publication_type["strictness"] == "strict_enum"

    chembl_publication_is_oa = _row(rows, "chembl_publication", "is_oa")
    assert chembl_publication_is_oa["normalizer"] == "normalize_profile_boolean"
    assert chembl_publication_is_oa["strictness"] == "strict_boolean"

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

    standard_flag = _row(rows, "chembl_activity", "standard_flag")
    assert standard_flag["strictness"] == "strict_flag"
    assert "checks=isin" in standard_flag["schema_coverage"]
    assert standard_flag["dq_coverage"] == "range:error"

    activity_properties = _row(rows, "chembl_activity", "activity_properties")
    assert activity_properties["normalizer"] == "normalize_profile_json_string"
    assert activity_properties["hash_ordering"] == "set_like"
    assert activity_properties["strictness"] == "canonical_json"

    activity_units = _row(rows, "chembl_activity", "units")
    assert activity_units["normalizer"] == "normalize_profile_unit"
    assert activity_units["strictness"] == "controlled_unit"

    bao_format = _row(rows, "chembl_activity", "bao_format")
    assert bao_format["controlled_vocabulary_source"] == (
        "domain.normalization.ontology_id_prefixes"
    )
    assert bao_format["strictness"] == "canonical_ontology_id"

    publication_term_type = _row(rows, "chembl_publication_term", "term_type")
    assert publication_term_type["controlled_vocabulary_source"] == (
        "configs/enums/chembl.yaml"
    )
    assert publication_term_type["strictness"] == "strict_enum"
    assert publication_term_type["dq_coverage"] == "enum:error"


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
    assert "schema_coverage" in markdown
    assert "dq_coverage" in markdown
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


def test_committed_artifacts_match_generator_output() -> None:
    assert check_artifacts(DEFAULT_OUT_DIR.resolve()) == 0
