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
from tests.helpers.clock import FIXED_TEST_TIME

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
        "_ingestion_ts": FIXED_TEST_TIME.isoformat(),
        "_dq_warn": False,
        "_dq_error": False,
        "_index": 0,
        "openalex_id": "W2148763428",
        # Cross-reference IDs for linking publications across providers
        "doi": "10.1038/s41586-024-07487-w",
        "pmid": "12345678",  # PubMed ID (numeric string)
        "pmc_id": None,  # Excluded from Silver/Gold schemas per design (2026-01)
        # Core content
        "title": "Example Publication",
        "abstract": "This is an abstract",
        "authors": '["John Doe", "Jane Smith"]',  # JSON array (unified format)
        # Publication metadata
        "publication_year": 2024,
        "publication_date": "2024-05-15",
        "publication_type": "article",  # Raw OpenAlex type (unified field name)
        "type_crossref": "journal-article",
        "publication_type_unified": None,
        "publication_subclass": None,
        "publication_class": None,
        "language": "en",
        # Journal info
        "journal": "Nature",
        "issn": "0028-0836",
        "publisher": "Springer Nature",
        # Open Access
        "is_oa": True,
        "oa_status": "gold",
        # Metrics
        "citations_received": 42,  # Unified field name (from OpenAlex cited_by_count)
        # Bibliographic info (from biblio object)
        "volume": "42",
        "issue": "3",
        "page_first": "123",
        "page_last": "145",
        # Additional metrics
        "fwci": 1.5,  # Field-Weighted Citation Impact
        "citations_made": 25,
        # Quality indicators
        "is_retracted": False,
        # Topics (hierarchical classification - replaces deprecated concepts)
        "subject_topics": '[{"id": "T12345", "display_name": "Topic A", "score": 0.95}]',
        "primary_topic": '{"id": "T12345", "display_name": "Topic A", "score": 0.95}',
        # Grants/funding information
        "grants": '[{"funder": "F1234", "funder_display_name": "NIH", "award_id": "R01"}]',
        # Classification (JSON arrays, unified field names)
        "concepts": '["Biology", "Genetics"]',  # Extra column (not in schema, allowed by strict=False)
        "subject_mesh": '["D000123", "D000456"]',
        "subject_keywords": '["gene expression", "transcription"]',
        # External identifier
        "mag_id": "12345678",
        # Author affiliations
        "affiliation_list": '["MIT", "Stanford"]',
        # Author identifiers
        "author_openalex_ids": '["A1234567890", "A9876543210"]',
        # Institution identifiers
        "institution_ids": '["I1234567890", "I9876543210"]',
        "institution_country_codes": '["US", "GB"]',
        # ROR identifiers (may be empty if not returned by Works API)
        "ror_ids": None,
        # Lookup tracking
        "_source": "openalex",
        "_lookup_method": "doi",
        "_original_id": None,
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
        """Should validate publication_year range (1950-CURRENT_YEAR+1)."""
        # Valid year
        valid_record["publication_year"] = 2024
        df = pd.DataFrame([valid_record])
        validated = OpenAlexPublicationSchema.validate(df)
        assert validated["publication_year"].iloc[0] == 2024

        # Valid boundary values
        for year in [1950, 2050]:
            valid_record["publication_year"] = year
            df = pd.DataFrame([valid_record])
            validated = OpenAlexPublicationSchema.validate(df)
            assert validated["publication_year"].iloc[0] == year

        # Year too low
        valid_record["publication_year"] = 1499
        df = pd.DataFrame([valid_record])
        with pytest.raises(SchemaError):
            OpenAlexPublicationSchema.validate(df)

        # Year too high
        valid_record["publication_year"] = 2101
        df = pd.DataFrame([valid_record])
        with pytest.raises(SchemaError):
            OpenAlexPublicationSchema.validate(df)

    def test_year_nullable(self, valid_record: dict) -> None:
        """Should allow null publication_year."""
        valid_record["publication_year"] = None
        df = pd.DataFrame([valid_record])
        validated = OpenAlexPublicationSchema.validate(df)
        assert pd.isna(validated["publication_year"].iloc[0])

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

    def test_citations_received_non_negative(self, valid_record: dict) -> None:
        """Should validate citations_received is non-negative.

        Note: OpenAlex source field is 'cited_by_count', but we use the
        unified field name 'citations_received' for cross-provider consistency.
        """
        # Valid count
        valid_record["citations_received"] = 0
        df = pd.DataFrame([valid_record])
        validated = OpenAlexPublicationSchema.validate(df)
        assert validated["citations_received"].iloc[0] == 0

        # Negative count
        valid_record["citations_received"] = -1
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

    def test_source_field_exists(self, valid_record: dict) -> None:
        """Verify _source field is present in valid records.

        Note: Pandera ignores underscore-prefixed fields, so this test
        only verifies the field is in the data, not validated by schema.
        """
        assert "_source" in valid_record
        assert valid_record["_source"] is not None

    # Note: test_doc_type_required removed - doc_type replaced by 'type' field (2026-01)
    # OpenAlex now uses raw 'type' field instead of unified doc_type

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

    def test_volume_nullable(self, valid_record: dict) -> None:
        """Should allow null volume."""
        valid_record["volume"] = None
        df = pd.DataFrame([valid_record])
        validated = OpenAlexPublicationSchema.validate(df)
        assert pd.isna(validated["volume"].iloc[0])

    def test_issue_nullable(self, valid_record: dict) -> None:
        """Should allow null issue."""
        valid_record["issue"] = None
        df = pd.DataFrame([valid_record])
        validated = OpenAlexPublicationSchema.validate(df)
        assert pd.isna(validated["issue"].iloc[0])

    def test_fwci_non_negative(self, valid_record: dict) -> None:
        """Should validate fwci is non-negative."""
        # Valid fwci
        valid_record["fwci"] = 1.5
        df = pd.DataFrame([valid_record])
        validated = OpenAlexPublicationSchema.validate(df)
        assert validated["fwci"].iloc[0] == pytest.approx(1.5)

        # Zero is valid
        valid_record["fwci"] = 0.0
        df = pd.DataFrame([valid_record])
        validated = OpenAlexPublicationSchema.validate(df)
        assert validated["fwci"].iloc[0] == pytest.approx(0.0)

        # Negative fwci
        valid_record["fwci"] = -1.0
        df = pd.DataFrame([valid_record])
        with pytest.raises(SchemaError):
            OpenAlexPublicationSchema.validate(df)

    def test_fwci_nullable(self, valid_record: dict) -> None:
        """Should allow null fwci."""
        valid_record["fwci"] = None
        df = pd.DataFrame([valid_record])
        validated = OpenAlexPublicationSchema.validate(df)
        assert pd.isna(validated["fwci"].iloc[0])

    def test_citations_made_non_negative(self, valid_record: dict) -> None:
        """Should validate citations_made is non-negative."""
        # Valid count
        valid_record["citations_made"] = 25
        df = pd.DataFrame([valid_record])
        validated = OpenAlexPublicationSchema.validate(df)
        assert validated["citations_made"].iloc[0] == 25

        # Zero is valid
        valid_record["citations_made"] = 0
        df = pd.DataFrame([valid_record])
        validated = OpenAlexPublicationSchema.validate(df)
        assert validated["citations_made"].iloc[0] == 0

        # Negative count
        valid_record["citations_made"] = -1
        df = pd.DataFrame([valid_record])
        with pytest.raises(SchemaError):
            OpenAlexPublicationSchema.validate(df)

    def test_citations_made_nullable(self, valid_record: dict) -> None:
        """Should allow null citations_made."""
        valid_record["citations_made"] = None
        df = pd.DataFrame([valid_record])
        validated = OpenAlexPublicationSchema.validate(df)
        assert pd.isna(validated["citations_made"].iloc[0])

    def test_is_retracted_values(self, valid_record: dict) -> None:
        """Should validate is_retracted boolean values."""
        # False (not retracted)
        valid_record["is_retracted"] = False
        df = pd.DataFrame([valid_record])
        validated = OpenAlexPublicationSchema.validate(df)
        assert bool(validated["is_retracted"].iloc[0]) is False

        # True (retracted)
        valid_record["is_retracted"] = True
        df = pd.DataFrame([valid_record])
        validated = OpenAlexPublicationSchema.validate(df)
        assert bool(validated["is_retracted"].iloc[0]) is True

    def test_subject_topics_nullable(self, valid_record: dict) -> None:
        """Should allow null subject_topics."""
        valid_record["subject_topics"] = None
        df = pd.DataFrame([valid_record])
        validated = OpenAlexPublicationSchema.validate(df)
        assert pd.isna(validated["subject_topics"].iloc[0])

    def test_subject_topics_json_string(self, valid_record: dict) -> None:
        """Should accept subject_topics as JSON-serialized string."""
        topics_json = '[{"id": "T1", "display_name": "Topic 1", "score": 0.9}]'
        valid_record["subject_topics"] = topics_json
        df = pd.DataFrame([valid_record])
        validated = OpenAlexPublicationSchema.validate(df)
        assert validated["subject_topics"].iloc[0] == topics_json

    def test_primary_topic_nullable(self, valid_record: dict) -> None:
        """Should allow null primary_topic."""
        valid_record["primary_topic"] = None
        df = pd.DataFrame([valid_record])
        validated = OpenAlexPublicationSchema.validate(df)
        assert pd.isna(validated["primary_topic"].iloc[0])

    def test_primary_topic_json_string(self, valid_record: dict) -> None:
        """Should accept primary_topic as JSON-serialized string."""
        primary_topic_json = '{"id": "T1", "display_name": "Topic 1", "score": 0.9}'
        valid_record["primary_topic"] = primary_topic_json
        df = pd.DataFrame([valid_record])
        validated = OpenAlexPublicationSchema.validate(df)
        assert validated["primary_topic"].iloc[0] == primary_topic_json

    def test_grants_nullable(self, valid_record: dict) -> None:
        """Should allow null grants."""
        valid_record["grants"] = None
        df = pd.DataFrame([valid_record])
        validated = OpenAlexPublicationSchema.validate(df)
        assert pd.isna(validated["grants"].iloc[0])

    def test_grants_json_string(self, valid_record: dict) -> None:
        """Should accept grants as JSON-serialized string."""
        grants_json = (
            '[{"funder": "F1", "funder_display_name": "NIH", "award_id": "R01"}]'
        )
        valid_record["grants"] = grants_json
        df = pd.DataFrame([valid_record])
        validated = OpenAlexPublicationSchema.validate(df)
        assert validated["grants"].iloc[0] == grants_json

    def test_author_ids_nullable(self, valid_record: dict) -> None:
        """Should allow null author_openalex_ids."""
        valid_record["author_openalex_ids"] = None
        df = pd.DataFrame([valid_record])
        validated = OpenAlexPublicationSchema.validate(df)
        assert pd.isna(validated["author_openalex_ids"].iloc[0])

    def test_author_ids_json_string(self, valid_record: dict) -> None:
        """Should accept author_openalex_ids as JSON-serialized string."""
        ids_json = '["A1234567890", "A9876543210"]'
        valid_record["author_openalex_ids"] = ids_json
        df = pd.DataFrame([valid_record])
        validated = OpenAlexPublicationSchema.validate(df)
        assert validated["author_openalex_ids"].iloc[0] == ids_json

    def test_institution_ids_nullable(self, valid_record: dict) -> None:
        """Should allow null institution_ids."""
        valid_record["institution_ids"] = None
        df = pd.DataFrame([valid_record])
        validated = OpenAlexPublicationSchema.validate(df)
        assert pd.isna(validated["institution_ids"].iloc[0])

    def test_institution_ids_json_string(self, valid_record: dict) -> None:
        """Should accept institution_ids as JSON-serialized string."""
        ids_json = '["I1234567890", "I9876543210"]'
        valid_record["institution_ids"] = ids_json
        df = pd.DataFrame([valid_record])
        validated = OpenAlexPublicationSchema.validate(df)
        assert validated["institution_ids"].iloc[0] == ids_json

    def test_institution_country_codes_nullable(self, valid_record: dict) -> None:
        """Should allow null institution_country_codes."""
        valid_record["institution_country_codes"] = None
        df = pd.DataFrame([valid_record])
        validated = OpenAlexPublicationSchema.validate(df)
        assert pd.isna(validated["institution_country_codes"].iloc[0])

    def test_institution_country_codes_json_string(self, valid_record: dict) -> None:
        """Should accept institution_country_codes as JSON-serialized string."""
        codes_json = '["US", "GB", "DE"]'
        valid_record["institution_country_codes"] = codes_json
        df = pd.DataFrame([valid_record])
        validated = OpenAlexPublicationSchema.validate(df)
        assert validated["institution_country_codes"].iloc[0] == codes_json
