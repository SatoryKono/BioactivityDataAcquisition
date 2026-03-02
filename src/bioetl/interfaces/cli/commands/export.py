"""Export commands for BioETL CLI.

Provides commands to export Silver/Gold Delta Lake tables
to CSV, XLSX, and TSV formats.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import click

from bioetl.application.services import ExportOptions
from bioetl.composition.entrypoints import get_export_service
from bioetl.interfaces.cli.formatters import (
    echo_error,
    echo_export_preview,
    echo_export_result,
    echo_info,
    echo_table_list,
)


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
    """Export Delta Lake tables to CSV, XLSX, or TSV format.

    TABLE: Table name in format "provider.entity" (e.g., chembl.activity)

    Examples:

        # List all available tables
        bioetl export --list

        # List only Silver layer tables
        bioetl export --list --layer silver

        # Preview table schema and sample data
        bioetl export chembl.activity --preview

        # Export to CSV (default)
        bioetl export chembl.activity

        # Export to Excel format
        bioetl export chembl.activity --format xlsx

        # Export with row limit
        bioetl export chembl.activity --limit 10000

        # Export specific columns
        bioetl export chembl.activity --columns id,name,value

        # Export Gold layer
        bioetl export chembl.activity --layer gold

        # Export to custom directory
        bioetl export chembl.activity -o ./my_exports

    Args:
        table: Table.
        list_tables: Whether to list tables.
        preview: Whether to preview.
        output_format: Output format.
        layer: Layer.
        output: Path to output.
        limit: Maximum number of records to process.
        columns: List of column names.
    """
    service = get_export_service()

    # Handle --list flag
    if list_tables:
        tables = service.list_tables(layer=layer if layer != "silver" else "all")
        if not tables:
            echo_info("No Delta tables found.")
            return
        echo_table_list(tables)
        return

    # Validate table argument for other operations
    if not table:
        echo_error("TABLE argument is required (or use --list to see available tables)")
        raise SystemExit(1)

    # Handle --preview flag
    if preview:

        async def _preview() -> None:
            try:
                table_preview = await service.preview(table, layer=layer)
                echo_export_preview(table_preview)
            except FileNotFoundError as e:
                echo_error(str(e))
                raise SystemExit(1) from None

        asyncio.run(_preview())
        return

    # Parse columns
    column_list = None
    if columns:
        column_list = [c.strip() for c in columns.split(",")]

    # Build export options
    options = ExportOptions(
        format=output_format,  # type: ignore[arg-type]
        output_path=output,
        limit=limit,
        columns=column_list,
    )

    async def _export() -> None:
        result = await service.export(table, layer=layer, options=options)
        echo_export_result(result)
        if not result.success:
            raise SystemExit(1)

    asyncio.run(_export())
