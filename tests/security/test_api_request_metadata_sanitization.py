"""Security regressions for Bronze API request metadata."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from bioetl.infrastructure.adapters.common.api_request_collector import (
    APIRequestCollector,
)

pytestmark = [pytest.mark.security, pytest.mark.unit]


def test_request_metadata_strips_url_credentials_and_encoded_secret_params() -> None:
    collector = APIRequestCollector()
    collector.record_request(
        "https://user:url-password@example.org:8443/records?"
        "API%5FKEY=query-secret&cursor=safe-cursor",
        timestamp=datetime(2026, 7, 17, tzinfo=UTC),
    )

    request = collector.to_source_metadata().api_requests[0]

    assert request.base_url == "https://example.org:8443"
    assert request.query_params["API_KEY"] == "[REDACTED]"
    assert request.query_params["cursor"] == "safe-cursor"
    assert "url-password" not in request.model_dump_json()
    assert "query-secret" not in request.model_dump_json()
