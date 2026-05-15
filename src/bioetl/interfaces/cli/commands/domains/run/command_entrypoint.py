"""Click entrypoint builder for the run CLI command."""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

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


class RunCommandCallback(Protocol):
    """Typed callback signature consumed by the Click entrypoint."""

    def __call__(self, ctx: click.Context, /, **kwargs: object) -> None: ...


def _add_core_options(
    validate_pipeline_name: Callable[..., object],
) -> CommandDecorator:
    """Add core CLI options to the command."""

    def decorator(cmd: CommandCallback) -> CommandCallback:
        cmd = click.option(
            "--pipeline",
            callback=validate_pipeline_name,
            required=True,
            help="Pipeline to run",
        )(cmd)
        cmd = with_run_type_option("Type of run")(cmd)
        cmd = click.option(
            "--resume",
            is_flag=True,
            help="Resume from last checkpoint state; not a strict exact replay",
        )(cmd)
        cmd = click.option(
            "--start-offset",
            type=int,
            default=None,
            help="Start extraction from specific record offset (skips checkpoint). "
            "Use after crash to resume from known position.",
        )(cmd)
        return cmd

    return decorator


def _add_filter_options() -> CommandDecorator:
    """Add filter-related CLI options."""

    def decorator(cmd: CommandCallback) -> CommandCallback:
        cmd = with_limit_option("Maximum number of records to process")(cmd)
        cmd = click.option(
            "--input-csv",
            type=click.Path(exists=True),
            help="Path to CSV file with filter IDs",
        )(cmd)
        cmd = click.option(
            "--filter-column",
            type=str,
            help="Column name in CSV containing filter IDs (default: 'id')",
        )(cmd)
        cmd = click.option(
            "--filter-field",
            type=str,
            help="API field name to filter by (default: 'molecule_chembl_id')",
        )(cmd)
        return cmd

    return decorator


def _add_execution_options() -> CommandDecorator:
    """Add execution control options."""

    def decorator(cmd: CommandCallback) -> CommandCallback:
        cmd = with_dry_run_option(
            "Preview cleanup without execution (for rebuild/backfill)"
        )(cmd)
        cmd = with_yes_option("Skip confirmation prompt for rebuild/backfill")(cmd)
        return cmd

    return decorator


def _add_vacuum_options() -> CommandDecorator:
    """Add Delta table vacuum options."""

    def decorator(cmd: CommandCallback) -> CommandCallback:
        cmd = click.option(
            "--vacuum-after-run",
            is_flag=True,
            default=None,
            help="Run VACUUM on Delta tables after successful run (overrides YAML config)",
        )(cmd)
        cmd = click.option(
            "--vacuum-retention-days",
            type=int,
            default=None,
            help="Minimum age of files to remove during VACUUM (days, overrides YAML config)",
        )(cmd)
        return cmd

    return decorator


def _add_debug_options(default_health_server_port: int) -> CommandDecorator:
    """Add debugging and monitoring options."""

    def decorator(cmd: CommandCallback) -> CommandCallback:
        cmd = with_debug_option()(cmd)
        cmd = with_health_server_options(default_health_server_port)(cmd)
        return cmd

    return decorator


def _add_tracing_options() -> CommandDecorator:
    """Add tracing configuration options."""

    def decorator(cmd: CommandCallback) -> CommandCallback:
        cmd = click.option(
            "--tracing/--no-tracing",
            "enable_tracing",
            default=None,
            help="Override distributed tracing for this run",
        )(cmd)
        return cmd

    return decorator


def _add_cache_options() -> CommandDecorator:
    """Add Bronze cache options."""

    def decorator(cmd: CommandCallback) -> CommandCallback:
        cmd = click.option(
            "--use-cached-bronze/--no-cached-bronze",
            "use_cached_bronze",
            default=False,
            help="Load data from Bronze cache instead of API",
            show_default=True,
        )(cmd)
        cmd = click.option(
            "--cached-bronze-date",
            type=str,
            default=None,
            help="Filter Bronze cache by date (YYYY-MM-DD)",
        )(cmd)
        cmd = click.option(
            "--cached-bronze-path",
            type=click.Path(exists=True),
            default=None,
            help="Explicit path to Bronze cache directory",
        )(cmd)
        cmd = click.option(
            "--exact-replay/--no-exact-replay",
            "exact_replay",
            default=False,
            help="Request strict exact replay with snapshot-backed inputs; not the same as --resume or rebuild",
            show_default=True,
        )(cmd)
        return cmd

    return decorator


def _add_replay_parentage_options() -> CommandDecorator:
    """Add explicit replay ancestry options."""

    def decorator(cmd: CommandCallback) -> CommandCallback:
        cmd = click.option(
            "--replay-of-run-id",
            type=str,
            default=None,
            help="Explicit parent run_id when this execution is an exact replay",
        )(cmd)
        cmd = click.option(
            "--replay-of-manifest-id",
            type=str,
            default=None,
            help="Explicit parent manifest_id when this execution is an exact replay",
        )(cmd)
        return cmd

    return decorator


def _add_persistence_profile_options() -> CommandDecorator:
    """Add per-run control-plane persistence profile options."""

    def decorator(cmd: CommandCallback) -> CommandCallback:
        cmd = click.option(
            "--required-persistence-profile",
            type=click.Choice(
                ["degraded_observable", "replay_ready", "forensic_grade"]
            ),
            default=None,
            help=(
                "Override the required control-plane persistence profile for "
                "this run"
            ),
        )(cmd)
        return cmd

    return decorator


def build_run_click_command(
    *,
    validate_pipeline_name: Callable[..., object],
    default_health_server_port: int,
    run_callback: RunCommandCallback,
) -> click.Command:
    """Build the canonical Click command object for ``bioetl run``."""

    def run_command(ctx: click.Context, /, **kwargs: object) -> None:
        """Run an ETL pipeline."""
        run_callback(ctx, **kwargs)

    callback: CommandCallback = run_command

    # Apply all option groups
    callback = _add_core_options(validate_pipeline_name)(callback)
    callback = _add_filter_options()(callback)
    callback = _add_execution_options()(callback)
    callback = _add_vacuum_options()(callback)
    callback = _add_debug_options(default_health_server_port)(callback)
    callback = _add_tracing_options()(callback)
    callback = _add_cache_options()(callback)
    callback = _add_replay_parentage_options()(callback)
    callback = _add_persistence_profile_options()(callback)

    return click.command()(click.pass_context(callback))


__all__ = ["build_run_click_command"]
