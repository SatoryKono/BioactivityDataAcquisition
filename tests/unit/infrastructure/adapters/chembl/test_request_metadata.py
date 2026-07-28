"""Unit tests for ChEMBL request-metadata behavior."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.domain.models.filter import ExtractionParams
from bioetl.infrastructure.adapters.chembl import ChemblAdapter
from bioetl.infrastructure.adapters.chembl.constants import CHEMBL_API_BASE
from tests.helpers.adapter_request_metadata import (
    assert_clear_request_collector_resets_count,
    assert_metadata_snapshot_consumes_requests,
    assert_request_count_starts_at_zero,
)

pytestmark = pytest.mark.unit


@pytest.fixture
def mock_http_client() -> AsyncMock:
    """Create mock HTTP client for lightweight metadata tests."""
    client = AsyncMock()
    client.__aenter__.return_value = client
    client.__aexit__.return_value = None
    return client


@pytest.fixture
def mock_logger() -> MagicMock:
    """Create mock logger."""
    return MagicMock()


def test_request_count_starts_at_zero(
    mock_http_client: AsyncMock, mock_logger: MagicMock
) -> None:
    """New adapter instances should start with an empty request collector."""
    adapter = ChemblAdapter(http_client=mock_http_client, logger=mock_logger)
    assert_request_count_starts_at_zero(adapter)


def test_get_source_metadata_returns_chembl_snapshot_and_clears_requests(
    mock_http_client: AsyncMock, mock_logger: MagicMock
) -> None:
    """Metadata snapshot should reflect collector state and consume it."""
    adapter = ChemblAdapter(http_client=mock_http_client, logger=mock_logger)
    adapter._request_collector.record_request(
        url=f"{CHEMBL_API_BASE}/activity?limit=20",
        method="GET",
        duration_ms=100,
        status_code=200,
    )
    assert_metadata_snapshot_consumes_requests(
        adapter,
        expected_url=CHEMBL_API_BASE,
        api_version="33",
    )


def test_clear_request_collector_resets_request_count(
    mock_http_client: AsyncMock, mock_logger: MagicMock
) -> None:
    """Clearing the collector should drop accumulated request state."""
    adapter = ChemblAdapter(http_client=mock_http_client, logger=mock_logger)
    adapter._request_collector.record_request(
        url=f"{CHEMBL_API_BASE}/target?limit=1",
        method="GET",
        duration_ms=75,
        status_code=200,
    )
    assert adapter.request_count == 1
    assert_clear_request_collector_resets_count(adapter)


def test_get_source_metadata_includes_extraction_query_string(
    mock_http_client: AsyncMock, mock_logger: MagicMock
) -> None:
    """Extraction params should be carried into metadata.query_string."""
    adapter = ChemblAdapter(
        http_client=mock_http_client,
        logger=mock_logger,
        extraction_params=ExtractionParams(
            params={
                "standard_type__in": "IC50",
                "standard_units": "nM",
            }
        ),
    )

    metadata = adapter.get_source_metadata()

    assert metadata.query_string == "standard_type__in=IC50&standard_units=nM"


def test_get_source_metadata_omits_query_string_when_extraction_params_empty(
    mock_http_client: AsyncMock, mock_logger: MagicMock
) -> None:
    """Empty extraction params should not add a metadata query string."""
    adapter = ChemblAdapter(http_client=mock_http_client, logger=mock_logger)

    metadata = adapter.get_source_metadata()

    assert metadata.query_string is None
