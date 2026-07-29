# Host attrs/methods are initialized by concrete classes (PD2 W1 host surface).
"""Shared PubMed adapter state annotations for split mixins."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from bioetl.domain.ports import ErrorHandlerPort, LoggerPort, MetricsPort
    from bioetl.infrastructure.adapters.base_metrics import AdapterMetricsRecorder
    from bioetl.infrastructure.adapters.common.api_request_collector import (
        APIRequestCollector,
    )
    from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient


class PubMedAdapterStateMixin:
    """Attribute contract shared by PubMed split mixins."""

    http_client: UnifiedHTTPClient = cast(Any, None)  # Any: host attr default (PD6)
    logger: LoggerPort = cast(Any, None)  # Any: host attr default (PD6)
    email: str = cast(Any, None)  # Any: host attr default (PD6)
    api_key: str | None = cast(Any, None)  # Any: host attr default (PD6)
    _logger: LoggerPort = cast(Any, None)  # Any: host attr default (PD6)
    _adapter_metrics: AdapterMetricsRecorder = cast(Any, None)  # Any: host attr default (PD6)
    _request_collector: APIRequestCollector = cast(Any, None)  # Any: host attr default (PD6)
    _error_handler: ErrorHandlerPort = cast(Any, None)  # Any: host attr default (PD6)
    provider_name: str = cast(Any, None)  # Any: host attr default (PD6)
    batch_size: int = cast(Any, None)  # Any: host attr default (PD6)
    metrics: MetricsPort | None = cast(Any, None)  # Any: host attr default (PD6)


__all__ = ["PubMedAdapterStateMixin"]
