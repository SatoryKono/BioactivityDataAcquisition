"""Shared HTTP request-header builders for BioETL adapters."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping

__all__ = [
    "build_json_accept_headers",
    "build_mailto_user_agent_headers",
]


def build_json_accept_headers(
    user_agent: str,
    *,
    correlation_id: object | None = None,
    extra_headers: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Build the canonical JSON request-header set for BioETL adapters."""
    headers: dict[str, str] = {
        "User-Agent": user_agent,
        "Accept": "application/json",
    }
    if correlation_id is not None:
        headers["X-Correlation-ID"] = str(correlation_id)
    if extra_headers is not None:
        headers.update(extra_headers)
    return headers


def build_mailto_user_agent_headers(mailto: str) -> dict[str, str]:
    """Build the canonical polite-pool header set for mailto-aware providers."""
    return build_json_accept_headers(f"BioETL/1.0 (mailto:{mailto})")
