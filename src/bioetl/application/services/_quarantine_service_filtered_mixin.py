"""Filtered/explorer methods for QuarantineService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.domain.types import JsonDict

if TYPE_CHECKING:
    from bioetl.application.services.quarantine_service import QuarantineService


class QuarantineServiceFilteredMixin:
    """Filtered-record explorer operations for QuarantineService."""

    async def list_filtered_records(
        self: QuarantineService,
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
        self.logger.info(
            "Listed filtered quarantine records",
            pipeline=pipeline,
            result_count=len(result.get("items", []))
            if isinstance(result.get("items"), list)
            else 0,
            total=result.get("total", 0),
        )
        return result

    async def get_filtered_record(
        self: QuarantineService,
        *,
        payload_hash: str,
        pipeline: str | None = None,
    ) -> JsonDict | None:
        """Get one Silver-filter record detail by payload hash."""
        self.logger.debug(
            "Getting filtered quarantine record",
            payload_hash=payload_hash,
            pipeline=pipeline,
        )
        result = await self.quarantine_port.get_filtered_record(
            payload_hash=payload_hash,
            pipeline=pipeline,
        )
        if result is None:
            self.logger.warning(
                "Filtered quarantine record not found",
                payload_hash=payload_hash,
                pipeline=pipeline,
            )
            return None
        self.logger.info(
            "Got filtered quarantine record",
            payload_hash=payload_hash,
            pipeline=result.get("pipeline", pipeline),
        )
        return result

    async def get_filtered_stats(
        self: QuarantineService,
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
        self.logger.info(
            "Got filtered quarantine stats",
            pipeline=pipeline,
            total=stats.get("total", 0),
        )
        return stats

    async def get_filtered_filter_options(
        self: QuarantineService,
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
        options = await self.quarantine_port.get_filtered_filter_options(
            pipeline=pipeline,
            run_type=run_type,
            reason_code=reason_code,
            field=field,
            run_id=run_id,
            from_ts=from_ts,
            to_ts=to_ts,
        )
        self.logger.info(
            "Got filtered quarantine filter options",
            pipeline=pipeline,
            run_type_count=len(options.get("run_types", []))
            if isinstance(options.get("run_types"), list)
            else 0,
        )
        return options
