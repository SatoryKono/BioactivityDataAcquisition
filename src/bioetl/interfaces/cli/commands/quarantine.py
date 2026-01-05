"""Quarantine management commands for BioETL CLI.

Implements quarantine inspection and management commands.
Provides error recovery dashboard functionality (ERR-001).
"""

from __future__ import annotations

import asyncio
import json
import sys
from typing import Any

import click

from bioetl.composition.entrypoints import (
    get_quarantine_manager,
    get_quarantine_service,
)
from bioetl.domain.types import QuarantineRecordStatus
from bioetl.interfaces.cli.exit_codes import ExitCode
from bioetl.interfaces.cli.formatters import (
    echo_error,
    echo_info,
    echo_quarantine_record,
)


@click.group()
def quarantine() -> None:
    """Manage quarantine (failed records).

    Error recovery dashboard commands for inspecting, analyzing,
    and recovering from pipeline failures.
    """
    pass


@quarantine.command("inspect")
@click.option("--pipeline", required=True, help="Pipeline name")
@click.option("--limit", type=int, default=100, help="Maximum records to show")
@click.option("--error-code", help="Filter by error code")
def quarantine_inspect(pipeline: str, limit: int, error_code: str | None) -> None:
    """Inspect quarantined records.

    Example:
        bioetl quarantine inspect --pipeline chembl_activity
        bioetl quarantine inspect --pipeline chembl_activity --error-code DQ_MISSING_FIELD
    """
    echo_info(f"Inspecting quarantine for {pipeline} (limit {limit})...")

    quarantine_manager = get_quarantine_manager(pipeline)

    async def _inspect() -> None:
        records = await quarantine_manager.inspect(limit=limit, error_code=error_code)
        if not records:
            echo_info("No records found.")
            return

        for rec in records:
            echo_quarantine_record(rec)

    asyncio.run(_inspect())


@quarantine.command("stats")
@click.option("--pipeline", required=True, help="Pipeline name")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def quarantine_stats(pipeline: str, output_json: bool) -> None:
    """Show quarantine statistics dashboard.

    Displays a summary of quarantined records including:
    - Total count
    - Breakdown by error code
    - Breakdown by status (NEW, REVIEWED, RESOLVED)

    Example:
        bioetl quarantine stats --pipeline chembl_activity
        bioetl quarantine stats --pipeline chembl_activity --json
    """
    quarantine_manager = get_quarantine_manager(pipeline)

    async def _stats() -> dict[str, Any]:
        return await quarantine_manager.get_stats()

    try:
        stats = asyncio.run(_stats())
    except Exception as e:
        echo_error(f"Failed to get stats: {e}")
        sys.exit(ExitCode.FAIL)

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
    """Replay (retry) quarantined records.

    Retrieves quarantined records for reprocessing by the pipeline.
    Use --dry-run to preview records without actually replaying.

    Example:
        bioetl quarantine replay --pipeline chembl_activity --dry-run
        bioetl quarantine replay --pipeline chembl_activity --error-code DQ_NETWORK_ERROR
    """
    quarantine_service = get_quarantine_service()

    records = quarantine_service.replay(
        pipeline=pipeline,
        error_code=error_code,
        max_age_days=max_age_days,
    )

    if not records:
        echo_info("No records found for replay.")
        return

    if dry_run:
        click.echo(f"\nWould replay {len(records)} record(s):\n")
        for i, rec in enumerate(records[:10], 1):
            click.echo(
                f"  {i}. Error: {rec.get('error_code')} | Hash: {rec.get('payload_hash', 'N/A')[:16]}..."
            )
        if len(records) > 10:
            click.echo(f"  ... and {len(records) - 10} more")
    else:
        click.echo(f"\nReplaying {len(records)} record(s)...")
        # Mark records as reprocessed
        marked_count = quarantine_service.mark_as_reprocessed(records)
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
    """Purge old quarantine records.

    Deletes quarantined records older than the specified number of days.
    Default retention is 30 days per RULES.md §2.6.

    Example:
        bioetl quarantine purge --pipeline chembl_activity --dry-run
        bioetl quarantine purge --pipeline chembl_activity --older-than-days 60
    """
    quarantine_service = get_quarantine_service()

    if dry_run:
        # Get count of records that would be purged
        async def _get_stats() -> dict[str, Any]:
            return await quarantine_service.get_stats(pipeline)

        stats = asyncio.run(_get_stats())
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

    count = quarantine_service.purge(
        pipeline=pipeline,
        older_than_days=older_than_days,
    )

    click.echo(f"Purged {count} record(s) from quarantine.")


@quarantine.command("resolve")
@click.option("--pipeline", required=True, help="Pipeline name")
@click.option("--payload-hash", required=True, help="Payload hash of record to resolve")
@click.option(
    "--status", type=click.Choice(["IGNORED", "REPROCESSED"]), default="IGNORED"
)
def quarantine_resolve(pipeline: str, payload_hash: str, status: str) -> None:
    """Mark a quarantine record as resolved.

    Updates the status of a quarantined record to indicate
    it has been reviewed (IGNORED) or reprocessed (REPROCESSED).

    Status values:
    - IGNORED: Reviewed and marked as non-actionable
    - REPROCESSED: Successfully reprocessed and moved to Silver

    Example:
        bioetl quarantine resolve --pipeline chembl_activity --payload-hash abc123
        bioetl quarantine resolve --pipeline chembl_activity --payload-hash abc123 --status REPROCESSED
    """
    quarantine_service = get_quarantine_service()

    new_status = QuarantineRecordStatus[status]
    success = quarantine_service.update_status(payload_hash, new_status)

    if success:
        click.echo(f"Record {payload_hash} marked as {status}.")
    else:
        echo_error(f"Record not found: {payload_hash}")
        sys.exit(ExitCode.FAIL)


__all__ = ["quarantine"]
