"""Health server integration for CLI commands."""

from __future__ import annotations

import asyncio
import sys
import tempfile
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, cast

import click

from bioetl.domain.exceptions import BioETLError
from bioetl.interfaces.cli.commands.domains.health.failure_handling import (
    handle_health_failure as _handle_health_failure,
)
from bioetl.interfaces.cli.commands.domains.health.rendering import (
    build_health_server_info_lines,
)
from bioetl.interfaces.cli.commands.domains.shared.execution_policy import (
    CLI_ENTRYPOINT_TYPED_ERRORS,
)
from bioetl.interfaces.cli.exit_codes import ExitCode

if TYPE_CHECKING:
    from bioetl.application.services.quarantine_service import QuarantineService
    from bioetl.composition.health_service_access import (
        HealthServerDependenciesProtocol,
        QuarantineRuntimeServiceProtocol,
    )
    from bioetl.domain.ports import LoggerPort
    from bioetl.interfaces.http.health_server import HealthServer

DEFAULT_HEALTH_SERVER_PORT = 8081

_HEALTH_SERVER_DOMAIN_ERROR_TITLE = "Health server failed with domain error"
_HEALTH_SERVER_UNEXPECTED_ERROR_TITLE = "Unexpected error in health server command"
_HEALTH_SERVER_INTERRUPTED_MESSAGE = "Health server interrupted by user (Ctrl+C)"


class _HealthObservabilitySettings(Protocol):
    @property
    def metrics_enabled(self) -> bool: ...

    @property
    def metrics_server_enabled(self) -> bool: ...

    @property
    def metrics_fail_fast(self) -> bool: ...

    @property
    def metrics_retry_count(self) -> int: ...

    @property
    def metrics_retry_delay(self) -> float: ...


class _HealthRuntimeSettings(Protocol):
    @property
    def metrics_port(self) -> int: ...

    @property
    def metrics_addr(self) -> str: ...

    @property
    def observability(self) -> _HealthObservabilitySettings: ...


def get_health_server_dependencies(
    *,
    data_root: Path | None = None,
) -> HealthServerDependenciesProtocol:
    """Load health-listener dependencies from the canonical composition seam."""
    from bioetl.composition.health_service_access import (
        get_health_server_dependencies as _impl,
    )

    if data_root is None:
        return _impl()
    return _impl(data_root=data_root)


def get_health_server_quarantine_service(
    *,
    data_root: Path | None = None,
) -> QuarantineService:
    """Load read-only quarantine service for health listener endpoints."""
    from bioetl.composition.health_service_access import get_quarantine_service as _impl

    if data_root is None:
        return _impl()
    return _impl(data_root=data_root)


def get_quarantine_runtime_service(
    pipeline: str,
) -> QuarantineRuntimeServiceProtocol:
    """Load one pipeline-scoped quarantine runtime service from composition."""
    from bioetl.composition.health_service_access import (
        get_quarantine_runtime_service as _impl,
    )

    return _impl(pipeline)


def get_runtime_settings() -> _HealthRuntimeSettings:
    """Load runtime settings through the composition boundary."""
    from bioetl.composition.runtime_builders.config_access import get_settings as _impl

    return cast("_HealthRuntimeSettings", _impl())


def _start_metrics_server_via_interface(
    *,
    port: int,
    addr: str,
    fail_fast: bool,
    retry_count: int,
    retry_delay: float,
    logger: LoggerPort | None,
) -> bool:
    """Start the metrics server through the observability composition seam."""
    from bioetl.composition.observability_api import start_metrics_server as _impl

    starter = cast("Callable[..., bool]", _impl)
    return starter(
        port=port,
        addr=addr,
        fail_fast=fail_fast,
        retry_count=retry_count,
        retry_delay=retry_delay,
        logger=logger,
    )


start_metrics_server = _start_metrics_server_via_interface


def get_metrics_server_starter() -> Callable[..., bool]:
    """Expose the patchable metrics-server starter without direct call-site drift."""
    return start_metrics_server


def build_health_server_pycache_prefix() -> Path:
    """Return the deterministic pycache root for the health server process."""
    return Path(tempfile.gettempdir()) / "bioetl-pycache"


def _get_optional_health_server_quarantine_service(
    *,
    data_root: Path | None = None,
) -> QuarantineService | None:
    """Return quarantine service when available without failing health probes."""
    try:
        if data_root is None:
            return get_health_server_quarantine_service()
        return get_health_server_quarantine_service(data_root=data_root)
    except CLI_ENTRYPOINT_TYPED_ERRORS:
        return None


def build_health_server(
    *,
    host: str,
    port: int,
    deps: HealthServerDependenciesProtocol,
    quarantine_service: QuarantineService | None,
) -> HealthServer:
    """Construct the HTTP health server from composition dependencies."""
    from bioetl.interfaces.http.health_server import (
        HealthServer,
        HealthServerControlPlaneDeps,
    )

    metrics_exposition = getattr(deps, "metrics_exposition", None)
    server = HealthServer(
        host=host,
        port=port,
        control_plane=HealthServerControlPlaneDeps(
            health_monitor=deps.health_monitor,
            quarantine_service=quarantine_service,
            checkpoint_port=deps.checkpoint_port,
            run_manifest_port=deps.run_manifest_port,
            run_ledger_port=deps.run_ledger_port,
            workflow_manifest_port=deps.workflow_manifest_port,
            metrics_exposition=metrics_exposition,
        ),
    )
    data_root = getattr(deps, "data_root", None)
    server.set_data_root(str(data_root) if data_root is not None else None)
    return server


async def close_health_server_resources(
    *,
    deps: HealthServerDependenciesProtocol,
    quarantine_service: QuarantineService | None,
) -> None:
    """Close resources shared by health-server execution modes."""
    await deps.checkpoint_port.aclose()
    if quarantine_service is not None:
        await quarantine_service.aclose()


def _start_health_observability(logger: LoggerPort | None = None) -> None:
    """Start the Prometheus metrics server for long-lived health mode."""
    settings = get_runtime_settings()
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

    started = get_metrics_server_starter()(
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


async def _run_health_server(
    host: str,
    port: int,
    *,
    start_metrics: bool = True,
    data_root: Path | None = None,
) -> None:
    """Start and keep the health server alive until interrupted."""
    if sys.pycache_prefix is None:
        sys.pycache_prefix = str(build_health_server_pycache_prefix())
    deps = (
        get_health_server_dependencies()
        if data_root is None
        else get_health_server_dependencies(data_root=data_root)
    )
    server = build_health_server(
        host=host,
        port=port,
        deps=deps,
        quarantine_service=None,
    )
    quarantine_service = None
    try:
        await server.start()
        quarantine_service = (
            _get_optional_health_server_quarantine_service()
            if data_root is None
            else _get_optional_health_server_quarantine_service(data_root=data_root)
        )
        server._quarantine_service = quarantine_service
        if start_metrics:
            _start_health_observability()
        while True:
            await asyncio.sleep(1)
    finally:
        await server.stop()
        await close_health_server_resources(
            deps=deps,
            quarantine_service=quarantine_service,
        )
        click.echo("\nHealth server stopped.")


def run_long_lived_health_server_command(
    host: str,
    port: int,
    *,
    start_metrics: bool = True,
    data_root: Path | None = None,
) -> None:
    """Start the long-lived health/quarantine explorer backend."""
    for line in build_health_server_info_lines(host, port):
        click.echo(line)
    if data_root is None:
        coro = _run_health_server(host=host, port=port, start_metrics=start_metrics)
    else:
        coro = _run_health_server(
            host=host,
            port=port,
            start_metrics=start_metrics,
            data_root=data_root,
        )
    try:
        asyncio.run(coro)
    except asyncio.CancelledError:
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


@asynccontextmanager
async def health_server_context(
    enabled: bool,
    host: str = "127.0.0.1",
    port: int = DEFAULT_HEALTH_SERVER_PORT,
) -> AsyncIterator[HealthServer | None]:
    """Run the health server for the context lifetime when enabled."""
    if not enabled:
        yield None
        return

    deps = get_health_server_dependencies()
    quarantine_service = _get_optional_health_server_quarantine_service()
    server = build_health_server(
        host=host,
        port=port,
        deps=deps,
        quarantine_service=quarantine_service,
    )

    try:
        await server.start()
    except OSError:
        await close_health_server_resources(
            deps=deps,
            quarantine_service=quarantine_service,
        )
        click.echo(
            f"Warning: Health server failed to bind to {host}:{port} "
            f"(port in use). Pipeline will continue without health server.",
            err=True,
        )
        yield None
        return

    try:
        yield server
    finally:
        await server.stop()
        await close_health_server_resources(
            deps=deps,
            quarantine_service=quarantine_service,
        )


def add_health_server_options(cmd: click.Command) -> click.Command:
    """Add health server options to a Click command."""
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
    """Output health server status information."""
    if enabled:
        click.echo(f"Health server: http://{host}:{port}/health")


COMMANDS = (add_health_server_options, echo_health_server_info, health_server_context)

__all__ = [
    "DEFAULT_HEALTH_SERVER_PORT",
    "_handle_health_failure",
    "add_health_server_options",
    "echo_health_server_info",
    "get_health_server_dependencies",
    "get_health_server_quarantine_service",
    "get_quarantine_runtime_service",
    "get_runtime_settings",
    "health_server_context",
    "run_long_lived_health_server_command",
    "start_metrics_server",
]
