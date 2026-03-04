"""Health check command for BioETL CLI.

Provides commands for running health checks and starting the health server.
Uses composition entrypoints for clean layering and proper DI.
"""

from __future__ import annotations

import asyncio
import sys

import click

from bioetl.composition.entrypoints import (
    get_health_server_dependencies,
    get_health_service,
)
from bioetl.domain.exceptions import BioETLError
from bioetl.interfaces.cli.commands.execution_policy import (
    CLI_ENTRYPOINT_TYPED_ERRORS,
)
from bioetl.interfaces.cli.commands.execution_policy import (
    handle_cli_failure as handle_cli_execution_failure,
)
from bioetl.interfaces.cli.exit_codes import ExitCode


def _handle_health_failure(
    exc: BaseException,
    *,
    reason_code: str,
    target: str,
    domain_error_title: str,
    unexpected_error_title: str,
    interrupted_message: str,
) -> None:
    """Handle health command failures with shared CLI policy."""
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
        host: Host.
        port: Port.
    """
    click.echo(f"Starting health server on http://{host}:{port}")
    click.echo("Endpoints:")
    click.echo(f"  - http://{host}:{port}/health")
    click.echo(f"  - http://{host}:{port}/health/live")
    click.echo(f"  - http://{host}:{port}/health/ready")
    click.echo(f"  - http://{host}:{port}/health/providers")
    click.echo("\nPress Ctrl+C to stop.")

    async def run() -> None:
        """Start health server and keep it running until interrupted."""
        # Import HealthServer here (interfaces layer can import from interfaces)
        from bioetl.interfaces.http.health_server import HealthServer

        # Get dependencies from composition root (proper DI)
        deps = get_health_server_dependencies()

        # Create server in interfaces layer with injected dependencies
        server = HealthServer(
            host=host,
            port=port,
            health_monitor=deps.health_monitor,
        )

        await server.start()

        try:
            # Keep server running until interrupted
            while True:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            pass
        finally:
            await server.stop()
            click.echo("\nHealth server stopped.")

    coro = run()
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
        provider: Data provider name.
        output_json: Whether to output json.
    """
    import json as json_module

    click.echo("Running health checks...")

    async def run_checks() -> dict[str, dict[str, str]]:
        """Execute health checks and return results as dictionary.

        Returns:
            Result dictionary.
        """
        service = get_health_service()

        # Convert tuple to list or None for all providers
        providers_list = list(provider) if provider else None

        summary = await service.check_providers(providers=providers_list)

        # Convert to dict format for backward compatibility
        return summary.to_dict()

    coro = run_checks()
    providers_subject = ",".join(provider) if provider else "all"
    try:
        results = asyncio.run(coro)
    except BioETLError as exc:
        _handle_health_failure(
            exc,
            reason_code="CLI_HEALTH_CHECK_DOMAIN_ERROR",
            target=providers_subject,
            domain_error_title="Error running health checks",
            unexpected_error_title="Error running health checks",
            interrupted_message="Health checks interrupted by user (Ctrl+C)",
        )
        return
    except KeyboardInterrupt as exc:
        _handle_health_failure(
            exc,
            reason_code="CLI_HEALTH_CHECK_SIGINT",
            target=providers_subject,
            domain_error_title="Error running health checks",
            unexpected_error_title="Error running health checks",
            interrupted_message="Health checks interrupted by user (Ctrl+C)",
        )
        return
    except CLI_ENTRYPOINT_TYPED_ERRORS as exc:
        _handle_health_failure(
            exc,
            reason_code="CLI_HEALTH_CHECK_UNEXPECTED_ERROR",
            target=providers_subject,
            domain_error_title="Error running health checks",
            unexpected_error_title="Error running health checks",
            interrupted_message="Health checks interrupted by user (Ctrl+C)",
        )
        return
    finally:
        if getattr(coro, "cr_frame", None) is not None:
            coro.close()

    all_healthy = all(
        result.get("status", "unknown") == "healthy" for result in results.values()
    )
    if output_json:
        click.echo(json_module.dumps(results, indent=2))
        sys.exit(ExitCode.OK if all_healthy else ExitCode.FAIL)
    else:
        for prov, result in results.items():
            status = result.get("status", "unknown")
            status_icon = (
                "[OK]"
                if status == "healthy"
                else "[WARN]"
                if status == "degraded"
                else "[FAIL]"
            )

            line = f"  {status_icon} {prov}: {status}"
            if "latency_ms" in result:
                line += f" ({result['latency_ms']}ms)"
            if "error" in result:
                line += f" - {result['error']}"

            click.echo(line)

        if all_healthy:
            click.echo("\nAll providers healthy.")
            sys.exit(ExitCode.OK)
        else:
            click.echo("\nSome providers unhealthy.")
            sys.exit(ExitCode.FAIL)


COMMANDS = (health_server_command,)

__all__ = ["health"]
