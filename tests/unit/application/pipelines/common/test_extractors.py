"""Unit tests for common field extractors.

Tests the pure functions in extractors.py module.
"""

from __future__ import annotations

import pytest

from bioetl.application.pipelines.common.extractors import extract_author_names


pytestmark = pytest.mark.unit

class TestExtractAuthorNames:
    """Tests for extract_author_names function."""

    # Basic functionality tests

    def test_extract_authors_flat_structure(self) -> None:
        """Should extract author names from flat structure (SemanticScholar-like)."""
        items = [
            {"authorId": "123", "name": "John Doe"},
            {"authorId": "456", "name": "Jane Smith"},
        ]
        result = extract_author_names(items, name_field="name")
        assert result == ["John Doe", "Jane Smith"]

    def test_extract_authors_nested_structure(self) -> None:
        """Should extract author names from nested structure (OpenAlex-like)."""
        items = [
            {"author": {"display_name": "John Doe", "id": "A123"}},
            {"author": {"display_name": "Jane Smith", "id": "A456"}},
        ]
        result = extract_author_names(
            items, name_field="display_name", nested_field="author"
        )
        assert result == ["John Doe", "Jane Smith"]

    def test_extract_single_author(self) -> None:
        """Should handle single author in list."""
        items = [{"name": "Single Author"}]
        result = extract_author_names(items, name_field="name")
        assert result == ["Single Author"]

    # Empty and None input tests

    def test_extract_authors_none_input(self) -> None:
        """Should return empty list for None input."""
        result = extract_author_names(None)
        assert result == []

    def test_extract_authors_empty_list(self) -> None:
        """Should return empty list for empty input list."""
        result = extract_author_names([])
        assert result == []

    # Missing field tests

    def test_extract_authors_missing_name_field(self) -> None:
        """Should skip items without the name field."""
        items = [
            {"authorId": "123"},  # No name field
            {"authorId": "456", "name": "Has Name"},
        ]
        result = extract_author_names(items, name_field="name")
        assert result == ["Has Name"]

    def test_extract_authors_missing_nested_field(self) -> None:
        """Should skip items without the nested field."""
        items = [
            {"not_author": {"display_name": "Ignored"}},  # Wrong nested key
            {"author": {"display_name": "Valid Author"}},
        ]
        result = extract_author_names(
            items, name_field="display_name", nested_field="author"
        )
        assert result == ["Valid Author"]

    def test_extract_authors_none_name_value(self) -> None:
        """Should skip items where name is None."""
        items = [
            {"name": None},
            {"name": "Valid Name"},
        ]
        result = extract_author_names(items, name_field="name")
        assert result == ["Valid Name"]

    def test_extract_authors_none_nested_value(self) -> None:
        """Should skip items where nested field is None."""
        items = [
            {"author": None},
            {"author": {"display_name": "Valid Author"}},
        ]
        result = extract_author_names(
            items, name_field="display_name", nested_field="author"
        )
        assert result == ["Valid Author"]

    # Type validation tests

    def test_extract_authors_non_dict_nested_value(self) -> None:
        """Should skip items where nested field is not a dict."""
        items = [
            {"author": "string_value"},  # String instead of dict
            {"author": ["list_value"]},  # List instead of dict
            {"author": {"display_name": "Valid Author"}},
        ]
        result = extract_author_names(
            items, name_field="display_name", nested_field="author"
        )
        assert result == ["Valid Author"]

    def test_extract_authors_non_string_name_value(self) -> None:
        """Should skip items where name is not a string."""
        items = [
            {"name": 12345},  # Integer
            {"name": ["list"]},  # List
            {"name": {"nested": "dict"}},  # Dict
            {"name": "Valid String"},
        ]
        result = extract_author_names(items, name_field="name")
        assert result == ["Valid String"]

    # Whitespace handling tests

    def test_extract_authors_strips_whitespace(self) -> None:
        """Should strip leading/trailing whitespace from names."""
        items = [
            {"name": "  John Doe  "},
            {"name": "\tJane Smith\n"},
        ]
        result = extract_author_names(items, name_field="name")
        assert result == ["John Doe", "Jane Smith"]

    def test_extract_authors_skips_whitespace_only_names(self) -> None:
        """Should skip names that are only whitespace after stripping."""
        items = [
            {"name": "   "},
            {"name": "\t\n"},
            {"name": "Valid Name"},
        ]
        result = extract_author_names(items, name_field="name")
        assert result == ["Valid Name"]

    def test_extract_authors_empty_string_name(self) -> None:
        """Should skip empty string names."""
        items = [
            {"name": ""},
            {"name": "Valid Name"},
        ]
        result = extract_author_names(items, name_field="name")
        assert result == ["Valid Name"]

    # Mixed scenarios tests

    def test_extract_authors_mixed_valid_invalid(self) -> None:
        """Should handle mix of valid and invalid entries."""
        items = [
            {"author": {"display_name": "Author One"}},
            {"author": None},  # Invalid
            {"author": {"display_name": "  "}},  # Whitespace only
            {"not_author": {}},  # Wrong key
            {"author": {"display_name": "Author Two"}},
        ]
        result = extract_author_names(
            items, name_field="display_name", nested_field="author"
        )
        assert result == ["Author One", "Author Two"]

    # Default parameters tests

    def test_extract_authors_default_name_field(self) -> None:
        """Should use 'name' as default name_field."""
        items = [{"name": "Default Field Author"}]
        result = extract_author_names(items)
        assert result == ["Default Field Author"]

    def test_extract_authors_no_nested_field_default(self) -> None:
        """Should access item directly when nested_field is None (default)."""
        items = [{"name": "Direct Access Author"}]
        result = extract_author_names(items, name_field="name", nested_field=None)
        assert result == ["Direct Access Author"]


class TestExtractAuthorNamesProviderFormats:
    """Tests simulating real provider data formats."""

    def test_openalex_format(self) -> None:
        """Should handle OpenAlex authorship format."""
        authorships = [
            {
                "author": {
                    "id": "https://openalex.org/A1234567890",
                    "display_name": "Albert Einstein",
                    "ormolecule_id": "https://ormolecule_id.org/0000-0000-0000-0001",
                },
                "author_position": "first",
                "institutions": [],
            },
            {
                "author": {
                    "id": "https://openalex.org/A0987654321",
                    "display_name": "Niels Bohr",
                    "ormolecule_id": None,
                },
                "author_position": "last",
                "institutions": [],
            },
        ]
        result = extract_author_names(
            authorships, name_field="display_name", nested_field="author"
        )
        assert result == ["Albert Einstein", "Niels Bohr"]

    def test_semanticscholar_format(self) -> None:
        """Should handle Semantic Scholar author format."""
        authors = [
            {"authorId": "1234567", "name": "Marie Curie"},
            {"authorId": "7654321", "name": "Pierre Curie"},
            {"authorId": None, "name": "Anonymous Contributor"},
        ]
        result = extract_author_names(authors, name_field="name")
        assert result == ["Marie Curie", "Pierre Curie", "Anonymous Contributor"]

    def test_semanticscholar_format_missing_names(self) -> None:
        """Should handle Semantic Scholar entries with missing names."""
        authors = [
            {"authorId": "123", "name": "Has Name"},
            {"authorId": "456"},  # Missing name
            {"authorId": "789", "name": None},  # Explicit None
            {"authorId": "012", "name": "Also Has Name"},
        ]
        result = extract_author_names(authors, name_field="name")
        assert result == ["Has Name", "Also Has Name"]

    def test_openalex_format_invalid_structures(self) -> None:
        """Should handle OpenAlex entries with invalid structures."""
        authorships = [
            {"author": {"display_name": "Valid Author"}},
            {"author": None},  # Invalid author
            {"not_author": {}},  # Missing author key
            {"author": "string"},  # Invalid type
            {"author": {"id": "A123"}},  # Missing display_name
        ]
        result = extract_author_names(
            authorships, name_field="display_name", nested_field="author"
        )
        assert result == ["Valid Author"]


class TestExtractAuthorNamesEdgeCases:
    """Edge case tests for extract_author_names."""

    def test_large_author_list(self) -> None:
        """Should handle large lists efficiently."""
        items = [{"name": f"Author {i}"} for i in range(1000)]
        result = extract_author_names(items, name_field="name")
        assert len(result) == 1000
        assert result[0] == "Author 0"
        assert result[-1] == "Author 999"

    def test_unicode_names(self) -> None:
        """Should handle Unicode characters in names."""
        items = [
            {"name": "José García"},
            {"name": "中村 太郎"},
            {"name": "Müller, Hans"},
            {"name": "Иван Петров"},
        ]
        result = extract_author_names(items, name_field="name")
        assert result == ["José García", "中村 太郎", "Müller, Hans", "Иван Петров"]

    def test_special_characters_in_names(self) -> None:
        """Should preserve special characters in names."""
        items = [
            {"name": "John O'Brien"},
            {"name": "Mary-Jane Watson"},
            {"name": "Dr. Smith, Jr."},
        ]
        result = extract_author_names(items, name_field="name")
        assert result == ["John O'Brien", "Mary-Jane Watson", "Dr. Smith, Jr."]

    def test_deeply_nested_would_not_work(self) -> None:
        """Demonstrates that deeply nested structures need custom extraction.

        The function only supports one level of nesting.
        """
        items = [{"outer": {"inner": {"name": "Deeply Nested"}}}]
        # This won't work - only one level of nesting supported
        result = extract_author_names(items, name_field="name", nested_field="outer")
        # The "inner" dict doesn't have a "name" field directly
        assert result == []

    @pytest.mark.parametrize(
        ("name_field", "expected"),
        [
            ("display_name", ["Display Name Author"]),
            ("full_name", ["Full Name Author"]),
            ("author_name", ["Author Name Author"]),
        ],
    )
    def test_custom_name_fields(self, name_field: str, expected: list[str]) -> None:
        """Should work with various custom name field names."""
        items = [
            {
                "display_name": "Display Name Author",
                "full_name": "Full Name Author",
                "author_name": "Author Name Author",
            }
        ]
        result = extract_author_names(items, name_field=name_field)
        assert result == expected
