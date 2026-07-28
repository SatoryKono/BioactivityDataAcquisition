# pyright: reportArgumentType=false
# Boundary object/payload typing residual at this module.
"""Prometheus metrics server public facade."""

from __future__ import annotations

import time
from datetime import datetime
from typing import TYPE_CHECKING

from prometheus_client import REGISTRY, start_http_server
from prometheus_client.exposition import delete_from_gateway, push_to_gateway

from bioetl.domain.exceptions import MetricsServerError
from bioetl.infrastructure.observability._metrics_defs_core import (
    METRICS_PUBLICATION_EVENTS_TOTAL,
)
from bioetl.infrastructure.observability._metrics_gateway_publication import (
    publish_metrics_to_gateway,
    remove_metrics_from_gateway,
)
from bioetl.infrastructure.observability._metrics_server_startup import (
    start_metrics_server_runtime,
)
from bioetl.infrastructure.observability._metrics_server_state import (
    get_metrics_server_runtime_status,
    is_metrics_server_running,
    reset_server_state,
)

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort

_PUSHGATEWAY_GROUPING_LABELS = ("pipeline", "run_type")

__all__ = [
    "MetricsServerError",
    "delete_metrics_from_gateway",
    "get_metrics_server_runtime_status",
    "is_metrics_server_running",
    "push_metrics_to_gateway",
    "reset_server_state",
    "start_metrics_server",
]


def start_metrics_server(
    port: int = 8000,
    addr: str = "0.0.0.0",
    *,
    started_at: datetime | None = None,
    fail_fast: bool = False,
    retry_count: int = 3,
    retry_delay: float = 1.0,
    logger: LoggerPort | None = None,
) -> bool:
    """Start Prometheus metrics server once with retry and optional fail-fast."""
    return start_metrics_server_runtime(
        start_http_server_fn=start_http_server,
        sleep_fn=time.sleep,
        publication_metric=METRICS_PUBLICATION_EVENTS_TOTAL,
        port=port,
        addr=addr,
        started_at=started_at,
        fail_fast=fail_fast,
        retry_count=retry_count,
        retry_delay=retry_delay,
        logger=logger,
    )


def push_metrics_to_gateway(
    gateway: str | None = None,
    run_label: str = "bioetl",
    logger: LoggerPort | None = None,
    grouping_key: dict[str, str] | None = None,
    metric_names: tuple[str, ...] | None = None,
    job: str | None = None,
) -> bool:
    """Publish a bounded aggregate metrics snapshot to Prometheus Pushgateway."""
    return publish_metrics_to_gateway(
        registry=REGISTRY,
        push_gateway=push_to_gateway,
        publication_metric=METRICS_PUBLICATION_EVENTS_TOTAL,
        gateway=gateway,
        run_label=run_label,
        logger=logger,
        grouping_key=grouping_key,
        metric_names=metric_names,
        job=job,
    )


def delete_metrics_from_gateway(
    gateway: str | None = None,
    run_label: str = "bioetl",
    logger: LoggerPort | None = None,
    grouping_key: dict[str, str] | None = None,
    job: str | None = None,
) -> bool:
    """Delete a bounded aggregate metrics snapshot from Prometheus Pushgateway."""
    return remove_metrics_from_gateway(
        delete_gateway=delete_from_gateway,
        publication_metric=METRICS_PUBLICATION_EVENTS_TOTAL,
        gateway=gateway,
        run_label=run_label,
        logger=logger,
        grouping_key=grouping_key,
        job=job,
    )
