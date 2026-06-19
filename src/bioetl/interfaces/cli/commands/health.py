"""Health-check CLI commands and health-server entrypoints."""

from __future__ import annotations

import asyncio
import sys
from typing import TYPE_CHECKING

import click

from bioetl.domain.exceptions import BioETLError
from bioetl.interfaces.cli.commands.domains.health.rendering import (
    HealthResults,
    all_health_results_healthy,
    build_health_result_lines,
    render_health_results_json,
)
from bioetl.interfaces.cli.commands.domains.health.server_integration import (
    DEFAULT_HEALTH_SERVER_PORT,
    run_long_lived_health_server_command,
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
    from bioetl.composition._service_protocols import HealthServerDependenciesProtocol

_HEALTH_SERVER_DOMAIN_ERROR_TITLE = "Health server failed with domain error"
_HEALTH_SERVER_UNEXPECTED_ERROR_TITLE = "Unexpected error in health server command"
_HEALTH_SERVER_INTERRUPTED_MESSAGE = "Health server interrupted by user (Ctrl+C)"
_HEALTH_CHECKS_ERROR_TITLE = "Error running health checks"
_HEALTH_CHECKS_INTERRUPTED_MESSAGE = "Health checks interrupted by user (Ctrl+C)"


def get_health_service() -> HealthService:
    """Load the health service through composition on demand."""
    from bioetl.composition._services import get_health_service as _impl

    return _impl()


def get_health_server_dependencies() -> HealthServerDependenciesProtocol:
    """Load health server dependencies through the lower-level server seam."""
    from bioetl.interfaces.cli.commands.domains.health.server_integration import (
        get_health_server_dependencies as _impl,
    )

    return _impl()


def get_quarantine_service() -> QuarantineService:
    """Load quarantine service through composition on demand."""
    from bioetl.composition._services import get_quarantine_service as _impl

    return _impl()


def get_health_server_quarantine_service() -> QuarantineService:
    """Load read-only quarantine service for health listener endpoints."""
    from bioetl.interfaces.cli.commands.domains.health.server_integration import (
        get_health_server_quarantine_service as _impl,
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


def run_health_server_command(host: str, port: int) -> None:
    """Start the long-lived health/quarantine explorer backend."""
    run_long_lived_health_server_command(host=host, port=port)


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

__all__ = [
    "get_health_server_dependencies",
    "get_health_service",
    "health",
    "health_check",
    "run_health_server_command",
]
