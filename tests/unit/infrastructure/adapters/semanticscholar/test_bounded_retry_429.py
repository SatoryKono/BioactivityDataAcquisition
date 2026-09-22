# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# PD5 test mock/fixture surface.
"""Bounded retry for HTTP 429 in Semantic Scholar adapters (10577 P2)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from bioetl.domain.exceptions import RetryExhaustedError
from bioetl.domain.exceptions.network.service import ApiError
from bioetl.infrastructure.adapters.semanticscholar import SemanticScholarAdapter
from bioetl.infrastructure.adapters.semanticscholar.fallback import (
    SemanticScholarTitleFallbackHandler,
)
from tests.helpers.adapter_runtime import build_http_adapter_runtime_kwargs

pytestmark = pytest.mark.unit


@pytest.fixture
def mock_logger() -> MagicMock:
    return MagicMock()


@pytest.fixture
def mock_http_client() -> MagicMock:
    client = MagicMock()
    client.get = AsyncMock()
    client.get_once = AsyncMock()
    client.post = AsyncMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock()
    return client


@pytest.fixture
def adapter(mock_http_client: MagicMock, mock_logger: MagicMock) -> SemanticScholarAdapter:
    return SemanticScholarAdapter(
        http_client=mock_http_client,
        logger=mock_logger,
        api_key="test-api-key",
        batch_size=10,
        **build_http_adapter_runtime_kwargs(
            "semanticscholar",
            logger=mock_logger,
            include_fallback_service=True,
        ),
    )


class TestSearchFetchBoundedRetry429:
    """Search pagination must use bounded retry for 429."""

    @pytest.mark.asyncio
    async def test_fetch_search_page_uses_bounded_retry_get(
        self, adapter: SemanticScholarAdapter, mock_http_client: MagicMock
    ) -> None:
        """_fetch_search_page must call get (bounded retry) not get_once."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": [{"paperId": "a" * 40}], "next": None}
        mock_response.status_code = 200
        mock_http_client.get.return_value = mock_response

        records, nxt = await adapter._fetch_search_page(
            query="test", page_size=10, current_offset=0
        )

        mock_http_client.get.assert_called_once()
        mock_http_client.get_once.assert_not_called()
        assert len(records) == 1

    @pytest.mark.asyncio
    async def test_fetch_search_page_429_exhaustion_is_bounded(
        self, adapter: SemanticScholarAdapter, mock_http_client: MagicMock
    ) -> None:
        """429 exhaustion must be bounded and mapped to ApiError 429."""
        mock_http_client.get.side_effect = RetryExhaustedError(
            "https://api.semanticscholar.org/graph/v1/paper/search: 429 Too Many Requests",
            attempts=5,
        )

        with pytest.raises(ApiError) as excinfo:
            await adapter._fetch_search_page(query="test", page_size=10, current_offset=0)

        assert excinfo.value.status_code == 429
        mock_http_client.get.assert_called_once()
        mock_http_client.get_once.assert_not_called()

    @pytest.mark.asyncio
    async def test_paginate_search_propagates_bounded_429(
        self, adapter: SemanticScholarAdapter, mock_http_client: MagicMock
    ) -> None:
        """Paginate must not infinite-loop on 429; it must propagate bounded error."""
        mock_http_client.get.side_effect = RetryExhaustedError(
            "search 429", attempts=5
        )

        with pytest.raises(ApiError) as excinfo:
            async for _ in adapter._paginate_search(query="test", limit=5):
                pass

        assert excinfo.value.status_code == 429


class TestFallbackBoundedRetry429:
    """Title fallback must use bounded retry for 429."""

    @pytest.mark.asyncio
    async def test_fallback_uses_bounded_retry_get(
        self, mock_logger: MagicMock, mock_http_client: MagicMock
    ) -> None:
        """Fallback _search_by_title must call get (bounded) not get_once."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": [{"paperId": "abc", "title": "Test Paper"}]}
        mock_http_client.get.return_value = mock_response

        handler = SemanticScholarTitleFallbackHandler(
            http_client=mock_http_client, logger=mock_logger
        )
        result = await handler._search_by_title("Test Paper")

        mock_http_client.get.assert_called_once()
        mock_http_client.get_once.assert_not_called()
        assert result is not None

    @pytest.mark.asyncio
    async def test_fallback_retry_exhausted_bounded(
        self, mock_logger: MagicMock, mock_http_client: MagicMock
    ) -> None:
        """RetryExhaustedError from bounded retry must not infinite-loop."""
        mock_http_client.get.side_effect = RetryExhaustedError("429 exhausted", attempts=5)
        handler = SemanticScholarTitleFallbackHandler(
            http_client=mock_http_client, logger=mock_logger
        )
        result = await handler._search_by_title("Test Paper")
        assert result is None
        mock_http_client.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_fallback_with_metrics_uses_bounded_get(
        self, mock_logger: MagicMock, mock_http_client: MagicMock
    ) -> None:
        """With metrics, fallback must still use bounded get."""
        metrics = MagicMock()
        metrics.measure_request.return_value.__enter__ = MagicMock()
        metrics.measure_request.return_value.__exit__ = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": [{"paperId": "abc", "title": "Test Paper"}]}
        mock_http_client.get.return_value = mock_response

        handler = SemanticScholarTitleFallbackHandler(
            http_client=mock_http_client, logger=mock_logger, metrics=metrics
        )
        result = await handler._search_by_title("Test Paper")
        assert result is not None
        mock_http_client.get.assert_called_once()
        metrics.measure_request.assert_called_once_with("/paper/search")


class TestRetryConfigBounded:
    """Config-level bounded retry sanity."""

    def test_retry_config_429_is_bounded(self) -> None:
        """DEFAULT_RETRYABLE_STATUSES includes 429 and max_attempts bounds retries."""
        from bioetl.domain.resilience import DEFAULT_RETRYABLE_STATUSES, RetryConfig

        assert 429 in DEFAULT_RETRYABLE_STATUSES
        cfg = RetryConfig(max_attempts=5)
        assert cfg.is_retryable_status(429)
        assert cfg.is_last_attempt(4) is True
        assert cfg.effective_retry_budget() == 4
        assert cfg.max_attempts == 5
