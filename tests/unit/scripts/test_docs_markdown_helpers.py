"""Tests for shared markdown helper regexes."""

from __future__ import annotations

import pytest

from scripts.docs.common.markdown import MD_HEADING_RE


pytestmark = pytest.mark.unit

def test_md_heading_re_matches_single_line_heading_only() -> None:
    match = MD_HEADING_RE.match("### Example Heading")

    assert match is not None
    assert match.group(1) == "Example Heading"


def test_md_heading_re_ignores_multiline_payloads() -> None:
    assert MD_HEADING_RE.match("### Heading\nNext line") is None
