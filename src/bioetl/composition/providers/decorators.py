"""Decorators for provider registration.

Provides a declarative API for registering provider adapters.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, TypeVar

from bioetl.composition.providers._models import (
    AdapterCreator,
    HttpConfig,
    ProviderConfig,
)
from bioetl.composition.providers._default_registry import (
    register_default_provider_config,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from bioetl.domain.ports import DataSourcePort


__all__ = [
    "T",
    "register_provider",
]

T = TypeVar("T", bound="DataSourcePort")


def _register_provider_class[T: "DataSourcePort"](
    *,
    cls: type[T],
    name: str,
    http_rate: float,
    http_capacity: int,
    requires_http_client: bool,
    requires_logger: bool,
    rate_overrides: dict[str, float] | None,
    custom_creator: AdapterCreator | None,
    default_kwargs: dict[str, object],
) -> None:
    """Register decorated adapter class in provider registry.

    Args:
        cls: Adapter class implementing DataSourcePort to register.
        name: Unique provider name (e.g., 'chembl', 'pubchem').
        http_rate: Base rate limit in requests per second.
        http_capacity: Token bucket capacity for burst handling.
        requires_http_client: If True, http_client is injected at adapter creation.
        requires_logger: If True, logger is injected at adapter creation.
        rate_overrides: Optional dict mapping settings attribute names to boosted
            rate limits when API keys are present.
        custom_creator: Optional callable replacing the standard adapter creation
            logic for complex initialization.
        default_kwargs: Additional kwargs merged into the adapter constructor call.
    """
    http_config: HttpConfig | None = None
    if requires_http_client:
        http_config = HttpConfig(
            rate=http_rate,
            capacity=http_capacity,
            rate_overrides=rate_overrides or {},
        )

    config = ProviderConfig(
        adapter_class=cls,
        http_config=http_config,
        requires_http_client=requires_http_client,
        requires_logger=requires_logger,
        default_kwargs=default_kwargs,
        custom_creator=custom_creator,
    )
    # Decorators remain the sanctioned import-time compatibility seam for
    # populating the lazy default registry.
    register_default_provider_config(name, config)
    cls.__provider_name__ = name  # type: ignore[attr-defined]


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
    """Decorator for registering a provider adapter class.

    Args:
        name: Unique provider name (e.g., 'chembl', 'pubchem').
        http_rate: Base rate limit in requests per second; defaults to 5.0.
        http_capacity: Token bucket capacity; defaults to 10.
        requires_http_client: If True, http_client is injected at adapter creation;
            defaults to True.
        requires_logger: If True, logger is injected at adapter creation;
            defaults to True.
        rate_overrides: Optional dict mapping settings attribute names to boosted
            rate limits when API keys are present; defaults to None.
        custom_creator: Optional callable replacing standard adapter creation;
            defaults to None.
        **default_kwargs: Additional kwargs merged into the adapter constructor.

    Returns:
        Class decorator that registers the adapter and returns it unchanged.
    """
    resolved_defaults = dict(default_kwargs)

    def decorator(cls: type[T]) -> type[T]:
        """Register class and return it unchanged."""
        _register_provider_class(
            cls=cls,
            name=name,
            http_rate=http_rate,
            http_capacity=http_capacity,
            requires_http_client=requires_http_client,
            requires_logger=requires_logger,
            rate_overrides=rate_overrides,
            custom_creator=custom_creator,
            default_kwargs=dict(resolved_defaults),
        )
        return cls

    return decorator
