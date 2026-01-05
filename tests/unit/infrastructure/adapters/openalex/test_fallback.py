"""Unit tests for OpenAlex fallback handler.

Tests the TitleFallbackHandler class for title-based search fallback.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.infrastructure.adapters.openalex.fallback import TitleFallbackHandler


@pytest.fixture
def mock_logger() -> MagicMock:
    """Create a mock logger."""
    logger = MagicMock()
    logger.debug = MagicMock()
    logger.info = MagicMock()
    logger.warning = MagicMock()
    return logger


@pytest.fixture
def mock_search_fn() -> AsyncMock:
    """Create a mock search function."""
    return AsyncMock()


@pytest.fixture
def handler(mock_logger: MagicMock, mock_search_fn: AsyncMock) -> TitleFallbackHandler:
    """Create a fallback handler for testing."""
    return TitleFallbackHandler(logger=mock_logger, search_fn=mock_search_fn)


class TestGetFallbackTitle:
    """Tests for _get_fallback_title method."""

    def test_get_title_with_original_doi(self, handler: TitleFallbackHandler) -> None:
        """Should return title from original DOI."""
        fallback_mapping = {"10.1038/test": "Test Title"}
        result = handler._get_fallback_title(
            "10.1038/test", "10.1038/test", fallback_mapping
        )
        assert result == "Test Title"

    def test_get_title_with_normalized_doi(self, handler: TitleFallbackHandler) -> None:
        """Should fall back to normalized DOI."""
        fallback_mapping = {"10.1038/test": "Test Title"}
        result = handler._get_fallback_title(
            "https://doi.org/10.1038/test", "10.1038/test", fallback_mapping
        )
        assert result == "Test Title"

    def test_get_title_without_normalized_doi(
        self, handler: TitleFallbackHandler
    ) -> None:
        """Should work when normalized DOI is None."""
        fallback_mapping = {"10.1038/test": "Test Title"}
        result = handler._get_fallback_title("10.1038/test", None, fallback_mapping)
        assert result == "Test Title"

    def test_get_title_not_found(self, handler: TitleFallbackHandler) -> None:
        """Should return None when title not in mapping."""
        fallback_mapping = {"other_doi": "Other Title"}
        result = handler._get_fallback_title(
            "10.1038/test", "10.1038/test", fallback_mapping
        )
        assert result is None


class TestTruncateTitle:
    """Tests for _truncate_title method."""

    def test_truncate_short_title(self, handler: TitleFallbackHandler) -> None:
        """Should not truncate short titles."""
        result = handler._truncate_title("Short title", max_len=50)
        assert result == "Short title"

    def test_truncate_long_title(self, handler: TitleFallbackHandler) -> None:
        """Should truncate long titles with ellipsis."""
        long_title = "A" * 100
        result = handler._truncate_title(long_title, max_len=50)
        assert result == "A" * 50 + "..."
        assert len(result) == 53

    def test_truncate_exact_length(self, handler: TitleFallbackHandler) -> None:
        """Should not truncate titles at exact max length."""
        title = "A" * 50
        result = handler._truncate_title(title, max_len=50)
        assert result == title
        assert "..." not in result


class TestProcessMissingDois:
    """Tests for process_missing_dois async generator."""

    @pytest.mark.asyncio
    async def test_process_found_doi_is_skipped(
        self, handler: TitleFallbackHandler, mock_search_fn: AsyncMock
    ) -> None:
        """Should skip DOIs that were already found."""
        dois = ["10.1038/test"]
        found_dois = {"10.1038/test"}  # Already found
        fallback_mapping = {"10.1038/test": "Test Title"}

        results = []
        async for work in handler.process_missing_dois(
            dois=dois,
            found_dois=found_dois,
            fallback_mapping=fallback_mapping,
            normalize_fn=lambda x: x,
            limit=None,
            fetched=0,
        ):
            results.append(work)

        assert len(results) == 0
        mock_search_fn.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_missing_doi_with_fallback_success(
        self,
        handler: TitleFallbackHandler,
        mock_search_fn: AsyncMock,
        mock_logger: MagicMock,
    ) -> None:
        """Should search by title and return work when DOI not found."""
        dois = ["10.1038/missing"]
        found_dois: set[str] = set()
        fallback_mapping = {"10.1038/missing": "Missing Title"}
        mock_search_fn.return_value = {
            "id": "https://openalex.org/W123",
            "title": "Missing Title",
        }

        results = []
        async for work in handler.process_missing_dois(
            dois=dois,
            found_dois=found_dois,
            fallback_mapping=fallback_mapping,
            normalize_fn=lambda x: x,
            limit=None,
            fetched=0,
        ):
            results.append(work)

        assert len(results) == 1
        assert results[0]["_lookup_method"] == "title_fallback"
        assert results[0]["_original_doi"] == "10.1038/missing"
        mock_search_fn.assert_called_once_with("Missing Title", 3)

    @pytest.mark.asyncio
    async def test_process_missing_doi_with_fallback_not_found(
        self,
        handler: TitleFallbackHandler,
        mock_search_fn: AsyncMock,
        mock_logger: MagicMock,
    ) -> None:
        """Should log warning when title fallback doesn't find work."""
        dois = ["10.1038/notfound"]
        found_dois: set[str] = set()
        fallback_mapping = {"10.1038/notfound": "Not Found Title"}
        mock_search_fn.return_value = None  # No work found

        results = []
        async for work in handler.process_missing_dois(
            dois=dois,
            found_dois=found_dois,
            fallback_mapping=fallback_mapping,
            normalize_fn=lambda x: x,
            limit=None,
            fetched=0,
        ):
            results.append(work)

        assert len(results) == 0
        mock_logger.warning.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_missing_doi_without_title(
        self,
        handler: TitleFallbackHandler,
        mock_search_fn: AsyncMock,
        mock_logger: MagicMock,
    ) -> None:
        """Should skip DOI when no title in fallback mapping."""
        dois = ["10.1038/notitle"]
        found_dois: set[str] = set()
        fallback_mapping = {}  # No title for DOI

        results = []
        async for work in handler.process_missing_dois(
            dois=dois,
            found_dois=found_dois,
            fallback_mapping=fallback_mapping,
            normalize_fn=lambda x: x,
            limit=None,
            fetched=0,
        ):
            results.append(work)

        assert len(results) == 0
        mock_search_fn.assert_not_called()
        mock_logger.debug.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_respects_limit(
        self, handler: TitleFallbackHandler, mock_search_fn: AsyncMock
    ) -> None:
        """Should stop when limit is reached."""
        dois = ["10.1038/test1", "10.1038/test2", "10.1038/test3"]
        found_dois: set[str] = set()
        fallback_mapping = {
            "10.1038/test1": "Title 1",
            "10.1038/test2": "Title 2",
            "10.1038/test3": "Title 3",
        }
        mock_search_fn.return_value = {"id": "W123", "title": "Found"}

        results = []
        async for work in handler.process_missing_dois(
            dois=dois,
            found_dois=found_dois,
            fallback_mapping=fallback_mapping,
            normalize_fn=lambda x: x,
            limit=2,  # Only fetch 2
            fetched=1,  # Already fetched 1
        ):
            results.append(work)

        # Should only get 1 more (limit=2, fetched=1, so 1 remaining)
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_process_with_normalized_doi_lookup(
        self, handler: TitleFallbackHandler, mock_search_fn: AsyncMock
    ) -> None:
        """Should normalize DOIs when checking found set."""
        dois = ["https://doi.org/10.1038/TEST"]  # URL format, uppercase
        found_dois = {"10.1038/test"}  # lowercase normalized
        fallback_mapping = {"https://doi.org/10.1038/TEST": "Test Title"}

        def normalize(doi: str) -> str:
            """Simple normalize for test."""
            if doi.startswith("https://doi.org/"):
                return doi[16:]
            return doi

        results = []
        async for work in handler.process_missing_dois(
            dois=dois,
            found_dois=found_dois,
            fallback_mapping=fallback_mapping,
            normalize_fn=normalize,
            limit=None,
            fetched=0,
        ):
            results.append(work)

        # Should skip because normalized DOI is in found_dois
        assert len(results) == 0
        mock_search_fn.assert_not_called()
