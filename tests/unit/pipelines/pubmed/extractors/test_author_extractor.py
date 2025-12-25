"""Unit tests for AuthorExtractor."""

from __future__ import annotations

import xml.etree.ElementTree as ET

from bioetl.application.pipelines.pubmed.extractors.author import AuthorExtractor


class TestParseAuthors:
    """Tests for parse_authors method."""

    def test_author_with_initials(self):
        """Test author with LastName and Initials."""
        xml = """
        <Article>
            <AuthorList>
                <Author>
                    <LastName>Doe</LastName>
                    <Initials>J</Initials>
                </Author>
            </AuthorList>
        </Article>
        """
        node = ET.fromstring(xml)
        authors = AuthorExtractor.parse_authors(node)
        assert authors == ["Doe, J"]

    def test_author_with_forename(self):
        """Test author with LastName and ForeName (no Initials)."""
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
        node = ET.fromstring(xml)
        authors = AuthorExtractor.parse_authors(node)
        assert authors == ["Smith, John"]

    def test_author_lastname_only(self):
        """Test author with only LastName."""
        xml = """
        <Article>
            <AuthorList>
                <Author>
                    <LastName>Johnson</LastName>
                </Author>
            </AuthorList>
        </Article>
        """
        node = ET.fromstring(xml)
        authors = AuthorExtractor.parse_authors(node)
        assert authors == ["Johnson"]

    def test_collective_author(self):
        """Test collective/group author."""
        xml = """
        <Article>
            <AuthorList>
                <Author>
                    <CollectiveName>WHO Working Group</CollectiveName>
                </Author>
            </AuthorList>
        </Article>
        """
        node = ET.fromstring(xml)
        authors = AuthorExtractor.parse_authors(node)
        assert authors == ["WHO Working Group"]

    def test_multiple_authors(self):
        """Test multiple authors."""
        xml = """
        <Article>
            <AuthorList>
                <Author>
                    <LastName>Doe</LastName>
                    <Initials>J</Initials>
                </Author>
                <Author>
                    <LastName>Smith</LastName>
                    <Initials>AB</Initials>
                </Author>
                <Author>
                    <LastName>Johnson</LastName>
                    <ForeName>Mary</ForeName>
                </Author>
            </AuthorList>
        </Article>
        """
        node = ET.fromstring(xml)
        authors = AuthorExtractor.parse_authors(node)
        assert authors == ["Doe, J", "Smith, AB", "Johnson, Mary"]

    def test_mixed_individual_and_collective(self):
        """Test mix of individual and collective authors."""
        xml = """
        <Article>
            <AuthorList>
                <Author>
                    <LastName>Doe</LastName>
                    <Initials>J</Initials>
                </Author>
                <Author>
                    <CollectiveName>Research Consortium</CollectiveName>
                </Author>
            </AuthorList>
        </Article>
        """
        node = ET.fromstring(xml)
        authors = AuthorExtractor.parse_authors(node)
        assert authors == ["Doe, J", "Research Consortium"]

    def test_empty_author_list(self):
        """Test empty AuthorList."""
        xml = """
        <Article>
            <AuthorList>
            </AuthorList>
        </Article>
        """
        node = ET.fromstring(xml)
        authors = AuthorExtractor.parse_authors(node)
        assert authors == []

    def test_no_author_list(self):
        """Test article without AuthorList element."""
        xml = "<Article></Article>"
        node = ET.fromstring(xml)
        authors = AuthorExtractor.parse_authors(node)
        assert authors == []

    def test_author_with_both_initials_and_forename(self):
        """Test author with both Initials and ForeName (Initials takes precedence)."""
        xml = """
        <Article>
            <AuthorList>
                <Author>
                    <LastName>Doe</LastName>
                    <Initials>JM</Initials>
                    <ForeName>John Michael</ForeName>
                </Author>
            </AuthorList>
        </Article>
        """
        node = ET.fromstring(xml)
        authors = AuthorExtractor.parse_authors(node)
        assert authors == ["Doe, JM"]

    def test_author_with_empty_elements(self):
        """Test author with empty text elements."""
        xml = """
        <Article>
            <AuthorList>
                <Author>
                    <LastName></LastName>
                    <Initials></Initials>
                </Author>
            </AuthorList>
        </Article>
        """
        node = ET.fromstring(xml)
        authors = AuthorExtractor.parse_authors(node)
        assert authors == []
