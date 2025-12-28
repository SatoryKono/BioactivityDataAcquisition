"""Unit tests for OpenAlex abstract parser."""

from __future__ import annotations

from bioetl.infrastructure.adapters.openalex.abstract_parser import (
    estimate_abstract_length,
    reconstruct_abstract,
)


class TestReconstructAbstract:
    """Tests for abstract reconstruction from inverted index."""

    def test_simple_abstract(self):
        """Test reconstructing a simple abstract."""
        inverted_index = {
            "Hello": [0],
            "world": [1],
        }

        result = reconstruct_abstract(inverted_index)

        assert result == "Hello world"

    def test_multiple_word_positions(self):
        """Test word appearing at multiple positions."""
        inverted_index = {
            "The": [0],
            "cat": [1, 4],
            "and": [2],
            "dog": [3],
            "play": [5],
        }

        result = reconstruct_abstract(inverted_index)

        assert result == "The cat and dog cat play"

    def test_complex_abstract(self):
        """Test reconstructing a more complex abstract."""
        inverted_index = {
            "This": [0],
            "is": [1, 5],
            "a": [2],
            "test": [3],
            "abstract": [4],
            "that": [6],
            "complex": [7],
        }

        result = reconstruct_abstract(inverted_index)

        assert result == "This is a test abstract is that complex"

    def test_empty_inverted_index(self):
        """Test with empty inverted index returns None."""
        result = reconstruct_abstract({})
        assert result is None

    def test_none_inverted_index(self):
        """Test with None inverted index returns None."""
        result = reconstruct_abstract(None)
        assert result is None

    def test_single_word(self):
        """Test with single word."""
        inverted_index = {"Abstract": [0]}

        result = reconstruct_abstract(inverted_index)

        assert result == "Abstract"

    def test_preserves_word_order(self):
        """Test that word order is preserved correctly."""
        inverted_index = {
            "A": [0],
            "B": [1],
            "C": [2],
            "D": [3],
        }

        result = reconstruct_abstract(inverted_index)

        assert result == "A B C D"

    def test_non_sequential_positions(self):
        """Test with non-sequential positions."""
        inverted_index = {
            "First": [0],
            "Last": [100],
            "Middle": [50],
        }

        result = reconstruct_abstract(inverted_index)

        assert result == "First Middle Last"


class TestEstimateAbstractLength:
    """Tests for abstract length estimation."""

    def test_simple_estimate(self):
        """Test estimating length of simple abstract."""
        inverted_index = {
            "Hello": [0],
            "world": [1],
        }

        length = estimate_abstract_length(inverted_index)

        assert length == 2

    def test_repeated_words(self):
        """Test estimating length with repeated words."""
        inverted_index = {
            "The": [0, 5],
            "cat": [1, 3],
            "is": [2],
            "sleepy": [4],
        }

        length = estimate_abstract_length(inverted_index)

        assert length == 6

    def test_empty_returns_zero(self):
        """Test empty inverted index returns 0."""
        length = estimate_abstract_length({})
        assert length == 0

    def test_none_returns_zero(self):
        """Test None inverted index returns 0."""
        length = estimate_abstract_length(None)
        assert length == 0

    def test_single_word_many_occurrences(self):
        """Test single word with many occurrences."""
        inverted_index = {
            "test": [0, 5, 10, 15, 20],
        }

        length = estimate_abstract_length(inverted_index)

        assert length == 5
