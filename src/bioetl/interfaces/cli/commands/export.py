"""Export commands for BioETL CLI."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

import click

from bioetl.interfaces.cli.commands.domains.shared.click_options import (
    typed_click_argument,
    typed_click_command,
    typed_click_option,
)
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
    from bioetl.composition.control_plane_service_access import (
        get_export_service as _impl,
    )

    return _impl()


@typed_click_command("export")
@typed_click_argument("table", required=False)
@typed_click_option(
    "--list",
    "list_tables",
    is_flag=True,
    help="List all available Delta tables",
)
@typed_click_option(
    "--preview",
    is_flag=True,
    help="Show table schema and sample data",
)
@typed_click_option(
    "--format",
    "-f",
    "output_format",
    type=click.Choice(["csv", "xlsx", "tsv"]),
    default="csv",
    help="Output format (default: csv)",
)
@typed_click_option(
    "--layer",
    "-l",
    type=click.Choice(["silver", "gold"]),
    default="silver",
    help="Medallion layer to export from (default: silver)",
)
@typed_click_option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    help="Output directory (default: data/exports)",
)
@typed_click_option(
    "--limit",
    type=int,
    help="Maximum number of rows to export",
)
@typed_click_option(
    "--columns",
    "-c",
    help="Comma-separated list of columns to include",
)
@typed_click_option(
    "--requester",
    help="Requester identity for governed export audit metadata",
)
@typed_click_option(
    "--role",
    type=click.Choice(["viewer", "investigator", "exporter", "admin"]),
    default="viewer",
    show_default=True,
    help="Governed export role used for redaction policy",
)
@typed_click_option(
    "--filters-hash",
    help="Stable SHA/hash of the query filters used for parity auditing",
)
@typed_click_option(
    "--expires-at",
    help="ISO-8601 expiry timestamp for governed export download semantics",
)
@typed_click_option(
    "--redaction-profile",
    type=click.Choice(["default", "none"]),
    default="default",
    show_default=True,
    help="Export redaction profile; 'none' requires a privileged role",
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
    requester: str | None,
    role: str,
    filters_hash: str | None,
    expires_at: str | None,
    redaction_profile: str,
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
        requester=requester,
        role=role,
        filters_hash=filters_hash,
        expires_at=expires_at,
        redaction_profile=redaction_profile,
    )
    _run_export(service=service, table=resolved_table, layer=layer, options=options)
