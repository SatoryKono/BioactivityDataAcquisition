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
"""Tests for DOI regex validation across Pandera schemas.

Tests DOI_REGEX_PATTERN constant and schema DOI field validation.
Per DOI Handbook: https://www.doi.org/doi_handbook/2_Numbering.html
Per ISO 26324:2012 (DOI System)

Requirements:
- Registrant code MUST be at least 4 digits
- Suffix MUST contain at least 1 character
"""

from __future__ import annotations

import re

import pytest

from bioetl.domain.validation import DOI_REGEX_PATTERN


pytestmark = pytest.mark.unit


class TestDoiRegexPattern:
    """Tests for DOI_REGEX_PATTERN constant."""

    @pytest.mark.parametrize(
        "doi,is_valid",
        [
            # Valid DOIs - minimum registrant (4 digits)
            ("10.1000/xyz", True),
            ("10.1234/a", True),
            ("10.9999/suffix", True),
            # Valid DOIs - longer registrant codes
            ("10.12345/some.suffix-123", True),
            ("10.1234567890/a", True),
            ("10.123456/very-long-suffix.with/many/parts", True),
            # Valid DOIs - various suffix formats
            ("10.1038/nature12373", True),
            ("10.1016/j.cell.2024.01.001", True),
            ("10.1021/acs.jmedchem.9b00359", True),
            ("10.1371/journal.pone.0123456", True),
            ("10.1007/s12274-020-2755-z", True),
            # Invalid DOIs - registrant < 4 digits
            ("10.1/xyz", False),
            ("10.12/xyz", False),
            ("10.123/xyz", False),
            # Invalid DOIs - wrong prefix
            ("11.1234/xyz", False),
            ("9.1234/xyz", False),
            ("doi:10.1234/xyz", False),
            ("https://doi.org/10.1234/xyz", False),
            # Invalid DOIs - no suffix
            ("10.1234", False),
            ("10.1234/", False),
            # Invalid DOIs - malformed
            ("10.1234", False),
            ("10./suffix", False),
            ("10/1234/suffix", False),
            ("/10.1234/suffix", False),
        ],
    )
    def test_doi_regex_validation(self, doi: str, is_valid: bool) -> None:
        """Test DOI regex pattern matches DOI Handbook specification.

        Validates that:
        - Prefix is exactly '10.'
        - Registrant code has minimum 4 digits
        - Suffix has at least 1 character
        """
        result = bool(re.match(DOI_REGEX_PATTERN, doi))
        assert result == is_valid, (
            f"DOI '{doi}' should be {'valid' if is_valid else 'invalid'}"
        )

    def test_pattern_is_string(self) -> None:
        """Test DOI_REGEX_PATTERN is exported as string for Pandera str_matches."""
        assert isinstance(DOI_REGEX_PATTERN, str)
        assert DOI_REGEX_PATTERN.startswith("^")
        assert DOI_REGEX_PATTERN.endswith("$")

    def test_pattern_components(self) -> None:
        """Test DOI regex pattern has correct components."""
        # Pattern should be: ^10\.\d{4,}/\S+$
        assert "10\\." in DOI_REGEX_PATTERN, "Pattern should start with '10.'"
        assert "\\d{4,}" in DOI_REGEX_PATTERN, (
            "Pattern should require 4+ digit registrant"
        )
        assert "/\\S+" in DOI_REGEX_PATTERN, (
            "Pattern should require non-empty suffix without whitespace"
        )


class TestDoiRegexEdgeCases:
    """Edge case tests for DOI validation."""

    @pytest.mark.parametrize(
        "registrant_length",
        [1, 2, 3],
    )
    def test_doi_regex_edge_cases__registrant_rejected__bd44fbc9(
        self, registrant_length: int
    ) -> None:
        """Test that registrant codes with < 4 digits are rejected."""
        registrant = "1" * registrant_length
        doi = f"10.{registrant}/suffix"
        assert not re.match(DOI_REGEX_PATTERN, doi)

    @pytest.mark.parametrize(
        "registrant_length",
        [4, 5, 6, 10, 20],
    )
    def test_doi_regex_edge_cases__registrant_lengths__f2d0f297(
        self, registrant_length: int
    ) -> None:
        """Test that registrant codes with >= 4 digits are accepted."""
        registrant = "1" * registrant_length
        doi = f"10.{registrant}/suffix"
        assert re.match(DOI_REGEX_PATTERN, doi)

    def test_empty_suffix_rejected(self) -> None:
        """Test that empty suffix is rejected."""
        assert not re.match(DOI_REGEX_PATTERN, "10.1234/")
        assert not re.match(DOI_REGEX_PATTERN, "10.12345/")

    def test_suffix_with_special_chars(self) -> None:
        """Test suffix can contain special characters."""
        special_suffixes = [
            "a",
            "abc",
            "abc-def",
            "abc.def",
            "abc/def",
            "abc_def",
            "abc:def",
            "abc(def)",
            "abc[def]",
        ]
        for suffix in special_suffixes:
            doi = f"10.1234/{suffix}"
            assert re.match(DOI_REGEX_PATTERN, doi), (
                f"Suffix '{suffix}' should be valid"
            )


class TestDoiSchemaIntegration:
    """Integration tests verifying DOI_REGEX_PATTERN is correctly imported in schemas."""

    def test_chembl_publication_uses_doi_regex_pattern(self) -> None:
        """Test ChEMBL ChemblPublicationSchema uses DOI_REGEX_PATTERN constant."""
        from bioetl.domain.schemas.chembl import publication

        # Verify the import exists
        assert hasattr(publication, "DOI_REGEX_PATTERN")
        assert publication.DOI_REGEX_PATTERN == DOI_REGEX_PATTERN

    def test_pubmed_publication_uses_doi_regex_pattern(self) -> None:
        """Test PubMed PubMedPublicationSchema uses DOI_REGEX_PATTERN constant."""
        from bioetl.domain.schemas.pubmed import publication

        # Verify the import exists
        assert hasattr(publication, "DOI_REGEX_PATTERN")
        assert publication.DOI_REGEX_PATTERN == DOI_REGEX_PATTERN

    def test_semanticscholar_publication_uses_doi_regex_pattern(self) -> None:
        """Test SemanticScholar PublicationSchema uses DOI_REGEX_PATTERN constant."""
        from bioetl.domain.schemas.semanticscholar import publication

        # Verify the import exists
        assert hasattr(publication, "DOI_REGEX_PATTERN")
        assert publication.DOI_REGEX_PATTERN == DOI_REGEX_PATTERN

    def test_openalex_publication_uses_doi_regex_pattern(self) -> None:
        """Test OpenAlex PublicationSchema uses DOI_REGEX_PATTERN constant."""
        from bioetl.domain.schemas.openalex import publication

        # Verify the import exists
        assert hasattr(publication, "DOI_REGEX_PATTERN")
        assert publication.DOI_REGEX_PATTERN == DOI_REGEX_PATTERN

    def test_crossref_publication_uses_doi_regex_pattern(self) -> None:
        """Test CrossRef PublicationEnrichedSchema uses DOI_REGEX_PATTERN constant."""
        from bioetl.domain.schemas.crossref import publication

        # Verify the import exists
        assert hasattr(publication, "DOI_REGEX_PATTERN")
        assert publication.DOI_REGEX_PATTERN == DOI_REGEX_PATTERN

    def test_crossref_work_uses_doi_regex_pattern(self) -> None:
        """Test CrossRef PublicationSchema (work.py) uses DOI_REGEX_PATTERN constant."""
        from bioetl.domain.schemas.crossref import work

        # Verify the import exists
        assert hasattr(work, "DOI_REGEX_PATTERN")
        assert work.DOI_REGEX_PATTERN == DOI_REGEX_PATTERN

    def test_all_schemas_use_consistent_pattern(self) -> None:
        """Test all schemas use the same DOI pattern value."""
        from bioetl.domain.schemas.chembl import publication as chembl_pub
        from bioetl.domain.schemas.crossref import publication as crossref_pub
        from bioetl.domain.schemas.crossref import work
        from bioetl.domain.schemas.openalex import publication as openalex_pub
        from bioetl.domain.schemas.pubmed import publication as pubmed_pub
        from bioetl.domain.schemas.semanticscholar import publication as s2_pub

        patterns = [
            chembl_pub.DOI_REGEX_PATTERN,
            pubmed_pub.DOI_REGEX_PATTERN,
            s2_pub.DOI_REGEX_PATTERN,
            openalex_pub.DOI_REGEX_PATTERN,
            crossref_pub.DOI_REGEX_PATTERN,
            work.DOI_REGEX_PATTERN,
        ]

        # All patterns should be identical
        assert all(p == DOI_REGEX_PATTERN for p in patterns)
