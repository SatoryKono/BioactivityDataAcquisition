"""Run-scoped quarantine statistics enrichment helpers."""

from __future__ import annotations

from typing import Protocol

from bioetl.domain.types import JsonDict

__all__ = [
    "RunManifestInspectionServiceProtocol",
    "enrich_run_scoped_stats",
]


class RunManifestInspectionResultProtocol(Protocol):
    """Protocol for manifest inspection payloads used in CLI enrichment."""

    @property
    def ledger_entries(self) -> tuple[object, ...]:
        """Return the associated ledger entries."""
        ...


class RunManifestInspectionServiceProtocol(Protocol):
    """Protocol for control-plane manifest lookup used by quarantine CLI."""

    def show(self, identifier: str) -> RunManifestInspectionResultProtocol:
        """Resolve one manifest or run identifier."""
        ...


def _resolve_run_scoped_bronze_records(
    run_manifest_service: RunManifestInspectionServiceProtocol | None,
    *,
    run_id: str | None,
) -> int | None:
    """Resolve a Bronze denominator for one run from control-plane ledger data."""
    if run_manifest_service is None or run_id is None:
        return None
    try:
        inspection = run_manifest_service.show(run_id)
    except ValueError:
        return None

    bronze_records: int | None = None
    for entry in inspection.ledger_entries:
        metrics_snapshot = getattr(entry, "metrics_snapshot", None)
        if not isinstance(metrics_snapshot, dict):
            continue
        value = metrics_snapshot.get("records_bronze")
        if not isinstance(value, int) or value <= 0:
            continue
        bronze_records = value if bronze_records is None else max(bronze_records, value)
    return bronze_records


def enrich_run_scoped_stats(
    stats: JsonDict,
    *,
    run_id: str | None,
    run_manifest_service: RunManifestInspectionServiceProtocol | None,
) -> JsonDict:
    """Add run-scoped metadata and optional Bronze denominator to stats."""
    if run_id is None:
        return stats

    stats["run_scope"] = {"run_id": run_id}
    silver = stats.get("silver_filter_rejects")
    if not isinstance(silver, dict):
        return stats

    bronze_records = _resolve_run_scoped_bronze_records(
        run_manifest_service,
        run_id=run_id,
    )
    if bronze_records is None:
        return stats

    silver_total = silver.get("total_count")
    if not isinstance(silver_total, int):
        return stats

    silver["bronze_records"] = bronze_records
    if bronze_records > 0:
        silver["bronze_ratio"] = silver_total / bronze_records
        silver["bronze_ratio_pct"] = (silver_total / bronze_records) * 100
    return stats
