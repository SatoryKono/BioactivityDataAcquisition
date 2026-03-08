"""Quarantine management commands for BioETL CLI.

Implements quarantine inspection and management commands.
Provides error recovery dashboard functionality (ERR-001).
"""

from __future__ import annotations

import asyncio
import json
import sys
from collections.abc import Callable, Coroutine
from typing import Any, TypeVar

import click

from bioetl.composition.entrypoints import (
    get_quarantine_manager,
    get_quarantine_service,
)
from bioetl.domain.exceptions import BioETLError
from bioetl.domain.types import QuarantineRecordStatus
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

_T = TypeVar("_T")


def _handle_quarantine_failure(
    exc: BaseException,
    *,
    reason_code: str,
    pipeline: str,
    domain_error_title: str,
    unexpected_error_title: str,
    interrupted_message: str = "Quarantine command interrupted by user (Ctrl+C)",
) -> None:
    """Handle quarantine command failures with shared CLI policy.

    Args:
        exc: Exception caught at the CLI command boundary.
        reason_code: Machine-readable code for the failure (e.g., 'CLI_QUARANTINE_INSPECT_DOMAIN_ERROR').
        pipeline: Pipeline name used as subject value in the structured error context.
        domain_error_title: Human-readable title for BioETLError failures.
        unexpected_error_title: Human-readable title for unexpected exception failures.
        interrupted_message: Message displayed when KeyboardInterrupt is caught.
    """
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
    coro: Coroutine[Any, Any, _T],  # Any: standard Coroutine type params
    *,
    pipeline: str,
    reason_prefix: str,
    domain_error_title: str,
    unexpected_error_title: str,
) -> _T | None:
    """Run an async quarantine coroutine with typed exception policy.

    Args:
        coro: Async coroutine to run via asyncio.run.
        pipeline: Pipeline name used in error context for structured failure handling.
        reason_prefix: Prefix for the reason_code (e.g., 'CLI_QUARANTINE_INSPECT');
            suffixed with '_DOMAIN_ERROR', '_SIGINT', or '_UNEXPECTED_ERROR'.
        domain_error_title: Human-readable title for BioETLError failures.
        unexpected_error_title: Human-readable title for unexpected exception failures.

    Returns:
        Coroutine result on success, None if an exception was handled and process will exit.
    """
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
    """Run a synchronous quarantine callable with typed exception policy.

    Args:
        fn: Callable to invoke synchronously; must take no arguments.
        pipeline: Pipeline name used in error context for structured failure handling.
        reason_prefix: Prefix for the reason_code (e.g., 'CLI_QUARANTINE_REPLAY');
            suffixed with '_DOMAIN_ERROR', '_SIGINT', or '_UNEXPECTED_ERROR'.
        domain_error_title: Human-readable title for BioETLError failures.
        unexpected_error_title: Human-readable title for unexpected exception failures.

    Returns:
        Callable result on success, None if an exception was handled and process will exit.
    """
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


@click.group()
def quarantine() -> None:
    """Manage quarantine (failed records)."""


@quarantine.command("inspect")
@click.option("--pipeline", required=True, help="Pipeline name")
@click.option("--limit", type=int, default=100, help="Maximum records to show")
@click.option("--error-code", help="Filter by error code")
def quarantine_inspect(pipeline: str, limit: int, error_code: str | None) -> None:
    """Inspect quarantined records for a pipeline."""
    echo_info(f"Inspecting quarantine for {pipeline} (limit {limit})...")

    quarantine_manager = get_quarantine_manager(pipeline)

    async def _inspect() -> None:
        records = await quarantine_manager.inspect(limit=limit, error_code=error_code)
        if not records:
            echo_info("No records found.")
            return

        for rec in records:
            echo_quarantine_record(rec)

    _run_quarantine_async(
        _inspect(),
        pipeline=pipeline,
        reason_prefix="CLI_QUARANTINE_INSPECT",
        domain_error_title="Failed to inspect quarantine with domain error",
        unexpected_error_title="Unexpected error during quarantine inspect",
    )


@quarantine.command("stats")
@click.option("--pipeline", required=True, help="Pipeline name")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def quarantine_stats(pipeline: str, output_json: bool) -> None:
    """Show quarantine statistics dashboard for a pipeline."""
    quarantine_manager = get_quarantine_manager(pipeline)

    async def _stats() -> dict[str, Any]:  # Any: heterogeneous values
        return await quarantine_manager.get_stats()

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
    else:
        click.echo(f"\n{'=' * 50}")
        click.echo(f"  Quarantine Dashboard: {pipeline}")
        click.echo(f"{'=' * 50}")

        total = stats.get("total_count", 0)
        click.echo(f"\n  Total Records: {total}")

        by_error = stats.get("by_error_code", {})
        if by_error:
            click.echo("\n  By Error Code:")
            for code, count in sorted(by_error.items(), key=lambda x: -x[1]):
                pct = (count / total * 100) if total > 0 else 0
                click.echo(f"    - {code}: {count} ({pct:.1f}%)")

        by_status = stats.get("by_status", {})
        if by_status:
            click.echo("\n  By Status:")
            for status, count in sorted(by_status.items()):
                pct = (count / total * 100) if total > 0 else 0
                click.echo(f"    - {status}: {count} ({pct:.1f}%)")

        click.echo(f"\n{'=' * 50}\n")


@quarantine.command("replay")
@click.option("--pipeline", required=True, help="Pipeline name")
@click.option("--error-code", help="Filter by error code")
@click.option(
    "--max-age-days", type=int, default=7, help="Max age of records to replay"
)
@click.option("--dry-run", is_flag=True, help="Show records without replaying")
def quarantine_replay(
    pipeline: str,
    error_code: str | None,
    max_age_days: int,
    dry_run: bool,
) -> None:
    """Replay (retry) quarantined records."""
    quarantine_service = get_quarantine_service()
    records = _run_quarantine_sync(
        lambda: quarantine_service.replay(
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
        for i, rec in enumerate(records[:10], 1):
            payload_hash = rec.get("payload_hash")
            hash_display = payload_hash[:16] if payload_hash else "—"
            click.echo(
                f"  {i}. Error: {rec.get('error_code')} | Hash: {hash_display}..."
            )
        if len(records) > 10:
            click.echo(f"  ... and {len(records) - 10} more")
    else:
        click.echo(f"\nReplaying {len(records)} record(s)...")
        marked_count = _run_quarantine_sync(
            lambda: quarantine_service.mark_as_reprocessed(records),
            pipeline=pipeline,
            reason_prefix="CLI_QUARANTINE_REPLAY_MARK",
            domain_error_title="Failed to mark replayed records with domain error",
            unexpected_error_title="Unexpected error during quarantine replay mark",
        )
        if marked_count is None:
            return
        click.echo(f"Marked {marked_count} record(s) as REPROCESSED.")
        echo_info("Records are ready for reprocessing by the pipeline.")


@quarantine.command("purge")
@click.option("--pipeline", required=True, help="Pipeline name")
@click.option(
    "--older-than-days", type=int, default=30, help="Delete records older than N days"
)
@click.option("--dry-run", is_flag=True, help="Show count without deleting")
@click.option("--force", is_flag=True, help="Skip confirmation prompt")
def quarantine_purge(
    pipeline: str,
    older_than_days: int,
    dry_run: bool,
    force: bool,
) -> None:
    """Purge old quarantine records."""
    quarantine_service = get_quarantine_service()

    if dry_run:
        # Get count of records that would be purged
        async def _get_stats() -> dict[
            str, Any  # Any: CLI/HTTP response values are heterogeneous
        ]:  # Any: quarantine record has heterogeneous values
            return await quarantine_service.get_stats(pipeline)

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
        lambda: quarantine_service.purge(
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


@quarantine.command("resolve")
@click.option("--pipeline", required=True, help="Pipeline name")
@click.option("--payload-hash", required=True, help="Payload hash of record to resolve")
@click.option(
    "--status", type=click.Choice(["IGNORED", "REPROCESSED"]), default="IGNORED"
)
def quarantine_resolve(pipeline: str, payload_hash: str, status: str) -> None:
    """Mark a quarantine record as resolved."""
    quarantine_service = get_quarantine_service()
    success = _run_quarantine_sync(
        lambda: quarantine_service.update_status(
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
    else:
        echo_error(f"Record not found: {payload_hash}")
        sys.exit(ExitCode.FAIL)


COMMANDS = (
    quarantine_inspect,
    quarantine_purge,
    quarantine_replay,
    quarantine_resolve,
    quarantine_stats,
)

__all__ = ["quarantine"]
