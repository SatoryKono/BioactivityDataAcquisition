"""Click entrypoint builder for the run CLI command."""

from __future__ import annotations

from collections.abc import Callable

import click


def build_run_click_command(
    *,
    validate_pipeline_name: Callable[..., object],
    default_health_server_port: int,
    run_callback: Callable[..., None],
) -> click.Command:
    """Build the canonical Click command object for ``bioetl run``."""

    @click.command()
    @click.option(
        "--pipeline",
        callback=validate_pipeline_name,
        required=True,
        help="Pipeline to run",
    )
    @click.option(
        "--run-type",
        type=click.Choice(["incremental", "backfill", "rebuild"]),
        default="incremental",
        help="Type of run",
    )
    @click.option("--resume", is_flag=True, help="Resume from last checkpoint")
    @click.option(
        "--start-offset",
        type=int,
        default=None,
        help="Start extraction from specific record offset (skips checkpoint). "
        "Use after crash to resume from known position.",
    )
    @click.option("--limit", type=int, help="Maximum number of records to process")
    @click.option(
        "--input-csv",
        type=click.Path(exists=True),
        help="Path to CSV file with filter IDs",
    )
    @click.option(
        "--filter-column",
        type=str,
        help="Column name in CSV containing filter IDs (default: 'id')",
    )
    @click.option(
        "--filter-field",
        type=str,
        help="API field name to filter by (default: 'molecule_chembl_id')",
    )
    @click.option(
        "--dry-run",
        is_flag=True,
        help="Preview cleanup without execution (for rebuild/backfill)",
    )
    @click.option(
        "--yes",
        "-y",
        is_flag=True,
        help="Skip confirmation prompt for rebuild/backfill",
    )
    @click.option(
        "--vacuum-after-run",
        is_flag=True,
        default=None,
        help="Run VACUUM on Delta tables after successful run (overrides YAML config)",
    )
    @click.option(
        "--vacuum-retention-days",
        type=int,
        default=None,
        help="Minimum age of files to remove during VACUUM (days, overrides YAML config)",
    )
    @click.option(
        "--debug",
        is_flag=True,
        help="Enable DEBUG level logging for detailed output",
    )
    @click.option(
        "--health-server/--no-health-server",
        "health_server",
        default=True,
        help="Enable/disable HTTP health server during execution.",
        show_default=True,
    )
    @click.option(
        "--health-port",
        type=int,
        default=default_health_server_port,
        help="Port for the HTTP health server.",
        show_default=True,
    )
    @click.option(
        "--use-cached-bronze/--no-cached-bronze",
        "use_cached_bronze",
        default=False,
        help="Load data from Bronze cache instead of API",
        show_default=True,
    )
    @click.option(
        "--cached-bronze-date",
        type=str,
        default=None,
        help="Filter Bronze cache by date (YYYY-MM-DD)",
    )
    @click.option(
        "--cached-bronze-path",
        type=click.Path(exists=True),
        default=None,
        help="Explicit path to Bronze cache directory",
    )
    @click.pass_context
    def run_command(
        ctx: click.Context,
        pipeline: str,
        run_type: str,
        resume: bool,
        start_offset: int | None,
        limit: int | None,
        input_csv: str | None,
        filter_column: str | None,
        filter_field: str | None,
        dry_run: bool,
        yes: bool,
        vacuum_after_run: bool | None,
        vacuum_retention_days: int | None,
        debug: bool,
        health_server: bool,
        health_port: int,
        use_cached_bronze: bool,
        cached_bronze_date: str | None,
        cached_bronze_path: str | None,
    ) -> None:
        """Run an ETL pipeline."""
        run_callback(
            ctx,
            pipeline=pipeline,
            run_type=run_type,
            resume=resume,
            start_offset=start_offset,
            limit=limit,
            input_csv=input_csv,
            filter_column=filter_column,
            filter_field=filter_field,
            dry_run=dry_run,
            yes=yes,
            vacuum_after_run=vacuum_after_run,
            vacuum_retention_days=vacuum_retention_days,
            debug=debug,
            health_server=health_server,
            health_port=health_port,
            use_cached_bronze=use_cached_bronze,
            cached_bronze_date=cached_bronze_date,
            cached_bronze_path=cached_bronze_path,
        )

    return run_command


__all__ = ["build_run_click_command"]
