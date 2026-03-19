"""Health check command for BioETL CLI.

Provides commands for running health checks and starting the health server.
Uses composition entrypoints for clean layering and proper DI.
"""

from __future__ import annotations

import asyncio
import sys
from typing import TYPE_CHECKING

import click

from bioetl.domain.exceptions import BioETLError
from bioetl.interfaces.cli.commands.domains.health.rendering import (
    all_health_results_healthy,
    build_health_result_lines,
    build_health_server_info_lines,
    render_health_results_json,
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
    from bioetl.composition.bootstrap.cli.health import HealthServerDependencies


def get_health_service() -> HealthService:
    """Load the health service through composition on demand."""
    from bioetl.composition.services_api import get_health_service as _impl

    return _impl()


def get_health_server_dependencies() -> HealthServerDependencies:
    """Load health server dependencies through composition on demand."""
    from bioetl.composition.services_api import (
        get_health_server_dependencies as _impl,
    )

    return _impl()


def _handle_health_failure(
    exc: BaseException,
    *,
    reason_code: str,
    target: str,
    domain_error_title: str,
    unexpected_error_title: str,
    interrupted_message: str,
) -> None:
    """Handle health command failures with shared CLI policy.

    Args:
        exc: Exception caught at the CLI command boundary.
        reason_code: Machine-readable code for the failure (e.g., 'CLI_HEALTH_CHECK_DOMAIN_ERROR').
        target: Target identifier (e.g., provider name or host:port) used in error context.
        domain_error_title: Human-readable title for BioETLError failures.
        unexpected_error_title: Human-readable title for unexpected exception failures.
        interrupted_message: Message displayed when KeyboardInterrupt is caught.
    """
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
    """Build stable provider subject label for error handling.

    Args:
        provider: Tuple of provider names selected via CLI. Empty tuple means all providers.

    Returns:
        Comma-joined provider names, or 'all' when the tuple is empty.
    """
    return ",".join(provider) if provider else "all"


def _echo_health_server_info(host: str, port: int) -> None:
    """Print startup information for health server command.

    Args:
        host: IP address the server will bind to.
        port: TCP port the server will listen on.
    """
    for line in build_health_server_info_lines(host, port):
        click.echo(line)


async def _run_health_server(host: str, port: int) -> None:
    """Start and keep the health server alive until interrupted.

    Args:
        host: IP address to bind the server to.
        port: TCP port for the health server to listen on.
    """
    from bioetl.interfaces.http.health_server import HealthServer

    deps = get_health_server_dependencies()
    server = HealthServer(
        host=host,
        port=port,
        health_monitor=deps.health_monitor,
    )
    await server.start()
    try:
        while True:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        pass  # Why: shutdown loop exit; CancelledError is the normal stop signal
    finally:
        await server.stop()
        click.echo("\nHealth server stopped.")


def _execute_health_server(host: str, port: int) -> None:
    """Execute health server coroutine with CLI error policy.

    Args:
        host: IP address the server will bind to.
        port: TCP port the server will listen on.
    """
    coro = _run_health_server(host=host, port=port)
    try:
        asyncio.run(coro)
    except BioETLError as exc:
        _handle_health_failure(
            exc,
            reason_code="CLI_HEALTH_SERVER_DOMAIN_ERROR",
            target=f"{host}:{port}",
            domain_error_title="Health server failed with domain error",
            unexpected_error_title="Unexpected error in health server command",
            interrupted_message="Health server interrupted by user (Ctrl+C)",
        )
    except CLI_ENTRYPOINT_TYPED_ERRORS as exc:
        _handle_health_failure(
            exc,
            reason_code="CLI_HEALTH_SERVER_UNEXPECTED_ERROR",
            target=f"{host}:{port}",
            domain_error_title="Health server failed with domain error",
            unexpected_error_title="Unexpected error in health server command",
            interrupted_message="Health server interrupted by user (Ctrl+C)",
        )
    except KeyboardInterrupt:
        click.echo("\nShutting down...")
        sys.exit(ExitCode.OK)
    finally:
        if getattr(coro, "cr_frame", None) is not None:
            coro.close()


async def _run_health_checks(provider: tuple[str, ...]) -> dict[str, dict[str, str]]:
    """Execute health checks and return results as serializable dictionary.

    Args:
        provider: Tuple of provider names to check. Empty tuple checks all providers.

    Returns:
        Dict mapping provider names to their health check result dicts.
    """
    service = get_health_service()
    providers_list = list(provider) if provider else None
    summary = await service.check_providers(providers=providers_list)
    return summary.to_dict()


def _execute_health_checks(
    provider: tuple[str, ...],
) -> dict[str, dict[str, str]] | None:
    """Execute health checks with CLI error policy and return results.

    Args:
        provider: Tuple of provider names to check. Empty tuple checks all providers.

    Returns:
        Dict mapping provider names to health check results, or None if an exception
        was handled and the process will exit.
    """
    providers_subject = _provider_subject(provider)
    coro = _run_health_checks(provider)
    try:
        return asyncio.run(coro)
    except BioETLError as exc:
        _handle_health_failure(
            exc,
            reason_code="CLI_HEALTH_CHECK_DOMAIN_ERROR",
            target=providers_subject,
            domain_error_title="Error running health checks",
            unexpected_error_title="Error running health checks",
            interrupted_message="Health checks interrupted by user (Ctrl+C)",
        )
    except KeyboardInterrupt as exc:
        _handle_health_failure(
            exc,
            reason_code="CLI_HEALTH_CHECK_SIGINT",
            target=providers_subject,
            domain_error_title="Error running health checks",
            unexpected_error_title="Error running health checks",
            interrupted_message="Health checks interrupted by user (Ctrl+C)",
        )
    except CLI_ENTRYPOINT_TYPED_ERRORS as exc:
        _handle_health_failure(
            exc,
            reason_code="CLI_HEALTH_CHECK_UNEXPECTED_ERROR",
            target=providers_subject,
            domain_error_title="Error running health checks",
            unexpected_error_title="Error running health checks",
            interrupted_message="Health checks interrupted by user (Ctrl+C)",
        )
    finally:
        if getattr(coro, "cr_frame", None) is not None:
            coro.close()
    return None


def _render_health_results(
    results: dict[str, dict[str, str]],
    *,
    output_json: bool,
) -> None:
    """Render health check output and exit with mapped status code.

    Args:
        results: Dict mapping provider names to health check result dicts.
        output_json: When True, outputs results as JSON; otherwise uses a
            human-readable text format.
    """
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
    default=8081,
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

    Example:
        bioetl health server --port 8081

    Args:
        host: IP address to bind the server to (e.g., '127.0.0.1' or '0.0.0.0').
        port: TCP port for the health server to listen on.
    """
    _echo_health_server_info(host, port)
    _execute_health_server(host, port)


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

__all__ = ["health"]
