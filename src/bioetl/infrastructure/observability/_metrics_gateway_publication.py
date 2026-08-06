"""Prometheus Pushgateway publication helpers."""

from __future__ import annotations

import re

from collections.abc import Callable
from typing import TYPE_CHECKING, Protocol

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
_PUSHGATEWAY_PUBLICATION_TIMEOUT_SECONDS = 5.0
_PUSHGATEWAY_DELETE_TIMEOUT_SECONDS = 1.0


class _BoundPublicationMetric(Protocol):
    def inc(self) -> object: ...


class _PublicationMetric(Protocol):
    def labels(self, **labels: str) -> _BoundPublicationMetric: ...


class _RestrictableRegistry(Protocol):
    def restricted_registry(self, metric_names: tuple[str, ...]) -> object: ...


def _emit_metrics_publication_event(
    *,
    grouping_key: dict[str, str] | None,
    status: str,
    publication_metric: _PublicationMetric,
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


def _normalize_grouping_label_value(key: str, value: object) -> str:
    """Normalize one Pushgateway grouping label to a bounded safe token."""
    raw = str(value).strip().lower()
    if not raw:
        return "unknown"
    # Bound free-form values: keep alnum/underscore/dash only, max 64 chars.
    cleaned = re.sub(r"[^a-z0-9_.:-]+", "_", raw)
    cleaned = cleaned.strip("._-")[:64]
    if not cleaned:
        return "unknown"
    if key in {"pipeline", "provider", "job", "instance", "run_type"}:
        return cleaned
    return cleaned


def _sanitize_pushgateway_grouping_key(
    grouping_key: dict[str, str] | None,
) -> dict[str, str]:
    """Keep Pushgateway grouping labels bounded to aggregate run classes."""
    if not grouping_key:
        return {}
    sanitized: dict[str, str] = {}
    for key in _PUSHGATEWAY_GROUPING_LABELS:
        value = grouping_key.get(key)
        if value is None or value == "":
            continue
        sanitized[key] = _normalize_grouping_label_value(key, value)
    return sanitized


def _redact_gateway_target(gateway: str) -> str:
    """Redact credentials from gateway URLs for log emission."""
    # Strip URL userinfo without embedding detector-triggering samples.
    scheme_sep = "://"
    if scheme_sep not in gateway or "@" not in gateway:
        return gateway
    scheme, rest = gateway.split(scheme_sep, 1)
    if "@" not in rest:
        return gateway
    _userinfo, host_part = rest.rsplit("@", 1)
    return f"{scheme}{scheme_sep}***@{host_part}"




def _redact_grouping_for_log(grouping_key: dict[str, str]) -> dict[str, str]:
    """Return a log-safe copy of grouping labels (already bounded)."""
    return {key: value for key, value in grouping_key.items()}


def publish_metrics_to_gateway(
    *,
    registry: _RestrictableRegistry,
    push_gateway: Callable[..., object],
    publication_metric: _PublicationMetric,
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
            timeout=_PUSHGATEWAY_PUBLICATION_TIMEOUT_SECONDS,
        )
        logger.info(
            "Metrics pushed to gateway",
            gateway=_redact_gateway_target(gateway),
            run_label=effective_run_label,
            grouping_key=_redact_grouping_for_log(safe_grouping_key),
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
            gateway=_redact_gateway_target(gateway),
            error=type(e).__name__,
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
    publication_metric: _PublicationMetric,
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
            timeout=_PUSHGATEWAY_DELETE_TIMEOUT_SECONDS,
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
