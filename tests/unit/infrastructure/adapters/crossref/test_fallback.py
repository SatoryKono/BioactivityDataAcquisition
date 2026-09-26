# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Unit tests for CrossRef fallback search utilities.

Tests for CrossRefTitleFallbackHandler and title matching functions.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.infrastructure.adapters.common._title_fallback_flow import (
    get_fallback_title,
    truncate_title,
)
from bioetl.infrastructure.adapters.crossref.fallback import (
    CrossRefTitleFallbackHandler,
    titles_match,
)
from tests.helpers.async_iterables import async_iterable, failing_async_iterable

pytestmark = pytest.mark.unit

# =============================================================================
# titles_match Tests
# =============================================================================


class TestTitlesMatch:
    """Tests for the titles_match function."""

    def test_fallback_titles_match__exact_match__74cc140c(self):
        """Test exact title match."""
        assert titles_match(
            "Crystal structure of rhodopsin",
            "Crystal structure of rhodopsin",
        )

    def test_case_insensitive_match(self):
        """Test case-insensitive matching."""
        assert titles_match(
            "Crystal Structure of Rhodopsin",
            "crystal structure of rhodopsin",
        )

    def test_fallback_titles_match__whitespace_handling__1f564cf5(self):
        """Test whitespace is stripped."""
        assert titles_match("  Crystal structure  ", "Crystal structure")

    def test_substring_query_in_found(self):
        """Test query is substring of found title."""
        assert titles_match(
            "Crystal structure",
            "Crystal structure of rhodopsin bound to arrestin",
        )

    def test_substring_found_in_query(self):
        """Test found title is substring of query."""
        assert titles_match(
            "Crystal structure of rhodopsin bound to arrestin",
            "Crystal structure",
        )

    def test_no_match(self):
        """Test non-matching titles."""
        assert not titles_match(
            "Crystal structure of rhodopsin",
            "Protein folding mechanisms",
        )

    def test_empty_strings(self):
        """Empty titles never match (fail-closed for fallback quality)."""
        assert titles_match("", "") is False
        assert titles_match("Title", "") is False
        assert titles_match("", "Title") is False


# =============================================================================
# CrossRefTitleFallbackHandler Tests
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
    """Create a CrossRefTitleFallbackHandler instance."""
    return CrossRefTitleFallbackHandler(
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

    handler = CrossRefTitleFallbackHandler(logger=mock_logger, search_fn=mock_search)
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

    handler = CrossRefTitleFallbackHandler(logger=mock_logger, search_fn=mock_search)
    result = await handler.search_by_title("Crystal structure of rhodopsin")

    assert result is None


@pytest.mark.asyncio
async def test_search_by_title_empty_results(mock_logger):
    """Test title search with no results."""

    def mock_search(query, limit) -> AsyncIterator[dict[str, object]]:
        del query, limit
        return async_iterable()

    handler = CrossRefTitleFallbackHandler(logger=mock_logger, search_fn=mock_search)
    result = await handler.search_by_title("Nonexistent publication")

    assert result is None


@pytest.mark.asyncio
async def test_search_by_title_truncates_long_title(mock_logger):
    """Test that long titles are truncated to 200 chars for search."""
    long_title = "A" * 300
    query_received = []

    def mock_search(query, limit) -> AsyncIterator[dict[str, object]]:
        query_received.append(query)
        del limit
        return async_iterable()

    handler = CrossRefTitleFallbackHandler(logger=mock_logger, search_fn=mock_search)
    await handler.search_by_title(long_title)

    # Verify the query was truncated (200 chars + quotes + "title:")
    assert len(query_received) == 1
    assert len(query_received[0]) <= 210


@pytest.mark.asyncio
async def test_search_by_title_handles_exception(mock_logger):
    """Test that search errors are caught and logged."""

    def mock_search(query, limit) -> AsyncIterator[dict[str, object]]:
        del query, limit
        return failing_async_iterable(RuntimeError("Search failed"))

    handler = CrossRefTitleFallbackHandler(logger=mock_logger, search_fn=mock_search)
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

    handler = CrossRefTitleFallbackHandler(logger=mock_logger, search_fn=mock_search)
    result = await handler.search_by_title("Crystal structure of rhodopsin")

    assert result is not None
    assert result["DOI"] == "10.1038/nature12373"


def test_get_fallback_title():
    """Test getting fallback title from mapping."""
    mapping = {
        "10.1038/nature12373": "Crystal structure",
        "10.1016/j.cell.2019.03.025": "Cell paper",
    }

    # Direct match
    title = get_fallback_title("10.1038/nature12373", "10.1038/nature12373", mapping)
    assert title == "Crystal structure"

    # Normalized DOI match
    title = get_fallback_title(
        "10.1038/NATURE12373",  # Uppercase original
        "10.1038/nature12373",  # Lowercase normalized
        mapping,
    )
    assert title == "Crystal structure"

    # No match
    title = get_fallback_title("10.1234/unknown", "10.1234/unknown", mapping)
    assert title is None


def test_truncate_title():
    """Test title truncation for logging."""
    short_title = "Short title"
    assert truncate_title(short_title) == "Short title"

    long_title = "A" * 100
    truncated = truncate_title(long_title, max_len=50)
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

    handler = CrossRefTitleFallbackHandler(logger=mock_logger, search_fn=mock_search)

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
        del limit
        search_called.append(query)
        for _ in ():
            yield {}

    handler = CrossRefTitleFallbackHandler(logger=mock_logger, search_fn=mock_search)

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
        del query, limit
        for _ in ():
            yield {}

    handler = CrossRefTitleFallbackHandler(logger=mock_logger, search_fn=mock_search)

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

    handler = CrossRefTitleFallbackHandler(logger=mock_logger, search_fn=mock_search)

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
        del query, limit
        for _ in ():
            yield {}

    handler = CrossRefTitleFallbackHandler(logger=mock_logger, search_fn=mock_search)

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


# =============================================================================
# Phase 3: Title-Only Entry Tests
# =============================================================================


def test_title_only_event_names(mock_logger, mock_search_fn):
    """Test that title-only event names are correctly prefixed."""
    handler = CrossRefTitleFallbackHandler(logger=mock_logger, search_fn=mock_search_fn)

    assert handler._event_title_only_attempt == "crossref_title_only_attempt"
    assert handler._event_title_only_success == "crossref_title_only_success"
    assert handler._event_title_only_not_found == "crossref_title_only_not_found"


def test_process_found_result_adds_metadata(mock_logger, mock_search_fn):
    """Test that process_found_result adds lookup method metadata."""
    handler = CrossRefTitleFallbackHandler(logger=mock_logger, search_fn=mock_search_fn)

    result = {"DOI": "10.1038/nature12373", "title": ["Test Paper"]}
    processed = handler._process_found_result(result, "10.1234/original")

    assert processed["_lookup_method"] == "title_fallback"
    assert processed["_original_id"] == "10.1234/original"


@pytest.mark.asyncio
async def test_process_title_only_entries_success(mock_logger):
    """Test processing title-only entries with successful search."""

    async def mock_search(query, limit):
        yield {
            "DOI": "10.1038/nature12373",
            "title": ["Crystal structure of rhodopsin"],
        }

    handler = CrossRefTitleFallbackHandler(logger=mock_logger, search_fn=mock_search)

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
    assert results[0]["DOI"] == "10.1038/nature12373"
    assert results[0]["_lookup_method"] == "title_only"
    mock_logger.info.assert_called()  # Should log title-only attempt and success


@pytest.mark.asyncio
async def test_process_title_only_entries_no_mapping(mock_logger):
    """Test title-only processing with no title mapping."""

    async def mock_search(query, limit):
        del query, limit
        for _ in ():
            yield {}

    handler = CrossRefTitleFallbackHandler(logger=mock_logger, search_fn=mock_search)

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
async def test_process_title_only_entries_respects_limit(mock_logger):
    """Test that limit is respected during title-only processing."""

    async def mock_search(query, limit):
        yield {"DOI": "10.found/1", "title": ["Title 1"]}

    handler = CrossRefTitleFallbackHandler(logger=mock_logger, search_fn=mock_search)

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


@pytest.mark.asyncio
async def test_process_title_only_entries_not_found(mock_logger):
    """Test title-only processing when search returns no results."""

    async def mock_search(query, limit):
        del query, limit
        for _ in ():
            yield {}

    handler = CrossRefTitleFallbackHandler(logger=mock_logger, search_fn=mock_search)

    fallback_mapping = {
        "": "Some title",
    }

    results = []
    async for pub in handler.process_title_only_entries(
        entries=[""],
        fallback_mapping=fallback_mapping,
        limit=None,
        fetched=0,
    ):
        results.append(pub)

    assert len(results) == 0
    mock_logger.debug.assert_called()  # Should log title-only not found
