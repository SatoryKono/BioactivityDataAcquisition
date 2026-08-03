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
