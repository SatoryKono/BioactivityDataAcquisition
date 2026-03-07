"""Helper utilities for rate-limit exception construction."""

from __future__ import annotations


def resolve_rate_limit_params(
    provider: str | None,
    message: str | None,
    service_name: str | None,
) -> tuple[str, str, str | None]:
    """Resolve provider name, message text, and service name for RateLimitError."""
    resolved_service = service_name if service_name is not None else provider
    resolved_message = (
        message
        if message is not None
        else (provider if provider is not None else "Rate limit exceeded")
    )
    provider_name = resolved_service if resolved_service is not None else "unknown"
    return provider_name, resolved_message, resolved_service
