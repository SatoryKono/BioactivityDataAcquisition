"""Internal builder helpers for composite runtime bootstrap.

This module holds orchestration internals so ``composite.py`` can remain
as a thin compatibility facade with stable patch points.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.composition.bootstrap.composite_infrastructure_context import (
    CompositeInfrastructureContext,
)
from bioetl.composition.bootstrap.runtime._composite_plan_support import (
    build_bootstrap_runtime_resources,
)
from bioetl.composition.bootstrap.runtime.runner_assembly import (
    create_composite_runner as _create_composite_runner_impl,
)
from bioetl.composition.bootstrap.runtime.runtime_basics import (
    bootstrap_runtime_basics as _bootstrap_runtime_basics_impl,
)
from bioetl.composition.bootstrap.runtime.runtime_basics import (
    build_runner_factories,
    build_support_services,
)
from bioetl.infrastructure.time import SystemClock

__all__ = [
    "bootstrap_runtime_basics",
    "build_runner_factories",
    "build_support_services",
    "create_composite_runner",
]


def bootstrap_runtime_basics(
    *,
    config: CompositeConfig,
    run_id: str | None,
    settings_provider: Callable[[], Settings],
    logger_bootstrapper: Callable[[str, UUID, str], LoggerPort],
    tracer_bootstrapper: Callable[[Settings], TracingPort],
    storage_bootstrapper: Callable[..., object],
    lock_factory: Callable[[], LockPort],
    uuid_factory: Callable[[], UUID],
) -> CompositeInfrastructureContext:
    """Build base runtime dependencies shared across composite bootstrap.

    Args:
        config: Validated CompositeConfig used to derive the pipeline name.
        run_id: Optional run UUID string; a new UUID is generated when None.
        settings_provider: Callable returning global Settings.
        logger_bootstrapper: Callable accepting (pipeline_name, run_uuid, log_level)
            and returning a LoggerPort.
        storage_bootstrapper: Callable returning a storage adapter (any type).
        lock_factory: Callable returning a LockPort implementation.
        uuid_factory: Callable returning a new UUID (injectable for testing).

    Returns:
        Infrastructure context handoff for the composite run.
    """
    runtime_resources = build_bootstrap_runtime_resources(
        bootstrap_runtime_basics_fn=lambda *, config, run_id: (
            _bootstrap_runtime_basics_impl(
                config=config,
                run_id=run_id,
                settings_provider=settings_provider,
                logger_bootstrapper=logger_bootstrapper,
                tracer_bootstrapper=tracer_bootstrapper,
                storage_bootstrapper=storage_bootstrapper,
                lock_factory=lock_factory,
                uuid_factory=uuid_factory,
            )
        ),
        config=config,
        run_id=run_id,
    )
    return CompositeInfrastructureContext(
        run_id=runtime_resources.run_id,
        settings=runtime_resources.settings,
        logger=runtime_resources.logger,
        metrics=runtime_resources.metrics,
        tracer=runtime_resources.tracer,
        storage=runtime_resources.storage,
        lock=runtime_resources.lock,
        clock=SystemClock(),
    )


if TYPE_CHECKING:
    from collections.abc import Callable
    from uuid import UUID

    from bioetl.application.composite.runtime_models import CompositeRuntimeConfig
    from bioetl.domain.composite.config import CompositeConfig
    from bioetl.domain.ports import LockPort, LoggerPort, TracingPort
    from bioetl.infrastructure.config import Settings

    # Preserve the stable runtime-config facade in this module's type surface.
    _RuntimeConfigFacade = CompositeRuntimeConfig

create_composite_runner = _create_composite_runner_impl
