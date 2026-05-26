"""Unit tests for Semantic Scholar fallback search utilities.

Tests for SemanticScholarTitleFallbackHandler class.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.infrastructure.adapters.semanticscholar.fallback import (
    SemanticScholarTitleFallbackHandler,
    TitleFallbackHandler,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_logger():
    """Create a mock logger."""
    return MagicMock()


@pytest.fixture
def mock_http_client():
    """Create a mock HTTP client."""
    return AsyncMock()


@pytest.fixture
def mock_metrics():
    """Create a mock metrics instance."""
    metrics = MagicMock()
    # Make measure_request return a context manager
    metrics.measure_request.return_value.__enter__ = MagicMock()
    metrics.measure_request.return_value.__exit__ = MagicMock()
    return metrics


def create_mock_response(data: list[dict[str, Any]]) -> MagicMock:
    """Create a mock HTTP response with given data."""
    response = MagicMock()
    response.json.return_value = {"data": data}
    return response


# =============================================================================
# TitleFallbackHandler Tests
# =============================================================================


class TestSemanticScholarTitleFallbackHandler:
    """Tests for the SemanticScholarTitleFallbackHandler class."""

    def test_event_names(self, mock_logger, mock_http_client):
        """Test that event names are correctly defined."""
        handler = SemanticScholarTitleFallbackHandler(
            http_client=mock_http_client,
            logger=mock_logger,
        )

        assert handler._event_no_fallback_title == "semanticscholar_no_fallback_title"
        assert handler._event_fallback_attempt == "title_fallback_search"
        assert handler._event_fallback_success == "title_fallback_found"
        assert handler._event_fallback_not_found == "title_fallback_not_found"
        assert handler._event_title_only_attempt == "title_only_search"
        assert handler._event_title_only_success == "semanticscholar_title_only_success"
        assert (
            handler._event_title_only_not_found
            == "semanticscholar_title_only_not_found"
        )

    def test_backwards_compatibility_alias(self, mock_logger, mock_http_client):
        """Test that TitleFallbackHandler alias works."""
        handler = TitleFallbackHandler(
            http_client=mock_http_client,
            logger=mock_logger,
        )
        assert isinstance(handler, SemanticScholarTitleFallbackHandler)

    def test_get_result_identifier(self, mock_logger, mock_http_client):
        """Test that result identifier returns paper ID."""
        handler = SemanticScholarTitleFallbackHandler(
            http_client=mock_http_client,
            logger=mock_logger,
        )

        result = {"paperId": "abc123", "title": "Test Paper"}
        field_name, value = handler._get_result_identifier(result)

        assert field_name == "found_paper_id"
        assert value == "abc123"

    def test_get_result_identifier_missing_id(self, mock_logger, mock_http_client):
        """Test result identifier with missing paper ID."""
        handler = SemanticScholarTitleFallbackHandler(
            http_client=mock_http_client,
            logger=mock_logger,
        )

        result = {"title": "Test Paper"}
        field_name, value = handler._get_result_identifier(result)

        assert field_name == "found_paper_id"
        assert value == "unknown"

    def test_process_found_result_adds_metadata(self, mock_logger, mock_http_client):
        """Test that process_found_result adds lookup method metadata."""
        handler = SemanticScholarTitleFallbackHandler(
            http_client=mock_http_client,
            logger=mock_logger,
        )

        result = {"paperId": "abc123", "title": "Test Paper"}
        processed = handler._process_found_result(result, "10.1234/original")

        assert processed["_lookup_method"] == "title_fallback"
        assert processed["_original_id"] == "10.1234/original"

    def test_titles_match_method(self, mock_logger, mock_http_client):
        """Test the titles_match instance method."""
        handler = SemanticScholarTitleFallbackHandler(
            http_client=mock_http_client,
            logger=mock_logger,
        )

        # Case-insensitive match
        assert handler.titles_match("Crystal Structure", "crystal structure") is True
        # Partial match
        assert handler.titles_match("Crystal", "Crystal structure of rhodopsin") is True
        # No match
        assert handler.titles_match("Different topic", "Crystal structure") is False

    def test_escape_title_for_search(self, mock_logger, mock_http_client):
        """Test title escaping for search query."""
        handler = SemanticScholarTitleFallbackHandler(
            http_client=mock_http_client,
            logger=mock_logger,
        )

        # Test quote removal
        assert handler._escape_title_for_search('"Test" title') == "Test title"
        assert handler._escape_title_for_search("Test's title") == "Test s title"

        # Test whitespace normalization
        assert handler._escape_title_for_search("Test   title") == "Test title"

    def test_build_headers_without_api_key__test_semantic_scholar_title_fallback_handler_adapters_semanticscholar_test_fallback_154(
        self, mock_logger, mock_http_client
    ):
        """Test header building without API key."""
        handler = SemanticScholarTitleFallbackHandler(
            http_client=mock_http_client,
            logger=mock_logger,
        )

        headers = handler._build_headers()
        assert headers["User-Agent"] == "BioETL/1.0"
        assert headers["Accept"] == "application/json"
        assert "x-api-key" not in headers

    def test_build_headers_with_api_key__test_semantic_scholar_title_fallback_handler_adapters_semanticscholar_test_fallback_166(
        self, mock_logger, mock_http_client
    ):
        """Test header building with API key."""
        handler = SemanticScholarTitleFallbackHandler(
            http_client=mock_http_client,
            logger=mock_logger,
            api_key="test-api-key",
        )

        headers = handler._build_headers()
        assert headers["x-api-key"] == "test-api-key"

    @pytest.mark.asyncio
    async def test_search_by_title_success(self, mock_logger, mock_http_client):
        """Test successful title search."""
        mock_http_client.get_once.return_value = create_mock_response(
            [{"paperId": "abc123", "title": "Crystal structure of rhodopsin"}]
        )

        handler = SemanticScholarTitleFallbackHandler(
            http_client=mock_http_client,
            logger=mock_logger,
        )
        result = await handler._search_by_title("Crystal structure of rhodopsin")

        assert result is not None
        assert result["paperId"] == "abc123"
        mock_http_client.get_once.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_by_title_validates_title_match(
        self, mock_logger, mock_http_client
    ):
        """Test that title matching validates results."""
        mock_http_client.get_once.return_value = create_mock_response(
            [{"paperId": "abc123", "title": "Completely different topic"}]
        )

        handler = SemanticScholarTitleFallbackHandler(
            http_client=mock_http_client,
            logger=mock_logger,
        )
        result = await handler._search_by_title("Crystal structure of rhodopsin")

        # Should return None because titles don't match
        assert result is None

    @pytest.mark.asyncio
    async def test_search_by_title_no_results(self, mock_logger, mock_http_client):
        """Test title search with no results."""
        mock_http_client.get_once.return_value = create_mock_response([])

        handler = SemanticScholarTitleFallbackHandler(
            http_client=mock_http_client,
            logger=mock_logger,
        )
        result = await handler._search_by_title("Nonexistent publication")

        assert result is None

    @pytest.mark.asyncio
    async def test_search_by_title_handles_exception(
        self, mock_logger, mock_http_client
    ):
        """Test that search errors are caught and logged."""
        mock_http_client.get_once.side_effect = RuntimeError("Search failed")

        handler = SemanticScholarTitleFallbackHandler(
            http_client=mock_http_client,
            logger=mock_logger,
        )
        result = await handler._search_by_title("Test title")

        assert result is None
        mock_logger.debug.assert_called()

    @pytest.mark.asyncio
    async def test_search_by_title_returns_first_matching(
        self, mock_logger, mock_http_client
    ):
        """Test that first matching result is returned."""
        mock_http_client.get_once.return_value = create_mock_response(
            [
                {"paperId": "wrong1", "title": "Wrong topic"},
                {"paperId": "correct", "title": "Crystal structure of rhodopsin"},
                {"paperId": "wrong2", "title": "Another wrong topic"},
            ]
        )

        handler = SemanticScholarTitleFallbackHandler(
            http_client=mock_http_client,
            logger=mock_logger,
        )
        result = await handler._search_by_title("Crystal structure of rhodopsin")

        assert result is not None
        assert result["paperId"] == "correct"

    @pytest.mark.asyncio
    async def test_search_by_title_returns_result_without_title(
        self, mock_logger, mock_http_client
    ):
        """Test that result without title field is returned."""
        mock_http_client.get_once.return_value = create_mock_response(
            [{"paperId": "abc123"}]  # No title field
        )

        handler = SemanticScholarTitleFallbackHandler(
            http_client=mock_http_client,
            logger=mock_logger,
        )
        result = await handler._search_by_title("Any title")

        assert result is not None
        assert result["paperId"] == "abc123"

    @pytest.mark.asyncio
    async def test_search_with_metrics(
        self, mock_logger, mock_http_client, mock_metrics
    ):
        """Test that metrics are recorded when provided."""
        mock_http_client.get_once.return_value = create_mock_response(
            [{"paperId": "abc123", "title": "Test Paper"}]
        )

        handler = SemanticScholarTitleFallbackHandler(
            http_client=mock_http_client,
            logger=mock_logger,
            metrics=mock_metrics,
        )
        await handler._search_by_title("Test Paper")

        mock_metrics.measure_request.assert_called_once_with("/paper/search")


# =============================================================================
# Process Missing DOIs Tests
# =============================================================================


class TestProcessMissingDois:
    """Tests for process_missing_dois method."""

    @pytest.mark.asyncio
    async def test_process_missing_dois_success(self, mock_logger, mock_http_client):
        """Test processing missing DOIs with successful fallback."""
        mock_http_client.get_once.return_value = create_mock_response(
            [{"paperId": "abc123", "title": "Crystal structure of rhodopsin"}]
        )

        handler = SemanticScholarTitleFallbackHandler(
            http_client=mock_http_client,
            logger=mock_logger,
        )

        fallback_mapping = {
            "10.1234/notfound": "Crystal structure of rhodopsin",
        }

        results = []
        async for pub in handler.process_missing_dois(
            dois=["10.1234/notfound"],
            found_dois=set(),
            fallback_mapping=fallback_mapping,
            normalize_fn=lambda x: x.lower(),
            limit=None,
            fetched=0,
        ):
            results.append(pub)

        assert len(results) == 1
        assert results[0]["paperId"] == "abc123"
        assert results[0]["_lookup_method"] == "title_fallback"
        assert results[0]["_original_id"] == "10.1234/notfound"

    @pytest.mark.asyncio
    async def test_process_missing_dois_skips_found(
        self, mock_logger, mock_http_client
    ):
        """Test that already-found DOIs are skipped."""
        handler = SemanticScholarTitleFallbackHandler(
            http_client=mock_http_client,
            logger=mock_logger,
        )

        results = []
        async for pub in handler.process_missing_dois(
            dois=["10.1234/found"],
            found_dois={"10.1234/found"},  # Already found
            fallback_mapping={"10.1234/found": "Title"},
            normalize_fn=lambda x: x.lower(),
            limit=None,
            fetched=0,
        ):
            results.append(pub)

        assert len(results) == 0
        # HTTP client should not be called
        mock_http_client.get_once.assert_not_called()


# =============================================================================
# Process Title-Only Entries Tests
# =============================================================================


class TestProcessTitleOnlyEntries:
    """Tests for process_title_only_entries method."""

    @pytest.mark.asyncio
    async def test_process_title_only_success(self, mock_logger, mock_http_client):
        """Test processing title-only entries with successful search."""
        mock_http_client.get_once.return_value = create_mock_response(
            [{"paperId": "abc123", "title": "Crystal structure of rhodopsin"}]
        )

        handler = SemanticScholarTitleFallbackHandler(
            http_client=mock_http_client,
            logger=mock_logger,
        )

        fallback_mapping = {
            "": "Crystal structure of rhodopsin",
        }

        results = []
        async for pub in handler.process_title_only_entries(
            entries=[""],
            fallback_mapping=fallback_mapping,
            limit=None,
            fetched=0,
        ):
            results.append(pub)

        assert len(results) == 1
        assert results[0]["paperId"] == "abc123"
        assert results[0]["_lookup_method"] == "title_only"

    @pytest.mark.asyncio
    async def test_process_title_only_no_mapping(self, mock_logger, mock_http_client):
        """Test title-only processing with no title mapping."""
        handler = SemanticScholarTitleFallbackHandler(
            http_client=mock_http_client,
            logger=mock_logger,
        )

        results = []
        async for pub in handler.process_title_only_entries(
            entries=[""],
            fallback_mapping={},  # No mapping
            limit=None,
            fetched=0,
        ):
            results.append(pub)

        assert len(results) == 0
        # HTTP client should not be called
        mock_http_client.get_once.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_title_only_respects_limit(
        self, mock_logger, mock_http_client
    ):
        """Test that limit is respected during title-only processing."""
        # Return different papers for different titles
        mock_http_client.get_once.return_value = create_mock_response(
            [{"paperId": "abc123", "title": "Title 1"}]
        )

        handler = SemanticScholarTitleFallbackHandler(
            http_client=mock_http_client,
            logger=mock_logger,
        )

        fallback_mapping = {
            "": "Title 1",
            " ": "Title 2",
        }

        results = []
        async for pub in handler.process_title_only_entries(
            entries=["", " "],
            fallback_mapping=fallback_mapping,
            limit=2,
            fetched=1,  # Already fetched 1
        ):
            results.append(pub)

        # Should only process 1 more (limit=2, fetched=1)
        assert len(results) == 1
