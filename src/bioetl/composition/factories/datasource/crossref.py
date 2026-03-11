"""CrossRef adapter factory for composition-layer wiring only."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from bioetl.infrastructure.adapters.crossref import CrossRefAdapter

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort
    from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
    from bioetl.infrastructure.config import Settings

__all__ = ["create_crossref_adapter"]


def create_crossref_adapter(
    http_client: UnifiedHTTPClient | None,
    logger: LoggerPort | None,
    settings: Settings | None,
    **kwargs: Any,  # Any: forward arbitrary adapter config kwargs
) -> CrossRefAdapter:
    """Create CrossRefAdapter resolving mandatory ``mailto`` from kwargs/settings.

    Args:
        http_client: HTTP client for CrossRef API calls; raises ValueError if None.
        logger: LoggerPort for structured logging; raises ValueError if None.
        settings: Optional application settings used to resolve default_email as
            fallback mailto when not provided in kwargs.
        **kwargs: Additional adapter kwargs forwarded to CrossRefAdapter, including
            mailto, batch_size, metrics, error_handler, adapter_metrics,
            request_collector, and fallback_fetch_service.

    Returns:
        Configured CrossRefAdapter instance.

    Raises:
        ValueError: If mailto cannot be resolved or http_client/logger is None.
    """
    mailto = kwargs.get("mailto")
    if not mailto and settings:
        mailto = getattr(settings, "default_email", None)
    if not mailto:
        raise ValueError(
            "CrossRef adapter requires mailto. "
            "Provide via 'mailto' kwarg or settings.default_email"
        )
    if http_client is None:
        raise ValueError("CrossRef adapter requires http_client")
    if logger is None:
        raise ValueError("CrossRef adapter requires logger")

    return CrossRefAdapter(
        http_client=http_client,
        logger=logger,
        mailto=mailto,
        batch_size=kwargs.get("batch_size", 50),
        metrics=kwargs.get("metrics"),
        error_handler=kwargs.get("error_handler"),
        adapter_metrics=kwargs.get("adapter_metrics"),
        request_collector=kwargs.get("request_collector"),
        fallback_fetch_service=kwargs.get("fallback_fetch_service"),
    )
