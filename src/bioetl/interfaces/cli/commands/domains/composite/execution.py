"""Execution helpers for the run-composite CLI command."""

from __future__ import annotations

from contextlib import AbstractAsyncContextManager
from typing import TYPE_CHECKING

from bioetl.application.composite.runtime_models import CompositeRuntimeConfig
from bioetl.domain.exceptions import BioETLError
from bioetl.interfaces.cli.commands.domains.health.metrics_server_integration import (
    ensure_metrics_server_started,
)
from bioetl.interfaces.cli.commands.domains.health.server_integration import (
    DEFAULT_HEALTH_SERVER_PORT,
    health_server_context,
)

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from bioetl.application.composite.runner_pkg import CompositePipelineRunner
    from bioetl.domain.composite import CompositeConfig
    from bioetl.domain.composite.result import CompositeResult


def load_composite_config(name: str) -> CompositeConfig:
    """Load composite config through composition on demand."""
    from bioetl.composition.composite_api import load_composite_config as _impl

    return _impl(name)


def bootstrap_composite_runner(
    config: CompositeConfig,
    runtime: CompositeRuntimeConfig,
) -> CompositePipelineRunner:
    """Build composite runner through composition on demand."""
    from bioetl.composition.composite_api import bootstrap_composite_runner as _impl

    return _impl(config, runtime)


def build_run_composite_result(
    result: CompositeResult,
) -> tuple[bool, str | None]:
    """Map composite runner result to CLI success/error tuple."""
    if result.is_success:
        return True, None
    failed = result.failed_enrichers
    if failed:
        return False, f"Failed enrichers: {', '.join(failed)}"
    return False, "Composite pipeline failed"


async def run_composite_inner(
    composite_name: str,
    runtime: CompositeRuntimeConfig,
    *,
    load_config: Callable[[str], CompositeConfig] = load_composite_config,
    build_runner: Callable[
        [CompositeConfig, CompositeRuntimeConfig],
        CompositePipelineRunner,
    ] = bootstrap_composite_runner,
) -> tuple[bool, str | None]:
    """Run composite pipeline execution logic."""
    try:
        config = load_config(composite_name)
    except FileNotFoundError as exc:
        return False, str(exc)
    except ValueError as exc:
        return False, f"Invalid configuration: {exc}"

    try:
        runner = build_runner(config, runtime)
        return build_run_composite_result(await runner.run())
    except (BioETLError, OSError, RuntimeError, ValueError, TypeError) as exc:
        return (
            False,
            (
                f"{exc} "
                f"(reason_code=CLI_COMPOSITE_RUNNER_ERROR, composite={composite_name}, "
                f"error_type={type(exc).__name__})"
            ),
        )


async def run_composite_async(
    composite_name: str,
    runtime: CompositeRuntimeConfig,
    health_server_enabled: bool = True,
    health_port: int = DEFAULT_HEALTH_SERVER_PORT,
    *,
    run_inner: Callable[
        [str, CompositeRuntimeConfig],
        Awaitable[tuple[bool, str | None]],
    ] = run_composite_inner,
    metrics_starter: Callable[[], bool | None] = ensure_metrics_server_started,
    health_context_factory: Callable[
        ...,
        AbstractAsyncContextManager[object],
    ] = health_server_context,
) -> tuple[bool, str | None]:
    """Run composite pipeline asynchronously with optional health server."""
    metrics_starter()
    async with health_context_factory(
        enabled=health_server_enabled,
        port=health_port,
    ):
        return await run_inner(composite_name, runtime)
