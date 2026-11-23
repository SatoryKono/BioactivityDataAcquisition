"""Shared request-header helpers for Semantic Scholar adapter flows."""

from __future__ import annotations

__all__ = ["build_semanticscholar_headers", "normalize_semanticscholar_api_key"]

from bioetl.infrastructure.adapters.base import (
    BIOETL_USER_AGENT,
    build_json_accept_headers,
)


def normalize_semanticscholar_api_key(api_key: str) -> str:
    """Trim a configured key and resolve ``your_*`` placeholders as anonymous."""
    normalized = api_key.strip()
    if normalized.lower().startswith("your_"):
        return ""
    return normalized


def build_semanticscholar_headers(
    api_key: str,
    *,
    include_content_type: bool,
    skip_placeholder_api_key: bool,
) -> dict[str, str]:
    """Build Semantic Scholar request headers with optional API-key handling.

    Args:
        api_key: Optional configured Semantic Scholar API key.
        include_content_type: When True, include JSON content type header.
        skip_placeholder_api_key: When True, suppress placeholder values such as
            ``your_*`` from being sent as real API keys.

    Returns:
        Dictionary of HTTP headers for Semantic Scholar requests.
    """
    headers = build_json_accept_headers(BIOETL_USER_AGENT)
    if include_content_type:
        headers["Content-Type"] = "application/json"
    request_key = (
        normalize_semanticscholar_api_key(api_key)
        if skip_placeholder_api_key
        else api_key
    )
    if request_key:
        headers["x-api-key"] = request_key
    return headers
