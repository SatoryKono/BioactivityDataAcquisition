"""Adapter creation helpers for bibliographic provider registration."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from bioetl.composition.factories.datasource.adapter_helpers import (
    AdapterHelpersFactory,
)
from bioetl.composition.providers._models import ProviderSettingsProtocol

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort
    from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
    from bioetl.infrastructure.adapters.openalex import OpenAlexAdapter
    from bioetl.infrastructure.adapters.pubmed import PubMedAdapter


def _get_default_email(settings: ProviderSettingsProtocol | None) -> str | None:
    """Return non-empty default email from settings when available."""
    return None if settings is None else settings.default_email or None


def _get_pubmed_api_key(settings: ProviderSettingsProtocol | None) -> str | None:
    """Return resolved PubMed API key from settings when configured."""
    if settings is None or settings.pubmed_api_key is None:
        return None
    return settings.pubmed_api_key.get_secret_value()


def _get_openalex_api_key(settings: ProviderSettingsProtocol | None) -> str | None:
    """Return resolved OpenAlex API key from settings when configured."""
    if settings is None or settings.openalex_api_key is None:
        return None
    return settings.openalex_api_key.get_secret_value()


def _build_pubmed_adapter_from_settings(
    *,
    adapter_cls: type[PubMedAdapter],
    http_client: UnifiedHTTPClient | None,
    logger: LoggerPort | None,
    settings: ProviderSettingsProtocol | None,
    **kwargs: Any,  # Any: forward arbitrary adapter kwargs
) -> PubMedAdapter:
    """Create PubMedAdapter with credential resolution owned by composition."""
    email = kwargs.get("email") or _get_default_email(settings)
    if not email:
        raise ValueError("PubMed adapter requires email")

    api_key = kwargs.get("api_key") or _get_pubmed_api_key(settings)

    if http_client is None:
        raise ValueError("PubMed adapter requires http_client")
    if logger is None:
        raise ValueError("PubMed adapter requires logger")
    metrics = kwargs.get("metrics")
    helper_services = AdapterHelpersFactory.create_http_helpers(
        provider="pubmed",
        logger=logger,
        metrics=metrics,
    )

    return adapter_cls(
        http_client=http_client,
        logger=logger,
        email=email,
        api_key=api_key,
        batch_size=kwargs.get("batch_size", 200),
        metrics=metrics,
        dependency_context=kwargs.get("dependency_context"),
        error_handler=kwargs.get("error_handler", helper_services.error_handler),
        adapter_metrics=kwargs.get(
            "adapter_metrics",
            helper_services.adapter_metrics,
        ),
        request_collector=kwargs.get(
            "request_collector",
            helper_services.request_collector,
        ),
        fallback_fetch_service=kwargs.get(
            "fallback_fetch_service",
            helper_services.fallback_fetch_service,
        ),
    )


def _build_openalex_adapter_from_settings(
    *,
    adapter_cls: type[OpenAlexAdapter],
    http_client: UnifiedHTTPClient | None,
    logger: LoggerPort | None,
    settings: ProviderSettingsProtocol | None,
    **kwargs: Any,  # Any: forward arbitrary adapter kwargs
) -> OpenAlexAdapter:
    """Create OpenAlexAdapter with API-key/mailto resolution owned by composition."""
    api_key = kwargs.get("api_key") or _get_openalex_api_key(settings)
    mailto = kwargs.get("mailto") or _get_default_email(settings)
    if not api_key and not mailto:
        raise ValueError(
            "OpenAlex adapter requires api_key or mailto. "
            "Provide via 'api_key' kwarg/BIOETL_OPENALEX_API_KEY or "
            "'mailto' kwarg/settings.default_email for legacy compatibility"
        )

    if http_client is None:
        raise ValueError("OpenAlex adapter requires http_client")
    if logger is None:
        raise ValueError("OpenAlex adapter requires logger")
    metrics = kwargs.get("metrics")
    helper_services = AdapterHelpersFactory.create_http_helpers(
        provider="openalex",
        logger=logger,
        metrics=metrics,
    )

    return adapter_cls(
        http_client=http_client,
        logger=logger,
        mailto=mailto,
        api_key=api_key,
        batch_size=kwargs.get("batch_size", 50),
        metrics=metrics,
        dependency_context=kwargs.get("dependency_context"),
        error_handler=kwargs.get("error_handler", helper_services.error_handler),
        adapter_metrics=kwargs.get(
            "adapter_metrics",
            helper_services.adapter_metrics,
        ),
        request_collector=kwargs.get(
            "request_collector",
            helper_services.request_collector,
        ),
        fallback_fetch_service=kwargs.get(
            "fallback_fetch_service",
            helper_services.fallback_fetch_service,
        ),
    )


__all__ = [
    "_build_openalex_adapter_from_settings",
    "_build_pubmed_adapter_from_settings",
]
