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
from bioetl.interfaces.cli.exit_codes import ExitCode


@click.group()
def health() -> None:
    """Health check and monitoring operations."""
    pass


@health.command("server")
@click.option(
    "--host",
    default="0.0.0.0",
    help="Host to bind to.",
    show_default=True,
)
@click.option(
    "--port",
    "-p",
    default=8080,
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
        bioetl health server --port 8080
    """
    click.echo(f"Starting health server on http://{host}:{port}")
    click.echo("Endpoints:")
    click.echo(f"  - http://{host}:{port}/health")
    click.echo(f"  - http://{host}:{port}/health/live")
    click.echo(f"  - http://{host}:{port}/health/ready")
    click.echo(f"  - http://{host}:{port}/health/providers")
    click.echo("\nPress Ctrl+C to stop.")

    async def run() -> None:
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

    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        click.echo("\nShutting down...")
        sys.exit(ExitCode.OK.value)


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
    """
    import json as json_module

    click.echo("Running health checks...")

    async def run_checks() -> dict[str, dict[str, str]]:
        service = get_health_service()

        # Convert tuple to list or None for all providers
        providers_list = list(provider) if provider else None

        summary = await service.check_providers(providers=providers_list)

        # Convert to dict format for backward compatibility
        return summary.to_dict()

    try:
        results = asyncio.run(run_checks())
    except Exception as e:
        click.echo(f"Error running health checks: {e}", err=True)
        sys.exit(ExitCode.FAIL.value)

    if output_json:
        click.echo(json_module.dumps(results, indent=2))
    else:
        all_healthy = True
        for prov, result in results.items():
            status = result.get("status", "unknown")
            status_icon = (
                "[OK]"
                if status == "healthy"
                else "[WARN]" if status == "degraded" else "[FAIL]"
            )

            if status != "healthy":
                all_healthy = False

            line = f"  {status_icon} {prov}: {status}"
            if "latency_ms" in result:
                line += f" ({result['latency_ms']}ms)"
            if "error" in result:
                line += f" - {result['error']}"

            click.echo(line)

        if all_healthy:
            click.echo("\nAll providers healthy.")
            sys.exit(ExitCode.OK.value)
        else:
            click.echo("\nSome providers unhealthy.")
            sys.exit(ExitCode.FAIL.value)


__all__ = ["health"]
