"""Factory helpers for PubMed adapter construction."""

# pyright: reportImportCycles=false
from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort
    from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
    from bioetl.infrastructure.config.settings_api import Settings

    from .adapter import PubMedAdapter

__all__ = [
    "_create_pubmed_adapter",
    "_require_pubmed_runtime",
    "_resolve_pubmed_api_key",
    "_resolve_pubmed_email",
]


def _resolve_pubmed_email(
    settings: Settings | None,
    kwargs: dict[str, Any],  # Any: opaque factory kwargs from adapter registry
) -> str | None:
    """Resolve PubMed contact email from kwargs or settings."""
    email = kwargs.get("email")
    if email is not None:
        return str(email)
    if settings is None:
        return None
    default_email = getattr(settings, "default_email", None)
    return str(default_email) if default_email is not None else None


def _resolve_pubmed_api_key(
    settings: Settings | None,
    kwargs: dict[str, Any],  # Any: opaque factory kwargs from adapter registry
) -> str | None:
    """Resolve PubMed API key from kwargs or settings secrets."""
    api_key = kwargs.get("api_key")
    if api_key is not None:
        return str(api_key)
    if settings is None or not hasattr(settings, "pubmed_api_key"):
        return None
    pubmed_key = settings.pubmed_api_key
    if not pubmed_key:
        return None
    return str(pubmed_key.get_secret_value())


def _require_pubmed_runtime(
    http_client: UnifiedHTTPClient | None,
    logger: LoggerPort | None,
    kwargs: dict[str, Any],  # Any: opaque factory kwargs from adapter registry
) -> tuple[UnifiedHTTPClient, LoggerPort]:
    """Validate required PubMed runtime dependencies."""
    if http_client is None:
        raise ValueError("PubMed adapter requires http_client")
    if logger is None:
        raise ValueError("PubMed adapter requires logger")
    if "fallback_fetch_service" not in kwargs:
        raise ValueError("PubMed adapter requires fallback_fetch_service")
    return http_client, logger


def _create_pubmed_adapter(
    http_client: UnifiedHTTPClient | None,
    logger: LoggerPort | None,
    settings: Settings | None,
    **kwargs: Any,  # Any: forward arbitrary adapter kwargs
) -> PubMedAdapter:
    """Create a PubMed adapter with resolved credentials.

    Email precedence: kwargs['email'] > settings.default_email.
    API key precedence: kwargs['api_key'] > settings.pubmed_api_key.

    Args:
        http_client: HTTP client (required).
        logger: Logger (required).
        settings: Application settings for fallback email/api_key resolution.
        **kwargs: email, api_key, batch_size, metrics, error_handler,
            adapter_metrics, request_collector, fallback_fetch_service.

    Returns:
        Initialized PubMedAdapter.

    Raises:
        ValueError: If email, http_client, or logger not provided.
    """
    from .adapter import PubMedAdapter

    email = _resolve_pubmed_email(settings, kwargs)
    if not email:
        raise ValueError("PubMed adapter requires email")
    api_key = _resolve_pubmed_api_key(settings, kwargs)
    resolved_http_client, resolved_logger = _require_pubmed_runtime(
        http_client,
        logger,
        kwargs,
    )
    return PubMedAdapter(
        http_client=resolved_http_client,
        logger=resolved_logger,
        email=email,
        api_key=api_key,
        batch_size=kwargs.get("batch_size", 200),
        metrics=kwargs.get("metrics"),
        dependency_context=kwargs.get("dependency_context"),
        error_handler=kwargs.get("error_handler"),
        adapter_metrics=kwargs.get("adapter_metrics"),
        request_collector=kwargs.get("request_collector"),
        fallback_fetch_service=kwargs["fallback_fetch_service"],
    )
