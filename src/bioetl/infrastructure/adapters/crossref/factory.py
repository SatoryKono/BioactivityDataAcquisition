"""CrossRef adapter factory function."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from bioetl.infrastructure.adapters.crossref.client import CrossRefAdapter

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort
    from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
    from bioetl.infrastructure.config import Settings

__all__ = ["_create_crossref_adapter"]


def _create_crossref_adapter(
    http_client: UnifiedHTTPClient | None,
    logger: LoggerPort | None,
    settings: Settings | None,
    **kwargs: Any,  # Any: forward arbitrary adapter config kwargs
) -> CrossRefAdapter:
    """Create CrossRefAdapter resolving mandatory `mailto` from kwargs/settings."""
    # Mailto: from kwargs or settings
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
