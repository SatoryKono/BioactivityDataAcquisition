"""Shared helpers for quarantine CLI commands."""

from __future__ import annotations

import asyncio
import json
import sys
from collections.abc import Callable, Coroutine
from typing import Protocol, TypeVar

import click

from bioetl.domain.exceptions import BioETLError
from bioetl.domain.types import JsonDict, QuarantineRecordStatus
from bioetl.interfaces.cli.commands.execution_policy import (
    CLI_ENTRYPOINT_TYPED_ERRORS,
)
from bioetl.interfaces.cli.commands.execution_policy import (
    handle_cli_failure as handle_cli_execution_failure,
)
from bioetl.interfaces.cli.exit_codes import ExitCode
from bioetl.interfaces.cli.formatters import (
    echo_error,
    echo_info,
    echo_quarantine_record,
)

__all__ = [
    "_inspect_quarantine",
    "_purge_quarantine",
    "_replay_quarantine",
    "_resolve_quarantine_record",
    "_show_quarantine_stats",
]

_T = TypeVar("_T")


class _QuarantineManager(Protocol):
    """Protocol for quarantine manager methods used by CLI."""

    async def inspect(
        self,
        limit: int,
        error_code: str | None = None,
    ) -> list[JsonDict]:
        """Return quarantined records."""
        ...

    async def get_stats(self) -> JsonDict:
        """Return aggregate quarantine statistics."""
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


def _handle_quarantine_failure(
    exc: BaseException,
    *,
    reason_code: str,
    pipeline: str,
    domain_error_title: str,
    unexpected_error_title: str,
    interrupted_message: str = "Quarantine command interrupted by user (Ctrl+C)",
) -> None:
    """Handle quarantine command failures with shared CLI policy."""
    handle_cli_execution_failure(
        exc,
        reason_code=reason_code,
        subject_key="pipeline",
        subject_value=pipeline,
        domain_error_title=domain_error_title,
        unexpected_error_title=unexpected_error_title,
        interrupted_message=interrupted_message,
        default_exit_code=ExitCode.FAIL,
    )


def _run_quarantine_async(
    coro: Coroutine[object, object, _T],
    *,
    pipeline: str,
    reason_prefix: str,
    domain_error_title: str,
    unexpected_error_title: str,
) -> _T | None:
    """Run an async quarantine coroutine with typed exception policy."""
    try:
        return asyncio.run(coro)
    except BioETLError as exc:
        _handle_quarantine_failure(
            exc,
            reason_code=f"{reason_prefix}_DOMAIN_ERROR",
            pipeline=pipeline,
            domain_error_title=domain_error_title,
            unexpected_error_title=unexpected_error_title,
        )
    except KeyboardInterrupt as exc:
        _handle_quarantine_failure(
            exc,
            reason_code=f"{reason_prefix}_SIGINT",
            pipeline=pipeline,
            domain_error_title=domain_error_title,
            unexpected_error_title=unexpected_error_title,
        )
    except CLI_ENTRYPOINT_TYPED_ERRORS as exc:
        _handle_quarantine_failure(
            exc,
            reason_code=f"{reason_prefix}_UNEXPECTED_ERROR",
            pipeline=pipeline,
            domain_error_title=domain_error_title,
            unexpected_error_title=unexpected_error_title,
        )
    finally:
        if getattr(coro, "cr_frame", None) is not None:
            coro.close()
    return None


def _run_quarantine_sync(
    fn: Callable[[], _T],
    *,
    pipeline: str,
    reason_prefix: str,
    domain_error_title: str,
    unexpected_error_title: str,
) -> _T | None:
    """Run a synchronous quarantine callable with typed exception policy."""
    try:
        return fn()
    except BioETLError as exc:
        _handle_quarantine_failure(
            exc,
            reason_code=f"{reason_prefix}_DOMAIN_ERROR",
            pipeline=pipeline,
            domain_error_title=domain_error_title,
            unexpected_error_title=unexpected_error_title,
        )
    except KeyboardInterrupt as exc:
        _handle_quarantine_failure(
            exc,
            reason_code=f"{reason_prefix}_SIGINT",
            pipeline=pipeline,
            domain_error_title=domain_error_title,
            unexpected_error_title=unexpected_error_title,
        )
    except CLI_ENTRYPOINT_TYPED_ERRORS as exc:
        _handle_quarantine_failure(
            exc,
            reason_code=f"{reason_prefix}_UNEXPECTED_ERROR",
            pipeline=pipeline,
            domain_error_title=domain_error_title,
            unexpected_error_title=unexpected_error_title,
        )
    return None


def _render_stats_dashboard(stats: JsonDict, *, pipeline: str) -> None:
    """Render human-readable quarantine statistics."""
    click.echo(f"\n{'=' * 50}")
    click.echo(f"  Quarantine Dashboard: {pipeline}")
    click.echo(f"{'=' * 50}")

    total = stats.get("total_count", 0)
    click.echo(f"\n  Total Records: {total}")

    by_error = stats.get("by_error_code", {})
    if by_error:
        click.echo("\n  By Error Code:")
        for code, count in sorted(by_error.items(), key=lambda item: -item[1]):
            pct = (count / total * 100) if total > 0 else 0
            click.echo(f"    - {code}: {count} ({pct:.1f}%)")

    by_status = stats.get("by_status", {})
    if by_status:
        click.echo("\n  By Status:")
        for status, count in sorted(by_status.items()):
            pct = (count / total * 100) if total > 0 else 0
            click.echo(f"    - {status}: {count} ({pct:.1f}%)")

    click.echo(f"\n{'=' * 50}\n")


def _inspect_quarantine(
    manager: _QuarantineManager,
    *,
    pipeline: str,
    limit: int,
    error_code: str | None,
) -> None:
    """Inspect quarantined records for one pipeline."""
    echo_info(f"Inspecting quarantine for {pipeline} (limit {limit})...")

    async def _inspect() -> list[JsonDict]:
        return await manager.inspect(limit=limit, error_code=error_code)

    records = _run_quarantine_async(
        _inspect(),
        pipeline=pipeline,
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
) -> None:
    """Display quarantine statistics for one pipeline."""

    async def _stats() -> JsonDict:
        return await manager.get_stats()

    stats = _run_quarantine_async(
        _stats(),
        pipeline=pipeline,
        reason_prefix="CLI_QUARANTINE_STATS",
        domain_error_title="Failed to get stats",
        unexpected_error_title="Failed to get stats",
    )
    if stats is None:
        return
    if output_json:
        click.echo(json.dumps(stats, indent=2))
        return
    _render_stats_dashboard(stats, pipeline=pipeline)


def _replay_quarantine(
    service: _QuarantineService,
    *,
    pipeline: str,
    error_code: str | None,
    max_age_days: int,
    dry_run: bool,
) -> None:
    """Replay or preview replay for quarantine records."""
    records = _run_quarantine_sync(
        lambda: service.replay(
            pipeline=pipeline,
            error_code=error_code,
            max_age_days=max_age_days,
        ),
        pipeline=pipeline,
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
        click.echo(f"\nWould replay {len(records)} record(s):\n")
        for index, record in enumerate(records[:10], 1):
            payload_hash = record.get("payload_hash")
            hash_display = payload_hash[:16] if payload_hash else "—"
            click.echo(
                f"  {index}. Error: {record.get('error_code')} | Hash: {hash_display}..."
            )
        if len(records) > 10:
            click.echo(f"  ... and {len(records) - 10} more")
        return

    click.echo(f"\nReplaying {len(records)} record(s)...")
    marked_count = _run_quarantine_sync(
        lambda: service.mark_as_reprocessed(records),
        pipeline=pipeline,
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
    if dry_run:

        async def _get_stats() -> JsonDict:
            return await service.get_stats(pipeline)

        stats = _run_quarantine_async(
            _get_stats(),
            pipeline=pipeline,
            reason_prefix="CLI_QUARANTINE_PURGE_PREVIEW",
            domain_error_title="Failed to preview quarantine purge with domain error",
            unexpected_error_title="Unexpected error during quarantine purge preview",
        )
        if stats is None:
            return
        total = stats.get("total_count", 0)
        click.echo(f"\nWould purge records older than {older_than_days} days.")
        click.echo(f"Current total in quarantine: {total}")
        click.echo("\nUse without --dry-run to actually purge.")
        return

    if not force:
        click.confirm(
            f"Delete quarantine records older than {older_than_days} days for {pipeline}?",
            abort=True,
        )

    count = _run_quarantine_sync(
        lambda: service.purge(
            pipeline=pipeline,
            older_than_days=older_than_days,
        ),
        pipeline=pipeline,
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
    success = _run_quarantine_sync(
        lambda: service.update_status(
            payload_hash,
            QuarantineRecordStatus[status],
        ),
        pipeline=pipeline,
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
