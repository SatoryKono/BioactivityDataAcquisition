"""Unit tests for PubMed AuthorExtractor.

Tests extraction of author names and affiliations.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET

from bioetl.application.pipelines.pubmed.extractors import AuthorExtractor


class TestExtract:
    """Tests for extract method."""

    def test_extract_with_affiliations(self) -> None:
        """Should extract affiliations in RawAuthor."""
        xml = """
        <Article>
            <AuthorList>
                <Author>
                    <LastName>Smith</LastName>
                    <AffiliationInfo>
                        <Affiliation>University of A</Affiliation>
                    </AffiliationInfo>
                </Author>
            </AuthorList>
        </Article>
        """
        article = ET.fromstring(xml)
        extractor = AuthorExtractor()
        result = extractor.extract(article)
        assert result is not None
        assert len(result) == 1
        assert result[0]["affiliations"] == ["University of A"]


class TestParseAffiliations:
    """Tests for parse_affiliations method."""

    def test_parse_affiliations_basic(self) -> None:
        """Should extract and deduplicate affiliations from authors."""
        xml = """
        <Article>
            <AuthorList>
                <Author>
                    <LastName>Smith</LastName>
                    <ForeName>John</ForeName>
                    <AffiliationInfo>
                        <Affiliation>University of A, Department X</Affiliation>
                    </AffiliationInfo>
                </Author>
                <Author>
                    <LastName>Doe</LastName>
                    <ForeName>Jane</ForeName>
                    <AffiliationInfo>
                        <Affiliation>University of B, Department Y</Affiliation>
                    </AffiliationInfo>
                     <AffiliationInfo>
                        <Affiliation>Institute C</Affiliation>
                    </AffiliationInfo>
                </Author>
                <Author>
                    <LastName>Bar</LastName>
                    <ForeName>Foo</ForeName>
                    <AffiliationInfo>
                        <Affiliation>University of A, Department X</Affiliation>
                    </AffiliationInfo>
                </Author>
            </AuthorList>
        </Article>
        """
        article = ET.fromstring(xml)
        result = AuthorExtractor.parse_affiliations(article)
        expected = [
            "Institute C",
            "University of A, Department X",
            "University of B, Department Y",
        ]
        assert result == expected

    def test_parse_affiliations_no_affiliations(self) -> None:
        """Should return empty list when no affiliations are present."""
        xml = """
        <Article>
            <AuthorList>
                <Author>
                    <LastName>Smith</LastName>
                    <ForeName>John</ForeName>
                </Author>
            </AuthorList>
        </Article>
        """
        article = ET.fromstring(xml)
        result = AuthorExtractor.parse_affiliations(article)
        assert result == []

    def test_parse_affiliations_no_authors(self) -> None:
        """Should return empty list when no authors are present."""
        xml = "<Article><AuthorList></AuthorList></Article>"
        article = ET.fromstring(xml)
        result = AuthorExtractor.parse_affiliations(article)
        assert result == []

    def test_parse_affiliations_none_input(self) -> None:
        """Should return empty list for None input."""
        result = AuthorExtractor.parse_affiliations(None)
        assert result == []

    def test_parse_affiliations_empty_text(self) -> None:
        """Should skip empty affiliation text."""
        xml = """
        <Article>
            <AuthorList>
                <Author>
                    <AffiliationInfo>
                        <Affiliation>   </Affiliation>
                    </AffiliationInfo>
                </Author>
            </AuthorList>
        </Article>
        """
        article = ET.fromstring(xml)
        result = AuthorExtractor.parse_affiliations(article)
        assert result == []
