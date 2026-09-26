"""Filtered/explorer methods for UnifiedQuarantineAdapter."""

from __future__ import annotations

import asyncio
from typing import Protocol

from bioetl.domain.types import JsonDict
from bioetl.infrastructure.quarantine.filtered_reads import (
    get_filtered_filter_options,
    get_filtered_record,
    list_filtered_records,
)
from bioetl.infrastructure.quarantine.operations import (
    get_filtered_stats,
    get_filtered_timeseries,
)


class _UnifiedQuarantineFilteredHost(Protocol):
    """Minimal host contract required by filtered quarantine helpers."""

    base_path: str


class UnifiedQuarantineFilteredMixin:
    """Filtered-record explorer operations for UnifiedQuarantineAdapter."""

    async def list_filtered_records(
        self: _UnifiedQuarantineFilteredHost,
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
        """List paginated Silver-filter quarantine rows for record-level exploration."""
        return await asyncio.to_thread(
            list_filtered_records,
            self.base_path,
            None,
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

    async def get_filtered_record(
        self: _UnifiedQuarantineFilteredHost,
        *,
        payload_hash: str,
        pipeline: str | None = None,
    ) -> JsonDict | None:
        """Return one filtered Silver record with full payload details."""
        return await asyncio.to_thread(
            get_filtered_record,
            self.base_path,
            None,
            payload_hash=payload_hash,
            pipeline=pipeline,
        )

    async def get_filtered_stats(
        self: _UnifiedQuarantineFilteredHost,
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
        """Return aggregate Silver-filter explorer stats for current scope."""
        return await asyncio.to_thread(
            get_filtered_stats,
            self.base_path,
            None,
            pipeline=pipeline,
            run_type=run_type,
            reason_code=reason_code,
            field=field,
            run_id=run_id,
            payload_hash=payload_hash,
            from_ts=from_ts,
            to_ts=to_ts,
        )

    async def get_filtered_timeseries(
        self: _UnifiedQuarantineFilteredHost,
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
        """Return time-bucketed Silver-filter explorer stats for current scope."""
        return await asyncio.to_thread(
            get_filtered_timeseries,
            self.base_path,
            None,
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

    async def get_filtered_filter_options(
        self: _UnifiedQuarantineFilteredHost,
        *,
        pipeline: str | None = None,
        run_type: str | None = None,
        reason_code: str | None = None,
        field: str | None = None,
        run_id: str | None = None,
        from_ts: str | None = None,
        to_ts: str | None = None,
    ) -> JsonDict:
        """Return dynamic filter options for record-level quarantine exploration."""
        return await asyncio.to_thread(
            get_filtered_filter_options,
            self.base_path,
            None,
            pipeline=pipeline,
            run_type=run_type,
            reason_code=reason_code,
            field=field,
            run_id=run_id,
            from_ts=from_ts,
            to_ts=to_ts,
        )
