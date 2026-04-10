"""Tests for code-derived pipeline normalization field-matrix generation."""

from __future__ import annotations

from pathlib import Path

from scripts.docs.generate_pipeline_normalization_field_matrix import (
    CSV_NAME,
    MD_NAME,
    build_artifacts,
    build_field_matrix_rows,
    check_artifacts,
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
    assert crossref_title["normalization_source"] == "fallback"
    assert crossref_title["normalizer"] == "normalize_title"

    pubmed_date = _row(rows, "pubmed_publication", "publication_date")
    assert pubmed_date["normalization_source"] == "fallback"
    assert pubmed_date["normalizer"] == "normalize_partial_date"

    pubchem_smiles = _row(rows, "pubchem_compound", "canonical_smiles")
    assert pubchem_smiles["normalization_source"] == "fallback"
    assert pubchem_smiles["normalizer"] == "SMILES.from_raw(mode=soft)"


def test_build_field_matrix_rows_marks_composite_join_keys_and_inherited_fields() -> None:
    rows = build_field_matrix_rows()

    molecule_id = _row(rows, "composite_activity", "molecule_id")
    assert molecule_id["normalization_source"] == "composite_join_key_policy"
    assert molecule_id["normalizer"] == "join_key_policy"

    standard_type = _row(rows, "composite_activity", "standard_type")
    assert standard_type["normalization_source"] == "upstream_inherited"
    assert standard_type["normalizer"] == "none"


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
