"""Typed registry backing the public composition entrypoint functions."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import cast

from bioetl.application.ports.health import HealthServiceProtocol

_REGISTRY: dict[type[object], Callable[[], object]] = {}


def register[T](port: type[T], factory: Callable[[], T]) -> None:
    """Register a zero-argument factory for a port or protocol type."""
    _REGISTRY[cast(type[object], port)] = cast(Callable[[], object], factory)


def resolve[T](port: type[T]) -> T:
    """Resolve a registered port factory."""
    factory = _REGISTRY.get(cast(type[object], port))
    if factory is None:
        raise KeyError(f"no composition factory registered for {port!r}")
    return cast(T, factory())


def registered_ports() -> Mapping[type[object], Callable[[], object]]:
    """Return an isolated snapshot of registered composition factories."""
    return dict(_REGISTRY)


def _build_health_service() -> HealthServiceProtocol:
    """Build provider-health orchestration without eager bootstrap imports."""
    from bioetl.composition.bootstrap.cli.health import bootstrap_health_service

    return bootstrap_health_service()


register(HealthServiceProtocol, _build_health_service)
