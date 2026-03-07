"""Helper utilities for rate-limit exception construction."""

from __future__ import annotations


def resolve_rate_limit_params(
    provider: str | None,
    message: str | None,
    service_name: str | None,
) -> tuple[str, str, str | None]:
    """Resolve provider name, message text, and service name for RateLimitError.

    Args:
        provider: Provider identifier (e.g., 'chembl'). Used as fallback for message and service_name.
        message: Human-readable error message. Defaults to provider name or 'Rate limit exceeded'.
        service_name: Explicit service name override. Defaults to provider if None.

    Returns:
        Tuple of (provider_name, resolved_message, resolved_service_name).
    """
    resolved_service = service_name if service_name is not None else provider
    resolved_message = (
        message
        if message is not None
        else (provider if provider is not None else "Rate limit exceeded")
    )
    provider_name = resolved_service if resolved_service is not None else "unknown"
    return provider_name, resolved_message, resolved_service
