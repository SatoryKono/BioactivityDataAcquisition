# Host attrs/methods provided by concrete composition.
"""Metric label helpers for Gold writer support."""

from __future__ import annotations

from typing import Any, cast

from bioetl.domain.observability_contract import normalize_observability_pipeline_label

__all__ = [
    "_gold_validation_error_type_label",
    "_gold_validation_metric_labels",
    "_gold_write_metric_labels",
    "_normalize_gold_metric_mode",
    "_normalize_gold_metric_status",
    "_split_gold_table_label",
]


_KNOWN_GOLD_WRITE_MODES = frozenset({"append", "merge", "overwrite", "scd2"})
_KNOWN_GOLD_WRITE_STATUSES = frozenset({"success", "failure", "validation_failure"})


def _normalize_gold_metric_mode(mode: str) -> str:
    normalized = mode.strip().lower()
    return normalized if normalized in _KNOWN_GOLD_WRITE_MODES else "other"


def _normalize_gold_metric_status(status: str) -> str:
    return status if status in _KNOWN_GOLD_WRITE_STATUSES else "failure"


def _split_gold_table_label(table_name: str) -> tuple[str, str]:
    normalized = table_name.replace("\\", "/").strip("/")
    if not normalized:
        return "unknown", "unknown"
    parts = [part for part in normalized.split("/") if part]
    if not parts:
        return "unknown", "unknown"
    if len(parts) >= 2:
        pipeline, table = parts[0], parts[-1]
    elif "." in parts[0]:
        pipeline, table = parts[0].split(".", maxsplit=1)
    else:
        pipeline = table = parts[0]
    return (
        normalize_observability_pipeline_label(pipeline),
        normalize_observability_pipeline_label(table),
    )


def _gold_write_metric_labels(
    request: object,
    *,
    status: str | None = None,
) -> dict[str, str]:
    pipeline, table = _split_gold_table_label(
        cast(
            Any, request
        ).table_name  # Any: gold write request duck-type  # type: ignore[attr-defined]
    )
    labels = {
        "pipeline": pipeline,
        "table": table,
        "mode": _normalize_gold_metric_mode(
            cast(
                Any, request
            ).mode  # Any: gold write request duck-type  # type: ignore[attr-defined]
        ),
    }
    if status is not None:
        labels["status"] = _normalize_gold_metric_status(status)
    return labels


def _gold_validation_error_type_label(error: Exception) -> str:
    if isinstance(error, ValueError):
        return "ValueError"
    return type(error).__name__


def _gold_validation_metric_labels(
    request: object,
    error: Exception,
) -> dict[str, str]:
    return {
        **_gold_write_metric_labels(request),
        "error_type": _gold_validation_error_type_label(error),
    }
