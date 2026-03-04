"""Decorators for provider registration.

Provides a declarative API for registering provider adapters.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, TypeVar

from bioetl.composition.providers.provider_registry import (
    AdapterCreator,
    HttpConfig,
    ProviderConfig,
    ProviderRegistry,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from bioetl.domain.ports import DataSourcePort

T = TypeVar("T", bound="DataSourcePort")


def register_provider(
    name: str,
    *,
    http_rate: float = 5.0,
    http_capacity: int = 10,
    requires_http_client: bool = True,
    requires_logger: bool = True,
    rate_overrides: dict[str, float] | None = None,
    custom_creator: AdapterCreator | None = None,
    **default_kwargs: object,
) -> Callable[[type[T]], type[T]]:
    """Decorator for registering a data provider.

    Registers the adapter class in ProviderRegistry at module import time.

    Args:
        name: Unique provider name (e.g., "chembl", "pubchem").
        http_rate: Rate limit for the HTTP client (requests/second).
        http_capacity: Token bucket capacity.
        requires_http_client: Whether an HTTP client is needed for initialization.
        requires_logger: Whether a logger is needed for initialization.
        rate_overrides: Conditional rate limit overrides.
            Key is a Settings attribute name, value is the new rate.
        custom_creator: Custom adapter creation function.
            If specified, used instead of the standard logic.
        **default_kwargs: Default kwargs for the adapter constructor.

    Returns:
        Class decorator.

    Example:
        >>> @register_provider(
        ...     "chembl",
        ...     http_rate=10.0,
        ...     http_capacity=20,
        ... )
        ... class ChemblAdapter:
        ...     def __init__(self, http_client, logger=None):
        ...         ...

        >>> # For providers with complex initialization logic:
        >>> def create_pubmed(http_client, logger, settings, **kwargs):
        ...     api_key = kwargs.get("api_key") or settings.pubmed_api_key
        ...     return PubMedAdapter(http_client, logger, api_key=api_key)
        >>>
        >>> @register_provider(
        ...     "pubmed",
        ...     http_rate=3.0,
        ...     rate_overrides={"pubmed_api_key": 10.0},
        ...     custom_creator=create_pubmed,
        ... )
        ... class PubMedAdapter:
        ...     ...
    """

    def decorator(cls: type[T]) -> type[T]:
        """Inner decorator that performs provider registration.

        Captures configuration from the outer scope and registers the
        decorated class with ProviderRegistry. Also injects __provider_name__
        attribute for runtime introspection.

        Args:
            cls: The adapter class being decorated.

        Returns:
            The original class unchanged (registration is a side effect).

        Side effects:
            - Registers provider in ProviderRegistry with captured config
            - Adds __provider_name__ attribute to the class
        """
        # Create HTTP configuration
        http_config: HttpConfig | None = None
        if requires_http_client:
            http_config = HttpConfig(
                rate=http_rate,
                capacity=http_capacity,
                rate_overrides=rate_overrides or {},
            )

        # Create provider configuration
        config = ProviderConfig(
            adapter_class=cls,
            http_config=http_config,
            requires_http_client=requires_http_client,
            requires_logger=requires_logger,
            default_kwargs=dict(default_kwargs),
            custom_creator=custom_creator,
        )

        # Register the provider
        ProviderRegistry.register(name, config)

        # Store the provider name on the class for introspection
        cls.__provider_name__ = name  # type: ignore[attr-defined]

        return cls

    return decorator
