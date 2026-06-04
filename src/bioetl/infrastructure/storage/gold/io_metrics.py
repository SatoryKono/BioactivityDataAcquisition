"""Metric label helpers for Gold merged writes."""

from __future__ import annotations

from bioetl.domain.medallion import GoldWriteMode
from bioetl.domain.observability_contract import normalize_observability_pipeline_label

__all__ = [
    "_gold_merged_metric_labels",
    "_gold_merged_validation_metric_labels",
    "_normalize_gold_merged_metric_status",
    "_split_gold_merged_table_label",
]


_KNOWN_GOLD_MERGED_METRIC_STATUSES = frozenset(
    {"success", "failure", "validation_failure"}
)


def _normalize_gold_merged_metric_status(status: str) -> str:
    return status if status in _KNOWN_GOLD_MERGED_METRIC_STATUSES else "failure"


def _split_gold_merged_table_label(table_name: str) -> tuple[str, str]:
    normalized = table_name.replace("\\", "/").strip("/")
    if not normalized:
        return "unknown", "unknown"
    parts = tuple(part for part in normalized.split("/") if part)
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


def _gold_merged_metric_labels(
    table_name: str,
    *,
    status: str | None = None,
) -> dict[str, str]:
    pipeline, table = _split_gold_merged_table_label(table_name)
    labels = {
        "pipeline": pipeline,
        "table": table,
        "mode": GoldWriteMode.OVERWRITE.value,
    }
    if status is not None:
        labels["status"] = _normalize_gold_merged_metric_status(status)
    return labels


def _gold_merged_validation_metric_labels(
    table_name: str,
    error: Exception,
) -> dict[str, str]:
    return {
        **_gold_merged_metric_labels(table_name),
        "error_type": type(error).__name__,
    }
