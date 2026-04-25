"""Archive command for BioETL CLI.

Implements table archival to cold storage.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import TYPE_CHECKING, cast

import click

from bioetl.domain.exceptions import BioETLError
from bioetl.interfaces.cli.commands.domains.shared.execution_policy import (
    CLI_ENTRYPOINT_TYPED_ERRORS,
)
from bioetl.interfaces.cli.commands.domains.shared.execution_policy import (
    handle_cli_failure as handle_cli_execution_failure,
)
from bioetl.interfaces.cli.exit_codes import ExitCode
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
    from bioetl.composition.resources_api import get_lifecycle_service as _impl

    impl = cast("Callable[[], MedallionLifecycleService]", _impl)
    return impl()


def _handle_archive_failure(
    exc: BaseException,
    *,
    reason_code: str,
    table: str,
) -> None:
    """Handle archive command failures with shared CLI policy.

    Args:
        exc: Exception caught at the CLI command boundary.
        reason_code: Machine-readable code for the failure (e.g., 'CLI_MAINTENANCE_ARCHIVE_DOMAIN_ERROR').
        table: Table name used as subject value in the structured error context.
    """
    handle_cli_execution_failure(
        exc,
        reason_code=reason_code,
        subject_key="table",
        subject_value=table,
        domain_error_title="Maintenance archive failed with domain error",
        unexpected_error_title="Unexpected error during maintenance archive",
        interrupted_message="Maintenance archive interrupted by user (Ctrl+C)",
        default_exit_code=ExitCode.FAIL,
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

    coro = _run()
    try:
        asyncio.run(coro)
    except BioETLError as exc:
        _handle_archive_failure(
            exc,
            reason_code="CLI_MAINTENANCE_ARCHIVE_DOMAIN_ERROR",
            table=table,
        )
    except KeyboardInterrupt as exc:
        _handle_archive_failure(
            exc,
            reason_code="CLI_MAINTENANCE_ARCHIVE_SIGINT",
            table=table,
        )
    except CLI_ENTRYPOINT_TYPED_ERRORS as exc:
        _handle_archive_failure(
            exc,
            reason_code="CLI_MAINTENANCE_ARCHIVE_UNEXPECTED_ERROR",
            table=table,
        )
    finally:
        if getattr(coro, "cr_frame", None) is not None:
            coro.close()
