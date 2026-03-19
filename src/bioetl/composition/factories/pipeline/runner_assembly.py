"""Runner assembly helper for pipeline factory."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

from bioetl.application.core.lifecycle.lock_manager import LockCoordinator
from bioetl.application.core.preflight.health_aggregator import _HealthAggregator
from bioetl.application.core.preflight.medallion_validator import (
    _MedallionConfigValidator,
)
from bioetl.application.core.preflight.service import PreflightService
from bioetl.application.core.runner import (
    PipelineRunner,
    PipelineRunnerDependencies,
)
from bioetl.application.observability.observer import PipelineObserver
from bioetl.application.services.medallion_lifecycle import MedallionLifecycleService
from bioetl.composition.bootstrap_contexts import DQConfigsContext
from bioetl.composition.factories.dq.context_resolver import (
    extract_dq_output_paths,
)
from bioetl.composition.factories.pipeline.postrun_assembly import (
    build_postrun_service,
)
from bioetl.composition.factories.services.common_service_wiring import resolve_tracer
from bioetl.composition.factories.services.factory import ServicesBuilder
from bioetl.domain.locking import LockContextHolder
from bioetl.domain.medallion import LoadingStrategy, WriteModePolicy

if TYPE_CHECKING:
    import pyarrow as pa

    from bioetl.application.core.base import BasePipeline
    from bioetl.application.core.batch_executor import BatchExecutor
    from bioetl.application.core.lifecycle.checkpoint_manager import (
        CheckpointManagerService,
    )
    from bioetl.application.core.postrun.service import PostrunService
    from bioetl.composition.observability import ObservabilityBundle
    from bioetl.domain.ports import LoggerPort
    from bioetl.domain.types import GoldSchemaType
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig

__all__ = [
    "assemble_runner_impl",
]


@dataclass(frozen=True, slots=True)
class _RunnerAssemblyParts:
    """Concrete runner collaborators assembled before PipelineRunner creation."""

    checkpoint_manager: CheckpointManagerService
    lifecycle_service: MedallionLifecycleService
    lock_manager: LockCoordinator
    preflight_service: PreflightService
    postrun_service: PostrunService
    observer: PipelineObserver
    batch_executor: BatchExecutor


def _build_checkpoint_manager(
    *,
    pipeline: BasePipeline,
    logger_port: LoggerPort,
) -> CheckpointManagerService:
    return ServicesBuilder.create_checkpoint_manager(
        checkpoint_port=pipeline.services.checkpoint,
        logger=logger_port,
        pipeline_name=pipeline.config.pipeline_name,
        run_id=pipeline.run_id,
        resume=pipeline.runtime.resume,
        loading_strategy=cast(LoadingStrategy | None, pipeline.config.loading_strategy),
    )


def _build_lock_manager(
    *,
    pipeline: BasePipeline,
    logger_port: LoggerPort,
    checkpoint_manager: CheckpointManagerService,
    context_holder: LockContextHolder,
) -> LockCoordinator:
    return LockCoordinator.create(
        lock_port=pipeline.services.lock,
        run_id=pipeline.context.run_id,
        provider=pipeline.config.provider,
        entity_type=pipeline.config.entity_type,
        run_type=pipeline.runtime.run_type,
        lock_ttl=pipeline.runtime.effective_lock_ttl,
        wait_for_lock=pipeline.runtime.wait_for_lock,
        wait_timeout=pipeline.runtime.lock_wait_timeout,
        heartbeat_interval=pipeline.runtime.heartbeat_interval,
        logger=logger_port,
        shutdown_signal=pipeline.shutdown_signal,
        checkpoint_manager=checkpoint_manager,
        context_holder=context_holder,
    )


def _build_preflight_service(
    *,
    pipeline: BasePipeline,
    logger_port: LoggerPort,
) -> PreflightService:
    health_aggregator = _HealthAggregator(
        metrics=pipeline.services.metrics,
        logger=logger_port,
        pipeline_name=pipeline.config.pipeline_name,
        health_check_mode=pipeline.runtime.health_check_mode,
    )
    medallion_validator = _MedallionConfigValidator(
        config=pipeline.config,
        logger=logger_port,
        write_mode_policy=WriteModePolicy(),
    )
    return PreflightService(
        config=pipeline.config,
        context=pipeline.context,
        logger=logger_port,
        metrics=pipeline.services.metrics,
        health_aggregator=health_aggregator,
        medallion_validator=medallion_validator,
    )


def _build_observer(
    *,
    pipeline: BasePipeline,
    observability: ObservabilityBundle,
    logger_port: LoggerPort,
) -> PipelineObserver:
    return PipelineObserver(
        pipeline_name=pipeline.config.pipeline_name,
        run_id=pipeline.context.run_id,
        run_type=pipeline.runtime.run_type,
        metrics=pipeline.services.metrics,
        logger=logger_port,
        tracer=observability.tracer,
    )


def _build_batch_executor(
    *,
    pipeline: BasePipeline,
    yaml_config: PipelineYamlConfig | None,
    silver_schema: pa.Schema | None,
    gold_schema: GoldSchemaType,
    strict_gold_validation: bool,
    checkpoint_manager: CheckpointManagerService,
    lock_manager: LockCoordinator,
    observability: ObservabilityBundle,
) -> BatchExecutor:
    dq_output_paths = extract_dq_output_paths(yaml_config)
    return ServicesBuilder.create_batch_executor_from_pipeline(
        pipeline=pipeline,
        silver_schema=silver_schema,
        gold_schema=gold_schema,
        checkpoint_manager=checkpoint_manager,
        shutdown_signal=pipeline.shutdown_signal,
        strict_gold_validation=strict_gold_validation,
        lock_validator=lock_manager.validate,
        tracer=observability.tracer,
        bronze_output_path=dq_output_paths.bronze_path,
        silver_output_path=dq_output_paths.silver_path,
        gold_output_path=dq_output_paths.gold_path,
        flat_structure=dq_output_paths.flat_structure,
    )


def _create_pipeline_runner(
    *,
    pipeline: BasePipeline,
    observability: ObservabilityBundle,
    executor: BatchExecutor,
    checkpoint_manager: CheckpointManagerService,
    lock_manager: LockCoordinator,
    preflight_service: PreflightService,
    postrun_service: PostrunService,
    lifecycle_service: MedallionLifecycleService,
    observer: PipelineObserver,
) -> PipelineRunner:
    resolved_tracer = resolve_tracer(observability.tracer)
    dependencies = PipelineRunnerDependencies(
        executor=executor,
        checkpoint_manager=checkpoint_manager,
        lock_manager=lock_manager,
        preflight=preflight_service,
        postrun=postrun_service,
        lifecycle_service=lifecycle_service,
        observer=observer,
        shutdown_signal=pipeline.shutdown_signal,
    )
    return PipelineRunner(
        config=pipeline.config,
        runtime=pipeline.runtime,
        services=pipeline.services,
        context=pipeline.context,
        dependencies=dependencies,
        pipeline=pipeline,
        tracer=resolved_tracer,
    )


def _assemble_runner_parts(
    *,
    pipeline: BasePipeline,
    observability: ObservabilityBundle,
    logger_port: LoggerPort,
    yaml_config: PipelineYamlConfig | None,
    silver_schema: pa.Schema | None,
    gold_schema: GoldSchemaType,
    strict_gold_validation: bool,
    dq_configs_extractor: Callable[
        [PipelineYamlConfig | None],
        DQConfigsContext,
    ],
) -> _RunnerAssemblyParts:
    """Assemble runner collaborators before creating the PipelineRunner shell."""
    checkpoint_manager = _build_checkpoint_manager(
        pipeline=pipeline,
        logger_port=logger_port,
    )
    lifecycle_service = MedallionLifecycleService(
        storage=pipeline.services.storage,
        logger=logger_port,
    )
    lock_manager = _build_lock_manager(
        pipeline=pipeline,
        logger_port=logger_port,
        checkpoint_manager=checkpoint_manager,
        context_holder=LockContextHolder(),
    )
    preflight_service = _build_preflight_service(
        pipeline=pipeline,
        logger_port=logger_port,
    )
    dq_configs = dq_configs_extractor(yaml_config)
    postrun_service = build_postrun_service(
        pipeline=pipeline,
        logger_port=logger_port,
        lifecycle_service=lifecycle_service,
        dq_configs=dq_configs,
        tracer=observability.tracer,
    )
    observer = _build_observer(
        pipeline=pipeline,
        observability=observability,
        logger_port=logger_port,
    )
    batch_executor = _build_batch_executor(
        pipeline=pipeline,
        yaml_config=yaml_config,
        silver_schema=silver_schema,
        gold_schema=gold_schema,
        strict_gold_validation=strict_gold_validation,
        checkpoint_manager=checkpoint_manager,
        lock_manager=lock_manager,
        observability=observability,
    )
    return _RunnerAssemblyParts(
        checkpoint_manager=checkpoint_manager,
        lifecycle_service=lifecycle_service,
        lock_manager=lock_manager,
        preflight_service=preflight_service,
        postrun_service=postrun_service,
        observer=observer,
        batch_executor=batch_executor,
    )


def assemble_runner_impl(
    pipeline: BasePipeline,
    observability: ObservabilityBundle,
    silver_schema: pa.Schema | None,
    gold_schema: GoldSchemaType,
    strict_gold_validation: bool,
    dq_configs_extractor: Callable[
        [PipelineYamlConfig | None],
        DQConfigsContext,
    ],
    yaml_config: PipelineYamlConfig | None = None,
) -> PipelineRunner:
    """Assemble a PipelineRunner from a configured pipeline instance.

    Args:
        pipeline: Configured pipeline instance with services, context, and runtime.
        observability: Bundle containing logger, tracer, metrics, and DQ monitor.
        silver_schema: Optional PyArrow schema for Silver layer validation.
        gold_schema: Pandera DataFrameModel class for Gold layer validation.
        strict_gold_validation: If True, raises on Gold schema violations.
        yaml_config: Optional pre-loaded pipeline YAML config for DQ path extraction.
        dq_configs_extractor: Callable extracting DQ configs from YAML config.

    Returns:
        Fully wired PipelineRunner ready for execution.
    """
    logger_port = observability.logger
    assembly_parts = _assemble_runner_parts(
        pipeline=pipeline,
        observability=observability,
        logger_port=logger_port,
        yaml_config=yaml_config,
        silver_schema=silver_schema,
        gold_schema=gold_schema,
        strict_gold_validation=strict_gold_validation,
        dq_configs_extractor=dq_configs_extractor,
    )

    return _create_pipeline_runner(
        pipeline=pipeline,
        observability=observability,
        executor=assembly_parts.batch_executor,
        checkpoint_manager=assembly_parts.checkpoint_manager,
        lock_manager=assembly_parts.lock_manager,
        preflight_service=assembly_parts.preflight_service,
        postrun_service=assembly_parts.postrun_service,
        lifecycle_service=assembly_parts.lifecycle_service,
        observer=assembly_parts.observer,
    )
