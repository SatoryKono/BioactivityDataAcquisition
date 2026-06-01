"""Unit tests for Semantic Scholar request-metadata behavior."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.infrastructure.adapters.semanticscholar import SemanticScholarAdapter
from bioetl.infrastructure.adapters.semanticscholar.constants import (
    SEMANTICSCHOLAR_BASE_URL,
)
from tests.helpers.adapter_runtime import build_http_adapter_runtime_kwargs

pytestmark = pytest.mark.unit


@pytest.fixture
def mock_http_client() -> MagicMock:
    """Create mock HTTP client for lightweight metadata tests."""
    client = MagicMock()
    client.get_once = AsyncMock()
    client.post = AsyncMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock()
    return client


@pytest.fixture
def mock_logger() -> MagicMock:
    """Create mock logger."""
    logger = MagicMock()
    logger.debug = MagicMock()
    logger.info = MagicMock()
    logger.warning = MagicMock()
    return logger


@pytest.fixture
def adapter(
    mock_http_client: MagicMock, mock_logger: MagicMock
) -> SemanticScholarAdapter:
    """Create Semantic Scholar adapter instance."""
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


def test_request_metadata__count_starts_at_zero__d202a52a(adapter: SemanticScholarAdapter) -> None:
    """New adapter instances should start with an empty request collector."""
    assert adapter.request_count == 0


def test_request_metadata__and_clears_requests__408831e1(
    adapter: SemanticScholarAdapter,
) -> None:
    """Metadata snapshot should reflect collector state and consume it."""
    adapter._request_collector.record_request(
        url=f"{SEMANTICSCHOLAR_BASE_URL}/paper/search?query=test",
        method="GET",
        duration_ms=15.0,
        status_code=200,
    )

    metadata = adapter.get_source_metadata()

    assert metadata.type == "api"
    assert metadata.url == SEMANTICSCHOLAR_BASE_URL
    assert metadata.api_version == "v1"
    assert metadata.total_requests == 1
    assert adapter.request_count == 0


def test_request_metadata__resets_request_count__c1676188(
    adapter: SemanticScholarAdapter,
) -> None:
    """Clearing the collector should drop accumulated request state."""
    adapter._request_collector.record_request(
        url=f"{SEMANTICSCHOLAR_BASE_URL}/paper/search?query=aspirin",
        method="GET",
        duration_ms=12.0,
        status_code=200,
    )

    assert adapter.request_count == 1

    adapter.clear_request_collector()

    assert adapter.request_count == 0
