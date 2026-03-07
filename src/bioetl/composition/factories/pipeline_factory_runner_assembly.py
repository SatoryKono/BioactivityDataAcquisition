"""Runner assembly helper for pipeline factory."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, cast

from bioetl.application.core.lock_manager import LockCoordinator
from bioetl.application.core.postrun_service import PostrunService
from bioetl.application.core.preflight_health_aggregator import _HealthAggregator
from bioetl.application.core.preflight_medallion_validator import (
    _MedallionConfigValidator,
)
from bioetl.application.core.preflight_service import PreflightService
from bioetl.application.core.runner import PipelineRunner
from bioetl.application.observability.observer import PipelineObserver
from bioetl.application.services.data_quality_service import DataQualityService
from bioetl.application.services.medallion_lifecycle import MedallionLifecycleService
from bioetl.composition.bootstrap_contexts import DQConfigsContext
from bioetl.composition.factories.pipeline_factory_dq_helpers import (
    extract_dq_output_paths,
)
from bioetl.composition.factories.services_factory import ServicesBuilder
from bioetl.domain.locking import LockContextHolder
from bioetl.domain.medallion import LoadingStrategy, WriteModePolicy

if TYPE_CHECKING:
    import pandera
    import pyarrow as pa

    from bioetl.application.core.base import BasePipeline
    from bioetl.composition.observability import ObservabilityBundle
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig

__all__ = [
    "assemble_runner_impl",
]


def assemble_runner_impl(
    pipeline: BasePipeline,
    observability: ObservabilityBundle,
    silver_schema: pa.Schema | None,
    gold_schema: object,
    strict_gold_validation: bool,
    yaml_config: PipelineYamlConfig | None = None,
    dq_configs_extractor: (
        Callable[
            [PipelineYamlConfig | None],
            DQConfigsContext,
        ]
        | None
    ) = None,
) -> PipelineRunner:
    """Assemble a PipelineRunner from a configured pipeline instance."""
    logger_port = observability.logger

    checkpoint_manager = ServicesBuilder.create_checkpoint_manager(
        checkpoint_port=pipeline.services.checkpoint,
        logger=logger_port,
        pipeline_name=pipeline.config.pipeline_name,
        run_id=pipeline.run_id,
        resume=pipeline.runtime.resume,
        loading_strategy=cast(LoadingStrategy | None, pipeline.config.loading_strategy),
    )

    lifecycle_service = MedallionLifecycleService(
        storage=pipeline.services.storage,
        logger=logger_port,
    )

    context_holder = LockContextHolder()

    lock_manager = LockCoordinator.create(
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

    preflight_service = PreflightService(
        config=pipeline.config,
        context=pipeline.context,
        logger=logger_port,
        metrics=pipeline.services.metrics,
        health_aggregator=health_aggregator,
        medallion_validator=medallion_validator,
    )

    dq_service = DataQualityService(
        dq_monitor=pipeline.services.dq_monitor,
        config=pipeline.config.dq,
        logger=logger_port,
        metrics=pipeline.services.metrics,
        pipeline_name=pipeline.config.pipeline_name,
        entity_type=pipeline.config.entity_type,
    )

    extractor: Callable[[PipelineYamlConfig | None], DQConfigsContext] = (
        dq_configs_extractor
        or (lambda cfg: DQConfigsContext(bronze=None, silver=None, gold=None))
    )
    dq_configs = extractor(yaml_config)

    postrun_service = PostrunService(
        config=pipeline.config,
        runtime=pipeline.runtime,
        context=pipeline.context,
        dq_service=dq_service,
        lifecycle_service=lifecycle_service,
        storage=pipeline.services.storage,
        metrics=pipeline.services.metrics,
        logger=logger_port,
        metadata_coordinator=pipeline.services.metadata_coordinator,
        metadata_writer=pipeline.services.metadata_writer,
        dq_report_service=pipeline.services.dq_report_service,
        bronze_dq_config=dq_configs.bronze if dq_configs else None,
        silver_dq_config=dq_configs.silver if dq_configs else None,
        gold_dq_config=dq_configs.gold if dq_configs else None,
    )

    observer = PipelineObserver(
        pipeline_name=pipeline.config.pipeline_name,
        run_id=pipeline.context.run_id,
        run_type=pipeline.runtime.run_type,
        metrics=pipeline.services.metrics,
        logger=logger_port,
        tracer=observability.tracer,
    )

    dq_output_paths = extract_dq_output_paths(yaml_config)

    batch_executor = ServicesBuilder.create_batch_executor_from_pipeline(
        pipeline=pipeline,
        silver_schema=silver_schema,
        gold_schema=cast("type[pandera.DataFrameModel]", gold_schema),
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

    return PipelineRunner(
        config=pipeline.config,
        runtime=pipeline.runtime,
        services=pipeline.services,
        context=pipeline.context,
        executor=batch_executor,
        checkpoint_manager=checkpoint_manager,
        shutdown_signal=pipeline.shutdown_signal,
        logger=logger_port,
        lock_manager=lock_manager,
        preflight=preflight_service,
        postrun=postrun_service,
        lifecycle_service=lifecycle_service,
        observer=observer,
        pipeline=pipeline,
        tracer=observability.tracer,
    )
