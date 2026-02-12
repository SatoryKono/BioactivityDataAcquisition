"""Run composite pipeline command for BioETL CLI.

Implements the composite pipeline execution command that orchestrates
multiple data sources (seed + enrichers) into a unified dataset.

See ADR-026 for architectural decisions.
"""

from __future__ import annotations

import asyncio
import sys

import click

from bioetl.application.composite.runner import CompositeRuntimeConfig
from bioetl.composition.bootstrap.runtime.composite import (
    bootstrap_composite_runner,
    load_composite_config,
)
from bioetl.interfaces.cli.commands.health_server_integration import (
    DEFAULT_HEALTH_SERVER_PORT,
    echo_health_server_info,
    health_server_context,
)
from bioetl.interfaces.cli.commands.metrics_server_integration import (
    ensure_metrics_server_started,
)
from bioetl.interfaces.cli.exit_codes import ExitCode
from bioetl.interfaces.cli.formatters import echo_error, echo_info, echo_warning


def _validate_composite_name(
    _ctx: click.Context, _param: click.Parameter, value: str
) -> str:
    """Validate composite pipeline name."""
    if not value:
        raise click.BadParameter("Composite pipeline name is required")
    return value


async def _run_composite_inner(
    composite_name: str,
    runtime: CompositeRuntimeConfig,
) -> tuple[bool, str | None]:
    """Run composite pipeline execution logic.

    Args:
        composite_name: Name of composite pipeline (e.g., 'publication').
        runtime: Runtime configuration.

    Returns:
        Tuple of (success, error_message).
    """
    try:
        config = load_composite_config(composite_name)
    except FileNotFoundError as e:
        return False, str(e)
    except ValueError as e:
        return False, f"Invalid configuration: {e}"

    runner = bootstrap_composite_runner(config, runtime)

    try:
        result = await runner.run()
        if result.is_success:
            return True, None
        # Get error from failed enrichers if any
        failed = result.failed_enrichers
        if failed:
            return False, f"Failed enrichers: {', '.join(failed)}"
        return False, "Composite pipeline failed"
    except Exception as e:
        return False, str(e)


async def _run_composite_async(
    composite_name: str,
    runtime: CompositeRuntimeConfig,
    health_server_enabled: bool = True,
    health_port: int = DEFAULT_HEALTH_SERVER_PORT,
) -> tuple[bool, str | None]:
    """Run composite pipeline asynchronously with optional health server.

    Args:
        composite_name: Name of composite pipeline (e.g., 'publication').
        runtime: Runtime configuration.
        health_server_enabled: Whether to enable health server.
        health_port: Port for health server.

    Returns:
        Tuple of (success, error_message).
    """
    # Start metrics server if enabled (side-effect in entrypoint, not bootstrap)
    ensure_metrics_server_started()

    async with health_server_context(
        enabled=health_server_enabled,
        port=health_port,
    ):
        return await _run_composite_inner(composite_name, runtime)


@click.command(name="run-composite")
@click.option(
    "--composite",
    callback=_validate_composite_name,
    required=True,
    help="Composite pipeline name (e.g., 'publication')",
)
@click.option(
    "--resume",
    is_flag=True,
    help="Resume from last checkpoint",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Preview execution without writing data",
)
@click.option(
    "--seed-limit",
    type=int,
    help="Maximum records for seed pipeline",
)
@click.option(
    "--enrich-only",
    type=str,
    help="Run only specified enrichers (comma-separated)",
)
@click.option(
    "--required-only",
    is_flag=True,
    help="Skip optional enrichers",
)
@click.option(
    "--force-enricher",
    type=str,
    help="Force re-run of specified enricher (ignores checkpoint)",
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
@click.option(
    "--cached-bronze-enrichers/--no-cached-bronze-enrichers",
    "cached_bronze_enrichers",
    default=None,
    help="Override cached Bronze for enrichers (default: follow --use-cached-bronze)",
)
@click.option(
    "--cached-bronze-dependencies/--no-cached-bronze-dependencies",
    "cached_bronze_dependencies",
    default=False,
    help="Override cached Bronze for dependencies (default: use API)",
    show_default=True,
)
@click.option(
    "--debug",
    is_flag=True,
    help="Enable DEBUG level logging",
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
    default=DEFAULT_HEALTH_SERVER_PORT,
    help="Port for the HTTP health server.",
    show_default=True,
)
def run_composite(
    composite: str,
    resume: bool,
    dry_run: bool,
    seed_limit: int | None,
    enrich_only: str | None,
    required_only: bool,
    force_enricher: str | None,
    use_cached_bronze: bool,
    cached_bronze_date: str | None,
    cached_bronze_path: str | None,
    cached_bronze_enrichers: bool | None,
    cached_bronze_dependencies: bool,
    debug: bool,
    health_server: bool,
    health_port: int,
) -> None:
    """Run a composite pipeline that combines multiple data sources.

    Composite pipelines orchestrate a seed pipeline (e.g., ChEMBL publications)
    with multiple enricher pipelines (CrossRef, OpenAlex, PubMed, etc.) to
    create a unified, enriched dataset.

    Example:
        bioetl run-composite --composite publication --seed-limit 100
    """
    # Parse enrich_only into tuple
    enrich_only_tuple: tuple[str, ...] | None = None
    if enrich_only:
        enrich_only_tuple = tuple(e.strip() for e in enrich_only.split(","))

    runtime = CompositeRuntimeConfig(
        resume=resume,
        dry_run=dry_run,
        enrich_only=enrich_only_tuple,
        required_only=required_only,
        force_enricher=force_enricher,
        seed_limit=seed_limit,
        use_cached_bronze=use_cached_bronze,
        cached_bronze_path=cached_bronze_path,
        cached_bronze_date=cached_bronze_date,
        cached_bronze_enrichers=cached_bronze_enrichers,
        cached_bronze_dependencies=cached_bronze_dependencies,
    )

    echo_info(f"Starting composite pipeline: {composite}")

    if dry_run:
        echo_warning("Dry-run mode: no data will be written")

    if resume:
        echo_info("Resume mode: continuing from last checkpoint")

    # Display health server info
    echo_health_server_info(health_server, health_port)

    try:
        success, error_message = asyncio.run(
            _run_composite_async(
                composite,
                runtime,
                health_server_enabled=health_server,
                health_port=health_port,
            )
        )
    except KeyboardInterrupt:
        echo_warning("Composite pipeline interrupted by user (Ctrl+C)")
        sys.exit(ExitCode.SIGINT)
    except Exception as e:
        echo_error("Unexpected error during composite execution", str(e))
        sys.exit(ExitCode.FAIL)

    if success:
        echo_info("Composite pipeline completed successfully")
        sys.exit(ExitCode.OK)
    else:
        echo_error("Composite pipeline failed", error_message or "Unknown error")
        sys.exit(ExitCode.PIPELINE_ERROR)
