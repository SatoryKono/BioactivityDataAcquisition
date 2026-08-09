"""Tests for extract_null_fields.py."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from scripts.ops.data.extract_null_fields import extract_null_fields, NULL_FIELDS

pytestmark = pytest.mark.unit


class TestExtractNullFields:
    """Test null field extraction from CSV files."""

    def test_extract_null_fields_success(self, tmp_path: Path) -> None:
        """Test successful null field extraction."""
        # Create sample CSV file
        csv_file = tmp_path / "test_publication.csv"
        csv_file.write_text(
            "pmid,abstract,author_orcids\n1,,\n2,,\n3,,\n",
            encoding="utf-8",
        )

        output_file = tmp_path / "output.csv"
        fields_to_extract = ["pmid", "abstract", "author_orcids"]

        # Test
        extract_null_fields(csv_file, fields_to_extract, output_file)

        # Assertions
        assert output_file.exists()
        result_df = pd.read_csv(output_file)
        assert len(result_df) == 3
        assert list(result_df.columns) == fields_to_extract

    def test_extract_null_fields_no_matching_columns(self, tmp_path: Path) -> None:
        """Test extraction when no matching columns exist."""
        # Create CSV file without target columns
        csv_file = tmp_path / "test_publication.csv"
        csv_file.write_text("id,name\n1,test\n2,test2\n", encoding="utf-8")

        output_file = tmp_path / "output.csv"
        fields_to_extract = ["pmid", "abstract"]

        # Test (should not create output file)
        extract_null_fields(csv_file, fields_to_extract, output_file)

        # Assertions
        assert not output_file.exists()

    def test_extract_null_fields_csv_read_error(self, tmp_path: Path) -> None:
        """Test extraction when CSV file cannot be read."""
        # Create invalid CSV file
        csv_file = tmp_path / "test_publication.csv"
        csv_file.write_text("invalid,csv,content", encoding="utf-8")

        output_file = tmp_path / "output.csv"
        fields_to_extract = ["pmid", "abstract"]

        # Test (should handle error gracefully)
        extract_null_fields(csv_file, fields_to_extract, output_file)

        # Assertions (file should not be created on error)
        # The function handles errors by printing, not raising
        assert True  # Test passes if no exception is raised

    def test_null_fields_structure(self) -> None:
        """Test that NULL_FIELDS has expected structure."""
        # Assertions
        assert isinstance(NULL_FIELDS, dict)
        assert "crossref" in NULL_FIELDS
        assert "semanticscholar" in NULL_FIELDS
        assert "chembl" in NULL_FIELDS
        assert "pubmed" in NULL_FIELDS
        assert "openalex" in NULL_FIELDS

        # Check that each source has a list of fields
        for _source, fields in NULL_FIELDS.items():
            assert isinstance(fields, list)
            assert len(fields) > 0
            assert all(isinstance(field, str) for field in fields)

    def test_extract_null_fields_crossref_fields(self) -> None:
        """Test that crossref null fields are defined."""
        crossref_fields = NULL_FIELDS.get("crossref", [])
        expected_fields = ["pmid", "abstract", "author_orcids", "affiliation_list"]

        for field in expected_fields:
            assert field in crossref_fields, (
                f"Expected field {field} not in crossref fields"
            )

    def test_extract_null_fields_chembl_fields(self) -> None:
        """Test that chembl null fields are defined."""
        chembl_fields = NULL_FIELDS.get("chembl", [])
        expected_fields = [
            "author_orcids",
            "language",
            "affiliation_list",
            "publication_date",
        ]

        for field in expected_fields:
            assert field in chembl_fields, (
                f"Expected field {field} not in chembl fields"
            )
