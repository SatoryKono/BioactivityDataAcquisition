"""Runner assembly helper for pipeline factory."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, cast

from bioetl.application.services.checkpoint_compatibility_service import (
    CheckpointCompatibilityService,
)
from bioetl.application.services.medallion_lifecycle import MedallionLifecycleService
from bioetl.composition.bootstrap_contexts import DQConfigsContext
from bioetl.composition.factories.pipeline._runner_assembly_support import (
    RunnerAssemblyContext as _RunnerAssemblyContext,
)
from bioetl.composition.factories.pipeline._runner_assembly_support import (
    build_batch_executor as _build_batch_executor_impl,
)
from bioetl.composition.factories.pipeline._runner_assembly_support import (
    build_lock_runtime_service as _build_lock_runtime_service_impl,
)
from bioetl.composition.factories.pipeline._runner_assembly_support import (
    build_observer as _build_observer_impl,
)
from bioetl.composition.factories.pipeline._runner_assembly_support import (
    build_preflight_service as _build_preflight_service_impl,
)
from bioetl.composition.factories.pipeline._runner_assembly_support import (
    build_runner_constructor_payload as _build_runner_constructor_payload_impl,
)
from bioetl.composition.factories.pipeline.checkpoint_metadata_helpers import (
    build_current_checkpoint_metadata,
)
from bioetl.composition.factories.pipeline.checkpoint_policy_helpers import (
    resolve_checkpoint_compatibility_policy,
)
from bioetl.composition.factories.pipeline.postrun_assembly import build_postrun_service
from bioetl.composition.factories.pipeline.runner_constructor import (
    RunnerAssemblyParts,
    create_pipeline_runner_from_payload,
)
from bioetl.composition.factories.services.factory import ServicesBuilder
from bioetl.domain.locking import LockContextHolder
from bioetl.domain.medallion import LoadingStrategy
from bioetl.domain.types.checkpoint_metadata import CheckpointMetadata

if TYPE_CHECKING:
    import pyarrow as pa

    from bioetl.application.core.base import BasePipeline
    from bioetl.application.core.batch_executor import BatchExecutor
    from bioetl.application.core.lifecycle import (
        CheckpointRuntimeService,
        LockRuntimeService,
    )
    from bioetl.application.core.postrun import PostrunService
    from bioetl.application.core.preflight import PreflightService
    from bioetl.application.core.runner import PipelineRunner
    from bioetl.application.observability.observer import PipelineObserver
    from bioetl.composition.factories.pipeline.runner_constructor import (
        RunnerConstructorPayload,
    )
    from bioetl.composition.observability import ObservabilityBundle
    from bioetl.domain.ports import LoggerPort
    from bioetl.domain.types import GoldSchemaType
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig

__all__ = ["assemble_runner_impl"]


def _build_checkpoint_manager(
    *,
    pipeline: BasePipeline,
    logger_port: LoggerPort,
) -> CheckpointRuntimeService:
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
    return build_current_checkpoint_metadata(pipeline)


def _build_lock_runtime_service(
    context: _RunnerAssemblyContext,
    *,
    checkpoint_manager: CheckpointRuntimeService,
    context_holder: LockContextHolder,
) -> LockRuntimeService:
    return _build_lock_runtime_service_impl(
        context,
        checkpoint_manager=checkpoint_manager,
        context_holder=context_holder,
    )


def _build_lock_manager(
    context: _RunnerAssemblyContext,
    *,
    checkpoint_manager: CheckpointRuntimeService,
    context_holder: LockContextHolder,
) -> LockRuntimeService:
    """Compatibility seam for tests still patching the legacy helper name."""
    return _build_lock_runtime_service(
        context,
        checkpoint_manager=checkpoint_manager,
        context_holder=context_holder,
    )


def _build_preflight_service(
    context: _RunnerAssemblyContext,
) -> PreflightService:
    return _build_preflight_service_impl(context)


def _build_observer(
    context: _RunnerAssemblyContext,
) -> PipelineObserver:
    return _build_observer_impl(context)


def _build_batch_executor(
    context: _RunnerAssemblyContext,
    *,
    checkpoint_manager: CheckpointRuntimeService,
    lock_runtime_service: LockRuntimeService,
    observer: PipelineObserver,
) -> BatchExecutor:
    return _build_batch_executor_impl(
        context,
        checkpoint_manager=checkpoint_manager,
        lock_runtime_service=lock_runtime_service,
        observer=observer,
    )


def _create_pipeline_runner(
    payload: RunnerConstructorPayload,
) -> PipelineRunner:
    return create_pipeline_runner_from_payload(payload)


def _build_postrun_service(
    context: _RunnerAssemblyContext,
    *,
    lifecycle_service: MedallionLifecycleService,
) -> PostrunService:
    return build_postrun_service(
        pipeline=context.pipeline,
        logger_port=context.logger_port,
        lifecycle_service=lifecycle_service,
        dq_configs=context.dq_configs_extractor(context.yaml_config),
        tracer=context.observability.tracer,
    )


def _build_runner_constructor_payload(
    *,
    pipeline: BasePipeline,
    observability: ObservabilityBundle,
    parts: RunnerAssemblyParts,
) -> RunnerConstructorPayload:
    return _build_runner_constructor_payload_impl(
        pipeline=pipeline,
        observability=observability,
        parts=parts,
    )


def _assemble_runner_parts(
    context: _RunnerAssemblyContext,
) -> RunnerAssemblyParts:
    checkpoint_manager = _build_checkpoint_manager(
        pipeline=context.pipeline,
        logger_port=context.logger_port,
    )
    lifecycle_service = MedallionLifecycleService(
        storage=context.pipeline.services.storage,
        logger=context.logger_port,
    )
    lock_runtime_service = _build_lock_runtime_service(
        context,
        checkpoint_manager=checkpoint_manager,
        context_holder=LockContextHolder(),
    )
    preflight_service = _build_preflight_service(context)
    observer = _build_observer(context)
    postrun_service = _build_postrun_service(
        context,
        lifecycle_service=lifecycle_service,
    )
    batch_executor = _build_batch_executor(
        context,
        checkpoint_manager=checkpoint_manager,
        lock_runtime_service=lock_runtime_service,
        observer=observer,
    )
    return RunnerAssemblyParts(
        checkpoint_manager=checkpoint_manager,
        lifecycle_service=lifecycle_service,
        lock_runtime_service=lock_runtime_service,
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
