"""Unit tests for Semantic Scholar fallback search utilities.

Tests for TitleFallbackHandler class.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from bioetl.infrastructure.adapters.semanticscholar.fallback import TitleFallbackHandler


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_logger():
    """Create a mock logger."""
    return MagicMock()


# =============================================================================
# TitleFallbackHandler Tests
# =============================================================================


class TestTitleFallbackHandler:
    """Tests for the TitleFallbackHandler class."""

    def test_event_names(self, mock_logger):
        """Test that event names are correctly prefixed."""

        async def mock_search(title):
            return
            yield

        handler = TitleFallbackHandler(logger=mock_logger, search_fn=mock_search)

        assert handler._event_no_fallback_title == "semanticscholar_no_fallback_title"
        assert (
            handler._event_fallback_attempt == "semanticscholar_title_fallback_attempt"
        )
        assert (
            handler._event_fallback_success == "semanticscholar_title_fallback_success"
        )
        assert (
            handler._event_fallback_not_found
            == "semanticscholar_title_fallback_not_found"
        )
        assert handler._event_title_only_attempt == "semanticscholar_title_only_attempt"
        assert handler._event_title_only_success == "semanticscholar_title_only_success"
        assert (
            handler._event_title_only_not_found
            == "semanticscholar_title_only_not_found"
        )

    def test_get_result_identifier(self, mock_logger):
        """Test that result identifier returns paper ID."""

        async def mock_search(title):
            return
            yield

        handler = TitleFallbackHandler(logger=mock_logger, search_fn=mock_search)

        result = {"paperId": "abc123", "title": "Test Paper"}
        field_name, value = handler._get_result_identifier(result)

        assert field_name == "found_paper_id"
        assert value == "abc123"

    def test_get_result_identifier_missing_id(self, mock_logger):
        """Test result identifier with missing paper ID."""

        async def mock_search(title):
            return
            yield

        handler = TitleFallbackHandler(logger=mock_logger, search_fn=mock_search)

        result = {"title": "Test Paper"}
        field_name, value = handler._get_result_identifier(result)

        assert field_name == "found_paper_id"
        assert value == "unknown"

    def test_process_found_result_adds_metadata(self, mock_logger):
        """Test that process_found_result adds lookup method metadata."""

        async def mock_search(title):
            return
            yield

        handler = TitleFallbackHandler(logger=mock_logger, search_fn=mock_search)

        result = {"paperId": "abc123", "title": "Test Paper"}
        processed = handler._process_found_result(result, "10.1234/original")

        assert processed["_lookup_method"] == "title_fallback"
        assert processed["_original_doi"] == "10.1234/original"

    @pytest.mark.asyncio
    async def test_search_by_title_success(self, mock_logger):
        """Test successful title search."""

        async def mock_search(title):
            yield {"paperId": "abc123", "title": "Crystal structure of rhodopsin"}

        handler = TitleFallbackHandler(logger=mock_logger, search_fn=mock_search)
        result = await handler._search_by_title("Crystal structure of rhodopsin")

        assert result is not None
        assert result["paperId"] == "abc123"

    @pytest.mark.asyncio
    async def test_search_by_title_validates_title_match(self, mock_logger):
        """Test that title matching validates results."""

        async def mock_search(title):
            yield {"paperId": "abc123", "title": "Completely different topic"}

        handler = TitleFallbackHandler(logger=mock_logger, search_fn=mock_search)
        result = await handler._search_by_title("Crystal structure of rhodopsin")

        # Should return None because titles don't match
        assert result is None

    @pytest.mark.asyncio
    async def test_search_by_title_no_results(self, mock_logger):
        """Test title search with no results."""

        async def mock_search(title):
            return
            yield

        handler = TitleFallbackHandler(logger=mock_logger, search_fn=mock_search)
        result = await handler._search_by_title("Nonexistent publication")

        assert result is None

    @pytest.mark.asyncio
    async def test_search_by_title_handles_exception(self, mock_logger):
        """Test that search errors are caught and logged."""

        async def mock_search(title):
            raise Exception("Search failed")
            yield

        handler = TitleFallbackHandler(logger=mock_logger, search_fn=mock_search)
        result = await handler._search_by_title("Test title")

        assert result is None
        mock_logger.debug.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_by_title_returns_first_matching(self, mock_logger):
        """Test that first matching result is returned."""

        async def mock_search(title):
            yield {"paperId": "wrong1", "title": "Wrong topic"}
            yield {"paperId": "correct", "title": "Crystal structure of rhodopsin"}
            yield {"paperId": "wrong2", "title": "Another wrong topic"}

        handler = TitleFallbackHandler(logger=mock_logger, search_fn=mock_search)
        result = await handler._search_by_title("Crystal structure of rhodopsin")

        assert result is not None
        assert result["paperId"] == "correct"

    @pytest.mark.asyncio
    async def test_search_by_title_returns_result_without_title(self, mock_logger):
        """Test that result without title field is returned."""

        async def mock_search(title):
            yield {"paperId": "abc123"}  # No title field

        handler = TitleFallbackHandler(logger=mock_logger, search_fn=mock_search)
        result = await handler._search_by_title("Any title")

        assert result is not None
        assert result["paperId"] == "abc123"


# =============================================================================
# Process Missing DOIs Tests
# =============================================================================


class TestProcessMissingDois:
    """Tests for process_missing_dois method."""

    @pytest.mark.asyncio
    async def test_process_missing_dois_success(self, mock_logger):
        """Test processing missing DOIs with successful fallback."""

        async def mock_search(title):
            yield {"paperId": "abc123", "title": "Crystal structure of rhodopsin"}

        handler = TitleFallbackHandler(logger=mock_logger, search_fn=mock_search)

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
        assert results[0]["_original_doi"] == "10.1234/notfound"

    @pytest.mark.asyncio
    async def test_process_missing_dois_skips_found(self, mock_logger):
        """Test that already-found DOIs are skipped."""
        search_called = []

        async def mock_search(title):
            search_called.append(title)
            return
            yield

        handler = TitleFallbackHandler(logger=mock_logger, search_fn=mock_search)

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
        assert len(search_called) == 0


# =============================================================================
# Process Title-Only Entries Tests
# =============================================================================


class TestProcessTitleOnlyEntries:
    """Tests for process_title_only_entries method."""

    @pytest.mark.asyncio
    async def test_process_title_only_success(self, mock_logger):
        """Test processing title-only entries with successful search."""

        async def mock_search(title):
            yield {"paperId": "abc123", "title": "Crystal structure of rhodopsin"}

        handler = TitleFallbackHandler(logger=mock_logger, search_fn=mock_search)

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
    async def test_process_title_only_no_mapping(self, mock_logger):
        """Test title-only processing with no title mapping."""

        async def mock_search(title):
            return
            yield

        handler = TitleFallbackHandler(logger=mock_logger, search_fn=mock_search)

        results = []
        async for pub in handler.process_title_only_entries(
            entries=[""],
            fallback_mapping={},  # No mapping
            limit=None,
            fetched=0,
        ):
            results.append(pub)

        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_process_title_only_respects_limit(self, mock_logger):
        """Test that limit is respected during title-only processing."""

        async def mock_search(title):
            yield {"paperId": "abc123", "title": title}

        handler = TitleFallbackHandler(logger=mock_logger, search_fn=mock_search)

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
