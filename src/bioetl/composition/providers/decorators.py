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


__all__ = [
    "T",
    "register_provider",
]

T = TypeVar("T", bound="DataSourcePort")


def _register_provider_class(
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
    """Register decorated adapter class in provider registry."""
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
    ProviderRegistry.register(name, config)
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
    """Decorator for registering a provider adapter class."""
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
