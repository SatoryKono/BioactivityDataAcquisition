"""OpenAlex runtime wiring helpers and request-style API."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from bioetl.domain.ports import LoggerPort, MetricsPort, TracingPort
from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient

if TYPE_CHECKING:
    from bioetl.infrastructure.config import Settings


@dataclass(frozen=True)
class OpenAlexRuntimeServicesRequest:
    """Request object for OpenAlex runtime services bundle.
    
    Centralizes all dependencies needed to build OpenAlex adapter runtime services.
    """
    settings: Settings
    http_client: UnifiedHTTPClient
    tracer: TracingPort
    metrics: MetricsPort
    logger: LoggerPort


@dataclass(frozen=True)
class OpenAlexRuntimeServicesBundle:
    """Bundle of OpenAlex runtime services.
    
    Contains all services needed for OpenAlex adapter operation.
    """
    http_client: UnifiedHTTPClient
    tracer: TracingPort
    metrics: MetricsPort
    logger: LoggerPort


# Legacy compatibility wrapper
# TODO: remove after full migration to request-style API
def build_openalex_runtime_services(
    settings: Settings,
    http_client: UnifiedHTTPClient,
    tracer: TracingPort,
    metrics: MetricsPort,
    logger: LoggerPort,
) -> OpenAlexRuntimeServicesBundle:
    """Build OpenAlex runtime services bundle (legacy API).
    
    This is a compatibility wrapper around the new request-style API.
    Will be removed after full migration.
    """
    request = OpenAlexRuntimeServicesRequest(
        settings=settings,
        http_client=http_client,
        tracer=tracer,
        metrics=metrics,
        logger=logger,
    )
    return _build_openalex_runtime_services_from_request(request)


def _build_openalex_runtime_services_from_request(
    request: OpenAlexRuntimeServicesRequest,
) -> OpenAlexRuntimeServicesBundle:
    """Build OpenAlex runtime services bundle from request (new API).
    
    This is the core implementation that centralizes all OpenAlex runtime wiring.
    """
    # Validate request
    if not request.settings:
        raise ValueError("OpenAlex settings are required")
    if not request.http_client:
        raise ValueError("HTTP client is required")
    if not request.tracer:
        raise ValueError("Tracer is required")
    if not request.metrics:
        raise ValueError("Metrics port is required")
    if not request.logger:
        raise ValueError("Logger is required")
    
    # Build and return bundle
    return OpenAlexRuntimeServicesBundle(
        http_client=request.http_client,
        tracer=request.tracer,
        metrics=request.metrics,
        logger=request.logger,
    )


__all__ = [
    "OpenAlexRuntimeServicesRequest",
    "OpenAlexRuntimeServicesBundle",
    "build_openalex_runtime_services",
    "_build_openalex_runtime_services_from_request",
]
