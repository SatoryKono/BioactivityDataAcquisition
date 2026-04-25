"""API request collector for Bronze metadata enrichment."""

from __future__ import annotations

import threading
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Literal
from urllib.parse import urlparse

if TYPE_CHECKING:
    import httpx

from bioetl.domain.models.metadata import (
    APIRequestDetails,
    RateLimitInfo,
    SourceMetadata,
)
from bioetl.domain.types import JsonDict
from bioetl.infrastructure.time import SystemClock


class APIRequestCollector:
    """Collect API request metadata and build SourceMetadata snapshots."""

    _clock = SystemClock()

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
        params: JsonDict | None = None,  # Any: untyped API JSON record
        rate_limit_remaining: int | None = None,
        rate_limit_limit: int | None = None,
        rate_limit_reset: datetime | None = None,
        retry_after_seconds: float | None = None,
        timestamp: datetime | None = None,
    ) -> None:
        """Record normalized request telemetry (URL, timing, status, and rate-limit data)."""
        parsed = urlparse(url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        endpoint = parsed.path

        if params is None:
            params = self._parse_query_params(parsed.query)
        sanitized_params = self._sanitize_params(params)
        rate_limit = self._build_rate_limit_info(
            rate_limit_remaining=rate_limit_remaining,
            rate_limit_limit=rate_limit_limit,
            rate_limit_reset=rate_limit_reset,
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
            timestamp=timestamp or self._clock.now(),
        )

        with self._lock:
            self._requests.append(request_details)

    @staticmethod
    def _build_rate_limit_info(
        *,
        rate_limit_remaining: int | None,
        rate_limit_limit: int | None,
        rate_limit_reset: datetime | None,
        retry_after_seconds: float | None,
    ) -> RateLimitInfo | None:
        """Build RateLimitInfo when at least one rate-limit attribute is present."""
        if not any(
            (
                rate_limit_remaining,
                rate_limit_limit,
                rate_limit_reset,
                retry_after_seconds,
            )
        ):
            return None
        return RateLimitInfo(
            remaining=rate_limit_remaining,
            limit=rate_limit_limit,
            reset_at=rate_limit_reset,
            retry_after_seconds=retry_after_seconds,
        )

    def record_from_response(
        self,
        response: httpx.Response,
        duration_ms: float,
        timestamp: datetime | None = None,
    ) -> None:
        """Record request details from an ``httpx.Response`` object."""
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
        """Build SourceMetadata with collected request details and aggregates."""
        with self._lock:
            requests_copy = self._requests.copy()

        total_requests = len(requests_copy)
        total_response_bytes = sum(r.response_size_bytes for r in requests_copy)

        avg_duration = (
            sum(r.request_duration_ms for r in requests_copy) / total_requests
            if total_requests > 0
            else 0.0
        )

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
        params: JsonDict,  # Any: untyped API JSON record
    ) -> dict[str, str | int | float | bool | None]:
        """Sanitize query parameters to exclude sensitive data."""
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
            pass  # Why: response body not JSON-parseable as Unix timestamp; return None
        # Could extend to parse HTTP date format if needed
        return None


__all__ = ["APIRequestCollector"]
