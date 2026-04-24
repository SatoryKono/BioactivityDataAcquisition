"""Click entrypoint builder for the run-all CLI command."""

from __future__ import annotations

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


class RunAllCommandCallback(Protocol):
    """Typed callback signature consumed by the run-all Click entrypoint."""

    def __call__(
        self,
        click_context: click.Context,
        /,
        *,
        source: str,
        run_type: str,
        limit: int | None,
        dry_run: bool,
        yes: bool,
        list_only: bool,
        debug: bool,
        health_server: bool,
        health_port: int,
    ) -> None: ...


def build_run_all_click_command(
    *,
    default_health_server_port: int,
    run_callback: RunAllCommandCallback,
) -> click.Command:
    """Build the canonical Click command object for ``bioetl run-all``."""

    @click.command("run-all")
    @click.option(
        "--source",
        required=True,
        help="Provider name (e.g., chembl, pubchem, uniprot)",
    )
    @with_run_type_option("Type of run for all pipelines")
    @with_limit_option("Maximum records per pipeline")
    @with_dry_run_option("Preview mode - show pipelines without execution")
    @with_yes_option("Skip confirmation prompt for rebuild/backfill")
    @click.option(
        "--list-only",
        is_flag=True,
        help="List pipelines for the source without running them",
    )
    @with_debug_option("Enable DEBUG level logging")
    @with_health_server_options(default_health_server_port)
    @click.pass_context
    def run_all_command(
        click_context: click.Context,
        /,
        source: str,
        run_type: str,
        limit: int | None,
        dry_run: bool,
        yes: bool,
        list_only: bool,
        debug: bool,
        health_server: bool,
        health_port: int,
    ) -> None:
        """Run all registered pipelines for one provider sequentially."""
        run_callback(
            click_context,
            source=source,
            run_type=run_type,
            limit=limit,
            dry_run=dry_run,
            yes=yes,
            list_only=list_only,
            debug=debug,
            health_server=health_server,
            health_port=health_port,
        )

    return run_all_command


__all__ = ["build_run_all_click_command"]
