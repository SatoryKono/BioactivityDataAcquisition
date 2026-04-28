"""Shared helpers for the export CLI command."""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Coroutine
from pathlib import Path
from typing import Literal, Protocol, TypeVar, cast

from bioetl.application.services import (
    ExportOptions,
    ExportResult,
    TableInfo,
    TablePreview,
)
from bioetl.domain.exceptions import BioETLError
from bioetl.interfaces.cli.commands.domains.shared.execution_policy import (
    CLI_ENTRYPOINT_TYPED_ERRORS,
)
from bioetl.interfaces.cli.commands.domains.shared.execution_policy import (
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
_T = TypeVar("_T")


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


def _run_export_async[T](
    coro: Coroutine[object, object, _T],
    *,
    table: str,
    reason_prefix: str,
    domain_error_title: str,
    unexpected_error_title: str,
    handle_file_not_found: bool = False,
) -> _T | None:
    """Run an async export coroutine with shared CLI exception handling."""
    try:
        return asyncio.run(coro)
    except FileNotFoundError as exc:
        if handle_file_not_found:
            echo_error(str(exc))
            raise SystemExit(ExitCode.FAIL) from None
        raise
    except BioETLError as exc:
        _handle_export_failure(
            exc,
            reason_code=f"{reason_prefix}_DOMAIN_ERROR",
            table=table,
            domain_error_title=domain_error_title,
            unexpected_error_title=unexpected_error_title,
        )
    except KeyboardInterrupt as exc:
        _handle_export_failure(
            exc,
            reason_code=f"{reason_prefix}_SIGINT",
            table=table,
            domain_error_title=domain_error_title,
            unexpected_error_title=unexpected_error_title,
        )
    except CLI_ENTRYPOINT_TYPED_ERRORS as exc:
        _handle_export_failure(
            exc,
            reason_code=f"{reason_prefix}_UNEXPECTED_ERROR",
            table=table,
            domain_error_title=domain_error_title,
            unexpected_error_title=unexpected_error_title,
        )
    finally:
        if getattr(coro, "cr_frame", None) is not None:
            coro.close()
    return None


def _run_export_sync[T](
    fn: Callable[[], _T],
    *,
    table: str,
    reason_prefix: str,
    domain_error_title: str,
    unexpected_error_title: str,
) -> _T | None:
    """Run a sync export callable with shared CLI exception handling."""
    try:
        return fn()
    except BioETLError as exc:
        _handle_export_failure(
            exc,
            reason_code=f"{reason_prefix}_DOMAIN_ERROR",
            table=table,
            domain_error_title=domain_error_title,
            unexpected_error_title=unexpected_error_title,
        )
    except KeyboardInterrupt as exc:
        _handle_export_failure(
            exc,
            reason_code=f"{reason_prefix}_SIGINT",
            table=table,
            domain_error_title=domain_error_title,
            unexpected_error_title=unexpected_error_title,
        )
    except CLI_ENTRYPOINT_TYPED_ERRORS as exc:
        _handle_export_failure(
            exc,
            reason_code=f"{reason_prefix}_UNEXPECTED_ERROR",
            table=table,
            domain_error_title=domain_error_title,
            unexpected_error_title=unexpected_error_title,
        )
    return None


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


def _build_export_options(
    output_format: str,
    output: Path | None,
    limit: int | None,
    columns: str | None,
) -> ExportOptions:
    """Build validated ExportOptions from CLI parameters."""
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
