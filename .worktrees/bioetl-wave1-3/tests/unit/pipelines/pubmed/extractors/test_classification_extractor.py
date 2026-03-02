"""Unit tests for ClassificationExtractor."""

from __future__ import annotations

import xml.etree.ElementTree as ET

from bioetl.application.pipelines.pubmed.extractors.classification import (
    ClassificationExtractor,
)


class TestParseKeywords:
    """Tests for parse_keywords method."""

    def test_keywords_extracted(self):
        """Test extracting keywords from KeywordList."""
        xml = """
        <MedlineCitation>
            <KeywordList>
                <Keyword>bioinformatics</Keyword>
                <Keyword>drug discovery</Keyword>
                <Keyword>machine learning</Keyword>
            </KeywordList>
        </MedlineCitation>
        """
        node = ET.fromstring(xml)
        keywords = ClassificationExtractor.parse_keywords(node)
        assert keywords == ["bioinformatics", "drug discovery", "machine learning"]

    def test_single_keyword(self):
        """Test single keyword extraction."""
        xml = """
        <MedlineCitation>
            <KeywordList>
                <Keyword>proteomics</Keyword>
            </KeywordList>
        </MedlineCitation>
        """
        node = ET.fromstring(xml)
        keywords = ClassificationExtractor.parse_keywords(node)
        assert keywords == ["proteomics"]

    def test_empty_keyword_list(self):
        """Test empty KeywordList."""
        xml = """
        <MedlineCitation>
            <KeywordList>
            </KeywordList>
        </MedlineCitation>
        """
        node = ET.fromstring(xml)
        keywords = ClassificationExtractor.parse_keywords(node)
        assert keywords == []

    def test_no_keyword_list(self):
        """Test missing KeywordList element."""
        xml = "<MedlineCitation></MedlineCitation>"
        node = ET.fromstring(xml)
        keywords = ClassificationExtractor.parse_keywords(node)
        assert keywords == []

    def test_none_node_returns_empty(self):
        """Test that None node returns empty list."""
        keywords = ClassificationExtractor.parse_keywords(None)
        assert keywords == []

    def test_keywords_stripped(self):
        """Test that keyword whitespace is stripped."""
        xml = """
        <MedlineCitation>
            <KeywordList>
                <Keyword>  spaced keyword  </Keyword>
            </KeywordList>
        </MedlineCitation>
        """
        node = ET.fromstring(xml)
        keywords = ClassificationExtractor.parse_keywords(node)
        assert keywords == ["spaced keyword"]


class TestParseMeshTerms:
    """Tests for parse_mesh_terms method."""

    def test_mesh_terms_extracted(self):
        """Test extracting MeSH terms from MeshHeadingList."""
        xml = """
        <MedlineCitation>
            <MeshHeadingList>
                <MeshHeading>
                    <DescriptorName>Proteins</DescriptorName>
                </MeshHeading>
                <MeshHeading>
                    <DescriptorName>Drug Discovery</DescriptorName>
                </MeshHeading>
            </MeshHeadingList>
        </MedlineCitation>
        """
        node = ET.fromstring(xml)
        terms = ClassificationExtractor.parse_mesh_terms(node)
        assert terms == ["Proteins", "Drug Discovery"]

    def test_mesh_heading_with_qualifiers(self):
        """Test MeSH heading with qualifiers (only descriptor extracted)."""
        xml = """
        <MedlineCitation>
            <MeshHeadingList>
                <MeshHeading>
                    <DescriptorName>Neoplasms</DescriptorName>
                    <QualifierName>drug therapy</QualifierName>
                    <QualifierName>genetics</QualifierName>
                </MeshHeading>
            </MeshHeadingList>
        </MedlineCitation>
        """
        node = ET.fromstring(xml)
        terms = ClassificationExtractor.parse_mesh_terms(node)
        assert terms == ["Neoplasms"]

    def test_empty_mesh_list(self):
        """Test empty MeshHeadingList."""
        xml = """
        <MedlineCitation>
            <MeshHeadingList>
            </MeshHeadingList>
        </MedlineCitation>
        """
        node = ET.fromstring(xml)
        terms = ClassificationExtractor.parse_mesh_terms(node)
        assert terms == []

    def test_no_mesh_list(self):
        """Test missing MeshHeadingList element."""
        xml = "<MedlineCitation></MedlineCitation>"
        node = ET.fromstring(xml)
        terms = ClassificationExtractor.parse_mesh_terms(node)
        assert terms == []

    def test_none_node_returns_empty(self):
        """Test that None node returns empty list."""
        terms = ClassificationExtractor.parse_mesh_terms(None)
        assert terms == []


class TestParsePublicationTypes:
    """Tests for parse_publication_types method."""

    def test_publication_types_extracted(self):
        """Test extracting publication types."""
        xml = """
        <Article>
            <PublicationTypeList>
                <PublicationType>Journal Article</PublicationType>
                <PublicationType>Research Support, N.I.H.</PublicationType>
            </PublicationTypeList>
        </Article>
        """
        node = ET.fromstring(xml)
        types = ClassificationExtractor.parse_publication_types(node)
        assert types == ["Journal Article", "Research Support, N.I.H."]

    def test_single_publication_type(self):
        """Test single publication type."""
        xml = """
        <Article>
            <PublicationTypeList>
                <PublicationType>Review</PublicationType>
            </PublicationTypeList>
        </Article>
        """
        node = ET.fromstring(xml)
        types = ClassificationExtractor.parse_publication_types(node)
        assert types == ["Review"]

    def test_empty_publication_type_list(self):
        """Test empty PublicationTypeList."""
        xml = """
        <Article>
            <PublicationTypeList>
            </PublicationTypeList>
        </Article>
        """
        node = ET.fromstring(xml)
        types = ClassificationExtractor.parse_publication_types(node)
        assert types == []

    def test_no_publication_type_list(self):
        """Test missing PublicationTypeList element."""
        xml = "<Article></Article>"
        node = ET.fromstring(xml)
        types = ClassificationExtractor.parse_publication_types(node)
        assert types == []

    def test_publication_types_stripped(self):
        """Test that publication type whitespace is stripped."""
        xml = """
        <Article>
            <PublicationTypeList>
                <PublicationType>  Case Reports  </PublicationType>
            </PublicationTypeList>
        </Article>
        """
        node = ET.fromstring(xml)
        types = ClassificationExtractor.parse_publication_types(node)
        assert types == ["Case Reports"]
