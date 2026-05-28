"""Health-check CLI commands and health-server entrypoints."""

from __future__ import annotations

import asyncio
import sys
from typing import TYPE_CHECKING, cast

import click

from bioetl.domain.exceptions import BioETLError
from bioetl.interfaces.cli.commands.domains.health.rendering import (
    HealthResults,
    all_health_results_healthy,
    build_health_result_lines,
    build_health_server_info_lines,
    render_health_results_json,
)
from bioetl.interfaces.cli.commands.domains.health.server_integration import (
    DEFAULT_HEALTH_SERVER_PORT,
)
from bioetl.interfaces.cli.commands.domains.shared.execution_policy import (
    CLI_ENTRYPOINT_TYPED_ERRORS,
)
from bioetl.interfaces.cli.commands.domains.shared.execution_policy import (
    handle_cli_failure as handle_cli_execution_failure,
)
from bioetl.interfaces.cli.exit_codes import ExitCode

if TYPE_CHECKING:
    from bioetl.application.services.health_service import HealthService
    from bioetl.application.services.quarantine_service import QuarantineService
    from bioetl.composition.health_api import (
        HealthServerDependenciesProtocol,
    )
    from bioetl.composition.health_api import (
        RuntimeSettingsProtocol as Settings,
    )
    from bioetl.domain.ports import LoggerPort

_HEALTH_SERVER_DOMAIN_ERROR_TITLE = "Health server failed with domain error"
_HEALTH_SERVER_UNEXPECTED_ERROR_TITLE = "Unexpected error in health server command"
_HEALTH_SERVER_INTERRUPTED_MESSAGE = "Health server interrupted by user (Ctrl+C)"
_HEALTH_CHECKS_ERROR_TITLE = "Error running health checks"
_HEALTH_CHECKS_INTERRUPTED_MESSAGE = "Health checks interrupted by user (Ctrl+C)"


def get_health_service() -> HealthService:
    """Load the health service through composition on demand."""
    from bioetl.composition.health_api import get_health_service as _impl

    return _impl()


def get_health_server_dependencies() -> HealthServerDependenciesProtocol:
    """Load health server dependencies through composition on demand."""
    from bioetl.composition.health_api import (
        get_health_server_dependencies as _impl,
    )

    return _impl()


def get_quarantine_service() -> QuarantineService:
    """Load quarantine service through composition on demand."""
    from bioetl.composition.health_api import get_quarantine_service as _impl

    return _impl()


def get_settings() -> Settings:
    """Load runtime settings through composition on demand."""
    from bioetl.composition.health_api import get_runtime_settings as _impl

    return cast("Settings", _impl())


def _start_metrics_server_via_interface(
    *,
    port: int,
    addr: str,
    fail_fast: bool,
    retry_count: int,
    retry_delay: float,
    logger: LoggerPort | None,
) -> bool:
    """Start the metrics server through the lightweight runtime server seam."""
    from bioetl.composition.observability_api import start_metrics_server as _impl

    return _impl(
        port=port,
        addr=addr,
        fail_fast=fail_fast,
        retry_count=retry_count,
        retry_delay=retry_delay,
        logger=logger,
    )


# Backward-compatible patch point for existing tests and callers.
start_metrics_server = _start_metrics_server_via_interface


def _handle_health_failure(
    exc: BaseException,
    *,
    reason_code: str,
    target: str,
    domain_error_title: str,
    unexpected_error_title: str,
    interrupted_message: str,
) -> None:
    """Handle health command failures with the shared CLI execution policy."""
    handle_cli_execution_failure(
        exc,
        reason_code=reason_code,
        subject_key="target",
        subject_value=target,
        domain_error_title=domain_error_title,
        unexpected_error_title=unexpected_error_title,
        interrupted_message=interrupted_message,
        default_exit_code=ExitCode.FAIL,
    )


def _provider_subject(provider: tuple[str, ...]) -> str:
    """Build a stable provider subject label for error handling."""
    return ",".join(provider) if provider else "all"


def _echo_health_server_info(host: str, port: int) -> None:
    """Print startup information for the health server command."""
    for line in build_health_server_info_lines(host, port):
        click.echo(line)


def _start_health_observability(logger: LoggerPort | None = None) -> None:
    """Start the Prometheus metrics server for long-lived health mode."""
    settings = get_settings()
    if not (
        settings.observability.metrics_enabled
        and settings.observability.metrics_server_enabled
    ):
        if logger is not None:
            logger.info(
                "health_server_metrics_disabled",
                metrics_enabled=settings.observability.metrics_enabled,
                metrics_server_enabled=settings.observability.metrics_server_enabled,
            )
        return

    start_metrics = start_metrics_server
    started = start_metrics(
        port=settings.metrics_port,
        addr=settings.metrics_addr,
        fail_fast=settings.observability.metrics_fail_fast,
        retry_count=settings.observability.metrics_retry_count,
        retry_delay=settings.observability.metrics_retry_delay,
        logger=logger,
    )
    if logger is not None:
        logger.info(
            "health_server_metrics_ready",
            metrics_started=started,
            metrics_port=settings.metrics_port,
            metrics_addr=settings.metrics_addr,
        )


async def _run_health_server(host: str, port: int) -> None:
    """Start and keep the health server alive until interrupted."""
    from bioetl.interfaces.http.health_server import HealthServer

    if sys.pycache_prefix is None:
        sys.pycache_prefix = "/tmp/bioetl-pycache"  # nosec B108
    deps = get_health_server_dependencies()
    _start_health_observability()
    quarantine_service: QuarantineService | None = None
    try:
        quarantine_service = get_quarantine_service()
    except CLI_ENTRYPOINT_TYPED_ERRORS:
        # Why: Health probes must stay available even when quarantine storage
        # setup fails; explorer endpoints remain disabled in that case.
        quarantine_service = None
    server = HealthServer(
        host=host,
        port=port,
        health_monitor=deps.health_monitor,
        quarantine_service=quarantine_service,
        run_manifest_port=deps.run_manifest_port,
        run_ledger_port=deps.run_ledger_port,
    )
    try:
        await server.start()
        while True:
            await asyncio.sleep(1)
    finally:
        await server.stop()
        if quarantine_service is not None:
            await quarantine_service.aclose()
        click.echo("\nHealth server stopped.")


def _execute_health_server(host: str, port: int) -> None:
    """Execute health server coroutine with CLI error policy."""
    coro = _run_health_server(host=host, port=port)
    try:
        asyncio.run(coro)
    except asyncio.CancelledError:
        # Why: tests and shutdown callers may use CancelledError as the stop
        # signal for the long-lived health server loop. The coroutine already
        # performs cleanup and emits the shutdown line in its finally block.
        return
    except BioETLError as exc:
        _handle_health_failure(
            exc,
            reason_code="CLI_HEALTH_SERVER_DOMAIN_ERROR",
            target=f"{host}:{port}",
            domain_error_title=_HEALTH_SERVER_DOMAIN_ERROR_TITLE,
            unexpected_error_title=_HEALTH_SERVER_UNEXPECTED_ERROR_TITLE,
            interrupted_message=_HEALTH_SERVER_INTERRUPTED_MESSAGE,
        )
    except CLI_ENTRYPOINT_TYPED_ERRORS as exc:
        _handle_health_failure(
            exc,
            reason_code="CLI_HEALTH_SERVER_UNEXPECTED_ERROR",
            target=f"{host}:{port}",
            domain_error_title=_HEALTH_SERVER_DOMAIN_ERROR_TITLE,
            unexpected_error_title=_HEALTH_SERVER_UNEXPECTED_ERROR_TITLE,
            interrupted_message=_HEALTH_SERVER_INTERRUPTED_MESSAGE,
        )
    except KeyboardInterrupt:
        click.echo("\nShutting down...")
        sys.exit(ExitCode.OK)
    finally:
        if getattr(coro, "cr_frame", None) is not None:
            coro.close()


def run_health_server_command(host: str, port: int) -> None:
    """Start the long-lived health/quarantine explorer backend."""
    _echo_health_server_info(host, port)
    _execute_health_server(host, port)


async def _run_health_checks(provider: tuple[str, ...]) -> HealthResults:
    """Execute health checks and return results as serializable dictionary."""
    service = get_health_service()
    providers_list = list(provider) if provider else None
    summary = await service.check_providers(providers=providers_list)
    results: HealthResults = summary.to_dict()
    return results


def _execute_health_checks(
    provider: tuple[str, ...],
) -> HealthResults | None:
    """Execute health checks with CLI error policy and return results."""
    providers_subject = _provider_subject(provider)
    coro = _run_health_checks(provider)
    try:
        return asyncio.run(coro)
    except BioETLError as exc:
        _handle_health_failure(
            exc,
            reason_code="CLI_HEALTH_CHECK_DOMAIN_ERROR",
            target=providers_subject,
            domain_error_title=_HEALTH_CHECKS_ERROR_TITLE,
            unexpected_error_title=_HEALTH_CHECKS_ERROR_TITLE,
            interrupted_message=_HEALTH_CHECKS_INTERRUPTED_MESSAGE,
        )
    except KeyboardInterrupt as exc:
        _handle_health_failure(
            exc,
            reason_code="CLI_HEALTH_CHECK_SIGINT",
            target=providers_subject,
            domain_error_title=_HEALTH_CHECKS_ERROR_TITLE,
            unexpected_error_title=_HEALTH_CHECKS_ERROR_TITLE,
            interrupted_message=_HEALTH_CHECKS_INTERRUPTED_MESSAGE,
        )
    except CLI_ENTRYPOINT_TYPED_ERRORS as exc:
        _handle_health_failure(
            exc,
            reason_code="CLI_HEALTH_CHECK_UNEXPECTED_ERROR",
            target=providers_subject,
            domain_error_title=_HEALTH_CHECKS_ERROR_TITLE,
            unexpected_error_title=_HEALTH_CHECKS_ERROR_TITLE,
            interrupted_message=_HEALTH_CHECKS_INTERRUPTED_MESSAGE,
        )
    finally:
        if getattr(coro, "cr_frame", None) is not None:
            coro.close()
    return None


def _render_health_results(
    results: HealthResults,
    *,
    output_json: bool,
) -> None:
    """Render health check output and exit with mapped status code."""
    all_healthy = all_health_results_healthy(results)
    if output_json:
        click.echo(render_health_results_json(results))
        sys.exit(ExitCode.OK if all_healthy else ExitCode.FAIL)

    for line in build_health_result_lines(results):
        click.echo(line)

    if all_healthy:
        click.echo("\nAll providers healthy.")
        sys.exit(ExitCode.OK)
    click.echo("\nSome providers unhealthy.")
    sys.exit(ExitCode.FAIL)


@click.group()
def health() -> None:
    """Health check and monitoring operations."""


@health.command("server")
@click.option(
    "--host",
    default="127.0.0.1",
    help="Host to bind to. Use 0.0.0.0 to expose externally.",
    show_default=True,
)
@click.option(
    "--port",
    "-p",
    default=DEFAULT_HEALTH_SERVER_PORT,
    type=int,
    help="Port to listen on.",
    show_default=True,
)
def health_server_command(host: str, port: int) -> None:
    """Start the HTTP health server.

    Runs an HTTP server that exposes health check endpoints:

    \b
    - GET /health         - Overall health status
    - GET /health/live    - Kubernetes liveness probe
    - GET /health/ready   - Kubernetes readiness probe
    - GET /health/providers - Detailed provider status
    - GET /ops/quarantine/filtered-records - Silver reject list (read-only)
    - GET /ops/quarantine/filtered-record/{payload_hash} - Silver reject detail
    - GET /ops/quarantine/filtered-stats - Silver reject aggregates
    - GET /ops/quarantine/filter-options - Explorer variable options

    Example:
        bioetl health server --port 8081

    Args:
        host: IP address to bind the server to (e.g., '127.0.0.1' or '0.0.0.0').
        port: TCP port for the health server to listen on.
    """
    run_health_server_command(host, port)


@health.command("check")
@click.option(
    "--provider",
    "-p",
    multiple=True,
    help="Provider(s) to check. If not specified, checks all configured providers.",
)
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Output results as JSON.",
)
def health_check(provider: tuple[str, ...], output_json: bool) -> None:
    """Run health checks on data providers.

    Checks connectivity and health status of configured data providers
    (ChEMBL, PubChem, UniProt, etc.).

    Example:
        bioetl health check
        bioetl health check --provider chembl --provider pubchem
        bioetl health check --json

    Args:
        provider: Tuple of provider names to check (e.g., ('chembl', 'pubchem')).
            Checks all configured providers when empty.
        output_json: When True, outputs health check results as JSON.
    """
    click.echo("Running health checks...")
    results = _execute_health_checks(provider)
    if results is None:
        return
    _render_health_results(results, output_json=output_json)


COMMANDS = (health_server_command,)

__all__ = ["health", "run_health_server_command"]
