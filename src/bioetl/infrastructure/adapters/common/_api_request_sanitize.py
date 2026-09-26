"""Sanitization and header-parse helpers for APIRequestCollector."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal
from urllib.parse import SplitResult, parse_qsl

from bioetl.domain.types import JsonDict

__all__ = [
    "normalize_http_method",
    "parse_float_header",
    "parse_int_header",
    "parse_query_params",
    "parse_reset_header",
    "sanitize_base_url",
    "sanitize_params",
]

_SENSITIVE_KEYS = frozenset(
    {
        "api_key",
        "apikey",
        "key",
        "token",
        "access_token",
        "secret",
        "password",
        "auth",
        "authorization",
        "x_api_key",
        "bearer",
    }
)


def parse_query_params(
    query_string: str,
) -> dict[str, str | int | float | bool | None]:
    """Parse query string into dict."""
    if not query_string:
        return {}
    return dict(parse_qsl(query_string, keep_blank_values=True))


def sanitize_base_url(parsed: SplitResult) -> str:
    """Build a credential-free base URL while preserving host and port."""
    hostname = parsed.hostname or ""
    if ":" in hostname and not hostname.startswith("["):
        hostname = f"[{hostname}]"
    try:
        port = parsed.port
    except ValueError as exc:
        raise ValueError("Request URL contains an invalid port") from exc
    netloc = f"{hostname}:{port}" if port is not None else hostname
    return f"{parsed.scheme}://{netloc}"


def sanitize_params(
    params: JsonDict,  # Any: untyped API JSON record
) -> dict[str, str | int | float | bool | None]:
    """Sanitize query parameters to exclude sensitive data."""
    result: dict[str, str | int | float | bool | None] = {}
    for key, value in params.items():
        normalized_key = key.lower().replace("-", "_")
        if normalized_key in _SENSITIVE_KEYS:
            result[key] = "[REDACTED]"
        elif isinstance(value, (str, int, float, bool)) or value is None:
            result[key] = value
        else:
            result[key] = str(value)
    return result


def normalize_http_method(method: str) -> Literal["GET", "POST", "HEAD"]:
    """Normalize HTTP method to SourceMetadata-compatible literal."""
    normalized = method.upper()
    if normalized == "GET":
        return "GET"
    if normalized == "POST":
        return "POST"
    if normalized == "HEAD":
        return "HEAD"
    return "GET"


def parse_int_header(value: str | None) -> int | None:
    """Parse integer header value."""
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def parse_float_header(value: str | None) -> float | None:
    """Parse float header value."""
    if value is None:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def parse_reset_header(value: str | None) -> datetime | None:
    """Parse X-RateLimit-Reset header (Unix timestamp or HTTP date)."""
    if value is None:
        return None
    try:
        timestamp = int(value)
        return datetime.fromtimestamp(timestamp, tz=UTC)
    except ValueError:
        pass  # Why: response body not JSON-parseable as Unix timestamp; return None
    return None
