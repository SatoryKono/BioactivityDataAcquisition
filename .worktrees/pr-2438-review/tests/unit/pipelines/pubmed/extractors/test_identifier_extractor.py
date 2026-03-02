"""Unit tests for IdentifierExtractor."""

from __future__ import annotations

import xml.etree.ElementTree as ET

from bioetl.application.pipelines.pubmed.extractors.identifier import (
    IdentifierExtractor,
)


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


class TestExtractPii:
    """Tests for extract_pii method (Publisher Item Identifier)."""

    def test_pii_from_elocationid(self):
        """Test extracting PII from ELocationID."""
        xml = """
        <PubmedArticle>
            <Article>
                <ELocationID EIdType="pii">S1234-5678(23)00001-2</ELocationID>
            </Article>
        </PubmedArticle>
        """
        root = ET.fromstring(xml)
        pii = IdentifierExtractor.extract_pii(root)
        assert pii == "S1234-5678(23)00001-2"

    def test_pii_from_articleidlist(self):
        """Test extracting PII from ArticleIdList."""
        xml = """
        <PubmedArticle>
            <Article><Title>Test</Title></Article>
            <ArticleIdList>
                <ArticleId IdType="pii">S9876-5432(24)00002-3</ArticleId>
            </ArticleIdList>
        </PubmedArticle>
        """
        root = ET.fromstring(xml)
        pii = IdentifierExtractor.extract_pii(root)
        assert pii == "S9876-5432(24)00002-3"

    def test_elocationid_pii_takes_precedence(self):
        """Test that ELocationID PII takes precedence over ArticleIdList."""
        xml = """
        <PubmedArticle>
            <Article>
                <ELocationID EIdType="pii">PRIMARY-PII</ELocationID>
            </Article>
            <ArticleIdList>
                <ArticleId IdType="pii">SECONDARY-PII</ArticleId>
            </ArticleIdList>
        </PubmedArticle>
        """
        root = ET.fromstring(xml)
        pii = IdentifierExtractor.extract_pii(root)
        assert pii == "PRIMARY-PII"

    def test_no_pii_returns_none(self):
        """Test that missing PII returns None."""
        xml = """
        <PubmedArticle>
            <Article><Title>Test</Title></Article>
        </PubmedArticle>
        """
        root = ET.fromstring(xml)
        pii = IdentifierExtractor.extract_pii(root)
        assert pii is None


class TestExtractMid:
    """Tests for extract_mid method (Manuscript ID)."""

    def test_mid_extracted(self):
        """Test extracting MID from ArticleIdList."""
        xml = """
        <PubmedArticle>
            <ArticleIdList>
                <ArticleId IdType="mid">NIHMS123456</ArticleId>
            </ArticleIdList>
        </PubmedArticle>
        """
        root = ET.fromstring(xml)
        mid = IdentifierExtractor.extract_mid(root)
        assert mid == "NIHMS123456"

    def test_no_mid_returns_none(self):
        """Test that missing MID returns None."""
        xml = """
        <PubmedArticle>
            <ArticleIdList>
                <ArticleId IdType="pubmed">12345</ArticleId>
            </ArticleIdList>
        </PubmedArticle>
        """
        root = ET.fromstring(xml)
        mid = IdentifierExtractor.extract_mid(root)
        assert mid is None


class TestExtractPublisherId:
    """Tests for extract_publisher_id method."""

    def test_publisher_id_extracted(self):
        """Test extracting publisher-id from ArticleIdList."""
        xml = """
        <PubmedArticle>
            <ArticleIdList>
                <ArticleId IdType="publisher-id">JCI-12345</ArticleId>
            </ArticleIdList>
        </PubmedArticle>
        """
        root = ET.fromstring(xml)
        pub_id = IdentifierExtractor.extract_publisher_id(root)
        assert pub_id == "JCI-12345"

    def test_no_publisher_id_returns_none(self):
        """Test that missing publisher-id returns None."""
        xml = """
        <PubmedArticle>
            <ArticleIdList>
                <ArticleId IdType="pubmed">12345</ArticleId>
            </ArticleIdList>
        </PubmedArticle>
        """
        root = ET.fromstring(xml)
        pub_id = IdentifierExtractor.extract_publisher_id(root)
        assert pub_id is None


class TestParseAllArticleIds:
    """Tests for parse_all_article_ids method."""

    def test_all_standard_ids_extracted(self):
        """Test extracting all standard identifier types."""
        xml = """
        <PubmedArticle>
            <ArticleIdList>
                <ArticleId IdType="pubmed">12345678</ArticleId>
                <ArticleId IdType="doi">10.1234/test.2024</ArticleId>
                <ArticleId IdType="pmc">PMC9876543</ArticleId>
                <ArticleId IdType="pii">S1234-5678(24)00001-X</ArticleId>
                <ArticleId IdType="mid">NIHMS654321</ArticleId>
                <ArticleId IdType="publisher-id">PUB-2024-001</ArticleId>
            </ArticleIdList>
        </PubmedArticle>
        """
        root = ET.fromstring(xml)
        ids = IdentifierExtractor.parse_all_article_ids(root)

        assert ids["pubmed"] == "12345678"
        assert ids["doi"] == "10.1234/test.2024"
        assert ids["pmc"] == "PMC9876543"
        assert ids["pii"] == "S1234-5678(24)00001-X"
        assert ids["mid"] == "NIHMS654321"
        assert ids["publisher_id"] == "PUB-2024-001"

    def test_unknown_ids_stored_in_other_ids(self):
        """Test that unknown ID types are stored in other_ids."""
        xml = """
        <PubmedArticle>
            <ArticleIdList>
                <ArticleId IdType="pubmed">12345</ArticleId>
                <ArticleId IdType="custom-type">CUSTOM-VALUE</ArticleId>
            </ArticleIdList>
        </PubmedArticle>
        """
        root = ET.fromstring(xml)
        ids = IdentifierExtractor.parse_all_article_ids(root)

        assert ids["pubmed"] == "12345"
        assert ids["other_ids"]["custom-type"] == "CUSTOM-VALUE"

    def test_empty_articleidlist_returns_none_values(self):
        """Test that empty ArticleIdList returns None values."""
        xml = """
        <PubmedArticle>
            <ArticleIdList></ArticleIdList>
        </PubmedArticle>
        """
        root = ET.fromstring(xml)
        ids = IdentifierExtractor.parse_all_article_ids(root)

        assert ids["pubmed"] is None
        assert ids["doi"] is None
        assert ids["pmc"] is None
        assert ids["other_ids"] == {}

    def test_no_articleidlist_returns_none_values(self):
        """Test that missing ArticleIdList returns None values."""
        xml = "<PubmedArticle></PubmedArticle>"
        root = ET.fromstring(xml)
        ids = IdentifierExtractor.parse_all_article_ids(root)

        assert ids["pubmed"] is None
        assert ids["doi"] is None


class TestExtractElocationIds:
    """Tests for extract_elocation_ids method."""

    def test_both_doi_and_pii_extracted(self):
        """Test extracting both DOI and PII from ELocationID elements."""
        xml = """
        <PubmedArticle>
            <Article>
                <ELocationID EIdType="doi">10.1234/test.2024</ELocationID>
                <ELocationID EIdType="pii">S1234-5678(24)00001</ELocationID>
            </Article>
        </PubmedArticle>
        """
        root = ET.fromstring(xml)
        eloc_ids = IdentifierExtractor.extract_elocation_ids(root)

        assert eloc_ids["doi"] == "10.1234/test.2024"
        assert eloc_ids["pii"] == "S1234-5678(24)00001"

    def test_only_doi_present(self):
        """Test when only DOI is present in ELocationID."""
        xml = """
        <PubmedArticle>
            <Article>
                <ELocationID EIdType="doi">10.5678/only.doi</ELocationID>
            </Article>
        </PubmedArticle>
        """
        root = ET.fromstring(xml)
        eloc_ids = IdentifierExtractor.extract_elocation_ids(root)

        assert eloc_ids["doi"] == "10.5678/only.doi"
        assert eloc_ids["pii"] is None

    def test_no_elocationid_returns_none_values(self):
        """Test that missing ELocationID elements return None values."""
        xml = """
        <PubmedArticle>
            <Article><Title>Test</Title></Article>
        </PubmedArticle>
        """
        root = ET.fromstring(xml)
        eloc_ids = IdentifierExtractor.extract_elocation_ids(root)

        assert eloc_ids["doi"] is None
        assert eloc_ids["pii"] is None
