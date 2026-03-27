"""Click entrypoint builder for the run-all CLI command."""

from __future__ import annotations

from collections.abc import Callable

import click


def build_run_all_click_command(
    *,
    default_health_server_port: int,
    run_callback: Callable[..., None],
) -> click.Command:
    """Build the canonical Click command object for ``bioetl run-all``."""

    @click.command("run-all")
    @click.option(
        "--source",
        required=True,
        help="Provider name (e.g., chembl, pubchem, uniprot)",
    )
    @click.option(
        "--run-type",
        type=click.Choice(["incremental", "backfill", "rebuild"]),
        default="incremental",
        help="Type of run for all pipelines",
    )
    @click.option("--limit", type=int, help="Maximum records per pipeline")
    @click.option(
        "--dry-run",
        is_flag=True,
        help="Preview mode - show pipelines without execution",
    )
    @click.option(
        "--yes",
        "-y",
        is_flag=True,
        help="Skip confirmation prompt for rebuild/backfill",
    )
    @click.option(
        "--list-only",
        is_flag=True,
        help="List pipelines for the source without running them",
    )
    @click.option("--debug", is_flag=True, help="Enable DEBUG level logging")
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
    @click.pass_context
    def run_all_command(
        click_context: click.Context,
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
