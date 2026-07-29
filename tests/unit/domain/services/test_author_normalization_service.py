# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD6 residual test mock/fixture surface — product NewTypes/Ports stay strict (#7048).
"""Tests for AuthorNormalizer.

Tests unified author and affiliation normalization across providers.
"""

from __future__ import annotations

import json

import pytest

from bioetl.domain.behavior._author_helpers import (
    deduplicate_case_insensitive,
    hash_author_name,
    normalize_affiliation_string,
    normalize_to_surname_initial,
)
from bioetl.domain.behavior.author_normalization_service import (
    AuthorNormalizer,
)

pytestmark = pytest.mark.unit


class TestNormalizeAuthorList:
    """Tests for normalize_author_list method."""

    @pytest.fixture
    def service(self) -> AuthorNormalizer:
        """Create service instance."""
        return AuthorNormalizer()

    def test_list_of_strings(self, service: AuthorNormalizer) -> None:
        """Test normalization with list of author name strings."""
        authors = ["John Doe", "Jane Smith"]
        result = service.normalize_author_list(authors)

        assert result is not None
        parsed = json.loads(result)
        assert isinstance(parsed, list)
        assert len(parsed) == 2
        assert parsed == ["John Doe", "Jane Smith"]

    def test_list_of_dicts_with_name(self, service: AuthorNormalizer) -> None:
        """Test normalization with list of author dicts (PubMed/CrossRef format)."""
        authors = [
            {"name": "John Doe", "orcid": "0000-0001-2345-6789"},
            {"name": "Jane Smith", "affiliation": ["MIT"]},
        ]
        result = service.normalize_author_list(authors)

        assert result is not None
        parsed = json.loads(result)
        assert len(parsed) == 2
        assert parsed == ["John Doe", "Jane Smith"]

    def test_semicolon_delimited_string(self, service: AuthorNormalizer) -> None:
        """Test normalization with semicolon-delimited string (ChEMBL format)."""
        authors = "John Doe; Jane Smith; Bob Johnson"
        result = service.normalize_author_list(authors)

        assert result is not None
        parsed = json.loads(result)
        assert len(parsed) == 3
        assert parsed == ["John Doe", "Jane Smith", "Bob Johnson"]

    def test_comma_delimited_string(self, service: AuthorNormalizer) -> None:
        """Test normalization with comma-delimited string."""
        authors = "John Doe, Jane Smith, Bob Johnson"
        result = service.normalize_author_list(authors)

        assert result is not None
        parsed = json.loads(result)
        assert len(parsed) == 3
        assert parsed == ["John Doe", "Jane Smith", "Bob Johnson"]

    def test_json_string_of_names(self, service: AuthorNormalizer) -> None:
        """Test normalization with JSON array string."""
        authors = '["John Doe", "Jane Smith"]'
        result = service.normalize_author_list(authors)

        assert result is not None
        parsed = json.loads(result)
        assert len(parsed) == 2
        assert parsed == ["John Doe", "Jane Smith"]

    def test_json_string_of_dicts(self, service: AuthorNormalizer) -> None:
        """Test normalization with JSON array of dicts."""
        authors = '[{"name": "John Doe"}, {"name": "Jane Smith"}]'
        result = service.normalize_author_list(authors)

        assert result is not None
        parsed = json.loads(result)
        assert len(parsed) == 2
        assert parsed == ["John Doe", "Jane Smith"]

    def test_empty_inputs_return_none(self, service: AuthorNormalizer) -> None:
        """Test that empty inputs return None."""
        assert service.normalize_author_list(None) is None
        assert service.normalize_author_list([]) is None
        assert service.normalize_author_list("") is None
        assert service.normalize_author_list("   ") is None

    def test_whitespace_normalization(self, service: AuthorNormalizer) -> None:
        """Test that whitespace is normalized in author names."""
        authors = ["  John Doe  ", "Jane Smith"]
        result = service.normalize_author_list(authors)

        assert result is not None
        # Should produce same result as without extra whitespace
        expected = service.normalize_author_list(["John Doe", "Jane Smith"])
        assert result == expected

    def test_case_preserved_in_output(self, service: AuthorNormalizer) -> None:
        """Test that case is preserved in normalized output."""
        result = service.normalize_author_list(["John Doe"])

        assert result is not None
        parsed = json.loads(result)
        assert parsed == ["John Doe"]

    def test_deterministic_output(self, service: AuthorNormalizer) -> None:
        """Test that normalization is deterministic."""
        authors = ["John Doe"]
        result1 = service.normalize_author_list(authors)
        result2 = service.normalize_author_list(authors)

        assert result1 == result2


class TestNormalizeAffiliations:
    """Tests for normalize_affiliations method."""

    @pytest.fixture
    def service(self) -> AuthorNormalizer:
        """Create service instance."""
        return AuthorNormalizer()

    def test_normalize_affiliations__list_of_strings__966db24c(
        self, service: AuthorNormalizer
    ) -> None:
        """Test normalization with list of affiliation strings."""
        affiliations = ["MIT", "Harvard University", "Stanford"]
        result = service.normalize_affiliations(affiliations)

        assert result is not None
        parsed = json.loads(result)
        assert len(parsed) == 3
        assert sorted(parsed) == parsed  # Should be sorted

    def test_case_insensitive_deduplication(self, service: AuthorNormalizer) -> None:
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

    def test_normalize_affiliations__normalization__760741bb(
        self, service: AuthorNormalizer
    ) -> None:
        """Test that whitespace is normalized in affiliations."""
        affiliations = ["  MIT  ", "MIT", "  MIT"]
        result = service.normalize_affiliations(affiliations)

        assert result is not None
        parsed = json.loads(result)
        # Should deduplicate to single "MIT"
        assert len(parsed) == 1
        assert parsed[0] == "MIT"

    def test_html_cleanup(self, service: AuthorNormalizer) -> None:
        """Test that HTML tags are removed from affiliations."""
        affiliations = ["<b>MIT</b>", "Harvard &amp; MIT"]
        result = service.normalize_affiliations(affiliations)

        assert result is not None
        parsed = json.loads(result)
        assert "MIT" in parsed
        assert "Harvard & MIT" in parsed

    def test_list_of_dicts_with_name_key(self, service: AuthorNormalizer) -> None:
        """Test normalization with dicts containing 'name' key (CrossRef format)."""
        affiliations = [{"name": "MIT"}, {"name": "Harvard"}]
        result = service.normalize_affiliations(affiliations)

        assert result is not None
        parsed = json.loads(result)
        assert len(parsed) == 2
        assert "MIT" in parsed
        assert "Harvard" in parsed

    def test_list_of_dicts_with_display_name_key(
        self, service: AuthorNormalizer
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

    def test_normalize_affiliations__inputs_return_none__616cfda3(
        self, service: AuthorNormalizer
    ) -> None:
        """Test that empty inputs return None."""
        assert service.normalize_affiliations(None) is None
        assert service.normalize_affiliations([]) is None

    def test_sorted_output(self, service: AuthorNormalizer) -> None:
        """Test that output is sorted alphabetically."""
        affiliations = ["Stanford", "MIT", "Harvard", "Berkeley"]
        result = service.normalize_affiliations(affiliations)

        assert result is not None
        parsed = json.loads(result)
        assert parsed == ["Berkeley", "Harvard", "MIT", "Stanford"]


class TestExtractAffiliationsFromAuthors:
    """Tests for extract_affiliations_from_authors method."""

    @pytest.fixture
    def service(self) -> AuthorNormalizer:
        """Create service instance."""
        return AuthorNormalizer()

    def test_extract_from_author_dicts(self, service: AuthorNormalizer) -> None:
        """Test extraction from author dicts with affiliations."""
        authors = [
            {"name": "John Doe", "affiliations": ["MIT", "Harvard"]},
            {"name": "Jane Smith", "affiliations": ["Stanford"]},
        ]
        result = service.extract_affiliations_from_authors(authors)

        assert len(result) == 3
        assert sorted(result) == ["Harvard", "MIT", "Stanford"]

    def test_deduplication_across_authors(self, service: AuthorNormalizer) -> None:
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

    def test_empty_affiliations(self, service: AuthorNormalizer) -> None:
        """Test handling of authors without affiliations."""
        authors = [
            {"name": "John Doe", "affiliations": []},
            {"name": "Jane Smith"},  # No affiliations key
        ]
        result = service.extract_affiliations_from_authors(authors)

        assert result == []

    def test_single_affiliation_string(self, service: AuthorNormalizer) -> None:
        """Test handling of single affiliation as string (not list)."""
        authors = [
            {"name": "John Doe", "affiliations": "MIT"},
        ]
        result = service.extract_affiliations_from_authors(authors)

        assert len(result) == 1
        assert result[0] == "MIT"


class TestHelperFunctions:
    """Tests for helper functions in _author_helpers module."""

    def test_hash_author_name_consistency(self) -> None:
        """Test that hashing is consistent."""
        hash1 = hash_author_name("John Doe", "salt")
        hash2 = hash_author_name("John Doe", "salt")

        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 hex digest

    def test_normalize_affiliation_string_pipeline(self) -> None:
        """Test affiliation string normalization pipeline."""
        # HTML + whitespace + unicode
        text = "<b>MIT</b>  &amp;  Harvard  "
        result = normalize_affiliation_string(text)

        assert result == "MIT & Harvard"

    def test_deduplicate_case_insensitive_preserves_first(self) -> None:
        """Test that deduplication preserves first occurrence case."""
        strings = ["MIT", "mit", "Harvard", "HARVARD"]
        result = deduplicate_case_insensitive(strings)

        assert "MIT" in result  # First occurrence preserved
        assert "mit" not in result
        assert "Harvard" in result
        assert "HARVARD" not in result


class TestNormalizeToSurnameInitial:
    """Tests for normalize_to_surname_initial helper."""

    @pytest.mark.parametrize(
        ("name", "expected"),
        [
            # Standard FirstName LastName (CrossRef, OpenAlex, S2)
            ("John Doe", "Doe_J"),
            ("Jane Smith", "Smith_J"),
            ("Yanyong Kang", "Kang_Y"),
            # FirstName Middle LastName
            ("John A. Doe", "Doe_J"),
            ("John Allen Doe", "Doe_J"),
            # LastName, FirstName (PubMed inverted)
            ("Doe, John", "Doe_J"),
            ("Smith, Jane", "Smith_J"),
            # LastName, Initial (PubMed)
            ("Doe, J", "Doe_J"),
            ("Smith, A", "Smith_A"),
            # LastName, Initials (PubMed)
            ("Doe, JA", "Doe_J"),
            ("Smith, AB", "Smith_A"),
            # LastName Initials (ChEMBL)
            ("Smith J", "Smith_J"),
            ("Smith JA", "Smith_J"),
            ("Zhou X", "Zhou_X"),
            # Initial. LastName
            ("X. Zhou", "Zhou_X"),
            ("J. Doe", "Doe_J"),
            # Multi-word surname with comma
            ("Van der Berg, Jan", "Van der Berg_J"),
            # Single name (organization or mononym)
            ("Madonna", "Madonna"),
            ("WHO", "WHO"),
            # Organization-like multi-word (no initials detected)
            ("World Health Organization", "Organization_W"),
        ],
        ids=[
            "first_last",
            "first_last_2",
            "east_asian",
            "first_middle_last",
            "first_middle_last_full",
            "last_comma_first",
            "last_comma_first_2",
            "last_comma_initial",
            "last_comma_initial_2",
            "last_comma_initials",
            "last_comma_initials_2",
            "chembl_single_initial",
            "chembl_double_initials",
            "chembl_single_letter",
            "initial_dot_last",
            "initial_dot_last_2",
            "multi_word_surname",
            "mononym",
            "acronym",
            "org_multi_word",
        ],
    )
    def test_name_formats(self, name: str, expected: str) -> None:
        """Test various name format conversions."""
        assert normalize_to_surname_initial(name) == expected

    @pytest.mark.parametrize(
        "name",
        [None, "", "   "],
        ids=["none", "empty", "whitespace"],
    )
    def test_empty_returns_none(self, name: str | None) -> None:
        """Test that empty/None inputs return None."""
        assert normalize_to_surname_initial(name) is None  # type: ignore[arg-type]

    def test_leading_trailing_whitespace_stripped(self) -> None:
        """Test that whitespace around name is stripped."""
        assert normalize_to_surname_initial("  John Doe  ") == "Doe_J"

    def test_comma_only_surname(self) -> None:
        """Test surname with comma but no first name."""
        assert normalize_to_surname_initial("Doe,") == "Doe"


class TestNormalizeAuthorKeys:
    """Tests for normalize_author_keys method on AuthorNormalizer."""

    @pytest.fixture
    def service(self) -> AuthorNormalizer:
        return AuthorNormalizer()

    def test_normalize_author_keys__list_of_strings__f8d8e84c(
        self, service: AuthorNormalizer
    ) -> None:
        """Test pipe-delimited output from list of name strings."""
        result = service.normalize_author_keys(["John Doe", "Jane Smith"])
        assert result == "Doe_J|Smith_J"

    def test_list_of_dicts(self, service: AuthorNormalizer) -> None:
        """Test with list of author dicts (name key)."""
        authors = [{"name": "John Doe"}, {"name": "Jane Smith"}]
        result = service.normalize_author_keys(authors)
        assert result == "Doe_J|Smith_J"

    def test_semicolon_delimited_chembl(self, service: AuthorNormalizer) -> None:
        """Test with ChEMBL semicolon-delimited string."""
        result = service.normalize_author_keys("Smith J; Doe JA; Zhou X")
        assert result == "Smith_J|Doe_J|Zhou_X"

    def test_normalize_author_keys__empty_returns_none__5ee090a0(
        self, service: AuthorNormalizer
    ) -> None:
        """Test that empty inputs return None."""
        assert service.normalize_author_keys(None) is None
        assert service.normalize_author_keys([]) is None
        assert service.normalize_author_keys("") is None

    def test_single_author(self, service: AuthorNormalizer) -> None:
        """Test with single author (no pipe delimiter)."""
        result = service.normalize_author_keys(["John Doe"])
        assert result == "Doe_J"

    def test_mixed_formats(self, service: AuthorNormalizer) -> None:
        """Test with mixed name formats in one list."""
        result = service.normalize_author_keys(
            ["John Doe", "Smith, J", "X. Zhou", "WHO"]
        )
        assert result == "Doe_J|Smith_J|Zhou_X|WHO"
