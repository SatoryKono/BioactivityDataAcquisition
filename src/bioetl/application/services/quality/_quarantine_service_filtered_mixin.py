"""Filtered/explorer methods for QuarantineService."""

from __future__ import annotations

from time import perf_counter
from typing import TYPE_CHECKING, Protocol

from bioetl.application.services.quality._quarantine_service_async_mixin import (
    QuarantineServiceAsyncMixin,
)
from bioetl.application.services.quality._quarantine_service_filtered_helpers import (
    _QUARANTINE_OPERATOR_ERRORS,
    _enrich_filtered_stats_with_bronze_denominator,
    _enrich_filtered_timeseries_with_bronze_denominators,
)
from bioetl.application.services.quality._quarantine_service_sync_mixin import (
    QuarantineServiceSyncMixin,
)
from bioetl.domain.types import JsonDict

if TYPE_CHECKING:
    from bioetl.application.services.control_plane.manifest.inspection_service import (
        RunManifestInspectionService,
    )
    from bioetl.domain.ports import LoggerPort, QuarantinePort


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


def _list_length(payload: JsonDict, key: str) -> int:
    value = payload.get(key)
    return len(value) if isinstance(value, list) else 0


class QuarantineServiceFilteredMixin(
    QuarantineServiceAsyncMixin,
    QuarantineServiceSyncMixin,
):
    """Filtered explorer plus composed sync/async quarantine operators."""

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
            result_count=_list_length(result, "items"),
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
            pipeline=pipeline,
            run_type=run_type,
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
            run_type_count=_list_length(options, "run_types"),
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
            rows=_list_length(payload, "rows"),
            bucket=payload.get("bucket", bucket),
        )
        self._record_operator_metrics(
            operation="filtered_timeseries",
            status="success",
            duration_seconds=perf_counter() - start_time,
        )
        return payload
