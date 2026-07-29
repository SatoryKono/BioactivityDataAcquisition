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
"""Unit tests for OpenAlex fallback handler.

Tests the OpenAlexTitleFallbackHandler class for title-based search fallback.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.infrastructure.adapters.common._title_fallback_flow import (
    get_fallback_title,
    truncate_title,
)
from bioetl.infrastructure.adapters.openalex.fallback import (
    OpenAlexTitleFallbackHandler,
)


pytestmark = pytest.mark.unit


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
def handler(
    mock_logger: MagicMock, mock_search_fn: AsyncMock
) -> OpenAlexTitleFallbackHandler:
    """Create a fallback handler for testing."""
    return OpenAlexTitleFallbackHandler(logger=mock_logger, search_fn=mock_search_fn)


class TestGetFallbackTitle:
    """Tests for canonical fallback-title helper."""

    def test_get_title_with_original_id(self) -> None:
        """Should return title from original DOI."""
        fallback_mapping = {"10.1038/test": "Test Title"}
        result = get_fallback_title("10.1038/test", "10.1038/test", fallback_mapping)
        assert result == "Test Title"

    def test_get_title_with_normalized_doi(self) -> None:
        """Should fall back to normalized DOI."""
        fallback_mapping = {"10.1038/test": "Test Title"}
        result = get_fallback_title(
            "https://doi.org/10.1038/test", "10.1038/test", fallback_mapping
        )
        assert result == "Test Title"

    def test_get_title_without_normalized_doi(self) -> None:
        """Should work when normalized DOI is None."""
        fallback_mapping = {"10.1038/test": "Test Title"}
        result = get_fallback_title("10.1038/test", None, fallback_mapping)
        assert result == "Test Title"

    def test_get_title_not_found(self) -> None:
        """Should return None when title not in mapping."""
        fallback_mapping = {"other_doi": "Other Title"}
        result = get_fallback_title("10.1038/test", "10.1038/test", fallback_mapping)
        assert result is None


class TestTruncateTitle:
    """Tests for canonical title-truncation helper."""

    def test_truncate_short_title(self) -> None:
        """Should not truncate short titles."""
        result = truncate_title("Short title", max_len=50)
        assert result == "Short title"

    def test_truncate_long_title(self) -> None:
        """Should truncate long titles with ellipsis."""
        long_title = "A" * 100
        result = truncate_title(long_title, max_len=50)
        assert result == "A" * 50 + "..."
        assert len(result) == 53

    def test_truncate_exact_length(self) -> None:
        """Should not truncate titles at exact max length."""
        title = "A" * 50
        result = truncate_title(title, max_len=50)
        assert result == title
        assert "..." not in result


class TestProcessMissingDois:
    """Tests for process_missing_dois async generator."""

    @pytest.mark.asyncio
    async def test_process_found_doi_is_skipped(
        self, handler: OpenAlexTitleFallbackHandler, mock_search_fn: AsyncMock
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
        handler: OpenAlexTitleFallbackHandler,
        mock_search_fn: AsyncMock,
        mock_logger: MagicMock,
    ) -> None:
        """Should search by title and return work when DOI not found."""
        dois = ["10.1038/missing"]
        found_dois: set[str] = set()
        fallback_mapping = {"10.1038/missing": "Missing Title"}
        mock_search_fn.return_value = [
            {
                "id": "https://openalex.org/W123",
                "title": "Missing Title",
            }
        ]

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
        assert results[0]["_original_id"] == "10.1038/missing"
        mock_search_fn.assert_called_once_with("Missing Title", 3)

    @pytest.mark.asyncio
    async def test_process_missing_doi_with_fallback_not_found(
        self,
        handler: OpenAlexTitleFallbackHandler,
        mock_search_fn: AsyncMock,
        mock_logger: MagicMock,
    ) -> None:
        """Should log warning when title fallback doesn't find work."""
        dois = ["10.1038/notfound"]
        found_dois: set[str] = set()
        fallback_mapping = {"10.1038/notfound": "Not Found Title"}
        mock_search_fn.return_value = []  # No work found

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
        handler: OpenAlexTitleFallbackHandler,
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
        self, handler: OpenAlexTitleFallbackHandler, mock_search_fn: AsyncMock
    ) -> None:
        """Should stop when limit is reached."""
        dois = ["10.1038/test1", "10.1038/test2", "10.1038/test3"]
        found_dois: set[str] = set()
        fallback_mapping = {
            "10.1038/test1": "Title 1",
            "10.1038/test2": "Title 2",
            "10.1038/test3": "Title 3",
        }
        # Mock should return title matching the first DOI's mapping
        mock_search_fn.return_value = [{"id": "W123", "title": "Title 1"}]

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
        self, handler: OpenAlexTitleFallbackHandler, mock_search_fn: AsyncMock
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


class TestSearchByTitleEdgeCases:
    """Direct tests for _search_by_title fallback branches."""

    @pytest.mark.asyncio
    async def test_returns_first_no_title_candidate_when_no_match(
        self,
        handler: OpenAlexTitleFallbackHandler,
        mock_search_fn: AsyncMock,
    ) -> None:
        mock_search_fn.return_value = [
            {"id": "W1", "title": "Completely Different"},
            {"id": "W2", "title": ""},
            {"id": "W3"},
        ]

        result = await handler._search_by_title("Expected Title")

        assert result is not None
        assert result["id"] == "W2"

    @pytest.mark.asyncio
    async def test_returns_none_when_candidates_have_non_matching_titles(
        self,
        handler: OpenAlexTitleFallbackHandler,
        mock_search_fn: AsyncMock,
    ) -> None:
        mock_search_fn.return_value = [
            {"id": "W1", "title": "Different A"},
            {"id": "W2", "title": "Different B"},
        ]

        result = await handler._search_by_title("Expected Title")

        assert result is None
