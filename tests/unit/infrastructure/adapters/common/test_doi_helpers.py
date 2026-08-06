# pyright: reportArgumentType=false
"""Unit tests for adapter-side DOI transport prefix stripping."""

from __future__ import annotations

import pytest

from bioetl.infrastructure.adapters.common.doi_helpers import strip_doi_transport_prefix

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("https://doi.org/10.1000/xyz123", "10.1000/xyz123"),
        ("http://dx.doi.org/10.1000/xyz123", "10.1000/xyz123"),
        ("https://dx.doi.org/10.1000/xyz123", "10.1000/xyz123"),
        ("doi:10.1000/xyz123", "10.1000/xyz123"),
        ("DOI:10.1000/xyz123", "10.1000/xyz123"),
        ("10.1000/xyz123", "10.1000/xyz123"),
    ],
)
def test_strip_doi_transport_prefix_covers_url_and_doi_prefixes(
    raw: str, expected: str
) -> None:
    assert strip_doi_transport_prefix(raw) == expected


def test_strip_doi_transport_prefix_always_strips_uppercase_regardless_of_flag() -> None:
    # allow_uppercase_prefix is deprecated and ignored; DOI: always strips.
    assert (
        strip_doi_transport_prefix("DOI:10.1000/xyz123", allow_uppercase_prefix=False)
        == "10.1000/xyz123"
    )
    assert (
        strip_doi_transport_prefix("DOI:10.1000/xyz123", allow_uppercase_prefix=True)
        == "10.1000/xyz123"
    )
