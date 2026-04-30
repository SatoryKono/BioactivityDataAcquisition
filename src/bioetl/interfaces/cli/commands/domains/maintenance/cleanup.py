"""Cleanup commands for BioETL CLI.

Implements Bronze layer cleanup per RULES.md retention policy.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, cast

import click

from bioetl.interfaces.cli.commands.domains.shared.execution_policy import (
    CliBoundaryExecutionPolicy,
    run_async_with_cli_failure_policy,
)
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
    from bioetl.composition.maintenance_api import preview_cleanup as _impl

    impl = cast("Callable[[str], Awaitable[CleanupPreview]]", _impl)
    return await impl(pipeline)


def _cleanup_policy(
    *,
    reason_prefix: str,
    subject_key: str = "target",
    subject_value: str = "bronze",
    domain_error_title: str = "Maintenance bronze-cleanup failed with domain error",
    unexpected_error_title: str = (
        "Unexpected error during maintenance bronze-cleanup"
    ),
    interrupted_message: str = (
        "Maintenance bronze-cleanup interrupted by user (Ctrl+C)"
    ),
) -> CliBoundaryExecutionPolicy:
    """Build the shared CLI boundary policy for cleanup commands."""
    return CliBoundaryExecutionPolicy(
        reason_prefix=reason_prefix,
        subject_key=subject_key,
        subject_value=subject_value,
        domain_error_title=domain_error_title,
        unexpected_error_title=unexpected_error_title,
        interrupted_message=interrupted_message,
    )


@click.command("bronze-cleanup")
@click.option(
    "-r",
    "--retention-days",
    default=90,
    help="Remove files older than N days",
)
@click.option(
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

    run_async_with_cli_failure_policy(
        _run(),
        policy=_cleanup_policy(reason_prefix="CLI_MAINTENANCE_BRONZE_CLEANUP"),
    )


@click.command("cleanup-preview")
@click.option(
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

    run_async_with_cli_failure_policy(
        _run(),
        policy=_cleanup_policy(
            reason_prefix="CLI_MAINTENANCE_CLEANUP_PREVIEW",
            subject_key="pipeline",
            subject_value=pipeline,
            domain_error_title=_CLEANUP_PREVIEW_DOMAIN_ERROR_TITLE,
            unexpected_error_title=_CLEANUP_PREVIEW_UNEXPECTED_ERROR_TITLE,
            interrupted_message=_CLEANUP_PREVIEW_INTERRUPTED_MESSAGE,
        ),
    )
