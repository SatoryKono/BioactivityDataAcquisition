"""Tests for PublicationBaseSchema.

Tests the base schema used by all publication entities across providers.
Validates common fields: pmid, doi, pmc_id, title, abstract, authors, journal,
publication_year, publication_date, citations_received, is_oa, lookup_method, source, publication_type, language.
"""

from __future__ import annotations


import pandas as pd
import pandera as pa
import pytest

from bioetl.domain.schemas.common.publication_base import (
    LOOKUP_METHODS,
    PublicationBaseSchema,
)
from tests.helpers.clock import FIXED_TEST_TIME


@pytest.fixture
def valid_base_record() -> dict:
    """Create a valid record with all base publication fields.

    Includes all fields from ETLRecordSchema base class plus
    PublicationBaseSchema specific fields for unified cross-provider analysis.
    """
    return {
        # === ETLRecordSchema fields ===
        "entity_id": "test_pub_001",
        # SHA256 hash must be exactly 64 hex characters
        "content_hash": "a" * 64,
        "_run_id": "run-001",
        "_run_type": "incremental",
        "_source_batch_id": "batch-001",
        "_ingestion_ts": FIXED_TEST_TIME.isoformat(),
        "_dq_warn": False,
        "_dq_error": False,
        "_index": 0,
        # === Cross-reference IDs ===
        "pmid": "12345678",
        "doi": "10.1234/example.test",
        "pmc_id": "PMC1234567",
        # === Core content ===
        "title": "Test Publication Title",
        "abstract": "This is a test abstract for the publication.",
        "authors": '["John Doe", "Jane Smith"]',  # JSON array
        "affiliation_list": '["University of Testing"]',  # JSON array (unified)
        # === Publication metadata ===
        "journal": "Journal of Testing",
        "issn": "0028-0836",
        "issn_list": '["0028-0836"]',
        "publication_year": 2024,
        "publication_date": "2024-06-15",
        "publication_type": "journal-article",
        "publication_type_unified": None,
        "publication_subclass": None,
        "publication_class": None,
        "language": "en",
        # === Pagination (unified field names) ===
        "page_first": "1",
        "page_last": "10",
        # === Metrics (unified field names) ===
        "citations_received": 10,
        "citations_made": 5,
        # === Open Access ===
        "is_oa": True,
        # === Lookup tracking (note: column names use _ prefix) ===
        "_lookup_method": "doi",
        "_original_id": "10.1234/example.test",
        "_source": "test_provider",
    }


@pytest.mark.unit
class TestPublicationBaseSchemaValidation:
    """Test suite for PublicationBaseSchema validation."""

    def test_valid_record_passes_validation(self, valid_base_record: dict) -> None:
        """Valid record with all required fields should pass."""
        df = pd.DataFrame([valid_base_record])

        validated = PublicationBaseSchema.validate(df)

        assert len(validated) == 1
        assert validated["pmid"].iloc[0] == "12345678"
        assert validated["doi"].iloc[0] == "10.1234/example.test"
        assert validated["publication_year"].iloc[0] == 2024

    def test_record_with_nullable_string_fields(self, valid_base_record: dict) -> None:
        """Record with nullable string fields set to None should pass."""
        record = valid_base_record.copy()
        record["pmid"] = None
        record["doi"] = None
        record["pmc_id"] = None
        record["title"] = None
        record["abstract"] = None
        # Note: year is pd.Int64Dtype (nullable integer), keep as valid int

        df = pd.DataFrame([record])

        validated = PublicationBaseSchema.validate(df)

        assert len(validated) == 1
        assert pd.isna(validated["pmid"].iloc[0])
        assert pd.isna(validated["doi"].iloc[0])

    def test_extra_columns_allowed(self, valid_base_record: dict) -> None:
        """Extra columns should be allowed (strict=False)."""
        valid_base_record["extra_field"] = "extra_value"
        valid_base_record["provider_specific"] = 123

        df = pd.DataFrame([valid_base_record])

        validated = PublicationBaseSchema.validate(df)

        assert len(validated) == 1
        assert "extra_field" in validated.columns

    def test_type_coercion(self, valid_base_record: dict) -> None:
        """Values should be coerced to correct types (coerce=True)."""
        record = valid_base_record.copy()
        # Year as string should be coerced to Int64
        record["publication_year"] = "2024"
        # _dq_warn as int should be coerced to bool
        record["_dq_warn"] = 0
        # _dq_error as int should be coerced to bool
        record["_dq_error"] = 0

        df = pd.DataFrame([record])

        validated = PublicationBaseSchema.validate(df)

        assert len(validated) == 1
        assert validated["publication_year"].iloc[0] == 2024
        assert bool(validated["_dq_warn"].iloc[0]) is False
        assert bool(validated["_dq_error"].iloc[0]) is False


@pytest.mark.unit
class TestPublicationBaseSchemaFieldValidation:
    """Tests for individual field validation rules."""

    def test_valid_pmid_formats(self, valid_base_record: dict) -> None:
        """PMID must be numeric string."""
        valid_pmids = ["1", "12345678", "9999999999"]

        for pmid in valid_pmids:
            record = valid_base_record.copy()
            record["pmid"] = pmid
            df = pd.DataFrame([record])
            validated = PublicationBaseSchema.validate(df)
            assert validated["pmid"].iloc[0] == pmid

    def test_invalid_pmid_format_fails(self, valid_base_record: dict) -> None:
        """PMID must be numeric string - non-numeric should fail."""
        invalid_pmids = ["PMID12345", "abc", "12345.67", "12345abc", "10000000000"]

        for pmid in invalid_pmids:
            record = valid_base_record.copy()
            record["pmid"] = pmid
            df = pd.DataFrame([record])

            with pytest.raises(pa.errors.SchemaError):
                PublicationBaseSchema.validate(df)

    def test_valid_doi_formats(self, valid_base_record: dict) -> None:
        """DOI should validate correctly formatted values."""
        valid_dois = [
            "10.1234/test",
            "10.1038/nature12373",
            "10.1000/xyz-abc_123",
            "10.1016/j.cell.2020.01.001",
        ]

        for doi in valid_dois:
            record = valid_base_record.copy()
            record["doi"] = doi
            df = pd.DataFrame([record])
            validated = PublicationBaseSchema.validate(df)
            assert validated["doi"].iloc[0] == doi

    def test_invalid_doi_format_fails(self, valid_base_record: dict) -> None:
        """Invalid DOI formats should fail validation."""
        invalid_dois = [
            "not-a-doi",
            "doi:10.1234/test",  # with prefix
            "https://doi.org/10.1234/test",  # URL format
        ]

        for doi in invalid_dois:
            record = valid_base_record.copy()
            record["doi"] = doi
            df = pd.DataFrame([record])

            with pytest.raises(pa.errors.SchemaError):
                PublicationBaseSchema.validate(df)

    def test_valid_pmc_id_format(self, valid_base_record: dict) -> None:
        """PMC ID must start with 'PMC' followed by digits."""
        valid_pmc_ids = ["PMC1", "PMC1234567", "PMC99999999"]

        for pmc_id in valid_pmc_ids:
            record = valid_base_record.copy()
            record["pmc_id"] = pmc_id
            df = pd.DataFrame([record])
            validated = PublicationBaseSchema.validate(df)
            assert validated["pmc_id"].iloc[0] == pmc_id

    def test_invalid_pmc_id_format_fails(self, valid_base_record: dict) -> None:
        """PMC ID without 'PMC' prefix should fail."""
        invalid_pmc_ids = ["1234567", "pmc1234567", "PMCabc", "abc"]

        for pmc_id in invalid_pmc_ids:
            record = valid_base_record.copy()
            record["pmc_id"] = pmc_id
            df = pd.DataFrame([record])

            with pytest.raises(pa.errors.SchemaError):
                PublicationBaseSchema.validate(df)

    def test_year_range_valid(self, valid_base_record: dict) -> None:
        """Year should be within valid range (1950-CURRENT_YEAR+1)."""
        current_year = FIXED_TEST_TIME.year
        valid_years = [1950, 1990, 2000, 2024, current_year + 1]

        for year in valid_years:
            record = valid_base_record.copy()
            record["publication_year"] = year
            df = pd.DataFrame([record])
            validated = PublicationBaseSchema.validate(df)
            assert validated["publication_year"].iloc[0] == year

    def test_year_below_minimum_fails(self, valid_base_record: dict) -> None:
        """Year below minimum (1500) should fail."""
        record = valid_base_record.copy()
        record["publication_year"] = 1499

        df = pd.DataFrame([record])

        with pytest.raises(pa.errors.SchemaError):
            PublicationBaseSchema.validate(df)

    def test_year_above_maximum_fails(self, valid_base_record: dict) -> None:
        """Year above 2100 should fail."""
        record = valid_base_record.copy()
        record["publication_year"] = 2101

        df = pd.DataFrame([record])

        with pytest.raises(pa.errors.SchemaError):
            PublicationBaseSchema.validate(df)


@pytest.mark.unit
class TestLookupMethods:
    """Tests for LOOKUP_METHODS constant."""

    def test_lookup_methods_contains_expected_values(self) -> None:
        """All expected lookup methods should be defined."""
        expected = {"direct", "doi", "pmid", "title_fallback", "title_only", "unknown"}

        assert set(LOOKUP_METHODS) == expected

    def test_lookup_methods_is_list(self) -> None:
        """LOOKUP_METHODS should be a list for iteration."""
        assert isinstance(LOOKUP_METHODS, list)

    @pytest.mark.parametrize("lookup_method", LOOKUP_METHODS)
    def test_valid_lookup_method_values(self, lookup_method: str) -> None:
        """All defined lookup methods should be non-empty strings."""
        assert isinstance(lookup_method, str)
        assert len(lookup_method) > 0


@pytest.mark.unit
class TestPublicationBaseSchemaConfig:
    """Tests for schema configuration."""

    def test_schema_strict_is_false(self) -> None:
        """Schema should allow extra columns (strict=False)."""
        assert PublicationBaseSchema.Config.strict is False

    def test_schema_coerce_is_true(self) -> None:
        """Schema should coerce types (coerce=True)."""
        assert PublicationBaseSchema.Config.coerce is True

    def test_schema_ordered_is_false(self) -> None:
        """Schema should not enforce column order (ordered=False)."""
        assert PublicationBaseSchema.Config.ordered is False


@pytest.mark.unit
class TestPublicationBaseSchemaMultipleRecords:
    """Tests for validating multiple records."""

    def test_multiple_valid_records(self, valid_base_record: dict) -> None:
        """Multiple valid records should all pass validation."""
        record1 = valid_base_record.copy()
        record2 = valid_base_record.copy()
        record2["entity_id"] = "test_pub_002"
        record2["pmid"] = "87654321"
        record2["doi"] = "10.9999/another.test"
        record2["publication_year"] = 2023

        record3 = valid_base_record.copy()
        record3["entity_id"] = "test_pub_003"
        record3["pmid"] = "11111111"
        record3["doi"] = None
        record3["pmc_id"] = None
        # Note: publication_year is int64 in Pandera schema, must be valid integer
        record3["publication_year"] = 2022

        records = [record1, record2, record3]

        df = pd.DataFrame(records)

        validated = PublicationBaseSchema.validate(df)

        assert len(validated) == 3

    def test_one_invalid_record_fails_batch(self, valid_base_record: dict) -> None:
        """One invalid record in batch should fail validation."""
        record1 = valid_base_record.copy()
        record2 = valid_base_record.copy()
        record2["entity_id"] = "test_pub_002"
        record2["pmid"] = "INVALID"  # Invalid PMID format

        records = [record1, record2]

        df = pd.DataFrame(records)

        with pytest.raises(pa.errors.SchemaError):
            PublicationBaseSchema.validate(df)

    def test_lazy_validation_collects_all_errors(self, valid_base_record: dict) -> None:
        """Lazy validation should collect all errors."""
        record1 = valid_base_record.copy()
        record1["pmid"] = "INVALID1"  # Invalid PMID
        record1["publication_year"] = 1499  # Invalid year

        record2 = valid_base_record.copy()
        record2["entity_id"] = "test_pub_002"
        record2["pmid"] = "INVALID2"  # Invalid PMID
        record2["pmc_id"] = "invalid_pmc"  # Invalid PMC ID

        records = [record1, record2]

        df = pd.DataFrame(records)

        with pytest.raises(pa.errors.SchemaErrors) as exc_info:
            PublicationBaseSchema.validate(df, lazy=True)

        # Should have multiple errors collected
        assert len(exc_info.value.failure_cases) > 1
