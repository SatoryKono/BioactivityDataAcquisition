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
from tests.helpers import (
    assert_build_artifacts_are_stable,
    assert_check_artifacts_detects_drift,
    assert_check_artifacts_passes_for_fresh_outputs,
    assert_repeated_core_output_bytes_are_stable,
    assert_written_core_artifacts_are_deterministic,
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
    assert_written_core_artifacts_are_deterministic(
        tmp_path,
        write_artifacts=write_artifacts,
        csv_name=CSV_NAME,
        md_name=MD_NAME,
        write_kwargs={"with_docx": False, "with_pdf": False},
    )


def test_build_artifacts_is_byte_for_byte_stable_across_repeated_calls() -> None:
    assert_build_artifacts_are_stable(
        build_artifacts=build_artifacts,
        artifact_names=(CSV_NAME, MD_NAME),
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
        write_kwargs={"with_docx": False, "with_pdf": False},
    )


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
    assert_repeated_core_output_bytes_are_stable(
        tmp_path,
        write_artifacts=write_artifacts,
        artifact_name=CSV_NAME,
        write_kwargs={"with_docx": False, "with_pdf": False},
    )
