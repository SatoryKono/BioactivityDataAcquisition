"""Composite runtime bootstrap planning helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import ValidationError

from bioetl.application.composite.runner_pkg import CompositePipelineRunner
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
from bioetl.infrastructure.config.composite_config_api import (
    load_composite_config as _load_composite_config_impl,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    import polars as pl

    from bioetl.application.composite.runtime_models import CompositeRuntimeConfig
    from bioetl.application.composite.runtime_wiring_api import PipelineRunner
    from bioetl.composition.bootstrap.composite_infrastructure_context import (
        CompositeInfrastructureContext,
    )
    from bioetl.composition.bootstrap.runtime.composite_support_services_factory import (
        CompositeSupportServices,
    )
    from bioetl.domain.composite.config import CompositeConfig
    from bioetl.domain.ports import LockPort, LoggerPort, MetricsPort, TracingPort
    from bioetl.infrastructure.config import Settings


@dataclass(frozen=True, slots=True)
class CompositeBootstrapPlan:
    run_id: str
    logger: LoggerPort
    metrics: MetricsPort
    tracer: TracingPort
    lock: LockPort
    seed_runner_factory: Callable[[], PipelineRunner]
    dependencies_runner_factory: Callable[[str, pl.DataFrame], PipelineRunner]
    enricher_runner_factory: Callable[[str, pl.DataFrame], PipelineRunner]
    support_services: CompositeSupportServices


def load_composite_config_impl(
    name: str,
    *,
    resolve_config_path_fn: Callable[[str], Path],
    validate_payload: Callable[[object], object],
) -> CompositeConfig:
    return _load_runtime_composite_config_impl(
        name,
        resolve_config_path_fn=resolve_config_path_fn,
        load_config_fn=_load_composite_config_impl,
        validate_payload=validate_payload,
        validation_error_cls=ValidationError,
    )


def bootstrap_runtime_basics_impl(
    *,
    config: CompositeConfig,
    run_id: str | None,
    settings_provider: Callable[[], Settings],
    logger_bootstrapper: Callable[[str, str, str], LoggerPort],
    tracer_bootstrapper: Callable[[str, str, LoggerPort], TracingPort],
    storage_bootstrapper: Callable[..., object],
    lock_factory: type[object],
    uuid_factory: Callable[[], object],
) -> CompositeInfrastructureContext:
    return _bootstrap_runtime_basics_builder_impl(
        config=config,
        run_id=run_id,
        settings_provider=settings_provider,
        logger_bootstrapper=logger_bootstrapper,
        tracer_bootstrapper=tracer_bootstrapper,
        storage_bootstrapper=storage_bootstrapper,
        lock_factory=lock_factory,
        uuid_factory=uuid_factory,
    )


def build_runner_factories_impl(
    *,
    config: CompositeConfig,
    runtime: CompositeRuntimeConfig,
    logger: LoggerPort,
    runner_factory_builder_cls: type[object],
    filter_extraction_service_cls: type[object],
    pipeline_runner_builder: Callable[..., PipelineRunner],
    resolve_bronze_opts_fn: Callable[..., dict[str, object]],
) -> tuple[
    Callable[[], PipelineRunner],
    Callable[[str, pl.DataFrame], PipelineRunner],
    Callable[[str, pl.DataFrame], PipelineRunner],
]:
    return _build_runner_factories_builder_impl(
        config=config,
        runtime=runtime,
        logger=logger,
        runner_factory_builder_cls=runner_factory_builder_cls,
        filter_extraction_service_cls=filter_extraction_service_cls,
        pipeline_runner_builder=pipeline_runner_builder,
        resolve_bronze_opts_fn=resolve_bronze_opts_fn,
    )


def build_support_services_impl(
    *,
    config: CompositeConfig,
    runtime: CompositeRuntimeConfig,
    infra_context: CompositeInfrastructureContext,
    support_services_factory_cls: type[object],
    resolve_gold_schema_fn: Callable[[str], type | None],
    load_field_group_registry_fn: Callable[..., object],
    create_dq_report_service_fn: Callable[..., object],
) -> CompositeSupportServices:
    return _build_support_services_builder_impl(
        config=config,
        runtime=runtime,
        infra_context=infra_context,
        support_services_factory_cls=support_services_factory_cls,
        resolve_gold_schema_fn=resolve_gold_schema_fn,
        load_field_group_registry_fn=load_field_group_registry_fn,
        create_dq_report_service_fn=create_dq_report_service_fn,
    )


def build_composite_bootstrap_plan_impl(
    *,
    config: CompositeConfig,
    runtime: CompositeRuntimeConfig,
    run_id: str | None,
    bootstrap_runtime_basics_fn: Callable[..., CompositeInfrastructureContext],
    build_runner_factories_fn: Callable[
        ...,
        tuple[
            Callable[[], PipelineRunner],
            Callable[[str, pl.DataFrame], PipelineRunner],
            Callable[[str, pl.DataFrame], PipelineRunner],
        ],
    ],
    build_support_services_fn: Callable[..., CompositeSupportServices],
) -> CompositeBootstrapPlan:
    infra_context = bootstrap_runtime_basics_fn(config=config, run_id=run_id)
    seed_runner_factory, dependencies_runner_factory, enricher_runner_factory = (
        build_runner_factories_fn(
            config=config,
            runtime=runtime,
            logger=infra_context.logger,
        )
    )
    support_services = build_support_services_fn(
        config=config,
        runtime=runtime,
        infra_context=infra_context,
    )
    return CompositeBootstrapPlan(
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


def create_composite_runner_from_plan_impl(
    *,
    config: CompositeConfig,
    runtime: CompositeRuntimeConfig,
    plan: CompositeBootstrapPlan,
    runner_factory: Callable[..., CompositePipelineRunner],
) -> CompositePipelineRunner:
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
        runner_factory=runner_factory,
    )
