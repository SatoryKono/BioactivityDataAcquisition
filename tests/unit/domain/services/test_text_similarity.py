"""Unit tests for text similarity domain service.

Tests for normalize_text and jaccard_similarity functions.
"""

from __future__ import annotations

import pytest

from bioetl.domain.behavior.text_similarity import jaccard_similarity, normalize_text


pytestmark = pytest.mark.unit

class TestNormalizeText:
    """Tests for normalize_text function."""

    def test_lowercase(self) -> None:
        assert normalize_text("Hello World") == "hello world"

    def test_normalize_text__strips_whitespace__3a692a52(self) -> None:
        assert normalize_text("  hello  ") == "hello"

    def test_collapses_internal_whitespace(self) -> None:
        assert normalize_text("hello   world") == "hello world"

    def test_removes_punctuation(self) -> None:
        assert normalize_text("hello, world!") == "hello world"

    def test_normalize_text__empty_string__8f7a205b(self) -> None:
        assert normalize_text("") == ""

    def test_only_punctuation(self) -> None:
        result = normalize_text(".,!?")
        assert result == ""

    def test_mixed_case_punctuation(self) -> None:
        assert (
            normalize_text("A Novel Drug-Target Interaction")
            == "a novel drug target interaction"
        )


class TestJaccardSimilarity:
    """Tests for jaccard_similarity function."""

    def test_identical_strings(self) -> None:
        assert jaccard_similarity("hello world", "hello world") == pytest.approx(1.0)

    def test_completely_different(self) -> None:
        assert jaccard_similarity("hello world", "foo bar") == pytest.approx(0.0)

    def test_partial_overlap(self) -> None:
        # "hello world" -> {"hello", "world"}
        # "hello foo" -> {"hello", "foo"}
        # intersection=1, union=3 -> 1/3
        result = jaccard_similarity("hello world", "hello foo")
        assert result == pytest.approx(1 / 3, abs=0.01)

    def test_jaccard_similarity__case_insensitive__52061d12(self) -> None:
        assert jaccard_similarity("Hello World", "hello world") == pytest.approx(1.0)

    def test_punctuation_ignored(self) -> None:
        assert jaccard_similarity("hello, world!", "hello world") == pytest.approx(1.0)

    def test_empty_first(self) -> None:
        assert jaccard_similarity("", "hello") == pytest.approx(0.0)

    def test_empty_second(self) -> None:
        assert jaccard_similarity("hello", "") == pytest.approx(0.0)

    def test_both_empty(self) -> None:
        assert jaccard_similarity("", "") == pytest.approx(0.0)

    def test_similar_titles(self) -> None:
        title_a = "A Novel Approach to Drug Discovery"
        title_b = "A Novel Approach to Drug Discovery and Development"
        # overlap: {a, novel, approach, to, drug, discovery} = 6
        # union: {a, novel, approach, to, drug, discovery, and, development} = 8
        # similarity = 6/8 = 0.75
        result = jaccard_similarity(title_a, title_b)
        assert result == pytest.approx(0.75)

    def test_threshold_boundary(self) -> None:
        """Titles that should pass 0.8 threshold."""
        title_a = "Inhibition of EGFR in cancer cells"
        title_b = "Inhibition of EGFR in cancer cell lines"
        result = jaccard_similarity(title_a, title_b)
        # {inhibition, of, egfr, in, cancer, cells} vs {inhibition, of, egfr, in, cancer, cell, lines}
        # intersection: {inhibition, of, egfr, in, cancer} = 5
        # union: {inhibition, of, egfr, in, cancer, cells, cell, lines} = 8
        # 5/8 = 0.625
        assert result < 0.8  # Demonstrates threshold sensitivity
