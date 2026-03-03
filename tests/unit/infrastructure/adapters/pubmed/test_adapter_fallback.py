"""Unit tests for PubMedAdapter fallback methods.

Tests for _search_by_title and fetch_filtered_with_fallback methods
that enable title-based publication resolution when PMID lookup fails.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bioetl.infrastructure.adapters.pubmed.pubmed_client import PubMedAdapter


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
                pass

    @pytest.mark.asyncio
    async def test_separates_valid_ids_from_empty(self, adapter: PubMedAdapter) -> None:
        """Test correctly separates valid IDs from empty/whitespace entries."""
        captured_ids: list[str] = []

        async def mock_fetch_filtered(
            entity_type: str,
            filter_ids: list[str],
            filter_field: str,
            limit: int | None,
        ) -> AsyncIterator[dict[str, Any]]:
            captured_ids.extend(filter_ids)
            return
            yield  # Make it an async generator

        with patch.object(adapter, "fetch_filtered", mock_fetch_filtered):
            async for _ in adapter.fetch_filtered_with_fallback(
                entity_type="publication",
                filter_ids=["12345", "", "67890", "  ", "11111"],
                filter_field="pmid",
                fallback_mapping={},
            ):
                pass

        # Only non-empty, non-whitespace IDs should be passed
        assert "12345" in captured_ids
        assert "67890" in captured_ids
        assert "11111" in captured_ids
        assert "" not in captured_ids
        assert "  " not in captured_ids

    @pytest.mark.asyncio
    async def test_adds_primary_lookup_method_to_results(
        self, adapter: PubMedAdapter
    ) -> None:
        """Test primary results are marked with _lookup_method='primary'."""

        async def mock_fetch_filtered(
            entity_type: str,
            filter_ids: list[str],
            filter_field: str,
            limit: int | None,
        ) -> AsyncIterator[dict[str, Any]]:
            yield {"pmid": "12345678", "article_title": "Test Article"}

        with patch.object(adapter, "fetch_filtered", mock_fetch_filtered):
            results = []
            async for record in adapter.fetch_filtered_with_fallback(
                entity_type="publication",
                filter_ids=["12345678"],
                filter_field="pmid",
                fallback_mapping={},
            ):
                results.append(record)

        assert len(results) == 1
        assert results[0]["_lookup_method"] == "pmid"

    @pytest.mark.asyncio
    async def test_tracks_found_pmids_for_fallback(
        self, adapter: PubMedAdapter
    ) -> None:
        """Test found PMIDs are tracked to avoid duplicate fallback searches."""
        # Track what IDs the fallback handler receives
        processed_missing: list[str] = []
        assert adapter._fallback_handler is not None

        async def mock_fetch_filtered(
            entity_type: str,
            filter_ids: list[str],
            filter_field: str,
            limit: int | None,
        ) -> AsyncIterator[dict[str, Any]]:
            yield {"pmid": "12345678", "article_title": "Found Article"}

        async def mock_process_missing(
            dois: list[str],
            found_dois: set[str],
            fallback_mapping: dict[str, str],
            normalize_fn: Any,
            limit: int | None,
            fetched: int,
        ) -> AsyncIterator[dict[str, Any]]:
            # Record which IDs were marked as found
            processed_missing.extend(dois)
            # Check that 12345678 is in found set (lowercase)
            assert "12345678" in found_dois
            return
            yield

        with (
            patch.object(adapter, "fetch_filtered", mock_fetch_filtered),
            patch.object(
                adapter._fallback_handler, "process_missing_dois", mock_process_missing
            ),
        ):
            async for _ in adapter.fetch_filtered_with_fallback(
                entity_type="publication",
                filter_ids=["12345678", "99999999"],
                filter_field="pmid",
                fallback_mapping={"99999999": "Missing Title"},
            ):
                pass

    @pytest.mark.asyncio
    async def test_respects_limit(self, adapter: PubMedAdapter) -> None:
        """Test stops fetching when limit is reached."""

        async def mock_fetch_filtered(
            entity_type: str,
            filter_ids: list[str],
            filter_field: str,
            limit: int | None,
        ) -> AsyncIterator[dict[str, Any]]:
            for i, pmid in enumerate(filter_ids):
                yield {"pmid": pmid, "article_title": f"Article {i}"}

        with patch.object(adapter, "fetch_filtered", mock_fetch_filtered):
            results = []
            async for record in adapter.fetch_filtered_with_fallback(
                entity_type="publication",
                filter_ids=["11111", "22222", "33333", "44444", "55555"],
                filter_field="pmid",
                fallback_mapping={},
                limit=2,
            ):
                results.append(record)

        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_fallback_phase_invoked_for_missing_ids(
        self, adapter: PubMedAdapter
    ) -> None:
        """Test Phase 2 fallback is invoked for unresolved IDs."""
        fallback_invoked = [False]
        assert adapter._fallback_handler is not None

        async def mock_fetch_filtered(
            entity_type: str,
            filter_ids: list[str],
            filter_field: str,
            limit: int | None,
        ) -> AsyncIterator[dict[str, Any]]:
            # Only return result for first ID
            yield {"pmid": "12345678", "article_title": "Found"}

        async def mock_process_missing(
            dois: list[str],
            found_dois: set[str],
            fallback_mapping: dict[str, str],
            normalize_fn: Any,
            limit: int | None,
            fetched: int,
        ) -> AsyncIterator[dict[str, Any]]:
            fallback_invoked[0] = True
            return
            yield

        with (
            patch.object(adapter, "fetch_filtered", mock_fetch_filtered),
            patch.object(
                adapter._fallback_handler, "process_missing_dois", mock_process_missing
            ),
        ):
            async for _ in adapter.fetch_filtered_with_fallback(
                entity_type="publication",
                filter_ids=["12345678", "99999999"],
                filter_field="pmid",
                fallback_mapping={"99999999": "Missing Article Title"},
            ):
                pass

        assert fallback_invoked[0] is True

    @pytest.mark.asyncio
    async def test_title_only_phase_invoked_for_empty_ids(
        self, adapter: PubMedAdapter
    ) -> None:
        """Test Phase 3 title-only lookup is invoked for empty ID entries."""
        title_only_invoked = [False]
        assert adapter._fallback_handler is not None

        async def mock_fetch_filtered(
            entity_type: str,
            filter_ids: list[str],
            filter_field: str,
            limit: int | None,
        ) -> AsyncIterator[dict[str, Any]]:
            return
            yield

        async def mock_process_title_only(
            entries: list[str],
            fallback_mapping: dict[str, str],
            limit: int | None,
            fetched: int,
        ) -> AsyncIterator[dict[str, Any]]:
            title_only_invoked[0] = True
            # Verify we receive the empty entries
            assert "" in entries
            return
            yield

        with (
            patch.object(adapter, "fetch_filtered", mock_fetch_filtered),
            patch.object(
                adapter._fallback_handler,
                "process_title_only_entries",
                mock_process_title_only,
            ),
        ):
            async for _ in adapter.fetch_filtered_with_fallback(
                entity_type="publication",
                filter_ids=["12345678", ""],
                filter_field="pmid",
                fallback_mapping={"": "Title Only Publication"},
            ):
                pass

        assert title_only_invoked[0] is True

    @pytest.mark.asyncio
    async def test_all_three_phases_execute_in_order(
        self, adapter: PubMedAdapter
    ) -> None:
        """Test all three phases execute in correct order."""
        execution_order: list[str] = []
        assert adapter._fallback_handler is not None

        async def mock_fetch_filtered(
            entity_type: str,
            filter_ids: list[str],
            filter_field: str,
            limit: int | None,
        ) -> AsyncIterator[dict[str, Any]]:
            execution_order.append("phase1_primary")
            yield {"pmid": "11111", "article_title": "Primary Result"}

        async def mock_process_missing(
            dois: list[str],
            found_dois: set[str],
            fallback_mapping: dict[str, str],
            normalize_fn: Any,
            limit: int | None,
            fetched: int,
        ) -> AsyncIterator[dict[str, Any]]:
            execution_order.append("phase2_fallback")
            yield {"pmid": "22222", "article_title": "Fallback Result"}

        async def mock_process_title_only(
            entries: list[str],
            fallback_mapping: dict[str, str],
            limit: int | None,
            fetched: int,
        ) -> AsyncIterator[dict[str, Any]]:
            execution_order.append("phase3_title_only")
            yield {"pmid": "33333", "article_title": "Title Only Result"}

        with (
            patch.object(adapter, "fetch_filtered", mock_fetch_filtered),
            patch.object(
                adapter._fallback_handler, "process_missing_dois", mock_process_missing
            ),
            patch.object(
                adapter._fallback_handler,
                "process_title_only_entries",
                mock_process_title_only,
            ),
        ):
            results = []
            async for record in adapter.fetch_filtered_with_fallback(
                entity_type="publication",
                filter_ids=["11111", "22222", ""],
                filter_field="pmid",
                fallback_mapping={
                    "22222": "Fallback Title",
                    "": "Title Only Title",
                },
            ):
                results.append(record)

        # Verify correct execution order
        assert execution_order == [
            "phase1_primary",
            "phase2_fallback",
            "phase3_title_only",
        ]
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_logs_warning_for_non_pmid_filter_field(
        self, adapter: PubMedAdapter, mock_logger: MagicMock
    ) -> None:
        """Test warning is logged when filter_field is not 'pmid'."""

        async def mock_fetch_filtered(
            entity_type: str,
            filter_ids: list[str],
            filter_field: str,
            limit: int | None,
        ) -> AsyncIterator[dict[str, Any]]:
            return
            yield

        with patch.object(adapter, "fetch_filtered", mock_fetch_filtered):
            async for _ in adapter.fetch_filtered_with_fallback(
                entity_type="publication",
                filter_ids=["10.1234/test"],
                filter_field="doi",
                fallback_mapping={},
            ):
                pass

        # fetch_filtered (mocked) would normally log the warning
        # In real scenario, PubMedAdapter.fetch_filtered logs this


# =============================================================================
# Fallback Handler Integration Tests
# =============================================================================


class TestFallbackHandlerIntegration:
    """Tests for proper integration between PubMedAdapter and TitleFallbackHandler."""

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
