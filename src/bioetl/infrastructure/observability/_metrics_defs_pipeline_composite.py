"""Composite pipeline Prometheus metrics."""

from __future__ import annotations

from prometheus_client import Counter

__all__ = ["COMPOSITE_SOURCE_SELECTION_TOTAL"]

COMPOSITE_SOURCE_SELECTION_TOTAL = Counter(
    "bioetl_composite_source_selection_total",
    "Total low-cardinality composite source-selection decisions recorded at persistence time",
    ["pipeline", "decision_type", "selected_source"],
)
