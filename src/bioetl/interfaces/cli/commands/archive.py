"""Archive command for BioETL CLI.

Implements table archival to cold storage.
"""

from __future__ import annotations

import asyncio

import click

from bioetl.composition.entrypoints import get_lifecycle_service
from bioetl.domain.exceptions import BioETLError
from bioetl.interfaces.cli.commands.execution_policy import (
    CLI_ENTRYPOINT_TYPED_ERRORS,
)
from bioetl.interfaces.cli.commands.execution_policy import (
    handle_cli_failure as handle_cli_execution_failure,
)
from bioetl.interfaces.cli.exit_codes import ExitCode
from bioetl.interfaces.cli.formatters import echo_info


def _handle_archive_failure(
    exc: BaseException,
    *,
    reason_code: str,
    table: str,
) -> None:
    """Handle archive command failures with shared CLI policy."""
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
