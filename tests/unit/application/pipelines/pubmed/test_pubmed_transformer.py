"""Unit tests for PubMed Publication Transformer.

Tests the PubMedPublicationTransformer which transforms raw PubMed XML
records into Silver-layer format.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from bioetl.application.pipelines.pubmed.transformer import (
    PubMedPublicationTransformer,
)
from bioetl.domain.context import PipelineContext
from bioetl.domain.types import RunType

# Sample PubMed XML for testing
MINIMAL_PUBMED_XML = """<?xml version="1.0"?>
<PubmedArticle>
  <MedlineCitation>
    <PMID>12345678</PMID>
    <Article>
      <ArticleTitle>Test Article Title</ArticleTitle>
    </Article>
  </MedlineCitation>
</PubmedArticle>
"""

FULL_PUBMED_XML = """<?xml version="1.0"?>
<PubmedArticle>
  <MedlineCitation>
    <PMID>98765432</PMID>
    <Article>
      <Journal>
        <ISSN IssnType="Print">1234-5678</ISSN>
        <JournalIssue>
          <Volume>42</Volume>
          <Issue>3</Issue>
          <PubDate>
            <Year>2025</Year>
            <Month>Mar</Month>
            <Day>15</Day>
          </PubDate>
        </JournalIssue>
        <Title>Journal of Test Science</Title>
        <ISOAbbreviation>J Test Sci</ISOAbbreviation>
      </Journal>
      <ArticleTitle>A Comprehensive Study of Unit Testing</ArticleTitle>
      <Pagination>
        <MedlinePgn>123-145</MedlinePgn>
      </Pagination>
      <ELocationID EIdType="doi">10.1234/test.2025.001</ELocationID>
      <Abstract>
        <AbstractText>This is the abstract of the test article.</AbstractText>
      </Abstract>
      <AuthorList>
        <Author>
          <LastName>Smith</LastName>
          <ForeName>John</ForeName>
        </Author>
        <Author>
          <LastName>Doe</LastName>
          <ForeName>Jane</ForeName>
        </Author>
      </AuthorList>
      <Language>eng</Language>
      <PublicationTypeList>
        <PublicationType>Journal Article</PublicationType>
        <PublicationType>Research Support</PublicationType>
      </PublicationTypeList>
      <ArticleDate DateType="Electronic">
        <Year>2025</Year>
        <Month>02</Month>
        <Day>28</Day>
      </ArticleDate>
    </Article>
    <MedlineJournalInfo>
      <Country>United States</Country>
    </MedlineJournalInfo>
    <KeywordList>
      <Keyword>unit testing</Keyword>
      <Keyword>python</Keyword>
    </KeywordList>
    <MeshHeadingList>
      <MeshHeading>
        <DescriptorName>Software Testing</DescriptorName>
      </MeshHeading>
    </MeshHeadingList>
  </MedlineCitation>
  <PubmedData>
    <History>
      <PubMedPubDate PubStatus="received">
        <Year>2024</Year>
        <Month>12</Month>
        <Day>01</Day>
      </PubMedPubDate>
      <PubMedPubDate PubStatus="accepted">
        <Year>2025</Year>
        <Month>01</Month>
        <Day>15</Day>
      </PubMedPubDate>
      <PubMedPubDate PubStatus="revised">
        <Year>2025</Year>
        <Month>01</Month>
        <Day>10</Day>
      </PubMedPubDate>
    </History>
    <ArticleIdList>
      <ArticleId IdType="pubmed">98765432</ArticleId>
      <ArticleId IdType="pmc">PMC1234567</ArticleId>
    </ArticleIdList>
  </PubmedData>
</PubmedArticle>
"""

STRUCTURED_ABSTRACT_XML = """<?xml version="1.0"?>
<PubmedArticle>
  <MedlineCitation>
    <PMID>11111111</PMID>
    <Article>
      <ArticleTitle>Structured Abstract Test</ArticleTitle>
      <Abstract>
        <AbstractText Label="BACKGROUND">Background section text.</AbstractText>
        <AbstractText Label="METHODS">Methods section text.</AbstractText>
        <AbstractText Label="RESULTS">Results section text.</AbstractText>
        <AbstractText Label="CONCLUSION">Conclusion section text.</AbstractText>
      </Abstract>
    </Article>
  </MedlineCitation>
</PubmedArticle>
"""

NO_ARTICLE_XML = """<?xml version="1.0"?>
<PubmedArticle>
  <MedlineCitation>
    <PMID>99999999</PMID>
  </MedlineCitation>
</PubmedArticle>
"""


@pytest.fixture
def mock_context() -> PipelineContext:
    """Create a mock pipeline context."""
    mock_logger = MagicMock()
    mock_logger.bind = MagicMock(return_value=mock_logger)
    mock_logger.warning = MagicMock()
    mock_logger.debug = MagicMock()
    return PipelineContext(
        run_id=uuid4(),
        run_type=RunType.INCREMENTAL,
        logger=mock_logger,
    )


@pytest.mark.unit
class TestPubMedPublicationTransformer:
    """Tests for PubMedPublicationTransformer."""

    @pytest.fixture
    def transformer(self) -> PubMedPublicationTransformer:
        """Create PubMedPublicationTransformer instance."""
        return PubMedPublicationTransformer(provider="pubmed")

    @pytest.mark.asyncio
    async def test_transform_minimal_xml(
        self,
        transformer: PubMedPublicationTransformer,
        mock_context: PipelineContext,
    ) -> None:
        """Test transformation of minimal valid PubMed XML."""
        record: dict[str, Any] = {"_raw_xml": MINIMAL_PUBMED_XML}

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["pmid"] == "12345678"
        assert result["title"] == "Test Article Title"
        assert "entity_id" in result
        assert "content_hash" in result

    @pytest.mark.asyncio
    async def test_transform_full_xml(
        self,
        transformer: PubMedPublicationTransformer,
        mock_context: PipelineContext,
    ) -> None:
        """Test transformation of full PubMed XML with all fields."""
        record: dict[str, Any] = {"_raw_xml": FULL_PUBMED_XML}

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        # Identifiers
        assert result["pmid"] == "98765432"
        assert result["doi"] == "10.1234/test.2025.001"
        assert result["pmc_id"] == "PMC1234567"
        # Title and abstract
        assert result["title"] == "A Comprehensive Study of Unit Testing"
        assert result["abstract"] == "This is the abstract of the test article."
        # Journal info
        assert result["journal"] == "Journal of Test Science"
        assert result["journal_abbrev"] == "J Test Sci"
        assert result["issn"] == "1234-5678"
        assert result["volume"] == "42"
        assert result["issue"] == "3"
        assert result["pages"] == "123-145"
        # Dates
        assert result["pub_date"] == "2025-03-15"
        assert result["year"] == 2025
        assert result["publication_year"] == 2025
        assert result["epub_date"] == "2025-02-28"
        assert result["received_date"] == "2024-12-01"
        assert result["accepted_date"] == "2025-01-15"
        assert result["revised_date"] == "2025-01-10"
        # Classification
        assert result["language"] == "eng"
        assert result["country"] == "United States"
        # Lists
        assert "Journal Article" in result["publication_types"]
        assert "unit testing" in result["keywords"]
        assert "Software Testing" in result["mesh_terms"]
        # Authors (may be hashed)
        assert result["authors"] is not None
        assert len(result["authors"]) == 2

    @pytest.mark.asyncio
    async def test_transform_structured_abstract(
        self,
        transformer: PubMedPublicationTransformer,
        mock_context: PipelineContext,
    ) -> None:
        """Test extraction of structured abstract with labeled sections."""
        record: dict[str, Any] = {"_raw_xml": STRUCTURED_ABSTRACT_XML}

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["pmid"] == "11111111"
        assert "BACKGROUND:" in result["abstract"]
        assert "METHODS:" in result["abstract"]
        assert "RESULTS:" in result["abstract"]
        assert "CONCLUSION:" in result["abstract"]

    @pytest.mark.asyncio
    async def test_transform_missing_raw_xml(
        self,
        transformer: PubMedPublicationTransformer,
        mock_context: PipelineContext,
    ) -> None:
        """Test that transformation returns None when _raw_xml is missing."""
        record: dict[str, Any] = {"pmid": "12345678"}

        result = await transformer.transform(mock_context, record, index=0)

        assert result is None

    @pytest.mark.asyncio
    async def test_transform_empty_raw_xml(
        self,
        transformer: PubMedPublicationTransformer,
        mock_context: PipelineContext,
    ) -> None:
        """Test that transformation returns None for empty _raw_xml."""
        record: dict[str, Any] = {"_raw_xml": ""}

        result = await transformer.transform(mock_context, record, index=0)

        assert result is None

    @pytest.mark.asyncio
    async def test_transform_invalid_xml(
        self,
        transformer: PubMedPublicationTransformer,
        mock_context: PipelineContext,
    ) -> None:
        """Test that transformation returns None for invalid XML."""
        record: dict[str, Any] = {"_raw_xml": "<invalid><xml>"}

        result = await transformer.transform(mock_context, record, index=0)

        assert result is None
        mock_context.logger.warning.assert_called()

    @pytest.mark.asyncio
    async def test_transform_xml_without_pmid(
        self,
        transformer: PubMedPublicationTransformer,
        mock_context: PipelineContext,
    ) -> None:
        """Test that transformation returns None when PMID is missing."""
        xml_without_pmid = """<?xml version="1.0"?>
        <PubmedArticle>
          <MedlineCitation>
            <Article>
              <ArticleTitle>No PMID Article</ArticleTitle>
            </Article>
          </MedlineCitation>
        </PubmedArticle>
        """
        record: dict[str, Any] = {"_raw_xml": xml_without_pmid}

        result = await transformer.transform(mock_context, record, index=0)

        assert result is None

    @pytest.mark.asyncio
    async def test_transform_no_article_element(
        self,
        transformer: PubMedPublicationTransformer,
        mock_context: PipelineContext,
    ) -> None:
        """Test transformation when Article element is missing."""
        record: dict[str, Any] = {"_raw_xml": NO_ARTICLE_XML}

        result = await transformer.transform(mock_context, record, index=0)

        # Should return minimal record with just pmid
        assert result is not None
        assert result["pmid"] == "99999999"

    @pytest.mark.asyncio
    async def test_entity_id_format(
        self,
        transformer: PubMedPublicationTransformer,
        mock_context: PipelineContext,
    ) -> None:
        """Test that entity_id follows the expected format."""
        record: dict[str, Any] = {"_raw_xml": MINIMAL_PUBMED_XML}

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        # entity_id should contain pmid
        assert "12345678" in result["entity_id"]

    @pytest.mark.asyncio
    async def test_content_hash_determinism(
        self,
        transformer: PubMedPublicationTransformer,
        mock_context: PipelineContext,
    ) -> None:
        """Test that content_hash is deterministic for same input."""
        record: dict[str, Any] = {"_raw_xml": FULL_PUBMED_XML}

        result1 = await transformer.transform(mock_context, record, index=0)
        result2 = await transformer.transform(mock_context, record, index=0)

        assert result1 is not None
        assert result2 is not None
        assert result1["content_hash"] == result2["content_hash"]

    @pytest.mark.asyncio
    async def test_lineage_metadata_present(
        self,
        transformer: PubMedPublicationTransformer,
        mock_context: PipelineContext,
    ) -> None:
        """Test that lineage metadata fields are present."""
        record: dict[str, Any] = {"_raw_xml": MINIMAL_PUBMED_XML}

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert "_run_id" in result
        assert "_run_type" in result
        assert "_ingestion_ts" in result
        assert "_index" in result
        assert result["_index"] == 0

    @pytest.mark.asyncio
    async def test_index_propagation(
        self,
        transformer: PubMedPublicationTransformer,
        mock_context: PipelineContext,
    ) -> None:
        """Test that index is correctly propagated to result."""
        record: dict[str, Any] = {"_raw_xml": MINIMAL_PUBMED_XML}

        result = await transformer.transform(mock_context, record, index=42)

        assert result is not None
        assert result["_index"] == 42


@pytest.mark.unit
class TestPubMedTransformerJournalExtraction:
    """Tests for journal data extraction."""

    @pytest.fixture
    def transformer(self) -> PubMedPublicationTransformer:
        """Create PubMedPublicationTransformer instance."""
        return PubMedPublicationTransformer(provider="pubmed")

    @pytest.mark.asyncio
    async def test_missing_journal_element(
        self,
        transformer: PubMedPublicationTransformer,
        mock_context: PipelineContext,
    ) -> None:
        """Test extraction when Journal element is missing."""
        xml = """<?xml version="1.0"?>
        <PubmedArticle>
          <MedlineCitation>
            <PMID>22222222</PMID>
            <Article>
              <ArticleTitle>Article Without Journal</ArticleTitle>
            </Article>
          </MedlineCitation>
        </PubmedArticle>
        """
        record: dict[str, Any] = {"_raw_xml": xml}

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["journal"] is None
        assert result["journal_abbrev"] is None
        assert result["issn"] is None
        assert result["volume"] is None
        assert result["issue"] is None

    @pytest.mark.asyncio
    async def test_partial_journal_data(
        self,
        transformer: PubMedPublicationTransformer,
        mock_context: PipelineContext,
    ) -> None:
        """Test extraction with partial journal information."""
        xml = """<?xml version="1.0"?>
        <PubmedArticle>
          <MedlineCitation>
            <PMID>33333333</PMID>
            <Article>
              <Journal>
                <Title>Partial Journal</Title>
              </Journal>
              <ArticleTitle>Partial Journal Article</ArticleTitle>
            </Article>
          </MedlineCitation>
        </PubmedArticle>
        """
        record: dict[str, Any] = {"_raw_xml": xml}

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["journal"] == "Partial Journal"
        assert result["journal_abbrev"] is None
        assert result["volume"] is None


@pytest.mark.unit
class TestPubMedTransformerDateExtraction:
    """Tests for date data extraction."""

    @pytest.fixture
    def transformer(self) -> PubMedPublicationTransformer:
        """Create PubMedPublicationTransformer instance."""
        return PubMedPublicationTransformer(provider="pubmed")

    @pytest.mark.asyncio
    async def test_year_only_date(
        self,
        transformer: PubMedPublicationTransformer,
        mock_context: PipelineContext,
    ) -> None:
        """Test extraction when only year is available."""
        xml = """<?xml version="1.0"?>
        <PubmedArticle>
          <MedlineCitation>
            <PMID>44444444</PMID>
            <Article>
              <Journal>
                <JournalIssue>
                  <PubDate>
                    <Year>2024</Year>
                  </PubDate>
                </JournalIssue>
              </Journal>
              <ArticleTitle>Year Only Article</ArticleTitle>
            </Article>
          </MedlineCitation>
        </PubmedArticle>
        """
        record: dict[str, Any] = {"_raw_xml": xml}

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["pub_date"] == "2024"
        assert result["year"] == 2024

    @pytest.mark.asyncio
    async def test_year_month_date(
        self,
        transformer: PubMedPublicationTransformer,
        mock_context: PipelineContext,
    ) -> None:
        """Test extraction when year and month are available."""
        xml = """<?xml version="1.0"?>
        <PubmedArticle>
          <MedlineCitation>
            <PMID>55555555</PMID>
            <Article>
              <Journal>
                <JournalIssue>
                  <PubDate>
                    <Year>2024</Year>
                    <Month>Dec</Month>
                  </PubDate>
                </JournalIssue>
              </Journal>
              <ArticleTitle>Year-Month Article</ArticleTitle>
            </Article>
          </MedlineCitation>
        </PubmedArticle>
        """
        record: dict[str, Any] = {"_raw_xml": xml}

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["pub_date"] == "2024-12"
        assert result["year"] == 2024

    @pytest.mark.asyncio
    async def test_missing_history_dates(
        self,
        transformer: PubMedPublicationTransformer,
        mock_context: PipelineContext,
    ) -> None:
        """Test that missing history dates return None."""
        record: dict[str, Any] = {"_raw_xml": MINIMAL_PUBMED_XML}

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["received_date"] is None
        assert result["accepted_date"] is None
        assert result["revised_date"] is None


@pytest.mark.unit
class TestPubMedTransformerIdentifierExtraction:
    """Tests for identifier extraction."""

    @pytest.fixture
    def transformer(self) -> PubMedPublicationTransformer:
        """Create PubMedPublicationTransformer instance."""
        return PubMedPublicationTransformer(provider="pubmed")

    @pytest.mark.asyncio
    async def test_doi_from_elocation(
        self,
        transformer: PubMedPublicationTransformer,
        mock_context: PipelineContext,
    ) -> None:
        """Test DOI extraction from ELocationID element."""
        xml = """<?xml version="1.0"?>
        <PubmedArticle>
          <MedlineCitation>
            <PMID>66666666</PMID>
            <Article>
              <ArticleTitle>ELocationID DOI Test</ArticleTitle>
              <ELocationID EIdType="doi">10.1000/eloc.test</ELocationID>
            </Article>
          </MedlineCitation>
        </PubmedArticle>
        """
        record: dict[str, Any] = {"_raw_xml": xml}

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["doi"] == "10.1000/eloc.test"

    @pytest.mark.asyncio
    async def test_doi_from_article_id_list(
        self,
        transformer: PubMedPublicationTransformer,
        mock_context: PipelineContext,
    ) -> None:
        """Test DOI extraction from ArticleIdList fallback."""
        xml = """<?xml version="1.0"?>
        <PubmedArticle>
          <MedlineCitation>
            <PMID>77777777</PMID>
            <Article>
              <ArticleTitle>ArticleIdList DOI Test</ArticleTitle>
            </Article>
          </MedlineCitation>
          <PubmedData>
            <ArticleIdList>
              <ArticleId IdType="doi">10.1000/artid.test</ArticleId>
            </ArticleIdList>
          </PubmedData>
        </PubmedArticle>
        """
        record: dict[str, Any] = {"_raw_xml": xml}

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["doi"] == "10.1000/artid.test"

    @pytest.mark.asyncio
    async def test_no_doi_available(
        self,
        transformer: PubMedPublicationTransformer,
        mock_context: PipelineContext,
    ) -> None:
        """Test handling when DOI is not available."""
        record: dict[str, Any] = {"_raw_xml": MINIMAL_PUBMED_XML}

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["doi"] is None


@pytest.mark.unit
class TestPubMedTransformerClassificationExtraction:
    """Tests for classification data extraction (keywords, MeSH, pub types)."""

    @pytest.fixture
    def transformer(self) -> PubMedPublicationTransformer:
        """Create PubMedPublicationTransformer instance."""
        return PubMedPublicationTransformer(provider="pubmed")

    @pytest.mark.asyncio
    async def test_empty_classification_lists(
        self,
        transformer: PubMedPublicationTransformer,
        mock_context: PipelineContext,
    ) -> None:
        """Test handling when classification lists are empty."""
        record: dict[str, Any] = {"_raw_xml": MINIMAL_PUBMED_XML}

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        # Empty lists or None depending on implementation
        assert result["publication_types"] is None or result["publication_types"] == []
        assert result["keywords"] is None or result["keywords"] == []
        assert result["mesh_terms"] is None or result["mesh_terms"] == []

    @pytest.mark.asyncio
    async def test_multiple_keywords(
        self,
        transformer: PubMedPublicationTransformer,
        mock_context: PipelineContext,
    ) -> None:
        """Test extraction of multiple keywords."""
        xml = """<?xml version="1.0"?>
        <PubmedArticle>
          <MedlineCitation>
            <PMID>88888888</PMID>
            <Article>
              <ArticleTitle>Multiple Keywords Test</ArticleTitle>
            </Article>
            <KeywordList>
              <Keyword>keyword1</Keyword>
              <Keyword>keyword2</Keyword>
              <Keyword>keyword3</Keyword>
            </KeywordList>
          </MedlineCitation>
        </PubmedArticle>
        """
        record: dict[str, Any] = {"_raw_xml": xml}

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert len(result["keywords"]) == 3
        assert "keyword1" in result["keywords"]
        assert "keyword2" in result["keywords"]
        assert "keyword3" in result["keywords"]
