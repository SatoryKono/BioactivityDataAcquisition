"""Shared helpers for the export CLI command."""

from __future__ import annotations

import sys
from collections.abc import Callable, Coroutine
from pathlib import Path
from typing import Literal, Protocol, cast

from bioetl.application.services.export_models import (
    ExportOptions,
    ExportRedactionProfile,
    ExportResult,
    ExportRole,
    TableInfo,
    TablePreview,
)
from bioetl.interfaces.cli.commands.domains.shared.execution_policy import (
    CliBoundaryExecutionPolicy,
    run_async_with_cli_failure_policy,
    run_sync_with_cli_failure_policy,
)
from bioetl.interfaces.cli.exit_codes import ExitCode
from bioetl.interfaces.cli.formatters import (
    echo_error,
    echo_export_preview,
    echo_export_result,
    echo_info,
    echo_table_list,
)

__all__ = [
    "ExportFormat",
    "_ExportCommandService",
    "_build_export_options",
    "_list_tables_or_exit",
    "_require_table_argument",
    "_run_export",
    "_run_preview",
]

ExportFormat = Literal["csv", "xlsx", "tsv"]


def _scrub_parent_package_binding() -> None:
    """Keep helper module importable as a submodule, not a package-root seam."""
    package_name, _, module_name = __name__.rpartition(".")
    package = sys.modules.get(package_name)
    module = sys.modules.get(__name__)
    if (
        package is not None
        and module is not None
        and getattr(package, module_name, None) is module
    ):
        delattr(package, module_name)


_scrub_parent_package_binding()


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


def _export_policy(
    *,
    table: str,
    reason_prefix: str,
    domain_error_title: str,
    unexpected_error_title: str,
) -> CliBoundaryExecutionPolicy:
    """Build the shared CLI boundary policy for export helpers."""
    return CliBoundaryExecutionPolicy(
        reason_prefix=reason_prefix,
        subject_key="table",
        subject_value=table,
        domain_error_title=domain_error_title,
        unexpected_error_title=unexpected_error_title,
        interrupted_message="Export interrupted by user (Ctrl+C)",
    )


def _run_export_async[T](
    coro: Coroutine[object, object, T],
    *,
    table: str,
    reason_prefix: str,
    domain_error_title: str,
    unexpected_error_title: str,
    handle_file_not_found: bool = False,
) -> T | None:
    """Run an async export coroutine with shared CLI exception handling."""
    try:
        return run_async_with_cli_failure_policy(
            coro,
            policy=_export_policy(
                table=table,
                reason_prefix=reason_prefix,
                domain_error_title=domain_error_title,
                unexpected_error_title=unexpected_error_title,
            ),
            passthrough_exception_types=(
                (FileNotFoundError,) if handle_file_not_found else ()
            ),
        )
    except FileNotFoundError as exc:
        if handle_file_not_found:
            echo_error(str(exc))
            raise SystemExit(ExitCode.FAIL) from None
        raise


def _run_export_sync[T](
    fn: Callable[[], T],
    *,
    table: str,
    reason_prefix: str,
    domain_error_title: str,
    unexpected_error_title: str,
) -> T | None:
    """Run a sync export callable with shared CLI exception handling."""
    return run_sync_with_cli_failure_policy(
        fn,
        policy=_export_policy(
            table=table,
            reason_prefix=reason_prefix,
            domain_error_title=domain_error_title,
            unexpected_error_title=unexpected_error_title,
        ),
    )


def _resolve_list_layer(layer: str) -> str:
    """Map CLI layer value to service list scope."""
    return layer if layer != "silver" else "all"


def _require_table_argument(table: str | None) -> str:
    """Validate table argument for non-list operations."""
    if table:
        return table
    echo_error("TABLE argument is required (or use --list to see available tables)")
    raise SystemExit(ExitCode.FAIL)


def _parse_columns(columns: str | None) -> list[str] | None:
    """Parse comma-separated columns from CLI option."""
    if not columns:
        return None
    return [column.strip() for column in columns.split(",")]


def _parse_export_format(output_format: str) -> ExportFormat:
    """Parse output format value into strict ExportFormat literal."""
    if output_format in {"csv", "xlsx", "tsv"}:
        return cast("ExportFormat", output_format)
    return "csv"


def _parse_export_role(role: str) -> ExportRole:
    """Parse a CLI role into the export authorization literal."""
    if role in {"viewer", "investigator", "exporter", "admin"}:
        return cast("ExportRole", role)
    return "viewer"


def _parse_redaction_profile(profile: str) -> ExportRedactionProfile:
    """Parse a CLI redaction profile into the supported literal."""
    if profile in {"default", "none"}:
        return cast("ExportRedactionProfile", profile)
    return "default"


def _build_export_options(
    output_format: str,
    output: Path | None,
    limit: int | None,
    columns: str | None,
    *,
    requester: str | None = None,
    role: str = "viewer",
    filters_hash: str | None = None,
    expires_at: str | None = None,
    redaction_profile: str = "default",
) -> ExportOptions:
    """Build validated ExportOptions from CLI parameters."""
    return ExportOptions(
        format=_parse_export_format(output_format),
        output_path=output,
        limit=limit,
        columns=_parse_columns(columns),
        requester=requester,
        role=_parse_export_role(role),
        filters_hash=filters_hash,
        expires_at=expires_at,
        redaction_profile=_parse_redaction_profile(redaction_profile),
    )


def _run_preview(
    service: _ExportCommandService,
    table: str,
    layer: str,
) -> None:
    """Execute async preview operation from sync CLI context."""

    async def _preview() -> TablePreview:
        return await service.preview(table, layer=layer)

    table_preview = _run_export_async(
        _preview(),
        table=table,
        reason_prefix="CLI_EXPORT_PREVIEW",
        domain_error_title="Export preview failed with domain error",
        unexpected_error_title="Unexpected error during export preview",
        handle_file_not_found=True,
    )
    if table_preview is not None:
        echo_export_preview(table_preview)


def _run_export(
    service: _ExportCommandService,
    table: str,
    layer: str,
    options: ExportOptions,
) -> None:
    """Execute async export operation from sync CLI context."""

    async def _export() -> ExportResult:
        return await service.export(table, layer=layer, options=options)

    result = _run_export_async(
        _export(),
        table=table,
        reason_prefix="CLI_EXPORT_RUN",
        domain_error_title="Export failed with domain error",
        unexpected_error_title="Unexpected error during export",
    )
    if result is None:
        return
    echo_export_result(result)
    if not result.success:
        raise SystemExit(ExitCode.FAIL)


def _list_tables_or_exit(
    service: _ExportCommandService,
    *,
    layer: str,
) -> None:
    """Handle table listing mode."""
    tables = _run_export_sync(
        lambda: service.list_tables(layer=_resolve_list_layer(layer)),
        table=f"<list:{layer}>",
        reason_prefix="CLI_EXPORT_LIST",
        domain_error_title="Export table listing failed with domain error",
        unexpected_error_title="Unexpected error during export table listing",
    )
    if tables is None:
        return
    if not tables:
        echo_info("No Delta tables found.")
        return
    echo_table_list(tables)
