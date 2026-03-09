"""Export commands for BioETL CLI.

Provides commands to export Silver/Gold Delta Lake tables
to CSV, XLSX, and TSV formats.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Literal, Protocol, cast

import click

from bioetl.application.services import (
    ExportOptions,
    ExportResult,
    TableInfo,
    TablePreview,
)
from bioetl.composition.entrypoints import get_export_service
from bioetl.domain.exceptions import BioETLError
from bioetl.interfaces.cli.commands.execution_policy import (
    CLI_ENTRYPOINT_TYPED_ERRORS,
)
from bioetl.interfaces.cli.commands.execution_policy import (
    handle_cli_failure as handle_cli_execution_failure,
)
from bioetl.interfaces.cli.exit_codes import ExitCode
from bioetl.interfaces.cli.formatters import (
    echo_error,
    echo_export_preview,
    echo_export_result,
    echo_info,
    echo_table_list,
)

__all__ = ["ExportFormat", "export_command"]

ExportFormat = Literal["csv", "xlsx", "tsv"]


class _ExportCommandService(Protocol):
    """Service protocol for export CLI commands."""

    async def preview(self, table_name: str, layer: str = "silver") -> TablePreview:
        """Return a preview of the given table."""
        ...

    async def export(
        self,
        table_name: str,
        layer: str = "silver",
        options: ExportOptions | None = None,
    ) -> ExportResult:
        """Export the given table to the specified format."""
        ...

    def list_tables(self, layer: str = "all") -> list[TableInfo]:
        """List available tables for export."""
        ...


def _handle_export_failure(
    exc: BaseException,
    *,
    reason_code: str,
    table: str,
    domain_error_title: str,
    unexpected_error_title: str,
) -> None:
    """Handle export command failures with shared CLI policy."""
    handle_cli_execution_failure(
        exc,
        reason_code=reason_code,
        subject_key="table",
        subject_value=table,
        domain_error_title=domain_error_title,
        unexpected_error_title=unexpected_error_title,
        interrupted_message="Export interrupted by user (Ctrl+C)",
        default_exit_code=ExitCode.FAIL,
    )


def _resolve_list_layer(layer: str) -> str:
    """Map CLI layer value to service list scope.

    Args:
        layer: CLI layer option value (e.g., 'silver', 'gold').

    Returns:
        Scope string accepted by the export service list method.
    """
    return layer if layer != "silver" else "all"


def _require_table_argument(table: str | None) -> str:
    """Validate table argument for non-list operations.

    Args:
        table: Table name argument from CLI; None if the user did not provide it.

    Returns:
        Validated table name string.
    """
    if table:
        return table
    echo_error("TABLE argument is required (or use --list to see available tables)")
    raise SystemExit(ExitCode.FAIL)


def _parse_columns(columns: str | None) -> list[str] | None:
    """Parse comma-separated columns from CLI option.

    Args:
        columns: Comma-separated column names string from CLI; None if not provided.

    Returns:
        List of stripped column name strings, or None if no columns were specified.
    """
    if not columns:
        return None
    return [column.strip() for column in columns.split(",")]


def _parse_export_format(output_format: str) -> ExportFormat:
    """Parse output format value into strict ExportFormat literal.

    Args:
        output_format: Format string from CLI (e.g., 'csv', 'xlsx', 'tsv').

    Returns:
        Validated ExportFormat literal; defaults to 'csv' for unrecognized values.
    """
    if output_format in {"csv", "xlsx", "tsv"}:
        return cast("ExportFormat", output_format)
    return "csv"


def _build_export_options(
    output_format: str,
    output: Path | None,
    limit: int | None,
    columns: str | None,
) -> ExportOptions:
    """Build validated ExportOptions from CLI parameters.

    Args:
        output_format: Format string from CLI (e.g., 'csv', 'xlsx', 'tsv').
        output: Output directory path; uses the default export directory when None.
        limit: Maximum number of rows to export; exports all rows when None.
        columns: Comma-separated column names to include; exports all columns when None.

    Returns:
        Configured ExportOptions instance.
    """
    return ExportOptions(
        format=_parse_export_format(output_format),
        output_path=output,
        limit=limit,
        columns=_parse_columns(columns),
    )


def _run_preview(
    service: _ExportCommandService,
    table: str,
    layer: str,
) -> None:
    """Execute async preview operation from sync CLI context.

    Args:
        service: Export service used to fetch the table preview.
        table: Table name in 'provider.entity' format (e.g., 'chembl.activity').
        layer: Medallion layer to preview from ('silver' or 'gold').
    """

    async def _preview() -> None:
        table_preview = await service.preview(table, layer=layer)
        echo_export_preview(table_preview)

    coro = _preview()
    try:
        asyncio.run(coro)
    except FileNotFoundError as exc:
        echo_error(str(exc))
        raise SystemExit(ExitCode.FAIL) from None
    except BioETLError as exc:
        _handle_export_failure(
            exc,
            reason_code="CLI_EXPORT_PREVIEW_DOMAIN_ERROR",
            table=table,
            domain_error_title="Export preview failed with domain error",
            unexpected_error_title="Unexpected error during export preview",
        )
    except KeyboardInterrupt as exc:
        _handle_export_failure(
            exc,
            reason_code="CLI_EXPORT_PREVIEW_SIGINT",
            table=table,
            domain_error_title="Export preview failed with domain error",
            unexpected_error_title="Unexpected error during export preview",
        )
    except CLI_ENTRYPOINT_TYPED_ERRORS as exc:
        _handle_export_failure(
            exc,
            reason_code="CLI_EXPORT_PREVIEW_UNEXPECTED_ERROR",
            table=table,
            domain_error_title="Export preview failed with domain error",
            unexpected_error_title="Unexpected error during export preview",
        )
    finally:
        if getattr(coro, "cr_frame", None) is not None:
            coro.close()


def _run_export(
    service: _ExportCommandService,
    table: str,
    layer: str,
    options: ExportOptions,
) -> None:
    """Execute async export operation from sync CLI context.

    Args:
        service: Export service used to perform the table export.
        table: Table name in 'provider.entity' format (e.g., 'chembl.activity').
        layer: Medallion layer to export from ('silver' or 'gold').
        options: ExportOptions with format, output path, row limit, and column selection.
    """

    async def _export() -> None:
        result = await service.export(table, layer=layer, options=options)
        echo_export_result(result)
        if not result.success:
            raise SystemExit(ExitCode.FAIL)

    coro = _export()
    try:
        asyncio.run(coro)
    except BioETLError as exc:
        _handle_export_failure(
            exc,
            reason_code="CLI_EXPORT_RUN_DOMAIN_ERROR",
            table=table,
            domain_error_title="Export failed with domain error",
            unexpected_error_title="Unexpected error during export",
        )
    except KeyboardInterrupt as exc:
        _handle_export_failure(
            exc,
            reason_code="CLI_EXPORT_RUN_SIGINT",
            table=table,
            domain_error_title="Export failed with domain error",
            unexpected_error_title="Unexpected error during export",
        )
    except CLI_ENTRYPOINT_TYPED_ERRORS as exc:
        _handle_export_failure(
            exc,
            reason_code="CLI_EXPORT_RUN_UNEXPECTED_ERROR",
            table=table,
            domain_error_title="Export failed with domain error",
            unexpected_error_title="Unexpected error during export",
        )
    finally:
        if getattr(coro, "cr_frame", None) is not None:
            coro.close()


def _list_tables_or_exit(
    service: _ExportCommandService,
    *,
    layer: str,
) -> bool:
    """Handle table listing mode.

    Args:
        service: Export service used to list available tables.
        layer: Medallion layer scope for listing ('silver', 'gold', or 'all').

    Returns:
        True when list mode is handled and command should return.
    """
    try:
        tables = service.list_tables(layer=_resolve_list_layer(layer))
    except BioETLError as exc:
        _handle_export_failure(
            exc,
            reason_code="CLI_EXPORT_LIST_DOMAIN_ERROR",
            table=f"<list:{layer}>",
            domain_error_title="Export table listing failed with domain error",
            unexpected_error_title="Unexpected error during export table listing",
        )
        return True
    except KeyboardInterrupt as exc:
        _handle_export_failure(
            exc,
            reason_code="CLI_EXPORT_LIST_SIGINT",
            table=f"<list:{layer}>",
            domain_error_title="Export table listing failed with domain error",
            unexpected_error_title="Unexpected error during export table listing",
        )
        return True
    except CLI_ENTRYPOINT_TYPED_ERRORS as exc:
        _handle_export_failure(
            exc,
            reason_code="CLI_EXPORT_LIST_UNEXPECTED_ERROR",
            table=f"<list:{layer}>",
            domain_error_title="Export table listing failed with domain error",
            unexpected_error_title="Unexpected error during export table listing",
        )
        return True
    if not tables:
        echo_info("No Delta tables found.")
        return True
    echo_table_list(tables)
    return True


@click.command("export")
@click.argument("table", required=False)
@click.option(
    "--list",
    "list_tables",
    is_flag=True,
    help="List all available Delta tables",
)
@click.option(
    "--preview",
    is_flag=True,
    help="Show table schema and sample data",
)
@click.option(
    "--format",
    "-f",
    "output_format",
    type=click.Choice(["csv", "xlsx", "tsv"]),
    default="csv",
    help="Output format (default: csv)",
)
@click.option(
    "--layer",
    "-l",
    type=click.Choice(["silver", "gold"]),
    default="silver",
    help="Medallion layer to export from (default: silver)",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    help="Output directory (default: data/exports)",
)
@click.option(
    "--limit",
    type=int,
    help="Maximum number of rows to export",
)
@click.option(
    "--columns",
    "-c",
    help="Comma-separated list of columns to include",
)
def export_command(
    table: str | None,
    list_tables: bool,
    preview: bool,
    output_format: str,
    layer: str,
    output: Path | None,
    limit: int | None,
    columns: str | None,
) -> None:
    """Export Delta Lake tables.

    `table` must use `provider.entity` format (for example `chembl.activity`).
    Use `--list` to display available tables and `--preview` for schema/sample.
    """
    service = get_export_service()

    if list_tables:
        _list_tables_or_exit(service, layer=layer)
        return

    resolved_table = _require_table_argument(table)

    if preview:
        _run_preview(service=service, table=resolved_table, layer=layer)
        return

    options = _build_export_options(
        output_format=output_format,
        output=output,
        limit=limit,
        columns=columns,
    )
    _run_export(service=service, table=resolved_table, layer=layer, options=options)
