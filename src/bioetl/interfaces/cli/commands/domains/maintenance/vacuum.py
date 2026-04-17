"""Vacuum commands for BioETL CLI.

Implements vacuum operations for Delta tables storage reclamation.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import click

from bioetl.domain.exceptions import BioETLError
from bioetl.interfaces.cli.commands.domains.shared.execution_policy import (
    CLI_ENTRYPOINT_TYPED_ERRORS,
)
from bioetl.interfaces.cli.commands.domains.shared.execution_policy import (
    handle_cli_failure as handle_cli_execution_failure,
)
from bioetl.interfaces.cli.exit_codes import ExitCode
from bioetl.interfaces.cli.formatters import (
    echo_dry_run_prefix,
    echo_info,
    echo_vacuum_all_summary,
    echo_vacuum_result,
)

if TYPE_CHECKING:
    from bioetl.application.services.medallion_lifecycle import (
        MedallionLifecycleService,
    )
    from bioetl.application.services.vacuum_service import VacuumService

__all__ = [
    "get_lifecycle_service",
    "get_vacuum_service",
    "vacuum_all_command",
    "vacuum_command",
]

_VACUUM_DOMAIN_ERROR_TITLE = "Maintenance vacuum failed with domain error"
_VACUUM_UNEXPECTED_ERROR_TITLE = "Unexpected error during maintenance vacuum"
_VACUUM_INTERRUPTED_MESSAGE = "Maintenance vacuum interrupted by user (Ctrl+C)"

_VACUUM_ALL_DOMAIN_ERROR_TITLE = "Maintenance vacuum-all failed with domain error"
_VACUUM_ALL_UNEXPECTED_ERROR_TITLE = "Unexpected error during maintenance vacuum-all"
_VACUUM_ALL_INTERRUPTED_MESSAGE = (
    "Maintenance vacuum-all interrupted by user (Ctrl+C)"
)


def get_lifecycle_service() -> MedallionLifecycleService:
    """Load the lifecycle service through composition on demand."""
    from bioetl.composition.resources_api import get_lifecycle_service as _impl

    return _impl()


def get_vacuum_service() -> VacuumService:
    """Load the vacuum service through composition on demand."""
    from bioetl.composition.maintenance_api import get_vacuum_service as _impl

    return _impl()


def _handle_maintenance_failure(
    exc: BaseException,
    *,
    reason_code: str,
    target: str,
    domain_error_title: str,
    unexpected_error_title: str,
    interrupted_message: str,
) -> None:
    """Handle maintenance command failures with shared CLI policy.

    Args:
        exc: Exception caught at the CLI command boundary.
        reason_code: Machine-readable code for the failure (e.g., 'CLI_MAINTENANCE_VACUUM_DOMAIN_ERROR').
        target: Target identifier (e.g., table name or layer) used in error context.
        domain_error_title: Human-readable title for BioETLError failures.
        unexpected_error_title: Human-readable title for unexpected exception failures.
        interrupted_message: Message displayed when KeyboardInterrupt is caught.
    """
    handle_cli_execution_failure(
        exc,
        reason_code=reason_code,
        subject_key="target",
        subject_value=target,
        domain_error_title=domain_error_title,
        unexpected_error_title=unexpected_error_title,
        interrupted_message=interrupted_message,
        default_exit_code=ExitCode.FAIL,
    )


@click.command("vacuum")  # type: ignore[untyped-decorator]
@click.argument("table")  # type: ignore[untyped-decorator]
@click.option(  # type: ignore[untyped-decorator]
    "--retention-days",
    "-r",
    default=7,
    help="Minimum age of files to remove (days)",
)
@click.option(  # type: ignore[untyped-decorator]
    "--dry-run",
    is_flag=True,
    help="Show what would be removed without removing",
)
def vacuum_command(table: str, retention_days: int, dry_run: bool) -> None:
    """Vacuum Delta table to reclaim storage space.

    TABLE: Table name in format "provider.entity" (e.g., chembl.activity)

    Examples:

        bioetl maintenance vacuum chembl.activity

        bioetl maintenance vacuum chembl.activity --dry-run

        bioetl maintenance vacuum chembl.activity -r 30

    Args:
        table: Table.
        retention_days: Retention days.
        dry_run: Dry run mode flag.
    """
    lifecycle = get_lifecycle_service()

    async def _run() -> None:
        if dry_run:
            echo_dry_run_prefix(f"Would vacuum {table} (retention: {retention_days}d)")

        files_removed = await lifecycle.vacuum(
            table=table,
            retention_days=retention_days,
            dry_run=dry_run,
        )

        if dry_run:
            echo_info(f"Would remove {files_removed} files")
        else:
            echo_info(f"Removed {files_removed} files")

    coro = _run()
    try:
        asyncio.run(coro)
    except BioETLError as exc:
        _handle_maintenance_failure(
            exc,
            reason_code="CLI_MAINTENANCE_VACUUM_DOMAIN_ERROR",
            target=table,
            domain_error_title=_VACUUM_DOMAIN_ERROR_TITLE,
            unexpected_error_title=_VACUUM_UNEXPECTED_ERROR_TITLE,
            interrupted_message=_VACUUM_INTERRUPTED_MESSAGE,
        )
    except KeyboardInterrupt as exc:
        _handle_maintenance_failure(
            exc,
            reason_code="CLI_MAINTENANCE_VACUUM_SIGINT",
            target=table,
            domain_error_title=_VACUUM_DOMAIN_ERROR_TITLE,
            unexpected_error_title=_VACUUM_UNEXPECTED_ERROR_TITLE,
            interrupted_message=_VACUUM_INTERRUPTED_MESSAGE,
        )
    except CLI_ENTRYPOINT_TYPED_ERRORS as exc:
        _handle_maintenance_failure(
            exc,
            reason_code="CLI_MAINTENANCE_VACUUM_UNEXPECTED_ERROR",
            target=table,
            domain_error_title=_VACUUM_DOMAIN_ERROR_TITLE,
            unexpected_error_title=_VACUUM_UNEXPECTED_ERROR_TITLE,
            interrupted_message=_VACUUM_INTERRUPTED_MESSAGE,
        )
    finally:
        if getattr(coro, "cr_frame", None) is not None:
            coro.close()


@click.command("vacuum-all")  # type: ignore[untyped-decorator]
@click.option(  # type: ignore[untyped-decorator]
    "--retention-days",
    "-r",
    default=7,
    help="Minimum age of files to remove (days)",
)
@click.option(  # type: ignore[untyped-decorator]
    "--dry-run",
    is_flag=True,
    help="Show what would be removed without removing",
)
@click.option(  # type: ignore[untyped-decorator]
    "--layer",
    type=click.Choice(["all", "silver", "gold"]),
    default="all",
    help="Which layer to vacuum (default: all)",
)
def vacuum_all_command(retention_days: int, dry_run: bool, layer: str) -> None:
    """Vacuum all Delta tables to reclaim storage space.

    Runs VACUUM on all registered Silver and Gold tables.

    Examples:

        bioetl maintenance vacuum-all

        bioetl maintenance vacuum-all --dry-run

        bioetl maintenance vacuum-all -r 30

        bioetl maintenance vacuum-all --layer silver

    Args:
        retention_days: Retention days.
        dry_run: Dry run mode flag.
        layer: Layer.
    """
    service = get_vacuum_service()
    tables_to_vacuum = service.collect_tables(layer)

    if not tables_to_vacuum:
        echo_info("No tables found to vacuum.")
        return

    async def _run() -> None:
        result = await service.vacuum_all(
            tables=tables_to_vacuum,
            retention_days=retention_days,
            dry_run=dry_run,
        )

        for table_result in result.results:
            echo_vacuum_result(table_result, dry_run)

        echo_vacuum_all_summary(result)

    coro = _run()
    try:
        asyncio.run(coro)
    except BioETLError as exc:
        _handle_maintenance_failure(
            exc,
            reason_code="CLI_MAINTENANCE_VACUUM_ALL_DOMAIN_ERROR",
            target=layer,
            domain_error_title=_VACUUM_ALL_DOMAIN_ERROR_TITLE,
            unexpected_error_title=_VACUUM_ALL_UNEXPECTED_ERROR_TITLE,
            interrupted_message=_VACUUM_ALL_INTERRUPTED_MESSAGE,
        )
    except KeyboardInterrupt as exc:
        _handle_maintenance_failure(
            exc,
            reason_code="CLI_MAINTENANCE_VACUUM_ALL_SIGINT",
            target=layer,
            domain_error_title=_VACUUM_ALL_DOMAIN_ERROR_TITLE,
            unexpected_error_title=_VACUUM_ALL_UNEXPECTED_ERROR_TITLE,
            interrupted_message=_VACUUM_ALL_INTERRUPTED_MESSAGE,
        )
    except CLI_ENTRYPOINT_TYPED_ERRORS as exc:
        _handle_maintenance_failure(
            exc,
            reason_code="CLI_MAINTENANCE_VACUUM_ALL_UNEXPECTED_ERROR",
            target=layer,
            domain_error_title=_VACUUM_ALL_DOMAIN_ERROR_TITLE,
            unexpected_error_title=_VACUUM_ALL_UNEXPECTED_ERROR_TITLE,
            interrupted_message=_VACUUM_ALL_INTERRUPTED_MESSAGE,
        )
    finally:
        if getattr(coro, "cr_frame", None) is not None:
            coro.close()
