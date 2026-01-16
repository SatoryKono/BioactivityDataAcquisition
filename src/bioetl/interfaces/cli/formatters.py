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
    from bioetl.application.services import (
        ExportResult,
        TableInfo,
        TablePreview,
        TableVacuumResult,
        VacuumAllResult,
    )


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
            click.echo(f"  Gold: {preview.gold.path} ({preview.gold.file_count} files)")
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


# =============================================================================
# Export formatters
# =============================================================================


def echo_table_list(tables: list[TableInfo]) -> None:
    """Output list of available Delta tables.

    Args:
        tables: List of TableInfo objects to display.
    """
    click.echo("\nAvailable Delta tables:\n")

    current_layer = ""
    for table in tables:
        if table.layer != current_layer:
            current_layer = table.layer
            click.echo(f"  {current_layer.upper()}:")

        click.echo(f"    {table.name}")

    click.echo()


def echo_export_preview(preview: TablePreview) -> None:
    """Output table preview with schema and sample data.

    Args:
        preview: TablePreview with schema and sample rows.
    """
    click.echo(f"\nTable: {preview.table_name} ({preview.layer})")
    click.echo(f"Rows: {preview.row_count:,}")
    click.echo(f"\nSchema ({len(preview.columns)} columns):")

    for col in preview.columns:
        nullable = " (nullable)" if col.nullable else ""
        click.echo(f"  {col.name}: {col.type}{nullable}")

    if preview.sample_rows:
        click.echo(f"\nSample data ({len(preview.sample_rows)} rows):")
        click.echo("-" * 60)

        # Get column names for header
        if preview.columns:
            col_names = [c.name for c in preview.columns[:5]]  # First 5 cols
            if len(preview.columns) > 5:
                col_names.append("...")
            click.echo(" | ".join(col_names))
            click.echo("-" * 60)

        # Display sample rows
        for row in preview.sample_rows:
            values = []
            for col in preview.columns[:5]:
                val = row.get(col.name, "")
                # Truncate long values
                val_str = str(val)[:30]
                if len(str(val)) > 30:
                    val_str += "..."
                values.append(val_str)
            if len(preview.columns) > 5:
                values.append("...")
            click.echo(" | ".join(values))

    click.echo()


def echo_export_result(result: ExportResult) -> None:
    """Output export operation result.

    Args:
        result: ExportResult with export outcome.
    """
    if result.success:
        click.echo(f"\nExported {result.row_count:,} rows to {result.format.upper()}")
        click.echo(f"Output: {result.output_path}")
    else:
        click.echo(f"\nExport failed: {result.error}", err=True)
