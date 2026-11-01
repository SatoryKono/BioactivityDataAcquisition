"""Tests for low-level text normalization helpers."""

from __future__ import annotations

import pytest

from bioetl.domain.normalization.text import _collapse_whitespace, normalize_title


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


def test_normalize_title_strips_control_characters_and_preserves_whitespace() -> None:
    control_chars = "".join(
        [chr(codepoint) for codepoint in range(9)]
        + [chr(codepoint) for codepoint in range(14, 32)]
        + [chr(codepoint) for codepoint in range(127, 160)]
    )

    assert normalize_title(f"left{control_chars}right") == "leftright"
    assert normalize_title("left\t right\n") == "left right"


def test_normalize_title_preserves_unicode_and_strips_control_characters() -> None:
    assert normalize_title("β-catenin\x01 regulation") == "β-catenin regulation"
