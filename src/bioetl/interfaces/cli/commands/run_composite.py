"""Run the composite pipeline CLI command."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

import click

from bioetl.application.composite.runtime_models import CompositeRuntimeConfig
from bioetl.interfaces.cli.commands.domains.composite.command_input import (
    build_composite_run_command_input,
)
from bioetl.interfaces.cli.commands.domains.composite.execution import (
    bootstrap_composite_runner as _bootstrap_composite_runner_impl,
)
from bioetl.interfaces.cli.commands.domains.composite.execution import (
    load_composite_config as _load_composite_config_impl,
)
from bioetl.interfaces.cli.commands.domains.composite.execution import (
    run_composite_async as _run_composite_async_impl,
)
from bioetl.interfaces.cli.commands.domains.composite.execution import (
    run_composite_inner as _run_composite_inner_impl,
)
from bioetl.interfaces.cli.commands.domains.composite.runtime import (
    CompositeRuntimeCliInput,
    build_runtime_config,
)
from bioetl.interfaces.cli.commands.domains.composite.support import (
    emit_composite_startup as _emit_composite_startup_impl,
)
from bioetl.interfaces.cli.commands.domains.composite.support import (
    exit_with_composite_result as _exit_with_composite_result_impl,
)
from bioetl.interfaces.cli.commands.domains.composite.support import (
    handle_run_composite_exception as _handle_run_composite_exception_impl,
)
from bioetl.interfaces.cli.commands.domains.composite.support import (
    run_composite_with_cli_policy as _run_composite_with_cli_policy_impl,
)
from bioetl.interfaces.cli.commands.domains.health.metrics_server_integration import (
    ensure_metrics_server_started,
)
from bioetl.interfaces.cli.commands.domains.health.observability_backend_runtime import (
    build_observability_backend_required_probe_paths,
    ensure_observability_backend_started,
    should_disable_transient_health_server,
)
from bioetl.interfaces.cli.commands.domains.health.server_integration import (
    DEFAULT_HEALTH_SERVER_PORT,
    echo_health_server_info,
    health_server_context,
)
from bioetl.interfaces.cli.formatters import echo_info, echo_warning

if TYPE_CHECKING:
    from bioetl.application.composite.runner_pkg import CompositePipelineRunner
    from bioetl.domain.composite.config import CompositeConfig

__all__ = ["run_composite"]


def _validate_composite_name(
    _ctx: click.Context, _param: click.Parameter, value: str
) -> str:
    """Validate composite pipeline name."""
    if not value:
        raise click.BadParameter("Composite pipeline name is required")
    return value


def load_composite_config(name: str) -> CompositeConfig:
    """Load composite config through the canonical execution helper seam."""
    return _load_composite_config_impl(name)


def bootstrap_composite_runner(
    config: CompositeConfig,
    runtime: CompositeRuntimeConfig,
) -> CompositePipelineRunner:
    """Build composite runner through the canonical execution helper seam."""
    return _bootstrap_composite_runner_impl(config, runtime)


async def _run_composite_inner(
    composite_name: str,
    runtime: CompositeRuntimeConfig,
) -> tuple[bool, str | None]:
    """Run composite pipeline execution logic."""
    result: tuple[bool, str | None] = await _run_composite_inner_impl(
        composite_name,
        runtime,
        load_config=load_composite_config,
        build_runner=bootstrap_composite_runner,
    )
    return result


async def _run_composite_async(
    composite_name: str,
    runtime: CompositeRuntimeConfig,
    health_server_enabled: bool = True,
    health_port: int = DEFAULT_HEALTH_SERVER_PORT,
) -> tuple[bool, str | None]:
    """Run composite pipeline asynchronously with optional health server."""
    result: tuple[bool, str | None] = await _run_composite_async_impl(
        composite_name,
        runtime,
        health_server_enabled=health_server_enabled,
        health_port=health_port,
        run_inner=_run_composite_inner,
        metrics_starter=ensure_metrics_server_started,
        health_context_factory=health_server_context,
    )
    return result


def _handle_run_composite_exception(
    exc: BaseException,
    *,
    composite: str,
    reason_code: str,
) -> None:
    _handle_run_composite_exception_impl(
        exc,
        composite=composite,
        reason_code=reason_code,
    )


def _run_composite_with_cli_policy(
    *,
    composite: str,
    runtime: CompositeRuntimeConfig,
    health_server: bool,
    health_port: int,
) -> tuple[bool, str | None]:
    result: tuple[bool, str | None] = _run_composite_with_cli_policy_impl(
        composite=composite,
        runtime=runtime,
        health_server=health_server,
        health_port=health_port,
        run_async=_run_composite_async,
        exception_handler=lambda exc, composite_name, code: (
            _handle_run_composite_exception(
                exc,
                composite=composite_name,
                reason_code=code,
            )
        ),
    )
    return result


def _echo_composite_startup(
    *,
    composite: str,
    dry_run: bool,
    resume: bool,
    cached_bronze_enabled: bool,
    health_server: bool,
    health_port: int,
) -> None:
    """Emit startup information for composite run."""
    _emit_composite_startup_impl(
        composite=composite,
        dry_run=dry_run,
        resume=resume,
        cached_bronze_enabled=cached_bronze_enabled,
        health_server=health_server,
        health_port=health_port,
        info_printer=echo_info,
        warning_printer=echo_warning,
        health_info_printer=echo_health_server_info,
    )


def _exit_with_composite_result(success: bool, error_message: str | None) -> None:
    _exit_with_composite_result_impl(success, error_message)


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
    help="Resume from last checkpoint state; not a strict exact replay",
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
    help="Load data from Bronze cache instead of API; composite remains rebuild/resume only",
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
@click.option(
    "--ensure-observability-backend/--no-ensure-observability-backend",
    "ensure_observability_backend",
    default=True,
    help="Auto-start a detached Quarantine Explorer backend for Grafana ID/detail panels.",
    show_default=True,
)
@click.option(
    "--observability-backend-port",
    type=int,
    default=DEFAULT_HEALTH_SERVER_PORT,
    help="Port for the detached Quarantine Explorer backend used by Grafana ID/detail panels.",
    show_default=True,
)
def run_composite(**options: object) -> None:
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
    cli_input = build_composite_run_command_input(options)
    backend_result = ensure_observability_backend_started(
        enabled=cli_input.ensure_observability_backend,
        port=cli_input.observability_backend_port,
        required_probe_paths=build_observability_backend_required_probe_paths(),
    )
    if should_disable_transient_health_server(
        health_server_enabled=cli_input.health_server,
        health_port=cli_input.health_port,
        observability_backend_port=cli_input.observability_backend_port,
        backend_result=backend_result,
    ):
        cli_input = replace(cli_input, health_server=False)
    runtime = build_runtime_config(
        CompositeRuntimeCliInput(
            resume=cli_input.resume,
            dry_run=cli_input.dry_run,
            seed_limit=cli_input.seed_limit,
            enrich_only=cli_input.enrich_only,
            required_only=cli_input.required_only,
            force_enricher=cli_input.force_enricher,
            use_cached_bronze=cli_input.use_cached_bronze,
            cached_bronze_date=cli_input.cached_bronze_date,
            cached_bronze_path=cli_input.cached_bronze_path,
            cached_bronze_enrichers=cli_input.cached_bronze_enrichers,
            cached_bronze_dependencies=cli_input.cached_bronze_dependencies,
        )
    )
    _echo_composite_startup(
        composite=cli_input.composite,
        dry_run=cli_input.dry_run,
        resume=cli_input.resume,
        cached_bronze_enabled=(
            runtime.use_cached_bronze
            or runtime.cached_bronze_enrichers is True
            or runtime.cached_bronze_dependencies
        ),
        health_server=cli_input.health_server,
        health_port=cli_input.health_port,
    )
    success, error_message = _run_composite_with_cli_policy(
        composite=cli_input.composite,
        runtime=runtime,
        health_server=cli_input.health_server,
        health_port=cli_input.health_port,
    )
    _exit_with_composite_result(success, error_message)
