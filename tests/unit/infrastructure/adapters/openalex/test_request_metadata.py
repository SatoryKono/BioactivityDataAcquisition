"""Unit tests for OpenAlex request-metadata behavior."""

from __future__ import annotations

import pytest

from bioetl.infrastructure.adapters.common.api_request_collector import (
    APIRequestCollector,
)
from bioetl.infrastructure.adapters.openalex.client_helpers_adapter_mixin import (
    OpenAlexAdapterHelpersMixin,
)

pytestmark = pytest.mark.unit


class _OpenAlexMetadataHarness(OpenAlexAdapterHelpersMixin):
    def __init__(self, mailto: str = "bioetl@example.org") -> None:
        self.mailto = mailto
        self.api_key = None
        self._request_collector = APIRequestCollector()


def test_request_count_starts_at_zero() -> None:
    """New adapter instances should start with an empty request collector."""
    harness = _OpenAlexMetadataHarness()

    assert harness.request_count == 0


def test_get_source_metadata_returns_collector_state_and_clears_requests() -> None:
    """Metadata snapshot should reflect collector state and consume it."""
    harness = _OpenAlexMetadataHarness()
    harness._request_collector.record_request(
        url="https://api.openalex.org/works?filter=doi:10.1/abc",
        method="GET",
        duration_ms=25.0,
        status_code=200,
    )

    metadata = harness.get_source_metadata(api_version="v1")

    assert metadata.type == "api"
    assert metadata.url == "https://api.openalex.org"
    assert metadata.api_version == "v1"
    assert metadata.total_requests == 1
    assert harness.request_count == 0


def test_clear_request_collector_resets_request_count() -> None:
    """Clearing the collector should drop accumulated request state."""
    harness = _OpenAlexMetadataHarness()
    harness._request_collector.record_request(
        url="https://api.openalex.org/works?search=gene+editing",
        method="GET",
        duration_ms=19.5,
        status_code=200,
    )

    assert harness.request_count == 1

    harness.clear_request_collector()

    assert harness.request_count == 0
