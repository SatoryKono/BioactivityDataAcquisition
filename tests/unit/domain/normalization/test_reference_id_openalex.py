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
"""Tests for pure OpenAlex reference ID normalization helpers."""

from __future__ import annotations

import pytest

from bioetl.domain.normalization._reference_id_openalex import (
    normalize_openalex_author_reference_id,
    normalize_openalex_institution_reference_id,
    normalize_openalex_reference_id,
    normalize_openalex_topic_reference_id,
    normalize_openalex_work_reference_id,
)

pytestmark = pytest.mark.unit


def test_normalize_openalex_reference_id_preserves_non_text_and_missing_values() -> (
    None
):
    sentinel = object()

    assert normalize_openalex_reference_id(None, prefix="W") is None
    assert normalize_openalex_reference_id("   ", prefix="W") is None
    assert normalize_openalex_reference_id(sentinel, prefix="W") is sentinel


def test_openalex_specific_reference_helpers_canonicalize_urls() -> None:
    assert normalize_openalex_author_reference_id("https://openalex.org/a123") == "A123"
    assert (
        normalize_openalex_institution_reference_id("https://openalex.org/i456")
        == "I456"
    )
    assert normalize_openalex_topic_reference_id("https://openalex.org/t789") == "T789"
    assert normalize_openalex_work_reference_id("https://openalex.org/w987") == "W987"
