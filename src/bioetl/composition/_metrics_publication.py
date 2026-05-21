"""Compatibility wrapper for metrics publication helpers."""

from __future__ import annotations

from collections.abc import Mapping

from bioetl.composition.observability_api import (
    push_metrics_to_gateway as _push_metrics_to_gateway,
)

__all__ = ["push_metrics_to_gateway"]


def push_metrics_to_gateway(
    run_label: str = "bioetl",
    *,
    pipeline_name: str | None = None,
    run_type: str | None = None,
    grouping_key_extra: Mapping[str, str] | None = None,
    metric_names: tuple[str, ...] | None = None,
) -> bool:
    """Push metrics through the canonical observability composition API."""
    return _push_metrics_to_gateway(
        run_label=run_label,
        pipeline_name=pipeline_name,
        run_type=run_type,
        grouping_key_extra=grouping_key_extra,
        metric_names=metric_names,
    )
