"""Runner assembly helper for pipeline factory."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

from bioetl.application.core.lifecycle import LockCoordinator
from bioetl.application.core.preflight import (
    HealthAggregator,
    MedallionConfigValidator,
    PreflightService,
)
from bioetl.application.observability.observer import PipelineObserver
from bioetl.application.services.checkpoint_compatibility_service import (
    CheckpointCompatibilityService,
)
from bioetl.application.services.medallion_lifecycle import MedallionLifecycleService
from bioetl.composition.bootstrap_contexts import DQConfigsContext
from bioetl.composition.factories.dq.context_resolver import (
    extract_dq_output_paths,
)
from bioetl.composition.factories.pipeline.checkpoint_metadata_helpers import (
    build_current_checkpoint_metadata,
)
from bioetl.composition.factories.pipeline.checkpoint_policy_helpers import (
    resolve_checkpoint_compatibility_policy,
)
from bioetl.composition.factories.pipeline.postrun_assembly import (
    build_postrun_service,
)
from bioetl.composition.factories.pipeline.runner_constructor import (
    RunnerAssemblyParts,
    RunnerConstructorPayload,
    create_pipeline_runner_from_payload,
)
from bioetl.composition.factories.services.factory import ServicesBuilder
from bioetl.domain.locking import LockContextHolder
from bioetl.domain.medallion import LoadingStrategy, WriteModePolicy
from bioetl.domain.types.checkpoint_metadata import CheckpointMetadata

if TYPE_CHECKING:
    import pyarrow as pa

    from bioetl.application.core.base import BasePipeline
    from bioetl.application.core.batch_executor import BatchExecutor
    from bioetl.application.core.lifecycle import CheckpointManagerService
    from bioetl.application.core.postrun import PostrunService
    from bioetl.application.core.runner import PipelineRunner
    from bioetl.composition.observability import ObservabilityBundle
    from bioetl.domain.ports import LoggerPort
    from bioetl.domain.types import GoldSchemaType
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig

__all__ = [
    "assemble_runner_impl",
]


@dataclass(frozen=True, slots=True)
class _RunnerAssemblyContext:
    """Typed seam carrying the inputs shared across runner assembly helpers."""

    pipeline: BasePipeline
    observability: ObservabilityBundle
    logger_port: LoggerPort
    yaml_config: PipelineYamlConfig | None
    silver_schema: pa.Schema | None
    gold_schema: GoldSchemaType
    strict_gold_validation: bool
    dq_configs_extractor: Callable[
        [PipelineYamlConfig | None],
        DQConfigsContext,
    ]


def _build_checkpoint_manager(
    *,
    pipeline: BasePipeline,
    logger_port: LoggerPort,
) -> CheckpointManagerService:
    """Backward-compatible seam for direct unit tests around policy selection."""
    current_metadata = _build_current_checkpoint_metadata(pipeline)
    compatibility_service = CheckpointCompatibilityService(
        logger=logger_port,
        metrics=pipeline.services.metrics,
        pipeline_name=pipeline.config.pipeline_name,
    )
    compatibility_policy = resolve_checkpoint_compatibility_policy(
        pipeline=pipeline,
        logger_port=logger_port,
    )
    return ServicesBuilder.create_checkpoint_manager(
        checkpoint_port=pipeline.services.checkpoint,
        logger=logger_port,
        pipeline_name=pipeline.config.pipeline_name,
        run_id=pipeline.run_id,
        resume=pipeline.runtime.resume,
        loading_strategy=cast(LoadingStrategy | None, pipeline.config.loading_strategy),
        metrics=pipeline.services.metrics,
        checkpoint_compatibility_service=compatibility_service,
        current_metadata=current_metadata,
        compatibility_policy=compatibility_policy,
    )


def _build_current_checkpoint_metadata(pipeline: BasePipeline) -> CheckpointMetadata:
    """Backward-compatible seam for unit tests that patch metadata assembly."""
    return build_current_checkpoint_metadata(pipeline)


def _build_lock_manager(
    context: _RunnerAssemblyContext,
    *,
    checkpoint_manager: CheckpointManagerService,
    context_holder: LockContextHolder,
) -> LockCoordinator:
    pipeline = context.pipeline
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
        logger=context.logger_port,
        shutdown_signal=pipeline.shutdown_signal,
        checkpoint_manager=checkpoint_manager,
        context_holder=context_holder,
    )


def _build_preflight_service(
    context: _RunnerAssemblyContext,
) -> PreflightService:
    pipeline = context.pipeline
    health_aggregator = HealthAggregator(
        metrics=pipeline.services.metrics,
        logger=context.logger_port,
        pipeline_name=pipeline.config.pipeline_name,
        health_check_mode=pipeline.runtime.health_check_mode,
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


def _build_observer(
    context: _RunnerAssemblyContext,
) -> PipelineObserver:
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
        effective_config_hash=getattr(pipeline_context, "config_hash", None),
        contract_ref=getattr(pipeline_context, "contract_ref", None),
        contract_version=getattr(pipeline_context, "contract_version", None),
        composite_run_id=getattr(pipeline_context, "composite_run_id", None),
    )


def _build_batch_executor(
    context: _RunnerAssemblyContext,
    *,
    checkpoint_manager: CheckpointManagerService,
    lock_manager: LockCoordinator,
) -> BatchExecutor:
    dq_output_paths = extract_dq_output_paths(context.yaml_config)
    return ServicesBuilder.create_batch_executor_from_pipeline(
        pipeline=context.pipeline,
        silver_schema=context.silver_schema,
        gold_schema=context.gold_schema,
        checkpoint_manager=checkpoint_manager,
        shutdown_signal=context.pipeline.shutdown_signal,
        strict_gold_validation=context.strict_gold_validation,
        lock_validator=lock_manager.validate,
        tracer=context.observability.tracer,
        bronze_output_path=dq_output_paths.bronze_path,
        silver_output_path=dq_output_paths.silver_path,
        gold_output_path=dq_output_paths.gold_path,
        flat_structure=dq_output_paths.flat_structure,
    )


def _build_postrun_service_for_pipeline(
    context: _RunnerAssemblyContext,
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


def _create_pipeline_runner(
    payload: RunnerConstructorPayload,
) -> PipelineRunner:
    """Backward-compatible seam for unit tests that patch runner creation."""
    return create_pipeline_runner_from_payload(payload)


def _build_runner_constructor_payload(
    *,
    pipeline: BasePipeline,
    observability: ObservabilityBundle,
    parts: RunnerAssemblyParts,
) -> RunnerConstructorPayload:
    """Package the final runner shell inputs into one typed constructor payload."""
    return RunnerConstructorPayload(
        pipeline=pipeline,
        observability=observability,
        parts=parts,
    )


def _assemble_runner_parts(
    context: _RunnerAssemblyContext,
) -> RunnerAssemblyParts:
    """Assemble runner collaborators before creating the PipelineRunner shell."""
    checkpoint_manager = _build_checkpoint_manager(
        pipeline=context.pipeline,
        logger_port=context.logger_port,
    )
    lifecycle_service = MedallionLifecycleService(
        storage=context.pipeline.services.storage,
        logger=context.logger_port,
    )
    lock_manager = _build_lock_manager(
        context,
        checkpoint_manager=checkpoint_manager,
        context_holder=LockContextHolder(),
    )
    preflight_service = _build_preflight_service(context)
    postrun_service = _build_postrun_service_for_pipeline(
        context,
        lifecycle_service=lifecycle_service,
    )
    observer = _build_observer(context)
    batch_executor = _build_batch_executor(
        context,
        checkpoint_manager=checkpoint_manager,
        lock_manager=lock_manager,
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
    """Assemble the fully wired PipelineRunner for one configured pipeline."""
    assembly_context = _RunnerAssemblyContext(
        pipeline=pipeline,
        observability=observability,
        logger_port=observability.logger,
        yaml_config=yaml_config,
        silver_schema=silver_schema,
        gold_schema=gold_schema,
        strict_gold_validation=strict_gold_validation,
        dq_configs_extractor=dq_configs_extractor,
    )
    assembly_parts = _assemble_runner_parts(assembly_context)
    constructor_payload = _build_runner_constructor_payload(
        pipeline=pipeline,
        observability=observability,
        parts=assembly_parts,
    )
    return _create_pipeline_runner(constructor_payload)
