"""Archive command for BioETL CLI.

Implements table archival to cold storage.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import click

from bioetl.interfaces.cli.commands.domains.shared.execution_policy import (
    CliBoundaryExecutionPolicy,
    run_async_with_cli_failure_policy,
)
from bioetl.interfaces.cli.formatters import echo_info

if TYPE_CHECKING:
    from bioetl.application.services.medallion_lifecycle import (
        MedallionLifecycleService,
    )

__all__ = [
    "archive_command",
    "get_lifecycle_service",
]


def get_lifecycle_service() -> MedallionLifecycleService:
    """Load the lifecycle service through composition on demand."""
    from bioetl.composition.maintenance_api import get_lifecycle_service as _impl

    return _impl()


def _archive_policy(table: str) -> CliBoundaryExecutionPolicy:
    """Build the shared CLI boundary policy for archive commands."""
    return CliBoundaryExecutionPolicy(
        reason_prefix="CLI_MAINTENANCE_ARCHIVE",
        subject_key="table",
        subject_value=table,
        domain_error_title="Maintenance archive failed with domain error",
        unexpected_error_title="Unexpected error during maintenance archive",
        interrupted_message="Maintenance archive interrupted by user (Ctrl+C)",
    )


@click.command("archive")
@click.argument("table")
@click.argument("target_path")
@click.option(
    "--remove-source",
    is_flag=True,
    help="Remove source table after archiving",
)
def archive_command(table: str, target_path: str, remove_source: bool) -> None:
    """Archive Delta table to cold storage.

    TABLE: Table name to archive

    TARGET_PATH: Destination path for archive

    Examples:

        bioetl maintenance archive chembl.activity /archive/chembl

        bioetl maintenance archive chembl.activity /archive/chembl --remove-source

    Args:
        table: Table.
        target_path: File path for target.
        remove_source: Whether to remove source.
    """
    lifecycle = get_lifecycle_service()

    async def _run() -> None:
        files_archived = await lifecycle.archive(
            table=table,
            target_path=target_path,
            remove_source=remove_source,
        )

        echo_info(f"Archived {files_archived} files to {target_path}")

    run_async_with_cli_failure_policy(_run(), policy=_archive_policy(table))
