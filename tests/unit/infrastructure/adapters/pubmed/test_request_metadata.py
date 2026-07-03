"""Unit tests for PubMed request-metadata behavior."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.infrastructure.adapters.pubmed import ENTREZ_API_BASE, PubMedAdapter
from tests.helpers.adapter_runtime import build_http_adapter_runtime_kwargs

pytestmark = pytest.mark.unit


@pytest.fixture
def mock_http_client() -> AsyncMock:
    """Create mock HTTP client for lightweight metadata tests."""
    client = AsyncMock()
    client.__aenter__.return_value = client
    client.__aexit__.return_value = None
    client._client = AsyncMock()
    client._client.aclose = AsyncMock()
    return client


@pytest.fixture
def mock_logger() -> MagicMock:
    """Create mock logger."""
    return MagicMock()


@pytest.fixture
def adapter(mock_http_client: AsyncMock, mock_logger: MagicMock) -> PubMedAdapter:
    """Create PubMed adapter instance."""
    return PubMedAdapter(
        http_client=mock_http_client,
        logger=mock_logger,
        email="test@example.com",
        api_key=None,
        **build_http_adapter_runtime_kwargs(
            "pubmed",
            logger=mock_logger,
            include_fallback_service=True,
        ),
    )


def test_request_metadata__count_starts_at_zero__ebe0eef7(
    adapter: PubMedAdapter,
) -> None:
    """New adapter instances should start with an empty request collector."""
    assert adapter.request_count == 0


def test_request_metadata__and_clears_requests__70bf0692(
    adapter: PubMedAdapter,
) -> None:
    """Metadata snapshot should reflect collector state and consume it."""
    adapter._request_collector.record_request(
        url=f"{ENTREZ_API_BASE}einfo.fcgi?db=pubmed",
        method="GET",
        duration_ms=18.0,
        status_code=200,
    )

    metadata = adapter.get_source_metadata(api_version="v1")

    assert metadata.type == "api"
    assert metadata.url == ENTREZ_API_BASE
    assert metadata.api_version == "v1"
    assert metadata.total_requests == 1
    assert adapter.request_count == 0


def test_request_metadata__resets_request_count__e1eb5603(
    adapter: PubMedAdapter,
) -> None:
    """Clearing the collector should drop accumulated request state."""
    adapter._request_collector.record_request(
        url=f"{ENTREZ_API_BASE}esearch.fcgi?db=pubmed&term=aspirin",
        method="GET",
        duration_ms=22.0,
        status_code=200,
    )

    assert adapter.request_count == 1

    adapter.clear_request_collector()

    assert adapter.request_count == 0
