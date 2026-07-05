"""Shared helpers for quarantine CLI commands."""

from __future__ import annotations

import json
import sys
from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from typing import Protocol, TypeVar

import click

from bioetl.domain.types import JsonDict, QuarantineRecordStatus
from bioetl.interfaces.cli.commands.domains.quarantine._run_scope_stats import (
    RunManifestInspectionServiceProtocol,
    enrich_run_scoped_stats,
)
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
    "RunManifestInspectionServiceProtocol",
    "_inspect_quarantine",
    "_purge_quarantine",
    "_replay_quarantine",
    "_resolve_quarantine_record",
    "_resolve_silver_filter_error_code",
    "_show_quarantine_stats",
    "_show_quarantine_stats_for_cli_options",
    "_show_quarantine_stats_for_pipeline_cli_options",
]


class _QuarantineRuntimeService(Protocol):
    async def inspect(
        self,
        limit: int,
        error_code: str | None = None,
        run_id: str | None = None,
    ) -> list[JsonDict]: ...

    async def get_stats(
        self,
        error_code: str | None = None,
        run_id: str | None = None,
    ) -> JsonDict: ...


class _QuarantineService(Protocol):
    def replay(
        self,
        *,
        pipeline: str,
        error_code: str | None,
        max_age_days: int,
    ) -> list[JsonDict]: ...

    def mark_as_reprocessed(self, records: list[JsonDict]) -> int: ...

    async def get_stats(self, pipeline: str) -> JsonDict: ...

    def purge(self, *, pipeline: str, older_than_days: int) -> int: ...

    def update_status(
        self, payload_hash: str, status: QuarantineRecordStatus
    ) -> bool: ...


@dataclass(frozen=True, slots=True)
class _QuarantineCommandContext:
    pipeline: str

    def run_async(
        self,
        coro: Coroutine[object, object, _T],
        *,
        reason_prefix: str,
        domain_error_title: str,
        unexpected_error_title: str,
    ) -> _T | None:
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
    for line in build_quarantine_grouped_lines(
        stats,
        pipeline=pipeline,
        top=top,
        group_by=group_by,
    ):
        click.echo(line)


def _resolve_silver_filter_error_code(
    *,
    silver_filter_only: bool,
    error_code: str | None,
    silver_filter_error_code: str,
) -> str | None:
    return silver_filter_error_code if silver_filter_only else error_code


def _inspect_quarantine(
    runtime_service: _QuarantineRuntimeService,
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
        if run_id is None:
            return await runtime_service.inspect(limit=limit, error_code=error_code)
        return await runtime_service.inspect(
            limit=limit,
            error_code=error_code,
            run_id=run_id,
        )

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
    runtime_service: _QuarantineRuntimeService,
    *,
    pipeline: str,
    output_json: bool,
    error_code: str | None,
    top: int = 10,
    group_by: str | None = None,
    run_id: str | None = None,
    run_manifest_service: RunManifestInspectionServiceProtocol | None = None,
) -> None:
    """Display quarantine statistics for one pipeline."""
    context = _QuarantineCommandContext(pipeline=pipeline)

    async def _stats() -> JsonDict:
        return await runtime_service.get_stats(error_code=error_code, run_id=run_id)

    stats = context.run_async(
        _stats(),
        reason_prefix="CLI_QUARANTINE_STATS",
        domain_error_title="Failed to get stats",
        unexpected_error_title="Failed to get stats",
    )
    if stats is None:
        return
    stats = enrich_run_scoped_stats(
        stats,
        run_id=run_id,
        run_manifest_service=run_manifest_service,
    )
    if output_json:
        click.echo(json.dumps(stats, indent=2))
        return
    _render_stats_dashboard(stats, pipeline=pipeline, top=top, group_by=group_by)


def _show_quarantine_stats_for_cli_options(
    runtime_service: _QuarantineRuntimeService,
    *,
    pipeline: str,
    output_json: bool,
    error_code: str | None,
    silver_filter_only: bool,
    silver_filter_error_code: str,
    top: int = 10,
    group_by: str | None = None,
    run_id: str | None = None,
    run_manifest_service: RunManifestInspectionServiceProtocol | None = None,
) -> None:
    """Resolve shared CLI aliases before displaying quarantine statistics."""
    _show_quarantine_stats(
        runtime_service,
        pipeline=pipeline,
        output_json=output_json,
        error_code=_resolve_silver_filter_error_code(
            silver_filter_only=silver_filter_only,
            error_code=error_code,
            silver_filter_error_code=silver_filter_error_code,
        ),
        top=top,
        group_by=group_by,
        run_id=run_id,
        run_manifest_service=run_manifest_service,
    )


def _show_quarantine_stats_for_pipeline_cli_options(
    get_runtime_service: Callable[[str], _QuarantineRuntimeService],
    get_run_manifest_service: Callable[[], RunManifestInspectionServiceProtocol],
    *,
    pipeline: str,
    output_json: bool,
    error_code: str | None,
    silver_filter_only: bool,
    silver_filter_error_code: str,
    top: int = 10,
    group_by: str | None = None,
    run_id: str | None = None,
) -> None:
    _show_quarantine_stats_for_cli_options(
        get_runtime_service(pipeline),
        pipeline=pipeline,
        output_json=output_json,
        error_code=error_code,
        silver_filter_only=silver_filter_only,
        silver_filter_error_code=silver_filter_error_code,
        top=top,
        group_by=group_by,
        run_id=run_id,
        run_manifest_service=get_run_manifest_service() if run_id else None,
    )


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
