"""Factory for adapter helper services assembled at composition root."""

from __future__ import annotations

from dataclasses import dataclass

from bioetl.domain.ports import ErrorHandlerPort, LoggerPort, MetricsPort, NoOpMetrics
from bioetl.infrastructure.adapters.base_metrics import AdapterMetricsRecorder
from bioetl.infrastructure.adapters.common import FallbackFetchOrchestratorService
from bioetl.infrastructure.adapters.common.api_request_collector import (
    APIRequestCollector,
)
from bioetl.infrastructure.adapters.error_handling import ErrorService

__all__ = [
    "AdapterHelperServices",
    "AdapterHelpersFactory",
]


@dataclass(frozen=True, slots=True)
class AdapterHelperServices:
    """Container with helper dependencies shared by HTTP adapters."""

    error_handler: ErrorHandlerPort
    adapter_metrics: AdapterMetricsRecorder
    request_collector: APIRequestCollector
    fallback_fetch_service: FallbackFetchOrchestratorService

    def as_injection_kwargs(self) -> dict[str, object]:
        """Return kwargs payload for adapter constructor injection.

        Returns:
            Dict of kwargs for injecting adapter helpers into constructor.
        """
        return {
            "error_handler": self.error_handler,
            "adapter_metrics": self.adapter_metrics,
            "request_collector": self.request_collector,
            "fallback_fetch_service": self.fallback_fetch_service,
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
        metrics_port = metrics if metrics is not None else NoOpMetrics()
        adapter_metrics = AdapterMetricsRecorder(metrics_port, provider)
        request_collector = APIRequestCollector()
        error_handler = ErrorService(logger=logger, metrics=metrics_port)
        fallback_fetch_service = FallbackFetchOrchestratorService(adapter_metrics)
        return AdapterHelperServices(
            error_handler=error_handler,
            adapter_metrics=adapter_metrics,
            request_collector=request_collector,
            fallback_fetch_service=fallback_fetch_service,
        )
