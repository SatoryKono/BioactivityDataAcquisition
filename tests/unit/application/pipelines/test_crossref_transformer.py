"""Unit tests for CrossRef Publication transformer."""

from __future__ import annotations

from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from bioetl.application.pipelines.crossref.transformer import CrossRefPublicationTransformer
from bioetl.domain.context import PipelineContext
from bioetl.domain.types import RunType


@pytest.fixture
def mock_context():
    """Create a mock pipeline context."""
    mock_logger = MagicMock()
    mock_logger.bind = MagicMock(return_value=mock_logger)
    mock_logger.warning = MagicMock()
    return PipelineContext(
        run_id=uuid4(),
        run_type=RunType.INCREMENTAL,
        logger=mock_logger,
    )


@pytest.mark.unit
class TestCrossRefPublicationTransformer:
    """Tests for CrossRefPublicationTransformer."""

    @pytest.fixture
    def transformer(self):
        """Create CrossRefPublicationTransformer instance."""
        return CrossRefPublicationTransformer(provider="crossref")

    @pytest.mark.asyncio
    async def test_transform_valid_record(self, transformer, mock_context):
        """Test transformation of valid CrossRef record with all fields."""
        record = {
            "DOI": "10.1234/test.2024.001",
            "title": ["Test Publication Title"],
            "author": [
                {"given": "John", "family": "Doe"},
                {"given": "Jane", "family": "Smith"},
            ],
            "container-title": ["Journal of Testing"],
            "published-print": {
                "date-parts": [[2024, 1, 15]],
            },
            "volume": "10",
            "issue": "2",
            "page": "100-110",
            "abstract": "<jats:p>This is the abstract.</jats:p>",
            "type": "journal-article",
            "is-referenced-by-count": 42,
            "references-count": 25,
            "publisher": "Test Publisher",
            "ISSN": ["1234-5678"],
            "subject": ["Biology", "Chemistry"],
            "URL": "https://doi.org/10.1234/test.2024.001",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["doi"] == "10.1234/test.2024.001"
        assert result["title"] == "Test Publication Title"
        assert result["authors"] == ["John Doe", "Jane Smith"]
        assert result["journal"] == "Journal of Testing"
        assert result["year"] == 2024
        assert result["published_date"] == "2024-01-15"
        assert result["volume"] == "10"
        assert result["issue"] == "2"
        assert result["first_page"] == "100"
        assert result["last_page"] == "110"
        assert result["abstract"] == "This is the abstract."
        assert result["doc_type"] == "journal-article"
        assert result["citation_count"] == 42
        assert result["references_count"] == 25
        assert result["publisher"] == "Test Publisher"
        assert result["issn"] == "1234-5678"
        assert result["subjects"] == ["Biology", "Chemistry"]
        assert "entity_id" in result
        assert "content_hash" in result
        # Lineage fields should be present
        assert "_run_id" in result
        assert "_run_type" in result
        assert "_ingestion_ts" in result

    @pytest.mark.asyncio
    async def test_transform_missing_doi(self, transformer, mock_context):
        """Test transformation returns None when DOI is missing."""
        record = {
            "title": ["Test Publication"],
            "author": [{"given": "John", "family": "Doe"}],
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is None
        mock_context.logger.warning.assert_called()

    @pytest.mark.asyncio
    async def test_transform_minimal_record(self, transformer, mock_context):
        """Test transformation of minimal record with only DOI."""
        record = {
            "DOI": "10.1234/minimal",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["doi"] == "10.1234/minimal"
        assert result["title"] is None
        assert result["authors"] == []
        assert result["year"] is None

    @pytest.mark.asyncio
    async def test_transform_normalizes_doi(self, transformer, mock_context):
        """Test DOI is normalized to lowercase."""
        record = {
            "DOI": "10.1234/UPPERCASE.DOI",
            "title": ["Test"],
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["doi"] == "10.1234/uppercase.doi"

    @pytest.mark.asyncio
    async def test_transform_cleans_abstract_html(self, transformer, mock_context):
        """Test HTML tags are removed from abstract."""
        record = {
            "DOI": "10.1234/abstract.test",
            "abstract": "<jats:p><b>Bold</b> and <i>italic</i> text.</jats:p>",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["abstract"] == "Bold and italic text."

    @pytest.mark.asyncio
    async def test_transform_extracts_first_title(self, transformer, mock_context):
        """Test first title is extracted from list."""
        record = {
            "DOI": "10.1234/title.test",
            "title": ["First Title", "Subtitle"],
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["title"] == "First Title"

    @pytest.mark.asyncio
    async def test_transform_extracts_authors(self, transformer, mock_context):
        """Test authors are correctly extracted and formatted."""
        record = {
            "DOI": "10.1234/authors.test",
            "author": [
                {"given": "John", "family": "Doe"},
                {"family": "Anonymous"},  # No given name
                {"name": "Research Group"},  # Corporate author
            ],
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert "John Doe" in result["authors"]
        assert "Anonymous" in result["authors"]
        assert "Research Group" in result["authors"]
        assert len(result["authors"]) == 3

    @pytest.mark.asyncio
    async def test_transform_extracts_pages(self, transformer, mock_context):
        """Test page range is correctly split."""
        record = {
            "DOI": "10.1234/pages.test",
            "page": "123-456",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["first_page"] == "123"
        assert result["last_page"] == "456"

    @pytest.mark.asyncio
    async def test_transform_handles_single_page(self, transformer, mock_context):
        """Test single page (no range) is handled correctly."""
        record = {
            "DOI": "10.1234/single.page",
            "page": "42",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["first_page"] == "42"
        assert result["last_page"] is None

    @pytest.mark.asyncio
    async def test_transform_extracts_publication_date(self, transformer, mock_context):
        """Test publication date is correctly extracted from date-parts."""
        record = {
            "DOI": "10.1234/date.test",
            "published-print": {
                "date-parts": [[2023, 6, 15]],
            },
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["year"] == 2023
        assert result["published_date"] == "2023-06-15"

    @pytest.mark.asyncio
    async def test_transform_handles_partial_date(self, transformer, mock_context):
        """Test partial date (year-month only) is handled."""
        record = {
            "DOI": "10.1234/partial.date",
            "published-print": {
                "date-parts": [[2023, 6]],
            },
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["year"] == 2023
        assert result["published_date"] == "2023-06"

    @pytest.mark.asyncio
    async def test_transform_falls_back_to_published_online(
        self, transformer, mock_context
    ):
        """Test fallback to published-online date when published-print is missing."""
        record = {
            "DOI": "10.1234/online.date",
            "published-online": {
                "date-parts": [[2023, 5, 10]],
            },
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["year"] == 2023
        assert result["published_date"] == "2023-05-10"

    @pytest.mark.asyncio
    async def test_transform_serializes_funders(self, transformer, mock_context):
        """Test funder information is serialized to JSON."""
        record = {
            "DOI": "10.1234/funders.test",
            "funder": [
                {"name": "NIH", "award": ["R01-12345"]},
                {"name": "NSF", "award": ["ABC-67890"]},
            ],
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["funders"] is not None
        # Should be JSON serialized
        import json

        funders = json.loads(result["funders"])
        assert len(funders) == 2
        assert funders[0]["name"] == "NIH"

    @pytest.mark.asyncio
    async def test_transform_extracts_license_url(self, transformer, mock_context):
        """Test license URL is extracted."""
        record = {
            "DOI": "10.1234/license.test",
            "license": [
                {"URL": "https://creativecommons.org/licenses/by/4.0/"},
            ],
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["license_url"] == "https://creativecommons.org/licenses/by/4.0/"

    @pytest.mark.asyncio
    async def test_transform_handles_html_entities_in_title(
        self, transformer, mock_context
    ):
        """Test HTML entities in title are unescaped."""
        record = {
            "DOI": "10.1234/html.entities",
            "title": ["Study of CO&lt;sub&gt;2&lt;/sub&gt; levels"],
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        # HTML entities should be unescaped
        assert "&lt;" not in result["title"]

    @pytest.mark.asyncio
    async def test_transform_empty_abstract_becomes_none(
        self, transformer, mock_context
    ):
        """Test empty abstract after cleaning becomes None."""
        record = {
            "DOI": "10.1234/empty.abstract",
            "abstract": "   ",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["abstract"] is None

    @pytest.mark.asyncio
    async def test_provider_name(self, transformer):
        """Test provider name is set correctly."""
        assert transformer.provider == "crossref"

    @pytest.mark.asyncio
    async def test_entity_type(self, transformer):
        """Test entity type is set correctly."""
        assert transformer.entity_type == "publication"


@pytest.mark.unit
class TestCrossRefPublicationTransformerExtractors:
    """Tests for individual extractor methods."""

    def test_extract_title_from_list(self):
        """Test _extract_title extracts first element from list."""
        result = CrossRefPublicationTransformer._extract_title(
            {"title": ["First", "Second"]}
        )
        assert result == "First"

    def test_extract_title_empty_list(self):
        """Test _extract_title returns None for empty list."""
        result = CrossRefPublicationTransformer._extract_title({"title": []})
        assert result is None

    def test_extract_title_missing(self):
        """Test _extract_title returns None when title is missing."""
        result = CrossRefPublicationTransformer._extract_title({})
        assert result is None

    def test_extract_abstract_removes_html(self):
        """Test _extract_abstract removes HTML tags."""
        result = CrossRefPublicationTransformer._extract_abstract(
            {"abstract": "<p>Hello <b>World</b></p>"}
        )
        assert result == "Hello World"

    def test_extract_abstract_missing(self):
        """Test _extract_abstract returns None when abstract is missing."""
        result = CrossRefPublicationTransformer._extract_abstract({})
        assert result is None

    def test_extract_authors_full_names(self):
        """Test _extract_authors formats given + family names."""
        result = CrossRefPublicationTransformer._extract_authors(
            {"author": [{"given": "John", "family": "Doe"}]}
        )
        assert result == ["John Doe"]

    def test_extract_authors_family_only(self):
        """Test _extract_authors handles family-only names."""
        result = CrossRefPublicationTransformer._extract_authors(
            {"author": [{"family": "Anonymous"}]}
        )
        assert result == ["Anonymous"]

    def test_extract_authors_corporate(self):
        """Test _extract_authors handles corporate authors."""
        result = CrossRefPublicationTransformer._extract_authors(
            {"author": [{"name": "Research Consortium"}]}
        )
        assert result == ["Research Consortium"]

    def test_extract_pages_range(self):
        """Test _extract_pages splits page ranges."""
        result = CrossRefPublicationTransformer._extract_pages("100-200")
        assert result == ("100", "200")

    def test_extract_pages_single(self):
        """Test _extract_pages handles single page."""
        result = CrossRefPublicationTransformer._extract_pages("42")
        assert result == ("42", None)

    def test_extract_pages_none(self):
        """Test _extract_pages handles None input."""
        result = CrossRefPublicationTransformer._extract_pages(None)
        assert result == (None, None)

    def test_extract_publication_date_full(self):
        """Test _extract_publication_date extracts full date."""
        result = CrossRefPublicationTransformer._extract_publication_date(
            {"published-print": {"date-parts": [[2024, 3, 15]]}}
        )
        assert result == (2024, "2024-03-15")

    def test_extract_publication_date_partial(self):
        """Test _extract_publication_date extracts year-month."""
        result = CrossRefPublicationTransformer._extract_publication_date(
            {"published-print": {"date-parts": [[2024, 3]]}}
        )
        assert result == (2024, "2024-03")

    def test_extract_publication_date_year_only(self):
        """Test _extract_publication_date extracts year only."""
        result = CrossRefPublicationTransformer._extract_publication_date(
            {"published-print": {"date-parts": [[2024]]}}
        )
        assert result == (2024, None)

    def test_extract_publication_date_missing(self):
        """Test _extract_publication_date returns None when missing."""
        result = CrossRefPublicationTransformer._extract_publication_date({})
        assert result == (None, None)

    def test_extract_first_item_from_list(self):
        """Test _extract_first_item gets first element."""
        result = CrossRefPublicationTransformer._extract_first_item(["a", "b"])
        assert result == "a"

    def test_extract_first_item_from_string(self):
        """Test _extract_first_item returns string as-is."""
        result = CrossRefPublicationTransformer._extract_first_item("value")
        assert result == "value"

    def test_extract_first_item_empty_list(self):
        """Test _extract_first_item returns None for empty list."""
        result = CrossRefPublicationTransformer._extract_first_item([])
        assert result is None

    def test_normalize_doi(self):
        """Test _normalize_doi strips and lowercases."""
        result = CrossRefPublicationTransformer._normalize_doi("  10.1234/ABC  ")
        assert result == "10.1234/abc"
