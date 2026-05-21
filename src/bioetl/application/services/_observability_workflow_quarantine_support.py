"""Quarantine summary helpers for observability workflow dossiers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from bioetl.application.services.control_plane.run_manifest_inspection_service import (
        RunManifestInspectionResult,
    )

__all__ = [
    "enrich_quarantine_summary",
    "resolve_bronze_record_count",
    "resolve_quarantine_summary_for_run",
]


class _QuarantineStatsService(Protocol):
    async def get_filtered_stats(
        self,
        *,
        pipeline: str,
        run_id: str,
    ) -> dict[str, object]: ...


def resolve_bronze_record_count(
    run_manifest: RunManifestInspectionResult,
) -> int | None:
    bronze_records: int | None = None
    for entry in run_manifest.ledger_entries:
        metrics_snapshot = getattr(entry, "metrics_snapshot", None)
        if not isinstance(metrics_snapshot, dict):
            continue
        value = metrics_snapshot.get("records_bronze")
        if not isinstance(value, int) or value <= 0:
            continue
        bronze_records = value if bronze_records is None else max(bronze_records, value)
    return bronze_records


def enrich_quarantine_summary(
    *,
    stats: dict[str, object],
    run_id: str,
    run_manifest: RunManifestInspectionResult | None,
) -> dict[str, object]:
    summary = dict(stats)
    summary["run_scope"] = {"run_id": run_id}
    silver_stats = summary.get("silver_filter_rejects")
    if (
        run_manifest is not None
        and isinstance(silver_stats, dict)
        and isinstance(silver_stats.get("total_count"), int)
    ):
        bronze_records = resolve_bronze_record_count(run_manifest)
        if bronze_records is not None:
            silver_total = silver_stats["total_count"]
            silver_stats["bronze_records"] = bronze_records
            silver_stats["bronze_ratio"] = silver_total / bronze_records
            silver_stats["bronze_ratio_pct"] = (silver_total / bronze_records) * 100
    return summary


async def resolve_quarantine_summary_for_run(
    *,
    quarantine_service: _QuarantineStatsService | None,
    run_id: str,
    pipeline_name: str | None,
    run_manifest: RunManifestInspectionResult | None,
) -> dict[str, object] | None:
    """Resolve bounded quarantine summary for one run when available."""
    if quarantine_service is None or pipeline_name is None:
        return None
    try:
        stats = await quarantine_service.get_filtered_stats(
            pipeline=pipeline_name,
            run_id=run_id,
        )
    except (OSError, RuntimeError, TypeError, ValueError):
        return None
    return enrich_quarantine_summary(
        stats=stats,
        run_id=run_id,
        run_manifest=run_manifest,
    )
