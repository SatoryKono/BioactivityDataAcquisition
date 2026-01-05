# ruff: noqa: RUF001
"""Unit tests for PubMedPublicationTransformer.

Comprehensive tests for XML parsing and field extraction edge cases.
Unicode characters in tests are intentional for testing international content handling.
"""

from __future__ import annotations

from typing import cast
from unittest.mock import MagicMock
from uuid import UUID

import pytest

from bioetl.application.pipelines.pubmed.transformer import PubMedPublicationTransformer
from bioetl.domain.context import PipelineContext
from bioetl.domain.types import BronzeRecord, RunType


@pytest.fixture
def transformer() -> PubMedPublicationTransformer:
    """Create a PubMedPublicationTransformer instance."""
    return PubMedPublicationTransformer(provider="pubmed")


@pytest.fixture
def mock_logger() -> MagicMock:
    """Create a mock logger."""
    logger = MagicMock()
    logger.bind.return_value = logger
    return logger


@pytest.fixture
def pipeline_context(mock_logger) -> PipelineContext:
    """Create a pipeline context for testing."""
    return PipelineContext(
        run_id=UUID("00000000-0000-0000-0000-000000000000"),
        run_type=RunType.INCREMENTAL,
        logger=mock_logger,
    )


class TestTransformImplBasicCases:
    """Tests for basic transformation cases."""

    @pytest.mark.asyncio
    async def test_transform_valid_record(self, transformer, pipeline_context):
        """Test transformation of a valid PubMed XML record."""
        xml_content = """
        <PubmedArticle>
            <MedlineCitation>
                <PMID>12345</PMID>
                <Article>
                    <ArticleTitle>Test Title</ArticleTitle>
                    <Abstract>
                        <AbstractText>Test Abstract</AbstractText>
                    </Abstract>
                </Article>
            </MedlineCitation>
        </PubmedArticle>
        """

        bronze_record: BronzeRecord = cast(
            "BronzeRecord",
            {"pmid": "12345", "_raw_xml": xml_content, "source_batch_id": "test"},
        )

        result = await transformer._transform_impl(pipeline_context, bronze_record, 0)

        assert result is not None
        assert result["pmid"] == "12345"
        assert result["title"] == "Test Title"
        assert result["abstract"] == "Test Abstract"

    @pytest.mark.asyncio
    async def test_transform_missing_raw_xml(self, transformer, pipeline_context):
        """Test that missing _raw_xml returns None."""
        bronze_record: BronzeRecord = cast(
            "BronzeRecord",
            {"pmid": "12345", "source_batch_id": "test"},
        )

        result = await transformer._transform_impl(pipeline_context, bronze_record, 0)

        assert result is None

    @pytest.mark.asyncio
    async def test_transform_empty_raw_xml(self, transformer, pipeline_context):
        """Test that empty _raw_xml returns None."""
        bronze_record: BronzeRecord = cast(
            "BronzeRecord",
            {"pmid": "12345", "_raw_xml": "", "source_batch_id": "test"},
        )

        result = await transformer._transform_impl(pipeline_context, bronze_record, 0)

        assert result is None

    @pytest.mark.asyncio
    async def test_transform_non_string_raw_xml(self, transformer, pipeline_context):
        """Test that non-string _raw_xml returns None."""
        bronze_record: BronzeRecord = cast(
            "BronzeRecord",
            {"pmid": "12345", "_raw_xml": 12345, "source_batch_id": "test"},
        )

        result = await transformer._transform_impl(pipeline_context, bronze_record, 0)

        assert result is None

    @pytest.mark.asyncio
    async def test_transform_invalid_xml(self, transformer, pipeline_context):
        """Test that invalid XML returns None and logs warning."""
        bronze_record: BronzeRecord = cast(
            "BronzeRecord",
            {"pmid": "12345", "_raw_xml": "<Invalid>XML", "source_batch_id": "test"},
        )

        result = await transformer._transform_impl(pipeline_context, bronze_record, 0)

        assert result is None
        pipeline_context.logger.warning.assert_called_once()
        args, kwargs = pipeline_context.logger.warning.call_args
        assert args[0] == "XML_parse_error"
        assert kwargs["pmid"] == "12345"

    @pytest.mark.asyncio
    async def test_transform_missing_pmid(self, transformer, pipeline_context):
        """Test that missing PMID in XML returns None."""
        xml_content = """
        <PubmedArticle>
            <MedlineCitation>
                <Article>
                    <ArticleTitle>Test Title</ArticleTitle>
                </Article>
            </MedlineCitation>
        </PubmedArticle>
        """

        bronze_record: BronzeRecord = cast(
            "BronzeRecord",
            {"_raw_xml": xml_content, "source_batch_id": "test"},
        )

        result = await transformer._transform_impl(pipeline_context, bronze_record, 0)

        assert result is None


class TestTransformImplMissingArticle:
    """Tests for records with missing Article element."""

    @pytest.mark.asyncio
    async def test_transform_missing_article_element(
        self, transformer, pipeline_context
    ):
        """Test that missing Article element returns minimal record."""
        xml_content = """
        <PubmedArticle>
            <MedlineCitation>
                <PMID>12345</PMID>
            </MedlineCitation>
        </PubmedArticle>
        """

        bronze_record: BronzeRecord = cast(
            "BronzeRecord",
            {"pmid": "12345", "_raw_xml": xml_content, "source_batch_id": "test"},
        )

        result = await transformer._transform_impl(pipeline_context, bronze_record, 0)

        assert result is not None
        assert result["pmid"] == "12345"
        # All other fields should be None or empty
        assert result.get("title") is None
        assert result.get("abstract") is None


class TestExtractJournalData:
    """Tests for journal data extraction."""

    def test_extract_journal_data_complete(self, transformer):
        """Test extraction of complete journal data."""
        import xml.etree.ElementTree as ET

        xml = """
        <Article>
            <Journal>
                <Title>Nature Medicine</Title>
                <ISOAbbreviation>Nat Med</ISOAbbreviation>
                <ISSN>1234-5678</ISSN>
                <JournalIssue>
                    <Volume>25</Volume>
                    <Issue>10</Issue>
                </JournalIssue>
            </Journal>
            <Pagination>
                <MedlinePgn>100-110</MedlinePgn>
            </Pagination>
        </Article>
        """
        article = ET.fromstring(xml)

        result = transformer._extract_journal_data(article)

        assert result["journal"] == "Nature Medicine"
        assert result["journal_abbrev"] == "Nat Med"
        assert result["issn"] == "1234-5678"
        assert result["volume"] == "25"
        assert result["issue"] == "10"
        assert result["pages"] == "100-110"

    def test_extract_journal_data_missing_journal(self, transformer):
        """Test extraction when Journal element is missing."""
        import xml.etree.ElementTree as ET

        xml = """
        <Article>
            <Pagination>
                <MedlinePgn>100-110</MedlinePgn>
            </Pagination>
        </Article>
        """
        article = ET.fromstring(xml)

        result = transformer._extract_journal_data(article)

        assert result["journal"] is None
        assert result["journal_abbrev"] is None
        assert result["issn"] is None
        assert result["volume"] is None
        assert result["issue"] is None
        assert result["pages"] == "100-110"

    def test_extract_journal_data_partial(self, transformer):
        """Test extraction with partial journal data."""
        import xml.etree.ElementTree as ET

        xml = """
        <Article>
            <Journal>
                <Title>Test Journal</Title>
            </Journal>
        </Article>
        """
        article = ET.fromstring(xml)

        result = transformer._extract_journal_data(article)

        assert result["journal"] == "Test Journal"
        assert result["journal_abbrev"] is None
        assert result["issn"] is None
        assert result["volume"] is None
        assert result["issue"] is None
        assert result["pages"] is None

    def test_extract_journal_data_missing_journal_issue(self, transformer):
        """Test extraction when JournalIssue is missing."""
        import xml.etree.ElementTree as ET

        xml = """
        <Article>
            <Journal>
                <Title>Test Journal</Title>
                <ISOAbbreviation>Test J</ISOAbbreviation>
            </Journal>
        </Article>
        """
        article = ET.fromstring(xml)

        result = transformer._extract_journal_data(article)

        assert result["journal"] == "Test Journal"
        assert result["journal_abbrev"] == "Test J"
        assert result["volume"] is None
        assert result["issue"] is None


class TestExtractDateData:
    """Tests for date data extraction."""

    def test_extract_date_data_complete(self, transformer):
        """Test extraction of complete date data."""
        import xml.etree.ElementTree as ET

        article_xml = """
        <Article>
            <Journal>
                <JournalIssue>
                    <PubDate>
                        <Year>2023</Year>
                        <Month>Mar</Month>
                        <Day>15</Day>
                    </PubDate>
                </JournalIssue>
            </Journal>
            <ArticleDate DateType="Electronic">
                <Year>2023</Year>
                <Month>03</Month>
                <Day>10</Day>
            </ArticleDate>
        </Article>
        """
        pubmed_data_xml = """
        <PubmedData>
            <History>
                <PubMedPubDate PubStatus="received">
                    <Year>2022</Year><Month>12</Month><Day>01</Day>
                </PubMedPubDate>
                <PubMedPubDate PubStatus="accepted">
                    <Year>2023</Year><Month>02</Month><Day>15</Day>
                </PubMedPubDate>
                <PubMedPubDate PubStatus="revised">
                    <Year>2023</Year><Month>01</Month><Day>20</Day>
                </PubMedPubDate>
            </History>
        </PubmedData>
        """
        article = ET.fromstring(article_xml)
        pubmed_data = ET.fromstring(pubmed_data_xml)

        result = transformer._extract_date_data(article, pubmed_data)

        assert result["pub_date"] == "2023-03-15"
        assert result["pub_year"] == 2023
        assert result["publication_year"] == 2023
        assert result["accepted_date"] == "2023-02-15"
        assert result["received_date"] == "2022-12-01"
        assert result["revised_date"] == "2023-01-20"
        assert result["epub_date"] == "2023-03-10"

    def test_extract_date_data_year_only(self, transformer):
        """Test extraction with year-only publication date."""
        import xml.etree.ElementTree as ET

        article_xml = """
        <Article>
            <Journal>
                <JournalIssue>
                    <PubDate>
                        <Year>2023</Year>
                    </PubDate>
                </JournalIssue>
            </Journal>
        </Article>
        """
        article = ET.fromstring(article_xml)

        result = transformer._extract_date_data(article, None)

        assert result["pub_date"] == "2023"
        assert result["pub_year"] == 2023
        assert result["publication_year"] == 2023
        assert result["accepted_date"] is None
        assert result["received_date"] is None
        assert result["revised_date"] is None
        assert result["epub_date"] is None

    def test_extract_date_data_no_dates(self, transformer):
        """Test extraction with no date data."""
        import xml.etree.ElementTree as ET

        article_xml = "<Article></Article>"
        article = ET.fromstring(article_xml)

        result = transformer._extract_date_data(article, None)

        assert result["pub_date"] is None
        assert result["pub_year"] is None
        assert result["publication_year"] is None
        assert result["accepted_date"] is None
        assert result["received_date"] is None
        assert result["revised_date"] is None
        assert result["epub_date"] is None

    def test_extract_date_data_missing_journal(self, transformer):
        """Test extraction when Journal element is missing."""
        import xml.etree.ElementTree as ET

        article_xml = """
        <Article>
            <ArticleTitle>Test</ArticleTitle>
        </Article>
        """
        article = ET.fromstring(article_xml)

        result = transformer._extract_date_data(article, None)

        assert result["pub_date"] is None
        assert result["pub_year"] is None


class TestExtractBusinessData:
    """Tests for business data extraction."""

    def test_extract_business_data_complete(self, transformer):
        """Test extraction of complete business data."""
        import xml.etree.ElementTree as ET

        xml = """
        <PubmedArticle>
            <MedlineCitation>
                <PMID>12345</PMID>
                <Article>
                    <ArticleTitle>Complete Test Article</ArticleTitle>
                    <Abstract>
                        <AbstractText>Full abstract text here.</AbstractText>
                    </Abstract>
                    <AuthorList>
                        <Author>
                            <LastName>Doe</LastName>
                            <Initials>J</Initials>
                        </Author>
                        <Author>
                            <LastName>Smith</LastName>
                            <ForeName>Jane</ForeName>
                        </Author>
                    </AuthorList>
                    <Journal>
                        <Title>Test Journal</Title>
                        <ISOAbbreviation>Test J</ISOAbbreviation>
                        <ISSN>1234-5678</ISSN>
                        <JournalIssue>
                            <Volume>10</Volume>
                            <Issue>5</Issue>
                            <PubDate>
                                <Year>2023</Year>
                                <Month>Mar</Month>
                                <Day>15</Day>
                            </PubDate>
                        </JournalIssue>
                    </Journal>
                    <Language>eng</Language>
                    <PublicationTypeList>
                        <PublicationType>Journal Article</PublicationType>
                        <PublicationType>Review</PublicationType>
                    </PublicationTypeList>
                    <ELocationID EIdType="doi">10.1234/test.2023</ELocationID>
                </Article>
                <MedlineJournalInfo>
                    <Country>United States</Country>
                </MedlineJournalInfo>
                <KeywordList>
                    <Keyword>keyword1</Keyword>
                    <Keyword>keyword2</Keyword>
                </KeywordList>
                <MeshHeadingList>
                    <MeshHeading>
                        <DescriptorName>Proteins</DescriptorName>
                    </MeshHeading>
                </MeshHeadingList>
            </MedlineCitation>
            <PubmedData>
                <ArticleIdList>
                    <ArticleId IdType="pmc">PMC123456</ArticleId>
                </ArticleIdList>
            </PubmedData>
        </PubmedArticle>
        """
        root = ET.fromstring(xml)

        result = transformer._extract_business_data(root, "12345")

        assert result["pmid"] == "12345"
        assert result["doi"] == "10.1234/test.2023"
        assert result["title"] == "Complete Test Article"
        assert result["abstract"] == "Full abstract text here."
        assert result["authors"] == ["Doe, J", "Smith, Jane"]
        assert result["journal"] == "Test Journal"
        assert result["journal_abbrev"] == "Test J"
        assert result["issn"] == "1234-5678"
        assert result["volume"] == "10"
        assert result["issue"] == "5"
        assert result["pub_date"] == "2023-03-15"
        assert result["pub_year"] == 2023
        assert result["publication_year"] == 2023
        assert result["publication_types"] == ["Journal Article", "Review"]
        assert result["keywords"] == ["keyword1", "keyword2"]
        assert result["mesh_terms"] == ["Proteins"]
        assert result["language"] == "eng"
        assert result["country"] == "United States"
        assert result["pmc_id"] == "PMC123456"

    def test_extract_business_data_minimal(self, transformer):
        """Test extraction with minimal data (PMID only in article)."""
        import xml.etree.ElementTree as ET

        xml = """
        <PubmedArticle>
            <MedlineCitation>
                <PMID>12345</PMID>
            </MedlineCitation>
        </PubmedArticle>
        """
        root = ET.fromstring(xml)

        result = transformer._extract_business_data(root, "12345")

        assert result["pmid"] == "12345"
        # All other fields should be None/empty

    def test_extract_business_data_missing_article_element(self, transformer):
        """Test extraction when Article element is missing."""
        import xml.etree.ElementTree as ET

        xml = """
        <PubmedArticle>
            <MedlineCitation>
                <PMID>12345</PMID>
            </MedlineCitation>
            <PubmedData>
                <ArticleIdList>
                    <ArticleId IdType="pmc">PMC123456</ArticleId>
                </ArticleIdList>
            </PubmedData>
        </PubmedArticle>
        """
        root = ET.fromstring(xml)

        result = transformer._extract_business_data(root, "12345")

        # When Article is missing, only pmid is returned
        assert result["pmid"] == "12345"
        # The function returns early with just pmid when article is None
        assert len(result) == 1


class TestTransformImplCompleteRecord:
    """Tests for complete record transformation with all fields."""

    @pytest.mark.asyncio
    async def test_transform_complete_record_with_metadata(
        self, transformer, pipeline_context
    ):
        """Test that Silver record includes ingestion metadata."""
        xml_content = """
        <PubmedArticle>
            <MedlineCitation>
                <PMID>99999</PMID>
                <Article>
                    <ArticleTitle>Metadata Test</ArticleTitle>
                </Article>
            </MedlineCitation>
        </PubmedArticle>
        """

        bronze_record: BronzeRecord = cast(
            "BronzeRecord",
            {"pmid": "99999", "_raw_xml": xml_content, "source_batch_id": "test"},
        )

        result = await transformer._transform_impl(pipeline_context, bronze_record, 0)

        assert result is not None
        assert "_ingestion_ts" in result
        assert "_run_id" in result
        assert "_run_type" in result
        assert "entity_id" in result
        assert "content_hash" in result


class TestTransformImplStructuredAbstract:
    """Tests for structured abstract handling."""

    @pytest.mark.asyncio
    async def test_transform_structured_abstract(self, transformer, pipeline_context):
        """Test transformation of record with structured abstract."""
        xml_content = """
        <PubmedArticle>
            <MedlineCitation>
                <PMID>12345</PMID>
                <Article>
                    <ArticleTitle>Structured Abstract Test</ArticleTitle>
                    <Abstract>
                        <AbstractText Label="BACKGROUND">Background text.</AbstractText>
                        <AbstractText Label="METHODS">Methods text.</AbstractText>
                        <AbstractText Label="RESULTS">Results text.</AbstractText>
                        <AbstractText Label="CONCLUSION">Conclusion text.</AbstractText>
                    </Abstract>
                </Article>
            </MedlineCitation>
        </PubmedArticle>
        """

        bronze_record: BronzeRecord = cast(
            "BronzeRecord",
            {"pmid": "12345", "_raw_xml": xml_content, "source_batch_id": "test"},
        )

        result = await transformer._transform_impl(pipeline_context, bronze_record, 0)

        assert result is not None
        expected_abstract = (
            "BACKGROUND: Background text. "
            "METHODS: Methods text. "
            "RESULTS: Results text. "
            "CONCLUSION: Conclusion text."
        )
        assert result["abstract"] == expected_abstract


class TestTransformImplCollectiveAuthors:
    """Tests for collective author handling."""

    @pytest.mark.asyncio
    async def test_transform_collective_author(self, transformer, pipeline_context):
        """Test transformation of record with collective author."""
        xml_content = """
        <PubmedArticle>
            <MedlineCitation>
                <PMID>12345</PMID>
                <Article>
                    <ArticleTitle>Collective Author Test</ArticleTitle>
                    <AuthorList>
                        <Author>
                            <LastName>Doe</LastName>
                            <Initials>J</Initials>
                        </Author>
                        <Author>
                            <CollectiveName>WHO Collaborative Group</CollectiveName>
                        </Author>
                    </AuthorList>
                </Article>
            </MedlineCitation>
        </PubmedArticle>
        """

        bronze_record: BronzeRecord = cast(
            "BronzeRecord",
            {"pmid": "12345", "_raw_xml": xml_content, "source_batch_id": "test"},
        )

        result = await transformer._transform_impl(pipeline_context, bronze_record, 0)

        assert result is not None
        assert result["authors"] == ["Doe, J", "WHO Collaborative Group"]


class TestTransformImplSpecialCharacters:
    """Tests for handling special characters in XML."""

    @pytest.mark.asyncio
    async def test_transform_unicode_characters(self, transformer, pipeline_context):
        """Test transformation of record with unicode characters."""
        xml_content = """
        <PubmedArticle>
            <MedlineCitation>
                <PMID>12345</PMID>
                <Article>
                    <ArticleTitle>Effect of α-tocopherol on β-cells</ArticleTitle>
                    <AuthorList>
                        <Author>
                            <LastName>Müller</LastName>
                            <Initials>H</Initials>
                        </Author>
                        <Author>
                            <LastName>García</LastName>
                            <Initials>M</Initials>
                        </Author>
                    </AuthorList>
                </Article>
            </MedlineCitation>
        </PubmedArticle>
        """

        bronze_record: BronzeRecord = cast(
            "BronzeRecord",
            {"pmid": "12345", "_raw_xml": xml_content, "source_batch_id": "test"},
        )

        result = await transformer._transform_impl(pipeline_context, bronze_record, 0)

        assert result is not None
        assert result["title"] == "Effect of α-tocopherol on β-cells"
        assert result["authors"] == ["Müller, H", "García, M"]


class TestTransformImplXMLEntities:
    """Tests for handling XML entities."""

    @pytest.mark.asyncio
    async def test_transform_xml_entities(self, transformer, pipeline_context):
        """Test transformation of record with XML entities."""
        xml_content = """
        <PubmedArticle>
            <MedlineCitation>
                <PMID>12345</PMID>
                <Article>
                    <ArticleTitle>5' &amp; 3' ends in DNA &lt;structure&gt;</ArticleTitle>
                </Article>
            </MedlineCitation>
        </PubmedArticle>
        """

        bronze_record: BronzeRecord = cast(
            "BronzeRecord",
            {"pmid": "12345", "_raw_xml": xml_content, "source_batch_id": "test"},
        )

        result = await transformer._transform_impl(pipeline_context, bronze_record, 0)

        assert result is not None
        assert result["title"] == "5' & 3' ends in DNA <structure>"


class TestTransformImplMultipleDois:
    """Tests for DOI extraction priority."""

    @pytest.mark.asyncio
    async def test_transform_elocationid_doi_priority(
        self, transformer, pipeline_context
    ):
        """Test that ELocationID DOI takes precedence over ArticleIdList."""
        xml_content = """
        <PubmedArticle>
            <MedlineCitation>
                <PMID>12345</PMID>
                <Article>
                    <ArticleTitle>DOI Priority Test</ArticleTitle>
                    <ELocationID EIdType="doi">10.1234/primary</ELocationID>
                </Article>
            </MedlineCitation>
            <PubmedData>
                <ArticleIdList>
                    <ArticleId IdType="doi">10.5678/secondary</ArticleId>
                </ArticleIdList>
            </PubmedData>
        </PubmedArticle>
        """

        bronze_record: BronzeRecord = cast(
            "BronzeRecord",
            {"pmid": "12345", "_raw_xml": xml_content, "source_batch_id": "test"},
        )

        result = await transformer._transform_impl(pipeline_context, bronze_record, 0)

        assert result is not None
        assert result["doi"] == "10.1234/primary"
