"""Factory helpers for OpenAlex adapter construction."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort
    from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
    from bioetl.infrastructure.adapters.openalex import OpenAlexAdapter
    from bioetl.infrastructure.config.settings_api import Settings

__all__ = [
    "_create_openalex_adapter",
    "_require_openalex_runtime",
    "_resolve_openalex_api_key",
    "_resolve_openalex_mailto",
]


def _resolve_openalex_api_key(
    settings: Settings | None,
    kwargs: dict[str, Any],  # Any: opaque factory kwargs from adapter registry
) -> str | None:
    """Resolve OpenAlex API key from kwargs or settings secrets."""
    api_key = kwargs.get("api_key")
    if api_key is not None:
        return str(api_key)
    if settings is None:
        return None
    settings_api_key = getattr(settings, "openalex_api_key", None)
    if not settings_api_key:
        return None
    if hasattr(settings_api_key, "get_secret_value"):
        secret_value = settings_api_key.get_secret_value()
        return str(secret_value)
    return str(settings_api_key)


def _resolve_openalex_mailto(
    settings: Settings | None,
    kwargs: dict[str, Any],  # Any: opaque factory kwargs from adapter registry
) -> str | None:
    """Resolve legacy OpenAlex mailto attribution from kwargs or settings."""
    mailto = kwargs.get("mailto")
    if mailto is not None:
        return str(mailto)
    if settings is None:
        return None
    default_email = getattr(settings, "default_email", None)
    return str(default_email) if default_email is not None else None


def _require_openalex_runtime(
    http_client: UnifiedHTTPClient | None,
    logger: LoggerPort | None,
    kwargs: dict[str, Any],  # Any: opaque factory kwargs from adapter registry
) -> tuple[UnifiedHTTPClient, LoggerPort]:
    """Validate required OpenAlex runtime dependencies."""
    if http_client is None:
        raise ValueError("OpenAlex adapter requires http_client")
    if logger is None:
        raise ValueError("OpenAlex adapter requires logger")
    if "fallback_fetch_service" not in kwargs:
        raise ValueError("OpenAlex adapter requires fallback_fetch_service")
    return http_client, logger


def _create_openalex_adapter(
    http_client: UnifiedHTTPClient | None,
    logger: LoggerPort | None,
    settings: Settings | None,
    **kwargs: Any,  # Any: forward arbitrary adapter kwargs
) -> OpenAlexAdapter:
    """Custom creator for OpenAlex adapter.

    Handles logic for obtaining OpenAlex credentials from settings.

    Args:
        http_client: HTTP client
        logger: Logger
        settings: Application settings
        **kwargs: Additional parameters (api_key, mailto, batch_size, metrics)

    Returns:
        Initialized OpenAlexAdapter

    Raises:
        ValueError: If neither api_key nor mailto can be resolved

    """
    from bioetl.infrastructure.adapters.openalex import OpenAlexAdapter

    api_key = _resolve_openalex_api_key(settings, kwargs)
    mailto = _resolve_openalex_mailto(settings, kwargs)
    if not api_key and not mailto:
        raise ValueError(
            "OpenAlex adapter requires api_key or mailto. "
            "Provide via 'api_key' kwarg/BIOETL_OPENALEX_API_KEY or "
            "'mailto' kwarg/settings.default_email for legacy compatibility"
        )

    resolved_http_client, resolved_logger = _require_openalex_runtime(
        http_client,
        logger,
        kwargs,
    )
    return OpenAlexAdapter(
        http_client=resolved_http_client,
        logger=resolved_logger,
        mailto=mailto,
        api_key=api_key,
        batch_size=kwargs.get("batch_size", 50),
        metrics=kwargs.get("metrics"),
        dependency_context=kwargs.get("dependency_context"),
        error_handler=kwargs.get("error_handler"),
        adapter_metrics=kwargs.get("adapter_metrics"),
        request_collector=kwargs.get("request_collector"),
        fallback_fetch_service=kwargs["fallback_fetch_service"],
    )
