"""CLI output formatters for BioETL.

Provides formatting utilities for CLI output. These are pure presentation
functions without business logic - they only transform data into
human-readable format.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import click

if TYPE_CHECKING:
    from bioetl.application.core.cleanup_service import CleanupPreview
    from bioetl.application.services import TableVacuumResult, VacuumAllResult


def format_bytes(b: int) -> str:
    """Format bytes as human-readable string.

    Args:
        b: Number of bytes.

    Returns:
        Human-readable string (e.g., "1.5 GB", "256 KB").
    """
    for unit, divisor in [("GB", 1024**3), ("MB", 1024**2), ("KB", 1024)]:
        if b >= divisor:
            return f"{b / divisor:.2f} {unit}"
    return f"{b} bytes"


def echo_cleanup_preview(preview: CleanupPreview) -> None:
    """Output cleanup preview information.

    Args:
        preview: CleanupPreview with information about what would be cleared.
    """
    click.echo("\nFiles/directories that would be cleared:")

    if preview.silver.exists:
        click.echo(
            f"  Silver: {preview.silver.path} ({preview.silver.file_count} files)"
        )
    else:
        click.echo(f"  Silver: {preview.silver.path} (does not exist)")

    if preview.gold:
        if preview.gold.exists:
            click.echo(
                f"  Gold: {preview.gold.path} ({preview.gold.file_count} files)"
            )
        else:
            click.echo(f"  Gold: {preview.gold.path} (does not exist)")

    click.echo(f"\nTotal items that would be cleared: ~{preview.total_files}")
    click.echo("\nNo changes were made (dry-run mode).")


def echo_vacuum_result(result: TableVacuumResult, dry_run: bool) -> None:
    """Output vacuum result for a single table.

    Args:
        result: TableVacuumResult with operation outcome.
        dry_run: Whether this was a dry run.
    """
    prefix = "[DRY-RUN] " if dry_run else ""
    action = "Would vacuum" if dry_run else "Vacuuming"

    click.echo(f"{prefix}{action} {result.layer}/{result.table_name}...")

    if result.error:
        click.echo(f"  Error: {result.error}", err=True)
    else:
        result_verb = "Would remove" if dry_run else "Removed"
        click.echo(f"  {result_verb} {result.files_removed} files")


def echo_vacuum_all_summary(result: VacuumAllResult) -> None:
    """Output summary for vacuum-all operation.

    Args:
        result: VacuumAllResult with aggregated statistics.
    """
    result_verb = "would remove" if result.dry_run else "removed"
    click.echo(f"\nTotal: {result_verb} {result.total_files_removed} files")

    if result.failed_tables:
        click.echo(f"Failed tables: {', '.join(result.failed_tables)}", err=True)


def echo_quarantine_record(record: dict[str, Any]) -> None:
    """Output a single quarantine record.

    Args:
        record: Dictionary with quarantine record data.
    """
    error_code = record.get("error_code", "UNKNOWN")
    payload = record.get("payload", "N/A")
    click.echo(f"Error: {error_code} | Payload: {payload}")


def echo_checkpoint(checkpoint: str) -> None:
    """Output a single checkpoint entry.

    Args:
        checkpoint: Checkpoint identifier string.
    """
    click.echo(f"- {checkpoint}")


def echo_error(message: str, detail: str | None = None) -> None:
    """Output error message to stderr.

    Args:
        message: Main error message.
        detail: Optional additional detail.
    """
    if detail:
        click.echo(f"{message}: {detail}", err=True)
    else:
        click.echo(message, err=True)


def echo_info(message: str) -> None:
    """Output informational message.

    Args:
        message: Message to output.
    """
    click.echo(message)


def echo_warning(message: str) -> None:
    """Output warning message.

    Args:
        message: Warning message to output.
    """
    click.echo(f"WARNING: {message}")


def echo_dry_run_prefix(message: str) -> None:
    """Output message with dry-run prefix.

    Args:
        message: Message to prefix with [DRY-RUN].
    """
    click.echo(f"[DRY-RUN] {message}")
