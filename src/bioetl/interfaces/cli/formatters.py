"""CLI output formatters for BioETL.

Provides formatting utilities for CLI output. These are pure presentation
functions without business logic - they only transform data into
human-readable format.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import click

from bioetl.domain.types import JsonDict

if TYPE_CHECKING:
    from collections.abc import Sequence

    from bioetl.application.core.lifecycle.cleanup_service import CleanupPreview
    from bioetl.application.services import (
        ColumnInfo,
        ExportResult,
        TableInfo,
        TablePreview,
        TableVacuumResult,
        VacuumAllResult,
    )


__all__ = [
    "echo_checkpoint",
    "echo_cleanup_preview",
    "echo_dry_run_prefix",
    "echo_error",
    "echo_export_preview",
    "echo_export_result",
    "echo_info",
    "echo_quarantine_record",
    "echo_table_list",
    "echo_vacuum_all_summary",
    "echo_vacuum_result",
    "echo_warning",
    "format_bytes",
]


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


def _echo_error_detail_fields(error_details: dict[str, object]) -> None:
    """Print structured quarantine error detail fields when present."""
    for label, key in (
        ("Reason Code", "reason_code"),
        ("Rule Type", "rule_type"),
        ("Field", "field"),
        ("Operator", "operator"),
        ("Expected", "expected"),
        ("Actual", "actual"),
    ):
        value = error_details.get(key)
        if value is None or value == "":
            continue
        click.echo(f"{label}: {value}")


def echo_quarantine_record(
    record: JsonDict,  # Any: CLI/HTTP response values are heterogeneous
) -> None:  # Any: quarantine record has heterogeneous values
    """Output a single quarantine record.

    Args:
        record: Dictionary with quarantine record data.
    """
    error_code = record.get("error_code") or "UNKNOWN"
    payload_hash = record.get("payload_hash")
    dq_status = record.get("dq_status") or "UNKNOWN"
    ingestion_ts = record.get("ingestion_ts")
    payload = record.get("payload")
    payload_display = payload if payload is not None else "—"
    header_parts = [f"Error: {error_code}", f"Status: {dq_status}"]
    if isinstance(payload_hash, str) and payload_hash:
        header_parts.append(f"Hash: {payload_hash[:16]}...")
    if ingestion_ts:
        header_parts.append(f"Ingested: {ingestion_ts}")
    click.echo(" | ".join(header_parts))

    error_details = record.get("error_details")
    if isinstance(error_details, dict) and error_details:
        if error_details.get("message"):
            click.echo(f"Reason: {error_details['message']}")
        _echo_error_detail_fields(error_details)

    click.echo(f"Payload: {payload_display}")
    click.echo("")


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


def _format_preview_row(
    row: dict[str, object],
    columns: Sequence[ColumnInfo],
    max_cols: int = 5,
) -> str:
    """Format a single sample row for preview display."""
    values = []
    for col in columns[:max_cols]:
        val = str(row.get(col.name, ""))
        values.append(f"{val[:30]}..." if len(val) > 30 else val)
    if len(columns) > max_cols:
        values.append("...")
    return " | ".join(values)


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

    if not preview.sample_rows:
        click.echo()
        return

    click.echo(f"\nSample data ({len(preview.sample_rows)} rows):")
    click.echo("-" * 60)

    if preview.columns:
        col_names = [c.name for c in preview.columns[:5]]
        if len(preview.columns) > 5:
            col_names.append("...")
        click.echo(" | ".join(col_names))
        click.echo("-" * 60)

    for row in preview.sample_rows:
        click.echo(_format_preview_row(row, preview.columns))

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
