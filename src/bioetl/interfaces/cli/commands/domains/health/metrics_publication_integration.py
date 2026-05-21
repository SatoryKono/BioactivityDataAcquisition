"""Metrics publication helpers for CLI command boundaries."""

from __future__ import annotations

from collections.abc import Mapping

__all__ = ["publish_metrics_safely"]


def publish_metrics_safely(
    run_label: str = "bioetl",
    *,
    pipeline_name: str | None = None,
    run_type: str | None = None,
    grouping_key_extra: Mapping[str, str] | None = None,
    metric_names: tuple[str, ...] | None = None,
) -> bool:
    """Push process-local metrics without failing the completed CLI command."""
    from bioetl.composition.execution_api import push_metrics_to_gateway

    try:
        gateway_kwargs: dict[str, object] = {
            "run_label": run_label,
            "pipeline_name": pipeline_name,
            "run_type": run_type,
            "grouping_key_extra": grouping_key_extra,
        }
        if metric_names is not None:
            gateway_kwargs["metric_names"] = metric_names
        push_metrics_to_gateway(**gateway_kwargs)
        return True
    except (
        OSError,
        ConnectionError,
        TimeoutError,
        RuntimeError,
        ValueError,
        TypeError,
    ):
        # Observability publication must never turn a completed CLI run into failure.
        return False
