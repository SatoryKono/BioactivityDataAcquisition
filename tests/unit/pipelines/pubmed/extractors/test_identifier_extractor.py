"""Unit tests for IdentifierExtractor."""

from __future__ import annotations

import xml.etree.ElementTree as ET

from bioetl.application.pipelines.pubmed.extractors.identifier import IdentifierExtractor


class TestExtractDoi:
    """Tests for extract_doi method."""

    def test_doi_from_elocationid(self):
        """Test extracting DOI from ELocationID."""
        xml = """
        <PubmedArticle>
            <Article>
                <ELocationID EIdType="doi">10.1234/test.2023</ELocationID>
            </Article>
        </PubmedArticle>
        """
        root = ET.fromstring(xml)
        doi = IdentifierExtractor.extract_doi(root)
        assert doi == "10.1234/test.2023"

    def test_doi_from_articleidlist(self):
        """Test extracting DOI from ArticleIdList."""
        xml = """
        <PubmedArticle>
            <Article>
                <Title>Test</Title>
            </Article>
            <ArticleIdList>
                <ArticleId IdType="doi">10.5678/fallback.2023</ArticleId>
            </ArticleIdList>
        </PubmedArticle>
        """
        root = ET.fromstring(xml)
        doi = IdentifierExtractor.extract_doi(root)
        assert doi == "10.5678/fallback.2023"

    def test_elocationid_takes_precedence(self):
        """Test that ELocationID DOI takes precedence over ArticleIdList."""
        xml = """
        <PubmedArticle>
            <Article>
                <ELocationID EIdType="doi">10.1234/primary.2023</ELocationID>
            </Article>
            <ArticleIdList>
                <ArticleId IdType="doi">10.5678/secondary.2023</ArticleId>
            </ArticleIdList>
        </PubmedArticle>
        """
        root = ET.fromstring(xml)
        doi = IdentifierExtractor.extract_doi(root)
        assert doi == "10.1234/primary.2023"

    def test_no_doi_returns_none(self):
        """Test that missing DOI returns None."""
        xml = """
        <PubmedArticle>
            <Article>
                <Title>Test</Title>
            </Article>
        </PubmedArticle>
        """
        root = ET.fromstring(xml)
        doi = IdentifierExtractor.extract_doi(root)
        assert doi is None

    def test_no_article_returns_none(self):
        """Test that missing Article element returns None."""
        xml = "<PubmedArticle></PubmedArticle>"
        root = ET.fromstring(xml)
        doi = IdentifierExtractor.extract_doi(root)
        assert doi is None

    def test_different_eidtype_ignored(self):
        """Test that non-DOI EIdTypes are ignored."""
        xml = """
        <PubmedArticle>
            <Article>
                <ELocationID EIdType="pii">S1234-5678(23)00001-2</ELocationID>
            </Article>
        </PubmedArticle>
        """
        root = ET.fromstring(xml)
        doi = IdentifierExtractor.extract_doi(root)
        assert doi is None

    def test_doi_with_whitespace_stripped(self):
        """Test that DOI whitespace is stripped."""
        xml = """
        <PubmedArticle>
            <Article>
                <ELocationID EIdType="doi">  10.1234/test.2023  </ELocationID>
            </Article>
        </PubmedArticle>
        """
        root = ET.fromstring(xml)
        doi = IdentifierExtractor.extract_doi(root)
        assert doi == "10.1234/test.2023"


class TestExtractPmcId:
    """Tests for extract_pmc_id method."""

    def test_pmc_id_extracted(self):
        """Test extracting PMC ID."""
        xml = """
        <PubmedArticle>
            <ArticleIdList>
                <ArticleId IdType="pmc">PMC123456</ArticleId>
            </ArticleIdList>
        </PubmedArticle>
        """
        root = ET.fromstring(xml)
        pmc_id = IdentifierExtractor.extract_pmc_id(root)
        assert pmc_id == "PMC123456"

    def test_no_pmc_id_returns_none(self):
        """Test that missing PMC ID returns None."""
        xml = """
        <PubmedArticle>
            <ArticleIdList>
                <ArticleId IdType="pubmed">12345</ArticleId>
            </ArticleIdList>
        </PubmedArticle>
        """
        root = ET.fromstring(xml)
        pmc_id = IdentifierExtractor.extract_pmc_id(root)
        assert pmc_id is None

    def test_no_articleidlist_returns_none(self):
        """Test that missing ArticleIdList returns None."""
        xml = "<PubmedArticle></PubmedArticle>"
        root = ET.fromstring(xml)
        pmc_id = IdentifierExtractor.extract_pmc_id(root)
        assert pmc_id is None

    def test_pmc_id_with_whitespace_stripped(self):
        """Test that PMC ID whitespace is stripped."""
        xml = """
        <PubmedArticle>
            <ArticleIdList>
                <ArticleId IdType="pmc">  PMC789012  </ArticleId>
            </ArticleIdList>
        </PubmedArticle>
        """
        root = ET.fromstring(xml)
        pmc_id = IdentifierExtractor.extract_pmc_id(root)
        assert pmc_id == "PMC789012"

    def test_multiple_article_ids(self):
        """Test extracting PMC ID from multiple ArticleIds."""
        xml = """
        <PubmedArticle>
            <ArticleIdList>
                <ArticleId IdType="pubmed">12345</ArticleId>
                <ArticleId IdType="doi">10.1234/test</ArticleId>
                <ArticleId IdType="pmc">PMC999888</ArticleId>
            </ArticleIdList>
        </PubmedArticle>
        """
        root = ET.fromstring(xml)
        pmc_id = IdentifierExtractor.extract_pmc_id(root)
        assert pmc_id == "PMC999888"
