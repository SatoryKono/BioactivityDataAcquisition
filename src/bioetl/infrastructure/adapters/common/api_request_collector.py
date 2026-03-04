"""API Request Collector for capturing detailed request metadata.

Accumulates API request details for Bronze layer metadata enrichment.
Supports audit, debugging, and rate limit monitoring use cases.

Thread-safe for concurrent request recording within a single pipeline run.
"""

from __future__ import annotations

import threading
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Literal
from urllib.parse import urlparse

if TYPE_CHECKING:
    import httpx


from bioetl.domain.models.metadata import (
    APIRequestDetails,
    RateLimitInfo,
    SourceMetadata,
)


class APIRequestCollector:
    """Collects API request metadata for Bronze layer enrichment.

    Thread-safe collector that accumulates request details and produces
    a SourceMetadata instance with aggregate statistics.

    Example:
        >>> collector = APIRequestCollector()
        >>> collector.record_request(
        ...     url="https://api.example.com/data?limit=100",
        ...     method="GET",
        ...     response_size=1024,
        ...     duration_ms=150.5,
        ...     status_code=200,
        ... )
        >>> source_metadata = collector.to_source_metadata()

    """

    def __init__(self) -> None:
        """Initialize an empty request collector."""
        self._requests: list[APIRequestDetails] = []
        self._lock = threading.Lock()

    def record_request(
        self,
        url: str,
        method: str = "GET",
        response_size: int = 0,
        duration_ms: float = 0.0,
        status_code: int = 200,
        params: dict[str, Any] | None = None,  # Any: untyped API JSON record
        rate_limit_remaining: int | None = None,
        rate_limit_limit: int | None = None,
        rate_limit_reset: datetime | None = None,
        retry_after_seconds: float | None = None,
        timestamp: datetime | None = None,
    ) -> None:
        """Record a completed API request.

        Args:
            url: Full request URL (base URL + endpoint + query string).
            method: HTTP method (GET, POST, HEAD).
            response_size: Size of response body in bytes.
            duration_ms: Request duration in milliseconds.
            status_code: HTTP response status code.
            params: Query parameters dict (alternative to parsing from URL).
            rate_limit_remaining: Value of X-RateLimit-Remaining header.
            rate_limit_limit: Value of X-RateLimit-Limit header.
            rate_limit_reset: Parsed X-RateLimit-Reset timestamp.
            retry_after_seconds: Value of Retry-After header in seconds.
            timestamp: UTC timestamp when request was made. Defaults to now.
        """
        parsed = urlparse(url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        endpoint = parsed.path

        # Parse query params from URL if not provided
        if params is None:
            params = self._parse_query_params(parsed.query)
        # Sanitize params to ensure no sensitive data (API keys, etc.)
        sanitized_params = self._sanitize_params(params)

        # Build rate limit info if any headers present
        rate_limit: RateLimitInfo | None = None
        if any(
            [
                rate_limit_remaining,
                rate_limit_limit,
                rate_limit_reset,
                retry_after_seconds,
            ]
        ):
            rate_limit = RateLimitInfo(
                remaining=rate_limit_remaining,
                limit=rate_limit_limit,
                reset_at=rate_limit_reset,
                retry_after_seconds=retry_after_seconds,
            )

        request_details = APIRequestDetails(
            endpoint=endpoint,
            base_url=base_url,
            query_params=sanitized_params,
            http_method=self._normalize_method(method),
            response_size_bytes=response_size,
            request_duration_ms=duration_ms,
            status_code=status_code,
            rate_limit=rate_limit,
            timestamp=timestamp or datetime.now(UTC),
        )

        with self._lock:
            self._requests.append(request_details)

    def record_from_response(
        self,
        response: httpx.Response,
        duration_ms: float,
        timestamp: datetime | None = None,
    ) -> None:
        """Record request details from an httpx Response object.

        Extracts URL, status, size, and rate limit headers automatically.

        Args:
            response: httpx.Response object after request completion.
            duration_ms: Request duration in milliseconds.
            timestamp: UTC timestamp when request was made. Defaults to now.
        """
        # Extract rate limit headers
        rate_limit_remaining = self._parse_int_header(
            response.headers.get("X-RateLimit-Remaining")
        )
        rate_limit_limit = self._parse_int_header(
            response.headers.get("X-RateLimit-Limit")
        )
        rate_limit_reset = self._parse_reset_header(
            response.headers.get("X-RateLimit-Reset")
        )
        retry_after = self._parse_float_header(response.headers.get("Retry-After"))

        # Calculate response size
        response_size = len(response.content)

        # Get method from request
        method = response.request.method if response.request else "GET"

        self.record_request(
            url=str(response.url),
            method=method,
            response_size=response_size,
            duration_ms=duration_ms,
            status_code=response.status_code,
            rate_limit_remaining=rate_limit_remaining,
            rate_limit_limit=rate_limit_limit,
            rate_limit_reset=rate_limit_reset,
            retry_after_seconds=retry_after,
            timestamp=timestamp,
        )

    def to_source_metadata(
        self,
        source_type: Literal["api", "csv", "parquet"] = "api",
        url: str | None = None,
        api_version: str | None = None,
        query_string: str | None = None,
    ) -> SourceMetadata:
        """Build SourceMetadata with collected request details and aggregates.

        Args:
            source_type: Source type for metadata ("api", "csv", "parquet").
            url: Optional base API URL to include.
            api_version: Optional API version string.
            query_string: Optional query string for audit trail
                (e.g., extraction-level filtering params from ADR-028 §3).

        Returns:
            SourceMetadata instance with all collected requests and statistics.
        """
        with self._lock:
            requests_copy = list(self._requests)

        total_requests = len(requests_copy)
        total_response_bytes = sum(r.response_size_bytes for r in requests_copy)

        if total_requests > 0:
            avg_duration = (
                sum(r.request_duration_ms for r in requests_copy) / total_requests
            )
        else:
            avg_duration = 0.0

        return SourceMetadata(
            type=source_type,
            url=url,
            query_string=query_string,
            api_version=api_version,
            api_requests=requests_copy,
            total_requests=total_requests,
            total_response_bytes=total_response_bytes,
            avg_request_duration_ms=round(avg_duration, 2),
        )

    def clear(self) -> None:
        """Clear all collected requests."""
        with self._lock:
            self._requests.clear()

    @property
    def request_count(self) -> int:
        """Get current number of recorded requests."""
        with self._lock:
            return len(self._requests)

    def _parse_query_params(
        self, query_string: str
    ) -> dict[str, str | int | float | bool | None]:
        """Parse query string into dict."""
        if not query_string:
            return {}
        params: dict[str, str | int | float | bool | None] = {}
        for part in query_string.split("&"):
            if "=" in part:
                key, value = part.split("=", 1)
                params[key] = value
        return params

    def _sanitize_params(
        self,
        params: dict[str, Any],  # Any: untyped API JSON record
    ) -> dict[str, str | int | float | bool | None]:
        """Sanitize query parameters to exclude sensitive data.

        Removes API keys, tokens, and other sensitive parameter names.
        """
        sensitive_keys = {
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
        }
        result: dict[str, str | int | float | bool | None] = {}
        for key, value in params.items():
            if key.lower() in sensitive_keys:
                result[key] = "[REDACTED]"
            elif isinstance(value, (str, int, float, bool)) or value is None:
                result[key] = value
            else:
                # Convert other types to string
                result[key] = str(value)
        return result

    def _normalize_method(self, method: str) -> Literal["GET", "POST", "HEAD"]:
        """Normalize HTTP method to SourceMetadata-compatible literal."""
        normalized = method.upper()
        if normalized == "GET":
            return "GET"
        if normalized == "POST":
            return "POST"
        if normalized == "HEAD":
            return "HEAD"
        return "GET"

    def _parse_int_header(self, value: str | None) -> int | None:
        """Parse integer header value."""
        if value is None:
            return None
        try:
            return int(value)
        except ValueError:
            return None

    def _parse_float_header(self, value: str | None) -> float | None:
        """Parse float header value."""
        if value is None:
            return None
        try:
            return float(value)
        except ValueError:
            return None

    def _parse_reset_header(self, value: str | None) -> datetime | None:
        """Parse X-RateLimit-Reset header (Unix timestamp or HTTP date)."""
        if value is None:
            return None
        try:
            # Try Unix timestamp first
            timestamp = int(value)
            return datetime.fromtimestamp(timestamp, tz=UTC)
        except ValueError:
            pass
        # Could extend to parse HTTP date format if needed
        return None


__all__ = ["APIRequestCollector"]
