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


def _add_core_options() -> Callable:
    """Add core CLI options to the command."""
    def decorator(cmd: CommandCallback) -> CommandCallback:
        cmd = click.option(  # type: ignore[untyped-decorator]
            "--pipeline",
            callback=validate_pipeline_name,
            required=True,
            help="Pipeline to run",
        )(cmd)
        cmd = typed_with_run_type_option("Type of run")(cmd)
        cmd = click.option(  # type: ignore[untyped-decorator]
            "--resume", is_flag=True, help="Resume from last checkpoint"
        )(cmd)
        cmd = click.option(  # type: ignore[untyped-decorator]
            "--start-offset",
            type=int,
            default=None,
            help="Start extraction from specific record offset (skips checkpoint). "
            "Use after crash to resume from known position.",
        )(cmd)
        return cmd


def _add_filter_options() -> Callable:
    """Add filter-related CLI options."""
    def decorator(cmd: CommandCallback) -> CommandCallback:
        cmd = typed_with_limit_option("Maximum number of records to process")(cmd)
        cmd = click.option(  # type: ignore[untyped-decorator]
            "--input-csv",
            type=click.Path(exists=True),
            help="Path to CSV file with filter IDs",
        )(cmd)
        cmd = click.option(  # type: ignore[untyped-decorator]
            "--filter-column",
            type=str,
            help="Column name in CSV containing filter IDs (default: 'id')",
        )(cmd)
        cmd = click.option(  # type: ignore[untyped-decorator]
            "--filter-field",
            type=str,
            help="API field name to filter by (default: 'molecule_chembl_id')",
        )(cmd)
        return cmd


def _add_execution_options() -> Callable:
    """Add execution control options."""
    def decorator(cmd: CommandCallback) -> CommandCallback:
        cmd = typed_with_dry_run_option(
            "Preview cleanup without execution (for rebuild/backfill)"
        )(cmd)
        cmd = typed_with_yes_option("Skip confirmation prompt for rebuild/backfill")(cmd)
        return cmd


def _add_vacuum_options() -> Callable:
    """Add Delta table vacuum options."""
    def decorator(cmd: CommandCallback) -> CommandCallback:
        cmd = click.option(  # type: ignore[untyped-decorator]
            "--vacuum-after-run",
            is_flag=True,
            default=None,
            help="Run VACUUM on Delta tables after successful run (overrides YAML config)",
        )(cmd)
        cmd = click.option(  # type: ignore[untyped-decorator]
            "--vacuum-retention-days",
            type=int,
            default=None,
            help="Minimum age of files to remove during VACUUM (days, overrides YAML config)",
        )(cmd)
        return cmd


def _add_debug_options(default_health_server_port: int) -> Callable:
    """Add debugging and monitoring options."""
    def decorator(cmd: CommandCallback) -> CommandCallback:
        cmd = typed_with_debug_option()(cmd)
        cmd = typed_with_health_server_options(default_health_server_port)(cmd)
        return cmd


def _add_tracing_options() -> Callable:
    """Add tracing configuration options."""
    def decorator(cmd: CommandCallback) -> CommandCallback:
        cmd = click.option(  # type: ignore[untyped-decorator]
            "--tracing/--no-tracing",
            "enable_tracing",
            default=None,
            help="Override distributed tracing for this run",
        )(cmd)
        return cmd


def _add_cache_options() -> Callable:
    """Add Bronze cache options."""
    def decorator(cmd: CommandCallback) -> CommandCallback:
        cmd = click.option(  # type: ignore[untyped-decorator]
            "--use-cached-bronze/--no-cached-bronze",
            "use_cached_bronze",
            default=False,
            help="Load data from Bronze cache instead of API",
            show_default=True,
        )(cmd)
        cmd = click.option(  # type: ignore[untyped-decorator]
            "--cached-bronze-date",
            type=str,
            default=None,
            help="Filter Bronze cache by date (YYYY-MM-DD)",
        )(cmd)
        cmd = click.option(  # type: ignore[untyped-decorator]
            "--cached-bronze-path",
            type=click.Path(exists=True),
            default=None,
            help="Explicit path to Bronze cache directory",
        )(cmd)
        return cmd


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
    @click.pass_context  # type: ignore[untyped-decorator]
    def run_command(ctx: click.Context, **kwargs) -> None:
        """Run an ETL pipeline."""
        run_callback(ctx, **kwargs)

    # Apply all option groups
    run_command = _add_core_options()(run_command)
    run_command = _add_filter_options()(run_command)
    run_command = _add_execution_options()(run_command)
    run_command = _add_vacuum_options()(run_command)
    run_command = _add_debug_options(default_health_server_port)(run_command)
    run_command = _add_tracing_options()(run_command)
    run_command = _add_cache_options()(run_command)

    return run_command


__all__ = ["build_run_click_command"]
