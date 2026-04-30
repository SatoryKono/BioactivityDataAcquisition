"""Shared test helpers for explicit adapter runtime dependency injection."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort, MetricsPort
    from bioetl.infrastructure.adapters.common import (
        FallbackFetchOrchestrator,
        HttpAdapterDependencyContext,
    )

__all__ = [
    "HttpAdapterRuntimeBundle",
    "build_http_adapter_runtime_bundle",
    "build_http_adapter_runtime_kwargs",
]


@dataclass(frozen=True, slots=True)
class HttpAdapterRuntimeBundle:
    """Explicit runtime collaborators for HTTP adapter tests."""

    dependency_context: HttpAdapterDependencyContext
    fallback_fetch_service: FallbackFetchOrchestrator


def build_http_adapter_runtime_bundle(
    provider: str,
    *,
    logger: LoggerPort,
    metrics: MetricsPort | None = None,
) -> HttpAdapterRuntimeBundle:
    """Build the same HTTP adapter helper bundle as the composition root."""
    from bioetl.composition.factories.datasource.adapter_helpers import (
        AdapterHelpersFactory,
    )

    helper_services = AdapterHelpersFactory.create_http_helpers(
        provider=provider,
        logger=logger,
        metrics=metrics,
    )
    return HttpAdapterRuntimeBundle(
        dependency_context=helper_services.build_dependency_context(),
        fallback_fetch_service=helper_services.fallback_fetch_service,
    )


def build_http_adapter_runtime_kwargs(
    provider: str,
    *,
    logger: LoggerPort,
    metrics: MetricsPort | None = None,
    include_fallback_service: bool = False,
) -> dict[str, object]:
    """Return explicit kwargs payload for direct adapter constructors in tests."""
    runtime_bundle = build_http_adapter_runtime_bundle(
        provider,
        logger=logger,
        metrics=metrics,
    )
    kwargs: dict[str, object] = {
        "dependency_context": runtime_bundle.dependency_context,
    }
    if include_fallback_service:
        kwargs["fallback_fetch_service"] = runtime_bundle.fallback_fetch_service
    return kwargs
