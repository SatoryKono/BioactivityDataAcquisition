"""Explicit dependency bundles for adapter constructor injection."""

from __future__ import annotations

from dataclasses import dataclass

from bioetl.domain.ports import ErrorHandlerPort, MetricsPort
from bioetl.infrastructure.adapters.base_metrics import AdapterMetricsRecorder
from bioetl.infrastructure.adapters.common.api_request_collector import (
    APIRequestCollector,
)

__all__ = [
    "HttpAdapterDependencyContext",
    "SyncAdapterDependencyContext",
]


@dataclass(frozen=True, slots=True)
class HttpAdapterDependencyContext:
    """Resolved runtime collaborators for one HTTP-backed adapter."""

    metrics: MetricsPort
    error_handler: ErrorHandlerPort
    adapter_metrics: AdapterMetricsRecorder
    request_collector: APIRequestCollector


@dataclass(frozen=True, slots=True)
class SyncAdapterDependencyContext:
    """Resolved runtime collaborators for one sync-backed adapter."""

    metrics: MetricsPort
    error_handler: ErrorHandlerPort
    request_collector: APIRequestCollector
