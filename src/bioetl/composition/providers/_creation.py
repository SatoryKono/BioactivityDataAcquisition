"""Shared adapter/data-source creation helpers for provider registry."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from bioetl.composition.providers._models import (
    DataSourceCreatorProtocol,
    ProviderConfig,
    ProviderSettingsProtocol,
)

if TYPE_CHECKING:
    from bioetl.domain.filtering import InputFilterConfig
    from bioetl.domain.ports import DataSourcePort, LoggerPort, MetricsPort
    from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig


@dataclass(frozen=True, slots=True)
class ProviderDataSourceCreationRequest:
    """Canonical request object for provider data-source creation."""

    name: str
    config: ProviderConfig
    settings: ProviderSettingsProtocol
    pipeline_config: PipelineYamlConfig
    logger: LoggerPort
    filter_config: InputFilterConfig | None = None
    metrics: MetricsPort | None = None
    pipeline_name: str = "unknown"


class ProviderCreator:
    """Consolidated provider adapter and data-source creation logic."""

    def create_adapter(
        self,
        *,
        name: str,
        config: ProviderConfig,
        http_client: UnifiedHTTPClient | None = None,
        logger: LoggerPort | None = None,
        settings: ProviderSettingsProtocol | None = None,
        **kwargs: object,
    ) -> DataSourcePort:
        """Create a provider adapter instance."""
        return create_provider_adapter(
            name=name,
            config=config,
            http_client=http_client,
            logger=logger,
            settings=settings,
            **kwargs,
        )

    def create_data_source(
        self,
        request: ProviderDataSourceCreationRequest,
    ) -> DataSourcePort:
        """Create a fully configured provider data source."""
        return create_provider_data_source(request)

    def has_data_source_creator(self, config: ProviderConfig) -> bool:
        """Return whether the provider config exposes a data-source creator."""
        return provider_has_data_source_creator(config)

    def require_data_source_creator(self, *, name: str, config: ProviderConfig) -> None:
        """Raise a stable error when a provider lacks data-source creator support."""
        require_provider_data_source_creator(name=name, config=config)

    def build_bound_creator(
        self,
        *,
        name: str,
        create_data_source_fn: DataSourceCreatorProtocol,
    ) -> DataSourceCreatorProtocol:
        """Return a provider-bound data-source creator closure."""
        return build_bound_data_source_creator(
            name=name,
            create_data_source=create_data_source_fn,
        )


def create_provider_adapter(
    *,
    name: str,
    config: ProviderConfig,
    http_client: UnifiedHTTPClient | None = None,
    logger: LoggerPort | None = None,
    settings: ProviderSettingsProtocol | None = None,
    **kwargs: object,
) -> DataSourcePort:
    """Create a provider adapter instance using the supplied registry config."""
    if config.adapter_creator is not None:
        return config.adapter_creator(
            http_client=http_client,
            logger=logger,
            settings=settings,
            **kwargs,
        )

    init_kwargs: dict[str, object] = {
        **config.default_kwargs,
        **kwargs,
    }
    _inject_http_client(
        provider_name=name,
        config=config,
        http_client=http_client,
        init_kwargs=init_kwargs,
    )
    _inject_logger(
        provider_name=name,
        config=config,
        logger=logger,
        init_kwargs=init_kwargs,
    )
    return config.adapter_class(**init_kwargs)


def create_provider_data_source(
    request: ProviderDataSourceCreationRequest,
) -> DataSourcePort:
    """Create a fully configured provider data source from registry metadata."""
    if request.config.data_source_creator is None:
        raise ValueError(
            f"Provider '{request.name}' does not have a data_source_creator configured. "
            "Register the provider with a data_source_creator in registration.py."
        )

    return request.config.data_source_creator(
        settings=request.settings,
        pipeline_config=request.pipeline_config,
        logger=request.logger,
        filter_config=request.filter_config,
        metrics=request.metrics,
        pipeline_name=request.pipeline_name,
    )


def provider_has_data_source_creator(config: ProviderConfig) -> bool:
    """Return whether the provider config exposes a data-source creator."""
    return config.data_source_creator is not None


def require_provider_data_source_creator(
    *,
    name: str,
    config: ProviderConfig,
) -> None:
    """Raise a stable error when a provider lacks data-source creator support."""
    if provider_has_data_source_creator(config):
        return
    raise KeyError(
        f"Provider '{name}' does not have a data_source_creator. "
        "Ensure it is registered with data_source_creator in registration.py."
    )


def build_bound_data_source_creator(
    *,
    name: str,
    create_data_source: DataSourceCreatorProtocol,
) -> DataSourceCreatorProtocol:
    """Return a provider-bound data-source creator closure."""
    del name

    def creator(
        settings: ProviderSettingsProtocol,
        pipeline_config: PipelineYamlConfig,
        logger: LoggerPort,
        filter_config: InputFilterConfig | None = None,
        metrics: MetricsPort | None = None,
        pipeline_name: str = "unknown",
    ) -> DataSourcePort:
        return create_data_source(
            settings=settings,
            pipeline_config=pipeline_config,
            logger=logger,
            filter_config=filter_config,
            metrics=metrics,
            pipeline_name=pipeline_name,
        )

    return creator


def _inject_http_client(
    *,
    provider_name: str,
    config: ProviderConfig,
    http_client: UnifiedHTTPClient | None,
    init_kwargs: dict[str, object],
) -> None:
    """Inject the shared HTTP client into adapter init kwargs when required."""
    if not config.requires_http_client:
        return
    if http_client is None:
        raise ValueError(
            f"Provider '{provider_name}' requires http_client but none was provided. "
            "Ensure http_client is passed from Composition Root."
        )
    init_kwargs["http_client"] = http_client


def _inject_logger(
    *,
    provider_name: str,
    config: ProviderConfig,
    logger: LoggerPort | None,
    init_kwargs: dict[str, object],
) -> None:
    """Inject structured logger into adapter init kwargs when required."""
    if not config.requires_logger:
        return
    if logger is None:
        raise ValueError(
            f"Provider '{provider_name}' requires logger but none was provided. "
            "Ensure logger is passed from Composition Root."
        )
    init_kwargs["logger"] = logger
