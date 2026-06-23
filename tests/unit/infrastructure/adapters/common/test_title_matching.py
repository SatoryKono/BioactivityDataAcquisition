"""Unit tests for title matching utilities.

Tests for normalize_title and titles_match functions.
"""

from __future__ import annotations

import pytest

from bioetl.infrastructure.adapters.common.title_matching import (
    normalize_title,
    titles_match,
)

pytestmark = pytest.mark.unit


# =============================================================================
# normalize_title Tests
# =============================================================================


class TestNormalizeTitle:
    """Tests for the normalize_title function."""

    def test_lowercase_conversion(self):
        """Test that titles are converted to lowercase."""
        assert normalize_title("Crystal Structure") == "crystal structure"

    def test_normalize_title__normalization__6c44bc4f(self):
        """Test that whitespace is normalized."""
        assert normalize_title("  Crystal   structure  ") == "crystal structure"

    def test_newlines_normalized(self):
        """Test that newlines are normalized to spaces."""
        assert normalize_title("Crystal\nstructure") == "crystal structure"

    def test_tabs_normalized(self):
        """Test that tabs are normalized to spaces."""
        assert normalize_title("Crystal\tstructure") == "crystal structure"

    def test_normalize_title__empty_string__89e80b3c(self):
        """Test empty string handling."""
        assert normalize_title("") == ""

    def test_already_normalized(self):
        """Test that already normalized strings pass through."""
        assert normalize_title("crystal structure") == "crystal structure"


# =============================================================================
# titles_match Tests - Exact Method
# =============================================================================


class TestTitlesMatchExact:
    """Tests for titles_match with exact method."""

    def test_exact_match(self):
        """Test exact title match."""
        assert titles_match(
            "Crystal structure of rhodopsin",
            "Crystal structure of rhodopsin",
            method="exact",
        )

    def test_exact_case_insensitive(self):
        """Test exact match is case insensitive."""
        assert titles_match(
            "Crystal Structure",
            "crystal structure",
            method="exact",
        )

    def test_exact_no_match(self):
        """Test exact match fails for different titles."""
        assert not titles_match(
            "Crystal structure",
            "Protein folding",
            method="exact",
        )

    def test_exact_substring_not_allowed(self):
        """Test that substring doesn't count as exact match."""
        assert not titles_match(
            "Crystal structure",
            "Crystal structure of rhodopsin",
            method="exact",
        )


# =============================================================================
# titles_match Tests - Substring Method
# =============================================================================


class TestTitlesMatchSubstring:
    """Tests for titles_match with substring method (default)."""

    def test_exact_match_as_substring(self):
        """Test exact match also works with substring method."""
        assert titles_match(
            "Crystal structure of rhodopsin",
            "Crystal structure of rhodopsin",
            method="substring",
        )

    def test_query_is_substring_of_found(self):
        """Test query is substring of found title."""
        assert titles_match(
            "Crystal structure",
            "Crystal structure of rhodopsin bound to arrestin",
            method="substring",
        )

    def test_found_is_substring_of_query(self):
        """Test found title is substring of query."""
        assert titles_match(
            "Crystal structure of rhodopsin bound to arrestin",
            "Crystal structure",
            method="substring",
        )

    def test_no_substring_match(self):
        """Test non-matching titles."""
        assert not titles_match(
            "Crystal structure of rhodopsin",
            "Protein folding mechanisms",
            method="substring",
        )

    def test_default_method_is_substring(self):
        """Test that default method is substring."""
        # Same assertion without explicit method
        assert titles_match(
            "Crystal structure",
            "Crystal structure of rhodopsin",
        )

    def test_empty_string_handling(self):
        """Test empty string handling - empty is substring of anything."""
        assert titles_match("", "")
        assert titles_match("Title", "")
        assert titles_match("", "Title")


# =============================================================================
# titles_match Tests - Fuzzy Method
# =============================================================================


class TestTitlesMatchFuzzy:
    """Tests for titles_match with fuzzy (Jaccard) method."""

    def test_fuzzy_identical_titles(self):
        """Test fuzzy match with identical titles."""
        assert titles_match(
            "Crystal structure of rhodopsin",
            "Crystal structure of rhodopsin",
            method="fuzzy",
        )

    def test_fuzzy_similar_titles(self):
        """Test fuzzy match with similar titles."""
        # "structure crystal rhodopsin" vs "crystal structure rhodopsin"
        # Same words, different order -> Jaccard = 1.0
        assert titles_match(
            "Structure crystal rhodopsin",
            "Crystal structure rhodopsin",
            method="fuzzy",
        )

    def test_fuzzy_partial_overlap(self):
        """Test fuzzy match with partial word overlap."""
        # "crystal structure" vs "crystal rhodopsin"
        # Words: {crystal, structure} vs {crystal, rhodopsin}
        # Intersection: {crystal} = 1
        # Union: {crystal, structure, rhodopsin} = 3
        # Jaccard: 1/3 = 0.33 < 0.8 default threshold
        assert not titles_match(
            "Crystal structure",
            "Crystal rhodopsin",
            method="fuzzy",
        )

    def test_fuzzy_custom_threshold(self):
        """Test fuzzy match with custom threshold."""
        # Same partial overlap but lower threshold
        assert titles_match(
            "Crystal structure",
            "Crystal rhodopsin",
            method="fuzzy",
            threshold=0.3,
        )

    def test_fuzzy_completely_different(self):
        """Test fuzzy match with completely different titles."""
        assert not titles_match(
            "Crystal structure",
            "Protein folding",
            method="fuzzy",
        )

    def test_fuzzy_empty_strings(self):
        """Test fuzzy match with empty strings returns False."""
        assert not titles_match("", "Title", method="fuzzy")
        assert not titles_match("Title", "", method="fuzzy")
        assert not titles_match("", "", method="fuzzy")

    def test_fuzzy_high_threshold(self):
        """Test fuzzy match with high threshold."""
        # Same title should still pass even with 1.0 threshold
        assert titles_match(
            "Crystal structure",
            "Crystal structure",
            method="fuzzy",
            threshold=1.0,
        )


# =============================================================================
# Edge Cases
# =============================================================================


class TestTitlesMatchEdgeCases:
    """Tests for edge cases in title matching."""

    def test_unknown_method_defaults_to_exact(self):
        """Test that unknown method defaults to exact match."""
        assert (
            titles_match(
                "Crystal structure",
                "Crystal structure",
                method="unknown",
            )
            is True
        )
        assert (
            titles_match(
                "Crystal structure",
                "Crystal structure of rhodopsin",
                method="unknown",
            )
            is False
        )

    def test_special_characters_preserved(self):
        """Test that special characters are preserved in comparison."""
        assert (
            titles_match(
                "Structure of Na+/K+-ATPase",
                "Structure of Na+/K+-ATPase",
            )
            is True
        )

    def test_match_edge_cases__unicode_handling__5f839299(self):
        """Test unicode characters are handled correctly."""
        assert (
            titles_match(
                "Strukturanalyse der Rhodopsin-Kristalle",
                "strukturanalyse der rhodopsin-kristalle",
            )
            is True
        )

    def test_threshold_ignored_for_non_fuzzy(self):
        """Test that threshold parameter is ignored for non-fuzzy methods."""
        # Should still work regardless of threshold value
        assert (
            titles_match(
                "Crystal structure",
                "Crystal structure of rhodopsin",
                method="substring",
                threshold=1.0,
            )
            is True
        )
