"""Unit tests for DOI transport helpers."""

import pytest

from bioetl.infrastructure.adapters.common.doi_helpers import strip_doi_transport_prefix


@pytest.mark.parametrize(
    ("input_doi", "expected_output"),
    [
        # Bare DOIs (no change expected)
        ("10.1038/s41586-020-2649-2", "10.1038/s41586-020-2649-2"),
        ("10.1016/j.cell.2021.02.021", "10.1016/j.cell.2021.02.021"),
        # HTTP URL formats
        ("http://doi.org/10.1038/s41586-020-2649-2", "10.1038/s41586-020-2649-2"),
        ("https://doi.org/10.1038/s41586-020-2649-2", "10.1038/s41586-020-2649-2"),
        ("http://dx.doi.org/10.1038/s41586-020-2649-2", "10.1038/s41586-020-2649-2"),
        ("https://dx.doi.org/10.1038/s41586-020-2649-2", "10.1038/s41586-020-2649-2"),
        # DOI: prefix (case insensitive according to implementation)
        ("doi:10.1038/s41586-020-2649-2", "10.1038/s41586-020-2649-2"),
        ("DOI:10.1038/s41586-020-2649-2", "10.1038/s41586-020-2649-2"),
        ("DoI:10.1038/s41586-020-2649-2", "10.1038/s41586-020-2649-2"),
        # With whitespace
        ("  10.1038/s41586-020-2649-2  ", "10.1038/s41586-020-2649-2"),
        ("  doi:10.1038/s41586-020-2649-2  ", "10.1038/s41586-020-2649-2"),
    ],
)
def test_strip_doi_transport_prefix(input_doi: str, expected_output: str) -> None:
    """Test that strip_doi_transport_prefix correctly removes prefixes."""
    assert strip_doi_transport_prefix(input_doi) == expected_output


def test_strip_doi_transport_prefix_allow_uppercase_prefix_ignored() -> None:
    """Test that the allow_uppercase_prefix argument is safely ignored."""
    # It should strip "DOI:" even if allow_uppercase_prefix=False
    assert (
        strip_doi_transport_prefix("DOI:10.123/abc", allow_uppercase_prefix=False)
        == "10.123/abc"
    )
    assert (
        strip_doi_transport_prefix("DOI:10.123/abc", allow_uppercase_prefix=True)
        == "10.123/abc"
    )
