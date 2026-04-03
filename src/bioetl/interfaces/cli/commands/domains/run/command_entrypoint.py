"""Click entrypoint builder for the run CLI command."""

from __future__ import annotations

from collections.abc import Callable
from typing import cast

import click

from bioetl.interfaces.cli.commands.domains.shared.click_options import (
    with_debug_option,
    with_dry_run_option,
    with_health_server_options,
    with_limit_option,
    with_run_type_option,
    with_yes_option,
)

CommandCallback = Callable[..., object]
CommandDecorator = Callable[[CommandCallback], CommandCallback]
CommandDecoratorFactory = Callable[..., CommandDecorator]


def build_run_click_command(
    *,
    validate_pipeline_name: Callable[..., object],
    default_health_server_port: int,
    run_callback: Callable[..., None],
) -> click.Command:
    """Build the canonical Click command object for ``bioetl run``."""

    typed_with_run_type_option = cast(CommandDecoratorFactory, with_run_type_option)
    typed_with_limit_option = cast(CommandDecoratorFactory, with_limit_option)
    typed_with_dry_run_option = cast(CommandDecoratorFactory, with_dry_run_option)
    typed_with_yes_option = cast(CommandDecoratorFactory, with_yes_option)
    typed_with_debug_option = cast(CommandDecoratorFactory, with_debug_option)
    typed_with_health_server_options = cast(
        CommandDecoratorFactory,
        with_health_server_options,
    )

    @click.command()  # type: ignore[untyped-decorator]
    @click.option(  # type: ignore[untyped-decorator]
        "--pipeline",
        callback=validate_pipeline_name,
        required=True,
        help="Pipeline to run",
    )
    @typed_with_run_type_option("Type of run")
    @click.option(  # type: ignore[untyped-decorator]
        "--resume", is_flag=True, help="Resume from last checkpoint"
    )
    @click.option(  # type: ignore[untyped-decorator]
        "--start-offset",
        type=int,
        default=None,
        help="Start extraction from specific record offset (skips checkpoint). "
        "Use after crash to resume from known position.",
    )
    @typed_with_limit_option("Maximum number of records to process")
    @click.option(  # type: ignore[untyped-decorator]
        "--input-csv",
        type=click.Path(exists=True),
        help="Path to CSV file with filter IDs",
    )
    @click.option(  # type: ignore[untyped-decorator]
        "--filter-column",
        type=str,
        help="Column name in CSV containing filter IDs (default: 'id')",
    )
    @click.option(  # type: ignore[untyped-decorator]
        "--filter-field",
        type=str,
        help="API field name to filter by (default: 'molecule_chembl_id')",
    )
    @typed_with_dry_run_option(
        "Preview cleanup without execution (for rebuild/backfill)"
    )
    @typed_with_yes_option("Skip confirmation prompt for rebuild/backfill")
    @click.option(  # type: ignore[untyped-decorator]
        "--vacuum-after-run",
        is_flag=True,
        default=None,
        help="Run VACUUM on Delta tables after successful run (overrides YAML config)",
    )
    @click.option(  # type: ignore[untyped-decorator]
        "--vacuum-retention-days",
        type=int,
        default=None,
        help="Minimum age of files to remove during VACUUM (days, overrides YAML config)",
    )
    @typed_with_debug_option()
    @typed_with_health_server_options(default_health_server_port)
    @click.option(  # type: ignore[untyped-decorator]
        "--tracing/--no-tracing",
        "enable_tracing",
        default=None,
        help="Override distributed tracing for this run",
    )
    @click.option(  # type: ignore[untyped-decorator]
        "--use-cached-bronze/--no-cached-bronze",
        "use_cached_bronze",
        default=False,
        help="Load data from Bronze cache instead of API",
        show_default=True,
    )
    @click.option(  # type: ignore[untyped-decorator]
        "--cached-bronze-date",
        type=str,
        default=None,
        help="Filter Bronze cache by date (YYYY-MM-DD)",
    )
    @click.option(  # type: ignore[untyped-decorator]
        "--cached-bronze-path",
        type=click.Path(exists=True),
        default=None,
        help="Explicit path to Bronze cache directory",
    )
    @click.pass_context  # type: ignore[untyped-decorator]
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
        enable_tracing: bool | None,
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
            enable_tracing=enable_tracing,
            use_cached_bronze=use_cached_bronze,
            cached_bronze_date=cached_bronze_date,
            cached_bronze_path=cached_bronze_path,
        )

    return run_command


__all__ = ["build_run_click_command"]
