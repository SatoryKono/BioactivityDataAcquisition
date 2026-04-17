"""Tests for code-derived ChemBL Activity field-matrix generation."""

from __future__ import annotations

import csv
import io
from pathlib import Path

from bioetl.domain.normalization.profiles import (
    CHEMBL_ACTIVITY_PROFILE,
    CHEMBL_ACTIVITY_SCHEMA_FIELDS,
)
from bioetl.infrastructure.schemas.silver_chembl_core import CHEMBL_ACTIVITY_SCHEMA
from scripts.docs.generate_chembl_activity_field_matrix import (
    CSV_COLUMNS,
    CSV_NAME,
    MD_NAME,
    build_artifacts,
    build_field_matrix_rows,
    check_artifacts,
    render_csv,
    write_artifacts,
)


def test_build_field_matrix_rows_covers_schema_and_hash_policy() -> None:
    rows = build_field_matrix_rows()

    assert [row["field_name"] for row in rows] == sorted(CHEMBL_ACTIVITY_SCHEMA_FIELDS)
    assert {row["field_name"] for row in rows} == set(CHEMBL_ACTIVITY_SCHEMA_FIELDS)
    activity_properties = next(
        row for row in rows if row["field_name"] == "activity_properties"
    )
    entity_id = next(row for row in rows if row["field_name"] == "entity_id")
    assert activity_properties["set_like"] == "true"
    assert activity_properties["include_in_content_hash"] == (
        "true"
        if "activity_properties" in CHEMBL_ACTIVITY_PROFILE.hash_included_fields
        else "false"
    )
    assert entity_id["include_in_content_hash"] == "false"
    assert activity_properties["set_like"] == "true"
    assert activity_properties["type"] == "string"
    assert (
        activity_properties["current_normalization"]
        == "normalizer=_normalize_json_string; content_hash=included; hash_order=set_like"
    )
    assert (
        activity_properties["proposed_normalization"]
        == activity_properties["current_normalization"]
    )
    publication_year = next(
        row for row in rows if row["field_name"] == "publication_year"
    )
    assert publication_year["type"] == str(
        CHEMBL_ACTIVITY_SCHEMA.field("publication_year").type
    )


def test_render_csv_uses_contract_column_order() -> None:
    rows = build_field_matrix_rows()

    rendered = render_csv(rows)
    parsed = csv.DictReader(io.StringIO(rendered))

    assert parsed.fieldnames == list(CSV_COLUMNS)


def test_write_artifacts_is_deterministic(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"

    write_artifacts(first, with_docx=False, with_pdf=False)
    write_artifacts(second, with_docx=False, with_pdf=False)

    assert (first / CSV_NAME).read_text(encoding="utf-8") == (
        second / CSV_NAME
    ).read_text(encoding="utf-8")
    assert (first / MD_NAME).read_text(encoding="utf-8") == (
        second / MD_NAME
    ).read_text(encoding="utf-8")


def test_build_artifacts_is_byte_for_byte_stable_across_repeated_calls() -> None:
    first = build_artifacts()
    second = build_artifacts()

    assert first[CSV_NAME].encode("utf-8") == second[CSV_NAME].encode("utf-8")
    assert first[MD_NAME].encode("utf-8") == second[MD_NAME].encode("utf-8")


def test_check_artifacts_detects_drift(tmp_path: Path) -> None:
    out_dir = tmp_path / "matrix"
    payloads = build_artifacts()
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / CSV_NAME).write_text(payloads[CSV_NAME], encoding="utf-8")
    (out_dir / MD_NAME).write_text("drift", encoding="utf-8")

    assert check_artifacts(out_dir) == 1


def test_check_artifacts_returns_zero_for_fresh_outputs(tmp_path: Path) -> None:
    out_dir = tmp_path / "matrix"

    write_artifacts(out_dir, with_docx=False, with_pdf=False)

    assert check_artifacts(out_dir) == 0


def test_write_artifacts_preserves_csv_and_md_when_optional_exports_requested(
    tmp_path: Path,
) -> None:
    out_dir = tmp_path / "matrix"

    result = write_artifacts(out_dir, with_docx=True, with_pdf=True)

    assert (out_dir / CSV_NAME).exists()
    assert (out_dir / MD_NAME).exists()
    assert isinstance(result["warnings"], list)


def test_write_artifacts_produces_byte_identical_csv_on_repeated_generation(
    tmp_path: Path,
) -> None:
    out_dir = tmp_path / "matrix"

    write_artifacts(out_dir, with_docx=False, with_pdf=False)
    first_csv = (out_dir / CSV_NAME).read_bytes()

    write_artifacts(out_dir, with_docx=False, with_pdf=False)
    second_csv = (out_dir / CSV_NAME).read_bytes()

    assert first_csv == second_csv
