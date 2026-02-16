"""Tests for AuthorNormalizationService.

Tests unified author and affiliation normalization across providers.
"""

from __future__ import annotations

import json

import pytest

from bioetl.domain.services._author_helpers import (
    deduplicate_case_insensitive,
    hash_author_name,
    normalize_affiliation_string,
)
from bioetl.domain.services.author_normalization_service import (
    AuthorNormalizationService,
)


class TestNormalizeAuthorList:
    """Tests for normalize_author_list method."""

    @pytest.fixture
    def service(self) -> AuthorNormalizationService:
        """Create service instance."""
        return AuthorNormalizationService()

    def test_list_of_strings(self, service: AuthorNormalizationService) -> None:
        """Test normalization with list of author name strings."""
        authors = ["John Doe", "Jane Smith"]
        result = service.normalize_author_list(authors, salt="test_salt")

        assert result is not None
        parsed = json.loads(result)
        assert isinstance(parsed, list)
        assert len(parsed) == 2
        assert all(isinstance(h, str) for h in parsed)
        assert all(len(h) == 64 for h in parsed)  # SHA-256 hex digest

    def test_list_of_dicts_with_name(self, service: AuthorNormalizationService) -> None:
        """Test normalization with list of author dicts (PubMed/CrossRef format)."""
        authors = [
            {"name": "John Doe", "orcid": "0000-0001-2345-6789"},
            {"name": "Jane Smith", "affiliation": ["MIT"]},
        ]
        result = service.normalize_author_list(authors, salt="test_salt")

        assert result is not None
        parsed = json.loads(result)
        assert len(parsed) == 2

    def test_semicolon_delimited_string(
        self, service: AuthorNormalizationService
    ) -> None:
        """Test normalization with semicolon-delimited string (ChEMBL format)."""
        authors = "John Doe; Jane Smith; Bob Johnson"
        result = service.normalize_author_list(authors, salt="test_salt")

        assert result is not None
        parsed = json.loads(result)
        assert len(parsed) == 3

    def test_comma_delimited_string(self, service: AuthorNormalizationService) -> None:
        """Test normalization with comma-delimited string."""
        authors = "John Doe, Jane Smith, Bob Johnson"
        result = service.normalize_author_list(authors, salt="test_salt")

        assert result is not None
        parsed = json.loads(result)
        assert len(parsed) == 3

    def test_json_string_of_names(self, service: AuthorNormalizationService) -> None:
        """Test normalization with JSON array string."""
        authors = '["John Doe", "Jane Smith"]'
        result = service.normalize_author_list(authors, salt="test_salt")

        assert result is not None
        parsed = json.loads(result)
        assert len(parsed) == 2

    def test_json_string_of_dicts(self, service: AuthorNormalizationService) -> None:
        """Test normalization with JSON array of dicts."""
        authors = '[{"name": "John Doe"}, {"name": "Jane Smith"}]'
        result = service.normalize_author_list(authors, salt="test_salt")

        assert result is not None
        parsed = json.loads(result)
        assert len(parsed) == 2

    def test_empty_inputs_return_none(
        self, service: AuthorNormalizationService
    ) -> None:
        """Test that empty inputs return None."""
        assert service.normalize_author_list(None, salt="test") is None
        assert service.normalize_author_list([], salt="test") is None
        assert service.normalize_author_list("", salt="test") is None
        assert service.normalize_author_list("   ", salt="test") is None

    def test_whitespace_normalization(
        self, service: AuthorNormalizationService
    ) -> None:
        """Test that whitespace is normalized in author names."""
        authors = ["  John Doe  ", "Jane Smith"]
        result = service.normalize_author_list(authors, salt="test_salt")

        assert result is not None
        # Should produce same hash as without extra whitespace
        expected = service.normalize_author_list(
            ["John Doe", "Jane Smith"], salt="test_salt"
        )
        assert result == expected

    def test_case_insensitive_hashing(
        self, service: AuthorNormalizationService
    ) -> None:
        """Test that hashing is case-insensitive per RULES.md §5.4."""
        result_lower = service.normalize_author_list(["john doe"], salt="test")
        result_upper = service.normalize_author_list(["JOHN DOE"], salt="test")
        result_mixed = service.normalize_author_list(["John Doe"], salt="test")

        assert result_lower == result_upper == result_mixed

    def test_different_salt_different_hash(
        self, service: AuthorNormalizationService
    ) -> None:
        """Test that different salt produces different hashes."""
        authors = ["John Doe"]
        result1 = service.normalize_author_list(authors, salt="salt1")
        result2 = service.normalize_author_list(authors, salt="salt2")

        assert result1 != result2


class TestNormalizeAffiliations:
    """Tests for normalize_affiliations method."""

    @pytest.fixture
    def service(self) -> AuthorNormalizationService:
        """Create service instance."""
        return AuthorNormalizationService()

    def test_list_of_strings(self, service: AuthorNormalizationService) -> None:
        """Test normalization with list of affiliation strings."""
        affiliations = ["MIT", "Harvard University", "Stanford"]
        result = service.normalize_affiliations(affiliations)

        assert result is not None
        parsed = json.loads(result)
        assert len(parsed) == 3
        assert sorted(parsed) == parsed  # Should be sorted

    def test_case_insensitive_deduplication(
        self, service: AuthorNormalizationService
    ) -> None:
        """Test that affiliations are deduplicated case-insensitively."""
        affiliations = ["MIT", "mit", "Harvard", "HARVARD", "Stanford"]
        result = service.normalize_affiliations(affiliations)

        assert result is not None
        parsed = json.loads(result)
        # Should have 3 unique (case-insensitive): MIT, Harvard, Stanford
        assert len(parsed) == 3
        # Original case should be preserved (first occurrence)
        assert "MIT" in parsed
        assert "Harvard" in parsed
        assert "Stanford" in parsed

    def test_whitespace_normalization(
        self, service: AuthorNormalizationService
    ) -> None:
        """Test that whitespace is normalized in affiliations."""
        affiliations = ["  MIT  ", "MIT", "  MIT"]
        result = service.normalize_affiliations(affiliations)

        assert result is not None
        parsed = json.loads(result)
        # Should deduplicate to single "MIT"
        assert len(parsed) == 1
        assert parsed[0] == "MIT"

    def test_html_cleanup(self, service: AuthorNormalizationService) -> None:
        """Test that HTML tags are removed from affiliations."""
        affiliations = ["<b>MIT</b>", "Harvard &amp; MIT"]
        result = service.normalize_affiliations(affiliations)

        assert result is not None
        parsed = json.loads(result)
        assert "MIT" in parsed
        assert "Harvard & MIT" in parsed

    def test_list_of_dicts_with_name_key(
        self, service: AuthorNormalizationService
    ) -> None:
        """Test normalization with dicts containing 'name' key (CrossRef format)."""
        affiliations = [{"name": "MIT"}, {"name": "Harvard"}]
        result = service.normalize_affiliations(affiliations)

        assert result is not None
        parsed = json.loads(result)
        assert len(parsed) == 2
        assert "MIT" in parsed
        assert "Harvard" in parsed

    def test_list_of_dicts_with_display_name_key(
        self, service: AuthorNormalizationService
    ) -> None:
        """Test normalization with dicts containing 'display_name' key (OpenAlex)."""
        affiliations = [
            {"display_name": "MIT", "id": "I1234"},
            {"display_name": "Harvard", "id": "I5678"},
        ]
        result = service.normalize_affiliations(affiliations)

        assert result is not None
        parsed = json.loads(result)
        assert len(parsed) == 2

    def test_empty_inputs_return_none(
        self, service: AuthorNormalizationService
    ) -> None:
        """Test that empty inputs return None."""
        assert service.normalize_affiliations(None) is None
        assert service.normalize_affiliations([]) is None

    def test_sorted_output(self, service: AuthorNormalizationService) -> None:
        """Test that output is sorted alphabetically."""
        affiliations = ["Stanford", "MIT", "Harvard", "Berkeley"]
        result = service.normalize_affiliations(affiliations)

        assert result is not None
        parsed = json.loads(result)
        assert parsed == ["Berkeley", "Harvard", "MIT", "Stanford"]


class TestExtractAffiliationsFromAuthors:
    """Tests for extract_affiliations_from_authors method."""

    @pytest.fixture
    def service(self) -> AuthorNormalizationService:
        """Create service instance."""
        return AuthorNormalizationService()

    def test_extract_from_author_dicts(
        self, service: AuthorNormalizationService
    ) -> None:
        """Test extraction from author dicts with affiliations."""
        authors = [
            {"name": "John Doe", "affiliations": ["MIT", "Harvard"]},
            {"name": "Jane Smith", "affiliations": ["Stanford"]},
        ]
        result = service.extract_affiliations_from_authors(authors)

        assert len(result) == 3
        assert sorted(result) == ["Harvard", "MIT", "Stanford"]

    def test_deduplication_across_authors(
        self, service: AuthorNormalizationService
    ) -> None:
        """Test that affiliations are deduplicated across authors."""
        authors = [
            {"name": "John Doe", "affiliations": ["MIT", "Harvard"]},
            {"name": "Jane Smith", "affiliations": ["MIT", "Stanford"]},
            {"name": "Bob Johnson", "affiliations": ["Harvard"]},
        ]
        result = service.extract_affiliations_from_authors(authors)

        # Should have 3 unique: MIT, Harvard, Stanford
        assert len(result) == 3
        assert set(result) == {"MIT", "Harvard", "Stanford"}

    def test_empty_affiliations(self, service: AuthorNormalizationService) -> None:
        """Test handling of authors without affiliations."""
        authors = [
            {"name": "John Doe", "affiliations": []},
            {"name": "Jane Smith"},  # No affiliations key
        ]
        result = service.extract_affiliations_from_authors(authors)

        assert result == []

    def test_single_affiliation_string(
        self, service: AuthorNormalizationService
    ) -> None:
        """Test handling of single affiliation as string (not list)."""
        authors = [
            {"name": "John Doe", "affiliations": "MIT"},
        ]
        result = service.extract_affiliations_from_authors(authors)

        assert len(result) == 1
        assert result[0] == "MIT"


class TestPrivateMethods:
    """Tests for private helper methods (for coverage)."""

    @pytest.fixture
    def service(self) -> AuthorNormalizationService:
        """Create service instance."""
        return AuthorNormalizationService()

    def test_hash_author_name_consistency(
        self, service: AuthorNormalizationService
    ) -> None:
        """Test that hashing is consistent."""
        hash1 = service._hash_author_name("John Doe", "salt")
        hash2 = service._hash_author_name("John Doe", "salt")

        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 hex digest

    def test_normalize_affiliation_string_pipeline(
        self, service: AuthorNormalizationService
    ) -> None:
        """Test affiliation string normalization pipeline."""
        # HTML + whitespace + unicode
        text = "<b>MIT</b>  &amp;  Harvard  "
        result = service._normalize_affiliation_string(text)

        assert result == "MIT & Harvard"

    def test_deduplicate_case_insensitive_preserves_first(
        self, service: AuthorNormalizationService
    ) -> None:
        """Test that deduplication preserves first occurrence case."""
        strings = ["MIT", "mit", "Harvard", "HARVARD"]
        result = service._deduplicate_case_insensitive(strings)

        assert "MIT" in result  # First occurrence preserved
        assert "mit" not in result
        assert "Harvard" in result
        assert "HARVARD" not in result
