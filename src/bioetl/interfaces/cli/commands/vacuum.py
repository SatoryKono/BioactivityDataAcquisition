"""Vacuum commands for BioETL CLI.

Implements vacuum operations for Delta tables storage reclamation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import click

from bioetl.interfaces.cli.commands.domains.maintenance import service_access
from bioetl.interfaces.cli.commands.domains.shared.click_options import (
    typed_click_argument,
    typed_click_command,
    typed_click_option,
)
from bioetl.interfaces.cli.commands.domains.shared.execution_policy import (
    CliBoundaryExecutionPolicy,
    build_target_cli_boundary_policy,
    run_async_with_cli_failure_policy,
)
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
_VACUUM_ALL_INTERRUPTED_MESSAGE = "Maintenance vacuum-all interrupted by user (Ctrl+C)"


def get_lifecycle_service() -> MedallionLifecycleService:
    """Load the lifecycle service through the owner-only maintenance seam."""
    return service_access.get_lifecycle_service()


def get_vacuum_service() -> VacuumService:
    """Load the vacuum service through the owner-only maintenance seam."""
    return service_access.get_vacuum_service()


def _maintenance_policy(
    *,
    reason_prefix: str,
    target: str,
    domain_error_title: str,
    unexpected_error_title: str,
    interrupted_message: str,
) -> CliBoundaryExecutionPolicy:
    """Build the shared CLI boundary policy for maintenance vacuum commands."""
    return build_target_cli_boundary_policy(
        reason_prefix=reason_prefix,
        target=target,
        domain_error_title=domain_error_title,
        unexpected_error_title=unexpected_error_title,
        interrupted_message=interrupted_message,
    )


@typed_click_command("vacuum")
@typed_click_argument("table")
@typed_click_option(
    "--retention-days",
    "-r",
    default=7,
    help="Minimum age of files to remove (days)",
)
@typed_click_option(
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

    run_async_with_cli_failure_policy(
        _run(),
        policy=_maintenance_policy(
            reason_prefix="CLI_MAINTENANCE_VACUUM",
            target=table,
            domain_error_title=_VACUUM_DOMAIN_ERROR_TITLE,
            unexpected_error_title=_VACUUM_UNEXPECTED_ERROR_TITLE,
            interrupted_message=_VACUUM_INTERRUPTED_MESSAGE,
        ),
    )


@typed_click_command("vacuum-all")
@typed_click_option(
    "--retention-days",
    "-r",
    default=7,
    help="Minimum age of files to remove (days)",
)
@typed_click_option(
    "--dry-run",
    is_flag=True,
    help="Show what would be removed without removing",
)
@typed_click_option(
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

    run_async_with_cli_failure_policy(
        _run(),
        policy=_maintenance_policy(
            reason_prefix="CLI_MAINTENANCE_VACUUM_ALL",
            target=layer,
            domain_error_title=_VACUUM_ALL_DOMAIN_ERROR_TITLE,
            unexpected_error_title=_VACUUM_ALL_UNEXPECTED_ERROR_TITLE,
            interrupted_message=_VACUUM_ALL_INTERRUPTED_MESSAGE,
        ),
    )
