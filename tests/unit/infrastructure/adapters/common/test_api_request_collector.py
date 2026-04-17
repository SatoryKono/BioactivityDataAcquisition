"""Unit tests for APIRequestCollector.

Tests request recording, aggregation, and metadata generation
for Bronze layer source metadata enrichment.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from bioetl.infrastructure.adapters.common.api_request_collector import (
    APIRequestCollector,
)


class TestAPIRequestCollector:
    """Tests for APIRequestCollector initialization and basic operations."""

    def test_init_creates_empty_collector(self) -> None:
        """Collector starts with no requests."""
        collector = APIRequestCollector()
        assert collector.request_count == 0

    def test_clear_removes_all_requests(self) -> None:
        """Clear removes all recorded requests."""
        collector = APIRequestCollector()
        collector.record_request(
            url="https://api.example.com/data",
            response_size=100,
            duration_ms=50.0,
        )
        assert collector.request_count == 1

        collector.clear()
        assert collector.request_count == 0


class TestRecordRequest:
    """Tests for the record_request method."""

    def test_record_request_basic(self) -> None:
        """Basic request recording captures required fields."""
        collector = APIRequestCollector()

        collector.record_request(
            url="https://api.example.com/v1/data?limit=100&offset=0",
            method="GET",
            response_size=1024,
            duration_ms=150.5,
            status_code=200,
        )

        assert collector.request_count == 1
        metadata = collector.to_source_metadata()

        assert len(metadata.api_requests) == 1
        request = metadata.api_requests[0]

        assert request.endpoint == "/v1/data"
        assert request.base_url == "https://api.example.com"
        assert request.http_method == "GET"
        assert request.response_size_bytes == 1024
        assert request.request_duration_ms == pytest.approx(150.5)
        assert request.status_code == 200

    def test_record_request_with_params(self) -> None:
        """Request recording with explicit params dict."""
        collector = APIRequestCollector()

        params = {"limit": 500, "offset": 1000, "format": "json"}
        collector.record_request(
            url="https://api.example.com/data",
            params=params,
            response_size=2048,
            duration_ms=200.0,
        )

        metadata = collector.to_source_metadata()
        request = metadata.api_requests[0]

        assert request.query_params == {"limit": 500, "offset": 1000, "format": "json"}

    def test_record_request_parses_url_params(self) -> None:
        """Request recording parses query params from URL."""
        collector = APIRequestCollector()

        collector.record_request(
            url="https://api.example.com/data?limit=100&offset=0",
            response_size=1024,
            duration_ms=100.0,
        )

        metadata = collector.to_source_metadata()
        request = metadata.api_requests[0]

        assert request.query_params == {"limit": "100", "offset": "0"}

    def test_record_request_sanitizes_api_keys(self) -> None:
        """Sensitive parameters are redacted."""
        collector = APIRequestCollector()

        params = {
            "api_key": "secret_key_12345",
            "token": "bearer_token_abc",
            "limit": 100,
            "Authorization": "Basic xyz",
        }
        collector.record_request(
            url="https://api.example.com/data",
            params=params,
            response_size=1024,
            duration_ms=100.0,
        )

        metadata = collector.to_source_metadata()
        request = metadata.api_requests[0]

        assert request.query_params["api_key"] == "[REDACTED]"
        assert request.query_params["token"] == "[REDACTED]"
        assert request.query_params["Authorization"] == "[REDACTED]"
        assert request.query_params["limit"] == 100

    def test_record_request_with_rate_limit_info(self) -> None:
        """Request recording captures rate limit headers."""
        collector = APIRequestCollector()
        reset_time = datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC)

        collector.record_request(
            url="https://api.example.com/data",
            response_size=1024,
            duration_ms=100.0,
            rate_limit_remaining=95,
            rate_limit_limit=100,
            rate_limit_reset=reset_time,
            retry_after_seconds=5.0,
        )

        metadata = collector.to_source_metadata()
        request = metadata.api_requests[0]

        assert request.rate_limit is not None
        assert request.rate_limit.remaining == 95
        assert request.rate_limit.limit == 100
        assert request.rate_limit.reset_at == reset_time
        assert request.rate_limit.retry_after_seconds == pytest.approx(5.0)

    def test_record_request_timestamp_default(self) -> None:
        """Request recording uses current UTC time if not provided."""
        collector = APIRequestCollector()
        before = datetime.now(UTC)

        collector.record_request(
            url="https://api.example.com/data",
            response_size=1024,
            duration_ms=100.0,
        )

        after = datetime.now(UTC)
        metadata = collector.to_source_metadata()
        request = metadata.api_requests[0]

        assert request.timestamp is not None
        assert before <= request.timestamp <= after

    def test_record_request_explicit_timestamp(self) -> None:
        """Request recording uses provided timestamp."""
        collector = APIRequestCollector()
        custom_time = datetime(2024, 6, 15, 10, 30, 0, tzinfo=UTC)

        collector.record_request(
            url="https://api.example.com/data",
            response_size=1024,
            duration_ms=100.0,
            timestamp=custom_time,
        )

        metadata = collector.to_source_metadata()
        request = metadata.api_requests[0]

        assert request.timestamp == custom_time

    def test_record_multiple_requests(self) -> None:
        """Multiple requests are accumulated."""
        collector = APIRequestCollector()

        collector.record_request(
            url="https://api.example.com/data?page=1",
            response_size=1000,
            duration_ms=100.0,
        )
        collector.record_request(
            url="https://api.example.com/data?page=2",
            response_size=2000,
            duration_ms=200.0,
        )
        collector.record_request(
            url="https://api.example.com/data?page=3",
            response_size=3000,
            duration_ms=300.0,
        )

        assert collector.request_count == 3
        metadata = collector.to_source_metadata()
        assert len(metadata.api_requests) == 3

    def test_record_post_request(self) -> None:
        """POST method is recorded correctly."""
        collector = APIRequestCollector()

        collector.record_request(
            url="https://api.example.com/search",
            method="POST",
            response_size=5000,
            duration_ms=500.0,
        )

        metadata = collector.to_source_metadata()
        request = metadata.api_requests[0]

        assert request.http_method == "POST"


class TestRecordFromResponse:
    """Tests for the record_from_response method."""

    def test_record_from_response_basic(self) -> None:
        """Recording from httpx response extracts basic info."""
        collector = APIRequestCollector()

        # Create mock response
        mock_response = MagicMock()
        mock_response.url = "https://api.example.com/data?limit=100"
        mock_response.status_code = 200
        mock_response.content = b"x" * 1024  # 1KB response
        mock_response.headers = {}
        mock_response.request.method = "GET"

        collector.record_from_response(mock_response, duration_ms=150.0)

        metadata = collector.to_source_metadata()
        request = metadata.api_requests[0]

        assert request.base_url == "https://api.example.com"
        assert request.endpoint == "/data"
        assert request.status_code == 200
        assert request.response_size_bytes == 1024
        assert request.request_duration_ms == pytest.approx(150.0)
        assert request.http_method == "GET"

    def test_record_from_response_with_rate_limit_headers(self) -> None:
        """Recording extracts rate limit headers."""
        collector = APIRequestCollector()

        mock_response = MagicMock()
        mock_response.url = "https://api.example.com/data"
        mock_response.status_code = 200
        mock_response.content = b"test"
        mock_response.headers = {
            "X-RateLimit-Remaining": "95",
            "X-RateLimit-Limit": "100",
            "X-RateLimit-Reset": "1705320000",  # Unix timestamp
            "Retry-After": "5.5",
        }
        mock_response.request.method = "GET"

        collector.record_from_response(mock_response, duration_ms=100.0)

        metadata = collector.to_source_metadata()
        request = metadata.api_requests[0]

        assert request.rate_limit is not None
        assert request.rate_limit.remaining == 95
        assert request.rate_limit.limit == 100
        assert request.rate_limit.reset_at is not None
        assert request.rate_limit.retry_after_seconds == pytest.approx(5.5)

    def test_record_from_response_missing_headers(self) -> None:
        """Recording handles missing rate limit headers gracefully."""
        collector = APIRequestCollector()

        mock_response = MagicMock()
        mock_response.url = "https://api.example.com/data"
        mock_response.status_code = 200
        mock_response.content = b"test"
        mock_response.headers = {}
        mock_response.request.method = "GET"

        collector.record_from_response(mock_response, duration_ms=100.0)

        metadata = collector.to_source_metadata()
        request = metadata.api_requests[0]

        # No rate limit info when headers are missing
        assert request.rate_limit is None


class TestToSourceMetadata:
    """Tests for the to_source_metadata method."""

    def test_empty_collector_returns_minimal_metadata(self) -> None:
        """Empty collector returns metadata with zero aggregates."""
        collector = APIRequestCollector()

        metadata = collector.to_source_metadata()

        assert metadata.type == "api"
        assert metadata.api_requests == []
        assert metadata.total_requests == 0
        assert metadata.total_response_bytes == 0
        assert metadata.avg_request_duration_ms == pytest.approx(0.0)

    def test_aggregates_multiple_requests(self) -> None:
        """Aggregates are computed correctly from multiple requests."""
        collector = APIRequestCollector()

        collector.record_request(
            url="https://api.example.com/data?page=1",
            response_size=1000,
            duration_ms=100.0,
        )
        collector.record_request(
            url="https://api.example.com/data?page=2",
            response_size=2000,
            duration_ms=200.0,
        )
        collector.record_request(
            url="https://api.example.com/data?page=3",
            response_size=3000,
            duration_ms=300.0,
        )

        metadata = collector.to_source_metadata()

        assert metadata.total_requests == 3
        assert metadata.total_response_bytes == 6000
        assert metadata.avg_request_duration_ms == pytest.approx(
            200.0
        )  # (100 + 200 + 300) / 3

    def test_to_source_metadata_with_url(self) -> None:
        """Source metadata includes base URL when provided."""
        collector = APIRequestCollector()
        collector.record_request(
            url="https://api.example.com/data",
            response_size=1024,
            duration_ms=100.0,
        )

        metadata = collector.to_source_metadata(url="https://api.example.com")

        assert metadata.url == "https://api.example.com"

    def test_to_source_metadata_with_api_version(self) -> None:
        """Source metadata includes API version when provided."""
        collector = APIRequestCollector()
        collector.record_request(
            url="https://api.example.com/data",
            response_size=1024,
            duration_ms=100.0,
        )

        metadata = collector.to_source_metadata(api_version="v2.1.0")

        assert metadata.api_version == "v2.1.0"

    def test_to_source_metadata_csv_type(self) -> None:
        """Source type can be set to non-api values."""
        collector = APIRequestCollector()

        metadata = collector.to_source_metadata(source_type="csv")

        assert metadata.type == "csv"

    def test_avg_duration_rounds_to_two_decimals(self) -> None:
        """Average duration is rounded to 2 decimal places."""
        collector = APIRequestCollector()

        collector.record_request(
            url="https://api.example.com/data",
            response_size=1000,
            duration_ms=100.333333,
        )
        collector.record_request(
            url="https://api.example.com/data",
            response_size=1000,
            duration_ms=200.666666,
        )

        metadata = collector.to_source_metadata()

        # (100.333333 + 200.666666) / 2 = 150.499999... → 150.5
        assert metadata.avg_request_duration_ms == pytest.approx(150.5)


class TestThreadSafety:
    """Tests for thread-safety of the collector."""

    def test_concurrent_recording(self) -> None:
        """Collector handles concurrent access safely."""
        import threading

        collector = APIRequestCollector()
        num_threads = 10
        requests_per_thread = 100

        def record_requests() -> None:
            for i in range(requests_per_thread):
                collector.record_request(
                    url=f"https://api.example.com/data?id={i}",
                    response_size=100,
                    duration_ms=10.0,
                )

        threads = [threading.Thread(target=record_requests) for _ in range(num_threads)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert collector.request_count == num_threads * requests_per_thread


class TestBackwardCompatibility:
    """Tests for backward compatibility with existing SourceMetadata usage."""

    def test_source_metadata_serializable(self) -> None:
        """Generated SourceMetadata is JSON serializable."""
        collector = APIRequestCollector()
        collector.record_request(
            url="https://api.example.com/data",
            response_size=1024,
            duration_ms=100.0,
            rate_limit_remaining=95,
        )

        metadata = collector.to_source_metadata()

        # Should not raise
        json_dict = metadata.model_dump()
        assert isinstance(json_dict, dict)
        assert json_dict["type"] == "api"
        assert json_dict["total_requests"] == 1

    def test_minimal_source_metadata_compatible(self) -> None:
        """Empty collector produces metadata compatible with old format."""
        collector = APIRequestCollector()
        metadata = collector.to_source_metadata()

        # Old code expects these fields
        assert hasattr(metadata, "type")
        assert hasattr(metadata, "url")
        assert hasattr(metadata, "file_path")
        assert hasattr(metadata, "api_version")

        # New fields have safe defaults
        assert metadata.api_requests == []
        assert metadata.total_requests == 0


class TestParameterSanitization:
    """Tests for parameter sanitization."""

    @pytest.mark.parametrize(
        "param_name",
        [
            "api_key",
            "apikey",
            "key",
            "token",
            "access_token",
            "secret",
            "password",
            "auth",
            "authorization",
            "x-api-key",
            "bearer",
        ],
    )
    def test_sensitive_params_redacted(self, param_name: str) -> None:
        """All known sensitive parameter names are redacted."""
        collector = APIRequestCollector()

        collector.record_request(
            url="https://api.example.com/data",
            params={param_name: "sensitive_value_123"},
            response_size=1024,
            duration_ms=100.0,
        )

        metadata = collector.to_source_metadata()
        request = metadata.api_requests[0]

        assert request.query_params[param_name] == "[REDACTED]"

    def test_case_insensitive_sanitization(self) -> None:
        """Sanitization is case-insensitive."""
        collector = APIRequestCollector()

        collector.record_request(
            url="https://api.example.com/data",
            params={
                "API_KEY": "secret1",
                "Token": "secret2",
                "SECRET": "secret3",
            },
            response_size=1024,
            duration_ms=100.0,
        )

        metadata = collector.to_source_metadata()
        request = metadata.api_requests[0]

        assert request.query_params["API_KEY"] == "[REDACTED]"
        assert request.query_params["Token"] == "[REDACTED]"
        assert request.query_params["SECRET"] == "[REDACTED]"
