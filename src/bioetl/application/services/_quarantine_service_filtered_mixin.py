"""Filtered/explorer methods for QuarantineService."""

from __future__ import annotations

from time import perf_counter
from typing import TYPE_CHECKING, Protocol

from bioetl.domain.types import JsonDict

if TYPE_CHECKING:
    from bioetl.application.services.control_plane.run_manifest_inspection_service import (
        RunManifestInspectionService,
    )
    from bioetl.domain.ports import LoggerPort, QuarantinePort


_QUARANTINE_OPERATOR_ERRORS = (OSError, RuntimeError, TypeError, ValueError)


class _FilteredQuarantineHost(Protocol):
    """Structural contract required by filtered quarantine explorer helpers."""

    logger: LoggerPort
    quarantine_port: QuarantinePort
    run_manifest_service: RunManifestInspectionService | None

    def _record_operator_metrics(
        self,
        *,
        operation: str,
        status: str,
        duration_seconds: float,
    ) -> None: ...


def _resolve_bronze_records_from_inspection(inspection: object) -> int | None:
    """Return one run-scoped Bronze denominator from manifest ledger entries."""
    bronze_records: int | None = None
    for entry in getattr(inspection, "ledger_entries", ()):
        metrics_snapshot = getattr(entry, "metrics_snapshot", None)
        if not isinstance(metrics_snapshot, dict):
            continue
        value = metrics_snapshot.get("records_bronze")
        if not isinstance(value, int) or value <= 0:
            continue
        bronze_records = value if bronze_records is None else max(bronze_records, value)
    return bronze_records


def _resolve_filtered_stats_run_ids(
    *,
    run_id: str | None,
    scoped_run_ids: object,
) -> list[str]:
    """Resolve unique run identifiers used to derive Bronze denominators."""
    if run_id is not None:
        return [run_id]
    del scoped_run_ids
    return []


def _sum_bronze_records_for_runs(
    *,
    run_ids: list[str],
    run_manifest_service: object,
) -> int:
    """Sum resolved Bronze record counts across the selected runs."""
    bronze_records = 0
    for candidate_run_id in sorted(set(run_ids)):
        try:
            inspection = run_manifest_service.show(candidate_run_id)
        except ValueError:
            continue
        resolved = _resolve_bronze_records_from_inspection(inspection)
        if resolved is not None:
            bronze_records += resolved
    return bronze_records


def _enrich_filtered_stats_with_bronze_denominator(
    stats: JsonDict,
    *,
    run_id: str | None,
    run_manifest_service: object,
) -> JsonDict:
    """Attach a bounded Bronze denominator when manifest evidence is available."""
    enriched = dict(stats)
    scoped_run_ids = enriched.pop("run_ids", None)
    if run_manifest_service is None:
        return enriched

    resolved_run_ids = _resolve_filtered_stats_run_ids(
        run_id=run_id,
        scoped_run_ids=scoped_run_ids,
    )
    bronze_records = _sum_bronze_records_for_runs(
        run_ids=resolved_run_ids,
        run_manifest_service=run_manifest_service,
    )
    if bronze_records <= 0:
        return enriched

    total = enriched.get("total", 0)
    enriched["bronze_records"] = bronze_records
    enriched["reject_ratio"] = (
        float(total / bronze_records) if isinstance(total, int) and total > 0 else 0.0
    )
    return enriched


def _reject_ratio(reject_count: object, bronze_records: int) -> float:
    """Calculate a bounded reject ratio for positive integer reject counts."""
    if isinstance(reject_count, int) and reject_count > 0:
        return float(reject_count / bronze_records)
    return 0.0


def _filtered_timeseries_run_ids(row: JsonDict) -> list[str]:
    """Remove and normalize run ids carried by the storage aggregation layer."""
    return [
        candidate
        for candidate in row.pop("run_ids", [])
        if isinstance(candidate, str) and candidate.strip()
    ]


def _enrich_filtered_timeseries_row(
    item: JsonDict,
    *,
    run_manifest_service: object,
) -> JsonDict:
    """Attach Bronze denominator evidence to one timeseries row when available."""
    enriched_row = dict(item)
    run_ids = _filtered_timeseries_run_ids(enriched_row)
    if run_manifest_service is None or not run_ids:
        return enriched_row

    bronze_records = _sum_bronze_records_for_runs(
        run_ids=run_ids,
        run_manifest_service=run_manifest_service,
    )
    if bronze_records <= 0:
        return enriched_row

    enriched_row["bronze_records"] = bronze_records
    enriched_row["reject_ratio"] = _reject_ratio(
        enriched_row.get("reject_count", 0),
        bronze_records,
    )
    return enriched_row


def _enrich_filtered_timeseries_with_bronze_denominators(
    payload: JsonDict,
    *,
    run_manifest_service: object,
) -> JsonDict:
    """Attach per-bucket Bronze denominators when manifest evidence is available."""
    rows = payload.get("rows")
    if not isinstance(rows, list):
        return payload

    enriched_payload = dict(payload)
    enriched_rows: list[JsonDict] = []
    for item in rows:
        if not isinstance(item, dict):
            continue
        enriched_rows.append(
            _enrich_filtered_timeseries_row(
                item,
                run_manifest_service=run_manifest_service,
            )
        )

    enriched_payload["rows"] = enriched_rows
    return enriched_payload


class QuarantineServiceFilteredMixin:
    """Filtered-record explorer operations for QuarantineService."""

    async def list_filtered_records(
        self: _FilteredQuarantineHost,
        *,
        pipeline: str | None = None,
        run_type: str | None = None,
        reason_code: str | None = None,
        field: str | None = None,
        run_id: str | None = None,
        payload_hash: str | None = None,
        from_ts: str | None = None,
        to_ts: str | None = None,
        limit: int = 50,
        offset: int = 0,
        sort: str = "ingestion_ts_desc",
    ) -> JsonDict:
        """List paginated Silver-filter records for the quarantine explorer."""
        start_time = perf_counter()
        self.logger.debug(
            "Listing filtered quarantine records",
            pipeline=pipeline,
            run_type=run_type,
            reason_code=reason_code,
            field=field,
            run_id=run_id,
            payload_hash=payload_hash,
            from_ts=from_ts,
            to_ts=to_ts,
            limit=limit,
            offset=offset,
            sort=sort,
        )
        try:
            result = await self.quarantine_port.list_filtered_records(
                pipeline=pipeline,
                run_type=run_type,
                reason_code=reason_code,
                field=field,
                run_id=run_id,
                payload_hash=payload_hash,
                from_ts=from_ts,
                to_ts=to_ts,
                limit=limit,
                offset=offset,
                sort=sort,
            )
        except _QUARANTINE_OPERATOR_ERRORS:
            self._record_operator_metrics(
                operation="filtered_list",
                status="failed",
                duration_seconds=perf_counter() - start_time,
            )
            raise
        self.logger.info(
            "Listed filtered quarantine records",
            pipeline=pipeline,
            result_count=len(result.get("items", []))
            if isinstance(result.get("items"), list)
            else 0,
            total=result.get("total", 0),
        )
        self._record_operator_metrics(
            operation="filtered_list",
            status="success",
            duration_seconds=perf_counter() - start_time,
        )
        return result

    async def get_filtered_record(
        self: _FilteredQuarantineHost,
        *,
        payload_hash: str,
        pipeline: str | None = None,
    ) -> JsonDict | None:
        """Get one Silver-filter record detail by payload hash."""
        start_time = perf_counter()
        self.logger.debug(
            "Getting filtered quarantine record",
            payload_hash=payload_hash,
            pipeline=pipeline,
        )
        try:
            result = await self.quarantine_port.get_filtered_record(
                payload_hash=payload_hash,
                pipeline=pipeline,
            )
        except _QUARANTINE_OPERATOR_ERRORS:
            self._record_operator_metrics(
                operation="filtered_get",
                status="failed",
                duration_seconds=perf_counter() - start_time,
            )
            raise
        if result is None:
            self.logger.warning(
                "Filtered quarantine record not found",
                payload_hash=payload_hash,
                pipeline=pipeline,
            )
            self._record_operator_metrics(
                operation="filtered_get",
                status="not_found",
                duration_seconds=perf_counter() - start_time,
            )
            return None
        self.logger.info(
            "Got filtered quarantine record",
            payload_hash=payload_hash,
            pipeline=result.get("pipeline", pipeline),
        )
        self._record_operator_metrics(
            operation="filtered_get",
            status="success",
            duration_seconds=perf_counter() - start_time,
        )
        return result

    async def get_filtered_stats(
        self: _FilteredQuarantineHost,
        *,
        pipeline: str | None = None,
        run_type: str | None = None,
        reason_code: str | None = None,
        field: str | None = None,
        run_id: str | None = None,
        payload_hash: str | None = None,
        from_ts: str | None = None,
        to_ts: str | None = None,
    ) -> JsonDict:
        """Get aggregate stats for filtered Silver records."""
        start_time = perf_counter()
        self.logger.debug(
            "Getting filtered quarantine stats",
            pipeline=pipeline,
            run_type=run_type,
            reason_code=reason_code,
            field=field,
            run_id=run_id,
            payload_hash=payload_hash,
            from_ts=from_ts,
            to_ts=to_ts,
        )
        try:
            stats = await self.quarantine_port.get_filtered_stats(
                pipeline=pipeline,
                run_type=run_type,
                reason_code=reason_code,
                field=field,
                run_id=run_id,
                payload_hash=payload_hash,
                from_ts=from_ts,
                to_ts=to_ts,
            )
        except _QUARANTINE_OPERATOR_ERRORS:
            self._record_operator_metrics(
                operation="filtered_stats",
                status="failed",
                duration_seconds=perf_counter() - start_time,
            )
            raise
        self.logger.info(
            "Got filtered quarantine stats",
            pipeline=pipeline,
            total=stats.get("total", 0),
        )
        stats = _enrich_filtered_stats_with_bronze_denominator(
            stats,
            run_id=run_id,
            run_manifest_service=getattr(self, "run_manifest_service", None),
        )
        self._record_operator_metrics(
            operation="filtered_stats",
            status="success",
            duration_seconds=perf_counter() - start_time,
        )
        return stats

    async def get_filtered_filter_options(
        self: _FilteredQuarantineHost,
        *,
        pipeline: str | None = None,
        run_type: str | None = None,
        reason_code: str | None = None,
        field: str | None = None,
        run_id: str | None = None,
        from_ts: str | None = None,
        to_ts: str | None = None,
    ) -> JsonDict:
        """Get scoped variable options for filtered-record exploration."""
        start_time = perf_counter()
        self.logger.debug(
            "Getting filtered quarantine filter options",
            pipeline=pipeline,
            run_type=run_type,
            reason_code=reason_code,
            field=field,
            run_id=run_id,
            from_ts=from_ts,
            to_ts=to_ts,
        )
        try:
            options = await self.quarantine_port.get_filtered_filter_options(
                pipeline=pipeline,
                run_type=run_type,
                reason_code=reason_code,
                field=field,
                run_id=run_id,
                from_ts=from_ts,
                to_ts=to_ts,
            )
        except _QUARANTINE_OPERATOR_ERRORS:
            self._record_operator_metrics(
                operation="filtered_filter_options",
                status="failed",
                duration_seconds=perf_counter() - start_time,
            )
            raise
        self.logger.info(
            "Got filtered quarantine filter options",
            pipeline=pipeline,
            run_type_count=len(options.get("run_types", []))
            if isinstance(options.get("run_types"), list)
            else 0,
        )
        self._record_operator_metrics(
            operation="filtered_filter_options",
            status="success",
            duration_seconds=perf_counter() - start_time,
        )
        return options

    async def get_filtered_timeseries(
        self: _FilteredQuarantineHost,
        *,
        pipeline: str | None = None,
        run_type: str | None = None,
        reason_code: str | None = None,
        field: str | None = None,
        run_id: str | None = None,
        payload_hash: str | None = None,
        from_ts: str | None = None,
        to_ts: str | None = None,
        bucket: str = "1h",
    ) -> JsonDict:
        """Get time-bucketed stats for filtered Silver records."""
        start_time = perf_counter()
        self.logger.debug(
            "Getting filtered quarantine timeseries",
            pipeline=pipeline,
            run_type=run_type,
            reason_code=reason_code,
            field=field,
            run_id=run_id,
            payload_hash=payload_hash,
            from_ts=from_ts,
            to_ts=to_ts,
            bucket=bucket,
        )
        try:
            payload = await self.quarantine_port.get_filtered_timeseries(
                pipeline=pipeline,
                run_type=run_type,
                reason_code=reason_code,
                field=field,
                run_id=run_id,
                payload_hash=payload_hash,
                from_ts=from_ts,
                to_ts=to_ts,
                bucket=bucket,
            )
        except _QUARANTINE_OPERATOR_ERRORS:
            self._record_operator_metrics(
                operation="filtered_timeseries",
                status="failed",
                duration_seconds=perf_counter() - start_time,
            )
            raise
        payload = _enrich_filtered_timeseries_with_bronze_denominators(
            payload,
            run_manifest_service=getattr(self, "run_manifest_service", None),
        )
        self.logger.info(
            "Got filtered quarantine timeseries",
            pipeline=pipeline,
            rows=len(payload.get("rows", []))
            if isinstance(payload.get("rows"), list)
            else 0,
            bucket=payload.get("bucket", bucket),
        )
        self._record_operator_metrics(
            operation="filtered_timeseries",
            status="success",
            duration_seconds=perf_counter() - start_time,
        )
        return payload
