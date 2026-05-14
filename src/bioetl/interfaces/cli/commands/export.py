"""Export commands for BioETL CLI."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

import click

from bioetl.interfaces.cli.commands.export_support import (
    ExportFormat,
    _build_export_options,
    _list_tables_or_exit,
    _require_table_argument,
    _run_export,
    _run_preview,
)

if TYPE_CHECKING:
    from bioetl.application.services.export_service import ExportService

__all__ = ["ExportFormat", "export_command"]


def _scrub_helper_module_binding() -> None:
    """Keep helper-only export_support off the package-root public seam."""
    package = sys.modules.get(__package__)
    if package is not None and hasattr(package, "export_support"):
        delattr(package, "export_support")


_scrub_helper_module_binding()


def get_export_service() -> ExportService:
    """Load the export service through composition on demand."""
    from bioetl.composition.control_plane_api import get_export_service as _impl

    return _impl()


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
