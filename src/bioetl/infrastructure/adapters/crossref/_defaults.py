"""CrossRef adapter default wiring helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.infrastructure.adapters.common import (
    FallbackDecoratorConfig,
    FallbackFetchOrchestratorService,
)

if TYPE_CHECKING:
    from bioetl.domain.ports import ErrorHandlerPort, LoggerPort, MetricsPort
    from bioetl.infrastructure.adapters.base_metrics import AdapterMetrics


def create_default_crossref_error_handler(
    *,
    logger: LoggerPort,
    metrics: MetricsPort | None,
) -> ErrorHandlerPort:
    """Create default adapter error handler for non-DI call sites."""
    from bioetl.infrastructure.adapters.error_handling import ErrorService

    return ErrorService(logger, metrics=metrics)


def create_default_crossref_fallback_service(
    *,
    adapter_metrics: AdapterMetrics,
) -> FallbackFetchOrchestratorService:
    """Create fallback orchestrator service for non-DI call sites."""
    return FallbackFetchOrchestratorService(adapter_metrics)


CROSSREF_DEFAULT_FALLBACK_CONFIG = FallbackDecoratorConfig(
    supported_filter_field="doi",
    unsupported_filter_event="unsupported_filter_field_for_fallback",
    unsupported_filter_message=(
        "CrossRef fallback only supports 'doi' filtering, proceeding with DOI semantics"
    ),
    skip_on_unsupported_filter_field=False,
    primary_lookup_method="doi",
    trim_primary_ids_to_limit=True,
    fallback_operation="fetch_filtered_with_fallback",
)
