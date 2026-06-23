"""Prometheus Pushgateway publication helpers."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from bioetl.infrastructure.observability.noop_logger import NoOpLogger

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort

__all__ = [
    "_PUSHGATEWAY_GROUPING_LABELS",
    "_emit_metrics_publication_event",
    "_sanitize_pushgateway_grouping_key",
    "publish_metrics_to_gateway",
    "remove_metrics_from_gateway",
]

_PUSHGATEWAY_GROUPING_LABELS = ("pipeline", "run_type")


def _emit_metrics_publication_event(
    *,
    grouping_key: dict[str, str] | None,
    status: str,
    publication_metric: object,
    target: str = "pushgateway",
) -> None:
    """Emit best-effort publication outcomes through the shared registry."""
    labels = grouping_key or {}
    publication_metric.labels(
        pipeline=labels.get("pipeline", "unknown"),
        run_type=labels.get("run_type", "unknown"),
        target=target,
        status=status,
    ).inc()


def _sanitize_pushgateway_grouping_key(
    grouping_key: dict[str, str] | None,
) -> dict[str, str]:
    """Keep Pushgateway grouping labels bounded to aggregate run classes."""
    if not grouping_key:
        return {}
    return {
        key: str(value)
        for key in _PUSHGATEWAY_GROUPING_LABELS
        if (value := grouping_key.get(key))
    }


def publish_metrics_to_gateway(
    *,
    registry: object,
    push_gateway: Callable[..., object],
    publication_metric: object,
    gateway: str | None = None,
    run_label: str = "bioetl",
    logger: LoggerPort | None = None,
    grouping_key: dict[str, str] | None = None,
    metric_names: tuple[str, ...] | None = None,
    job: str | None = None,
) -> bool:
    """Publish a bounded aggregate metrics snapshot to Prometheus Pushgateway."""
    if logger is None:
        logger = NoOpLogger()

    gateway = gateway or "localhost:9091"
    effective_run_label = job if job is not None else run_label
    safe_grouping_key = _sanitize_pushgateway_grouping_key(grouping_key)
    selected_registry = (
        registry.restricted_registry(metric_names)
        if metric_names is not None
        else registry
    )

    try:
        push_gateway(
            gateway,
            job=effective_run_label,
            registry=selected_registry,
            grouping_key=safe_grouping_key,
            timeout=1.0,
        )
        logger.info(
            "Metrics pushed to gateway",
            gateway=gateway,
            run_label=effective_run_label,
            grouping_key=safe_grouping_key,
        )
        _emit_metrics_publication_event(
            grouping_key=safe_grouping_key,
            status="success",
            publication_metric=publication_metric,
        )
        return True
    except (
        OSError,
        ConnectionError,
        TimeoutError,
        RuntimeError,
        ValueError,
        TypeError,
    ) as e:
        logger.warning(
            "Failed to push metrics to gateway",
            gateway=gateway,
            error=str(e),
        )
        _emit_metrics_publication_event(
            grouping_key=safe_grouping_key,
            status="failed",
            publication_metric=publication_metric,
        )
        return False


def remove_metrics_from_gateway(
    *,
    delete_gateway: Callable[..., object],
    publication_metric: object,
    gateway: str | None = None,
    run_label: str = "bioetl",
    logger: LoggerPort | None = None,
    grouping_key: dict[str, str] | None = None,
    job: str | None = None,
) -> bool:
    """Delete a bounded aggregate metrics snapshot from Prometheus Pushgateway."""
    if logger is None:
        logger = NoOpLogger()

    gateway = gateway or "localhost:9091"
    effective_run_label = job if job is not None else run_label
    safe_grouping_key = _sanitize_pushgateway_grouping_key(grouping_key)

    try:
        delete_gateway(
            gateway,
            job=effective_run_label,
            grouping_key=safe_grouping_key,
            timeout=1.0,
        )
        logger.info(
            "Metrics deleted from gateway",
            gateway=gateway,
            run_label=effective_run_label,
            grouping_key=safe_grouping_key,
        )
        _emit_metrics_publication_event(
            grouping_key=safe_grouping_key,
            status="success",
            publication_metric=publication_metric,
        )
        return True
    except (
        OSError,
        ConnectionError,
        TimeoutError,
        RuntimeError,
        ValueError,
        TypeError,
    ) as e:
        logger.warning(
            "Failed to delete metrics from gateway",
            gateway=gateway,
            error=str(e),
        )
        _emit_metrics_publication_event(
            grouping_key=safe_grouping_key,
            status="failed",
            publication_metric=publication_metric,
        )
        return False
