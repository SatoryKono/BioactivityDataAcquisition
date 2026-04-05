"""Shared helpers for quarantine CLI commands."""

from __future__ import annotations

import json
import sys
from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from typing import Protocol, TypeVar

import click

from bioetl.domain.types import JsonDict, QuarantineRecordStatus
from bioetl.interfaces.cli.commands.domains.quarantine.execution import (
    QuarantineExecutionPolicy,
    run_quarantine_async,
    run_quarantine_sync,
)
from bioetl.interfaces.cli.commands.domains.quarantine.rendering import (
    build_purge_preview_lines,
    build_quarantine_grouped_lines,
    build_replay_preview_lines,
)
from bioetl.interfaces.cli.exit_codes import ExitCode
from bioetl.interfaces.cli.formatters import (
    echo_error,
    echo_info,
    echo_quarantine_record,
)

_T = TypeVar("_T")

__all__ = [
    "_inspect_quarantine",
    "_purge_quarantine",
    "_replay_quarantine",
    "_resolve_quarantine_record",
    "_show_quarantine_stats",
]


class _QuarantineManager(Protocol):
    """Protocol for quarantine manager methods used by CLI."""

    async def inspect(
        self,
        limit: int,
        error_code: str | None = None,
        run_id: str | None = None,
    ) -> list[JsonDict]:
        """Return quarantined records."""
        ...

    async def get_stats(
        self,
        error_code: str | None = None,
        run_id: str | None = None,
    ) -> JsonDict:
        """Return aggregate quarantine statistics."""
        ...


class _RunManifestInspectionResult(Protocol):
    """Protocol for manifest inspection payloads used in CLI enrichment."""

    @property
    def ledger_entries(self) -> tuple[object, ...]:
        """Return the associated ledger entries."""
        ...


class _RunManifestInspectionService(Protocol):
    """Protocol for control-plane manifest lookup used by quarantine CLI."""

    def show(self, identifier: str) -> _RunManifestInspectionResult:
        """Resolve one manifest or run identifier."""
        ...


class _QuarantineService(Protocol):
    """Protocol for quarantine service methods used by CLI."""

    def replay(
        self,
        *,
        pipeline: str,
        error_code: str | None,
        max_age_days: int,
    ) -> list[JsonDict]:
        """Find records eligible for replay."""
        ...

    def mark_as_reprocessed(self, records: list[JsonDict]) -> int:
        """Mark replay candidates as reprocessed."""
        ...

    async def get_stats(self, pipeline: str) -> JsonDict:
        """Return stats for purge preview."""
        ...

    def purge(self, *, pipeline: str, older_than_days: int) -> int:
        """Purge old quarantine records."""
        ...

    def update_status(self, payload_hash: str, status: QuarantineRecordStatus) -> bool:
        """Update one quarantine record status."""
        ...


@dataclass(frozen=True, slots=True)
class _QuarantineCommandContext:
    """Shared execution context for one quarantine CLI command."""

    pipeline: str

    def run_async(
        self,
        coro: Coroutine[object, object, _T],
        *,
        reason_prefix: str,
        domain_error_title: str,
        unexpected_error_title: str,
    ) -> _T | None:
        """Run one async quarantine operation with a consistent policy."""
        return run_quarantine_async(
            coro,
            policy=self._build_policy(
                reason_prefix=reason_prefix,
                domain_error_title=domain_error_title,
                unexpected_error_title=unexpected_error_title,
            ),
        )

    def run_sync(
        self,
        fn: Callable[[], _T],
        *,
        reason_prefix: str,
        domain_error_title: str,
        unexpected_error_title: str,
    ) -> _T | None:
        """Run one sync quarantine operation with a consistent policy."""
        return run_quarantine_sync(
            fn,
            policy=self._build_policy(
                reason_prefix=reason_prefix,
                domain_error_title=domain_error_title,
                unexpected_error_title=unexpected_error_title,
            ),
        )

    def _build_policy(
        self,
        *,
        reason_prefix: str,
        domain_error_title: str,
        unexpected_error_title: str,
    ) -> QuarantineExecutionPolicy:
        """Build the shared execution policy for one operation."""
        return QuarantineExecutionPolicy(
            pipeline=self.pipeline,
            reason_prefix=reason_prefix,
            domain_error_title=domain_error_title,
            unexpected_error_title=unexpected_error_title,
        )


def _render_stats_dashboard(
    stats: JsonDict,
    *,
    pipeline: str,
    top: int,
    group_by: str | None,
) -> None:
    """Render human-readable quarantine statistics."""
    for line in build_quarantine_grouped_lines(
        stats,
        pipeline=pipeline,
        top=top,
        group_by=group_by,
    ):
        click.echo(line)


def _resolve_run_scoped_bronze_records(
    run_manifest_service: _RunManifestInspectionService | None,
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


def _enrich_run_scoped_stats(
    stats: JsonDict,
    *,
    run_id: str | None,
    run_manifest_service: _RunManifestInspectionService | None,
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


def _inspect_quarantine(
    manager: _QuarantineManager,
    *,
    pipeline: str,
    limit: int,
    error_code: str | None,
    run_id: str | None = None,
) -> None:
    """Inspect quarantined records for one pipeline."""
    echo_info(f"Inspecting quarantine for {pipeline} (limit {limit})...")
    context = _QuarantineCommandContext(pipeline=pipeline)

    async def _inspect() -> list[JsonDict]:
        inspect_kwargs: dict[str, object] = {
            "limit": limit,
            "error_code": error_code,
        }
        if run_id is not None:
            inspect_kwargs["run_id"] = run_id
        return await manager.inspect(**inspect_kwargs)

    records = context.run_async(
        _inspect(),
        reason_prefix="CLI_QUARANTINE_INSPECT",
        domain_error_title="Failed to inspect quarantine with domain error",
        unexpected_error_title="Unexpected error during quarantine inspect",
    )
    if records is None:
        return
    if not records:
        echo_info("No records found.")
        return
    for record in records:
        echo_quarantine_record(record)


def _show_quarantine_stats(
    manager: _QuarantineManager,
    *,
    pipeline: str,
    output_json: bool,
    error_code: str | None,
    top: int = 10,
    group_by: str | None = None,
    run_id: str | None = None,
    run_manifest_service: _RunManifestInspectionService | None = None,
) -> None:
    """Display quarantine statistics for one pipeline."""
    context = _QuarantineCommandContext(pipeline=pipeline)

    async def _stats() -> JsonDict:
        return await manager.get_stats(error_code=error_code, run_id=run_id)

    stats = context.run_async(
        _stats(),
        reason_prefix="CLI_QUARANTINE_STATS",
        domain_error_title="Failed to get stats",
        unexpected_error_title="Failed to get stats",
    )
    if stats is None:
        return
    stats = _enrich_run_scoped_stats(
        stats,
        run_id=run_id,
        run_manifest_service=run_manifest_service,
    )
    if output_json:
        click.echo(json.dumps(stats, indent=2))
        return
    _render_stats_dashboard(stats, pipeline=pipeline, top=top, group_by=group_by)


def _replay_quarantine(
    service: _QuarantineService,
    *,
    pipeline: str,
    error_code: str | None,
    max_age_days: int,
    dry_run: bool,
) -> None:
    """Replay or preview replay for quarantine records."""
    context = _QuarantineCommandContext(pipeline=pipeline)
    records = context.run_sync(
        lambda: service.replay(
            pipeline=pipeline,
            error_code=error_code,
            max_age_days=max_age_days,
        ),
        reason_prefix="CLI_QUARANTINE_REPLAY",
        domain_error_title="Failed to replay quarantine records with domain error",
        unexpected_error_title="Unexpected error during quarantine replay",
    )
    if records is None:
        return
    if not records:
        echo_info("No records found for replay.")
        return
    if dry_run:
        for line in build_replay_preview_lines(records):
            click.echo(line)
        return

    click.echo(f"\nReplaying {len(records)} record(s)...")
    marked_count = context.run_sync(
        lambda: service.mark_as_reprocessed(records),
        reason_prefix="CLI_QUARANTINE_REPLAY_MARK",
        domain_error_title="Failed to mark replayed records with domain error",
        unexpected_error_title="Unexpected error during quarantine replay mark",
    )
    if marked_count is None:
        return
    click.echo(f"Marked {marked_count} record(s) as REPROCESSED.")
    echo_info("Records are ready for reprocessing by the pipeline.")


def _purge_quarantine(
    service: _QuarantineService,
    *,
    pipeline: str,
    older_than_days: int,
    dry_run: bool,
    force: bool,
) -> None:
    """Purge old quarantine records or preview the purge."""
    context = _QuarantineCommandContext(pipeline=pipeline)
    if dry_run:

        async def _get_stats() -> JsonDict:
            return await service.get_stats(pipeline)

        stats = context.run_async(
            _get_stats(),
            reason_prefix="CLI_QUARANTINE_PURGE_PREVIEW",
            domain_error_title="Failed to preview quarantine purge with domain error",
            unexpected_error_title="Unexpected error during quarantine purge preview",
        )
        if stats is None:
            return
        total = stats.get("total_count", 0)
        for line in build_purge_preview_lines(
            older_than_days=older_than_days,
            total_count=total,
        ):
            click.echo(line)
        return

    if not force:
        click.confirm(
            f"Delete quarantine records older than {older_than_days} days for {pipeline}?",
            abort=True,
        )

    count = context.run_sync(
        lambda: service.purge(
            pipeline=pipeline,
            older_than_days=older_than_days,
        ),
        reason_prefix="CLI_QUARANTINE_PURGE",
        domain_error_title="Failed to purge quarantine records with domain error",
        unexpected_error_title="Unexpected error during quarantine purge",
    )
    if count is None:
        return
    click.echo(f"Purged {count} record(s) from quarantine.")


def _resolve_quarantine_record(
    service: _QuarantineService,
    *,
    pipeline: str,
    payload_hash: str,
    status: str,
) -> None:
    """Resolve one quarantine record by payload hash."""
    context = _QuarantineCommandContext(pipeline=pipeline)
    success = context.run_sync(
        lambda: service.update_status(
            payload_hash,
            QuarantineRecordStatus[status],
        ),
        reason_prefix="CLI_QUARANTINE_RESOLVE",
        domain_error_title="Failed to resolve quarantine record with domain error",
        unexpected_error_title="Unexpected error during quarantine resolve",
    )
    if success is None:
        return
    if success:
        click.echo(f"Record {payload_hash} marked as {status}.")
        return
    echo_error(f"Record not found: {payload_hash}")
    sys.exit(ExitCode.FAIL)
