"""Unit tests for PubMedAdapter fallback methods.

Tests for _search_by_title and fetch_filtered_with_fallback methods
that enable title-based publication resolution when PMID lookup fails.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bioetl.infrastructure.adapters.pubmed import PubMedAdapter
from tests.helpers.adapter_runtime import build_http_adapter_runtime_kwargs


@pytest.fixture
def mock_http_client() -> AsyncMock:
    """Create mock HTTP client."""
    client = AsyncMock()
    client.__aenter__.return_value = client
    client.__aexit__.return_value = None
    client.get = AsyncMock()
    return client


@pytest.fixture
def mock_logger() -> MagicMock:
    """Create mock logger."""
    logger = MagicMock()
    logger.debug = MagicMock()
    logger.info = MagicMock()
    logger.warning = MagicMock()
    logger.error = MagicMock()
    return logger


@pytest.fixture
def adapter(mock_http_client: AsyncMock, mock_logger: MagicMock) -> PubMedAdapter:
    """Create adapter instance for testing."""
    return PubMedAdapter(
        http_client=mock_http_client,
        logger=mock_logger,
        email="test@example.com",
        **build_http_adapter_runtime_kwargs(
            "pubmed",
            logger=mock_logger,
            include_fallback_service=True,
        ),
    )


# =============================================================================
# _search_by_title Tests
# =============================================================================


class TestSearchByTitle:
    """Tests for PubMedAdapter._search_by_title method."""

    @pytest.mark.asyncio
    async def test_constructs_correct_pubmed_query(
        self, adapter: PubMedAdapter, mock_http_client: AsyncMock
    ) -> None:
        """Test title search constructs correct PubMed [Title] query."""
        # Mock esearch response with empty results
        esearch_response = MagicMock()
        esearch_response.json.return_value = {"esearchresult": {"idlist": []}}
        mock_http_client.get.return_value = esearch_response

        await adapter._search_by_title("CRISPR gene editing")

        # Verify esearch was called
        mock_http_client.get.assert_called_once()
        call_args = mock_http_client.get.call_args
        params = call_args[1]["params"]

        # Verify query uses [Title] field syntax
        assert '"CRISPR gene editing"[Title]' in params["term"]
        assert params["db"] == "pubmed"

    @pytest.mark.asyncio
    async def test_escapes_quotes_in_title(
        self, adapter: PubMedAdapter, mock_http_client: AsyncMock
    ) -> None:
        """Test quotes in title are replaced with single quotes."""
        esearch_response = MagicMock()
        esearch_response.json.return_value = {"esearchresult": {"idlist": []}}
        mock_http_client.get.return_value = esearch_response

        await adapter._search_by_title('Title with "quotes"')

        call_args = mock_http_client.get.call_args
        params = call_args[1]["params"]

        # Inner quotes should be replaced with single quotes
        assert "\"Title with 'quotes'\"[Title]" in params["term"]

    @pytest.mark.asyncio
    async def test_truncates_long_titles(
        self, adapter: PubMedAdapter, mock_http_client: AsyncMock
    ) -> None:
        """Test titles longer than 200 chars are truncated."""
        esearch_response = MagicMock()
        esearch_response.json.return_value = {"esearchresult": {"idlist": []}}
        mock_http_client.get.return_value = esearch_response

        long_title = "A" * 300
        await adapter._search_by_title(long_title)

        call_args = mock_http_client.get.call_args
        params = call_args[1]["params"]

        # Title in query should be truncated to 200 chars
        # Format: "...title..."[Title]
        expected_truncated = "A" * 200
        assert f'"{expected_truncated}"[Title]' in params["term"]

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_no_pmids(
        self, adapter: PubMedAdapter, mock_http_client: AsyncMock
    ) -> None:
        """Test returns empty list when esearch finds no PMIDs."""
        esearch_response = MagicMock()
        esearch_response.json.return_value = {"esearchresult": {"idlist": []}}
        mock_http_client.get.return_value = esearch_response

        results = await adapter._search_by_title("Nonexistent Title")

        assert results == []

    @pytest.mark.asyncio
    async def test_returns_fetched_records_when_pmids_found(
        self, adapter: PubMedAdapter, mock_http_client: AsyncMock
    ) -> None:
        """Test returns records when PMIDs are found and fetched."""
        # Mock esearch response
        esearch_response = MagicMock()
        esearch_response.json.return_value = {"esearchresult": {"idlist": ["12345678"]}}

        # Mock efetch response
        efetch_response = MagicMock()
        efetch_response.text = """<?xml version="1.0"?>
        <PubmedArticleSet>
            <PubmedArticle>
                <MedlineCitation>
                    <PMID>12345678</PMID>
                    <Article>
                        <ArticleTitle>Test Publication Title</ArticleTitle>
                    </Article>
                </MedlineCitation>
            </PubmedArticle>
        </PubmedArticleSet>"""

        # Return different responses for esearch and efetch
        mock_http_client.get.side_effect = [esearch_response, efetch_response]

        results = await adapter._search_by_title("Test Publication Title")

        assert len(results) == 1
        assert results[0]["pmid"] == "12345678"

    @pytest.mark.asyncio
    async def test_handles_exception_gracefully(
        self,
        adapter: PubMedAdapter,
        mock_http_client: AsyncMock,
        mock_logger: MagicMock,
    ) -> None:
        """Test returns empty list and logs on exception."""
        mock_http_client.get.side_effect = RuntimeError("Network error")

        results = await adapter._search_by_title("Test Title")

        assert results == []
        mock_logger.debug.assert_called()

    @pytest.mark.asyncio
    async def test_strips_whitespace_from_title(
        self, adapter: PubMedAdapter, mock_http_client: AsyncMock
    ) -> None:
        """Test leading/trailing whitespace is stripped from title."""
        esearch_response = MagicMock()
        esearch_response.json.return_value = {"esearchresult": {"idlist": []}}
        mock_http_client.get.return_value = esearch_response

        await adapter._search_by_title("  Padded Title  ")

        call_args = mock_http_client.get.call_args
        params = call_args[1]["params"]

        # Whitespace should be stripped
        assert '"Padded Title"[Title]' in params["term"]


# =============================================================================
# fetch_filtered_with_fallback Tests
# =============================================================================


class TestFetchFilteredWithFallback:
    """Tests for PubMedAdapter.fetch_filtered_with_fallback method."""

    @pytest.mark.asyncio
    async def test_rejects_non_publication_entity_type(
        self, adapter: PubMedAdapter
    ) -> None:
        """Test raises ValueError for non-publication entity types."""
        with pytest.raises(ValueError, match="only supports 'publication'"):
            async for _ in adapter.fetch_filtered_with_fallback(
                entity_type="compound",
                filter_ids=["12345"],
                filter_field="pmid",
                fallback_mapping={},
            ):
                continue

    @pytest.mark.asyncio
    async def test_delegates_pubmed_request_to_fallback_service(
        self, adapter: PubMedAdapter, mock_logger: MagicMock
    ) -> None:
        """Bridge PubMed-specific closure/config into the shared fallback service."""
        captured: dict[str, Any] = {}
        forwarded: dict[str, Any] = {}
        assert adapter._fallback_handler is not None

        async def mock_fetch_filtered(
            entity_type: str,
            filter_ids: list[str],
            filter_field: str,
            limit: int | None,
        ) -> AsyncIterator[dict[str, Any]]:
            forwarded["entity_type"] = entity_type
            forwarded["filter_ids"] = list(filter_ids)
            forwarded["filter_field"] = filter_field
            forwarded["limit"] = limit
            yield {
                "pmid": "12345678",
                "article_title": "Primary Result",
                "_lookup_method": "pmid",
            }

        async def capture_execute(request: Any) -> AsyncIterator[dict[str, Any]]:
            captured["request"] = request
            async for record in request.primary_record_fetcher(["12345678"], 2):
                yield record

        with (
            patch.object(adapter, "fetch_filtered", mock_fetch_filtered),
            patch.object(adapter._fallback_fetch_service, "execute", capture_execute),
        ):
            results = []
            async for record in adapter.fetch_filtered_with_fallback(
                entity_type="publication",
                filter_ids=["12345678", "", "99999999"],
                filter_field="doi",
                fallback_mapping={
                    "99999999": "Missing Title",
                    "": "Title Only Title",
                },
                limit=2,
            ):
                results.append(record)

        request = captured["request"]
        assert forwarded == {
            "entity_type": "publication",
            "filter_ids": ["12345678"],
            "filter_field": "doi",
            "limit": 2,
        }
        assert len(results) == 1
        assert results[0]["_lookup_method"] == "pmid"
        assert request.filter_ids == ["12345678", "", "99999999"]
        assert request.fallback_mapping == {
            "99999999": "Missing Title",
            "": "Title Only Title",
        }
        assert request.limit == 2
        assert request.primary_lookup_method == "pmid"
        assert request.fallback_operation == "fetch_filtered_with_fallback"
        assert request.resolve_fallback_handler() is adapter._fallback_handler
        assert request.resolve_normalize_id()(" 12345678 ") == "12345678"
        assert request.resolve_extract_record_id()({"pmid": "12345678"}) == "12345678"
        mock_logger.warning.assert_not_called()

    def test_pubmed_fallback_decorator_config(self, adapter: PubMedAdapter) -> None:
        """PubMed fallback config must keep permissive filter semantics."""
        config = adapter._fallback_decorator.config

        assert config.supported_filter_field is None
        assert config.skip_on_unsupported_filter_field is False
        assert config.primary_lookup_method == "pmid"
        assert config.fallback_operation == "fetch_filtered_with_fallback"
        assert (
            config.unsupported_filter_message
            == "PubMed fallback accepts any field and resolves via PMID/title phases"
        )


# =============================================================================
# Fallback Handler Integration Tests
# =============================================================================


class TestFallbackHandlerIntegration:
    """Tests for proper integration between PubMedAdapter and PubMedTitleFallbackHandler."""

    def test_fallback_handler_initialized(self, adapter: PubMedAdapter) -> None:
        """Test fallback handler is initialized in __post_init__."""
        assert adapter._fallback_handler is not None

    def test_fallback_handler_has_correct_search_fn(
        self, adapter: PubMedAdapter
    ) -> None:
        """Test fallback handler uses adapter's _search_by_title method."""
        assert adapter._fallback_handler is not None
        # The search_fn should be bound to adapter._search_by_title
        assert adapter._fallback_handler._search_fn == adapter._search_by_title

    @pytest.mark.asyncio
    async def test_fallback_handler_search_fn_callable(
        self, adapter: PubMedAdapter, mock_http_client: AsyncMock
    ) -> None:
        """Test the search function passed to handler is callable."""
        assert adapter._fallback_handler is not None
        esearch_response = MagicMock()
        esearch_response.json.return_value = {"esearchresult": {"idlist": []}}
        mock_http_client.get.return_value = esearch_response

        # Call search_fn through fallback handler
        result = await adapter._fallback_handler._search_fn("Test Title", 3)

        # Should return list (empty in this case)
        assert isinstance(result, list)
