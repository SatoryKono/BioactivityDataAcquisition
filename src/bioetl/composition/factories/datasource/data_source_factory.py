"""Canonical data-source factory module with a retained legacy compat facade."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
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
    ensure_provider_registry_ready,
    resolve_provider_registry,
)
from bioetl.domain.ports import DataSourcePort

if TYPE_CHECKING:
    from bioetl.domain.filtering import InputFilterConfig
    from bioetl.domain.ports import DataSourcePort, LoggerPort, MetricsPort
    from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
    from bioetl.infrastructure.config.settings_api import Settings
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig


@lru_cache(maxsize=1)
def _get_default_provider_names() -> frozenset[str]:
    """Return config-backed provider names without loading the provider graph."""
    providers_dir = Path(__file__).resolve().parents[5] / "configs" / "providers"
    configured_provider_names = frozenset(
        path.stem for path in providers_dir.glob("*.yaml")
    )
    registry_only_provider_names = frozenset({"uniprot_idmapping"})
    return configured_provider_names | registry_only_provider_names


def get_data_source_creator(
    provider: str,
    *,
    provider_registry: ProviderDataSourceAccessProtocol | None = None,
) -> DataSourceCreatorProtocol:
    """Return the canonical provider-bound data-source creator callback."""
    resolved_registry = cast(
        "ProviderDataSourceAccessProtocol",
        resolve_provider_registry(provider_registry, ensure_ready=False),
    )
    available_providers = resolved_registry.list_providers()
    if available_providers and not resolved_registry.is_registered(provider):
        available = ", ".join(available_providers)
        raise KeyError(f"Unknown provider: {provider}. Available: {available}")
    if provider_registry is None and provider not in _get_default_provider_names():
        available = ", ".join(sorted(_get_default_provider_names()))
        raise KeyError(f"Unknown provider: {provider}. Available: {available}")
    cached_creator: DataSourceCreatorProtocol | None = None

    def _lazy_creator(
        settings: object,
        pipeline_config: "PipelineYamlConfig",
        logger: "LoggerPort",
        filter_config: "InputFilterConfig | None" = None,
        metrics: "MetricsPort | None" = None,
        pipeline_name: str = "unknown",
    ) -> DataSourcePort:
        nonlocal cached_creator
        if cached_creator is None:
            ready_registry = cast(
                "ProviderDataSourceAccessProtocol",
                ensure_provider_registry_ready(resolved_registry),
            )
            cached_creator = ready_registry.build_data_source_creator(provider)
        return cached_creator(
            settings=settings,
            pipeline_config=pipeline_config,
            logger=logger,
            filter_config=filter_config,
            metrics=metrics,
            pipeline_name=pipeline_name,
        )

    return cast("DataSourceCreatorProtocol", _lazy_creator)


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
