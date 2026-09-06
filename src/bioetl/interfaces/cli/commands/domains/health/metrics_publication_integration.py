"""Metrics publication helpers for CLI command boundaries."""

from __future__ import annotations

import json
from collections.abc import Mapping

import click

__all__ = ["publish_metrics_safely"]


def publish_metrics_safely(
    run_label: str = "bioetl",
    *,
    pipeline_name: str | None = None,
    run_type: str | None = None,
    grouping_key_extra: Mapping[str, str] | None = None,
    metric_names: tuple[str, ...] | None = None,
    workflow_name: str | None = None,
    pipeline_names: tuple[str, ...] = (),
) -> bool:
    """Push process-local metrics without failing the completed CLI command."""
    try:
        from bioetl.composition.observability_runtime import push_metrics_to_gateway

        return bool(
            push_metrics_to_gateway(
                run_label=run_label,
                pipeline_name=pipeline_name,
                run_type=run_type,
                grouping_key_extra=grouping_key_extra,
                metric_names=metric_names,
                workflow_name=workflow_name,
                pipeline_names=pipeline_names,
            )
        )
    except (
        ImportError,
        OSError,
        ConnectionError,
        TimeoutError,
        RuntimeError,
        ValueError,
        TypeError,
        AttributeError,
    ) as exc:
        click.echo(
            json.dumps(
                {
                    "event": "push_failed",
                    "pipeline": pipeline_name,
                    "pipeline_names": pipeline_names,
                    "run_type": run_type,
                    "workflow_name": workflow_name,
                    "gateway_class": "unavailable",
                    "error_type": type(exc).__name__,
                },
                sort_keys=True,
            ),
            err=True,
        )
        # Observability publication must never turn a completed CLI run into failure.
        # AttributeError included so incomplete metric surfaces cannot skip the
        # best-effort path's safety net (#6728).
        return False
