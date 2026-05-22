"""Canonical data-source factory module with a retained legacy compat facade."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from bioetl.composition.factories.datasource.adapter_helpers import (
    AdapterHelpersFactory,
)
from bioetl.composition.factories.datasource.provider_registry_resolution import (
    resolve_datasource_provider_registry as _resolve_provider_registry,
)
from bioetl.composition.providers.provider_registry import (
    DataSourceCreatorProtocol,
    ProviderDataSourceAccessProtocol,
)
from bioetl.domain.ports import DataSourcePort

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort, MetricsPort
    from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
    from bioetl.infrastructure.config._base import Settings


def get_data_source_creator(
    provider: str,
    *,
    provider_registry: ProviderDataSourceAccessProtocol | None = None,
) -> DataSourceCreatorProtocol:
    """Return the canonical provider-bound data-source creator callback."""
    registry = _resolve_provider_registry(provider_registry)
    return registry.build_data_source_creator(provider)


class DataSourceFactory:
    """Factory for creating data source adapters."""

    @classmethod
    def create(
        cls,
        provider: str,
        http_client: UnifiedHTTPClient | None = None,
        logger: LoggerPort | None = None,
        settings: Settings | None = None,
        provider_registry: ProviderDataSourceAccessProtocol | None = None,
        **kwargs: object,
    ) -> DataSourcePort:
        """Create a data source adapter."""
        registry = _resolve_provider_registry(provider_registry)

        if not registry.is_registered(provider):
            available = ", ".join(registry.list_providers())
            raise ValueError(f"Unknown provider: {provider}. Available: {available}")

        adapter_kwargs = {k: v for k, v in kwargs.items() if k != "filter_config"}
        cls._inject_adapter_helpers(
            provider=provider,
            logger=logger,
            adapter_kwargs=adapter_kwargs,
        )

        adapter = registry.create_adapter(
            provider,
            http_client=http_client,
            logger=logger,
            settings=settings,
            **adapter_kwargs,
        )
        assert isinstance(adapter, DataSourcePort), (
            f"Adapter for provider '{provider}' must implement DataSourcePort, "
            f"got {type(adapter)}"
        )
        return adapter

    @staticmethod
    def _inject_adapter_helpers(
        *,
        provider: str,
        logger: LoggerPort | None,
        adapter_kwargs: dict[str, object],
    ) -> None:
        """Inject helper-service bundle for DI-target providers."""
        if not AdapterHelpersFactory.supports_provider(provider):
            return
        if logger is None:
            return

        required_keys = frozenset(
            {
                "error_handler",
                "adapter_metrics",
                "request_collector",
                "fallback_fetch_service",
            }
        )
        if required_keys.issubset(adapter_kwargs.keys()):
            return

        metrics = cast("MetricsPort | None", adapter_kwargs.get("metrics"))
        helpers = AdapterHelpersFactory.create_http_helpers(
            provider=provider,
            logger=logger,
            metrics=metrics,
        )
        for key, value in helpers.as_injection_kwargs().items():
            adapter_kwargs.setdefault(key, value)

    @classmethod
    def list_providers(cls) -> list[str]:
        """List all available providers."""
        providers: list[str] = _resolve_provider_registry().list_providers()
        return providers


__all__ = [
    "DataSourceCreatorProtocol",
    "DataSourceFactory",
    "get_data_source_creator",
]
