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
"""Unit tests for PubMed fallback handler.

Tests the PubMedTitleFallbackHandler class for title-based search fallback.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.infrastructure.adapters.pubmed.fallback import PubMedTitleFallbackHandler


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
) -> PubMedTitleFallbackHandler:
    """Create a fallback handler for testing."""
    return PubMedTitleFallbackHandler(logger=mock_logger, search_fn=mock_search_fn)


class TestEventProperties:
    """Tests for event name properties."""

    def test_event_no_fallback_title(self, handler: PubMedTitleFallbackHandler) -> None:
        """Should return pubmed-specific event name."""
        assert handler._event_no_fallback_title == "pubmed_no_fallback_title"

    def test_event_fallback_attempt(self, handler: PubMedTitleFallbackHandler) -> None:
        """Should return pubmed-specific event name."""
        assert handler._event_fallback_attempt == "pubmed_title_fallback_attempt"

    def test_event_fallback_success(self, handler: PubMedTitleFallbackHandler) -> None:
        """Should return pubmed-specific event name."""
        assert handler._event_fallback_success == "pubmed_title_fallback_success"

    def test_event_fallback_not_found(
        self, handler: PubMedTitleFallbackHandler
    ) -> None:
        """Should return pubmed-specific event name."""
        assert handler._event_fallback_not_found == "pubmed_title_fallback_not_found"

    def test_event_title_only_attempt(
        self, handler: PubMedTitleFallbackHandler
    ) -> None:
        """Should return pubmed-specific event name."""
        assert handler._event_title_only_attempt == "pubmed_title_only_attempt"

    def test_event_title_only_success(
        self, handler: PubMedTitleFallbackHandler
    ) -> None:
        """Should return pubmed-specific event name."""
        assert handler._event_title_only_success == "pubmed_title_only_success"

    def test_event_title_only_not_found(
        self, handler: PubMedTitleFallbackHandler
    ) -> None:
        """Should return pubmed-specific event name."""
        assert handler._event_title_only_not_found == "pubmed_title_only_not_found"


class TestGetResultIdentifier:
    """Tests for _get_result_identifier method."""

    def test_get_identifier_with_pmid(
        self, handler: PubMedTitleFallbackHandler
    ) -> None:
        """Should return PMID from record."""
        result = handler._get_result_identifier({"pmid": "12345678"})
        assert result == ("found_pmid", "12345678")

    def test_get_identifier_without_pmid(
        self, handler: PubMedTitleFallbackHandler
    ) -> None:
        """Should return 'unknown' when no PMID."""
        result = handler._get_result_identifier({})
        assert result == ("found_pmid", "unknown")


class TestProcessFoundResult:
    """Tests for _process_found_result method."""

    def test_adds_lookup_method(self, handler: PubMedTitleFallbackHandler) -> None:
        """Should add _lookup_method field."""
        record = {"pmid": "12345678", "article_title": "Test"}
        result = handler._process_found_result(record, "10.1234/test")

        assert result["_lookup_method"] == "title_fallback"

    def test_adds_original_id(self, handler: PubMedTitleFallbackHandler) -> None:
        """Should add _original_id field."""
        record = {"pmid": "12345678", "article_title": "Test"}
        result = handler._process_found_result(record, "10.1234/test")

        assert result["_original_id"] == "10.1234/test"


class TestSearchByTitle:
    """Tests for _search_by_title method."""

    @pytest.mark.asyncio
    async def test_search_found_with_matching_title(
        self, handler: PubMedTitleFallbackHandler, mock_search_fn: AsyncMock
    ) -> None:
        """Should return publication when title matches."""
        mock_search_fn.return_value = [
            {"pmid": "12345678", "article_title": "Test Publication Title"}
        ]

        result = await handler._search_by_title("Test Publication Title")

        assert result is not None
        assert result["pmid"] == "12345678"
        mock_search_fn.assert_called_once_with("Test Publication Title", 3)

    @pytest.mark.asyncio
    async def test_search_found_with_case_insensitive_match(
        self, handler: PubMedTitleFallbackHandler, mock_search_fn: AsyncMock
    ) -> None:
        """Should match titles case-insensitively."""
        mock_search_fn.return_value = [
            {"pmid": "12345678", "article_title": "TEST PUBLICATION TITLE"}
        ]

        result = await handler._search_by_title("test publication title")

        assert result is not None
        assert result["pmid"] == "12345678"

    @pytest.mark.asyncio
    async def test_search_found_with_substring_match(
        self, handler: PubMedTitleFallbackHandler, mock_search_fn: AsyncMock
    ) -> None:
        """Should match when query is substring of found title."""
        mock_search_fn.return_value = [
            {
                "pmid": "12345678",
                "article_title": "Test Publication Title: Extended Subtitle",
            }
        ]

        result = await handler._search_by_title("Test Publication Title")

        assert result is not None
        assert result["pmid"] == "12345678"

    @pytest.mark.asyncio
    async def test_search_empty_results(
        self, handler: PubMedTitleFallbackHandler, mock_search_fn: AsyncMock
    ) -> None:
        """Should return None when no results."""
        mock_search_fn.return_value = []

        result = await handler._search_by_title("Nonexistent Title")

        assert result is None

    @pytest.mark.asyncio
    async def test_search_returns_none_when_no_title_match(
        self, handler: PubMedTitleFallbackHandler, mock_search_fn: AsyncMock
    ) -> None:
        mock_search_fn.return_value = [
            {"pmid": "12345678", "article_title": "Completely Different Title"}
        ]

        result = await handler._search_by_title("Test Publication Title")

        assert result is None

    @pytest.mark.asyncio
    async def test_search_handles_exception(
        self,
        handler: PubMedTitleFallbackHandler,
        mock_search_fn: AsyncMock,
        mock_logger: MagicMock,
    ) -> None:
        """Should return None and log on exception."""
        mock_search_fn.side_effect = RuntimeError("Network error")

        result = await handler._search_by_title("Test Title")

        assert result is None
        mock_logger.debug.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_truncates_long_title(
        self, handler: PubMedTitleFallbackHandler, mock_search_fn: AsyncMock
    ) -> None:
        """Should truncate titles longer than 200 chars."""
        mock_search_fn.return_value = []
        long_title = "A" * 300

        await handler._search_by_title(long_title)

        # Check that the title passed to search_fn is truncated
        call_args = mock_search_fn.call_args[0]
        assert len(call_args[0]) == 200


class TestProcessMissingDois:
    """Tests for process_missing_dois async generator (inherited from base)."""

    @pytest.mark.asyncio
    async def test_process_found_pmid_is_skipped(
        self, handler: PubMedTitleFallbackHandler, mock_search_fn: AsyncMock
    ) -> None:
        """Should skip PMIDs that were already found."""
        pmids = ["12345678"]
        found_pmids = {"12345678"}  # Already found
        fallback_mapping = {"12345678": "Test Title"}

        results = []
        async for pub in handler.process_missing_dois(
            dois=pmids,
            found_dois=found_pmids,
            fallback_mapping=fallback_mapping,
            normalize_fn=lambda x: x.lower().strip(),
            limit=None,
            fetched=0,
        ):
            results.append(pub)

        assert len(results) == 0
        mock_search_fn.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_missing_pmid_with_fallback_success(
        self,
        handler: PubMedTitleFallbackHandler,
        mock_search_fn: AsyncMock,
        mock_logger: MagicMock,
    ) -> None:
        """Should search by title and return publication when PMID not found."""
        pmids = ["99999999"]
        found_pmids: set[str] = set()
        fallback_mapping = {"99999999": "Missing Publication Title"}
        mock_search_fn.return_value = [
            {"pmid": "12345678", "article_title": "Missing Publication Title"}
        ]

        results = []
        async for pub in handler.process_missing_dois(
            dois=pmids,
            found_dois=found_pmids,
            fallback_mapping=fallback_mapping,
            normalize_fn=lambda x: x.lower().strip(),
            limit=None,
            fetched=0,
        ):
            results.append(pub)

        assert len(results) == 1
        assert results[0]["_lookup_method"] == "title_fallback"
        assert results[0]["_original_id"] == "99999999"
        mock_search_fn.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_missing_pmid_with_fallback_not_found(
        self,
        handler: PubMedTitleFallbackHandler,
        mock_search_fn: AsyncMock,
        mock_logger: MagicMock,
    ) -> None:
        """Should log warning when title fallback doesn't find publication."""
        pmids = ["99999999"]
        found_pmids: set[str] = set()
        fallback_mapping = {"99999999": "Not Found Title"}
        mock_search_fn.return_value = []  # No publication found

        results = []
        async for pub in handler.process_missing_dois(
            dois=pmids,
            found_dois=found_pmids,
            fallback_mapping=fallback_mapping,
            normalize_fn=lambda x: x.lower().strip(),
            limit=None,
            fetched=0,
        ):
            results.append(pub)

        assert len(results) == 0
        mock_logger.warning.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_missing_pmid_without_title(
        self,
        handler: PubMedTitleFallbackHandler,
        mock_search_fn: AsyncMock,
        mock_logger: MagicMock,
    ) -> None:
        """Should skip PMID when no title in fallback mapping."""
        pmids = ["99999999"]
        found_pmids: set[str] = set()
        fallback_mapping: dict[str, str] = {}  # No title for PMID

        results = []
        async for pub in handler.process_missing_dois(
            dois=pmids,
            found_dois=found_pmids,
            fallback_mapping=fallback_mapping,
            normalize_fn=lambda x: x.lower().strip(),
            limit=None,
            fetched=0,
        ):
            results.append(pub)

        assert len(results) == 0
        mock_search_fn.assert_not_called()
        mock_logger.debug.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_missing_dois__respects_limit__87ae202e(
        self, handler: PubMedTitleFallbackHandler, mock_search_fn: AsyncMock
    ) -> None:
        """Should stop when limit is reached."""
        pmids = ["11111111", "22222222", "33333333"]
        found_pmids: set[str] = set()
        fallback_mapping = {
            "11111111": "Title 1",
            "22222222": "Title 2",
            "33333333": "Title 3",
        }
        mock_search_fn.return_value = [{"pmid": "12345678", "article_title": "Title 1"}]

        results = []
        async for pub in handler.process_missing_dois(
            dois=pmids,
            found_dois=found_pmids,
            fallback_mapping=fallback_mapping,
            normalize_fn=lambda x: x.lower().strip(),
            limit=2,  # Only fetch 2
            fetched=1,  # Already fetched 1
        ):
            results.append(pub)

        # Should only get 1 more (limit=2, fetched=1, so 1 remaining)
        assert len(results) == 1


class TestProcessTitleOnlyEntries:
    """Tests for process_title_only_entries async generator (inherited from base)."""

    @pytest.mark.asyncio
    async def test_process_title_only_success(
        self,
        handler: PubMedTitleFallbackHandler,
        mock_search_fn: AsyncMock,
        mock_logger: MagicMock,
    ) -> None:
        """Should search by title for empty ID entries."""
        entries = [""]  # Empty ID
        fallback_mapping = {"": "Title-Only Publication"}
        mock_search_fn.return_value = [
            {"pmid": "12345678", "article_title": "Title-Only Publication"}
        ]

        results = []
        async for pub in handler.process_title_only_entries(
            entries=entries,
            fallback_mapping=fallback_mapping,
            limit=None,
            fetched=0,
        ):
            results.append(pub)

        assert len(results) == 1
        assert results[0]["_lookup_method"] == "title_only"

    @pytest.mark.asyncio
    async def test_process_title_only_not_found(
        self,
        handler: PubMedTitleFallbackHandler,
        mock_search_fn: AsyncMock,
        mock_logger: MagicMock,
    ) -> None:
        """Should log debug when title-only search fails."""
        entries = [""]
        fallback_mapping = {"": "Not Found Title"}
        mock_search_fn.return_value = []

        results = []
        async for pub in handler.process_title_only_entries(
            entries=entries,
            fallback_mapping=fallback_mapping,
            limit=None,
            fetched=0,
        ):
            results.append(pub)

        assert len(results) == 0
        mock_logger.debug.assert_called()

    @pytest.mark.asyncio
    async def test_process_title_only_no_mapping(
        self, handler: PubMedTitleFallbackHandler, mock_search_fn: AsyncMock
    ) -> None:
        """Should skip when no title in mapping."""
        entries = [""]
        fallback_mapping: dict[str, str] = {}  # No title

        results = []
        async for pub in handler.process_title_only_entries(
            entries=entries,
            fallback_mapping=fallback_mapping,
            limit=None,
            fetched=0,
        ):
            results.append(pub)

        assert len(results) == 0
        mock_search_fn.assert_not_called()


class TestEventNamesUniqueness:
    """Tests for event name uniqueness across all handlers."""

    def test_all_event_names_are_unique(
        self, handler: PubMedTitleFallbackHandler
    ) -> None:
        """All 7 event names should be unique for proper log filtering."""
        event_names = [
            handler._event_no_fallback_title,
            handler._event_fallback_attempt,
            handler._event_fallback_success,
            handler._event_fallback_not_found,
            handler._event_title_only_attempt,
            handler._event_title_only_success,
            handler._event_title_only_not_found,
        ]
        assert len(event_names) == 7, "Should have exactly 7 event properties"
        assert len(set(event_names)) == 7, "All event names should be unique"

    def test_all_event_names_have_pubmed_prefix(
        self, handler: PubMedTitleFallbackHandler
    ) -> None:
        """All event names should have 'pubmed_' prefix for log filtering."""
        event_names = [
            handler._event_no_fallback_title,
            handler._event_fallback_attempt,
            handler._event_fallback_success,
            handler._event_fallback_not_found,
            handler._event_title_only_attempt,
            handler._event_title_only_success,
            handler._event_title_only_not_found,
        ]
        for event_name in event_names:
            assert event_name.startswith("pubmed_"), (
                f"{event_name} should start with 'pubmed_'"
            )


class TestSearchByTitleMatchingPriority:
    """Tests for title matching priority in _search_by_title."""

    @pytest.mark.asyncio
    async def test_prefers_matching_title_over_first_result(
        self, mock_logger: MagicMock
    ) -> None:
        """Should prefer publication with matching title over first result."""
        mock_search_fn = AsyncMock(
            return_value=[
                {"pmid": "11111111", "article_title": "Wrong Title First"},
                {"pmid": "22222222", "article_title": "Exact Query Title"},
                {"pmid": "33333333", "article_title": "Another Wrong Title"},
            ]
        )
        handler = PubMedTitleFallbackHandler(
            logger=mock_logger, search_fn=mock_search_fn
        )

        result = await handler._search_by_title("Exact Query Title")

        assert result is not None
        assert result["pmid"] == "22222222"
        assert result["article_title"] == "Exact Query Title"

    @pytest.mark.asyncio
    async def test_handles_special_characters_in_title(
        self, mock_logger: MagicMock
    ) -> None:
        """Should handle titles with special characters."""
        mock_search_fn = AsyncMock(
            return_value=[
                {"pmid": "12345678", "article_title": "CRISPR-Cas9: A Review (2023)"}
            ]
        )
        handler = PubMedTitleFallbackHandler(
            logger=mock_logger, search_fn=mock_search_fn
        )

        result = await handler._search_by_title("CRISPR-Cas9: A Review (2023)")

        assert result is not None
        assert result["pmid"] == "12345678"

    @pytest.mark.asyncio
    async def test_handles_empty_article_title_in_results(
        self, mock_logger: MagicMock
    ) -> None:
        """Should skip results with empty article_title when matching."""
        mock_search_fn = AsyncMock(
            return_value=[
                {"pmid": "11111111", "article_title": ""},
                {"pmid": "22222222", "article_title": "Test Publication Title"},
            ]
        )
        handler = PubMedTitleFallbackHandler(
            logger=mock_logger, search_fn=mock_search_fn
        )

        result = await handler._search_by_title("Test Publication Title")

        # Should find the second result with matching title
        assert result is not None
        assert result["pmid"] == "22222222"

    @pytest.mark.asyncio
    async def test_returns_none_when_all_titles_empty(
        self, mock_logger: MagicMock
    ) -> None:
        mock_search_fn = AsyncMock(
            return_value=[
                {"pmid": "11111111", "article_title": ""},
                {"pmid": "22222222", "article_title": ""},
            ]
        )
        handler = PubMedTitleFallbackHandler(
            logger=mock_logger, search_fn=mock_search_fn
        )

        result = await handler._search_by_title("Test Title")

        assert result is None

    @pytest.mark.asyncio
    async def test_handles_whitespace_in_titles(self, mock_logger: MagicMock) -> None:
        """Should match titles with extra whitespace."""
        mock_search_fn = AsyncMock(
            return_value=[
                {"pmid": "12345678", "article_title": "Title  with   extra   spaces"}
            ]
        )
        handler = PubMedTitleFallbackHandler(
            logger=mock_logger, search_fn=mock_search_fn
        )

        result = await handler._search_by_title("Title with extra spaces")

        assert result is not None
        assert result["pmid"] == "12345678"
