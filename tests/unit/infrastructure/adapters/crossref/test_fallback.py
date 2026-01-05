"""Unit tests for CrossRef fallback search utilities.

Tests for TitleFallbackHandler and title matching functions.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.infrastructure.adapters.crossref.fallback import (
    TitleFallbackHandler,
    titles_match,
)

# =============================================================================
# titles_match Tests
# =============================================================================


class TestTitlesMatch:
    """Tests for the titles_match function."""

    def test_exact_match(self):
        """Test exact title match."""
        assert (
            titles_match(
                "Crystal structure of rhodopsin", "Crystal structure of rhodopsin"
            )
            is True
        )

    def test_case_insensitive_match(self):
        """Test case-insensitive matching."""
        assert (
            titles_match(
                "Crystal Structure of Rhodopsin", "crystal structure of rhodopsin"
            )
            is True
        )

    def test_whitespace_handling(self):
        """Test whitespace is stripped."""
        assert titles_match("  Crystal structure  ", "Crystal structure") is True

    def test_substring_query_in_found(self):
        """Test query is substring of found title."""
        assert (
            titles_match(
                "Crystal structure", "Crystal structure of rhodopsin bound to arrestin"
            )
            is True
        )

    def test_substring_found_in_query(self):
        """Test found title is substring of query."""
        assert (
            titles_match(
                "Crystal structure of rhodopsin bound to arrestin", "Crystal structure"
            )
            is True
        )

    def test_no_match(self):
        """Test non-matching titles."""
        assert (
            titles_match("Crystal structure of rhodopsin", "Protein folding mechanisms")
            is False
        )

    def test_empty_strings(self):
        """Test empty string handling."""
        assert titles_match("", "") is True  # Both empty = match
        # Empty string is substring of any string, so this returns True
        assert titles_match("Title", "") is True  # Empty is substring of "title"
        assert titles_match("", "Title") is True  # Empty is substring of "title"


# =============================================================================
# TitleFallbackHandler Tests
# =============================================================================


@pytest.fixture
def mock_logger():
    """Create a mock logger."""
    return MagicMock()


@pytest.fixture
def mock_search_fn():
    """Create a mock search function."""
    return AsyncMock()


@pytest.fixture
def fallback_handler(mock_logger, mock_search_fn):
    """Create a TitleFallbackHandler instance."""
    return TitleFallbackHandler(
        logger=mock_logger,
        search_fn=mock_search_fn,
    )


@pytest.mark.asyncio
async def test_search_by_title_success(mock_logger):
    """Test successful title search."""

    async def mock_search(query, limit):
        yield {
            "DOI": "10.1038/nature12373",
            "title": ["Crystal structure of rhodopsin"],
        }

    handler = TitleFallbackHandler(logger=mock_logger, search_fn=mock_search)
    result = await handler.search_by_title("Crystal structure of rhodopsin")

    assert result is not None
    assert result["DOI"] == "10.1038/nature12373"


@pytest.mark.asyncio
async def test_search_by_title_no_match(mock_logger):
    """Test title search returns None when no relevant match."""

    async def mock_search(query, limit):
        yield {
            "DOI": "10.1234/unrelated",
            "title": ["Completely different topic"],
        }

    handler = TitleFallbackHandler(logger=mock_logger, search_fn=mock_search)
    result = await handler.search_by_title("Crystal structure of rhodopsin")

    assert result is None


@pytest.mark.asyncio
async def test_search_by_title_empty_results(mock_logger):
    """Test title search with no results."""

    async def mock_search(query, limit):
        return
        yield  # Make it a generator

    handler = TitleFallbackHandler(logger=mock_logger, search_fn=mock_search)
    result = await handler.search_by_title("Nonexistent publication")

    assert result is None


@pytest.mark.asyncio
async def test_search_by_title_truncates_long_title(mock_logger):
    """Test that long titles are truncated to 200 chars for search."""
    long_title = "A" * 300
    query_received = []

    async def mock_search(query, limit):
        query_received.append(query)
        return
        yield

    handler = TitleFallbackHandler(logger=mock_logger, search_fn=mock_search)
    await handler.search_by_title(long_title)

    # Verify the query was truncated (200 chars + quotes + "title:")
    assert len(query_received) == 1
    assert len(query_received[0]) <= 210


@pytest.mark.asyncio
async def test_search_by_title_handles_exception(mock_logger):
    """Test that search errors are caught and logged."""

    async def mock_search(query, limit):
        raise Exception("Search failed")
        yield

    handler = TitleFallbackHandler(logger=mock_logger, search_fn=mock_search)
    result = await handler.search_by_title("Test title")

    assert result is None
    mock_logger.debug.assert_called_once()


@pytest.mark.asyncio
async def test_search_by_title_checks_multiple_results(mock_logger):
    """Test that multiple results are checked for relevance."""

    async def mock_search(query, limit):
        # First result is irrelevant
        yield {"DOI": "10.1234/irrelevant", "title": ["Wrong topic"]}
        # Second result matches
        yield {
            "DOI": "10.1038/nature12373",
            "title": ["Crystal structure of rhodopsin"],
        }

    handler = TitleFallbackHandler(logger=mock_logger, search_fn=mock_search)
    result = await handler.search_by_title("Crystal structure of rhodopsin")

    assert result is not None
    assert result["DOI"] == "10.1038/nature12373"


def test_get_fallback_title(fallback_handler):
    """Test getting fallback title from mapping."""
    mapping = {
        "10.1038/nature12373": "Crystal structure",
        "10.1016/j.cell.2019.03.025": "Cell paper",
    }

    # Direct match
    title = fallback_handler._get_fallback_title(
        "10.1038/nature12373", "10.1038/nature12373", mapping
    )
    assert title == "Crystal structure"

    # Normalized DOI match
    title = fallback_handler._get_fallback_title(
        "10.1038/NATURE12373",  # Uppercase original
        "10.1038/nature12373",  # Lowercase normalized
        mapping,
    )
    assert title == "Crystal structure"

    # No match
    title = fallback_handler._get_fallback_title(
        "10.1234/unknown", "10.1234/unknown", mapping
    )
    assert title is None


def test_truncate_title(fallback_handler):
    """Test title truncation for logging."""
    short_title = "Short title"
    assert fallback_handler._truncate_title(short_title) == "Short title"

    long_title = "A" * 100
    truncated = fallback_handler._truncate_title(long_title, max_len=50)
    assert len(truncated) == 53  # 50 + "..."
    assert truncated.endswith("...")


@pytest.mark.asyncio
async def test_process_missing_dois_success(mock_logger):
    """Test processing missing DOIs with successful fallback."""

    async def mock_search(query, limit):
        yield {
            "DOI": "10.1038/nature12373",
            "title": ["Crystal structure of rhodopsin"],
        }

    handler = TitleFallbackHandler(logger=mock_logger, search_fn=mock_search)

    fallback_mapping = {
        "10.1234/notfound": "Crystal structure of rhodopsin",
    }

    results = []
    async for pub in handler.process_missing_dois(
        dois=["10.1234/notfound"],
        found_dois=set(),  # None found in batch
        fallback_mapping=fallback_mapping,
        normalize_fn=lambda x: x.lower(),
        limit=None,
        fetched=0,
    ):
        results.append(pub)

    assert len(results) == 1
    assert results[0]["DOI"] == "10.1038/nature12373"
    mock_logger.info.assert_called()  # Should log fallback success


@pytest.mark.asyncio
async def test_process_missing_dois_skips_found(mock_logger):
    """Test that already-found DOIs are skipped."""
    search_called = []

    async def mock_search(query, limit):
        search_called.append(query)
        return
        yield

    handler = TitleFallbackHandler(logger=mock_logger, search_fn=mock_search)

    results = []
    async for pub in handler.process_missing_dois(
        dois=["10.1038/nature12373"],
        found_dois={"10.1038/nature12373"},  # Already found
        fallback_mapping={"10.1038/nature12373": "Title"},
        normalize_fn=lambda x: x.lower(),
        limit=None,
        fetched=0,
    ):
        results.append(pub)

    assert len(results) == 0
    assert len(search_called) == 0


@pytest.mark.asyncio
async def test_process_missing_dois_no_fallback_title(mock_logger):
    """Test behavior when no fallback title is available."""

    async def mock_search(query, limit):
        return
        yield

    handler = TitleFallbackHandler(logger=mock_logger, search_fn=mock_search)

    results = []
    async for pub in handler.process_missing_dois(
        dois=["10.1234/notfound"],
        found_dois=set(),
        fallback_mapping={},  # No mapping available
        normalize_fn=lambda x: x.lower(),
        limit=None,
        fetched=0,
    ):
        results.append(pub)

    assert len(results) == 0
    mock_logger.debug.assert_called_with(
        "crossref_no_fallback_title", doi="10.1234/notfound"
    )


@pytest.mark.asyncio
async def test_process_missing_dois_respects_limit(mock_logger):
    """Test that limit is respected during fallback processing."""

    async def mock_search(query, limit):
        yield {"DOI": "10.found/1", "title": ["Title 1"]}

    handler = TitleFallbackHandler(logger=mock_logger, search_fn=mock_search)

    results = []
    async for pub in handler.process_missing_dois(
        dois=["10.1234/a", "10.1234/b", "10.1234/c"],
        found_dois=set(),
        fallback_mapping={
            "10.1234/a": "Title 1",
            "10.1234/b": "Title 2",
            "10.1234/c": "Title 3",
        },
        normalize_fn=lambda x: x.lower(),
        limit=2,
        fetched=1,  # Already fetched 1
    ):
        results.append(pub)

    # Should only process 1 more (limit=2, fetched=1)
    assert len(results) == 1


@pytest.mark.asyncio
async def test_process_missing_dois_logs_not_found(mock_logger):
    """Test that failed fallback search is logged."""

    async def mock_search(query, limit):
        return
        yield

    handler = TitleFallbackHandler(logger=mock_logger, search_fn=mock_search)

    results = []
    async for pub in handler.process_missing_dois(
        dois=["10.1234/notfound"],
        found_dois=set(),
        fallback_mapping={"10.1234/notfound": "Some title"},
        normalize_fn=lambda x: x.lower(),
        limit=None,
        fetched=0,
    ):
        results.append(pub)

    assert len(results) == 0
    mock_logger.warning.assert_called()  # Should log fallback not found
