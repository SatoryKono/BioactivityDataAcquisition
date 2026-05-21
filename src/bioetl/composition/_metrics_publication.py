"""Leaf composition seam for metrics publication helpers."""

from __future__ import annotations

from collections.abc import Mapping
from uuid import uuid4

from bioetl.composition.bootstrap.cli.metrics import bootstrap_metrics_service
from bioetl.composition.bootstrap.runtime.observability import (
    bootstrap_logger,
)
from bioetl.infrastructure.config import get_settings

_PUSHGATEWAY_FALLBACK = "localhost:9091"

__all__ = ["push_metrics_to_gateway"]


def push_metrics_to_gateway(
    run_label: str = "bioetl",
    *,
    pipeline_name: str | None = None,
    run_type: str | None = None,
    grouping_key_extra: Mapping[str, str] | None = None,
    metric_names: tuple[str, ...] | None = None,
) -> bool:
    """Push current metrics to Prometheus Pushgateway via a leaf bootstrap seam."""
    settings = get_settings()
    gateway = getattr(settings, "pushgateway_url", None) or _PUSHGATEWAY_FALLBACK
    grouping_key: dict[str, str] = {}
    if pipeline_name:
        grouping_key["pipeline"] = pipeline_name
    if run_type:
        grouping_key["run_type"] = run_type
    if grouping_key_extra:
        grouping_key.update(grouping_key_extra)

    metrics_service = bootstrap_metrics_service()
    metrics_service.logger = bootstrap_logger(
        pipeline=pipeline_name or "metrics_publication",
        run_id=uuid4(),
        log_level="INFO",
    )
    result = metrics_service.push_to_gateway(
        gateway=gateway,
        run_label=run_label,
        grouping_key=grouping_key,
        metric_names=metric_names,
    )
    return bool(result.success)
