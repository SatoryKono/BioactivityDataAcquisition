"""Factory for adapter helper services assembled at composition root."""

from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from bioetl.composition.observability_resolution import resolve_metrics_port
from bioetl.domain.ports import (
    ErrorHandlerPort,
    LoggerPort,
    MetricsPort,
)
from bioetl.infrastructure.adapters.base_metrics import AdapterMetricsRecorder
from bioetl.infrastructure.adapters.common import (
    FallbackFetchOrchestrator,
    HttpAdapterDependencyContext,
    SyncAdapterDependencyContext,
)
from bioetl.infrastructure.adapters.common.api_request_collector import (
    APIRequestCollector,
)
from bioetl.infrastructure.adapters.error_handling import ErrorService

__all__ = [
    "AdapterHelperServices",
    "AdapterHelpersFactory",
    "SyncAdapterHelperServices",
]


@dataclass(frozen=True, slots=True)
class AdapterHelperServices:
    """Container with helper dependencies shared by HTTP adapters."""

    metrics: MetricsPort
    error_handler: ErrorHandlerPort
    adapter_metrics: AdapterMetricsRecorder
    request_collector: APIRequestCollector
    fallback_fetch_service: FallbackFetchOrchestrator

    def build_dependency_context(self) -> HttpAdapterDependencyContext:
        """Return explicit constructor context for HTTP adapter runtime deps."""
        return HttpAdapterDependencyContext(
            metrics=self.metrics,
            error_handler=self.error_handler,
            adapter_metrics=self.adapter_metrics,
            request_collector=self.request_collector,
        )

    def as_injection_kwargs(self) -> dict[str, object]:
        """Return kwargs payload for adapter constructor injection.

        Returns:
            Dict of kwargs for injecting adapter helpers into constructor.
        """
        return {
            "dependency_context": self.build_dependency_context(),
            "error_handler": self.error_handler,
            "adapter_metrics": self.adapter_metrics,
            "request_collector": self.request_collector,
            "fallback_fetch_service": self.fallback_fetch_service,
        }


@dataclass(frozen=True, slots=True)
class SyncAdapterHelperServices:
    """Container with helper dependencies shared by sync-backed adapters."""

    metrics: MetricsPort
    error_handler: ErrorHandlerPort
    request_collector: APIRequestCollector

    def build_dependency_context(self) -> SyncAdapterDependencyContext:
        """Return explicit constructor context for sync adapter runtime deps."""
        return SyncAdapterDependencyContext(
            metrics=self.metrics,
            error_handler=self.error_handler,
            request_collector=self.request_collector,
        )

    def as_injection_kwargs(self) -> dict[str, object]:
        """Return kwargs payload for sync adapter constructor injection."""
        return {
            "dependency_context": self.build_dependency_context(),
            "error_handler": self.error_handler,
            "request_collector": self.request_collector,
        }


class AdapterHelpersFactory:
    """Build helper service bundles for adapter constructor injection."""

    _DI_TARGET_PROVIDERS = frozenset(
        {"openalex", "crossref", "pubmed", "semanticscholar", "uniprot", "chembl"}
    )

    @classmethod
    def supports_provider(cls, provider: str) -> bool:
        """Return True if provider uses helper-service DI profile.

        Args:
            provider: Provider name to check (e.g., 'chembl', 'pubmed').

        Returns:
            True if the provider is in the DI target set, False otherwise.
        """
        return provider in cls._DI_TARGET_PROVIDERS

    @classmethod
    def create_http_helpers(
        cls,
        *,
        provider: str,
        logger: LoggerPort,
        metrics: MetricsPort | None = None,
    ) -> AdapterHelperServices:
        """Create helper services for one HTTP-backed provider adapter.

        Args:
            provider: Provider name used as label in adapter metrics.
            logger: LoggerPort for structured error and request logging.
            metrics: Optional MetricsPort; uses NoOpMetrics if None.

        Returns:
            AdapterHelperServices bundle with error handler, metrics, request
            collector, and fallback fetch service.
        """
        metrics_port = resolve_metrics_port(metrics=metrics)
        adapter_metrics = AdapterMetricsRecorder(metrics_port, provider)
        request_collector = APIRequestCollector()
        error_handler = cast(
            ErrorHandlerPort,
            ErrorService(logger=logger, metrics=metrics_port),
        )
        fallback_fetch_service = FallbackFetchOrchestrator(adapter_metrics)
        return AdapterHelperServices(
            metrics=metrics_port,
            error_handler=error_handler,
            adapter_metrics=adapter_metrics,
            request_collector=request_collector,
            fallback_fetch_service=fallback_fetch_service,
        )

    @classmethod
    def create_sync_helpers(
        cls,
        *,
        provider: str,
        logger: LoggerPort,
        metrics: MetricsPort | None = None,
    ) -> SyncAdapterHelperServices:
        """Create helper services for one sync-backed provider adapter.

        Args:
            provider: Provider name kept for a symmetric factory signature.
            logger: LoggerPort for structured error and request logging.
            metrics: Optional MetricsPort; uses NoOpMetrics if None.

        Returns:
            SyncAdapterHelperServices bundle with error handler and request
            collector for sync-backed adapters.
        """
        del provider
        metrics_port = resolve_metrics_port(metrics=metrics)
        request_collector = APIRequestCollector()
        error_handler = cast(
            ErrorHandlerPort,
            ErrorService(logger=logger, metrics=metrics_port),
        )
        return SyncAdapterHelperServices(
            metrics=metrics_port,
            error_handler=error_handler,
            request_collector=request_collector,
        )
