"""Run composite pipeline command for BioETL CLI.

Implements the composite pipeline execution command that orchestrates
multiple data sources (seed + enrichers) into a unified dataset.
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
from bioetl.composition.entrypoints import push_metrics_to_gateway
from bioetl.domain.exceptions import BioETLError
from bioetl.interfaces.cli.commands.execution_policy import (
    CLI_ENTRYPOINT_TYPED_ERRORS,
    map_success_flag_to_exit_code,
)
from bioetl.interfaces.cli.commands.execution_policy import (
    handle_cli_failure as handle_cli_execution_failure,
)
from bioetl.interfaces.cli.commands.health_server_integration import (
    DEFAULT_HEALTH_SERVER_PORT,
    echo_health_server_info,
    health_server_context,
)
from bioetl.interfaces.cli.commands.metrics_server_integration import (
    ensure_metrics_server_started,
)
from bioetl.interfaces.cli.commands.run_composite_runtime import (
    build_runtime_config,
)
from bioetl.interfaces.cli.exit_codes import ExitCode
from bioetl.interfaces.cli.formatters import echo_error, echo_info, echo_warning

__all__ = [
    "run_composite",
]


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
    except (BioETLError, OSError, RuntimeError, ValueError) as exc:
        return (
            False,
            (
                f"{exc} "
                f"(reason_code=CLI_COMPOSITE_RUNNER_ERROR, composite={composite_name}, "
                f"error_type={type(exc).__name__})"
            ),
        )


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


def _handle_run_composite_exception(
    exc: BaseException,
    *,
    composite: str,
    reason_code: str,
) -> None:
    handle_cli_execution_failure(
        exc,
        reason_code=reason_code,
        subject_key="composite",
        subject_value=composite,
        domain_error_title="Composite execution failed with domain error",
        unexpected_error_title="Unexpected error during composite execution",
        interrupted_message="Composite pipeline interrupted by user (Ctrl+C)",
        default_exit_code=ExitCode.FAIL,
    )


def _run_composite_with_cli_policy(
    *,
    composite: str,
    runtime: CompositeRuntimeConfig,
    health_server: bool,
    health_port: int,
) -> tuple[bool, str | None]:
    coro = _run_composite_async(
        composite,
        runtime,
        health_server_enabled=health_server,
        health_port=health_port,
    )
    success = False
    error_message: str | None = None
    try:
        success, error_message = asyncio.run(coro)
    except BioETLError as exc:
        _handle_run_composite_exception(
            exc,
            composite=composite,
            reason_code="CLI_COMPOSITE_DOMAIN_ERROR",
        )
    except KeyboardInterrupt as exc:
        _handle_run_composite_exception(
            exc,
            composite=composite,
            reason_code="CLI_COMPOSITE_SIGINT",
        )
    except CLI_ENTRYPOINT_TYPED_ERRORS as exc:
        _handle_run_composite_exception(
            exc,
            composite=composite,
            reason_code="CLI_COMPOSITE_UNEXPECTED_ERROR",
        )
    finally:
        push_metrics_to_gateway(pipeline_name=f"composite_{composite}")
        if getattr(coro, "cr_frame", None) is not None:
            coro.close()
    return success, error_message


def _echo_composite_startup(
    *,
    composite: str,
    dry_run: bool,
    resume: bool,
    health_server: bool,
    health_port: int,
) -> None:
    """Emit startup information for composite run."""
    echo_info(f"Starting composite pipeline: {composite}")
    if dry_run:
        echo_warning("Dry-run mode: no data will be written")
    if resume:
        echo_info("Resume mode: continuing from last checkpoint")
    echo_health_server_info(health_server, health_port)


def _exit_with_composite_result(success: bool, error_message: str | None) -> None:
    exit_code = map_success_flag_to_exit_code(success)
    if success:
        echo_info("Composite pipeline completed successfully")
        sys.exit(exit_code)
    echo_error("Composite pipeline failed", error_message or "Unknown error")
    sys.exit(exit_code)


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

    Args:
        composite: Composite pipeline name (e.g., 'publication').
        resume: When True, resumes from the last saved checkpoint.
        dry_run: When True, runs the pipeline without writing data to storage.
        seed_limit: Maximum number of seed records to fetch; no limit if None.
        enrich_only: Comma-separated enricher names to run; all enrichers run
            if None.
        required_only: When True, optional enrichers are skipped.
        force_enricher: Enricher name to force-rerun, ignoring its checkpoint.
        use_cached_bronze: When True, loads data from the Bronze cache instead
            of calling the external API.
        cached_bronze_date: ISO date string (YYYY-MM-DD) used to filter cached
            Bronze files; not applied if None.
        cached_bronze_path: Explicit path to a Bronze cache directory; auto-
            resolved from settings if None.
        cached_bronze_enrichers: Override cached Bronze usage for enrichers only;
            follows ``use_cached_bronze`` if None.
        cached_bronze_dependencies: When True, dependency pipelines also load
            from the Bronze cache.
        debug: When True, sets log level to DEBUG for detailed output.
        health_server: When True, starts an HTTP health server during execution.
        health_port: TCP port for the HTTP health server.
    """
    runtime = build_runtime_config(
        resume=resume,
        dry_run=dry_run,
        seed_limit=seed_limit,
        enrich_only=enrich_only,
        required_only=required_only,
        force_enricher=force_enricher,
        use_cached_bronze=use_cached_bronze,
        cached_bronze_date=cached_bronze_date,
        cached_bronze_path=cached_bronze_path,
        cached_bronze_enrichers=cached_bronze_enrichers,
        cached_bronze_dependencies=cached_bronze_dependencies,
    )
    _echo_composite_startup(
        composite=composite,
        dry_run=dry_run,
        resume=resume,
        health_server=health_server,
        health_port=health_port,
    )
    success, error_message = _run_composite_with_cli_policy(
        composite=composite,
        runtime=runtime,
        health_server=health_server,
        health_port=health_port,
    )
    _exit_with_composite_result(success, error_message)
