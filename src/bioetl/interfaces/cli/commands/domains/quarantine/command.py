"""Quarantine management commands for BioETL CLI.

Implements quarantine inspection and management commands.
Provides error recovery dashboard functionality (ERR-001).
"""

from __future__ import annotations

import click

SILVER_FILTER_ERROR_CODE = "FILTERED_OUT_SILVER"


def get_quarantine_manager(pipeline: str) -> object:
    """Load the quarantine manager through composition on demand."""
    from bioetl.composition.resources_api import get_quarantine_manager as _impl

    return _impl(pipeline)


def get_run_manifest_service() -> object:
    """Load the run manifest service through composition on demand."""
    from bioetl.composition.control_plane_api import (
        get_run_manifest_service as _impl,
    )

    return _impl()


def get_quarantine_service() -> object:
    """Load the quarantine service through composition on demand."""
    from bioetl.composition.health_api import get_quarantine_service as _impl

    return _impl()


@click.group()  # type: ignore[untyped-decorator]
def quarantine() -> None:
    """Manage quarantine (failed records)."""


@quarantine.command("inspect")  # type: ignore[untyped-decorator]
@click.option(  # type: ignore[untyped-decorator]
    "--pipeline", required=True, help="Pipeline name"
)
@click.option(  # type: ignore[untyped-decorator]
    "--limit", type=int, default=100, help="Maximum records to show"
)
@click.option(  # type: ignore[untyped-decorator]
    "--error-code", help="Filter by error code"
)
@click.option(  # type: ignore[untyped-decorator]
    "--run-id",
    help="Scope inspection to one pipeline run ID",
)
@click.option(  # type: ignore[untyped-decorator]
    "--silver-filter-only",
    is_flag=True,
    help="Shortcut for --error-code FILTERED_OUT_SILVER",
)
def quarantine_inspect(
    pipeline: str,
    limit: int,
    error_code: str | None,
    run_id: str | None,
    silver_filter_only: bool,
) -> None:
    """Inspect quarantined records for a pipeline."""
    from bioetl.interfaces.cli.commands.domains.quarantine.support import (
        _inspect_quarantine,
    )

    resolved_error_code = SILVER_FILTER_ERROR_CODE if silver_filter_only else error_code
    _inspect_quarantine(
        get_quarantine_manager(pipeline),
        pipeline=pipeline,
        limit=limit,
        error_code=resolved_error_code,
        run_id=run_id,
    )


@quarantine.command("stats")  # type: ignore[untyped-decorator]
@click.option(  # type: ignore[untyped-decorator]
    "--pipeline", required=True, help="Pipeline name"
)
@click.option(  # type: ignore[untyped-decorator]
    "--json", "output_json", is_flag=True, help="Output as JSON"
)
@click.option(  # type: ignore[untyped-decorator]
    "--error-code", help="Scope stats to one error code"
)
@click.option(  # type: ignore[untyped-decorator]
    "--run-id",
    help="Scope stats to one pipeline run ID",
)
@click.option(  # type: ignore[untyped-decorator]
    "--silver-filter-only",
    is_flag=True,
    help="Shortcut for --error-code FILTERED_OUT_SILVER",
)
@click.option(  # type: ignore[untyped-decorator]
    "--group-by",
    type=click.Choice(
        [
            "reason-code",
            "field",
            "rule-type",
            "operator",
            "reason-code-field",
            "reason-signature",
        ],
        case_sensitive=False,
    ),
    help="Focused Silver reject grouping for operator triage",
)
@click.option(  # type: ignore[untyped-decorator]
    "--top",
    type=int,
    default=10,
    show_default=True,
    help="Maximum grouping entries to display",
)
def quarantine_stats(
    pipeline: str,
    output_json: bool,
    error_code: str | None,
    run_id: str | None,
    silver_filter_only: bool,
    group_by: str | None,
    top: int,
) -> None:
    """Show quarantine statistics dashboard for a pipeline."""
    from bioetl.interfaces.cli.commands.domains.quarantine.support import (
        _show_quarantine_stats,
    )

    resolved_error_code = SILVER_FILTER_ERROR_CODE if silver_filter_only else error_code
    _show_quarantine_stats(
        get_quarantine_manager(pipeline),
        pipeline=pipeline,
        output_json=output_json,
        error_code=resolved_error_code,
        top=top,
        group_by=group_by,
        run_id=run_id,
        run_manifest_service=get_run_manifest_service() if run_id else None,
    )


@quarantine.command("replay")  # type: ignore[untyped-decorator]
@click.option(  # type: ignore[untyped-decorator]
    "--pipeline", required=True, help="Pipeline name"
)
@click.option(  # type: ignore[untyped-decorator]
    "--error-code", help="Filter by error code"
)
@click.option(  # type: ignore[untyped-decorator]
    "--max-age-days", type=int, default=7, help="Max age of records to replay"
)
@click.option(  # type: ignore[untyped-decorator]
    "--dry-run", is_flag=True, help="Show records without replaying"
)
def quarantine_replay(
    pipeline: str,
    error_code: str | None,
    max_age_days: int,
    dry_run: bool,
) -> None:
    """Replay (retry) quarantined records."""
    from bioetl.interfaces.cli.commands.domains.quarantine.support import (
        _replay_quarantine,
    )

    _replay_quarantine(
        get_quarantine_service(),
        pipeline=pipeline,
        error_code=error_code,
        max_age_days=max_age_days,
        dry_run=dry_run,
    )


@quarantine.command("purge")  # type: ignore[untyped-decorator]
@click.option(  # type: ignore[untyped-decorator]
    "--pipeline", required=True, help="Pipeline name"
)
@click.option(  # type: ignore[untyped-decorator]
    "--older-than-days", type=int, default=30, help="Delete records older than N days"
)
@click.option(  # type: ignore[untyped-decorator]
    "--dry-run", is_flag=True, help="Show count without deleting"
)
@click.option(  # type: ignore[untyped-decorator]
    "--force", is_flag=True, help="Skip confirmation prompt"
)
def quarantine_purge(
    pipeline: str,
    older_than_days: int,
    dry_run: bool,
    force: bool,
) -> None:
    """Purge old quarantine records."""
    from bioetl.interfaces.cli.commands.domains.quarantine.support import (
        _purge_quarantine,
    )

    _purge_quarantine(
        get_quarantine_service(),
        pipeline=pipeline,
        older_than_days=older_than_days,
        dry_run=dry_run,
        force=force,
    )


@quarantine.command("resolve")  # type: ignore[untyped-decorator]
@click.option(  # type: ignore[untyped-decorator]
    "--pipeline", required=True, help="Pipeline name"
)
@click.option(  # type: ignore[untyped-decorator]
    "--payload-hash", required=True, help="Payload hash of record to resolve"
)
@click.option(  # type: ignore[untyped-decorator]
    "--status", type=click.Choice(["IGNORED", "REPROCESSED"]), default="IGNORED"
)
def quarantine_resolve(pipeline: str, payload_hash: str, status: str) -> None:
    """Mark a quarantine record as resolved."""
    from bioetl.interfaces.cli.commands.domains.quarantine.support import (
        _resolve_quarantine_record,
    )

    _resolve_quarantine_record(
        get_quarantine_service(),
        pipeline=pipeline,
        payload_hash=payload_hash,
        status=status,
    )


COMMANDS = (
    quarantine_inspect,
    quarantine_purge,
    quarantine_replay,
    quarantine_resolve,
    quarantine_stats,
)

__all__ = [
    "get_quarantine_manager",
    "get_quarantine_service",
    "get_run_manifest_service",
    "quarantine",
]
