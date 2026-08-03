"""Health server long-lived lifecycle and context helpers."""

from __future__ import annotations

import asyncio
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

import click

from bioetl.domain.exceptions import BioETLError
from bioetl.interfaces.cli.commands.domains.health import (
    server_integration_deps as _deps,
)
from bioetl.interfaces.cli.commands.domains.health import (
    server_integration_observability as _observability,
)
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
    from pathlib import Path

    from bioetl.interfaces.http.health_server import HealthServer

DEFAULT_HEALTH_SERVER_PORT = 8081

_HEALTH_SERVER_DOMAIN_ERROR_TITLE = "Health server failed with domain error"
_HEALTH_SERVER_UNEXPECTED_ERROR_TITLE = "Unexpected error in health server command"
_HEALTH_SERVER_INTERRUPTED_MESSAGE = "Health server interrupted by user (Ctrl+C)"


async def _run_health_server(
    host: str,
    port: int,
    *,
    start_metrics: bool = True,
    data_root: Path | None = None,
) -> None:
    """Start and keep the health server alive until interrupted."""
    if sys.pycache_prefix is None:
        sys.pycache_prefix = str(_deps.build_health_server_pycache_prefix())
    deps = (
        _deps.get_health_server_dependencies()
        if data_root is None
        else _deps.get_health_server_dependencies(data_root=data_root)
    )
    # ARCH-CR2-03: resolve optional quarantine before building the health graph
    # so build_health_server receives a consistent dependency set.
    quarantine_service = (
        _deps._get_optional_health_server_quarantine_service()
        if data_root is None
        else _deps._get_optional_health_server_quarantine_service(data_root=data_root)
    )
    server = _deps.build_health_server(
        host=host,
        port=port,
        deps=deps,
        quarantine_service=quarantine_service,
    )
    try:
        await server.start()
        if start_metrics:
            _observability._start_health_observability()
        while True:
            await asyncio.sleep(1)
    finally:
        await server.stop()
        await _deps.close_health_server_resources(
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

    deps = _deps.get_health_server_dependencies()
    quarantine_service = _deps._get_optional_health_server_quarantine_service()
    server = _deps.build_health_server(
        host=host,
        port=port,
        deps=deps,
        quarantine_service=quarantine_service,
    )

    try:
        await server.start()
    except OSError:
        await _deps.close_health_server_resources(
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
    except BaseException:
        # Clean up for every startup failure, then re-raise (ARCH-CR-03 / #6865).
        await _deps.close_health_server_resources(
            deps=deps,
            quarantine_service=quarantine_service,
        )
        raise

    try:
        yield server
    finally:
        await server.stop()
        await _deps.close_health_server_resources(
            deps=deps,
            quarantine_service=quarantine_service,
        )


__all__ = [
    "DEFAULT_HEALTH_SERVER_PORT",
    "health_server_context",
    "run_long_lived_health_server_command",
]
