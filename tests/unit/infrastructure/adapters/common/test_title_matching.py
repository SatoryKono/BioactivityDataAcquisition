"""Unit tests for title matching utilities.

Tests for normalize_title and titles_match functions.
"""

from __future__ import annotations

from bioetl.infrastructure.adapters.common.title_matching import (
    normalize_title,
    titles_match,
)


# =============================================================================
# normalize_title Tests
# =============================================================================


class TestNormalizeTitle:
    """Tests for the normalize_title function."""

    def test_lowercase_conversion(self):
        """Test that titles are converted to lowercase."""
        assert normalize_title("Crystal Structure") == "crystal structure"

    def test_whitespace_normalization(self):
        """Test that whitespace is normalized."""
        assert normalize_title("  Crystal   structure  ") == "crystal structure"

    def test_newlines_normalized(self):
        """Test that newlines are normalized to spaces."""
        assert normalize_title("Crystal\nstructure") == "crystal structure"

    def test_tabs_normalized(self):
        """Test that tabs are normalized to spaces."""
        assert normalize_title("Crystal\tstructure") == "crystal structure"

    def test_empty_string(self):
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
        assert (
            titles_match(
                "Crystal structure of rhodopsin",
                "Crystal structure of rhodopsin",
                method="exact",
            )
            is True
        )

    def test_exact_case_insensitive(self):
        """Test exact match is case insensitive."""
        assert (
            titles_match(
                "Crystal Structure",
                "crystal structure",
                method="exact",
            )
            is True
        )

    def test_exact_no_match(self):
        """Test exact match fails for different titles."""
        assert (
            titles_match(
                "Crystal structure",
                "Protein folding",
                method="exact",
            )
            is False
        )

    def test_exact_substring_not_allowed(self):
        """Test that substring doesn't count as exact match."""
        assert (
            titles_match(
                "Crystal structure",
                "Crystal structure of rhodopsin",
                method="exact",
            )
            is False
        )


# =============================================================================
# titles_match Tests - Substring Method
# =============================================================================


class TestTitlesMatchSubstring:
    """Tests for titles_match with substring method (default)."""

    def test_exact_match_as_substring(self):
        """Test exact match also works with substring method."""
        assert (
            titles_match(
                "Crystal structure of rhodopsin",
                "Crystal structure of rhodopsin",
                method="substring",
            )
            is True
        )

    def test_query_is_substring_of_found_long_titles(self):
        """Test query is substring of found title (both >= 4 words)."""
        # Both titles must have >= 4 words for substring matching
        assert (
            titles_match(
                "Crystal structure of rhodopsin",
                "Crystal structure of rhodopsin bound to arrestin",
                method="substring",
            )
            is True
        )

    def test_found_is_substring_of_query_long_titles(self):
        """Test found title is substring of query (both >= 4 words)."""
        assert (
            titles_match(
                "Crystal structure of rhodopsin bound to arrestin",
                "Crystal structure of rhodopsin",
                method="substring",
            )
            is True
        )

    def test_short_title_falls_back_to_fuzzy(self):
        """Test short titles (< 4 words) use fuzzy matching instead of substring.

        This prevents false positives like "Cancer" matching "Breast Cancer Research".
        """
        # Short query (2 words) against long title - uses fuzzy matching
        # "Crystal structure" has low Jaccard similarity with long title
        assert (
            titles_match(
                "Crystal structure",
                "Crystal structure of rhodopsin bound to arrestin",
                method="substring",
            )
            is False  # Falls back to fuzzy, low similarity (2/7 = 0.29)
        )

        # Short titles with very high word overlap still match via fuzzy
        # Jaccard = 3/4 = 0.75 (close to 0.8 threshold)
        assert (
            titles_match(
                "Machine learning",
                "Machine learning study",
                method="substring",
                threshold=0.6,  # Lower threshold for this test
            )
            is True
        )

        # One-word title should require exact match via fuzzy
        assert (
            titles_match(
                "Cancer",
                "Breast Cancer Research Methods",
                method="substring",
            )
            is False  # 1/4 = 0.25 < 0.8 threshold
        )

    def test_no_substring_match(self):
        """Test non-matching titles."""
        assert (
            titles_match(
                "Crystal structure of rhodopsin",
                "Protein folding mechanisms here",
                method="substring",
            )
            is False
        )

    def test_default_method_is_substring(self):
        """Test that default method is substring (with fuzzy fallback for short titles)."""
        # Long titles use substring matching
        assert (
            titles_match(
                "Crystal structure of rhodopsin",
                "Crystal structure of rhodopsin bound to protein",
            )
            is True
        )

    def test_empty_string_handling(self):
        """Test empty string handling - returns False for safety."""
        assert titles_match("", "") is True  # Both empty = equal
        assert titles_match("Title", "") is False  # Empty has no words
        assert titles_match("", "Title") is False  # Empty has no words


# =============================================================================
# titles_match Tests - Fuzzy Method
# =============================================================================


class TestTitlesMatchFuzzy:
    """Tests for titles_match with fuzzy (Jaccard) method."""

    def test_fuzzy_identical_titles(self):
        """Test fuzzy match with identical titles."""
        assert (
            titles_match(
                "Crystal structure of rhodopsin",
                "Crystal structure of rhodopsin",
                method="fuzzy",
            )
            is True
        )

    def test_fuzzy_similar_titles(self):
        """Test fuzzy match with similar titles."""
        # "structure crystal rhodopsin" vs "crystal structure rhodopsin"
        # Same words, different order -> Jaccard = 1.0
        assert (
            titles_match(
                "Structure crystal rhodopsin",
                "Crystal structure rhodopsin",
                method="fuzzy",
            )
            is True
        )

    def test_fuzzy_partial_overlap(self):
        """Test fuzzy match with partial word overlap."""
        # "crystal structure" vs "crystal rhodopsin"
        # Words: {crystal, structure} vs {crystal, rhodopsin}
        # Intersection: {crystal} = 1
        # Union: {crystal, structure, rhodopsin} = 3
        # Jaccard: 1/3 = 0.33 < 0.8 default threshold
        assert (
            titles_match(
                "Crystal structure",
                "Crystal rhodopsin",
                method="fuzzy",
            )
            is False
        )

    def test_fuzzy_custom_threshold(self):
        """Test fuzzy match with custom threshold."""
        # Same partial overlap but lower threshold
        assert (
            titles_match(
                "Crystal structure",
                "Crystal rhodopsin",
                method="fuzzy",
                threshold=0.3,
            )
            is True
        )

    def test_fuzzy_completely_different(self):
        """Test fuzzy match with completely different titles."""
        assert (
            titles_match(
                "Crystal structure",
                "Protein folding",
                method="fuzzy",
            )
            is False
        )

    def test_fuzzy_empty_strings(self):
        """Test fuzzy match with empty strings returns False."""
        assert titles_match("", "Title", method="fuzzy") is False
        assert titles_match("Title", "", method="fuzzy") is False
        assert titles_match("", "", method="fuzzy") is False

    def test_fuzzy_high_threshold(self):
        """Test fuzzy match with high threshold."""
        # Same title should still pass even with 1.0 threshold
        assert (
            titles_match(
                "Crystal structure",
                "Crystal structure",
                method="fuzzy",
                threshold=1.0,
            )
            is True
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

    def test_unicode_handling(self):
        """Test unicode characters are handled correctly."""
        assert (
            titles_match(
                "Strukturanalyse der Rhodopsin-Kristalle",
                "strukturanalyse der rhodopsin-kristalle",
            )
            is True
        )

    def test_threshold_used_for_short_titles_in_substring_mode(self):
        """Test that threshold is used for short titles even in substring mode.

        Short titles (< 4 words) fall back to fuzzy matching which uses threshold.
        """
        # Short title with high threshold - requires higher similarity
        assert (
            titles_match(
                "Crystal structure",
                "Crystal structure of rhodopsin",
                method="substring",
                threshold=1.0,  # Requires 100% similarity
            )
            is False  # Falls back to fuzzy, doesn't meet 1.0 threshold
        )
        # Same titles with lower threshold
        assert (
            titles_match(
                "Crystal structure",
                "Crystal structure of rhodopsin",
                method="substring",
                threshold=0.5,  # Lower threshold
            )
            is True  # 2/4 words = 0.5 Jaccard similarity
        )
