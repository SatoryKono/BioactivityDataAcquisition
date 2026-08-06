"""Runtime bootstrap helpers for BaseHttpAdapter and dataclass adapters."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.infrastructure.adapters.common.adapter_defaults import (
    create_default_adapter_metrics,
    create_default_error_handler,
    create_default_request_collector,
)

if TYPE_CHECKING:
    from bioetl.domain.ports import ErrorHandlerPort, LoggerPort, MetricsPort
    from bioetl.infrastructure.adapters.base_metrics import AdapterMetricsRecorder
    from bioetl.infrastructure.adapters.common import HttpAdapterDependencyContext
    from bioetl.infrastructure.adapters.common.api_request_collector import (
        APIRequestCollector,
    )

__all__ = [
    "apply_dependency_context",
    "init_default_adapter_metrics",
    "init_inline_adapter_collaborators",
    "resolve_lazy_private_alias",
]


def apply_dependency_context(
    host: object,
    dependency_context: HttpAdapterDependencyContext,
) -> None:
    """Bind metrics/error/request collaborators from a composition context."""
    object.__setattr__(host, "_metrics", dependency_context.metrics)
    object.__setattr__(host, "metrics", dependency_context.metrics)
    object.__setattr__(host, "_error_handler", dependency_context.error_handler)
    object.__setattr__(host, "_adapter_metrics", dependency_context.adapter_metrics)
    object.__setattr__(host, "_request_collector", dependency_context.request_collector)


def init_inline_adapter_collaborators(
    host: object,
    *,
    logger: LoggerPort,
    metrics: MetricsPort | None,
    error_handler: ErrorHandlerPort | None,
    adapter_metrics: AdapterMetricsRecorder | None,
    request_collector: APIRequestCollector | None,
) -> bool:
    """Initialize inline collaborators when no dependency context is provided.

    Returns True when metrics/collector initialization is complete (caller can
    return), False when the host still needs ``_init_adapter_metrics()``.
    """
    object.__setattr__(host, "_metrics", metrics)
    object.__setattr__(host, "metrics", metrics)
    resolved_error_handler = (
        error_handler
        if error_handler is not None
        else create_default_error_handler(logger=logger, metrics=metrics)
    )
    object.__setattr__(host, "_error_handler", resolved_error_handler)
    if adapter_metrics is not None and request_collector is not None:
        object.__setattr__(host, "_adapter_metrics", adapter_metrics)
        object.__setattr__(host, "_request_collector", request_collector)
        return True
    return False


def init_default_adapter_metrics(
    host: object,
    *,
    metrics: MetricsPort | None,
    provider_name: str,
) -> None:
    """Create standardized adapter metrics and request collector on the host."""
    object.__setattr__(
        host,
        "_adapter_metrics",
        create_default_adapter_metrics(metrics=metrics, provider=provider_name),
    )
    object.__setattr__(host, "_request_collector", create_default_request_collector())


def resolve_lazy_private_alias(host: object, name: str) -> tuple[bool, object]:
    """Resolve private runtime aliases for dataclass-based adapters.

    Returns ``(handled, value)``. When ``handled`` is False the caller should
    raise ``AttributeError``.
    """
    host_dict = object.__getattribute__(host, "__dict__")
    if name == "_http_client":
        http_client = host_dict.get("http_client")
        if http_client is not None:
            object.__setattr__(host, "_http_client", http_client)
            return True, http_client
        return False, None
    if name == "_logger":
        logger = host_dict.get("logger")
        if logger is not None:
            object.__setattr__(host, "_logger", logger)
            return True, logger
        return False, None
    if name == "_metrics":
        metrics = host_dict.get("metrics")
        object.__setattr__(host, "_metrics", metrics)
        return True, metrics
    return False, None
