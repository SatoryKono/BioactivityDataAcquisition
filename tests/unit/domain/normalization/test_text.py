"""Tests for low-level text normalization helpers."""

from __future__ import annotations

import pytest

from bioetl.domain.normalization.text import _collapse_whitespace


pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("", ""),
        (" \t\n", " "),
        ("alpha\t beta\n", "alpha beta "),
        (" alpha   beta ", " alpha beta "),
    ],
)
def test_collapse_whitespace_matches_regex_semantics(raw: str, expected: str) -> None:
    assert _collapse_whitespace(raw) == expected
