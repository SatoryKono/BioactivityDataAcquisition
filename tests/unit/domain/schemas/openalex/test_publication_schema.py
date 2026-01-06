"""Unit tests for OpenAlex Publication Pandera schema.

Tests the OpenAlexPublicationSchema validation.
"""

from __future__ import annotations

import sys
from datetime import UTC, datetime
from uuid import uuid4

import pandas as pd
import pytest
from pandera.errors import SchemaError

from bioetl.domain.schemas.openalex.publication import OpenAlexPublicationSchema

# Pandera DataFrameModel has issues with Python 3.14+ due to function dispatch bug
# See: https://github.com/unionai-oss/pandera/issues
PANDERA_PYTHON314_SKIP = pytest.mark.skipif(
    sys.version_info >= (3, 14),
    reason="Pandera DataFrameModel has compatibility issues with Python 3.14",
)


@pytest.fixture
def valid_record() -> dict:
    """Create a valid OpenAlex publication record."""
    return {
        "entity_id": "openalex:publication:W2148763428",
        "content_hash": "a" * 64,  # SHA256 hex
        "_run_id": uuid4(),
        "_run_type": "incremental",
        "_source_batch_id": None,
        "_ingestion_ts": datetime.now(UTC),
        "_dq_warn": False,
        "_dq_error": False,
        "_index": 0,
        "openalex_id": "W2148763428",
        "doi": "10.1038/s41586-024-07487-w",
        "title": "Example Publication",
        "abstract": "This is an abstract",
        "year": 2024,
        "publication_date": "2024-05-15",
        "doc_type": "PUBLICATION",
        "journal": "Nature",
        "issn": "0028-0836",
        "publisher": "Springer Nature",
        "is_oa": True,
        "oa_status": "gold",
        "cited_by_count": 42,
        "language": "en",
        "source": "openalex",
        "_lookup_method": "doi",
        "_original_doi": None,
    }


@PANDERA_PYTHON314_SKIP
class TestOpenAlexPublicationSchema:
    """Tests for OpenAlexPublicationSchema validation."""

    def test_valid_record_passes(self, valid_record: dict) -> None:
        """Should validate a correct record."""
        df = pd.DataFrame([valid_record])
        validated = OpenAlexPublicationSchema.validate(df)
        assert len(validated) == 1
        assert validated["openalex_id"].iloc[0] == "W2148763428"

    def test_openalex_id_required(self, valid_record: dict) -> None:
        """Should fail when openalex_id is missing."""
        valid_record["openalex_id"] = None
        df = pd.DataFrame([valid_record])
        with pytest.raises(SchemaError):
            OpenAlexPublicationSchema.validate(df)

    def test_openalex_id_format(self, valid_record: dict) -> None:
        """Should validate openalex_id format (W followed by digits)."""
        # Valid format
        valid_record["openalex_id"] = "W123456789"
        df = pd.DataFrame([valid_record])
        validated = OpenAlexPublicationSchema.validate(df)
        assert validated["openalex_id"].iloc[0] == "W123456789"

        # Invalid format
        valid_record["openalex_id"] = "INVALID123"
        df = pd.DataFrame([valid_record])
        with pytest.raises(SchemaError):
            OpenAlexPublicationSchema.validate(df)

    def test_doi_format_validation(self, valid_record: dict) -> None:
        """Should validate DOI format."""
        # Valid DOI
        valid_record["doi"] = "10.1038/nature12373"
        df = pd.DataFrame([valid_record])
        validated = OpenAlexPublicationSchema.validate(df)
        assert validated["doi"].iloc[0] == "10.1038/nature12373"

        # Invalid DOI (should fail)
        valid_record["doi"] = "not-a-valid-doi"
        df = pd.DataFrame([valid_record])
        with pytest.raises(SchemaError):
            OpenAlexPublicationSchema.validate(df)

    def test_doi_nullable(self, valid_record: dict) -> None:
        """Should allow null DOI."""
        valid_record["doi"] = None
        df = pd.DataFrame([valid_record])
        validated = OpenAlexPublicationSchema.validate(df)
        assert pd.isna(validated["doi"].iloc[0])

    def test_year_range_validation(self, valid_record: dict) -> None:
        """Should validate year range (1800-2100)."""
        # Valid year
        valid_record["year"] = 2024
        df = pd.DataFrame([valid_record])
        validated = OpenAlexPublicationSchema.validate(df)
        assert validated["year"].iloc[0] == 2024

        # Valid boundary values
        for year in [1800, 2100]:
            valid_record["year"] = year
            df = pd.DataFrame([valid_record])
            validated = OpenAlexPublicationSchema.validate(df)
            assert validated["year"].iloc[0] == year

        # Year too low
        valid_record["year"] = 1799
        df = pd.DataFrame([valid_record])
        with pytest.raises(SchemaError):
            OpenAlexPublicationSchema.validate(df)

        # Year too high
        valid_record["year"] = 2101
        df = pd.DataFrame([valid_record])
        with pytest.raises(SchemaError):
            OpenAlexPublicationSchema.validate(df)

    def test_year_nullable(self, valid_record: dict) -> None:
        """Should allow null year."""
        valid_record["year"] = None
        df = pd.DataFrame([valid_record])
        validated = OpenAlexPublicationSchema.validate(df)
        assert pd.isna(validated["year"].iloc[0])

    def test_publication_date_format(self, valid_record: dict) -> None:
        """Should validate publication_date format (YYYY-MM-DD)."""
        # Valid date
        valid_record["publication_date"] = "2024-05-15"
        df = pd.DataFrame([valid_record])
        validated = OpenAlexPublicationSchema.validate(df)
        assert validated["publication_date"].iloc[0] == "2024-05-15"

        # Invalid date format
        valid_record["publication_date"] = "15-05-2024"
        df = pd.DataFrame([valid_record])
        with pytest.raises(SchemaError):
            OpenAlexPublicationSchema.validate(df)

    def test_oa_status_values(self, valid_record: dict) -> None:
        """Should validate oa_status values."""
        valid_statuses = ["gold", "green", "hybrid", "bronze", "closed"]

        for status in valid_statuses:
            valid_record["oa_status"] = status
            df = pd.DataFrame([valid_record])
            validated = OpenAlexPublicationSchema.validate(df)
            assert validated["oa_status"].iloc[0] == status

    def test_oa_status_nullable(self, valid_record: dict) -> None:
        """Should allow null oa_status."""
        valid_record["oa_status"] = None
        df = pd.DataFrame([valid_record])
        validated = OpenAlexPublicationSchema.validate(df)
        assert pd.isna(validated["oa_status"].iloc[0])

    def test_cited_by_count_non_negative(self, valid_record: dict) -> None:
        """Should validate cited_by_count is non-negative."""
        # Valid count
        valid_record["cited_by_count"] = 0
        df = pd.DataFrame([valid_record])
        validated = OpenAlexPublicationSchema.validate(df)
        assert validated["cited_by_count"].iloc[0] == 0

        # Negative count
        valid_record["cited_by_count"] = -1
        df = pd.DataFrame([valid_record])
        with pytest.raises(SchemaError):
            OpenAlexPublicationSchema.validate(df)

    def test_lookup_method_values(self, valid_record: dict) -> None:
        """Should validate _lookup_method values."""
        valid_methods = ["doi", "title_fallback", "title_only", "unknown"]

        for method in valid_methods:
            valid_record["_lookup_method"] = method
            df = pd.DataFrame([valid_record])
            validated = OpenAlexPublicationSchema.validate(df)
            assert validated["_lookup_method"].iloc[0] == method

    def test_lookup_method_required(self, valid_record: dict) -> None:
        """Should require _lookup_method field."""
        valid_record["_lookup_method"] = None
        df = pd.DataFrame([valid_record])
        with pytest.raises(SchemaError):
            OpenAlexPublicationSchema.validate(df)

    def test_source_required(self, valid_record: dict) -> None:
        """Should require source field."""
        valid_record["source"] = None
        df = pd.DataFrame([valid_record])
        with pytest.raises(SchemaError):
            OpenAlexPublicationSchema.validate(df)

    def test_doc_type_required(self, valid_record: dict) -> None:
        """Should require doc_type field."""
        valid_record["doc_type"] = None
        df = pd.DataFrame([valid_record])
        with pytest.raises(SchemaError):
            OpenAlexPublicationSchema.validate(df)

    def test_content_hash_format(self, valid_record: dict) -> None:
        """Should validate content_hash is 64 hex chars."""
        # Valid hash
        valid_record["content_hash"] = "0123456789abcdef" * 4
        df = pd.DataFrame([valid_record])
        validated = OpenAlexPublicationSchema.validate(df)
        assert len(validated["content_hash"].iloc[0]) == 64

        # Invalid hash (too short)
        valid_record["content_hash"] = "abc123"
        df = pd.DataFrame([valid_record])
        with pytest.raises(SchemaError):
            OpenAlexPublicationSchema.validate(df)
