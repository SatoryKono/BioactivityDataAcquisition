================================================================================
File: __init__.py
Path: __init__.py
================================================================================
"""User interfaces for BioETL.

This package contains user-facing interfaces for the BioETL system.
Currently provides CLI and observability interfaces.

Components:
    cli: Command-line interface (Click-based).
    observability: User-facing observability utilities.

The interfaces layer sits at the outermost ring of the hexagonal
architecture and depends on all other layers per RULES.md.
"""

================================================================================
File: __init__.py
Path: cli\__init__.py
================================================================================
"""CLI package for BioETL.

Provides command-line interface for pipeline operations.
This package follows the thin controller pattern - commands delegate
to Application services for all business logic.

Structure:
    cli/
    ├── __init__.py      # Package exports
    ├── main.py          # CLI entry point
    ├── formatters.py    # Output formatters
    └── commands/        # Individual command modules
        ├── run.py       # bioetl run
        ├── checkpoint.py# bioetl checkpoint
        ├── quarantine.py# bioetl quarantine
        └── maintenance.py# bioetl maintenance
"""

from __future__ import annotations

# Re-export entrypoint functions for convenience
from bioetl.composition.entrypoints import create_pipeline_runner
from bioetl.composition.registry import get_default_registry
from bioetl.interfaces.cli.commands.run_helpers import validate_pipeline_name
from bioetl.interfaces.cli.main import cli, main

__all__ = [
    "cli",
    "create_pipeline_runner",
    "get_default_registry",
    "main",
    "validate_pipeline_name",
]

================================================================================
File: __main__.py
Path: cli\__main__.py
================================================================================
"""Entry point for running CLI as a module.

Allows: python -m bioetl.interfaces.cli [commands]
"""

from bioetl.interfaces.cli.main import main

if __name__ == "__main__":
    main()

================================================================================
File: __init__.py
Path: cli\commands\__init__.py
================================================================================
"""CLI commands package for BioETL.

Each module contains a single command group or standalone command.
All commands are thin wrappers that delegate to Application services.
"""

from __future__ import annotations

================================================================================
File: archive.py
Path: cli\commands\archive.py
================================================================================
"""Archive command for BioETL CLI.

Implements table archival to cold storage.
"""

from __future__ import annotations

import asyncio

import click

from bioetl.composition.entrypoints import get_lifecycle_service
from bioetl.interfaces.cli.formatters import echo_info


@click.command("archive")
@click.argument("table")
@click.argument("target_path")
@click.option(
    "--remove-source",
    is_flag=True,
    help="Remove source table after archiving",
)
def archive_command(table: str, target_path: str, remove_source: bool) -> None:
    """Archive Delta table to cold storage.

    TABLE: Table name to archive

    TARGET_PATH: Destination path for archive

    Examples:

        bioetl maintenance archive chembl.activity /archive/chembl

        bioetl maintenance archive chembl.activity /archive/chembl --remove-source
    """
    lifecycle = get_lifecycle_service()

    async def _run() -> None:
        files_archived = await lifecycle.archive(
            table=table,
            target_path=target_path,
            remove_source=remove_source,
        )

        echo_info(f"Archived {files_archived} files to {target_path}")

    asyncio.run(_run())

================================================================================
File: checkpoint.py
Path: cli\commands\checkpoint.py
================================================================================
"""Checkpoint management commands for BioETL CLI.

Implements checkpoint listing and management commands.
"""

from __future__ import annotations

import asyncio

import click

from bioetl.composition.entrypoints import get_checkpoint_manager
from bioetl.interfaces.cli.formatters import echo_checkpoint, echo_info


@click.group()
def checkpoint() -> None:
    """Manage checkpoints."""


@checkpoint.command("list")
@click.option("--pipeline", required=True, help="Pipeline name")
def checkpoint_list(pipeline: str) -> None:
    """List all checkpoints."""
    echo_info(f"Listing checkpoints for {pipeline}...")

    checkpoint_manager = get_checkpoint_manager(pipeline)

    async def _list() -> None:
        checkpoints = await checkpoint_manager.list_all()
        for cp in checkpoints:
            echo_checkpoint(cp)

    asyncio.run(_list())

================================================================================
File: cleanup.py
Path: cli\commands\cleanup.py
================================================================================
"""Cleanup commands for BioETL CLI.

Implements Bronze layer cleanup per RULES.md retention policy.
"""

from __future__ import annotations

import asyncio

import click

from bioetl.composition.entrypoints import get_bronze_cleanup_service
from bioetl.interfaces.cli.formatters import (
    echo_dry_run_prefix,
    echo_info,
    format_bytes,
)


@click.command("bronze-cleanup")
@click.option(
    "-r",
    "--retention-days",
    default=90,
    help="Remove files older than N days",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be removed",
)
def bronze_cleanup_command(retention_days: int, dry_run: bool) -> None:
    """Clean up old Bronze files (RULES.md 2.1 retention, default 90 days).

    Examples:

        bioetl maintenance bronze-cleanup

        bioetl maintenance bronze-cleanup --dry-run

        bioetl maintenance bronze-cleanup -r 30
    """
    service = get_bronze_cleanup_service()

    async def _run() -> None:
        if dry_run:
            echo_dry_run_prefix(
                f"Cleanup Bronze files older than {retention_days} days"
            )
        result = await service.cleanup(retention_days=retention_days, dry_run=dry_run)
        action = "Would remove" if dry_run else "Removed"
        echo_info(
            f"{action} {result.files_removed} files ({format_bytes(result.bytes_freed)})"
        )
        echo_info(f"{action} {result.directories_removed} empty directories")

    asyncio.run(_run())

================================================================================
File: config.py
Path: cli\commands\config.py
================================================================================
"""Configuration commands for BioETL CLI.

Implements config inspection and validation commands.
Uses ConfigService from composition entrypoints for clean layering.
"""

from __future__ import annotations

import json
from typing import Any

import click

from bioetl.composition.entrypoints import get_config_service
from bioetl.interfaces.cli.formatters import echo_error, echo_info


def _config_to_dict(config: Any) -> dict[str, Any]:
    """Convert a Pydantic model or dataclass to a JSON-serializable dict."""
    if hasattr(config, "model_dump"):
        result: dict[str, Any] = config.model_dump()
        return result
    if hasattr(config, "__dict__"):
        converted: dict[str, Any] = {
            k: _config_to_dict(v) if hasattr(v, "__dict__") else v
            for k, v in config.__dict__.items()
            if not k.startswith("_")
        }
        return converted
    return {"value": config}  # Wrap primitives in a dict


@click.group()
def config() -> None:
    """View and validate configuration."""


@config.command("show")
@click.argument("pipeline")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["json", "yaml"]),
    default="yaml",
    help="Output format",
)
def show_command(pipeline: str, output_format: str) -> None:
    """Show configuration for a pipeline.

    PIPELINE: Name of the pipeline (e.g., chembl_activity)

    Examples:

        bioetl config show chembl_activity

        bioetl config show chembl_activity --format json
    """
    service = get_config_service()

    try:
        config_dict = service.get_pipeline_yaml_config(pipeline)
    except ValueError as e:
        echo_error("Configuration error", str(e))
        return
    except FileNotFoundError as e:
        echo_error("Config file not found", str(e))
        return

    if output_format == "json":
        echo_info(json.dumps(config_dict, indent=2, default=str))
    else:
        import yaml

        echo_info(yaml.dump(config_dict, default_flow_style=False, sort_keys=False))


@config.command("validate")
@click.argument("pipeline")
def validate_command(pipeline: str) -> None:
    """Validate configuration for a pipeline.

    PIPELINE: Name of the pipeline (e.g., chembl_activity)

    Examples:

        bioetl config validate chembl_activity
    """
    service = get_config_service()

    try:
        info = service.validate_pipeline_config(pipeline)
        echo_info(f"Configuration valid for {pipeline}")
        echo_info(f"  Provider: {info.provider}")
        echo_info(f"  Entity type: {info.entity_type}")
        echo_info(f"  Silver table: {info.silver_table}")
        if info.gold_table:
            echo_info(f"  Gold table: {info.gold_table}")
    except ValueError as e:
        echo_error("Configuration invalid", str(e))
    except FileNotFoundError as e:
        echo_error("Config file not found", str(e))


@config.command("show-settings")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["json", "yaml"]),
    default="yaml",
    help="Output format",
)
def show_settings_command(output_format: str) -> None:
    """Show global application settings.

    Displays environment-based configuration from BIOETL_* variables.

    Examples:

        bioetl config show-settings

        bioetl config show-settings --format json
    """
    service = get_config_service()
    settings_info = service.get_settings()

    # Convert SettingsInfo to dict for output
    settings_dict: dict[str, Any] = {
        "env": settings_info.env,
        "data_dir": settings_info.data_dir,
        "bronze_path": settings_info.bronze_path,
        "silver_path": settings_info.silver_path,
        "gold_path": settings_info.gold_path,
        "checkpoint_path": settings_info.checkpoint_path,
        "quarantine_path": settings_info.quarantine_path,
        "debug": settings_info.debug,
        "test_mode": settings_info.test_mode,
        "metrics_enabled": settings_info.metrics_enabled,
        "metrics_port": settings_info.metrics_port,
        "batch_size": settings_info.batch_size,
    }

    # Add additional settings (with sensitive values masked)
    for key, value in settings_info.additional.items():
        if "api_key" in key.lower() or "password" in key.lower():
            settings_dict[key] = "***MASKED***"
        else:
            settings_dict[key] = value

    if output_format == "json":
        echo_info(json.dumps(settings_dict, indent=2, default=str))
    else:
        import yaml

        echo_info(yaml.dump(settings_dict, default_flow_style=False, sort_keys=False))


@config.command("list-pipelines")
def list_pipelines_command() -> None:
    """List all registered pipelines.

    Examples:

        bioetl config list-pipelines
    """
    service = get_config_service()
    pipelines = service.list_pipelines()

    if not pipelines:
        echo_info("No pipelines registered.")
        return

    echo_info("Available pipelines:")
    for pipeline in sorted(pipelines):
        echo_info(f"  - {pipeline}")

================================================================================
File: export.py
Path: cli\commands\export.py
================================================================================
"""Export commands for BioETL CLI.

Provides commands to export Silver/Gold Delta Lake tables
to CSV, XLSX, and TSV formats.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import click

from bioetl.application.services import ExportOptions
from bioetl.composition.entrypoints import get_export_service
from bioetl.interfaces.cli.formatters import (
    echo_error,
    echo_export_preview,
    echo_export_result,
    echo_info,
    echo_table_list,
)


@click.command("export")
@click.argument("table", required=False)
@click.option(
    "--list",
    "list_tables",
    is_flag=True,
    help="List all available Delta tables",
)
@click.option(
    "--preview",
    is_flag=True,
    help="Show table schema and sample data",
)
@click.option(
    "--format",
    "-f",
    "output_format",
    type=click.Choice(["csv", "xlsx", "tsv"]),
    default="csv",
    help="Output format (default: csv)",
)
@click.option(
    "--layer",
    "-l",
    type=click.Choice(["silver", "gold"]),
    default="silver",
    help="Medallion layer to export from (default: silver)",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    help="Output directory (default: data/exports)",
)
@click.option(
    "--limit",
    type=int,
    help="Maximum number of rows to export",
)
@click.option(
    "--columns",
    "-c",
    help="Comma-separated list of columns to include",
)
def export_command(
    table: str | None,
    list_tables: bool,
    preview: bool,
    output_format: str,
    layer: str,
    output: Path | None,
    limit: int | None,
    columns: str | None,
) -> None:
    """Export Delta Lake tables to CSV, XLSX, or TSV format.

    TABLE: Table name in format "provider.entity" (e.g., chembl.activity)

    Examples:

        # List all available tables
        bioetl export --list

        # List only Silver layer tables
        bioetl export --list --layer silver

        # Preview table schema and sample data
        bioetl export chembl.activity --preview

        # Export to CSV (default)
        bioetl export chembl.activity

        # Export to Excel format
        bioetl export chembl.activity --format xlsx

        # Export with row limit
        bioetl export chembl.activity --limit 10000

        # Export specific columns
        bioetl export chembl.activity --columns id,name,value

        # Export Gold layer
        bioetl export chembl.activity --layer gold

        # Export to custom directory
        bioetl export chembl.activity -o ./my_exports
    """
    service = get_export_service()

    # Handle --list flag
    if list_tables:
        tables = service.list_tables(layer=layer if layer != "silver" else "all")
        if not tables:
            echo_info("No Delta tables found.")
            return
        echo_table_list(tables)
        return

    # Validate table argument for other operations
    if not table:
        echo_error("TABLE argument is required (or use --list to see available tables)")
        raise SystemExit(1)

    # Handle --preview flag
    if preview:

        async def _preview() -> None:
            try:
                table_preview = await service.preview(table, layer=layer)
                echo_export_preview(table_preview)
            except FileNotFoundError as e:
                echo_error(str(e))
                raise SystemExit(1) from None

        asyncio.run(_preview())
        return

    # Parse columns
    column_list = None
    if columns:
        column_list = [c.strip() for c in columns.split(",")]

    # Build export options
    options = ExportOptions(
        format=output_format,  # type: ignore[arg-type]
        output_path=output,
        limit=limit,
        columns=column_list,
    )

    async def _export() -> None:
        result = await service.export(table, layer=layer, options=options)
        echo_export_result(result)
        if not result.success:
            raise SystemExit(1)

    asyncio.run(_export())

================================================================================
File: health.py
Path: cli\commands\health.py
================================================================================
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

    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        click.echo("\nShutting down...")
        sys.exit(ExitCode.OK)


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
        """Execute health checks and return results as dictionary."""
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
        sys.exit(ExitCode.FAIL)

    if output_json:
        click.echo(json_module.dumps(results, indent=2))
    else:
        all_healthy = True
        for prov, result in results.items():
            status = result.get("status", "unknown")
            status_icon = (
                "[OK]"
                if status == "healthy"
                else "[WARN]"
                if status == "degraded"
                else "[FAIL]"
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
            sys.exit(ExitCode.OK)
        else:
            click.echo("\nSome providers unhealthy.")
            sys.exit(ExitCode.FAIL)


__all__ = ["health"]

================================================================================
File: health_server_integration.py
Path: cli\commands\health_server_integration.py
================================================================================
"""Health server integration for CLI commands.

Provides utilities for running the health server alongside long-running
pipeline operations. The health server exposes Kubernetes-compatible
health probes while pipelines execute.

This module follows the thin controller pattern - it delegates to
composition entrypoints for dependency injection.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

import click

if TYPE_CHECKING:
    from bioetl.interfaces.http.health_server import HealthServer


# Default port for health server during pipeline operations
DEFAULT_HEALTH_SERVER_PORT = 8080


@asynccontextmanager
async def health_server_context(
    enabled: bool,
    host: str = "127.0.0.1",
    port: int = DEFAULT_HEALTH_SERVER_PORT,
) -> AsyncIterator[HealthServer | None]:
    """Context manager that optionally runs a health server.

    When enabled, starts an HTTP health server before yielding and
    gracefully shuts it down afterward. Provides Kubernetes-compatible
    liveness and readiness probes.

    Args:
        enabled: Whether to start the health server.
        host: Host to bind the server to.
        port: Port for the health server.

    Yields:
        HealthServer instance if enabled, None otherwise.

    Example:
        async with health_server_context(enabled=True, port=8080) as server:
            # Health server is running
            await run_pipeline()
        # Health server is stopped
    """
    if not enabled:
        yield None
        return

    # Import here to avoid circular imports and keep interfaces layer clean
    from bioetl.composition.entrypoints import get_health_server_dependencies
    from bioetl.interfaces.http.health_server import HealthServer

    # Get dependencies from composition root (proper DI)
    deps = get_health_server_dependencies()

    server = HealthServer(
        host=host,
        port=port,
        health_monitor=deps.health_monitor,
        logger=deps.logger if hasattr(deps, "logger") else None,
    )

    try:
        await server.start()
        yield server
    finally:
        await server.stop()


def add_health_server_options(cmd: click.Command) -> click.Command:
    """Add health server options to a Click command.

    Adds --health-server/--no-health-server and --health-port options
    to the given command.

    Args:
        cmd: Click command to add options to.

    Returns:
        Modified command with health server options.
    """
    cmd = click.option(
        "--health-server/--no-health-server",
        default=True,
        help="Enable/disable HTTP health server during execution (default: enabled).",
        show_default=True,
    )(cmd)

    cmd = click.option(
        "--health-port",
        type=int,
        default=DEFAULT_HEALTH_SERVER_PORT,
        help="Port for the HTTP health server.",
        show_default=True,
    )(cmd)

    return cmd


def echo_health_server_info(enabled: bool, port: int, host: str = "127.0.0.1") -> None:
    """Output health server status information.

    Args:
        enabled: Whether health server is enabled.
        port: Port the server is listening on.
        host: Host the server is bound to (default: 127.0.0.1 for security).
    """
    if enabled:
        click.echo(f"Health server: http://{host}:{port}/health")


__all__ = [
    "DEFAULT_HEALTH_SERVER_PORT",
    "add_health_server_options",
    "echo_health_server_info",
    "health_server_context",
]

================================================================================
File: lock.py
Path: cli\commands\lock.py
================================================================================
"""Lock management commands for BioETL CLI.

Implements lock release and inspection commands.
Note: Uses in-memory locking - operations only affect current process.
"""

from __future__ import annotations

import asyncio
from typing import cast
from uuid import UUID

import click

from bioetl.composition.entrypoints import get_lock_service
from bioetl.domain.types import RunID
from bioetl.interfaces.cli.formatters import echo_error, echo_info, echo_warning


@click.group()
def lock() -> None:
    """Manage pipeline locks."""


@lock.command("release")
@click.option("--pipeline", required=True, help="Pipeline name (lock key)")
@click.option("--run-id", required=True, help="Run ID that holds the lock")
@click.option("--exclusive", is_flag=True, help="Release exclusive lock")
def release_command(pipeline: str, run_id: str, exclusive: bool) -> None:
    """Release a pipeline lock.

    Use this to clean up stale locks from crashed processes.
    Only works if the specified run-id holds the lock.

    Examples:

        bioetl lock release --pipeline chembl_activity --run-id abc123

        bioetl lock release --pipeline chembl_activity --run-id abc123 --exclusive
    """
    try:
        parsed_run_id = cast(RunID, UUID(run_id))
    except ValueError:
        echo_error("Invalid run-id", "Must be a valid UUID")
        return

    service = get_lock_service()

    async def _run() -> None:
        released = await service.release_lock(
            pipeline_id=pipeline,
            owner_id=parsed_run_id,
            exclusive=exclusive,
        )

        if released:
            echo_info(f"Lock released for {pipeline}")
        else:
            echo_warning(f"Lock not released (not held by run-id {run_id})")

    asyncio.run(_run())


@lock.command("check")
@click.option("--pipeline", required=True, help="Pipeline name (lock key)")
@click.option("--run-id", required=True, help="Run ID to check")
def check_command(pipeline: str, run_id: str) -> None:
    """Check if a lock is held by a specific run-id.

    Examples:

        bioetl lock check --pipeline chembl_activity --run-id abc123
    """
    try:
        parsed_run_id = cast(RunID, UUID(run_id))
    except ValueError:
        echo_error("Invalid run-id", "Must be a valid UUID")
        return

    service = get_lock_service()

    async def _run() -> None:
        is_held = await service.check_lock(
            pipeline_id=pipeline,
            owner_id=parsed_run_id,
        )

        if is_held:
            echo_info(f"Lock for {pipeline} IS held by run-id {run_id}")
        else:
            echo_info(f"Lock for {pipeline} is NOT held by run-id {run_id}")

    asyncio.run(_run())

================================================================================
File: maintenance.py
Path: cli\commands\maintenance.py
================================================================================
"""Maintenance command group for BioETL CLI.

Registers all maintenance-related subcommands for Delta table operations.
This module is a thin orchestrator that imports and registers commands.
"""

from __future__ import annotations

import click

from bioetl.interfaces.cli.commands.archive import archive_command
from bioetl.interfaces.cli.commands.cleanup import bronze_cleanup_command
from bioetl.interfaces.cli.commands.vacuum import vacuum_all_command, vacuum_command


@click.group()
def maintenance() -> None:
    """Maintenance operations for Delta tables."""


# Register all maintenance subcommands
maintenance.add_command(vacuum_command)
maintenance.add_command(vacuum_all_command)
maintenance.add_command(archive_command)
maintenance.add_command(bronze_cleanup_command)

================================================================================
File: metrics_server_integration.py
Path: cli\commands\metrics_server_integration.py
================================================================================
"""Metrics server integration for CLI commands.

Provides utilities for starting the Prometheus metrics HTTP server
alongside pipeline operations. The metrics server exposes Prometheus-compatible
metrics endpoint while pipelines execute.

This module follows the thin controller pattern - it delegates to
composition layer for server startup, keeping side-effects out of bootstrap.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from bioetl.composition.entrypoints import ensure_metrics_server_started

__all__ = [
    "ensure_metrics_server_started",
    "metrics_server_context",
]


@contextmanager
def metrics_server_context() -> Iterator[bool]:
    """Context manager that ensures metrics server is started.

    Starts the Prometheus metrics HTTP server before yielding.
    The server runs as a daemon thread and doesn't need explicit shutdown.

    Yields:
        True if server was started, False if disabled.

    Example:
        with metrics_server_context():
            # Metrics server is running
            await run_pipeline()
        # Server continues running (daemon thread)
    """
    # Re-exported from entrypoints, use directly
    started = ensure_metrics_server_started()
    yield started

================================================================================
File: quarantine.py
Path: cli\commands\quarantine.py
================================================================================
"""Quarantine management commands for BioETL CLI.

Implements quarantine inspection and management commands.
Provides error recovery dashboard functionality (ERR-001).
"""

from __future__ import annotations

import asyncio
import json
import sys
from typing import Any

import click

from bioetl.composition.entrypoints import (
    get_quarantine_manager,
    get_quarantine_service,
)
from bioetl.domain.types import QuarantineRecordStatus
from bioetl.interfaces.cli.exit_codes import ExitCode
from bioetl.interfaces.cli.formatters import (
    echo_error,
    echo_info,
    echo_quarantine_record,
)


@click.group()
def quarantine() -> None:
    """Manage quarantine (failed records).

    Error recovery dashboard commands for inspecting, analyzing,
    and recovering from pipeline failures.
    """


@quarantine.command("inspect")
@click.option("--pipeline", required=True, help="Pipeline name")
@click.option("--limit", type=int, default=100, help="Maximum records to show")
@click.option("--error-code", help="Filter by error code")
def quarantine_inspect(pipeline: str, limit: int, error_code: str | None) -> None:
    """Inspect quarantined records.

    Example:
        bioetl quarantine inspect --pipeline chembl_activity
        bioetl quarantine inspect --pipeline chembl_activity --error-code DQ_MISSING_FIELD
    """
    echo_info(f"Inspecting quarantine for {pipeline} (limit {limit})...")

    quarantine_manager = get_quarantine_manager(pipeline)

    async def _inspect() -> None:
        records = await quarantine_manager.inspect(limit=limit, error_code=error_code)
        if not records:
            echo_info("No records found.")
            return

        for rec in records:
            echo_quarantine_record(rec)

    asyncio.run(_inspect())


@quarantine.command("stats")
@click.option("--pipeline", required=True, help="Pipeline name")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def quarantine_stats(pipeline: str, output_json: bool) -> None:
    """Show quarantine statistics dashboard.

    Displays a summary of quarantined records including:
    - Total count
    - Breakdown by error code
    - Breakdown by status (NEW, REVIEWED, RESOLVED)

    Example:
        bioetl quarantine stats --pipeline chembl_activity
        bioetl quarantine stats --pipeline chembl_activity --json
    """
    quarantine_manager = get_quarantine_manager(pipeline)

    async def _stats() -> dict[str, Any]:
        return await quarantine_manager.get_stats()

    try:
        stats = asyncio.run(_stats())
    except Exception as e:
        echo_error(f"Failed to get stats: {e}")
        sys.exit(ExitCode.FAIL)

    if output_json:
        click.echo(json.dumps(stats, indent=2))
    else:
        click.echo(f"\n{'=' * 50}")
        click.echo(f"  Quarantine Dashboard: {pipeline}")
        click.echo(f"{'=' * 50}")

        total = stats.get("total_count", 0)
        click.echo(f"\n  Total Records: {total}")

        by_error = stats.get("by_error_code", {})
        if by_error:
            click.echo("\n  By Error Code:")
            for code, count in sorted(by_error.items(), key=lambda x: -x[1]):
                pct = (count / total * 100) if total > 0 else 0
                click.echo(f"    - {code}: {count} ({pct:.1f}%)")

        by_status = stats.get("by_status", {})
        if by_status:
            click.echo("\n  By Status:")
            for status, count in sorted(by_status.items()):
                pct = (count / total * 100) if total > 0 else 0
                click.echo(f"    - {status}: {count} ({pct:.1f}%)")

        click.echo(f"\n{'=' * 50}\n")


@quarantine.command("replay")
@click.option("--pipeline", required=True, help="Pipeline name")
@click.option("--error-code", help="Filter by error code")
@click.option(
    "--max-age-days", type=int, default=7, help="Max age of records to replay"
)
@click.option("--dry-run", is_flag=True, help="Show records without replaying")
def quarantine_replay(
    pipeline: str,
    error_code: str | None,
    max_age_days: int,
    dry_run: bool,
) -> None:
    """Replay (retry) quarantined records.

    Retrieves quarantined records for reprocessing by the pipeline.
    Use --dry-run to preview records without actually replaying.

    Example:
        bioetl quarantine replay --pipeline chembl_activity --dry-run
        bioetl quarantine replay --pipeline chembl_activity --error-code DQ_NETWORK_ERROR
    """
    quarantine_service = get_quarantine_service()

    records = quarantine_service.replay(
        pipeline=pipeline,
        error_code=error_code,
        max_age_days=max_age_days,
    )

    if not records:
        echo_info("No records found for replay.")
        return

    if dry_run:
        click.echo(f"\nWould replay {len(records)} record(s):\n")
        for i, rec in enumerate(records[:10], 1):
            payload_hash = rec.get("payload_hash")
            hash_display = payload_hash[:16] if payload_hash else "—"
            click.echo(
                f"  {i}. Error: {rec.get('error_code')} | Hash: {hash_display}..."
            )
        if len(records) > 10:
            click.echo(f"  ... and {len(records) - 10} more")
    else:
        click.echo(f"\nReplaying {len(records)} record(s)...")
        # Mark records as reprocessed
        marked_count = quarantine_service.mark_as_reprocessed(records)
        click.echo(f"Marked {marked_count} record(s) as REPROCESSED.")
        echo_info("Records are ready for reprocessing by the pipeline.")


@quarantine.command("purge")
@click.option("--pipeline", required=True, help="Pipeline name")
@click.option(
    "--older-than-days", type=int, default=30, help="Delete records older than N days"
)
@click.option("--dry-run", is_flag=True, help="Show count without deleting")
@click.option("--force", is_flag=True, help="Skip confirmation prompt")
def quarantine_purge(
    pipeline: str,
    older_than_days: int,
    dry_run: bool,
    force: bool,
) -> None:
    """Purge old quarantine records.

    Deletes quarantined records older than the specified number of days.
    Default retention is 30 days per RULES.md §2.6.

    Example:
        bioetl quarantine purge --pipeline chembl_activity --dry-run
        bioetl quarantine purge --pipeline chembl_activity --older-than-days 60
    """
    quarantine_service = get_quarantine_service()

    if dry_run:
        # Get count of records that would be purged
        async def _get_stats() -> dict[str, Any]:
            return await quarantine_service.get_stats(pipeline)

        stats = asyncio.run(_get_stats())
        total = stats.get("total_count", 0)
        click.echo(f"\nWould purge records older than {older_than_days} days.")
        click.echo(f"Current total in quarantine: {total}")
        click.echo("\nUse without --dry-run to actually purge.")
        return

    if not force:
        click.confirm(
            f"Delete quarantine records older than {older_than_days} days for {pipeline}?",
            abort=True,
        )

    count = quarantine_service.purge(
        pipeline=pipeline,
        older_than_days=older_than_days,
    )

    click.echo(f"Purged {count} record(s) from quarantine.")


@quarantine.command("resolve")
@click.option("--pipeline", required=True, help="Pipeline name")
@click.option("--payload-hash", required=True, help="Payload hash of record to resolve")
@click.option(
    "--status", type=click.Choice(["IGNORED", "REPROCESSED"]), default="IGNORED"
)
def quarantine_resolve(pipeline: str, payload_hash: str, status: str) -> None:
    """Mark a quarantine record as resolved.

    Updates the status of a quarantined record to indicate
    it has been reviewed (IGNORED) or reprocessed (REPROCESSED).

    Status values:
    - IGNORED: Reviewed and marked as non-actionable
    - REPROCESSED: Successfully reprocessed and moved to Silver

    Example:
        bioetl quarantine resolve --pipeline chembl_activity --payload-hash abc123
        bioetl quarantine resolve --pipeline chembl_activity --payload-hash abc123 --status REPROCESSED
    """
    quarantine_service = get_quarantine_service()

    new_status = QuarantineRecordStatus[status]
    success = quarantine_service.update_status(payload_hash, new_status)

    if success:
        click.echo(f"Record {payload_hash} marked as {status}.")
    else:
        echo_error(f"Record not found: {payload_hash}")
        sys.exit(ExitCode.FAIL)


__all__ = ["quarantine"]

================================================================================
File: run.py
Path: cli\commands\run.py
================================================================================
"""Run command for BioETL CLI.

Implements the main pipeline execution command using PipelineRunnerService.
"""

from __future__ import annotations

import asyncio
import sys

import click

from bioetl.application.services import (
    PipelineNotFoundError,
    RunOptions,
    RunStatus,
)
from bioetl.composition.entrypoints import get_pipeline_runner_service
from bioetl.interfaces.cli.commands.health_server_integration import (
    DEFAULT_HEALTH_SERVER_PORT,
    echo_health_server_info,
    health_server_context,
)
from bioetl.interfaces.cli.commands.metrics_server_integration import (
    ensure_metrics_server_started,
)
from bioetl.interfaces.cli.commands.run_helpers import (
    get_runner_logger,
    handle_destructive_run_confirmation,
    show_cleanup_preview,
    validate_pipeline_name,
)
from bioetl.interfaces.cli.exit_codes import ExitCode
from bioetl.interfaces.cli.formatters import echo_error, echo_info, echo_warning


def _map_status_to_exit_code(status: RunStatus, error_type: str | None) -> ExitCode:
    """Map RunStatus to CLI exit code.

    Args:
        status: Run status from service.
        error_type: Exception type name if failed.

    Returns:
        Appropriate ExitCode for the status.
    """
    if status == RunStatus.SUCCESS:
        return ExitCode.OK
    if status == RunStatus.DRY_RUN:
        return ExitCode.OK
    if status == RunStatus.SHUTDOWN:
        return ExitCode.SIGINT
    # FAILED status - map based on error type
    if error_type:
        error_mapping = {
            "ValueError": ExitCode.CONFIG_ERROR,
            "FileNotFoundError": ExitCode.EX_NOINPUT,
            "ConfigValidationError": ExitCode.CONFIG_ERROR,
            "DataQualityError": ExitCode.DATA_QUALITY_ERROR,
            "DataQualityThresholdError": ExitCode.DATA_QUALITY_ERROR,
            "LockAcquisitionError": ExitCode.LOCK_ERROR,
            "LockLostError": ExitCode.LOCK_ERROR,
            "StorageError": ExitCode.STORAGE_ERROR,
            "NetworkError": ExitCode.NETWORK_ERROR,
            "RateLimitError": ExitCode.NETWORK_ERROR,
            "CircuitBreakerOpenError": ExitCode.NETWORK_ERROR,
        }
        return error_mapping.get(error_type, ExitCode.PIPELINE_ERROR)
    return ExitCode.PIPELINE_ERROR


async def _run_pipeline_async(
    pipeline: str,
    options: RunOptions,
    health_server_enabled: bool = True,
    health_port: int = DEFAULT_HEALTH_SERVER_PORT,
) -> tuple[RunStatus, str | None, str | None, str]:
    """Run pipeline asynchronously via service.

    Args:
        pipeline: Pipeline name.
        options: Run options.
        health_server_enabled: Whether to enable health server.
        health_port: Port for health server.

    Returns:
        Tuple of (status, error_message, error_type, run_id).
    """
    # Start metrics server if enabled (side-effect in entrypoint, not bootstrap)
    ensure_metrics_server_started()

    async with health_server_context(
        enabled=health_server_enabled,
        port=health_port,
    ):
        service = get_pipeline_runner_service()
        result = await service.run(pipeline, options=options)
        return result.status, result.error_message, result.error_type, result.run_id


def _echo_run_result(status: RunStatus, error_message: str | None, run_id: str) -> None:
    """Output run result message based on status.

    Args:
        status: Run status from service.
        error_message: Error message if failed.
        run_id: Unique identifier for the pipeline run.
    """
    # Truncate run_id to first 8 chars for readability (like git short hash)
    short_run_id = run_id[:8] if len(run_id) > 8 else run_id

    status_handlers = {
        RunStatus.SUCCESS: lambda: echo_info(
            f"Pipeline completed successfully (run_id: {short_run_id})"
        ),
        RunStatus.DRY_RUN: lambda: echo_info(
            f"Dry-run completed (no changes made) (run_id: {short_run_id})"
        ),
        RunStatus.SHUTDOWN: lambda: echo_warning(
            f"Pipeline was gracefully shut down (run_id: {short_run_id})"
        ),
        RunStatus.FAILED: lambda: echo_error(
            f"Pipeline failed (run_id: {short_run_id})",
            error_message or "Unknown error",
        ),
    }
    handler = status_handlers.get(status)
    if handler:
        handler()


@click.command()
@click.option(
    "--pipeline",
    callback=validate_pipeline_name,
    required=True,
    help="Pipeline to run",
)
@click.option(
    "--run-type",
    type=click.Choice(["incremental", "backfill", "rebuild"]),
    default="incremental",
    help="Type of run",
)
@click.option("--resume", is_flag=True, help="Resume from last checkpoint")
@click.option("--limit", type=int, help="Maximum number of records to process")
@click.option(
    "--input-csv",
    type=click.Path(exists=True),
    help="Path to CSV file with filter IDs",
)
@click.option(
    "--filter-column",
    type=str,
    help="Column name in CSV containing filter IDs (default: 'id')",
)
@click.option(
    "--filter-field",
    type=str,
    help="API field name to filter by (default: 'molecule_chembl_id')",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Preview cleanup without execution (for rebuild/backfill)",
)
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    help="Skip confirmation prompt for rebuild/backfill",
)
@click.option(
    "--vacuum-after-run",
    is_flag=True,
    default=None,
    help="Run VACUUM on Delta tables after successful run (overrides YAML config)",
)
@click.option(
    "--vacuum-retention-days",
    type=int,
    default=None,
    help="Minimum age of files to remove during VACUUM (days, overrides YAML config)",
)
@click.option(
    "--debug",
    is_flag=True,
    help="Enable DEBUG level logging for detailed output",
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
    "--use-cached-bronze/--no-cached-bronze",
    "use_cached_bronze",
    default=True,
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
def run(
    pipeline: str,
    run_type: str,
    resume: bool,
    limit: int | None,
    input_csv: str | None,
    filter_column: str | None,
    filter_field: str | None,
    dry_run: bool,
    yes: bool,
    vacuum_after_run: bool | None,
    vacuum_retention_days: int | None,
    debug: bool,
    health_server: bool,
    health_port: int,
    use_cached_bronze: bool,
    cached_bronze_date: str | None,
    cached_bronze_path: str | None,
) -> None:
    """Run an ETL pipeline."""
    # Handle confirmation for destructive operations (CLI responsibility)
    if not handle_destructive_run_confirmation(pipeline, run_type, dry_run, yes):
        return

    # Build options using application-layer RunOptions
    options = RunOptions(
        run_type=run_type,
        resume=resume,
        limit=limit,
        dry_run=dry_run,
        input_csv=input_csv,
        filter_column=filter_column,
        filter_field=filter_field,
        vacuum_after_run=vacuum_after_run if vacuum_after_run else None,
        vacuum_retention_days=vacuum_retention_days,
        log_level="DEBUG" if debug else "INFO",
        use_cached_bronze=use_cached_bronze,
        cached_bronze_path=cached_bronze_path,
        cached_bronze_date=cached_bronze_date,
    )

    # Display health server info
    echo_health_server_info(health_server, health_port)

    # Run pipeline via service
    try:
        status, error_message, error_type, run_id = asyncio.run(
            _run_pipeline_async(
                pipeline,
                options,
                health_server_enabled=health_server,
                health_port=health_port,
            )
        )
    except PipelineNotFoundError as e:
        echo_error("Pipeline not found", str(e))
        sys.exit(ExitCode.CONFIG_ERROR)
    except KeyboardInterrupt:
        echo_warning("Pipeline interrupted by user (Ctrl+C)")
        sys.exit(ExitCode.SIGINT)
    except Exception as e:
        echo_error("Unexpected error during pipeline execution", str(e))
        sys.exit(ExitCode.FAIL)

    # Map status to exit code and output result
    exit_code = _map_status_to_exit_code(status, error_type)
    _echo_run_result(status, error_message, run_id)
    sys.exit(exit_code)


# Re-export helpers for backward compatibility with tests
# These are imported by tests/unit/interfaces/test_cli.py
_get_runner_logger = get_runner_logger
_handle_destructive_run_confirmation = handle_destructive_run_confirmation
_preview_cleanup = show_cleanup_preview

================================================================================
File: run_all.py
Path: cli\commands\run_all.py
================================================================================
"""Run-all command for executing all pipelines for a specific provider.

Provides a universal command to run all pipelines for a given source (provider),
replacing the need for hardcoded provider-specific commands.
"""

from __future__ import annotations

import asyncio
import sys
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import click

from bioetl.application.services import (
    PipelineNotFoundError,
    RunOptions,
    RunResult,
    RunStatus,
)
from bioetl.composition.entrypoints import get_pipeline_runner_service
from bioetl.composition.registry import get_default_registry
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

if TYPE_CHECKING:
    from bioetl.application.services import PipelineRunnerService


@dataclass
class BatchRunResult:
    """Result of running multiple pipelines."""

    total: int = 0
    succeeded: int = 0
    failed: int = 0
    skipped: int = 0
    results: list[RunResult] = field(default_factory=list)
    failed_pipelines: list[str] = field(default_factory=list)

    @property
    def all_succeeded(self) -> bool:
        """Check if all pipelines succeeded."""
        return self.failed == 0 and self.total > 0


def _get_available_providers() -> list[str]:
    """Get sorted list of unique provider names from registered pipelines."""
    registry = get_default_registry()
    pipelines = registry.list_pipelines()
    providers = {p.split("_")[0] for p in pipelines if "_" in p}
    return sorted(providers)


def _filter_pipelines_by_provider(provider: str) -> list[str]:
    """Filter registered pipelines by provider prefix."""
    registry = get_default_registry()
    all_pipelines = registry.list_pipelines()
    return sorted([name for name in all_pipelines if name.startswith(f"{provider}_")])


def _validate_provider(provider: str) -> tuple[bool, str | None]:
    """Validate that the provider has registered pipelines."""
    available_providers = _get_available_providers()
    if not available_providers:
        return False, "No pipelines are registered."
    pipelines = _filter_pipelines_by_provider(provider)
    if not pipelines:
        return False, (
            f"No pipelines found for provider '{provider}'. "
            f"Available providers: {', '.join(available_providers)}"
        )
    return True, None


async def _run_pipeline_async(
    service: PipelineRunnerService, pipeline: str, options: RunOptions
) -> RunResult:
    """Run a single pipeline asynchronously."""
    return await service.run(pipeline, options=options)


async def _run_pipelines_batch(
    service: PipelineRunnerService, pipelines: list[str], options: RunOptions
) -> BatchRunResult:
    """Run pipelines sequentially within a service context."""
    batch_result = BatchRunResult(total=len(pipelines))

    for pipeline in pipelines:
        try:
            result = await _run_pipeline_async(service, pipeline, options)
            batch_result.results.append(result)

            if result.status == RunStatus.SUCCESS:
                batch_result.succeeded += 1
                echo_info(f"[OK] {pipeline}: completed successfully")
            elif result.status == RunStatus.DRY_RUN:
                batch_result.skipped += 1
                echo_info(f"[DRY] {pipeline}: dry-run (no changes)")
            elif result.status == RunStatus.SHUTDOWN:
                batch_result.skipped += 1
                echo_warning(f"[STOP] {pipeline}: gracefully shut down")
                # Stop processing remaining pipelines on shutdown
                break
            elif result.status == RunStatus.FAILED:
                batch_result.failed += 1
                batch_result.failed_pipelines.append(pipeline)
                echo_error(
                    f"[FAIL] {pipeline}: failed",
                    result.error_message or "Unknown error",
                )
        except PipelineNotFoundError as e:
            batch_result.failed += 1
            batch_result.failed_pipelines.append(pipeline)
            echo_error(f"[FAIL] {pipeline}: not found", str(e))
        except Exception as e:
            batch_result.failed += 1
            batch_result.failed_pipelines.append(pipeline)
            echo_error(f"[FAIL] {pipeline}: unexpected error", str(e))

    return batch_result


async def _run_all_pipelines_async(
    pipelines: list[str],
    options: RunOptions,
    health_server_enabled: bool = True,
    health_port: int = DEFAULT_HEALTH_SERVER_PORT,
) -> BatchRunResult:
    """Run all pipelines sequentially with optional health server."""
    # Start metrics server if enabled (side-effect in entrypoint, not bootstrap)
    ensure_metrics_server_started()

    async with health_server_context(enabled=health_server_enabled, port=health_port):
        service = get_pipeline_runner_service()
        return await _run_pipelines_batch(service, pipelines, options)


def _echo_batch_summary(result: BatchRunResult, dry_run: bool) -> None:
    """Output batch run summary."""
    echo_info("")
    echo_info("=" * 50)

    if dry_run:
        echo_info(f"Dry-run complete: {result.total} pipelines previewed")
    else:
        echo_info(f"Batch run complete: {result.total} pipelines")
        echo_info(f"  Succeeded: {result.succeeded}")
        if result.failed > 0:
            echo_info(f"  Failed: {result.failed}")
        if result.skipped > 0:
            echo_info(f"  Skipped: {result.skipped}")

    if result.failed_pipelines:
        echo_error("Failed pipelines:", ", ".join(result.failed_pipelines))


def _handle_list_only(source: str, pipelines: list[str]) -> None:
    """Handle --list-only mode and exit."""
    echo_info(f"Pipelines for provider '{source}':")
    for pipeline in pipelines:
        echo_info(f"  - {pipeline}")
    echo_info(f"\nTotal: {len(pipelines)} pipeline(s)")
    sys.exit(ExitCode.OK)


def _handle_destructive_confirmation(
    run_type: str, pipelines: list[str], dry_run: bool, yes: bool
) -> bool:
    """Handle confirmation for destructive operations.

    Returns:
        True if should continue, False if cancelled.
    """
    if run_type not in ("rebuild", "backfill") or dry_run or yes:
        return True

    echo_warning(f"{run_type} will clear existing data for {len(pipelines)} pipelines.")
    echo_info("Pipelines to be affected:")
    for pipeline in pipelines:
        echo_info(f"  - {pipeline}")

    if not click.confirm("\nDo you want to continue?"):
        echo_info("Operation cancelled.")
        sys.exit(ExitCode.OK)
    return True


def _show_run_preview(source: str, pipelines: list[str], dry_run: bool) -> None:
    """Show what pipelines will be run."""
    if dry_run:
        echo_info(f"[DRY-RUN] Would run {len(pipelines)} pipeline(s) for '{source}':")
    else:
        echo_info(f"Running {len(pipelines)} pipeline(s) for '{source}':")

    for pipeline in pipelines:
        echo_info(f"  - {pipeline}")
    echo_info("")


def _determine_exit_code(batch_result: BatchRunResult) -> ExitCode:
    """Determine exit code from batch result."""
    if batch_result.all_succeeded:
        return ExitCode.OK
    if batch_result.failed > 0:
        return ExitCode.PIPELINE_ERROR
    # All skipped (shutdown)
    return ExitCode.SIGINT


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
def run_all(
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
    """Run all ETL pipelines for a specific provider.

    Executes all registered pipelines matching the given source (provider).
    Pipelines are run sequentially in alphabetical order.

    Examples:

        bioetl run-all --source chembl

        bioetl run-all --source chembl --list-only

        bioetl run-all --source pubchem --dry-run

        bioetl run-all --source chembl --run-type rebuild --yes
    """
    # Validate provider has pipelines
    is_valid, error_msg = _validate_provider(source)
    if not is_valid:
        echo_error("Provider error", error_msg)
        sys.exit(ExitCode.FAIL)

    # Get pipelines for provider
    pipelines = _filter_pipelines_by_provider(source)

    # Handle --list-only mode
    if list_only:
        _handle_list_only(source, pipelines)

    # Handle confirmation for destructive operations (CLI responsibility)
    _handle_destructive_confirmation(run_type, pipelines, dry_run, yes)

    # Show what we're about to do
    _show_run_preview(source, pipelines, dry_run)

    # Display health server info
    echo_health_server_info(health_server, health_port)

    # Build options and run pipelines
    options = RunOptions(
        run_type=run_type,
        limit=limit,
        dry_run=dry_run,
        log_level="DEBUG" if debug else "INFO",
    )

    try:
        batch_result = asyncio.run(
            _run_all_pipelines_async(
                pipelines,
                options,
                health_server_enabled=health_server,
                health_port=health_port,
            )
        )
    except KeyboardInterrupt:
        echo_warning("Batch run interrupted by user (Ctrl+C)")
        sys.exit(ExitCode.SIGINT)
    except Exception as e:
        echo_error("Unexpected error during batch execution", str(e))
        sys.exit(ExitCode.FAIL)

    # Output summary and exit
    _echo_batch_summary(batch_result, dry_run)
    sys.exit(_determine_exit_code(batch_result))


__all__ = [
    "BatchRunResult",
    "run_all",
]

================================================================================
File: run_composite.py
Path: cli\commands\run_composite.py
================================================================================
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
    default=True,
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

================================================================================
File: run_helpers.py
Path: cli\commands\run_helpers.py
================================================================================
"""Helper functions for the run command.

Provides validation, confirmation, and preview utilities for pipeline execution.
These are CLI-layer responsibilities separated for maintainability.
"""

from __future__ import annotations

import asyncio
import sys
from typing import TYPE_CHECKING

import click

__all__ = [
    "get_runner_logger",
    "handle_destructive_run_confirmation",
    "show_cleanup_preview",
    "validate_pipeline_name",
]

from bioetl.composition.entrypoints import preview_cleanup
from bioetl.composition.registry import get_default_registry
from bioetl.interfaces.cli.exit_codes import ExitCode
from bioetl.interfaces.cli.formatters import (
    echo_cleanup_preview,
    echo_dry_run_prefix,
    echo_error,
    echo_info,
    echo_warning,
)

if TYPE_CHECKING:
    from bioetl.application.core.runner import PipelineRunner
    from bioetl.domain.ports import LoggerPort


def validate_pipeline_name(
    _ctx: click.Context | None, _param: click.Parameter | None, value: str
) -> str:
    """Validate pipeline name against the registry at runtime.

    Args:
        _ctx: Click context (unused).
        _param: Click parameter (unused).
        value: Pipeline name to validate.

    Returns:
        Validated pipeline name.

    Raises:
        click.BadParameter: If pipeline name is not in registry.
    """
    registry = get_default_registry()
    available = registry.list_pipelines()
    if value not in available:
        raise click.BadParameter(f"Unknown pipeline: {value}. Available: {available}")
    return value


def get_runner_logger(runner: PipelineRunner) -> LoggerPort | None:
    """Get logger from runner with fallback.

    Args:
        runner: PipelineRunner instance.

    Returns:
        Logger instance (LoggerPort) or None if not found.
    """
    logger = getattr(runner, "logger", None)
    if logger is None:
        logger = getattr(runner, "_logger", None)
    return logger


async def _preview_cleanup_async(pipeline: str) -> None:
    """Preview what data would be cleared in dry-run mode.

    Args:
        pipeline: Pipeline name.
    """
    preview_result = await preview_cleanup(pipeline)
    echo_cleanup_preview(preview_result)


def show_cleanup_preview(pipeline: str) -> None:
    """Show cleanup preview synchronously.

    Args:
        pipeline: Pipeline name.
    """
    try:
        asyncio.run(_preview_cleanup_async(pipeline))
    except Exception as e:
        echo_error("Error previewing cleanup", str(e))


def handle_destructive_run_confirmation(
    pipeline: str, run_type: str, dry_run: bool, yes: bool
) -> bool:
    """Handle confirmation for rebuild/backfill runs.

    Args:
        pipeline: Pipeline name.
        run_type: Type of run.
        dry_run: Whether this is a dry run.
        yes: Whether to skip confirmation.

    Returns:
        True if should continue with pipeline execution, False if should exit early.
    """
    if run_type not in ("rebuild", "backfill"):
        return True

    if dry_run:
        echo_dry_run_prefix(f"Would clear data for pipeline: {pipeline}")
        echo_dry_run_prefix(f"Run type: {run_type}")
        show_cleanup_preview(pipeline)
        return False

    if not yes:
        echo_warning(f"{run_type} will clear existing data for {pipeline}.")
        if not click.confirm("Do you want to continue?"):
            echo_info("Operation cancelled.")
            sys.exit(ExitCode.OK)

    return True

================================================================================
File: vacuum.py
Path: cli\commands\vacuum.py
================================================================================
"""Vacuum commands for BioETL CLI.

Implements vacuum operations for Delta tables storage reclamation.
"""

from __future__ import annotations

import asyncio

import click

from bioetl.composition.entrypoints import get_lifecycle_service, get_vacuum_service
from bioetl.interfaces.cli.formatters import (
    echo_dry_run_prefix,
    echo_info,
    echo_vacuum_all_summary,
    echo_vacuum_result,
)


@click.command("vacuum")
@click.argument("table")
@click.option(
    "--retention-days",
    "-r",
    default=7,
    help="Minimum age of files to remove (days)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be removed without removing",
)
def vacuum_command(table: str, retention_days: int, dry_run: bool) -> None:
    """Vacuum Delta table to reclaim storage space.

    TABLE: Table name in format "provider.entity" (e.g., chembl.activity)

    Examples:

        bioetl maintenance vacuum chembl.activity

        bioetl maintenance vacuum chembl.activity --dry-run

        bioetl maintenance vacuum chembl.activity -r 30
    """
    lifecycle = get_lifecycle_service()

    async def _run() -> None:
        if dry_run:
            echo_dry_run_prefix(f"Would vacuum {table} (retention: {retention_days}d)")

        files_removed = await lifecycle.vacuum(
            table=table,
            retention_days=retention_days,
            dry_run=dry_run,
        )

        if dry_run:
            echo_info(f"Would remove {files_removed} files")
        else:
            echo_info(f"Removed {files_removed} files")

    asyncio.run(_run())


@click.command("vacuum-all")
@click.option(
    "--retention-days",
    "-r",
    default=7,
    help="Minimum age of files to remove (days)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be removed without removing",
)
@click.option(
    "--layer",
    type=click.Choice(["all", "silver", "gold"]),
    default="all",
    help="Which layer to vacuum (default: all)",
)
def vacuum_all_command(retention_days: int, dry_run: bool, layer: str) -> None:
    """Vacuum all Delta tables to reclaim storage space.

    Runs VACUUM on all registered Silver and Gold tables.

    Examples:

        bioetl maintenance vacuum-all

        bioetl maintenance vacuum-all --dry-run

        bioetl maintenance vacuum-all -r 30

        bioetl maintenance vacuum-all --layer silver
    """
    service = get_vacuum_service()
    tables_to_vacuum = service.collect_tables(layer)

    if not tables_to_vacuum:
        echo_info("No tables found to vacuum.")
        return

    async def _run() -> None:
        result = await service.vacuum_all(
            tables=tables_to_vacuum,
            retention_days=retention_days,
            dry_run=dry_run,
        )

        for table_result in result.results:
            echo_vacuum_result(table_result, dry_run)

        echo_vacuum_all_summary(result)

    asyncio.run(_run())

================================================================================
File: exit_codes.py
Path: cli\exit_codes.py
================================================================================
"""Standardized CLI exit codes for BioETL.

Exit codes follow Unix conventions and sysexits.h standards:
- 0: Success (EX_OK)
- 1: General errors (EX_FAIL)
- 64-78: Reserved for standard exit codes

Custom BioETL codes (80-99) for specific scenarios.

References:
- BSD sysexits.h: https://man.freebsd.org/cgi/man.cgi?query=sysexits
- POSIX: https://pubs.opengroup.org/onlinepubs/9699919799/utilities/V3_chap02.html
"""

from __future__ import annotations

from enum import IntEnum


class ExitCode(IntEnum):
    """Standardized exit codes for CLI commands.

    Follows Unix conventions with custom BioETL-specific codes.
    """

    # Success
    OK = 0  # Successful execution

    # General errors (1-63 reserved)
    FAIL = 1  # Unspecified error

    # Standard sysexits.h codes (64-78)
    EX_USAGE = 64  # Command line usage error
    EX_DATAERR = 65  # Data format error
    EX_NOINPUT = 66  # Cannot open input
    EX_NOUSER = 67  # Addressee unknown
    EX_NOHOST = 68  # Host name unknown
    EX_UNAVAILABLE = 69  # Service unavailable
    EX_SOFTWARE = 70  # Internal software error
    EX_OSERR = 71  # System error (e.g., can't fork)
    EX_OSFILE = 72  # Critical OS file missing
    EX_CANTCREAT = 73  # Can't create output file
    EX_IOERR = 74  # Input/output error
    EX_TEMPFAIL = 75  # Temporary failure; user can retry
    EX_PROTOCOL = 76  # Remote error in protocol
    EX_NOPERM = 77  # Permission denied
    EX_CONFIG = 78  # Configuration error

    # BioETL-specific codes (80-99)
    CONFIG_ERROR = 80  # Pipeline configuration error
    INIT_ERROR = 81  # Initialization failure
    PIPELINE_ERROR = 82  # Pipeline execution error
    DATA_QUALITY_ERROR = 83  # Data quality threshold exceeded
    LOCK_ERROR = 84  # Lock acquisition/validation failure
    STORAGE_ERROR = 85  # Storage operation failure
    NETWORK_ERROR = 86  # Network/API error
    CHECKPOINT_ERROR = 87  # Checkpoint save/load failure

    # Signal-related (128 + signal number)
    SIGINT = 130  # Interrupted by SIGINT (Ctrl+C) [128 + 2]
    SIGTERM = 143  # Terminated by SIGTERM [128 + 15]


# Mapping of exception types to exit codes
# Used by CLI error handlers to determine appropriate exit codes
EXCEPTION_EXIT_CODES: dict[str, ExitCode] = {
    # Critical errors
    "CriticalError": ExitCode.FAIL,
    "InfrastructureError": ExitCode.STORAGE_ERROR,
    "LockAcquisitionError": ExitCode.LOCK_ERROR,
    "LockLostError": ExitCode.LOCK_ERROR,
    "StorageError": ExitCode.STORAGE_ERROR,
    # Configuration errors
    "ValueError": ExitCode.CONFIG_ERROR,
    "FileNotFoundError": ExitCode.EX_NOINPUT,
    "ConfigValidationError": ExitCode.CONFIG_ERROR,
    # Data quality errors
    "DataQualityError": ExitCode.DATA_QUALITY_ERROR,
    "DataQualityThresholdError": ExitCode.DATA_QUALITY_ERROR,
    "SchemaViolationError": ExitCode.DATA_QUALITY_ERROR,
    # Network errors
    "NetworkError": ExitCode.NETWORK_ERROR,
    "RateLimitError": ExitCode.NETWORK_ERROR,
    "ApiError": ExitCode.NETWORK_ERROR,
    "CircuitBreakerOpenError": ExitCode.NETWORK_ERROR,
    # Recoverable errors (temporary failures)
    "RecoverableError": ExitCode.EX_TEMPFAIL,
    "RetryExhaustedError": ExitCode.EX_TEMPFAIL,
    # Shutdown
    "PipelineShutdownError": ExitCode.SIGINT,
    "KeyboardInterrupt": ExitCode.SIGINT,
}


def get_exit_code_for_exception(exc: BaseException) -> ExitCode:
    """Get the appropriate exit code for an exception.

    Args:
        exc: The exception to get exit code for.

    Returns:
        The appropriate ExitCode, defaulting to FAIL for unknown exceptions.

    """
    exc_type_name = type(exc).__name__

    # Check direct mapping first
    if exc_type_name in EXCEPTION_EXIT_CODES:
        return EXCEPTION_EXIT_CODES[exc_type_name]

    # Check MRO for parent class mappings
    for base_class in type(exc).__mro__:
        base_name = base_class.__name__
        if base_name in EXCEPTION_EXIT_CODES:
            return EXCEPTION_EXIT_CODES[base_name]

    return ExitCode.FAIL


__all__ = [
    "EXCEPTION_EXIT_CODES",
    "ExitCode",
    "get_exit_code_for_exception",
]

================================================================================
File: formatters.py
Path: cli\formatters.py
================================================================================
"""CLI output formatters for BioETL.

Provides formatting utilities for CLI output. These are pure presentation
functions without business logic - they only transform data into
human-readable format.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import click

if TYPE_CHECKING:
    from bioetl.application.core.cleanup_service import CleanupPreview
    from bioetl.application.services import (
        ExportResult,
        TableInfo,
        TablePreview,
        TableVacuumResult,
        VacuumAllResult,
    )


def format_bytes(b: int) -> str:
    """Format bytes as human-readable string.

    Args:
        b: Number of bytes.

    Returns:
        Human-readable string (e.g., "1.5 GB", "256 KB").
    """
    for unit, divisor in [("GB", 1024**3), ("MB", 1024**2), ("KB", 1024)]:
        if b >= divisor:
            return f"{b / divisor:.2f} {unit}"
    return f"{b} bytes"


def echo_cleanup_preview(preview: CleanupPreview) -> None:
    """Output cleanup preview information.

    Args:
        preview: CleanupPreview with information about what would be cleared.
    """
    click.echo("\nFiles/directories that would be cleared:")

    if preview.silver.exists:
        click.echo(
            f"  Silver: {preview.silver.path} ({preview.silver.file_count} files)"
        )
    else:
        click.echo(f"  Silver: {preview.silver.path} (does not exist)")

    if preview.gold:
        if preview.gold.exists:
            click.echo(f"  Gold: {preview.gold.path} ({preview.gold.file_count} files)")
        else:
            click.echo(f"  Gold: {preview.gold.path} (does not exist)")

    click.echo(f"\nTotal items that would be cleared: ~{preview.total_files}")
    click.echo("\nNo changes were made (dry-run mode).")


def echo_vacuum_result(result: TableVacuumResult, dry_run: bool) -> None:
    """Output vacuum result for a single table.

    Args:
        result: TableVacuumResult with operation outcome.
        dry_run: Whether this was a dry run.
    """
    prefix = "[DRY-RUN] " if dry_run else ""
    action = "Would vacuum" if dry_run else "Vacuuming"

    click.echo(f"{prefix}{action} {result.layer}/{result.table_name}...")

    if result.error:
        click.echo(f"  Error: {result.error}", err=True)
    else:
        result_verb = "Would remove" if dry_run else "Removed"
        click.echo(f"  {result_verb} {result.files_removed} files")


def echo_vacuum_all_summary(result: VacuumAllResult) -> None:
    """Output summary for vacuum-all operation.

    Args:
        result: VacuumAllResult with aggregated statistics.
    """
    result_verb = "would remove" if result.dry_run else "removed"
    click.echo(f"\nTotal: {result_verb} {result.total_files_removed} files")

    if result.failed_tables:
        click.echo(f"Failed tables: {', '.join(result.failed_tables)}", err=True)


def echo_quarantine_record(record: dict[str, Any]) -> None:
    """Output a single quarantine record.

    Args:
        record: Dictionary with quarantine record data.
    """
    error_code = record.get("error_code") or "UNKNOWN"
    payload = record.get("payload")
    payload_display = payload if payload is not None else "—"
    click.echo(f"Error: {error_code} | Payload: {payload_display}")


def echo_checkpoint(checkpoint: str) -> None:
    """Output a single checkpoint entry.

    Args:
        checkpoint: Checkpoint identifier string.
    """
    click.echo(f"- {checkpoint}")


def echo_error(message: str, detail: str | None = None) -> None:
    """Output error message to stderr.

    Args:
        message: Main error message.
        detail: Optional additional detail.
    """
    if detail:
        click.echo(f"{message}: {detail}", err=True)
    else:
        click.echo(message, err=True)


def echo_info(message: str) -> None:
    """Output informational message.

    Args:
        message: Message to output.
    """
    click.echo(message)


def echo_warning(message: str) -> None:
    """Output warning message.

    Args:
        message: Warning message to output.
    """
    click.echo(f"WARNING: {message}")


def echo_dry_run_prefix(message: str) -> None:
    """Output message with dry-run prefix.

    Args:
        message: Message to prefix with [DRY-RUN].
    """
    click.echo(f"[DRY-RUN] {message}")


# =============================================================================
# Export formatters
# =============================================================================


def echo_table_list(tables: list[TableInfo]) -> None:
    """Output list of available Delta tables.

    Args:
        tables: List of TableInfo objects to display.
    """
    click.echo("\nAvailable Delta tables:\n")

    current_layer = ""
    for table in tables:
        if table.layer != current_layer:
            current_layer = table.layer
            click.echo(f"  {current_layer.upper()}:")

        click.echo(f"    {table.name}")

    click.echo()


def echo_export_preview(preview: TablePreview) -> None:
    """Output table preview with schema and sample data.

    Args:
        preview: TablePreview with schema and sample rows.
    """
    click.echo(f"\nTable: {preview.table_name} ({preview.layer})")
    click.echo(f"Rows: {preview.row_count:,}")
    click.echo(f"\nSchema ({len(preview.columns)} columns):")

    for col in preview.columns:
        nullable = " (nullable)" if col.nullable else ""
        click.echo(f"  {col.name}: {col.type}{nullable}")

    if preview.sample_rows:
        click.echo(f"\nSample data ({len(preview.sample_rows)} rows):")
        click.echo("-" * 60)

        # Get column names for header
        if preview.columns:
            col_names = [c.name for c in preview.columns[:5]]  # First 5 cols
            if len(preview.columns) > 5:
                col_names.append("...")
            click.echo(" | ".join(col_names))
            click.echo("-" * 60)

        # Display sample rows
        for row in preview.sample_rows:
            values = []
            for col in preview.columns[:5]:
                val = row.get(col.name, "")
                # Truncate long values
                val_str = str(val)[:30]
                if len(str(val)) > 30:
                    val_str += "..."
                values.append(val_str)
            if len(preview.columns) > 5:
                values.append("...")
            click.echo(" | ".join(values))

    click.echo()


def echo_export_result(result: ExportResult) -> None:
    """Output export operation result.

    Args:
        result: ExportResult with export outcome.
    """
    if result.success:
        click.echo(f"\nExported {result.row_count:,} rows to {result.format.upper()}")
        click.echo(f"Output: {result.output_path}")
    else:
        click.echo(f"\nExport failed: {result.error}", err=True)

================================================================================
File: main.py
Path: cli\main.py
================================================================================
"""Main CLI entry point for BioETL.

This module provides the main Click group and registers all command groups.
It serves as the thin orchestration layer that delegates to Application services.
"""

from __future__ import annotations

import click

from bioetl import __version__
from bioetl.composition.factories.pipeline_factories import register_all_pipelines
from bioetl.interfaces.cli.commands.checkpoint import checkpoint
from bioetl.interfaces.cli.commands.config import config
from bioetl.interfaces.cli.commands.export import export_command
from bioetl.interfaces.cli.commands.health import health
from bioetl.interfaces.cli.commands.lock import lock
from bioetl.interfaces.cli.commands.maintenance import maintenance
from bioetl.interfaces.cli.commands.quarantine import quarantine
from bioetl.interfaces.cli.commands.run import run
from bioetl.interfaces.cli.commands.run_all import run_all
from bioetl.interfaces.cli.commands.run_composite import run_composite


@click.group()
@click.version_option(version=__version__)
def cli() -> None:
    """BioETL - Bioactivity Data ETL Pipeline."""


# Register commands
cli.add_command(run)
cli.add_command(run_all)
cli.add_command(run_composite)
cli.add_command(export_command, name="export")
cli.add_command(quarantine)
cli.add_command(checkpoint)
cli.add_command(config)
cli.add_command(health)
cli.add_command(lock)
cli.add_command(maintenance)


def main() -> None:
    """Main entry point."""
    register_all_pipelines()
    cli()


if __name__ == "__main__":
    main()

================================================================================
File: __init__.py
Path: http\__init__.py
================================================================================
"""HTTP interface module for BioETL.

Provides HTTP endpoints for health checks and monitoring.
"""

from __future__ import annotations

from bioetl.interfaces.http.health_server import HealthServer
from bioetl.interfaces.http.types import HealthResponse

__all__ = ["HealthResponse", "HealthServer"]

================================================================================
File: health_server.py
Path: http\health_server.py
================================================================================
"""HTTP Health Server for BioETL.

Provides Kubernetes-compatible liveness and readiness probes.
"""

from __future__ import annotations

import asyncio
import json
import time
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from bioetl.domain.types import HealthStatus
from bioetl.interfaces.http.types import HealthResponse

if TYPE_CHECKING:
    from bioetl.domain.ports import HealthMonitorPort, LoggerPort


class HealthServer:
    """Async HTTP server for health check endpoints.

    Provides Kubernetes-compatible health probes.
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 8080,
        health_monitor: HealthMonitorPort | None = None,
        logger: LoggerPort | None = None,
    ) -> None:
        """Initialize health server."""
        self.host = host
        self.port = port
        self._health_monitor = health_monitor
        self._logger = logger
        self._server: asyncio.Server | None = None
        self._start_time: float | None = None

    async def start(self) -> None:
        """Start the health server."""
        self._start_time = time.monotonic()
        self._server = await asyncio.start_server(
            self._handle_connection,
            self.host,
            self.port,
        )
        if self._logger:
            self._logger.info("health_server_started", host=self.host, port=self.port)

    async def stop(self) -> None:
        """Stop the health server gracefully."""
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            self._server = None
            if self._logger:
                self._logger.info("health_server_stopped")

    @property
    def is_running(self) -> bool:
        """Check if server is running."""
        return self._server is not None and self._server.is_serving()

    @property
    def uptime_seconds(self) -> float:
        """Get server uptime in seconds."""
        if self._start_time is None:
            return 0.0
        return time.monotonic() - self._start_time

    async def _handle_connection(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        """Handle incoming HTTP connection."""
        try:
            await self._process_request(reader, writer)
        except TimeoutError:
            await self._send_response(writer, 408, "Request Timeout")
        except Exception as e:
            await self._handle_request_error(writer, e)
        finally:
            await self._close_writer(writer)

    async def _process_request(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        """Process incoming HTTP request."""
        request_line = await asyncio.wait_for(reader.readline(), timeout=5.0)
        if not request_line:
            return

        method, path = self._parse_request_line(request_line)
        if method is None or path is None:
            await self._send_response(writer, 400, "Bad Request")
            return

        await self._consume_headers(reader)

        if method != "GET":
            await self._send_response(writer, 405, "Method Not Allowed")
            return

        await self._route_request(writer, path)

    def _parse_request_line(self, request_line: bytes) -> tuple[str | None, str | None]:
        """Parse HTTP request line into method and path."""
        request = request_line.decode("utf-8").strip()
        parts = request.split(" ")
        if len(parts) < 2:
            return None, None
        return parts[0], parts[1]

    async def _consume_headers(self, reader: asyncio.StreamReader) -> None:
        """Read and discard HTTP headers."""
        while True:
            line = await reader.readline()
            if line in (b"\r\n", b"\n", b""):
                break

    async def _handle_request_error(
        self, writer: asyncio.StreamWriter, error: Exception
    ) -> None:
        """Handle request processing error."""
        if self._logger:
            self._logger.error("health_server_error", error=str(error))
        await self._send_response(writer, 500, "Internal Server Error")

    async def _close_writer(self, writer: asyncio.StreamWriter) -> None:
        """Close the stream writer safely."""
        try:
            writer.close()
            await writer.wait_closed()
        except Exception:
            pass

    async def _route_request(self, writer: asyncio.StreamWriter, path: str) -> None:
        """Route request to appropriate handler."""
        path = path.split("?")[0]  # Remove query string
        handlers = {
            "/health": self._handle_health,
            "/healthz": self._handle_health,
            "/health/live": self._handle_liveness,
            "/health/ready": self._handle_readiness,
            "/health/providers": self._handle_providers,
        }
        handler = handlers.get(path)
        if handler:
            response = await handler()
            await self._send_json_response(writer, response)
        else:
            await self._send_response(writer, 404, "Not Found")

    async def _handle_health(self) -> HealthResponse:
        """Handle /health endpoint - overall health status."""
        status = self._get_overall_status()
        checks: dict[str, Any] = {
            "server": {
                "status": "healthy",
                "uptime_seconds": round(self.uptime_seconds, 2),
            },
        }
        if self._health_monitor:
            checks["providers"] = self._get_provider_statuses()
        return HealthResponse(
            status=status.value.lower(),
            timestamp=datetime.now(tz=UTC).isoformat(),
            checks=checks,
        )

    async def _handle_liveness(self) -> HealthResponse:
        """Handle /health/live - Kubernetes liveness probe."""
        return HealthResponse(
            status="healthy",
            timestamp=datetime.now(tz=UTC).isoformat(),
            checks={
                "server": {
                    "status": "healthy",
                    "uptime_seconds": round(self.uptime_seconds, 2),
                }
            },
        )

    async def _handle_readiness(self) -> HealthResponse:
        """Handle /health/ready - Kubernetes readiness probe."""
        if not self._health_monitor:
            return HealthResponse(
                status="healthy",
                timestamp=datetime.now(tz=UTC).isoformat(),
                checks={"message": "No health monitor configured"},
            )
        provider_statuses = self._get_provider_statuses()
        has_unhealthy = any(
            p.get("status") == "unhealthy" for p in provider_statuses.values()
        )
        status = "unhealthy" if has_unhealthy else "healthy"
        return HealthResponse(
            status=status,
            timestamp=datetime.now(tz=UTC).isoformat(),
            checks={"providers": provider_statuses},
        )

    async def _handle_providers(self) -> HealthResponse:
        """Handle /health/providers - detailed provider status."""
        if not self._health_monitor:
            return HealthResponse(
                status="healthy",
                timestamp=datetime.now(tz=UTC).isoformat(),
                checks={"message": "No health monitor configured"},
            )
        return HealthResponse(
            status=self._get_overall_status().value.lower(),
            timestamp=datetime.now(tz=UTC).isoformat(),
            checks={"providers": self._get_provider_statuses()},
        )

    def _get_overall_status(self) -> HealthStatus:
        """Get overall health status from all providers."""
        if not self._health_monitor:
            return HealthStatus.HEALTHY
        states = self._health_monitor.get_all_states()
        if not states:
            return HealthStatus.HEALTHY
        statuses = [state.status for state in states.values()]
        if any(s == HealthStatus.UNHEALTHY for s in statuses):
            return HealthStatus.UNHEALTHY
        if any(s == HealthStatus.DEGRADED for s in statuses):
            return HealthStatus.DEGRADED
        return HealthStatus.HEALTHY

    def _get_provider_statuses(self) -> dict[str, dict[str, Any]]:
        """Get detailed status for all providers."""
        if not self._health_monitor:
            return {}
        states = self._health_monitor.get_all_states()
        return {
            name: {
                "status": state.status.value.lower(),
                "consecutive_errors": state.consecutive_errors,
            }
            for name, state in states.items()
        }

    async def _send_json_response(
        self, writer: asyncio.StreamWriter, response: HealthResponse
    ) -> None:
        """Send JSON response."""
        body = response.to_json()
        status_code = response.http_status
        status_text = "OK" if status_code == 200 else "Service Unavailable"
        http_response = (
            f"HTTP/1.1 {status_code} {status_text}\r\n"
            f"Content-Type: application/json\r\n"
            f"Content-Length: {len(body)}\r\n"
            f"Connection: close\r\n"
            f"\r\n"
            f"{body}"
        )
        writer.write(http_response.encode("utf-8"))
        await writer.drain()

    async def _send_response(
        self, writer: asyncio.StreamWriter, status_code: int, message: str
    ) -> None:
        """Send plain text response."""
        body = json.dumps({"error": message})
        http_response = (
            f"HTTP/1.1 {status_code} {message}\r\n"
            f"Content-Type: application/json\r\n"
            f"Content-Length: {len(body)}\r\n"
            f"Connection: close\r\n"
            f"\r\n"
            f"{body}"
        )
        writer.write(http_response.encode("utf-8"))
        await writer.drain()


async def run_health_server(
    host: str = "0.0.0.0",
    port: int = 8080,
    health_monitor: HealthMonitorPort | None = None,
    logger: LoggerPort | None = None,
) -> None:
    """Run the health server until interrupted."""
    server = HealthServer(
        host=host, port=port, health_monitor=health_monitor, logger=logger
    )
    await server.start()
    try:
        while True:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        pass
    finally:
        await server.stop()


__all__ = ["HealthResponse", "HealthServer", "run_health_server"]

================================================================================
File: types.py
Path: http\types.py
================================================================================
"""HTTP interface types for BioETL."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any


@dataclass
class HealthResponse:
    """Health check response data."""

    status: str
    timestamp: str
    version: str = "1.0.0"
    checks: dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(
            {
                "status": self.status,
                "timestamp": self.timestamp,
                "version": self.version,
                "checks": self.checks,
            },
            indent=2,
        )

    @property
    def http_status(self) -> int:
        """Return HTTP status code based on health status."""
        if self.status == "healthy":
            return 200
        elif self.status == "degraded":
            return 200  # Still operational
        return 503  # Service Unavailable


__all__ = ["HealthResponse"]

================================================================================
File: observability.py
Path: observability.py
================================================================================
"""Observability interface for BioETL.

Re-exports observability components for external consumers.

Note:
    MetricsServerError is defined in domain.exceptions (value object,
    can be imported by all layers). start_metrics_server is re-exported
    from infrastructure.observability.
"""

from __future__ import annotations

from bioetl.domain.exceptions import MetricsServerError
from bioetl.infrastructure.observability import start_metrics_server

__all__ = [
    "MetricsServerError",
    "start_metrics_server",
]

================================================================================
File: __init__.py
Path: orchestration\__init__.py
================================================================================
"""Orchestration utilities for pipeline execution.

This module is the designated location for orchestration utilities that
coordinate pipeline execution from interfaces layer (CLI, REST API, etc.).

REQ-ARCH-APP-001 states that external orchestration frameworks (Celery, Airflow)
must NOT be imported in application layer. This module serves as the integration
point for any such frameworks when needed.

Current status:
- Signal handlers were removed in 2025-12-31 (CLI handles KeyboardInterrupt directly)
- The module is reserved for future orchestration needs

For pipeline execution, use the entrypoints module:
    from bioetl.composition.entrypoints import run_pipeline, get_pipeline_runner_service
"""

from __future__ import annotations

__all__: list[str] = []

