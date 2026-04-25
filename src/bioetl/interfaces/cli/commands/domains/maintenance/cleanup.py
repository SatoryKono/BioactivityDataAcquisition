"""Cleanup commands for BioETL CLI.

Implements Bronze layer cleanup per RULES.md retention policy.
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
    echo_cleanup_preview,
    echo_dry_run_prefix,
    echo_info,
    format_bytes,
)

if TYPE_CHECKING:
    from bioetl.application.core.lifecycle.cleanup_service import CleanupPreview
    from bioetl.application.services.bronze_cleanup_service import BronzeCleanupService

__all__ = [
    "bronze_cleanup_command",
    "cleanup_preview_command",
    "get_bronze_cleanup_service",
    "preview_pipeline_cleanup",
]

_CLEANUP_PREVIEW_DOMAIN_ERROR_TITLE = (
    "Maintenance cleanup-preview failed with domain error"
)
_CLEANUP_PREVIEW_UNEXPECTED_ERROR_TITLE = (
    "Unexpected error during maintenance cleanup-preview"
)
_CLEANUP_PREVIEW_INTERRUPTED_MESSAGE = (
    "Maintenance cleanup-preview interrupted by user (Ctrl+C)"
)


def get_bronze_cleanup_service() -> BronzeCleanupService:
    """Load the bronze cleanup service through composition on demand."""
    from bioetl.composition.maintenance_api import (
        get_bronze_cleanup_service as _impl,
    )

    return _impl()


async def preview_pipeline_cleanup(pipeline: str) -> CleanupPreview:
    """Preview pipeline cleanup scope through composition on demand."""
    from bioetl.composition.resources_api import preview_cleanup as _impl

    return await _impl(pipeline)


def _handle_cleanup_failure(
    exc: BaseException,
    *,
    reason_code: str,
    subject_key: str = "target",
    subject_value: str = "bronze",
    domain_error_title: str = "Maintenance bronze-cleanup failed with domain error",
    unexpected_error_title: str = (
        "Unexpected error during maintenance bronze-cleanup"
    ),
    interrupted_message: str = (
        "Maintenance bronze-cleanup interrupted by user (Ctrl+C)"
    ),
) -> None:
    """Handle cleanup command failures with shared CLI policy."""
    handle_cli_execution_failure(
        exc,
        reason_code=reason_code,
        subject_key=subject_key,
        subject_value=subject_value,
        domain_error_title=domain_error_title,
        unexpected_error_title=unexpected_error_title,
        interrupted_message=interrupted_message,
        default_exit_code=ExitCode.FAIL,
    )


@click.command("bronze-cleanup")  # type: ignore[untyped-decorator]
@click.option(  # type: ignore[untyped-decorator]
    "-r",
    "--retention-days",
    default=90,
    help="Remove files older than N days",
)
@click.option(  # type: ignore[untyped-decorator]
    "--dry-run",
    is_flag=True,
    help="Show what would be removed",
)
def bronze_cleanup_command(retention_days: int, dry_run: bool) -> None:
    """Clean up old Bronze files (RULES.md 2.1 retention, default 90 days).

    Examples:

        bioetl maintenance bronze-cleanup

        bioetl maintenance bronze-cleanup --dry-run

        bioetl maintenance bronze-cleanup -r 30

    Args:
        retention_days: Retention days.
        dry_run: Dry run mode flag.
    """
    service = get_bronze_cleanup_service()

    async def _run() -> None:
        if dry_run:
            echo_dry_run_prefix(
                f"Cleanup Bronze files older than {retention_days} days"
            )
        result = await service.cleanup(retention_days=retention_days, dry_run=dry_run)
        action = "Would remove" if dry_run else "Removed"
        echo_info(
            f"{action} {result.files_removed} files ({format_bytes(result.bytes_freed)})"
        )
        echo_info(f"{action} {result.directories_removed} empty directories")

    coro = _run()
    try:
        asyncio.run(coro)
    except BioETLError as exc:
        _handle_cleanup_failure(
            exc,
            reason_code="CLI_MAINTENANCE_BRONZE_CLEANUP_DOMAIN_ERROR",
        )
    except KeyboardInterrupt as exc:
        _handle_cleanup_failure(
            exc,
            reason_code="CLI_MAINTENANCE_BRONZE_CLEANUP_SIGINT",
        )
    except CLI_ENTRYPOINT_TYPED_ERRORS as exc:
        _handle_cleanup_failure(
            exc,
            reason_code="CLI_MAINTENANCE_BRONZE_CLEANUP_UNEXPECTED_ERROR",
        )
    finally:
        if getattr(coro, "cr_frame", None) is not None:
            coro.close()


@click.command("cleanup-preview")  # type: ignore[untyped-decorator]
@click.option(  # type: ignore[untyped-decorator]
    "--pipeline",
    required=True,
    help="Pipeline name to preview (e.g., chembl_activity)",
)
def cleanup_preview_command(pipeline: str) -> None:
    """Preview Silver/Gold cleanup scope for a pipeline (dry-run only).

    Examples:

        bioetl maintenance cleanup-preview --pipeline chembl_activity
    """

    async def _run() -> None:
        preview_result = await preview_pipeline_cleanup(pipeline)
        echo_dry_run_prefix(f"Cleanup preview for pipeline: {pipeline}")
        echo_cleanup_preview(preview_result)

    coro = _run()
    try:
        asyncio.run(coro)
    except BioETLError as exc:
        _handle_cleanup_failure(
            exc,
            reason_code="CLI_MAINTENANCE_CLEANUP_PREVIEW_DOMAIN_ERROR",
            subject_key="pipeline",
            subject_value=pipeline,
            domain_error_title=_CLEANUP_PREVIEW_DOMAIN_ERROR_TITLE,
            unexpected_error_title=_CLEANUP_PREVIEW_UNEXPECTED_ERROR_TITLE,
            interrupted_message=_CLEANUP_PREVIEW_INTERRUPTED_MESSAGE,
        )
    except KeyboardInterrupt as exc:
        _handle_cleanup_failure(
            exc,
            reason_code="CLI_MAINTENANCE_CLEANUP_PREVIEW_SIGINT",
            subject_key="pipeline",
            subject_value=pipeline,
            domain_error_title=_CLEANUP_PREVIEW_DOMAIN_ERROR_TITLE,
            unexpected_error_title=_CLEANUP_PREVIEW_UNEXPECTED_ERROR_TITLE,
            interrupted_message=_CLEANUP_PREVIEW_INTERRUPTED_MESSAGE,
        )
    except CLI_ENTRYPOINT_TYPED_ERRORS as exc:
        _handle_cleanup_failure(
            exc,
            reason_code="CLI_MAINTENANCE_CLEANUP_PREVIEW_UNEXPECTED_ERROR",
            subject_key="pipeline",
            subject_value=pipeline,
            domain_error_title=_CLEANUP_PREVIEW_DOMAIN_ERROR_TITLE,
            unexpected_error_title=_CLEANUP_PREVIEW_UNEXPECTED_ERROR_TITLE,
            interrupted_message=_CLEANUP_PREVIEW_INTERRUPTED_MESSAGE,
        )
    finally:
        if getattr(coro, "cr_frame", None) is not None:
            coro.close()
