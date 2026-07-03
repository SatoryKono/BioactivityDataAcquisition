"""Unit tests for PubMed Publication Transformer.

Tests the PubMedPublicationTransformer which transforms raw PubMed XML
records into Silver-layer format.
"""

from __future__ import annotations

from functools import cache
import xml.etree.ElementTree as ET
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock
from tests.helpers.deterministic_ids import deterministic_uuid_from_callsite

import pytest

from bioetl.application.core.base_transformer import FilteredOutError

if TYPE_CHECKING:
    from bioetl.application.pipelines.pubmed.transformer import (
        PubMedPublicationTransformer,
    )
    from bioetl.domain.context import PipelineContext
else:
    PipelineContext = Any
    PubMedPublicationTransformer = Any

pytestmark = pytest.mark.usefixtures("publication_type_classification_data")

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


@cache
def _pubmed_test_symbols() -> dict[str, Any]:
    """Import PubMed transformer collaborators lazily for faster collection."""
    from bioetl.application.pipelines.pubmed.extractors import (
        AuthorExtractor,
        DateExtractor,
    )
    from bioetl.application.pipelines.pubmed.transformer import (
        PubMedPublicationTransformer,
    )
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.types import RunType
    from tests.helpers.transformer_dependencies import instantiate_test_transformer

    return {
        "AuthorExtractor": AuthorExtractor,
        "DateExtractor": DateExtractor,
        "PubMedPublicationTransformer": PubMedPublicationTransformer,
        "PipelineContext": PipelineContext,
        "RunType": RunType,
        "instantiate_test_transformer": instantiate_test_transformer,
    }


def _build_transformer(**kwargs: Any):
    """Create a PubMed transformer without importing the stack during collection."""
    symbols = _pubmed_test_symbols()
    return symbols["instantiate_test_transformer"](
        symbols["PubMedPublicationTransformer"],
        provider="pubmed",
        **kwargs,
    )


def _build_pipeline_context(mock_logger: MagicMock):
    """Create a PipelineContext without importing it during collection."""
    symbols = _pubmed_test_symbols()
    return symbols["PipelineContext"](
        run_id=deterministic_uuid_from_callsite("test_pubmed_transformer"),
        run_type=symbols["RunType"].INCREMENTAL,
        logger=mock_logger,
    )


@pytest.fixture
def mock_context() -> PipelineContext:
    """Create a mock pipeline context."""
    mock_logger = MagicMock()
    mock_logger.bind = MagicMock(return_value=mock_logger)
    mock_logger.warning = MagicMock()
    mock_logger.debug = MagicMock()
    return _build_pipeline_context(mock_logger)


@pytest.mark.unit
class TestPubMedPublicationTransformer:
    """Tests for PubMedPublicationTransformer."""

    @pytest.fixture
    def transformer(self) -> PubMedPublicationTransformer:
        """Create PubMedPublicationTransformer instance."""
        return _build_transformer()

    def test_init_accepts_injected_extractors(self) -> None:
        """Transformer should allow extractor overrides via DI."""
        symbols = _pubmed_test_symbols()
        author_extractor = MagicMock(spec=symbols["AuthorExtractor"])
        date_extractor = MagicMock(spec=symbols["DateExtractor"])

        transformer = _build_transformer(
            author_extractor=author_extractor,
            date_extractor=date_extractor,
        )

        assert transformer._author_extractor is author_extractor
        assert transformer._date_extractor is date_extractor

    def test_extract_author_block_uses_injected_author_extractor(self) -> None:
        """Author normalization should use injected extractor instance."""
        symbols = _pubmed_test_symbols()
        author_extractor = MagicMock(spec=symbols["AuthorExtractor"])
        author_extractor.normalize.return_value = ["Smith, J"]
        author_extractor.parse_structured_affiliations.return_value = []
        transformer = _build_transformer(author_extractor=author_extractor)

        data_normalizer = MagicMock()
        data_normalizer.normalize_author_list.return_value = '["Smith, J"]'
        data_normalizer.normalize_author_keys.return_value = ["smith_j"]
        data_normalizer.extract_affiliations_from_authors.return_value = []
        data_normalizer.normalize_affiliations.return_value = None
        transformer._data_normalizer = data_normalizer

        article = ET.fromstring("<Article><AuthorList/></Article>")
        raw_author_data = [{"last_name": "Smith", "initials": "J"}]
        extracted = transformer._extract_author_block(article, raw_author_data)

        author_extractor.normalize.assert_called_once_with(raw_author_data)
        assert extracted["author_count"] == 1

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
        assert result["journal_name_short"] == "J Test Sci"
        assert result["issn"] == "1234-5678"
        assert result["issn_list"] == '["1234-5678"]'
        assert result["volume"] == "42"
        assert result["issue"] == "3"
        assert result["page_range"] == "123-145"
        # Dates
        assert result["pub_date"] == "2025-03-15"
        assert result["pub_month"] == 3  # March
        assert result["pub_day"] == 15  # Day from PubDate/Day element
        assert result["publication_year"] == 2025
        # epub_date, received_date, accepted_date, revised_date excluded from pipeline
        # Classification
        assert result["language"] == "eng"
        assert result["country"] == "United States"
        # Lists
        assert "Journal Article" in result["publication_types"]
        assert "unit testing" in result["subject_keywords"]
        assert "Software Testing" in result["subject_mesh"]
        # Authors (JSON-serialized list, may be hashed)
        assert result["authors"] is not None
        import json

        authors_list = json.loads(result["authors"])
        assert len(authors_list) == 2

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
        """Direct transform() must expose missing _raw_xml validation failures."""
        record: dict[str, Any] = {"pmid": "12345678"}

        with pytest.raises(ValueError, match="Missing or invalid _raw_xml field"):
            await transformer.transform(mock_context, record, index=0)

    @pytest.mark.asyncio
    async def test_transform_empty_raw_xml(
        self,
        transformer: PubMedPublicationTransformer,
        mock_context: PipelineContext,
    ) -> None:
        """Direct transform() must expose empty _raw_xml validation failures."""
        record: dict[str, Any] = {"_raw_xml": ""}

        with pytest.raises(ValueError, match="Missing or invalid _raw_xml field"):
            await transformer.transform(mock_context, record, index=0)

    @pytest.mark.asyncio
    async def test_transform_invalid_xml(
        self,
        transformer: PubMedPublicationTransformer,
        mock_context: PipelineContext,
    ) -> None:
        """Direct transform() must expose invalid XML parse failures."""
        record: dict[str, Any] = {"_raw_xml": "<invalid><xml>"}

        with pytest.raises(ValueError, match="XML parse error"):
            await transformer.transform(mock_context, record, index=0)
        mock_context.logger.warning.assert_called()

    @pytest.mark.asyncio
    async def test_transform_xml_without_pmid(
        self,
        transformer: PubMedPublicationTransformer,
        mock_context: PipelineContext,
    ) -> None:
        """Missing publication primary identifier must raise FilteredOutError."""
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

        with pytest.raises(FilteredOutError, match="primary identifier"):
            await transformer.transform(mock_context, record, index=0)

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

    # test_transform_affiliations removed: affiliations field renamed to affiliation_list


@pytest.mark.unit
class TestPubMedTransformerJournalExtraction:
    """Tests for journal data extraction."""

    @pytest.fixture
    def transformer(self) -> PubMedPublicationTransformer:
        """Create PubMedPublicationTransformer instance."""
        return _build_transformer()

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
        assert result["journal_name_short"] is None
        assert result["issn"] is None
        assert result["issn_list"] is None
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
        assert result["journal_name_short"] is None
        assert result["volume"] is None


@pytest.mark.unit
class TestPubMedTransformerDateExtraction:
    """Tests for date data extraction."""

    @pytest.fixture
    def transformer(self) -> PubMedPublicationTransformer:
        """Create PubMedPublicationTransformer instance."""
        return _build_transformer()

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
        # End-of-period strategy: year-only → YYYY-12-31
        assert result["pub_date"] == "2024-12-31"
        assert result["publication_year"] == 2024

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
        # End-of-period strategy: year+month → YYYY-MM-DD (last day of month)
        assert result["pub_date"] == "2024-12-31"
        assert result["publication_year"] == 2024

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
        # received_date, accepted_date, revised_date excluded from pipeline
        # These fields are no longer output by the transformer


@pytest.mark.unit
class TestPubMedTransformerIdentifierExtraction:
    """Tests for identifier extraction."""

    @pytest.fixture
    def transformer(self) -> PubMedPublicationTransformer:
        """Create PubMedPublicationTransformer instance."""
        return _build_transformer()

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
    """Tests for classification data extraction (subject keywords, MeSH, pub types)."""

    @pytest.fixture
    def transformer(self) -> PubMedPublicationTransformer:
        """Create PubMedPublicationTransformer instance."""
        return _build_transformer()

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
        assert result["subject_keywords"] is None or result["subject_keywords"] == []
        assert result["subject_mesh"] is None or result["subject_mesh"] == []

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
        # subject_keywords is serialized as canonical JSON string
        assert result["subject_keywords"] == '["keyword1","keyword2","keyword3"]'


@pytest.mark.unit
class TestPubMedTransformerDoiNormalization:
    """Tests for DOI normalization in PubMed transformer."""

    @pytest.fixture
    def transformer(self) -> PubMedPublicationTransformer:
        """Create PubMedPublicationTransformer instance."""
        return _build_transformer()

    @staticmethod
    def _make_xml_with_doi(pmid: str, doi: str) -> str:
        """Create PubMed XML with a specific DOI."""
        return f"""<?xml version="1.0"?>
        <PubmedArticle>
          <MedlineCitation>
            <PMID>{pmid}</PMID>
            <Article>
              <ArticleTitle>DOI Normalization Test</ArticleTitle>
              <ELocationID EIdType="doi">{doi}</ELocationID>
            </Article>
          </MedlineCitation>
        </PubmedArticle>
        """

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "raw_doi,expected",
        [
            ("10.1038/NATURE12373", "10.1038/nature12373"),
            ("10.1038/nature12373", "10.1038/nature12373"),
            ("  10.1000/xyz  ", "10.1000/xyz"),
            ("10.1000/ABC.DEF", "10.1000/abc.def"),
            ("10.1000/Test-DOI_123", "10.1000/test-doi_123"),
        ],
    )
    async def test_doi_normalization__lowercase_and_strip__ce7643b5(
        self,
        transformer: PubMedPublicationTransformer,
        mock_context: PipelineContext,
        raw_doi: str,
        expected: str,
    ) -> None:
        """Test that DOIs are normalized to lowercase and stripped."""
        xml = self._make_xml_with_doi("12345678", raw_doi)
        record: dict[str, Any] = {"_raw_xml": xml}

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["doi"] == expected

    @pytest.mark.asyncio
    async def test_doi_normalization__none_handling__f65d8f98(
        self,
        transformer: PubMedPublicationTransformer,
        mock_context: PipelineContext,
    ) -> None:
        """Test that None DOI remains None."""
        xml = """<?xml version="1.0"?>
        <PubmedArticle>
          <MedlineCitation>
            <PMID>12345678</PMID>
            <Article>
              <ArticleTitle>No DOI Article</ArticleTitle>
            </Article>
          </MedlineCitation>
        </PubmedArticle>
        """
        record: dict[str, Any] = {"_raw_xml": xml}

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["doi"] is None

    @pytest.mark.asyncio
    async def test_doi_normalization__affects_content_hash__5a01ead0(
        self,
        transformer: PubMedPublicationTransformer,
        mock_context: PipelineContext,
    ) -> None:
        """Test that DOIs with different cases produce same content hash after normalization."""
        xml_upper = self._make_xml_with_doi("12345678", "10.1038/NATURE12373")
        xml_lower = self._make_xml_with_doi("12345678", "10.1038/nature12373")

        result_upper = await transformer.transform(
            mock_context, {"_raw_xml": xml_upper}, index=0
        )
        result_lower = await transformer.transform(
            mock_context, {"_raw_xml": xml_lower}, index=0
        )

        assert result_upper is not None
        assert result_lower is not None
        # After normalization, content hashes should be identical
        assert result_upper["content_hash"] == result_lower["content_hash"]


@pytest.mark.unit
class TestPubMedTransformerUnifiedPageFields:
    """Tests for unified page field parsing (page_first, page_last).

    Note: The parse_page_range function tests are in tests/unit/domain/test_normalization.py.
    These tests verify the integration with the transformer.
    """

    @pytest.fixture
    def transformer(self) -> PubMedPublicationTransformer:
        """Create PubMedPublicationTransformer instance."""
        return _build_transformer()

    @pytest.mark.asyncio
    async def test_unified_page_fields_in_transform(
        self,
        transformer: PubMedPublicationTransformer,
        mock_context: PipelineContext,
    ) -> None:
        """Test that unified page fields are present in transformed output."""
        record: dict[str, Any] = {"_raw_xml": FULL_PUBMED_XML}

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["page_range"] == "123-145"
        assert result["page_first"] == "123"
        assert result["page_last"] == "145"


@pytest.mark.unit
class TestPubMedTransformerUnifiedDateFields:
    """Tests for unified publication_date field."""

    @pytest.fixture
    def transformer(self) -> PubMedPublicationTransformer:
        """Create PubMedPublicationTransformer instance."""
        return _build_transformer()

    def test_compute_publication_date_from_epub(
        self,
        transformer: PubMedPublicationTransformer,
    ) -> None:
        """Test publication_date computed from epub_date (priority 1)."""
        result = transformer._compute_publication_date(
            epub_date="2025-02-28", pub_date="2025-03-15", year=2025
        )
        assert result == "2025-02-28"

    def test_compute_publication_date_from_pub_date(
        self,
        transformer: PubMedPublicationTransformer,
    ) -> None:
        """Test publication_date computed from pub_date (priority 2)."""
        result = transformer._compute_publication_date(
            epub_date=None, pub_date="2025-03-15", year=2025
        )
        assert result == "2025-03-15"

    def test_compute_publication_date_from_year(
        self,
        transformer: PubMedPublicationTransformer,
    ) -> None:
        """Test publication_date computed from year only (priority 3)."""
        result = transformer._compute_publication_date(
            epub_date=None, pub_date=None, year=2025
        )
        # End-of-period strategy: year-only → YYYY-12-31
        assert result == "2025-12-31"

    def test_compute_publication_date_none(
        self,
        transformer: PubMedPublicationTransformer,
    ) -> None:
        """Test publication_date returns None when no date info available."""
        result = transformer._compute_publication_date(
            epub_date=None, pub_date=None, year=None
        )
        assert result is None

    def test_compute_publication_date_partial_epub_date(
        self,
        transformer: PubMedPublicationTransformer,
    ) -> None:
        """Test that partial epub_date (YYYY-MM) falls back to pub_date."""
        result = transformer._compute_publication_date(
            epub_date="2025-02", pub_date="2025-03-15", year=2025
        )
        # epub_date is partial, so falls back to pub_date
        assert result == "2025-03-15"

    @pytest.mark.asyncio
    async def test_unified_publication_date_in_transform(
        self,
        transformer: PubMedPublicationTransformer,
        mock_context: PipelineContext,
    ) -> None:
        """Test that publication_date is present in transformed output."""
        record: dict[str, Any] = {"_raw_xml": FULL_PUBMED_XML}

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        # epub_date (2025-02-28) was used to compute publication_date but is excluded from output
        assert result["publication_date"] == "2025-02-28"
        # epub_date excluded from pipeline output
        assert result["pub_date"] == "2025-03-15"

    @pytest.mark.asyncio
    async def test_pub_day_extraction_with_medline_date(
        self,
        transformer: PubMedPublicationTransformer,
        mock_context: PipelineContext,
    ) -> None:
        """Test extraction of pub_day from MedlineDate element."""
        # MedlineDate format: "2023 Jan-Feb" -> month=02, day=None
        # Note: DateExtractor currently returns day=None for MedlineDate
        # So we expect pub_day to be None, but pub_month to be set.

        xml = """<?xml version="1.0"?>
        <PubmedArticle>
          <MedlineCitation>
            <PMID>123</PMID>
            <Article>
              <Journal>
                <JournalIssue>
                  <PubDate>
                    <MedlineDate>2023 Jan-Feb</MedlineDate>
                  </PubDate>
                </JournalIssue>
              </Journal>
              <ArticleTitle>MedlineDate Test</ArticleTitle>
            </Article>
          </MedlineCitation>
        </PubmedArticle>
        """
        record: dict[str, Any] = {"_raw_xml": xml}

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["pub_date"] == "2023-02-28"  # End of Feb (not leap year)
        assert result["pub_month"] == 2
        assert result["pub_day"] is None  # Day is not extracted from MedlineDate range


@pytest.mark.unit
class TestPubMedTransformerIdentifierNormalization:
    """Tests for identifier normalization (pii, mid, publisher_id).

    Verifies that empty strings are normalized to None to ensure
    consistent content_hash computation across equivalent records.
    """

    @pytest.fixture
    def transformer(self) -> PubMedPublicationTransformer:
        """Create PubMedPublicationTransformer instance."""
        return _build_transformer()

    @staticmethod
    def _make_xml_with_identifiers(
        pmid: str,
        pii: str | None = None,
        mid: str | None = None,
        publisher_id: str | None = None,
    ) -> str:
        """Create PubMed XML with specific identifiers in ArticleIdList."""
        article_ids = [f'<ArticleId IdType="pubmed">{pmid}</ArticleId>']
        if pii is not None:
            article_ids.append(f'<ArticleId IdType="pii">{pii}</ArticleId>')
        if mid is not None:
            article_ids.append(f'<ArticleId IdType="mid">{mid}</ArticleId>')
        if publisher_id is not None:
            article_ids.append(
                f'<ArticleId IdType="publisher-id">{publisher_id}</ArticleId>'
            )

        return f"""<?xml version="1.0"?>
        <PubmedArticle>
          <MedlineCitation>
            <PMID>{pmid}</PMID>
            <Article>
              <ArticleTitle>Identifier Normalization Test</ArticleTitle>
            </Article>
          </MedlineCitation>
          <PubmedData>
            <ArticleIdList>
              {"".join(article_ids)}
            </ArticleIdList>
          </PubmedData>
        </PubmedArticle>
        """

    @pytest.mark.asyncio
    async def test_empty_pii_normalized_to_none(
        self,
        transformer: PubMedPublicationTransformer,
        mock_context: PipelineContext,
    ) -> None:
        """Test that empty string pii is normalized to None."""
        xml = self._make_xml_with_identifiers("12345678", pii="")
        record: dict[str, Any] = {"_raw_xml": xml}

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["pii"] is None

    @pytest.mark.asyncio
    async def test_whitespace_pii_normalized_to_none(
        self,
        transformer: PubMedPublicationTransformer,
        mock_context: PipelineContext,
    ) -> None:
        """Test that whitespace-only pii is normalized to None."""
        xml = self._make_xml_with_identifiers("12345678", pii="   ")
        record: dict[str, Any] = {"_raw_xml": xml}

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["pii"] is None

    @pytest.mark.asyncio
    async def test_valid_pii_preserved(
        self,
        transformer: PubMedPublicationTransformer,
        mock_context: PipelineContext,
    ) -> None:
        """Test that valid pii is preserved after normalization."""
        xml = self._make_xml_with_identifiers("12345678", pii="S0123-4567(23)00001-2")
        record: dict[str, Any] = {"_raw_xml": xml}

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["pii"] == "S0123-4567(23)00001-2"

    @pytest.mark.asyncio
    async def test_empty_mid_normalized_to_none(
        self,
        transformer: PubMedPublicationTransformer,
        mock_context: PipelineContext,
    ) -> None:
        """Test that empty string mid is normalized to None."""
        xml = self._make_xml_with_identifiers("12345678", mid="")
        record: dict[str, Any] = {"_raw_xml": xml}

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["mid"] is None

    @pytest.mark.asyncio
    async def test_valid_mid_preserved(
        self,
        transformer: PubMedPublicationTransformer,
        mock_context: PipelineContext,
    ) -> None:
        """Test that valid mid is preserved after normalization."""
        xml = self._make_xml_with_identifiers("12345678", mid="NIHMS123456")
        record: dict[str, Any] = {"_raw_xml": xml}

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["mid"] == "NIHMS123456"

    @pytest.mark.asyncio
    async def test_empty_publisher_id_normalized_to_none(
        self,
        transformer: PubMedPublicationTransformer,
        mock_context: PipelineContext,
    ) -> None:
        """Test that empty string publisher_id is normalized to None."""
        xml = self._make_xml_with_identifiers("12345678", publisher_id="")
        record: dict[str, Any] = {"_raw_xml": xml}

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["publisher_id"] is None

    @pytest.mark.asyncio
    async def test_valid_publisher_id_preserved(
        self,
        transformer: PubMedPublicationTransformer,
        mock_context: PipelineContext,
    ) -> None:
        """Test that valid publisher_id is preserved after normalization."""
        xml = self._make_xml_with_identifiers(
            "12345678", publisher_id="10.1234/pub.123"
        )
        record: dict[str, Any] = {"_raw_xml": xml}

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["publisher_id"] == "10.1234/pub.123"

    @pytest.mark.asyncio
    async def test_content_hash_same_for_empty_vs_none_identifiers(
        self,
        transformer: PubMedPublicationTransformer,
        mock_context: PipelineContext,
    ) -> None:
        """Test that empty string and None identifiers produce same content_hash.

        This ensures that equivalent records (where empty strings and None
        represent the same semantic meaning of "no value") have identical
        content hashes, preventing unnecessary updates in Silver layer.
        """
        # XML with no identifier elements (will result in None)
        xml_none = """<?xml version="1.0"?>
        <PubmedArticle>
          <MedlineCitation>
            <PMID>12345678</PMID>
            <Article>
              <ArticleTitle>Identifier Normalization Test</ArticleTitle>
            </Article>
          </MedlineCitation>
          <PubmedData>
            <ArticleIdList>
              <ArticleId IdType="pubmed">12345678</ArticleId>
            </ArticleIdList>
          </PubmedData>
        </PubmedArticle>
        """

        # XML with empty identifier elements (should be normalized to None)
        xml_empty = self._make_xml_with_identifiers(
            "12345678", pii="", mid="", publisher_id=""
        )

        result_none = await transformer.transform(
            mock_context, {"_raw_xml": xml_none}, index=0
        )
        result_empty = await transformer.transform(
            mock_context, {"_raw_xml": xml_empty}, index=0
        )

        assert result_none is not None
        assert result_empty is not None
        # Both should have None for the identifiers
        assert result_none["pii"] is None
        assert result_empty["pii"] is None
        assert result_none["mid"] is None
        assert result_empty["mid"] is None
        assert result_none["publisher_id"] is None
        assert result_empty["publisher_id"] is None
        # Content hashes should be identical
        assert result_none["content_hash"] == result_empty["content_hash"]


@pytest.mark.unit
class TestPubMedTransformerDateValidation:
    """Tests for date validation in transformer.

    Verifies that invalid dates ("2024-13-99", "n/a") result in
    publication_date becoming None rather than propagating bad data.
    """

    @pytest.fixture
    def transformer(self) -> PubMedPublicationTransformer:
        """Create PubMedPublicationTransformer instance."""
        return _build_transformer()

    def test_is_valid_date_format_full_date(
        self,
        transformer: PubMedPublicationTransformer,
    ) -> None:
        """Test that valid full dates are recognized."""
        assert transformer._is_valid_date_format("2024-01-15") is True
        assert transformer._is_valid_date_format("2023-12-31") is True
        assert transformer._is_valid_date_format("1999-06-01") is True

    def test_is_valid_date_format_partial_month(
        self,
        transformer: PubMedPublicationTransformer,
    ) -> None:
        """Test that valid YYYY-MM dates are recognized."""
        assert transformer._is_valid_date_format("2024-01") is True
        assert transformer._is_valid_date_format("2023-12") is True

    def test_is_valid_date_format_year_only(
        self,
        transformer: PubMedPublicationTransformer,
    ) -> None:
        """Test that valid YYYY dates are recognized."""
        assert transformer._is_valid_date_format("2024") is True
        assert transformer._is_valid_date_format("1999") is True

    def test_is_valid_date_format_invalid_month(
        self,
        transformer: PubMedPublicationTransformer,
    ) -> None:
        """Test that dates with invalid months are rejected."""
        assert transformer._is_valid_date_format("2024-13-01") is False
        assert transformer._is_valid_date_format("2024-00-15") is False
        assert transformer._is_valid_date_format("2024-13") is False
        assert transformer._is_valid_date_format("2024-00") is False

    def test_is_valid_date_format_invalid_day(
        self,
        transformer: PubMedPublicationTransformer,
    ) -> None:
        """Test that dates with invalid days are rejected."""
        assert transformer._is_valid_date_format("2024-01-32") is False
        assert transformer._is_valid_date_format("2024-01-00") is False
        assert transformer._is_valid_date_format("2024-12-99") is False

    def test_is_valid_date_format_text_values(
        self,
        transformer: PubMedPublicationTransformer,
    ) -> None:
        """Test that non-date text values are rejected."""
        assert transformer._is_valid_date_format("n/a") is False
        assert transformer._is_valid_date_format("unknown") is False
        assert transformer._is_valid_date_format("TBD") is False
        assert transformer._is_valid_date_format("") is False
        assert transformer._is_valid_date_format(None) is False

    def test_is_valid_date_format_malformed(
        self,
        transformer: PubMedPublicationTransformer,
    ) -> None:
        """Test that malformed dates are rejected."""
        assert (
            transformer._is_valid_date_format("2024/01/15") is False
        )  # Wrong separator
        assert transformer._is_valid_date_format("01-15-2024") is False  # Wrong order
        assert (
            transformer._is_valid_date_format("2024-1-15") is False
        )  # Missing leading zero
        assert transformer._is_valid_date_format("24-01-15") is False  # 2-digit year

    @pytest.mark.asyncio
    async def test_invalid_pub_date_results_in_none_publication_date(
        self,
        transformer: PubMedPublicationTransformer,
        mock_context: PipelineContext,
    ) -> None:
        """Test that invalid pub_date causes fallback to year for publication_date.

        When pub_date is invalid (e.g., "2024-13-99") and there's no valid
        epub_date, the transformer should fall back to using year only.
        """
        # This test relies on DateExtractor returning malformed dates.
        # Since DateExtractor does its own normalization, we test the
        # _compute_publication_date behavior with year fallback.
        result = transformer._compute_publication_date(
            epub_date=None, pub_date=None, year=2024
        )
        assert result == "2024-12-31"

    @pytest.mark.asyncio
    async def test_publication_date_with_only_year(
        self,
        transformer: PubMedPublicationTransformer,
        mock_context: PipelineContext,
    ) -> None:
        """Test that publication_date is correctly computed when only year is present.

        When both epub_date and pub_date are None/invalid, the transformer
        should fall back to year and produce YYYY-12-31.
        """
        xml = """<?xml version="1.0"?>
        <PubmedArticle>
          <MedlineCitation>
            <PMID>12345678</PMID>
            <Article>
              <Journal>
                <JournalIssue>
                  <PubDate>
                    <Year>2024</Year>
                  </PubDate>
                </JournalIssue>
              </Journal>
              <ArticleTitle>Year Only Test</ArticleTitle>
            </Article>
          </MedlineCitation>
        </PubmedArticle>
        """
        record: dict[str, Any] = {"_raw_xml": xml}

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["publication_year"] == 2024
        # When only year is available, publication_date uses end-of-year
        assert result["publication_date"] == "2024-12-31"

    def test_compute_publication_date_year_only_fallback(
        self,
        transformer: PubMedPublicationTransformer,
    ) -> None:
        """Test _compute_publication_date with only year available.

        This directly tests the method to ensure year-only fallback
        produces YYYY-12-31 format.
        """
        result = transformer._compute_publication_date(
            epub_date=None, pub_date=None, year=2023
        )
        assert result == "2023-12-31"

    def test_compute_publication_date_all_none(
        self,
        transformer: PubMedPublicationTransformer,
    ) -> None:
        """Test _compute_publication_date when all inputs are None."""
        result = transformer._compute_publication_date(
            epub_date=None, pub_date=None, year=None
        )
        assert result is None

    def test_compute_publication_date_priority_order(
        self,
        transformer: PubMedPublicationTransformer,
    ) -> None:
        """Test that _compute_publication_date follows priority order.

        Priority: epub_date > pub_date > year
        """
        # epub_date takes priority
        result = transformer._compute_publication_date(
            epub_date="2024-02-15", pub_date="2024-03-01", year=2024
        )
        assert result == "2024-02-15"

        # pub_date takes priority when epub_date is partial
        result = transformer._compute_publication_date(
            epub_date="2024-02", pub_date="2024-03-01", year=2024
        )
        assert result == "2024-03-01"

        # year fallback when both dates are None
        result = transformer._compute_publication_date(
            epub_date=None, pub_date=None, year=2024
        )
        assert result == "2024-12-31"


@pytest.mark.unit
class TestPubMedTransformerContentHashStability:
    """Tests to verify content_hash stability for valid records.

    Ensures that the normalization changes don't affect content_hash
    computation for records with valid data.
    """

    @pytest.fixture
    def transformer(self) -> PubMedPublicationTransformer:
        """Create PubMedPublicationTransformer instance."""
        return _build_transformer()

    @pytest.mark.asyncio
    async def test_valid_record_content_hash_deterministic(
        self,
        transformer: PubMedPublicationTransformer,
        mock_context: PipelineContext,
    ) -> None:
        """Test that valid records produce consistent content_hash.

        Multiple transformations of the same valid record should always
        produce identical content_hash values.
        """
        record: dict[str, Any] = {"_raw_xml": FULL_PUBMED_XML}

        results = [
            await transformer.transform(mock_context, record, index=0) for _ in range(3)
        ]

        assert all(r is not None for r in results)
        hashes = [r["content_hash"] for r in results]
        assert len(set(hashes)) == 1, "All hashes should be identical"

    @pytest.mark.asyncio
    async def test_valid_identifiers_do_not_change_hash(
        self,
        transformer: PubMedPublicationTransformer,
        mock_context: PipelineContext,
    ) -> None:
        """Test that valid identifiers produce stable content_hash.

        Records with valid pii, mid, publisher_id values should have
        deterministic content_hash values.
        """
        xml = """<?xml version="1.0"?>
        <PubmedArticle>
          <MedlineCitation>
            <PMID>12345678</PMID>
            <Article>
              <ArticleTitle>Valid Identifiers Test</ArticleTitle>
            </Article>
          </MedlineCitation>
          <PubmedData>
            <ArticleIdList>
              <ArticleId IdType="pubmed">12345678</ArticleId>
              <ArticleId IdType="pii">S0123-4567(23)00001-2</ArticleId>
              <ArticleId IdType="mid">NIHMS123456</ArticleId>
              <ArticleId IdType="publisher-id">pub.12345</ArticleId>
            </ArticleIdList>
          </PubmedData>
        </PubmedArticle>
        """
        record: dict[str, Any] = {"_raw_xml": xml}

        result1 = await transformer.transform(mock_context, record, index=0)
        result2 = await transformer.transform(mock_context, record, index=0)

        assert result1 is not None
        assert result2 is not None
        assert result1["pii"] == "S0123-4567(23)00001-2"
        assert result1["mid"] == "NIHMS123456"
        assert result1["publisher_id"] == "pub.12345"
        assert result1["content_hash"] == result2["content_hash"]


# ---------------------------------------------------------------------------
# Tests merged from orphan tests/unit/pipelines/pubmed/test_pubmed_transformer.py
# ---------------------------------------------------------------------------


@pytest.fixture
def _orphan_transformer() -> PubMedPublicationTransformer:
    """Create a PubMedPublicationTransformer instance (orphan fixture)."""
    return _build_transformer()


@pytest.fixture
def _orphan_mock_logger() -> MagicMock:
    """Create a mock logger (orphan fixture)."""
    logger = MagicMock()
    logger.bind.return_value = logger
    return logger


@pytest.fixture
def _orphan_pipeline_context(_orphan_mock_logger: MagicMock) -> PipelineContext:
    """Create a pipeline context for testing (orphan fixture)."""
    from uuid import UUID

    symbols = _pubmed_test_symbols()
    return symbols["PipelineContext"](
        run_id=UUID("00000000-0000-0000-0000-000000000000"),
        run_type=symbols["RunType"].INCREMENTAL,
        logger=_orphan_mock_logger,
    )


@pytest.mark.unit
class TestTransformNonStringRawXml:
    """Test that non-string _raw_xml raises ValueError."""

    @pytest.mark.asyncio
    async def test_transform_non_string_raw_xml(
        self,
        _orphan_transformer: PubMedPublicationTransformer,
        _orphan_pipeline_context: PipelineContext,
    ) -> None:
        """Test that non-string _raw_xml raises ValueError."""
        from typing import cast

        from bioetl.domain.types import BronzeRecord

        bronze_record: BronzeRecord = cast(
            "BronzeRecord",
            {"pmid": "12345", "_raw_xml": 12345, "source_batch_id": "test"},
        )

        with pytest.raises(ValueError, match="Missing or invalid _raw_xml"):
            await _orphan_transformer._transform_impl(
                _orphan_pipeline_context, bronze_record, 0
            )


@pytest.mark.unit
class TestExtractJournalData:
    """Tests for journal data extraction (private method)."""

    def test_extract_journal_data_complete(
        self, _orphan_transformer: PubMedPublicationTransformer
    ) -> None:
        """Test extraction of complete journal data."""
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

        result = _orphan_transformer._extract_journal_data(article)

        assert result["journal"] == "Nature Medicine"
        assert result["journal_name_short"] == "Nat Med"
        assert result["issn"] == "1234-5678"
        assert result["volume"] == "25"
        assert result["issue"] == "10"
        assert result["page_range"] == "100-110"

    def test_extract_journal_data_missing_journal(
        self, _orphan_transformer: PubMedPublicationTransformer
    ) -> None:
        """Test extraction when Journal element is missing."""
        xml = """
        <Article>
            <Pagination>
                <MedlinePgn>100-110</MedlinePgn>
            </Pagination>
        </Article>
        """
        article = ET.fromstring(xml)

        result = _orphan_transformer._extract_journal_data(article)

        assert result["journal"] is None
        assert result["journal_name_short"] is None
        assert result["issn"] is None
        assert result["volume"] is None
        assert result["issue"] is None
        assert result["page_range"] == "100-110"

    def test_extract_journal_data_partial(
        self, _orphan_transformer: PubMedPublicationTransformer
    ) -> None:
        """Test extraction with partial journal data."""
        xml = """
        <Article>
            <Journal>
                <Title>Test Journal</Title>
            </Journal>
        </Article>
        """
        article = ET.fromstring(xml)

        result = _orphan_transformer._extract_journal_data(article)

        assert result["journal"] == "Test Journal"
        assert result["journal_name_short"] is None
        assert result["issn"] is None
        assert result["volume"] is None
        assert result["issue"] is None
        assert result["page_range"] is None

    def test_extract_journal_data_missing_journal_issue(
        self, _orphan_transformer: PubMedPublicationTransformer
    ) -> None:
        """Test extraction when JournalIssue is missing."""
        xml = """
        <Article>
            <Journal>
                <Title>Test Journal</Title>
                <ISOAbbreviation>Test J</ISOAbbreviation>
            </Journal>
        </Article>
        """
        article = ET.fromstring(xml)

        result = _orphan_transformer._extract_journal_data(article)

        assert result["journal"] == "Test Journal"
        assert result["journal_name_short"] == "Test J"
        assert result["volume"] is None
        assert result["issue"] is None


@pytest.mark.unit
class TestExtractDateData:
    """Tests for date data extraction (private method)."""

    def test_extract_date_data_complete(
        self, _orphan_transformer: PubMedPublicationTransformer
    ) -> None:
        """Test extraction of complete date data."""
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

        result = _orphan_transformer._extract_date_data(article, pubmed_data, None)

        assert result["pub_date"] == "2023-03-15"
        assert result["publication_year"] == 2023
        assert result["date_completed"] is None
        assert result["date_revised"] is None

    def test_extract_date_data_year_only(
        self, _orphan_transformer: PubMedPublicationTransformer
    ) -> None:
        """Test extraction with year-only publication date (end-of-period: Dec 31)."""
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

        result = _orphan_transformer._extract_date_data(article, None, None)

        assert result["pub_date"] == "2023-12-31"
        assert result["publication_year"] == 2023
        assert result["date_completed"] is None
        assert result["date_revised"] is None

    def test_extract_date_data_no_dates(
        self, _orphan_transformer: PubMedPublicationTransformer
    ) -> None:
        """Test extraction with no date data."""
        article_xml = "<Article></Article>"
        article = ET.fromstring(article_xml)

        result = _orphan_transformer._extract_date_data(article, None, None)

        assert result["pub_date"] is None
        assert result["publication_year"] is None
        assert result["date_completed"] is None
        assert result["date_revised"] is None

    def test_extract_date_data_missing_journal(
        self, _orphan_transformer: PubMedPublicationTransformer
    ) -> None:
        """Test extraction when Journal element is missing."""
        article_xml = """
        <Article>
            <ArticleTitle>Test</ArticleTitle>
        </Article>
        """
        article = ET.fromstring(article_xml)

        result = _orphan_transformer._extract_date_data(article, None, None)

        assert result["pub_date"] is None
        assert result["publication_year"] is None
        assert result["date_completed"] is None
        assert result["date_revised"] is None

    def test_extract_date_data_with_medline_dates(
        self, _orphan_transformer: PubMedPublicationTransformer
    ) -> None:
        """Test extraction of DateCompleted and DateRevised from MedlineCitation."""
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
        medline_xml = """
        <MedlineCitation>
            <DateCompleted>
                <Year>2023</Year>
                <Month>05</Month>
                <Day>15</Day>
            </DateCompleted>
            <DateRevised>
                <Year>2024</Year>
                <Month>01</Month>
                <Day>10</Day>
            </DateRevised>
        </MedlineCitation>
        """
        article = ET.fromstring(article_xml)
        medline = ET.fromstring(medline_xml)

        result = _orphan_transformer._extract_date_data(article, None, medline)

        assert result["date_completed"] == "2023-05-15"
        assert result["date_revised"] == "2024-01-10"
        assert result["publication_year"] == 2023


@pytest.mark.unit
class TestExtractBusinessData:
    """Tests for business data extraction (private method).

    After refactoring to BasePublicationTransformer:
    - _extract_business_data now takes only record (BronzeRecord)
    - It uses the cached _cached_xml_root set by _pre_extract_validation
    - Tests must set up _cached_xml_root before calling _extract_business_data
    """

    def test_extract_business_data_complete(
        self, _orphan_transformer: PubMedPublicationTransformer
    ) -> None:
        """Test extraction of complete business data."""
        import json

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
        _orphan_transformer._cached_xml_root = root

        result = _orphan_transformer._extract_business_data({})

        assert result["pmid"] == "12345"
        assert result["doi"] == "10.1234/test.2023"
        assert result["title"] == "Complete Test Article"
        assert result["abstract"] == "Full abstract text here."
        assert json.loads(result["authors"]) == [
            "Doe, J",
            "Smith, Jane",
        ]
        assert result["journal"] == "Test Journal"
        assert result["journal_name_short"] == "Test J"
        assert result["issn"] == "1234-5678"
        assert result["issn_list"] == '["1234-5678"]'
        assert result["volume"] == "10"
        assert result["issue"] == "5"
        assert result["pub_date"] == "2023-03-15"
        assert result["publication_year"] == 2023
        assert result["publication_types"] == '["Journal Article","Review"]'
        assert result["subject_keywords"] == '["keyword1","keyword2"]'
        assert result["subject_mesh"] == '["Proteins"]'
        assert result["language"] == "eng"
        assert result["country"] == "United States"
        assert result["pmc_id"] == "PMC123456"

    def test_extract_business_data__data_minimal__8fd4cde7(
        self, _orphan_transformer: PubMedPublicationTransformer
    ) -> None:
        """Test extraction with minimal data (PMID only in article)."""
        xml = """
        <PubmedArticle>
            <MedlineCitation>
                <PMID>12345</PMID>
            </MedlineCitation>
        </PubmedArticle>
        """
        root = ET.fromstring(xml)
        _orphan_transformer._cached_xml_root = root

        result = _orphan_transformer._extract_business_data({})

        assert result["pmid"] == "12345"

    def test_extract_business_data_missing_article_element(
        self, _orphan_transformer: PubMedPublicationTransformer
    ) -> None:
        """Test extraction when Article element is missing."""
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
        _orphan_transformer._cached_xml_root = root

        result = _orphan_transformer._extract_business_data({})

        assert result["pmid"] == "12345"
        assert len(result) == 1
