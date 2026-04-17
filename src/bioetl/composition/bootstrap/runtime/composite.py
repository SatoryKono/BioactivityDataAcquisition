"""Bootstrap facade for Composite Pipeline execution (ADR-026)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import ValidationError

from bioetl.application.composite.runner_pkg import CompositePipelineRunner
from bioetl.application.composite.runtime_models import CompositeRuntimeConfig
from bioetl.composition.bootstrap.composite_infrastructure_context import (
    CompositeInfrastructureContext,
)
from bioetl.composition.bootstrap.runtime._composite_config_runtime_compat import (
    load_runtime_composite_config as _load_runtime_composite_config_impl,
)
from bioetl.composition.bootstrap.runtime.composite_bootstrap_builders import (
    bootstrap_runtime_basics as _bootstrap_runtime_basics_builder_impl,
)
from bioetl.composition.bootstrap.runtime.composite_bootstrap_builders import (
    build_runner_factories as _build_runner_factories_builder_impl,
)
from bioetl.composition.bootstrap.runtime.composite_bootstrap_builders import (
    build_support_services as _build_support_services_builder_impl,
)
from bioetl.composition.bootstrap.runtime.composite_bootstrap_builders import (
    create_composite_runner as _create_composite_runner_builder_impl,
)
from bioetl.composition.bootstrap.runtime.composite_support_helpers import (
    _create_dq_report_service,
    _load_field_group_registry,
)
from bioetl.composition.bootstrap.runtime.composite_support_services_factory import (
    CompositeSupportServices,
)
from bioetl.composition.bootstrap.runtime.runner_assembly import (
    create_composite_runner_service,
)
from bioetl.domain.composite.config import CompositeConfig
from bioetl.infrastructure.config.composite_config_api import (
    DEFAULT_COMPOSITE_CONFIG_DIR,
    DEFAULT_COMPOSITE_GOLD_SCHEMA_REGISTRY,
)
from bioetl.infrastructure.config.composite_config_api import (
    load_composite_config as _load_composite_config_impl,
)
from bioetl.infrastructure.config.composite_config_api import (
    resolve_composite_config_path as _resolve_composite_config_path_impl,
)
from bioetl.infrastructure.config.composite_config_api import (
    resolve_composite_gold_schema as _resolve_composite_gold_schema_impl,
)
from bioetl.infrastructure.schemas.composite_config import (
    validate_composite_config_payload,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    import polars as pl

    from bioetl.application.composite.runtime_wiring_api import PipelineRunner
    from bioetl.domain.ports import LockPort, LoggerPort, MetricsPort, TracingPort

__all__ = [
    "CompositeRuntimeConfig",
    "bootstrap_composite_runner",
    "load_composite_config",
]


@dataclass(frozen=True, slots=True)
class _CompositeBootstrapPlan:
    """Resolved bootstrap plan passed to the final runner factory."""

    run_id: str
    logger: LoggerPort
    metrics: MetricsPort
    tracer: TracingPort
    lock: LockPort
    seed_runner_factory: Callable[[], PipelineRunner]
    dependencies_runner_factory: Callable[[str, pl.DataFrame], PipelineRunner]
    enricher_runner_factory: Callable[[str, pl.DataFrame], PipelineRunner]
    support_services: CompositeSupportServices


def _resolve_composite_gold_schema(composite_name: str) -> type | None:
    """Resolve composite Gold contract by composite pipeline name."""
    return _resolve_composite_gold_schema_impl(
        composite_name,
        schema_registry=DEFAULT_COMPOSITE_GOLD_SCHEMA_REGISTRY,
    )


def _resolve_composite_config_path(name: str) -> Path:
    """Resolve composite config path from canonical composites directory."""
    return _resolve_composite_config_path_impl(
        name,
        config_dir=DEFAULT_COMPOSITE_CONFIG_DIR,
    )


def load_composite_config(name: str) -> CompositeConfig:
    """Load and validate composite pipeline configuration from YAML.

    Keeps compatibility patch points used by legacy tests:
    - ``_resolve_composite_config_path``
    - ``validate_composite_config_payload``
    - ``ValidationError``

    Args:
        name: Composite pipeline name (e.g., 'composite_publication'). Used to
            resolve the YAML file path from the canonical composites directory.

    Returns:
        Validated and parsed CompositeConfig domain object.

    Raises:
        FileNotFoundError: If no YAML config file exists for the given name.
        ValueError: If the YAML file fails Pydantic schema validation.
    """
    return _load_runtime_composite_config_impl(
        name,
        resolve_config_path_fn=_resolve_composite_config_path,
        load_config_fn=_load_composite_config_impl,
        validate_payload=validate_composite_config_payload,
        validation_error_cls=ValidationError,
    )


def _bootstrap_runtime_basics(
    *,
    config: CompositeConfig,
    run_id: str | None,
) -> CompositeInfrastructureContext:
    """Build base runtime dependencies shared across composite bootstrap."""
    from uuid import uuid4

    from bioetl.composition.bootstrap.assembly.storage import bootstrap_storage_adapter
    from bioetl.composition.bootstrap.runtime.observability import (
        bootstrap_logger_port,
    )
    from bioetl.composition.bootstrap.runtime.tracing_bootstrap import (
        bootstrap_tracer_port,
    )
    from bioetl.infrastructure.config import get_settings
    from bioetl.infrastructure.locking.memory_lock import MemoryLock

    return _bootstrap_runtime_basics_builder_impl(
        config=config,
        run_id=run_id,
        settings_provider=get_settings,
        logger_bootstrapper=lambda pipeline_name, run_uuid, level: (
            bootstrap_logger_port(
                pipeline=pipeline_name,
                run_id=run_uuid,
                log_level=level,
            )
        ),
        tracer_bootstrapper=bootstrap_tracer_port,
        storage_bootstrapper=bootstrap_storage_adapter,
        lock_factory=MemoryLock,
        uuid_factory=uuid4,
    )


def _build_runner_factories(
    *,
    config: CompositeConfig,
    runtime: CompositeRuntimeConfig,
    logger: LoggerPort,
) -> tuple[
    Callable[[], PipelineRunner],
    Callable[[str, pl.DataFrame], PipelineRunner],
    Callable[[str, pl.DataFrame], PipelineRunner],
]:
    """Build seed/dependency/enricher runner factories for composite phases."""
    from bioetl.composition.bootstrap.runtime.composite_filter_extraction_service import (
        CompositeFilterExtractionService,
    )
    from bioetl.composition.bootstrap.runtime.pipeline import (
        bootstrap_pipeline_runner as bootstrap_pipeline_runner_impl,
    )
    from bioetl.composition.bootstrap.runtime.runner_factory_builder_service import (
        RunnerFactoryBuilderService,
        resolve_bronze_opts,
    )

    return _build_runner_factories_builder_impl(
        config=config,
        runtime=runtime,
        logger=logger,
        runner_factory_builder_cls=RunnerFactoryBuilderService,
        filter_extraction_service_cls=CompositeFilterExtractionService,
        pipeline_runner_builder=bootstrap_pipeline_runner_impl,
        resolve_bronze_opts_fn=resolve_bronze_opts,
    )


def _build_support_services(
    *,
    config: CompositeConfig,
    runtime: CompositeRuntimeConfig,
    infra_context: CompositeInfrastructureContext,
) -> CompositeSupportServices:
    """Build composite support service bundle consumed by runner facade."""
    from bioetl.composition.bootstrap.runtime.composite_support_services_factory import (
        CompositeSupportServicesFactory,
    )

    return _build_support_services_builder_impl(
        config=config,
        runtime=runtime,
        infra_context=infra_context,
        support_services_factory_cls=CompositeSupportServicesFactory,
        resolve_gold_schema_fn=_resolve_composite_gold_schema,
        load_field_group_registry_fn=_load_field_group_registry,
        create_dq_report_service_fn=_create_dq_report_service,
    )


def _build_composite_bootstrap_plan(
    *,
    config: CompositeConfig,
    runtime: CompositeRuntimeConfig,
    run_id: str | None,
) -> _CompositeBootstrapPlan:
    """Resolve declarative bootstrap plan for the composite runner."""
    infra_context = _bootstrap_runtime_basics(config=config, run_id=run_id)
    seed_runner_factory, dependencies_runner_factory, enricher_runner_factory = (
        _build_runner_factories(
            config=config,
            runtime=runtime,
            logger=infra_context.logger,
        )
    )
    support_services = _build_support_services(
        config=config,
        runtime=runtime,
        infra_context=infra_context,
    )
    return _CompositeBootstrapPlan(
        run_id=infra_context.run_id,
        logger=infra_context.logger,
        metrics=infra_context.metrics,
        tracer=infra_context.tracer,
        lock=infra_context.lock,
        seed_runner_factory=seed_runner_factory,
        dependencies_runner_factory=dependencies_runner_factory,
        enricher_runner_factory=enricher_runner_factory,
        support_services=support_services,
    )


def _create_composite_runner_from_plan(
    *,
    config: CompositeConfig,
    runtime: CompositeRuntimeConfig,
    plan: _CompositeBootstrapPlan,
) -> CompositePipelineRunner:
    """Create the final composite runner from the resolved bootstrap plan."""
    return _create_composite_runner_builder_impl(
        config=config,
        runtime=runtime,
        run_id=plan.run_id,
        logger=plan.logger,
        metrics=plan.metrics,
        tracer=plan.tracer,
        lock=plan.lock,
        seed_runner_factory=plan.seed_runner_factory,
        dependencies_runner_factory=plan.dependencies_runner_factory,
        enricher_runner_factory=plan.enricher_runner_factory,
        support_services=plan.support_services,
        runner_factory=create_composite_runner_service,
    )


def bootstrap_composite_runner(
    config: CompositeConfig,
    runtime: CompositeRuntimeConfig,
    run_id: str | None = None,
) -> CompositePipelineRunner:
    """Create a ``CompositePipelineRunner`` with all dependencies.

    Args:
        config: Parsed and validated CompositeConfig domain object describing
            the composite pipeline (seed, enrichers, dependencies, merge config).
        runtime: Immutable runtime options for this composite run (resume,
            dry_run, cached bronze settings, etc.).
        run_id: Optional UUID string identifying this run; a new UUID is
            generated when None.

    Returns:
        Fully wired CompositePipelineRunner ready for execution.
    """
    plan = _build_composite_bootstrap_plan(
        config=config, runtime=runtime, run_id=run_id
    )
    return _create_composite_runner_from_plan(config=config, runtime=runtime, plan=plan)
