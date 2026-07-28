# pyright: reportUninitializedInstanceVariable=false
# Host attrs/methods are initialized by concrete classes (PD2 W1 host surface).
"""Shared PubMed adapter state annotations for split mixins."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.domain.ports import ErrorHandlerPort, LoggerPort, MetricsPort
    from bioetl.infrastructure.adapters.base_metrics import AdapterMetricsRecorder
    from bioetl.infrastructure.adapters.common.api_request_collector import (
        APIRequestCollector,
    )
    from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient


class PubMedAdapterStateMixin:
    """Attribute contract shared by PubMed split mixins."""

    http_client: UnifiedHTTPClient
    logger: LoggerPort
    email: str
    api_key: str | None
    _logger: LoggerPort
    _adapter_metrics: AdapterMetricsRecorder
    _request_collector: APIRequestCollector
    _error_handler: ErrorHandlerPort
    provider_name: str
    batch_size: int
    metrics: MetricsPort | None


__all__ = ["PubMedAdapterStateMixin"]
