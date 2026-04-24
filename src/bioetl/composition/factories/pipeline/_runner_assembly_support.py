"""Private support helpers for pipeline runner assembly."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from bioetl.application.core.lifecycle import LockCoordinator
from bioetl.application.core.lifecycle.lock_manager import (
    LockCoordinatorCreateContext,
)
from bioetl.application.core.preflight import (
    HealthAggregator,
    MedallionConfigValidator,
    PreflightService,
)
from bioetl.application.observability.observer import PipelineObserver
from bioetl.application.services.medallion_lifecycle import MedallionLifecycleService
from bioetl.composition.bootstrap_contexts import DQConfigsContext
from bioetl.composition.factories.dq.context_resolver import extract_dq_output_paths
from bioetl.composition.factories.pipeline.postrun_assembly import build_postrun_service
from bioetl.composition.factories.pipeline.runner_constructor import (
    RunnerAssemblyParts,
    RunnerConstructorPayload,
)
from bioetl.composition.factories.services.callbacks import extract_pipeline_callbacks
from bioetl.composition.factories.services.factory import ServicesBuilder
from bioetl.composition.factories.services.pipeline_builder import (
    BatchExecutorBuildRequest,
)
from bioetl.domain.locking import LockContextHolder
from bioetl.domain.medallion import WriteModePolicy
from bioetl.infrastructure.time import SystemClock

if TYPE_CHECKING:
    import pyarrow as pa

    from bioetl.application.core.base import BasePipeline
    from bioetl.application.core.batch_executor import BatchExecutor
    from bioetl.application.core.lifecycle import CheckpointManagerService
    from bioetl.application.core.postrun import PostrunService
    from bioetl.composition.observability import ObservabilityBundle
    from bioetl.domain.ports import LoggerPort
    from bioetl.domain.types import GoldSchemaType
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig


@dataclass(frozen=True, slots=True)
class RunnerAssemblyContext:
    """Typed seam carrying the inputs shared across runner assembly helpers."""

    pipeline: BasePipeline
    observability: ObservabilityBundle
    logger_port: LoggerPort
    yaml_config: PipelineYamlConfig | None
    silver_schema: pa.Schema | None
    gold_schema: GoldSchemaType
    strict_gold_validation: bool
    dq_configs_extractor: Callable[[PipelineYamlConfig | None], DQConfigsContext]


def build_lock_manager(
    context: RunnerAssemblyContext,
    *,
    checkpoint_manager: CheckpointManagerService,
    context_holder: LockContextHolder,
) -> LockCoordinator:
    """Build the lock coordinator for one assembled runner."""
    pipeline = context.pipeline
    return LockCoordinator.create(
        LockCoordinatorCreateContext(
            lock_port=pipeline.services.lock,
            run_id=pipeline.context.run_id,
            provider=pipeline.config.provider,
            entity_type=pipeline.config.entity_type,
            run_type=pipeline.runtime.run_type,
            lock_ttl=pipeline.runtime.effective_lock_ttl,
            wait_for_lock=pipeline.runtime.wait_for_lock,
            wait_timeout=pipeline.runtime.lock_wait_timeout,
            heartbeat_interval=pipeline.runtime.heartbeat_interval,
            logger=context.logger_port,
            shutdown_signal=pipeline.shutdown_signal,
            checkpoint_manager=checkpoint_manager,
            context_holder=context_holder,
        )
    )


def build_preflight_service(context: RunnerAssemblyContext) -> PreflightService:
    """Build the preflight service for a pipeline runner."""
    pipeline = context.pipeline
    health_aggregator = HealthAggregator(
        logger=context.logger_port,
        health_check_mode=pipeline.runtime.health_check_mode,
        clock=SystemClock(),
    )
    medallion_validator = MedallionConfigValidator(
        config=pipeline.config,
        logger=context.logger_port,
        write_mode_policy=WriteModePolicy(),
    )
    return PreflightService(
        config=pipeline.config,
        context=pipeline.context,
        logger=context.logger_port,
        metrics=pipeline.services.metrics,
        health_aggregator=health_aggregator,
        medallion_validator=medallion_validator,
    )


def build_observer(context: RunnerAssemblyContext) -> PipelineObserver:
    """Build the pipeline observer bound to the current run context."""
    pipeline = context.pipeline
    pipeline_context = pipeline.context
    return PipelineObserver(
        pipeline_name=pipeline.config.pipeline_name,
        run_id=pipeline_context.run_id,
        run_type=pipeline.runtime.run_type,
        metrics=pipeline.services.metrics,
        logger=context.logger_port,
        tracer=context.observability.tracer,
        manifest_id=getattr(pipeline_context, "manifest_id", None),
        entity=getattr(pipeline_context, "entity", None),
        effective_config_hash=getattr(pipeline_context, "effective_config_hash", None),
        contract_ref=getattr(pipeline_context, "contract_ref", None),
        contract_version=getattr(pipeline_context, "contract_version", None),
        composite_run_id=getattr(pipeline_context, "composite_run_id", None),
    )


def build_batch_executor(
    context: RunnerAssemblyContext,
    *,
    checkpoint_manager: CheckpointManagerService,
    lock_manager: LockCoordinator,
    observer: PipelineObserver,
) -> BatchExecutor:
    """Build the batch executor with YAML-derived DQ output paths."""
    dq_output_paths = extract_dq_output_paths(context.yaml_config)
    return ServicesBuilder.create_batch_executor_from_pipeline(
        BatchExecutorBuildRequest(
            pipeline=context.pipeline,
            callbacks=extract_pipeline_callbacks(context.pipeline),
            silver_schema=context.silver_schema,
            gold_schema=context.gold_schema,
            checkpoint_manager=checkpoint_manager,
            shutdown_signal=context.pipeline.shutdown_signal,
            create_batch_processing_components_fn=(
                ServicesBuilder.create_batch_processing_components
            ),
            strict_gold_validation=context.strict_gold_validation,
            lock_validator=lock_manager.validate,
            tracer=context.observability.tracer,
            bronze_output_path=dq_output_paths.bronze_path,
            silver_output_path=dq_output_paths.silver_path,
            gold_output_path=dq_output_paths.gold_path,
            flat_structure=dq_output_paths.flat_structure,
            domain_event_emitter=observer,
        )
    )


def build_postrun_service_for_pipeline(
    context: RunnerAssemblyContext,
    *,
    lifecycle_service: MedallionLifecycleService,
) -> PostrunService:
    """Build the postrun service from YAML-derived DQ config seams."""
    dq_configs = context.dq_configs_extractor(context.yaml_config)
    return build_postrun_service(
        pipeline=context.pipeline,
        logger_port=context.logger_port,
        lifecycle_service=lifecycle_service,
        dq_configs=dq_configs,
        tracer=context.observability.tracer,
    )


def build_runner_constructor_payload(
    *,
    pipeline: BasePipeline,
    observability: ObservabilityBundle,
    parts: RunnerAssemblyParts,
) -> RunnerConstructorPayload:
    """Package runner shell inputs into one typed constructor payload."""
    return RunnerConstructorPayload(
        pipeline=pipeline,
        observability=observability,
        parts=parts,
    )


def assemble_runner_parts(
    context: RunnerAssemblyContext,
    *,
    checkpoint_manager_builder: Callable[..., CheckpointManagerService],
    lock_manager_builder: Callable[..., LockCoordinator],
    preflight_service_builder: Callable[[RunnerAssemblyContext], PreflightService],
    observer_builder: Callable[[RunnerAssemblyContext], PipelineObserver],
    postrun_service_builder: Callable[..., PostrunService],
    batch_executor_builder: Callable[..., BatchExecutor],
) -> RunnerAssemblyParts:
    """Assemble runner collaborators before creating the PipelineRunner shell."""
    checkpoint_manager = checkpoint_manager_builder(
        pipeline=context.pipeline,
        logger_port=context.logger_port,
    )
    lifecycle_service = MedallionLifecycleService(
        storage=context.pipeline.services.storage,
        logger=context.logger_port,
    )
    lock_manager = lock_manager_builder(
        context,
        checkpoint_manager=checkpoint_manager,
        context_holder=LockContextHolder(),
    )
    preflight_service = preflight_service_builder(context)
    observer = observer_builder(context)
    postrun_service = postrun_service_builder(
        context,
        lifecycle_service=lifecycle_service,
    )
    batch_executor = batch_executor_builder(
        context,
        checkpoint_manager=checkpoint_manager,
        lock_manager=lock_manager,
        observer=observer,
    )
    return RunnerAssemblyParts(
        checkpoint_manager=checkpoint_manager,
        lifecycle_service=lifecycle_service,
        lock_manager=lock_manager,
        preflight_service=preflight_service,
        postrun_service=postrun_service,
        observer=observer,
        batch_executor=batch_executor,
    )
