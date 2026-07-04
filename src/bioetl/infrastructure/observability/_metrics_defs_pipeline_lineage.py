"""Lineage Prometheus metrics."""

from __future__ import annotations

from prometheus_client import Counter

__all__ = [
    "LINEAGE_FRAGMENTS_EMITTED_TOTAL",
    "LINEAGE_REFS_MISSING_TOTAL",
    "TRACED_RUNS_TOTAL",
]

TRACED_RUNS_TOTAL = Counter(
    "bioetl_traced_runs_total",
    "Total pipeline runs that started with real tracing enabled",
    ["pipeline", "run_type"],
)

LINEAGE_FRAGMENTS_EMITTED_TOTAL = Counter(
    "bioetl_lineage_fragments_emitted_total",
    "Total lineage fragment persistence attempts by pipeline and layer",
    ["pipeline", "layer", "status"],
)

LINEAGE_REFS_MISSING_TOTAL = Counter(
    "bioetl_lineage_refs_missing_total",
    "Total writes that detected missing upstream lineage references",
    ["pipeline", "layer", "ref_type"],
)
