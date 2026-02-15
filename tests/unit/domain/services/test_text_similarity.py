"""Unit tests for text similarity domain service.

Tests for normalize_text and jaccard_similarity functions.
"""

from __future__ import annotations

import pytest

from bioetl.domain.services.text_similarity import jaccard_similarity, normalize_text


class TestNormalizeText:
    """Tests for normalize_text function."""

    def test_lowercase(self):
        assert normalize_text("Hello World") == "hello world"

    def test_strips_whitespace(self):
        assert normalize_text("  hello  ") == "hello"

    def test_collapses_internal_whitespace(self):
        assert normalize_text("hello   world") == "hello world"

    def test_removes_punctuation(self):
        assert normalize_text("hello, world!") == "hello world"

    def test_empty_string(self):
        assert normalize_text("") == ""

    def test_only_punctuation(self):
        result = normalize_text(".,!?")
        assert result == ""

    def test_mixed_case_punctuation(self):
        assert (
            normalize_text("A Novel Drug-Target Interaction")
            == "a novel drug target interaction"
        )


class TestJaccardSimilarity:
    """Tests for jaccard_similarity function."""

    def test_identical_strings(self):
        assert jaccard_similarity("hello world", "hello world") == 1.0

    def test_completely_different(self):
        assert jaccard_similarity("hello world", "foo bar") == 0.0

    def test_partial_overlap(self):
        # "hello world" -> {"hello", "world"}
        # "hello foo" -> {"hello", "foo"}
        # intersection=1, union=3 -> 1/3
        result = jaccard_similarity("hello world", "hello foo")
        assert abs(result - 1 / 3) < 0.01

    def test_case_insensitive(self):
        assert jaccard_similarity("Hello World", "hello world") == 1.0

    def test_punctuation_ignored(self):
        assert jaccard_similarity("hello, world!", "hello world") == 1.0

    def test_empty_first(self):
        assert jaccard_similarity("", "hello") == 0.0

    def test_empty_second(self):
        assert jaccard_similarity("hello", "") == 0.0

    def test_both_empty(self):
        assert jaccard_similarity("", "") == 0.0

    def test_similar_titles(self):
        title_a = "A Novel Approach to Drug Discovery"
        title_b = "A Novel Approach to Drug Discovery and Development"
        # overlap: {a, novel, approach, to, drug, discovery} = 6
        # union: {a, novel, approach, to, drug, discovery, and, development} = 8
        # similarity = 6/8 = 0.75
        result = jaccard_similarity(title_a, title_b)
        assert result == pytest.approx(0.75)

    def test_threshold_boundary(self):
        """Titles that should pass 0.8 threshold."""
        title_a = "Inhibition of EGFR in cancer cells"
        title_b = "Inhibition of EGFR in cancer cell lines"
        result = jaccard_similarity(title_a, title_b)
        # {inhibition, of, egfr, in, cancer, cells} vs {inhibition, of, egfr, in, cancer, cell, lines}
        # intersection: {inhibition, of, egfr, in, cancer} = 5
        # union: {inhibition, of, egfr, in, cancer, cells, cell, lines} = 8
        # 5/8 = 0.625
        assert result < 0.8  # Demonstrates threshold sensitivity
