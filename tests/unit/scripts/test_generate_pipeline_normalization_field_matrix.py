"""Tests for code-derived pipeline normalization field-matrix generation."""

from __future__ import annotations

from pathlib import Path

from scripts.docs.generate_pipeline_normalization_field_matrix import (
    CSV_NAME,
    DEFAULT_OUT_DIR,
    MD_NAME,
    build_artifacts,
    build_entity_profile_coverage_kpi,
    build_field_matrix_rows,
    check_artifacts,
    render_markdown,
    write_artifacts,
)


def _row(rows: list[dict[str, str]], pipeline_name: str, field_name: str) -> dict[str, str]:
    return next(
        row
        for row in rows
        if row["pipeline_name"] == pipeline_name and row["field_name"] == field_name
    )


def test_build_field_matrix_rows_covers_entity_profile_and_generic_rules() -> None:
    rows = build_field_matrix_rows()

    chembl_activity_doi = _row(rows, "chembl_activity", "publication_doi")
    assert chembl_activity_doi["normalization_source"] == "profile"
    assert chembl_activity_doi["normalizer"] == "normalize_profile_doi"
    assert chembl_activity_doi["include_in_content_hash"] == "true"

    crossref_title = _row(rows, "crossref_publication", "title")
    assert crossref_title["normalization_source"] == "profile"
    assert crossref_title["normalizer"] == "normalize_profile_title"

    pubmed_date = _row(rows, "pubmed_publication", "publication_date")
    assert pubmed_date["normalization_source"] == "profile"
    assert pubmed_date["normalizer"] == "normalize_profile_date"

    pubchem_smiles = _row(rows, "pubchem_compound", "canonical_smiles")
    assert pubchem_smiles["normalization_source"] == "profile"
    assert pubchem_smiles["normalizer"] == "_normalize_canonical_smiles"

    openalex_title = _row(rows, "openalex_publication", "title")
    assert openalex_title["normalization_source"] == "profile"
    assert openalex_title["normalizer"] == "normalize_profile_title"

    semanticscholar_title = _row(rows, "semanticscholar_publication", "title")
    assert semanticscholar_title["normalization_source"] == "profile"
    assert semanticscholar_title["normalizer"] == "normalize_profile_title"

    chembl_molecule_smiles = _row(rows, "chembl_molecule", "canonical_smiles")
    assert chembl_molecule_smiles["normalization_source"] == "profile"
    assert chembl_molecule_smiles["normalizer"] == "_normalize_canonical_smiles"

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
    assert chembl_assay_parameters_run_id["normalizer"] == "normalize_profile_json_string"
    assert chembl_assay_parameters_run_id["include_in_content_hash"] == "false"

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


def test_build_field_matrix_rows_marks_composite_join_keys_and_inherited_fields() -> None:
    rows = build_field_matrix_rows()

    molecule_id = _row(rows, "composite_activity", "molecule_id")
    assert molecule_id["normalization_source"] == "composite_join_key_policy"
    assert molecule_id["normalizer"] == "join_key_policy"

    standard_type = _row(rows, "composite_activity", "standard_type")
    assert standard_type["normalization_source"] == "upstream_inherited"
    assert standard_type["normalizer"] == "none"


def test_build_entity_profile_coverage_kpi_summarizes_entity_rows() -> None:
    kpi = build_entity_profile_coverage_kpi(
        [
            {"pipeline_kind": "entity", "normalization_source": "profile"},
            {"pipeline_kind": "entity", "normalization_source": "profile"},
            {"pipeline_kind": "entity", "normalization_source": "fallback_business"},
            {"pipeline_kind": "composite", "normalization_source": "upstream_inherited"},
        ]
    )

    assert kpi["name"] == "explicit_profile_coverage_pct"
    assert kpi["numerator"] == 2
    assert kpi["denominator"] == 3
    assert kpi["value_pct"] == 66.67


def test_render_markdown_mentions_headline_coverage_kpi() -> None:
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

    assert "## Headline KPI" in markdown
    assert "- explicit_profile_coverage_pct: `50.00%`" in markdown


def test_write_artifacts_is_deterministic(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"

    write_artifacts(first)
    write_artifacts(second)

    assert (first / CSV_NAME).read_text(encoding="utf-8") == (
        second / CSV_NAME
    ).read_text(encoding="utf-8")
    assert (first / MD_NAME).read_text(encoding="utf-8") == (
        second / MD_NAME
    ).read_text(encoding="utf-8")


def test_check_artifacts_detects_drift(tmp_path: Path) -> None:
    out_dir = tmp_path / "matrix"
    payloads = build_artifacts()
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / CSV_NAME).write_text(payloads[CSV_NAME], encoding="utf-8")
    (out_dir / MD_NAME).write_text("drift", encoding="utf-8")

    assert check_artifacts(out_dir) == 1


def test_check_artifacts_returns_zero_for_fresh_outputs(tmp_path: Path) -> None:
    out_dir = tmp_path / "matrix"

    write_artifacts(out_dir)

    assert check_artifacts(out_dir) == 0


def test_committed_artifacts_match_generator_output() -> None:
    assert check_artifacts(DEFAULT_OUT_DIR.resolve()) == 0
