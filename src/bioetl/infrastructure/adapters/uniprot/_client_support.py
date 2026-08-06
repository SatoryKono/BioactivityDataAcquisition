"""Factory helper for registry-based UniProt adapter construction."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from bioetl.infrastructure.adapters.uniprot.client import UniProtAdapter
from bioetl.infrastructure.adapters.uniprot.constants import UNIPROT_API_BASE

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort
    from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient

__all__ = ["_create_uniprot_adapter"]


def _create_uniprot_adapter(
    http_client: UnifiedHTTPClient | None,
    logger: LoggerPort | None,
    _settings: object | None,
    **kwargs: Any,  # Any: forwarding arbitrary kwargs to HTTP client
) -> UniProtAdapter:
    """Factory helper for registry-based adapter construction.

    Args:
        http_client: HTTP client for API requests; raises ValueError if None.
        logger: Logger port for structured logging; raises ValueError if None.
        _settings: Application settings (unused; present for registry signature compatibility).
        **kwargs: Additional keyword arguments forwarded to UniProtAdapter constructor.

    Returns:
        UniProtAdapter instance configured with the given HTTP client and logger.

    Raises:
        ValueError: If http_client or logger is None.
    """
    if http_client is None:
        raise ValueError("UniProt adapter requires http_client")
    if logger is None:
        raise ValueError("UniProt adapter requires logger")
    if "fallback_fetch_service" not in kwargs:
        raise ValueError("UniProt adapter requires fallback_fetch_service")

    return UniProtAdapter(
        http_client=http_client,
        logger=logger,
        api_key=kwargs.get("api_key"),
        base_url=kwargs.get("base_url", UNIPROT_API_BASE),
        strict_error_handling=kwargs.get("strict_error_handling", False),
        metrics=kwargs.get("metrics"),
        dependency_context=kwargs.get("dependency_context"),
        error_handler=kwargs.get("error_handler"),
        adapter_metrics=kwargs.get("adapter_metrics"),
        request_collector=kwargs.get("request_collector"),
        fallback_fetch_service=kwargs["fallback_fetch_service"],
    )
