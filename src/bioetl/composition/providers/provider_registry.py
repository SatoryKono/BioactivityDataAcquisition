"""Provider Registry - unified data provider registry.

Centralizes provider registration, eliminating the need
to modify multiple files when adding a new provider.

After unification with DataSourceRegistry, this module is also responsible for
high-level data source creation with filtering support.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, ClassVar, Protocol

if TYPE_CHECKING:
    from bioetl.domain.filtering import InputFilterConfig
    from bioetl.domain.ports import DataSourcePort, LoggerPort, MetricsPort
    from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
    from bioetl.infrastructure.config import Settings
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig


@dataclass(frozen=True)
class HttpConfig:
    """HTTP client configuration for a provider.

    Attributes:
        rate: Base rate limit (requests/second).
        capacity: Token bucket capacity.
        rate_overrides: Conditional rate limit overrides.
            Key is a Settings attribute name (e.g., "pubmed_api_key"),
            value is the new rate when that attribute is present.
    """

    rate: float = 5.0
    capacity: int = 10
    rate_overrides: dict[str, float] = field(default_factory=dict)


# Type alias for low-level adapter creator
AdapterCreator = Callable[..., "DataSourcePort"]


class DataSourceCreator(Protocol):
    """Protocol for high-level data source creator functions.

    These functions create fully configured data sources with filtering support.
    """

    def __call__(
        self,
        settings: Settings,
        pipeline_config: PipelineYamlConfig,
        logger: LoggerPort,
        filter_config: InputFilterConfig | None = None,
        metrics: MetricsPort | None = None,
        pipeline_name: str = "unknown",
    ) -> DataSourcePort:
        """Create a configured data source.

        Args:
            settings: Application settings
            pipeline_config: Pipeline configuration from YAML
            logger: LoggerPort instance for structured logging
            filter_config: Optional filter configuration
            metrics: Optional metrics port for recording filter statistics
            pipeline_name: Pipeline name for metrics labels

        Returns:
            Configured DataSourcePort instance
        """
        ...


@dataclass(frozen=True)
class ProviderConfig:
    """Complete provider configuration.

    Attributes:
        adapter_class: Adapter class implementing DataSourcePort.
        http_config: HTTP client configuration (None if the provider
            manages its own client independently).
        requires_http_client: Whether an HTTP client is needed for initialization.
        requires_logger: Whether a logger is needed for initialization.
        default_kwargs: Additional kwargs for the adapter constructor.
        custom_creator: Custom adapter creation function for
            complex cases (e.g., PubMed with API key logic).
        data_source_creator: High-level data source creation function
            with filtering support. If specified, used instead of
            the standard logic in create_data_source().
    """

    adapter_class: type[DataSourcePort]
    http_config: HttpConfig | None = None
    requires_http_client: bool = True
    requires_logger: bool = True
    default_kwargs: dict[
        str, Any  # Any: provider kwargs vary by adapter
    ] = field(default_factory=dict)
    custom_creator: AdapterCreator | None = None
    data_source_creator: DataSourceCreator | None = None


class ProviderRegistry:
    """Unified data provider registry.

    Centralizes:
    - Provider adapter registration
    - HTTP client configuration
    - Adapter instance creation

    Example:
        >>> from bioetl.composition.providers import ProviderRegistry, register_provider
        >>>
        >>> @register_provider("mydb", http_rate=10.0)
        ... class MyDBAdapter:
        ...     pass
        >>>
        >>> adapter = ProviderRegistry.create_adapter("mydb", http_client=client)
    """

    _providers: ClassVar[dict[str, ProviderConfig]] = {}

    @classmethod
    def register(cls, name: str, config: ProviderConfig) -> None:
        """Register a provider.

        Re-registering the same provider overwrites the configuration.
        This allows correct behavior during module reloads.

        Args:
            name: Unique provider name (e.g., "chembl", "pubchem").
            config: Provider configuration.
        """
        cls._providers[name] = config

    @classmethod
    def get(cls, name: str) -> ProviderConfig:
        """Return provider configuration.

        Args:
            name: Provider name.

        Returns:
            Provider configuration.

        Raises:
            KeyError: If the provider is not registered.
        """
        if name not in cls._providers:
            available = ", ".join(sorted(cls._providers.keys()))
            raise KeyError(f"Unknown provider: {name}. Available: {available}")
        return cls._providers[name]

    @classmethod
    def is_registered(cls, name: str) -> bool:
        """Check whether a provider is registered.

        Args:
            name: Provider name.

        Returns:
            True if the provider is registered.
        """
        return name in cls._providers

    @classmethod
    def create_adapter(
        cls,
        name: str,
        http_client: UnifiedHTTPClient | None = None,
        logger: LoggerPort | None = None,
        settings: Settings | None = None,
        **kwargs: Any,  # Any: forwarded adapter cons...
    ) -> DataSourcePort:
        """Create a provider adapter instance.

        Args:
            name: Provider name.
            http_client: HTTP client (required for providers with
                requires_http_client=True).
            logger: Logger (required for providers with requires_logger=True).
            settings: Application settings (for custom creators).
            **kwargs: Additional arguments for the constructor.

        Returns:
            Adapter instance implementing DataSourcePort.

        Raises:
            KeyError: If the provider is not registered.
            ValueError: If a required http_client or logger is not provided.
        """
        config = cls.get(name)

        # Use custom creator if available
        if config.custom_creator:
            return config.custom_creator(
                http_client=http_client,
                logger=logger,
                settings=settings,
                **kwargs,
            )

        # Standard creation logic
        init_kwargs: dict[
            str, Any  # Any: factory wiring; concrete types resolved at runtime
        ] = {  # Any: factory wiring; concrete types resolved at runtime
            **config.default_kwargs,
            **kwargs,
        }  # Any: factory wiring; concrete types resolved at runtime

        if config.requires_http_client:
            if http_client is None:
                raise ValueError(
                    f"Provider '{name}' requires http_client but none was provided. "
                    "Ensure http_client is passed from Composition Root."
                )
            init_kwargs["http_client"] = http_client

        if config.requires_logger:
            if logger is None:
                raise ValueError(
                    f"Provider '{name}' requires logger but none was provided. "
                    "Ensure logger is passed from Composition Root."
                )
            init_kwargs["logger"] = logger

        return config.adapter_class(**init_kwargs)

    @classmethod
    def get_http_config(cls, name: str) -> HttpConfig | None:
        """Return the HTTP configuration for a provider.

        Args:
            name: Provider name.

        Returns:
            HttpConfig or None if the provider does not use a shared HTTP client.
        """
        config = cls.get(name)
        return config.http_config

    @classmethod
    def create_data_source(
        cls,
        name: str,
        settings: Settings,
        pipeline_config: PipelineYamlConfig,
        logger: LoggerPort,
        filter_config: InputFilterConfig | None = None,
        metrics: MetricsPort | None = None,
        pipeline_name: str = "unknown",
    ) -> DataSourcePort:
        """Create a fully configured data source with filtering support.

        High-level method combining the functionality of ProviderRegistry
        and the former DataSourceRegistry. Uses data_source_creator from
        the provider configuration if one is specified.

        Args:
            name: Provider name.
            settings: Application settings.
            pipeline_config: Pipeline configuration from YAML.
            logger: LoggerPort instance for structured logging.
            filter_config: Optional filter configuration.
            metrics: Optional MetricsPort for statistics.
            pipeline_name: Pipeline name for metric labels.

        Returns:
            Configured DataSourcePort with filtering support.

        Raises:
            KeyError: If the provider is not registered.
            ValueError: If data_source_creator is not set for the provider.
        """
        config = cls.get(name)

        if config.data_source_creator is None:
            raise ValueError(
                f"Provider '{name}' does not have a data_source_creator configured. "
                "Register the provider with a data_source_creator in registration.py."
            )

        return config.data_source_creator(
            settings=settings,
            pipeline_config=pipeline_config,
            logger=logger,
            filter_config=filter_config,
            metrics=metrics,
            pipeline_name=pipeline_name,
        )

    @classmethod
    def has_data_source_creator(cls, name: str) -> bool:
        """Check whether a provider has a data_source_creator.

        Args:
            name: Provider name.

        Returns:
            True if the provider has a data_source_creator.
        """
        if not cls.is_registered(name):
            return False
        config = cls.get(name)
        return config.data_source_creator is not None

    @classmethod
    def list_providers(cls) -> list[str]:
        """List all registered providers.

        Returns:
            Sorted list of provider names.
        """
        return sorted(cls._providers.keys())

    @classmethod
    def clear(cls) -> None:
        """Clear the registry. Used for testing."""
        cls._providers.clear()
